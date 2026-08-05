"""La date limite, la ou la source l'imprime: le pied d'annonce Rekrute.

Rekrute ecrit "Postulez avant le JJ/MM/AAAA" a la fin de chaque annonce. Le
scraper ne lisait que la carte de resultat, ou cette ligne n'existe pas: c'est
pour cela que la colonne etait vide sur des annonces qui publient pourtant leur
date. Rien n'est deduit ici - la date est recopiee telle que la source l'ecrit.

    python research/deadlines.py [lean|business] [--write]
"""
import sys, io, os, re, json, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run

track = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "business"
run = Run(os.path.join(ROOT, "spec.json" if track == "lean" else "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "field_candidates.json"), encoding="utf-8"))
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))
_fv = os.path.join(run.datadir, "field_verdicts.json")
FV = {v["key"]: v for v in json.load(open(_fv, encoding="utf-8"))} if os.path.exists(_fv) else {}

PAT = re.compile(r"Postulez avant le\s*(\d{2})[/-](\d{2})[/-](\d{4})", re.I)
today = datetime.date.today()

out, past = [], []
for x in cand:
    if str(FV.get(x["key"], {}).get("deadline", "") or x["current"].get("deadline", "") or "").strip():
        continue
    body = re.sub(r"\s+", " ", (ft.get(x["url"]) or {}).get("text", "") or "")
    m = PAT.search(body)
    if not m:
        continue
    d = datetime.date(int(m[3]), int(m[2]), int(m[1]))
    rec = (x["key"], x["job_title"], d, m.group(0))
    (past if d < today else out).append(rec)

print(f"piste {track}: {len(out)} dates limites a venir, {len(past)} deja passees")
for k, t, d, q in sorted(out, key=lambda r: r[2])[:40]:
    print(f"  {d}  {t[:56]:58s} {q}")
if past:
    print("\n  --- deja passees (l'annonce elle-meme ferme la candidature) ---")
    for k, t, d, q in sorted(past, key=lambda r: r[2]):
        print(f"  {d}  {t[:56]:58s} {q}")

if "--write" in sys.argv:
    p = os.path.join(run.datadir, "field_verdicts.json")
    old = {v["key"]: v for v in json.load(open(p, encoding="utf-8"))}
    for k, t, d, q in out + past:
        e = old.setdefault(k, {"key": k})
        e["deadline"] = d.strftime("%d/%m/%Y")
        e["reason"] = (e.get("reason", "") + " | " if e.get("reason") else "") + \
            f"date limite imprimee par la source en pied d'annonce: \"{q}\""
    json.dump(list(old.values()), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> {p} (+{len(out) + len(past)}, {len(old)} verdicts)")
