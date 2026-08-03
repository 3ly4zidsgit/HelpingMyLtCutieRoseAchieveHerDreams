"""Re-fetch the full ad text for the offers whose source refuses scripted HTTP.

Dreamjob and Emploi.ma sit behind Cloudflare, Optioncarriere blocks on IP
reputation, Bayt / Jooble / Indeed / MarocAnnonces refuse scripted clients. A
VISIBLE window clears all of them; headless clears none.

The logic lives in the skill (pipeline/fulltext.py) so a future run gets it for
free; this script only feeds it the url list from data/walled_urls.json.

Run: python fetch_walled.py [domain ...]
Resumable: an offer that already has a real body is never refetched.
"""
import sys, io, os, json, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))

import fulltext as F


class Run:
    """fulltext.py only ever asks for datadir."""
    datadir = os.path.join(ROOT, "data")


def main():
    with open(os.path.join(Run.datadir, "walled_urls.json"), encoding="utf-8") as f:
        walled = json.load(f)
    want = [d.lower() for d in sys.argv[1:]] or [d.lower() for d in walled]
    urls = [u for host, lst in walled.items() if host.lower() in want for u in lst]

    run = Run()
    store = F._load(run)
    print(f"{len(urls)} urls murees | "
          f"{sum(1 for u in urls if F._have(store, u))} deja recuperees", flush=True)
    F.uc_pass(run, urls, store)
    F._save(run, store)
    good = sum(1 for u in urls if F._have(store, u))
    print(f"TERMINE: {good}/{len(urls)} avec texte integral", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
