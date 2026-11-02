"""Correlation of the privesc module.

An audit event is written as several records with the same serial
(msg=audit(<time>:<serial>)): SYSCALL, EXECVE, CWD, PATH, PROCTITLE... and,
for the events of the kernel with more than one record, EOE at the end.
Records of different events can be interleaved, so they are joined by their
serial and the event is due at its EOE, at once for the records of user space
(USER_*, CRED_*, DAEMON_*...: one record each), or when no record of it
arrived for a short window. Hook and syslog lines are events of their own.
"""

import time

cWindowSeconds = 2.0
cMaxPending = 50000
# LOGIN and CONFIG_CHANGE are not here: a SYSCALL record may come with them.
lStandalonePrefixes = ("USER_", "CRED_", "DAEMON_", "SERVICE_", "SYSTEM_", "ANOM_", "USYS_", "GRP_", "ADD_", "DEL_", "ROLE_", "ACCT_")


class Correlator:

  def __init__(self, pWindow: float = cWindowSeconds):
    self.vWindow = float(pWindow)
    self.dPending = {}
    self.lReady = []

  def mAdd(self, pRecord: dict, pNow: float | None = None) -> None:
    vNow = time.time() if pNow is None else pNow
    vKey = pRecord.get("correlation")
    if not vKey or not str(vKey).startswith("audit:"):
      self.lReady.append({"key": str(vKey or pRecord.get("source_key") or ""), "records": [pRecord], "weak": False, "uid": None})
      return
    dEntry = self.dPending.get(vKey)
    if dEntry is None:
      if len(self.dPending) >= cMaxPending:
        # Never keep more than cMaxPending events in memory: the oldest goes
        # out as it is.
        vOldest = next(iter(self.dPending))
        self.lReady.append({"key": vOldest, "records": self.dPending.pop(vOldest)["records"], "weak": False, "uid": vOldest})
      dEntry = {"records": [], "last": vNow, "done": False}
      self.dPending[vKey] = dEntry
    dEntry["records"].append(pRecord)
    dEntry["last"] = vNow
    vType = str((pRecord.get("fields") or {}).get("type") or "")
    if vType == "EOE" or (vType.startswith(lStandalonePrefixes) and len(dEntry["records"]) == 1):
      dEntry["done"] = True

  def mDue(self, pNow: float | None = None, pForce: bool = False, pWatermark: float | None = None) -> list[dict]:
    vNow = time.time() if pNow is None else pNow
    lDue = self.lReady
    self.lReady = []
    for vKey in list(self.dPending):
      dEntry = self.dPending[vKey]
      if pForce or dEntry["done"] or vNow - dEntry["last"] >= self.vWindow:
        lDue.append({"key": vKey, "records": dEntry["records"], "weak": False, "uid": vKey})
        del self.dPending[vKey]
    return lDue

  def mPendingCount(self) -> int:
    return len(self.dPending) + len(self.lReady)
