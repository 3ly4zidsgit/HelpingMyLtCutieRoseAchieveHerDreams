import io

P = "merge.py"
lines = io.open(P, encoding="utf-8").read().split("\n")

# locate the damaged text-repair block: from the MOJI definition down to the
# line right before TEXT_FIELDS
start = next(i for i, l in enumerate(lines) if l.startswith("MOJI = re.compile"))
end = next(i for i, l in enumerate(lines) if l.startswith("TEXT_FIELDS = "))

block = '''MOJI = re.compile(
    "[\\u00c3\\u00c2\\u00e2][\\u0080-\\u00bf\\u2018-\\u201e\\u20ac\\u0161\\u0153\\u2122]")

def unmojibake(s):
    """Undo one round of 'UTF-8 bytes decoded as cp1252/latin-1'."""
    if not s or not MOJI.search(s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = s.encode(enc, "strict").decode("utf-8", "strict")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if not MOJI.search(fixed):
            return fixed
    return s

'''.split("\n")

lines[start:end] = block
io.open(P, "w", encoding="utf-8").write("\n".join(lines))
print(f"replaced lines {start+1}-{end} with {len(block)} lines")

import subprocess, sys
print(subprocess.run([sys.executable, "-c", "import merge; print('import OK');"
                      "print(merge.unmojibake('Les Eaux Min\\u00c3\\u00a9rales d\\u00e2\\u20ac\\u2122Oulm\\u00c3\\u00a8s'));"
                      "print(merge.unmojibake(\"HUIR - L'H\\u00c3\\u00b4pital\"));"
                      "print(merge.unmojibake('Casablanca'))"],
                     capture_output=True, text=True).stdout)
