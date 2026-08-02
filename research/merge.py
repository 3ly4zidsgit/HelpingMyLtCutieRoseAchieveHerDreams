"""Merge every scraped source, dedupe, classify junior / experienced / abroad."""
import json, os, re, glob, sys
from datetime import datetime, timedelta
from common import norm, save, load, strip_accents

TODAY = datetime(2026, 7, 28)

SOURCES = ["rekrute", "linkedin", "remote", "maboards", "selenium_oc", "selenium_bayt",
           "sel2_bayt", "selenium_indeed", "sel_indeed", "selenium_jooble", "sel_jooble",
           "sel2_indeed_remote", "selenium_emploima", "sel_emploima", "agencies",
           # round 2: ATS feeds + the Cloudflare-walled sources cracked with UC mode
           "ats", "anapec_boards", "worldwide",
           "uc_emploima", "uc_indeed", "uc_bayt", "uc_glassdoor", "uc_all"]

# ------------------------------------------------------------------ dates
FR_MONTH = {"janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,
            "aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12}

def parse_date(s):
    if not s: return None
    t = norm(s)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"(\d{1,2})\s+(" + "|".join(FR_MONTH) + r")\s+(\d{4})", t)
    if m: return datetime(int(m.group(3)), FR_MONTH[m.group(2)], int(m.group(1)))
    m = re.search(r"il y a (\d+)\s*(jour|semaine|mois|heure|minute)", t)
    if m:
        n = int(m.group(1)); u = m.group(2)
        d = {"jour":1, "semaine":7, "mois":30, "heure":0, "minute":0}[u] * n
        return TODAY - timedelta(days=d)
    m = re.search(r"(\d+)\+?\s*(day|week|month|hour)s?\s*ago", t)
    if m:
        n = int(m.group(1)); u = m.group(2)
        return TODAY - timedelta(days={"day":1,"week":7,"month":30,"hour":0}[u] * n)
    if re.search(r"aujourd|today|just posted|nouvelle offre", t): return TODAY
    if re.search(r"hier|yesterday", t): return TODAY - timedelta(days=1)
    return None

def iso(d): return d.strftime("%Y-%m-%d") if d else ""

# ------------------------------------------------------- experience level
JUNIOR = re.compile(
    r"debutant|d[ée]butant|moins d.?un an|[-–]\s?1 an\b|0\s?[-a]\s?1 an|"
    r"\bentry level\b|\bjunior\b|\bstage\b|\bstagiaire\b|\binternship\b|\bintern\b|"
    r"fraichement diplome|sans experience|\bpfe\b|\bnot applicable\b|\balternance\b|"
    r"\bapprenti|premiere experience|\b0 an|1 an d.?experience")
SENIOR = re.compile(
    r"\b([2-9]|1[0-9])\s*(ans|ann[ée]es|\+?\s*years?)\b|\bde\s*[2-9]\s*a\s*\d+\s*ans|"
    r"\bsenior\b|\bconfirm[ée]\b|\bexp[ée]riment[ée]\b|mid[- ]senior|\bexecutive\b|"
    r"\bdirector\b|\bdirecteur\b|\bmanager\b|\bchef de\b|\bresponsable\b|\bhead of\b|"
    r"\blead\b|\bexpert\b|\bmaster\b|\bblack belt\b|\bprincipal\b|minimum\s*\d+\s*ans|"
    r"\bassociate\b|\bmid[- ]level\b|\b[3-9]\s*[-a]\s*\d+\s*ans")

# LinkedIn reports a seniority label rather than a number of years; map it first.
LI_LEVEL = {
    "stage": "Junior / Debutant", "internship": "Junior / Debutant",
    "debutant": "Junior / Debutant", "entry level": "Junior / Debutant",
    "premier emploi": "Junior / Debutant", "alternance": "Junior / Debutant",
    "apprentissage": "Junior / Debutant", "temporaire": "Junior / Debutant",
    "confirme": "Experimente", "associate": "Experimente", "mid-senior level": "Experimente",
    "cadre": "Experimente", "cadre superieur": "Experimente", "cadre dirigeant": "Experimente",
    "directeur": "Experimente", "director": "Experimente", "executive": "Experimente",
    "senior": "Experimente",
}
TOP_TITLE = re.compile(r"\bvice president\b|\bvp\b|\bchief\b|\bhead of\b|\bdirector\b|"
                       r"\bdirecteur\b|\bpresident\b|\bc[ei]o\b|\bcoo\b|\bpartner\b")

def classify_exp(row):
    blob = norm(" ".join([row.get("experience_required",""), row.get("job_title",""),
                          row.get("description_snippet","")[:400]]))
    exp_field = norm(row.get("experience_required",""))
    if exp_field in LI_LEVEL: return LI_LEVEL[exp_field]
    if TOP_TITLE.search(norm(row.get("job_title", ""))): return "Experimente"
    if exp_field and JUNIOR.search(exp_field): return "Junior / Debutant"
    if exp_field and SENIOR.search(exp_field): return "Experimente"
    if JUNIOR.search(blob): return "Junior / Debutant"
    if SENIOR.search(blob): return "Experimente"
    return "Non precise"

# extract "X ans d'experience" from text when field is missing
EXP_TXT = re.compile(r"(\d{1,2})\s*(?:a|à|-|–)?\s*(\d{1,2})?\s*(?:ans|ann[ée]es|years?)\s*"
                     r"(?:d[e']\s*)?(?:exp[ée]rience|experience)?", re.I)

def guess_exp_text(row):
    if row.get("experience_required"): return row["experience_required"]
    blob = row.get("description_snippet","") + " " + row.get("job_title","")
    m = re.search(r"(?:exp[ée]rience|experience)[^.]{0,40}?(\d{1,2})\s*(?:a|à|-|–)\s*(\d{1,2})\s*ans", blob, re.I)
    if m: return f"{m.group(1)} a {m.group(2)} ans"
    m = re.search(r"(?:minimum|au moins|min\.?)\s*(\d{1,2})\s*ans", blob, re.I)
    if m: return f"Minimum {m.group(1)} ans"
    m = re.search(r"(\d{1,2})\s*ans? d[e']\s*exp[ée]rience", blob, re.I)
    if m: return f"{m.group(1)} ans"
    return ""

# --------------------------------------------------------------- contract
def guess_contract(row):
    if row.get("contract_type"): return row["contract_type"]
    blob = norm(row.get("description_snippet","") + " " + row.get("job_title",""))
    for pat, label in [(r"\bcdi\b","CDI"), (r"\bcdd\b","CDD"), (r"\bstage\b|\bpfe\b","Stage"),
                       (r"\balternance\b|\bapprentissage\b","Alternance"),
                       (r"\bfreelance\b|\bconsultant ind","Freelance"),
                       (r"\binterim\b|\bint[ée]rim\b","Interim"),
                       (r"\bfull[- ]time\b|\btemps plein\b","Temps plein / Full-time"),
                       (r"\bpart[- ]time\b|\btemps partiel\b","Temps partiel"),
                       (r"\bcontract\b","Contract"), (r"\bpermanent\b","Permanent")]:
        if re.search(pat, blob): return label
    return ""

# ----------------------------------------------------------------- cities
MA_CITIES = ["casablanca","tanger","tangier","rabat","kenitra","kénitra","marrakech","marrakesh",
             "agadir","fes","fès","fez","meknes","meknès","oujda","tetouan","tétouan","sale","salé",
             "mohammedia","el jadida","safi","nador","berrechid","settat","benguerir","laayoune",
             "khouribga","temara","bouskoura","nouaceur","ain sebaa","tit mellil","skhirat",
             "beni mellal","taza","larache","essaouira","dakhla","midelt","tiflet","ksar el kebir"]

DATEISH = re.compile(r"^\s*(\d+\+?\s*(jour|semaine|mois|heure|day|week|month|hour|minute)s?"
                     r"|il y a\b|.*\bago\b|aujourd|today|hier|yesterday|\d{2}/\d{2}/\d{4}"
                     r"|\d{4}-\d{2}-\d{2}|nouvelle offre|just posted)", re.I)

def clean_city(row):
    raw = row.get("location_city","") or ""
    t = norm(raw)
    for c in MA_CITIES:
        if c in t:
            return c.title().replace("Fes","Fès").replace("Kenitra","Kénitra")
    if DATEISH.match(raw.strip()):
        # some boards put the posting age where the location should be
        if not row.get("date_posted"): row["date_posted"] = raw.strip()
        return ""
    if not raw: return ""
    part = raw.split(",")[0].strip()
    return re.sub(r"\s*\(.*?\)", "", part)[:60]

COUNTRY_HINT = re.compile(
    r"(états[- ]unis|etats[- ]unis|united states|usa|royaume[- ]uni|united kingdom|angleterre|"
    r"canada|allemagne|germany|france|espagne|spain|portugal|italie|italy|suisse|switzerland|"
    r"belgique|belgium|pays[- ]bas|netherlands|irlande|ireland|pologne|poland|roumanie|romania|"
    r"tunisie|tunisia|algerie|algeria|egypte|egypt|senegal|c[oô]te d.?ivoire|nigeria|kenya|"
    r"afrique du sud|south africa|emirats|emirates|uae|arabie saoudite|saudi|qatar|koweit|"
    r"turquie|turkey|inde|india|mexique|mexico|bresil|brazil|argentine|colombie|chili|"
    r"australie|australia|nouvelle[- ]z[ée]lande|japon|japan|chine|china|singapour|singapore|"
    r"malaisie|philippines|vietnam|indon[ée]sie|su[eè]de|sweden|norv[eè]ge|norway|danemark|"
    r"denmark|finlande|finland|autriche|austria|r[ée]publique tch[eè]que|czech|hongrie|hungary|"
    r"gr[eè]ce|greece|luxembourg|europe|worldwide|anywhere|remote|latam|emea|apac)", re.I)

def split_location(raw):
    """-> (city, country) for a non-Moroccan location string."""
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    if not parts: return "", ""
    country = ""
    for p in reversed(parts):
        if COUNTRY_HINT.search(strip_accents(p).lower()) or (len(parts) > 1 and p == parts[-1]):
            country = p; break
    city = parts[0] if parts[0] != country else ""
    return city, country

def is_morocco(row):
    blob = norm(" ".join([row.get("country",""), row.get("location_city",""), row.get("source","")]))
    if "maroc" in blob or "morocco" in blob: return True
    if any(c in blob for c in MA_CITIES): return True
    return False

# ------------------------------------------------------------- text repair
# A couple of boards serve UTF-8 without declaring it, so requests decodes as
# latin-1 and we get "L'HÃ´pital" instead of "L'Hôpital".
MOJI = re.compile(
    "[\u00c3\u00c2\u00e2][\u0080-\u00bf\u2018-\u201e\u20ac\u0161\u0153\u2122]")

def unmojibake(s):
    """Undo one round of 'UTF-8 bytes decoded as cp1252/latin-1'."""
    if not s or not MOJI.search(s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = s.encode(enc, "strict").decode("utf-8", "strict")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if not MOJI.search(fixed):
            return fixed
    return s


TEXT_FIELDS = ("job_title", "company", "location_city", "sector", "function",
               "description_snippet", "contract_type", "experience_required",
               "education_level", "recruiter_or_hr", "salary")

# ------------------------------- company / date rescue for aggregator posts
# Dreamjob & MarocAnnonces publish blog-style titles ("X recrute un ...") with no
# company field, so pull the employer out of the headline instead.
COMPANY_PATTERNS = [
    re.compile(r"^(.{2,45}?)\s+recrut(?:e|ement)\b", re.I),
    re.compile(r"^(.{2,45}?)\s*:\s", re.I),
    re.compile(r"\bchez\s+([A-ZÀ-Ÿ][\w'&\.\- ]{2,40}?)(?:\s+[àa]\s|\s*[,\.\|]|$)", re.I),
    re.compile(r"\brejoignez\s+([A-ZÀ-Ÿ][\w'&\.\- ]{2,40}?)(?:\s*[:,\.\|]|$)", re.I),
    re.compile(r"\b(?:groupe|société|societe)\s+([A-ZÀ-Ÿ][\w'&\.\- ]{2,35})", re.I),
]
STOPWORDS = re.compile(r"^(offre|offres|emploi|poste|recrutement|opportunit|urgent|nouveau|"
                       r"ingenieur|ingénieur|responsable|technicien|chef|directeur|stage)", re.I)

def rescue_company(row):
    if row.get("company"): return row["company"]
    t = row.get("job_title", "")
    for p in COMPANY_PATTERNS:
        m = p.search(t)
        if m:
            c = re.sub(r"\s+", " ", m.group(1)).strip(" -–:,.")
            if 2 < len(c) < 46 and not STOPWORDS.match(c):
                return c
    return ""

DATE_IN_TEXT = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")

def rescue_date(row):
    if row.get("date_posted"): return row["date_posted"]
    m = DATE_IN_TEXT.search(row.get("description_snippet", "") or "")
    return m.group(1) if m else ""

# ------------------------------------------------- strict off-domain filter
# "amelioration continue" / "excellence operationnelle" are boilerplate in almost
# every French job ad, so a body-only hit is not enough: the role itself must be
# industrial. Drop anything whose TITLE clearly belongs to another trade.
OFFDOMAIN = re.compile(
    r"\bd[ée]veloppeur\b|\bdeveloper\b|\bfull ?stack\b|\bback ?end\b|\bfront ?end\b|"
    r"\bnode\.?js\b|\breact\b|\bangular\b|\bjava\b|\bpython\b|\b\.net\b|\bphp\b|\bdevops\b|"
    r"\bdata scientist\b|\bdata engineer\b|\bcybers[ée]curit|\badministrateur (r[ée]seau|syst[eè]me)|"
    r"\bd[ée]veloppement (web|mobile)\b|\bui/?ux\b|\bwebmaster\b|\bintegrateur web\b|"
    r"\bcomptab|\bfinanci[eè]re?\b|\bcontr[oô]leur de gestion\b|\btr[ée]sorerie\b|\bfiscal|"
    r"\bjuridique\b|\bavocat\b|\bjuriste\b|\bnotaire\b|"
    r"\bcommercial\b|\bvendeur\b|\bvente\b|\bsales\b|\bmarketing\b|\bcommunity manager\b|"
    r"\bgraphiste\b|\bdesigner\b|\binfographiste\b|\bcommunication\b|\br[ée]dacteur\b|"
    r"\bressources humaines\b|\bchargé de recrutement\b|\brecruteur\b|\bpaie\b|"
    r"\bt[ée]l[ée]conseil|\bcall ?cent|\bcentre d.?appel|\bcustomer (service|support)\b|"
    r"\bbanque\b|\bassurance\b|\bimmobilier\b|\bh[oô]tell|\bcuisin|\brestaura|"
    r"\bm[ée]decin\b|\binfirmi|\bpharmaci|\bdentiste\b|\bprofesseur\b|\benseignant\b|"
    r"\btraducteur\b|\bchauffeur\b|\blivreur\b|\bagent de s[ée]curit|\bm[ée]nage\b|"
    r"\bsecr[ée]taire\b|\bassistant[e]? de direction\b|\bstandardiste\b|\bcaissier\b|"
    r"\barchitecte (logiciel|solution|cloud)\b|\bscrum master\b|\bproduct owner\b")

INDUSTRIAL_CTX = re.compile(
    r"\bindustri|\bmanufactur|\busine\b|\bplant\b|\bproduction\b|\batelier\b|\bqualit[ée]\b|"
    r"\bquality\b|\bprocess\b|\bproc[ée]d[ée]|\bm[ée]thodes?\b|\bmaintenance\b|\blogistique\b|"
    r"\bsupply chain\b|\bautomobile\b|\ba[ée]ronautique\b|\bagroaliment|\btextile\b|\bc[aâ]blage\b|"
    r"\blean\b|\bsigma\b|\bkaizen\b|\bkanban\b|\bexcellence op|\bam[ée]lioration continue\b|"
    r"\bg[ée]nie industriel\b|\bindustrial engineer|\bproductivit|\bopex\b|\bhse\b|\bqhse\b")

def strict_keep(r):
    title = norm(r.get("job_title", ""))
    score = r.get("score", 0)
    if OFFDOMAIN.search(title):
        # only survives if the TITLE itself carries a hard lean/industrial keyword
        return score >= 10
    if score >= 10:
        return True
    blob = norm(" ".join([title, r.get("function",""), r.get("sector",""),
                          r.get("description_snippet","")[:500]]))
    return bool(INDUSTRIAL_CTX.search(blob))

# -------------------------------------------------------------------- run
def main():
    all_rows = []
    for name in SOURCES:
        rows = load(name)
        if rows:
            print(f"  {name:22s} {len(rows):4d}")
            all_rows += rows
    print(f"raw total: {len(all_rows)}")

    # dedupe: by URL, then by title+company
    by_url, by_tc = {}, {}
    for r in all_rows:
        u = (r.get("url") or "").split("?")[0].rstrip("/")
        k1 = norm(u)
        tc = norm(r.get("job_title","")) + "|" + norm(r.get("company",""))
        if k1 and k1 in by_url:
            keep = by_url[k1]
            for f, v in r.items():
                if v and not keep.get(f): keep[f] = v
            continue
        if len(norm(r.get("job_title",""))) > 8 and r.get("company") and tc in by_tc:
            keep = by_tc[tc]
            for f, v in r.items():
                if v and not keep.get(f): keep[f] = v
            if r.get("source") not in keep.get("source",""):
                keep["source"] = keep["source"] + " ; " + r.get("source","")
            continue
        if k1: by_url[k1] = r
        if r.get("company"): by_tc[tc] = r
        all_rows_keep = r

    rows = list({id(v): v for v in list(by_url.values()) + list(by_tc.values())}.values())
    print(f"after dedupe: {len(rows)}")

    for r in rows:
        for f in TEXT_FIELDS:
            if r.get(f): r[f] = unmojibake(r[f])
        r["company"] = rescue_company(r)
        r["date_posted"] = rescue_date(r)
        raw_loc = r.get("location_city", "")
        if is_morocco(r):
            r["location_city"] = clean_city(r)
            r["country"] = "Maroc"
        else:
            city, country = split_location(raw_loc)
            r["location_city"] = city or clean_city(r)
            r["country"] = country or "International (Remote)"
        r["experience_required"] = guess_exp_text(r)
        r["contract_type"] = guess_contract(r)
        r["seniority_bucket"] = classify_exp(r)
        d = parse_date(r.get("date_posted"))
        r["date_posted_iso"] = iso(d)
        dl = parse_date(r.get("deadline"))
        r["deadline_iso"] = iso(dl)
        if not r.get("remote"):
            blob = norm(r.get("job_title","") + " " + r.get("description_snippet","")[:300])
            r["remote"] = "Oui / Remote" if re.search(r"\bremote\b|t[ée]l[ée]travail|work from home|hybride|hybrid", blob) else ""

    # drop rows with no usable link, then apply the strict off-domain filter
    rows = [r for r in rows if r.get("url","").startswith("http")]
    before = len(rows)
    dropped = [r for r in rows if not strict_keep(r)]
    rows = [r for r in rows if strict_keep(r)]
    print(f"strict filter: {before} -> {len(rows)} (dropped {len(dropped)})")
    for r in dropped[:10]:
        print(f"    DROP: {r['job_title'][:58]!r} [{r.get('score')}]")
    # graft the company-level lookup (site / careers email / named HR contact)
    import json as _json, os as _os
    from common import OUT as _OUT
    cf = _os.path.join(_OUT, "company_cache.json")
    cache = _json.load(open(cf, encoding="utf-8")) if _os.path.exists(cf) else {}
    hit = 0
    for r in rows:
        info = cache.get(norm(r.get("company", "")))
        if not info: continue
        hit += 1
        r["company_website"] = info.get("website", "")
        r["company_email"] = ", ".join(info.get("emails", [])[:2])
        if not r.get("recruiter_or_hr"):
            r["recruiter_or_hr"] = info.get("hr_name", "")
            r["hr_title"] = info.get("hr_title", "")
            r["hr_profile"] = info.get("hr_profile", "")
    print(f"company cache applied to {hit}/{len(rows)} rows ({len(cache)} companies known)")

    rows.sort(key=lambda r: (-r.get("score", 0), r.get("company","")))
    print(f"final: {len(rows)}")
    print(f"  Maroc: {sum(1 for r in rows if r['country']=='Maroc')}")
    print(f"  Hors Maroc: {sum(1 for r in rows if r['country']!='Maroc')}")
    from collections import Counter
    print("  buckets:", Counter(r["seniority_bucket"] for r in rows))
    save("merged", rows)
    return rows

if __name__ == "__main__":
    main()
