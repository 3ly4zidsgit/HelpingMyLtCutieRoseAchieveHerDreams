import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from common import load, norm

base = load("merged")
ww = load("worldwide")
BAD = re.compile(r"\btechnicien(ne)?s?\b|\btechnician[s]?\b")

intl = [r for r in base if r["country"] != "Maroc" and not BAD.search(norm(r.get("job_title","")))]
ww = [r for r in ww if not BAD.search(norm(r.get("job_title","")))]
print(f"### international from merged: {len(intl)} | worldwide set: {len(ww)}\n")

# keep only titles that plausibly belong to the user's field
FIELD = re.compile(
    r"\blean\b|\bsix ?sigma\b|\bkaizen\b|\bkanban\b|\bblack belt\b|\bgreen belt\b|"
    r"\bcontinuous improvement\b|\bprocess improvement\b|\bprocess excellence\b|"
    r"\boperational excellence\b|\boperations excellence\b|\bmanufacturing excellence\b|"
    r"\bindustrial engineer|\bmanufacturing engineer|\bmethods? engineer|\bvalue stream\b|"
    r"\bproduction (engineer|manager|planner)|\bindustriali[sz]ation\b|\bplant manager\b|"
    r"\bquality (engineer|manager|specialist|analyst|lead)|\bsupply chain\b|"
    r"\bprocess (engineer|analyst|consultant|manager|owner|optimi|mining)|"
    r"\blogistics (manager|analyst|coordinator|specialist)|\bbusiness process\b|"
    r"\bamelioration continue\b|\bexcellence operationnelle\b|\bgenie industriel\b|"
    r"\bingenieur (industriel|methodes|process|production|qualite)\b|\bproductivity\b|"
    r"\boperations (analyst|excellence|improvement)\b")

cands = [r for r in intl + ww if FIELD.search(norm(r.get("job_title","")))]
print(f"### title-relevant to genie industriel / lean: {len(cands)}\n")

for i, r in enumerate(cands, 1):
    d = re.sub(r"\s+", " ", r.get("description_snippet", ""))[:700]
    print(f"--- [{i}] {r['job_title']}")
    print(f"    ENTREPRISE : {r.get('company','')}")
    print(f"    LIEU       : {r.get('location_city','')} | PAYS: {r.get('country','')}")
    print(f"    SOURCE     : {r.get('source','')} | CONTRAT: {r.get('contract_type','')} | NIV: {r.get('experience_required','')}")
    print(f"    URL        : {r.get('url','')}")
    print(f"    DESC       : {d}")
    print()
