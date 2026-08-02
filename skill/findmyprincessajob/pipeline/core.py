"""Shared plumbing: keyword expansion, relevance scoring, row model, storage."""
import json, os, re, hashlib, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA,
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive"}


def strip_accents(s):
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def norm(s):
    return re.sub(r"\s+", " ", strip_accents(s).lower()).strip()


# --------------------------------------------------------------- run context
class Run:
    """Everything that depends on the requested specialty lives here."""

    def __init__(self, spec_path):
        with open(spec_path, encoding="utf-8") as f:
            self.spec = json.load(f)
        self.specialty = self.spec["specialty"]
        self.outdir = self.spec["outdir"]
        self.datadir = os.path.join(self.outdir, "data")
        os.makedirs(self.datadir, exist_ok=True)
        self.queries_fr = self.spec.get("queries_fr", [])
        self.queries_en = self.spec.get("queries_en", [])
        self.queries = self.queries_fr + self.queries_en
        self._strong = [re.compile(p) for p in self.spec.get("strong", [])]
        self._medium = [re.compile(p) for p in self.spec.get("medium", [])]
        self._context = [re.compile(p) for p in self.spec.get("context", [])]
        self._offdomain = [re.compile(p) for p in self.spec.get("offdomain", [])]
        self._exclude = [re.compile(p) for p in self.spec.get("exclude_titles", [])]

    # ---- relevance -------------------------------------------------------
    def relevance(self, title, body=""):
        """(keep, score, matched). A strong hit in the TITLE is worth 10; in the
        body only 4, because phrases like 'amelioration continue' are filler in
        almost every French ad."""
        t, b = norm(title), norm(body)
        if any(p.search(t) for p in self._exclude):
            return False, 0, []
        hits, score = [], 0
        for p in self._strong:
            if p.search(t):
                hits.append(p.pattern); score += 10
            elif p.search(b):
                hits.append(p.pattern); score += 4
        for p in self._medium:
            if p.search(t):
                hits.append(p.pattern); score += 3
        hits = sorted(set(hits))
        if score >= 10 or score >= 4:
            return True, score, hits
        if score >= 3 and any(p.search(t + " " + b) for p in self._context):
            return True, score, hits
        return False, score, hits

    def strict_keep(self, row):
        """Second gate applied at merge time: a body-only hit is not enough when
        the title clearly belongs to another trade."""
        title = norm(row.get("job_title", ""))
        score = row.get("score", 0)
        if any(p.search(title) for p in self._exclude):
            return False
        if any(p.search(title) for p in self._offdomain):
            return score >= 10
        if score >= 10:
            return True
        blob = norm(" ".join([title, row.get("function", ""), row.get("sector", ""),
                              row.get("description_snippet", "")[:500]]))
        return any(p.search(blob) for p in self._context)

    # ---- storage ---------------------------------------------------------
    def save(self, name, rows):
        p = os.path.join(self.datadir, f"{name}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print(f"  -> {len(rows)} rows saved to {name}.json", flush=True)

    def load(self, name):
        p = os.path.join(self.datadir, f"{name}.json")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return json.load(f)


# --------------------------------------------------------------- row model
FIELDS = ("source job_title company recruiter_or_hr hr_title hr_profile contact_email "
          "company_email company_website location_city country remote contract_type "
          "experience_required education_level sector function date_posted date_posted_iso "
          "deadline deadline_iso positions salary url description_snippet keywords_matched "
          "seniority_bucket remote_verdict remote_reason").split()


def blank(**kw):
    row = {f: "" for f in FIELDS}
    row["score"] = 0
    row.update(kw)
    return row


def jid(url, title="", company=""):
    key = norm(url) or (norm(title) + norm(company))
    return hashlib.md5(key.encode()).hexdigest()[:12]


def dedupe(rows):
    """Collapse on URL first, then on title+company, merging non-empty fields."""
    by_url, by_tc, out = {}, {}, []
    for r in rows:
        u = norm((r.get("url") or "").split("?")[0].rstrip("/"))
        tc = norm(r.get("job_title", "")) + "|" + norm(r.get("company", ""))
        tgt = by_url.get(u) if u else None
        if tgt is None and r.get("company") and len(norm(r.get("job_title", ""))) > 8:
            tgt = by_tc.get(tc)
        if tgt is not None:
            for f, v in r.items():
                if v and not tgt.get(f):
                    tgt[f] = v
            if r.get("source") and r["source"] not in tgt.get("source", ""):
                tgt["source"] += " ; " + r["source"]
            continue
        out.append(r)
        if u:
            by_url[u] = r
        if r.get("company"):
            by_tc[tc] = r
    return out


# --------------------------------------------------------------- text repair
MOJI = re.compile("[ÃÂâ][-¿‘-„€šœ™]")


def unmojibake(s):
    """Undo one round of 'UTF-8 bytes decoded as cp1252/latin-1'."""
    if not s or not MOJI.search(s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = s.encode(enc, "strict").decode("utf-8", "strict")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if not MOJI.search(fixed):
            return fixed
    return s


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
BAD_MAIL = re.compile(r"(sentry|example|wixpress|godaddy|hostmaster|abuse@|postmaster|"
                      r"noreply|no-reply|\.(png|jpe?g|gif|webp|svg|avif|ico|css|js)\b|"
                      r"@\dx\b|placeholder|votreadresse|your(name|email)|nom@)", re.I)


def find_emails(text):
    return sorted({m for m in EMAIL_RE.findall(text or "")
                   if not BAD_MAIL.search(m) and len(m) <= 60})
