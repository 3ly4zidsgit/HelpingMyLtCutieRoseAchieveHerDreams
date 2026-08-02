import json
from collections import Counter
d = json.load(open("data/merged.json", encoding="utf-8"))
print("rows", len(d))
fields = ["job_title","company","contract_type","experience_required","education_level",
          "location_city","country","remote","sector","function","positions","salary",
          "date_posted","date_posted_iso","deadline","deadline_iso","recruiter_or_hr",
          "contact_email","company_email","company_website","url","description_snippet"]
for f in fields:
    n = sum(1 for r in d if r.get(f))
    print(f"{f:22s} {n:4d}  {100*n/len(d):5.1f}%")
print()
print("sources:", Counter(r["source"].split(" ; ")[0] for r in d).most_common())
print()
print("top MA cities:", Counter(r["location_city"] for r in d if r["country"] == "Maroc").most_common(14))
print()
print("countries:", Counter(r["country"] for r in d).most_common(12))
print()
print("contract types:", Counter(r["contract_type"] for r in d if r["contract_type"]).most_common(10))
print()
print("--- 10 most recent ---")
for r in sorted([x for x in d if x["date_posted_iso"]], key=lambda x: x["date_posted_iso"], reverse=True)[:10]:
    print(" ", r["date_posted_iso"], "|", r["job_title"][:44], "|", r["company"][:22], "|",
          r["location_city"][:16], "|", r["source"].split(" ; ")[0][:14])
