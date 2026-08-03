"""Evidence for the shipping Moroccan rows that have never been field-ruled."""
import sys, os, re, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run, jid, norm
import run as R

run = Run(os.path.join(ROOT, "spec.json"))
rows = [r for r in R.shipping(run) if r.get("country") == "Maroc"]
fv = {x["key"] for x in json.load(open(os.path.join(run.datadir, "field_verdicts.json"),
                                       encoding="utf-8")) if x.get("key")}
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))
todo = [r for r in rows if jid(r["url"]) not in fv]
print(f"{len(rows)} lignes Maroc livrables, {len(todo)} jamais renseignees par lecture\n")

EXP = re.compile(r"[^.;\n|]{0,90}(?:\d{1,2}\s*(?:\+|a|à|-|to)?\s*\d{0,2}\s*(?:ans?|ann[ée]es?|mois|years?)"
                 r"[^.;\n|]{0,50}?(?:exp|of exp)|exp[ée]rience[^.;\n|]{0,50}?\d{1,2}\s*(?:ans?|years?|mois)"
                 r"|(?:minimum|au moins|at least)\s*\d{1,2}\s*(?:ans?|years?|mois)"
                 r"|exp[ée]rience\s*(?:requise|exig|obligatoire|souhait|confirm|significative|professionnelle|r[ée]ussie)"
                 r"|premi[èe]re exp[ée]rience|d[ée]butant|jeune dipl[oô]m|fra[iî]chement dipl[oô]m"
                 r"|sans exp[ée]rience|years of experience|profil recherch[ée])[^.;\n|]{0,110}", re.I)
LAB = re.compile(r"[^.;\n|]{0,45}(?:type de contrat|contrat\s*[:：]|type d.emploi|employment type"
                 r"|\bcdi\b|\bcdd\b|int[ée]rim|temps plein|secteurs?\s*[:：]|fonction\s*[:：]"
                 r"|ville\s*[:：]|lieu\s*[:：]|localisation|date limite|entreprise\s*[:：]"
                 r"|niveau d.[ée]tudes)[^.;\n|]{0,70}", re.I)

for r in todo:
    b = re.sub(r"[ \t]+", " ", (ft.get(r["url"]) or {}).get("text", ""))
    print(f"--- [{jid(r['url'])}] {r['job_title'][:60]}")
    print(f"    ENT={r.get('company','')!r} VILLE={r.get('location_city','')!r} "
          f"CTR={r.get('contract_type','')!r} EXP={r.get('experience_required','')!r} "
          f"SEC={r.get('sector','')!r} FON={r.get('function','')!r} DAT={r.get('date_posted','')!r}")
    if not b:
        print("    !! aucun texte integral;", re.sub(r"\s+", " ", r.get("description_snippet", ""))[:260])
        continue
    print("    head:", re.sub(r"\s*\n\s*", " ", b[:260]).strip())
    seen = set()
    for rx, tag in ((EXP, "EXP"), (LAB, "LAB")):
        n = 0
        for m in rx.finditer(b):
            s = re.sub(r"\s+", " ", m.group(0)).strip(" .;-|")[:135]
            if norm(s)[:40] in seen or len(s) < 8:
                continue
            seen.add(norm(s)[:40])
            print(f"    {tag}: {s}")
            n += 1
            if n >= 3:
                break
