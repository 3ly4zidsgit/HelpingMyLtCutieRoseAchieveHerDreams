"""Which employers expose a public ATS feed? Greenhouse / Lever / SmartRecruiters /
Recruitee / Ashby / Teamtailor / Workable all serve unauthenticated JSON."""
import requests, re, sys, json, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from common import HDRS, strip_accents

S_HDRS = dict(HDRS); S_HDRS["Accept"] = "application/json,text/plain,*/*"

COMPANIES = [
 # automobile / cablage
 "renault", "renaultgroup", "stellantis", "yazaki", "aptiv", "lear", "leoni",
 "forvia", "faurecia", "valeo", "novares", "sumitomoelectric", "sews", "delphi",
 "teconnectivity", "te-connectivity", "hirschmann", "hirschmannautomotive",
 "adient", "antolin", "gestamp", "plasticomnium", "opmobility", "mahle", "denso",
 "bosch", "continental", "schaeffler", "zf", "brose", "marelli", "nexteer",
 # aeronautique
 "safran", "safrangroup", "bombardier", "spiritaero", "collinsaerospace",
 "thales", "thalesgroup", "airbus", "boeing", "figeacaero", "latecoere",
 "daher", "stelia", "sabca", "aerospace",
 # electrique / industrie
 "alstom", "siemens", "schneiderelectric", "abb", "nexans", "eaton", "emerson",
 "legrand", "hitachienergy", "generalelectric", "gevernova", "honeywell",
 "stmicroelectronics", "jabil", "flex", "sanmina", "molex", "amphenol",
 # agro / conso / pharma
 "danone", "nestle", "cocacola", "mondelez", "unilever", "pepsico", "kraftheinz",
 "lesaffre", "bel", "groupebel", "savola", "pfizer", "sanofi", "novonordisk",
 "gsk", "bayer", "roche", "abbvie", "viatris", "teva", "fresenius",
 # maroc
 "ocpgroup", "ocp", "managem", "cosumar", "lesieurcristal", "marjane", "labelvie",
 "maroctelecom", "attijariwafabank", "royalairmaroc", "tangermed", "cimentsdumaroc",
 "lafargeholcim", "holcim", "taqamorocco", "nareva", "akwagroup", "ynna",
 # conseil / ingenierie / ESN
 "alten", "altengroup", "akkodis", "segula", "expleo", "assystem", "capgemini",
 "sopragroup", "soprasteria", "atos", "accenture", "deloitte", "ey", "pwc",
 "kpmg", "mckinsey", "bcg", "bain", "kearney", "rolandberger", "wavestone",
 # logistique / retail / autres
 "dhl", "kuehne-nagel", "geodis", "dachser", "maersk", "apmterminals", "cma-cgm",
 "decathlon", "ikea", "inditex", "hm", "leroymerlin", "amazon", "tesla",
 # tech maroc / offshore
 "intelcia", "webhelp", "concentrix", "teleperformance", "majorel", "sitel",
 # ---- piste business (commercial / graduate / conseil / achats) -------------
 # jamais sondes jusqu'ici. Ces employeurs sont ceux que la proprietaire du
 # classeur a cites nommement, plus les cabinets qui recrutent des ingenieurs
 # sans experience. Un slug qui ne repond pas ne coute rien; un slug devine qui
 # repond est verifiable, donc utilisable.
 "pg", "procterandgamble", "pgcareers", "dell", "delltechnologies", "dellemc",
 "mars", "marsinc", "marswrigley", "jti", "jtinternational", "henkel", "loreal",
 "beiersdorf", "reckittbenckiser", "heineken", "diageo", "britishamericantobacco",
 "capgemini", "capgeminiinvent", "kearney", "wavestone", "alvarezandmarsal",
 "oliverwyman", "strategyand", "eyparthenon", "grantthornton", "mazars", "bdo",
 "sia-partners", "siapartners", "valyans", "lms-orh", "devoteam", "sqli",
 "salesforce", "sap", "oracle", "cisco", "hp", "hpe", "lenovo", "ibm",
 "schneiderelectric-careers", "sew-eurodrive", "endress", "trane",
]

ENDPOINTS = [
 ("greenhouse",     "https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true"),
 ("lever",          "https://api.lever.co/v0/postings/{c}?mode=json"),
 ("smartrecruiters","https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=100"),
 ("recruitee",      "https://{c}.recruitee.com/api/offers/"),
 ("ashby",          "https://api.ashbyhq.com/posting-api/job-board/{c}"),
 ("teamtailor",     "https://{c}.teamtailor.com/jobs.json"),
 ("workable",       "https://apply.workable.com/api/v1/widget/accounts/{c}?details=true"),
 ("personio",       "https://{c}.jobs.personio.de/search.json"),
]

LOCK = threading.Lock()
HITS = []

def probe(company, name, tmpl):
    url = tmpl.format(c=company)
    try:
        r = requests.get(url, headers=S_HDRS, timeout=12)
    except Exception:
        return
    if r.status_code != 200 or len(r.text) < 40:
        return
    try:
        data = r.json()
    except Exception:
        return
    # count jobs in whatever shape this ATS uses
    n = 0
    if isinstance(data, list):
        n = len(data)
    elif isinstance(data, dict):
        for k in ("jobs", "content", "offers", "data", "results"):
            v = data.get(k)
            if isinstance(v, list):
                n = len(v); break
        if not n and isinstance(data.get("totalFound"), int):
            n = data["totalFound"]
    if n == 0:
        return
    txt = r.text.lower()
    morocco = bool(re.search(r"morocco|maroc|casablanca|tanger|tangier|rabat|kenitra|"
                             r"marrakech|agadir|fes|meknes|oujda|tetouan|jadida|nouaceur|"
                             r"bouskoura|salé|sale\b|berrechid|settat", txt))
    with LOCK:
        HITS.append({"company": company, "ats": name, "url": url, "jobs": n, "morocco": morocco})
        flag = "  <-- MAROC" if morocco else ""
        print(f"  {company:22s} {name:15s} {n:5d} jobs{flag}", flush=True)

if __name__ == "__main__":
    tasks = [(c, n, t) for c in COMPANIES for n, t in ENDPOINTS]
    print(f"probing {len(tasks)} (company, ATS) combinations...", flush=True)
    with ThreadPoolExecutor(max_workers=40) as ex:
        futs = [ex.submit(probe, c, n, t) for c, n, t in tasks]
        for f in as_completed(futs):
            pass
    ma = [h for h in HITS if h["morocco"]]
    print(f"\n{len(HITS)} live ATS feeds | {len(ma)} mention Morocco")
    out = sys.argv[1] if len(sys.argv) > 1 else "data/ats_hits.json"
    json.dump(HITS, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {out}")
    print("\n--- feeds mentioning Morocco ---")
    for h in sorted(ma, key=lambda x: -x["jobs"]):
        print(f"  {h['company']:22s} {h['ats']:15s} {h['jobs']:5d}  {h['url']}")
