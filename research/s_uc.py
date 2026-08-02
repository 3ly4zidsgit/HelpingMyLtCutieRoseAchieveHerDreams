"""SeleniumBase UC mode: the four walls that blocked plain requests/Selenium.
Emploi.ma (Cloudflare), Bayt (real ?q= search), Indeed.ma (deep paging), Glassdoor Morocco.
Run: python s_uc.py [emploima|bayt|indeed|glassdoor|all]
"""
import sys, io, re, time, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from seleniumbase import SB
from common import blank, relevance, save, jid, norm, find_emails

def T(el, sel=None):
    if sel: el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

rows = []
BAD = re.compile(r"\btechnicien\b|\btechnician\b")

def push(src, title, comp, loc, ctype, date, url, desc, **extra):
    if not title or not url: return False
    if BAD.search(norm(title)): return False
    keep, score, hits = relevance(title, desc)
    if not keep: return False
    rows.append(blank(source=src, job_title=title, company=comp, location_city=loc,
                      country="Maroc", contract_type=ctype, date_posted=date, url=url,
                      description_snippet=desc[:800],
                      contact_email=", ".join(find_emails(desc)[:2]),
                      keywords_matched=", ".join(hits), score=score, **extra))
    return True

def open_page(sb, url, wait_css, settle=3.0, reconnect=5):
    try:
        sb.uc_open_with_reconnect(url, reconnect_time=reconnect)
    except Exception:
        try: sb.open(url)
        except Exception: return ""
    # uc_gui_click_captcha drives the real mouse and blocks indefinitely when
    # there is no challenge on screen - only call it if one is actually shown.
    try:
        head = sb.get_page_source()[:4000].lower()
        if any(k in head for k in ("cf-challenge", "just a moment", "un instant",
                                   "checking your browser", "cf_chl", "turnstile")):
            sb.uc_gui_click_captcha()
    except Exception:
        pass
    for _ in range(int(settle * 2)):
        time.sleep(0.5)
        try:
            if sb.is_element_present(wait_css): break
        except Exception: pass
    time.sleep(0.6)
    try: return sb.get_page_source()
    except Exception: return ""

KW_FR = ["lean", "amelioration continue", "six sigma", "genie industriel", "kaizen",
         "excellence operationnelle", "ingenieur methodes", "industrialisation",
         "supply chain", "ingenieur qualite", "ingenieur process", "ingenieur production",
         "kanban", "black belt", "performance industrielle", "ingenieur industriel",
         "lean manufacturing", "ordonnancement", "planification industrielle", "qhse",
         "productivite", "value stream", "process engineer", "manufacturing"]

# ======================================================== EMPLOI.MA
def emploima(sb):
    n = 0
    for kw in KW_FR:
        for pg in range(0, 3):
            url = (f"https://www.emploi.ma/recherche-jobs-maroc?keywords={quote_plus(kw)}"
                   + (f"&page={pg}" if pg else ""))
            html = open_page(sb, url, "div.card-job, li.card-job", settle=3)
            if not html: break
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("div.card-job, li.card-job")
            if not cards: break
            got = 0
            for c in cards:
                a = c.select_one("h3 a, a[href*='/offre-emploi-maroc/']")
                if not a: continue
                u = urljoin("https://www.emploi.ma", a.get("href", ""))
                comp = (c.get("data-company") or T(c, "a.card-job-company")
                        or T(c, ".card-job-company") or "")
                loc = ""
                for li in c.select("ul li"):
                    tx = T(li)
                    if re.search(r"Casablanca|Tanger|Rabat|K[ée]nitra|Marrakech|Agadir|F[èe]s|"
                                 r"Mekn[èe]s|Oujda|T[ée]touan|Jadida|Sal[ée]|Mohammedia|Nador|"
                                 r"Safi|Settat|Berrechid|Maroc", tx, re.I):
                        loc = tx; break
                ctype = ""
                mc = re.search(r"\b(CDI|CDD|Stage|Int[ée]rim|Freelance|Temps plein)\b", T(c), re.I)
                if mc: ctype = mc.group(1)
                date = T(c, "time") or T(c, ".card-job-date")
                if push("Emploi.ma", T(a), comp, loc, ctype, date, u, T(c)): got += 1
            n += got
            print(f"  [Emploi.ma] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 15: break
    return n

# ======================================================== BAYT (?q= search)
def bayt(sb):
    n = 0
    for kw in KW_FR:
        for pg in range(1, 4):
            url = (f"https://www.bayt.com/en/morocco/jobs/?q={quote_plus(kw)}"
                   + (f"&page={pg}" if pg > 1 else ""))
            html = open_page(sb, url, "li[data-js-job]", settle=3)
            if not html: break
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("li[data-js-job]")
            if not cards: break
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/jobs/']")
                if not a: continue
                u = urljoin("https://www.bayt.com", a.get("href", ""))
                logo = c.select_one("img.jb-logo")
                comp = (logo.get("title") or logo.get("alt") or "").strip() if logo else ""
                comp = comp or T(c, "b.jb-company")
                date = T(c, "span[data-automation-id='job-active-date']")
                loc = ""
                for el in c.select("div.t-mute, span.t-mute, .jb-loc, .t-small"):
                    tx = T(el)
                    if tx in (date, comp) or not tx: continue
                    if re.search(r"ago$|\d+\+?\s*(day|month|hour)", tx, re.I): continue
                    if re.search(r"Morocco|Maroc|Casablanca|Tanger|Tangier|Rabat|Kenitra|"
                                 r"Marrakech|Agadir|Fes|Meknes|Oujda|Tetouan|Jadida", tx, re.I):
                        loc = tx; break
                if push("Bayt.com", T(a), comp, loc or "Maroc", "", date, u,
                        T(c, "div.jb-descr") or T(c)): got += 1
            n += got
            print(f"  [Bayt] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 20: break
    return n

# ======================================================== INDEED.MA (deep)
def indeed(sb):
    n = 0
    for kw in KW_FR:
        for start in (0, 10, 20, 30):
            url = f"https://ma.indeed.com/jobs?q={quote_plus(kw)}&l=Maroc&start={start}"
            html = open_page(sb, url, "div.job_seen_beacon", settle=3)
            if not html:
                print(f"  [Indeed] '{kw}' s{start}: empty page", flush=True); break
            s = BeautifulSoup(html, "html.parser")
            cards = s.select("div.job_seen_beacon")
            if not cards:
                print(f"  [Indeed] '{kw}' s{start}: 0 cards (blocked or end)", flush=True); break
            got = 0
            for c in cards:
                a = c.select_one("a.jcs-JobTitle") or c.select_one("h2 a")
                if not a: continue
                jk = a.get("data-jk") or ""
                m = re.search(r"jk=([0-9a-f]+)", a.get("href", ""))
                if not jk and m: jk = m.group(1)
                u = f"https://ma.indeed.com/viewjob?jk={jk}" if jk else urljoin("https://ma.indeed.com", a.get("href", ""))
                ctype = ""
                mc = re.search(r"\b(CDI|CDD|Stage|Temps plein|Temps partiel|Freelance|"
                               r"Int[ée]rim|Apprentissage|Alternance)\b", T(c), re.I)
                if mc: ctype = mc.group(1)
                if push("Indeed.ma", T(a.select_one("span") or a),
                        T(c, "span[data-testid='company-name']"),
                        T(c, "div[data-testid='text-location']"), ctype,
                        T(c, "span[data-testid='myJobsStateDate']"), u,
                        T(c, "div[data-testid='belowJobSnippet']") or T(c),
                        salary=T(c, "div[data-testid='attribute_snippet_testid']")): got += 1
            n += got
            print(f"  [Indeed] '{kw}' s{start}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 12: break
    return n

# ======================================================== GLASSDOOR Morocco
def glassdoor(sb):
    n = 0
    for kw in ["lean", "amelioration continue", "six sigma", "genie industriel",
               "continuous improvement", "operational excellence", "industrial engineer",
               "supply chain", "quality engineer", "process engineer", "production manager"]:
        url = (f"https://www.glassdoor.com/Job/morocco-{quote_plus(kw).replace('+','-')}"
               f"-jobs-SRCH_IL.0,7_IN169_KO8,{8+len(kw)}.htm")
        html = open_page(sb, url, "li[data-test='jobListing']", settle=4)
        if not html: continue
        s = BeautifulSoup(html, "html.parser")
        if not re.search(r"Morocco", (s.title.get_text() if s.title else ""), re.I):
            print(f"  [Glassdoor] '{kw}': wrong country page, skipped", flush=True); continue
        cards = s.select("li[data-test='jobListing']")
        got = 0
        for c in cards:
            a = c.select_one("a[data-test='job-title']") or c.select_one("a[href*='/job-listing/']")
            if not a: continue
            u = urljoin("https://www.glassdoor.com", a.get("href", ""))
            if push("Glassdoor", T(a), T(c, "span[data-test='employer-short-name']"),
                    T(c, "div[data-test='emp-location']"), "",
                    T(c, "div[data-test='job-age']"), u, T(c),
                    salary=T(c, "div[data-test='detailSalary']")): got += 1
        n += got
        print(f"  [Glassdoor] '{kw}': {len(cards)} cards, +{got} (tot {n})", flush=True)
    return n


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"emploima": emploima, "bayt": bayt, "indeed": indeed, "glassdoor": glassdoor}
    todo = fns if which == "all" else {which: fns[which]}
    with SB(uc=True, headless=False, locale="fr", ad_block=True) as sb:
        for name, fn in todo.items():
            print(f"\n########## {name.upper()} ##########", flush=True)
            try:
                fn(sb)
            except Exception:
                traceback.print_exc()
            uniq = {}
            for r in rows:
                k = jid(r["url"], r["job_title"], r["company"])
                if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
            save(f"uc_{which}", list(uniq.values()))
    uniq = {}
    for r in rows:
        k = jid(r["url"], r["job_title"], r["company"])
        if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
    print(f"\nTOTAL UC ({which}): {len(uniq)}")
    save(f"uc_{which}", list(uniq.values()))
