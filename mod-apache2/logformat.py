"""Access log parsers generated from Apache LogFormat strings.

Supports the usual nicknames (combined, vhost_combined, common), the
recommended localsiem_combined and any custom LogFormat read from the Apache
configuration: each directive becomes a capture group of a regular
expression, and the time pieces (%t or several %{format}t) are put back
together and converted to UTC.
"""

import datetime
import re

from backend.core.timeutil import cUtc, fParseApacheAccessTime

dKnownFormats = {
  "localsiem_combined": "%a %l %u [%{%d/%b/%Y:%H:%M:%S}t.%{msec_frac}t %{%z}t] \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\" %v %D %{UNIQUE_ID}e",
  "combined": "%h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"",
  "vhost_combined": "%v:%p %h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"",
  "common": "%h %l %u %t \"%r\" %>s %O",
  "combinedio": "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %I %O"
}
# Apache's defaults when the nickname is not redefined (Debian and Alpine
# define combined with %O; the manual's examples use %b).
lFallbackFormats = ["localsiem_combined", "vhost_combined", "combined", "common"]
dStrftimeRegex = {
  "d": r"\d{2}", "e": r"[ \d]\d", "m": r"\d{2}", "b": r"[A-Za-z]{3}", "h": r"[A-Za-z]{3}", "B": r"[A-Za-z]+",
  "Y": r"\d{4}", "y": r"\d{2}", "H": r"\d{2}", "I": r"\d{2}", "M": r"\d{2}", "S": r"\d{2}", "p": r"[AP]M",
  "z": r"[+-]\d{4}", "Z": r"[A-Za-z]+", "a": r"[A-Za-z]{3}", "A": r"[A-Za-z]+", "j": r"\d{3}",
  "T": r"\d{2}:\d{2}:\d{2}", "D": r"\d{2}/\d{2}/\d{2}", "F": r"\d{4}-\d{2}-\d{2}", "R": r"\d{2}:\d{2}",
  "s": r"\d+", "%": "%"
}
dSpecialTimes = {
  "sec": r"\d+", "msec": r"\d+", "usec": r"\d+", "msec_frac": r"\d{3}", "usec_frac": r"\d{6}"
}
cDirectiveRegex = re.compile(r"%([<>]?)(?:!?\d+(?:,\d+)*)?(?:\{([^}]*)\})?([<>]?)([a-zA-Z%^])(t[io])?")
cQuotedValue = r"(?:[^\"\\]|\\.)*"
cRequestLineRegex = re.compile(r"^(\S+) (\S+)(?: (HTTP/[\d.]+|\S+))?$")


def fStrftimeToRegex(pFormat: str) -> str:
  lParts = []
  vIndex = 0
  while vIndex < len(pFormat):
    vChar = pFormat[vIndex]
    if vChar == "%" and vIndex + 1 < len(pFormat):
      vCode = pFormat[vIndex + 1]
      lParts.append(dStrftimeRegex.get(vCode, r"\S+?") if vCode != "%" else "%")
      vIndex += 2
      continue
    lParts.append(re.escape(vChar))
    vIndex += 1
  return "".join(lParts)


def fUnescape(pValue: str) -> str:
  # Apache escapes " and \ in quoted fields; \xhh stays as written.
  return pValue.replace("\\\"", "\"").replace("\\\\", "\\")


class AccessFormat:

  def __init__(self, pFormat: str, pName: str = ""):
    self.vFormat = pFormat
    self.vName = pName
    self.lGroups = []
    self.vRegex = self.mCompile(pFormat)
    self.vHasVhost = any(dGroup["field"] == "vhost" for dGroup in self.lGroups)
    self.vHasUid = any(dGroup["field"] == "uid" for dGroup in self.lGroups)
    self.vHasMilliseconds = any(dGroup["field"] == "time_part" and dGroup["argument"] in ("msec_frac", "usec_frac", "msec", "usec") for dGroup in self.lGroups)
    self.vHasDuration = any(dGroup["field"] in ("duration_us", "duration_s", "duration_ms") for dGroup in self.lGroups)

  def mCompile(self, pFormat: str):
    lPattern = ["^"]
    vPosition = 0
    for vMatch in cDirectiveRegex.finditer(pFormat):
      vLiteral = pFormat[vPosition:vMatch.start()]
      lPattern.append(re.escape(vLiteral).replace("\\ ", " +") if vLiteral else "")
      vPosition = vMatch.end()
      vArgument = vMatch.group(2) or ""
      vLetter = vMatch.group(4)
      vFinal = vMatch.group(1) == ">" or vMatch.group(3) == ">"
      vQuoted = vMatch.start() > 0 and pFormat[vMatch.start() - 1] == "\"" and pFormat[vMatch.end():vMatch.end() + 1] == "\""
      if vLetter == "%":
        lPattern.append("%")
        continue
      vField, vRegex = self.mDirective(vLetter, vArgument, vQuoted, vFinal)
      vGroup = f"g{len(self.lGroups)}"
      self.lGroups.append({"name": vGroup, "field": vField, "argument": vArgument, "letter": vLetter})
      lPattern.append(f"(?P<{vGroup}>{vRegex})")
    vLiteral = pFormat[vPosition:]
    lPattern.append(re.escape(vLiteral).replace("\\ ", " +") if vLiteral else "")
    lPattern.append(r"\s*$")
    return re.compile("".join(lPattern))

  def mDirective(self, pLetter: str, pArgument: str, pQuoted: bool, pFinal: bool) -> tuple[str, str]:
    vGeneric = cQuotedValue if pQuoted else r"\S*"
    if pLetter == "t":
      if not pArgument:
        return "time_clf", r"\[[^\]]+\]"
      vArgument = pArgument
      for vPrefix in ("begin:", "end:"):
        if vArgument.startswith(vPrefix):
          vArgument = vArgument[len(vPrefix):]
      if vArgument in dSpecialTimes:
        return "time_part", dSpecialTimes[vArgument]
      return "time_part", fStrftimeToRegex(vArgument)
    if pLetter == "a":
      return ("peer_ip" if pArgument == "c" else "client_ip"), r"\S+"
    if pLetter == "h":
      return "remote_host", r"\S+"
    if pLetter == "A":
      return "local_ip", r"\S+"
    if pLetter == "l":
      return "logname", r"\S+"
    if pLetter == "u":
      return "user", vGeneric if pQuoted else r"\S+"
    if pLetter == "r":
      return "request_line", vGeneric
    if pLetter == "s":
      return ("status" if pFinal else "status_original"), r"\d{3}|-"
    if pLetter in ("b", "B"):
      return "bytes_body", r"-|\d+"
    if pLetter == "O":
      return "bytes", r"-|\d+"
    if pLetter == "I":
      return "bytes_in", r"-|\d+"
    if pLetter == "S":
      return "bytes_total", r"-|\d+"
    if pLetter == "D":
      return "duration_us", r"-|\d+"
    if pLetter == "T":
      if pArgument == "ms":
        return "duration_ms", r"-|\d+"
      if pArgument == "us":
        return "duration_us", r"-|\d+"
      return "duration_s", r"-|\d+"
    if pLetter == "v":
      return "vhost", r"\S+"
    if pLetter == "V":
      return "server_name", r"\S+"
    if pLetter == "p":
      return "port", r"-|\d+"
    if pLetter == "P":
      return "pid", r"\S+"
    if pLetter == "m":
      return "method", r"\S+"
    if pLetter == "U":
      return "url_path", vGeneric if pQuoted else r"\S*"
    if pLetter == "q":
      return "query_string", vGeneric if pQuoted else r"\S*"
    if pLetter == "H":
      return "protocol", r"\S*"
    if pLetter == "X":
      return "connection_status", r"[X+-]"
    if pLetter == "k":
      return "keepalive", r"\d+"
    if pLetter == "L":
      return "log_id", r"\S+"
    if pLetter in ("i", "o", "e", "n", "C"):
      vName = pArgument.lower()
      if pLetter == "i" and vName == "referer":
        return "referer", vGeneric
      if pLetter == "i" and vName == "user-agent":
        return "ua", vGeneric
      if pLetter == "i" and vName == "host":
        return "host_header", vGeneric
      if pLetter == "e" and vName == "unique_id":
        return "uid", vGeneric
      return f"{pLetter}:{vName}", vGeneric
    return f"other:{pLetter}", vGeneric

  def mParse(self, pLine: str) -> dict | None:
    vMatch = self.vRegex.match(pLine)
    if vMatch is None:
      return None
    dFields = {}
    lTimeParts = []
    for dGroup in self.lGroups:
      vValue = vMatch.group(dGroup["name"])
      if vValue is None:
        continue
      if dGroup["field"] == "time_part":
        lTimeParts.append((dGroup["argument"], vValue))
        continue
      if dGroup["field"] == "time_clf":
        dFields["time_clf"] = vValue[1:-1]
        continue
      if vValue == "-" and dGroup["field"] not in ("request_line",):
        continue
      dFields.setdefault(dGroup["field"], fUnescape(vValue))
    vTime = None
    if "time_clf" in dFields:
      vTime = fParseApacheAccessTime(dFields.pop("time_clf"))
    elif lTimeParts:
      vTime = fCombineTimeParts(lTimeParts)
    return {"fields": dFields, "time": vTime}


def fCombineTimeParts(pParts: list[tuple]) -> datetime.datetime | None:
  lFormats = []
  lValues = []
  vEpoch = None
  vMicroseconds = None
  for vArgument, vValue in pParts:
    for vPrefix in ("begin:", "end:"):
      if vArgument.startswith(vPrefix):
        vArgument = vArgument[len(vPrefix):]
    if vArgument == "sec":
      vEpoch = int(vValue)
    elif vArgument == "msec":
      vEpoch = int(vValue) / 1000.0
    elif vArgument == "usec":
      vEpoch = int(vValue) / 1000000.0
    elif vArgument == "msec_frac":
      vMicroseconds = int(vValue) * 1000
    elif vArgument == "usec_frac":
      vMicroseconds = int(vValue)
    else:
      lFormats.append(vArgument)
      lValues.append(vValue)
  try:
    if vEpoch is not None and not lFormats:
      return datetime.datetime.fromtimestamp(vEpoch, cUtc)
    if not lFormats:
      return None
    vTime = datetime.datetime.strptime("\x01".join(lValues), "\x01".join(lFormats))
    if vMicroseconds is not None:
      vTime = vTime.replace(microsecond=vMicroseconds)
    if vTime.tzinfo is None:
      # Without %z the time is local to the server.
      return vTime.astimezone(cUtc)
    return vTime.astimezone(cUtc)
  except (ValueError, OverflowError):
    return None


def fSplitRequestLine(pRequestLine: str) -> dict:
  vMatch = cRequestLineRegex.match(pRequestLine or "")
  if vMatch is None:
    return {}
  vUri = vMatch.group(2)
  vPath, vSeparator, vQuery = vUri.partition("?")
  dResult = {"method": vMatch.group(1), "uri": vUri, "path": vPath, "protocol": vMatch.group(3) or ""}
  if vSeparator:
    dResult["query"] = vQuery
  return dResult
