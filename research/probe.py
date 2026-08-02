import requests, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
H = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

targets = {
 "rekrute_search": "https://www.rekrute.com/offres.html?s=1&p=1&keyword=lean",
 "emploi_ma": "https://www.emploi.ma/recherche-jobs-maroc?keywords=lean",
 "marocannonces": "https://www.marocannonces.com/maroc/offres-emploi-b309.html",
 "optioncarriere": "https://www.optioncarriere.ma/emploi?s=lean&l=Maroc",
 "bayt": "https://www.bayt.com/en/morocco/jobs/lean-jobs/",
 "linkedin_guest": "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=lean%20six%20sigma&location=Morocco&start=0",
 "remoteok": "https://remoteok.com/api",
 "wwr_rss": "https://weworkremotely.com/remote-jobs.rss",
 "workingnomads": "https://www.workingnomads.com/api/exposed_jobs/",
 "himalayas": "https://himalayas.app/jobs/api?limit=20",
 "jooble_ma": "https://ma.jooble.org/emploi-lean-six-sigma",
 "novojob": "https://www.novojob.com/maroc/offres-emploi?keywords=lean",
 "dreamjob": "https://www.dreamjob.ma/?s=lean",
 "anapec": "https://www.anapec.org/sigec-app-rv/fr/offres",
 "indeed_ma": "https://ma.indeed.com/jobs?q=lean+six+sigma",
 "glassdoor": "https://www.glassdoor.com/Job/morocco-lean-jobs-SRCH_IL.0,7_IN169_KO8,12.htm",
 "wttj": "https://www.welcometothejungle.com/fr/jobs?query=lean&refinementList%5Boffices.country_code%5D%5B%5D=MA",
 "mjob": "https://www.m-job.ma/recherche?q=lean",
 "menaraemploi": "https://www.menaraemploi.ma/?s=lean",
 "jobsquare": "https://www.jobsquare.ma/recherche?q=lean",
 "khadamat": "https://www.khadamat.ma/?s=lean",
 "stagiaires": "https://www.stagiaires.ma/?s=lean",
 "amaljob": "https://www.amaljob.com/?s=lean",
 "talent_ma": "https://www.talent.ma/offres-emploi?q=lean",
 "michaelpage": "https://www.michaelpage.ma/jobs",
 "fedafrica": "https://www.fedafrica.com/nos-offres-emploi",
 "manpower_ma": "https://www.manpower.ma/offres-emploi",
}

for name, url in targets.items():
    try:
        r = requests.get(url, headers=H, timeout=25, allow_redirects=True)
        body = r.text or ""
        print(f"{name:16s} {r.status_code} len={len(body):8d} ctype={r.headers.get('content-type','')[:40]}")
    except Exception as e:
        print(f"{name:16s} ERR {type(e).__name__}: {str(e)[:80]}")
    sys.stdout.flush()
