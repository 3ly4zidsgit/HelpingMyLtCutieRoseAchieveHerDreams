import requests, re, json, urllib3
from bs4 import BeautifulSoup
from common import HDRS
urllib3.disable_warnings()
S = requests.Session(); S.headers.update(HDRS); S.verify = False

print("=" * 20, "ANAPEC structure")
r = S.get("https://www.anapec.org/sigec-app-rv/", timeout=25)
s = BeautifulSoup(r.text, "html.parser")
print("title:", s.title.get_text(strip=True)[:70] if s.title else "")
links = [(a.get_text(" ", strip=True)[:40], a.get("href")) for a in s.select("a[href]")]
inter = [l for l in links if re.search(r"offre|emploi|recherche|search|job", str(l[1] or ""), re.I)]
for t, h in inter[:25]:
    print(f"   {t:40s} {h}")
forms = s.select("form")
print(f"forms: {len(forms)}")
for f in forms[:3]:
    print("   action:", f.get("action"), "method:", f.get("method"),
          "inputs:", [i.get("name") for i in f.select("input,select")][:10])

print("\n" + "=" * 20, "ANAPEC.ma")
r2 = S.get("https://www.anapec.ma/", timeout=25)
s2 = BeautifulSoup(r2.text, "html.parser")
print("title:", s2.title.get_text(strip=True)[:70] if s2.title else "")
for a in s2.select("a[href]"):
    h = a.get("href") or ""
    if re.search(r"offre|emploi|recrut|job", h, re.I):
        print(f"   {a.get_text(' ', strip=True)[:40]:40s} {h[:80]}")

print("\n" + "=" * 20, "WTTJ organizations MA")
r3 = S.get("https://api.welcometothejungle.com/api/v1/organizations",
           params={"page": 1, "country": "MA"}, timeout=40)
print("status", r3.status_code, "len", len(r3.text))
try:
    d = r3.json()
    print("keys:", list(d.keys())[:8])
    orgs = d.get("organizations") or d.get("data") or []
    print("orgs:", len(orgs), "meta:", d.get("meta"))
    for o in orgs[:5]:
        print("   ", str(o.get("name"))[:32], "|", o.get("slug"), "|",
              (o.get("offices") or [{}])[0].get("country") if o.get("offices") else "")
    if orgs:
        slug = orgs[0].get("slug")
        for u in [f"https://api.welcometothejungle.com/api/v1/organizations/{slug}/jobs",
                  f"https://api.welcometothejungle.com/api/v1/organizations/{slug}"]:
            rr = S.get(u, timeout=25)
            print(f"   {rr.status_code} len={len(rr.text):7d} {u}")
except Exception as e:
    print("json ERR", e, r3.text[:200])
