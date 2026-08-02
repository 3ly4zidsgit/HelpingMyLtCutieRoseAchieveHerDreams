"""Hand-curated verdicts on the international offers.

Each ad was read individually. An offer is kept only if a candidate based in
Morocco could actually hold it: fully remote, no residency requirement, no work
permit / visa sponsorship needed, no on-site or relocation obligation.
Keyed by the LinkedIn/board job id found in the URL.
"""

# id -> (why it is genuinely open worldwide)
KEEP = {
    "4429666879": "Mercor - contrat AI-evaluation, 'Location: Remote', talents recrutes dans le monde entier, 80-120 $/h",
    "4435017721": "Mercor - 'Fully Remote', 15-20 h/semaine, 50 $/h, recrutement mondial",
    "4445187180": "Turing - poste explicitement 'Remote Industrial Engineer', plateforme de talents 100% distribuee",
    "4438920449": "Crossing Hurdles - contrat 'Location: Remote', 10-40 h/semaine, 40-50 $/h",
    "4438910657": "Crossing Hurdles - contrat 'Location: Remote', 10-40 h/semaine, 40-50 $/h",
    "4433394658": "Magic - freelance, 'Location: Global+', poste debutant, aucune condition de residence",
    "4424795887": "Handshake - travail contractuel horaire flexible pour la recherche IA, sans lieu impose",
    "4424813226": "Handshake - travail contractuel horaire flexible pour la recherche IA, sans lieu impose",
    "4427143059": "AbroadWorks - societe de staffing mondial, poste affiche 'Remote', equipes US/Inde/Philippines",
    "4445989269": "LSA - work placement 100% a distance, 4 semaines, ouvert aux jeunes diplomes",
}

# board offers (non-LinkedIn) kept on the same reading, keyed by exact title+company
KEEP_BOARD = {
    ("business analyst", "elite software automation"):
        "WeWorkRemotely - region 'Anywhere in the World', analyse et amelioration de processus",
    ("senior manager, gtm operational excellence", "remote"):
        "Jobicy - eligibilite EMEA/LATAM/Canada multi-regions, poste d'excellence operationnelle",
    ("compliance operations specialist", "twilio"):
        "WeWorkRemotely - region 'Anywhere in the World', poste operations/conformite",
    ("fast track operations specialist 2", "twilio"):
        "WeWorkRemotely - region 'Anywhere in the World', poste operations",
}

# Explicitly rejected, with the reason found in the ad itself. Kept for the
# handoff document so the judgement is auditable.
REJECT_REASONS = {
    "US only / no visa sponsorship": [
        "Ladders - Director Global Value Stream : 'Remote - US based candidates only, no visa sponsorship available'",
        "Ladders - Manager CI Predictive Maintenance : idem",
        "Softthink Solutions : 'Work Authorization: US Citizen'",
        "Paradigm Global Consulting : 'US Only - Must be US Citizen, no dual citizenship'",
        "Lockheed Martin : 'Secret security clearance, which requires U.S. citizenship'",
        "Celerity : 'Remote West Coast based'",
        "Winland Foods : 'Remote with the ideal candidate living close to Grand Forks'",
        "Refocus LLC : 'Multiple Locations all across United States'",
    ],
    "Residence obligatoire dans un pays donne": [
        "10x.Team (Lean Six Sigma Black Belt + OpEx Manager) : 'located in the EU or UK'",
        "Empire Life (3 postes) : 'Remote - Ontario' / 'Remote in Canada'",
        "Insight Global : 'fully remote across Canada'",
        "Hays : 'Candidates must be based in Portugal and have the legal right to work in Portugal'",
        "Somewhere : 'Remote - Latin America'",
        "HyperGrowth Recruitment : 'Full Time Remote | EU-Based'",
        "Pod Talent : 'Fully Remote UK or EU'",
        "Hire Far Out : 'South Africa (Remote)'",
        "Storyteller : 'working from anywhere in Egypt'",
        "Paired : titre '(Remote, US-Based)'",
        "Apptoza : 'Location: Remote (Canada)'",
        "Optilogic : 'Preference given to candidates based in EMEA'",
    ],
    "En realite sur site / terrain / voyages": [
        "Agilent - Regional Lean Business Analyst : 'spend significant time on manufacturing floors'",
        "FMC Talent (2 postes) : 'UK or Ireland home base, ~90% onsite at customer plants'",
        "TE Connectivity Portugal : 'regular travel, including international trips, 50-75%'",
        "Winland Foods : 'Remote with Travel up to 75%'",
        "Scientific Search : 'Remote opportunity with 60-80% travel to manufacturing partners'",
        "ON.energy : 'Remote with up to 75% travel'",
        "Kore Recruiters : 'THIS IS NOT A REMOTE POSITION - Position is on-site'",
        "Parcc Associates : 'must be willing to relocate to Dover Delaware'",
        "Graymont : 'Full-Time, Permanent (Hybrid)'",
        "Hays Portugal : 'Remote work with 1-2 visits to the office each month'",
        "Google : 'hybrid workplace', lieu Prague/Tchequie",
        "Micarna : observation des processus sur le terrain (Gemba)",
    ],
    "Hors domaine malgre le mot-cle": [
        "Alignerr - 'Researcher Lean 4 & Formal Proof Systems' : Lean 4 est un langage de preuve formelle, pas le Lean manufacturing",
        "Aptive - 'Lean Agilist' : SAFe / Agile logiciel",
        "NuvoLogic - 'LEAN/MAP (HUD) Loan Underwriter' : LEAN est ici un programme de prets HUD",
        "StackAdapt / Duetto / CORTO / Accenture / 1KOMMA5 : Quality Engineer = test logiciel",
    ],
}

def keep_reason(row):
    """-> reason string if this international offer is genuinely worldwide, else None"""
    import re
    url = row.get("url", "")
    m = re.search(r"-(\d{6,})(?:\?|/|$)", url)
    if m and m.group(1) in KEEP:
        return KEEP[m.group(1)]
    key = (re.sub(r"\s+", " ", (row.get("job_title") or "")).strip().lower(),
           re.sub(r"\s+", " ", (row.get("company") or "")).strip().lower())
    return KEEP_BOARD.get(key)
