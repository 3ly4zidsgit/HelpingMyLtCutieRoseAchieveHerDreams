"""ANAPEC (national employment agency) + four Moroccan boards not covered before.
ANAPEC serves a broken TLS chain, hence verify=False."""
import requests, re, sys, time, urllib3
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, norm, find_emails
urllib3.disable_warnings()

S = requests.Session(); S.headers.update(HDRS); S.verify = False

def T(el, sel=None):
    if sel: el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

rows = []
def push(src, title, comp, loc, ctype, date, url, desc, **extra):
    if not title or not url: return False
    if re.search(r"\btechnicien\b|\btechnician\b", norm(title)): return False
    keep, score, hits = relevance(title, desc)
    if not keep: return False
    rows.append(blank(source=src, job_title=title, company=comp, location_city=loc,
                      country="Maroc", contract_type=ctype, date_posted=date, url=url,
                      description_snippet=desc[:800],
                      contact_email=", ".join(find_emails(desc)[:2]),
                      keywords_matched=", ".join(hits), score=score, **extra))
    return True

# ============================================================ ANAPEC
BASE = "https://www.anapec.org"
KW = ["lean", "amelioration continue", "six sigma", "genie industriel", "kaizen",
      "excellence operationnelle", "methodes", "industrialisation", "process",
      "qualite", "production", "supply chain", "logistique", "maintenance",
      "ingenieur", "planification", "ordonnancement", "performance", "qhse",
      "industriel", "kanban", "productivite", "optimisation", "audit"]
n = 0
for kw in KW:
    # the site's own form posts motclee as a GET query param, not a path segment
    url = f"{BASE}/sigec-app-rv/fr/chercheurs/resultat_recherche"
    try:
        r = S.get(url, params={"motclee": kw, "appcle": "", "gender": "",
                               "entreprise": "", "ville": ""}, timeout=30)
    except Exception as e:
        print(f"  [ANAPEC] '{kw}' ERR {str(e)[:50]}", flush=True); continue
    if r.status_code != 200:
        print(f"  [ANAPEC] '{kw}' HTTP {r.status_code}", flush=True); continue
    s = BeautifulSoup(r.text, "html.parser")
    cards = s.select("div.offre, li.offre, tr, div.bloc_offre, div.item-offre")
    got = 0
    links = s.select("a[href*='bloc_offre'], a[href*='offre'], a[href*='postulation']")
    seenu = set()
    for a in links:
        href = a.get("href") or ""
        if "resultat_recherche" in href or not href: continue
        u = urljoin(BASE, href)
        if u in seenu: continue
        seenu.add(u)
        title = T(a)
        if len(title) < 5: continue
        parent = a.find_parent(["tr", "li", "div"])
        ctx = T(parent) if parent else title
        city = ""
        m = re.search(r"\b(Casablanca|Tanger|Rabat|K[ée]nitra|Marrakech|Agadir|F[èe]s|"
                      r"Mekn[èe]s|Oujda|T[ée]touan|El Jadida|Sal[ée]|Mohammedia|Nador|"
                      r"Safi|Settat|Berrechid|Temara|Laayoune|Beni Mellal)\b", ctx, re.I)
        if m: city = m.group(1)
        date = ""
        md = re.search(r"(\d{2}/\d{2}/\d{4})", ctx)
        if md: date = md.group(1)
        ctype = ""
        mc = re.search(r"\b(CDI|CDD|Stage|Anapec|Int[ée]rim|Temps plein)\b", ctx, re.I)
        if mc: ctype = mc.group(1).upper() if len(mc.group(1)) <= 3 else mc.group(1)
        if push("ANAPEC.org", title, "", city, ctype, date, u, ctx): got += 1
    n += got
    print(f"  [ANAPEC] '{kw}': {len(seenu)} liens, +{got} (tot {n})", flush=True)
    time.sleep(0.6)

# ============================================================ MarocEmploi.net
n2 = 0
for kw in ["lean", "amelioration continue", "six sigma", "genie industriel",
           "excellence operationnelle", "kaizen", "ingenieur methodes",
           "industrialisation", "supply chain", "ingenieur qualite",
           "ingenieur process", "ingenieur production", "kanban", "performance industrielle"]:
    for pg in (1, 2):
        u = (f"https://www.marocemploi.net/page/{pg}/?s={quote(kw)}" if pg > 1
             else f"https://www.marocemploi.net/?s={quote(kw)}")
        try:
            r = S.get(u, timeout=30)
        except Exception: break
        if r.status_code != 200: break
        s = BeautifulSoup(r.text, "html.parser")
        cards = s.select("article, div.post, h2.entry-title")
        got = 0
        seenu = set()
        for a in s.select("a[href]"):
            href = a.get("href") or ""
            if not re.search(r"marocemploi\.net/\d{4}/|/offre|/emploi/", href): continue
            if href in seenu: continue
            seenu.add(href)
            title = T(a)
            if len(title) < 8: continue
            par = a.find_parent(["article", "div", "li"])
            ctx = T(par) if par else title
            md = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\d{2}/\d{2}/\d{4})", ctx)
            if push("MarocEmploi.net", title, "", "", "", md.group(1) if md else "",
                    href, ctx): got += 1
        n2 += got
        print(f"  [MarocEmploi] '{kw}' p{pg}: {len(seenu)} liens, +{got} (tot {n2})", flush=True)
        time.sleep(0.4)

# ============================================================ Modiami
n3 = 0
for kw in ["lean", "amelioration continue", "genie industriel", "excellence operationnelle",
           "ingenieur methodes", "industrialisation", "supply chain", "ingenieur qualite",
           "ingenieur process", "six sigma", "production", "kaizen"]:
    u = f"https://www.modiami.com/search?q={quote(kw)}"
    try:
        r = S.get(u, timeout=30)
    except Exception: continue
    if r.status_code != 200: continue
    s = BeautifulSoup(r.text, "html.parser")
    got = 0; seenu = set()
    for a in s.select("a[href*='modiami.com/20']"):
        href = (a.get("href") or "").split("?")[0]
        if href in seenu: continue
        seenu.add(href)
        title = T(a)
        if len(title) < 10: continue
        par = a.find_parent(["article", "div"])
        ctx = T(par) if par else title
        if push("Modiami.com", title, "", "", "", "", href, ctx): got += 1
    n3 += got
    print(f"  [Modiami] '{kw}': {len(seenu)} liens, +{got} (tot {n3})", flush=True)
    time.sleep(0.4)

# ============================================================ Jobsquare.ma
n4 = 0
for kw in ["lean", "amelioration-continue", "genie-industriel", "ingenieur-methodes",
           "industrialisation", "supply-chain", "ingenieur-qualite", "ingenieur-process",
           "six-sigma", "production", "excellence-operationnelle", "kaizen", "qualite"]:
    for u in [f"https://www.jobsquare.ma/recherche?q={quote(kw)}",
              f"https://www.jobsquare.ma/offres-emploi?q={quote(kw)}",
              f"https://www.jobsquare.ma/?s={quote(kw)}"]:
        try:
            r = S.get(u, timeout=25)
        except Exception: continue
        if r.status_code != 200: continue
        s = BeautifulSoup(r.text, "html.parser")
        got = 0; seenu = set()
        for a in s.select("a[href*='/offre'], a[href*='/emploi/'], a[href*='/job']"):
            href = urljoin("https://www.jobsquare.ma", (a.get("href") or "").split("?")[0])
            if href in seenu: continue
            seenu.add(href)
            title = T(a)
            if len(title) < 8: continue
            par = a.find_parent(["article", "div", "li"])
            ctx = T(par) if par else title
            if push("Jobsquare.ma", title, "", "", "", "", href, ctx): got += 1
        if got:
            n4 += got
            print(f"  [Jobsquare] '{kw}': +{got} (tot {n4})", flush=True)
            break
    time.sleep(0.3)

uniq = {}
for r in rows:
    k = jid(r["url"], r["job_title"], r["company"])
    if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
out = list(uniq.values())
print(f"\nTOTAL ANAPEC + nouveaux boards: {len(out)}")
save("anapec_boards", out)
from collections import Counter
print(Counter(r["source"] for r in out))
