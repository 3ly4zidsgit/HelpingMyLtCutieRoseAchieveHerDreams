"""Find the same ad republished elsewhere in the workbook.

An aggregator that will not hand over its detail page has usually only mirrored an
ad that is already in the list under its real source, with every column filled.
Matching the two is worth more than fighting the captcha - and it is the only
honest way to fill those rows, since nothing may be invented."""
import sys, io, os, re, json, difflib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import jid, norm

rows = json.load(open(os.path.join(ROOT, "data", "audit_rows.json"), encoding="utf-8"))
for r in rows:
    r["_k"] = jid(r["LIEN DE L'OFFRE"])

BLOCKED = sys.argv[1:]
STOP = re.compile(r"\b(h/f|f/h|m/f|maroc|morocco)\b|\(.*?\)|[-–|]")


def core_title(t):
    return norm(STOP.sub(" ", t or ""))


for k in BLOCKED:
    src = next((r for r in rows if r["_k"] == k), None)
    if not src:
        print(f"{k}: introuvable")
        continue
    st = core_title(src.get("Titre du poste"))
    print(f"\n===== {k} | {src.get('Titre du poste')}")
    print(f"      {(src.get('Description (extrait)') or '')[-160:]}")
    cands = []
    for r in rows:
        if r["_k"] == k:
            continue
        s = difflib.SequenceMatcher(None, st, core_title(r.get("Titre du poste"))).ratio()
        if s >= 0.72:
            cands.append((s, r))
    for s, r in sorted(cands, reverse=True, key=lambda x: x[0])[:4]:
        print(f"   {s:.2f} [{r['_k']}] {r.get('Titre du poste')[:52]:54s} "
              f"ENT={r.get('Entreprise')[:26]:28s} VILLE={r.get('Ville')[:14]:16s} "
              f"EXP={r.get('Expérience requise')[:22]}")
