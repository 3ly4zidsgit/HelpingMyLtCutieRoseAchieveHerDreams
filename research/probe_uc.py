"""Can SeleniumBase UC mode get past the Cloudflare / anti-bot walls?"""
import sys, io, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from seleniumbase import SB
from bs4 import BeautifulSoup

TARGETS = [
 ("emploi.ma",  "https://www.emploi.ma/recherche-jobs-maroc?keywords=lean",
                "div.card-job, li.card-job, article"),
 ("bayt",       "https://www.bayt.com/en/morocco/jobs/six-sigma-jobs/", "li[data-js-job]"),
 ("bayt-search","https://www.bayt.com/en/morocco/jobs/?q=amelioration+continue", "li[data-js-job]"),
 ("indeed",     "https://ma.indeed.com/jobs?q=amelioration+continue&l=Maroc", "div.job_seen_beacon"),
 ("glassdoor",  "https://www.glassdoor.com/Job/morocco-lean-jobs-SRCH_IL.0,7_IN169_KO8,12.htm",
                "li[data-test='jobListing']"),
 ("wttj",       "https://www.welcometothejungle.com/fr/jobs?query=lean&refinementList%5Boffices.country_code%5D%5B%5D=MA",
                "a[href*='/jobs/']"),
]

with SB(uc=True, headless=False, locale="fr", ad_block=True) as sb:
    for name, url, sel in TARGETS:
        try:
            sb.uc_open_with_reconnect(url, reconnect_time=6)
            try:
                sb.uc_gui_click_captcha()
            except Exception:
                pass
            time.sleep(3)
            html = sb.get_page_source()
            s = BeautifulSoup(html, "html.parser")
            title = (s.title.get_text(strip=True) if s.title else "")[:60]
            cards = s.select(sel)
            body = s.get_text(" ", strip=True)[:120]
            print(f"{name:12s} len={len(html):8d} cards={len(cards):4d} | {title}")
            print(f"             body: {re.sub(r'  +', ' ', body)}")
            if cards:
                print(f"             sample: {re.sub(r'\\s+', ' ', cards[0].get_text(' ', strip=True))[:130]}")
        except Exception as e:
            print(f"{name:12s} ERR {type(e).__name__}: {str(e)[:70]}")
        sys.stdout.flush()
