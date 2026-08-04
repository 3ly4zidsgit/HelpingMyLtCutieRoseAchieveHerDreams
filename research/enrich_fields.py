"""Type de contrat / Fonction / Secteur, lus la ou la source les publie.

LinkedIn imprime un bloc en pied d'annonce - "Niveau hierarchique X Type d'emploi
Y Fonction Z Secteurs W" - et Rekrute une ligne "Type de contrat : ...". C'est la
source qui parle, pas une deduction.

Le piege est le mot lui-meme: chercher "Fonction" sans frontiere attrape
"fonctionnelles", "fonctionnement des infrastructures", "besoins fonctionnels".
D'ou l'ancrage sur le bloc, et la verification que ce qui sort ressemble a une
valeur et non a un morceau de phrase.

    python research/enrich_fields.py [--write]
"""
import sys, io, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run

run = Run(os.path.join(ROOT, "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "field_candidates.json"), encoding="utf-8"))
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))

# le pied d'annonce LinkedIn, pris en bloc
# Le corps est d'abord aplati (tous les blancs -> une espace), sinon un separateur
# "espaces / retour ligne / tiret optionnel" repete quatre fois fait exploser le
# moteur en backtracking: la meme regex mettait plus de deux minutes sur 359 corps.
LI_FOOT = re.compile(
    r"Niveau hi[ée]rarchique\s+(?P<niv>.{2,40}?)\s+-\s+"
    r"Type d.emploi\s+(?P<ctr>.{2,40}?)\s+-\s+"
    r"Fonction\s+(?P<fn>.{2,70}?)\s+-\s+"
    r"Secteurs?\s+(?P<sec>.{2,80}?)\s+(?:Les recommandations|Voir qui|R[ée]f[ée]rences)")
LI_CTR = re.compile(r"Type d.emploi\s+(.{2,40}?)\s+-\s+(?:Fonction|Secteurs?)")
RK_CTR = re.compile(r"Type de contrat (?:propos[ée])?\s*[:：]\s*([^|]{2,40}?)\s{2,}", re.I)
# MarocAnnonces aligne ses etiquettes sur une seule ligne: il faut s'arreter a la
# suivante, sinon "Contrat : CDI" devient "CDI Entreprise : AFRICA STAFFING"
MA_CTR = re.compile(r"Contrat\s*[:：]\s*(.{2,30}?)\s*(?:Entreprise|Salaire|Niveau|Ville|"
                    r"Annonceur|Avantage|Lieu|R[ée]mun[ée]ration|•|$)", re.I)
NOISE = re.compile(r"^\s*(non pertinent|not applicable|n/?a|autre|indifferent|a discuter)\s*$", re.I)


def clean(v):
    v = re.sub(r"\s+", " ", (v or "")).strip(" -:|,")
    if not v or NOISE.match(v) or len(v) > 70:
        return ""
    # un fragment de phrase n'est pas une valeur de champ
    if re.search(r"\b(le|la|les|des|du|de la|nos|notre|vous|nous)\b", v.lower()) and len(v) > 28:
        return ""
    return v


out = collections.defaultdict(dict)
stats = collections.Counter()
for x in cand:
    cur, key = x["current"], x["key"]
    body = re.sub(r"[ \t]+", " ", (ft.get(x["url"]) or {}).get("text", ""))
    if not body:
        continue
    m = LI_FOOT.search(body)
    got = {}
    if m:
        got["contract_type"] = clean(m.group("ctr"))
        got["function"] = clean(m.group("fn"))
        got["sector"] = clean(m.group("sec"))
    else:
        c = LI_CTR.search(body) or RK_CTR.search(body) or MA_CTR.search(body)
        if c:
            got["contract_type"] = clean(c.group(1))
    for f, v in got.items():
        if v and not str(cur.get(f, "")).strip():
            out[key][f] = v
            stats[f] += 1

print("valeurs trouvees:", dict(stats))
shown = 0
for k, v in out.items():
    if shown >= 25:
        break
    shown += 1
    t = next(x["job_title"] for x in cand if x["key"] == k)
    print(f"  {t[:40]:42s} {v}")

if "--write" in sys.argv:
    p = os.path.join(run.datadir, "field_verdicts.json")
    old = {v["key"]: v for v in json.load(open(p, encoding="utf-8"))} if os.path.exists(p) else {}
    for k, v in out.items():
        e = old.setdefault(k, {"key": k})
        e.update(v)
        e["reason"] = (e.get("reason", "") + " | " if e.get("reason") else "") + \
            "contrat/fonction/secteur repris du bloc que la source publie en pied d'annonce"
    json.dump(list(old.values()), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {p} ({len(old)} verdicts)")
