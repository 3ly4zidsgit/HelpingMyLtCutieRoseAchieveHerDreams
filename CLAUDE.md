# CLAUDE.md — project state and how to resume

Job-hunting pipeline for **Génie Industriel / Lean Six Sigma / Amélioration
Continue / Excellence Opérationnelle** (Morocco + genuinely visa-free remote).

**Owner:** intern at DICE (DataLab, UM6P / EMI), Rabat. Windows 11, PowerShell,
Python 3.13.5, Chrome 150.
**Status as of 2026-08-02: PAUSED mid-round-2 by the user. Code complete, not run.**

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

`Offres_Emploi_Genie_Industriel_Lean_2026.xlsx` — 4 sheets, 366 rows:

| Sheet | Rows |
|---|---|
| MAROC - JUNIOR | 181 |
| MAROC - AVEC EXPERIENCE | 171 |
| REMOTE - JUNIOR | 10 |
| REMOTE - AVEC EXPERIENCE | 4 |

14 columns (15 on remote sheets — they carry the evidence quote). Offer links are
clickable, filters on, header row frozen, no pinned columns, no "technicien"
titles. Verified: 181/181 links clickable, 0 excluded titles.

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

**PAUSED HERE — this is the resume point.**

`data/merged.json` holds 647 rows. The workbook still shows the 366 from round 1
because the round-2 rows have not been through the two human/LLM review gates.

### What is left to do

1. **Relevance curation (`run.py curate`)** — new in the skill, never run. Read
   every offer and drop the keyword-matched-but-off-topic ones.
2. **Remote/visa review** — 256 international offers are unreviewed.
   `scratchpad/triage_intl.py` was mid-edit: it now auto-rejects on a stated bar
   *and* on the principle that **a country-scoped location is itself the visa
   barrier** (silence is not permission). It has not been re-run since that edit.
3. **Rebuild the workbook** and verify.
4. Company enrichment for the ~100 new companies (`enrich_company.py`, cached).

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

```powershell
cd skill\findmyprincessajob\pipeline
$env:PYTHONIOENCODING="utf-8"
python run.py curate C:\Users\pc\Desktop\Emploi\spec.json   # then read + rule
python run.py stage  C:\Users\pc\Desktop\Emploi\spec.json   # then read + rule
python run.py build  C:\Users\pc\Desktop\Emploi\spec.json
```

Back up the workbook first. A Chrome window opens during `scrape` — leave it alone.
