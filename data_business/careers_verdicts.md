# Sites carrieres des multinationales - ce qui a ete etabli le 2026-08-04

Methode : `research/probe_ats.py` (8 familles d'ATS publiques x ~180 slugs) puis
`research/probe_careers.py` (ouvrir la page carrieres, suivre les redirections,
lire l'hote du board dans l'URL que l'entreprise publie elle-meme). Aucun tenant
n'a ete devine : `research/probe_bypass.py` avait deja montre que 20 tenants
Workday devines donnent zero, et un sondage de ce round a renvoye 422 - pas 404 -
sur danone, jti et mars, ce qui dit "le tenant existe, ta requete est fausse"
et non "essaie un autre nom".

## Exploitable

| Employeur | Board | Etat |
|---|---|---|
| Mazars | SmartRecruiters + Recruitee | **vivant, Maroc** - 100 + 3 offres |
| Grant Thornton | Recruitee | **vivant, Maroc** - 89 offres |
| Devoteam | SmartRecruiters | **vivant, Maroc** - 100 offres |
| Oliver Wyman | Lever | **vivant, Maroc** - 2 offres |
| EY, Accenture | Recruitee | vivant, Maroc (deja en place) |
| BCG | Greenhouse | vivant, Maroc (deja en place) |
| Roland Berger | SmartRecruiters | vivant, Maroc (deja en place) |
| Schneider Electric | SmartRecruiters | deja en place |

## Atteint, mais sans offre au Maroc

- **Unilever** - Workday. Les vrais noms de site ont ete lus sur leur page :
  `unilever.wd3.myworkdayjobs.com/wday/cxs/unilever/Unilever_Experienced_Professionals/jobs`
  et `.../Unilever_Early_Careers/jobs` repondent **200**, et renvoient
  `total = 0` pour Morocco. Le board est joignable ; il n'y a rien dedans pour le
  Maroc aujourd'hui. A re-sonder plus tard, le code n'est pas necessaire.

## Atteint, mais inutilisable

- **Schneider Electric** - `careers.se.com/api/jobs` (Phenom) repond 200 avec de
  vraies offres, mais **ses filtres geographiques ne fonctionnent pas** :
  `country=Morocco` renvoie une offre au Caire, `location=Casablanca` aussi.
  Sans filtre fiable il faudrait aspirer 3 012 offres pour en trier quelques-unes.
  Schneider est de toute facon deja couvert par SmartRecruiters.
- **Dell** - la page carrieres pointe vers Oracle Cloud Recruiting
  (`/hcmUI/CandidateExperience/fr-FR/sites/careers`) mais l'hote n'a pas ete
  resolu en HTTP simple. `dell.wd1.myworkdayjobs.com/wday/cxs/dell/External/jobs`
  repond 200 avec `total = 0`.
- **Deloitte** - trois boards differents selon le pays (SuccessFactors
  `career4.successfactors.com`, Taleo `dttit.taleo.net`, Workday
  `deloitteie.wd3`), aucun n'etant l'entite Maroc.

## Aucun board public atteignable en HTTP simple

P&G, Nestle, Danone, Siemens, Mars, JTI, Coca-Cola, Henkel, L'Oreal, PwC, KPMG,
Capgemini, OCP, Managem, Attijariwafa, Maroc Telecom.

Pages carrieres rendues en JavaScript ou protegees par un WAF. **La route
pratique vers ces employeurs reste la recherche LinkedIn**, ce pour quoi le
`queries_en` de `spec_business.json` porte des sondes ancrees employeur
("graduate program Morocco", "management trainee Casablanca").

## Ce qui n'a PAS ete ecrit, et pourquoi

Pas de `scrape.workday()`. Le seul tenant Workday joignable et pertinent
(Unilever) renvoie zero offre au Maroc : ecrire un scraper pour un board vide
serait du code mort a maintenir. La methode de decouverte est documentee ici et
dans `references/SOURCES.md` ; le jour ou un tenant repond avec des offres
marocaines, la boucle se calque sur celles de `scrape.ats`.
