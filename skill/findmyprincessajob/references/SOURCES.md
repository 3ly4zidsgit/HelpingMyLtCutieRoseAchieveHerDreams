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

Confirmed live with Morocco postings: **alten** (by far the richest),
lesaffre, abbvie, rolandberger, assystem, thales, continental (SmartRecruiters);
flex, bcg (Greenhouse); geodis, teleperformance, ey, accenture (Recruitee);
delphi (Ashby); safrangroup (Workable).

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

**Setup gotcha:** SeleniumBase downloads its own chromedriver from
`chromedriver.storage.googleapis.com`, which may time out. Selenium Manager has
usually already cached a matching driver; copy it in:

```powershell
Copy-Item "$env:USERPROFILE\.cache\selenium\chromedriver\win64\<ver>\chromedriver.exe" `
          "<site-packages>\seleniumbase\drivers\chromedriver.exe" -Force
Copy-Item "$env:USERPROFILE\.cache\selenium\chromedriver\win64\<ver>\chromedriver.exe" `
          "<site-packages>\seleniumbase\drivers\uc_driver.exe" -Force
```

Also set `page_load_strategy="eager"` on ordinary Selenium drivers: these
ad-heavy pages never fire `load`, so the default strategy burns the whole
timeout on every page (~10x slowdown).

## Reachable but awkward

- **ANAPEC** — serves a broken TLS chain; needs `verify=False`.
  `anapec.org/sigec-app-rv/fr/chercheurs/resultat_recherche/tout:all` lists
  offers server-side; `anapec.ma/chercheurs/offres` is JS-rendered (needs a
  browser). Keyword search returns nothing useful. Mostly non-engineering roles.
- **Welcome to the Jungle** — `api.welcometothejungle.com/api/v1/organizations?country=MA`
  returns Moroccan companies unauthenticated, but the per-organization jobs
  endpoint 404s. Site itself is behind a cookie wall.
- **Optioncarriere.ma** — needs a browser (`article.job`); listing pages work,
  detail pages serve a captcha.
- **Jooble.org** — needs a browser (`div[data-test-name='_jobCard']`).

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
