"""One dense line per empty cell: the sentence in the ad that answers it, or
nothing at all. Reading 300 ads means reading the sentence that decides, not the
ad; anything that prints here is a quote the model still has to judge (a board
that writes 'Niveau hierarchique: Non pertinent' answers nothing).

    python research/scan.py [chunk_NN ...]
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import jid, norm

full = json.load(open(os.path.join(ROOT, "data", "fulltext.json"), encoding="utf-8"))
WL = os.path.join(ROOT, "data", "worklist")
names = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(WL) if f.startswith("chunk_"))

# an experience REQUIREMENT, not any sentence with a number in it
EXP = re.compile(
    r"(?:[^.;\n]{0,110})(?:"
    r"exp[ée]rience[^.;\n]{0,60}?\d{1,2}\s*(?:ans?|ann[ée]es?|mois)"
    r"|\d{1,2}\s*(?:\+|à|a|-|to)?\s*\d{0,2}\s*(?:ans?|ann[ée]es?|mois|years?|yrs?)[^.;\n]{0,40}?"
    r"(?:exp[ée]rience|experience|dans un poste|in a similar|of experience)"
    r"|(?:minimum|au moins|at least|min\.?)\s*\d{1,2}\s*(?:ans?|years?|mois|months?)"
    r"|\d{1,2}\s*(?:\+|à|a|-|to)\s*\d{1,2}\s*(?:ans?|years?)\s*(?:d.exp|of exp|exp)"
    r"|exp[ée]rience\s*(?:requise|exig[ée]e?|obligatoire|souhait[ée]e?|confirm[ée]e?|"
    r"significative|professionnelle|pr[ée]alable|minimale|r[ée]ussie|av[ée]r[ée]e)"
    r"|premi[èe]re exp[ée]rience|d[ée]butant[s]?\s*(?:accept|bienvenu|motiv)?"
    r"|jeune[s]? dipl[oô]m|fra[iî]chement dipl[oô]m|sans exp[ée]rience|avec ou sans exp"
    r"|entry[- ]level|new graduate|nouveaux dipl[oô]m|no (?:prior )?experience"
    r"|niveau d.exp[ée]rience\s*[:：]|years of experience|experience (?:required|in a similar)"
    r")(?:[^.;\n]{0,110})", re.I)
CTR = re.compile(r"[^.;\n|]{0,70}(?:type de contrat\s*[:：]|contrat\s*[:：]|employment type\s*[:：]"
                 r"|\ben cdi\b|\ben cdd\b|\bcontrat cdi\b|\bcdi\b|\bcdd\b|\bint[ée]rim\b"
                 r"|temps plein|full[- ]time|permanent contract|contrat de projet"
                 r"|contrat [àa] dur[ée]e)[^.;\n|]{0,70}", re.I)
DL = re.compile(r"[^.;\n|]{0,80}(?:date limite|limite de candidature|d[ée]lai de candidature"
                r"|dernier d[ée]lai|cl[oô]ture des candidatures|postuler avant|avant le \d"
                r"|jusqu.au \d{1,2}[/ ]|apply before|apply by \w|closing date|deadline\s*[:：]"
                r"|candidatures? ferm[ée]e?s?|n.est plus d.actualit[ée]|offre (?:a )?expir[ée]e?"
                r"|no longer accepting)[^.;\n|]{0,80}", re.I)
COMP = re.compile(r"[^.;\n|]{0,60}(?:entreprise\s*[:：]|soci[ée]t[ée]\s*[:：]|employeur\s*[:：]"
                  r"|annonceur\s*[:：]|company\s*[:：]|recrute pour|pour notre client"
                  r"|notre client)[^.;\n|]{0,80}", re.I)
CITY = re.compile(r"[^.;\n|]{0,50}(?:ville\s*[:：]|lieu de travail\s*[:：]|localisation\s*[:：]"
                  r"|location\s*[:：]|poste bas[ée]|site de|bas[ée] [àa] )[^.;\n|]{0,60}", re.I)
SECT = re.compile(r"[^.;\n|]{0,50}(?:secteur[s]? d.activit[ée]\s*[:：]|secteurs?\s*[:：]"
                  r"|domaine\s*[:：]|industry\s*[:：]|industrie\s*[:：])[^.;\n|]{0,60}", re.I)
FUNC = re.compile(r"[^.;\n|]{0,50}(?:fonction\s*[:：]|m[ée]tier\s*[:：]|job function\s*[:：]"
                  r"|job family\s*[:：]|d[ée]partement\s*[:：])[^.;\n|]{0,60}", re.I)
DATE = re.compile(r"[^.;\n|]{0,40}(?:publi[ée]e? le|date de publication|posted on|il y a \d"
                  r"|\d+ (?:days?|weeks?|months?) ago)[^.;\n|]{0,40}", re.I)
RX = {"experience_required": EXP, "contract_type": CTR, "deadline": DL, "company": COMP,
      "city": CITY, "sector": SECT, "function": FUNC, "date_posted": DATE}
SHORT = {"experience_required": "EXP", "contract_type": "CTR", "deadline": "DL",
         "company": "SOC", "city": "VIL", "sector": "SEC", "function": "FON",
         "date_posted": "DAT"}


def pick(rx, body, n=3, cap=145):
    out, seen = [], set()
    for m in rx.finditer(body):
        s = re.sub(r"\s+", " ", m.group(0)).strip(" .;-|")[:cap]
        k = norm(s)[:50]
        if k in seen or len(s) < 8:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= n:
            break
    return out


for name in names:
    items = json.load(open(os.path.join(WL, name + ".json"), encoding="utf-8"))
    print(f"########## {name} ({len(items)}) ##########")
    for it in items:
        body = re.sub(r"[ \t]+", " ", (full.get(it["url"]) or {}).get("text", ""))
        if not body:
            for u, d in full.items():
                if jid(u) == it["key"]:
                    body = re.sub(r"[ \t]+", " ", d.get("text", ""))
                    break
        print(f"\n[{it['key']}] {it['t']}")
        print(f"   A={it.get('have')}")
        if not body:
            print("   !! AUCUN TEXTE INTEGRAL")
            if it.get("snip"):
                print("   snip:", it["snip"][:300])
            continue
        for f in it["empty"]:
            for s in pick(RX[f], body, 3 if f == "experience_required" else 2):
                print(f"   {SHORT[f]}: {s}")
