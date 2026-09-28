"""bhstudy_pdftext.py - crude text grep inside FlateDecode streams of a PDF (research aid, no install)."""
import re, sys, zlib
data = open(sys.argv[1], "rb").read()
pat = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
out = []
for m in pat.finditer(data):
    s = m.group(1)
    try:
        t = zlib.decompress(s)
    except Exception:
        continue
    # text-showing operators: (..) Tj and [..] TJ
    parts = re.findall(rb"[(]((?:[^()\\\\]|\\\\.)*)[)]", t)
    if parts:
        out.append(b"".join(parts).decode("latin-1"))
txt = "\n".join(out)
for kw in sys.argv[2:]:
    for mm in re.finditer(kw, txt, re.I):
        print("==", kw, ":", txt[max(0, mm.start()-200): mm.end()+500].replace("\n", " | "))
        print()
