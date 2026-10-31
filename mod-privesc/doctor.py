"""Doctor of the privesc module: what the server has, what is missing and the
exact command that fixes it. It runs as the localsiem user, without storage
(the web and manage.py call it too).

Each check: {"id", "status": ok|warning|error|info, "title", "detail",
"fix" (command, optional)}.
"""

import grp
import os
import stat
from pathlib import Path

from backend.core.timeutil import fStorageToDisplay
from .discovery import (
  cHookDir, cHookFile, cProfileFile, cRulesFile, cSetupVersion, fAuditdBinary, fAuditdPid, fBashPath, fCanRead,
  fContainer, fFileMarker, fFlavor, fSnoopyInstalled, fSyslogPath
)
from .surface import fCheckSensitiveFiles, fPrivilegedMembers, fSurfaceFindings, lRootGroups

cModulePath = Path(__file__).resolve().parent
cSetupCommand = "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py setup-modules --configure-privesc"


def fCheck(pId: str, pStatus: str, pTitle: str, pDetail: str = "", pFix: str = "") -> dict:
  dCheck = {"id": pId, "status": pStatus, "title": pTitle, "detail": pDetail}
  if pFix:
    dCheck["fix"] = pFix
  return dCheck


def fAuditdFix(pFlavor: str, pRunning: bool) -> str:
  if pFlavor == "alpine":
    return "rc-update add auditd && rc-service auditd start" if pRunning else "apk add audit && rc-update add auditd && rc-service auditd start"
  return "systemctl enable --now auditd" if pRunning else "apt-get install auditd"


def fSameFile(pInstalled: Path, pShipped: Path) -> bool:
  try:
    return pInstalled.read_bytes() == pShipped.read_bytes()
  except OSError:
    return False


def fAuditdChecks(pInfo: dict, pState: dict) -> list[dict]:
  ldChecks = []
  vFlavor = fFlavor()
  if pInfo.get("container"):
    ldChecks.append(fCheck(
      "auditd", "info", f"This server is a container ({pInfo['container']}): auditd is not available",
      "The audit of the kernel is not namespaced: auditd only works on the host. Here the module reads the bash hook and syslog (and the commands of snoopy, if installed). To see every command of this container, run auditd with the rules of this module on the host."
    ))
    return ldChecks
  if not pInfo.get("auditd_binary"):
    ldChecks.append(fCheck(
      "auditd", "warning", "auditd is not installed",
      "Without auditd the module only sees the interactive bash shells (hook) and syslog: not the commands of scripts, web shells or exploits, nor the changes of sensitive files. Installing this module does not install auditd: install it, then press Reconfigure and run the command it shows (with --configure-privesc).",
      fAuditdFix(vFlavor, False)
    ))
    return ldChecks
  if not pInfo.get("auditd_pid"):
    ldChecks.append(fCheck("auditd", "error", "auditd is installed but not running", "Start it and enable it at boot; then apply --configure-privesc.", fAuditdFix(vFlavor, True)))
    return ldChecks
  ldChecks.append(fCheck("auditd", "ok", "auditd is running", f"pid {pInfo['auditd_pid']}."))
  vMarker = fFileMarker(cRulesFile)
  if vMarker == cSetupVersion:
    ldChecks.append(fCheck("audit_rules", "ok", "The audit rules of localSIEM are installed", str(cRulesFile)))
  elif vMarker:
    ldChecks.append(fCheck("audit_rules", "warning", "The audit rules of localSIEM are outdated", f"{cRulesFile} was written by an older version of the module.", cSetupCommand))
  elif os.access(cRulesFile.parent, os.X_OK):
    ldChecks.append(fCheck("audit_rules", "warning", "The audit rules of localSIEM are not installed", "Without them auditd does not log the commands, setuid programs, sensitive files nor kernel modules that this module watches.", cSetupCommand))
  if pState.get("last_key_time"):
    ldChecks.append(fCheck("audit_records", "ok", "Records of the localSIEM audit rules are being read", "Last one: " + fStorageToDisplay(pState["last_key_time"]) + "."))
  elif pState.get("audit_lines"):
    ldChecks.append(fCheck(
      "audit_records", "warning", "No record of the localSIEM audit rules has been read yet",
      "auditd is writing, but no record carries a key lsiem_*: the rules of localSIEM are probably not loaded (or nobody has run a command yet).", cSetupCommand
    ))
  vLog = pInfo.get("audit_log") or ""
  if vLog and os.path.exists(vLog):
    if not fCanRead(vLog):
      ldChecks.append(fCheck("audit_log", "error", f"localsiem cannot read {vLog}", "Run the command of the Modules page as root: it gives read access to /var/log/audit and sets log_group = adm.", cSetupCommand))
    else:
      ldChecks.append(fCheck("audit_log", "ok", "The audit log is readable", vLog))
      try:
        vStat = os.stat(vLog)
        vGroup = grp.getgrgid(vStat.st_gid).gr_name
      except (OSError, KeyError):
        vGroup = ""
      if vGroup != "adm":
        ldChecks.append(fCheck(
          "audit_log_group", "warning", "auditd does not create its logs for the group adm",
          f"{vLog} belongs to the group {vGroup or '?'}: when auditd rotates it, the new file may not be readable by localsiem. --configure-privesc sets log_group = adm.", cSetupCommand
        ))
  elif vLog:
    ldChecks.append(fCheck("audit_log", "warning", f"The audit log {vLog} does not exist", "Check log_file in /etc/audit/auditd.conf, or the setting Audit log."))
  return ldChecks


def fHookChecks(pInfo: dict) -> list[dict]:
  ldChecks = []
  if not pInfo.get("bash"):
    ldChecks.append(fCheck("bash", "info", "bash is not installed", "The hook only works in bash: the shells of busybox (ash, the default of Alpine) are not seen. Install bash and make it the shell of the users to see their builtins too, or rely on auditd/snoopy."))
  if not cHookFile.exists():
    ldChecks.append(fCheck("hook", "warning", "The bash hook is not installed", "The builtins (pwd, cd, unset HISTFILE) and the commands of the shells without auditd are not seen.", cSetupCommand))
  elif not fSameFile(cHookFile, cModulePath / "hook" / "hook.bash") or not fSameFile(cProfileFile, cModulePath / "hook" / "profile.sh"):
    ldChecks.append(fCheck("hook", "warning", "The installed bash hook is not the one of this version", "Apply --configure-privesc again (also after updating the module).", cSetupCommand))
  else:
    ldChecks.append(fCheck("hook", "ok", "The bash hook is installed", f"{cHookFile}, {cProfileFile}"))
  if cHookDir.is_dir():
    try:
      vStat = os.stat(cHookDir)
      vGroup = grp.getgrgid(vStat.st_gid).gr_name
    except (OSError, KeyError):
      vStat = None
      vGroup = ""
    if vStat is None or stat.S_IMODE(vStat.st_mode) != 0o3753 or vStat.st_uid != 0 or vGroup != "localsiem":
      ldChecks.append(fCheck(
        "hook_folder", "error", f"The permissions of {cHookDir} are wrong",
        "It must be root:localsiem with mode 3753: users create their own file and cannot list nor delete the files of the others.", cSetupCommand
      ))
    else:
      vCount = sum(1 for vName in os.listdir(cHookDir) if vName.endswith(".log")) if os.access(cHookDir, os.R_OK) else 0
      ldChecks.append(fCheck("hook_folder", "ok", f"{cHookDir} is ready", f"{vCount} files of users."))
  for dProblem in (pInfo.get("hook_problems") or [])[:10]:
    if dProblem["problem"] == "wrong_owner":
      ldChecks.append(fCheck(
        "hook_file_owner", "error", f"{dProblem['path']} does not belong to {dProblem.get('user') or dProblem['uid']}",
        f"It belongs to {dProblem.get('owner_name') or dProblem['owner']}: someone created the file of another user to read or block their commands. It is not read. --configure-privesc moves it aside and creates the right one.", cSetupCommand
      ))
    elif dProblem["problem"] == "unreadable":
      ldChecks.append(fCheck("hook_file_mode", "warning", f"localsiem cannot read {dProblem['path']}", f"Mode {dProblem.get('mode')}: its user changed it to hide their commands, or it was created before the setup.", cSetupCommand))
    else:
      ldChecks.append(fCheck("hook_file", "error", f"{dProblem['path']} is not a regular file", "A link or another kind of file in the place of the file of a user.", cSetupCommand))
  return ldChecks


def fSyslogChecks(pInfo: dict) -> list[dict]:
  ldChecks = []
  vFlavor = fFlavor()
  vWithoutAuditd = bool(pInfo.get("container")) or not pInfo.get("auditd_pid")
  vSyslog = pInfo.get("syslog") or ""
  if vSyslog:
    if fCanRead(vSyslog):
      ldChecks.append(fCheck("syslog", "ok", "syslog is read", f"{vSyslog}: sudo, su, pkexec, doas" + (" and the commands of snoopy." if pInfo.get("snoopy") else ".")))
    else:
      ldChecks.append(fCheck("syslog", "error", f"localsiem cannot read {vSyslog}", "Give it read access (it keeps it after a rotation if the rotated file is created with the same group).", f"setfacl -m g:localsiem:r {vSyslog}"))
  elif vWithoutAuditd and not fSyslogPath():
    ldChecks.append(fCheck(
      "syslog", "warning", "There is no syslog file",
      "Without auditd and without a syslog file (only the journal of systemd), sudo, su and pkexec are not seen. Install a syslog daemon that writes /var/log/auth.log.",
      "rc-update add syslog boot && rc-service syslog start" if vFlavor == "alpine" else "apt-get install rsyslog"
    ))
  if pInfo.get("snoopy"):
    ldChecks.append(fCheck("snoopy", "ok", "snoopy is installed", "Every program run is logged to syslog (with --configure-privesc, with the effective uid and the parent)."))
  elif vWithoutAuditd:
    ldChecks.append(fCheck(
      "snoopy", "warning", "Without auditd, the commands of scripts and web shells are not seen",
      "The bash hook only sees interactive bash shells. snoopy logs every program run to syslog and works inside containers. Installing this module does not install it.",
      "Build snoopy from https://github.com/a2o/snoopy (Alpine has no package of it)" if vFlavor == "alpine" else "apt-get install snoopy"
    ))
  return ldChecks


def fSurfaceChecks(pState: dict, pAccounts) -> list[dict]:
  ldChecks = []
  dScan = pState.get("surface") or {}
  if pState.get("surface_disabled"):
    ldChecks.append(fCheck("surface_scan", "info", "The search of setuid programs is turned off", "Setting Hours between scans of setuid programs: 0."))
  elif dScan.get("time"):
    dFindings = fSurfaceFindings(dScan.get("files") or {})
    ldChecks.append(fCheck(
      "surface_scan", "info", "Setuid programs and capabilities", f"Last scan {fStorageToDisplay(dScan['time'])}: {dScan.get('visited', 0)} files, {dFindings['setuid']} setuid, {dFindings['setgid']} setgid" + (" (stopped at its limit)" if dScan.get("truncated") else "") + "."
    ))
    if dFindings["gtfobins"]:
      ldChecks.append(fCheck(
        "surface_gtfobins", "warning", f"{len(dFindings['gtfobins'])} setuid programs give a root shell (GTFOBins)",
        ", ".join(dFindings["gtfobins"][:20]) + (" …" if len(dFindings["gtfobins"]) > 20 else "") + ". Remove the setuid bit unless it is needed.",
        "chmod u-s " + " ".join(dFindings["gtfobins"][:20])
      ))
    if dFindings["capabilities"]:
      ldChecks.append(fCheck(
        "surface_capabilities", "warning", f"{len(dFindings['capabilities'])} programs have capabilities that are root in practice",
        ", ".join(dFindings["capabilities"][:20]) + ". Remove them unless they are needed (setcap -r <file>).",
      ))
  else:
    ldChecks.append(fCheck("surface_scan", "info", "Setuid programs and capabilities not scanned yet", "The first scan starts a few minutes after the collector."))
  for dProblem in fCheckSensitiveFiles()[:10]:
    vFix = f"chown root:root {dProblem['path']} && chmod go-w {dProblem['path']}" if dProblem["problem"] == "writable" else f"chmod o-r {dProblem['path']}"
    ldChecks.append(fCheck(
      "surface_writable", "error", f"{dProblem['path']} is {'writable' if dProblem['problem'] == 'writable' else 'readable'} by {dProblem['detail']}",
      f"Mode {dProblem['mode']}. Anyone who can change it can become root.", vFix
    ))
  dMembers = fPrivilegedMembers(pAccounts)
  for vGroup in lRootGroups:
    if dMembers.get(vGroup):
      ldChecks.append(fCheck(
        "privileged_group", "warning", f"Members of {vGroup} are root in practice",
        f"{', '.join(dMembers[vGroup][:20])}: the group {vGroup} gives full access to the host (a container with / mounted, a raw disk...). Keep only the people who need it.",
        f"gpasswd -d <user> {vGroup}"
      ))
  return ldChecks


def fRunDoctor(pInfo: dict, pState: dict, pAccounts) -> list[dict]:
  return fAuditdChecks(pInfo, pState) + fHookChecks(pInfo) + fSyslogChecks(pInfo) + fSurfaceChecks(pState, pAccounts)


def fRequirementChecks() -> list[dict]:
  # What the module needs before it can be turned on: one way to see the
  # commands. auditd (not in a container), bash (the hook) or snoopy.
  # Installing the module installs none of them.
  vContainer = fContainer()
  lWays = []
  if fAuditdBinary() and not vContainer:
    lWays.append("auditd")
  if fBashPath():
    lWays.append("bash (hook)")
  if fSnoopyInstalled():
    lWays.append("snoopy")
  if lWays:
    return [fCheck("command_source", "ok", "The commands can be seen", "With: " + ", ".join(lWays) + ".")]
  vFlavor = fFlavor()
  if vContainer:
    vFix = "apk add bash" if vFlavor == "alpine" else "apt-get install bash snoopy"
  else:
    vFix = "apk add audit bash && rc-update add auditd && rc-service auditd start" if vFlavor == "alpine" else "apt-get install auditd"
  return [fCheck(
    "command_source", "error", "Nothing can show the commands run on this server",
    "The module needs auditd (bare metal and virtual machines), bash (for its hook) or snoopy. Installing the module installs none of them: install one, then press Reconfigure.",
    vFix
  )]
