import sys, re
from bs4 import BeautifulSoup
from sel_common import driver, get

d = driver(headless=True)
urls = [
 "https://www.bayt.com/en/morocco/jobs/lean-jobs/?page=2",
 "https://www.bayt.com/en/morocco/jobs/six-sigma-jobs/",
 "https://www.bayt.com/en/morocco/jobs/continuous-improvement-jobs/",
 "https://www.bayt.com/en/morocco/jobs/?q=lean+six+sigma",
 "https://www.bayt.com/en/morocco/jobs/industrial-engineer-jobs/",
 "https://www.bayt.com/en/morocco/jobs/quality-engineer-jobs/",
 "https://www.bayt.com/en/morocco/jobs/supply-chain-jobs/",
 "https://www.bayt.com/en/morocco/jobs/production-jobs/",
 "https://www.bayt.com/en/morocco/jobs/amelioration-continue-jobs/",
 "https://www.bayt.com/en/uae/jobs/lean-jobs/",
]
try:
    for u in urls:
        html = get(d, u, wait_css="li[data-js-job]", timeout=25, settle=3.0)
        s = BeautifulSoup(html, "html.parser")
        n = len(s.select("li[data-js-job]"))
        cnt = ""
        h = s.select_one("h1, .u-stretch span")
        m = re.search(r"([\d,]+)\s+jobs?\s+found", s.get_text(" ", strip=True)[:4000], re.I)
        if m: cnt = m.group(1)
        print(f"{n:3d} cards | total='{cnt}' | {u}")
        sys.stdout.flush()
finally:
    d.quit()
