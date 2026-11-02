"""Doctor of the privesc module: what the server has, what the module sees
with it and what it cannot see. It runs as the localsiem user, without storage
(the web and manage.py call it too).

The module never changes the server: the doctor only describes. Its fix is
only the command that installs a missing package or gives the localsiem user
read access to a log; it never changes the rules or the configuration of
auditd, snoopy, the shells or anything else.

Each check: {"id", "status": ok|warning|error|info, "title", "detail",
"fix" (command, optional)}.
"""

import os
import stat

from backend.core.timeutil import fStorageToDisplay
from .discovery import (
  fAuditdBinary, fAuditdPid, fAuditLogPath, fContainer, fFlavor, fReadState, fSnoopyInstalled, fSyslogPath
)
from .surface import fCheckSensitiveFiles, fPrivilegedMembers, fSurfaceFindings, lRootGroups

cSetupCommand = "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py setup-modules"
cAuditFolder = "/var/log/audit/"
# What the module classifies from the audit records besides the programs run,
# when the audit rules of the server record it.
dAuditKinds = {
  "file": "changes of sensitive files", "chmod": "setuid or setgid bits set", "kmod": "kernel modules",
  "ptrace": "ptrace", "denied": "files refused to people"
}


def fCheck(pId: str, pStatus: str, pTitle: str, pDetail: str = "", pFix: str = "") -> dict:
  dCheck = {"id": pId, "status": pStatus, "title": pTitle, "detail": pDetail}
  if pFix:
    dCheck["fix"] = pFix
  return dCheck


def fAuditdInstallFix(pFlavor: str) -> str:
  return "apk add audit && rc-update add auditd && rc-service auditd start" if pFlavor == "alpine" else "apt-get install auditd"


def fSyslogInstallFix(pFlavor: str) -> str:
  return "apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start" if pFlavor == "alpine" else "apt-get install rsyslog"


def fSnoopyInstallFix(pFlavor: str) -> str:
  # Alpine has no package of snoopy.
  return "" if pFlavor == "alpine" else "apt-get install snoopy"


def fAuditReadFix(pLog: str) -> str:
  # /var/log/audit is in read_paths: the command of the Modules page gives
  # localsiem read access to it, also to the logs of the next rotations.
  if pLog.startswith(cAuditFolder):
    return cSetupCommand
  vFolder = os.path.dirname(pLog) or "/"
  return f"setfacl -m g:localsiem:rx {vFolder} && setfacl -d -m g:localsiem:r {vFolder} && setfacl -m g:localsiem:r {pLog}"


def fSyslogReadFix(pSyslog: str) -> str:
  return f"setfacl -m g:localsiem:r {pSyslog}"


def fAuditUsable(pInfo: dict) -> bool:
  # auditd gives the commands: it runs (never inside a container) and its log
  # can be read.
  return bool(pInfo.get("auditd_pid")) and not pInfo.get("container") and pInfo.get("audit_state") == "readable"


def fSyslogUsable(pInfo: dict) -> bool:
  return bool(pInfo.get("syslog")) and pInfo.get("syslog_state") == "readable"


def fAuditdChecks(pInfo: dict, pState: dict) -> list[dict]:
  ldChecks = []
  vFlavor = fFlavor()
  if pInfo.get("container"):
    ldChecks.append(fCheck(
      "auditd", "info", f"This server is a container ({pInfo['container']}): auditd cannot run in it",
      "The audit of the kernel is not namespaced: auditd only runs on the host. Here the module reads syslog: sudo, su, pkexec and doas and, if snoopy is installed, every program run."
    ))
    return ldChecks
  if not pInfo.get("auditd_binary"):
    ldChecks.append(fCheck(
      "auditd", "warning", "auditd is not installed",
      "Without auditd the module does not see the changes of sensitive files, the setuid bits set, the kernel modules, ptrace nor the files refused, and only snoopy (if installed) shows the programs run by scripts, web shells and exploits. Installing this module does not install auditd.",
      fAuditdInstallFix(vFlavor)
    ))
    return ldChecks
  if not pInfo.get("auditd_pid"):
    ldChecks.append(fCheck(
      "auditd", "warning", "auditd is installed but not running",
      "The module does not read it while it is stopped: what auditd would record is not seen. Whether it runs is the decision of the administrator."
    ))
    return ldChecks
  ldChecks.append(fCheck("auditd", "ok", "auditd is running", f"pid {pInfo['auditd_pid']}."))
  vLog = pInfo.get("audit_log") or ""
  vState = pInfo.get("audit_state") or "missing"
  if vState == "unreadable":
    ldChecks.append(fCheck(
      "audit_log", "error", f"localsiem cannot read {vLog}",
      "Give the localsiem user read access to the audit log, also to the logs of the next rotations: run the command of the Modules page as root.", fAuditReadFix(vLog)
    ))
  elif vState == "missing":
    ldChecks.append(fCheck(
      "audit_log", "warning", f"The audit log {vLog} does not exist",
      "auditd is running but its log is not there: check log_file in /etc/audit/auditd.conf and set it in the setting Audit log."
    ))
  else:
    ldChecks.append(fCheck("audit_log", "ok", "The audit log is readable", vLog))
    try:
      vStat = os.stat(vLog)
    except OSError:
      vStat = None
    # The group of the log is log_group of auditd.conf. With root, auditd
    # creates every log with mode 600 and the default ACL of localsiem gets no
    # permission on it (its mask comes from the group bits).
    if vStat is not None and vStat.st_gid == 0:
      ldChecks.append(fCheck(
        "audit_log_group", "warning", "auditd creates its logs readable by root only",
        f"{vLog} belongs to the group root (mode {oct(stat.S_IMODE(vStat.st_mode))}): auditd runs with log_group = root, so every log it creates when it rotates has mode 600 and the read access of localsiem does not reach it (localSIEM stops reading until the read access is given again). With log_group = adm in /etc/audit/auditd.conf, and auditd restarted, the new logs are created with mode 640 and stay readable.",
        "log_group = adm"
      ))
  ldChecks.extend(fAuditRecordChecks(pState))
  return ldChecks


def fAuditRecordChecks(pState: dict) -> list[dict]:
  # What the audit rules of the server have given so far (since localSIEM
  # started): the module uses the rules the server has, whatever they are.
  ldChecks = []
  vLines = int(pState.get("audit_lines") or 0)
  if not vLines:
    return ldChecks
  dKinds = pState.get("audit_kinds") or {}
  if dKinds.get("exec"):
    ldChecks.append(fCheck("audit_records", "ok", "auditd records the programs run", "Last program run read: " + fStorageToDisplay(dKinds["exec"]) + "."))
  else:
    ldChecks.append(fCheck(
      "audit_records", "warning", "auditd records no program run",
      f"{vLines} audit records were read since localSIEM started and none of them is a program run (EXECVE): the audit rules of this server do not record execve, so the commands of scripts, web shells and exploits are not seen through auditd; logins, sudo and su still are. Which rules auditd loads is the decision of the administrator (auditctl -l, as root, lists them)."
    ))
  lSeen = [vLabel for vKind, vLabel in dAuditKinds.items() if dKinds.get(vKind)]
  lNotSeen = [vLabel for vKind, vLabel in dAuditKinds.items() if not dKinds.get(vKind)]
  ldChecks.append(fCheck(
    "audit_coverage", "info", "What the audit rules of this server have recorded",
    ("Seen since localSIEM started: " + ", ".join(lSeen) + ". " if lSeen else "")
    + ("Not seen yet: " + ", ".join(lNotSeen) + ". They appear only if the audit rules of the server record those system calls or watch those files." if lNotSeen else "")
  ))
  return ldChecks


def fSyslogChecks(pInfo: dict, pState: dict) -> list[dict]:
  ldChecks = []
  vFlavor = fFlavor()
  vAudit = fAuditUsable(pInfo)
  vSyslog = pInfo.get("syslog") or ""
  vState = pInfo.get("syslog_state") or "missing"
  if vSyslog:
    if vState == "readable":
      ldChecks.append(fCheck("syslog", "ok", "syslog is read", f"{vSyslog}: sudo, su, pkexec, doas and the SSH logins" + (", and the programs logged by snoopy." if pInfo.get("snoopy") else ".")))
    elif vState == "unreadable":
      ldChecks.append(fCheck(
        "syslog", "error", f"localsiem cannot read {vSyslog}",
        "Give the localsiem user read access to it. If the rotated file is created with another group, the access has to be given again after a rotation.", fSyslogReadFix(vSyslog)
      ))
    else:
      ldChecks.append(fCheck("syslog", "warning", f"The syslog file {vSyslog} does not exist", "Check the setting Syslog file."))
  elif not vAudit and not pInfo.get("syslog_path"):
    ldChecks.append(fCheck(
      "syslog", "warning", "There is no syslog file",
      "Without the audit log and without a syslog file (only the journal of systemd), sudo, su, pkexec and doas are not seen. A syslog daemon that writes /var/log/auth.log (Debian) or /var/log/messages (Alpine) gives them. Installing this module does not install it.",
      fSyslogInstallFix(vFlavor)
    ))
  elif not vAudit and pInfo.get("syslog_mode") == "never":
    ldChecks.append(fCheck("syslog", "warning", "syslog is not read", f"The setting Read syslog is Never, and the audit log cannot be used: {pInfo.get('syslog_path')} is not read."))
  if pInfo.get("snoopy"):
    if fSyslogUsable(pInfo):
      ldChecks.append(fCheck("snoopy", "ok", "snoopy is installed", f"Its lines in {vSyslog} give every program run."))
    elif not vSyslog:
      ldChecks.append(fCheck(
        "snoopy", "warning", "snoopy is installed but its lines are not read",
        "snoopy writes to syslog, and syslog is not read: " + ("the setting Read syslog is Never." if pInfo.get("syslog_mode") == "never" else "there is no syslog file (the journal of systemd alone is not read).")
      ))
    if pState.get("snoopy_lines") and not pState.get("snoopy_euid"):
      ldChecks.append(fCheck(
        "snoopy_format", "info", "The lines of snoopy have no effective uid",
        "The message_format of /etc/snoopy.ini on this server does not write the euid: root inherited from an abused setuid program (rule privesc-suid-escape) is not seen through snoopy. The module reads the lines as they are; their format is the decision of the administrator."
      ))
  elif not vAudit:
    ldChecks.append(fCheck(
      "snoopy", "warning", "Without auditd, the commands of scripts and web shells are not seen",
      "snoopy logs every program run to syslog and also works inside containers. Installing this module does not install it." + (" Alpine has no package of it: it is built from source (https://github.com/a2o/snoopy)." if vFlavor == "alpine" else ""),
      fSnoopyInstallFix(vFlavor)
    ))
  return ldChecks


def fCoverageCheck(pInfo: dict, pState: dict) -> dict:
  # In one sentence, what the module sees with what the server has.
  vBuiltins = " The builtins of the shell (pwd, cd, unset HISTFILE, history -c) run no program: no source sees them."
  vAudit = fAuditUsable(pInfo)
  vSyslog = fSyslogUsable(pInfo)
  vSnoopy = vSyslog and bool(pInfo.get("snoopy"))
  if vAudit:
    vExec = bool((pState.get("audit_kinds") or {}).get("exec"))
    return fCheck(
      "coverage", "info", "The module sees what auditd records" + (" and snoopy logs" if vSnoopy else ""),
      "auditd: logins, sudo and su (PAM) and what the audit rules of this server record" + (", programs run included." if vExec else ".")
      + (" snoopy: every program run." if vSnoopy else "") + vBuiltins
    )
  if vSnoopy:
    return fCheck(
      "coverage", "info", "The module sees the programs run through snoopy",
      "syslog: sudo, su, pkexec, doas and the SSH logins; snoopy: every program run, with its user and folder (not the programs linked statically nor the ones started without its library). Not seen without auditd: the changes of sensitive files, the setuid bits set, the kernel modules, ptrace and the files refused." + vBuiltins
    )
  if vSyslog:
    return fCheck(
      "coverage", "warning", "The module only sees sudo, su, pkexec and doas",
      "syslog gives sudo, su, pkexec, doas and the SSH logins. The commands typed and the programs run by scripts, web shells and exploits are not seen, so most rules (reconnaissance, tools, exploits, reverse shells, service accounts, root inherited from a setuid program) cannot fire. auditd (outside containers) or snoopy would show them." + vBuiltins
    )
  return fCheck("coverage", "error", "The module sees nothing", "It cannot read the audit log nor a syslog file: see the checks above.")


def fLegacyChecks(pInfo: dict) -> list[dict]:
  lFound = pInfo.get("leftovers") or []
  if not lFound:
    return []
  return [fCheck(
    "legacy_files", "info", "Files of version 1.0.0 of the module",
    ", ".join(lFound) + ": version 1.0.0 of the module created them with --configure-privesc (its audit rules, the bash hook and the folder of its command files, and a line in the bashrc of the system). Since version 1.1.0 localSIEM no longer uses them and never deletes them, because they are outside /opt/localsiem. While the hook is there it keeps writing the commands typed into /var/log/localsiem-privesc, which nobody reads, and while its audit rules are loaded they are used like any other rule of the server. The administrator may delete them (and, in the bashrc, the line that follows «localSIEM privesc: command hook»)."
  )]


def fSurfaceChecks(pState: dict, pAccounts) -> list[dict]:
  # Only described: the module never changes the permissions of the server.
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
        ", ".join(dFindings["gtfobins"][:20]) + (" …" if len(dFindings["gtfobins"]) > 20 else "") + ". Unless the setuid bit is needed, it is an open door to root."
      ))
    if dFindings["capabilities"]:
      ldChecks.append(fCheck(
        "surface_capabilities", "warning", f"{len(dFindings['capabilities'])} programs have capabilities that are root in practice",
        ", ".join(dFindings["capabilities"][:20]) + ". Unless they are needed, they are an open door to root."
      ))
  else:
    ldChecks.append(fCheck("surface_scan", "info", "Setuid programs and capabilities not scanned yet", "The first scan starts a few minutes after the collector."))
  for dProblem in fCheckSensitiveFiles()[:10]:
    ldChecks.append(fCheck(
      "surface_writable", "error", f"{dProblem['path']} is {'writable' if dProblem['problem'] == 'writable' else 'readable'} by {dProblem['detail']}",
      f"Mode {dProblem['mode']}. Anyone who can " + ("change it can become root: only root should be able to." if dProblem["problem"] == "writable" else "read it can try to crack the password hashes.")
    ))
  dMembers = fPrivilegedMembers(pAccounts)
  for vGroup in lRootGroups:
    if dMembers.get(vGroup):
      ldChecks.append(fCheck(
        "privileged_group", "warning", f"Members of {vGroup} are root in practice",
        f"{', '.join(dMembers[vGroup][:20])}: the group {vGroup} gives full access to the host (a container with / mounted, a raw disk...). Only the people who need it should be in it."
      ))
  return ldChecks


def fRunDoctor(pInfo: dict, pState: dict, pAccounts) -> list[dict]:
  return (
    fAuditdChecks(pInfo, pState) + fSyslogChecks(pInfo, pState) + [fCoverageCheck(pInfo, pState)]
    + fLegacyChecks(pInfo) + fSurfaceChecks(pState, pAccounts)
  )


def fRequirementChecks(pSettings: dict | None = None) -> list[dict]:
  # What the module needs before it can be turned on: any readable source of
  # what is run on the server. The auditd log (auditd running, not in a
  # container), or the syslog file with sudo, su, pkexec and doas (and the
  # lines of snoopy, when it is installed). Readable means that the file
  # exists and the localsiem user can open it. It needs no root and installs
  # nothing.
  dSettings = pSettings or {}
  vFlavor = fFlavor()
  vContainer = fContainer()
  vSnoopy = fSnoopyInstalled()
  lReadable = []
  ldUnreadable = []
  if not vContainer and fAuditdPid() is not None:
    vLog = fAuditLogPath(dSettings.get("audit_log", ""))
    vState = fReadState(vLog)
    if vState == "readable":
      lReadable.append(f"the audit log ({vLog})")
    elif vState == "unreadable":
      ldUnreadable.append(fCheck(
        "audit_log", "error", f"localsiem cannot read the audit log {vLog}",
        "auditd is running, but the localsiem user cannot read its log: run the command of the Modules page as root, then press Reconfigure.", fAuditReadFix(vLog)
      ))
  vMode = dSettings.get("syslog_mode") or "auto"
  vSyslog = fSyslogPath(dSettings.get("syslog_file", ""))
  if vSyslog and vMode != "never":
    vState = fReadState(vSyslog)
    vWhat = "sudo, su, pkexec and doas" + (", and the programs logged by snoopy" if vSnoopy else "")
    if vState == "readable":
      lReadable.append(f"syslog ({vSyslog}: {vWhat})")
    elif vState == "unreadable":
      ldUnreadable.append(fCheck(
        "syslog", "error", f"localsiem cannot read {vSyslog}",
        f"It holds {vWhat}, but the localsiem user cannot read it: give it read access, then press Reconfigure.", fSyslogReadFix(vSyslog)
      ))
  if lReadable:
    # Met: a source that cannot be read is only a warning.
    return [fCheck("command_source", "ok", "The module has something to read", "It reads " + " and ".join(lReadable) + ".")] + [dict(dCheck, status="warning") for dCheck in ldUnreadable]
  if ldUnreadable:
    return ldUnreadable
  # Nothing to read: what the server lacks and the package that gives it.
  vNoSyslog = f"the setting Read syslog is Never, so {vSyslog} is not read" if vMode == "never" and vSyslog else "there is no syslog file"
  vNeeds = "The module needs auditd running, or a syslog daemon that writes /var/log/auth.log (Debian) or /var/log/messages (Alpine), for sudo, su, pkexec and doas (and snoopy to also see every program run). Installing the module installs none of them"
  if vContainer:
    vDetail = f"This server is a container ({vContainer}), where auditd cannot run, and {vNoSyslog}. The module needs a syslog daemon that writes /var/log/auth.log (Debian) or /var/log/messages (Alpine), for sudo, su, pkexec and doas, and snoopy to also see every program run. Installing the module installs none of them: install them, then press Reconfigure."
    vFix = fSyslogInstallFix(vFlavor) if vFlavor == "alpine" or vSnoopy else "apt-get install rsyslog snoopy"
  elif fAuditdPid() is not None:
    # auditd runs but its log is not where the module looks for it.
    vDetail = f"auditd is running but its log {fAuditLogPath(dSettings.get('audit_log', ''))} was not found (set the setting Audit log to the log_file of /etc/audit/auditd.conf), and {vNoSyslog}. {vNeeds}: install a syslog daemon or set the audit log, then press Reconfigure."
    vFix = fSyslogInstallFix(vFlavor)
  elif fAuditdBinary():
    # auditd is there but stopped: starting it is the decision of the
    # administrator, so the fix is the package of a syslog daemon.
    vDetail = f"auditd is installed but not running, and {vNoSyslog}. {vNeeds}: start auditd or install a syslog daemon, then press Reconfigure."
    vFix = fSyslogInstallFix(vFlavor)
  else:
    vDetail = f"auditd is not installed, and {vNoSyslog}. {vNeeds}: install one (auditd sees the most), then press Reconfigure."
    vFix = fAuditdInstallFix(vFlavor)
  return [fCheck("command_source", "error", "The module has nothing to read on this server", vDetail, vFix)]
