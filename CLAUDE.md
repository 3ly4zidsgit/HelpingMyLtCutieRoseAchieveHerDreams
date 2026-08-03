# CLAUDE.md — project state and how to resume

Job-hunting pipeline for **Génie Industriel / Lean Six Sigma / Amélioration
Continue / Excellence Opérationnelle** (Morocco + genuinely visa-free remote).

**Owner:** intern at DICE (DataLab, UM6P / EMI), Rabat. Windows 11, PowerShell,
Python 3.13.5, Chrome 150.
**Status as of 2026-08-03: round 3 COMPLETE. Full ad bodies fetched, columns
filled by reading, workbook rebuilt and verified at 301 rows.**

---

## Ground rules for this repo

- **Never invent an offer, company, email, contact name or date.** Every row must
  trace to a URL that was actually fetched. An empty cell is the correct answer
  when the source published nothing.
- **The workbook only grows.** `build` reads the existing file and merges into
  it. Back up to `backup/` with a timestamp before every build.
- No emojis anywhere — not in code, comments, commits, docs or output.
- Report progress numerically (X/Y, MB, %), never "in progress".
- Do not commit unless asked.

## Where things stand

### Delivered and verified

`Offres_Emploi_Genie_Industriel_Lean_2026.xlsx` — 4 sheets, 301 rows:

| Sheet | Rows |
|---|---|
| MAROC - JUNIOR | 116 |
| MAROC - AVEC EXPERIENCE | 184 |
| REMOTE - JUNIOR | 1 |
| REMOTE - AVEC EXPERIENCE | 0 |

14 columns (15 on remote sheets — they carry the evidence quote). Offer links are
clickable, filters on, header row frozen. Verified 2026-08-03: 301/301 links
clickable, 301 distinct URLs, 0 excluded titles, 0 job-board names in the
employer column, `Expérience requise` usable on 235/301 (78 %).

A copy is republished to `G:\My Drive\Emploi Rose\` on every build — that is the
link the workbook is shared through, since an e-mail attachment can never be
updated once sent.

**The count keeps going down on purpose.** 366 (round 1, unreviewed) -> 324
(relevance gate) -> 313 (field reading) -> 301. Round 1 shipped before any gate
existed. Each later round drops rows that reading proved wrong: an off-topic
role, an internship, a technicien post inside a grouped ad. A shorter honest list
beats a long one — do not restore a row without re-reading its ad.

### Round 1 (complete) — 615 offers merged from

Rekrute 53 · LinkedIn Maroc 129 · LinkedIn Remote 238 · Dreamjob 68 ·
Optioncarriere 61 · MarocAnnonces 23 · Jooble 20 · Bayt 12 · Jobicy 5 ·
Arbeitnow 5 · Indeed 1. Plus company enrichment: 294/369 websites, 132 emails.

### Round 2 (code done, PARTIALLY RUN, then paused)

Goal was to break the platforms that blocked round 1.

**Won:**

| Was blocked | Fix | Yield |
|---|---|---|
| Emploi.ma (Cloudflare) | SeleniumBase UC mode | 6 unique — the site ignores its own `keywords` param |
| Bayt.com (403) | UC + real `?q=` endpoint | 19 |
| Indeed.ma (403) | UC mode | 9 — rate-limits hard after page 1 |
| Glassdoor (403) | UC mode | wall cleared; Morocco URL unstable |
| ANAPEC (SSL) | `verify=False` | reachable; listing is JS-rendered; mostly non-engineering |
| ATS feeds (unexplored) | public JSON APIs | 10 clean offers, 17 live feeds found |

Merged total reached **647 offers** (387 Maroc / 260 international).

### Round 2 gates (run 2026-08-02)

`data/merged.json` holds the 647 rows. `data/raw_http.json` is a copy of it, so
that `run.py`'s `all_rows()` picks the corpus up without a re-scrape — the round-2
merge was done by the `research/` scripts, which do not write `raw_*.json`.

**Relevance (`curate`)** — 631 offers read one by one, **482 kept / 149 dropped**.
Verdicts with a reason per offer: `data/curation_verdicts.json`. What only reading
caught: an FMC Talent ad whose own text says *"This is not a Continuous Improvement
Manager vacancy... for a Customer Success Manager role"*; a "LEAN/MAP Loan
Underwriter" where LEAN is the HUD mortgage programme; `Lean 4` the proof
assistant; a Lever ATS demo posting; and a whole family of "Supply Chain
Specialist $50/hr remote" ads (Mercor, Handshake, Turing, Crossing Hurdles, YO
Labs, Weekday AI) that are document-annotation gigs for training AI models.
Kept in the other direction: "Ingénieur Fonctionnel" at Africawork, which reads as
IT but actually runs an automated parcel-sorting line.

**Remote / visa (`stage`)** — 160 international offers read, **1 OK / 159 REJET**.
Verdicts: `data/remote_verdicts.json`. The single pass is a Magic freelance
mission whose ad states `Location: Global+`. Everything else is scoped to a
country or a zone, or needs presence on a shop floor.

**Legacy rows** — `build` re-imports the existing workbook and used to stamp every
recovered REMOTE row `remote_verdict = OK` on sight. 55 round-1 rows therefore
sat in the deliverable having never faced either gate. On the user's decision
(2026-08-02) `do_build` now filters recovered rows through both verdict files too;
those 55 were dropped. Every prior workbook is in `backup/`.

### Round 3 (2026-08-03) — read the ads, fill the columns

The scrapers only ever kept the ~700-character listing card, so most of
`Expérience requise`, `Type de contrat`, `Secteur` and even `Entreprise` were
empty or carried a value the board invented. Fixed in two steps.

**1. Fetch the real ad body** — `run.py fulltext` (new). Plain HTTP for LinkedIn /
Rekrute / SmartRecruiters, then UC mode with a visible window for the walled
boards. `data/fulltext.json` now holds **609 bodies**.

168 walled offers were re-fetched, **151 succeeded**. Optioncarriere turned out
**not** to block by IP reputation — UC clears it (53/55). The 17 failures are 14
Jooble + 1 Indeed stuck on the Cloudflare interstitial, plus 2 expired ads. Those
rows keep their link and their listing-card values; the rest of their columns stay
empty rather than guessed.

**2. Rule on the fields by reading** — `run.py enrich`, 132 offers read this round,
`data/field_verdicts.json` now holds **289** rulings. Result: usable
`Expérience requise` went from 41/324 (12.7 %) to **235/301 (78.1 %)**, and 0 rows
still name a job board as the employer.

Six more rows were dropped by reading: an AbbVie post whose body places it in
*"Worcester, MA (5 days a week on site)"*; a Capgemini "Associate Quality
Engineer" that is REST/Postman/JIRA software testing; a Safran "Chef d'équipe"
the ad itself files as *"CDI Technicien"*; a Hirschmann grouped ad whose only
industrial post is a *Lean Management Technician*; an SNTL "chef d'équipe"
warehouse post at Bac+2; and a Manpower "Assistante Supply Chain" the source
files under *"Assistant(e) / Secrétaire de direction"*.

### What is left to do

1. **14 Jooble + 1 Indeed detail pages** are still behind Cloudflare. Do not burn
   time on the captcha — the user called this off explicitly on 2026-08-03. The
   rows ship with their link and whatever the listing card showed.
2. Company enrichment (`enrich_company.py`) is **not needed for the workbook** —
   it fills website/e-mail columns the deliverable no longer has.
3. Re-run `scrape` when the list needs refreshing, then `fulltext`, then rule on
   offers whose `key` is not already in the verdict files.

## The skill

`skill/findmyprincessajob/` — install by copying to `~/.claude/skills/`.

One input, the specialty. Pipeline: `scrape` -> `stage` -> `curate` -> `build`.

**Two steps the model must do itself and must not delegate to a regex:**

- **`stage`** — rule on every international offer: truly 100% remote, no visa,
  no work permit, no residency, no on-site? Quote the ad's own words as evidence;
  the quote becomes a column so the user can audit the judgement.
  **When an ad is silent about eligibility, reject it.**
- **`curate`** — rule on relevance. "Lean 4 & Formal Proof Systems" is a theorem
  prover; "Ingénieur Qualité Logiciel" is software QA; "Operations Manager - BPO"
  is call-centre staffing. All three pass a keyword filter. Only reading catches
  them.

`skill/findmyprincessajob/references/SOURCES.md` is the valuable artefact: a
tested map of which boards answer plain HTTP, which need a real browser, and
which are dead. Read it before touching a source.

## Hard-won facts (do not re-derive)

- **Rekrute and the LinkedIn guest API return 403 to WebFetch but respond
  normally to `requests` with a Chrome UA.** LinkedIn's `jobs-guest` endpoints
  need no auth at all.
- **UC mode needs `headless=False`** — the visible window is what clears the
  challenge.
- **`sb.uc_gui_click_captcha()` drives the real mouse and hangs forever when no
  challenge is on screen.** Only call it after confirming the page source
  contains a challenge marker. This cost a wasted 20-minute run.
- **Ordinary Selenium needs `page_load_strategy="eager"`** — these ad-heavy pages
  never fire `load`, so the default burns the full timeout every page (~10x).
- **SmartRecruiters throttles at the TLS layer** (`SSL: UNEXPECTED_EOF`). Back
  off; pre-filter on title instead of fetching a detail page per job.
- **SeleniumBase can't download its own chromedriver** here; copy the one
  Selenium Manager cached into `seleniumbase/drivers/` as both `chromedriver.exe`
  and `uc_driver.exe`.
- **403 from a script is not a dead link.** Bayt, Indeed, Jooble and Jobicy
  refuse scripted requests but open fine in a browser — a "Chef de projet Black
  belt F/H at Safran Group" URL that 403s to `requests` renders normally in UC.
- **Word boundaries matter.** Without `\b`, "fes" matches *professional* and
  "sale" matches *sales* — that bug put US jobs on the Morocco sheet.
- **Generic remote boards are tech-only.** RemoteOK, Remotive, WeWorkRemotely,
  Jobicy, Himalayas, WorkingNomads yield ~nothing for industrial roles.
- **Facebook / Instagram job posts are not publicly reachable.** Dreamjob.ma and
  MarocAnnonces republish them and are the practical substitute.
- Search engines (DuckDuckGo, Mojeek, Ecosia, Brave) rate-limit within tens of
  requests. Company sites were resolved by domain guessing + DNS instead.
- **Verdict files are keyed by `jid(url)`, not by list position.** `stage` used to
  index over unfiltered rows while `build` looked those ids up against the
  curation-filtered list, so a visa verdict could land on the wrong offer. Both
  now carry a `key`; the positional `id` is only a fallback for older files.
- **`read_existing` re-approves whatever is already in the workbook** — it sets
  `remote_verdict = OK` for every row on a REMOTE sheet so appends do not silently
  drop them. That also means a row never has to justify itself twice, which is why
  `do_build` re-checks recovered rows against both verdict files.
- **A single long-lived UC session silently burns the queue when it dies.** The
  browser window gets closed, Chrome updates, the driver drops — every later URL
  then fails instantly against a dead localhost port and looks like a source
  failure. `fulltext.uc_pass` reopens the session instead (12 retries max).
- **`uc_gui_click_captcha()` misses on a scaled display.** Selenium reports the
  checkbox in logical pixels, PyAutoGUI clicks in physical ones; at 150 % Windows
  scaling every click lands at two thirds of the right spot. Use
  `uc_gui_handle_captcha()` (TAB + SPACE) first. It still does not clear Jooble.
- **SeleniumBase downloaded its own `uc_driver.exe` fine on 2026-08-03** (driver
  150.0.7871.124, ~15 s), contradicting the earlier note. Keep the manual copy
  trick in `SOURCES.md` as a fallback, not as the first move.
- **`os.makedirs` raises WinError 3 on a Google Drive path that exists.** The
  virtual filesystem breaks the walk up to `G:/`. Guard with `os.path.isdir`
  first — this silently skipped the Drive publication for a whole build.
- **An expired Optioncarriere ad returns the site's "Dernières offres" list**,
  not a 404. Without checking for *"Cette offre d'emploi a expiré"* you store a
  page of Decathlon and Konecta ads as the offer's body.
- **A grouped ad is only as good as the posts inside it.** "STMicroelectronics
  recrute Plusieurs Profils" lists nothing but technicien roles; "Postes à saisir
  chez Safran" recruits Techniciens Supply Chain. The title passes every filter.

## Why the remote sheets are small, and why that is correct

Lean and industrial engineering happen on a shop floor. Roles that are at once
*in this field*, *100% remote*, and *open to someone applying from Morocco with
no work permit* are genuinely rare. Real rejections, quoted from the ads:

- `"Remote - US based candidates only, no visa sponsorship available"`
- `"Work Authorization: US Citizen"`
- `"Remote (EU/UK)"` · `"must be based in Portugal"` · `"Remote - Ontario"`
- `"Travel: ~90% - onsite at customer plants"` · `"THIS IS NOT A REMOTE POSITION"`

A small honest number beats a long list of applications that cannot succeed.
Do not loosen the bar to make the sheet look fuller.

## Layout

```
Offres_Emploi_Genie_Industriel_Lean_2026.xlsx   the deliverable
discussion_claude.md                            full session log, both rounds
CLAUDE.md                                       this file
spec.json                                       worked example of a skill spec
skill/findmyprincessajob/                       SKILL.md + pipeline/ + references/
research/                                       exploratory scripts from both rounds
data/                                           raw scraped JSON per source
backup/                                         timestamped workbook snapshots
```

## Resume checklist

`spec.json` carries the paths; it now points at this repo, not the old
`C:\Users\pc\Desktop\Emploi`.

```powershell
$root = "c:\Users\El Yazid\Desktop\HelpingMyLtCutieRoseAchieveHerDreams"
cd "$root\skill\findmyprincessajob\pipeline"
$env:PYTHONIOENCODING="utf-8"
python run.py fulltext "$root\spec.json"  # fetch the real ad bodies (opens Chrome)
python run.py curate   "$root\spec.json"  # then read every offer + rule
python run.py stage    "$root\spec.json"  # then read every offer + rule
python run.py enrich   "$root\spec.json"  # then read every offer + fill the columns
python run.py build    "$root\spec.json"
```

`fulltext` must run before `enrich` — `enrich` can only be as good as the text it
is handed. Close the workbook in Excel before `build`, or the save raises
`PermissionError`.

Back up the workbook first. A Chrome window opens during `scrape` — leave it alone.
`curate` and `stage` only write the candidate files; the rulings are yours to make
and go in `data/curation_verdicts.json` and `data/remote_verdicts.json`.
