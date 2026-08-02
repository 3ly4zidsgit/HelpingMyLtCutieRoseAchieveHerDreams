import re, sys, time, traceback
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from sel_common import driver, get
from common import blank, relevance, save, jid

def T(el, sel=None):
    if sel: el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

rows = []
def push(**kw):
    keep, score, hits = relevance(kw.get("job_title",""), kw.get("description_snippet",""))
    if not keep: return False
    rows.append(blank(keywords_matched=", ".join(hits), score=score, **kw)); return True

# ---------------- BAYT: only slugs that exist; paginate deeply ----------------
BAYT_SLUGS = ["lean", "lean-manufacturing", "amelioration-continue", "ingenieur",
              "qualite", "production", "logistique", "industrial", "engineer",
              "supply-chain-management", "quality", "manufacturing-engineer",
              "process", "operations", "six-sigma-jobs", "maintenance", "methodes"]

def bayt(d):
    n = 0
    for slug in BAYT_SLUGS:
        for page in range(1, 5):
            url = f"https://www.bayt.com/en/morocco/jobs/{slug}-jobs/" + (f"?page={page}" if page > 1 else "")
            html = get(d, url, wait_css="li[data-js-job]", timeout=18, settle=2.2)
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("li[data-js-job]")
            if not cards:
                if page == 1: print(f"  [Bayt] {slug}: no such listing"); sys.stdout.flush()
                break
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/jobs/']")
                if not a: continue
                u = urljoin("https://www.bayt.com", a.get("href", ""))
                logo = c.select_one("img.jb-logo")
                comp = (logo.get("title") or logo.get("alt") or "").strip() if logo else ""
                comp = comp or T(c, "b.jb-company") or T(c, "a[href*='/companies/']")
                date = T(c, "span[data-automation-id='job-active-date']")
                # location: the muted line that is neither the company nor the date
                loc = ""
                for el in c.select("div.t-mute, span.t-mute, div.jb-loc, .t-small"):
                    tx = T(el)
                    if not tx or tx == date or tx == comp: continue
                    if re.search(r"\d+\+?\s*(day|week|month|hour|minute)s?\s*ago|ago$", tx, re.I): continue
                    if re.search(r"(Maroc|Morocco|Casablanca|Tanger|Tangier|Rabat|Kenitra|Marrakech|"
                                 r"Agadir|Fes|Fez|Meknes|Oujda|Tetouan|Sale|Mohammedia|Nador|"
                                 r"Jadida|Safi|Settat|Berrechid)", tx, re.I):
                        loc = tx; break
                loc = loc or "Maroc"
                desc = T(c, "div.jb-descr")
                if push(source="Bayt.com", job_title=T(a), company=comp, location_city=loc,
                        country="Maroc", url=u, date_posted=date,
                        description_snippet=desc[:600]): got += 1
            n += got
            print(f"  [Bayt] {slug} p{page}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
            if len(cards) < 20: break
    return n

# ---------------- INDEED international, REMOTE only ----------------
IND_SITES = [
    ("https://www.indeed.com", "Remote", "USA"),
    ("https://uk.indeed.com", "Remote", "Royaume-Uni"),
    ("https://ca.indeed.com", "Remote", "Canada"),
    ("https://fr.indeed.com", "T%C3%A9l%C3%A9travail", "France"),
    ("https://ie.indeed.com", "Remote", "Irlande"),
    ("https://ae.indeed.com", "Remote", "Emirats Arabes Unis"),
]
IND_RKW = ["lean six sigma", "continuous improvement", "operational excellence",
           "process improvement", "industrial engineer", "business process improvement",
           "lean manufacturing", "six sigma black belt", "process excellence",
           "operations excellence", "kaizen", "supply chain analyst", "quality engineer"]

def indeed_remote(d):
    n = 0
    for base, loc, country in IND_SITES:
        for kw in IND_RKW:
            for start in (0, 10):
                url = f"{base}/jobs?q={quote_plus(kw)}&l={loc}&start={start}"
                html = get(d, url, wait_css="div.job_seen_beacon", timeout=18, settle=2.5)
                s = BeautifulSoup(html, "html.parser")
                cards = s.select("div.job_seen_beacon")
                if not cards: break
                got = 0
                for c in cards:
                    a = c.select_one("a.jcs-JobTitle") or c.select_one("h2 a")
                    if not a: continue
                    jk = a.get("data-jk") or ""
                    m = re.search(r"jk=([0-9a-f]+)", a.get("href", ""))
                    if not jk and m: jk = m.group(1)
                    u = f"{base}/viewjob?jk={jk}" if jk else urljoin(base, a.get("href",""))
                    loc_txt = T(c, "div[data-testid='text-location']")
                    if "remote" not in loc_txt.lower() and "télétravail" not in loc_txt.lower():
                        continue
                    if push(source=f"Indeed {country} (Remote)", job_title=T(a.select_one("span") or a),
                            company=T(c, "span[data-testid='company-name']"),
                            location_city=loc_txt, country=country, remote="Oui / Remote",
                            url=u, date_posted=T(c, "span[data-testid='myJobsStateDate']"),
                            salary=T(c, "div[data-testid='attribute_snippet_testid']"),
                            description_snippet=T(c, "div[data-testid='belowJobSnippet']")[:600]): got += 1
                n += got
                print(f"  [Indeed-{country}] '{kw}' s{start}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
                if len(cards) < 12: break
    return n

if __name__ == "__main__":
    which = sys.argv[1]
    d = driver(headless=True)
    fns = {"bayt": bayt, "indeed_remote": indeed_remote}
    try:
        fns[which](d)
    except Exception:
        traceback.print_exc()
    finally:
        d.quit()
    uniq = {}
    for r in rows:
        k = jid(r["url"], r["job_title"], r["company"])
        if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
    print(f"TOTAL {which}: {len(uniq)}")
    save(f"sel2_{which}", list(uniq.values()))
