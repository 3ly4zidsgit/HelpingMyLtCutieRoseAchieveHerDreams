"""Probe the bypass routes: WTTJ Algolia keys, ANAPEC over broken TLS,
Indeed RSS, Bayt real search endpoint, Workday tenants, unscraped MA boards."""
import requests, re, sys, json, urllib3
from bs4 import BeautifulSoup
from common import HDRS
urllib3.disable_warnings()

S = requests.Session(); S.headers.update(HDRS)

def hdr(t): print("\n" + "=" * 22 + " " + t, flush=True)

# ------------------------------------------------- WTTJ Algolia credentials
hdr("WTTJ ALGOLIA")
try:
    r = S.get("https://www.welcometothejungle.com/fr/jobs", timeout=30)
    html = r.text
    app = re.findall(r'["\']?(?:algolia)?[_-]?app(?:lication)?[_-]?id["\']?\s*[:=]\s*["\']([A-Z0-9]{8,12})["\']', html, re.I)
    key = re.findall(r'["\']?(?:algolia)?[_-]?(?:api[_-]?)?key["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']', html, re.I)
    print("inline appId:", set(app), "| keys:", set(key))
    # keys usually live in the JS bundle, not the HTML
    js = re.findall(r'src="([^"]+\.js)"', html)
    print(f"{len(js)} js bundles; scanning first 8")
    for u in js[:8]:
        if u.startswith("/"): u = "https://www.welcometothejungle.com" + u
        try:
            b = S.get(u, timeout=25).text
        except Exception:
            continue
        a2 = set(re.findall(r'["\']([A-Z0-9]{10})["\']\s*,\s*["\']([a-f0-9]{32})["\']', b))
        a3 = set(re.findall(r'algolia[^"\']{0,30}["\']([A-Z0-9]{10})["\']', b, re.I))
        k3 = set(re.findall(r'["\']([a-f0-9]{32})["\']', b))
        if a2 or a3:
            print(f"  {u[-60:]}\n    pairs={list(a2)[:3]} appIds={list(a3)[:3]} keys={list(k3)[:3]}")
except Exception as e:
    print("ERR", e)

# WTTJ public REST
for u in ["https://api.welcometothejungle.com/api/v1/organizations?page=1&country=MA",
          "https://api.welcometothejungle.com/api/v1/jobs?page=1",
          "https://api.welcometothejungle.com/api/v1/search/jobs?query=lean"]:
    try:
        r = S.get(u, timeout=20)
        print(f"  {r.status_code} len={len(r.text):7d} {u}")
    except Exception as e:
        print("  ERR", u, str(e)[:40])

# ------------------------------------------------- ANAPEC
hdr("ANAPEC")
for u in ["https://www.anapec.org/", "http://www.anapec.org/",
          "https://anapec.org/", "https://www.anapec.ma/",
          "https://www.anapec.org/sigec-app-rv/fr/offres",
          "https://candidat.anapec.org/", "https://emploi.anapec.org/"]:
    try:
        r = S.get(u, timeout=20, verify=False, allow_redirects=True)
        t = BeautifulSoup(r.text, "html.parser")
        print(f"  {r.status_code} len={len(r.text):7d} -> {r.url[:60]} | {(t.title.get_text(strip=True) if t.title else '')[:44]}")
    except Exception as e:
        print(f"  ERR {u[:44]} {type(e).__name__}: {str(e)[:44]}")

# ------------------------------------------------- Indeed RSS / mobile
hdr("INDEED alt routes")
for u in ["https://ma.indeed.com/rss?q=lean+six+sigma&l=Maroc",
          "https://ma.indeed.com/jobs?q=lean&l=Maroc&format=rss",
          "https://ma.indeed.com/m/jobs?q=lean&l=Maroc",
          "https://ma.indeed.com/api/jobs?q=lean"]:
    try:
        r = S.get(u, timeout=20)
        print(f"  {r.status_code} len={len(r.text):7d} ct={r.headers.get('content-type','')[:28]} {u[:56]}")
    except Exception as e:
        print("  ERR", str(e)[:50])

# ------------------------------------------------- Bayt search endpoint
hdr("BAYT search endpoints")
for u in ["https://www.bayt.com/en/morocco/jobs/?q=lean",
          "https://www.bayt.com/en/jobs/q/lean/morocco/",
          "https://www.bayt.com/en/morocco/jobs/six-sigma-jobs/",
          "https://www.bayt.com/en/international/jobs/lean-jobs/",
          "https://www.bayt.com/en/morocco/jobs/continuous-improvement-jobs/",
          "https://www.bayt.com/en/morocco/jobs/engineering-jobs/",
          "https://www.bayt.com/en/morocco/jobs/quality-jobs/",
          "https://www.bayt.com/en/morocco/jobs/supply-chain-jobs/",
          "https://www.bayt.com/en/morocco/jobs/industrial-engineering-jobs/",
          "https://www.bayt.com/en/morocco/jobs/production-engineer-jobs/"]:
    try:
        r = S.get(u, timeout=20)
        print(f"  {r.status_code} len={len(r.text):7d} {u[46:]}")
    except Exception as e:
        print("  ERR", str(e)[:50])

# ------------------------------------------------- Workday tenants
hdr("WORKDAY tenants")
TEN = ["valeo", "safran", "alstom", "stellantis", "renault", "schneiderelectric",
       "se", "danone", "nestle", "pfizer", "sanofi", "capgemini", "eaton",
       "emerson", "te", "honeywell", "jti", "mondelez", "philips", "abb"]
for t in TEN:
    for host in ["wd3", "wd1", "wd5"]:
        u = f"https://{t}.{host}.myworkdayjobs.com/wday/cxs/{t}/External/jobs"
        try:
            r = S.post(u, json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "lean"}, timeout=10)
            if r.status_code == 200:
                d = r.json()
                print(f"  OK {t}.{host} total={d.get('total')} items={len(d.get('jobPostings', []))}")
        except Exception:
            pass

# ------------------------------------------------- unscraped MA boards
hdr("MA BOARDS not yet scraped")
for name, u in [
    ("marocemploi", "https://www.marocemploi.net/?s=lean"),
    ("alwadifa", "https://www.alwadifa-maroc.com/?s=lean"),
    ("modiami", "https://www.modiami.com/search?q=lean"),
    ("stagiaires", "https://www.stagiaires.ma/?s=lean"),
    ("emploipublic", "https://www.emploi-public.ma/"),
    ("jobsquare", "https://www.jobsquare.ma/"),
    ("marocjob", "https://www.marocjob.ma/?s=lean"),
    ("emploimaroc", "https://emploi-maroc.net/?s=lean"),
    ("jobzz", "https://www.jobzz.ma/?s=lean"),
    ("tanmia", "https://www.tanmia.ma/offres-emploi/"),
    ("recrutons", "https://www.recrutons.ma/?s=lean"),
    ("marocemploi2", "https://www.marocemploi.net/?s=amelioration+continue"),
]:
    try:
        r = S.get(u, timeout=20)
        s = BeautifulSoup(r.text, "html.parser")
        arts = len(s.select("article"))
        links = len(s.select("a[href*='emploi'], a[href*='offre'], a[href*='job']"))
        print(f"  {name:14s} {r.status_code} len={len(r.text):7d} art={arts:3d} links={links:3d} | "
              f"{(s.title.get_text(strip=True) if s.title else '')[:38]}")
    except Exception as e:
        print(f"  {name:14s} ERR {type(e).__name__}: {str(e)[:40]}")
