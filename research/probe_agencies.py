import requests, re, sys
from bs4 import BeautifulSoup
from common import HDRS, find_emails

S = requests.Session(); S.headers.update(HDRS)

T = {
 "michaelpage": "https://www.michaelpage.ma/emploi",
 "michaelpage2": "https://www.michaelpage.ma/jobs?page=1",
 "fedafrica": "https://www.fedafrica.com/offres-emploi",
 "fedafrica2": "https://www.fedafrica.com/nos-offres",
 "diorh": "https://www.diorh.com/nos-offres-emploi/",
 "lmsorh": "https://www.lms-orh.com/offres-emploi/",
 "gesper": "https://www.gesperservices.com/offres-emploi",
 "talentspartners": "https://talentspartners.ma/offres-emploi/",
 "globerh": "https://www.globerh.ma/offres-emploi/",
 "convergence": "https://www.convergence-rh.com/offres",
 "manpowergroup": "https://www.manpowergroup.ma/offres-emploi",
 "adecco_ma": "https://www.adecco.ma/offres-emploi",
 "gigroup_ma": "https://ma.gigroup.com/offres-emploi/",
 "anapec_http": "http://www.anapec.org/",
 "anapec2": "https://anapec.org/sigec-app-rv/fr/offres",
 "amaljob": "https://www.amaljob.com/offres-emploi",
 "menara_alt": "https://menaraemploi.ma/",
 "jobsquare2": "https://www.jobsquare.ma/offres-emploi",
 "marocemploi": "https://www.marocemploi.net/?s=lean",
 "emploipublic": "https://www.emploi-public.ma/",
 "khadamatmaroc": "https://khadamat-maroc.com/?s=lean",
 "alwadifa": "https://www.alwadifa-maroc.com/?s=lean",
 "modiami": "https://www.modiami.com/search?q=lean",
 "stagiairesma2": "https://www.stagiaires.ma/offres/",
 "jobinmorocco": "https://www.jobinmorocco.com/jobs",
 "wttj_ma": "https://www.welcometothejungle.com/fr/companies?refinementList%5Boffices.country_code%5D%5B%5D=MA",
 "novojob2": "https://www.novojob.com/maroc/offres-d-emploi",
 "emploisma": "https://emplois.ma/?s=lean",
 "recrutement_ma": "https://www.recrutement.ma/",
 "tanitjobs_ma": "https://www.marocjob.com/?s=lean",
}

for k, u in T.items():
    try:
        r = S.get(u, timeout=20, allow_redirects=True)
        s = BeautifulSoup(r.text, "html.parser")
        ttl = (s.title.get_text(strip=True) if s.title else "")[:60]
        na = len(s.select("article")); nl = len(s.select("a[href*='offre'], a[href*='emploi'], a[href*='job']"))
        print(f"{k:16s} {r.status_code} len={len(r.text):7d} art={na:3d} joblinks={nl:3d} | {ttl}")
    except Exception as e:
        print(f"{k:16s} ERR {type(e).__name__}: {str(e)[:55]}")
    sys.stdout.flush()
