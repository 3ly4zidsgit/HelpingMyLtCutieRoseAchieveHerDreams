import requests, re
from bs4 import BeautifulSoup
from common import HDRS

S = requests.Session(); S.headers.update(HDRS)

def look(name, url, sels):
    print("="*25, name)
    try:
        r = S.get(url, timeout=30)
    except Exception as e:
        print("ERR", e); return
    print("status", r.status_code, "len", len(r.text))
    s = BeautifulSoup(r.text, "html.parser")
    print("TITLE:", (s.title.get_text(strip=True) if s.title else "")[:100])
    for sel in sels:
        els = s.select(sel)
        print(f"  {sel!r:45s} -> {len(els)}")
        if els:
            print("     sample:", re.sub(r"\s+"," ", els[0].get_text(" ", strip=True))[:220])
            a = els[0].select_one("a") or (els[0] if els[0].name=="a" else None)
            if a: print("     href:", a.get("href"))

look("MAROCANNONCES", "https://www.marocannonces.com/maroc/offres-emploi-b309.html",
     ["ul.cars-list li", "div.holder", "li", "a.tit"])

look("OPTIONCARRIERE", "https://www.optioncarriere.ma/emploi?s=lean&l=Maroc",
     ["article.job", "article", "li.job", "div.job"])

look("NOVOJOB", "https://www.novojob.com/maroc/offres-emploi?keywords=lean",
     ["div.job-item", "article", "div.offre", "li.job", "div.card"])

look("DREAMJOB", "https://www.dreamjob.ma/?s=lean",
     ["article", "div.job_listing", "li.job_listing", "h2.entry-title"])

look("STAGIAIRES", "https://www.stagiaires.ma/?s=lean",
     ["article", "div.job", "h2"])

look("WTTJ", "https://www.welcometothejungle.com/fr/jobs?query=lean&refinementList%5Boffices.country_code%5D%5B%5D=MA",
     ["li[data-testid]", "article", "div[data-testid='search-results']"])
