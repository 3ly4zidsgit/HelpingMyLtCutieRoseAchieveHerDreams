"""Second pass over the LinkedIn rows: the criteria block uses a typographic
apostrophe ("Type d’emploi"), so the first pass never captured contract type."""
import requests, re, sys, time, random, threading, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from common import HDRS, save, load, find_emails

DET = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
LOCK = threading.Lock()

def flat(s):
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace(" ", " ")).strip().lower()

NOISE = re.compile(r"^(non pertinent|not applicable|n/?a|autre|other)$", re.I)

def jobid(url):
    m = re.search(r"-(\d{6,})(?:\?|$)", url or "")
    return m.group(1) if m else ""

def one(row):
    jid = jobid(row.get("url", ""))
    if not jid: return row, False
    s = requests.Session(); s.headers.update(HDRS)
    try:
        r = s.get(DET.format(jid), timeout=20)
        if r.status_code != 200: return row, False
    except Exception:
        return row, False
    soup = BeautifulSoup(r.text, "html.parser")
    crit = {}
    for it in soup.select("li.description__job-criteria-item"):
        h, v = it.select_one("h3"), it.select_one("span")
        if h and v: crit[flat(h.get_text())] = re.sub(r"\s+", " ", v.get_text(strip=True))
    ct = crit.get("type d'emploi") or crit.get("employment type") or ""
    sen = crit.get("niveau hierarchique") or crit.get("niveau hiérarchique") or \
          crit.get("seniority level") or row.get("experience_required", "")
    fn = crit.get("fonction") or crit.get("job function") or row.get("function", "")
    ind = crit.get("secteurs") or crit.get("industries") or row.get("sector", "")
    if ct and not NOISE.match(ct): row["contract_type"] = ct
    row["experience_required"] = "" if NOISE.match(sen or "") else sen
    if fn and not NOISE.match(fn): row["function"] = fn
    if ind: row["sector"] = ind

    if not row.get("description_snippet"):
        de = soup.select_one("div.show-more-less-html__markup")
        if de: row["description_snippet"] = re.sub(r"\s+", " ", de.get_text(" ", strip=True))[:600]
    if not row.get("contact_email"):
        em = find_emails(soup.get_text(" ", strip=True))
        if em: row["contact_email"] = ", ".join(em[:3])
    if not row.get("recruiter_or_hr"):
        for pa in soup.select("a[href*='/in/']"):
            nm = re.sub(r"\s+", " ", pa.get_text(strip=True))
            if nm and 3 < len(nm) < 60:
                row["recruiter_or_hr"] = nm
                row["hr_profile"] = (pa.get("href") or "").split("?")[0]
                break
    return row, True

if __name__ == "__main__":
    rows = load("linkedin")
    print(f"patching {len(rows)} LinkedIn rows", flush=True)
    done = ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(one, r) for r in rows]
        for f in as_completed(futs):
            done += 1
            try:
                _, good = f.result()
                ok += 1 if good else 0
            except Exception:
                pass
            if done % 50 == 0:
                print(f"  {done}/{len(rows)} (ok {ok})", flush=True)
                with LOCK: save("linkedin", rows)
    save("linkedin", rows)
    print(f"contract_type filled: {sum(1 for r in rows if r.get('contract_type'))}/{len(rows)}")
    print(f"recruiter names:      {sum(1 for r in rows if r.get('recruiter_or_hr'))}/{len(rows)}")
    print(f"emails:               {sum(1 for r in rows if r.get('contact_email'))}/{len(rows)}")
