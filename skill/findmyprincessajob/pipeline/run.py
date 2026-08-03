"""Orchestrator.

  python run.py scrape  spec.json      # every source -> data/raw_*.json
  python run.py stage   spec.json      # emit remote_candidates.json for LLM review
  python run.py curate  spec.json      # emit curation_candidates.json for LLM review
  python run.py enrich  spec.json      # emit field_candidates.json for LLM field-filling
  python run.py build   spec.json      # apply both verdict files + write/append the Excel

spec.json is written by the skill (see SKILL.md) and carries the specialty,
its keyword expansion, the relevance regexes and the output paths.
"""
import sys, io, os, re, json, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Run, jid
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


def curated(run):
    """The row set `build` will actually ship: automated filters, then the
    model's own relevance ruling if it has already been made."""
    rows = [r for r in B.finalize(all_rows(run)) if run.strict_keep(r)]
    cp = os.path.join(run.datadir, "curation_verdicts.json")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            keep = _by_key(json.load(f), rows)
        rows = [r for i, r in enumerate(rows)
                if keep.get(jid(r["url"]), keep.get(i, {})).get("keep", True)]
    return rows


def _by_key(verdicts, rows):
    """Verdict files are keyed by url hash; fall back to positional ids for
    files written before the key existed."""
    out = {}
    for v in verdicts:
        if v.get("key"):
            out[v["key"]] = v
        elif "id" in v:
            out[v["id"]] = v
    return out


def do_stage(run):
    """Everything outside Morocco needs a human/LLM ruling on 'really remote,
    really no visa'. Emit exactly what is needed to decide."""
    cand = [r for r in curated(run) if r["country"] != "Maroc"]
    out = [{"id": i, "key": jid(r["url"]),
            "job_title": r["job_title"], "company": r["company"],
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
    out = [{"id": i, "key": jid(r["url"]),
            "job_title": r["job_title"], "company": r["company"],
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


EXP_RE = re.compile(
    r"[^.\n]{0,140}(?:\b\d{1,2}\s*(?:\+|a|à|-|to)?\s*\d{0,2}\s*(?:ans?|ann[ée]es?|years?|yrs?)\b"
    r"|minimum\s*\d|au moins\s*\d|d[ée]butant|junior|senior|confirm[ée]|exp[ée]riment[ée]"
    r"|fraichement diplom|jeune diplom|entry[- ]level|niveau d.exp[ée]rience)[^.\n]{0,140}", re.I)
CTR_RE = re.compile(r"[^.\n]{0,90}\b(cdi|cdd|stage|alternance|apprentissage|freelance|int[ée]rim"
                    r"|temps plein|temps partiel|full[- ]time|part[- ]time|permanent|contract)\b"
                    r"[^.\n]{0,90}", re.I)


def do_enrich(run):
    """Third reading gate. The scrapers only ever saw the listing card, so most
    of 'Experience requise', 'Type de contrat', 'Secteur' and even 'Entreprise'
    came out empty or wrong. This stages the FULL ad text plus the sentences that
    actually carry the answer, so the model fills the columns by reading."""
    ftp = os.path.join(run.datadir, "fulltext.json")
    full = json.load(open(ftp, encoding="utf-8")) if os.path.exists(ftp) else {}
    rows = [r for r in curated(run)]
    out, missing = [], 0
    for i, r in enumerate(rows):
        u = r["url"]
        txt = (full.get(u) or {}).get("text", "")
        if not txt:
            missing += 1
        body = re.sub(r"\s+", " ", txt or r.get("description_snippet", ""))
        out.append({
            "id": i, "key": jid(u), "url": u,
            "job_title": r["job_title"],
            "current": {"company": r.get("company", ""),
                        "experience_required": r.get("experience_required", ""),
                        "seniority_bucket": r.get("seniority_bucket", ""),
                        "contract_type": r.get("contract_type", ""),
                        "location_city": r.get("location_city", ""),
                        "sector": r.get("sector", ""), "function": r.get("function", "")},
            "has_fulltext": bool(txt),
            "evidence_experience": [m.group(0).strip() for m in EXP_RE.finditer(body)][:6],
            "evidence_contract": [m.group(0).strip() for m in CTR_RE.finditer(body)][:4],
            "text": body[:2600],
        })
    p = os.path.join(run.datadir, "field_candidates.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} offres a enrichir -> {p}")
    print(f"  dont {len(out) - missing} avec le texte integral, {missing} sans "
          f"(sources murees - lancer fetch_fulltext)")
    print('Write data/field_verdicts.json as [{"key": "...", "company": "...", '
          '"experience_required": "...", "seniority_bucket": "Junior|Experimente|Non precise", '
          '"contract_type": "...", "sector": "...", "function": "...", "city": "..."}]')


def apply_fields(run, rows):
    """Overlay the model's field rulings. A key that is PRESENT overwrites, even
    when empty - that is how a wrong value gets cleared (LinkedIn stamps
    "Non pertinent" on ads that never stated a level). A key that is absent
    leaves the column untouched."""
    fp = os.path.join(run.datadir, "field_verdicts.json")
    if not os.path.exists(fp):
        return 0
    with open(fp, encoding="utf-8") as f:
        v = {x["key"]: x for x in json.load(f) if x.get("key")}
    n = 0
    for r in rows:
        d = v.get(jid(r["url"]))
        if not d:
            continue
        n += 1
        for src, dst in (("company", "company"), ("experience_required", "experience_required"),
                         ("contract_type", "contract_type"), ("sector", "sector"),
                         ("function", "function"), ("city", "location_city")):
            if src in d:
                r[dst] = d[src]
        if d.get("seniority_bucket"):
            r["seniority_bucket"] = d["seniority_bucket"]
            r["seniority_locked"] = True
    return n


def do_build(run):
    before = len([r for r in B.finalize(all_rows(run)) if run.strict_keep(r)])
    rows = curated(run)
    cp = os.path.join(run.datadir, "curation_verdicts.json")
    if os.path.exists(cp):
        print(f"relevance curation: {before} -> {len(rows)} "
              f"({before - len(rows)} judged off-topic)")
    else:
        print("WARNING: no curation_verdicts.json - shipping the keyword shortlist "
              "unreviewed. Run 'curate' and rule on the offers first.")

    nf = apply_fields(run, rows)
    if nf:
        print(f"champs renseignes par lecture du modele: {nf} offres")

    verdicts = {}
    vp = os.path.join(run.datadir, "remote_verdicts.json")
    if os.path.exists(vp):
        with open(vp, encoding="utf-8") as f:
            verdicts = _by_key(json.load(f), rows)
    intl = [r for r in rows if r["country"] != "Maroc"]
    for i, r in enumerate(intl):
        v = verdicts.get(jid(r["url"]), verdicts.get(i))
        if v:
            r["remote_verdict"] = "OK" if v["verdict"].upper().startswith("OK") else "REJET"
            r["remote_reason"] = v.get("reason", "")
    kept = sum(1 for r in intl if r.get("remote_verdict") == "OK")
    print(f"international: {len(intl)} reviewed -> {kept} confirmed fully remote / visa-free")

    # Rows already in the workbook were written before these gates existed, and
    # read_existing re-approves every remote one on sight. Hold them to the same
    # ruling, or a row the model has judged off-topic survives forever.
    previous = B.read_existing(run.spec["excel_path"])
    rejected = set()
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            rejected |= {v["key"] for v in json.load(f)
                         if v.get("key") and not v.get("keep", True)}
    if os.path.exists(vp):
        with open(vp, encoding="utf-8") as f:
            rejected |= {v["key"] for v in json.load(f)
                         if v.get("key") and not v["verdict"].upper().startswith("OK")}
    if rejected:
        n = len(previous)
        previous = [r for r in previous if jid(r.get("url", "")) not in rejected]
        print(f"existing rows re-checked against both gates: {n} -> {len(previous)} "
              f"({n - len(previous)} dropped)")

    # exclude_titles is a standing user rule ("never show me these"), so it has to
    # reach rows already in the workbook as well, not just newly scraped ones.
    n = len(previous)
    previous = [r for r in previous
                if not any(p.search(B.norm(r.get("job_title", ""))) for p in run._exclude)]
    if n != len(previous):
        print(f"existing rows dropped on exclude_titles: {n - len(previous)}")

    # dedupe keeps the first row it sees for a URL and only fills its blanks, so a
    # stale value already in the workbook would outrank the corrected one. Apply
    # the field rulings to the recovered rows too.
    if apply_fields(run, previous):
        print("field rulings also applied to the recovered workbook rows")
    B.build(rows, run.spec["excel_path"], previous=previous,
            publish_dir=run.spec.get("publish_dir"))


if __name__ == "__main__":
    cmd, spec = sys.argv[1], sys.argv[2]
    run = Run(spec)
    print(f"=== findmyprincessajob | {run.specialty} | {cmd} ===", flush=True)
    {"scrape": do_scrape, "stage": do_stage, "curate": do_curate,
     "enrich": do_enrich, "build": do_build}[cmd](run)
