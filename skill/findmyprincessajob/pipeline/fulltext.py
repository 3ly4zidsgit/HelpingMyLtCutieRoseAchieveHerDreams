"""Second fetch: the FULL body of every ad that will ship.

The scrapers only ever store what the list page showed (~700 chars). The
experience requirement, the contract type and often the real employer are in the
body, not on the card - which is why 'Experience requise' comes out empty or
carries a value the board invented ("Non pertinent", "Cadre"). `enrich` can only
be as good as the text it is given, so run this before it.

Two passes:
  1. plain HTTP  - LinkedIn (the jobs-guest posting endpoint needs no auth),
                   Rekrute, SmartRecruiters, and anything else that answers.
  2. UC mode     - whatever the first pass could not get. Dreamjob and Emploi.ma
                   sit behind Cloudflare, Optioncarriere blocks on IP reputation,
                   Bayt / Jooble / Indeed / MarocAnnonces refuse scripted clients.
                   A VISIBLE window is what clears these; headless does not.

Writes data/fulltext.json as {url: {"text","title","ok"}}. Resumable: an entry
that already holds a real body is never refetched.
"""
import os, re, json, time, html, random
import urllib.request, urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA,
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "identity"}

# answers a scripted request; everything else goes straight to the UC pass
PLAIN = re.compile(r"(linkedin\.com|rekrute\.com|smartrecruiters\.com|"
                   r"greenhouse\.io|lever\.co|workable\.com|recruitee\.com)", re.I)

CHALLENGE = ("cf-challenge", "just a moment", "un instant", "checking your browser",
             "cf_chl", "turnstile", "verification requise", "verification required")

MIN_BODY = 400


def _clean(h):
    h = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</tr>|</h\d>", "\n", h, flags=re.I)
    h = re.sub(r"<li[^>]*>", " - ", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    h = re.sub(r"[ \t\xa0]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def _get(url, timeout=35):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _http_one(url):
    m = re.search(r"linkedin\.com/jobs/view/(?:.*-)?(\d{6,})", url)
    if m:
        api = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}"
        return _clean(_get(api)), ""
    h = _get(url)
    ttl = re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)
    return _clean(h), html.unescape(ttl.group(1)).strip() if ttl else ""


def _store_path(run):
    return os.path.join(run.datadir, "fulltext.json")


def _load(run):
    p = _store_path(run)
    store = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            store = json.load(f)
    # tolerate a bare string written by an older helper
    for u, v in list(store.items()):
        if isinstance(v, str):
            store[u] = {"text": v, "title": "", "ok": len(v) > MIN_BODY}
    return store


def _save(run, store):
    with open(_store_path(run), "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False)


def _have(store, url):
    return len((store.get(url) or {}).get("text", "")) >= MIN_BODY


def http_pass(run, urls, store):
    todo = [u for u in urls if PLAIN.search(u) and not _have(store, u)]
    print(f"HTTP simple: {len(todo)} a recuperer", flush=True)
    ok = 0
    for i, u in enumerate(todo, 1):
        try:
            t, ttl = _http_one(u)
            store[u] = {"text": t, "title": ttl, "ok": len(t) > MIN_BODY}
            ok += 1 if len(t) > MIN_BODY else 0
        except urllib.error.HTTPError as e:
            store[u] = {"text": "", "title": "", "ok": False, "err": f"HTTP {e.code}"}
        except Exception as e:
            store[u] = {"text": "", "title": "", "ok": False, "err": type(e).__name__}
        if i % 10 == 0 or i == len(todo):
            _save(run, store)
            print(f"  {i}/{len(todo)} ok={ok}", flush=True)
        time.sleep(random.uniform(1.1, 2.3))
    return ok


# where the ad body lives on the walled boards; falls back to <body>
BODY_SEL = {
    "dreamjob.ma": ["div.entry-content", "article", "div.post-content"],
    "optioncarriere.ma": ["section.content", "div.content", "article"],
    "marocannonces.com": ["div.holder", "div#annonce", "div.description"],
    "bayt.com": ["div#job_description", "div.card-content", "div.t-break"],
    "ma.jooble.org": ["div[data-test-name='_jobDescription']", "div.description"],
    "emploi.ma": ["div.job-description", "div.card-block"],
    "ma.indeed.com": ["div#jobDescriptionText", "div.jobsearch-JobComponent"],
}


def _extract(html_src, host):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_src, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    for sel in BODY_SEL.get(host, []) + ["main", "body"]:
        el = soup.select_one(sel)
        if el:
            txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
            if len(txt) > MIN_BODY:
                return txt[:20000]
    return ""


DEAD = ("MaxRetryError", "NewConnectionError", "InvalidSessionIdException",
        "WebDriverException", "NoSuchWindowException", "ConnectionRefusedError")


def _one(sb, url, host):
    try:
        sb.uc_open_with_reconnect(url, reconnect_time=5)
    except Exception:
        sb.open(url)
    head = ""
    try:
        head = sb.get_page_source()[:5000].lower()
    except Exception:
        pass
    # uc_gui_click_captcha drives the real mouse and blocks forever when nothing
    # is on screen, so it is only called once a challenge marker is really there.
    if any(k in head for k in CHALLENGE):
        try:
            sb.uc_gui_click_captcha()
        except Exception:
            pass
        time.sleep(3)
    time.sleep(1.5)
    txt = _extract(sb.get_page_source(), host)
    ttl = ""
    try:
        ttl = re.sub(r"\s+", " ", sb.get_title() or "").strip()
    except Exception:
        pass
    return txt, ttl


def uc_pass(run, urls, store, max_restarts=12):
    """Visible-window pass.

    The browser dies mid-run often enough to plan for it - the window gets closed,
    Chrome updates, the driver session drops. Every later URL then fails instantly
    against a dead localhost port, so a single long-lived session silently burns
    the whole queue. Reopen instead, and only give up after `max_restarts`.
    """
    from urllib.parse import urlparse
    print(f"UC mode (fenetre visible): "
          f"{len([u for u in urls if not _have(store, u)])} a recuperer", flush=True)
    try:
        from seleniumbase import SB
    except ImportError:
        print("  seleniumbase absent - 'pip install seleniumbase'. Les colonnes de "
              "ces offres resteront vides plutot que devinees.", flush=True)
        return 0

    ok = 0
    hard = set()          # gave up on these, do not loop on them forever
    for attempt in range(max_restarts + 1):
        todo = [u for u in urls if not _have(store, u) and u not in hard]
        if not todo:
            break
        if attempt:
            print(f"  -- navigateur perdu, relance {attempt}/{max_restarts} "
                  f"({len(todo)} restantes)", flush=True)
        dead = False
        try:
            with SB(uc=True, headless=False, page_load_strategy="eager") as sb:
                for i, u in enumerate(todo, 1):
                    host = urlparse(u).netloc.replace("www.", "")
                    try:
                        txt, ttl = _one(sb, u, host)
                    except Exception as e:
                        name = type(e).__name__
                        if name in DEAD or "actively refused" in str(e):
                            dead = True
                            break
                        hard.add(u)
                        store[u] = {"text": "", "title": "", "ok": False, "err": name}
                        print(f"  {i}/{len(todo)} ERREUR {host} {name}", flush=True)
                        continue
                    store[u] = {"text": txt, "title": ttl,
                                "ok": len(txt) >= MIN_BODY}
                    if len(txt) >= MIN_BODY:
                        ok += 1
                    else:
                        hard.add(u)
                    print(f"  {i}/{len(todo)} "
                          f"{'OK' if len(txt) >= MIN_BODY else 'VIDE'} {host}",
                          flush=True)
                    if i % 10 == 0:
                        _save(run, store)
        except Exception as e:
            print(f"  session UC interrompue: {type(e).__name__}", flush=True)
            dead = True
        _save(run, store)
        if not dead:
            break
        time.sleep(4)
    if hard:
        print(f"  {len(hard)} offres sans texte exploitable - colonnes laissees "
              f"vides plutot que devinees", flush=True)
    return ok


def harvest(run, rows, uc=True):
    urls, seen = [], set()
    for r in rows:
        u = (r.get("url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    store = _load(run)
    have0 = sum(1 for u in urls if _have(store, u))
    print(f"{len(urls)} offres | {have0} ont deja leur texte integral", flush=True)
    http_pass(run, urls, store)
    if uc:
        uc_pass(run, urls, store)
    _save(run, store)
    have1 = sum(1 for u in urls if _have(store, u))
    print(f"texte integral: {have1}/{len(urls)} "
          f"({have1 - have0} recuperes cette fois)", flush=True)
    return store
