"""Genuinely worldwide remote roles: the board's own geo field must say
Worldwide/Anywhere/Global (or the ad must explicitly promise work-from-anywhere),
and the text must not require a visa, work permit, relocation or on-site presence.
Full feeds are pulled and filtered locally rather than relying on server-side search."""
import requests, re, sys, time, html as ihtml
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from common import HDRS, blank, save, jid, norm, find_emails

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

# the board's own geo field says "open to the whole world"
GEO_GLOBAL = re.compile(r"worldwide|anywhere in the world|^\s*anywhere\s*$|^\s*global\s*$|"
                        r"globally|any location|any country|^\s*remote\s*$|^\s*world\s*$|"
                        r"anywhere\s*\(|100%\s*remote")
# or the ad text promises it
TXT_GLOBAL = re.compile(r"work from anywhere|anywhere in the world|from any country|"
                        r"any time ?zone|globally distributed|fully distributed|"
                        r"location[- ]independent|no matter where you (are|live)|"
                        r"work remotely from anywhere|remote[- ]first company")
# real geographic / immigration restrictions only
BLOCKER = re.compile(
    r"must (be (located|based|physically|resident)|reside|live) (in|within)|"
    r"(authoriz|authoris)(ed|ation) to work|right to work in|eligible to work in|"
    r"work permit|visa sponsorship|cannot sponsor|no sponsorship|sponsorship (is )?not|"
    r"security clearance|u\.?s\.? citizen|green card|"
    r"\bhybrid\b|\bon[- ]?site\b|\bonsite\b|\bin[- ]office\b|relocat")

TITLE_OK = re.compile(
    r"\blean\b|\bsix ?sigma\b|\bkaizen\b|\bkanban\b|\bblack belt\b|\bgreen belt\b|"
    r"\bcontinuous improvement\b|\bprocess improvement\b|\bprocess excellence\b|"
    r"\boperational excellence\b|\boperations excellence\b|\bops excellence\b|"
    r"\bmanufacturing excellence\b|\bbusiness process\b|"
    r"\bprocess (analyst|consultant|engineer|manager|owner|optimi|mining|lead)|"
    r"\bindustrial engineer|\bmanufacturing engineer|\bmethods? engineer|"
    r"\bproduction (engineer|manager|planner)|\bindustriali[sz]ation\b|"
    r"\bquality (engineer|manager|specialist|analyst|lead|assurance)|"
    r"\bsupply chain\b|\bplant manager\b|\bproductivity\b|"
    r"\blogistics (manager|analyst|coordinator|specialist)|"
    r"\boperations (analyst|excellence|improvement|manager|specialist)|"
    r"\bbusiness (analyst|operations)\b|\bvalue stream\b|"
    r"\bamelioration continue\b|\bexcellence operationnelle\b|\bgenie industriel\b|"
    r"\bingenieur (industriel|methodes|process|production|qualite)\b|"
    r"\bworkflow (analyst|manager)|\bproject (engineer|manager).*(process|operations|supply)")
BAD_TITLE = re.compile(r"\btechnicien\b|\btechnician\b")

rows, seen = [], set()
stats = {"title_ko": 0, "geo_ko": 0, "blocked": 0, "kept": 0}

def add(src, title, comp, geo, ctype, date, url, desc, extra=None):
    if not title or not url: return False
    t = norm(title)
    if BAD_TITLE.search(t) or not TITLE_OK.search(t):
        stats["title_ko"] += 1; return False
    geo_n, txt_n = norm(geo), norm(desc)
    if not (GEO_GLOBAL.search(geo_n) or TXT_GLOBAL.search(txt_n)):
        stats["geo_ko"] += 1; return False
    if BLOCKER.search(txt_n):
        stats["blocked"] += 1; return False
    k = jid(url, title, comp)
    if k in seen: return False
    seen.add(k); stats["kept"] += 1
    rows.append(blank(source=src, job_title=title, company=comp,
                      location_city=geo.strip()[:40] or "Worldwide",
                      country="Remote mondial (sans visa)",
                      remote="100% remote - worldwide", contract_type=ctype,
                      date_posted=date, url=url, description_snippet=desc[:800],
                      contact_email=", ".join(find_emails(desc)[:2]),
                      keywords_matched="worldwide-remote", score=10, **(extra or {})))
    return True

# --------------------------------------------------------------- RemoteOK
try:
    for j in S.get("https://remoteok.com/api", timeout=40).json():
        if not isinstance(j, dict) or "position" not in j: continue
        add("RemoteOK", g(j, "position"), g(j, "company"), g(j, "location", default="Worldwide"),
            "Full-time", g(j, "date")[:10], g(j, "url", "apply_url"),
            clean(j.get("description", "")), {"sector": ", ".join((j.get("tags") or [])[:6])})
    print(f"RemoteOK done ({stats['kept']})", flush=True)
except Exception as e:
    print("RemoteOK ERR", e, flush=True)

# --------------------------------------------------------------- Remotive (full feed)
try:
    d = S.get("https://remotive.com/api/remote-jobs", params={"limit": 2000}, timeout=90).json()
    js = d.get("jobs", [])
    print(f"Remotive full feed: {len(js)} jobs", flush=True)
    for j in js:
        add("Remotive", g(j, "title"), g(j, "company_name"),
            g(j, "candidate_required_location"), g(j, "job_type"),
            g(j, "publication_date")[:10], g(j, "url"), clean(j.get("description", "")),
            {"salary": g(j, "salary"), "sector": g(j, "category")})
    print(f"Remotive done ({stats['kept']})", flush=True)
except Exception as e:
    print("Remotive ERR", e, flush=True)

# --------------------------------------------------------------- Jobicy
for geo in ["anywhere", ""]:
    for tag in ["operations", "business", "supply-chain", "engineering", "management",
                "project-management", "quality-assurance", "manufacturing", "consulting",
                "data", "product", "finance", "admin", "analytics"]:
        try:
            p = {"count": 100, "tag": tag}
            if geo: p["geo"] = geo
            for j in S.get("https://jobicy.com/api/v2/remote-jobs", params=p, timeout=30).json().get("jobs", []):
                add("Jobicy", g(j, "jobTitle"), g(j, "companyName"), g(j, "jobGeo"),
                    g(j, "jobType"), g(j, "pubDate")[:10], g(j, "url"),
                    clean(j.get("jobDescription") or j.get("jobExcerpt") or ""),
                    {"experience_required": g(j, "jobLevel"), "sector": g(j, "jobIndustry")})
        except Exception:
            pass
        time.sleep(0.2)
print(f"Jobicy done ({stats['kept']})", flush=True)

# --------------------------------------------------------------- WeWorkRemotely
for cat in ["remote-jobs", "categories/remote-management-and-finance-jobs",
            "categories/remote-business-executive-management-jobs",
            "categories/remote-product-jobs", "categories/all-other-remote-jobs",
            "categories/remote-customer-support-jobs", "categories/remote-design-jobs",
            "categories/remote-devops-sysadmin-jobs", "categories/remote-programming-jobs"]:
    try:
        root = ET.fromstring(S.get(f"https://weworkremotely.com/{cat}.rss", timeout=30).content)
    except Exception:
        continue
    for it in root.iter("item"):
        def t(tag):
            e = it.find(tag); return (e.text or "") if e is not None else ""
        raw = t("title"); comp, _, title = raw.partition(":")
        add("WeWorkRemotely", (title or raw).strip(), comp.strip(), t("region"),
            t("type"), t("pubDate")[:16], t("link"), clean(t("description")),
            {"sector": t("category")})
print(f"WeWorkRemotely done ({stats['kept']})", flush=True)

# --------------------------------------------------------------- Himalayas
for off in range(0, 2000, 100):
    try:
        d = S.get("https://himalayas.app/jobs/api", params={"limit": 100, "offset": off}, timeout=40).json()
        js = d.get("jobs", d if isinstance(d, list) else [])
        if not js: break
        for j in js:
            restr = j.get("locationRestrictions") or j.get("countries") or []
            geo = ", ".join(restr) if isinstance(restr, list) and restr else "Worldwide"
            add("Himalayas", g(j, "title"), g(j, "companyName", "company"), geo,
                g(j, "employmentType"), str(g(j, "pubDate", "publishedDate"))[:10],
                g(j, "applicationLink", "url", "guid"),
                clean(j.get("description") or j.get("excerpt") or ""),
                {"experience_required": g(j, "seniority")})
    except Exception:
        break
    time.sleep(0.25)
print(f"Himalayas done ({stats['kept']})", flush=True)

# --------------------------------------------------------------- WorkingNomads
try:
    for j in S.get("https://www.workingnomads.com/api/exposed_jobs/", timeout=45).json():
        add("WorkingNomads", g(j, "title"), g(j, "company_name"), g(j, "location"),
            "", g(j, "pub_date")[:10], g(j, "url"), clean(j.get("description", "")),
            {"sector": g(j, "category_name")})
    print(f"WorkingNomads done ({stats['kept']})", flush=True)
except Exception as e:
    print("WorkingNomads ERR", e, flush=True)

# --------------------------------------------------------------- Arbeitnow
for page in range(1, 30):
    try:
        js = S.get("https://www.arbeitnow.com/api/job-board-api",
                   params={"page": page}, timeout=30).json().get("data", [])
        if not js: break
        for j in js:
            if not j.get("remote"): continue
            add("Arbeitnow", g(j, "title"), g(j, "company_name"), g(j, "location"),
                g(j, "job_types"), str(j.get("created_at", ""))[:10], g(j, "url"),
                clean(j.get("description", "")), {"sector": g(j, "tags")})
    except Exception:
        break
    time.sleep(0.2)
print(f"Arbeitnow done ({stats['kept']})", flush=True)

print(f"\nfunnel: {stats}")
print(f"TOTAL worldwide-remote, visa-free: {len(rows)}")
save("worldwide", rows)
for r in sorted(rows, key=lambda x: x["job_title"]):
    print(f"  {r['job_title'][:54]:54s} | {r['company'][:22]:22s} | "
          f"{r['location_city'][:22]:22s} | {r['source'][:14]}")
