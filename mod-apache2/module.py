"""The «apache2» module: access.log, error.log and the ModSecurity audit log.

It lives outside the core (localSIEM-modules/mod-apache2/, installed in
/opt/localsiem/modules/apache2/) and the core loads it from module.json as the
package localsiem_modules.apache2: its own files are imported relatively, the
core through backend.core.

Action taken (what is "already resolved"), from the most reliable source:

  1. audit log: "Action: Intercepted (phase N)" (native) or
     audit_data.action.intercepted/phase (JSON); engine mode from
     Engine-Mode / engine_mode.
  2. error.log: "Access denied with code NNN (phase N)".
  3. access.log only: a 403 without any trace of ModSecurity is not a block
     of ModSecurity; it is marked as doubtful.

  blocked in phases 1-2 (the application never got it)  blocked  stays in localSIEM
  blocked in phases 3-4 (the application already ran)   none     SOC
  match with the engine in DetectionOnly                none     SOC
  match below the anomaly threshold                     none     SOC
  signals of the module rules                           none     SOC

Severity of what goes to the SOC (severity.yaml):

  CRS matches not blocked, response 3xx/4xx/5xx         medium
  CRS matches not blocked, response 2xx                 high
  blocked in phases 3-4                                 high
  signs of success (outbound 950-955 not blocked,
  SQL error right after, POST 2xx to a new .php)        critical
  below the blocking threshold                          low (settings)
"""

import os
import time
from pathlib import Path

import yaml

from backend.core.masking import fTrim
from backend.core.module import LineFramer, Module
from backend.core.query import fQuoteValue
from backend.core.timeutil import fEpochToStorage, fNowStorage, fStorageFromNow, fStorageToEpoch
from .correlate import Correlator
from .discovery import ApacheConfig, fDiscoverSources
from .doctor import fRequirementChecks, fRunDoctor
from .modsec import dCategoryLabels, dCategoryRanges, fSummarize
from .parsers import AccessParser, AuditFramer, fAuditDisplay, fParseAuditRecord, fParseErrorLine, fReadConcurrentEntry

cModulePath = Path(__file__).resolve().parent
dEngineModes = {"enabled": "on", "detection_only": "detection-only", "on": "on", "detectiononly": "detection-only", "off": "off", "disabled": "off"}
lSeverityOrder = ["low", "medium", "high", "critical"]


def fLoadSeverityTable() -> dict:
  dDefaults = {
    "crs_not_blocked_2xx": "high", "crs_not_blocked_other": "medium", "blocked_late": "high",
    "success_indicator": "critical", "below_threshold": "low"
  }
  try:
    with (cModulePath / "severity.yaml").open("r", encoding="utf-8") as vFile:
      dLoaded = yaml.safe_load(vFile) or {}
    dDefaults.update({vKey: str(vValue) for vKey, vValue in dLoaded.items() if str(vValue) in lSeverityOrder})
  except (OSError, yaml.YAMLError):
    pass
  return dDefaults


class ApacheModule(Module):

  vName = "apache2"

  def __init__(self, pSettings: dict, pMasker, pStorage, pManifest: dict | None = None):
    super().__init__(pSettings, pMasker, pStorage, pManifest)
    self.vConfig = None
    self.ldSources = []
    self.ldSkipped = []
    self.dDocumentRoots = {}
    self.dParsers = {}
    self.dSeverity = fLoadSeverityTable()
    self.vLowDisk = False
    self.dRuntime = {"producer": "", "engine_off_seen": False, "engine_modes": {}}
    self.dHealthMemory = {}
    self.vLastHealth = 0.0
    self.vModsecWasLoaded = None
    self.vEngineWas = None

  def mStart(self) -> None:
    # First start: the learning period of apache2.new_php counts from here.
    # The state keys keep the former name of the module (apache).
    if not self.vStorage.mGetState("apache.first_start"):
      self.vStorage.mSetState("apache.first_start", fNowStorage())

  # Discovery

  def mDiscover(self) -> list[dict]:
    dModule = self.mModuleSettings()
    self.vConfig = ApacheConfig(dModule.get("config_file", "")).mParse()
    self.ldSources, self.ldSkipped = fDiscoverSources(self.vConfig, dModule.get("sources", []), bool(dModule.get("manual_only")))
    self.dDocumentRoots = self.vConfig.mDocumentRoots()
    for vKey in dModule.get("document_roots", {}) or {}:
      self.dDocumentRoots[vKey] = dModule["document_roots"][vKey]
    self.dParsers = {}
    return self.ldSources

  def mThreshold(self) -> int:
    vSetting = int(self.mModuleSettings().get("anomaly_threshold") or 0)
    if vSetting > 0:
      return vSetting
    if self.vConfig is not None and self.vConfig.dModsec.get("threshold"):
      return int(self.vConfig.dModsec["threshold"])
    return 5

  def mConfiguredEngine(self, pVhost: str) -> str:
    if self.vConfig is None:
      return ""
    for dVhost in self.vConfig.lVhosts:
      if dVhost.get("rule_engine") and pVhost and (pVhost == dVhost["name"] or pVhost in dVhost["aliases"]):
        return dEngineModes.get(dVhost["rule_engine"].lower(), "")
    return dEngineModes.get((self.vConfig.dModsec.get("rule_engine") or "").lower(), "")

  # Reading

  def mCreateFramer(self, pSource: dict):
    if pSource["kind"] == "audit" and pSource.get("audit_type") != "concurrent":
      return AuditFramer()
    return LineFramer()

  def mAccessParser(self, pSource: dict) -> AccessParser:
    vParser = self.dParsers.get(pSource["key"])
    if vParser is None:
      dFormats = self.vConfig.dLogFormats if self.vConfig is not None else {}
      vParser = AccessParser(self.vMasker, pSource.get("format", ""), pSource.get("vhost", ""), {vName: vValue for vName, vValue in dFormats.items() if vName != "_default"})
      self.dParsers[pSource["key"]] = vParser
    return vParser

  def mParse(self, pSource: dict, pUnit: str, pReceived: str) -> dict:
    vKind = pSource["kind"]
    if vKind == "access":
      dRecord = self.mAccessParser(pSource).mParse(pUnit)
    elif vKind == "error":
      dRecord = fParseErrorLine(pUnit, self.vMasker)
      if not dRecord["fields"].get("vhost") and pSource.get("vhost"):
        dRecord["fields"]["vhost"] = pSource["vhost"]
    else:
      vText = pUnit
      if pSource.get("audit_type") == "concurrent":
        vText = fReadConcurrentEntry(pUnit, pSource.get("storage_dir", "")) or pUnit
      dRecord = fParseAuditRecord(vText, self.vMasker, self.vLowDisk)
      self.mObserveAudit(dRecord)
    dRecord["module"] = "apache2"
    dRecord["source"] = vKind
    dRecord["source_key"] = pSource["key"]
    dRecord["received"] = pReceived
    if not dRecord.get("time"):
      dRecord["time"] = pReceived
    return dRecord

  def mObserveAudit(self, pRecord: dict) -> None:
    dFields = pRecord.get("fields", {})
    if dFields.get("producer"):
      self.dRuntime["producer"] = dFields["producer"]
    vMode = str(dFields.get("engine_mode") or "").lower()
    if vMode:
      self.dRuntime["engine_modes"][vMode] = time.time()
      if vMode in ("disabled", "off"):
        self.dRuntime["engine_off_seen"] = True

  def mCreateCorrelator(self):
    return Correlator(
      self.dSettings.get("correlation_window_seconds", 5),
      self.dSettings.get("weak_correlation_seconds", 2)
    )

  # Events

  def mBuildEvent(self, pTransaction: dict) -> dict:
    lRecords = pTransaction["records"]
    dAccess = next((dRecord for dRecord in lRecords if dRecord["source"] == "access" and dRecord["parse_status"] != "unparsed"), None)
    dAudit = next((dRecord for dRecord in lRecords if dRecord["source"] == "audit" and dRecord["parse_status"] != "unparsed"), None)
    lErrors = [dRecord for dRecord in lRecords if dRecord["source"] == "error" and dRecord["parse_status"] != "unparsed"]
    dA = dAccess["fields"] if dAccess else {}
    dU = dAudit["fields"] if dAudit else {}
    dE = lErrors[0]["fields"] if lErrors else {}
    lSources = []
    for dRecord in lRecords:
      if dRecord["source"] not in lSources:
        lSources.append(dRecord["source"])
    lStatuses = [dRecord["parse_status"] for dRecord in lRecords]
    if all(vStatus == "unparsed" for vStatus in lStatuses):
      vParseStatus = "unparsed"
    elif any(vStatus != "ok" for vStatus in lStatuses):
      vParseStatus = "partial"
    else:
      vParseStatus = "ok"
    vTime = (dAccess or dAudit or {}).get("time") or min(dRecord["time"] for dRecord in lRecords)
    # The formats Apache writes by default have whole seconds: the audit
    # record of the same request has its microseconds.
    if dAccess and dAudit and dAudit.get("time") and str(vTime).endswith(".000") and str(dAudit["time"])[:19] == str(vTime)[:19]:
      vTime = dAudit["time"]
    vReceived = min(dRecord["received"] for dRecord in lRecords)

    def fPick(pName):
      for dFields in (dA, dU, dE):
        if dFields.get(pName) not in (None, ""):
          return dFields[pName]
      for dRecord in lErrors[1:]:
        if dRecord["fields"].get(pName) not in (None, ""):
          return dRecord["fields"][pName]
      return None

    vIp = fPick("client_ip")
    vVhost = (
      dA.get("vhost") or self.mVhostName(dU.get("vhost"), dU.get("server_ip", ""), dU.get("server_port"))
      or self.mVhostName(dE.get("vhost")) or ""
    ).lower() or None
    vUid = pTransaction.get("uid") or next((dRecord.get("correlation") for dRecord in lRecords if dRecord.get("correlation")), None)
    # ModSecurity: the audit record has every message; error.log lines are
    # used when there is no audit record (or to complete it).
    lMessages = list(dU.get("messages") or [])
    for dRecord in lErrors:
      if dRecord["fields"].get("error_type") == "modsecurity" and dRecord["fields"].get("modsecurity"):
        lMessages.append(dRecord["fields"]["modsecurity"])
    dSummary = fSummarize(lMessages)
    vEngine = dEngineModes.get(str(dU.get("engine_mode") or "").lower(), "") or (self.mConfiguredEngine(vVhost or "") if lMessages else "")
    vPhase = None
    vIntercepted = False
    dAction = dU.get("action") if isinstance(dU.get("action"), dict) else None
    if dAction and dAction.get("intercepted"):
      vIntercepted = True
      vPhase = dAction.get("phase")
    elif dSummary["denied"]:
      vIntercepted = True
      vPhase = dSummary["denied"].get("phase")
    try:
      vPhase = int(vPhase) if vPhase is not None else None
    except (TypeError, ValueError):
      vPhase = None
    vAction = "blocked" if vIntercepted and vPhase in (1, 2) else "none"
    vStatus = fPick("status")
    lRuleHits = [{"rule": dRule["rule"], "category": dRule["category"]} for dRule in dSummary["rules"]]
    vThreshold = dSummary["threshold"] or self.mThreshold()
    vScore = dSummary["score"]
    lErrorTypes = sorted({dRecord["fields"].get("error_type", "") for dRecord in lErrors if dRecord["fields"].get("error_type")})
    vDbError = any(dRecord["fields"].get("db_error") for dRecord in lErrors)
    vCrsMatched = any(dRule["category"] for dRule in dSummary["rules"])
    dFields = {
      "weak_correlation": bool(pTransaction.get("weak")),
      "protocol": fPick("protocol"),
      "user": dA.get("user"),
      "port": dA.get("port") or dU.get("server_port"),
      "intercepted": vIntercepted,
      "crs_matched": vCrsMatched,
      "db_error": vDbError,
      "error_types": lErrorTypes,
      "categories": sorted(dSummary["categories"]),
      "anomaly_score": vScore,
      "threshold": vThreshold,
      # 949xxx matches (blocking or, in DetectionOnly, as a warning) when the
      # inbound score reaches the threshold. A score computed from the rule
      # severities is only an estimate and does not decide.
      "above_threshold": bool(dSummary["inbound_evaluation"] or (dSummary["score_explicit"] and vScore is not None and vScore >= vThreshold)),
      "outbound": dSummary["outbound"]
    }
    if vStatus == 403 and not lMessages:
      dFields["doubtful_block"] = True
    if lErrors:
      dFields["error_messages"] = [fTrim(dRecord["fields"].get("message", ""), 500) for dRecord in lErrors[:10] if dRecord["fields"].get("error_type") != "modsecurity"]
    if dU.get("producer"):
      dFields["producer"] = dU["producer"]
    dEvent = {
      "time": vTime,
      "received": vReceived,
      "host": self.dSettings["host"],
      "module": "apache2",
      "sources": lSources,
      "ip": vIp,
      "vhost": vVhost,
      "method": fPick("method"),
      "uri": fPick("uri") or fPick("path"),
      "path": fPick("path"),
      "query": fPick("query"),
      "status": vStatus,
      "bytes": dA.get("bytes"),
      "duration": dA.get("duration_us"),
      "ua": fPick("ua"),
      "referer": fPick("referer"),
      "uid": vUid,
      "rules": [dRule["rule"] for dRule in dSummary["rules"]],
      "category": dSummary["primary"],
      "phase": vPhase,
      "score": vScore,
      "threshold": vThreshold if lMessages else None,
      "engine": vEngine or None,
      "severity": None,
      "action": vAction,
      "parse_status": vParseStatus,
      "correlation": "uid" if vUid and not pTransaction.get("weak") else ("weak" if pTransaction.get("weak") else "none"),
      "fields": {vKey: vValue for vKey, vValue in dFields.items() if vValue not in (None, "", [], False) or vKey in ("intercepted",)},
      "record_ids": [dRecord["id"] for dRecord in lRecords if dRecord.get("id")],
      "rule_hits": lRuleHits,
      "detections": []
    }
    dDetection = self.mAssess(dEvent, dSummary, vIntercepted, vPhase, vDbError, lMessages)
    if dDetection is not None:
      dEvent["detections"].append(dDetection)
      dEvent["severity"] = dDetection["severity"]
    if dEvent["path"] and str(dEvent["path"]).lower().endswith(".php") and isinstance(vStatus, int) and 200 <= vStatus < 300:
      dEvent["fields"]["php_first_seen"] = self.vStorage.mPathFirstSeen(vVhost or "", dEvent["path"], vTime)
    return dEvent

  def mVhostName(self, pHost, pServerIp: str = "", pPort: int | None = None) -> str:
    # The Host header of the audit record or the hostname of a ModSecurity
    # line, turned into the vhost Apache chose (what %v logs); the name as it
    # came when the configuration does not tell.
    if not pHost:
      return ""
    if self.vConfig is not None and self.vConfig.mFound():
      vName = self.vConfig.mVhostName(pHost, pServerIp, pPort)
      if vName:
        return vName
    return pHost

  def mAssess(self, pEvent: dict, pSummary: dict, pIntercepted: bool, pPhase: int | None, pDbError: bool, pMessages: list) -> dict | None:
    if not pSummary["rules"] or pEvent["action"] == "blocked":
      return None
    vCategory = pSummary["primary"] or "other"
    vLabel = dCategoryLabels.get(vCategory, vCategory)
    vRange = dCategoryRanges.get(vCategory, "")
    vStatus = pEvent["status"] if isinstance(pEvent["status"], int) else 0
    vSuccess = (pSummary["outbound"] and not pIntercepted) or pDbError
    vAbove = pEvent["fields"].get("above_threshold", False)
    vEngine = pEvent["engine"] or "unknown"
    if pIntercepted and pPhase in (3, 4):
      vSeverity = self.dSeverity["success_indicator"] if pDbError else self.dSeverity["blocked_late"]
      vSituation = "late_block"
      vRule = f"Apache/ModSecurity: {vLabel} blocked after the application ran (phase {pPhase})"
    elif vSuccess:
      vSeverity = self.dSeverity["success_indicator"]
      vSituation = "success"
      vRule = f"Apache/ModSecurity: {vLabel} not blocked, signs of success (CRS {vRange})"
    elif not vAbove:
      vSeverity = self.dSettings.get("below_threshold_severity") or self.dSeverity["below_threshold"]
      vSituation = "below_threshold"
      vRule = f"Apache/ModSecurity: {vLabel} below the blocking threshold (CRS {vRange})"
    else:
      vSeverity = self.dSeverity["crs_not_blocked_2xx"] if 200 <= vStatus < 300 else self.dSeverity["crs_not_blocked_other"]
      vSituation = "not_blocked"
      vRule = f"Apache/ModSecurity: {vLabel} not blocked (CRS {vRange})"
    if vSeverity not in lSeverityOrder:
      vSeverity = "low"
    vIp = pEvent["ip"] or ""
    vSearch = (f"ip:{fQuoteValue(vIp)} category:{vCategory}" if vIp else f"uid:{fQuoteValue(pEvent['uid'] or '')}")
    lRules = [dRule["rule"] for dRule in pSummary["rules"]]
    vData = next((dRule["message"].get("data") for dRule in pSummary["rules"] if dRule["message"].get("data") and dRule["category"]), "")
    dTexts = {
      "late_block": f"ModSecurity matched {vLabel} rules and blocked the response in phase {pPhase}, after the application had already run the request. Check what the application did with it (data changed, files written, queries run).",
      "success": "ModSecurity matched " + vLabel + " rules, did not block the request, and there are signs that it worked: " + ("an outbound rule matched the response" if pSummary["outbound"] else "") + (" and " if pSummary["outbound"] and pDbError else "") + ("a database error followed the request" if pDbError else "") + ". Treat it as a possible compromise.",
      "below_threshold": f"ModSecurity matched {vLabel} rules but the anomaly score ({pEvent['score'] if pEvent['score'] is not None else '?'}) stayed below the blocking threshold ({pEvent['fields'].get('threshold')}), so the request reached the application (engine: {vEngine}). It is often a false positive of the application itself: check the request and, if it is legitimate, tune the rule.",
      "not_blocked": f"ModSecurity matched {vLabel} rules but did not block the request (engine: {vEngine}) and the application answered {vStatus or '?'}. Check whether the request returned or changed data."
    }
    vDescription = dTexts[vSituation] + f" localSIEM search: {vSearch}"
    dDetails = {
      "vhost": pEvent["vhost"] or "",
      "client_ip": vIp,
      "method": pEvent["method"] or "",
      "uri": fTrim(pEvent["uri"] or "", 1000),
      "status": vStatus or "",
      "user_agent": fTrim(pEvent["ua"] or "", 300),
      "modsecurity": {
        "engine": {"on": "On", "detection-only": "DetectionOnly", "off": "Off"}.get(vEngine, vEngine),
        "action": "intercepted" if pIntercepted else "none",
        "phase": pPhase or "",
        "anomaly_score": pEvent["score"] if pEvent["score"] is not None else "",
        "threshold": pEvent["fields"].get("threshold") or "",
        "rules": lRules[:30],
        "data": fTrim(vData or "", 500)
      }
    }
    return {
      "module": "apache2", "vhost": pEvent["vhost"] or "", "ip": vIp, "category": vCategory, "severity": vSeverity,
      "rule": vRule, "type": "web-attack", "description": vDescription, "search": vSearch, "details": dDetails,
      "time": pEvent["time"], "uid": pEvent["uid"] or ""
    }

  def mDetectionFromSignal(self, pEvent: dict, pSignal: dict) -> dict:
    vIp = pEvent.get("ip") or ""
    dDetails = {
      "vhost": pEvent.get("vhost") or "",
      "client_ip": vIp,
      "method": pEvent.get("method") or "",
      "uri": fTrim(pEvent.get("uri") or "", 1000),
      "status": pEvent.get("status") or "",
      "user_agent": fTrim(pEvent.get("ua") or "", 300),
      "rule": {"id": pSignal["rule_id"], "count": pSignal.get("count", 1)}
    }
    vSearch = pSignal.get("search") or f"ip:{vIp}"
    vDescription = pSignal.get("description") or ""
    if "localSIEM search:" not in vDescription:
      vDescription = (vDescription + " localSIEM search: " + vSearch).strip()
    return {
      "module": "apache2", "vhost": pEvent.get("vhost") or "", "ip": vIp, "category": pSignal["category"],
      "severity": pSignal["severity"], "rule": pSignal["name"], "type": pSignal["type"], "description": vDescription,
      "search": vSearch, "details": dDetails, "time": pEvent.get("time"), "uid": pEvent.get("uid") or ""
    }

  # Rules

  def mRulesPath(self) -> Path:
    return cModulePath / "rules"

  def mRuleFunctions(self) -> dict:
    return {"apache2.new_php": self.mIsNewPhp}

  def mIsNewPhp(self, pEvent: dict, pValue) -> bool:
    # A PHP file never seen before in the history (first seen in the last
    # hour), or created/modified in its DocumentRoot in the last day.
    vPath = pEvent.get("path") or ""
    if not vPath.lower().endswith(".php") or ".." in vPath:
      return False
    vTime = fStorageToEpoch(pEvent.get("time") or fNowStorage())
    vRoot = self.dDocumentRoots.get(pEvent.get("vhost") or "") or self.dDocumentRoots.get("")
    if vRoot:
      vFile = os.path.normpath(os.path.join(vRoot, vPath.lstrip("/")))
      if vFile.startswith(os.path.normpath(vRoot) + os.sep):
        try:
          vStat = os.stat(vFile)
          if vTime - max(vStat.st_mtime, vStat.st_ctime) <= 86400:
            return True
        except OSError:
          pass
    vLearningDays = float(self.mModuleSettings().get("learning_days", 3))
    vFirstStart = self.vStorage.mGetState("apache.first_start")
    if not vFirstStart or vTime - fStorageToEpoch(vFirstStart) < vLearningDays * 86400:
      return False
    vFirstSeen = (pEvent.get("fields") or {}).get("php_first_seen")
    if not vFirstSeen:
      return False
    return vTime - fStorageToEpoch(vFirstSeen) <= 3600

  # Enrichment

  def mEnrich(self, pDetection: dict) -> dict:
    vIp = pDetection.get("ip")
    if not vIp:
      return {}
    dContext = self.vStorage.mGetIpContext(vIp, fStorageFromNow(-3600))
    return {
      "blocked_last_hour": dContext["blocked"],
      "blocked_rules": dContext["blocked_rules"],
      "requests_last_hour": dContext["requests"],
      "ip_first_seen": dContext["first_seen"] if dContext["first_seen"] else ""
    }

  # Doctor and health

  def mDoctor(self) -> list[dict]:
    if self.vConfig is None:
      self.mDiscover()
    return fRunDoctor(self.vConfig, self.ldSources, self.ldSkipped, self.dRuntime)

  def mHealth(self, pNow: float) -> list[dict]:
    from backend.core.health import fHealthDetection
    if pNow - self.vLastHealth < 300:
      return []
    self.vLastHealth = pNow
    # What was already reported survives restarts (an update restarts the
    # collector): the state is kept in the database.
    if not self.dHealthMemory:
      dStored = self.vStorage.mGetState("apache.health", {}) or {}
      # The times of the memory are in the storage format; a state saved by
      # an older version has them in epoch seconds.
      self.dHealthMemory = {vKey: fEpochToStorage(vValue) if isinstance(vValue, (int, float)) else vValue for vKey, vValue in (dStored.get("memory") or {}).items()}
      self.vModsecWasLoaded = dStored.get("modsec_loaded", self.vModsecWasLoaded)
      self.vEngineWas = dStored.get("engine", self.vEngineWas)
    ldDetections = []
    vConfig = ApacheConfig(self.mModuleSettings().get("config_file", "")).mParse()
    if not vConfig.mFound():
      return []
    vLoaded = vConfig.mModsecLoaded()
    vEngine = (vConfig.dModsec.get("rule_engine") or "").lower()
    if self.vModsecWasLoaded and not vLoaded:
      ldDetections.append(fHealthDetection(
        "health-modsecurity", "high", "localSIEM health: ModSecurity is no longer loaded",
        "ModSecurity (mod_security2) was loaded in Apache and is not any more: requests are not inspected. If nobody disabled it on purpose, someone may have turned the protection off.",
        "modsecurity", {"check": "health-modsecurity", "config": vConfig.vConfigFile}
      ))
    if vLoaded and vEngine == "off" and self.vEngineWas not in (None, "off"):
      ldDetections.append(fHealthDetection(
        "health-modsecurity", "high", "localSIEM health: ModSecurity engine turned Off",
        "SecRuleEngine is now Off: ModSecurity no longer evaluates rules. If nobody changed it on purpose, someone may have turned the protection off.",
        "modsecurity", {"check": "health-modsecurity", "config": vConfig.vConfigFile}
      ))
    if self.dRuntime.get("engine_off_seen") and not self.dHealthMemory.get("engine_off_runtime"):
      self.dHealthMemory["engine_off_runtime"] = fEpochToStorage(pNow)
      ldDetections.append(fHealthDetection(
        "health-modsecurity", "high", "localSIEM health: ModSecurity engine turned Off",
        "The ModSecurity audit log reports its engine as disabled.", "modsecurity", {"check": "health-modsecurity"}
      ))
    vChanged = self.vModsecWasLoaded != vLoaded or (vLoaded and self.vEngineWas != vEngine)
    self.vModsecWasLoaded = vLoaded
    self.vEngineWas = vEngine if vLoaded else self.vEngineWas
    if vChanged or ldDetections:
      self.mSaveHealth()
    # Real client IP missing: almost all the traffic from one private IP.
    dHealth = self.dSettings.get("health", {})
    dCounts = self.vStorage.mCountRecentEvents(fStorageFromNow(-3600), "apache2")
    if dCounts["total"] >= int(dHealth.get("single_ip_minimum_requests", 100)) and dCounts["top_ip"]:
      import ipaddress
      try:
        vAddress = ipaddress.ip_address(dCounts["top_ip"])
        vPrivate = vAddress.is_private or vAddress.is_loopback
      except ValueError:
        vPrivate = False
      vShare = dCounts["top_count"] * 100.0 / dCounts["total"]
      if vPrivate and vShare >= float(dHealth.get("single_ip_percent", 90)):
        vLast = fStorageToEpoch(self.dHealthMemory.get("single_ip") or "")
        if pNow - vLast > 86400:
          self.dHealthMemory["single_ip"] = fEpochToStorage(pNow)
          self.mSaveHealth()
          ldDetections.append(fHealthDetection(
            "health-real-ip", "medium", "localSIEM health: real client IP missing (mod_remoteip)",
            f"{vShare:.0f} % of the last {dCounts['total']} requests come from {dCounts['top_ip']}, a private or local address: the web is probably behind a proxy and Apache logs the proxy's IP. Configure mod_remoteip so the rules by IP work.",
            "remoteip", {"check": "health-real-ip", "ip": dCounts["top_ip"], "share_percent": round(vShare, 1), "requests": dCounts["total"]}
          ))
    return ldDetections

  def mSaveHealth(self) -> None:
    self.vStorage.mSetState("apache.health", {"memory": self.dHealthMemory, "modsec_loaded": self.vModsecWasLoaded, "engine": self.vEngineWas})

  def mSetLowDisk(self, pLowDisk: bool) -> None:
    self.vLowDisk = pLowDisk

  def mSkipped(self) -> list[dict]:
    return self.ldSkipped

  # Web and manage.py

  def mDisplayRecord(self, pRecord: dict) -> dict:
    # Headers and body of the request card are read from the stored (masked)
    # audit record.
    if pRecord.get("source") != "audit":
      return {}
    return fAuditDisplay(pRecord.get("raw", ""))

  def mSetupSnippet(self) -> str:
    from .setup import fBuildSnippet
    return fBuildSnippet(self.mModuleSettings().get("config_file", ""))

  def mApplySetup(self) -> None:
    from .setup import fConfigureApache
    fConfigureApache(self.mModuleSettings().get("config_file", ""))

  def mRequirements(self) -> list[dict]:
    # Apache and ModSecurity 2, read again on every call (no storage: the web
    # and manage.py call it too). localSIEM 2.2.0 or newer installs the module
    # turned off while one of them is missing, and does not let it be turned
    # on until both are found.
    return fRequirementChecks(ApacheConfig(self.mModuleSettings().get("config_file", "")).mParse())
