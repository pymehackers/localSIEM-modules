"""Discovery of the privesc module: what the server has and what to read.

Three kinds of sources, all read by the core tailer as the localsiem user:

  audit    the auditd log (/var/log/audit/audit.log, or the setting
           audit_log): every command of the people, setuid programs, sudo,
           su and logins (PAM), changes of sensitive files, kernel modules.
           auditd cannot run inside a container (LXC, podman,
           systemd-nspawn): the audit of the kernel is not namespaced.
  hook     /var/log/localsiem-privesc/<uid>.log, one file per user, written
           by the hook of the interactive bash shells (builtins included).
           It works everywhere, containers included, but it can be evaded.
  syslog   auth.log (Debian with rsyslog) or messages (Alpine): sudo, su,
           pkexec and doas, and the commands logged by snoopy when it is
           installed. Read when auditd is not running or snoopy is installed
           (setting syslog_mode: auto), always or never.

Nothing here needs root: the web and manage.py call it too.
"""

import grp
import os
import pwd
import re
import shutil
import stat
import subprocess
from pathlib import Path

cHookDir = Path("/var/log/localsiem-privesc")
cHookInstallDir = Path("/etc/localsiem-privesc")
cHookFile = cHookInstallDir / "hook.bash"
cProfileFile = Path("/etc/profile.d/localsiem-privesc.sh")
cRulesFile = Path("/etc/audit/rules.d/90-localsiem-privesc.rules")
cAuditConfig = Path("/etc/audit/auditd.conf")
cDefaultAuditLog = "/var/log/audit/audit.log"
lBashrcFiles = ["/etc/bash.bashrc", "/etc/bash/bashrc"]
lSyslogCandidates = ["/var/log/auth.log", "/var/log/secure", "/var/log/messages"]
lSnoopyFiles = [
  "/etc/snoopy.ini", "/usr/lib/x86_64-linux-gnu/libsnoopy.so", "/usr/lib/aarch64-linux-gnu/libsnoopy.so",
  "/lib/x86_64-linux-gnu/libsnoopy.so", "/usr/lib/libsnoopy.so", "/usr/local/lib/libsnoopy.so", "/lib/libsnoopy.so"
]
cHookNameRegex = re.compile(r"^(\d{1,10})\.log$")
# Marker of the files the setup writes: the doctor compares it with the
# version of the module to tell when the setup must be applied again.
cSetupVersion = "1"
cSetupMarker = "localsiem-privesc-setup " + cSetupVersion


def fFlavor() -> str:
  return "alpine" if os.path.exists("/etc/alpine-release") else "debian"


def fContainer() -> str:
  # The kind of container the server runs in, or "" (bare metal or a virtual
  # machine). Read as an unprivileged user: /proc/1/environ is not readable.
  try:
    vName = Path("/run/systemd/container").read_text(encoding="utf-8").strip()
    if vName:
      return vName
  except OSError:
    pass
  if os.path.exists("/run/.containerenv"):
    return "podman"
  if os.path.exists("/.dockerenv"):
    return "docker"
  try:
    vCgroup = Path("/proc/self/cgroup").read_text(encoding="utf-8", errors="replace")
    if "/lxc/" in vCgroup or "lxc.payload" in vCgroup:
      return "lxc"
    if "/docker/" in vCgroup:
      return "docker"
    if "machine.slice/systemd-nspawn" in vCgroup:
      return "systemd-nspawn"
  except OSError:
    pass
  vDetect = shutil.which("systemd-detect-virt")
  if vDetect:
    try:
      vResult = subprocess.run([vDetect, "--container"], capture_output=True, text=True, timeout=3, stdin=subprocess.DEVNULL)
      vName = vResult.stdout.strip()
      if vResult.returncode == 0 and vName and vName != "none":
        return vName
    except (OSError, subprocess.SubprocessError):
      pass
  return ""


def fAuditdBinary() -> str:
  for vPath in ("/sbin/auditd", "/usr/sbin/auditd", "/usr/bin/auditd"):
    if os.path.exists(vPath):
      return vPath
  return ""


def fAuditdPid() -> int | None:
  # The pid of a running auditd, from its pid file or, without it, from /proc.
  for vFile in ("/run/auditd.pid", "/var/run/auditd.pid"):
    try:
      vPid = int(Path(vFile).read_text(encoding="utf-8").strip())
      if Path(f"/proc/{vPid}/comm").read_text(encoding="utf-8").strip() == "auditd":
        return vPid
    except (OSError, ValueError):
      continue
  try:
    for vEntry in os.scandir("/proc"):
      if vEntry.name.isdigit():
        try:
          if Path(vEntry.path, "comm").read_text(encoding="utf-8").strip() == "auditd":
            return int(vEntry.name)
        except OSError:
          continue
  except OSError:
    pass
  return None


def fAuditLogPath(pSetting: str = "") -> str:
  # The setting, else log_file of auditd.conf (usually readable by root only),
  # else the default of auditd.
  if pSetting:
    return pSetting
  try:
    for vLine in cAuditConfig.read_text(encoding="utf-8").splitlines():
      vMatch = re.match(r"^\s*log_file\s*=\s*(\S+)\s*$", vLine)
      if vMatch:
        return vMatch.group(1)
  except OSError:
    pass
  return cDefaultAuditLog


def fBashPath() -> str:
  for vPath in ("/bin/bash", "/usr/bin/bash"):
    if os.path.exists(vPath):
      return vPath
  return ""


def fSnoopyInstalled() -> bool:
  if any(os.path.exists(vPath) for vPath in lSnoopyFiles):
    return True
  try:
    return "snoopy" in Path("/etc/ld.so.preload").read_text(encoding="utf-8", errors="replace")
  except OSError:
    return False


def fSyslogPath(pSetting: str = "") -> str:
  if pSetting:
    return pSetting
  for vPath in lSyslogCandidates:
    if os.path.isfile(vPath):
      return vPath
  return ""


def fCanRead(pPath: str) -> bool:
  try:
    with open(pPath, "rb") as vFile:
      vFile.read(1)
    return True
  except OSError:
    return False


def fFileMarker(pPath) -> str:
  # The setup marker of a file written by --configure-privesc, or "".
  try:
    with open(pPath, "r", encoding="utf-8", errors="replace") as vFile:
      for vLine in vFile.readlines()[:40]:
        vMatch = re.search(r"localsiem-privesc-setup (\S+)", vLine)
        if vMatch:
          return vMatch.group(1)
  except OSError:
    pass
  return ""


class Accounts:
  # Users and groups of /etc/passwd and /etc/group, read again when they
  # change: names, kind of account and the members of the admin groups.

  def __init__(self):
    self.vSignature = None
    self.dNames = {}
    self.dByName = {}
    self.dShells = {}
    self.dPrimaryGids = {}
    self.dGroups = {}
    self.dTypes = {}
    self.vUidMin = 1000
    self.mLoad()

  def mLoad(self) -> None:
    try:
      vSignature = (os.stat("/etc/passwd").st_mtime, os.stat("/etc/group").st_mtime)
    except OSError:
      vSignature = None
    if vSignature is not None and vSignature == self.vSignature:
      return
    self.vSignature = vSignature
    self.dTypes = {}
    self.dNames = {}
    self.dByName = {}
    self.dShells = {}
    self.dPrimaryGids = {}
    self.dGroups = {}
    try:
      for vEntry in pwd.getpwall():
        self.dNames[vEntry.pw_uid] = vEntry.pw_name
        self.dByName[vEntry.pw_name] = vEntry.pw_uid
        self.dShells[vEntry.pw_uid] = vEntry.pw_shell
        self.dPrimaryGids[vEntry.pw_uid] = vEntry.pw_gid
    except OSError:
      pass
    try:
      for vEntry in grp.getgrall():
        self.dGroups[vEntry.gr_name] = {"gid": vEntry.gr_gid, "members": list(vEntry.gr_mem)}
    except OSError:
      pass
    try:
      for vLine in Path("/etc/login.defs").read_text(encoding="utf-8", errors="replace").splitlines():
        vMatch = re.match(r"^\s*UID_MIN\s+(\d+)", vLine)
        if vMatch:
          self.vUidMin = int(vMatch.group(1))
    except OSError:
      pass

  def mName(self, pUid) -> str:
    try:
      vUid = int(pUid)
    except (TypeError, ValueError):
      return ""
    if vUid in (-1, 4294967295):
      return ""
    return self.dNames.get(vUid, str(vUid))

  def mUid(self, pName: str) -> int | None:
    return self.dByName.get(pName)

  def mGroupMembers(self, pGroup: str) -> list[str]:
    dGroup = self.dGroups.get(pGroup)
    if dGroup is None:
      return []
    lMembers = list(dGroup["members"])
    for vUid, vGid in self.dPrimaryGids.items():
      if vGid == dGroup["gid"] and self.dNames.get(vUid) not in lMembers:
        lMembers.append(self.dNames.get(vUid, str(vUid)))
    return lMembers

  def mIsAdmin(self, pUid: int, pAdminGroups: list[str]) -> bool:
    vName = self.mName(pUid)
    return any(vName in self.mGroupMembers(vGroup) for vGroup in pAdminGroups)

  def mAccountType(self, pUid, pAdminGroups: list[str]) -> str:
    # root, admin (member of an admin group), user (a person) or service.
    # Kept per uid until passwd or group change (every event asks).
    try:
      vUid = int(pUid)
    except (TypeError, ValueError):
      return ""
    vCacheKey = (vUid, tuple(pAdminGroups))
    if vCacheKey not in self.dTypes:
      self.dTypes[vCacheKey] = self.mFindAccountType(vUid, pAdminGroups)
    return self.dTypes[vCacheKey]

  def mFindAccountType(self, pUid: int, pAdminGroups: list[str]) -> str:
    if pUid == 0:
      return "root"
    if pUid in (-1, 4294967295):
      return ""
    if self.mIsAdmin(pUid, pAdminGroups):
      return "admin"
    vShell = self.dShells.get(pUid, "")
    if pUid >= self.vUidMin and pUid != 65534 and not vShell.endswith(("nologin", "false")):
      return "user"
    return "service"

  def mPeople(self) -> list[int]:
    # root and the accounts of people: the hook files the setup creates.
    lUids = [0]
    for vUid, vShell in self.dShells.items():
      if vUid >= self.vUidMin and vUid != 65534 and not vShell.endswith(("nologin", "false")):
        lUids.append(vUid)
    return sorted(set(lUids))


def fHookSources(pAccounts: Accounts) -> tuple[list[dict], list[dict]]:
  # One source per file of the hook folder. A file whose owner is not the
  # user of its name, or that localsiem cannot read, is reported (someone
  # created it in the place of another user, or hid their own commands).
  ldSources = []
  ldProblems = []
  if not cHookDir.is_dir():
    return ldSources, ldProblems
  try:
    lEntries = sorted(os.scandir(cHookDir), key=lambda vEntry: vEntry.name)
  except OSError as vError:
    ldProblems.append({"path": str(cHookDir), "problem": "unreadable_folder", "detail": str(vError)})
    return ldSources, ldProblems
  for vEntry in lEntries:
    vMatch = cHookNameRegex.match(vEntry.name)
    if not vMatch:
      continue
    try:
      vStat = os.lstat(vEntry.path)
    except OSError:
      continue
    vUid = int(vMatch.group(1))
    if not stat.S_ISREG(vStat.st_mode):
      ldProblems.append({"path": vEntry.path, "problem": "not_a_file", "uid": vUid, "owner": vStat.st_uid})
      continue
    if vStat.st_uid != vUid:
      ldProblems.append({"path": vEntry.path, "problem": "wrong_owner", "uid": vUid, "owner": vStat.st_uid, "user": pAccounts.mName(vUid), "owner_name": pAccounts.mName(vStat.st_uid)})
      continue
    if not fCanRead(vEntry.path) and vStat.st_size > 0:
      ldProblems.append({"path": vEntry.path, "problem": "unreadable", "uid": vUid, "user": pAccounts.mName(vUid), "mode": oct(stat.S_IMODE(vStat.st_mode))})
      continue
    ldSources.append({
      "key": "privesc:hook:" + vEntry.path, "path": vEntry.path, "kind": "hook", "format": "", "vhost": "",
      "owner_uid": vUid, "owner": pAccounts.mName(vUid)
    })
  return ldSources, ldProblems


def fDiscoverSources(pSettings: dict, pAccounts: Accounts) -> tuple[list[dict], list[dict], dict]:
  # (sources, skipped, information for the doctor).
  dInfo = {
    "container": fContainer(), "auditd_binary": fAuditdBinary(), "auditd_pid": fAuditdPid(),
    "audit_log": fAuditLogPath(pSettings.get("audit_log", "")), "snoopy": fSnoopyInstalled(),
    "bash": fBashPath(), "syslog": "", "hook_problems": []
  }
  ldSources = []
  ldSkipped = []
  vAudit = dInfo["audit_log"]
  if os.path.isfile(vAudit):
    ldSources.append({"key": "privesc:audit:" + os.path.realpath(vAudit), "path": vAudit, "kind": "audit", "format": "", "vhost": ""})
  elif dInfo["auditd_pid"]:
    ldSkipped.append({"path": vAudit, "kind": "audit", "reason": "missing"})
  ldHooks, dInfo["hook_problems"] = fHookSources(pAccounts)
  ldSources.extend(ldHooks)
  vMode = pSettings.get("syslog_mode") or "auto"
  vSyslog = fSyslogPath(pSettings.get("syslog_file", ""))
  vRead = vMode == "always" or (vMode == "auto" and (not dInfo["auditd_pid"] or dInfo["snoopy"]))
  if vSyslog and vRead:
    dInfo["syslog"] = vSyslog
    ldSources.append({"key": "privesc:syslog:" + os.path.realpath(vSyslog), "path": vSyslog, "kind": "syslog", "format": "", "vhost": ""})
  elif vSyslog:
    ldSkipped.append({"path": vSyslog, "kind": "syslog", "reason": "auditd_running" if vMode == "auto" else "syslog_mode_never"})
  return ldSources, ldSkipped, dInfo
