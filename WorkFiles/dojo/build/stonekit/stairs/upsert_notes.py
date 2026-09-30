"""Upsert track 9's section into the shared WorkFiles/dojo/build/stonekit/BUILD_NOTES.md between markers, under the
sk_shared file lock (other tracks' text is kept as it is). Run with Blender's or the system Python: py -3 upsert_notes.py"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent / "BUILD_NOTES.md"
BEGIN, END = "<!-- track9-stairs:begin -->", "<!-- track9-stairs:end -->"
sec = (HERE / "BUILD_NOTES_section.md").read_text(encoding="utf-8").strip()
lk = Path(str(NOTES) + ".lock")
t0 = time.time()
while True:
    try:
        fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        break
    except FileExistsError:
        if time.time() - t0 > 120:
            sys.exit("BUILD_NOTES.md lock held")
        time.sleep(0.5)
try:
    txt = NOTES.read_text(encoding="utf-8") if NOTES.exists() else "# Dojo stone kit: BUILD NOTES\n\n"
    block = f"{BEGIN}\n{sec}\n{END}"
    if BEGIN in txt and END in txt:
        a, b = txt.index(BEGIN), txt.index(END) + len(END)
        txt = txt[:a] + block + txt[b:]
    else:
        txt = txt.rstrip() + "\n\n" + block + "\n"
    tmp = NOTES.with_suffix(".md.tmp")
    tmp.write_text(txt, encoding="utf-8")
    os.replace(tmp, NOTES)
    print("upserted", NOTES)
finally:
    lk.unlink()
