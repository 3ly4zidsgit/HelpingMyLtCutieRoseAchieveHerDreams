"""Sources behind Cloudflare / anti-bot walls. Plain requests and ordinary
Selenium both get 403 here; SeleniumBase UC mode gets through.

UC mode needs a REAL (non-headless) browser window - that is what defeats the
challenge - so a Chrome window will open while this runs.
"""
import re, sys, time, traceback
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from core import blank, jid, norm, find_emails


def T(el, sel=None):
    if sel:
        el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def open_page(sb, url, wait_css, settle=3.0, reconnect=5):
    try:
        sb.uc_open_with_reconnect(url, reconnect_time=reconnect)
    except Exception:
        try:
            sb.open(url)
        except Exception:
            return ""
    # uc_gui_click_captcha drives the real mouse and blocks indefinitely when no
    # challenge is on screen - only invoke it when one is actually displayed.
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
            if sb.is_element_present(wait_css):
                break
        except Exception:
            pass
    time.sleep(1.0)
    try:
        return sb.get_page_source()
    except Exception:
        return ""


CITY_RE = (r"Casablanca|Tanger|Tangier|Rabat|K[ée]nitra|Marrakech|Agadir|F[èe]s|Mekn[èe]s|"
           r"Oujda|T[ée]touan|Jadida|Sal[ée]|Mohammedia|Nador|Safi|Settat|Berrechid|Maroc|Morocco")


def emploima(run, col, sb, pages=3):
    n = 0
    for kw in run.queries_fr:
        for pg in range(0, pages):
            url = (f"https://www.emploi.ma/recherche-jobs-maroc?keywords={quote_plus(kw)}"
                   + (f"&page={pg}" if pg else ""))
            html = open_page(sb, url, "div.card-job, li.card-job")
            if not html:
                break
            cards = BeautifulSoup(html, "html.parser").select("div.card-job, li.card-job")
            if not cards:
                break
            got = 0
            for c in cards:
                a = c.select_one("h3 a, a[href*='/offre-emploi-maroc/']")
                if not a:
                    continue
                loc = next((T(li) for li in c.select("ul li")
                            if re.search(CITY_RE, T(li), re.I)), "")
                mc = re.search(r"\b(CDI|CDD|Stage|Int[ée]rim|Freelance|Temps plein)\b", T(c), re.I)
                if col.push("Emploi.ma", T(a),
                            c.get("data-company") or T(c, ".card-job-company"), loc,
                            mc.group(1) if mc else "", T(c, "time"),
                            urljoin("https://www.emploi.ma", a.get("href", "")), T(c)):
                    got += 1
            n += got
            print(f"  [Emploi.ma] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 15:
                break
    return n


def bayt(run, col, pages=3, sb=None):
    n = 0
    for kw in run.queries_fr:
        for pg in range(1, pages + 1):
            url = (f"https://www.bayt.com/en/morocco/jobs/?q={quote_plus(kw)}"
                   + (f"&page={pg}" if pg > 1 else ""))
            html = open_page(sb, url, "li[data-js-job]")
            if not html:
                break
            cards = BeautifulSoup(html, "html.parser").select("li[data-js-job]")
            if not cards:
                break
            got = 0
            for c in cards:
                a = c.select_one("h2 a") or c.select_one("a[href*='/jobs/']")
                if not a:
                    continue
                logo = c.select_one("img.jb-logo")
                comp = (logo.get("title") or logo.get("alt") or "").strip() if logo else ""
                date = T(c, "span[data-automation-id='job-active-date']")
                loc = ""
                for el in c.select("div.t-mute, span.t-mute, .jb-loc, .t-small"):
                    tx = T(el)
                    if not tx or tx in (date, comp):
                        continue
                    if re.search(r"ago$|\d+\+?\s*(day|month|hour)", tx, re.I):
                        continue
                    if re.search(CITY_RE, tx, re.I):
                        loc = tx; break
                if col.push("Bayt.com", T(a), comp or T(c, "b.jb-company"), loc or "Maroc",
                            "", date, urljoin("https://www.bayt.com", a.get("href", "")),
                            T(c, "div.jb-descr") or T(c)):
                    got += 1
            n += got
            print(f"  [Bayt] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 20:
                break
    return n


def indeed(run, col, sb, starts=(0, 10, 20, 30)):
    n = 0
    for kw in run.queries_fr:
        for start in starts:
            url = f"https://ma.indeed.com/jobs?q={quote_plus(kw)}&l=Maroc&start={start}"
            html = open_page(sb, url, "div.job_seen_beacon")
            if not html:
                break
            cards = BeautifulSoup(html, "html.parser").select("div.job_seen_beacon")
            if not cards:
                break
            got = 0
            for c in cards:
                a = c.select_one("a.jcs-JobTitle") or c.select_one("h2 a")
                if not a:
                    continue
                jk = a.get("data-jk") or ""
                m = re.search(r"jk=([0-9a-f]+)", a.get("href", ""))
                if not jk and m:
                    jk = m.group(1)
                u = (f"https://ma.indeed.com/viewjob?jk={jk}" if jk
                     else urljoin("https://ma.indeed.com", a.get("href", "")))
                mc = re.search(r"\b(CDI|CDD|Stage|Temps plein|Temps partiel|Freelance|"
                               r"Int[ée]rim|Alternance)\b", T(c), re.I)
                if col.push("Indeed.ma", T(a.select_one("span") or a),
                            T(c, "span[data-testid='company-name']"),
                            T(c, "div[data-testid='text-location']"),
                            mc.group(1) if mc else "",
                            T(c, "span[data-testid='myJobsStateDate']"), u,
                            T(c, "div[data-testid='belowJobSnippet']") or T(c),
                            salary=T(c, "div[data-testid='attribute_snippet_testid']")):
                    got += 1
            n += got
            print(f"  [Indeed] '{kw}' s{start}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 12:
                break
    return n


def run_uc(run, col, which=("emploima", "bayt", "indeed")):
    """Open one UC browser and drive every walled source through it."""
    from seleniumbase import SB
    fns = {"emploima": emploima, "bayt": bayt, "indeed": indeed}
    with SB(uc=True, headless=False, locale="fr", ad_block=True) as sb:
        for name in which:
            print(f"\n########## UC: {name.upper()} ##########", flush=True)
            try:
                fns[name](run, col, sb=sb)
            except Exception:
                traceback.print_exc()
            run.save(f"uc_{name}", col.rows)
