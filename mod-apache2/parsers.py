"""Parsers of the three Apache sources: access.log, error.log and the
ModSecurity audit log (native serial, JSON, and the index of the concurrent
type). They are tolerant: what does not fit is kept as "unparsed" and counts
for the health of its source; nothing is dropped.

Every parser returns a record: time (storage format), correlation
(UNIQUE_ID when known), parse_status, fields and raw (masked).
"""

import json
import os
import re
from pathlib import Path

from backend.core.masking import fTrim
from backend.core.timeutil import fFormatStorage, fParseApacheAccessTime, fParseApacheErrorTime
from .logformat import AccessFormat, dKnownFormats, fSplitRequestLine, lFallbackFormats
from .modsec import fParseMessage

cErrorRegex = re.compile(
  r"^\[(?P<time>[^\]]+)\] \[(?:(?P<module>[^:\]]*):)?(?P<level>[^\]]+)\](?: \[pid (?P<pid>\d+)(?::tid (?P<tid>\d+))?\])?"
  r"(?: (?P<errno>\([^)]*\)[^:\[]*):)?(?: \[client (?P<client>[^\]]+)\])?(?: \[client [^\]]+\])?(?: (?P<message>.*))?$"
)
cAhRegex = re.compile(r"\b(AH\d{5})\b")
cReferrerRegex = re.compile(r", referer: (\S+)$")
cDatabaseRegex = re.compile(
  r"SQLSTATE\[|PDOException|You have an error in your SQL syntax|mysqli?_|mysql_fetch|pg_query|PostgreSQL query failed|"
  r"\bORA-\d{5}\b|SQLite3?::|Unclosed quotation mark|unterminated quoted string|Warning: mysql|supplied argument is not a valid MySQL",
  re.IGNORECASE
)
cPhpRegex = re.compile(r"PHP (Fatal error|Parse error|Warning|Notice|Deprecated|Recoverable fatal error|Catchable fatal error)", re.IGNORECASE)
cCrashRegex = re.compile(r"Segmentation fault|exit signal|possible coredump|child pid \d+ exit", re.IGNORECASE)
cAuditBoundaryRegex = re.compile(r"^--([0-9a-zA-Z]{8,})-([A-Z])--$")
cAuditSectionARegex = re.compile(r"^\[([^\]]+)\] (\S+) (\S+) (\d+) (\S+) (\d+)")
cHeaderLineRegex = re.compile(r"^([A-Za-z0-9!#$%&'*+.^_`|~-]+):\s?(.*)$")
cMaxBodyChars = 16384


def fClientIp(pValue: str) -> str:
  # "203.0.113.7:51234" or "[2001:db8::1]:51234" or "2001:db8::1:51234".
  vValue = str(pValue or "").strip()
  if vValue.startswith("["):
    return vValue[1:vValue.find("]")].lower() if "]" in vValue else vValue.lower()
  if vValue.count(":") == 1:
    return vValue.split(":")[0]
  if vValue.count(":") > 1:
    vHead, _, vTail = vValue.rpartition(":")
    return (vHead if vTail.isdigit() and vHead.count(":") >= 2 else vValue).lower()
  return vValue


def fNormalizeHost(pValue: str) -> str:
  vValue = str(pValue or "").strip().lower()
  if vValue.startswith("["):
    return vValue
  return vValue.split(":")[0] if vValue.count(":") == 1 else vValue


class AccessParser:

  def __init__(self, pMasker, pFormat: str = "", pVhost: str = "", pFormats: dict | None = None):
    self.vMasker = pMasker
    self.vVhost = pVhost
    dFormats = dict(dKnownFormats)
    dFormats.update(pFormats or {})
    self.lFormats = []
    if pFormat:
      vText = dFormats.get(pFormat, pFormat)
      if "%" in vText:
        self.lFormats.append(AccessFormat(vText, pFormat))
    for vName in lFallbackFormats:
      vText = dFormats.get(vName, dKnownFormats[vName])
      if not any(vFormat.vFormat == vText for vFormat in self.lFormats):
        self.lFormats.append(AccessFormat(vText, vName))
    self.vLast = 0

  def mParse(self, pLine: str) -> dict:
    vMasked = self.vMasker.mMaskText(pLine)
    # The last format that worked is tried first: a file uses one format.
    lOrder = [self.vLast] + [vIndex for vIndex in range(len(self.lFormats)) if vIndex != self.vLast]
    for vIndex in lOrder:
      dParsed = self.lFormats[vIndex].mParse(pLine)
      if dParsed is None:
        continue
      self.vLast = vIndex
      return self.mBuild(dParsed, vMasked, self.lFormats[vIndex])
    return {"time": None, "correlation": None, "parse_status": "unparsed", "fields": {}, "raw": vMasked}

  def mBuild(self, pParsed: dict, pMasked: str, pFormat: AccessFormat) -> dict:
    dRaw = pParsed["fields"]
    dFields = {"format": pFormat.vName or "custom"}
    vStatus = "ok"
    vIp = dRaw.get("client_ip") or dRaw.get("remote_host")
    if vIp:
      dFields["client_ip"] = vIp.lower()
    if dRaw.get("user"):
      dFields["user"] = dRaw["user"]
    dRequest = fSplitRequestLine(dRaw.get("request_line", ""))
    if dRaw.get("request_line") and not dRequest:
      vStatus = "partial"
      dFields["request_line"] = fTrim(self.vMasker.mMaskText(dRaw["request_line"]), 2000)
    if dRaw.get("method") and "method" not in dRequest:
      dRequest["method"] = dRaw["method"]
    if dRaw.get("url_path") and "path" not in dRequest:
      dRequest["path"] = dRaw["url_path"]
      vQuery = (dRaw.get("query_string") or "").lstrip("?")
      dRequest["uri"] = dRaw["url_path"] + ("?" + vQuery if vQuery else "")
      if vQuery:
        dRequest["query"] = vQuery
    if dRequest.get("uri"):
      dRequest["uri"] = fTrim(self.vMasker.mMaskUri(dRequest["uri"]), 4000)
    if dRequest.get("query"):
      dRequest["query"] = fTrim(self.vMasker.mMaskForm(dRequest["query"]), 4000)
    dFields.update(dRequest)
    for vName in ("status", "bytes", "duration_us"):
      if dRaw.get(vName, "").isdigit():
        dFields[vName] = int(dRaw[vName])
    if "status" not in dFields and dRaw.get("status_original", "").isdigit():
      dFields["status"] = int(dRaw["status_original"])
    if "bytes" not in dFields and dRaw.get("bytes_body", "").isdigit():
      dFields["bytes"] = int(dRaw["bytes_body"])
    if "duration_us" not in dFields:
      if dRaw.get("duration_ms", "").isdigit():
        dFields["duration_us"] = int(dRaw["duration_ms"]) * 1000
      elif dRaw.get("duration_s", "").isdigit():
        dFields["duration_us"] = int(dRaw["duration_s"]) * 1000000
    for vName in ("referer", "ua"):
      if dRaw.get(vName):
        dFields[vName] = fTrim(self.vMasker.mMaskUri(dRaw[vName]) if vName == "referer" else dRaw[vName], 1000)
    vVhost = dRaw.get("vhost") or dRaw.get("server_name") or self.vVhost or dRaw.get("host_header")
    if vVhost:
      dFields["vhost"] = fNormalizeHost(vVhost)
    if dRaw.get("port", "").isdigit():
      dFields["port"] = int(dRaw["port"])
    vUid = dRaw.get("uid")
    if pParsed["time"] is None:
      vStatus = "partial"
    return {
      "time": fFormatStorage(pParsed["time"]) if pParsed["time"] else None,
      "correlation": vUid or None,
      "parse_status": vStatus,
      "fields": dFields,
      "raw": pMasked
    }


def fParseErrorLine(pLine: str, pMasker) -> dict:
  vMasked = pMasker.mMaskText(pLine)
  vMatch = cErrorRegex.match(pLine)
  if vMatch is None:
    # Apache writes some start-up messages before its error log format
    # applies: "AH00558: apache2: Could not reliably determine...".
    vAh = cAhRegex.match(pLine.strip())
    if vAh:
      return {
        "time": None, "correlation": None, "parse_status": "partial",
        "fields": {"error_type": "apache", "ah_code": vAh.group(1), "message": fTrim(vMasked, 4000)}, "raw": vMasked
      }
    return {"time": None, "correlation": None, "parse_status": "unparsed", "fields": {}, "raw": vMasked}
  vTime = fParseApacheErrorTime(vMatch.group("time"))
  vMessage = vMatch.group("message") or ""
  dFields = {
    "error_module": vMatch.group("module") or "",
    "level": vMatch.group("level") or "",
  }
  if vMatch.group("client"):
    dFields["client_ip"] = fClientIp(vMatch.group("client"))
  vReferrer = cReferrerRegex.search(vMessage)
  if vReferrer:
    dFields["referer"] = fTrim(pMasker.mMaskUri(vReferrer.group(1)), 1000)
    vMessage = vMessage[:vReferrer.start()]
  vAh = cAhRegex.search(vMessage)
  if vAh:
    dFields["ah_code"] = vAh.group(1)
  if vMatch.group("errno"):
    dFields["errno"] = vMatch.group("errno").strip()
  vCorrelation = None
  if vMessage.startswith("ModSecurity: "):
    dModsec = fParseMessage(vMessage[len("ModSecurity: "):])
    dFields["error_type"] = "modsecurity"
    dFields["modsecurity"] = fMaskMessage(dModsec, pMasker)
    vCorrelation = dModsec.get("unique_id") or None
    if dModsec.get("hostname"):
      dFields["vhost"] = fNormalizeHost(dModsec["hostname"])
    if dModsec.get("uri"):
      dFields["path"] = fTrim(pMasker.mMaskUri(dModsec["uri"]), 4000)
  elif cDatabaseRegex.search(vMessage):
    dFields["error_type"] = "database"
    dFields["db_error"] = True
  elif cPhpRegex.search(vMessage):
    dFields["error_type"] = "php"
    dFields["php_level"] = cPhpRegex.search(vMessage).group(1)
  elif cCrashRegex.search(vMessage):
    dFields["error_type"] = "crash"
  else:
    dFields["error_type"] = "apache"
  if dFields["error_type"] in ("php",) and cDatabaseRegex.search(vMessage):
    dFields["db_error"] = True
  if dFields["error_type"] != "modsecurity":
    # A ModSecurity line is already in its parsed form and in the raw line.
    dFields["message"] = fTrim(pMasker.mMaskText(vMessage), 4000)
  return {
    "time": fFormatStorage(vTime) if vTime else None,
    "correlation": vCorrelation,
    "parse_status": "ok" if vTime else "partial",
    "fields": dFields,
    "raw": vMasked
  }


def fMaskMessage(pMessage: dict, pMasker) -> dict:
  # What the analyst and the decisions need; the whole message stays in the
  # raw record (file, line, version and the other tags would only repeat it).
  dResult = {}
  for vKey in ("kind", "id", "msg", "data", "severity", "phase", "code", "tags", "head"):
    if vKey not in pMessage or pMessage[vKey] in (None, "", []):
      continue
    if vKey == "head" and pMessage.get("id"):
      continue
    vValue = pMessage[vKey]
    if vKey == "tags":
      vValue = [vTag for vTag in vValue if vTag.lower().startswith(("attack-", "paranoia-level"))]
      if not vValue:
        continue
    if vKey in ("data", "msg", "head"):
      vValue = fTrim(pMasker.mMaskText(vValue), 2000)
    elif vKey == "uri":
      vValue = fTrim(pMasker.mMaskUri(vValue), 2000)
    dResult[vKey] = vValue
  return dResult


class AuditFramer:
  # Native serial records span many lines (--id-A-- ... --id-Z--); JSON
  # records are one line each. A record is only complete at its Z line, so
  # the commit position stays before an unfinished record.

  def __init__(self):
    self.lLines = []
    self.vStart = None
    self.vLastEnd = None

  def mFeed(self, pText: str, pDevice: int, pInode: int, pOffset: int) -> list[tuple]:
    vStripped = pText.strip()
    if not self.lLines:
      if vStripped.startswith("{"):
        self.vLastEnd = (pDevice, pInode, pOffset)
        return [(vStripped, (pDevice, pInode, pOffset))]
      vMatch = cAuditBoundaryRegex.match(vStripped)
      if vMatch and vMatch.group(2) == "A":
        self.lLines = [pText]
        return []
      # Blank lines between records and anything unexpected outside a record.
      self.vLastEnd = (pDevice, pInode, pOffset)
      return [] if not vStripped else [(pText, (pDevice, pInode, pOffset))]
    self.lLines.append(pText)
    vMatch = cAuditBoundaryRegex.match(vStripped)
    if vMatch and vMatch.group(2) == "Z":
      vText = "\n".join(self.lLines)
      self.lLines = []
      self.vLastEnd = (pDevice, pInode, pOffset)
      return [(vText, (pDevice, pInode, pOffset))]
    if len(self.lLines) > 20000:
      # A record without end: give it up as unparsed.
      vText = "\n".join(self.lLines)
      self.lLines = []
      return [(vText, (pDevice, pInode, pOffset))]
    return []

  def mSafeCommit(self):
    # While a record is open, only up to the end of the previous unit.
    if self.lLines:
      return self.vLastEnd if self.vLastEnd is not None else False
    return None


def fParseAuditRecord(pText: str, pMasker, pLowDisk: bool) -> dict:
  vStripped = pText.strip()
  if vStripped.startswith("{"):
    # matched_rules (part K) is the last and by far the largest member of a
    # mod_security2 JSON record: it is cut before decoding when possible.
    vCut = vStripped.find(',"matched_rules":')
    dDocument = None
    if vCut > 0:
      try:
        dDocument = json.loads(vStripped[:vCut] + "}")
      except ValueError:
        dDocument = None
    try:
      if dDocument is None:
        dDocument = json.loads(vStripped)
    except ValueError:
      return {"time": None, "correlation": None, "parse_status": "unparsed", "fields": {}, "raw": fTrim(pMasker.mMaskText(pText), 65536)}
    return fParseAuditJson(dDocument, pMasker, pLowDisk)
  if cAuditBoundaryRegex.match(vStripped.split("\n", 1)[0]):
    return fParseAuditNative(pText, pMasker, pLowDisk)
  return {"time": None, "correlation": None, "parse_status": "unparsed", "fields": {}, "raw": fTrim(pMasker.mMaskText(pText), 65536)}


def fHeaderDict(pLines: list[str]) -> dict:
  dHeaders = {}
  for vLine in pLines:
    vMatch = cHeaderLineRegex.match(vLine)
    if vMatch:
      vName = vMatch.group(1)
      dHeaders[vName] = (dHeaders[vName] + ", " + vMatch.group(2)) if vName in dHeaders else vMatch.group(2)
  return dHeaders


def fGetHeader(pHeaders: dict, pName: str) -> str:
  for vName, vValue in (pHeaders or {}).items():
    if vName.lower() == pName.lower():
      return str(vValue)
  return ""


def fParseAuditNative(pText: str, pMasker, pLowDisk: bool) -> dict:
  dSections = {}
  vCurrent = None
  for vLine in pText.split("\n"):
    vMatch = cAuditBoundaryRegex.match(vLine.strip())
    if vMatch:
      vCurrent = vMatch.group(2)
      dSections.setdefault(vCurrent, [])
      continue
    if vCurrent is not None:
      dSections[vCurrent].append(vLine)
  dFields = {"audit_format": "native"}
  vStatus = "ok"
  vTime = None
  vUid = None
  lA = [vLine for vLine in dSections.get("A", []) if vLine.strip()]
  if lA:
    vMatch = cAuditSectionARegex.match(lA[0])
    if vMatch:
      vTime = fParseApacheAccessTime(vMatch.group(1))
      vUid = vMatch.group(2)
      dFields.update({
        "client_ip": vMatch.group(3).lower(), "client_port": int(vMatch.group(4)),
        "server_ip": vMatch.group(5), "server_port": int(vMatch.group(6))
      })
  if vTime is None or vUid is None:
    vStatus = "partial"
  lB = [vLine for vLine in dSections.get("B", [])]
  while lB and not lB[0].strip():
    lB.pop(0)
  dRequestHeaders = {}
  if lB:
    dFields.update(fSplitRequestLine(lB[0].strip()))
    dRequestHeaders = fHeaderDict(lB[1:])
  vBody = "\n".join(dSections.get("I", []) or dSections.get("C", [])).strip("\n")
  lF = [vLine for vLine in dSections.get("F", []) if vLine.strip()]
  dResponseHeaders = {}
  if lF:
    vStatusMatch = re.match(r"^\S+ (\d{3})", lF[0])
    if vStatusMatch:
      dFields["status"] = int(vStatusMatch.group(1))
    dResponseHeaders = fHeaderDict(lF[1:])
  lMessages = []
  dAction = None
  for vLine in dSections.get("H", []):
    if vLine.startswith("Message: "):
      lMessages.append(fParseMessage(vLine[len("Message: "):]))
    elif vLine.startswith("Action: "):
      vMatch = re.search(r"Intercepted \(phase (\d)\)", vLine)
      dAction = {"intercepted": bool(vMatch), "phase": int(vMatch.group(1)) if vMatch else None}
    elif vLine.startswith("Engine-Mode: "):
      dFields["engine_mode"] = vLine[len("Engine-Mode: "):].strip().strip("\"")
    elif vLine.startswith("Producer: "):
      dFields["producer"] = vLine[len("Producer: "):].strip()
    elif vLine.startswith("Server: "):
      dFields["server"] = vLine[len("Server: "):].strip()
    elif vLine.startswith("Apache-Handler: "):
      dFields["handler"] = vLine[len("Apache-Handler: "):].strip()
  return fFinishAudit(dFields, vTime, vUid, vStatus, dRequestHeaders, vBody, dResponseHeaders, lMessages, dAction, pMasker, pLowDisk, pText, None)


def fParseAuditJson(pDocument: dict, pMasker, pLowDisk: bool) -> dict:
  dFields = {"audit_format": "json"}
  vStatus = "ok"
  dTransaction = pDocument.get("transaction") or {}
  dRequest = pDocument.get("request") or {}
  dResponse = pDocument.get("response") or {}
  dAudit = pDocument.get("audit_data") or {}
  vTime = fParseApacheAccessTime(str(dTransaction.get("time") or ""))
  vUid = dTransaction.get("transaction_id") or dTransaction.get("unique_id")
  if dTransaction.get("remote_address"):
    dFields["client_ip"] = str(dTransaction["remote_address"]).lower()
  for vSource, vTarget in (("remote_port", "client_port"), ("local_port", "server_port")):
    if str(dTransaction.get(vSource, "")).isdigit():
      dFields[vTarget] = int(dTransaction[vSource])
  if dTransaction.get("local_address"):
    dFields["server_ip"] = str(dTransaction["local_address"])
  if vTime is None or not vUid:
    vStatus = "partial"
  if dRequest.get("request_line"):
    dFields.update(fSplitRequestLine(str(dRequest["request_line"])))
  dRequestHeaders = dRequest.get("headers") if isinstance(dRequest.get("headers"), dict) else {}
  vBody = dRequest.get("body")
  if isinstance(vBody, list):
    vBody = "\n".join(str(vItem) for vItem in vBody)
  vBody = str(vBody or "")
  if str(dResponse.get("status", "")).isdigit():
    dFields["status"] = int(dResponse["status"])
  dResponseHeaders = dResponse.get("headers") if isinstance(dResponse.get("headers"), dict) else {}
  lMessages = [fParseMessage(vItem) for vItem in (dAudit.get("messages") or []) if isinstance(vItem, str)]
  dAction = None
  if isinstance(dAudit.get("action"), dict):
    dAction = {
      "intercepted": bool(dAudit["action"].get("intercepted")),
      "phase": dAudit["action"].get("phase"),
      "message": str(dAudit["action"].get("message") or "")[:500]
    }
  if dAudit.get("engine_mode"):
    dFields["engine_mode"] = str(dAudit["engine_mode"])
  if dAudit.get("producer"):
    vProducer = dAudit["producer"]
    dFields["producer"] = "; ".join(vProducer) if isinstance(vProducer, list) else str(vProducer)
  if dAudit.get("server"):
    dFields["server"] = str(dAudit["server"])
  if dAudit.get("handler"):
    dFields["handler"] = str(dAudit["handler"])
  return fFinishAudit(dFields, vTime, vUid, vStatus, dRequestHeaders, vBody, dResponseHeaders, lMessages, dAction, pMasker, pLowDisk, None, pDocument)


def fFinishAudit(pFields, pTime, pUid, pStatus, pRequestHeaders, pBody, pResponseHeaders, pMessages, pAction, pMasker, pLowDisk, pNativeText, pJson) -> dict:
  dFields = pFields
  if dFields.get("uri"):
    dFields["uri"] = fTrim(pMasker.mMaskUri(dFields["uri"]), 4000)
  if dFields.get("query"):
    dFields["query"] = fTrim(pMasker.mMaskForm(dFields["query"]), 4000)
  vHost = fGetHeader(pRequestHeaders, "Host")
  if vHost:
    dFields["vhost"] = fNormalizeHost(vHost)
  vAgent = fGetHeader(pRequestHeaders, "User-Agent")
  if vAgent:
    dFields["ua"] = fTrim(vAgent, 1000)
  vReferrer = fGetHeader(pRequestHeaders, "Referer")
  if vReferrer:
    dFields["referer"] = fTrim(pMasker.mMaskUri(vReferrer), 1000)
  dFields["messages"] = [fMaskMessage(dMessage, pMasker) for dMessage in pMessages[:100]]
  if pAction is not None:
    dFields["action"] = pAction
  vContentType = fGetHeader(pRequestHeaders, "Content-Type")
  dMaskedRequestHeaders = {vName: fTrim(str(vValue), 2000) for vName, vValue in pMasker.mMaskHeaders(pRequestHeaders).items()}
  dMaskedResponseHeaders = {vName: fTrim(str(vValue), 2000) for vName, vValue in pMasker.mMaskHeaders(pResponseHeaders).items()}
  vMaskedBody = "" if pLowDisk or not pBody else fTrim(pMasker.mMaskBody(pBody, vContentType), cMaxBodyChars)
  # Headers and body stay only in the raw record (the request card reads them
  # from it, fAuditDisplay): kept twice, they doubled the database.
  if pLowDisk:
    dFields["detail_dropped"] = True
  # The raw text is rebuilt from the masked parts: the original audit record
  # may hold passwords and cookies. Part K (the full text of every rule run,
  # CRS set-up rules included) is dropped: it is most of the size of a record
  # and the messages already name the rules.
  if pJson is not None:
    dRaw = dict(pJson)
    dRawRequest = dict(dRaw.get("request") or {})
    dRawRequest["headers"] = dMaskedRequestHeaders if not pLowDisk else {}
    if "body" in dRawRequest:
      dRawRequest["body"] = vMaskedBody
    if dRawRequest.get("request_line"):
      dRawRequest["request_line"] = pMasker.mMaskText(str(dRawRequest["request_line"]))
    dRaw["request"] = dRawRequest
    dRawResponse = dict(dRaw.get("response") or {})
    dRawResponse["headers"] = dMaskedResponseHeaders if not pLowDisk else {}
    dRawResponse.pop("body", None)
    dRaw["response"] = dRawResponse
    dRawAudit = dict(dRaw.get("audit_data") or {})
    if isinstance(dRawAudit.get("messages"), list):
      dRawAudit["messages"] = [pMasker.mMaskText(str(vItem)) for vItem in dRawAudit["messages"]]
    # error_messages repeats the messages in the error.log format.
    dRawAudit.pop("error_messages", None)
    dRawAudit.pop("matched_rules", None)
    dRaw["audit_data"] = dRawAudit
    dRaw.pop("matched_rules", None)
    vRaw = json.dumps(dRaw, ensure_ascii=False, separators=(",", ":"))
  else:
    vRaw = fMaskNativeText(pNativeText, pMasker, pLowDisk, vContentType)
  # Text for the full-text index: what an analyst searches for, not the whole
  # record.
  lSearch = [str(dFields.get("method", "")) + " " + str(dFields.get("uri", "")), fGetHeader(pRequestHeaders, "Host"), vAgent]
  for dMessage in dFields["messages"]:
    lSearch.append(" ".join(str(dMessage.get(vKey, "")) for vKey in ("id", "msg", "data")))
  return {
    "time": fFormatStorage(pTime) if pTime else None,
    "correlation": pUid or None,
    "parse_status": pStatus,
    "fields": dFields,
    "raw": fTrim(vRaw, 65536),
    "search": "\n".join(vItem for vItem in lSearch if vItem)
  }


def fAuditDisplay(pRaw: str) -> dict:
  # Headers and body of a stored (already masked) audit record, for the
  # request card.
  dResult = {}
  vText = str(pRaw or "").strip()
  if vText.startswith("{"):
    try:
      dDocument = json.loads(vText)
    except ValueError:
      return dResult
    dRequest = dDocument.get("request") or {}
    dResponse = dDocument.get("response") or {}
    if isinstance(dRequest.get("headers"), dict) and dRequest["headers"]:
      dResult["request_headers"] = dRequest["headers"]
    vBody = dRequest.get("body")
    if isinstance(vBody, list):
      vBody = "\n".join(str(vItem) for vItem in vBody)
    if vBody:
      dResult["request_body"] = str(vBody)
    if isinstance(dResponse.get("headers"), dict) and dResponse["headers"]:
      dResult["response_headers"] = dResponse["headers"]
    return dResult
  dSections = {}
  vCurrent = None
  for vLine in vText.split("\n"):
    vMatch = cAuditBoundaryRegex.match(vLine.strip())
    if vMatch:
      vCurrent = vMatch.group(2)
      dSections.setdefault(vCurrent, [])
      continue
    if vCurrent is not None:
      dSections[vCurrent].append(vLine)
  lB = [vLine for vLine in dSections.get("B", []) if vLine.strip()]
  if len(lB) > 1:
    dResult["request_headers"] = fHeaderDict(lB[1:])
  vBody = "\n".join(dSections.get("I", []) or dSections.get("C", [])).strip("\n")
  if vBody:
    dResult["request_body"] = vBody
  lF = [vLine for vLine in dSections.get("F", []) if vLine.strip()]
  if len(lF) > 1:
    dResult["response_headers"] = fHeaderDict(lF[1:])
  return dResult


def fMaskNativeText(pText: str, pMasker, pLowDisk: bool, pContentType: str) -> str:
  lOutput = []
  vCurrent = None
  lBody = []

  def fFlushBody():
    if lBody:
      if not pLowDisk:
        lOutput.append(fTrim(pMasker.mMaskBody("\n".join(lBody), pContentType), cMaxBodyChars))
      lBody.clear()

  for vLine in pText.split("\n"):
    vMatch = cAuditBoundaryRegex.match(vLine.strip())
    if vMatch:
      fFlushBody()
      vCurrent = vMatch.group(2)
      # Response bodies (E) are never kept.
      lOutput.append(vLine)
      continue
    if vCurrent in ("C", "I"):
      lBody.append(vLine)
    elif vCurrent in ("E", "K"):
      # Response body (E) and the full text of the rules run (K) are not kept.
      continue
    elif vCurrent in ("B", "F"):
      if pLowDisk and lOutput and not cAuditBoundaryRegex.match(lOutput[-1].strip()):
        continue
      vHeader = cHeaderLineRegex.match(vLine)
      if vHeader and (pMasker.mIsSensitiveHeader(vHeader.group(1))):
        lOutput.append(vHeader.group(1) + ": ***")
      else:
        lOutput.append(pMasker.mMaskText(vLine))
    else:
      lOutput.append(pMasker.mMaskText(vLine))
  fFlushBody()
  return "\n".join(lOutput)


def fReadConcurrentEntry(pLine: str, pStorageDirectory: str) -> str | None:
  # The index of the concurrent type has one line per transaction; the
  # second to last field is the file, relative to SecAuditLogStorageDir.
  vMatch = re.search(r" (/\S+) (\d+) (\d+) md5:", pLine) or re.search(r" (/\S+) (\d+) (\d+)", pLine)
  if vMatch is None:
    return None
  vRelative = vMatch.group(1)
  vPath = Path(pStorageDirectory) / vRelative.lstrip("/")
  try:
    vResolved = vPath.resolve()
    if not str(vResolved).startswith(str(Path(pStorageDirectory).resolve()) + os.sep):
      return None
    with vResolved.open("r", encoding="utf-8", errors="backslashreplace") as vFile:
      return vFile.read(8 * 1024 * 1024)
  except OSError:
    return None
