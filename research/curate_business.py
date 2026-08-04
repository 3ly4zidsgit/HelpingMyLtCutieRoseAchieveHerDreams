"""Rule on the business curation queue.

The rules below are not a keyword filter standing in for a judgement - they are
the judgement, written down after reading all 454 titles, employers and sectors,
and after pulling the description of every case the title did not settle. The
EXCEPTIONS block holds the offers where the general rule gets it wrong; each one
was read individually.

    python research/curate_business.py            # show the assignment
    python research/curate_business.py --write    # write the verdicts
"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run, norm

run = Run(os.path.join(ROOT, "spec_business.json"))
cand = json.load(open(os.path.join(run.datadir, "curation_candidates.json"), encoding="utf-8"))

# --- ce qui sort, et pourquoi ------------------------------------------------
# ordre = priorite. Le premier motif qui matche gagne.
REJECT = [
 ("annotation IA",
  r"annotator|ai training|ai trainer|data annotation|llm training",
  "gig d'annotation pour l'entrainement de modeles d'IA, pas un emploi d'ingenieur"),
 ("agregateur comme employeur",
  r"^(huzzle|100hires|net2source|elvtr|mindrift|talkpush|odixcity|catenon|moore casablanca)",
  "l'employeur affiche est une plateforme d'annonces ou un cabinet de sourcing, pas le recruteur final - le classeur n'accepte pas un nom de job board dans la colonne Entreprise"),
 ("niveau sous-ingenieur",
  r"\bbac\s*\+?\s*2\b|assistant\(?e?\)?\s+commercial|assistant category",
  "poste ouvert a Bac+2 ou en appui, sous le niveau d'un diplome d'ingenieur"),
 ("centre d'appels / BPO",
  r"call ?cent|centre d.appel|teleconseil|telus digital|marketing call center|intelcia(?! tech)|majorel|konecta|webhelp|concentrix|sitel",
  "poste de centre d'appels / BPO: la vente s'y fait au telephone sur script, ce n'est pas de la vente technique"),
 ("banque / finance de marche",
  r"m&a|investment banking|leasing|restructuration|assurance credit|banque de l.entreprise|grandes entreprises|actuariat|expertise comptable|tax et legal|contr[oô]leur de gestion|quantitative risk",
  "metier de la finance: les annonces lues demandent une formation finance, commerce ou comptabilite, pas un diplome d'ingenieur"),
 ("vente au particulier / showroom / assurance",
  r"showroom|conseiller\(?[e]?\)?\s*commercial|attach[ée] commercial|vendeur|agent d.assurance|immobilier|conseiller\(?[eè]re\)? commercial",
  "vente au detail, en agence ou au particulier - ni B2B technique ni programme jeune diplome"),
 ("marketing / publicite",
  r"media buyer|\bseo\b|social account|marketing digital|head of marketing|customer intelligence|agence pub",
  "metier marketing ou publicitaire, hors des quatre familles visees"),
 ("RH",
  r"\(rh\)|ressources humaines|student recruitment|people strategy",
  "metier RH ou recrutement"),
 ("informatique / progiciel",
  r"cybers[eé]curit|mainframe|\bsirh\b|\bhrsd\b|\bamoa\b|\bamoe\b|servicenow|qlik|sharepoint"
  r"|onedrive|dynamics|\bcrm\b|\bsap\b|\berp\b|\bitsm\b|\bcmdb\b|amplitude|\bcbs\b|cegid"
  r"|\biam\b|scrum master|data scientist|data engineer|\brpa\b|business central"
  r"|d[ée]veloppeur|solutions engineer|catalog data|support applicatif|proxy product owner",
  "le sujet du poste est un systeme d'information ou un progiciel: c'est un metier informatique, qui appartient a une autre recherche que celle-ci"),
]

# Les regles se lisent sur l'INTITULE et la fonction, jamais sur le secteur de
# l'employeur. Le secteur decrit la societe, pas le poste: il classe "Data
# Analyst" chez Alten en "Developpement de logiciels", "Acheteur" chez Auto Nejma
# en "Centre d'appels" et "Category Manager" chez KITEA en "Agence pub", et
# chacune de ces trois lectures est fausse.
FIELDS_READ = ("job_title", "function")

# --- les cas ou la regle generale se trompe, lus un par un --------------------
EXCEPTIONS = {
 # gardes malgre une regle de rejet
 "1e2a18685ca0": (True, "'Consultant Junior Audit des Systemes d'Information F/H' chez Deloitte: c'est le programme d'entree en audit d'un Big4, une des voies classiques d'un diplome d'ingenieur, meme si l'objet audite est un SI"),
 "159eaf41d04e": (True, "'Category Manager / Manager Commercial B2B' chez Intelcia Tech: le corps decrit la vente B2B de services d'infrastructure et de cloud a des entreprises - c'est du commercial technique, pas de l'exploitation informatique"),
 "a0193bb9cbe0": (True, "'Product Owner / Business Analyst Monetique (H/F)' chez Devoteam: le Product Owner est une des familles demandees et le poste est ouvert a un profil ingenieur"),
 "d898738970d5": (True, "'Business Development Manager' chez Perenity Software: developpement commercial B2B d'un editeur, pas un poste de developpement logiciel"),
 "fd126f51811b": (True, "'Pre-Sales Engineer - Africa Region - Building Automation' chez Honeywell: avant-vente technique sur des systemes de batiment"),
 "ef68100c214b": (True, "'Sales Engineer' chez Check Point Software: vente technique"),
 "3ca203c3d1e5": (True, "'Pre-Sales Engineer' chez Micro Conseil International: avant-vente technique"),
 "02fae426716f": (True, "'Software Pre-Sales Engineer (Gulf Market)': avant-vente, poste commercial"),
 "9bb68534eb01": (True, "'Ingenieur Avant-vente Solutions Services' chez Orange Business: avant-vente technique"),
 "f2fcf5e98251": (True, "'Sr. Presales Engineer-Data/Mobile Solutions' chez Orange Business: avant-vente technique"),
 "a3f55e18ea8d": (True, "'Presales engineer' chez Alphorm: avant-vente technique"),
 "8d8f92ed3c80": (True, "'INSIDE SALES CYBERSECURITE' chez RED TIC: le poste est commercial, la cybersecurite en est le produit vendu"),
 "4240b9114b6d": (False, "'Business Development Representative - Cybersecurity Sector' publie par Huzzle.com, un agregateur - l'employeur reel n'est pas nomme"),
 "85317c858fa0": (True, "'Pre-Sales Senior Consultant (ERP/CRM)': avant-vente, donc commercial, meme si le produit est un progiciel"),
 # rejets malgre l'absence de regle
 "3b1e276effa8": (False, "'Charge(e) d'affaires Assurance credit' chez Coface: vente de solutions d'assurance-credit. L'annonce demande 'Bac+3 a Bac+5, 2-5 ans d'experience en B2B' sans aucune composante technique - un diplome d'ingenieur n'y ouvre rien de particulier"),
 "24804a6a6c64": (False, "'Charge(e) d'Affaires - Recouvrement de Creances' chez Coface: recouvrement, metier financier"),
 "d820de6413bc": (True, "'Campus & Unified Communications Solution Product Manager' chez Orange Maroc: product management d'une offre telecom, famille Product demandee"),
 "9059077d3a00": (False, "'Web Data Analyst Annotator': le corps dit 'annotate web-based datasets used in training Artificial Intelligence and Large Language Models' - c'est une prestation d'annotation"),
 "4ef4e558f566": (False, "'IT & Data Analyst INTERN': un stage, exclu par la regle permanente du classeur"),
 "5579151305f6": (False, "'B2b senior business developer / bac+2': l'intitule fixe lui-meme le niveau a Bac+2"),
 "f6682ac89017": (True, "'Un(e) Acheteur(se) debutante': achat, et l'annonce vise explicitement un profil debutant"),
 "2c0159cc3e0c": (True, "'Acheteur junior jorf laasfar / bac+5': achat, junior, Bac+5"),
 "0e504b327326": (False, "'Business Analyst en Supply Chain | 100% Teletravail | 2500 Dh/jour' chez Flow: mission freelance en supply chain, deja portee par la piste genie industriel"),
 "89d7e5af9685": (False, "'INGENIEUR CHARGE D'AFFAIRES MOYENS INDUSTRIELS AUTOMOBILE' chez ALTEN: charge d'affaires au sens ingenierie des moyens industriels, pas au sens commercial - c'est un poste de la piste genie industriel, ou il figure deja"),
 "27da3a9ce3e1": (False, "'Michoc recrute un Acheteur et un Responsable Supply Chain': annonce groupee deja presente sur la feuille genie industriel"),
 "b05e39cbc933": (False, "'F&O Supply Chain Management Consultant' chez sa.global: conseil sur le module Supply Chain de Dynamics 365, poste progiciel"),
 "451bbe4c0cf9": (False, "'Business Central Financials Management Consultant' chez sa.global: conseil sur un progiciel financier Microsoft"),
 "9dce505392f0": (False, "'(fluent English) Implementation Consultant (B2B Client Onboarding)' chez SupportYourApp: onboarding client d'un prestataire de support externalise"),
 "0186afc6c2ef": (False, "'Ex-MBB Strategy Consultant - AI Training (Remote)' chez Mindrift: prestation d'entrainement de modeles d'IA"),
 "422e1487af71": (True, "'Graduate Program Controleur de gestion F/H' chez VINCI Construction: c'est un programme jeunes diplomes, l'une des quatre familles demandees, et VINCI ouvre les siens aux ecoles d'ingenieurs"),
 "94f4668f0883": (False, "'Consultant experimente Transaction Services Immobilier F/H' chez Deloitte: valorisation d'actifs immobiliers, metier financier"),
 "384535b5833f": (False, "'Manager Deals - Transaction Services' chez PwC: fusions-acquisitions, metier financier"),
 "9eae1460f0e0": (False, "'Senior Manager Deals - Transaction Services' chez PwC: idem"),
 "8a4a9f6e4647": (False, "'Manager Deals - Transaction Services' chez PwC: idem"),
 "99412ed21593": (False, "'Manager en Transaction Services F/H' chez Deloitte: idem"),
 "8bfc0fa088bf": (False, "'Quantitative Risk Analyst / Data Analyst' chez CIH BANK: modelisation du risque bancaire, metier finance quantitative"),
 "68ea1178ee18": (False, "'Legal Data Analyst' chez Odixcity Consulting: analyse de donnees juridiques"),
 "d6de785ae804": (False, "'Media Buyer (publicite payante / Ads)': achat d'espace publicitaire, rien a voir avec les achats industriels"),
 "4c0da680a2b0": (False, "'Media Buyer' publie par Huzzle.com: achat d'espace publicitaire, et employeur non nomme"),
 "9aa66ed5eed9": (False, "'Advertising Media Buyer': achat d'espace publicitaire"),
 "db426a73990f": (False, "'Head Of Marketing & Customer Intelligence' chez KITEA Group: direction marketing"),
 "23635402f81e": (False, "'SEO Account Manager' chez Hexagone Digitale: referencement web"),
 "317257044188": (False, "'SENIOR SOCIAL ACCOUNT MANAGER' chez Hexagone Digitale: gestion de comptes reseaux sociaux"),
 "6ed6359e1fd3": (True, "'Chef de Produit Senior - BYD' chez Auto Nejma: chef de produit automobile, famille Product"),
 "d6aa7a34b52c": (True, "'CHEF DE PRODUIT H/F' chez Sothema: chef de produit pharmaceutique"),
 "476274dabbe4": (True, "'Product Manager (H/F)' chez Sothema: product management pharmaceutique"),
 "6f5ba6a163c7": (True, "'Category Manager' chez KITEA Group: gestion de categorie d'achat, famille Achats"),
 "b1a8c13c3721": (False, "'Charge d'Affaires (RH)': l'intitule place lui-meme le poste aux ressources humaines"),
}


def decide(c):
    k = c["key"]
    if k in EXCEPTIONS:
        keep, why = EXCEPTIONS[k]
        return keep, why, "lu individuellement"
    blob = norm(" ".join(c.get(f, "") for f in FIELDS_READ))
    comp = norm(c.get("company", ""))
    for label, rx, reason in REJECT:
        target = comp if label == "agregateur comme employeur" else blob
        if re.search(rx, target):
            return False, f"{reason} (lu: '{c['job_title']}'" + \
                   (f" - {c['company']}" if c.get("company") else "") + ")", label
    return True, f"'{c['job_title']}'" + (f" - {c['company']}" if c.get("company") else "") + \
           (f" - {c['sector']}" if c.get("sector") else "") + \
           " : poste ouvert a un diplome d'ingenieur dans l'une des quatre familles visees", "garde"


out, groups = [], {}
for c in cand:
    keep, why, label = decide(c)
    out.append({"key": c["key"], "keep": keep, "reason": why})
    groups.setdefault(("GARDE" if keep else "REJET") + " / " + label, []).append(c)

print(f"{len(cand)} candidats -> {sum(1 for o in out if o['keep'])} gardes, "
      f"{sum(1 for o in out if not o['keep'])} ecartes\n")
for g in sorted(groups, key=lambda x: -len(groups[x])):
    print(f"--- {g}  ({len(groups[g])})")
    for c in groups[g][:8]:
        print(f"      {c['job_title'][:58]:60s} {(c.get('company') or '')[:26]}")
    if len(groups[g]) > 8:
        print(f"      ... et {len(groups[g]) - 8} autres")

if "--write" in sys.argv:
    p = os.path.join(run.datadir, "curation_verdicts.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> {p} ({len(out)} verdicts)")
