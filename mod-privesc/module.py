"""The «privesc» module: privilege escalation on the server itself.

It lives outside the core (localSIEM-modules/mod-privesc/, installed in
/opt/localsiem/modules/privesc/) and the core loads it from module.json as the
package localsiem_modules.privesc: its own files are imported relatively, the
core through backend.core.

Sources (discovery.py): the auditd log, the files of the bash hook and
syslog (sudo, su, pkexec, doas and snoopy). Each one becomes events with the
same meaning, so the rules do not care which source saw a command:

  vhost   the person (login user; for the hook, the owner of the file)
  method  exec, command, shell, sudo, su, pkexec, doas, login, file, chmod,
          kmod, ptrace, denied, audit_config, auditd, crash...
  uri     the command line (masked)
  path    the program run, or the file changed
  ip      where the session comes from (sshd), when it is known
  score   distinct reconnaissance commands of the session in the window
  fields  who (login, real and effective user), session, the flags the rules
          match (recon_burst, suid_escape, root_without_door...)

Action taken: "blocked" when the system itself stopped it (the program did
not run, sudo or su refused, the file was refused); the rules about attempts
(sudo failures, files refused) count them anyway. Every detection comes from
the rules of rules/ (mDetectionFromSignal), except the scan of setuid
programs and the files of the hook (mHealth, severity.yaml).
"""

import os
import re
import stat
import time
from pathlib import Path

import yaml

from backend.core.masking import fTrim
from backend.core.module import Module
from backend.core.query import fQuoteValue
from backend.core.timeutil import fEpochToStorage, fNowStorage, fStorageToEpoch
from .commands import (
  SessionTracker, cDownloadOnelinerRegex, fBase, fCommandArgs, fCompileInTemporary, fFirstOperand, fIsDownloader,
  fIsInterpreter, fIsShell, fProgramKey, fReconToken, sDoorParents, sDoors
)
from .correlate import Correlator
from .discovery import Accounts, fAuditdPid, fContainer, fDiscoverSources
from .doctor import fRequirementChecks, fRunDoctor
from .parsers import fParseAuditLine, fParseHookLine, fParseSyslogLine
from .surface import (
  SurfaceScanner, fCapabilitiesFromMask, fCheckSensitiveFiles, fGtfobin, sDangerousCapabilities
)

cModulePath = Path(__file__).resolve().parent
lSeverityOrder = ["low", "medium", "high", "critical"]
cUnset = 4294967295
cTemporaryRegex = re.compile(r"^/(tmp|var/tmp|dev/shm|run/shm|run/user/\d+)/")
cWritableFolderRegex = re.compile(r"^/(tmp|var/tmp|dev/shm|run/shm|run/user/\d+|home|srv|var/www)/")
sWatchKeys = {"lsiem_auth", "lsiem_preload", "lsiem_pam", "lsiem_ssh", "lsiem_cron", "lsiem_service_unit", "lsiem_audit_config", "lsiem_hook"}
# Programs that change accounts, packages or services as their job: a change
# of a sensitive file made by them (or by a program they started) is not
# reported.
sAllowedWriters = {
  "dpkg", "apt", "apt-get", "aptitude", "unattended-upgrade", "unattended-upgrades", "apk", "rpm", "dnf", "yum",
  "useradd", "usermod", "userdel", "groupadd", "groupmod", "groupdel", "gpasswd", "passwd", "chpasswd", "chsh", "chfn",
  "chage", "vipw", "vigr", "visudo", "newusers", "pwck", "grpck", "pwconv", "grpconv", "systemd", "systemctl",
  "systemd-sysusers", "systemd-tmpfiles", "update-alternatives", "dpkg-trigger", "adduser", "deluser", "addgroup",
  "delgroup", "pam-auth-update", "ucf", "ucfr", "debconf", "augenrules", "auditctl", "auditd"
}
sPackageManagers = {"dpkg", "apt", "apt-get", "aptitude", "apk", "rpm", "dnf", "yum", "unattended-upgrade", "unattended-upgrades"}


def fLoadSeverityTable() -> dict:
  dDefaults = {
    "new_setuid": "high", "new_setuid_writable_folder": "critical", "new_setuid_gtfobins": "critical",
    "new_capabilities": "high", "sensitive_file_writable": "critical", "hook_file_tampering": "high"
  }
  try:
    with (cModulePath / "severity.yaml").open("r", encoding="utf-8") as vFile:
      dLoaded = yaml.safe_load(vFile) or {}
    dDefaults.update({vKey: str(vValue) for vKey, vValue in dLoaded.items() if str(vValue) in lSeverityOrder})
  except (OSError, yaml.YAMLError):
    pass
  return dDefaults


def fInteger(pValue) -> int | None:
  try:
    vValue = int(str(pValue), 0) if isinstance(pValue, str) and pValue.startswith("0x") else int(pValue)
  except (TypeError, ValueError):
    return None
  return None if vValue in (cUnset, -1) else vValue


def fCleanFields(pFields: dict) -> dict:
  # Without the empty values (0 stays: argc 0 is PwnKit).
  return {vKey: vValue for vKey, vValue in pFields.items() if vValue is not None and vValue is not False and vValue != "" and vValue != [] and vValue != {}}


class PrivescModule(Module):

  vName = "privesc"

  def __init__(self, pSettings: dict, pMasker, pStorage, pManifest: dict | None = None):
    super().__init__(pSettings, pMasker, pStorage, pManifest)
    self.vAccounts = Accounts()
    self.ldSources = []
    self.ldSkipped = []
    self.dInfo = {}
    self.vTracker = SessionTracker()
    self.vScanner = SurfaceScanner()
    self.dSeverity = fLoadSeverityTable()
    self.dRuntime = {"last_key_time": "", "audit_lines": 0, "surface": {}, "surface_disabled": False}
    self.dHealthMemory = {}
    self.vStartTime = time.time()
    self.vLastHealth = 0.0
    self.vLastSave = 0.0
    self.vLastSensitive = 0.0
    self.vAuditdWasRunning = None
    self.dSettingsCache = None

  def mStart(self) -> None:
    # First start: the learning days of the service accounts count from here.
    if not self.vStorage.mGetState("privesc.first_start"):
      self.vStorage.mSetState("privesc.first_start", fNowStorage())
    self.vTracker.mImport(self.vStorage.mGetState("privesc.sessions", {}) or {})
    self.dRuntime["surface"] = self.vStorage.mGetState("privesc.surface", {}) or {}
    dHealth = self.vStorage.mGetState("privesc.health", {}) or {}
    # The times of the memory are in the storage format; a state saved by an
    # older version has them in epoch seconds.
    self.dHealthMemory = {vKey: fEpochToStorage(vValue) if isinstance(vValue, (int, float)) else vValue for vKey, vValue in (dHealth.get("memory") or {}).items()}
    self.vAuditdWasRunning = dHealth.get("auditd_running")

  # Settings (read once per reload: every event uses them)

  def mReload(self, pSettings: dict, pMasker) -> None:
    super().mReload(pSettings, pMasker)
    self.dSettingsCache = None

  def mSettings(self) -> dict:
    if getattr(self, "dSettingsCache", None) is None:
      dModule = self.mModuleSettings()
      dModule["admin_group_list"] = [vItem.strip() for vItem in str(dModule.get("admin_groups") or "").split(",") if vItem.strip()]
      dModule["ignored_user_set"] = {vItem.strip() for vItem in str(dModule.get("ignored_users") or "").split(",") if vItem.strip()} | {"localsiem"}
      self.dSettingsCache = dModule
    return self.dSettingsCache

  def mAdminGroups(self) -> list[str]:
    return self.mSettings()["admin_group_list"]

  def mIgnoredUsers(self) -> set[str]:
    return self.mSettings()["ignored_user_set"]

  # Discovery

  def mDiscover(self) -> list[dict]:
    self.vAccounts.mLoad()
    self.ldSources, self.ldSkipped, self.dInfo = fDiscoverSources(self.mModuleSettings(), self.vAccounts)
    return self.ldSources

  def mSkipped(self) -> list[dict]:
    return self.ldSkipped

  # Reading

  def mParse(self, pSource: dict, pUnit: str, pReceived: str) -> dict:
    vKind = pSource["kind"]
    if vKind == "audit":
      dRecord = fParseAuditLine(pUnit, self.vMasker)
      self.dRuntime["audit_lines"] += 1
      if str(dRecord["fields"].get("key") or "").startswith("lsiem_") and dRecord.get("time"):
        self.dRuntime["last_key_time"] = dRecord["time"]
    elif vKind == "hook":
      dRecord = fParseHookLine(pUnit, pSource, self.vMasker)
    else:
      dRecord = fParseSyslogLine(pUnit, self.vMasker)
    dRecord["module"] = "privesc"
    dRecord["source"] = vKind
    dRecord["source_key"] = pSource["key"]
    dRecord["received"] = pReceived
    if not dRecord.get("time"):
      dRecord["time"] = pReceived
    return dRecord

  def mCreateCorrelator(self):
    return Correlator()

  # Events

  def mNewEvent(self, pRecords: list[dict], pSource: str) -> dict:
    lStatuses = [dRecord["parse_status"] for dRecord in pRecords]
    if all(vStatus == "unparsed" for vStatus in lStatuses):
      vParseStatus = "unparsed"
    elif any(vStatus != "ok" for vStatus in lStatuses):
      vParseStatus = "partial"
    else:
      vParseStatus = "ok"
    dEvent = {vColumn: None for vColumn in ("vhost", "method", "uri", "path", "query", "status", "bytes", "duration", "ua", "referer", "uid", "category", "phase", "score", "threshold", "engine", "severity", "ip")}
    dEvent.update({
      "time": min(dRecord["time"] for dRecord in pRecords),
      "received": min(dRecord["received"] for dRecord in pRecords),
      "host": self.dSettings["host"],
      "module": "privesc",
      "sources": [pSource],
      "rules": [],
      "action": "none",
      "parse_status": vParseStatus,
      "correlation": "none",
      "fields": {},
      "record_ids": [dRecord["id"] for dRecord in pRecords if dRecord.get("id")],
      "rule_hits": [],
      "detections": []
    })
    return dEvent

  def mBuildEvent(self, pTransaction: dict) -> dict:
    lRecords = pTransaction["records"]
    vSource = lRecords[0].get("source") or "audit"
    dEvent = self.mNewEvent(lRecords, vSource)
    dFields = {}
    if vSource == "audit":
      self.mAuditEvent(lRecords, dEvent, dFields)
      dEvent["uid"] = pTransaction.get("uid") or lRecords[0].get("correlation")
      dEvent["correlation"] = "uid"
    elif vSource == "hook":
      self.mHookEvent(lRecords[0], dEvent, dFields)
    else:
      self.mSyslogEvent(lRecords[0], dEvent, dFields)
    if not dEvent["uid"]:
      dEvent["uid"] = f"{vSource}:{fStorageToEpoch(dEvent['time']):.6f}:{dFields.get('pid') or ''}"
    vUser = dEvent.get("vhost") or ""
    if vUser in self.mIgnoredUsers() or (dFields.get("real_user") or "") in self.mIgnoredUsers():
      dFields["ignored"] = True
    dEvent["uri"] = fTrim(dEvent["uri"], 2000) if dEvent["uri"] else None
    dEvent["fields"] = fCleanFields(dFields)
    return dEvent

  def mAccount(self, pUid) -> str:
    return self.vAccounts.mAccountType(pUid, self.mAdminGroups()) if pUid is not None else ""

  def mAnalyzeCommand(self, pEvent: dict, pFields: dict, pArgs: list[str], pSession: str, pDownloadScope: str, pNow: float) -> None:
    # What any command means, whatever its source: reconnaissance (distinct
    # tokens of the session in the window), a download piped into a shell,
    # the recent commands of the session, and, for service accounts, whether
    # the program is new for the account.
    dModule = self.mSettings()
    vAccount = pFields.get("account_type") or ""
    vToken = fReconToken(pArgs)
    if vToken and pSession:
      lTokens = self.vTracker.mRecon(pSession, vToken, pNow, float(dModule.get("recon_window_seconds", 120)))
      vThreshold = int(dModule.get("recon_threshold_admins", 20)) if vAccount in ("admin", "root") else int(dModule.get("recon_threshold", 8))
      vEnumeration = int(dModule.get("enumeration_threshold", 40))
      pFields["recon"] = vToken
      pFields["recon_distinct"] = len(lTokens)
      pFields["recon_burst"] = len(lTokens) >= vThreshold
      pFields["recon_massive"] = len(lTokens) >= vEnumeration
      if pFields["recon_burst"]:
        pFields["recon_tokens"] = lTokens[-40:]
      pEvent["score"] = len(lTokens)
      pEvent["threshold"] = vThreshold
    vFirst = fBase(pArgs[0]) if pArgs else ""
    if cDownloadOnelinerRegex.search(str(pEvent.get("uri") or "")):
      pFields["download_to_shell"] = True
    if fCompileInTemporary(pArgs, pFields.get("cwd") or ""):
      pFields["compile_in_tmp"] = True
    if pDownloadScope:
      if vFirst and fIsDownloader(vFirst):
        self.vTracker.mDownload(pDownloadScope, pNow)
      elif vFirst and (fIsShell(vFirst) or fIsInterpreter(vFirst)) and "-c" not in pArgs[1:] and not fFirstOperand(pArgs[1:]):
        if self.vTracker.mRecentDownload(pDownloadScope, pNow):
          pFields["download_to_shell"] = True
    if pSession and pEvent.get("uri"):
      self.vTracker.mCommand(pSession, pEvent["time"], pEvent["uri"], pNow)
    if vAccount == "service":
      pFields["service_account"] = True
      vProgram = fProgramKey(pFields.get("exe") or "", pArgs)
      pFields["program"] = vProgram
      if self.vStorage is not None and vProgram:
        vFirstSeen = self.vStorage.mPathFirstSeen("privesc:" + (pFields.get("real_user") or ""), vProgram, pEvent["time"])
        vLearning = float(dModule.get("learning_days", 3)) * 86400
        vFirstStart = self.vStorage.mGetState("privesc.first_start")
        if vFirstStart and pNow - fStorageToEpoch(vFirstStart) >= vLearning and pNow - fStorageToEpoch(vFirstSeen) <= 60:
          pFields["new_program"] = True

  # Audit

  def mWriterAllowed(self, pExe: str, pPpid) -> bool:
    # The program, or one of its known ancestors, changes accounts, packages
    # or services as its job.
    if fBase(pExe) in sAllowedWriters:
      return True
    vPid = pPpid
    for _ in range(8):
      dParent = self.vTracker.mProcess(vPid)
      if dParent is None:
        return False
      if fBase(dParent.get("exe")) in sAllowedWriters or fBase(dParent.get("exe")) in sPackageManagers:
        return True
      vPid = dParent.get("ppid")
    return False

  def mAuditEvent(self, pRecords: list[dict], pEvent: dict, pFields: dict) -> None:
    dByType = {}
    for dRecord in pRecords:
      dByType.setdefault(str(dRecord["fields"].get("type") or ""), []).append(dRecord["fields"])
    dSyscall = (dByType.get("SYSCALL") or [{}])[0]
    dFirst = pRecords[0]["fields"]
    dIds = dSyscall or dFirst
    vNow = fStorageToEpoch(pEvent["time"])
    vAuid = fInteger(dIds.get("auid"))
    vUid = fInteger(dIds.get("uid"))
    vEuid = fInteger(dIds.get("euid"))
    vSes = fInteger(dIds.get("ses"))
    vSession = f"audit:{vSes}" if vSes is not None else ""
    lKeys = [vItem for vItem in re.split(r"[\x01,]", str(dSyscall.get("key") or dFirst.get("key") or "")) if vItem and vItem != "(null)"]
    vKey = next((vItem for vItem in lKeys if vItem.startswith("lsiem_")), lKeys[0] if lKeys else "")
    vUser = self.vAccounts.mName(vAuid) if vAuid is not None else self.vAccounts.mName(vUid)
    pFields.update({
      "source_detail": "auditd", "type": ",".join(sorted(vType for vType in dByType if vType)), "key": vKey,
      "login_uid": vAuid, "login_user": self.vAccounts.mName(vAuid) if vAuid is not None else "",
      "real_uid": vUid, "real_user": self.vAccounts.mName(vUid) if vUid is not None else "",
      "effective_uid": vEuid, "effective_user": self.vAccounts.mName(vEuid) if vEuid is not None else "",
      "session": vSession, "pid": fInteger(dIds.get("pid")), "ppid": fInteger(dIds.get("ppid")),
      "tty": dIds.get("tty") if dIds.get("tty") not in ("(none)", "") else "", "exe": dIds.get("exe") or "",
      "comm": dIds.get("comm") or "", "syscall": (dSyscall.get("names") or {}).get("syscall") or dSyscall.get("syscall") or ""
    })
    pFields["account_type"] = self.mAccount(vAuid if vAuid is not None else vUid)
    pEvent["vhost"] = vUser or None
    if dSyscall:
      pFields["success"] = dSyscall.get("success") == "yes"
      pFields["exit"] = fInteger(dSyscall.get("exit"))
      if dSyscall.get("success") == "no":
        pEvent["action"] = "blocked"
    dSession = self.vTracker.mGet(vSession) if vSession else None
    if dSession and dSession.get("ip"):
      pEvent["ip"] = dSession["ip"]
    vCwd = ((dByType.get("CWD") or [{}])[0]).get("cwd") or ""
    if vCwd:
      pFields["cwd"] = vCwd
    if "EXECVE" in dByType:
      self.mAuditExec(dByType, dSyscall, pEvent, pFields, vNow)
      return
    vType = dFirst.get("type", "")
    if vType.startswith(("USER_", "CRED_")) or vType == "LOGIN":
      self.mAuditUser(vType, dFirst, pEvent, pFields, vNow)
      return
    if vType == "CONFIG_CHANGE" or "CONFIG_CHANGE" in dByType:
      dChange = (dByType.get("CONFIG_CHANGE") or [dFirst])[0]
      pEvent["method"] = "audit_config"
      pEvent["uri"] = " ".join(f"{vName}={dChange[vName]}" for vName in ("op", "key", "audit_enabled", "list", "res") if dChange.get(vName) not in (None, ""))
      pFields["audit_disabled"] = str(dChange.get("audit_enabled")) == "0"
      pFields["audit_rule_removed"] = "remove_rule" in str(dChange.get("op") or "") and str(dChange.get("key") or "").startswith("lsiem_")
      return
    if vType.startswith("DAEMON_"):
      pEvent["method"] = "auditd"
      pEvent["uri"] = vType + " " + str(dFirst.get("op") or "")
      pFields["daemon_event"] = vType
      vSender = fInteger(dFirst.get("pid"))
      pFields["auditd_stopped_manually"] = vType in ("DAEMON_END", "DAEMON_ABORT") and vSender not in (None, 1)
      return
    if vType == "ANOM_ABEND":
      vExe = dFirst.get("exe") or ""
      pEvent["method"] = "crash"
      pEvent["path"] = vExe
      pEvent["uri"] = f"{vExe} signal {dFirst.get('sig', '?')}"
      vSetuid = False
      try:
        vSetuid = bool(os.stat(vExe).st_mode & stat.S_ISUID)
      except OSError:
        pass
      pFields["setuid_exe"] = vSetuid
      pFields["crash_suspicious"] = vSetuid or bool(cTemporaryRegex.match(vExe))
      return
    if not dSyscall:
      pEvent["method"] = vType.lower() or "other"
      return
    lPaths = sorted(dByType.get("PATH") or [], key=lambda dItem: fInteger(dItem.get("item")) or 0)
    dTarget = next((dItem for dItem in lPaths if dItem.get("nametype") not in ("PARENT",)), lPaths[0] if lPaths else {})
    vFile = dTarget.get("name") or ""
    if vFile and not vFile.startswith("/") and vCwd:
      vFile = os.path.normpath(os.path.join(vCwd, vFile))
    pEvent["path"] = vFile or None
    pEvent["uri"] = (dByType.get("PROCTITLE") or [{}])[0].get("proctitle") or pFields.get("exe")
    if vFile:
      pFields["file"] = vFile
    if vKey in sWatchKeys:
      pEvent["method"] = "file"
      pFields["writer_allowed"] = self.mWriterAllowed(pFields["exe"], pFields.get("ppid"))
    elif vKey == "lsiem_suid":
      pEvent["method"] = "chmod"
      vArgument = dSyscall.get("a2") if "fchmodat" in str(pFields.get("syscall")) or dSyscall.get("syscall") in ("268", "53", "306") else dSyscall.get("a1")
      try:
        vMode = int(str(vArgument or "0"), 16)
        pFields["chmod_mode"] = oct(vMode & 0o7777)
      except ValueError:
        pass
      pFields["writer_allowed"] = self.mWriterAllowed(pFields["exe"], pFields.get("ppid"))
    elif vKey == "lsiem_kmod":
      pEvent["method"] = "kmod"
      vName = ((dByType.get("KERN_MODULE") or [{}])[0]).get("name") or ""
      if vName:
        pFields["kernel_module"] = vName
    elif vKey == "lsiem_ptrace":
      pEvent["method"] = "ptrace"
      pFields["ptrace_target"] = fInteger("0x" + str(dSyscall.get("a1") or "0"))
    elif vKey == "lsiem_denied":
      pEvent["method"] = "denied"
      pEvent["action"] = "blocked"
    else:
      pEvent["method"] = "syscall"

  def mAuditExec(self, pByType: dict, pSyscall: dict, pEvent: dict, pFields: dict, pNow: float) -> None:
    dExecve = pByType["EXECVE"][0]
    lArgs = list(dExecve.get("args") or [])
    vArgc = fInteger(dExecve.get("argc"))
    vExe = pFields.get("exe") or ""
    pEvent["method"] = "exec"
    pEvent["path"] = vExe or None
    pEvent["uri"] = dExecve.get("command") or (pByType.get("PROCTITLE") or [{}])[0].get("proctitle") or vExe
    pFields["argc"] = vArgc
    if vArgc == 0:
      pFields["argc_zero"] = True
    lPaths = sorted(pByType.get("PATH") or [], key=lambda dItem: fInteger(dItem.get("item")) or 0)
    # The file given to execve (item 0): for a script it is the script, while
    # exe is its interpreter (/tmp/x.sh run by /usr/bin/bash).
    vProgram = str(lPaths[0].get("name") or "") if lPaths else ""
    if vProgram and not vProgram.startswith("/") and pFields.get("cwd"):
      vProgram = os.path.normpath(os.path.join(str(pFields["cwd"]), vProgram))
    if vProgram.startswith("/"):
      pEvent["path"] = vProgram
    vSetuid = None
    if lPaths and lPaths[0].get("mode"):
      try:
        vMode = int(str(lPaths[0]["mode"]), 8)
        vSetuid = bool(vMode & stat.S_ISUID) and fInteger(lPaths[0].get("ouid")) == 0
      except ValueError:
        vSetuid = None
    if vSetuid is None and vExe:
      try:
        vStat = os.stat(vExe)
        vSetuid = bool(vStat.st_mode & stat.S_ISUID) and vStat.st_uid == 0
      except OSError:
        vSetuid = False
    pFields["setuid_exe"] = bool(vSetuid)
    vUid = pFields.get("real_uid")
    vEuid = pFields.get("effective_uid")
    vSuccess = pSyscall.get("success") != "no"
    dParent = self.vTracker.mProcess(pFields.get("ppid"))
    if dParent:
      pFields["parent_exe"] = dParent.get("exe")
    # Root inherited from a setuid program: the program run is not setuid,
    # but it runs with the effective uid of root and the real uid of a user
    # (find -exec /bin/sh -p, vim -c ':!sh', python os.setuid...).
    pFields["suid_escape"] = vSuccess and vEuid == 0 and vUid not in (None, 0) and not vSetuid
    # Capabilities gained from the file of the program (setcap).
    for dCaps in pByType.get("BPRM_FCAPS") or []:
      lGained = [vName for vName in fCapabilitiesFromMask(dCaps.get("pp")) if vName not in fCapabilitiesFromMask(dCaps.get("old_pp"))]
      if lGained:
        pFields["file_caps"] = lGained
        pFields["file_caps_dangerous"] = bool(set(lGained) & sDangerousCapabilities) and vUid not in (None, 0)
    vSession = pFields.get("session") or ""
    vAuid = pFields.get("login_uid")
    dSession = self.vTracker.mGet(vSession) if vSession else None
    # Root without a door: a session of a person whose start was seen, never
    # went through sudo, su, pkexec or doas, and runs programs as root.
    if vSuccess and dSession and dSession.get("started") and not dSession.get("door") and vAuid is not None and vAuid != 0 and vUid == 0 and vEuid == 0:
      pFields["root_without_door"] = True
    if vSuccess:
      self.vTracker.mRememberProcess(pFields.get("pid"), vExe, vUid, vEuid, pNow)
      dProcess = self.vTracker.mProcess(pFields.get("pid"))
      if dProcess is not None:
        dProcess["ppid"] = pFields.get("ppid")
    self.mAnalyzeCommand(pEvent, pFields, lArgs, vSession or f"audit-pid:{pFields.get('ppid')}", f"audit:{pFields.get('ppid')}", pNow)

  def mAuditUser(self, pType: str, pRecord: dict, pEvent: dict, pFields: dict, pNow: float) -> None:
    vExe = pRecord.get("exe") or ""
    vBase = fBase(vExe)
    vResult = "success" if pRecord.get("res") in ("success", "1", "yes") else ("failed" if pRecord.get("res") else "")
    vAddress = pRecord.get("addr") if pRecord.get("addr") not in (None, "", "?") else ""
    vSession = pFields.get("session") or ""
    vTarget = pRecord.get("acct") or ""
    pFields.update({"result": vResult, "target_user": vTarget, "op": pRecord.get("op") or "", "terminal": pRecord.get("terminal") or ""})
    if vBase in ("sshd", "sshd-session", "login", "sshd-auth"):
      pEvent["method"] = "login"
    elif vBase in sDoors or vBase in ("sudo", "su", "pkexec", "doas"):
      pEvent["method"] = vBase.replace("-rs", "")
    else:
      pEvent["method"] = pType.lower()
    pEvent["uri"] = pRecord.get("cmd") or pRecord.get("op") or pType
    pEvent["path"] = vExe or None
    if vAddress:
      pEvent["ip"] = vAddress
    if vResult == "failed":
      pEvent["action"] = "blocked"
    if pType == "LOGIN":
      vNewAuid = fInteger(pRecord.get("auid"))
      vNewSes = fInteger(pRecord.get("ses"))
      if vNewAuid is not None and vNewSes is not None and str(pRecord.get("res")) in ("1", "success"):
        self.vTracker.mStart(f"audit:{vNewSes}", self.vAccounts.mName(vNewAuid), "", pNow)
        pEvent["vhost"] = self.vAccounts.mName(vNewAuid) or pEvent["vhost"]
        pFields["session"] = f"audit:{vNewSes}"
      return
    if not vSession or vResult != "success":
      return
    if pType in ("USER_LOGIN", "USER_START") and pEvent["method"] == "login":
      self.vTracker.mStart(vSession, pEvent.get("vhost") or "", vAddress, pNow)
    if pType in ("USER_START", "USER_CMD", "USER_ROLE_CHANGE") and (vBase in sDoors and vBase not in ("sshd", "sshd-session", "login")):
      if pType == "USER_CMD" or vTarget in ("root", "") or self.vAccounts.mUid(vTarget) == 0:
        self.vTracker.mDoor(vSession, pNow)
        pFields["door"] = True
    if pType == "USER_CMD" and pEvent.get("uri"):
      self.vTracker.mCommand(vSession, pEvent["time"], "sudo " + str(pEvent["uri"]), pNow)

  # Hook

  def mHookEvent(self, pRecord: dict, pEvent: dict, pFields: dict) -> None:
    dLine = pRecord["fields"]
    vOwner = dLine.get("owner_uid")
    vUser = self.vAccounts.mName(vOwner) if vOwner is not None else ""
    vNow = fStorageToEpoch(pEvent["time"])
    vSession = f"hook:{vOwner}:{dLine.get('pid')}"
    pEvent["vhost"] = vUser or None
    pEvent["ip"] = dLine.get("ssh_client") or None
    pFields.update({
      "source_detail": "hook", "real_uid": vOwner, "real_user": vUser, "effective_uid": dLine.get("euid"),
      "effective_user": self.vAccounts.mName(dLine.get("euid")) if dLine.get("euid") is not None else "",
      "session": vSession, "pid": dLine.get("pid"), "ppid": dLine.get("ppid"), "tty": dLine.get("tty"),
      "cwd": dLine.get("cwd"), "ssh_client": dLine.get("ssh_client"), "sudo_user": dLine.get("sudo_user"),
      "forged": dLine.get("forged"), "account_type": self.mAccount(vOwner)
    })
    if pRecord.get("parse_status") == "unparsed":
      pEvent["method"] = "hook"
      return
    if dLine.get("kind") == "start":
      vParent = str(dLine.get("parent") or "")
      vParentUid = dLine.get("parent_uid")
      pEvent["method"] = "shell"
      pEvent["uri"] = f"interactive bash started by {vParent or '?'}"
      pEvent["path"] = vParent or None
      pFields["parent_comm"] = vParent
      pFields["parent_uid"] = vParentUid
      self.vTracker.mStart(vSession, vUser, dLine.get("ssh_client") or "", vNow)
      if dLine.get("sudo_user") or vParent in ("sudo", "su", "pkexec", "doas", "run0"):
        self.vTracker.mDoor(vSession, vNow)
        pFields["door"] = True
      if vOwner == 0:
        # A root shell whose parent is a program of a user that is not a way
        # to become root (an exploit that called setuid(0) and ran bash).
        pFields["root_without_door"] = vParentUid not in (None, 0) and vParent not in sDoorParents
        pFields["parent_interpreter"] = fIsInterpreter(vParent)
      return
    vCommand = str(dLine.get("command") or "")
    lArgs = fCommandArgs(vCommand)
    vFirst = lArgs[0] if lArgs else ""
    vPath = vFirst
    if "/" in vFirst and dLine.get("cwd"):
      vPath = os.path.normpath(os.path.join(str(dLine.get("cwd")), vFirst))
    pEvent["method"] = "command"
    pEvent["uri"] = vCommand
    pEvent["path"] = vPath or None
    self.mAnalyzeCommand(pEvent, pFields, lArgs, vSession, f"hook:{vOwner}:{dLine.get('pid')}:{dLine.get('line')}", vNow)

  # Syslog

  def mSyslogEvent(self, pRecord: dict, pEvent: dict, pFields: dict) -> None:
    dLine = pRecord["fields"]
    vKind = dLine.get("kind") or "other"
    vNow = fStorageToEpoch(pEvent["time"])
    pFields.update({"source_detail": "syslog", "program": dLine.get("program"), "syslog_host": dLine.get("syslog_host"), "pid": dLine.get("pid")})
    if pRecord.get("parse_status") == "unparsed":
      pEvent["method"] = "syslog"
      return
    if vKind == "exec":
      # snoopy
      vUid = dLine.get("uid")
      vEuid = dLine.get("euid")
      vUser = dLine.get("login") or dLine.get("username") or (self.vAccounts.mName(vUid) if vUid is not None else "")
      if vUser in ("(unknown)", "-", "(none)"):
        vUser = self.vAccounts.mName(vUid) if vUid is not None else ""
      vSession = f"snoopy:{vUid}:{dLine.get('sid')}"
      vFile = str(dLine.get("filename") or "")
      pEvent["vhost"] = vUser or None
      pEvent["method"] = "exec"
      pEvent["path"] = vFile or None
      pEvent["uri"] = dLine.get("command") or vFile
      pFields.update({
        "source_detail": "snoopy", "real_uid": vUid, "real_user": self.vAccounts.mName(vUid) if vUid is not None else "",
        "effective_uid": vEuid, "effective_user": self.vAccounts.mName(vEuid) if vEuid is not None else "",
        "session": vSession, "ppid": dLine.get("ppid"), "tty": dLine.get("tty"), "cwd": dLine.get("cwd"),
        "exe": vFile, "account_type": self.mAccount(vUid)
      })
      vSetuid = False
      try:
        vStat = os.stat(vFile)
        vSetuid = bool(vStat.st_mode & stat.S_ISUID) and vStat.st_uid == 0
      except OSError:
        pass
      pFields["setuid_exe"] = vSetuid
      pFields["suid_escape"] = vEuid == 0 and vUid not in (None, 0) and not vSetuid and bool(vFile)
      self.mAnalyzeCommand(pEvent, pFields, fCommandArgs(str(dLine.get("command") or "")), vSession, f"snoopy:{dLine.get('ppid')}", vNow)
      return
    vUser = dLine.get("user") or ""
    pEvent["vhost"] = vUser or None
    pFields.update({"real_user": vUser, "target_user": dLine.get("target"), "result": dLine.get("result"), "tty": dLine.get("tty"), "cwd": dLine.get("cwd"), "reason": dLine.get("reason")})
    vUid = self.vAccounts.mUid(vUser) if vUser else None
    pFields["account_type"] = self.mAccount(vUid) if vUid is not None else ""
    if dLine.get("result") == "failed":
      pEvent["action"] = "blocked"
    if vKind in ("sudo", "su", "pkexec", "doas"):
      pEvent["method"] = vKind
      pEvent["uri"] = dLine.get("command") or dLine.get("message") or (f"{vKind} to {dLine.get('target')}" if dLine.get("target") else vKind)
      pEvent["path"] = dLine.get("program")
      if vKind == "pkexec":
        pFields["message"] = dLine.get("message")
      return
    if vKind == "login":
      pEvent["method"] = "login"
      pEvent["ip"] = dLine.get("ip") or None
      pEvent["uri"] = f"{dLine.get('method', '')} login of {vUser}"
      return
    if vKind == "pam":
      pEvent["method"] = "pam"
      pEvent["uri"] = f"{dLine.get('service', '')} {dLine.get('stage', '')} {dLine.get('session') or dLine.get('result') or ''}".strip()
      return
    pEvent["method"] = "syslog"
    pEvent["path"] = dLine.get("program")

  # Detections of the rules

  def mDetectionFromSignal(self, pEvent: dict, pSignal: dict) -> dict:
    dFields = pEvent.get("fields") or {}
    vIp = pEvent.get("ip") or ""
    dDetails = {
      "user": pEvent.get("vhost") or "",
      "account_type": dFields.get("account_type", ""),
      "real_user": dFields.get("real_user", ""),
      "effective_user": dFields.get("effective_user", ""),
      "command": fTrim(pEvent.get("uri") or "", 1000),
      "program": fTrim(pEvent.get("path") or "", 500),
      "cwd": fTrim(dFields.get("cwd") or "", 300),
      "tty": dFields.get("tty", ""),
      "session": dFields.get("session", ""),
      "source": dFields.get("source_detail", ""),
      "client_ip": vIp,
      "rule": {"id": pSignal["rule_id"], "count": pSignal.get("count", 1)}
    }
    for vName in ("parent_exe", "parent_comm", "file", "target_user", "result", "recon_distinct", "recon_tokens", "file_caps", "chmod_mode", "kernel_module", "ssh_client", "sudo_user", "audit_disabled"):
      if dFields.get(vName) not in (None, "", []):
        dDetails[vName] = dFields[vName] if not isinstance(dFields[vName], str) else fTrim(dFields[vName], 500)
    if dFields.get("source_detail") == "hook" and vIp:
      dDetails["client_ip_source"] = "SSH_CLIENT of the shell (set by sshd, but a user can change it)"
    vSearch = pSignal.get("search") or ("module:privesc vhost:" + fQuoteValue(pEvent.get("vhost") or ""))
    vDescription = pSignal.get("description") or ""
    if "localSIEM search:" not in vDescription:
      vDescription = (vDescription + " localSIEM search: " + vSearch).strip()
    return {
      "module": "privesc", "vhost": pEvent.get("vhost") or "", "ip": vIp, "category": pSignal["category"],
      "severity": pSignal["severity"], "rule": pSignal["name"], "type": pSignal["type"], "description": vDescription,
      "search": vSearch, "details": dDetails, "time": pEvent.get("time"), "uid": pEvent.get("uid") or ""
    }

  # Rules

  def mRulesPath(self) -> Path:
    return cModulePath / "rules"

  # Enrichment

  def mEnrich(self, pDetection: dict) -> dict:
    vSession = (pDetection.get("details") or {}).get("session") or ""
    if not vSession:
      return {}
    dSession = self.vTracker.mGet(vSession) or {}
    dContext = {
      "session_started_seen": bool(dSession.get("started")),
      "session_used_sudo_su": bool(dSession.get("door")),
      "recent_commands": [f"{vTime} {vText}" for vTime, vText in self.vTracker.mRecent(vSession)[-20:]]
    }
    if dSession.get("ip"):
      dContext["session_ip"] = dSession["ip"]
    return dContext

  # Doctor and health

  def mDoctorState(self) -> dict:
    dState = dict(self.dRuntime)
    dState["surface_disabled"] = int(self.mModuleSettings().get("surface_scan_hours", 24) or 0) == 0
    return dState

  def mDoctor(self) -> list[dict]:
    if not self.dInfo:
      self.mDiscover()
    return fRunDoctor(self.dInfo, self.mDoctorState(), self.vAccounts)

  def mModuleDetection(self, pKey: str, pCategory: str, pTarget: str, pRule: str, pDescription: str, pDetails: dict) -> dict:
    return {
      "module": "privesc", "vhost": pTarget, "ip": "", "category": pCategory, "severity": self.dSeverity.get(pKey, "high"),
      "rule": pRule, "type": "privilege-escalation", "description": pDescription + " localSIEM search: module:privesc",
      "search": "module:privesc", "details": pDetails, "time": fNowStorage(), "uid": ""
    }

  def mHealth(self, pNow: float) -> list[dict]:
    from backend.core.health import fHealthDetection
    ldDetections = []
    if self.vTracker.vDirty and pNow - self.vLastSave >= 60:
      self.vStorage.mSetState("privesc.sessions", self.vTracker.mExport())
      self.vTracker.vDirty = False
      self.vLastSave = pNow
    ldDetections.extend(self.mSurfaceResult())
    if pNow - self.vLastHealth < 300:
      return ldDetections
    self.vLastHealth = pNow
    vChanged = False
    # Sessions idle for a day, old downloads and processes leave the memory.
    self.vTracker.mPrune(pNow)
    # auditd stopped (not in a container, where it never runs).
    if not (self.dInfo.get("container") if self.dInfo else fContainer()):
      vRunning = fAuditdPid() is not None
      if self.vAuditdWasRunning and not vRunning:
        ldDetections.append(fHealthDetection(
          "health-auditd", "high", "localSIEM health: auditd stopped",
          "auditd was running and is not any more: the commands, setuid programs and sensitive files are not audited. If nobody stopped it on purpose, someone may have turned the audit off after becoming root.",
          "auditd", {"check": "health-auditd"}
        ))
      if vRunning != self.vAuditdWasRunning:
        self.vAuditdWasRunning = vRunning
        vChanged = True
    # Files of the hook created by someone else in the place of a user.
    for dProblem in (self.dInfo.get("hook_problems") or []):
      if dProblem["problem"] not in ("wrong_owner", "not_a_file"):
        continue
      vMemory = "hook:" + dProblem["path"] + ":" + str(dProblem.get("owner"))
      if vMemory in self.dHealthMemory:
        continue
      self.dHealthMemory[vMemory] = fEpochToStorage(pNow)
      vChanged = True
      ldDetections.append(self.mModuleDetection(
        "hook_file_tampering", "hook-tampering", dProblem.get("user") or str(dProblem.get("uid")),
        "Privilege escalation: the command file of a user was taken by another user",
        f"{dProblem['path']} should belong to {dProblem.get('user') or dProblem.get('uid')} but " + ("belongs to " + str(dProblem.get("owner_name") or dProblem.get("owner")) if dProblem["problem"] == "wrong_owner" else "is not a regular file") + ": someone created it to read the commands of that user or to stop them from being logged. localSIEM does not read it; --configure-privesc moves it aside.",
        {"file": dProblem["path"], "problem": dProblem["problem"], "owner": dProblem.get("owner_name") or dProblem.get("owner")}
      ))
    # Sensitive files writable by someone other than root, once an hour.
    if pNow - self.vLastSensitive >= 3600:
      self.vLastSensitive = pNow
      for dProblem in fCheckSensitiveFiles():
        vMemory = "sensitive:" + dProblem["path"] + ":" + dProblem["problem"] + ":" + dProblem["detail"]
        if vMemory in self.dHealthMemory:
          continue
        self.dHealthMemory[vMemory] = fEpochToStorage(pNow)
        vChanged = True
        ldDetections.append(self.mModuleDetection(
          "sensitive_file_writable", "writable-sensitive-file", dProblem["path"],
          "Privilege escalation: sensitive file " + ("writable" if dProblem["problem"] == "writable" else "readable") + " by someone other than root",
          f"{dProblem['path']} (mode {dProblem['mode']}) can be " + ("changed" if dProblem["problem"] == "writable" else "read") + f" by {dProblem['detail']}. Whoever can change it can become root (a user in passwd, a rule in sudoers, a job in cron, a program in the PATH of root). Check who changed its permissions.",
          {"file": dProblem["path"], "problem": dProblem["problem"], "who": dProblem["detail"], "mode": dProblem["mode"]}
        ))
    # Scan of setuid programs, every surface_scan_hours (the first one five
    # minutes after the start).
    vHours = int(self.mModuleSettings().get("surface_scan_hours", 24) or 0)
    vLast = fStorageToEpoch((self.dRuntime.get("surface") or {}).get("time") or "") if (self.dRuntime.get("surface") or {}).get("time") else 0.0
    if vHours > 0 and pNow - self.vStartTime >= 300 and pNow - vLast >= vHours * 3600 and not self.vScanner.mRunning():
      lPaths = [vItem.strip() for vItem in str(self.mModuleSettings().get("scan_paths") or "").split(",") if vItem.strip()]
      self.vScanner.mStart(lPaths)
    if vChanged:
      self.vStorage.mSetState("privesc.health", {"memory": self.dHealthMemory, "auditd_running": self.vAuditdWasRunning})
    return ldDetections

  def mSurfaceResult(self) -> list[dict]:
    # A finished scan against the reference (the previous scan): new setuid
    # programs and new capabilities. The first scan is only the reference.
    dResult = self.vScanner.mTake()
    if dResult is None:
      return []
    ldDetections = []
    dPrevious = self.dRuntime.get("surface") or {}
    dOld = dPrevious.get("files") or {}
    if dPrevious.get("time"):
      for vPath, dFile in sorted(dResult["files"].items()):
        dBefore = dOld.get(vPath) or {}
        vSpecial = dFile["mode"] & (stat.S_ISUID | stat.S_ISGID)
        vNewSpecial = vSpecial & ~(dBefore.get("mode", 0) & (stat.S_ISUID | stat.S_ISGID))
        lNewCaps = [vName for vName in dFile.get("caps") or [] if vName not in (dBefore.get("caps") or [])]
        if vNewSpecial:
          vWhat = "setuid" if vNewSpecial & stat.S_ISUID else "setgid"
          if vNewSpecial & stat.S_ISUID and dFile["uid"] == 0 and fGtfobin(vPath):
            vKey = "new_setuid_gtfobins"
          elif cWritableFolderRegex.match(vPath):
            vKey = "new_setuid_writable_folder"
          else:
            vKey = "new_setuid"
          ldDetections.append(self.mModuleDetection(
            vKey, "new-setuid", vPath, f"Privilege escalation: new {vWhat} program {os.path.basename(vPath)}",
            f"{vPath} is now {vWhat} (mode {oct(dFile['mode'])}, owner uid {dFile['uid']}) and was not in the previous scan. An attacker who became root often leaves a setuid shell behind to come back; a package update can also add one. Check who created it (auditd: key lsiem_suid) and remove the bit if it is not expected.",
            {"file": vPath, "mode": oct(dFile["mode"]), "owner_uid": dFile["uid"], "gtfobins": fGtfobin(vPath)}
          ))
        if lNewCaps and set(lNewCaps) & sDangerousCapabilities:
          ldDetections.append(self.mModuleDetection(
            "new_capabilities", "new-capabilities", vPath, f"Privilege escalation: new capabilities on {os.path.basename(vPath)}",
            f"{vPath} has now the capabilities {', '.join(lNewCaps)}, which are root in practice (setcap). Check who set them and remove them if they are not expected (setcap -r {vPath}).",
            {"file": vPath, "capabilities": lNewCaps}
          ))
    dSaved = {
      "time": fEpochToStorage(dResult["time"]), "visited": dResult["visited"], "truncated": dResult["truncated"],
      "seconds": dResult["seconds"], "files": dResult["files"]
    }
    self.dRuntime["surface"] = dSaved
    self.vStorage.mSetState("privesc.surface", dSaved)
    return ldDetections

  # Web and manage.py

  def mSetupSnippet(self) -> str:
    from .setup import fBuildSnippet
    return fBuildSnippet()

  def mApplySetup(self) -> None:
    from .setup import fConfigurePrivesc
    from .discovery import fAuditLogPath
    fConfigurePrivesc(fAuditLogPath(self.mModuleSettings().get("audit_log", "")))

  def mRequirements(self) -> list[dict]:
    # auditd, bash or snoopy, checked again on every call (no storage: the
    # web and manage.py call it too). localSIEM 2.2.0 or newer installs the
    # module turned off while none of them is found.
    return fRequirementChecks()
