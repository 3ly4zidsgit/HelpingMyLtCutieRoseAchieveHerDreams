import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import merge

cases = [
    "Les Eaux MinÃ©rales dâ€™OulmÃ¨s",
    "HUIR - L'HÃ´pital Universitaire",
    "IngÃ©nieur AmÃ©lioration Continue",
    "Casablanca",
    "Ingénieur Méthodes",
]
for c in cases:
    out = merge.unmojibake(c)
    print(f"{c!r}\n  -> {out!r}\n  -> {out}\n")
print("MOJI pattern:", merge.MOJI.pattern.encode("unicode_escape").decode())
