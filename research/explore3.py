import re, sys
from bs4 import BeautifulSoup
from sel_common import driver, get

d = driver(headless=True)

def look(name, url, sels, wait=None):
    print("="*25, name); sys.stdout.flush()
    try:
        html = get(d, url, wait_css=wait, settle=3.5)
    except Exception as e:
        print("ERR", e); return
    s = BeautifulSoup(html, "html.parser")
    print("len", len(html), "| TITLE:", (s.title.get_text(strip=True) if s.title else "")[:90])
    body = s.get_text(" ", strip=True)[:180]
    print("body:", re.sub(r"\s+"," ", body))
    for sel in sels:
        els = s.select(sel)
        print(f"  {sel!r:42s} -> {len(els)}")
        if els:
            print("     txt:", re.sub(r"\s+"," ", els[0].get_text(" ", strip=True))[:200])
            a = els[0].select_one("a") or (els[0] if els[0].name == "a" else None)
            if a: print("     href:", (a.get("href") or "")[:140])

try:
    look("EMPLOI.MA", "https://www.emploi.ma/recherche-jobs-maroc?keywords=lean",
         ["div.card-job", "div.job-description-wrapper", "li.card-job", "div.search-results div", "h3"],
         wait="div.card-job, h3")
    look("BAYT", "https://www.bayt.com/en/morocco/jobs/lean-jobs/",
         ["li[data-js-job]", "div.card", "li.has-pointer-d", "h2.jobTitle"],
         wait="li[data-js-job], h2")
    look("INDEED.MA", "https://ma.indeed.com/jobs?q=lean+six+sigma&l=Maroc",
         ["div.job_seen_beacon", "td.resultContent", "a.jcs-JobTitle", "h2.jobTitle"],
         wait="div.job_seen_beacon, h2.jobTitle")
    look("OPTIONCARRIERE", "https://www.optioncarriere.ma/emploi?s=lean&l=Maroc",
         ["article.job", "article", "ul.jobs li", "h2"], wait="article")
    look("NOVOJOB", "https://www.novojob.com/maroc/offres-emploi?keywords=lean",
         ["div.job-item", "article", "div.list-group-item", "a[href*='/offre']", "h3"], wait="article, h3")
    look("WTTJ", "https://www.welcometothejungle.com/fr/jobs?query=lean&refinementList%5Boffices.country_code%5D%5B%5D=MA",
         ["li[data-testid='search-results-list-item-wrapper']", "article", "a[href*='/jobs/']"],
         wait="a[href*='/jobs/']")
    look("JOOBLE", "https://ma.jooble.org/emploi-lean", ["article", "div[data-test-name='_jobCard']", "h2"], wait="article")
finally:
    d.quit()
