---
name: findmyprincessajob
description: Find real, currently-open job offers for a given specialty across Moroccan and international job boards, verify which remote roles are genuinely 100% remote with no visa or work-permit requirement, and deliver them as an Excel split by zone and by experience level (Maroc junior / Maroc expérimenté / Remote junior / Remote expérimenté). Several specialties can share one workbook, each on its own sheets. Adds to the existing workbook instead of overwriting it. Use when asked to find jobs, search job offers, refresh the job list, add a second kind of role to the workbook, or run findmyprincessajob for a specialty.
---

# findmyprincessajob

Takes one input — **the specialty** (e.g. "Génie Industriel / Lean Six Sigma",
"Data Engineering", "Supply Chain") — and produces a verified, deduplicated
Excel of currently-open offers.

Four things make this more than a scraper, and you must actually do all four:

1. **You expand the specialty into a real keyword set** (FR + EN, job titles as
   employers actually word them), and you write the relevance regexes.
2. **You personally rule on every international offer** — is it truly 100%
   remote, with no visa, work permit, residency or on-site requirement? This is
   a reading task, not a regex task. Never delegate it to a pattern.
3. **You personally rule on relevance, at the end, offer by offer.** The
   regexes produce a shortlist, not a match. Before the workbook is written you
   read each surviving offer and drop everything that is not really this job.
   A workbook of 200 offers where 60 are off-topic is worse than 140 that all
   fit — every bad row costs a real application.
4. **You fill the columns by reading the ad**, not by trusting the board's own
   metadata. LinkedIn writes "Non pertinent" where the body says "Minimum 5
   years"; Rekrute shows "Confirmé (5 à 10 ans)" on a post open to new
   graduates; the employer column often holds the name of the job board. A
   column filled from the listing card is wrong often enough to mislead.

## Step 1 — Build the spec

Ask the user for the specialty if it was not given. Then write
`<outdir>/spec.json`:

```json
{
  "specialty": "Génie Industriel / Lean Six Sigma",
  "outdir":     "C:/Users/pc/Desktop/Emploi",
  "excel_path": "C:/Users/pc/Desktop/Emploi/Offres_Emploi_Genie_Industriel_Lean_2026.xlsx",
  "queries_fr": ["lean", "amelioration continue", "six sigma", "genie industriel", "..."],
  "queries_en": ["continuous improvement", "operational excellence", "industrial engineer", "..."],
  "strong":  ["\\blean\\b", "\\bsix ?sigma\\b", "\\bamelioration continue\\b"],
  "medium":  ["\\bingenieur methodes?\\b", "\\bsupply chain\\b"],
  "context": ["\\bindustri", "\\busine\\b", "\\bproduction\\b", "\\bqualite\\b"],
  "offdomain": ["\\bd[ée]veloppeur\\b", "\\bcomptab", "\\bcommercial\\b"],
  "exclude_titles": ["\\btechniciens?\\b", "\\btechnicians?\\b", "\\bstagiaires?\\b"],
  "publish_dir": "G:/My Drive/Emploi Rose"
}
```

Rules that matter:

- **`strong`** = terms that, in a *title*, are proof on their own. In a body
  they score less, because "amélioration continue" and "excellence
  opérationnelle" are filler in nearly every French ad.
- **`medium`** = adjacent titles that only count with industrial context.
- **`offdomain`** = other trades (IT, finance, sales, HR, health…). A body-only
  keyword hit on such a title gets dropped. Without this the list fills with
  developers whose ads happen to say "amélioration continue".
- **`exclude_titles`** = whatever the user never wants to see. This is a standing
  rule, so `build` applies it to rows already in the workbook too, not only to
  the fresh scrape. **Write the plural**: `\bstagiaire\b` leaves every
  "Stagiaires Génie Industriel" in place.
- **`track`** / **`datadir`** / **`applied_path`** / **`morocco_only`** /
  **`sources`** / **`offdomain_hard`** / **`ats`** = the keys that let a second
  search share one workbook. All optional; all documented in
  `references/TRACKS.md`. `datadir` stops being optional the moment `track` is
  set, because every verdict filename is a global constant.
- **`publish_dir`** (optional) = a synced folder (Google Drive Desktop, OneDrive)
  the workbook is copied to after every build. An emailed attachment is frozen at
  the moment it was sent; a link into a synced folder shows the current file. Use
  this when the user shares the workbook with someone.
- Regexes run against accent-stripped lowercase text: write `amelioration`, not
  `amélioration`. **Always use `\b` boundaries** — without them "professional"
  matches "fes" and "sales" matches "sale".

## Step 2 — Scrape

```bash
cd <skill>/pipeline
python run.py scrape <outdir>/spec.json
```

Runs ~20 minutes. A **visible Chrome window will open** near the end — UC mode
needs a real window to clear Cloudflare. Do not close it. Run it in the
background and report numeric progress as it goes.

Sources and their access route are listed in `references/SOURCES.md`. Read that
file before adding or debugging a source — it records which sites need which
technique and which are dead, so you do not re-derive it.

## Step 3 — Fetch the full ad text

```bash
python run.py fulltext <outdir>/spec.json
```

The scrapers keep only what the listing card showed (~700 characters). The
experience requirement, the contract type and often the real employer are in the
body of the ad. Skip this and the `enrich` step has nothing to read, so those
columns come out empty or carry a value the board invented — LinkedIn stamps
"Non pertinent" on ads that never stated a level, Rekrute shows its own bucket
("Confirmé 5 à 10 ans") on ads whose text asks for 1 to 3 years.

Two passes, both resumable: plain HTTP for LinkedIn / Rekrute / SmartRecruiters
and the ATS hosts, then UC mode for the walled boards. **The UC pass opens a
visible Chrome window** — Dreamjob and Emploi.ma sit behind Cloudflare,
Optioncarriere blocks on IP reputation, Bayt / Jooble / Indeed / MarocAnnonces
refuse scripted clients. Headless does not clear any of them. Leave the window
alone; it takes ~10 s per offer.

Rows already in the workbook are included, not just the fresh scrape — they came
back through `read_existing` and were never in `raw_*.json`.

## Step 4 — Rule on the remote offers (the part only you can do)

```bash
python run.py stage <outdir>/spec.json
```

This writes `data/remote_candidates.json`: every non-Moroccan offer with its
description. **Read them.** For each, decide whether someone applying *from
Morocco, with no work permit and no relocation*, could actually hold the job.

Reject on any of: "must be located/based in", "authorized to work in",
"right to work", "work permit", "visa sponsorship", "US citizen",
"security clearance", hybrid, on-site, relocation, or a country-scoped remote
("Remote - Ontario", "fully remote across Canada").

Accept only when the ad itself is open worldwide, or is a freelance/contract
engagement with no location condition. **When the ad is silent about
eligibility, reject it** — silence is not permission, and a false positive
wastes a real application.

Write `data/remote_verdicts.json`:

```json
[{"id": 0, "verdict": "OK",    "reason": "'Work from anywhere in the world' - no visa clause"},
 {"id": 1, "verdict": "REJET", "reason": "'must be authorized to work in the US'"}]
```

Quote the ad's own words in `reason`. That text becomes a column in the Excel,
so the user can check your judgement instead of trusting it.

Expect very few to pass in field-based specialties: Lean, industrial and
manufacturing work happens on a shop floor. A single-digit result is the honest
answer, not a failure — say so plainly rather than loosening the bar.

## Step 5 — Rule on relevance (the second thing only you can do)

```bash
python run.py curate <outdir>/spec.json
```

Writes `data/curation_candidates.json`: every offer that survived the automated
filters, with its title, company, sector, function and description. **Read them
against the specialty** and decide, one by one, whether this is genuinely the
job the user is looking for.

Keyword matching cannot do this. It cannot tell that:

- "Ingénieur Qualité Logiciel" is QA testing, not industrial quality;
- "Operations Manager - BPO" is call-centre staffing, not operational excellence;
- "Lean 4 & Formal Proof Systems" is a theorem prover, not Lean manufacturing;
- "Chef de Projet IT (Agile SCRUM, KANBAN)" is software delivery, not shop-floor
  Kanban;
- "Process Engineer" in a bank is not the same trade as in a factory.

All five pass a keyword filter. Only reading catches them.

Judge the **role**, not the vocabulary: would someone with this specialty
plausibly be hired into it and do that work day to day? Adjacent-but-real roles
stay (a Méthodes or Industrialisation post for a Lean profile). Same-word,
different-trade roles go.

Write `data/curation_verdicts.json`:

```json
[{"id": 0, "keep": true,  "reason": "Lean/CI engineer in an automotive plant - core match"},
 {"id": 1, "keep": false, "reason": "'Quality Engineer' but software QA/test automation"}]
```

Ids are the positions in `curation_candidates.json`. Any id you omit defaults to
kept, so cover them all. If `curation_verdicts.json` is missing, `build` warns
and ships the unreviewed keyword shortlist — do not let that be the outcome.

## Step 6 — Fill the columns by reading (the third thing only you can do)

```bash
python run.py enrich <outdir>/spec.json
```

Writes `data/field_candidates.json`: for every shipping offer, the columns as
they currently stand, the full ad body, and the sentences that carry an
experience or contract statement. **Read the body and fill the columns from what
the ad actually says**, not from what the board's own metadata claims.

What only reading catches:

- LinkedIn's "Niveau hiérarchique : Non pertinent" on an ad whose text says
  *"Minimum 5 years"* — the level was never absent, only unread;
- a Rekrute card showing *"Confirmé (5 à 10 ans)"* on an ad whose body opens the
  post *"de la sortie d'études à 6 ans"*, i.e. accessible to a new graduate;
- "Rekrute", "Dreamjob" or "LinkedIn" sitting in the employer column — that is
  the board, not the company. The real name is in the body or the logo alt text;
- an ad reproducing another group's corporate boilerplate word for word, posted
  under a client's name;
- *"Les candidatures ne sont plus acceptées"* — the offer is closed, mark it in
  `deadline` instead of letting the user apply to nothing.

Write `data/field_verdicts.json`, keyed by `key` (never by position):

```json
[{"key": "457cc51f74df", "company": "STMicroelectronics",
  "experience_required": "5 ans", "seniority_bucket": "Experimente",
  "contract_type": "CDI", "sector": "Semi-conducteurs", "city": "Casablanca",
  "reason": "'Vous justifiez d'une expérience de 5 ans dans un poste similaire'"}]
```

A field that is **present overwrites**, even when its value is empty — that is
how a wrong value gets cleared. A field that is **absent** leaves the column
untouched. Leave a field empty rather than guessing: an empty cell is the correct
answer when the ad published nothing.

Write `experience_required` as the ad words it, floor first: `1 à 3 ans`,
`3 ans minimum`, `0 à 2 ans`, `0`. Do **not** set `seniority_bucket` to force a
sheet — `build.exp_floor` derives the sheet from this string, and a bucket that
contradicts it loses. Set the bucket only when the ad states a level but no
duration at all.

When a source refuses its detail page, the ad is usually already in the list
under its real source. Match on title + employer + city, then check that the
aggregator card's vocabulary actually appears in the other ad's body before
copying anything, and name the URL you copied from in `reason`. That is reading
the same ad on a board that published more, which is what the offer being on two
or three boards is for. What the aggregator prints on its own card — employer,
city, posting age — is published data and can be used directly; the rest of the
row stays empty.

`build` applies these rulings to the rows recovered from the existing workbook as
well, so a correction sticks across runs.

## Step 7 — Build the Excel

```bash
python run.py build <outdir>/spec.json
```

Reads any existing workbook at `excel_path`, merges the new rows into it,
deduplicates on URL then title+company, and rewrites the four sheets:

| Sheet | Track | Contents |
|---|---|---|
| MAROC - JUNIOR | lean | Morocco, experience floor is zero or the ad is silent |
| MAROC - AVEC EXPERIENCE | lean | Morocco, the ad demands a non-zero floor |
| REMOTE - JUNIOR | lean | verdict OK, junior |
| REMOTE - AVEC EXPERIENCE | lean | verdict OK, experienced |
| COMMERCIAL & CONSEIL - JUNIOR | business | Morocco, floor zero or silent |
| COMMERCIAL & CONSEIL - AVEC EXP | business | Morocco, non-zero floor |

One workbook can carry several searches. A **track** is one spec.json with its
own keywords, regexes, verdict files and sheets — see
`references/TRACKS.md` before adding or building one. The short version: a second
track needs `"track"`, its own `"datadir"`, a shared `"applied_path"`, and
`"offdomain_hard": true`; and `do_build` sets the other track's rows aside before
the three steps that would otherwise delete them.

**The list only grows.** Back up the workbook to `<outdir>/backup/` with a
timestamp before running build.

Three rules `build` enforces on every run, on the fresh scrape *and* on the rows
recovered from the workbook. They are code, not a one-off cleanup:

- **A closed offer never ships.** `build.is_closed` drops any row whose date
  columns carry a closure that was *read on the page* — "cette offre a expiré",
  "candidatures fermées", a closing date the ad itself puts in the past. An ad
  that is merely **old** is kept: nobody established that it is closed, and
  "annonce publiée il y a 2 ans - vérifier qu'elle est toujours ouverte" is a
  warning, not a closure.
- **The sheet is decided by the FLOOR, never by the ceiling.** `build.exp_floor`
  returns the minimum the ad demands, in years: `0` when it explicitly takes
  someone with none, `>0` when it demands some, `None` when it is silent.
  JUNIOR means floor `0`. So `0 à 3 ans`, `de la sortie d'études à 6 ans`,
  `jeune diplômé jusqu'à 3 ans` and `junior (2 ans maximum)` are junior — every
  one of them contains a number, and every one of them puts it at the *top* of
  the range. `6 mois`, `1 an minimum` and `1 à 3 ans` are not. The floor
  outranks a `seniority_bucket` the model locked in, because that is exactly
  where the old mistake came from. A **silent** ad is not a zero-floor ad: it
  keeps `None` and falls through to the existing logic rather than being called
  junior on a guess.
- **"Open to beginners" is written as a number.** `build.normalize_exp` rewrites
  every zero-floor phrasing — "Débutant accepté", "Jeune diplômé", "Fraîchement
  diplômé(e)" — as `0`, keeping the ceiling when the ad gave one (`0 à 3 ans`)
  and any real qualifier (`0 (stage PFE apprécié)`). It only fires when the ad
  said it. A silent ad keeps its empty cell — **never write 0 by default.**

### The "Postulé" column

First column, dark blue, a one-item dropdown holding a tick. It is the only
column the pipeline never writes into: the user ticks it herself once she has
applied. Ticking greys the whole line out live in Excel (conditional formatting
on `$A3`), so a sent application stops competing for attention without
disappearing. `read_existing` reads the ticks back, and `do_build` also mirrors
them into `data/applied.json` keyed by URL, so they survive a workbook rebuilt
from scratch — not just an append.

## Step 8 — Report

Give numbers: rows added, new total per sheet, sources that contributed, and
sources that failed this run. State how many offers you judged off-topic and how
many international offers survived the remote/visa review, with a typical
rejection quote for each.

## Verify before claiming success

- Open the workbook and confirm sheet names, row counts and that offer links are
  clickable hyperlinks.
- Spot-check a few links. **403 from a script is not a dead link** — Bayt,
  Indeed, Jooble and Jobicy block scripted requests but open fine in a browser;
  confirm with UC mode before reporting a link as broken.
- Never invent an offer, a company, an email or a contact name. Every row must
  trace to a URL that was actually fetched. An empty cell is correct when the
  source published nothing.
