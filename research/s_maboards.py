import requests, re, sys, time
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from common import HDRS, blank, relevance, save, jid, find_emails

S = requests.Session(); S.headers.update(HDRS)

def T(el, sel=None):
    if sel: el = el.select_one(sel)
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

rows = []
def push(**kw):
    keep, score, hits = relevance(kw.get("job_title",""), kw.get("description_snippet",""))
    if not keep: return False
    rows.append(blank(keywords_matched=", ".join(hits), score=score, **kw)); return True

# ---------------- MarocAnnonces ----------------
MA_KW = ["lean", "amelioration continue", "six sigma", "genie industriel", "kaizen",
         "methodes", "industrialisation", "qualite", "production", "supply chain",
         "logistique", "process", "maintenance", "excellence operationnelle", "ingenieur"]
n = 0
for kw in MA_KW:
    for pg in range(1, 4):
        url = f"https://www.marocannonces.com/maroc/offres-emploi-b309.html?kw={quote_plus(kw)}&pge={pg}"
        try:
            r = S.get(url, timeout=30)
        except Exception as e:
            print("  MA ERR", e); break
        if r.status_code != 200: break
        s = BeautifulSoup(r.text, "html.parser")
        cards = s.select("ul.cars-list li")
        cards = [c for c in cards if c.select_one("a[href*='/annonce/']")]
        if not cards: break
        got = 0
        for c in cards:
            a = c.select_one("a[href*='/annonce/']")
            title = T(c, "h3") or T(a)
            u = urljoin("https://www.marocannonces.com/", a.get("href",""))
            loc = T(c, "span.location") or ""
            date = T(c, "em.date") or T(c, "span.date") or ""
            desc = T(c)
            if push(source="MarocAnnonces.com", job_title=title, company="",
                    location_city=loc, country="Maroc", url=u, date_posted=date,
                    description_snippet=desc[:400]): got += 1
        n += got
        print(f"  [MarocAnnonces] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {n})"); sys.stdout.flush()
        time.sleep(0.4)

# ---------------- Dreamjob.ma ----------------
DJ_KW = ["lean", "amelioration continue", "six sigma", "genie industriel", "kaizen",
         "excellence operationnelle", "ingenieur methodes", "industrialisation",
         "supply chain", "ingenieur qualite", "ingenieur process", "ingenieur production",
         "kanban", "black belt", "performance industrielle", "ingenieur industriel"]
m = 0
for kw in DJ_KW:
    for pg in range(1, 3):
        url = f"https://www.dreamjob.ma/page/{pg}/?s={quote_plus(kw)}" if pg > 1 else f"https://www.dreamjob.ma/?s={quote_plus(kw)}"
        try:
            r = S.get(url, timeout=30)
        except Exception: break
        if r.status_code != 200: break
        s = BeautifulSoup(r.text, "html.parser")
        cards = s.select("article")
        if not cards: break
        got = 0
        for c in cards:
            a = c.select_one("a[href*='/emploi/']") or c.select_one("h2 a") or c.select_one("a")
            if not a: continue
            title = T(c, "h2") or T(c, "h3") or T(a)
            u = a.get("href","")
            date = T(c, "time") or ""
            desc = T(c)
            if push(source="Dreamjob.ma", job_title=title, company="", location_city="",
                    country="Maroc", url=u, date_posted=date,
                    description_snippet=desc[:400]): got += 1
        m += got
        print(f"  [Dreamjob] '{kw}' p{pg}: {len(cards)} cards, +{got} (tot {m})"); sys.stdout.flush()
        time.sleep(0.4)

uniq = {}
for r in rows:
    k = jid(r["url"], r["job_title"], r["company"])
    if k not in uniq or r["score"] > uniq[k]["score"]: uniq[k] = r
print(f"TOTAL ma boards: {len(uniq)}")
save("maboards", list(uniq.values()))
