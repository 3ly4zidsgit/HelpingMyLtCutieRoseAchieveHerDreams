import re, sys, time, random, traceback
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from sel_common import driver, get
from common import blank, relevance, save, jid, find_emails, norm

def T(el, sel=None):
    if sel:
        el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

SHOWN = set()
def show(site, card):
    if site in SHOWN: return
    SHOWN.add(site)
    print(f"\n----- SAMPLE CARD [{site}] -----\n{card.prettify()[:2200]}\n-----\n")
    sys.stdout.flush()

rows = []
def push(**kw):
    keep, score, hits = relevance(kw.get("job_title", ""), kw.get("description_snippet", ""))
    if not keep: return False
    rows.append(blank(keywords_matched=", ".join(hits), score=score, **kw))
    return True

# =================================================================== BAYT
BAYT_KW = ["lean", "six-sigma", "continuous-improvement", "industrial-engineer",
           "operational-excellence", "kaizen", "process-improvement", "quality-engineer",
           "production-manager", "supply-chain", "manufacturing", "methods-engineer",
           "process-engineer", "operations-manager", "amelioration-continue", "kanban"]

def bayt(d):
    n = 0
    for kw in BAYT_KW:
        for page in range(1, 4):
            url = f"https://www.bayt.com/en/morocco/jobs/{kw}-jobs/" + (f"?page={page}" if page > 1 else "")
            html = get(d, url, wait_css="li[data-js-job]", settle=2.2)
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("li[data-js-job]")
            if not cards: break
            show("BAYT", cards[0])
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/jobs/']")
                if not a: continue
                title = T(a)
                href = a.get("href", "")
                u = urljoin("https://www.bayt.com", href)
                comp = T(c, "b.jb-company") or T(c, "a[href*='/en/morocco/jobs/companies/']") or T(c, ".t-nowrap")
                loc = T(c, "span.t-mute.t-small") or T(c, ".jb-loc")
                date = T(c, "span[data-automation-id='job-active-date']") or T(c, ".u-none span")
                desc = T(c, "div.jb-descr") or T(c)
                if push(source="Bayt.com", job_title=title, company=comp,
                        location_city=loc, country="Maroc", url=u,
                        date_posted=date, description_snippet=desc[:600]): got += 1
            n += got
            print(f"  [Bayt] {kw} p{page}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
            if len(cards) < 20: break
    return n

# =================================================================== INDEED
IND_KW = ["lean six sigma", "amelioration continue", "excellence operationnelle",
          "genie industriel", "lean manufacturing", "kaizen", "kanban", "ishikawa",
          "ingenieur methodes", "ingenieur industriel", "continuous improvement",
          "ingenieur process", "ingenieur qualite", "supply chain", "ingenieur production",
          "industrialisation", "black belt", "six sigma", "operational excellence",
          "responsable production", "performance industrielle", "5S TPM"]

def indeed(d):
    n = 0
    for kw in IND_KW:
        for start in (0, 10, 20):
            url = f"https://ma.indeed.com/jobs?q={quote_plus(kw)}&l=Maroc&start={start}"
            html = get(d, url, wait_css="div.job_seen_beacon", settle=2.5)
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("div.job_seen_beacon")
            if not cards: break
            show("INDEED", cards[0])
            got = 0
            for c in cards:
                a = c.select_one("a.jcs-JobTitle") or c.select_one("h2 a")
                if not a: continue
                title = T(a.select_one("span") or a)
                jk = a.get("data-jk") or ""
                m = re.search(r"jk=([0-9a-f]+)", a.get("href", ""))
                if not jk and m: jk = m.group(1)
                u = f"https://ma.indeed.com/viewjob?jk={jk}" if jk else urljoin("https://ma.indeed.com", a.get("href",""))
                comp = T(c, "span[data-testid='company-name']") or T(c, "span.companyName")
                loc = T(c, "div[data-testid='text-location']") or T(c, "div.companyLocation")
                date = T(c, "span[data-testid='myJobsStateDate']") or T(c, "span.date")
                sal = T(c, "div[data-testid='attribute_snippet_testid']") or T(c, "div.salary-snippet-container")
                desc = T(c, "div[data-testid='belowJobSnippet']") or T(c, "div.job-snippet") or T(c)
                ctype = ""
                for chip in c.select("div.metadataContainer li, div[data-testid*='attribute'] "):
                    tx = T(chip)
                    if re.search(r"CDI|CDD|Stage|Temps plein|Temps partiel|Freelance|Int[eé]rim|Apprentissage", tx, re.I):
                        ctype = tx; break
                if push(source="Indeed.ma", job_title=title, company=comp, location_city=loc,
                        country="Maroc", url=u, date_posted=date, salary=sal,
                        contract_type=ctype, description_snippet=desc[:600]): got += 1
            n += got
            print(f"  [Indeed] '{kw}' s{start}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
            if len(cards) < 12: break
    return n

# =================================================================== OPTIONCARRIERE
OC_KW = ["lean", "six sigma", "amelioration continue", "excellence operationnelle",
         "genie industriel", "kaizen", "kanban", "ishikawa", "methodes", "industrialisation",
         "process", "production", "qualite", "supply chain", "black belt", "5S",
         "continuous improvement", "ingenieur industriel", "performance", "maintenance"]

def optioncarriere(d):
    n = 0
    for kw in OC_KW:
        for page in range(1, 4):
            url = f"https://www.optioncarriere.ma/emploi?s={quote_plus(kw)}&l=Maroc" + (f"&p={page}" if page > 1 else "")
            html = get(d, url, wait_css="article.job", settle=2.2)
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("article.job")
            if not cards: break
            show("OPTIONCARRIERE", cards[0])
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/jobad/']")
                if not a: continue
                title = T(a)
                u = urljoin("https://www.optioncarriere.ma", a.get("href", ""))
                comp = T(c, "p.company") or T(c, "span.company")
                loc = T(c, "ul.location li") or T(c, "p.location")
                desc = T(c, "div.desc") or T(c)
                date = T(c, "span.badge-r") or T(c, "footer span.badge")
                ctype = ""
                for li in c.select("ul.tags li, span.badge"):
                    tx = T(li)
                    if re.search(r"CDI|CDD|Stage|Temps plein|Temps partiel|Freelance|Int[eé]rim", tx, re.I):
                        ctype = tx; break
                if push(source="Optioncarriere.ma", job_title=title, company=comp,
                        location_city=loc, country="Maroc", url=u, date_posted=date,
                        contract_type=ctype, description_snippet=desc[:600]): got += 1
            n += got
            print(f"  [OptionCarriere] '{kw}' p{page}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
            if len(cards) < 15: break
    return n

# =================================================================== JOOBLE
JB_KW = ["lean", "six-sigma", "amelioration-continue", "excellence-operationnelle",
         "genie-industriel", "kaizen", "kanban", "ingenieur-methodes", "ingenieur-industriel",
         "industrialisation", "supply-chain", "ingenieur-process", "ingenieur-qualite",
         "black-belt", "continuous-improvement", "ingenieur-production"]

def jooble(d):
    n = 0
    for kw in JB_KW:
        for page in (1, 2):
            url = f"https://ma.jooble.org/emploi-{kw}" + (f"?p={page}" if page > 1 else "")
            html = get(d, url, wait_css="div[data-test-name='_jobCard']", settle=2.5)
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("div[data-test-name='_jobCard']")
            if not cards: break
            show("JOOBLE", cards[0])
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/desc/']") or c.select_one("a")
                if not a: continue
                title = T(c, "h2") or T(a)
                u = a.get("href", "")
                if u.startswith("/"): u = "https://ma.jooble.org" + u
                comp = T(c, "p[class*='_1w6ovj']") or T(c, "div[data-test-name='_companyName']") or ""
                loc = T(c, "div[data-test-name='_jobLocation']") or ""
                date = T(c, "div[data-test-name='_dateCaption']") or ""
                sal = T(c, "p[data-test-name='_salary']") or ""
                desc = T(c, "div[data-test-name='_jobSnippet']") or T(c)
                if push(source="Jooble.org (Maroc)", job_title=title, company=comp,
                        location_city=loc, country="Maroc", url=u, date_posted=date,
                        salary=sal, description_snippet=desc[:600]): got += 1
            n += got
            print(f"  [Jooble] '{kw}' p{page}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
    return n

# =================================================================== EMPLOI.MA (cloudflare)
EM_KW = ["lean", "amelioration continue", "six sigma", "genie industriel", "kaizen",
         "excellence operationnelle", "methodes", "industrialisation", "supply chain",
         "ingenieur qualite", "ingenieur process", "production", "kanban"]

def emploima(d):
    n = 0
    # warm-up: let Cloudflare challenge resolve on the home page
    get(d, "https://www.emploi.ma/", wait_css="body", settle=12)
    for kw in EM_KW:
        url = f"https://www.emploi.ma/recherche-jobs-maroc?keywords={quote_plus(kw)}"
        html = get(d, url, wait_css="div.card-job, li.card-job", settle=6)
        s = BeautifulSoup(html, "html.parser")
        cards = s.select("div.card-job, li.card-job")
        if not cards:
            print(f"  [Emploi.ma] '{kw}': blocked/0"); sys.stdout.flush(); continue
        show("EMPLOIMA", cards[0])
        got = 0
        for c in cards:
            a = c.select_one("h3 a") or c.select_one("a[href*='/offre-emploi-maroc/']")
            if not a: continue
            title = T(a)
            u = urljoin("https://www.emploi.ma", a.get("href", ""))
            comp = c.get("data-company") or T(c, "a.card-job-company") or T(c, "div.card-job-company")
            loc = T(c, "li[title='Localisation'], .card-job-detail-location")
            date = T(c, "time") or T(c, ".card-job-date")
            desc = T(c, "div.card-job-description") or T(c)
            if push(source="Emploi.ma", job_title=title, company=comp, location_city=loc,
                    country="Maroc", url=u, date_posted=date, description_snippet=desc[:600]): got += 1
        n += got
        print(f"  [Emploi.ma] '{kw}': {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
    return n


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    d = driver(headless=True)
    fns = {"bayt": bayt, "indeed": indeed, "oc": optioncarriere, "jooble": jooble, "emploima": emploima}
    todo = fns if which == "all" else {which: fns[which]}
    try:
        for name, fn in todo.items():
            print(f"\n########## {name.upper()} ##########"); sys.stdout.flush()
            try:
                fn(d)
            except Exception:
                traceback.print_exc()
            save(f"sel_{name}", [r for r in rows])
    finally:
        d.quit()
    # dedupe within this run
    uniq = {}
    for r in rows:
        k = jid(r["url"], r["job_title"], r["company"])
        if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
    print(f"\nTOTAL selenium relevant: {len(uniq)}")
    save(f"selenium_{which}", list(uniq.values()))
