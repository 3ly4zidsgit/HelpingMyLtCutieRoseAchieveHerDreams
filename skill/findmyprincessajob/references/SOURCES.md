# Source access map

Established by direct testing (last verified 2026-08-02). Read this before
adding or debugging a source — it records what works, what needs a browser, and
what is simply dead, so none of it has to be re-derived.

## Works with plain `requests` + a Chrome User-Agent

These return 403 to the WebFetch tool but respond normally to `requests`. That
asymmetry is the single most useful fact here.

| Source | Endpoint | Notes |
|---|---|---|
| Rekrute.com | `/offres.html?s=1&p={n}&keyword={kw}` | Richest Moroccan board. Cards carry contract, experience, education, sector, function, **publication + deadline dates**, headcount. The only board that reliably publishes an application deadline. |
| LinkedIn guest API | `/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=&location=&start=` | No auth. 10 results per call, `start` steps by 10. `f_WT=2` filters to remote. Detail: `/jobs-guest/jobs/api/jobPosting/{jobId}` gives description, seniority, function, industry and sometimes the recruiter's name. Throttles after roughly 600 detail calls. |
| MarocAnnonces | `/maroc/offres-emploi-b309.html?kw=&pge=` | `ul.cars-list li` |
| Dreamjob.ma | `/?s={kw}` | WordPress. Titles are blog-style ("X recrute un ..."), so the employer must be parsed out of the headline. Results are not date-filtered — old posts appear. |

## JSON / RSS APIs (no blocking)

RemoteOK `/api` · Remotive `/api/remote-jobs?limit=2000` (full feed; local
filtering beats their search) · Jobicy `/api/v2/remote-jobs?count=100&tag=` ·
WeWorkRemotely `*.rss` per category · Himalayas `/jobs/api?limit=&offset=` ·
Arbeitnow `/api/job-board-api?page=`.

**All of them are tech-dominated.** For industrial/manufacturing specialties
expect near-zero yield — that is a property of the market, not a bug.

## ATS feeds — unauthenticated, clean, well-structured

The highest-quality route for named employers. Probe a company slug against each:

```
https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=100&offset={n}
https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true
https://api.lever.co/v0/postings/{c}?mode=json
https://{c}.recruitee.com/api/offers/
https://api.ashbyhq.com/posting-api/job-board/{c}
https://apply.workable.com/api/v1/widget/accounts/{c}?details=true
https://{c}.teamtailor.com/jobs.json
```

```
https://{c}.jobs.personio.de/search.json
```

Confirmed live with Morocco postings: **alten** (by far the richest),
lesaffre, abbvie, rolandberger, assystem, thales, continental (SmartRecruiters);
flex, bcg (Greenhouse); geodis, teleperformance, ey, accenture (Recruitee);
delphi (Ashby); safrangroup (Workable).

Added 2026-08-04 for the business track: **mazars** (SmartRecruiters 100 +
Recruitee 3), **grantthornton** (Recruitee 89), **devoteam** (SmartRecruiters
100), **oliverwyman** (Lever), **hpe** (Personio). Lever, Personio and Teamtailor
had been documented and probed here for a year without ever having a loop in
`scrape.ats` — they do now.

The slug lists in `scrape.py` are defaults; a spec adds its own with
`"ats": {"lever": ["oliverwyman"], ...}` so a second track does not have to edit
the file and does not drag the first track's employers along.

### Career sites of the big multinationals — the discovery recipe

Do **not** guess a Workday tenant. `research/probe_bypass.py` tried 20 across
3 hosts and got nothing; a later probe returned **422** (not 404) from danone,
jti and mars on every site name tried. Read the status code: 404 means "look
elsewhere", 422 or 500 means "the route is there, your request is wrong" — i.e.
the tenant exists and only the site path is missing, and the site path is written
in the URL the company itself links to.

`research/probe_careers.py` does that: fetch `<domain>/careers` (and `/jobs`,
`/fr/carrieres`...), follow the redirects, and read the ATS host out of the final
URL and out of every link on the page — Workday `{tenant}.wd{N}.myworkdayjobs.com`,
SuccessFactors `career{N}.successfactors.{eu,com}`, Taleo, Avature, Eightfold,
iCIMS, Oracle `/hcmUI/CandidateExperience/`. Output: `careers_hosts.json`.

Results on 2026-08-04, and they are mostly negative — worth knowing before
spending a day on it. Full write-up in `data_business/careers_verdicts.md`:

| | |
|---|---|
| Unilever | Workday reachable, real site names read off their page, **0 Morocco postings**. No scraper written: a board with nothing in it is dead code. |
| Schneider Electric | `careers.se.com/api/jobs` answers 200 with real jobs but its **geographic filters do not work** (`country=Morocco` returns a Cairo job). Already covered via SmartRecruiters anyway. |
| Dell | careers page points at Oracle Cloud Recruiting; host not resolved over plain HTTP. `dell.wd1...` answers 200 with total 0. |
| Deloitte | three different boards by country, none of them the Morocco entity. |
| P&G, Nestle, Danone, Siemens, Mars, JTI, Coca-Cola, Henkel, L'Oreal, PwC, KPMG, Capgemini, OCP, Managem, Attijariwafa, Maroc Telecom | no public board reachable over plain HTTP — JS-rendered or behind a WAF. |

**The practical route to these employers is the LinkedIn guest search**, which is
why the business spec's `queries_en` carries employer-anchored probes
("graduate program Morocco", "management trainee Casablanca").

Two traps:
- SmartRecruiters throttles **at the TLS layer** (`SSL: UNEXPECTED_EOF`) when
  hammered. Back off and retry; do not fetch a detail page per job — pre-filter
  on the title first.
- Filter Morocco on the **location field only**. A stray "Morocco" in
  boilerplate drags in US/UK jobs.

## Needs SeleniumBase UC mode (Cloudflare / anti-bot)

Plain `requests` **and** ordinary Selenium both get 403. SeleniumBase UC mode
gets through all of these:

```python
from seleniumbase import SB
with SB(uc=True, headless=False, locale="fr", ad_block=True) as sb:
    sb.uc_open_with_reconnect(url, reconnect_time=6)
    sb.uc_gui_click_captcha()          # harmless if there is no captcha
```

| Source | URL pattern | Selector |
|---|---|---|
| Emploi.ma | `/recherche-jobs-maroc?keywords=&page=` | `div.card-job` |
| Bayt.com | `/en/morocco/jobs/?q={kw}&page=` — the real search endpoint; the `/{slug}-jobs/` pages only exist for a few slugs | `li[data-js-job]` |
| Indeed.ma | `/jobs?q=&l=Maroc&start=` | `div.job_seen_beacon` |
| Glassdoor | Morocco URL is fragile; verify the page title says Morocco before parsing | `li[data-test='jobListing']` |

`headless=False` is required — the visible window is what clears the challenge.

**Setup gotcha:** SeleniumBase fetches its own `uc_driver.exe` on first use from
`storage.googleapis.com/chrome-for-testing-public`. That worked on 2026-08-03
(driver 150.0.7871.124, ~15 s). It has also timed out before — if it does,
Selenium Manager has usually already cached a matching driver; copy it in:

```powershell
Copy-Item "$env:USERPROFILE\.cache\selenium\chromedriver\win64\<ver>\chromedriver.exe" `
          "<site-packages>\seleniumbase\drivers\chromedriver.exe" -Force
Copy-Item "$env:USERPROFILE\.cache\selenium\chromedriver\win64\<ver>\chromedriver.exe" `
          "<site-packages>\seleniumbase\drivers\uc_driver.exe" -Force
```

Also set `page_load_strategy="eager"` on ordinary Selenium drivers: these
ad-heavy pages never fire `load`, so the default strategy burns the whole
timeout on every page (~10x slowdown).

## Detail pages under UC mode (verified 2026-08-03)

Fetching one **detail page per offer** is a different problem from scraping the
listing. 168 offers were re-fetched this way; 151 came back with a real body:

| Source | Detail pages | Result |
|---|---|---|
| Bayt.com | 14/14 | clean |
| Optioncarriere.ma | 53/55 | clean — **it does not block by IP reputation**, UC clears it. The 2 misses are expired ads |
| MarocAnnonces | 22/22 | clean, but the ad body sometimes carries a neighbouring ad's footer — do not read `Entreprise :` blindly |
| Dreamjob.ma | 59/59 | clean |
| Emploi.ma | 3/3 | clean |
| **ma.jooble.org** | **0/14** | stuck on the Cloudflare interstitial ("Just a moment...") |
| ma.indeed.com | 0/1 | same |

**Why the captcha click misses on a scaled display.** `uc_gui_click_captcha()`
computes the checkbox position from Selenium (logical pixels) and clicks it with
PyAutoGUI (physical pixels). At 150 % Windows scaling the screen is 2560x1440
logical / 3840x2160 physical, so every click lands at two thirds of the right
spot. `uc_gui_handle_captcha()` uses TAB + SPACE instead and is immune to this —
try it first. Check the machine with:

```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::PrimaryScreen.Bounds     # logical
python -c "import pyautogui;print(pyautogui.size())"    # physical
```

An offer whose body cannot be read keeps its link and its listing-card values.
Leave the other columns empty — a guessed cell is worse than a blank one.

## Reachable but awkward

- **ANAPEC** — serves a broken TLS chain; needs `verify=False`.
  `anapec.org/sigec-app-rv/fr/chercheurs/resultat_recherche/tout:all` lists
  offers server-side; `anapec.ma/chercheurs/offres` is JS-rendered (needs a
  browser). Keyword search returns nothing useful. Mostly non-engineering roles.
- **Welcome to the Jungle** — `api.welcometothejungle.com/api/v1/organizations?country=MA`
  returns Moroccan companies unauthenticated, but the per-organization jobs
  endpoint 404s. Site itself is behind a cookie wall.
- **Optioncarriere.ma** — needs a browser (`article.job`). Detail pages open fine
  under UC mode; an expired ad answers *"Cette offre d'emploi a expiré"* with the
  site's generic "Dernières offres" list, which is easy to mistake for content —
  check for that sentence before parsing.
- **Jooble.org** — listing works under UC (`div[data-test-name='_jobCard']`), but
  **detail pages sit behind a Cloudflare interstitial that UC does not clear**.

## Dead or unreachable (verified, do not retry blindly)

michaelpage.ma, fedafrica.com, lms-orh.com, manpower.ma, adecco.ma,
ma.gigroup.com, talent.ma, khadamat.ma, menaraemploi.ma, jobinmorocco.com,
marocjob.ma, jobzz.ma, recrutons.ma, emploi-maroc.net — dead domains, DNS or SSL
failures. Search engines (DuckDuckGo, Mojeek, Ecosia, Brave) rate-limit within
tens of requests; resolve company websites by direct domain guessing + DNS
instead.

**Facebook / Instagram** — job posts are not publicly reachable (auth required;
Instagram has no job-search surface). Moroccan aggregators that republish them
(Dreamjob.ma, MarocAnnonces) are the practical substitute.

## Recurring data traps

- **Word boundaries.** Without `\b`, "fes" matches *professional* and "sale"
  matches *sales*.
- **Mojibake.** Some boards serve UTF-8 without declaring it; `core.unmojibake`
  undoes the cp1252/latin-1 round-trip (`L'HÃ´pital` → `L'Hôpital`).
- **Dates in the city column.** Bayt puts the posting age where the location
  belongs; `build.clean_city` catches and re-routes it.
- **403 ≠ dead link.** Bayt, Indeed, Jooble and Jobicy refuse scripted requests
  but open fine in a browser. Confirm under UC before calling a link broken.
- **The "Dernières offres" sidebar.** Optioncarriere and Jooble ship a column of
  unrelated ads inside the same page. Every city, employer and salary in it
  belongs to another offer. A body fetched from those two must be read from the
  ad block, never scanned whole for a value.
- **An expired Optioncarriere ad answers 200,** with its own "Cette offre d'emploi
  a expiré" banner, and the page then lists other companies' ads. Store that and
  you have saved a page of Decathlon and Konecta as the offer's body.

## Where each source publishes the structured fields

Not prose — a labelled block the board prints verbatim. Worth extracting first,
then reading (`research/labels.py`, `research/deadlines.py`).

| Source | Block | What it is good for | Where it lies |
|---|---|---|---|
| LinkedIn | ad footer: `Niveau hiérarchique X - Type d'emploi Y - Fonction Z - Secteurs W` | contract type ("Temps plein"), function | **`Secteurs` is the posting company's sector**, so a staffing firm files an "Ingénieur méthodes" under *Technologie, information et Internet*. `Fonction Autre` and `Niveau hiérarchique Non pertinent` are non-answers |
| MarocAnnonces | `Domaine : X Fonction : Y Contrat : Z Entreprise : W Ville : V` | city, contract, sector | the advertiser miscategorises freely — "Acheteur Import" under *RH/Personnel*, "Acheteur senior" under *Production - Opérateur*. `Contrat : A discuter` and `Domaine : Autre` are published non-answers. `Entreprise` is often the interim agency (BEST PROFIL, AVANTA, Manpower, ARTUS, DEKRA Services, JobPlus, RHS EMPLOI), not the employer |
| Rekrute | ad footer: `Postulez avant le JJ/MM/AAAA` | **the only deadline any Moroccan board publishes** | absent from the listing card, so a scraper that only reads the card gets nothing |
| Jooble | the aggregator card itself: employer, city, posting age | fills rows whose detail page is walled | nothing else on the card is the ad |

Re-checked across all 640 fetched bodies on 2026-08-05: LinkedIn, Dreamjob,
MarocAnnonces, Optioncarriere and Bayt publish **no** application deadline
anywhere. Scanning for *date limite / avant le / jusqu'au / clôture / deadline /
postulez avant / closing date* returns only mission vocabulary ("jusqu'au
closing", "clôture des actions correctives"). The Date limite column sitting at
18 % is the sources' ceiling, not an unfinished job.
