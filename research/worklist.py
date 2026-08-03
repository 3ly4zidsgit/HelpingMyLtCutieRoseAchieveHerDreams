"""Build the per-row reading worklist: which columns are empty, and the passages
of the ad body that carry the answer.

Compact on purpose. The whole corpus is 3 MB of ad text; what decides a column is
never more than a couple of sentences, so only those sentences are staged. The
labelled blocks that Rekrute / Bayt / Optioncarriere publish ("Secteur d'activite :
Automobile") are pulled out separately - reading a field the site itself printed
is still reading, and it is the only place several of these columns exist at all."""
import sys, io, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import jid, norm

rows = json.load(open(os.path.join(ROOT, "data", "audit_rows.json"), encoding="utf-8"))
full = json.load(open(os.path.join(ROOT, "data", "fulltext.json"), encoding="utf-8"))
fvp = os.path.join(ROOT, "data", "field_verdicts.json")
fv = {x["key"]: x for x in json.load(open(fvp, encoding="utf-8")) if x.get("key")}

COL = {"company": "Entreprise", "contract_type": "Type de contrat",
       "experience_required": "Expérience requise", "city": "Ville",
       "sector": "Secteur", "function": "Fonction",
       "date_posted": "Date de publication", "deadline": "Date limite candidature"}

EXP_RE = re.compile(
    r"[^.\n]{0,90}(?:\b\d{1,2}\s*(?:\+|a|à|-|to)?\s*\d{0,2}\s*(?:ans?|ann[ée]es?|years?|yrs?|mois)\b"
    r"|minimum\s*\d|au moins\s*\d|d[ée]butant|entry[- ]level|fraichement diplom|jeune diplom"
    r"|exp[ée]rience (?:requise|exig|obligatoire|professionnelle|confirm|significative|souhait)"
    r"|niveau d.exp[ée]rience|profil recherch[ée]|nouveaux? dipl[oô]m|no experience)[^.\n]{0,110}",
    re.I)
CTR_RE = re.compile(r"[^.\n|]{0,60}\b(cdi|cdd|type de contrat|contrat [àa] dur|freelance|int[ée]rim"
                    r"|temps plein|full[- ]time|part[- ]time|permanent contract|contrat de projet"
                    r"|contrat propos)\b[^.\n|]{0,60}", re.I)
DL_RE = re.compile(r"[^.\n|]{0,70}\b(date limite|limite de candidature|deadline|cl[oô]ture des cand"
                   r"|postuler avant|avant le \d|jusqu.au \d|apply by|closing date|derni[eè]r délai"
                   r"|dernier d[ée]lai|candidatures? ferm|n.est plus d.actualit|offre expir"
                   r"|no longer accepting)\b[^.\n|]{0,70}", re.I)
# labelled blocks the boards print themselves
LAB_RE = re.compile(
    r"(secteur d.activit[ée]|secteur|domaine|industrie|industry|fonction|m[ée]tier|job function"
    r"|type de contrat|contrat|employment type|niveau d.[ée]tudes|niveau d.exp[ée]rience"
    r"|exp[ée]rience requise|experience|ville|lieu de travail|localisation|location|r[ée]gion"
    r"|entreprise|soci[ée]t[ée]|employeur|recruteur|company|date de publication|publi[ée]e? le"
    r"|date limite|nombre de postes|salaire)\s*[:：]\s*([^\n|]{2,70})", re.I)
CITY_RE = re.compile(r"\b(casablanca|tanger|tangier|rabat|k[ée]nitra|kenitra|marrakech|agadir|f[èe]s|"
                     r"mekn[èe]s|oujda|t[ée]touan|sal[ée]|mohammedia|el jadida|safi|nador|berrechid|"
                     r"settat|benguerir|la[âa]youne|khouribga|temara|bouskoura|nouaceur|skhirat|"
                     r"beni mellal|larache|essaouira|dakhla|had soualem|bouznika|bouknadel|"
                     r"ain sebaa|ain harrouda|midparc|technopolis|tit mellil)\b", re.I)


def hits(rx, body, n, cap=150, grp=0):
    out, seen = [], set()
    for m in rx.finditer(body):
        s = re.sub(r"\s+", " ", m.group(grp)).strip()[:cap]
        k = norm(s)[:45]
        if k in seen or len(s) < 6:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= n:
            break
    return out


work = []
for r in rows:
    url = r.get("LIEN DE L'OFFRE", "")
    key = jid(url)
    empty = [k for k, lab in COL.items() if not r.get(lab)]
    txt = (full.get(url) or {}).get("text", "")
    body = re.sub(r"[ \t]+", " ", txt or "")
    it = {"key": key, "t": r.get("Titre du poste", "")[:80],
          "s": r["_sheet"][:5], "url": url[:110],
          "have": {k: r.get(lab, "")[:40] for k, lab in COL.items() if r.get(lab)},
          "empty": empty, "ft": bool(txt)}
    if txt:
        it["head"] = re.sub(r"\s*\n\s*", " ", body[:330]).strip()
        labs = [f"{a.strip()}: {b.strip()}" for a, b in LAB_RE.findall(body)][:14]
        seen = set()
        it["lab"] = [x for x in labs if not (norm(x)[:40] in seen or seen.add(norm(x)[:40]))]
        if "experience_required" in empty:
            it["exp"] = hits(EXP_RE, body, 4)
        if "contract_type" in empty:
            it["ctr"] = hits(CTR_RE, body, 3, 110)
        it["dl"] = hits(DL_RE, body, 3, 130)
        if "city" in empty:
            it["cities"] = sorted({m.group(1).title() for m in CITY_RE.finditer(body)})[:6]
    else:
        it["snip"] = re.sub(r"\s+", " ", r.get("Description (extrait)", ""))[:400]
    work.append(it)

nof = [w for w in work if not w["ft"]]
print(f"lignes: {len(work)}  texte integral: {len(work) - len(nof)}  sans: {len(nof)}")
print(f"lignes deja completes: {sum(1 for w in work if not w['empty'])}")
c = collections.Counter(k for w in work for k in w["empty"])
print("cellules vides par champ:", dict(c.most_common()))

outdir = os.path.join(ROOT, "data", "worklist")
os.makedirs(outdir, exist_ok=True)
for f in os.listdir(outdir):
    if f.startswith("chunk_"):
        os.rename(os.path.join(outdir, f), os.path.join(outdir, "_old_" + f))
todo = [w for w in work if w["empty"]]
todo.sort(key=lambda w: (not w["ft"], w["s"], -len(w["empty"])))
CH = 34
for i in range(0, len(todo), CH):
    p = os.path.join(outdir, f"chunk_{i // CH:02d}.json")
    json.dump(todo[i:i + CH], open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
n = (len(todo) + CH - 1) // CH
print(f"\n{len(todo)} lignes a completer -> {n} fichiers dans data/worklist/")
print("total octets:", sum(os.path.getsize(os.path.join(outdir, f"chunk_{i:02d}.json"))
                           for i in range(n)))
