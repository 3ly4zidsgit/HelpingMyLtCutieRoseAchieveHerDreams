"""First pass over the international offers: auto-reject the ones whose own text
states a geographic / immigration / on-site bar. Whatever survives gets read
individually - the regex is only allowed to say NO, never YES."""
import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from common import norm

data = json.load(open("data/new_intl.json", encoding="utf-8"))

BLOCK = [
    (r"must (be (located|based|physically|resident|a resident)|reside|live) (in|within)", "residence imposee"),
    (r"(authoriz|authoris)(ed|ation) to work|right to work in|eligible to work in|work permit",
     "autorisation de travail exigee"),
    (r"visa sponsorship|cannot sponsor|no sponsorship|sponsorship (is )?not", "pas de sponsoring visa"),
    (r"u\.?s\.? citizen|green card|security clearance", "citoyennete/habilitation US"),
    (r"\bhybrid\b|\bon[- ]?site\b|\bonsite\b|\bin[- ]office\b|on the (manufacturing )?floors?",
     "presence sur site"),
    (r"relocat", "relocalisation"),
    (r"travel[^.]{0,25}\d{2}\s?%|~?\s?\d{2}\s?%\s?(travel|onsite)", "deplacements majoritaires"),
    (r"remote \((eu|uk|us|usa|emea|latam|apac|canada|europe)[^)]*\)", "remote limite a une zone"),
    (r"\b(us|usa|u\.s\.) (only|based candidates)", "US uniquement"),
    (r"candidates? must be", "condition de candidature geographique"),
]
BLOCK = [(re.compile(p, re.I), why) for p, why in BLOCK]

# A country in the location field that is not a global marker is itself a strong
# signal, but not proof - those go to manual reading, not auto-reject.
GLOBALISH = re.compile(r"worldwide|anywhere|global|remote|international|europe$", re.I)

GLOBAL_TXT = re.compile(
    r"work from anywhere|anywhere in the world|from any country|any time ?zone|"
    r"globally distributed|fully distributed|location[- ]independent|"
    r"no matter where you (are|live)|work remotely from anywhere|"
    r"remote[- ]first|hire globally|talent (from )?(all over|around) the world|"
    r"\bworldwide\b|\bglobal\+|location: remote\b|100% remote", re.I)
GLOBAL_LOC = re.compile(r"worldwide|anywhere|^global$|globally|international \(remote\)|"
                        r"^remote$|latam.*canada.*usa|emea.*latam", re.I)

rejected, survivors = [], []
for o in data:
    blob = norm(o["evidence"] + " " + o["title"])
    why = next((w for p, w in BLOCK if p.search(blob)), None)
    if why:
        rejected.append({**o, "why": why}); continue
    # A location scoped to one country IS the visa barrier, stated or not:
    # holding it requires the right to work there. Silence is not permission.
    loc_global = bool(GLOBAL_LOC.search(norm(o["loc"])) or GLOBAL_LOC.search(norm(o["country"])))
    txt_global = bool(GLOBAL_TXT.search(blob))
    if not (loc_global or txt_global):
        rejected.append({**o, "why": f"poste rattache a un pays ({o['country'][:22]}) "
                                     f"sans mention d'ouverture mondiale"})
        continue
    survivors.append(o)

print(f"{len(data)} offres internationales")
print(f"  auto-rejetees (barriere citee dans l'annonce) : {len(rejected)}")
print(f"  a lire une par une                            : {len(survivors)}\n")

from collections import Counter
print("motifs de rejet:", Counter(r["why"] for r in rejected).most_common(), "\n")

json.dump(survivors, open("data/intl_survivors.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(rejected, open("data/intl_rejected.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

for o in survivors:
    print(f"[{o['i']}] {o['title'][:66]}")
    print(f"     {o['company'][:26]} | loc={o['loc'][:24]} | {o['country'][:22]} | {o['src'][:16]}")
    print(f"     {o['evidence'][:420]}")
    print()
