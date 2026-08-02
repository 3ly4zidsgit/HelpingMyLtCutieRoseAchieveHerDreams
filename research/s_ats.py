"""Harvest the public ATS feeds discovered by probe_ats.py, keep Morocco + relevant."""
import requests, re, sys, time, html as ihtml, json
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, norm, find_emails

S = requests.Session(); S.headers.update(HDRS)
S.headers["Accept"] = "application/json,text/plain,*/*"

# word boundaries matter here: without them "professional" matches "fes" and
# "sales" matches "sale", which dragged in US/UK/NL jobs.
MA = re.compile(r"\b(morocco|maroc|casablanca|tanger|tangier|rabat|k[ée]nitra|kenitra|"
                r"marrakech|marrakesh|agadir|f[èe]s|fez|mekn[èe]s|meknes|oujda|t[ée]touan|"
                r"tetouan|el jadida|nouaceur|bouskoura|sal[ée]|berrechid|settat|mohammedia|"
                r"skhirat|t[ée]mara|benguerir|had soualem|ain sebaa|tit mellil|larache|"
                r"safi|nador|khouribga|b[ée]ni mellal|laayoune|dakhla)\b", re.I)

def clean(h):
    if not h: return ""
    return re.sub(r"\s+", " ", BeautifulSoup(ihtml.unescape(str(h)), "html.parser").get_text(" ", strip=True))

rows = []
def push(src, title, comp, loc, ctype, date, url, desc, **extra):
    # the location field is authoritative; a stray "Morocco" in a boilerplate
    # description is not enough to call the job Moroccan
    if not MA.search(loc or ""):
        return False
    keep, score, hits = relevance(title, desc)
    if not keep: return False
    if re.search(r"\btechnicien\b|\btechnician\b", norm(title)): return False
    rows.append(blank(source=src, job_title=title, company=comp, location_city=loc,
                      country="Maroc", contract_type=ctype, date_posted=date, url=url,
                      description_snippet=desc[:800],
                      contact_email=", ".join(find_emails(desc)[:2]),
                      keywords_matched=", ".join(hits), score=score, **extra))
    return True

def J(url, tries=4, **kw):
    """SmartRecruiters throttles at the TLS layer (SSL EOF) when hit hard, so back off."""
    for i in range(tries):
        try:
            r = S.get(url, timeout=25, **kw)
            if r.status_code == 429:
                time.sleep(5 * (i + 1)); continue
            return r.json() if r.status_code == 200 else None
        except Exception:
            time.sleep(3 * (i + 1))
    return None

# only spend a detail request when the title already looks like our domain
TITLE_HINT = re.compile(
    r"lean|sigma|kaizen|kanban|amelioration|continuous improvement|excellence|"
    r"industriel|industrial|methodes|methods|process|proces|production|qualit|quality|"
    r"supply chain|logistic|logistique|manufactur|planification|planning|planner|"
    r"industrialis|industrializ|maintenance|performance|productivit|operations|"
    r"ordonnancement|qhse|hse|value stream|black belt|green belt|opex", re.I)

# ---------------------------------------------------- SmartRecruiters (paginated)
SR = ["continental", "lesaffre", "abbvie", "alten", "rolandberger", "assystem",
      "thales", "apmterminals", "bosch", "siemens", "schneiderelectric", "vinci",
      "sodexo", "saint-gobain", "michelin", "safran", "arkema", "airliquide",
      "publicisgroupe", "ubisoft", "vodafone", "visa"]
n = 0
for c in SR:
    off, seen_ids = 0, set()
    while off < 800:
        d = J(f"https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=100&offset={off}")
        if not d or not d.get("content"): break
        for j in d["content"]:
            jid_ = j.get("id")
            if jid_ in seen_ids: continue
            seen_ids.add(jid_)
            loc = j.get("location") or {}
            loctxt = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
            if not MA.search(loctxt): continue
            if not TITLE_HINT.search(j.get("name", "")): continue
            det = J(f"https://api.smartrecruiters.com/v1/companies/{c}/postings/{jid_}")
            desc = ""
            if det:
                jd = det.get("jobAd", {}).get("sections", {})
                desc = " ".join(clean((jd.get(k) or {}).get("text", "")) for k in
                                ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
            if push(f"ATS SmartRecruiters ({c})", j.get("name", ""), c.title(), loctxt,
                    (j.get("typeOfEmployment") or {}).get("label", ""),
                    (j.get("releasedDate") or "")[:10],
                    f"https://jobs.smartrecruiters.com/{c}/{jid_}", desc,
                    function=(j.get("function") or {}).get("label", ""),
                    sector=(j.get("industry") or {}).get("label", "")):
                n += 1
            time.sleep(0.1)
        off += 100
        if len(d["content"]) < 100: break
    print(f"  SmartRecruiters/{c}: total {n}", flush=True)

# ---------------------------------------------------- Greenhouse
for c in ["flex", "bcg", "jabil", "sanmina", "stripe"]:
    d = J(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true")
    if not d: continue
    for j in d.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        desc = clean(j.get("content", ""))
        push(f"ATS Greenhouse ({c})", j.get("title", ""), c.title(), loc, "",
             (j.get("updated_at") or "")[:10], j.get("absolute_url", ""), desc)
    print(f"  Greenhouse/{c} done ({len(rows)})", flush=True)

# ---------------------------------------------------- Recruitee
for c in ["geodis", "teleperformance", "ey", "accenture", "intelcia", "webhelp"]:
    d = J(f"https://{c}.recruitee.com/api/offers/")
    if not d: continue
    for j in d.get("offers", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        desc = clean(j.get("description", "")) + " " + clean(j.get("requirements", ""))
        push(f"ATS Recruitee ({c})", j.get("title", ""), c.title(), loc,
             j.get("employment_type_code", ""), (j.get("published_at") or "")[:10],
             j.get("careers_url") or j.get("url", ""), desc,
             function=j.get("department", ""))
    print(f"  Recruitee/{c} done ({len(rows)})", flush=True)

# ---------------------------------------------------- Ashby
for c in ["delphi"]:
    d = J(f"https://api.ashbyhq.com/posting-api/job-board/{c}")
    if not d: continue
    for j in d.get("jobs", []):
        push(f"ATS Ashby ({c})", j.get("title", ""), c.title(), j.get("location", ""),
             j.get("employmentType", ""), (j.get("publishedAt") or "")[:10],
             j.get("jobUrl", ""), clean(j.get("descriptionHtml", "")),
             function=j.get("department", ""))
    print(f"  Ashby/{c} done ({len(rows)})", flush=True)

# ---------------------------------------------------- Workable
for c in ["safrangroup"]:
    d = J(f"https://apply.workable.com/api/v1/widget/accounts/{c}?details=true")
    if not d: continue
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        push(f"ATS Workable ({c})", j.get("title", ""), c.title(), loc, j.get("type", ""),
             (j.get("published_on") or "")[:10], j.get("url", ""),
             clean(j.get("description", "")) + " " + clean(j.get("requirements", "")))
    print(f"  Workable/{c} done ({len(rows)})", flush=True)

uniq = {}
for r in rows:
    k = jid(r["url"], r["job_title"], r["company"])
    if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
out = list(uniq.values())
print(f"\nTOTAL ATS Morocco relevant: {len(out)}")
save("ats", out)
for r in out:
    print(f"  {r['job_title'][:52]:52s} | {r['company'][:18]:18s} | {r['location_city'][:24]:24s} | {r['source'][:30]}")
