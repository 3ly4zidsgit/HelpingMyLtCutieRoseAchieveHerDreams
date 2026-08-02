"""Orchestrator.

  python run.py scrape  spec.json      # every source -> data/raw_*.json
  python run.py stage   spec.json      # emit remote_candidates.json for LLM review
  python run.py curate  spec.json      # emit curation_candidates.json for LLM review
  python run.py build   spec.json      # apply both verdict files + write/append the Excel

spec.json is written by the skill (see SKILL.md) and carries the specialty,
its keyword expansion, the relevance regexes and the output paths.
"""
import sys, io, os, json, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Run
import scrape
import build as B

MA_LOCS = ["Morocco", "Casablanca, Morocco", "Tangier, Morocco", "Rabat, Morocco",
           "Kenitra, Morocco", "Marrakesh, Morocco", "Agadir, Morocco", "Fes, Morocco",
           "Meknes, Morocco", "Oujda, Morocco", "Tetouan, Morocco", "El Jadida, Morocco"]
REMOTE_LOCS = ["European Union", "United States", "United Kingdom", "Worldwide", "Europe",
               "Remote", "France", "Canada", "Germany", "Spain", "Portugal", "Africa"]


def do_scrape(run):
    col = scrape.Collector(run)
    steps = [
        ("Rekrute", lambda: scrape.rekrute(run, col)),
        ("LinkedIn Maroc", lambda: scrape.linkedin(run, col, MA_LOCS, False)),
        ("LinkedIn Remote", lambda: scrape.linkedin(run, col, REMOTE_LOCS, True,
                                                    country="International",
                                                    label="LinkedIn (Remote)")),
        ("MarocAnnonces + Dreamjob", lambda: scrape.ma_boards(run, col)),
        ("ATS feeds", lambda: scrape.ats(run, col)),
        ("Worldwide remote boards", lambda: scrape.worldwide(run, col)),
    ]
    for name, fn in steps:
        print(f"\n########## {name} ##########", flush=True)
        try:
            fn()
        except Exception:
            traceback.print_exc()
        run.save("raw_http", col.rows)

    print("\n########## UC mode (Cloudflare-walled sources) ##########", flush=True)
    try:
        import scrape_uc
        uc = scrape.Collector(run)
        scrape_uc.run_uc(run, uc)
        run.save("raw_uc", uc.rows)
    except Exception:
        traceback.print_exc()
        print("  UC mode unavailable - continuing without the walled sources", flush=True)


def all_rows(run):
    rows = run.load("raw_http") + run.load("raw_uc")
    for extra in ("raw_extra",):
        rows += run.load(extra)
    return rows


def do_stage(run):
    """Everything outside Morocco needs a human/LLM ruling on 'really remote,
    really no visa'. Emit exactly what is needed to decide."""
    rows = B.finalize(all_rows(run))
    cand = [r for r in rows if r["country"] != "Maroc"]
    out = [{"id": i, "job_title": r["job_title"], "company": r["company"],
            "location": r["location_city"], "country": r["country"],
            "url": r["url"], "evidence": r["description_snippet"][:800]}
           for i, r in enumerate(cand)]
    p = os.path.join(run.datadir, "remote_candidates.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} international offers staged for review -> {p}")
    print("Write verdicts to data/remote_verdicts.json as "
          '[{"id": 0, "verdict": "OK"|"REJET", "reason": "..."}]')


def do_curate(run):
    """Regexes get you a shortlist, not a match. Emit every surviving offer so
    the model can read it and drop the ones that are not really this job."""
    rows = [r for r in B.finalize(all_rows(run)) if run.strict_keep(r)]
    out = [{"id": i, "job_title": r["job_title"], "company": r["company"],
            "sector": r.get("sector", ""), "function": r.get("function", ""),
            "country": r["country"], "url": r["url"],
            "description": r["description_snippet"][:700]}
           for i, r in enumerate(rows)]
    p = os.path.join(run.datadir, "curation_candidates.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"specialty: {run.specialty}")
    print(f"{len(out)} offers staged for relevance review -> {p}")
    print('Write data/curation_verdicts.json as '
          '[{"id": 0, "keep": true, "reason": "..."}]')


def do_build(run):
    rows = B.finalize(all_rows(run))
    rows = [r for r in rows if run.strict_keep(r)]

    # final relevance ruling by the model, if it has been produced
    cp = os.path.join(run.datadir, "curation_verdicts.json")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            keep = {v["id"]: v for v in json.load(f)}
        before = len(rows)
        rows = [r for i, r in enumerate(rows)
                if keep.get(i, {}).get("keep", True)]
        print(f"relevance curation: {before} -> {len(rows)} "
              f"({before - len(rows)} judged off-topic)")
    else:
        print("WARNING: no curation_verdicts.json - shipping the keyword shortlist "
              "unreviewed. Run 'curate' and rule on the offers first.")

    verdicts = {}
    vp = os.path.join(run.datadir, "remote_verdicts.json")
    if os.path.exists(vp):
        with open(vp, encoding="utf-8") as f:
            verdicts = {v["id"]: v for v in json.load(f)}
    intl = [r for r in rows if r["country"] != "Maroc"]
    for i, r in enumerate(intl):
        v = verdicts.get(i)
        if v:
            r["remote_verdict"] = "OK" if v["verdict"].upper().startswith("OK") else "REJET"
            r["remote_reason"] = v.get("reason", "")
    kept = sum(1 for r in intl if r.get("remote_verdict") == "OK")
    print(f"international: {len(intl)} reviewed -> {kept} confirmed fully remote / visa-free")
    B.build(rows, run.spec["excel_path"], previous=B.read_existing(run.spec["excel_path"]))


if __name__ == "__main__":
    cmd, spec = sys.argv[1], sys.argv[2]
    run = Run(spec)
    print(f"=== findmyprincessajob | {run.specialty} | {cmd} ===", flush=True)
    {"scrape": do_scrape, "stage": do_stage,
     "curate": do_curate, "build": do_build}[cmd](run)
