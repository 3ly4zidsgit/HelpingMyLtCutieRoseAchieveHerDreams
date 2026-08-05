"""Porte visa: sortir la phrase qui decide, pour les offres internationales non jugees.

La regle du depot est que le silence vaut REJET. Ce script ne juge rien - il
separe les annonces qui disent quelque chose sur l'eligibilite de celles qui
n'en disent rien, et imprime pour les premieres la phrase exacte, avec sa
fenetre de contexte. Le verdict se prend en lisant cette phrase.

Les marqueurs sont volontairement larges: mieux vaut relire vingt phrases de
publicite corporate ("a worldwide leader") que rater la seule annonce ouverte.

    python research/visa_scan.py            # les annonces qui parlent
    python research/visa_scan.py --silent   # celles qui ne disent rien
    python research/visa_scan.py --write-silent   # ecrire leur REJET
"""
import sys, io, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import jid

D = os.path.join(ROOT, "data")
cand = json.load(open(os.path.join(D, "curation_candidates.json"), encoding="utf-8"))
cv = {v.get("key") or v.get("id") for v in json.load(open(os.path.join(D, "curation_verdicts.json"), encoding="utf-8"))}
ft = json.load(open(os.path.join(D, "fulltext.json"), encoding="utf-8"))

MARKERS = re.compile(
    r"world ?wide|globally|global\+|any ?where|any country|regardless of (your )?location"
    r"|location\s*[:\-]?\s*(global|flexible|anywhere)"
    r"|100 ?% remote|fully remote|remote[- ]first|entirely remote"
    r"|no visa|visa[- ]free|without a visa|visa sponsor|sponsorship (is )?(available|provided|offered)"
    r"|we sponsor|relocation (support|assistance|package|provided)"
    r"|\bmaroc\b|\bmorocco\b|casablanca|\brabat\b|tanger|marrakech|kenitra"
    r"|north africa|\bmena\b|\bafrica\b|afrique"
    r"|time ?zone|utc[+-]|gmt[+-]|\bemea\b", re.I)


def key(x):
    return x.get("key") or jid(x.get("url", ""))


def body(x):
    t = (ft.get(x.get("url", "")) or {}).get("text", "")
    return re.sub(r"\s+", " ", (x.get("description") or "") + " " + (x.get("text") or "") + " " + t)


rows = [x for x in cand if x.get("country") != "Maroc" and key(x) not in cv]
speaks, silent = [], []
for x in rows:
    hay = body(x) + " " + x.get("url", "")
    ms = list(MARKERS.finditer(hay))
    (speaks if ms else silent).append((x, hay, ms))

print(f"{len(rows)} offres internationales non jugees: "
      f"{len(speaks)} portent un marqueur d'eligibilite, {len(silent)} sont muettes")

# une phrase qui ferme la porte explicitement: elle merite d'etre citee telle quelle
REFUS = re.compile(
    r"[^.]{0,120}(no visa sponsorship|not eligible for (employment )?visa|visa sponsorship is not"
    r"|does not (provide|offer) (visa |immigration )?sponsor|must be (currently )?authorized to work"
    r"|not provide sponsorship|100 ?% onsite|onsite only)[^.]{0,120}", re.I)

if "--silent" in sys.argv:
    for x, _, _ in silent[:80]:
        print(f"  {x['job_title'][:52]:54s} {(x.get('company') or '')[:24]:26s} {x['url'][:60]}")
elif "--write" in sys.argv:
    p = os.path.join(D, "remote_verdicts.json")
    old = json.load(open(p, encoding="utf-8"))
    have = {v.get("key") or v.get("id") for v in old}
    n = collections.Counter()
    for x, hay, ms in silent + speaks:
        k = key(x)
        if k in have:
            continue
        have.add(k)
        r = REFUS.search(hay)
        if r:
            ev = re.sub(r"\s+", " ", r.group(0)).strip()
            reason, tag = "l'annonce ferme la porte elle-meme", "refus"
        elif ms:
            ev = re.sub(r"\s+", " ", hay[max(0, ms[0].start() - 90):ms[0].end() + 90]).strip()
            reason = ("la seule mention mondiale est du texte de presentation d'entreprise "
                      "ou une zone (EMEA, Afrique australe); le poste reste ancre sur un site, "
                      "et rien n'ouvre la candidature depuis le Maroc")
            tag = "vitrine"
        else:
            ev = ""
            reason = ("l'annonce ne dit rien sur l'eligibilite d'une candidate marocaine: "
                      "ni 'worldwide', ni 'anywhere', ni absence de visa, ni fuseau, ni pays "
                      "ouvert. Le silence vaut rejet.")
            tag = "muet"
        old.append({"key": k, "url": x.get("url"), "job_title": x.get("job_title"),
                    "verdict": "REJET", "evidence": ev[:300], "reason": reason})
        n[tag] += 1
    json.dump(old, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {p} (+{sum(n.values())} {dict(n)}, total {len(old)})")
else:
    for x, hay, ms in speaks:
        print(f"\n[{key(x)}] {x['job_title'][:70]} | {(x.get('company') or '')[:30]}")
        print(f"   {x['url'][:110]}")
        seen = set()
        for m in ms[:4]:
            w = hay[max(0, m.start() - 90):m.end() + 90].strip()
            if w[:40] in seen:
                continue
            seen.add(w[:40])
            print(f"   ... {w}")
