import sys, io, re, urllib3, requests, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup
from common import HDRS
urllib3.disable_warnings()
S = requests.Session(); S.headers.update(HDRS); S.verify = False

r = S.get("https://www.anapec.ma/chercheurs/offres", timeout=30)
s = BeautifulSoup(r.text, "html.parser")
print("len", len(r.text))
offs = [a for a in s.select("a[href]") if re.search(r"/offre", a.get("href", ""))]
print("offer links:", len(offs))
for a in offs[:12]:
    print("   ", re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:52], "|", a.get("href")[:80])

for sel in ["div.card", "article", "div.offre", "tr", "div.job", "li", "div.row > div"]:
    els = s.select(sel)
    print(f"  {sel!r:22s} -> {len(els)}")

# find the card that wraps an offer link
if offs:
    p = offs[3].find_parent(["div", "article", "li", "tr"])
    if p:
        print("\nPARENT class:", p.get("class"))
        print(p.prettify()[:1800])

# look for an underlying JSON/api call
for m in set(re.findall(r'["\'](/[a-z0-9_\-/]*(?:api|ajax|offres)[a-z0-9_\-/]*)["\']', r.text, re.I))[:20]:
    print("  candidate path:", m)
# pagination
for a in s.select("a[href*='page'], ul.pagination a"):
    print("  page link:", a.get_text(strip=True)[:10], a.get("href")[:70])
