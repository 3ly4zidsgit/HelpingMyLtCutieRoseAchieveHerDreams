"""Remplir 'Experience requise' pour la piste business, en lisant les annonces.

C'est la colonne qui decide de la feuille, donc c'est celle qui compte. Le piege
n'est pas de trouver un nombre d'annees - il y en a partout - c'est de ne pas
prendre l'age de la societe pour une exigence: "conveyor belts for more than 50
years", "accompagne depuis 15 ans", "depuis plus de 40 ans", "certifie Top
Employeur pour 3 annees consecutives". Une duree ne compte que collee a un mot
d'experience, et jamais collee a un mot d'histoire d'entreprise.

    python research/enrich_business.py           # montrer phrase -> valeur
    python research/enrich_business.py --write   # ecrire les verdicts
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run, norm
from build import exp_floor, normalize_exp

run = Run(os.path.join(ROOT, "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "field_candidates.json"), encoding="utf-8"))

# une duree qui parle de la societe, pas du candidat
CORP = re.compile(r"depuis (plus de )?\d|for (more than|over) \d|\d+\s*(ans|annees|years)"
                  r"\s*(d.(existence|histoire|experience du groupe)|of (history|excellence))"
                  r"|fondee? en|creee? en|since \d{4}|chiffre d.affaires|milliard|million"
                  r"|top employeur|annees consecutives|celebre|anniversaire|\d+\s*collaborateurs"
                  r"|\d+\s*employees|\d+\s*consultants|leader depuis|present dans \d"
                  # "un groupe leader ... avec plus de 25 ans d'experience" parle de
                  # l'anciennete de la societe, pas de celle du candidat
                  r"|(groupe|societe|soci[ée]t[ée]|entreprise|cabinet|filiale|leader|acteur|"
                  r"marque|agence)[^.]{0,70}\d{1,2}\s*(ans|annees|years)"
                  r"|nous (accompagnons|intervenons|operons)|notre (groupe|histoire)", re.I)
# un plafond: "jusqu'a 1 an", "up to 2 years", "moins de 3 ans" -> le plancher est zero
CEIL = re.compile(r"(?:jusqu.[àa]|up to|au plus|moins de|maximum de)\s*(?P<c>\d{1,2})"
                  r"\s*\+?\s*(?:ans?|annees?|years?)", re.I)
# une duree collee a un mot d'experience: c'est une exigence
REQ = re.compile(
    r"(?P<a>\d{1,2})\s*(?:ans?|annees?|years?)?\s*(?:[-–]|\bto\b|\ba\b|\bà\b)\s*"
    r"(?P<b>\d{1,2})\s*\+?\s*(?:ans?|annees?|years?)"
    r"|(?:minimum|min\.?|au moins|at least|plus de|\+\s*de)\s*(?:de\s*)?(?P<m>\d{1,2})"
    r"\s*(?:ans?|annees?|years?)"
    r"|(?P<n>\d{1,2})\s*\+?\s*(?:ans?|annees?|years?)\s*(?:d.?experience|of experience|minimum|d.?exp)"
    r"|(?P<p>\d{1,2})\s*\+\s*(?:years?|ans?)", re.I)
EXPWORD = re.compile(r"experience|exp[ée]rience|anciennete|justifi", re.I)
ZERO = re.compile(r"d[ée]butant|jeune[s]? diplom|fraichement diplom|sans exp[ée]rience|premier emploi"
                  r"|entry.level|entry level|new grad|fresh graduate|no experience required"
                  r"|sortie d.[ée]cole|last year students", re.I)
VAGUE = re.compile(r"exp[ée]rience (confirm[ée]e|significative|solide|averee|reussie|prouvee"
                   r"|professionnelle|exigee|requise|obligatoire)|premiere exp[ée]rience"
                   r"|proven (track record|experience)|relevant experience", re.I)


def ans(n):
    return f"{n} an" if str(n) == "1" else f"{n} ans"


def pick(item):
    """(valeur, extrait cite) ou (None, None).

    Le jugement se fait sur une FENETRE autour du nombre, pas sur la phrase qui le
    contient quelque part: sans cela on cite une phrase ou le nombre n'apparait
    meme pas, et on ne voit plus que l'exigence lue n'est pas celle citee."""
    hay = " || ".join(list(item.get("evidence_experience") or []) + [item.get("text", "")])

    def window(m, w=70):
        return re.sub(r"\s+", " ", hay[max(0, m.start() - w):m.end() + w]).strip()

    # 1. un plafond explicite: le plancher est zero (programme jeunes diplomes)
    for m in CEIL.finditer(hay):
        win = window(m)
        if EXPWORD.search(win) and not CORP.search(win):
            return f"0 à {ans(m.group('c'))}", win
    # 2. une duree exigee, collee a un mot d'experience et loin de l'histoire de la boite
    for m in REQ.finditer(hay):
        win = window(m)
        if not EXPWORD.search(win) or CORP.search(win):
            continue
        g = m.groupdict()
        if g["a"] and g["b"]:
            return f"{g['a']} à {ans(g['b'])}", win
        for k in ("m", "n", "p"):
            if g[k]:
                return f"{ans(g[k])} minimum", win
    # 3. l'annonce dit qu'elle prend un debutant
    for m in ZERO.finditer(hay):
        win = window(m)
        if not CORP.search(win):
            return "0", win
    # 4. de l'experience est exigee, mais l'annonce ne la chiffre pas
    for m in VAGUE.finditer(hay):
        win = window(m)
        if not CORP.search(win):
            return "Expérience confirmée (durée non précisée)", win
    return None, None


out, shown = [], 0
stats = {"rempli": 0, "deja": 0, "muet": 0}
for it in cand:
    cur = it["current"].get("experience_required", "").strip()
    if cur:
        stats["deja"] += 1
        continue
    val, why = pick(it)
    if not val:
        stats["muet"] += 1
        continue
    stats["rempli"] += 1
    out.append({"key": it["key"], "experience_required": val,
                "reason": "lu dans le corps de l'annonce: '"
                          + re.sub(r"\s+", " ", why).strip()[:210] + "'"})
    if shown < 60:
        shown += 1
        f = exp_floor(val)
        print(f"{'JUN' if f == 0 else 'EXP'} {val:34s} <- {re.sub(r'  +', ' ', why)[:104]}")

print(f"\n{stats}   ({len(out)} verdicts d'experience)")
if "--write" in sys.argv:
    p = os.path.join(run.datadir, "field_verdicts.json")
    old = {v["key"]: v for v in json.load(open(p, encoding="utf-8"))} if os.path.exists(p) else {}
    for v in out:
        old.setdefault(v["key"], {}).update(v)
    json.dump(list(old.values()), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {p} ({len(old)} verdicts)")
