"""Orchestrator.

  python run.py scrape   spec.json     # every source -> data/raw_*.json
  python run.py fulltext spec.json     # fetch each ad's FULL body -> data/fulltext.json
  python run.py stage    spec.json     # emit remote_candidates.json for LLM review
  python run.py curate   spec.json     # emit curation_candidates.json for LLM review
  python run.py enrich   spec.json     # emit field_candidates.json for LLM field-filling
  python run.py build    spec.json     # apply both verdict files + write/append the Excel

`fulltext` must run before `enrich`: the scrapers only keep the listing card, and
a column filled from a card is empty or wrong more often than not.

spec.json is written by the skill (see SKILL.md) and carries the specialty,
its keyword expansion, the relevance regexes and the output paths.
"""
import sys, io, os, re, json, traceback
# only wrap a stdout that is not already wrapped: importing this module from
# another script would otherwise re-wrap - and close - the wrapper that script is
# printing through, killing it with "I/O operation on closed file"
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
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
    all_steps = [
        ("rekrute", "Rekrute", lambda: scrape.rekrute(run, col)),
        ("linkedin_ma", "LinkedIn Maroc", lambda: scrape.linkedin(run, col, MA_LOCS, False)),
        ("linkedin_remote", "LinkedIn Remote",
         lambda: scrape.linkedin(run, col, REMOTE_LOCS, True, country="International",
                                 label="LinkedIn (Remote)")),
        ("ma_boards", "MarocAnnonces + Dreamjob", lambda: scrape.ma_boards(run, col)),
        ("ats", "ATS feeds", lambda: scrape.ats(run, col)),
        ("worldwide", "Worldwide remote boards", lambda: scrape.worldwide(run, col)),
    ]
    # A Morocco-only track has no business spending an hour on the two
    # international steps, and every row they would return is one the router will
    # refuse anyway.
    want = run.spec.get("sources")
    steps = [(lab, fn) for key, lab, fn in all_steps if not want or key in want]
    if want:
        skipped = [k for k, _, _ in all_steps if k not in want]
        if skipped:
            print(f"sources ignorees pour cette piste: {', '.join(skipped)}", flush=True)
    for name, fn in steps:
        print(f"\n########## {name} ##########", flush=True)
        try:
            fn()
        except Exception:
            traceback.print_exc()
        run.save("raw_http", col.rows)

    if want and "uc" not in want:
        print("\nUC mode ignore pour cette piste (absent de spec['sources'])", flush=True)
        return
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
    """Every raw_*.json in data/, not a hard-coded three.

    `scrape` overwrites raw_http.json, so a corpus merged by hand once sat there
    waiting to be destroyed by the next run. Globbing means a rescued corpus, or a
    single source re-run on its own, is picked up by dropping the file in - no
    edit here, nothing to forget."""
    import glob
    rows = []
    for p in sorted(glob.glob(os.path.join(run.datadir, "raw_*.json"))):
        with open(p, encoding="utf-8") as f:
            rows += json.load(f)
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
    if run.spec.get("morocco_only"):
        # and do NOT write remote_verdicts.json: do_build re-checks the recovered
        # workbook rows against that file, so an empty one would start deleting
        # rows that never needed a visa ruling in the first place.
        print("piste Maroc uniquement - aucun arbitrage visa a rendre")
        return
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


_REMOTE_OK = {}


def _remote_ok(run):
    """{key: True} for the international offers the visa gate has passed. An offer
    that carries no verdict is absent, and absent means "cannot ship" - the gate's
    own rule is that silence is a rejection."""
    if run.track not in _REMOTE_OK:
        p = os.path.join(run.datadir, "remote_verdicts.json")
        v = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
        _REMOTE_OK[run.track] = {x["key"]: True for x in v
                                 if x.get("key") and str(x.get("verdict", "")).upper().startswith("OK")}
    return _REMOTE_OK[run.track]


def shipping(run):
    """Every row of THIS track that will end up in the workbook: the curated
    scrape plus the rows recovered from the existing workbook. Those came back
    through read_existing and were never in raw_*.json, so any step that sources
    its list from the scrape alone silently skips them.

    The track filter matters: without it, `fulltext` and `enrich` on a second spec
    would re-download and re-stage the other track's whole workbook, and put those
    ads in front of the model under the wrong specialty.

    The visa gate matters just as much. `curated` treats an offer with no verdict
    as kept, which is right for the relevance gate but wrong here: an international
    row can only reach a sheet with an explicit remote verdict of OK. Without this
    filter, `enrich` staged 2 799 offers for a track that ships 288, and `fulltext`
    would have downloaded every one of them."""
    rows = [r for r in curated(run) if r["country"] == "Maroc"
            or _remote_ok(run).get(jid(r["url"]))]
    seen = {r["url"] for r in rows}
    for r in B.read_existing(run.spec["excel_path"]):
        if r.get("track", B.DEFAULT_TRACK) != run.track:
            continue
        u = (r.get("url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            rows.append(r)
    return rows


def do_fulltext(run):
    import fulltext as F
    F.harvest(run, shipping(run))


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
    rows = shipping(run)
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
            # 'deadline' fait partie de l'etat courant: sans lui, un script
            # d'enrichissement croit la colonne vide et re-extrait 113 dates deja
            # presentes, ce qui ressemble a un gain et n'en est pas un.
            "current": {"deadline": r.get("deadline", ""),
                        "company": r.get("company", ""),
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
          '"contract_type": "...", "sector": "...", "function": "...", "city": "...", '
          '"deadline": "JJ/MM/AAAA"}]')


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
                         ("function", "function"), ("city", "location_city"),
                         ("deadline", "deadline")):
            if src in d:
                r[dst] = d[src]
        if d.get("seniority_bucket"):
            r["seniority_bucket"] = d["seniority_bucket"]
            r["seniority_locked"] = True
    return n


LI_CHROME = re.compile(
    r"Inscrivez-vous pour postuler|Mot de passe oubli|S.identifier avec|Politique de confidentialit"
    r"|Utilisez l.IA pour|Personnaliser mon CV|Identifiez-vous pour|D[ée]couvrez qui .{0,60}a recrut"
    r"|Les recommandations augmentent|Voir qui vous connaissez|Signaler cette offre|Show more Show less"
    r"|Plus de \d+ candidats|Faites partie des \d+ premiers", re.I)


def _bodies(run):
    """{url: full ad text} for every body this track has fetched, both tracks'
    files unioned - a closure read on one track's copy of an ad closes it on the
    other too, and the two tracks do republish the same offer."""
    out = {}
    for d in {run.datadir, os.path.join(run.outdir, "data")}:
        p = os.path.join(d, "fulltext.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for u, v in json.load(f).items():
                    if v.get("text"):
                        out.setdefault(u, v["text"])
    return out


def fill_descriptions(run, rows):
    """A row whose Description cell is empty while its body sits in fulltext.json.

    It happens when the board served the listing card but not the ad, and the body
    only arrived later. The text is the ad's own - nothing is being invented, it
    was simply fetched after the column had been filled."""
    ftp = os.path.join(run.datadir, "fulltext.json")
    if not os.path.exists(ftp):
        return 0
    with open(ftp, encoding="utf-8") as f:
        full = json.load(f)
    n = 0
    for r in rows:
        if len((r.get("description_snippet") or "").strip()) >= 60:
            continue
        body = (full.get(r.get("url", "")) or {}).get("text", "")
        if not body:
            continue
        txt = " ".join(s for s in re.split(r"\s*\n\s*", body) if not LI_CHROME.search(s))
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) >= 60:
            r["description_snippet"] = txt[:800]
            n += 1
    return n


def _check_isolation(run):
    """A second track pointed at the first one's data/ overwrites its verdicts on
    the first curate. Say so loudly rather than lose 683 rulings quietly."""
    default = os.path.normpath(os.path.join(run.outdir, "data"))
    if run.track != B.DEFAULT_TRACK and os.path.normpath(run.datadir) == default:
        print("!" * 74)
        print(f"! ATTENTION: piste '{run.track}' mais datadir = {run.datadir}")
        print("! Les fichiers de verdict de l'autre piste vont etre ecrases.")
        print("! Ajouter \"datadir\" au spec avant de continuer.")
        print("!" * 74, flush=True)


def do_build(run):
    _check_isolation(run)
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

    # ...but only the rows of THIS track. The other track's rows were judged by
    # another spec, with other keywords and other verdict files; re-judging them
    # here deletes them. That is not hypothetical: the Lean curation file already
    # says keep:false for a dozen Moroccan commercial offers, precisely because
    # they were off-topic FOR LEAN. Left unpartitioned, every Lean build would
    # quietly erase the commercial sheets.
    foreign = [r for r in previous if r.get("track", B.DEFAULT_TRACK) != run.track]
    previous = [r for r in previous if r.get("track", B.DEFAULT_TRACK) == run.track]
    if foreign:
        print(f"autre(s) piste(s): {len(foreign)} lignes reprises telles quelles, "
              f"sans repasser par les regles de ce spec")

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

    # The "Postule" ticks are the only thing in the workbook the user writes
    # herself, so they are also the only thing a rebuild could destroy. Mirror
    # them into data/applied.json, keyed by URL, and re-apply from there: the tick
    # then survives a workbook rebuilt from scratch, not just an append.
    # A tick belongs to the workbook, not to a search, so every track reads and
    # writes the same file and every track's rows get the mark re-applied.
    ap = run.applied_path
    os.makedirs(os.path.dirname(ap) or ".", exist_ok=True)
    marks = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else {}
    for r in list(previous) + list(foreign):
        if B.is_applied(r.get("applied")):
            marks[r["url"]] = B.TICK
    for r in list(rows) + list(previous) + list(foreign):
        if marks.get(r.get("url")):
            r["applied"] = B.TICK
    with open(ap, "w", encoding="utf-8") as f:
        json.dump(marks, f, ensure_ascii=False, indent=1)
    if marks:
        print(f"candidatures deja envoyees (cochees): {len(marks)} - lignes grisees, conservees")

    # A closed offer is not a lead. Reading an ad and finding "cette offre n'est
    # plus d'actualite" is a permanent verdict, so it is filtered here on every
    # build - both on the fresh scrape and on the rows recovered from the
    # workbook - and not cleaned out by hand once. An ad that is merely OLD is
    # kept: nobody has established that it is closed.
    nd = fill_descriptions(run, rows) + fill_descriptions(run, previous)
    if nd:
        print(f"colonne Description completee depuis le corps deja telecharge: {nd} offres")

    # closure is not a matter of specialty: a closed offer must never ship,
    # whichever track found it. The check reads the date columns AND the fetched
    # ad body, because a board that expires an ad does not always say so in a
    # field - Optioncarriere answers 200 with a banner in the page itself.
    bodies = _bodies(run)

    def closed(r):
        return B.is_closed(r, bodies.get((r.get("url") or "").strip(), ""))

    n, m, o = len(rows), len(previous), len(foreign)
    rows = [r for r in rows if not closed(r)]
    previous = [r for r in previous if not closed(r)]
    foreign = [r for r in foreign if not closed(r)]
    closed = (n - len(rows)) + (m - len(previous)) + (o - len(foreign))
    if closed:
        print(f"offres fermees ecartees (annonce lue comme expiree): {closed}")

    previous = previous + foreign
    B.build(rows, run.spec["excel_path"], previous=previous,
            publish_dir=run.spec.get("publish_dir"))


if __name__ == "__main__":
    cmd, spec = sys.argv[1], sys.argv[2]
    run = Run(spec)
    print(f"=== findmyprincessajob | {run.specialty} | {cmd} ===", flush=True)
    {"scrape": do_scrape, "fulltext": do_fulltext, "stage": do_stage,
     "curate": do_curate, "enrich": do_enrich, "build": do_build}[cmd](run)
