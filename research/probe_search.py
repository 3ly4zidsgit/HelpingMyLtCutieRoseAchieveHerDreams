import requests, re, sys
from bs4 import BeautifulSoup
from common import HDRS

S = requests.Session(); S.headers.update(HDRS)
Q = "Aptiv Maroc site officiel entreprise"

def show(name, r, sel):
    if r is None: print(f"{name:14s} FAIL"); return
    print(f"{name:14s} {r.status_code} len={len(r.text)}")
    s = BeautifulSoup(r.text, "html.parser")
    for a in s.select(sel)[:4]:
        print("    ", a.get_text(" ", strip=True)[:52], "|", (a.get("href") or "")[:90])

try: show("ddg-post", S.post("https://html.duckduckgo.com/html/", data={"q": Q}, timeout=15), "a.result__a")
except Exception as e: print("ddg-post ERR", e)
try: show("ddg-get", S.get("https://html.duckduckgo.com/html/", params={"q": Q}, timeout=15), "a.result__a")
except Exception as e: print("ddg-get ERR", e)
try: show("ddg-lite", S.get("https://lite.duckduckgo.com/lite/", params={"q": Q}, timeout=15), "a")
except Exception as e: print("ddg-lite ERR", e)
try: show("mojeek", S.get("https://www.mojeek.com/search", params={"q": Q}, timeout=15), "a.ob, h2 a")
except Exception as e: print("mojeek ERR", e)
try: show("bing", S.get("https://www.bing.com/search", params={"q": Q}, timeout=15), "h2 a")
except Exception as e: print("bing ERR", e)
try: show("search.marcia", S.get("https://search.marcia.cc/search", params={"q": Q}, timeout=15), "a")
except Exception as e: print("marcia ERR", e)
try: show("startpage", S.get("https://www.startpage.com/sp/search", params={"query": Q}, timeout=15), "a.result-link, h2 a")
except Exception as e: print("startpage ERR", e)
try: show("ecosia", S.get("https://www.ecosia.org/search", params={"q": Q}, timeout=15), "a.result__link, h2 a")
except Exception as e: print("ecosia ERR", e)
try: show("brave", S.get("https://search.brave.com/search", params={"q": Q}, timeout=15), "a.result-header, h2 a, a[href^='http']")
except Exception as e: print("brave ERR", e)
