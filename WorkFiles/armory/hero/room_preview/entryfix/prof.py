"""entryfix r2: compact luminance profiles of the entry foreground (reference 2 vs a render), for landmark reads."""
import sys
import numpy as np
from PIL import Image
REF = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png"
p = sys.argv[1]
cols = [int(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else [130, 300, 730, 1150, 1320]
rows = [int(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else [960, 1000, 1050]
for name, path in (("ref", REF), ("ours", p)):
    a = np.asarray(Image.open(path).convert("RGB"), float) @ [0.2126, 0.7152, 0.0722]
    for x in cols:
        c = a[780:1086, x - 2:x + 3].mean(1)
        print(name, "x", x, " ".join(f"{780 + i}:{int(v)}" for i, v in enumerate(c) if i % 4 == 0))
    for y in rows:
        r = a[y - 2:y + 3].mean(0)
        print(name, "y", y, " ".join(f"{i}:{int(r[i])}" for i in range(0, 1448, 8)))
