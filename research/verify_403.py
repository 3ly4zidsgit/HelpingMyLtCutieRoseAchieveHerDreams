import re, sys
from bs4 import BeautifulSoup
from sel_common import driver, get

URLS = [
 "https://www.bayt.com/en/morocco/jobs/chef-de-projet-black-belt-f-h-74807771/",
 "https://www.bayt.com/en/morocco/jobs/value-management-officer-74595556/",
 "https://ma.jooble.org/desc/-9137505351757062623?ckey=lean&rgn=-1&pos=1",
 "https://ma.jooble.org/desc/6619592889797180611?ckey=lean&rgn=-1&pos=7",
]
d = driver(headless=True)
try:
    for u in URLS:
        html = get(d, u, wait_css="h1, h2", timeout=15, settle=2.5)
        s = BeautifulSoup(html, "html.parser")
        title = (s.title.get_text(strip=True) if s.title else "")[:70]
        h1 = s.select_one("h1")
        print(f"len={len(html):7d} | title={title}")
        print(f"        h1={re.sub(r'  +',' ', h1.get_text(' ', strip=True))[:70] if h1 else '-'}")
        sys.stdout.flush()
finally:
    d.quit()
