"""Doctor of the Apache module: requirement checks.

By default nothing in Apache is changed: each missing requirement comes with
the exact snippet to add. Applied as root, --configure-apache writes one
file of its own (fBuildLocalsiemConf), enables the modules, runs configtest,
undoes everything if it fails and reloads (never restarts) if it works.

Each check: {"id", "status": ok|warning|error|info, "title", "detail",
"fix" (snippet or command, optional)}.
"""

import os

from .discovery import ApacheConfig

cLocalsiemFormat = "%a %l %u [%{%d/%b/%Y:%H:%M:%S}t.%{msec_frac}t %{%z}t] \\\"%r\\\" %>s %O \\\"%{Referer}i\\\" \\\"%{User-Agent}i\\\" %v %D %{UNIQUE_ID}e"
lSanitiseArguments = ["password", "pass", "pwd", "passwd", "token", "secret", "api_key", "apikey", "auth", "session"]
lSanitiseHeaders = ["Authorization", "Cookie", "Proxy-Authorization", "X-Api-Key"]


def fLogDirectory(pFlavor: str) -> str:
  return "${APACHE_LOG_DIR}" if pFlavor == "debian" else "/var/log/apache2"


def fModulePath(pFlavor: str) -> str:
  return "modules" if pFlavor == "alpine" else "/usr/lib/apache2/modules"


def fSanitiseAction(pSanitise: list[str] | None = None) -> str:
  lArguments = pSanitise or lSanitiseArguments
  vSanitise = ",".join(
    [f"sanitiseArg:{vName}" for vName in lArguments]
    + [f"sanitiseRequestHeader:{vName}" for vName in lSanitiseHeaders]
    + ["sanitiseResponseHeader:Set-Cookie"]
  )
  return f"SecAction \"id:77001,phase:5,nolog,pass,{vSanitise}\""


def fBuildLocalsiemConf(pFlavor: str, pJson: bool = True, pSanitise: list[str] | None = None) -> str:
  vLogDirectory = fLogDirectory(pFlavor)
  lLines = [
    "# localSIEM: requirements of the Apache module.",
    "# Written by localSIEM (--configure-apache). Remove this file to undo it.",
    ""
  ]
  if pFlavor == "alpine":
    # Alpine loads neither of them by default; %O of the format needs mod_logio.
    lLines += [
      "<IfModule !unique_id_module>",
      f"  LoadModule unique_id_module {fModulePath(pFlavor)}/mod_unique_id.so",
      "</IfModule>",
      "<IfModule !logio_module>",
      f"  LoadModule logio_module {fModulePath(pFlavor)}/mod_logio.so",
      "</IfModule>",
      ""
    ]
  lLines += [
    "# Access log with milliseconds, vhost, duration and UNIQUE_ID, for every vhost.",
    f"LogFormat \"{cLocalsiemFormat}\" localsiem_combined",
    f"GlobalLog {vLogDirectory}/localsiem_access.log localsiem_combined",
    "",
    "<IfModule security2_module>",
    "  # Serial audit log of the transactions with rule matches, without the",
    "  # response body (part E).",
    "  SecAuditEngine RelevantOnly",
    "  SecAuditLogRelevantStatus \"^(?:5|4(?!04))\"",
    "  SecAuditLogType Serial",
  ]
  if pJson:
    lLines.append("  SecAuditLogFormat JSON")
  lLines += [
    "  SecAuditLogParts ABIJFHKZ",
    "  SecAuditLog /var/log/apache2/modsec_audit.log",
    "  # Passwords, tokens and cookies are masked in the audit log on disk too.",
    "  " + fSanitiseAction(pSanitise),
    "</IfModule>",
    ""
  ]
  return "\n".join(lLines)


def fCheck(pId: str, pStatus: str, pTitle: str, pDetail: str = "", pFix: str = "") -> dict:
  dCheck = {"id": pId, "status": pStatus, "title": pTitle, "detail": pDetail}
  if pFix:
    dCheck["fix"] = pFix
  return dCheck


def fCanPair(pFormat: str) -> bool:
  # What joining an access line without UNIQUE_ID to its request needs:
  # client IP, time, request line and status (combined, vhost_combined and
  # common have them).
  vHasIp = "%h" in pFormat or "%a" in pFormat or "%{c}a" in pFormat
  vHasTime = "%t" in pFormat or "}t" in pFormat
  vHasRequest = "%r" in pFormat or ("%m" in pFormat and "%U" in pFormat)
  vHasStatus = "%s" in pFormat or "%>s" in pFormat
  return vHasIp and vHasTime and vHasRequest and vHasStatus


def fCanRead(pPath: str) -> bool:
  try:
    with open(pPath, "rb") as vFile:
      vFile.read(1)
    return True
  except OSError:
    return False


def fRunDoctor(pConfig: ApacheConfig, pSources: list[dict], pSkipped: list[dict], pState: dict | None = None) -> list[dict]:
  ldChecks = []
  dState = pState or {}
  vFlavor = pConfig.vFlavor or "debian"
  vConfFile = "/etc/apache2/conf-available/localsiem.conf" if vFlavor == "debian" else "/etc/apache2/conf.d/localsiem.conf"
  if not pConfig.mFound():
    ldChecks.append(fCheck("apache_config", "error", "Apache configuration not found", "No apache2.conf or httpd.conf was found. Fix the sources by hand in the settings (modules.apache2.sources)."))
    return ldChecks
  ldChecks.append(fCheck("apache_config", "ok", "Apache configuration found", f"{pConfig.vConfigFile} ({len(pConfig.lFiles)} files read, {len(pConfig.lVhosts)} vhosts)."))
  for vProblem in pConfig.lProblems[:5]:
    ldChecks.append(fCheck("apache_config_read", "warning", "Part of the Apache configuration could not be read", vProblem))
  # 1. ModSecurity with OWASP CRS
  if pConfig.mModsecV3Loaded() and not pConfig.mModsecLoaded():
    ldChecks.append(fCheck("modsecurity", "error", "ModSecurity v3 is not supported", "libmodsecurity v3 with the Apache connector was found. localSIEM supports mod_security2 (ModSecurity v2)."))
  elif not pConfig.mModsecLoaded():
    vFix = "apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2" if vFlavor == "debian" else "Alpine has no ModSecurity package for Apache: build mod_security2 2.9 from source and load it with LoadModule security2_module."
    ldChecks.append(fCheck("modsecurity", "error", "ModSecurity (mod_security2) is not loaded", "ModSecurity with OWASP CRS is a prerequisite: without it localSIEM only sees the access and error logs.", vFix))
  else:
    ldChecks.append(fCheck("modsecurity", "ok", "ModSecurity (mod_security2) is loaded", pConfig.dModules.get("security2_module", "")))
  if pConfig.mModsecLoaded():
    if pConfig.dModsec["crs_files"]:
      vDetail = f"{len(pConfig.dModsec['crs_files'])} CRS files included"
      if pConfig.dModsec["threshold"] is not None:
        vDetail += f"; inbound anomaly threshold {pConfig.dModsec['threshold']}"
      ldChecks.append(fCheck("crs", "ok", "OWASP CRS is included", vDetail + "."))
    else:
      ldChecks.append(fCheck("crs", "error", "OWASP CRS is not included", "ModSecurity without the Core Rule Set detects almost nothing.", "apt-get install modsecurity-crs" if vFlavor == "debian" else "Include the CRS crs-setup.conf and rules/*.conf after ModSecurity."))
    vEngine = (pConfig.dModsec["rule_engine"] or "").lower()
    sVhostEngines = {(dVhost.get("rule_engine") or "").lower() for dVhost in pConfig.lVhosts if dVhost.get("rule_engine")}
    if vEngine == "on":
      ldChecks.append(fCheck("rule_engine", "ok", "SecRuleEngine On", "Requests over the anomaly threshold are blocked in phase 2; they stay in localSIEM and do not go to the SOC."))
    elif vEngine == "detectiononly":
      ldChecks.append(fCheck("rule_engine", "ok", "SecRuleEngine DetectionOnly", "Nothing is blocked: every rule match goes to the SOC."))
    elif vEngine == "off" and sVhostEngines & {"on", "detectiononly"}:
      lActive = sorted(dVhost["name"] or "?" for dVhost in pConfig.lVhosts if (dVhost.get("rule_engine") or "").lower() in ("on", "detectiononly"))
      ldChecks.append(fCheck("rule_engine", "warning", "SecRuleEngine Off except in some vhosts", "ModSecurity evaluates rules only in: " + ", ".join(lActive) + ". The other vhosts are not inspected.", "SecRuleEngine DetectionOnly   # or On, in the server or in each vhost"))
    elif vEngine == "off":
      ldChecks.append(fCheck("rule_engine", "error", "SecRuleEngine Off", "ModSecurity is loaded but does not evaluate rules.", "SecRuleEngine DetectionOnly   # or On"))
    else:
      ldChecks.append(fCheck("rule_engine", "warning", "SecRuleEngine is not set", "ModSecurity defaults to Off when SecRuleEngine is missing.", "SecRuleEngine DetectionOnly   # or On"))
    if "off" in sVhostEngines:
      ldChecks.append(fCheck("rule_engine_vhost", "warning", "SecRuleEngine Off in some vhosts", "Those vhosts are not inspected by ModSecurity."))
  # 2. mod_unique_id
  if pConfig.mIsLoaded("unique_id_module"):
    ldChecks.append(fCheck("unique_id", "ok", "mod_unique_id is loaded", "The three sources of a request can be joined by UNIQUE_ID."))
  elif pConfig.mModsecLoaded():
    # ModSecurity 2 does nothing without it (Alpine does not load it).
    ldChecks.append(fCheck("unique_id", "error", "mod_unique_id is not loaded: ModSecurity inspects nothing", "ModSecurity 2 needs mod_unique_id. Without it, it writes \"ModSecurity requires mod_unique_id to be installed.\" in error.log for every request, and neither blocks nor logs any attack.", "a2enmod unique_id" if vFlavor == "debian" else "LoadModule unique_id_module modules/mod_unique_id.so"))
  else:
    ldChecks.append(fCheck("unique_id", "warning", "mod_unique_id is not loaded", "Without UNIQUE_ID, localSIEM joins the sources by client IP, request, status and time (weak correlation).", "a2enmod unique_id" if vFlavor == "debian" else "LoadModule unique_id_module modules/mod_unique_id.so"))
  # 3. LogFormat
  lAccess = [dSource for dSource in pSources if dSource["kind"] == "access"]
  lRich = [dSource for dSource in lAccess if "%{UNIQUE_ID}e" in dSource.get("format", "") and "msec" in dSource.get("format", "") and "%v" in dSource.get("format", "")]
  if lRich:
    ldChecks.append(fCheck("log_format", "ok", "Access log with milliseconds, vhost, duration and UNIQUE_ID", ", ".join(dSource["path"] for dSource in lRich)))
  elif lAccess and all(fCanPair(dSource.get("format", "")) for dSource in lAccess):
    ldChecks.append(fCheck(
      "log_format", "ok", "Access logs in the format Apache writes",
      ", ".join(dSource["path"] for dSource in lAccess) + ". localSIEM reads them as they are: each line is joined to the ModSecurity records of its request by client IP, method, URI, status and time, and the vhost comes from %v or from the Host header and port of the audit record. They have whole seconds and no duration. Optional, for milliseconds, duration and joining by UNIQUE_ID: the localsiem_combined format (--configure-apache)."
    ))
  else:
    vFix = (
      ("" if vFlavor == "debian" else f"LoadModule logio_module {fModulePath(vFlavor)}/mod_logio.so   # if it is not loaded yet\n")
      + f"LogFormat \"{cLocalsiemFormat}\" localsiem_combined\n"
      f"GlobalLog {fLogDirectory(vFlavor)}/localsiem_access.log localsiem_combined"
    )
    ldChecks.append(fCheck("log_format", "warning", "An access log lacks the client IP, time, request line or status", "localSIEM reads it, but cannot join its lines to the ModSecurity records of each request. Add the localsiem_combined format (in " + vConfFile + "):", vFix))
  # 4. mod_remoteip
  if pConfig.mIsLoaded("remoteip_module") and pConfig.vRemoteIp:
    ldChecks.append(fCheck("remoteip", "ok", "mod_remoteip is configured", "%a is the real client IP."))
  else:
    ldChecks.append(fCheck("remoteip", "info", "mod_remoteip is not configured", "Only needed when the web is behind a proxy or a load balancer: without it every request seems to come from the proxy and the rules by IP do not work.", "a2enmod remoteip\nRemoteIPHeader X-Forwarded-For\nRemoteIPInternalProxy 10.0.0.1   # the proxy" if vFlavor == "debian" else "LoadModule remoteip_module modules/mod_remoteip.so\nRemoteIPHeader X-Forwarded-For\nRemoteIPInternalProxy 10.0.0.1   # the proxy"))
  # 5. Audit log
  if pConfig.mModsecLoaded():
    dModsec = pConfig.dModsec
    vAuditFix = (
      "SecAuditEngine RelevantOnly\n"
      "SecAuditLogRelevantStatus \"^(?:5|4(?!04))\"\n"
      "SecAuditLogType Serial\n"
      "SecAuditLogFormat JSON\n"
      "SecAuditLogParts ABIJFHKZ\n"
      "SecAuditLog /var/log/apache2/modsec_audit.log"
    )
    vAuditEngine = (dModsec["audit_engine"] or "").lower()
    if vAuditEngine not in ("relevantonly", "on") or not dModsec["audit_log"]:
      ldChecks.append(fCheck("audit_log", "warning", "The ModSecurity audit log is off", "Without it localSIEM decides from error.log only, and the request card has no headers or rules list.", vAuditFix))
    else:
      lNotes = []
      vStatus = "ok"
      if dModsec["audit_type"].lower() == "concurrent":
        lNotes.append("Concurrent type: supported, but its files are usually created with mode 600 and localsiem cannot read them. Serial is recommended.")
        vStatus = "warning"
      if (dModsec["audit_format"] or "native").lower() != "json":
        lNotes.append("Native format (JSON is recommended if this ModSecurity supports it).")
      vParts = dModsec["audit_parts"] or ""
      if "E" in vParts:
        lNotes.append("Part E (response body) is logged: it is bulky and sensitive, and not needed.")
        vStatus = "warning"
      if "H" not in vParts and vParts:
        lNotes.append("Part H is missing: without it the action taken cannot be read from the audit log.")
        vStatus = "warning"
      ldChecks.append(fCheck("audit_log", vStatus, "ModSecurity audit log", f"{dModsec['audit_log']} ({dModsec['audit_type'] or 'Serial'}, {dModsec['audit_format'] or 'Native'}, parts {vParts or 'default'}). " + " ".join(lNotes), vAuditFix if vStatus != "ok" else ""))
    # 6. Masking at the source
    if dModsec["sanitise"]:
      ldChecks.append(fCheck("sanitise", "ok", "Sensitive arguments are masked in the audit log", "sanitise actions found."))
    else:
      ldChecks.append(fCheck("sanitise", "warning", "The audit log on disk may hold passwords and cookies", "localSIEM masks them before storing, but the file written by ModSecurity keeps them.", fSanitiseAction()))
  # 7. Permissions
  for dSource in pSources:
    if not os.path.exists(dSource["path"]):
      ldChecks.append(fCheck("source_missing", "info", f"{dSource['path']} does not exist yet", "It will be read when Apache creates it."))
    elif not fCanRead(dSource["path"]):
      vFix = "usermod -aG adm localsiem" if vFlavor == "debian" else f"setfacl -m g:localsiem:rx {os.path.dirname(dSource['path'])} && setfacl -d -m g:localsiem:r {os.path.dirname(dSource['path'])} && setfacl -m g:localsiem:r {dSource['path']}"
      ldChecks.append(fCheck("permissions", "error", f"localsiem cannot read {dSource['path']}", "Give the localsiem user read access, also for the files of the next rotation.", vFix))
  if pSources and all(fCanRead(dSource["path"]) for dSource in pSources if os.path.exists(dSource["path"])):
    ldChecks.append(fCheck("permissions", "ok", "localsiem can read the Apache logs", f"{len(pSources)} sources."))
  for dSkipped in pSkipped:
    if dSkipped["reason"] == "piped_log":
      ldChecks.append(fCheck("piped_log", "warning", f"Piped log not supported: {dSkipped['path']}", "localSIEM reads files. Write this log to a file too, or fix the source by hand."))
    elif dSkipped["reason"] == "format_without_data":
      # Only what happens: the format of the logs of the server is never
      # changed, so there is no fix.
      vWhy = f"its LogFormat «{dSkipped['format']}» has no directive" if dSkipped.get("defined") else f"it uses the format «{dSkipped['format']}», which no LogFormat defines"
      ldChecks.append(fCheck(
        "log_format_without_data", "warning", f"Access log without data: {dSkipped['path']}",
        (f"Vhost {dSkipped['vhost']}. " if dSkipped.get("vhost") else "")
        + f"Its CustomLog ({dSkipped['file']}:{dSkipped['line']}) {vWhy}, so Apache writes that same text on every line, without the client IP, the time or the request. "
        "localSIEM does not read it: the requests of this vhost are seen in its error log and in the ModSecurity audit log."
      ))
  # Information gathered at run time by the collector.
  if dState.get("engine_off_seen"):
    ldChecks.append(fCheck("engine_runtime", "error", "ModSecurity reported its engine Off", "Seen in the audit log records."))
  if dState.get("producer"):
    ldChecks.append(fCheck("producer", "info", "ModSecurity version", dState["producer"]))
  return ldChecks


def fRequirementChecks(pConfig: ApacheConfig) -> list[dict]:
  # What the module needs before it can be turned on: Apache and ModSecurity
  # 2. Installing the module installs neither of them: without them it is
  # installed turned off, and once they are installed the administrator
  # reconfigures it in the web and turns it on.
  if pConfig.mFound():
    # The same two checks the doctor starts with.
    dDoctor = {dCheck["id"]: dCheck for dCheck in fRunDoctor(pConfig, [], [])}
    return [dDoctor["apache_config"], dDoctor["modsecurity"]]
  vFlavor = "alpine" if os.path.exists("/etc/alpine-release") else "debian"
  return [
    fCheck(
      "apache_config", "error", "Apache configuration not found",
      "No apache2.conf or httpd.conf was found, nor the file of the setting Apache configuration file. Installing this module does not install Apache: install Apache with ModSecurity 2 and the OWASP CRS, then reconfigure the module.",
      "apt-get install apache2 libapache2-mod-security2 modsecurity-crs && a2enmod security2" if vFlavor == "debian" else "apk add apache2   # then mod_security2 2.9, built from source: Alpine has no package of it"
    ),
    fCheck("modsecurity", "error", "ModSecurity (mod_security2) is not loaded", "It is checked once Apache is found.")
  ]
