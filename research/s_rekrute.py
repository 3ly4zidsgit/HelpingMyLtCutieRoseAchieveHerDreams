import requests, re, sys, time
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, norm

KEYWORDS = [
    "lean", "six sigma", "kaizen", "kanban", "ishikawa", "amelioration continue",
    "amélioration continue", "excellence operationnelle", "excellence opérationnelle",
    "genie industriel", "génie industriel", "ingenieur industriel", "black belt",
    "green belt", "dmaic", "smed", "vsm", "tpm", "5s", "methodes", "méthodes",
    "industrialisation", "process", "production", "qualite", "qualité",
    "supply chain", "logistique", "performance industrielle", "productivite",
    "continuous improvement", "operational excellence", "industrial engineer",
    "manufacturing", "ordonnancement", "planification", "qhse", "maintenance",
    "consultant organisation", "audit qualite", "amelioration", "optimisation",
]

BASE = "https://www.rekrute.com"

def txt(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

def parse_li(li, sess):
    rid = li.get("id", "")
    a = li.select_one("a.titreJob")
    if not a: return None
    title = txt(a)
    href = a.get("href", "")
    url = BASE + href if href.startswith("/") else href
    img = li.select_one("img.photo")
    company = (img.get("title") or img.get("alt") or "").strip() if img else ""
    if not company:
        ca = li.select_one("div.col-sm-2 a")
        if ca and ca.get("href"):
            m = re.search(r"/([a-z0-9\-]+)-emploi-recrutement", ca["href"])
            company = m.group(1).replace("-", " ").title() if m else ""

    # location often inside title after "|"
    city = ""
    if "|" in title:
        parts = [p.strip() for p in title.split("|")]
        tail = parts[-1]
        city = re.sub(r"\((Maroc|Morocco)\)", "", tail).strip(" -")
        title = parts[0].strip()

    desc = ""
    for d in li.select("div.info span"):
        t = txt(d)
        if len(t) > len(desc): desc = t

    date_posted = deadline = positions = ""
    em = li.select_one("em.date")
    if em:
        spans = [txt(s) for s in em.select("span")]
        dates = [s for s in spans if re.match(r"\d{2}/\d{2}/\d{4}", s)]
        if len(dates) >= 1: date_posted = dates[0]
        if len(dates) >= 2: deadline = dates[1]
        nums = [s for s in spans if s.isdigit()]
        if nums: positions = nums[-1]

    sector = function = exp = study = contract = remote = ""
    for li2 in li.select("div.info ul li"):
        t = txt(li2)
        if t.lower().startswith("secteur"): sector = t.split(":", 1)[-1].strip()
        elif t.lower().startswith("fonction"): function = t.split(":", 1)[-1].strip()
        elif "xp" in t.lower()[:12] or t.lower().startswith("exp"): exp = t.split(":", 1)[-1].strip()
        elif "tude" in t.lower()[:14]: study = t.split(":", 1)[-1].strip()
        elif "contrat" in t.lower():
            v = t.split(":", 1)[-1].strip()
            if "élétravail" in v or "eletravail" in v.replace("é","e"):
                bits = re.split(r"-\s*T[ée]l[ée]travail\s*:", v)
                contract = bits[0].strip()
                remote = bits[1].strip() if len(bits) > 1 else ""
            else:
                contract = v

    keep, score, hits = relevance(title, desc + " " + function + " " + sector)
    if not keep: return None

    return blank(source="Rekrute.com", job_title=title, company=company,
                 location_city=city, country="Maroc", remote=remote,
                 contract_type=contract, experience_required=exp,
                 education_level=study, sector=sector, function=function,
                 date_posted=date_posted, deadline=deadline, positions=positions,
                 url=url, description_snippet=desc[:600],
                 keywords_matched=", ".join(hits), score=score)

def run():
    sess = requests.Session(); sess.headers.update(HDRS)
    found, seen = {}, set()
    for kw in KEYWORDS:
        for page in range(1, 6):
            u = f"{BASE}/offres.html?s=1&p={page}&keyword={requests.utils.quote(kw)}"
            try:
                r = sess.get(u, timeout=30)
            except Exception as e:
                print(f"  {kw} p{page} ERR {e}"); break
            if r.status_code != 200: break
            s = BeautifulSoup(r.text, "html.parser")
            lis = s.select("li.post-id")
            if not lis: break
            new = 0
            for li in lis:
                try:
                    row = parse_li(li, sess)
                except Exception:
                    continue
                if not row: continue
                k = jid(row["url"])
                if k in found: continue
                found[k] = row; new += 1
            print(f"  kw='{kw}' p{page}: {len(lis)} cards, +{new} relevant (total {len(found)})")
            sys.stdout.flush()
            if len(lis) < 10: break
            time.sleep(0.4)
    rows = list(found.values())
    save("rekrute", rows)
    return rows

if __name__ == "__main__":
    run()
