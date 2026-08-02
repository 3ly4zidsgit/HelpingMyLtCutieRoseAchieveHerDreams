import requests, re, json
from bs4 import BeautifulSoup
from common import HDRS, find_emails

S = requests.Session(); S.headers.update(HDRS)

d = json.load(open("data/rekrute.json", encoding="utf-8"))
print("rekrute rows:", len(d))
u = d[0]["url"]; print("test url:", u)
r = S.get(u, timeout=30)
print("status", r.status_code, "len", len(r.text))
s = BeautifulSoup(r.text, "html.parser")
print("emails on page:", find_emails(r.text))
for sel in ["div.contentbloc", "ul.recapOffre", "div.col-md-12 .section", "h1", "span.recruteur", "div#recruiter"]:
    els = s.select(sel)
    print(f"  {sel!r} -> {len(els)}")
    if els: print("     ", re.sub(r"\s+"," ", els[0].get_text(" ", strip=True))[:400])

print("\n=== DUCKDUCKGO test ===")
r2 = S.post("https://html.duckduckgo.com/html/", data={"q": "Aptiv Maroc site officiel"}, timeout=25)
print("ddg status", r2.status_code, "len", len(r2.text))
s2 = BeautifulSoup(r2.text, "html.parser")
for a in s2.select("a.result__a")[:5]:
    print("  ", a.get_text(strip=True)[:60], "|", a.get("href","")[:110])
