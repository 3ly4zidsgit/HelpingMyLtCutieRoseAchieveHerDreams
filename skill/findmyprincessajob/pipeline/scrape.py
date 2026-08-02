"""All sources reachable over plain HTTP (no browser needed).

Access map established by trial (see references/SOURCES.md):
  work with requests + a Chrome UA .. Rekrute, LinkedIn guest API, MarocAnnonces, Dreamjob
  JSON/RSS APIs ................... Remotive, RemoteOK, Jobicy, WeWorkRemotely, Himalayas, Arbeitnow
  ATS feeds ....................... SmartRecruiters, Greenhouse, Lever, Recruitee, Ashby, Workable
"""
import requests, re, sys, time, random, html as ihtml
import xml.etree.ElementTree as ET
from urllib.parse import quote, quote_plus, urljoin
from bs4 import BeautifulSoup
from core import HDRS, blank, jid, norm, find_emails

S = requests.Session(); S.headers.update(HDRS)

MA_CITY = (r"morocco|maroc|casablanca|tanger|tangier|rabat|k[ée]nitra|kenitra|marrakech|"
           r"marrakesh|agadir|f[èe]s|fez|mekn[èe]s|meknes|oujda|t[ée]touan|tetouan|"
           r"el jadida|nouaceur|bouskoura|sal[ée]|berrechid|settat|mohammedia|skhirat|"
           r"t[ée]mara|benguerir|had soualem|larache|safi|nador|khouribga|laayoune|dakhla")
MA = re.compile(r"\b(" + MA_CITY + r")\b", re.I)


def T(el, sel=None):
    if sel:
        el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def clean_html(h):
    if not h:
        return ""
    return re.sub(r"\s+", " ",
                  BeautifulSoup(ihtml.unescape(str(h)), "html.parser").get_text(" ", strip=True))


def g(d, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    return default


def J(url, tries=3, **kw):
    """Several of these APIs throttle at the TLS layer when hit hard, so back off."""
    for i in range(tries):
        try:
            r = S.get(url, timeout=30, **kw)
            if r.status_code == 429:
                time.sleep(5 * (i + 1)); continue
            return r.json() if r.status_code == 200 else None
        except Exception:
            time.sleep(2 * (i + 1))
    return None


class Collector:
    def __init__(self, run):
        self.run = run
        self.rows = []

    def push(self, source, title, company="", loc="", ctype="", date="", url="",
             desc="", country="Maroc", **extra):
        if not title or not url:
            return False
        keep, score, hits = self.run.relevance(title, desc)
        if not keep:
            return False
        self.rows.append(blank(source=source, job_title=title, company=company,
                               location_city=loc, country=country, contract_type=ctype,
                               date_posted=date, url=url, description_snippet=desc[:800],
                               contact_email=", ".join(find_emails(desc)[:2]),
                               keywords_matched=", ".join(hits), score=score, **extra))
        return True


# ============================================================ Rekrute
def rekrute(run, col, pages=5):
    base = "https://www.rekrute.com"
    n = 0
    for kw in run.queries_fr:
        for page in range(1, pages + 1):
            try:
                r = S.get(f"{base}/offres.html", params={"s": 1, "p": page, "keyword": kw}, timeout=30)
            except Exception:
                break
            if r.status_code != 200:
                break
            cards = BeautifulSoup(r.text, "html.parser").select("li.post-id")
            if not cards:
                break
            got = 0
            for c in cards:
                a = c.select_one("a.titreJob")
                if not a:
                    continue
                title = T(a); city = ""
                if "|" in title:
                    parts = [p.strip() for p in title.split("|")]
                    city = re.sub(r"\((Maroc|Morocco)\)", "", parts[-1]).strip(" -")
                    title = parts[0]
                img = c.select_one("img.photo")
                comp = (img.get("title") or img.get("alt") or "").strip() if img else ""
                desc = max((T(d) for d in c.select("div.info span")), key=len, default="")
                dp = dl = pos = ""
                em = c.select_one("em.date")
                if em:
                    sp = [T(x) for x in em.select("span")]
                    ds = [x for x in sp if re.match(r"\d{2}/\d{2}/\d{4}", x)]
                    dp = ds[0] if ds else ""
                    dl = ds[1] if len(ds) > 1 else ""
                    nums = [x for x in sp if x.isdigit()]
                    pos = nums[-1] if nums else ""
                sec = fn = exp = stu = ct = rem = ""
                for li in c.select("div.info ul li"):
                    t = T(li); low = t.lower()
                    val = t.split(":", 1)[-1].strip()
                    if low.startswith("secteur"): sec = val
                    elif low.startswith("fonction"): fn = val
                    elif low.startswith("exp"): exp = val
                    elif "tude" in low[:14]: stu = val
                    elif "contrat" in low:
                        bits = re.split(r"-\s*T[ée]l[ée]travail\s*:", val)
                        ct = bits[0].strip()
                        rem = bits[1].strip() if len(bits) > 1 else ""
                if col.push("Rekrute.com", title, comp, city, ct, dp,
                            urljoin(base, a.get("href", "")), desc, deadline=dl,
                            positions=pos, sector=sec, function=fn,
                            experience_required=exp, education_level=stu, remote=rem):
                    got += 1
            n += got
            print(f"  [Rekrute] '{kw}' p{page}: {len(cards)} cards, +{got} (tot {n})", flush=True)
            if len(cards) < 10:
                break
            time.sleep(0.4)
    return n


# ============================================================ LinkedIn guest API
LI_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LI_DET = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"


def linkedin(run, col, locations, remote_flag, pages=3, country="Maroc", label="LinkedIn"):
    found = {}
    for loc in locations:
        for kw in run.queries:
            for start in range(0, pages * 10, 10):
                p = {"keywords": kw, "location": loc, "start": start}
                if remote_flag:
                    p["f_WT"] = 2
                try:
                    r = S.get(LI_API, params=p, timeout=25)
                except Exception:
                    break
                if r.status_code != 200:
                    if r.status_code == 429:
                        time.sleep(8)
                    break
                cards = BeautifulSoup(r.text, "html.parser").select("li")
                if not cards:
                    break
                new = 0
                for c in cards:
                    a = (c.select_one("a.base-card__full-link")
                         or c.select_one("a[href*='/jobs/view/']"))
                    if not a:
                        continue
                    u = (a.get("href") or "").split("?")[0]
                    if u in found:
                        continue
                    t = c.select_one("h3.base-search-card__title")
                    comp = c.select_one("h4.base-search-card__subtitle")
                    lo = c.select_one("span.job-search-card__location")
                    d = c.select_one("time")
                    sal = c.select_one("span.job-search-card__salary-info")
                    m = re.search(r"-(\d{6,})$", u)
                    found[u] = {"url": u, "title": T(t), "company": T(comp), "loc": T(lo),
                                "date": (d.get("datetime") if d else ""), "salary": T(sal),
                                "jobid": m.group(1) if m else ""}
                    new += 1
                if new:
                    print(f"  [{label}] {loc[:20]:20s} '{kw[:24]:24s}' s{start}: +{new} "
                          f"(tot {len(found)})", flush=True)
                if len(cards) < 10:
                    break
                time.sleep(random.uniform(0.5, 1.0))
    # keep title-relevant only, then spend one detail request each
    cand = [c for c in found.values() if run.relevance(c["title"])[0]]
    print(f"  [{label}] {len(found)} raw -> {len(cand)} title-relevant; fetching details",
          flush=True)
    for i, c in enumerate(cand, 1):
        det = {}
        if c["jobid"]:
            try:
                r = S.get(LI_DET.format(c["jobid"]), timeout=25)
                if r.status_code == 200:
                    s = BeautifulSoup(r.text, "html.parser")
                    de = s.select_one("div.show-more-less-html__markup")
                    crit = {}
                    for it in s.select("li.description__job-criteria-item"):
                        h, v = it.select_one("h3"), it.select_one("span")
                        if h and v:
                            crit[norm(h.get_text()).replace("’", "'")] = T(v)
                    poster = ""
                    for pa in s.select("a[href*='/in/']"):
                        nm = T(pa)
                        if 3 < len(nm) < 60:
                            poster = nm; break
                    det = {"desc": T(de), "crit": crit, "poster": poster,
                           "emails": find_emails(T(de))}
            except Exception:
                pass
        crit = det.get("crit", {})
        noise = re.compile(r"^(non pertinent|not applicable|n/?a)$", re.I)
        sen = crit.get("niveau hierarchique") or crit.get("seniority level") or ""
        ct = crit.get("type d'emploi") or crit.get("employment type") or ""
        col.push(label, c["title"], c["company"], c["loc"],
                 "" if noise.match(ct) else ct, c["date"], c["url"], det.get("desc", ""),
                 country=("Maroc" if MA.search(c["loc"]) else country),
                 experience_required="" if noise.match(sen) else sen,
                 function=crit.get("fonction") or crit.get("job function") or "",
                 sector=crit.get("secteurs") or crit.get("industries") or "",
                 salary=c["salary"], recruiter_or_hr=det.get("poster", ""),
                 contact_email=", ".join(det.get("emails", [])[:2]),
                 remote="Oui / Remote" if remote_flag else "")
        if i % 50 == 0:
            print(f"  [{label}] detail {i}/{len(cand)}", flush=True)
        time.sleep(random.uniform(0.3, 0.7))
    return len(cand)


# ============================================================ MarocAnnonces + Dreamjob
def ma_boards(run, col):
    n = 0
    for kw in run.queries_fr:
        for pg in range(1, 4):
            try:
                r = S.get("https://www.marocannonces.com/maroc/offres-emploi-b309.html",
                          params={"kw": kw, "pge": pg}, timeout=30)
            except Exception:
                break
            if r.status_code != 200:
                break
            s = BeautifulSoup(r.text, "html.parser")
            cards = [c for c in s.select("ul.cars-list li") if c.select_one("a[href*='/annonce/']")]
            if not cards:
                break
            for c in cards:
                a = c.select_one("a[href*='/annonce/']")
                if col.push("MarocAnnonces.com", T(c, "h3") or T(a), "", T(c, "span.location"),
                            "", T(c, "em.date") or T(c, "span.date"),
                            urljoin("https://www.marocannonces.com/", a.get("href", "")), T(c)):
                    n += 1
            time.sleep(0.3)
    for kw in run.queries_fr:
        for pg in (1, 2):
            u = (f"https://www.dreamjob.ma/page/{pg}/?s={quote(kw)}" if pg > 1
                 else f"https://www.dreamjob.ma/?s={quote(kw)}")
            try:
                r = S.get(u, timeout=30)
            except Exception:
                break
            if r.status_code != 200:
                break
            cards = BeautifulSoup(r.text, "html.parser").select("article")
            if not cards:
                break
            for c in cards:
                a = c.select_one("a[href*='/emploi/']") or c.select_one("a")
                if a and col.push("Dreamjob.ma", T(c, "h2") or T(a), "", "", "",
                                  T(c, "time"), a.get("href", ""), T(c)):
                    n += 1
            time.sleep(0.3)
    print(f"  [MA boards] +{n}", flush=True)
    return n


# ============================================================ ATS feeds
ATS_SMARTRECRUITERS = ["alten", "lesaffre", "abbvie", "rolandberger", "assystem", "thales",
                       "continental", "apmterminals", "bosch", "siemens", "schneiderelectric",
                       "vinci", "sodexo", "saint-gobain", "michelin", "safran", "arkema",
                       "airliquide", "publicisgroupe", "vodafone", "visa"]
ATS_GREENHOUSE = ["flex", "bcg", "jabil", "sanmina"]
ATS_RECRUITEE = ["geodis", "teleperformance", "ey", "accenture"]
ATS_ASHBY = ["delphi"]
ATS_WORKABLE = ["safrangroup"]


def ats(run, col):
    hint = re.compile("|".join(run.queries_fr + run.queries_en), re.I) if run.queries else None
    for c in ATS_SMARTRECRUITERS:
        off = 0
        while off < 600:
            d = J(f"https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=100&offset={off}")
            if not d or not d.get("content"):
                break
            for j in d["content"]:
                lo = j.get("location") or {}
                loctxt = ", ".join(x for x in [lo.get("city"), lo.get("region"), lo.get("country")] if x)
                if not MA.search(loctxt):
                    continue
                if hint and not hint.search(j.get("name", "")):
                    continue
                det = J(f"https://api.smartrecruiters.com/v1/companies/{c}/postings/{j['id']}")
                desc = ""
                if det:
                    sec = det.get("jobAd", {}).get("sections", {})
                    desc = " ".join(clean_html((sec.get(k) or {}).get("text", "")) for k in
                                    ("companyDescription", "jobDescription", "qualifications",
                                     "additionalInformation"))
                col.push(f"ATS SmartRecruiters ({c})", j.get("name", ""), c.title(), loctxt,
                         (j.get("typeOfEmployment") or {}).get("label", ""),
                         (j.get("releasedDate") or "")[:10],
                         f"https://jobs.smartrecruiters.com/{c}/{j['id']}", desc,
                         function=(j.get("function") or {}).get("label", ""))
                time.sleep(0.15)
            off += 100
            if len(d["content"]) < 100:
                break
    for c in ATS_GREENHOUSE:
        d = J(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true")
        for j in (d or {}).get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            if MA.search(loc):
                col.push(f"ATS Greenhouse ({c})", j.get("title", ""), c.title(), loc, "",
                         (j.get("updated_at") or "")[:10], j.get("absolute_url", ""),
                         clean_html(j.get("content", "")))
    for c in ATS_RECRUITEE:
        d = J(f"https://{c}.recruitee.com/api/offers/")
        for j in (d or {}).get("offers", []):
            loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
            if MA.search(loc):
                col.push(f"ATS Recruitee ({c})", j.get("title", ""), c.title(), loc,
                         j.get("employment_type_code", ""), (j.get("published_at") or "")[:10],
                         j.get("careers_url") or j.get("url", ""),
                         clean_html(j.get("description", "")), function=j.get("department", ""))
    for c in ATS_ASHBY:
        d = J(f"https://api.ashbyhq.com/posting-api/job-board/{c}")
        for j in (d or {}).get("jobs", []):
            if MA.search(j.get("location", "")):
                col.push(f"ATS Ashby ({c})", j.get("title", ""), c.title(), j.get("location", ""),
                         j.get("employmentType", ""), (j.get("publishedAt") or "")[:10],
                         j.get("jobUrl", ""), clean_html(j.get("descriptionHtml", "")))
    for c in ATS_WORKABLE:
        d = J(f"https://apply.workable.com/api/v1/widget/accounts/{c}?details=true")
        for j in (d or {}).get("jobs", []):
            loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
            if MA.search(loc):
                col.push(f"ATS Workable ({c})", j.get("title", ""), c.title(), loc,
                         j.get("type", ""), (j.get("published_on") or "")[:10],
                         j.get("url", ""), clean_html(j.get("description", "")))
    print(f"  [ATS] total collected so far: {len(col.rows)}", flush=True)


# ============================================================ worldwide remote
GEO_GLOBAL = re.compile(r"worldwide|anywhere in the world|^\s*anywhere\s*$|^\s*global\s*$|"
                        r"globally|any location|any country|^\s*remote\s*$|100%\s*remote")
TXT_GLOBAL = re.compile(r"work from anywhere|anywhere in the world|from any country|"
                        r"any time ?zone|globally distributed|fully distributed|"
                        r"location[- ]independent|no matter where you (are|live)|"
                        r"work remotely from anywhere|remote[- ]first company")
BLOCKER = re.compile(r"must (be (located|based|physically|resident)|reside|live) (in|within)|"
                     r"(authoriz|authoris)(ed|ation) to work|right to work in|eligible to work in|"
                     r"work permit|visa sponsorship|cannot sponsor|no sponsorship|"
                     r"sponsorship (is )?not|security clearance|u\.?s\.? citizen|green card|"
                     r"\bhybrid\b|\bon[- ]?site\b|\bonsite\b|\bin[- ]office\b|relocat")


def worldwide(run, col):
    """Only offers the board itself flags as open to the whole world, with no
    visa / work-permit / on-site language anywhere in the ad."""
    def add(src, title, comp, geo, ctype, date, url, desc, **extra):
        if not (GEO_GLOBAL.search(norm(geo)) or TXT_GLOBAL.search(norm(desc))):
            return
        if BLOCKER.search(norm(desc)):
            return
        col.push(src, title, comp, geo.strip()[:40] or "Worldwide", ctype, date, url, desc,
                 country="Remote mondial (sans visa)", remote="100% remote - worldwide", **extra)

    d = J("https://remoteok.com/api")
    for j in (d or []):
        if isinstance(j, dict) and j.get("position"):
            add("RemoteOK", j["position"], g(j, "company"), g(j, "location", default="Worldwide"),
                "Full-time", g(j, "date")[:10], g(j, "url", "apply_url"),
                clean_html(j.get("description", "")))
    d = J("https://remotive.com/api/remote-jobs?limit=2000")
    for j in (d or {}).get("jobs", []):
        add("Remotive", g(j, "title"), g(j, "company_name"), g(j, "candidate_required_location"),
            g(j, "job_type"), g(j, "publication_date")[:10], g(j, "url"),
            clean_html(j.get("description", "")), salary=g(j, "salary"), sector=g(j, "category"))
    for tag in ["operations", "business", "supply-chain", "engineering", "management",
                "project-management", "quality-assurance", "manufacturing", "consulting", "data"]:
        d = J(f"https://jobicy.com/api/v2/remote-jobs?count=100&tag={tag}")
        for j in (d or {}).get("jobs", []):
            add("Jobicy", g(j, "jobTitle"), g(j, "companyName"), g(j, "jobGeo"), g(j, "jobType"),
                g(j, "pubDate")[:10], g(j, "url"),
                clean_html(j.get("jobDescription") or j.get("jobExcerpt") or ""),
                experience_required=g(j, "jobLevel"))
        time.sleep(0.2)
    for cat in ["remote-jobs", "categories/remote-management-and-finance-jobs",
                "categories/remote-business-executive-management-jobs",
                "categories/all-other-remote-jobs", "categories/remote-product-jobs"]:
        try:
            root = ET.fromstring(S.get(f"https://weworkremotely.com/{cat}.rss", timeout=30).content)
        except Exception:
            continue
        for it in root.iter("item"):
            def t(tag):
                e = it.find(tag); return (e.text or "") if e is not None else ""
            raw = t("title"); comp, _, title = raw.partition(":")
            add("WeWorkRemotely", (title or raw).strip(), comp.strip(), t("region"), t("type"),
                t("pubDate")[:16], t("link"), clean_html(t("description")))
    for off in range(0, 1000, 100):
        d = J(f"https://himalayas.app/jobs/api?limit=100&offset={off}")
        js = (d or {}).get("jobs", [])
        if not js:
            break
        for j in js:
            restr = j.get("locationRestrictions") or []
            geo = ", ".join(restr) if restr else "Worldwide"
            add("Himalayas", g(j, "title"), g(j, "companyName", "company"), geo,
                g(j, "employmentType"), str(g(j, "pubDate", "publishedDate"))[:10],
                g(j, "applicationLink", "url"), clean_html(j.get("description") or ""),
                experience_required=g(j, "seniority"))
        time.sleep(0.2)
    print(f"  [worldwide] total collected so far: {len(col.rows)}", flush=True)
