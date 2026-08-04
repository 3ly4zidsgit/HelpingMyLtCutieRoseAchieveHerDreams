"""Re-read the corpus already on disk with a second spec's eyes.

Four rounds of scraping left ~3 000 offers in data/raw_*.json, judged against one
specialty. 193 of them were refused as off-topic FOR LEAN - which says nothing
about whether they are off-topic for a commercial or graduate search. Their URLs
were fetched, their bodies are often already in data/fulltext.json. Nothing here
touches the network and nothing is invented: it is the same text, read with the
other spec's regexes.

It is also the free tuning loop. Run it, look at the titles, adjust the term
lists in spec_business.json, run it again - no scraping in between.

    python research/harvest_track2.py [spec_business.json] [--write]
"""
import sys, io, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run, jid, norm
import build as B

spec = next((a for a in sys.argv[1:] if not a.startswith("-")),
            os.path.join(ROOT, "spec_business.json"))
WRITE = "--write" in sys.argv
run = Run(spec)
src = os.path.join(ROOT, "data")

rows = []
for p in sorted(f for f in os.listdir(src) if f.startswith("raw_") and f.endswith(".json")):
    with open(os.path.join(src, p), encoding="utf-8") as f:
        rows += json.load(f)
print(f"corpus existant: {len(rows)} lignes brutes")

rows = B.finalize(rows)
# Re-score with THIS spec's eyes. The stored `score` was computed by the other
# track at scrape time, and strict_keep short-circuits on `score >= 10` - so
# without this every row the other search rated highly walks straight in, having
# matched nothing at all here.
scored = []
for r in rows:
    keep, score, hits = run.relevance(r.get("job_title", ""), r.get("description_snippet", ""))
    r["track"] = run.track          # they are being claimed by THIS search now
    r["score"] = score
    r["keywords_matched"] = ", ".join(hits)
    if keep:
        scored.append(r)
print(f"re-notees avec les regex de cette piste: {len(scored)} passent relevance()")
kept = [r for r in scored if run.strict_keep(r)]
ma = [r for r in kept if r.get("country") == "Maroc"]
print(f"apres dedupe: {len(rows)} | retenues par les regex du spec: {len(kept)} "
      f"| dont Maroc: {len(ma)}")

# what the other track already said about them - informative only, never binding:
# a Lean "keep:false" means off-topic for Lean, not off-topic here
cv = {}
p = os.path.join(src, "curation_verdicts.json")
if os.path.exists(p):
    cv = {v["key"]: v for v in json.load(open(p, encoding="utf-8")) if v.get("key")}
already = sum(1 for r in ma if jid(r["url"]) in cv)
refused = sum(1 for r in ma if not cv.get(jid(r["url"]), {}).get("keep", True))
print(f"deja vues par la porte Lean: {already} | dont refusees par elle: {refused} "
      f"(refus qui ne vaut que pour le genie industriel)")

full = {}
fp = os.path.join(src, "fulltext.json")
if os.path.exists(fp):
    full = json.load(open(fp, encoding="utf-8"))
withbody = [r for r in ma if (full.get(r["url"]) or {}).get("text")]
print(f"corps deja telecharge: {len(withbody)}/{len(ma)}")

print("\n--- les 60 premiers titres marocains retenus (a lire pour regler les regex) ---")
for r in sorted(ma, key=lambda x: -x.get("score", 0))[:60]:
    body = "corps" if (full.get(r["url"]) or {}).get("text") else "     "
    print(f"  {r.get('score', 0):3d} {body} {r['job_title'][:58]:60s} {r.get('company', '')[:24]}")

c = collections.Counter()
for r in ma:
    c[re.search(r"//([^/]+)", r["url"]).group(1).replace("www.", "")] += 1
print("\npar source:", dict(c.most_common()))

if not WRITE:
    print("\n(lecture seule - relancer avec --write pour deposer dans le datadir de la piste)")
    sys.exit()

os.makedirs(run.datadir, exist_ok=True)
run.save("raw_recovered", ma)
sub = {r["url"]: full[r["url"]] for r in ma if r["url"] in full}
with open(os.path.join(run.datadir, "fulltext.json"), "w", encoding="utf-8") as f:
    json.dump(sub, f, ensure_ascii=False)
print(f"-> {run.datadir}/raw_recovered.json ({len(ma)} offres) "
      f"et fulltext.json ({len(sub)} corps deja disponibles)")
