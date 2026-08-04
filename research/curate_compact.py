"""Two-pass reading for a curation queue that is too big to read in one go.

`curate` stages every candidate with 700 characters of description. At 400+
offers that is more text than can be held at once, and most of it is not what
decides: for the large majority, title + employer + city already settles it. So
pass 1 prints only that, and pass 2 pulls the description for the handful that
are genuinely ambiguous.

    python research/curate_compact.py <spec.json>              # pass 1, compact
    python research/curate_compact.py <spec.json> --keys a,b,c # pass 2, detail
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run, norm

spec = next((a for a in sys.argv[1:] if a.endswith(".json")), os.path.join(ROOT, "spec_business.json"))
run = Run(spec)
cand = json.load(open(os.path.join(run.datadir, "curation_candidates.json"), encoding="utf-8"))
vp = os.path.join(run.datadir, "curation_verdicts.json")
seen = set()
if os.path.exists(vp):
    seen = {v["key"] for v in json.load(open(vp, encoding="utf-8")) if v.get("key")}
todo = [c for c in cand if c.get("key") not in seen]

keys = None
for a in sys.argv[1:]:
    if a.startswith("--keys"):
        keys = set(a.split("=", 1)[1].split(",")) if "=" in a else None
if keys is None and "--keys" in sys.argv:
    keys = set(sys.argv[sys.argv.index("--keys") + 1].split(","))

if keys:
    for c in todo:
        if c["key"] in keys:
            print(f"\n=== [{c['key']}] {c['job_title']}")
            print(f"    {c.get('company', '')} | {c.get('country', '')} | "
                  f"{c.get('sector', '')} | {c.get('function', '')}")
            print(f"    {c['url'][:110]}")
            print("   ", re.sub(r"\s+", " ", c.get("description", ""))[:700])
    sys.exit()

print(f"{len(cand)} candidats, {len(seen)} deja juges, {len(todo)} a lire\n")
# a compact hint of what the ad is about, without the paragraph
FAM = [("COMM", r"commercial|sales|vente|account|affaires|business develop|client|export|secteur"),
       ("GRAD", r"graduate|trainee|jeune diplome|young|leadership program|vie\b|volontariat"),
       ("CONS", r"consultant|conseil|audit|analyst|strateg|transformation"),
       ("ACHT", r"acheteur|buyer|achats|procurement|sourcing|category|approvision"),
       ("DATA", r"data|business intelligence|\bbi\b|power ?bi|product owner|product manager")]
for i, c in enumerate(todo):
    blob = norm(c["job_title"] + " " + c.get("function", ""))
    fam = "/".join(t for t, rx in FAM if re.search(rx, blob)) or "?"
    print(f"{i:4d} [{c['key']}] {fam:14s} {c['job_title'][:56]:58s} "
          f"{(c.get('company') or '')[:26]:28s} {(c.get('sector') or '')[:20]}")
