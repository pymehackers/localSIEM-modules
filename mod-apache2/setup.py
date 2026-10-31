"""Apache requirements applied with --configure-apache, as root.

One file of its own, the modules it needs, configtest; everything is undone
if configtest fails, and Apache is reloaded (never restarted). It runs as
root, from manage.py apply-setup of localSIEM, through ApacheModule.mApplySetup.
"""

import shutil
import subprocess
from pathlib import Path

from .discovery import ApacheConfig
from .doctor import fBuildLocalsiemConf


def fRun(pCommand: list[str]) -> subprocess.CompletedProcess:
  return subprocess.run(pCommand, capture_output=True, text=True)


def fApacheCommands(pFlavor: str) -> dict:
  if pFlavor == "debian":
    return {"test": ["apache2ctl", "configtest"], "reload": ["systemctl", "reload", "apache2"], "file": Path("/etc/apache2/conf-available/localsiem.conf")}
  return {"test": ["httpd", "-t"], "reload": ["rc-service", "apache2", "reload"], "file": Path("/etc/apache2/conf.d/localsiem.conf")}


def fConfigureApache(pConfigFile: str = "") -> None:
  vConfig = ApacheConfig(pConfigFile).mParse()
  if not vConfig.mFound():
    print("Apache was not found: --configure-apache skipped.")
    return
  vFlavor = vConfig.vFlavor if vConfig.vFlavor in ("debian", "alpine") else "debian"
  dCommands = fApacheCommands(vFlavor)
  vFile = dCommands["file"]
  vPrevious = vFile.read_text(encoding="utf-8") if vFile.exists() else None
  lUndo = []
  if vFlavor == "debian":
    vEnabledConf = Path("/etc/apache2/conf-enabled/localsiem.conf")
    vEnabledModule = Path("/etc/apache2/mods-enabled/unique_id.load")
  for vJson in (True, False):
    vFile.write_text(fBuildLocalsiemConf(vFlavor, vJson), encoding="utf-8")
    vFile.chmod(0o644)
    if vFlavor == "debian":
      if not vEnabledConf.exists():
        fRun(["a2enconf", "localsiem"])
        lUndo.append(["a2disconf", "-q", "localsiem"])
      if not vEnabledModule.exists():
        fRun(["a2enmod", "unique_id"])
        lUndo.append(["a2dismod", "-q", "unique_id"])
    for vLog in ("localsiem_access.log", "modsec_audit.log"):
      # Created now, readable by the adm group (Debian) and by the ACLs that
      # localSIEM sets, before Apache creates them with its own mode.
      vPath = Path("/var/log/apache2") / vLog
      if not vPath.exists() and vPath.parent.is_dir():
        vPath.touch(mode=0o640)
        if vFlavor == "debian":
          shutil.chown(vPath, "root", "adm")
    vTest = fRun(dCommands["test"])
    if vTest.returncode == 0:
      vReload = fRun(dCommands["reload"])
      print("Apache configured for localSIEM (" + str(vFile) + ")" + ("" if vJson else ", native audit log format (JSON not supported)") + ".")
      if vReload.returncode != 0:
        print("Warning: Apache could not be reloaded: " + (vReload.stderr or vReload.stdout).strip()[:300])
      return
    if vJson and "SecAuditLogFormat" in (vTest.stdout + vTest.stderr):
      continue
    break
  # Undo everything: the client's web keeps its previous configuration.
  for lCommand in reversed(lUndo):
    fRun(lCommand)
  if vPrevious is None:
    vFile.unlink(missing_ok=True)
  else:
    vFile.write_text(vPrevious, encoding="utf-8")
  print("Warning: Apache configtest failed with the localSIEM configuration; nothing was changed and Apache was not reloaded:")
  print((vTest.stdout + vTest.stderr).strip()[:2000])


def fBuildSnippet(pConfigFile: str = "") -> str:
  vConfig = ApacheConfig(pConfigFile).mParse()
  return fBuildLocalsiemConf(vConfig.vFlavor or "debian")
