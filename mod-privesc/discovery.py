"""Discovery of the privesc module: what the server has and what to read.

The module reads only what the server already has: it never installs nor
configures anything (no audit rules, no hook, no format of snoopy). Two kinds
of sources, both read by the core tailer as the localsiem user:

  audit    the auditd log (/var/log/audit/audit.log, or the setting
           audit_log), with the rules the server already has: what it
           records (programs run, sudo, su and logins through PAM, changes of
           sensitive files, setuid bits, kernel modules...) depends on them.
           auditd cannot run inside a container (LXC, podman,
           systemd-nspawn): the audit of the kernel is not namespaced.
  syslog   auth.log (Debian with rsyslog), secure or messages (Alpine): sudo,
           su, pkexec and doas, and the commands logged by snoopy when it is
           installed. Read when auditd is not running, its log cannot be read
           or snoopy is installed (setting syslog_mode: auto), always or never.

Version 1.0.0 of the module installed audit rules and a bash hook with
--configure-privesc; both were removed in 1.1.0. fLegacyLeftovers lists the
files they left on the server, which the doctor only describes.

Nothing here needs root: the web and manage.py call it too.
"""

import grp
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

cAuditConfig = Path("/etc/audit/auditd.conf")
cDefaultAuditLog = "/var/log/audit/audit.log"
lSyslogCandidates = ["/var/log/auth.log", "/var/log/secure", "/var/log/messages"]
lSnoopyFiles = [
  "/etc/snoopy.ini", "/usr/lib/x86_64-linux-gnu/libsnoopy.so", "/usr/lib/aarch64-linux-gnu/libsnoopy.so",
  "/lib/x86_64-linux-gnu/libsnoopy.so", "/usr/lib/libsnoopy.so", "/usr/local/lib/libsnoopy.so", "/lib/libsnoopy.so"
]
# Files that --configure-privesc (version 1.0.0 of the module) left on the
# server. localSIEM no longer uses them and never deletes them: they are
# outside /opt/localsiem.
lLegacyPaths = [
  "/etc/localsiem-privesc", "/etc/profile.d/localsiem-privesc.sh", "/var/log/localsiem-privesc",
  "/etc/audit/rules.d/90-localsiem-privesc.rules"
]
lLegacyBashrcFiles = ["/etc/bash.bashrc", "/etc/bash/bashrc"]


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


def fReadState(pPath: str) -> str:
  # "readable", "unreadable" (it exists, or its folder cannot be entered, but
  # localsiem cannot open it) or "missing".
  if not pPath:
    return "missing"
  if fCanRead(pPath):
    return "readable"
  if os.path.exists(pPath):
    return "unreadable"
  vParent = os.path.dirname(pPath) or "/"
  if os.path.isdir(vParent) and not os.access(vParent, os.X_OK):
    return "unreadable"
  return "missing"


def fLegacyLeftovers() -> list[str]:
  # What an older version of the module (--configure-privesc, 1.0.0) left on
  # the server and localsiem can see: its files and the line it added to the
  # bashrc of the system. /etc/audit is often closed to localsiem: what it
  # cannot see is not listed.
  lFound = [vPath for vPath in lLegacyPaths if os.path.lexists(vPath)]
  for vBashrc in lLegacyBashrcFiles:
    try:
      if "localsiem-privesc" in Path(vBashrc).read_text(encoding="utf-8", errors="replace"):
        lFound.append(vBashrc)
    except OSError:
      continue
  return lFound


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


def fDiscoverSources(pSettings: dict, pAccounts: Accounts) -> tuple[list[dict], list[dict], dict]:
  # (sources, skipped, information for the doctor).
  dInfo = {
    "container": fContainer(), "auditd_binary": fAuditdBinary(), "auditd_pid": fAuditdPid(),
    "audit_log": fAuditLogPath(pSettings.get("audit_log", "")), "audit_state": "missing", "snoopy": fSnoopyInstalled(),
    "syslog": "", "syslog_path": "", "syslog_state": "missing", "syslog_mode": pSettings.get("syslog_mode") or "auto",
    "leftovers": fLegacyLeftovers()
  }
  ldSources = []
  ldSkipped = []
  vAudit = dInfo["audit_log"]
  dInfo["audit_state"] = fReadState(vAudit)
  if dInfo["audit_state"] == "readable" or (dInfo["audit_state"] == "unreadable" and dInfo["auditd_pid"]):
    # Also when auditd writes it and localsiem cannot read it yet: the core
    # reports it.
    ldSources.append({"key": "privesc:audit:" + os.path.realpath(vAudit), "path": vAudit, "kind": "audit", "format": "", "vhost": ""})
  elif dInfo["auditd_pid"]:
    ldSkipped.append({"path": vAudit, "kind": "audit", "reason": "missing"})
  vMode = dInfo["syslog_mode"]
  vSyslog = fSyslogPath(pSettings.get("syslog_file", ""))
  dInfo["syslog_path"] = vSyslog
  dInfo["syslog_state"] = fReadState(vSyslog)
  # auto: syslog is read when auditd cannot give the commands (not running,
  # in a container, or its log cannot be read) and when snoopy writes there.
  vAuditUsable = bool(dInfo["auditd_pid"]) and not dInfo["container"] and dInfo["audit_state"] == "readable"
  vRead = vMode == "always" or (vMode == "auto" and (not vAuditUsable or dInfo["snoopy"]))
  if vSyslog and vRead:
    dInfo["syslog"] = vSyslog
    ldSources.append({"key": "privesc:syslog:" + os.path.realpath(vSyslog), "path": vSyslog, "kind": "syslog", "format": "", "vhost": ""})
  elif vSyslog:
    ldSkipped.append({"path": vSyslog, "kind": "syslog", "reason": "auditd_running" if vMode == "auto" else "syslog_mode_never"})
  return ldSources, ldSkipped, dInfo
