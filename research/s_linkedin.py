import requests, re, sys, time, random
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, norm, find_emails

API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DET = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"

MA_KW = [
    "lean six sigma", "lean manufacturing", "amelioration continue", "excellence operationnelle",
    "genie industriel", "ingenieur industriel", "continuous improvement", "operational excellence",
    "kaizen", "kanban", "six sigma", "black belt", "green belt", "industrial engineer",
    "ingenieur methodes", "ingenieur process", "ingenieur production", "ingenieur qualite",
    "supply chain", "manufacturing engineer", "process engineer", "production manager",
    "quality engineer", "operations excellence", "performance industrielle", "industrialisation",
    "lean management", "process improvement", "responsable methodes", "planification industrielle",
    "ordonnancement", "qhse", "value stream", "tpm maintenance", "5s kaizen",
]
MA_LOC = ["Morocco", "Casablanca, Morocco", "Tangier, Morocco", "Rabat, Morocco",
          "Kenitra, Morocco", "Marrakesh, Morocco", "Agadir, Morocco", "Fes, Morocco",
          "Meknes, Morocco", "Oujda, Morocco", "Tetouan, Morocco", "El Jadida, Morocco"]

REMOTE_KW = [
    "lean six sigma remote", "continuous improvement remote", "operational excellence remote",
    "process improvement remote", "industrial engineer remote", "six sigma black belt remote",
    "business process improvement", "lean consultant", "operations excellence manager",
    "continuous improvement manager", "process excellence", "supply chain remote",
    "manufacturing excellence", "kaizen consultant", "lean transformation",
]
REMOTE_LOC = ["European Union", "United States", "United Kingdom", "Worldwide",
              "Europe", "Remote", "France", "Canada", "Germany", "Spain", "Portugal",
              "United Arab Emirates", "Africa"]


def parse_cards(html, source, default_country):
    out = []
    s = BeautifulSoup(html, "html.parser")
    for card in s.select("li"):
        a = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")
        if not a: continue
        url = (a.get("href") or "").split("?")[0]
        t = card.select_one("h3.base-search-card__title")
        c = card.select_one("h4.base-search-card__subtitle")
        loc = card.select_one("span.job-search-card__location")
        d = card.select_one("time")
        sal = card.select_one("span.job-search-card__salary-info")
        title = re.sub(r"\s+", " ", t.get_text(strip=True)) if t else ""
        comp = re.sub(r"\s+", " ", c.get_text(strip=True)) if c else ""
        locs = re.sub(r"\s+", " ", loc.get_text(strip=True)) if loc else ""
        date = (d.get("datetime") if d else "") or ""
        salary = re.sub(r"\s+", " ", sal.get_text(strip=True)) if sal else ""
        jobid = ""
        m = re.search(r"-(\d{6,})$", url)
        if m: jobid = m.group(1)
        out.append({"url": url, "title": title, "company": comp, "loc": locs,
                    "date": date, "salary": salary, "jobid": jobid,
                    "source": source, "country_hint": default_country})
    return out


def fetch_detail(sess, jobid):
    """returns dict with description text + criteria (seniority, employment type, function, industries)"""
    try:
        r = sess.get(DET.format(jobid), timeout=25)
        if r.status_code != 200: return {}
    except Exception:
        return {}
    s = BeautifulSoup(r.text, "html.parser")
    desc_el = s.select_one("div.show-more-less-html__markup") or s.select_one("div.description__text")
    desc = re.sub(r"\s+", " ", desc_el.get_text(" ", strip=True)) if desc_el else ""
    crit = {}
    items = s.select("li.description__job-criteria-item")
    for it in items:
        h = it.select_one("h3"); v = it.select_one("span")
        if h and v:
            crit[re.sub(r"\s+", " ", h.get_text(strip=True)).lower()] = re.sub(r"\s+", " ", v.get_text(strip=True))
    posters = []
    for pa in s.select("a[href*='/in/']"):
        nm = re.sub(r"\s+", " ", pa.get_text(strip=True))
        if nm and 3 < len(nm) < 60 and "linkedin" not in nm.lower():
            posters.append(nm)
    apply_url = ""
    au = s.select_one("a.topcard__link, code#applyUrl")
    if au:
        apply_url = au.get("href") or re.sub(r'[\\"<>!\-]', "", au.get_text(strip=True))
    return {"desc": desc, "crit": crit, "poster": posters[0] if posters else "",
            "emails": find_emails(desc), "apply_url": apply_url}


def harvest(sess, keywords, locations, source, country, remote_flag, max_pages=3):
    found = {}
    for loc in locations:
        for kw in keywords:
            for start in range(0, max_pages * 10, 10):
                p = {"keywords": kw, "location": loc, "start": start}
                if remote_flag: p["f_WT"] = 2
                try:
                    r = sess.get(API, params=p, timeout=25)
                except Exception:
                    break
                if r.status_code != 200:
                    if r.status_code == 429:
                        time.sleep(8)
                    break
                cards = parse_cards(r.text, source, country)
                if not cards: break
                new = 0
                for c in cards:
                    k = jid(c["url"])
                    if k in found: continue
                    found[k] = c; new += 1
                if new:
                    print(f"  [{source}] {loc[:22]:22s} '{kw[:28]:28s}' s{start}: +{new} (tot {len(found)})")
                    sys.stdout.flush()
                if len(cards) < 10: break
                time.sleep(random.uniform(0.5, 1.1))
            time.sleep(random.uniform(0.3, 0.7))
    return found


def run():
    sess = requests.Session(); sess.headers.update(HDRS)
    raw = {}
    print("--- LinkedIn Morocco ---")
    raw.update(harvest(sess, MA_KW, MA_LOC, "LinkedIn", "Maroc", False, max_pages=3))
    print("--- LinkedIn Remote international ---")
    raw.update(harvest(sess, REMOTE_KW, REMOTE_LOC, "LinkedIn (Remote)", "International", True, max_pages=3))
    print(f"raw cards: {len(raw)}")

    # relevance filter on titles first (cheap), then enrich survivors
    cand = []
    for c in raw.values():
        keep, score, hits = relevance(c["title"], "")
        if keep:
            c["_score"], c["_hits"] = score, hits
            cand.append(c)
    print(f"title-relevant: {len(cand)} -> fetching details")

    rows = []
    for i, c in enumerate(cand, 1):
        det = fetch_detail(sess, c["jobid"]) if c["jobid"] else {}
        crit = det.get("crit", {})
        contract = crit.get("type d'emploi") or crit.get("employment type") or ""
        senior = crit.get("niveau hiérarchique") or crit.get("seniority level") or ""
        func = crit.get("fonction") or crit.get("job function") or ""
        inds = crit.get("secteurs") or crit.get("industries") or ""
        locs = c["loc"]
        country = "Maroc" if re.search(r"maroc|morocco", norm(locs)) else c["country_hint"]
        city = locs.split(",")[0].strip() if locs else ""
        rows.append(blank(
            source=c["source"], job_title=c["title"], company=c["company"],
            recruiter_or_hr=det.get("poster", ""),
            contact_email=", ".join(det.get("emails", [])[:3]),
            location_city=locs, country=country,
            remote="Oui / Remote" if "Remote" in c["source"] else "",
            contract_type=contract, experience_required=senior,
            sector=inds, function=func, date_posted=c["date"], salary=c["salary"],
            url=c["url"], description_snippet=det.get("desc", "")[:600],
            keywords_matched=", ".join(c["_hits"]), score=c["_score"]))
        if i % 25 == 0:
            print(f"  detail {i}/{len(cand)}"); sys.stdout.flush()
            save("linkedin", rows)
        time.sleep(random.uniform(0.35, 0.8))
    save("linkedin", rows)
    return rows

if __name__ == "__main__":
    run()
