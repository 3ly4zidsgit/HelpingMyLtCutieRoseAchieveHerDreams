"""Company-level enrichment without a search engine: resolve the company's own
domain by trying the obvious candidates, then pull recruitment/contact emails
from its contact & careers pages. Threaded + cached + resumable."""
import requests, re, json, os, threading, socket
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from common import HDRS, find_emails, norm, load, OUT, strip_accents

CACHE_F = os.path.join(OUT, "company_cache.json")
CACHE = json.load(open(CACHE_F, encoding="utf-8")) if os.path.exists(CACHE_F) else {}
LOCK = threading.Lock()

LEGAL = re.compile(r"\b(sarl|s\.a\.r\.l|sa|s\.a|sas|spa|group[e]?|holding|maroc|morocco|"
                   r"company|co|inc|ltd|llc|gmbh|international|services?|industries?|"
                   r"technologies?|technology|solutions?|consulting|africa)\b", re.I)

COMMON = {"bank", "banque", "achat", "achats", "service", "fromagerie", "societe", "cabinet",
          "agence", "entreprise", "atlas", "atlantic", "global", "premium", "expert", "experts",
          "conseil", "assistance", "centre", "center", "medical", "clinique", "hopital",
          "universite", "ecole", "institut", "office", "direction", "delegation", "reseau",
          "capital", "finance", "invest", "energie", "energy", "transport", "logistic",
          "logistique", "immobilier", "assurance", "produits", "products", "system", "systems",
          "digital", "media", "market", "marketing", "trading", "export", "import", "sourcing",
          "recrutement", "emploi", "talent", "talents", "carriere", "carrieres", "profils"}

def slugs(company):
    base = strip_accents(company).lower()
    base = re.sub(r"[&/,\.'\"()]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    core = LEGAL.sub(" ", base)
    core = re.sub(r"\s+", " ", core).strip() or base
    out = []
    for name in (core, base):
        j = name.replace(" ", "")
        d = name.replace(" ", "-")
        for s in (j, d):
            if 2 < len(s) < 32 and s not in out:
                out.append(s)
        # only fall back to the first word when it is distinctive: "bank", "achat"
        # or "service" would happily resolve to somebody else's domain.
        first = name.split(" ")[0]
        if len(first) >= 6 and first not in COMMON and first not in out:
            out.append(first)
    return out[:4]

TLDS = [".ma", ".com", ".co.ma", ".net", ".fr", ".org"]
PATHS = ["/contact", "/contact-us", "/nous-contacter", "/contactez-nous",
         "/careers", "/carrieres", "/carriere", "/recrutement", "/jobs", ""]

def resolves(host):
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname(host)
        return True
    except Exception:
        return False

def find_site(s, company):
    toks = [t for t in re.split(r"\W+", strip_accents(company).lower()) if len(t) > 2 and not LEGAL.match(t)]
    for sl in slugs(company):
        for tld in TLDS:
            host = sl + tld
            if not resolves(host) and not resolves("www." + host):
                continue
            for scheme_host in (f"https://www.{host}", f"https://{host}"):
                try:
                    r = s.get(scheme_host, timeout=7, allow_redirects=True)
                except Exception:
                    continue
                if r.status_code >= 400 or len(r.text) < 400:
                    continue
                page = norm(BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:5000])
                # confirm it is really this company's site
                if toks and not any(t in page or t in norm(r.url) for t in toks):
                    continue
                if re.search(r"domain (is )?for sale|acheter ce domaine|parked|godaddy|sedo", page):
                    continue
                p = urlparse(r.url)
                return f"{p.scheme}://{p.netloc.split(':')[0]}"
    return ""

PLACEHOLDER = re.compile(r"(votreadresse|votre-adresse|your ?(name|email|address)|nom@|"
                         r"email@|adresse@|exemple|example|test@|user@|@mail\.com|@domain|"
                         r"@yourdomain|@site\.|xxx|abc@|nom\.prenom)", re.I)

GENERIC = re.compile(r"^(recrutement|recruitment|rh|hr|job|jobs|career|careers|emploi|emplois|"
                     r"candidature|candidatures|cv|contact|info|infos|hello|welcome|talent|"
                     r"ressources)", re.I)

def find_mails(s, site):
    found = []
    for p in PATHS:
        try:
            r = s.get(site + p, timeout=7)
        except Exception:
            continue
        if r.status_code != 200: continue
        for e in find_emails(r.text):
            if PLACEHOLDER.search(e): continue
            if e.lower() not in [x.lower() for x in found]:
                found.append(e)
        if len(found) >= 4: break
    host = urlparse(site).netloc.replace("www.", "")
    found.sort(key=lambda e: (0 if GENERIC.match(e) else 1,
                              0 if host.split(".")[0] in e.lower() else 1, len(e)))
    return found[:3]

def one(company):
    key = norm(company)
    with LOCK:
        if key in CACHE and CACHE[key].get("_v") == 3:
            return company, CACHE[key]
    s = requests.Session(); s.headers.update(HDRS)
    info = {"website": "", "emails": [], "hr_name": "", "hr_title": "", "hr_profile": "", "_v": 3}
    try:
        info["website"] = find_site(s, company)
        if info["website"]:
            info["emails"] = find_mails(s, info["website"])
    except Exception:
        pass
    with LOCK:
        old = CACHE.get(key) or {}
        for k in ("hr_name", "hr_title", "hr_profile"):
            if old.get(k) and not info[k]: info[k] = old[k]
        CACHE[key] = info
        json.dump(CACHE, open(CACHE_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return company, info


if __name__ == "__main__":
    rows = load("merged")
    comps = {}
    for r in rows:
        c = (r.get("company") or "").strip()
        if c and len(c) > 2 and not c.lower().startswith(("confidentiel", "anonym", "entreprise")):
            comps.setdefault(norm(c), c)
    todo = [c for k, c in comps.items() if not (CACHE.get(k) or {}).get("_v") == 3]
    print(f"{len(comps)} distinct companies | {len(todo)} to resolve", flush=True)

    done = ok = mails = 0
    with ThreadPoolExecutor(max_workers=40) as ex:
        futs = {ex.submit(one, c): c for c in todo}
        for f in as_completed(futs):
            done += 1
            try:
                c, info = f.result()
            except Exception as e:
                print(f"  {done}/{len(todo)} ERR {futs[f][:28]} {e}", flush=True); continue
            if info["website"]: ok += 1
            if info["emails"]: mails += 1
            print(f"  {done}/{len(todo)} {c[:30]:30s} {info['website'][:36]:36s} "
                  f"{', '.join(info['emails'])[:44]}", flush=True)

    w = sum(1 for v in CACHE.values() if v.get("website"))
    e = sum(1 for v in CACHE.values() if v.get("emails"))
    print(f"\nDONE — {len(CACHE)} companies cached | site found {w} | emails found {e}")
