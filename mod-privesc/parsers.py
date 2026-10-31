"""Parsers of the privesc module: audit records, hook lines and syslog lines.

Every parser returns a record of the core (time, received, module, source,
source_key, correlation, parse_status, fields, raw, search) whose text is
masked: command lines may hold passwords (mysql -pSECRET, sshpass -p,
curl -u user:pass, PASSWORD=...). The raw text of an audit record is rebuilt
from its masked and decoded parts: auditd writes in hexadecimal the values
with spaces or special characters, and the hexadecimal of a password would
keep the password.
"""

import datetime
import re
import shlex
import time

from backend.core.masking import fTrim
from backend.core.timeutil import fEpochToStorage, fFormatStorage, fParseStorage

cAuditLineRegex = re.compile(r"^(?:node=(?P<node>\S+) )?type=(?P<type>\S+) msg=audit\((?P<seconds>\d+)\.(?P<millis>\d+):(?P<serial>\d+)\):\s*(?P<body>.*)$")
cPairRegex = re.compile(r"([A-Za-z_][\w\-\[\]]*)=(\"[^\"]*\"|'[^']*'|\S*)")
cHexRegex = re.compile(r"^(?:[0-9A-Fa-f]{2})+$")
cArgRegex = re.compile(r"^a(\d+)(?:\[(\d+)\])?$")
# Values auditd encodes in hexadecimal when they hold spaces, quotes or
# control characters (the "untrusted strings").
sEncodedFields = {"proctitle", "cwd", "name", "comm", "exe", "cmd", "acct", "path", "data", "old-path", "new-path", "key", "ocomm", "root_dir"}
cMaxArgs = 128
cMaxArgLength = 4096
cMaxCommand = 8192

lCommandMasks = [
  (re.compile(r"(?i)(--?(?:password|passwd|pass|token|secret|api-?key|apikey)[= ])(\S+)"), r"\1***"),
  (re.compile(r"(\bsshpass\s+-p\s*)(\S+)"), r"\1***"),
  (re.compile(r"(://[^/\s:@]+:)([^@\s/]+)(@)"), r"\1***\3"),
  (re.compile(r"(\s(?:-u|--user)\s+[^:\s]+:)(\S+)"), r"\1***"),
  (re.compile(r"(?i)\b(\w*(?:password|passwd|pwd|token|secret|api_?key)\w*=)(\S+)"), r"\1***"),
  (re.compile(r"(\becho\s+)(\S+)(\s*\|\s*(?:sudo\s+-S|chpasswd|passwd|openssl\s+passwd))"), r"\1***\3"),
  (re.compile(r"(\b(?:usermod|useradd)\b.*?\s-p\s+)(\S+)"), r"\1***"),
  (re.compile(r"(\bopenssl\s+passwd\b(?:\s+-\S+)*\s+)(\S+)"), r"\1***")
]
cMysqlRegex = re.compile(r"\b(mysql|mariadb|mysqldump|mysqladmin)\b")
cMysqlPasswordRegex = re.compile(r"(\s-p)([^\s]+)")


def fMaskCommand(pText: str, pMasker) -> str:
  vText = str(pText or "")
  for vRegex, vReplacement in lCommandMasks:
    vText = vRegex.sub(vReplacement, vText)
  if cMysqlRegex.search(vText):
    vText = cMysqlPasswordRegex.sub(r"\1***", vText)
  return pMasker.mMaskText(vText) if pMasker is not None else vText


def fJoinCommand(pArgs: list[str]) -> str:
  # The command line as a person would type it (quoted where needed).
  try:
    return shlex.join([str(vArg) for vArg in pArgs])
  except (TypeError, ValueError):
    return " ".join(str(vArg) for vArg in pArgs)


# Audit

def fDecodeAuditValue(pName: str, pValue: str, pForceHex: bool = False) -> str:
  if pValue.startswith("\"") and pValue.endswith("\"") and len(pValue) >= 2:
    return pValue[1:-1]
  if pValue.startswith("'") and pValue.endswith("'") and len(pValue) >= 2:
    return pValue[1:-1]
  if pValue == "(null)":
    return ""
  if (pForceHex or pName in sEncodedFields) and cHexRegex.match(pValue):
    try:
      return bytes.fromhex(pValue).decode("utf-8", errors="replace")
    except ValueError:
      return pValue
  return pValue


def fAuditPairs(pText: str) -> list[tuple[str, str]]:
  return [(vMatch.group(1), vMatch.group(2)) for vMatch in cPairRegex.finditer(pText)]


def fParseAuditLine(pLine: str, pMasker) -> dict:
  vLine = pLine.rstrip("\r\n")
  vMatch = cAuditLineRegex.match(vLine)
  if not vMatch:
    return {
      "time": "", "correlation": None, "parse_status": "unparsed", "fields": {},
      "raw": pMasker.mMaskText(fTrim(vLine, 65536))
    }
  vType = vMatch.group("type")
  vEpoch = int(vMatch.group("seconds")) + int(vMatch.group("millis")) / 1000.0
  vBody = vMatch.group("body")
  vEnriched = ""
  if "\x1d" in vBody:
    vBody, vEnriched = vBody.split("\x1d", 1)
  dFields = {"type": vType}
  if vMatch.group("node"):
    dFields["node"] = vMatch.group("node")
  dArgs = {}
  lRendered = []
  for vName, vValue in fAuditPairs(vBody):
    if vName == "msg" and vValue.startswith("'"):
      # User space records: the details are inside msg='...'.
      lInner = []
      for vInnerName, vInnerValue in fAuditPairs(vValue[1:-1]):
        vDecoded = fDecodeAuditValue(vInnerName, vInnerValue)
        if vInnerName in ("cmd",):
          vDecoded = fMaskCommand(vDecoded, pMasker)
        dFields[vInnerName] = fTrim(vDecoded, cMaxCommand)
        lInner.append(f"{vInnerName}={fQuoteAudit(dFields[vInnerName]) if vInnerName in sEncodedFields else vInnerValue}")
      lRendered.append("msg='" + " ".join(lInner) + "'")
      continue
    vArg = cArgRegex.match(vName) if vType == "EXECVE" else None
    if vArg:
      vDecoded = fDecodeAuditValue(vName, vValue, True)
      vIndex = int(vArg.group(1))
      if vIndex < cMaxArgs:
        dArgs.setdefault(vIndex, []).append(vDecoded)
      continue
    if vType == "EXECVE" and re.match(r"^a\d+_len$", vName):
      continue
    vDecoded = fDecodeAuditValue(vName, vValue)
    if vName == "proctitle":
      vDecoded = vDecoded.replace("\x00", " ").strip()
    if vName in ("proctitle", "cmd"):
      vDecoded = fMaskCommand(vDecoded, pMasker)
    dFields[vName] = fTrim(vDecoded, cMaxCommand)
    lRendered.append(f"{vName}={fQuoteAudit(dFields[vName]) if vName in sEncodedFields else vValue}")
  if vType == "EXECVE":
    lArgs = [fTrim("".join(dArgs[vIndex]), cMaxArgLength) for vIndex in sorted(dArgs)]
    vCommand = fMaskCommand(fTrim(fJoinCommand(lArgs), cMaxCommand), pMasker)
    dFields["args"] = [fMaskCommand(vArg, pMasker) for vArg in lArgs]
    dFields["command"] = vCommand
    lRendered.append("command=" + fQuoteAudit(vCommand))
  if vEnriched:
    dNames = {}
    for vName, vValue in fAuditPairs(vEnriched):
      dNames[vName.lower()] = fDecodeAuditValue(vName, vValue)
    dFields["names"] = dNames
  vHeader = (f"node={dFields['node']} " if dFields.get("node") else "") + f"type={vType} msg=audit({vMatch.group('seconds')}.{vMatch.group('millis')}:{vMatch.group('serial')}): "
  vRaw = vHeader + " ".join(lRendered)
  if vEnriched:
    vRaw += " " + vEnriched.replace("\x1d", " ")
  vSearch = " ".join(str(dFields.get(vName) or "") for vName in ("type", "command", "proctitle", "cmd", "exe", "comm", "name", "cwd", "acct", "key", "op") if dFields.get(vName))
  return {
    "time": fEpochToStorage(vEpoch),
    "correlation": f"audit:{vMatch.group('seconds')}.{vMatch.group('millis')}:{vMatch.group('serial')}",
    "parse_status": "ok",
    "fields": dFields,
    "raw": pMasker.mMaskText(fTrim(vRaw, 65536)),
    "search": fTrim(vSearch, 4000)
  }


def fQuoteAudit(pValue: str) -> str:
  return "\"" + str(pValue).replace("\"", "'") + "\""


# Hook

dHookEscapes = {"\\\\": "\\", "\\t": "\t", "\\n": "\n", "\\r": "\r"}
cHookEscapeRegex = re.compile(r"\\\\|\\t|\\n|\\r")
lHookColumns = ["version", "kind", "time", "pid", "ppid", "uid", "euid", "line", "tty", "ssh_client", "sudo_user", "parent", "parent_uid", "cwd", "command"]


def fUnescapeHook(pValue: str) -> str:
  return cHookEscapeRegex.sub(lambda vMatch: dHookEscapes[vMatch.group(0)], pValue)


def fParseHookLine(pLine: str, pSource: dict, pMasker) -> dict:
  # The owner of the file is the user: the uid written in the line is only
  # what the shell claims (a user can write anything in their own file).
  vLine = pLine.rstrip("\r\n")
  lParts = vLine.split("\t")
  if len(lParts) != len(lHookColumns) or lParts[0] != "v1":
    return {
      "time": "", "correlation": None, "parse_status": "unparsed", "fields": {"owner_uid": pSource.get("owner_uid")},
      "raw": fMaskCommand(fTrim(vLine, 65536), pMasker)
    }
  dLine = dict(zip(lHookColumns, lParts))
  dFields = {"kind": dLine["kind"], "owner_uid": pSource.get("owner_uid"), "owner": pSource.get("owner", "")}
  for vName in ("pid", "ppid", "uid", "euid", "line", "parent_uid"):
    try:
      dFields[vName] = int(dLine[vName]) if dLine[vName] != "" else None
    except ValueError:
      dFields[vName] = None
  for vName in ("tty", "ssh_client", "sudo_user", "parent", "cwd"):
    dFields[vName] = fTrim(fUnescapeHook(dLine[vName]), 1024)
  dFields["command"] = fMaskCommand(fTrim(fUnescapeHook(dLine["command"]), cMaxCommand), pMasker)
  if dFields["uid"] is not None and pSource.get("owner_uid") is not None and dFields["uid"] != pSource.get("owner_uid"):
    dFields["forged"] = True
  # UTC in the native format (2026-10-29@13-59-59.723).
  vParsed = fParseStorage(dLine["time"])
  vTime = fFormatStorage(vParsed) if vParsed else ""
  lRaw = list(lParts[:-1]) + [dFields["command"].replace("\t", "\\t").replace("\n", "\\n")]
  return {
    "time": vTime,
    "correlation": None,
    "parse_status": "ok" if vTime else "partial",
    "fields": dFields,
    "raw": fTrim("\t".join(lRaw), 65536),
    "search": fTrim(" ".join(vValue for vValue in (dFields["kind"], dFields["owner"], dFields["command"], dFields["cwd"], dFields["parent"]) if vValue), 4000)
  }


# Syslog

cSyslogClassicRegex = re.compile(r"^(?P<time>[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2}) (?P<host>\S+) (?:(?P<facility>[a-z0-9]+\.[a-z]+) )?(?P<program>[^\s\[:]+)(?:\[(?P<pid>\d+)\])?: ?(?P<message>.*)$")
cSyslogIsoRegex = re.compile(r"^(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?) (?P<host>\S+) (?:(?P<facility>[a-z0-9]+\.[a-z]+) )?(?P<program>[^\s\[:]+)(?:\[(?P<pid>\d+)\])?: ?(?P<message>.*)$")
dMonths = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
cSnoopyRegex = re.compile(r"^\[(?P<head>[^\]]*)\]: (?P<command>.*)$")
cSnoopyPairRegex = re.compile(r"(\w+):(.*?)(?= \w+:|$)")
cSudoRegex = re.compile(r"^\s*(?P<user>\S+) : (?P<rest>.*)$")
cPkexecRegex = re.compile(r"^(?P<user>[^:\s]+): (?P<text>.*?)(?: \[USER=(?P<target>[^\]]*)\])?(?: \[TTY=(?P<tty>[^\]]*)\])?(?: \[CWD=(?P<cwd>[^\]]*)\])?(?: \[COMMAND=(?P<command>.*)\])?$")
cSuUtilRegex = re.compile(r"^(?P<failed>FAILED SU )?\(to (?P<target>[^)]+)\) (?P<user>\S+) on (?P<tty>\S+)")
cSuBusyboxRegex = re.compile(r"^(?P<sign>[+-]) (?P<tty>\S+) (?P<user>[^:\s]+):(?P<target>\S+)$")
cDoasRanRegex = re.compile(r"^(?P<user>\S+) ran command (?P<command>.*) as (?P<target>\S+) from (?P<cwd>.*)$")
cDoasFailRegex = re.compile(r"^(?:failed auth for (?P<user1>\S+)|command not permitted for (?P<user2>\S+): (?P<command>.*))$")
cPamRegex = re.compile(r"^pam_unix\((?P<service>[^:)]+):(?P<stage>[^)]+)\): (?P<text>.*)$")
cPamUserRegex = re.compile(r"\b(?:logname|ruser)=(\S*)")
cPamTargetRegex = re.compile(r"\buser=(\S+)")
cPamSessionRegex = re.compile(r"session (?P<what>opened|closed) for user (?P<target>[^\s(]+)(?:\(uid=\d+\))?(?: by (?P<user>[^\s(]*)(?:\(uid=(?P<uid>\d+)\))?)?")
cSshAcceptedRegex = re.compile(r"^Accepted (?P<method>\S+) for (?P<user>\S+) from (?P<ip>\S+) port \d+")
cSshFailedRegex = re.compile(r"^Failed (?P<method>\S+) for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+) port \d+")


def fSyslogTime(pText: str) -> str:
  # ISO 8601 (rsyslog of Debian 12 and newer) or the classic format without
  # year or zone (local time of the server; the year is the current one, or
  # the last one when the date would be in the future).
  try:
    if pText[:4].isdigit():
      vTime = datetime.datetime.fromisoformat(pText.replace("Z", "+00:00"))
      if vTime.tzinfo is None:
        vTime = vTime.astimezone()
      return fFormatStorage(vTime)
    lParts = pText.split()
    vMonth = dMonths.get(lParts[0])
    vDay = int(lParts[1])
    vHour, vMinute, vSecond = (int(vItem) for vItem in lParts[2].split(":"))
    vNow = datetime.datetime.now()
    vTime = datetime.datetime(vNow.year, vMonth, vDay, vHour, vMinute, vSecond)
    if vTime - vNow > datetime.timedelta(days=1):
      vTime = vTime.replace(year=vNow.year - 1)
    return fFormatStorage(datetime.datetime.fromtimestamp(time.mktime(vTime.timetuple()), datetime.UTC))
  except (ValueError, TypeError, IndexError, OverflowError):
    return ""


def fParseSyslogMessage(pProgram: str, pMessage: str, pMasker) -> dict:
  # What the programs that change of user write: kind (exec, sudo, su,
  # pkexec, doas, pam, login, other), user, target, result and command.
  vProgram = pProgram.lower()
  dFields = {"kind": "other"}
  if vProgram == "snoopy":
    vMatch = cSnoopyRegex.match(pMessage)
    if vMatch:
      dHead = {vName: vValue.strip() for vName, vValue in cSnoopyPairRegex.findall(vMatch.group("head"))}
      dFields.update({"kind": "exec", "snoopy": dHead, "command": fMaskCommand(fTrim(vMatch.group("command"), cMaxCommand), pMasker)})
      for vName in ("uid", "euid", "pid", "ppid", "sid"):
        try:
          if dHead.get(vName, "") != "":
            dFields[vName] = int(dHead[vName])
        except ValueError:
          pass
      for vName in ("login", "username", "tty", "cwd", "filename"):
        if dHead.get(vName):
          dFields[vName] = dHead[vName]
    return dFields
  vPam = cPamRegex.match(pMessage)
  if vPam:
    dFields.update({"kind": "pam", "service": vPam.group("service"), "stage": vPam.group("stage")})
    vText = vPam.group("text")
    if "authentication failure" in vText:
      dFields["result"] = "failed"
      vUser = cPamUserRegex.search(vText)
      vTarget = cPamTargetRegex.search(vText)
      dFields["user"] = vUser.group(1) if vUser else ""
      dFields["target"] = vTarget.group(1) if vTarget else ""
    vSession = cPamSessionRegex.search(vText)
    if vSession:
      dFields.update({"session": vSession.group("what"), "target": vSession.group("target"), "user": vSession.group("user") or "", "result": "success"})
    return dFields
  if vProgram in ("sudo", "sudo-rs"):
    vMatch = cSudoRegex.match(pMessage)
    if vMatch:
      lItems = [vItem.strip() for vItem in vMatch.group("rest").split(" ; ")]
      dFields.update({"kind": "sudo", "user": vMatch.group("user"), "result": "success"})
      if lItems and "=" not in lItems[0].split(" ")[0]:
        dFields["result"] = "failed"
        dFields["reason"] = lItems[0]
      for vItem in lItems:
        if "=" in vItem:
          vName, vValue = vItem.split("=", 1)
          vName = vName.strip().lower()
          if vName == "command":
            dFields["command"] = fMaskCommand(fTrim(vValue, cMaxCommand), pMasker)
          elif vName in ("tty", "pwd", "user"):
            dFields[{"pwd": "cwd", "user": "target"}.get(vName, vName)] = vValue
    return dFields
  if vProgram == "su":
    vMatch = cSuUtilRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "su", "user": vMatch.group("user"), "target": vMatch.group("target"), "tty": vMatch.group("tty"), "result": "failed" if vMatch.group("failed") else "success"})
      return dFields
    vMatch = cSuBusyboxRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "su", "user": vMatch.group("user"), "target": vMatch.group("target"), "tty": vMatch.group("tty"), "result": "success" if vMatch.group("sign") == "+" else "failed"})
    return dFields
  if vProgram == "pkexec":
    vMatch = cPkexecRegex.match(pMessage)
    dFields["kind"] = "pkexec"
    dFields["message"] = fMaskCommand(fTrim(pMessage, 2000), pMasker)
    if vMatch:
      vText = vMatch.group("text")
      dFields.update({"user": vMatch.group("user"), "target": vMatch.group("target") or "", "tty": vMatch.group("tty") or "", "cwd": vMatch.group("cwd") or ""})
      dFields["result"] = "success" if vText.startswith("Executing command") else "failed"
      if vMatch.group("command"):
        dFields["command"] = fMaskCommand(fTrim(vMatch.group("command"), cMaxCommand), pMasker)
    return dFields
  if vProgram == "doas":
    vMatch = cDoasRanRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "doas", "user": vMatch.group("user"), "target": vMatch.group("target"), "cwd": vMatch.group("cwd"), "result": "success", "command": fMaskCommand(fTrim(vMatch.group("command"), cMaxCommand), pMasker)})
      return dFields
    vMatch = cDoasFailRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "doas", "user": vMatch.group("user1") or vMatch.group("user2") or "", "result": "failed"})
      if vMatch.group("command"):
        dFields["command"] = fMaskCommand(fTrim(vMatch.group("command"), cMaxCommand), pMasker)
    return dFields
  if vProgram in ("sshd", "sshd-session"):
    vMatch = cSshAcceptedRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "login", "user": vMatch.group("user"), "ip": vMatch.group("ip"), "result": "success", "method": vMatch.group("method")})
      return dFields
    vMatch = cSshFailedRegex.match(pMessage)
    if vMatch:
      dFields.update({"kind": "login", "user": vMatch.group("user"), "ip": vMatch.group("ip"), "result": "failed", "method": vMatch.group("method")})
    return dFields
  return dFields


def fParseSyslogLine(pLine: str, pMasker) -> dict:
  vLine = pLine.rstrip("\r\n")
  vMatch = cSyslogIsoRegex.match(vLine) or cSyslogClassicRegex.match(vLine)
  if not vMatch:
    return {"time": "", "correlation": None, "parse_status": "unparsed", "fields": {}, "raw": fMaskCommand(fTrim(vLine, 65536), pMasker)}
  dFields = fParseSyslogMessage(vMatch.group("program"), vMatch.group("message"), pMasker)
  dFields.update({"program": vMatch.group("program"), "syslog_host": vMatch.group("host")})
  if vMatch.group("pid"):
    dFields.setdefault("pid", int(vMatch.group("pid")))
  vTime = fSyslogTime(vMatch.group("time"))
  return {
    "time": vTime,
    "correlation": None,
    "parse_status": "ok" if vTime else "partial",
    "fields": dFields,
    "raw": fMaskCommand(fTrim(vLine, 65536), pMasker),
    "search": fTrim(" ".join(str(vValue) for vValue in (dFields.get("program"), dFields.get("user"), dFields.get("target"), dFields.get("command")) if vValue), 4000)
  }
