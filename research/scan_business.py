"""Une ligne dense par cellule vide de la piste business: la phrase qui la remplit, ou rien.

Meme principe que research/scan.py cote Lean. Le script ne decide rien - il va
chercher dans le corps de l'annonce les passages ou la source publie la valeur
manquante, et les imprime. Si rien ne sort, c'est que la source n'a rien publie,
et la cellule doit rester vide.

    python research/scan_business.py [colonne] [lean|business]
        colonnes: experience, secteur, fonction, entreprise, contrat, deadline
"""
import sys, io, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run

track = sys.argv[2] if len(sys.argv) > 2 else "business"
run = Run(os.path.join(ROOT, "spec.json" if track == "lean" else "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "field_candidates.json"), encoding="utf-8"))
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))

# 'current' est la valeur brute de la ligne, AVANT apply_fields: sans cette
# superposition on relit 216 cellules dont 127 sont deja renseignees par un verdict.
_fv = os.path.join(run.datadir, "field_verdicts.json")
FV = {v["key"]: v for v in json.load(open(_fv, encoding="utf-8"))} if os.path.exists(_fv) else {}
for x in cand:
    for f, v in FV.get(x["key"], {}).items():
        if f not in ("key", "reason"):
            x["current"][f] = v

# ou chaque source publie la valeur. Les motifs sont larges: on relit ensuite.
PROBES = {
    "experience_required": [
        r"[^.|]{0,110}(?:exp[ée]rience|experience|anciennet[ée]|justifi\w+)[^.|]{0,110}",
        r"[^.|]{0,80}\b\d{1,2}\s*(?:[-–aà]|to)?\s*\d{0,2}\s*(?:ans?|ann[ée]es?|years?)[^.|]{0,80}",
        r"[^.|]{0,70}(?:d[ée]butant|jeune diplom|fraichement diplom|fra[îi]chement|entry.level|"
        r"graduate|nouveau diplom|sortie d.[ée]cole)[^.|]{0,70}",
    ],
    "sector": [r"Secteurs?\s+[^|]{3,80}", r"[^.|]{0,60}(?:secteur|industrie|domaine)\s+(?:de |d.|du )?[^.|]{3,60}"],
    "function": [r"Fonction\s+[^|]{3,70}", r"Niveau hi[ée]rarchique\s+[^|]{3,60}"],
    "company": [r"^[^|]{0,160}", r"[^.|]{0,60}(?:notre client|pour le compte de|rejoign\w+|au sein de)[^.|]{0,90}"],
    "contract_type": [r"[^.|]{0,60}(?:CDI|CDD|int[ée]rim|temps plein|full[- ]time|part[- ]time|"
                      r"freelance|stage|contrat|permanent|Type d.emploi)[^.|]{0,60}"],
    "deadline": [r"[^.|]{0,70}(?:date limite|avant le|jusqu.au|cl[ôo]ture|deadline|postulez avant|"
                 r"expire le|closing date)[^.|]{0,70}"],
}
ALIAS = {"experience": "experience_required", "secteur": "sector", "fonction": "function",
         "entreprise": "company", "contrat": "contract_type", "deadline": "deadline"}

col = ALIAS.get((sys.argv[1] if len(sys.argv) > 1 else "experience").lower())
if not col:
    sys.exit("colonne inconnue: " + ", ".join(ALIAS))
pats = [re.compile(p, re.I | re.M) for p in PROBES[col]]

n_vide = n_parle = 0
for x in cand:
    if str(x["current"].get(col, "") or "").strip():
        continue
    n_vide += 1
    body = re.sub(r"\s+", " ", (ft.get(x["url"]) or {}).get("text", "") or x.get("text", "") or "")
    if not body:
        print(f"\n[{x['key']}] {x['job_title'][:66]} | PAS DE CORPS")
        continue
    seen, out = set(), []
    for p in pats:
        for m in p.finditer(body):
            s = re.sub(r"\s+", " ", m.group(0)).strip()
            if len(s) < 12 or s[:34].lower() in seen:
                continue
            seen.add(s[:34].lower())
            out.append(s)
            if len(out) >= 5:
                break
        if len(out) >= 5:
            break
    if out:
        n_parle += 1
        print(f"\n[{x['key']}] {x['job_title'][:66]} | {(x.get('company') or '?')[:28]}")
        for s in out:
            print("   . " + s[:190])

print(f"\n{col}: {n_vide} cellules vides, {n_parle} ont au moins un passage a lire")
