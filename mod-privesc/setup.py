"""--configure-privesc, applied as root (manage.py setup-modules
--configure-privesc, through PrivescModule.mApplySetup).

It never installs software: it configures what the server already has.

  auditd (bare metal and virtual machines; never inside a container)
    /etc/audit/rules.d/90-localsiem-privesc.rules (fBuildAuditRules), loaded
    with augenrules; if loading fails, without the 32-bit rules, and if it
    still fails, the previous file comes back. log_group = adm in
    auditd.conf, so the logs auditd creates when it rotates them stay
    readable (with log_group = root they are created 600 and the ACL of
    localsiem stops working); localsiem joins adm on Alpine (on Debian
    manage.py already does it).
  bash hook (everywhere)
    /etc/localsiem-privesc/hook.bash, /etc/profile.d/localsiem-privesc.sh and
    one line in the bashrc of the system; the folder
    /var/log/localsiem-privesc (root:localsiem, 3753: every user creates their
    own file, nobody lists or deletes the files of the others) with a file
    for root and each person.
  snoopy (if installed)
    message_format of /etc/snoopy.ini with the effective uid and the parent.

Running it again is safe: every file is rewritten with the same content.
"""

import grp
import os
import platform
import shutil
import signal
import subprocess
from pathlib import Path

from backend.core.timeutil import fNowStorage
from .discovery import (
  Accounts, cAuditConfig, cHookDir, cHookFile, cHookInstallDir, cProfileFile, cRulesFile, cSetupMarker,
  fAuditdBinary, fAuditdPid, fContainer, lBashrcFiles
)

cModulePath = Path(__file__).resolve().parent
cBashrcMarker = "# localSIEM privesc: command hook (manage.py setup-modules --configure-privesc)"
cBashrcLine = "if [ -r /etc/localsiem-privesc/hook.bash ]; then . /etc/localsiem-privesc/hook.bash; fi"
cSnoopyFormat = "message_format = \"[login:%{login} uid:%{uid} euid:%{euid} pid:%{pid} ppid:%{ppid} sid:%{sid} tty:%{tty} cwd:%{cwd} filename:%{filename}]: %{cmdline}\""
lServicePrograms = [
  "sh", "bash", "dash", "zsh", "ksh", "mksh", "busybox", "python3", "python", "perl", "ruby", "php", "node", "lua",
  "socat", "nc", "ncat", "netcat", "curl", "wget", "whoami", "id", "uname", "hostname", "gcc", "cc", "script"
]
lWatches = [
  ("/etc/passwd", "lsiem_auth"), ("/etc/shadow", "lsiem_auth"), ("/etc/group", "lsiem_auth"), ("/etc/gshadow", "lsiem_auth"),
  ("/etc/sudoers", "lsiem_auth"), ("/etc/sudoers.d", "lsiem_auth"), ("/etc/doas.conf", "lsiem_auth"), ("/etc/doas.d", "lsiem_auth"),
  ("/etc/ld.so.preload", "lsiem_preload"), ("/etc/ld.so.conf", "lsiem_preload"), ("/etc/ld.so.conf.d", "lsiem_preload"),
  ("/etc/pam.d", "lsiem_pam"), ("/etc/security", "lsiem_pam"),
  ("/root/.ssh", "lsiem_ssh"), ("/etc/ssh/sshd_config", "lsiem_ssh"), ("/etc/ssh/sshd_config.d", "lsiem_ssh"),
  ("/etc/crontab", "lsiem_cron"), ("/etc/cron.d", "lsiem_cron"), ("/etc/cron.hourly", "lsiem_cron"), ("/etc/cron.daily", "lsiem_cron"),
  ("/etc/cron.weekly", "lsiem_cron"), ("/etc/cron.monthly", "lsiem_cron"), ("/var/spool/cron", "lsiem_cron"), ("/etc/periodic", "lsiem_cron"),
  ("/etc/systemd/system", "lsiem_service_unit"), ("/etc/init.d", "lsiem_service_unit"), ("/etc/rc.local", "lsiem_service_unit"), ("/etc/local.d", "lsiem_service_unit"),
  ("/etc/audit", "lsiem_audit_config"),
  ("/etc/localsiem-privesc", "lsiem_hook"), ("/etc/profile.d/localsiem-privesc.sh", "lsiem_hook"), ("/etc/bash.bashrc", "lsiem_hook"),
  ("/etc/bash/bashrc", "lsiem_hook"), ("/etc/snoopy.ini", "lsiem_hook")
]


def fRun(pCommand: list[str]) -> subprocess.CompletedProcess:
  return subprocess.run(pCommand, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def fFindProgram(pName: str) -> str:
  # Real path of a program, as auditd sees it (exe=): /bin/sh is /usr/bin/dash
  # on Debian and /bin/busybox on Alpine.
  vPath = shutil.which(pName, path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
  return os.path.realpath(vPath) if vPath else ""


def fSyscallSets(pMachine: str) -> list[dict]:
  # The architectures of the rules and the names of their system calls: the
  # 64-bit architectures without the old calls (aarch64, riscv64, loongarch64)
  # have no open nor chmod.
  dFull = {
    "exec": "execve,execveat", "chmod": [("chmod,fchmod", "a1"), ("fchmodat", "a2")], "open": "open,openat,openat2",
    "kmod": "init_module,finit_module,delete_module"
  }
  dReduced = {
    "exec": "execve,execveat", "chmod": [("fchmod", "a1"), ("fchmodat", "a2")], "open": "openat,openat2",
    "kmod": "init_module,finit_module,delete_module"
  }
  if pMachine in ("x86_64", "amd64"):
    return [dict(dFull, arch="b64"), dict(dFull, arch="b32", optional=True)]
  if pMachine in ("aarch64", "arm64", "riscv64", "loongarch64"):
    return [dict(dReduced, arch="b64")]
  if pMachine in ("ppc64le", "ppc64", "s390x", "mips64"):
    return [dict(dFull, arch="b64")]
  return [dict(dFull, arch="b32")]


def fBuildAuditRules(pWith32: bool = True) -> str:
  vAccounts = Accounts()
  vUidMin = vAccounts.vUidMin
  vLocalsiem = vAccounts.mUid("localsiem")
  lLines = [
    "## localSIEM privesc module: rules of auditd (" + cSetupMarker + ").",
    "## Written by manage.py setup-modules --configure-privesc, which rewrites",
    "## this file every time it runs: do not edit it, add your own rules to",
    "## another file of /etc/audit/rules.d.",
    ""
  ]
  lPrograms = []
  for vName in lServicePrograms:
    vPath = fFindProgram(vName)
    if vPath and vPath not in lPrograms:
      lPrograms.append(vPath)
  for dSet in fSyscallSets(platform.machine()):
    if dSet.get("optional") and not pWith32:
      continue
    vArch = dSet["arch"]
    lLines.append(f"## Architecture {vArch}")
    lLines.append("# Programs run with the effective uid of root by someone who is not root (setuid).")
    lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['exec']} -F euid=0 -F uid!=0 -k lsiem_euid")
    lLines.append("# Every program run by a person (login uid of a person).")
    lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['exec']} -F auid>={vUidMin} -F auid!=unset -k lsiem_exec")
    lLines.append("# Shells, interpreters and tools run by service accounts (a web shell).")
    for vPath in lPrograms:
      vExclude = f" -F uid!={vLocalsiem}" if vLocalsiem is not None else ""
      lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['exec']} -F uid>0 -F uid<{vUidMin}{vExclude} -F auid=unset -F exe={vPath} -k lsiem_service")
    lLines.append("# Setuid or setgid bit set on a file.")
    for vCalls, vArgument in dSet["chmod"]:
      lLines.append(f"-a always,exit -F arch={vArch} -S {vCalls} -F {vArgument}&0xc00 -k lsiem_suid")
    lLines.append("# Kernel modules loaded or removed.")
    lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['kmod']} -k lsiem_kmod")
    lLines.append("# Processes attached with ptrace (PTRACE_ATTACH, PTRACE_SEIZE).")
    lLines.append(f"-a always,exit -F arch={vArch} -S ptrace -F a0=0x10 -k lsiem_ptrace")
    lLines.append(f"-a always,exit -F arch={vArch} -S ptrace -F a0=0x4206 -k lsiem_ptrace")
    lLines.append("# Files refused to a person (enumeration).")
    lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['open']} -F exit=-EACCES -F auid>={vUidMin} -F auid!=unset -k lsiem_denied")
    lLines.append(f"-a always,exit -F arch={vArch} -S {dSet['open']} -F exit=-EPERM -F auid>={vUidMin} -F auid!=unset -k lsiem_denied")
    lLines.append("")
  lLines.append("## Accounts, sudo, preload, PAM, SSH, cron, services, auditd and the hook of localSIEM.")
  for vPath, vKey in lWatches:
    if os.path.exists(vPath):
      lLines.append(f"-w {vPath} -p wa -k {vKey}")
  lLines.append("")
  return "\n".join(lLines)


def fLoadAuditRules() -> subprocess.CompletedProcess:
  vAugenrules = fFindProgram("augenrules")
  if vAugenrules:
    return fRun([vAugenrules, "--load"])
  return fRun([fFindProgram("auditctl") or "auditctl", "-R", str(cRulesFile)])


def fSetLogGroup() -> bool:
  # log_group = adm in auditd.conf. Returns True when the file changed.
  if not cAuditConfig.is_file():
    return False
  try:
    grp.getgrnam("adm")
  except KeyError:
    print("Warning: the group adm does not exist: log_group of auditd.conf left as it is.")
    return False
  vText = cAuditConfig.read_text(encoding="utf-8")
  lLines = vText.splitlines()
  vFound = False
  vChanged = False
  for vIndex, vLine in enumerate(lLines):
    vStripped = vLine.strip()
    if vStripped.startswith("log_group") and "=" in vStripped:
      vFound = True
      if vStripped.split("=", 1)[1].strip() != "adm":
        lLines[vIndex] = "log_group = adm"
        vChanged = True
  if not vFound:
    lLines.append("log_group = adm")
    vChanged = True
  if vChanged:
    vMode = cAuditConfig.stat().st_mode & 0o777
    cAuditConfig.write_text("\n".join(lLines) + "\n", encoding="utf-8")
    cAuditConfig.chmod(vMode)
  return vChanged


def fFixAuditLogPermissions(pAuditLog: str) -> None:
  # The logs that already exist, as auditd creates them with log_group = adm.
  vFolder = Path(pAuditLog).parent
  try:
    vGid = grp.getgrnam("adm").gr_gid
  except KeyError:
    return
  if vFolder.is_dir():
    os.chown(vFolder, 0, vGid)
    vFolder.chmod(0o750)
    for vFile in vFolder.iterdir():
      if vFile.is_file() and vFile.name.startswith(Path(pAuditLog).name):
        os.chown(vFile, 0, vGid)
        vFile.chmod(0o640)


def fConfigureAuditd(pAuditLog: str) -> None:
  if not fAuditdBinary():
    print("auditd is not installed: its rules were skipped (the bash hook and syslog are used).")
    return
  vContainer = fContainer()
  if vContainer:
    print(f"This server is a container ({vContainer}): auditd cannot run inside it, its rules were skipped. Run auditd on the host.")
    return
  if os.path.exists("/etc/alpine-release"):
    try:
      if "localsiem" not in grp.getgrnam("adm").gr_mem:
        fRun(["addgroup", "localsiem", "adm"])
    except KeyError:
      pass
  vPrevious = cRulesFile.read_text(encoding="utf-8") if cRulesFile.exists() else None
  cRulesFile.parent.mkdir(parents=True, exist_ok=True)
  # A watch needs its path: /root/.ssh is created (empty, 700) so that an
  # authorized_keys added later is seen.
  if os.path.isdir("/root") and not os.path.exists("/root/.ssh"):
    os.mkdir("/root/.ssh", 0o700)
  vResult = None
  for vWith32 in (True, False):
    cRulesFile.write_text(fBuildAuditRules(vWith32), encoding="utf-8")
    cRulesFile.chmod(0o640)
    vResult = fLoadAuditRules()
    vOutput = (vResult.stdout + vResult.stderr).strip()
    if "immutable" in vOutput.lower():
      print(f"auditd rules written to {cRulesFile}; the audit system is immutable (-e 2): they are loaded at the next reboot.")
      break
    if vResult.returncode == 0:
      print(f"auditd rules loaded ({cRulesFile})" + ("" if vWith32 else ", without the 32-bit rules (the kernel does not support them)") + ".")
      break
  else:
    if vPrevious is None:
      cRulesFile.unlink(missing_ok=True)
    else:
      cRulesFile.write_text(vPrevious, encoding="utf-8")
    fLoadAuditRules()
    print("Warning: auditd did not accept the rules of localSIEM; the previous rules were restored:")
    print(((vResult.stdout + vResult.stderr) if vResult else "").strip()[:2000])
  if fSetLogGroup():
    vPid = fAuditdPid()
    if vPid:
      try:
        os.kill(vPid, signal.SIGHUP)
      except OSError as vError:
        print(f"Warning: auditd could not be told to read auditd.conf again: {vError}")
    print("auditd.conf: log_group = adm (the rotated logs stay readable by localSIEM).")
  fFixAuditLogPermissions(pAuditLog)


def fInstallHook(pAccounts: Accounts) -> None:
  try:
    vLocalsiemGid = grp.getgrnam("localsiem").gr_gid
  except KeyError:
    print("Warning: the group localsiem does not exist: the bash hook was not installed.")
    return
  cHookInstallDir.mkdir(mode=0o755, exist_ok=True)
  cHookInstallDir.chmod(0o755)
  shutil.copyfile(cModulePath / "hook" / "hook.bash", cHookFile)
  cHookFile.chmod(0o644)
  cProfileFile.parent.mkdir(parents=True, exist_ok=True)
  shutil.copyfile(cModulePath / "hook" / "profile.sh", cProfileFile)
  cProfileFile.chmod(0o644)
  for vBashrc in lBashrcFiles:
    vPath = Path(vBashrc)
    if not vPath.is_file():
      continue
    vText = vPath.read_text(encoding="utf-8", errors="replace")
    if cBashrcMarker not in vText:
      with vPath.open("a", encoding="utf-8") as vFile:
        vFile.write(("" if vText.endswith("\n") or not vText else "\n") + "\n" + cBashrcMarker + "\n" + cBashrcLine + "\n")
  # The folder: root:localsiem, setgid (the files are of the group
  # localsiem), sticky (nobody deletes the files of the others), others can
  # create (-wx) but not list. Without ACLs, so the umask of the hook decides
  # the mode of each file (640).
  cHookDir.mkdir(exist_ok=True)
  os.chown(cHookDir, 0, vLocalsiemGid)
  cHookDir.chmod(0o3753)
  vSetfacl = fFindProgram("setfacl")
  if vSetfacl:
    fRun([vSetfacl, "-b", str(cHookDir)])
  for vUid in pAccounts.mPeople():
    vFile = cHookDir / f"{vUid}.log"
    if vFile.exists() or vFile.is_symlink():
      vStat = os.lstat(vFile)
      if vStat.st_uid == vUid and not vFile.is_symlink():
        continue
      vAside = cHookDir / f"{vUid}.log.wrong-owner-{fNowStorage()}"
      os.rename(vFile, vAside)
      os.chown(vAside, 0, 0, follow_symlinks=False)
      print(f"Warning: {vFile} belonged to uid {vStat.st_uid}, not to {vUid}: moved to {vAside}.")
    vFile.touch(mode=0o640)
    os.chown(vFile, vUid, vLocalsiemGid)
    vFile.chmod(0o640)
  print(f"bash hook installed ({cHookFile}, {cProfileFile}); commands are written to {cHookDir}/<uid>.log.")


def fConfigureSnoopy() -> None:
  vIni = Path("/etc/snoopy.ini")
  if not vIni.is_file():
    return
  lLines = vIni.read_text(encoding="utf-8", errors="replace").splitlines()
  lOut = []
  vSection = ""
  vDone = False
  for vLine in lLines:
    vStripped = vLine.strip()
    if vStripped.startswith("[") and vStripped.endswith("]"):
      if vSection == "snoopy" and not vDone:
        lOut.extend(["; " + cSetupMarker, cSnoopyFormat])
        vDone = True
      vSection = vStripped[1:-1].strip().lower()
    if vSection == "snoopy" and (vStripped.startswith("message_format") or vStripped == "; " + cSetupMarker):
      if not vDone:
        lOut.extend(["; " + cSetupMarker, cSnoopyFormat])
        vDone = True
      continue
    lOut.append(vLine)
  if not vDone:
    if vSection != "snoopy":
      lOut.append("[snoopy]")
    lOut.extend(["; " + cSetupMarker, cSnoopyFormat])
  vIni.write_text("\n".join(lOut) + "\n", encoding="utf-8")
  print("snoopy: message_format with the effective uid and the parent process.")


def fConfigurePrivesc(pAuditLog: str) -> None:
  if os.geteuid() != 0:
    raise ValueError("--configure-privesc changes the configuration of the system: run it as root.")
  vAccounts = Accounts()
  fConfigureAuditd(pAuditLog)
  fInstallHook(vAccounts)
  fConfigureSnoopy()


def fBuildSnippet() -> str:
  return fBuildAuditRules(True)
