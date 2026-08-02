import sys, io, re, urllib3, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup
from common import HDRS
urllib3.disable_warnings()
S = requests.Session(); S.headers.update(HDRS); S.verify = False
B = "https://www.anapec.org/sigec-app-rv/fr/chercheurs/resultat_recherche"

for params in [{"motclee": "lean"}, {"motclee": "ingenieur"},
               {"motclee": "", "ville": "Casablanca"}, {}]:
    r = S.get(B, params=params, timeout=30)
    s = BeautifulSoup(r.text, "html.parser")
    print(f"\n--- params={params} status={r.status_code} len={len(r.text)}")
    print("    url:", r.url[:110])
    print("    title:", (s.title.get_text(strip=True) if s.title else "")[:60])
    for sel in ["div.offre", "table tr", "div.bloc_offre", "ul li a", "div.panel",
                "div.result", "a[href*='bloc_offre']", "a[href*='postulation']", "div.row"]:
        els = s.select(sel)
        if els:
            print(f"    {sel!r:32s} -> {len(els)}")
    txt = s.get_text(" ", strip=True)
    print("    body:", re.sub(r"\s+", " ", txt)[:260])

# also try the offers-listing path seen on the homepage
for u in ["https://www.anapec.org/sigec-app-rv/fr/chercheurs/resultat_recherche/tout:all",
          "https://www.anapec.ma/chercheurs/offres",
          "https://www.anapec.ma/chercheurs/offres?q=lean"]:
    try:
        r = S.get(u, timeout=30)
        s = BeautifulSoup(r.text, "html.parser")
        print(f"\n--- {u}\n    {r.status_code} len={len(r.text)} title={(s.title.get_text(strip=True) if s.title else '')[:50]}")
        for sel in ["div.offre", "table tr", "a[href*='offre']", "div.card", "article", "div.job"]:
            els = s.select(sel)
            if els:
                print(f"    {sel!r:26s} -> {len(els)}   e.g. {re.sub(r'\\s+',' ',els[0].get_text(' ',strip=True))[:90]}")
    except Exception as e:
        print("  ERR", str(e)[:60])
