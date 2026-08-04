"""Replay just the ATS step, into its own raw_ file.

The employers a track cares about change more often than the rest of the
pipeline, and a running scrape holds the module it loaded at start - so adding a
slug mid-run has no effect on it. This re-runs the one step and drops the result
next to the others, where all_rows() globs it up.

    python research/rerun_ats.py [spec.json]
"""
import sys, io, os, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run
import scrape

run = Run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec_business.json"))
col = scrape.Collector(run)
print(f"piste {run.track} | flux ATS declares par le spec: "
      f"{ {k: len(v) for k, v in (run.spec.get('ats') or {}).items()} }", flush=True)
try:
    scrape.ats(run, col)
except Exception:
    traceback.print_exc()
run.save("raw_ats", col.rows)
print(f"{len(col.rows)} offres ATS retenues -> {run.datadir}/raw_ats.json")
for r in col.rows[:25]:
    print(f"  {r['source'][:30]:32s} {r['job_title'][:52]:54s} {r.get('location_city','')[:20]}")
