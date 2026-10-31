"""ModSecurity messages, categories and CRS scores.

A message (error.log line, section H "Message:" of the native audit log, or
an item of audit_data.messages in JSON) looks like:

  Warning. detected SQLi using libinjection ... [file "..."] [line "66"]
  [id "942100"] [msg "SQL Injection Attack Detected via libinjection"]
  [data "Matched Data: ..."] [severity "CRITICAL"] [ver "OWASP_CRS/3.3.7"]
  [tag "attack-sqli"] [hostname "..."] [uri "/products.php"] [unique_id "..."]

  Access denied with code 403 (phase 2). Operator GE matched 5 at
  TX:inbound_anomaly_score. [file ...] [id "949110"]
  [msg "Inbound Anomaly Score Exceeded (Total Score: 5)"] ...
"""

import re

cFieldRegex = re.compile(r"\[(\w+) \"((?:[^\"\\]|\\.)*)\"\]")
cDeniedRegex = re.compile(r"Access denied with (?:code (\d+)|connection close|redirection to \S+)(?: using status (\d+))?\s*\(phase (\d)\)", re.IGNORECASE)
cTotalScoreRegex = re.compile(r"Total(?: Inbound)? Score: (\d+)", re.IGNORECASE)
cBlockingScoreRegex = re.compile(r"blocking=(\d+)")
cThresholdRegex = re.compile(r"threshold=(\d+)")
cOutboundScoreRegex = re.compile(r"Outbound Anomaly Score Exceeded.*?(?:Total Score|score): (\d+)", re.IGNORECASE)
dSeverityWeights = {"CRITICAL": 5, "ERROR": 4, "WARNING": 3, "NOTICE": 2, "2": 5, "3": 4, "4": 3, "5": 2}
dTagCategories = {
  "attack-sqli": "sqli", "attack-xss": "xss", "attack-lfi": "lfi", "attack-rfi": "rfi", "attack-rce": "rce",
  "attack-injection-php": "php", "attack-injection-java": "java", "attack-java": "java", "attack-fixation": "fixation",
  "attack-protocol": "protocol", "attack-multipart-header": "multipart", "attack-reputation-scanner": "scanner",
  "attack-reputation-scripting": "scanner", "attack-reputation-crawler": "scanner", "attack-disclosure": "data-leakage",
  "attack-generic": "generic", "attack-injection-generic": "generic", "attack-nodejs": "generic", "attack-ssrf": "generic",
  "attack-deserialization": "generic"
}
# Order of preference when one request matches several families.
lCategoryPriority = [
  "webshell", "data-leakage", "rce", "sqli", "php", "java", "lfi", "rfi", "xss", "fixation", "generic",
  "multipart", "scanner", "protocol", "method", "other"
]
dCategoryLabels = {
  "sqli": "SQL injection", "xss": "cross-site scripting", "lfi": "local file inclusion",
  "rfi": "remote file inclusion", "rce": "remote command execution", "php": "PHP injection",
  "java": "Java attack", "fixation": "session fixation", "generic": "generic attack",
  "protocol": "protocol violation", "multipart": "multipart attack", "scanner": "scanner",
  "method": "method not allowed", "data-leakage": "data leakage", "webshell": "web shell", "other": "rule match"
}
dCategoryRanges = {
  "sqli": "942", "xss": "941", "lfi": "930", "rfi": "931", "rce": "932", "php": "933", "generic": "934",
  "java": "944", "fixation": "943", "protocol": "920-921", "multipart": "922", "scanner": "913",
  "method": "911", "data-leakage": "950-954", "webshell": "955", "other": "other"
}


def fParseMessage(pText: str) -> dict:
  vText = str(pText or "")
  dMessage = {"text": vText, "tags": []}
  for vName, vValue in cFieldRegex.findall(vText):
    vValue = vValue.replace("\\\"", "\"")
    if vName == "tag":
      dMessage["tags"].append(vValue)
    elif vName not in dMessage:
      dMessage[vName] = vValue
  vHead = vText.split(" [", 1)[0]
  vDenied = cDeniedRegex.search(vHead)
  if vDenied:
    dMessage["kind"] = "denied"
    dMessage["code"] = int(vDenied.group(1) or vDenied.group(2) or 0) or None
    dMessage["phase"] = int(vDenied.group(3))
  elif vHead.lstrip().lower().startswith("warning"):
    dMessage["kind"] = "warning"
  elif "access allowed" in vHead.lower():
    dMessage["kind"] = "allowed"
  else:
    dMessage["kind"] = "other"
  dMessage["head"] = vHead.strip()
  return dMessage


def fRuleNumber(pRuleId) -> int | None:
  try:
    return int(str(pRuleId))
  except (TypeError, ValueError):
    return None


def fIsEvaluationRule(pRuleId) -> bool:
  # 949 (inbound blocking), 959 (outbound blocking) and 980 (correlation)
  # give the total score but not the category. 901/905/912/999 are setup.
  vNumber = fRuleNumber(pRuleId)
  if vNumber is None:
    return False
  vFamily = vNumber // 1000
  return vFamily in (949, 959, 980, 901, 905, 999)


def fCategoryFromRange(pRuleId) -> str | None:
  vNumber = fRuleNumber(pRuleId)
  if vNumber is None:
    return None
  vFamily = vNumber // 1000
  if vFamily == 911:
    return "method"
  if vFamily == 913:
    return "scanner"
  if vFamily in (920, 921):
    return "protocol"
  if vFamily == 922:
    return "multipart"
  if vFamily == 930:
    return "lfi"
  if vFamily == 931:
    return "rfi"
  if vFamily == 932:
    return "rce"
  if vFamily == 933:
    return "php"
  if vFamily == 934:
    return "generic"
  if vFamily == 941:
    return "xss"
  if vFamily == 942:
    return "sqli"
  if vFamily == 943:
    return "fixation"
  if vFamily == 944:
    return "java"
  if vFamily == 955:
    return "webshell"
  if 950 <= vFamily <= 954:
    return "data-leakage"
  return None


def fMessageCategory(pMessage: dict) -> str | None:
  if fIsEvaluationRule(pMessage.get("id")):
    return None
  # Outbound families are recognised by their range first: their tags
  # (attack-disclosure, attack-rce...) are shared with inbound families.
  vRange = fCategoryFromRange(pMessage.get("id"))
  if vRange in ("data-leakage", "webshell"):
    return vRange
  for vTag in pMessage.get("tags", []):
    vCategory = dTagCategories.get(vTag.lower())
    if vCategory:
      return vCategory
  return vRange or ("other" if pMessage.get("id") else None)


def fIsOutbound(pMessage: dict) -> bool:
  vNumber = fRuleNumber(pMessage.get("id"))
  return vNumber is not None and 950 <= vNumber // 1000 <= 955


def fSummarize(pMessages: list[dict]) -> dict:
  # Rules, categories, scores and the interception found in the messages.
  dSeen = {}
  for dMessage in pMessages:
    vId = dMessage.get("id") or dMessage.get("head", "")[:40]
    if vId and vId not in dSeen:
      dSeen[vId] = dMessage
  lRules = []
  dCategories = {}
  vScore = None
  vThreshold = None
  vComputed = 0
  vEvaluationMatched = False
  vOutboundMatched = False
  vOutboundEvaluation = False
  dDenied = None
  for dMessage in dSeen.values():
    vId = dMessage.get("id")
    if dMessage.get("kind") == "denied" and dDenied is None:
      dDenied = {"code": dMessage.get("code"), "phase": dMessage.get("phase"), "rule": vId}
    for vRegex in (cTotalScoreRegex, cBlockingScoreRegex):
      vMatch = vRegex.search(dMessage.get("msg", "") + " " + dMessage.get("data", "") + " " + dMessage.get("head", ""))
      if vMatch:
        vScore = max(vScore or 0, int(vMatch.group(1)))
    vMatch = cThresholdRegex.search(dMessage.get("msg", "") + " " + dMessage.get("head", ""))
    if vMatch:
      vThreshold = int(vMatch.group(1))
    if not vId:
      continue
    vNumber = fRuleNumber(vId)
    if vNumber is not None and vNumber // 1000 == 949:
      vEvaluationMatched = True
    if vNumber is not None and vNumber // 1000 == 959:
      vOutboundEvaluation = True
    if fIsEvaluationRule(vId):
      lRules.append({"rule": str(vId), "category": None, "message": dMessage})
      continue
    vCategory = fMessageCategory(dMessage)
    if fIsOutbound(dMessage):
      vOutboundMatched = True
    else:
      vComputed += dSeverityWeights.get(str(dMessage.get("severity", "")).upper(), 0)
    lRules.append({"rule": str(vId), "category": vCategory, "message": dMessage})
    if vCategory:
      dCategories[vCategory] = dCategories.get(vCategory, 0) + dSeverityWeights.get(str(dMessage.get("severity", "")).upper(), 1)
  vPrimary = None
  if dCategories:
    vPrimary = sorted(dCategories, key=lambda vName: (lCategoryPriority.index(vName) if vName in lCategoryPriority else 99, -dCategories[vName]))[0]
  return {
    "rules": lRules,
    "categories": dCategories,
    "primary": vPrimary,
    "score": vScore if vScore is not None else (vComputed or None),
    "score_explicit": vScore is not None,
    "threshold": vThreshold,
    "inbound_evaluation": vEvaluationMatched,
    "outbound_evaluation": vOutboundEvaluation,
    "outbound": vOutboundMatched,
    "denied": dDenied
  }
