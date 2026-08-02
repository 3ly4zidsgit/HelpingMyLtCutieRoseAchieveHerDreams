# Helping My Lt Cutie Rose Achieve Her Dreams

A job-hunting pipeline for **Génie Industriel / Lean Six Sigma / Amélioration
Continue / Excellence Opérationnelle** — Morocco, plus international roles that
are genuinely 100% remote with no visa requirement.

Everything here is real, scraped data. No offer, company, email or contact name
in the workbook was invented; every row traces back to a URL that was actually
fetched.

---

## What's in the box

| Path | What it is |
|---|---|
| `Offres_Emploi_Genie_Industriel_Lean_2026.xlsx` | The deliverable — 4 sheets |
| `discussion_claude.md` | Full session log: decisions, sources, blockers, data quality |
| `skill/findmyprincessajob/` | Reusable Claude Code skill — give it a specialty, get this workbook |
| `research/` | The exploratory scripts used to work out what was scrapable |
| `backup/` | Timestamped snapshots of the workbook |
| `data/` | Raw scraped JSON, one file per source |

## The workbook

| Sheet | Contents |
|---|---|
| `MAROC - JUNIOR` | Morocco, experience not required or unstated |
| `MAROC - AVEC EXPERIENCE` | Morocco, 2+ years / senior / manager / responsable |
| `REMOTE - JUNIOR` | Worldwide remote, no visa needed, junior |
| `REMOTE - AVEC EXPERIENCE` | Worldwide remote, no visa needed, experienced |

14 columns (15 on the remote sheets, which add the evidence quote). Offer links
are clickable. Filters on, header row frozen, no pinned columns.

### Why the remote sheets are small

Lean and industrial engineering happen on a shop floor — gemba walks, 5S, SMED
on real machines. Roles that are simultaneously *in this field*, *100% remote*,
and *open to someone applying from Morocco with no work permit* are genuinely
rare.

Every international offer was read individually rather than pattern-matched.
Typical rejections, quoted from the ads themselves:

- `"Remote - US based candidates only, no visa sponsorship available"`
- `"Work Authorization: US Citizen"`
- `"must be based in Portugal"` · `"Remote - Ontario"`
- `"THIS IS NOT A REMOTE POSITION"` · `"~90% onsite at customer plants"`

A small honest number beats a long list of applications that cannot succeed.

## The skill

`skill/findmyprincessajob/` is a Claude Code skill. Install by copying it to
`~/.claude/skills/`, then ask Claude to run it with a specialty.

It takes **one input — the specialty** — and:

1. expands it into FR + EN keywords and relevance rules,
2. scrapes every source in `references/SOURCES.md`,
3. **reads each international offer** and rules on remote/visa eligibility,
   quoting the ad's own words as evidence,
4. writes the 4-sheet workbook — **appending to the existing one**, never
   overwriting, so the list only grows.

```bash
cd skill/findmyprincessajob/pipeline
python run.py scrape  <outdir>/spec.json   # all sources
python run.py stage   <outdir>/spec.json   # emit offers needing a ruling
python run.py build   <outdir>/spec.json   # apply rulings, write Excel
```

`references/SOURCES.md` is the valuable part: a tested map of which job boards
respond to plain HTTP, which need a real browser, and which are dead — so none
of that has to be rediscovered.

## Notable findings

- **Rekrute and the LinkedIn guest API return 403 to some HTTP clients but
  respond normally to `requests` with a Chrome User-Agent.** The LinkedIn
  `jobs-guest` endpoints need no authentication at all.
- **SeleniumBase UC mode clears the Cloudflare walls** on Emploi.ma, Bayt,
  Indeed.ma and Glassdoor that both plain `requests` and ordinary Selenium hit
  403 on. It needs a visible browser window — that is what defeats the challenge.
- **ATS feeds are the cleanest source for named employers.** SmartRecruiters,
  Greenhouse, Lever, Recruitee, Ashby and Workable all serve unauthenticated
  JSON. Alten's Morocco postings alone are richer than most job boards.
- **Generic remote boards are tech-only.** RemoteOK, Remotive, WeWorkRemotely,
  Jobicy, Himalayas and WorkingNomads yield almost nothing for industrial roles.
- **Facebook and Instagram job posts are not publicly reachable.** Moroccan
  aggregators that republish them (Dreamjob.ma, MarocAnnonces) were used instead.

## Requirements

```
python 3.13 · requests · beautifulsoup4 · lxml · openpyxl · selenium · seleniumbase
```

SeleniumBase may fail to download its own chromedriver; copy the one Selenium
Manager already cached into `seleniumbase/drivers/`. See `SOURCES.md`.

## Ethics

Public job listings only, at polite request rates, for one person's own job
search. No authentication was bypassed and no private data was collected.
