"""Merge r4_batch_*.json into data/field_verdicts.json (later rulings win).

    python research/merge_verdicts.py
"""
import sys, io, os, json, glob, shutil
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

fp = os.path.join(DATA, "field_verdicts.json")
cur = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else []
shutil.copy2(fp, os.path.join(ROOT, "backup",
             f"field_verdicts_{datetime.now():%Y%m%d_%H%M%S}.json"))
by = {}
for v in cur:
    if v.get("key"):
        by[v["key"]] = v
n0, added, updated = len(by), 0, 0
for p in sorted(glob.glob(os.path.join(DATA, "r4_batch_*.json"))):
    batch = json.load(open(p, encoding="utf-8"))
    for v in batch:
        k = v["key"]
        if k in by:
            by[k].update(v)
            updated += 1
        else:
            by[k] = v
            added += 1
    print(f"  {os.path.basename(p)}: {len(batch)} rulings")
out = list(by.values())
json.dump(out, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"field_verdicts.json: {n0} -> {len(out)} ({added} nouveaux, {updated} completes)")

# relevance drops read this round
dps = sorted(glob.glob(os.path.join(DATA, "r4_drops*.json")))
if dps:
    cp = os.path.join(DATA, "curation_verdicts.json")
    cv = json.load(open(cp, encoding="utf-8"))
    shutil.copy2(cp, os.path.join(ROOT, "backup",
                 f"curation_verdicts_{datetime.now():%Y%m%d_%H%M%S}.json"))
    seen = {v["key"] for v in cv if v.get("key")}
    drops = [d for p in dps for d in json.load(open(p, encoding="utf-8"))]
    n = 0
    for d in drops:
        if d["key"] in seen:
            for v in cv:
                if v.get("key") == d["key"]:
                    v.update(d)
        else:
            cv.append(d)
        n += 1
    json.dump(cv, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"curation_verdicts.json: {n} refus ajoutes/mis a jour -> {len(cv)} verdicts")
