"""Read an employer's real job-board host out of its own careers page.

Guessing Workday tenants does not work - research/probe_bypass.py tried 20 across
3 hosts and got nothing, and a probe run for this track got 422 (not 404) from
danone, jti and mars on every site name tried. 422 means "the tenant is there,
your request is wrong", so the missing piece is the site path, and the site path
is written in the URL the company itself links to.

So: fetch the careers page, follow the redirects, and read the ATS host out of
the final URL and out of every link on the page. Nothing is guessed and nothing
is invented - if a company publishes no reachable board, it is reported as such.

    python research/probe_careers.py [out.json]
"""
import sys, io, os, re, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
import requests
from core import HDRS

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data_business", "careers_hosts.json")

# the employers named by the owner of the workbook, plus the graduate-programme
# recruiters that matter in Morocco
TARGETS = {
    "P&G": ["pg.com", "pgcareers.com", "fr.pg.com"],
    "Dell": ["dell.com", "jobs.dell.com"],
    "Unilever": ["unilever.com", "careers.unilever.com"],
    "Nestle": ["nestle.com", "nestle.ma", "nestlecareers.com"],
    "Danone": ["danone.com", "careers.danone.com"],
    "Schneider Electric": ["se.com", "careers.se.com"],
    "Siemens": ["siemens.com", "jobs.siemens.com"],
    "Mars": ["mars.com", "careers.mars.com"],
    "JTI": ["jti.com", "careers.jti.com"],
    "Coca-Cola": ["coca-colacompany.com", "careers.coca-colacompany.com"],
    "Henkel": ["henkel.com", "henkel.com/careers"],
    "L'Oreal": ["loreal.com", "careers.loreal.com"],
    "Deloitte": ["deloitte.com", "jobs2.deloitte.com", "deloitte.ma"],
    "PwC": ["pwc.com", "pwc.ma"],
    "KPMG": ["kpmg.com", "kpmg.ma"],
    "Capgemini": ["capgemini.com", "capgemini.ma"],
    "Managem": ["managemgroup.com"],
    "OCP": ["ocpgroup.ma"],
    "Attijariwafa": ["attijariwafabank.com"],
    "Maroc Telecom": ["iam.ma"],
}
PATHS = ["/careers", "/en/careers", "/fr/carrieres", "/carrieres", "/jobs", "/en/jobs",
         "/careers/", "/emploi", "/recrutement", ""]

# the ATS hosts worth recognising, with the bit of the URL that carries the tenant
ATS_HOST = re.compile(
    r"(?P<tenant>[a-z0-9\-]+)\.(?P<host>wd\d+)\.myworkdayjobs\.com(?P<path>/[^\"'\s>]*)?"
    r"|career\d*\.(?P<sf>successfactors\.(?:eu|com))/[^\"'\s>]*"
    r"|(?P<tal>[a-z0-9\-]+)\.taleo\.net/[^\"'\s>]*"
    r"|(?P<av>[a-z0-9\-]+)\.avature\.net/[^\"'\s>]*"
    r"|(?P<ef>[a-z0-9\-]+)\.eightfold\.ai/[^\"'\s>]*"
    r"|(?P<ic>[a-z0-9\-]+)\.icims\.com/[^\"'\s>]*"
    r"|(?P<sr>jobs\.smartrecruiters\.com)/[^\"'\s>]*"
    r"|(?P<gh>boards\.greenhouse\.io)/[^\"'\s>]*"
    r"|(?P<lv>jobs\.lever\.co)/[^\"'\s>]*"
    r"|hcmRestApi/resources/[^\"'\s>]*|/hcmUI/CandidateExperience/[^\"'\s>]*", re.I)

S = requests.Session()
S.headers.update(HDRS)
out = {}
for name, domains in TARGETS.items():
    found, tried = [], []
    for d in domains:
        for path in PATHS:
            url = f"https://{d.rstrip('/')}{path}" if not d.startswith("http") else d
            if url in tried:
                continue
            tried.append(url)
            try:
                r = S.get(url, timeout=20, allow_redirects=True)
            except Exception:
                continue
            if r.status_code >= 400:
                continue
            hay = r.url + " " + r.text[:400000]
            for m in ATS_HOST.finditer(hay):
                found.append(re.sub(r"\s+", "", m.group(0))[:160])
            if found:
                break
            time.sleep(0.3)
        if found:
            break
    uniq = list(dict.fromkeys(found))[:8]
    out[name] = {"tried": tried[:6], "ats_urls": uniq}
    print(f"{name:20s} {len(uniq)} piste(s)")
    for u in uniq[:4]:
        print(f"      {u}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
hit = sum(1 for v in out.values() if v["ats_urls"])
print(f"\n{hit}/{len(TARGETS)} employeurs exposent un board identifiable -> {OUT}")
