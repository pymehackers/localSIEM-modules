"""Discovery of the Apache sources from its configuration.

The configuration files are read directly (Include, IncludeOptional, Define,
${VARS} from Debian's envvars, <VirtualHost> and <IfModule> against the
loaded modules), so it works as the localsiem user, without apache2ctl and
without touching anything. It finds:

  - CustomLog, GlobalLog and TransferLog with their LogFormat, and the vhost
    each access log belongs to (from %v in the format, or from the file
    when only one vhost writes to it).
  - <VirtualHost> addresses, ServerName and ServerAlias: the vhost of a
    request is found from its Host header and local port the way Apache
    chooses it (mVhostName), for the formats without %v.
  - ErrorLog of the server and of each vhost.
  - SecRuleEngine, SecAuditEngine, SecAuditLog, SecAuditLogType,
    SecAuditLogFormat, SecAuditLogParts, SecAuditLogStorageDir and the CRS
    files (and its anomaly threshold in crs-setup.conf).
  - DocumentRoot of each vhost (for the web shell rule).
  - Loaded modules (security2, unique_id, remoteip...).

Piped logs ("|/usr/bin/rotatelogs ...") and syslog cannot be read: the
doctor reports them.
"""

import fnmatch
import glob
import os
import re
import shlex
import subprocess
from pathlib import Path

lConfigCandidates = [
  ("debian", "/etc/apache2/apache2.conf", "/etc/apache2"),
  ("alpine", "/etc/apache2/httpd.conf", "/var/www"),
  ("redhat", "/etc/httpd/conf/httpd.conf", "/etc/httpd")
]
sStaticModules = {"core", "so", "http", "http_core", "log_config", "logio", "version", "unixd", "watchdog", "mpm_common"}
cVariableRegex = re.compile(r"\$\{([A-Za-z0-9_]+)\}")
cThresholdRegex = re.compile(r"tx\.inbound_anomaly_score_threshold\s*=\s*(\d+)")
cParanoiaRegex = re.compile(r"tx\.(?:blocking_)?paranoia_level\s*=\s*(\d+)")


def fModuleNames(pName: str) -> set[str]:
  # security2_module, mod_security2.c and mod_security2.so name the same module.
  vName = pName.strip().strip("\"")
  sNames = {vName}
  vBase = os.path.basename(vName)
  for vSuffix in ("_module", ".c", ".so"):
    if vBase.endswith(vSuffix):
      vBase = vBase[:-len(vSuffix)]
  if vBase.startswith("mod_"):
    vBase = vBase[4:]
  sNames.add(vBase)
  return sNames


def fReadEnvvars(pPath: str) -> dict:
  # Debian: export APACHE_LOG_DIR=/var/log/apache2$SUFFIX
  dVariables = {}
  try:
    for vLine in Path(pPath).read_text(encoding="utf-8", errors="replace").splitlines():
      vMatch = re.match(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$", vLine)
      if not vMatch:
        continue
      vValue = vMatch.group(2).strip().strip("\"'")
      vValue = vValue.replace("$SUFFIX", "").replace("${SUFFIX}", "")
      if "$" in vValue or "`" in vValue:
        continue
      dVariables[vMatch.group(1)] = vValue
  except OSError:
    pass
  return dVariables


def fSplitArguments(pText: str) -> list[str]:
  try:
    return shlex.split(pText, posix=True)
  except ValueError:
    return pText.split()


def fSplitAddress(pAddress: str) -> tuple[str, str]:
  # Address of a <VirtualHost>: "*:80", "127.0.0.1:8080", "[::1]:443",
  # "_default_" or "*" -> (ip, port); port "" is any port.
  vAddress = pAddress.strip().lower()
  if vAddress.startswith("["):
    vIp, _, vRest = vAddress[1:].partition("]")
    return vIp, vRest.lstrip(":")
  if vAddress.count(":") == 1:
    vIp, _, vPort = vAddress.partition(":")
    return vIp, vPort
  return vAddress, ""


def fHostName(pHost: str) -> str:
  # Host header or hostname without its port.
  vHost = str(pHost or "").strip().lower()
  if vHost.startswith("["):
    return vHost[1:vHost.find("]")] if "]" in vHost else vHost
  if vHost.count(":") == 1:
    vHost = vHost.split(":")[0]
  return vHost.rstrip(".")


class ApacheConfig:

  def __init__(self, pConfigFile: str = ""):
    self.vFlavor = ""
    self.vConfigFile = ""
    self.vServerRoot = ""
    self.dVariables = {}
    self.dModules = {}
    self.sLoaded = set()
    self.dLogFormats = {}
    self.lAccessLogs = []
    self.lErrorLogs = []
    self.lVhosts = []
    self.dMain = {"server_name": "", "document_root": "", "error_log": ""}
    self.dModsec = {
      "rule_engine": "", "audit_engine": "", "audit_log": "", "audit_log2": "", "audit_type": "",
      "audit_format": "", "audit_parts": "", "storage_dir": "", "relevant_status": "", "crs_files": [],
      "crs_setup": "", "threshold": None, "paranoia": None, "sanitise": False, "vhost_engines": {}
    }
    self.vRemoteIp = False
    self.vErrorLogFormat = ""
    self.lFiles = []
    self.lProblems = []
    self.mLocate(pConfigFile)

  def mLocate(self, pConfigFile: str) -> None:
    if pConfigFile and Path(pConfigFile).is_file():
      self.vConfigFile = pConfigFile
      self.vServerRoot = str(Path(pConfigFile).parent)
      self.vFlavor = "custom"
      return
    for vFlavor, vFile, vRoot in lConfigCandidates:
      if Path(vFile).is_file():
        self.vFlavor = vFlavor
        self.vConfigFile = vFile
        self.vServerRoot = vRoot
        if vFlavor == "debian":
          self.dVariables.update(fReadEnvvars("/etc/apache2/envvars"))
          self.dVariables.setdefault("APACHE_LOG_DIR", "/var/log/apache2")
        return

  def mFound(self) -> bool:
    return bool(self.vConfigFile)

  def mExpand(self, pValue: str) -> str:
    return cVariableRegex.sub(lambda pMatch: self.dVariables.get(pMatch.group(1), pMatch.group(0)), pValue)

  def mResolve(self, pPath: str) -> str:
    vPath = self.mExpand(pPath.strip().strip("\""))
    if not vPath or vPath.startswith("|") or vPath.startswith("syslog"):
      return vPath
    if not os.path.isabs(vPath):
      vPath = os.path.join(self.vServerRoot, vPath)
    return os.path.normpath(vPath)

  def mParse(self) -> "ApacheConfig":
    if not self.vConfigFile:
      return self
    self.mParseFile(self.vConfigFile, 0, None, [True])
    if self.dModsec["crs_setup"]:
      self.mReadCrsSetup(self.dModsec["crs_setup"])
    return self

  def mIsLoaded(self, pName: str) -> bool:
    return bool(fModuleNames(pName) & (self.sLoaded | sStaticModules))

  def mParseFile(self, pPath: str, pDepth: int, pVhost: dict | None, pActive: list) -> None:
    if pDepth > 20 or pPath in self.lFiles:
      return
    try:
      vText = Path(pPath).read_text(encoding="utf-8", errors="replace")
    except OSError as vError:
      self.lProblems.append(f"{pPath}: {vError.strerror}")
      return
    self.lFiles.append(pPath)
    lLines = []
    vPending = ""
    for vLine in vText.splitlines():
      if vLine.rstrip().endswith("\\"):
        vPending += vLine.rstrip()[:-1] + " "
        continue
      lLines.append(vPending + vLine)
      vPending = ""
    if vPending:
      lLines.append(vPending)
    lStack = []
    vVhost = pVhost
    for vNumber, vRaw in enumerate(lLines, 1):
      vLine = vRaw.strip()
      if not vLine or vLine.startswith("#"):
        continue
      if vLine.startswith("</"):
        vName = vLine[2:].rstrip(">").strip().lower()
        if lStack:
          vKind, vPreviousVhost, vPreviousActive = lStack.pop()
          if vKind == "virtualhost":
            vVhost = vPreviousVhost
          pActive[0] = vPreviousActive
        continue
      if vLine.startswith("<"):
        vInner = vLine[1:].rstrip(">").strip()
        vName, _, vArguments = vInner.partition(" ")
        vName = vName.lower()
        lStack.append((vName, vVhost, pActive[0]))
        if vName == "virtualhost" and pActive[0]:
          vVhost = {
            "name": "", "aliases": [], "addresses": vArguments.split(), "document_root": "", "file": pPath,
            "line": vNumber, "access_logs": [], "error_log": "", "rule_engine": ""
          }
          self.lVhosts.append(vVhost)
        elif vName == "ifmodule":
          vModule = vArguments.strip().strip("\"")
          vNegated = vModule.startswith("!")
          vLoaded = self.mIsLoaded(vModule.lstrip("!"))
          pActive[0] = pActive[0] and (vLoaded != vNegated)
        continue
      if not pActive[0]:
        continue
      vDirective, _, vRest = vLine.partition(" ")
      vDirective = vDirective.lower()
      lArguments = fSplitArguments(self.mExpand(vRest.strip()))
      self.mDirective(vDirective, lArguments, vRest.strip(), pPath, vNumber, pDepth, vVhost, pActive)

  def mDirective(self, pDirective: str, pArguments: list[str], pRaw: str, pPath: str, pLine: int, pDepth: int, pVhost: dict | None, pActive: list) -> None:
    if pDirective == "serverroot" and pArguments:
      self.vServerRoot = pArguments[0]
    elif pDirective == "define" and pArguments:
      self.dVariables[pArguments[0]] = pArguments[1] if len(pArguments) > 1 else ""
    elif pDirective in ("include", "includeoptional") and pArguments:
      vPattern = self.mResolve(pArguments[0])
      lMatches = sorted(glob.glob(vPattern)) if any(vChar in vPattern for vChar in "*?[") else [vPattern]
      for vMatch in lMatches:
        if os.path.isdir(vMatch):
          for vFile in sorted(glob.glob(os.path.join(vMatch, "*"))):
            if os.path.isfile(vFile):
              self.mInclude(vFile, pDepth, pVhost, pActive)
        elif os.path.isfile(vMatch):
          self.mInclude(vMatch, pDepth, pVhost, pActive)
        elif pDirective == "include" and not any(vChar in vPattern for vChar in "*?["):
          self.lProblems.append(f"{pPath}:{pLine}: Include {vMatch} not found")
    elif pDirective == "loadmodule" and len(pArguments) >= 2:
      self.dModules[pArguments[0]] = pArguments[1]
      self.sLoaded |= fModuleNames(pArguments[0]) | fModuleNames(pArguments[1])
    elif pDirective == "logformat" and pArguments:
      vNickname = pArguments[1] if len(pArguments) > 1 else ""
      self.dLogFormats[vNickname or "_default"] = pArguments[0]
    elif pDirective in ("customlog", "globallog", "transferlog") and pArguments:
      vFormat = pArguments[1] if len(pArguments) > 1 and not pArguments[1].startswith("env=") and not pArguments[1].startswith("expr=") else ""
      if pDirective == "transferlog":
        vFormat = self.dLogFormats.get("_default", "common")
      dLog = {
        "path": self.mResolve(pArguments[0]), "format": vFormat, "directive": pDirective,
        "vhost": pVhost["name"] if pVhost else "", "conditional": any(vItem.startswith(("env=", "expr=")) for vItem in pArguments[1:]),
        "file": pPath, "line": pLine, "vhost_ref": pVhost
      }
      self.lAccessLogs.append(dLog)
      if pVhost is not None:
        pVhost["access_logs"].append(dLog)
    elif pDirective == "errorlog" and pArguments:
      vPath = self.mResolve(pArguments[0])
      if pVhost is not None:
        pVhost["error_log"] = vPath
      else:
        self.dMain["error_log"] = vPath
      self.lErrorLogs.append({"path": vPath, "vhost": pVhost["name"] if pVhost else "", "file": pPath, "line": pLine})
    elif pDirective == "errorlogformat" and pArguments:
      self.vErrorLogFormat = pArguments[-1]
    elif pDirective == "servername" and pArguments:
      vName = pArguments[0].split("://")[-1].split(":")[0].lower()
      if pVhost is not None:
        pVhost["name"] = vName
        for dLog in pVhost["access_logs"]:
          dLog["vhost"] = vName
      else:
        self.dMain["server_name"] = vName
    elif pDirective == "serveralias" and pVhost is not None:
      pVhost["aliases"].extend(vItem.lower() for vItem in pArguments)
    elif pDirective == "documentroot" and pArguments:
      if pVhost is not None:
        pVhost["document_root"] = self.mResolve(pArguments[0])
      else:
        self.dMain["document_root"] = self.mResolve(pArguments[0])
    elif pDirective == "remoteipheader":
      self.vRemoteIp = True
    elif pDirective == "secruleengine" and pArguments:
      if pVhost is not None:
        pVhost["rule_engine"] = pArguments[0]
      else:
        self.dModsec["rule_engine"] = pArguments[0]
    elif pDirective == "secauditengine" and pArguments:
      self.dModsec["audit_engine"] = pArguments[0]
    elif pDirective == "secauditlog" and pArguments:
      self.dModsec["audit_log"] = self.mResolve(pArguments[0])
    elif pDirective == "secauditlog2" and pArguments:
      self.dModsec["audit_log2"] = self.mResolve(pArguments[0])
    elif pDirective == "secauditlogtype" and pArguments:
      self.dModsec["audit_type"] = pArguments[0]
    elif pDirective == "secauditlogformat" and pArguments:
      self.dModsec["audit_format"] = pArguments[0]
    elif pDirective == "secauditlogparts" and pArguments:
      self.dModsec["audit_parts"] = pArguments[0]
    elif pDirective == "secauditlogstoragedir" and pArguments:
      self.dModsec["storage_dir"] = self.mResolve(pArguments[0])
    elif pDirective == "secauditlogrelevantstatus" and pArguments:
      self.dModsec["relevant_status"] = pArguments[0]
    elif pDirective.startswith("sec") and "sanitise" in pRaw.lower():
      self.dModsec["sanitise"] = True

  def mInclude(self, pFile: str, pDepth: int, pVhost: dict | None, pActive: list) -> None:
    vLower = pFile.lower()
    if any(vWord in vLower for vWord in ("crs", "coreruleset", "owasp")):
      self.dModsec["crs_files"].append(pFile)
      if os.path.basename(vLower).startswith("crs-setup"):
        self.dModsec["crs_setup"] = pFile
    vSaved = pActive[0]
    self.mParseFile(pFile, pDepth + 1, pVhost, pActive)
    pActive[0] = vSaved
    # The CRS load file may include crs-setup.conf from another folder.
    if not self.dModsec["crs_setup"]:
      for vFile in self.lFiles:
        if os.path.basename(vFile).lower().startswith("crs-setup"):
          self.dModsec["crs_setup"] = vFile

  def mReadCrsSetup(self, pPath: str) -> None:
    try:
      for vLine in Path(pPath).read_text(encoding="utf-8", errors="replace").splitlines():
        vStripped = vLine.strip()
        if vStripped.startswith("#"):
          continue
        vMatch = cThresholdRegex.search(vStripped)
        if vMatch:
          self.dModsec["threshold"] = int(vMatch.group(1))
        vMatch = cParanoiaRegex.search(vStripped)
        if vMatch:
          self.dModsec["paranoia"] = int(vMatch.group(1))
    except OSError:
      pass

  def mModsecLoaded(self) -> bool:
    return self.mIsLoaded("security2_module")

  def mModsecV3Loaded(self) -> bool:
    return self.mIsLoaded("security3_module")

  def mAccessFormat(self, pLog: dict) -> str:
    vFormat = pLog.get("format") or ""
    if vFormat in self.dLogFormats:
      return self.dLogFormats[vFormat]
    if "%" in vFormat:
      return vFormat
    from .logformat import dKnownFormats
    return dKnownFormats.get(vFormat, vFormat or dKnownFormats["common"])

  def mVhostName(self, pHost: str, pServerIp: str = "", pPort: int | None = None) -> str:
    # The vhost Apache chose for a request, as %v logs it: among the
    # <VirtualHost> blocks of the local address and port (an exact IP before
    # *), the one whose ServerName or ServerAlias is the Host header, else the
    # first one (the default of that address). Without the port only the
    # names are compared. "" when it cannot be told.
    vHost = fHostName(pHost)
    lCandidates = self.lVhosts
    if pPort is not None:
      lExact = []
      lWildcard = []
      for dVhost in self.lVhosts:
        for vAddress in dVhost["addresses"]:
          vIp, vPort = fSplitAddress(vAddress)
          if vPort not in ("", "*") and vPort != str(pPort):
            continue
          if vIp in ("*", "_default_"):
            lWildcard.append(dVhost)
            break
          if pServerIp and vIp == str(pServerIp).lower():
            lExact.append(dVhost)
            break
      lCandidates = lExact or lWildcard
      if not lCandidates:
        # No <VirtualHost> on that address: the main server answered.
        return self.dMain["server_name"]
    for dVhost in lCandidates:
      if vHost and (vHost == dVhost["name"] or any(fnmatch.fnmatchcase(vHost, vAlias) for vAlias in dVhost["aliases"])):
        return dVhost["name"] or self.dMain["server_name"]
    if pPort is not None:
      return lCandidates[0]["name"] or self.dMain["server_name"]
    return ""

  def mDocumentRoots(self) -> dict:
    dRoots = {}
    if self.dMain["document_root"]:
      dRoots[""] = self.dMain["document_root"]
    for dVhost in self.lVhosts:
      if dVhost["document_root"]:
        for vName in [dVhost["name"]] + dVhost["aliases"]:
          if vName:
            dRoots.setdefault(vName, dVhost["document_root"])
    return dRoots


def fSourceKey(pKind: str, pPath: str) -> str:
  # Still "apache" (the name before apache2): the saved positions use it.
  return f"apache:{pKind}:{pPath}"


def fDiscoverSources(pConfig: ApacheConfig, pManual: list[dict], pManualOnly: bool) -> tuple[list[dict], list[dict]]:
  # Returns (sources to read, skipped entries with the reason).
  ldSources = []
  ldSkipped = []
  sPaths = set()

  def fAdd(pSource: dict) -> None:
    vReal = os.path.realpath(pSource["path"]) if pSource["path"] and not pSource["path"].startswith("|") else pSource["path"]
    if vReal in sPaths:
      return
    sPaths.add(vReal)
    pSource["path"] = vReal
    pSource["key"] = fSourceKey(pSource["kind"], vReal)
    pSource["module"] = "apache2"
    ldSources.append(pSource)

  for dManual in pManual or []:
    if dManual.get("path") and dManual.get("kind") in ("access", "error", "audit"):
      fAdd({
        "path": dManual["path"], "kind": dManual["kind"], "format": dManual.get("format", ""), "vhost": dManual.get("vhost", ""),
        "audit_type": dManual.get("audit_type", "serial"), "storage_dir": dManual.get("storage_dir", ""), "manual": True
      })
  if pManualOnly or not pConfig.mFound():
    return ldSources, ldSkipped
  # A GlobalLog whose format has %v covers every vhost: the other access
  # logs would only repeat its lines.
  dGlobal = None
  for dLog in pConfig.lAccessLogs:
    vFormat = pConfig.mAccessFormat(dLog)
    if dLog["directive"] == "globallog" and "%v" in vFormat and not dLog["conditional"]:
      dGlobal = dLog
  # Names of the vhosts writing to each file (the :80 and :443 vhosts of a
  # site usually share one). A log of the main server is also written by
  # every vhost without an access log of its own (Alpine's access.log, for
  # example), and a GlobalLog by all of them.
  dNames = {}
  lInheriting = [dVhost for dVhost in pConfig.lVhosts if not dVhost["access_logs"]]
  for dLog in pConfig.lAccessLogs:
    sNames = dNames.setdefault(dLog["path"], set())
    sNames.add(dLog.get("vhost") or pConfig.dMain["server_name"])
    if dLog.get("vhost_ref") is None:
      for dVhost in (pConfig.lVhosts if dLog["directive"] == "globallog" else lInheriting):
        sNames.add(dVhost["name"] or pConfig.dMain["server_name"])
  # Files written by at least one CustomLog whose format has data.
  sWithData = {dLog["path"] for dLog in pConfig.lAccessLogs if "%" in pConfig.mAccessFormat(dLog)}
  for dLog in pConfig.lAccessLogs:
    vFormat = pConfig.mAccessFormat(dLog)
    if dLog["path"].startswith("|") or dLog["path"].startswith("syslog"):
      ldSkipped.append({"path": dLog["path"], "kind": "access", "reason": "piped_log"})
      continue
    if dGlobal is not None and dLog is not dGlobal:
      ldSkipped.append({"path": dLog["path"], "kind": "access", "reason": "covered_by_global_log"})
      continue
    if "%" not in vFormat:
      # A format without any directive: Apache writes a nickname that no
      # LogFormat defines as it is, so every line is that same text, without
      # the client IP, the time or the request. Nothing to read in it; the
      # requests of its vhost are still seen in the error log and in the
      # ModSecurity audit log. The format of the logs is never changed.
      if dLog["path"] not in sWithData and not any(dSkipped["path"] == dLog["path"] and dSkipped["reason"] == "format_without_data" for dSkipped in ldSkipped):
        ldSkipped.append({
          "path": dLog["path"], "kind": "access", "reason": "format_without_data", "format": dLog["format"],
          "defined": dLog["format"] in pConfig.dLogFormats, "vhost": dLog.get("vhost", ""), "file": dLog["file"], "line": dLog["line"]
        })
      continue
    vVhost = ""
    if "%v" not in vFormat and "%V" not in vFormat and len(dNames.get(dLog["path"], set())) == 1:
      vVhost = next(iter(dNames[dLog["path"]])) or ""
    fAdd({"path": dLog["path"], "kind": "access", "format": vFormat, "vhost": vVhost})
  for dLog in pConfig.lErrorLogs:
    if dLog["path"].startswith("|") or dLog["path"].startswith("syslog"):
      ldSkipped.append({"path": dLog["path"], "kind": "error", "reason": "piped_log"})
      continue
    fAdd({"path": dLog["path"], "kind": "error", "format": "", "vhost": dLog.get("vhost", "")})
  dModsec = pConfig.dModsec
  if pConfig.mModsecLoaded() and dModsec["audit_log"]:
    if dModsec["audit_log"].startswith("|"):
      ldSkipped.append({"path": dModsec["audit_log"], "kind": "audit", "reason": "piped_log"})
    else:
      vType = "concurrent" if dModsec["audit_type"].lower() == "concurrent" else "serial"
      fAdd({"path": dModsec["audit_log"], "kind": "audit", "format": dModsec["audit_format"] or "Native", "vhost": "", "audit_type": vType, "storage_dir": dModsec["storage_dir"]})
  return ldSources, ldSkipped


def fRunApacheCommand(pArguments: list[str]) -> tuple[int, str]:
  # apache2ctl -S / -M, when allowed (manage.py apply-setup runs as root).
  for vCommand in ("apache2ctl", "apachectl", "httpd", "apache2"):
    for vDirectory in ("/usr/sbin", "/usr/bin", "/sbin"):
      vPath = os.path.join(vDirectory, vCommand)
      if os.path.isfile(vPath) and os.access(vPath, os.X_OK):
        try:
          vResult = subprocess.run([vPath] + pArguments, capture_output=True, text=True, timeout=20)
          return vResult.returncode, (vResult.stdout + vResult.stderr)
        except (OSError, subprocess.SubprocessError) as vError:
          return 1, str(vError)
  return 127, "apache2ctl/httpd not found"
