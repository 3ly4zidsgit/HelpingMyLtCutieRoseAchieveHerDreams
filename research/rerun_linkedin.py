"""Re-run the two LinkedIn steps on their own.

`Collector.push` passed contact_email twice - once as a keyword, once inside
**extra - so blank() raised TypeError on the first LinkedIn row. run.py catches
per step, so the run looked healthy while both LinkedIn phases lost everything
they had collected: 1 309 raw / 130 title-relevant for Morocco, 4 375 / 543 for
remote. Fixed in scrape.py; this replays just those two steps rather than the
whole two-hour scrape.

    python research/rerun_linkedin.py <spec.json>
"""
import sys, io, os, json, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run
import scrape

# copied, not imported: importing run.py re-wraps sys.stdout at module level and
# closes the wrapper this script is already printing through
MA_LOCS = ["Morocco", "Casablanca, Morocco", "Tangier, Morocco", "Rabat, Morocco",
           "Kenitra, Morocco", "Marrakesh, Morocco", "Agadir, Morocco", "Fes, Morocco",
           "Meknes, Morocco", "Oujda, Morocco", "Tetouan, Morocco", "El Jadida, Morocco"]
REMOTE_LOCS = ["European Union", "United States", "United Kingdom", "Worldwide", "Europe",
               "Remote", "France", "Canada", "Germany", "Spain", "Portugal", "Africa"]

run = Run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec.json"))
col = scrape.Collector(run)
for name, fn in [("LinkedIn Maroc", lambda: scrape.linkedin(run, col, MA_LOCS, False)),
                 ("LinkedIn Remote", lambda: scrape.linkedin(
                     run, col, REMOTE_LOCS, True, country="International",
                     label="LinkedIn (Remote)"))]:
    print(f"\n########## {name} ##########", flush=True)
    try:
        fn()
    except Exception:
        traceback.print_exc()
    run.save("raw_linkedin", col.rows)
print(f"\ntermine: {len(col.rows)} offres -> data/raw_linkedin.json")
