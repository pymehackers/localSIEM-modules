"""Attack surface of the server for a privilege escalation.

  setuid and setgid programs, and programs with file capabilities, found by
  walking the folders of the setting scan_paths (each one inside its own file
  system) in a thread of its own, so the collector never waits for it. The
  first scan is the reference; a later one that finds a new setuid program or
  new capabilities is a detection (an attacker who became root often leaves a
  setuid shell behind to come back).
  GTFOBins: programs that give a shell, read or write any file when they are
  setuid or have capabilities. The doctor lists them.
  sensitive files and folders writable by someone other than root
  (/etc/passwd, sudoers, cron, the folders of the PATH of root...): an
  escalation waiting to happen.
  groups whose members are root in practice: docker, lxd, disk...

It runs as the localsiem user: what it cannot read is skipped.
"""

import glob
import os
import re
import stat
import struct
import threading
import time

cMaxFiles = 3000000
cMaxSeconds = 900
lSkipTops = ["/proc", "/sys", "/run/user", "/var/lib/docker", "/var/lib/containers", "/var/lib/lxc", "/var/lib/lxd", "/var/lib/machines", "/snap"]
lCapabilityNames = [
  "cap_chown", "cap_dac_override", "cap_dac_read_search", "cap_fowner", "cap_fsetid", "cap_kill", "cap_setgid",
  "cap_setuid", "cap_setpcap", "cap_linux_immutable", "cap_net_bind_service", "cap_net_broadcast", "cap_net_admin",
  "cap_net_raw", "cap_ipc_lock", "cap_ipc_owner", "cap_sys_module", "cap_sys_rawio", "cap_sys_chroot",
  "cap_sys_ptrace", "cap_sys_pacct", "cap_sys_admin", "cap_sys_boot", "cap_sys_nice", "cap_sys_resource",
  "cap_sys_time", "cap_sys_tty_config", "cap_mknod", "cap_lease", "cap_audit_write", "cap_audit_control",
  "cap_setfcap", "cap_mac_override", "cap_mac_admin", "cap_syslog", "cap_wake_alarm", "cap_block_suspend",
  "cap_audit_read", "cap_perfmon", "cap_bpf", "cap_checkpoint_restore"
]
# Capabilities that are root in practice (read or write any file, change of
# user, load kernel code, inject into processes).
sDangerousCapabilities = {
  "cap_chown", "cap_dac_override", "cap_dac_read_search", "cap_fowner", "cap_setgid", "cap_setuid", "cap_setpcap",
  "cap_sys_module", "cap_sys_rawio", "cap_sys_ptrace", "cap_sys_admin", "cap_setfcap", "cap_bpf"
}
# GTFOBins: programs that give a shell or read/write any file when setuid.
sGtfobins = {
  "aa-exec", "ab", "agetty", "alpine", "ar", "arj", "arp", "as", "ascii-xfr", "ash", "aspell", "atobm", "awk", "base32",
  "base64", "basenc", "basez", "bash", "bc", "bridge", "busybox", "bzip2", "cabal", "capsh", "cat", "chmod", "choom",
  "chown", "chroot", "clamscan", "cmp", "column", "comm", "cp", "cpio", "cpulimit", "csh", "csplit", "csvtool",
  "cupsfilter", "curl", "cut", "dash", "date", "dd", "debugfs", "dialog", "diff", "dig", "distcc", "dmsetup", "docker",
  "dosbox", "ed", "efax", "elvish", "emacs", "env", "eqn", "espeak", "expand", "expect", "file", "find", "fish", "flock",
  "fmt", "fold", "gawk", "gcore", "gdb", "genie", "genisoimage", "gimp", "grep", "gtester", "gzip", "hd", "head",
  "hexdump", "highlight", "hping3", "iconv", "install", "ionice", "ip", "ispell", "jjs", "join", "jq", "jrunscript",
  "julia", "ksh", "ksshell", "kubectl", "ld.so", "less", "links", "logsave", "look", "lua", "make", "mawk", "more",
  "mosquitto", "msgattrib", "msgcat", "msgconv", "msgfilter", "msgmerge", "msguniq", "multitime", "mv", "nano", "nasm",
  "nawk", "nc", "ncat", "ncftp", "nft", "nice", "nl", "nm", "nmap", "node", "nohup", "od", "openssl", "openvpn",
  "pandoc", "paste", "perf", "perl", "pexec", "pg", "php", "pidstat", "pr", "ptx", "python", "rc", "readelf", "restic",
  "rev", "rlwrap", "rsync", "rtorrent", "run-parts", "rview", "rvim", "sash", "scanmem", "scp", "sed", "setarch",
  "setfacl", "setlock", "shuf", "socat", "soelim", "softlimit", "sort", "sqlite3", "ss", "ssh-agent", "ssh-keygen",
  "ssh-keyscan", "sshpass", "start-stop-daemon", "stdbuf", "strace", "strings", "sysctl", "systemctl", "tac", "tail",
  "tar", "taskset", "tbl", "tclsh", "tee", "terraform", "tftp", "tic", "time", "timeout", "troff", "ul", "unexpand",
  "uniq", "unshare", "unsquashfs", "unzip", "update-alternatives", "uudecode", "uuencode", "vagrant", "varnishncsa",
  "vi", "view", "vigr", "vim", "vimdiff", "vipw", "w3m", "watch", "wc", "wget", "whiptail", "xargs", "xdotool",
  "xmodmap", "xmore", "xxd", "xz", "yash", "zip", "zsh", "zsoelim", "ruby", "irb", "gcc", "git", "ftp", "pip", "screen",
  "tmux", "man", "mysql", "psql", "ssh", "sudoedit", "lftp", "rpm", "dpkg", "apt", "apt-get", "journalctl", "dmesg"
}
cVersionSuffixRegex = re.compile(r"[0-9.]+$")
lCriticalFiles = [
  "/etc/passwd", "/etc/shadow", "/etc/group", "/etc/gshadow", "/etc/sudoers", "/etc/crontab", "/etc/ld.so.preload",
  "/etc/profile", "/etc/bash.bashrc", "/etc/environment", "/etc/doas.conf", "/etc/ld.so.conf", "/etc/security/limits.conf"
]
lCriticalGlobs = [
  "/etc/sudoers.d/*", "/etc/cron.d/*", "/etc/cron.hourly/*", "/etc/cron.daily/*", "/etc/cron.weekly/*",
  "/etc/cron.monthly/*", "/etc/profile.d/*", "/etc/pam.d/*", "/etc/systemd/system/*.service", "/etc/systemd/system/*.timer",
  "/lib/systemd/system/*.service", "/usr/lib/systemd/system/*.service", "/etc/init.d/*", "/etc/ld.so.conf.d/*",
  "/etc/update-motd.d/*", "/etc/local.d/*"
]
lCriticalFolders = [
  "/etc", "/etc/sudoers.d", "/etc/cron.d", "/etc/profile.d", "/etc/pam.d", "/etc/systemd/system", "/etc/init.d",
  "/usr/local/bin", "/usr/local/sbin", "/usr/bin", "/usr/sbin", "/bin", "/sbin"
]
lPrivilegedGroups = ["docker", "lxd", "lxc", "incus-admin", "disk", "libvirt", "kvm", "shadow", "video"]
lRootGroups = ["docker", "lxd", "incus-admin", "disk", "libvirt"]


def fCapabilities(pData: bytes) -> list[str]:
  # Permitted capabilities of a security.capability attribute (vfs_cap_data,
  # versions 1 to 3, little endian).
  if len(pData) < 12:
    return []
  vMagic = struct.unpack_from("<I", pData, 0)[0]
  vVersion = vMagic & 0xFF000000
  vPermitted = struct.unpack_from("<I", pData, 4)[0]
  if vVersion in (0x02000000, 0x03000000) and len(pData) >= 20:
    vPermitted |= struct.unpack_from("<I", pData, 12)[0] << 32
  return [vName for vIndex, vName in enumerate(lCapabilityNames) if vPermitted & (1 << vIndex)]


def fCapabilitiesFromMask(pHex: str) -> list[str]:
  # A capability mask of auditd (BPRM_FCAPS pp=0000000000000080).
  try:
    vMask = int(str(pHex or "0"), 16)
  except ValueError:
    return []
  return [vName for vIndex, vName in enumerate(lCapabilityNames) if vMask & (1 << vIndex)]


def fFileCapabilities(pPath: str) -> list[str]:
  try:
    return fCapabilities(os.getxattr(pPath, "security.capability", follow_symlinks=False))
  except (OSError, AttributeError):
    return []


def fGtfobin(pPath: str) -> bool:
  vName = os.path.basename(pPath)
  return vName in sGtfobins or cVersionSuffixRegex.sub("", vName) in sGtfobins


def fWritableByOthers(pStat: os.stat_result) -> str:
  # Who other than root can write it: "", "others", "group <gid>" or
  # "owner <uid>".
  vMode = stat.S_IMODE(pStat.st_mode)
  if pStat.st_uid != 0:
    return f"owner {pStat.st_uid}"
  if vMode & stat.S_IWOTH and not (stat.S_ISDIR(pStat.st_mode) and vMode & stat.S_ISVTX):
    return "others"
  if vMode & stat.S_IWGRP and pStat.st_gid != 0:
    return f"group {pStat.st_gid}"
  return ""


def fCheckSensitiveFiles() -> list[dict]:
  # [{path, problem, detail}]: sensitive files and folders that someone other
  # than root can write, and /etc/shadow readable by everybody.
  ldProblems = []
  lPaths = list(lCriticalFiles)
  for vPattern in lCriticalGlobs:
    lPaths.extend(sorted(glob.glob(vPattern))[:500])
  for vPath in lPaths + lCriticalFolders:
    try:
      vStat = os.lstat(vPath)
    except OSError:
      continue
    if stat.S_ISLNK(vStat.st_mode):
      continue
    vWho = fWritableByOthers(vStat)
    if vWho:
      ldProblems.append({"path": vPath, "problem": "writable", "detail": vWho, "mode": oct(stat.S_IMODE(vStat.st_mode))})
  for vPath in ("/etc/shadow", "/etc/gshadow"):
    try:
      vStat = os.stat(vPath)
      if stat.S_IMODE(vStat.st_mode) & stat.S_IROTH:
        ldProblems.append({"path": vPath, "problem": "readable", "detail": "others", "mode": oct(stat.S_IMODE(vStat.st_mode))})
    except OSError:
      pass
  for vPath in ("/var/run/docker.sock", "/run/docker.sock", "/run/podman/podman.sock", "/var/lib/lxd/unix.socket"):
    try:
      vStat = os.stat(vPath)
      if stat.S_IMODE(vStat.st_mode) & stat.S_IWOTH:
        ldProblems.append({"path": vPath, "problem": "writable", "detail": "others", "mode": oct(stat.S_IMODE(vStat.st_mode))})
    except OSError:
      pass
  return ldProblems


class SurfaceScanner:
  # Walks the folders in a thread; mTake gives the result of the last scan
  # that finished (once).

  def __init__(self):
    self.vLock = threading.Lock()
    self.vThread = None
    self.dResult = None
    self.vStarted = 0.0

  def mRunning(self) -> bool:
    return self.vThread is not None and self.vThread.is_alive()

  def mStart(self, pPaths: list[str]) -> bool:
    if self.mRunning():
      return False
    self.vStarted = time.time()
    self.vThread = threading.Thread(target=self.mRun, args=(list(pPaths),), name="privesc-surface", daemon=True)
    self.vThread.start()
    return True

  def mTake(self) -> dict | None:
    with self.vLock:
      dResult = self.dResult
      self.dResult = None
    return dResult

  def mRun(self, pPaths: list[str]) -> None:
    vStart = time.time()
    dFiles = {}
    sSeenFolders = set()
    vVisited = 0
    vTruncated = False
    for vTop in pPaths:
      vTop = vTop.strip()
      if not vTop.startswith("/") or any(vTop == vSkip or vTop.startswith(vSkip + "/") for vSkip in lSkipTops):
        continue
      try:
        vDevice = os.stat(vTop).st_dev
      except OSError:
        continue
      for vFolder, lFolders, lFiles in os.walk(vTop, onerror=None, followlinks=False):
        try:
          vFolderStat = os.lstat(vFolder)
        except OSError:
          lFolders[:] = []
          continue
        vFolderKey = (vFolderStat.st_dev, vFolderStat.st_ino)
        if vFolderKey in sSeenFolders or vFolderStat.st_dev != vDevice:
          lFolders[:] = []
          continue
        sSeenFolders.add(vFolderKey)
        lFolders[:] = [vName for vName in lFolders if os.path.join(vFolder, vName) not in lSkipTops]
        for vName in lFiles:
          vVisited += 1
          if vVisited > cMaxFiles or time.time() - vStart > cMaxSeconds:
            vTruncated = True
            break
          vPath = os.path.join(vFolder, vName)
          try:
            vStat = os.lstat(vPath)
          except OSError:
            continue
          if not stat.S_ISREG(vStat.st_mode):
            continue
          vMode = stat.S_IMODE(vStat.st_mode)
          lCaps = fFileCapabilities(vPath) if vMode & 0o111 else []
          if vMode & (stat.S_ISUID | stat.S_ISGID) or lCaps:
            dFiles[vPath] = {"mode": vMode, "uid": vStat.st_uid, "gid": vStat.st_gid, "caps": lCaps, "size": vStat.st_size}
        if vTruncated:
          break
      if vTruncated:
        break
    with self.vLock:
      self.dResult = {"time": time.time(), "seconds": round(time.time() - vStart, 1), "visited": vVisited, "truncated": vTruncated, "files": dFiles}


def fSurfaceFindings(pFiles: dict) -> dict:
  # What the doctor shows: setuid GTFOBins and dangerous capabilities.
  lGtfobins = sorted(vPath for vPath, dFile in pFiles.items() if dFile["mode"] & stat.S_ISUID and dFile["uid"] == 0 and fGtfobin(vPath))
  lCaps = sorted(f"{vPath} ({','.join(dFile['caps'])})" for vPath, dFile in pFiles.items() if set(dFile.get("caps") or []) & sDangerousCapabilities)
  return {"gtfobins": lGtfobins, "capabilities": lCaps, "setuid": sum(1 for dFile in pFiles.values() if dFile["mode"] & stat.S_ISUID), "setgid": sum(1 for dFile in pFiles.values() if dFile["mode"] & stat.S_ISGID)}


def fPrivilegedMembers(pAccounts) -> dict:
  # {group: [members]} of the groups that give root or a lot of power.
  return {vGroup: pAccounts.mGroupMembers(vGroup) for vGroup in lPrivilegedGroups if pAccounts.mGroupMembers(vGroup)}
