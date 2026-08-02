import requests, re, sys, time, html as ihtml
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, find_emails

S = requests.Session(); S.headers.update(HDRS)

def clean(h):
    if not h: return ""
    return re.sub(r"\s+", " ", BeautifulSoup(ihtml.unescape(str(h)), "html.parser").get_text(" ", strip=True))

def g(d, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    return default

import re as _re
from common import norm as _norm
# For remote/international we only keep offers whose TITLE is genuinely about
# industrial engineering / lean / continuous improvement / ops-excellence.
TITLE_OK = _re.compile(
    r"\blean\b|\bsix ?sigma\b|\bkaizen\b|\bkanban\b|\bblack belt\b|\bgreen belt\b|"
    r"\bcontinuous improvement\b|\bprocess improvement\b|\bprocess excellence\b|"
    r"\boperational excellence\b|\boperations excellence\b|\bmanufacturing excellence\b|"
    r"\bbusiness process\b|\bindustrial engineer|\bmanufacturing engineer|"
    r"\bprocess engineer|\bmethods? engineer|\bproduction engineer|\bindustrialization\b|"
    r"\bquality (engineer|manager|specialist)|\bsupply chain\b|\bplant manager\b|"
    r"\bproduction manager\b|\bmanufacturing manager\b|\bindustrial operations\b|"
    r"\bproductivity\b|\bprocess (analyst|consultant|optimi)|\bops excellence\b|"
    r"\bamelioration continue\b|\bexcellence operationnelle\b|\bgenie industriel\b|"
    r"\bingenieur (industriel|methodes|process|production|qualite)\b")

def add(rows, src, title, comp, loc, ctype, date, url, desc, extra=None):
    keep, score, hits = relevance(title, desc)
    if not keep: return False
    if not TITLE_OK.search(_norm(title)): return False
    e = extra or {}
    rows.append(blank(source=src, job_title=title, company=comp, location_city=loc,
                      country="International (Remote)", remote="Oui / Remote",
                      contract_type=ctype, date_posted=date, url=url,
                      description_snippet=desc[:600],
                      contact_email=", ".join(find_emails(desc)[:3]),
                      keywords_matched=", ".join(hits), score=score, **e))
    return True

rows = []

# ---------- RemoteOK ----------
try:
    d = S.get("https://remoteok.com/api", timeout=30).json()
    n = 0
    for j in d:
        if not isinstance(j, dict) or "position" not in j: continue
        desc = clean(j.get("description", "")) + " " + " ".join(j.get("tags") or [])
        if add(rows, "RemoteOK", g(j, "position"), g(j, "company"),
               g(j, "location", default="Worldwide"), "Full-time",
               g(j, "date")[:10], g(j, "url", "apply_url"), desc,
               {"salary": (f"{j.get('salary_min','')}-{j.get('salary_max','')}" if j.get("salary_min") else ""),
                "sector": ", ".join((j.get("tags") or [])[:6])}): n += 1
    print(f"RemoteOK: {len(d)} scanned, +{n}")
except Exception as e: print("RemoteOK ERR", e)

# ---------- Remotive (multi query) ----------
tot = 0
for q in ["lean", "six sigma", "continuous improvement", "operational excellence",
          "process improvement", "industrial engineer", "manufacturing", "supply chain",
          "operations excellence", "quality engineer", "kaizen", "process engineer",
          "business process", "production", "logistics", "operations manager",
          "process excellence", "black belt", "methods engineer", "plant manager",
          "productivity", "quality manager", "process analyst", "lean consultant",
          "manufacturing engineer", "production manager", "process optimization"]:
    try:
        d = S.get("https://remotive.com/api/remote-jobs", params={"search": q, "limit": 100}, timeout=30).json()
        for j in d.get("jobs", []):
            desc = clean(j.get("description", ""))
            if add(rows, "Remotive", g(j, "title"), g(j, "company_name"),
                   g(j, "candidate_required_location", default="Worldwide"),
                   g(j, "job_type"), g(j, "publication_date")[:10], g(j, "url"), desc,
                   {"salary": g(j, "salary"), "sector": g(j, "category")}): tot += 1
    except Exception as e: print("Remotive ERR", q, e)
    time.sleep(0.4)
print(f"Remotive: +{tot}")

# ---------- Jobicy ----------
tot = 0
for tag in ["operations", "business", "supply-chain", "engineering", "management",
            "project-management", "quality-assurance", "manufacturing", "consulting", "data"]:
    try:
        d = S.get("https://jobicy.com/api/v2/remote-jobs", params={"count": 100, "tag": tag}, timeout=30).json()
        for j in d.get("jobs", []):
            desc = clean(j.get("jobDescription") or j.get("jobExcerpt") or "")
            if add(rows, "Jobicy", g(j, "jobTitle"), g(j, "companyName"),
                   g(j, "jobGeo", default="Worldwide"), g(j, "jobType"),
                   g(j, "pubDate")[:10], g(j, "url"), desc,
                   {"salary": g(j, "annualSalaryMin", "salaryMin"),
                    "experience_required": g(j, "jobLevel"),
                    "sector": g(j, "jobIndustry")}): tot += 1
    except Exception as e: print("Jobicy ERR", tag, e)
    time.sleep(0.4)
print(f"Jobicy: +{tot}")

# ---------- WorkingNomads ----------
try:
    d = S.get("https://www.workingnomads.com/api/exposed_jobs/", timeout=40).json()
    n = 0
    for j in d:
        desc = clean(j.get("description", "")) + " " + g(j, "tags")
        if add(rows, "WorkingNomads", g(j, "title"), g(j, "company_name"),
               g(j, "location", default="Worldwide"), "", g(j, "pub_date")[:10],
               g(j, "url"), desc, {"sector": g(j, "category_name")}): n += 1
    print(f"WorkingNomads: {len(d)} scanned, +{n}")
except Exception as e: print("WorkingNomads ERR", e)

# ---------- Himalayas ----------
tot = 0
for off in range(0, 400, 100):
    try:
        d = S.get("https://himalayas.app/jobs/api", params={"limit": 100, "offset": off}, timeout=40).json()
        js = d.get("jobs", d if isinstance(d, list) else [])
        if not js: break
        for j in js:
            desc = clean(j.get("description") or j.get("excerpt") or "")
            loc = g(j, "locationRestrictions", "countries", default="Worldwide")
            if add(rows, "Himalayas", g(j, "title"), g(j, "companyName", "company"),
                   loc, g(j, "employmentType"), str(g(j, "pubDate", "publishedDate"))[:10],
                   g(j, "applicationLink", "url", "guid"), desc,
                   {"salary": g(j, "salaryRange", "minSalary"),
                    "experience_required": g(j, "seniority")}): tot += 1
    except Exception as e:
        print("Himalayas ERR", off, e); break
    time.sleep(0.4)
print(f"Himalayas: +{tot}")

# ---------- Arbeitnow (EU/remote) ----------
tot = 0
for page in range(1, 12):
    try:
        d = S.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page}, timeout=30).json()
        js = d.get("data", [])
        if not js: break
        for j in js:
            desc = clean(j.get("description", "")) + " " + g(j, "tags", "job_types")
            if add(rows, "Arbeitnow", g(j, "title"), g(j, "company_name"),
                   g(j, "location", default="Europe"), g(j, "job_types"),
                   str(j.get("created_at", ""))[:10], g(j, "url"), desc,
                   {"sector": g(j, "tags")}): tot += 1
    except Exception as e:
        print("Arbeitnow ERR", page, e); break
    time.sleep(0.3)
print(f"Arbeitnow: +{tot}")

# ---------- WeWorkRemotely RSS ----------
try:
    import xml.etree.ElementTree as ET
    n = 0
    for feed in ["https://weworkremotely.com/remote-jobs.rss",
                 "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
                 "https://weworkremotely.com/categories/remote-business-executive-management-jobs.rss",
                 "https://weworkremotely.com/categories/remote-product-jobs.rss"]:
        try:
            root = ET.fromstring(S.get(feed, timeout=30).content)
        except Exception: continue
        for it in root.iter("item"):
            def t(tag):
                e = it.find(tag); return (e.text or "") if e is not None else ""
            raw = t("title"); comp, _, title = raw.partition(":")
            title = (title or raw).strip(); comp = comp.strip()
            desc = clean(t("description"))
            if add(rows, "WeWorkRemotely", title, comp, t("region") or "Worldwide",
                   t("type"), t("pubDate")[:16], t("link"), desc,
                   {"sector": t("category")}): n += 1
    print(f"WeWorkRemotely: +{n}")
except Exception as e: print("WWR ERR", e)

# dedupe
uniq = {}
for r in rows:
    k = jid(r["url"], r["job_title"], r["company"])
    if k not in uniq or r["score"] > uniq[k]["score"]:
        uniq[k] = r
out = sorted(uniq.values(), key=lambda x: -x["score"])
print(f"TOTAL remote relevant (deduped): {len(out)}")
save("remote", out)
