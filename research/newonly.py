"""Stage only what has never been ruled on.

`curate` and `stage` re-emit the whole corpus every run. After four rounds most of
it already carries a verdict, and re-reading 600 offers to find the 80 new ones is
the slow way to get the same answer.

    python research/newonly.py curate     # -> data/curation_new.json
    python research/newonly.py stage      # -> data/remote_new.json
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

WHAT = sys.argv[1] if len(sys.argv) > 1 else "curate"
CAND, VERD, OUT = {
    "curate": ("curation_candidates.json", "curation_verdicts.json", "curation_new.json"),
    "stage": ("remote_candidates.json", "remote_verdicts.json", "remote_new.json"),
}[WHAT]

cand = json.load(open(os.path.join(DATA, CAND), encoding="utf-8"))
vp = os.path.join(DATA, VERD)
seen = set()
if os.path.exists(vp):
    seen = {v["key"] for v in json.load(open(vp, encoding="utf-8")) if v.get("key")}

new = [c for c in cand if c.get("key") not in seen]
for c in new:
    for k in ("description", "evidence"):
        if k in c:
            c[k] = re.sub(r"\s+", " ", c[k])[:420]
    c.pop("id", None)
p = os.path.join(DATA, OUT)
json.dump(new, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{len(cand)} candidats, {len(seen)} deja juges -> {len(new)} a lire  ({p})")
print(f"  {os.path.getsize(p) / 1024:.0f} Ko")
