import requests, sys
from common import HDRS
S = requests.Session(); S.headers.update(HDRS)
T = {
 "jobgether":     "https://jobgether.com/api/v1/offers?page=1&limit=50",
 "jobgether2":    "https://api.jobgether.com/offers?page=1",
 "remoteco":      "https://remote.co/api/jobs",
 "nodesk":        "https://nodesk.co/remote-jobs/feed/",
 "jobspresso":    "https://jobspresso.co/feed/",
 "dynamitejobs":  "https://dynamitejobs.com/api/jobs",
 "pangian":       "https://pangian.com/job-travel-remote/feed/",
 "justremote":    "https://justremote.co/api/jobs",
 "remoterocket":  "https://www.remoterocketship.com/api/jobs",
 "wellfound":     "https://wellfound.com/api/jobs",
 "remoteok_rss":  "https://remoteok.com/remote-jobs.rss",
 "weworkrem_all": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
 "remotive_all":  "https://remotive.com/api/remote-jobs?limit=200",
 "himalayas_ct":  "https://himalayas.app/jobs/api?limit=100&offset=0",
 "workingnomads": "https://www.workingnomads.com/api/exposed_jobs/",
 "arbeitnow":     "https://www.arbeitnow.com/api/job-board-api?page=1",
 "openrole":      "https://api.openroles.dev/jobs",
 "hnhiring":      "https://hacker-news.firebaseio.com/v0/item/1.json",
}
for k, u in T.items():
    try:
        r = S.get(u, timeout=20)
        ct = r.headers.get("content-type", "")[:32]
        print(f"{k:15s} {r.status_code} len={len(r.text):8d} {ct}")
    except Exception as e:
        print(f"{k:15s} ERR {type(e).__name__}: {str(e)[:50]}")
    sys.stdout.flush()
