"""Les blocs d'etiquettes que les sources publient elles-memes, extraits tels quels.

Deux blocs seulement, parce que ce sont les deux que les sources impriment
litteralement:

  MarocAnnonces  "Domaine : X Fonction : Y Contrat : Z Entreprise : W Ville : V"
  LinkedIn       "... Fonction X Secteurs Y Les recommandations ..."

`enrich_fields.py` n'attrapait que la forme longue du pied LinkedIn (les quatre
champs separes par " - "). Beaucoup d'annonces n'en publient que la fin, et
MarocAnnonces n'a jamais ete lu du tout. Ce script sort les valeurs brutes; le
verdict se prend en les lisant, parce que l'annonceur se trompe de rubrique
assez souvent pour qu'une reprise aveugle soit fausse (un "Acheteur Import"
classe en "RH/Personnel", un "Acheteur senior" en "Production").

    python research/labels.py [lean|business]
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run

track = sys.argv[1] if len(sys.argv) > 1 else "business"
run = Run(os.path.join(ROOT, "spec.json" if track == "lean" else "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "field_candidates.json"), encoding="utf-8"))
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))
_fv = os.path.join(run.datadir, "field_verdicts.json")
FV = {v["key"]: v for v in json.load(open(_fv, encoding="utf-8"))} if os.path.exists(_fv) else {}
for x in cand:
    for f, v in FV.get(x["key"], {}).items():
        if f not in ("key", "reason"):
            x["current"][f] = v

STOP = (r"(?=\s+(?:Domaine|Fonction|Contrat|Entreprise|Ville|Annonceur|Salaire|Avantage|"
        r"Niveau|R[ée]mun[ée]ration|Type de contrat)\s*:|\s*$)")
MA = {f: re.compile(r"\b" + lbl + r"\s*:\s*(.{2,60}?)" + STOP)
      for f, lbl in (("sector", "Domaine"), ("function", "Fonction"),
                     ("contract_type", "Contrat"), ("company", "Entreprise"),
                     ("city", "Ville"))}
# le pied LinkedIn, y compris quand la source n'en publie que la fin
LI = {
    "sector": re.compile(r"Secteurs?\s+(.{3,80}?)\s+(?:Les recommandations|Voir qui|"
                         r"R[ée]f[ée]rences|Recevez|Similar jobs)"),
    "function": re.compile(r"Fonction\s+(.{3,70}?)\s+Secteurs?\s"),
    "contract_type": re.compile(r"Type d.emploi\s+(.{2,40}?)\s+(?:-\s+)?(?:Fonction|Secteurs?)"),
}
NOISE = re.compile(r"^\s*(autre|non pertinent|not applicable|n/?a|indifferent|"
                   r"a discuter|confidential|anonyme)\s*$", re.I)


def clean(v):
    v = re.sub(r"\s+", " ", (v or "")).strip(" -:|,.")
    return "" if not v or NOISE.match(v) or len(v) > 70 else v


cols = ("sector", "function", "contract_type", "company", "city")
n = 0
for x in cand:
    body = re.sub(r"\s+", " ", (ft.get(x["url"]) or {}).get("text", "") or "")
    if not body:
        continue
    got = {}
    for f in cols:
        if str(x["current"].get(f, "") or "").strip():
            continue
        for src in (MA, LI):
            m = src.get(f) and src[f].search(body)
            if m and clean(m[1]):
                got[f] = clean(m[1])
                break
    if got:
        n += 1
        print(f"[{x['key']}] {x['job_title'][:58]}")
        print("   " + "  |  ".join(f"{f}={v}" for f, v in got.items()))
print(f"\n{n} offres ont au moins une etiquette publiee pour une colonne vide")
