"""Dump the requirement block of an ad body, by verdict key.
    python research/show.py <key> [<key> ...]"""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import jid

full = json.load(open(os.path.join(ROOT, "data", "fulltext.json"), encoding="utf-8"))
by_key = {jid(u): (u, d) for u, d in full.items()}

ANCHOR = re.compile(r"profil recherch|profil\s*:|votre profil|qualifications|requirements|"
                    r"required profile|exp[ée]rience|experience|comp[ée]tences requises|"
                    r"we are looking for|candidate profile|type de contrat|secteur|"
                    r"date limite|contrat", re.I)

for k in sys.argv[1:]:
    u, d = by_key.get(k, ("", {}))
    if not u:
        print(f"=== {k}: ABSENT de fulltext.json\n")
        continue
    body = re.sub(r"[ \t]+", " ", d.get("text", ""))
    print(f"=== {k} {u}")
    spans, last = [], -1
    for m in ANCHOR.finditer(body):
        a, b = max(0, m.start() - 200), min(len(body), m.start() + 500)
        if a <= last:
            spans[-1] = (spans[-1][0], b)
        else:
            spans.append((a, b))
        last = b
    for a, b in spans[:6]:
        print("   ..." + re.sub(r"\s+", " ", body[a:b]))
    print()
