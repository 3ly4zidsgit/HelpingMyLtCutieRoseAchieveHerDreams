import requests, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from common import HDRS
import s_ats  # reuse the MA regex

H = dict(HDRS); H["Accept"] = "application/json"
for loc in ["Rabat, Rabat-Salé-Kénitra, ma", "Casablanca, Casablanca-Settat, ma",
            "Fes, Fez-Meknès, ma", "New York, NY", "Rotterdam, Nederland",
            "Tetouan, Tangier-Tétouan-Al Hoceima, ma"]:
    print(f"  MA.search({loc!r}) -> {bool(s_ats.MA.search(loc))}")

print("\nlive check SmartRecruiters/alten:")
r = requests.get("https://api.smartrecruiters.com/v1/companies/alten/postings?limit=100&offset=0",
                 headers=H, timeout=25)
print("  status", r.status_code, "len", len(r.text))
if r.status_code == 200:
    d = r.json()
    print("  totalFound", d.get("totalFound"), "content", len(d.get("content", [])))
    ma = 0
    for j in d.get("content", [])[:100]:
        loc = j.get("location") or {}
        t = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x)
        if s_ats.MA.search(t): ma += 1
    print("  morocco-located in page 1:", ma)
else:
    print("  body:", r.text[:300])
