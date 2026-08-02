import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import Counter
from common import load, norm

rows = load("merged")
intl = [r for r in rows if r["country"] != "Maroc"]
print(f"international rows: {len(intl)}")
print("countries:", Counter(r["country"] for r in intl).most_common(20))
print()

GLOBAL_LOC = re.compile(r"worldwide|anywhere|global|remote|latam|emea|apac|europe|international")
GLOBAL_TXT = re.compile(
    r"work from anywhere|anywhere in the world|fully remote|100% remote|fully-remote|"
    r"remote[- ]first|globally distributed|any (country|location|time ?zone)|"
    r"no visa|visa[- ]free|worldwide|location[- ]independent|nomad")
BLOCKER = re.compile(
    r"must (be |reside|live|be located|be based|have)|"
    r"authoriz(ed|ation) to work|work authoriz|right to work|eligible to work|"
    r"visa sponsorship (is )?(not|un)available|cannot sponsor|no sponsorship|"
    r"sponsorship (is )?not|security clearance|us citizen|green card|"
    r"located in the (united states|us|uk)|based in the (united states|us|uk)|"
    r"hybrid|on[- ]site|onsite|in[- ]office|relocat|commut")

buckets = Counter()
sample_global = []
for r in intl:
    loc = norm(r.get("location_city", "") + " " + r.get("country", ""))
    txt = norm(r.get("description_snippet", ""))
    loc_global = bool(GLOBAL_LOC.search(loc)) and not re.search(
        r"\b(etats[- ]unis|united states|usa|royaume[- ]uni|canada|allemagne|france|suisse|"
        r"irlande|espagne|portugal|italie|belgique|pays[- ]bas|pologne|inde|australie)\b", loc)
    txt_global = bool(GLOBAL_TXT.search(txt))
    blocked = bool(BLOCKER.search(txt))
    if (loc_global or txt_global) and not blocked:
        buckets["GLOBAL-OK"] += 1
        sample_global.append(r)
    elif blocked:
        buckets["blocked (visa/onsite)"] += 1
    else:
        buckets["country-bound remote"] += 1

print("classification:", buckets)
print(f"\n--- {len(sample_global)} candidates fully-remote/worldwide ---")
for r in sample_global[:30]:
    print(f"  {r['job_title'][:48]:48s} | {r['company'][:20]:20s} | "
          f"{(r['location_city'] or '')[:18]:18s} | {r['country'][:16]:16s} | "
          f"{r['source'].split(' ; ')[0][:14]}")
print()
print("desc availability on intl rows:",
      sum(1 for r in intl if len(r.get("description_snippet", "")) > 80), "/", len(intl))
