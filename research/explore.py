import requests, re, json
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
H = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

print("="*30, "REKRUTE")
r = requests.get("https://www.rekrute.com/offres.html?s=1&p=1&keyword=lean", headers=H, timeout=30)
s = BeautifulSoup(r.text, "html.parser")
lis = s.select("li.post-id")
print("li.post-id count:", len(lis))
if lis:
    print(lis[0].prettify()[:4000])

print("="*30, "LINKEDIN GUEST")
r = requests.get("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=lean%20six%20sigma&location=Morocco&start=0", headers=H, timeout=30)
s = BeautifulSoup(r.text, "html.parser")
cards = s.select("li")
print("li count:", len(cards))
if cards:
    print(cards[0].prettify()[:2500])
