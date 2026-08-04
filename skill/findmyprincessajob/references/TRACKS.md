# Plusieurs recherches dans un seul classeur

Une **piste** (track) est une recherche complete : sa specialite, ses mots-cles,
ses regex de pertinence, ses fichiers de verdict, ses feuilles. Un classeur peut
en porter plusieurs. Aujourd'hui il y en a deux :

| Piste | Spec | Feuilles | Perimetre |
|---|---|---|---|
| `lean` | `spec.json` | MAROC - JUNIOR, MAROC - AVEC EXPERIENCE, REMOTE - JUNIOR, REMOTE - AVEC EXPERIENCE | Maroc + remote sans visa |
| `business` | `spec_business.json` | COMMERCIAL & CONSEIL - JUNIOR, COMMERCIAL & CONSEIL - AVEC EXP | Maroc uniquement |

## Les cles de spec qui font une piste

```jsonc
{
  "track": "business",                       // etiquette de la piste
  "datadir": "<outdir>/data_business",       // OBLIGATOIRE si track != "lean"
  "applied_path": "<outdir>/data/applied.json",   // partage entre pistes
  "excel_path": "<...>/le_meme_classeur.xlsx",    // le meme fichier
  "morocco_only": true,                      // desactive la porte visa
  "sources": ["rekrute", "linkedin_ma", "ma_boards", "ats", "uc"],
  "offdomain_hard": true,                    // voir "la regle miroir" plus bas
  "ats": { "lever": ["oliverwyman"], "recruitee": ["grantthornton"] }
}
```

- **`datadir` n'est pas optionnel pour une seconde piste.** Tous les fichiers de
  verdict ont un nom global (`curation_verdicts.json`, `field_verdicts.json`,
  `remote_verdicts.json`, `fulltext.json`, `raw_*.json`). Deux specs qui partagent
  un repertoire s'ecrasent des le premier `curate`. `do_build` avertit bruyamment
  si `track` est defini et que `datadir` est reste le repertoire par defaut.
- **`applied_path` est partage.** Une coche appartient au classeur, pas a une
  recherche : les deux pistes lisent et ecrivent le meme `data/applied.json`.
- **`sources`** limite `scrape` aux etapes utiles. Cles : `rekrute`,
  `linkedin_ma`, `linkedin_remote`, `ma_boards`, `ats`, `worldwide`, `uc`.
- **`ats`** ajoute des employeurs aux listes de `scrape.py` sans les modifier, et
  sans embarquer ceux de l'autre piste.

## La regle miroir : `offdomain_hard`

Quand une seule recherche tourne, `strict_keep` laisse une echappatoire : un
titre hors domaine passe quand meme s'il marque 10 sur le vocabulaire de la
specialite. C'est raisonnable seul, et faux a deux pistes - **l'`offdomain` de
l'une est le sujet de l'autre**, donc l'echappatoire permet aux deux de
revendiquer la meme offre.

`"offdomain_hard": true` transforme l'`offdomain` en veto. Il ne se leve que si le
titre nomme explicitement un metier de la piste (un motif de `strong` dans le
titre) - ce qui evite qu'une offre du genre "Charge de Pilotage Commercial &
Excellence Operationnelle" soit perdue par les deux recherches a la fois.

En pratique, l'`offdomain` de la piste business est l'image miroir de celui du
Lean : il bannit `\blean\b`, `\bcontinuous improvement\b`, `\bquality engineer\b`,
`\bsupply chain\b`, `\bindustrialisation\b`... et le Lean bannit `\bcommercial\b`,
`\bsales\b`, `\bvente\b`. **Partage retenu : supply chain et logistique au Lean,
achats et procurement au business.**

## Ce que la piste change dans le code

- `build.SHEETS` porte `(nom, piste, zone, bucket)`. `build.route(row)` rend la
  feuille **ou `None` avec un motif ecrit** - avant, une ligne hors Maroc sans
  verdict visa n'appartenait a aucun groupe et disparaissait sans un mot.
- **La piste n'est pas une colonne.** Aucun champ ne survit a l'aller-retour dans
  le classeur s'il n'est pas dans `COLS`, donc elle est relue depuis le **nom de
  la feuille** (`build.TRACK_OF_SHEET`), exactement comme `seniority_bucket` et
  `remote_verdict`. Un nom de feuille inconnu retombe sur `lean`, ce qui fait
  qu'un classeur ecrit avant les pistes se relit a l'identique.
- `run.shipping()` filtre sur la piste. Sans ce filtre, `fulltext` et `enrich`
  d'une seconde piste re-telechargent tout le classeur de la premiere et
  presentent ses annonces au modele sous la mauvaise specialite.
- `run.do_build` met les lignes des **autres** pistes de cote juste apres
  `read_existing`, avant les trois etapes propres au spec : le jeu de cles
  rejetees, `exclude_titles`, `apply_fields`. Elles ne repassent par aucune, et
  reviennent telles quelles.

  **Ce n'est pas theorique.** Le `curation_verdicts.json` du Lean porte
  `keep:false` sur des offres commerciales marocaines - parce qu'elles sont hors
  sujet *pour le Lean*. Sans la partition, chaque `build spec.json` aurait efface
  la feuille commerciale, ligne par ligne, en silence.

## Quand une offre convient aux deux pistes

`core.dedupe` ne connait pas les pistes : la premiere ligne vue gagne et les
suivantes ne remplissent que ses cases vides. `build()` passe `previous` avant
`rows`, donc **une offre deja dans le classeur garde la feuille ou elle est** et
ne saute pas d'un onglet a l'autre au gre des builds. Une URL n'apparait jamais
deux fois dans le classeur.

## Faire tourner les deux pistes

```powershell
$root = "c:\Users\El Yazid\Desktop\HelpingMyLtCutieRoseAchieveHerDreams"
cd "$root\skill\findmyprincessajob\pipeline"
$env:PYTHONIOENCODING="utf-8"

# piste 1 - genie industriel
python run.py scrape   "$root\spec.json"
python run.py fulltext "$root\spec.json"
python run.py curate   "$root\spec.json"   # puis LIRE et juger
python run.py stage    "$root\spec.json"   # puis LIRE et juger
python run.py enrich   "$root\spec.json"   # puis LIRE et remplir
python run.py build    "$root\spec.json"

# piste 2 - commercial / graduate / conseil / achats
python run.py scrape   "$root\spec_business.json"
python run.py fulltext "$root\spec_business.json"
python run.py curate   "$root\spec_business.json"   # puis LIRE et juger
python run.py enrich   "$root\spec_business.json"   # puis LIRE et remplir
python run.py build    "$root\spec_business.json"
```

`stage` sort tout de suite sur la piste business : `morocco_only` la dispense de
la porte visa, et surtout l'empeche d'ecrire un `remote_verdicts.json` que
`do_build` relirait ensuite pour supprimer des lignes qui n'ont jamais eu besoin
d'un arbitrage.

**Apres avoir construit une piste, reconstruire l'autre et verifier** que ses
feuilles sont intactes. C'est le test qui prouve que la partition tient :

```powershell
python run.py build "$root\spec.json"
python "$root\research\verify.py"
```

## Ajouter une troisieme piste

1. Copier `spec_business.json`, changer `specialty`, `track`, `datadir`, et les
   listes de mots-cles et de regex.
2. Ajouter deux lignes a `build.SHEETS` avec le nouveau nom de piste. Le nom de
   feuille doit contenir `JUNIOR` pour la feuille junior (`read_existing` et
   `verify.py` s'appuient dessus), ne pas commencer par `REMOTE` sauf si la piste
   arbitre vraiment les visas, et tenir en **31 caracteres** - au-dela, Excel
   tronque en silence et deux noms peuvent se telescoper.
3. Mettre l'`offdomain` de la nouvelle piste en miroir de celui des autres, et
   `"offdomain_hard": true`.
4. `python research/harvest_track2.py <nouveau_spec.json>` d'abord : il relit le
   corpus deja telecharge avec les nouvelles regex, sans reseau. C'est la boucle
   de reglage gratuite - regarder les titres, ajuster, relancer.

## Ce qu'il ne faut pas faire

**Ne rien ajouter au classeur a la main.** `build` le recree entierement a partir
de `SHEETS` : une feuille ajoutee, une note, une colonne supplementaire sont
detruites au build suivant, sans avertissement. La seule cellule qu'un humain
peut ecrire est la coche `Postule` en colonne A, et elle ne survit que parce que
`read_existing` la relit et que `applied.json` la double.
