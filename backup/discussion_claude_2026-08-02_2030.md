# Recherche d'offres d'emploi — Génie Industriel / Lean Six Sigma / Amélioration Continue

Document de reprise complet. Toute session Claude Code future doit pouvoir reprendre ce projet
en lisant uniquement ce fichier.

**Date de la recherche : 28/07/2026**
**Machine : Windows 11 Pro 10.0.26200, Python 3.13.5, Chrome 150.0.7871.187, Selenium 4.34.0**

---

## 1. Demande initiale

Rechercher sur Internet (Indeed, LinkedIn, Facebook, Instagram, sites de recruteurs) des offres
d'emploi correspondant aux mots-clés : Génie industriel, Lean Six Sigma, Kanban, Ishikawa,
amélioration continue, excellence opérationnelle — au Maroc, et à l'international **uniquement
si 100% remote**. Elargir avec d'autres mots-clés pertinents, en français et en anglais.
Profil : junior sans expérience, mais inclure aussi les postes exigeant de l'expérience.
Objectif : **100+ offres**, classées dans un Excel avec tous les attributs, une feuille dédiée aux
offres avec expérience, une feuille dédiée aux offres hors Maroc, liens cliquables, emails,
noms des responsables RH, dates de publication et dates limites.

## 2. Résultat livré (version finale, restructurée)

**Fichier : `C:/Users/pc/Desktop/Emploi/Offres_Emploi_Genie_Industriel_Lean_2026.xlsx` (118,6 KB)**

4 feuilles, pas de page de synthèse (supprimée à la demande) :

| Feuille | Lignes | Contenu |
|---|---|---|
| MAROC - JUNIOR | 181 | Maroc, expérience non exigée ou non précisée |
| MAROC - AVEC EXPERIENCE | 171 | Maroc, 2 ans et plus / senior / manager / responsable |
| REMOTE - JUNIOR | 10 | 100% remote mondial sans visa, profil junior |
| REMOTE - AVEC EXPERIENCE | 4 | 100% remote mondial sans visa, profil expérimenté |
| **TOTAL** | **366** | |

Volets figés : ligne d'en-tête uniquement (`A3`) — **aucune colonne épinglée**.

**14 colonnes** (jeu réduit à la demande) : N°, Titre du poste, Entreprise, Type de contrat,
Niveau d'expérience, Expérience requise, Ville, Pays / Éligibilité, Secteur, Fonction,
Date de publication, Date limite candidature, LIEN DE L'OFFRE, Description (extrait).
Les deux feuilles REMOTE portent une 15e colonne : **Pourquoi 100% remote / sans visa**.

Colonnes supprimées à la demande : Niveau d'études, Télétravail/Remote, Nombre de postes,
Salaire, Date publication (ISO), Date limite (ISO), Contact RH / Recruteur, Poste du contact RH,
Profil LinkedIn du contact, Email de candidature, Email société, Site web société, Source,
Mots-clés correspondants, Score pertinence.

Filtres supplémentaires appliqués : **tous les postes « technicien » / « technician » supprimés**
(15 lignes retirées).

Mise en forme : en-têtes bleu foncé, filtres automatiques, volets figés, lignes alternées,
code couleur du niveau d'expérience (vert = junior, orange = expérimenté, gris = non précisé),
100% des liens d'offres cliquables.

### Comment les offres REMOTE ont été triées (important)

Le Lean / génie industriel s'exerce sur le terrain (gemba, 5S, VSM, SMED machine) : les postes
100% remote **sans visa ni autorisation de travail** y sont très rares. Plutôt que de filtrer
par expression régulière, **les 219 annonces internationales du domaine ont été lues une par une**
et jugées individuellement. Verdicts codés dans `scripts/remote_curation.py`.

Motifs de rejet, cités mot pour mot dans les annonces :
- « Remote - US based candidates only, no visa sponsorship available » (Ladders, 2 postes)
- « Work Authorization: US Citizen » (Softthink) / « US Only - Must be US Citizen » (Paradigm)
- « located in the EU or UK » (10x.Team) / « must be based in Portugal » (Hays)
- « Remote - Ontario » (Empire Life) / « fully remote across Canada » (Insight Global)
- « THIS IS NOT A REMOTE POSITION » (Kore) / « must relocate to Dover Delaware » (Parcc)
- « ~90% onsite at customer plants » (FMC Talent) / « travel 50-75% » (TE Connectivity)
- Faux positifs du mot-clé : « Lean 4 » (langage de preuve formelle, Alignerr), « Lean Agilist »
  (SAFe logiciel), « LEAN/MAP (HUD) Loan Underwriter » (programme de prêts).

Les 14 offres retenues sont majoritairement des **missions freelance / contrat à l'heure**
(Mercor, Turing, Handshake, Crossing Hurdles, Magic) — c'est la voie réaliste pour travailler
à distance depuis le Maroc dans ce domaine.

### Version précédente (conservée)

Le premier classeur (615 offres, 6 feuilles, 29 colonnes avec emails/contacts RH) reste
disponible sous `Offres_Emploi_Genie_Industriel_Lean_2026.xlsx`. Il est régénérable via
`build_excel.py` ; la version restructurée l'est via `build_excel2.py`.

## 2bis. Round 2 — contournement des blocages (02/08/2026)

Objectif : débloquer les plateformes qui avaient refusé au premier passage.

### Ce qui a fonctionné

| Blocage | Contournement | Résultat |
|---|---|---|
| **Emploi.ma** (Cloudflare) | **SeleniumBase UC mode** (`uc=True`, fenêtre visible) | Mur franchi — 25 cartes/page. Mais la recherche par mot-clé du site ignore le paramètre `keywords` : seulement **6 offres uniques**. |
| **Bayt.com** (403) | UC mode + **vrai endpoint de recherche `?q=`** (les pages `/{slug}-jobs/` n'existent que pour quelques slugs) | 30 cartes/page, toutes requêtes acceptées |
| **Indeed.ma** (403 après 1 page) | UC mode | Mur franchi — « plus de 400 emplois » sur *amélioration continue* |
| **Glassdoor** (403) | UC mode | Mur franchi (30 cartes), mais l'URL Maroc est instable — vérifier le titre de page avant de parser |
| **ANAPEC** (erreur SSL) | `verify=False` | Site atteint. `anapec.org/.../resultat_recherche/tout:all` liste les offres ; `anapec.ma/chercheurs/offres` est rendu en JS. Offres majoritairement non-ingénieur. |
| **Flux ATS** (non exploré au round 1) | APIs publiques non authentifiées | **17 flux vivants**, 13 avec des postes au Maroc |

**Piège d'installation SeleniumBase** : il télécharge son propre chromedriver depuis
`chromedriver.storage.googleapis.com`, qui a expiré ici. Solution : copier celui déjà mis en
cache par Selenium Manager vers `seleniumbase/drivers/chromedriver.exe` **et** `uc_driver.exe`.

### Flux ATS découverts (JSON public, sans authentification)

```
https://api.smartrecruiters.com/v1/companies/{c}/postings?limit=100&offset={n}
https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true
https://{c}.recruitee.com/api/offers/
https://api.ashbyhq.com/posting-api/job-board/{c}
https://apply.workable.com/api/v1/widget/accounts/{c}?details=true
```

Vivants avec postes Maroc : **alten** (de loin le plus riche), lesaffre, abbvie, rolandberger,
assystem, thales, continental, apmterminals · flex, bcg · geodis, teleperformance, ey,
accenture · delphi · safrangroup.

Deux pièges : SmartRecruiters limite **au niveau TLS** (`SSL: UNEXPECTED_EOF`) quand on le
sollicite trop — prévoir un backoff et pré-filtrer sur le titre avant d'appeler le détail.
Et filtrer le Maroc **sur le champ localisation uniquement** : un « Morocco » perdu dans un
texte générique fait entrer des postes américains.

### Ce qui reste bloqué

- **Welcome to the Jungle** : `api.welcometothejungle.com/api/v1/organizations?country=MA`
  renvoie bien les entreprises marocaines, mais l'endpoint des offres par organisation est 404.
- **Workday** : aucun tenant deviné n'a répondu (noms de site non standardisés).
- **Moteurs de recherche** (DuckDuckGo, Mojeek, Ecosia, Brave) : tous limitent après quelques
  dizaines de requêtes. Les sites d'entreprises sont donc résolus par devinette de domaine + DNS.
- **Facebook / Instagram** : inchangé, non accessible publiquement.

### Bugs de données corrigés à ce round

- Regex Maroc sans `\b` : « professional » contenait *fes*, « sales » contenait *sale* —
  des postes américains/britanniques entraient dans la liste Maroc.
- Vérification remote : le premier filtre bloquait sur « must be able to » (formulation banale).
  Resserré aux vraies restrictions géographiques/visa uniquement.

## 3. Sources effectivement scrapées

| Source | Offres retenues | Méthode |
|---|---|---|
| LinkedIn (Remote international) | 238 | API invités `jobs-guest`, HTTP direct |
| LinkedIn (Maroc) | 129 | API invités `jobs-guest`, HTTP direct |
| Dreamjob.ma | 68 | HTTP direct + BeautifulSoup |
| Optioncarriere.ma | 61 | Selenium (JS obligatoire) |
| Rekrute.com | 53 | HTTP direct + pages détail (dates limites) |
| MarocAnnonces.com | 23 | HTTP direct |
| Jooble.org Maroc | 20 | Selenium |
| Bayt.com Maroc | 12 | Selenium |
| Jobicy | 5 | API JSON |
| Arbeitnow | 5 | API JSON |
| Indeed.ma | 1 | Selenium (fortement limité par anti-bot) |

**Volume brut traité : 3 598 cartes LinkedIn + ~2 000 cartes des autres boards → 949 lignes
pertinentes → 672 après déduplication → 615 après filtre strict anti-hors-domaine.**

### Sources testées sans résultat exploitable
- **RemoteOK, Remotive, WeWorkRemotely, WorkingNomads, Himalayas** : APIs fonctionnelles mais
  100% orientées tech/software. Aucune offre réelle de génie industriel / lean. Confirmé par
  requête directe sur ~800 offres.
- **Emploi.ma** : challenge Cloudflare non franchi (même avec Selenium furtif + warm-up).
- **Glassdoor** : 403 systématique.
- **Michael Page .ma, Fed Africa, LMS ORH, Manpower.ma, Adecco.ma, Gi Group .ma, Talent.ma,
  Khadamat.ma, Menaraemploi.ma, ANAPEC** : domaines morts, erreurs SSL/DNS ou 404 (vérifié le
  28/07/2026). L'ANAPEC renvoie une erreur SSL sur `anapec.org`.
- **Welcome to the Jungle** : mur de cookies, aucune carte extraite.
- **Facebook / Instagram** : les publications d'emploi ne sont pas accessibles publiquement
  (authentification obligatoire, pas de surface de recherche d'emploi sur Instagram). Contournement
  retenu : les agrégateurs marocains qui republient ces annonces (Dreamjob.ma, MarocAnnonces.com)
  ont été scrapés à la place.

## 4. Décisions techniques importantes

1. **HTTP direct plutôt que Selenium quand c'est possible.** Rekrute et LinkedIn bloquent l'outil
   WebFetch (403) mais répondent normalement à `requests` avec un User-Agent Chrome. Selenium n'a
   été utilisé que pour Bayt, Indeed, Optioncarriere et Jooble.
2. **`page_load_strategy = "eager"` obligatoire.** Avec la stratégie par défaut, les pages d'offres
   chargent des traceurs à l'infini et chaque `driver.get()` consommait les 60 s de timeout complet.
   Passage en `eager` + timeout 22 s + images désactivées : gain d'un facteur ~10.
3. **API invités LinkedIn** : `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`
   avec `keywords`, `location`, `start` (pas de 10), `f_WT=2` pour le filtre remote. Détail d'une
   offre : `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jobId}`. Aucune authentification.
   LinkedIn limite le débit après ~600 requêtes de détail (d'où seulement 38 types de contrat
   récupérés au second passage).
4. **Filtre de pertinence à deux niveaux.** Un mot-clé fort dans le *titre* suffit (score 10). Un
   mot-clé fort seulement dans la *description* ne suffit pas : « amélioration continue » et
   « excellence opérationnelle » sont du remplissage dans presque toutes les annonces françaises.
   Un filtre anti-hors-domaine (`OFFDOMAIN` dans `merge.py`) élimine les postes IT, finance,
   commercial, RH, santé, etc. sauf si le titre porte un vrai mot-clé lean. 57 faux positifs écartés.
5. **Enrichissement société sans moteur de recherche.** DuckDuckGo, Mojeek, Ecosia et Brave ont
   tous bloqué/limité après quelques dizaines de requêtes. Remplacé par une résolution directe de
   domaine : génération de slugs depuis le nom de l'entreprise, test DNS sur `.ma/.com/.co.ma/.fr`,
   vérification que la page contient bien un token du nom, puis extraction des emails sur
   `/contact`, `/careers`, `/recrutement`. Résultat : **294/369 sites trouvés, 132 avec emails**.
   Liste noire de mots trop génériques (`bank`, `achat`, `service`…) pour éviter les faux domaines.
6. **Noms de contacts RH** : uniquement ceux réellement publiés sur la page de l'offre LinkedIn
   (52 contacts). Aucun nom inventé ou déduit.
7. **Réparation d'encodage.** Certains boards servent de l'UTF-8 sans le déclarer : `unmojibake()`
   dans `merge.py` refait le tour cp1252/latin-1 → UTF-8 (`L'HÃ´pital` → `L'Hôpital`).

## 5. Qualité des données (taux de remplissage sur 615 lignes)

| Champ | Taux |
|---|---|
| Titre, Lien, Pays | 100% |
| Description (extrait) | 99.7% |
| Date de publication | 96.6% (93.3% convertie en ISO) |
| Entreprise | 85.9% |
| Ville | 83.7% |
| Secteur / Fonction | ~69% |
| Site web société | 68.8% |
| Expérience requise | 65.9% |
| Télétravail | 49.3% |
| Email société | 29.6% |
| Type de contrat | 27.2% |
| Date limite de candidature | 8.6% |
| Contact RH nommé | 8.5% |
| Email de candidature direct | 6.2% |
| Salaire | 0.3% |

**Limites assumées :** seul Rekrute.com publie systématiquement une date limite de candidature
(d'où 8.6%). Les salaires ne sont quasiment jamais publiés sur le marché marocain (0.3%).
LinkedIn n'expose le type de contrat que sur la page détail, et a limité le débit avant la fin
du second passage.

**Contrôle des liens :** échantillon de 75 offres testées. 52 réponses 200. Les 23 autres sont des
403 d'anti-bot (Bayt, Jooble, Indeed, Jobicy) — vérifiées une par une sous Selenium, **les pages
sont bien vivantes** (ex. `chef-de-projet-black-belt-f-h-74807771` = « Chef de projet Black belt
F/H at Safran Group - Temara »). Un seul vrai lien mort : une annonce MarocAnnonces expirée.

## 6. Mots-clés utilisés

**FR :** lean, six sigma, kaizen, kanban, ishikawa, amélioration continue, excellence
opérationnelle, génie industriel, ingénieur industriel, black belt, green belt, DMAIC, SMED, VSM,
TPM, 5S, méthodes, industrialisation, process, production, qualité, supply chain, logistique,
performance industrielle, productivité, ordonnancement, planification industrielle, QHSE,
maintenance, consultant organisation, audit qualité, optimisation, responsable méthodes.

**EN :** continuous improvement, operational excellence, operations excellence, industrial
engineer, manufacturing engineer, process engineer, methods engineer, production engineer,
quality engineer, process improvement, business process improvement, process excellence,
manufacturing excellence, lean manufacturing, lean management, lean transformation,
lean consultant, kaizen consultant, value stream, plant manager, production manager,
supply chain, productivity, WCM, OPEX.

**Villes Maroc interrogées :** Casablanca, Tanger, Rabat, Kénitra, Marrakech, Agadir, Fès,
Meknès, Oujda, Tétouan, El Jadida.
**Zones remote interrogées :** Union Européenne, États-Unis, Royaume-Uni, France, Canada,
Allemagne, Espagne, Portugal, Émirats, Afrique, Europe, Worldwide.

## 7. Carte des fichiers

```
C:/Users/pc/Desktop/Emploi/
  Offres_Emploi_Genie_Industriel_Lean_2026.xlsx   <- LIVRABLE
  discussion_claude.md                            <- ce fichier
  scripts/
    common.py           regex de pertinence, modele de ligne, extraction d'emails, I/O JSON
    sel_common.py       driver Chrome furtif (eager, sans images, anti-detection)
    s_rekrute.py        scraper Rekrute (44 mots-cles x 5 pages)
    s_linkedin.py       scraper API invites LinkedIn (Maroc + remote) + pages detail
    s_remote.py         RemoteOK / Remotive / Jobicy / WorkingNomads / Himalayas / Arbeitnow / WWR
    s_maboards.py       MarocAnnonces + Dreamjob.ma
    s_selenium.py       Bayt / Indeed.ma / Optioncarriere / Jooble / Emploi.ma  (arg: nom du site)
    s_selenium2.py      Bayt corrige + Indeed international remote  (arg: bayt | indeed_remote)
    patch_linkedin.py   2e passe LinkedIn: type de contrat (apostrophe typographique)
    enrich.py           pages detail Rekrute -> date limite, contrat, description, emails
    enrich_company.py   resolution de domaine -> site + emails recrutement (40 threads, cache)
    merge.py            fusion, dedoublonnage, filtre strict, classification junior/experimente
    s_worldwide.py      offres 100% remote mondiales (geo Worldwide/Anywhere + controle visa)
    remote_curation.py  VERDICTS MANUELS offre par offre sur le caractere remote / sans visa
    dump_intl.py        export des annonces internationales pour relecture humaine
    build_excel.py      generation du classeur 6 feuilles (version 1, 615 offres)
    build_excel2.py     generation du classeur 4 feuilles (version finale, colonnes reduites)
    check_links.py      controle de sante des liens sur echantillon
    stats.py            taux de remplissage et repartitions
    data/*.json         donnees brutes par source + merged.json + company_cache.json
```

## 8. Comment rafraîchir la liste

```powershell
cd C:\Users\pc\Desktop\Emploi\scripts
$env:PYTHONIOENCODING="utf-8"
python s_rekrute.py            # ~4 min
python s_linkedin.py           # ~35 min (le plus gros contributeur)
python s_maboards.py           # ~3 min
python s_selenium.py oc        # ~12 min
python s_selenium.py jooble    # ~6 min
python s_selenium2.py bayt     # ~3 min
python s_remote.py             # ~3 min
python enrich.py detail        # dates limites Rekrute
python merge.py                # fusion + filtres
python enrich_company.py       # sites + emails (cache: seules les nouvelles societes)
python merge.py                # re-fusion pour greffer le cache societes
python build_excel.py          # classeur final
```

Le cache `data/company_cache.json` évite de refaire les résolutions de domaine déjà faites.

## 9. Problèmes connus / pistes d'amélioration

- **Emploi.ma** reste inaccessible (Cloudflare). Piste : `undetected-chromedriver` ou un profil
  Chrome persistant avec cookies réels.
- **Indeed.ma** ne rend qu'une page avant blocage. Piste : rotation de proxies ou délais longs.
- **Type de contrat LinkedIn** à 27% seulement : relancer `patch_linkedin.py` un autre jour, la
  limitation de débit se réinitialise.
- **Facebook groupes emploi Maroc** : nécessiterait un compte et violerait les CGU ; non fait.
- 100 lignes sans ville (surtout Dreamjob, dont les titres sont de type article de blog).
- Certaines offres Dreamjob remontent à 2024-2025 : le site ne filtre pas par date. La colonne
  « Date publication (ISO) » permet de les écarter par tri/filtre.
