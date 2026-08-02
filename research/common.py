import json, os, re, time, hashlib, unicodedata

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
HDRS = {"User-Agent": UA,
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"}

def strip_accents(s):
    if not s: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm(s):
    return re.sub(r"\s+", " ", strip_accents(str(s or "")).lower()).strip()

# --- relevance -------------------------------------------------------------
# strong = on its own enough to keep the offer
STRONG = [
    r"\blean\b", r"\bsix ?sigma\b", r"\bkaizen\b", r"\bkanban\b", r"\bishikawa\b",
    r"\bamelioration continue\b", r"\bcontinuous improvement\b",
    r"\bexcellence operationnelle\b", r"\boperational excellence\b",
    r"\bgenie industriel\b", r"\bindustrial engineer", r"\bingenieur industriel\b",
    r"\bblack belt\b", r"\bgreen belt\b", r"\byellow belt\b",
    r"\bdmaic\b", r"\bsmed\b", r"\bvsm\b", r"\bvalue stream\b", r"\btpm\b",
    r"\b5s\b", r"\bmuda\b", r"\bpoka.?yoke\b", r"\bgemba\b", r"\bheijunka\b",
    r"\bprocess improvement\b", r"\bamelioration des process", r"\bperformance industrielle\b",
    r"\bexcellence industrielle\b", r"\bproductivite industrielle\b",
    r"\bwcm\b", r"\bworld class manufacturing\b", r"\bopex\b", r"\bops excellence\b",
    r"\bmanufacturing excellence\b", r"\bbusiness process improvement\b",
]
# medium = kept only if paired with an industrial/ops context word
MEDIUM = [
    r"\bingenieur methodes?\b", r"\bmethods engineer\b", r"\bresponsable methodes?\b",
    r"\bindustrialisation\b", r"\bindustrialization\b", r"\bprocess engineer\b",
    r"\bingenieur process\b", r"\bmanufacturing engineer\b", r"\bproduction engineer\b",
    r"\bingenieur production\b", r"\bingenieur qualite\b", r"\bquality engineer\b",
    r"\bsupply chain\b", r"\bingenieur logistique\b", r"\bplanification industrielle\b",
    r"\bordonnancement\b", r"\bqhse\b", r"\bqse\b", r"\bingenieur maintenance\b",
    r"\bresponsable production\b", r"\bproduction manager\b", r"\boperations manager\b",
    r"\bresponsable qualite\b", r"\bquality manager\b", r"\bplant manager\b",
    r"\bconsultant en organisation\b", r"\bbusiness analyst\b", r"\bproject engineer\b",
]
CONTEXT = [
    r"\blean\b", r"\bsigma\b", r"\bkaizen\b", r"\bkanban\b", r"\bamelioration\b",
    r"\bimprovement\b", r"\bexcellence\b", r"\bproductivit", r"\bperformance\b",
    r"\bindustri", r"\bmanufactur", r"\busine\b", r"\bplant\b", r"\bproduction\b",
    r"\bqualite\b", r"\bquality\b", r"\bprocess", r"\bautomobile\b", r"\baeronautique\b",
    r"\bsupply chain\b", r"\blogistique\b", r"\boperations\b", r"\bmethodes\b",
]
NEGATIVE = [
    r"\bclean architecture\b", r"\bclean code\b", r"\bnettoyage\b", r"\bagent de proprete\b",
    r"\bfemme de menage\b", r"\bcleaner\b", r"\bcleaning\b",
]

_S = [re.compile(p) for p in STRONG]
_M = [re.compile(p) for p in MEDIUM]
_C = [re.compile(p) for p in CONTEXT]
_N = [re.compile(p) for p in NEGATIVE]

def relevance(title, body=""):
    """return (keep: bool, score: int, matched: list[str])"""
    t, b = norm(title), norm(body)
    full = t + " || " + b
    if any(p.search(t) for p in _N) and not any(p.search(t) for p in _S):
        return False, 0, []
    hits, score = [], 0
    for p in _S:
        if p.search(t):
            hits.append(p.pattern); score += 10
        elif p.search(b):
            hits.append(p.pattern); score += 4
    for p in _M:
        if p.search(t):
            hits.append(p.pattern); score += 3
    if score >= 10:
        return True, score, sorted(set(hits))
    if score >= 4:   # strong keyword found only in the body
        return True, score, sorted(set(hits))
    if score >= 3 and any(p.search(full) for p in _C):
        return True, score, sorted(set(hits))
    return False, score, sorted(set(hits))

# --- storage ---------------------------------------------------------------
def jid(url, title="", company=""):
    return hashlib.md5(norm(url or (title + company)).encode()).hexdigest()[:12]

def save(name, rows):
    p = os.path.join(OUT, f"{name}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"  -> saved {len(rows)} rows to {name}.json")

def load(name):
    p = os.path.join(OUT, f"{name}.json")
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def blank(**kw):
    row = {
        "source": "", "job_title": "", "company": "", "recruiter_or_hr": "",
        "contact_email": "", "location_city": "", "country": "", "remote": "",
        "contract_type": "", "experience_required": "", "education_level": "",
        "sector": "", "function": "", "date_posted": "", "deadline": "",
        "positions": "", "salary": "", "url": "", "description_snippet": "",
        "keywords_matched": "", "score": 0,
    }
    row.update(kw)
    return row

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
BAD_MAIL = re.compile(r"(sentry|example|wixpress|godaddy|domain|hostmaster|abuse@|postmaster|"
                      r"noreply|no-reply|sentry\.io|\.(png|jpe?g|gif|webp|svg|avif|ico|css|js)\b|"
                      r"@\dx\b|@2x|@3x|\d+x\.|placeholder|lorem)", re.I)

def find_emails(text):
    out = []
    for m in EMAIL_RE.findall(text or ""):
        if BAD_MAIL.search(m): continue
        if len(m) > 60: continue
        out.append(m)
    return sorted(set(out))
