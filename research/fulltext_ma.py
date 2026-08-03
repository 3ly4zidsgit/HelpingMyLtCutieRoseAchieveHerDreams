"""fulltext, but only for the Moroccan rows that still have no body.

`run.py fulltext` walks every shipping row. After a remote sweep that is 2 800
URLs, 2 300 of which are international offers the visa gate will refuse anyway -
hours of UC mode for nothing. The workbook only ever ships Morocco plus the rare
visa-free remote, so that is what gets fetched."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
from core import Run
import run as R
import fulltext as F

run = Run(os.path.join(ROOT, "spec.json"))
rows = R.shipping(run)
ft = json.load(open(os.path.join(run.datadir, "fulltext.json"), encoding="utf-8"))
todo = [x for x in rows
        if x.get("country") == "Maroc"
        and not (ft.get(x["url"]) or {}).get("text")]
print(f"{len(rows)} lignes livrables, {len(todo)} marocaines sans texte integral")
F.harvest(run, todo)
