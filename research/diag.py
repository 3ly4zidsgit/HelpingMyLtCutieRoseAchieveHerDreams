import json, re, requests
from bs4 import BeautifulSoup
from common import HDRS, relevance, norm, find_emails

d = json.load(open("data/rekrute.json", encoding="utf-8"))
print("=== suspicious rekrute rows (IT / non-industrial) ===")
for r in d:
    if re.search(r"full stack|node\.js|react|developpeur|développeur|java|python|devops|frontend|backend",
                 norm(r["job_title"])):
        print(" TITLE:", r["job_title"][:60])
        print("   hits:", r["keywords_matched"], "| score", r["score"])
        print("   desc:", r["description_snippet"][:200])
        print()

print("=== OPTIONCARRIERE detail page structure ===")
S = requests.Session(); S.headers.update(HDRS)
oc = json.load(open("data/selenium_oc.json", encoding="utf-8"))
u = oc[0]["url"]; print("url:", u)
r = S.get(u, timeout=30)
print("status", r.status_code, "len", len(r.text))
s = BeautifulSoup(r.text, "html.parser")
print("emails:", find_emails(r.text)[:5])
for sel in ["section.content", "article", "div.container", "ul.details", "ul.tags",
            "section.details", "div.content", "header h1", "p.company", "span.company",
            "ul.location", "div.job-header"]:
    els = s.select(sel)
    print(f"  {sel!r:22s} -> {len(els)}")
    if els:
        print("      ", re.sub(r"\s+", " ", els[0].get_text(" ", strip=True))[:260])
