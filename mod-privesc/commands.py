"""Commands and sessions of the privesc module.

What a command means for an escalation, whatever the source that saw it
(auditd, the bash hook or snoopy):

  fReconToken      the reconnaissance it does, as a token (whoami,
                   read:/etc/passwd, find:-perm, sudo:list...), or "". The
                   rules count the distinct tokens of a session in a window:
                   a person runs a few, linpeas runs hundreds in seconds.
  fProgramKey      what a service account runs (sh -c id, python3 -c...): the
                   history of each account says whether it is new.
  fCommandArgs     the words of a command typed in a shell.

SessionTracker keeps, in memory and in the state of the database
(privesc.sessions), what each session did: who started it and from where,
whether it went through sudo, su, pkexec or doas (a «door»), its
reconnaissance tokens, its last commands, and the programs recently run (pid,
for the parent of a process).
"""

import collections
import os
import re
import shlex

from backend.core.timeutil import fEpochToStorage, fStorageToEpoch

sShells = {"sh", "bash", "dash", "zsh", "ksh", "mksh", "ash", "busybox", "fish", "tcsh", "csh", "rbash"}
cInterpreterRegex = re.compile(r"^(python[0-9.]*|perl[0-9.]*|ruby[0-9.]*|php[0-9.]*|php-cgi|node|nodejs|lua[0-9.]*|luajit|tclsh[0-9.]*|wish|expect|gawk|mawk|nawk|awk|jrunscript|jjs|irb|pwsh|rlwrap|gdb|socat)$")
# By the name the program was called with (argv[0]): on Alpine wget and sh are
# both /bin/busybox.
sDownloaders = {"curl", "wget", "fetch", "tftp", "ftp", "lftp", "aria2c", "axel", "nc", "ncat", "netcat"}
# Programs through which a person becomes root on purpose.
sDoors = {"sudo", "sudo-rs", "su", "su-rs", "pkexec", "doas", "run0", "runuser", "systemd", "systemd-executor", "sudoedit", "login", "sshd", "sshd-session"}
# Parents of a root shell that are a legitimate way in (hook).
sDoorParents = {
  "su", "sudo", "sudo-rs", "doas", "pkexec", "run0", "runuser", "login", "sshd", "sshd-session", "systemd", "init",
  "agetty", "getty", "lxc-attach", "nsenter", "machinectl", "systemd-nspawn", "conmon", "runc", "crun", "docker-init",
  "tini", "dumb-init", "tmux: server", "tmux", "screen", "SCREEN", "cron", "crond", "mc", "script", "su-rs", "lxc-start",
  "containerd-shim", "pct", "vzctl", "ttyd", "shellinaboxd", "cockpit-bridge", "cockpit-session", "webmin", "xterm",
  "gnome-terminal-", "konsole", "kitty", "alacritty", "terminator", "sshpass", "expect", "dropbear"
}
sReconSimple = {
  "whoami", "id", "groups", "uname", "hostname", "hostnamectl", "lsb_release", "w", "who", "last", "lastlog", "lastb",
  "users", "finger", "ps", "pstree", "netstat", "ss", "ifconfig", "route", "arp", "env", "printenv", "lsmod", "lscpu",
  "lsblk", "lspci", "lsusb", "uptime", "dmesg", "getcap", "pwd", "loginctl", "aa-status", "sestatus", "getenforce",
  "arp-scan", "lsof", "lsattr", "df", "history", "umask", "ulimit", "nproc", "arch", "timedatectl",
  "systemd-detect-virt", "virt-what", "dmidecode", "capsh", "free", "lslogins", "lsns", "showmount", "iptables-save"
}
sReaders = {"cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "strings", "awk", "sed", "nl", "tac", "od", "xxd", "base64", "vi", "vim", "nano", "view", "file", "stat", "bat", "batcat"}
cSensitiveFileRegex = re.compile(
  r"^(/etc/(passwd|group|shadow|gshadow|sudoers|crontab|os-release|issue|hostname|hosts|resolv\.conf|fstab|exports|"
  r"lsb-release|[\w.-]*-release|ssh/\S*|security/\S*|sudoers\.d\S*|cron\S*|profile|bash\.bashrc|environment|ld\.so\.preload|"
  r"ld\.so\.conf\S*|doas\.conf|polkit-1/\S*|apache2/\S*|nginx/\S*|mysql/\S*|php/\S*|exports|motd)|"
  r"/proc/(version|cpuinfo|mounts|net/\S+|sys/kernel/\S+|self/\S+|1/\S+)|/root(/|$)|/var/log/(auth\.log|secure|messages|syslog|audit)\S*|"
  r"/var/backups\S*|/var/mail\S*|/var/spool/(cron|mail)\S*)"
)
cCredentialFileRegex = re.compile(r"(\.bash_history|\.zsh_history|\.mysql_history|\.psql_history|\.viminfo|/\.ssh/|id_rsa|id_ecdsa|id_ed25519|\.env$|wp-config\.php$|config\.php$|settings\.py$|\.git-credentials$|\.pgpass$|\.my\.cnf$|\.netrc$|\.aws/|\.kube/|\.docker/config\.json$|credentials)")
cSensitiveDirRegex = re.compile(r"^(/root|/home|/etc/(sudoers\.d|cron\S*|systemd|init\.d|polkit-1)|/var/spool/cron|/opt|/tmp|/dev/shm|/var/tmp|/var/backups|/var/mail|/mnt|/media|/srv|/var/www|/etc|/usr/local/bin|/usr/local/sbin)(/|$)")
cSecretWordsRegex = re.compile(r"(?i)pass|pwd|secret|token|key|credential|auth")
cAssignmentRegex = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# A download run by a shell in one line: curl ... | sh, bash -c "$(curl ...)",
# bash <(wget ...), python -c "...urlopen...exec".
cDownloadOnelinerRegex = re.compile(
  r"(?i)\b(curl|wget|fetch)\b[^|;&]*\|\s*(sudo\s+)?(\S*/)?(ba|da|z|k|a)?sh\b|\$\(\s*(curl|wget|fetch)\b|<\(\s*(curl|wget|fetch)\b|"
  r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(\S*/)?(python[0-9.]*|perl|ruby|php)\b|urlopen\(.*\)\.read\(\).*\bexec\b"
)
cCompilerRegex = re.compile(r"^(gcc|cc|clang|tcc|g\+\+|c\+\+|musl-gcc|[\w.-]*-gcc(-[0-9.]+)?|gcc-[0-9.]+|clang-[0-9.]+|go|rustc|make|nasm|as)$")
cTemporaryFolderRegex = re.compile(r"^/(tmp|var/tmp|dev/shm|run/shm|run/user/\d+)(/|$)")
cMaxRecent = 30


def fCompileInTemporary(pArgs: list[str], pCwd: str) -> bool:
  # A compiler (or make) run in a temporary folder or on files of one: an
  # exploit downloaded and built on the spot.
  if not pArgs or not cCompilerRegex.match(os.path.basename(str(pArgs[0]))):
    return False
  if cTemporaryFolderRegex.match(str(pCwd or "")):
    return True
  return any(cTemporaryFolderRegex.match(str(vArg)) for vArg in pArgs[1:])


def fBase(pPath) -> str:
  return os.path.basename(str(pPath or "")).strip()


def fIsShell(pName: str) -> bool:
  return fBase(pName) in sShells


def fIsInterpreter(pName: str) -> bool:
  return bool(cInterpreterRegex.match(fBase(pName)))


def fIsDownloader(pName: str) -> bool:
  return fBase(pName) in sDownloaders


def fCommandArgs(pCommand: str) -> list[str]:
  # The words of a command typed in a shell, without the leading variable
  # assignments (FOO=1 whoami) nor the wrappers that only run the next word.
  try:
    lWords = shlex.split(str(pCommand or ""), comments=False, posix=True)
  except ValueError:
    lWords = str(pCommand or "").split()
  while lWords and (cAssignmentRegex.match(lWords[0]) or lWords[0] in ("command", "builtin", "exec", "time", "nohup", "nice", "env", "stdbuf", "timeout", "\\")):
    if lWords[0] == "timeout" and len(lWords) > 1:
      lWords = lWords[2:]
      continue
    if lWords[0] == "command" and len(lWords) > 1 and lWords[1] in ("-v", "-V"):
      break
    lWords = lWords[1:]
  return lWords


def fFirstOperand(pArgs: list[str]) -> str:
  for vArg in pArgs:
    if not str(vArg).startswith("-"):
      return str(vArg)
  return ""


def fReconToken(pArgs: list[str]) -> str:
  if not pArgs:
    return ""
  vName = fBase(pArgs[0]).lower()
  lRest = [str(vArg) for vArg in pArgs[1:]]
  if vName == "busybox" and lRest:
    return fReconToken(lRest)
  if len(lRest) == 1 and lRest[0] in ("--version", "-version", "-V", "-v") and vName not in ("sudo",):
    return "version:" + vName
  if vName == "ip":
    return "ip:" + (fFirstOperand(lRest) or "")[:10]
  if vName == "getent":
    return "getent:" + (fFirstOperand(lRest) or "")[:20]
  if vName in sReconSimple:
    return vName
  if vName == "mount" and not lRest:
    return "mount"
  if vName in ("sudo", "sudo-rs"):
    for vArg in lRest:
      if vArg in ("-l", "-ll", "--list") or (re.match(r"^-[A-Za-z]*l[A-Za-z]*$", vArg) and not vArg.startswith("--")):
        return "sudo:list"
      if vArg in ("-V", "--version"):
        return "sudo:version"
      if not vArg.startswith("-"):
        break
    return ""
  if vName == "pkexec" and lRest[:1] == ["--version"]:
    return "pkexec:version"
  if vName == "crontab" and "-l" in lRest:
    return "crontab:list"
  if vName == "systemctl" and lRest and (lRest[0].startswith("list-") or lRest[0] == "status" and len(lRest) == 1):
    return "systemctl:" + lRest[0]
  if (vName == "dpkg" and ("-l" in lRest or "--list" in lRest)) or (vName == "apt" and lRest[:1] == ["list"]) or (vName == "rpm" and "-qa" in lRest) or (vName == "apk" and lRest[:1] == ["info"]):
    return "packages:" + vName
  if vName in ("pip", "pip3") and lRest[:1] == ["list"]:
    return "packages:pip"
  if vName in ("which", "whereis", "locate", "type") or (vName == "command" and lRest[:1] in (["-v"], ["-V"])):
    vTarget = fFirstOperand(lRest)
    return ("which:" + fBase(vTarget)[:40]) if vTarget else ""
  if vName in ("docker", "podman", "lxc", "kubectl", "ctr", "crictl", "nerdctl"):
    vSub = fFirstOperand(lRest)
    if vSub in ("ps", "images", "info", "version", "network", "list", "get", "auth", "inspect", "volume"):
      return vName + ":" + vSub
    return ""
  if vName == "find":
    lOptions = sorted({vArg for vArg in lRest if vArg.startswith("-") and vArg not in ("-o", "-a", "-not", "-print", "-type", "-ls", "-print0")})
    lNames = [lRest[vIndex + 1] for vIndex, vArg in enumerate(lRest[:-1]) if vArg in ("-name", "-iname", "-path")]
    return ("find:" + ",".join(lOptions) + ":" + ",".join(lNames))[:120]
  if vName in sReaders:
    for vArg in lRest:
      if vArg.startswith("-"):
        continue
      if cSensitiveFileRegex.match(vArg) or cCredentialFileRegex.search(vArg):
        return "read:" + vArg[:120]
    if vName in ("grep", "egrep", "rg") and any(vArg.startswith("-") and ("r" in vArg or "R" in vArg) for vArg in lRest) and any(cSecretWordsRegex.search(vArg) for vArg in lRest if not vArg.startswith("-")):
      return "grep:secrets"
    return ""
  if vName in ("ls", "dir", "tree"):
    for vArg in lRest:
      if not vArg.startswith("-") and cSensitiveDirRegex.match(vArg):
        return "ls:" + vArg[:120]
    return ""
  return ""


def fProgramKey(pExe: str, pArgs: list[str]) -> str:
  # sh -c id -> "sh -c id"; python3 -c ... -> "python3 -c"; perl script.pl
  # -> "perl script.pl"; anything else, the program itself.
  vBase = fBase(pExe or (pArgs[0] if pArgs else ""))
  lRest = [str(vArg) for vArg in (pArgs[1:] if pArgs else [])]
  if vBase in sShells:
    if "-c" in lRest:
      vIndex = lRest.index("-c")
      vScript = lRest[vIndex + 1] if vIndex + 1 < len(lRest) else ""
      lWords = fCommandArgs(vScript)
      return f"{vBase} -c {fBase(lWords[0]) if lWords else ''}".strip()[:300]
    vOperand = fFirstOperand(lRest)
    return f"{vBase} {vOperand}".strip()[:300]
  if fIsInterpreter(vBase):
    for vFlag in ("-c", "-e", "-r", "-E"):
      if vFlag in lRest:
        return f"{vBase} {vFlag}"
    vOperand = fFirstOperand(lRest)
    return f"{vBase} {vOperand}".strip()[:300]
  return str(pExe or vBase)[:300]


class SessionTracker:

  def __init__(self):
    self.dSessions = {}
    self.dProcesses = collections.OrderedDict()
    self.dDownloads = {}
    self.vDirty = False

  def mSession(self, pKey: str, pNow: float) -> dict:
    dSession = self.dSessions.get(pKey)
    if dSession is None:
      dSession = {"user": "", "ip": "", "started": False, "door": False, "recon": {}, "commands": [], "last": pNow}
      self.dSessions[pKey] = dSession
    dSession["last"] = max(dSession.get("last", 0.0), pNow)
    return dSession

  def mGet(self, pKey: str) -> dict | None:
    return self.dSessions.get(pKey)

  def mStart(self, pKey: str, pUser: str, pIp: str, pNow: float) -> None:
    dSession = self.mSession(pKey, pNow)
    dSession["started"] = True
    if pUser:
      dSession["user"] = pUser
    if pIp:
      dSession["ip"] = pIp
    self.vDirty = True

  def mDoor(self, pKey: str, pNow: float) -> None:
    dSession = self.mSession(pKey, pNow)
    if not dSession["door"]:
      dSession["door"] = True
      self.vDirty = True

  def mRecon(self, pKey: str, pToken: str, pNow: float, pWindow: float) -> list[str]:
    # The distinct tokens of the session inside the window, this one included.
    dSession = self.mSession(pKey, pNow)
    dRecon = dSession["recon"]
    dRecon[pToken] = pNow
    for vToken in [vItem for vItem, vTime in dRecon.items() if vTime < pNow - pWindow]:
      del dRecon[vToken]
    if len(dRecon) > 2000:
      for vToken in sorted(dRecon, key=dRecon.get)[:len(dRecon) - 2000]:
        del dRecon[vToken]
    return sorted(dRecon, key=dRecon.get)

  def mCommand(self, pKey: str, pTime: str, pText: str, pNow: float) -> None:
    dSession = self.mSession(pKey, pNow)
    dSession["commands"].append([pTime, str(pText)[:300]])
    if len(dSession["commands"]) > cMaxRecent:
      del dSession["commands"][:-cMaxRecent]

  def mRecent(self, pKey: str) -> list:
    dSession = self.dSessions.get(pKey)
    return list(dSession["commands"]) if dSession else []

  def mRememberProcess(self, pPid, pExe: str, pUid, pEuid, pNow: float) -> None:
    if pPid in (None, ""):
      return
    self.dProcesses[str(pPid)] = {"exe": pExe, "uid": pUid, "euid": pEuid, "time": pNow}
    self.dProcesses.move_to_end(str(pPid))
    while len(self.dProcesses) > 20000:
      self.dProcesses.popitem(last=False)

  def mProcess(self, pPid) -> dict | None:
    return self.dProcesses.get(str(pPid)) if pPid not in (None, "") else None

  def mDownload(self, pScope: str, pNow: float) -> None:
    self.dDownloads[pScope] = pNow

  def mRecentDownload(self, pScope: str, pNow: float, pWithin: float = 10.0) -> bool:
    vTime = self.dDownloads.get(pScope)
    return vTime is not None and 0 <= pNow - vTime <= pWithin

  def mPrune(self, pNow: float) -> None:
    for vKey in [vItem for vItem, dSession in self.dSessions.items() if dSession.get("last", 0.0) < pNow - 86400]:
      del self.dSessions[vKey]
      self.vDirty = True
    for vKey in [vItem for vItem, vTime in self.dDownloads.items() if vTime < pNow - 60]:
      del self.dDownloads[vKey]
    while self.dProcesses:
      vOldest = next(iter(self.dProcesses))
      if self.dProcesses[vOldest]["time"] >= pNow - 86400:
        break
      del self.dProcesses[vOldest]

  def mExport(self) -> dict:
    # Only what a restart must not forget: who started each session and
    # whether it went through a door. last is saved in the storage format.
    dExport = {}
    for vKey, dSession in sorted(self.dSessions.items(), key=lambda vItem: vItem[1].get("last", 0.0))[-2000:]:
      if dSession.get("started") or dSession.get("door"):
        dExport[vKey] = {vName: dSession.get(vName) for vName in ("user", "ip", "started", "door")}
        dExport[vKey]["last"] = fEpochToStorage(dSession.get("last", 0.0))
    return dExport

  def mImport(self, pData: dict) -> None:
    for vKey, dSaved in (pData or {}).items():
      if not isinstance(dSaved, dict):
        continue
      # A state saved by an older version has last in epoch seconds.
      vLast = dSaved.get("last")
      dSession = self.mSession(vKey, float(vLast) if isinstance(vLast, (int, float)) else fStorageToEpoch(str(vLast or "")))
      for vName in ("user", "ip", "started", "door"):
        if dSaved.get(vName) not in (None, ""):
          dSession[vName] = dSaved[vName]
