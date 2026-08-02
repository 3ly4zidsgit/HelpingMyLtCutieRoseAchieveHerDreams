"""Sample the offer links and report how many are still live."""
import requests, random, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from common import HDRS, load

rows = load("merged")
random.seed(7)
by_src = {}
for r in rows:
    by_src.setdefault(r["source"].split(" ; ")[0], []).append(r)

sample = []
for src, rs in by_src.items():
    sample += random.sample(rs, min(8, len(rs)))
print(f"checking {len(sample)} links across {len(by_src)} sources", flush=True)

def check(r):
    s = requests.Session(); s.headers.update(HDRS)
    try:
        resp = s.get(r["url"], timeout=15, allow_redirects=True, stream=True)
        code = resp.status_code
        resp.close()
    except Exception as e:
        return r, type(e).__name__
    return r, code

res = Counter(); bad = []
with ThreadPoolExecutor(max_workers=10) as ex:
    for f in as_completed([ex.submit(check, r) for r in sample]):
        r, code = f.result()
        src = r["source"].split(" ; ")[0]
        res[(src, code)] += 1
        if not isinstance(code, int) or code >= 400:
            bad.append((src, code, r["url"][:80]))

for (src, code), n in sorted(res.items()):
    print(f"  {src:24s} {str(code):14s} {n}")
print(f"\nOK: {sum(n for (s,c),n in res.items() if isinstance(c,int) and c<400)}/{len(sample)}")
for b in bad[:12]:
    print("  BAD:", b)
