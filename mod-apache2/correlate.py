"""Correlation: from three sources to one request.

  - The key is the UNIQUE_ID: the access line, the error.log lines and the
    audit record with the same UNIQUE_ID become one transaction.
  - Sources do not arrive in order: a transaction waits a correlation window
    (5 s by default) from its first record before it is evaluated.
  - Access logs in the formats Apache writes by default (combined,
    vhost_combined, common) have no UNIQUE_ID. Such an access line and the
    ModSecurity records of a request without an access line are paired when
    the first of the two is due (mPair), when the audit record, with the
    whole request line and the status, has usually arrived too: same client
    IP, time within ±2 s (the access line has whole seconds) and, when both
    sides know them, the same method, URI, status and path. The candidate
    that agrees in more of them wins, then the nearest in time, then the
    oldest, so identical requests in the same second pair in order. The
    transaction is marked as weakly correlated.
  - error.log lines without UNIQUE_ID (PHP errors, for example) join, at
    once, a transaction of the same IP within ±2 s; otherwise they are an
    event of their own. Lines without a client (server notices) are events
    of their own at once.
"""

import collections
import time
import urllib.parse

from backend.core.timeutil import fStorageToEpoch

cMaxPending = 50000
# Which record gives the time of a transaction: the audit record has
# microseconds and its offset, the access line its offset, error.log only the
# local time.
dTimeRanks = {"audit": 0, "access": 1, "error": 2}
lRequestFacts = ["method", "uri", "status", "path"]


def fPathKey(pPath) -> str | None:
  # error.log has the decoded path (ModSecurity's [uri]), the access line and
  # the audit record the one sent by the client.
  if pPath in (None, ""):
    return None
  return urllib.parse.unquote(str(pPath))


class Correlator:

  def __init__(self, pWindow: float, pWeakSeconds: float):
    self.vWindow = float(pWindow)
    self.vWeakSeconds = float(pWeakSeconds)
    self.dPending = collections.OrderedDict()
    # (ip, path) -> transaction keys, for the weak correlation.
    self.dByIpPath = collections.defaultdict(list)
    self.dByIp = collections.defaultdict(list)
    self.vSequence = 0

  def mNewKey(self, pPrefix: str) -> str:
    self.vSequence += 1
    return f"{pPrefix}:{self.vSequence}"

  def mCreate(self, pKey: str, pRecord: dict, pNow: float, pDueNow: bool = False) -> dict:
    dTransaction = {
      "key": pKey, "records": [], "first": pNow, "due": pNow if pDueNow else pNow + self.vWindow,
      "weak": False, "uid": None, "ip": None, "path": None, "time": None, "time_rank": None, "coarse": False,
      "has_access": False, "request": {}
    }
    self.dPending[pKey] = dTransaction
    return dTransaction

  def mAttach(self, pTransaction: dict, pRecord: dict) -> None:
    pTransaction["records"].append(pRecord)
    dFields = pRecord.get("fields", {})
    vSource = pRecord.get("source")
    if pRecord.get("correlation") and not pTransaction["uid"]:
      pTransaction["uid"] = pRecord["correlation"]
    if vSource == "access":
      pTransaction["has_access"] = True
    vIp = dFields.get("client_ip")
    if vIp and not pTransaction["ip"]:
      pTransaction["ip"] = vIp
      self.dByIp[vIp].append(pTransaction["key"])
    vPath = fPathKey(dFields.get("path"))
    if vPath and not pTransaction["path"] and pTransaction["ip"]:
      pTransaction["path"] = vPath
      self.dByIpPath[(pTransaction["ip"], vPath)].append(pTransaction["key"])
    # What the request was, to pair an access line without UNIQUE_ID: from
    # the access line or the audit record (error.log only knows the path).
    dRequest = pTransaction["request"]
    if vSource in ("access", "audit"):
      for vName in ("method", "uri", "status"):
        if dFields.get(vName) not in (None, "") and vName not in dRequest:
          dRequest[vName] = dFields[vName]
    if vPath and "path" not in dRequest:
      dRequest["path"] = vPath
    vRank = dTimeRanks.get(vSource, 3)
    if pRecord.get("time") and (pTransaction["time_rank"] is None or vRank < pTransaction["time_rank"]):
      pTransaction["time"] = fStorageToEpoch(pRecord["time"])
      pTransaction["time_rank"] = vRank
      # The formats Apache writes by default have whole seconds.
      pTransaction["coarse"] = vSource == "access" and pTransaction["time"] == int(pTransaction["time"])

  def mFindWeak(self, pRecord: dict) -> dict | None:
    # For an error.log line without UNIQUE_ID: the nearest transaction of the
    # same IP (and path, if the line has one).
    dFields = pRecord.get("fields", {})
    vIp = dFields.get("client_ip")
    if not vIp:
      return None
    vPath = fPathKey(dFields.get("path"))
    lKeys = self.dByIpPath.get((vIp, vPath), []) if vPath else self.dByIp.get(vIp, [])
    vTime = fStorageToEpoch(pRecord["time"]) if pRecord.get("time") else None
    dBest = None
    vBestDistance = None
    for vKey in reversed(lKeys):
      dTransaction = self.dPending.get(vKey)
      if dTransaction is None:
        continue
      if vTime is None or dTransaction["time"] is None:
        continue
      vDistance = abs(dTransaction["time"] - vTime)
      if vDistance <= self.vWeakSeconds and (vBestDistance is None or vDistance < vBestDistance):
        dBest = dTransaction
        vBestDistance = vDistance
    return dBest

  def mAdd(self, pRecord: dict, pNow: float | None = None) -> None:
    vNow = time.time() if pNow is None else pNow
    vSource = pRecord.get("source")
    vUid = pRecord.get("correlation")
    if pRecord.get("parse_status") == "unparsed":
      dTransaction = self.mCreate(self.mNewKey("u"), pRecord, vNow, True)
      self.mAttach(dTransaction, pRecord)
      return
    if vUid:
      vKey = "uid:" + vUid
      dTransaction = self.dPending.get(vKey)
      if dTransaction is None:
        dTransaction = self.mCreate(vKey, pRecord, vNow)
      self.mAttach(dTransaction, pRecord)
      return
    if vSource == "access":
      # Paired with the records of its request when it is due (mPair).
      dTransaction = self.mCreate(self.mNewKey("a"), pRecord, vNow)
      self.mAttach(dTransaction, pRecord)
      return
    # error.log without UNIQUE_ID
    if pRecord.get("fields", {}).get("client_ip"):
      dWeak = self.mFindWeak(pRecord)
      if dWeak is not None:
        dWeak["weak"] = True
        self.mAttach(dWeak, pRecord)
        return
      dTransaction = self.mCreate(self.mNewKey("e"), pRecord, vNow)
      self.mAttach(dTransaction, pRecord)
      return
    dTransaction = self.mCreate(self.mNewKey("s"), pRecord, vNow, True)
    self.mAttach(dTransaction, pRecord)

  def mDistance(self, pAccess: dict, pOther: dict) -> float:
    # A time with whole seconds stands for that whole second.
    vStart = pAccess["time"]
    vEnd = vStart + (1.0 if pAccess["coarse"] else 0.0)
    vTime = pOther["time"]
    if vStart <= vTime <= vEnd:
      return 0.0
    return min(abs(vTime - vStart), abs(vTime - vEnd))

  def mAgreement(self, pAccess: dict, pOther: dict) -> int | None:
    # How many facts of the request agree; None when one differs.
    vAgreed = 0
    for vName in lRequestFacts:
      vAccess = pAccess["request"].get(vName)
      vOther = pOther["request"].get(vName)
      if vAccess is None or vOther is None:
        continue
      if vAccess != vOther:
        return None
      vAgreed += 1
    return vAgreed

  def mPair(self, pTransaction: dict) -> dict | None:
    # An access line without UNIQUE_ID looks for the records of its request
    # that have no access line, and those records for that access line.
    vAccessSide = pTransaction["has_access"] and pTransaction["uid"] is None
    if not vAccessSide and pTransaction["has_access"]:
      return None
    if not pTransaction["ip"] or pTransaction["time"] is None:
      return None
    vMost = sum(1 for vName in lRequestFacts if pTransaction["request"].get(vName) is not None)
    dBest = None
    tBest = None
    for vKey in self.dByIp.get(pTransaction["ip"], []):
      dCandidate = self.dPending.get(vKey)
      if dCandidate is None or dCandidate is pTransaction or dCandidate["time"] is None:
        continue
      if vAccessSide and dCandidate["has_access"]:
        continue
      if not vAccessSide and not (dCandidate["has_access"] and dCandidate["uid"] is None):
        continue
      dAccess, dOther = (pTransaction, dCandidate) if vAccessSide else (dCandidate, pTransaction)
      vAgreed = self.mAgreement(dAccess, dOther)
      if vAgreed is None:
        continue
      vDistance = self.mDistance(dAccess, dOther)
      if vDistance > self.vWeakSeconds:
        continue
      # The keys are in order of arrival: on a tie the oldest stays.
      tRank = (-vAgreed, vDistance)
      if tBest is None or tRank < tBest:
        dBest = dCandidate
        tBest = tRank
        if vAgreed == vMost and vDistance == 0:
          break
    return dBest

  def mMerge(self, pTransaction: dict, pPartner: dict) -> None:
    pTransaction["records"].extend(pPartner["records"])
    pTransaction["uid"] = pTransaction["uid"] or pPartner["uid"]
    pTransaction["has_access"] = pTransaction["has_access"] or pPartner["has_access"]
    pTransaction["weak"] = True

  def mDue(self, pNow: float | None = None, pForce: bool = False, pWatermark: float | None = None) -> list[dict]:
    # pWatermark: log time up to which every source behind (catching up)
    # has been read. A transaction after it waits, even past its window: its
    # other records may still be in the part of a file not read yet.
    vNow = time.time() if pNow is None else pNow
    lDue = []
    for vKey in list(self.dPending):
      dTransaction = self.dPending.get(vKey)
      if dTransaction is None:
        # Already paired with a transaction due before it.
        continue
      vWaiting = pWatermark is not None and dTransaction["time"] is not None and dTransaction["time"] + self.vWindow > pWatermark
      if pForce or (dTransaction["due"] <= vNow and not vWaiting) or len(self.dPending) > cMaxPending:
        self.mRemove(dTransaction)
        dPartner = self.mPair(dTransaction)
        if dPartner is not None:
          self.mRemove(dPartner)
          self.mMerge(dTransaction, dPartner)
        lDue.append(dTransaction)
    return lDue

  def mRemove(self, pTransaction: dict) -> None:
    self.dPending.pop(pTransaction["key"], None)
    if pTransaction["ip"]:
      self.mForget(self.dByIp, pTransaction["ip"], pTransaction["key"])
      if pTransaction["path"]:
        self.mForget(self.dByIpPath, (pTransaction["ip"], pTransaction["path"]), pTransaction["key"])

  def mForget(self, pIndex: dict, pIndexKey, pKey: str) -> None:
    lKeys = pIndex.get(pIndexKey)
    if not lKeys:
      return
    try:
      lKeys.remove(pKey)
    except ValueError:
      pass
    if not lKeys:
      pIndex.pop(pIndexKey, None)

  def mPendingCount(self) -> int:
    return len(self.dPending)
