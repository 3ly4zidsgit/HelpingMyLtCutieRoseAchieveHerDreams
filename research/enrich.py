"""Enrichment pass: detail pages -> deadline / contract / description / emails,
then company-level lookup -> careers email + a named HR/recruiter contact."""
import requests, re, sys, json, os, time, random
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from common import HDRS, find_emails, save, load, norm, OUT

S = requests.Session(); S.headers.update(HDRS)
CACHE_F = os.path.join(OUT, "company_cache.json")
CACHE = json.load(open(CACHE_F, encoding="utf-8")) if os.path.exists(CACHE_F) else {}

def savecache():
    json.dump(CACHE, open(CACHE_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def T(el, sel=None):
    if sel: el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

# ---------------------------------------------------------------- offer detail
def detail_rekrute(row):
    try:
        r = S.get(row["url"], timeout=25)
        if r.status_code != 200: return
    except Exception: return
    s = BeautifulSoup(r.text, "html.parser")
    txt = T(s.select_one("div.contentbloc")) or T(s.select_one("body"))
    m = re.search(r"Postulez avant le\s*(\d{2}/\d{2}/\d{4})", txt)
    if m: row["deadline"] = m.group(1)
    m = re.search(r"Publi[ée]e? (le|il y a)\s*([^\|]{2,24})", txt)
    if m and not row.get("date_posted"): row["date_posted"] = m.group(2).strip()
    body = T(s.select_one("div.contentbloc"))
    if body and len(body) > len(row.get("description_snippet", "")):
        row["description_snippet"] = body[:900]
    em = [e for e in find_emails(r.text) if "exemple@" not in e]
    if em: row["contact_email"] = ", ".join(em[:3])
    if not row.get("contract_type"):
        m = re.search(r"\b(CDI|CDD|Stage|Int[ée]rim|Freelance|Alternance)\b", txt)
        if m: row["contract_type"] = m.group(1)

def detail_optioncarriere(row):
    try:
        r = S.get(row["url"], timeout=25)
        if r.status_code != 200: return
    except Exception: return
    s = BeautifulSoup(r.text, "html.parser")
    art = s.select_one("section.content") or s.select_one("article") or s
    body = T(art)
    if len(body) > len(row.get("description_snippet", "")):
        row["description_snippet"] = body[:900]
    if not row.get("company"):
        row["company"] = T(s.select_one("p.company")) or T(s.select_one(".company"))
    em = find_emails(r.text)
    if em: row["contact_email"] = ", ".join(em[:3])
    for li in s.select("ul.details li, ul.tags li"):
        t = T(li)
        if re.search(r"\bCDI\b|\bCDD\b|Stage|Int[ée]rim|Freelance|Temps plein|Temps partiel", t, re.I) and not row.get("contract_type"):
            row["contract_type"] = t

def detail_bayt(row):
    try:
        r = S.get(row["url"], timeout=25)
        if r.status_code != 200: return
    except Exception: return
    s = BeautifulSoup(r.text, "html.parser")
    body = T(s.select_one("div[id*='job_description']")) or T(s.select_one("main"))
    if len(body) > len(row.get("description_snippet", "")):
        row["description_snippet"] = body[:900]
    txt = s.get_text(" ", strip=True)
    for label, key in [("Employment Status", "contract_type"), ("Job Role", "function"),
                       ("Career Level", "experience_required"), ("Degree", "education_level"),
                       ("Years of Experience", "experience_required"),
                       ("Company Industry", "sector"), ("Number of Vacancies", "positions")]:
        m = re.search(re.escape(label) + r"\s*[:\-]?\s*([A-Za-z0-9 ,/\+\-\.]{2,45})", txt)
        if m and not row.get(key): row[key] = m.group(1).strip()
    em = find_emails(r.text)
    if em: row["contact_email"] = ", ".join(em[:3])

# ------------------------------------------------------------ company lookup
def ddg(query, n=6):
    try:
        r = S.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=25)
        if r.status_code != 200: return []
    except Exception:
        return []
    s = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in s.select("a.result__a")[:n]:
        href = a.get("href", "")
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            from urllib.parse import unquote
            href = unquote(m.group(1))
        out.append((a.get_text(" ", strip=True), href))
    return out

SKIP_HOSTS = re.compile(r"(linkedin|facebook|indeed|rekrute|bayt|glassdoor|wikipedia|youtube|"
                        r"twitter|instagram|jooble|optioncarriere|emploi\.ma|dreamjob|marocannonces|"
                        r"medias24|leconomiste|challenge\.ma|amazon|google|blogspot|modiami)", re.I)

CAREER_PATHS = ["", "/contact", "/contact-us", "/nous-contacter", "/careers", "/carrieres",
                "/carrière", "/recrutement", "/jobs", "/en/contact", "/fr/contact",
                "/about/contact", "/contactez-nous"]

def company_info(company):
    key = norm(company)
    if not key or len(key) < 3: return {}
    if key in CACHE: return CACHE[key]
    info = {"website": "", "emails": [], "hr_name": "", "hr_title": "", "hr_profile": ""}

    # 1) official website
    for title, url in ddg(f"{company} Maroc site officiel"):
        host = urlparse(url).netloc
        if host and not SKIP_HOSTS.search(host):
            info["website"] = f"{urlparse(url).scheme}://{host}"
            break
    # 2) emails from contact / careers pages
    if info["website"]:
        for p in CAREER_PATHS:
            if len(info["emails"]) >= 2: break
            try:
                r = S.get(info["website"] + p, timeout=15)
                if r.status_code != 200: continue
                for e in find_emails(r.text):
                    if e.lower() not in [x.lower() for x in info["emails"]]:
                        info["emails"].append(e)
            except Exception:
                continue
    # 3) a named HR / talent-acquisition contact (public LinkedIn profile)
    for title, url in ddg(f'site:linkedin.com/in "{company}" (RH OR "Human Resources" OR "Talent Acquisition" OR Recrutement) Maroc'):
        if "linkedin.com/in" not in url: continue
        nm = re.split(r"\s+[-–|]\s+", title)[0].strip()
        nm = re.sub(r"\s*\|\s*LinkedIn$", "", nm).strip()
        if 3 < len(nm) < 55:
            info["hr_name"] = nm
            info["hr_title"] = title[:130]
            info["hr_profile"] = url.split("?")[0]
            break
    CACHE[key] = info
    savecache()
    time.sleep(random.uniform(1.4, 2.6))
    return info


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "detail"
    if mode == "detail":
        for name, fn in [("rekrute", detail_rekrute), ("selenium_oc", detail_optioncarriere),
                         ("sel2_bayt", detail_bayt)]:
            rows = load(name)
            if not rows: print(f"{name}: empty, skipped"); continue
            for i, row in enumerate(rows, 1):
                try: fn(row)
                except Exception: pass
                if i % 10 == 0:
                    print(f"  {name}: {i}/{len(rows)}"); sys.stdout.flush(); save(name, rows)
                time.sleep(random.uniform(0.3, 0.7))
            save(name, rows)
            print(f"{name}: enriched {len(rows)}")
    elif mode == "company":
        merged = load("merged")
        comps = {}
        for r in merged:
            c = r.get("company", "").strip()
            if c and len(c) > 2: comps.setdefault(norm(c), c)
        print(f"{len(comps)} distinct companies")
        for i, (k, c) in enumerate(comps.items(), 1):
            info = company_info(c)
            print(f"  {i}/{len(comps)} {c[:34]:34s} web={info.get('website','')[:34]:34s} "
                  f"mails={len(info.get('emails',[]))} hr={info.get('hr_name','')[:24]}")
            sys.stdout.flush()
