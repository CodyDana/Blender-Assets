import sys
import numpy as np
from PIL import Image
for p in sys.argv[1:]:
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)
    L = a @ [0.299, 0.587, 0.114]
    row = L[999:1002].mean(0)
    print(p.split("/")[-1])
    print(" y1000 L:", " ".join(f"{x}:{int(row[x])}" for x in range(370, 450, 2)))
    print(" y1000 R:", " ".join(f"{x}:{int(row[x])}" for x in range(1005, 1080, 2)))
    col = L[:, 721:728].mean(1)
    print(" x724 top:", " ".join(f"{y}:{int(col[y])}" for y in range(922, 958)))
    print(" x724 bot:", " ".join(f"{y}:{int(col[y])}" for y in range(1060, 1086)))
    for nm, (x0, x1, y0, y1) in (("shadeF", (700, 900, 960, 1050)), ("sunF", (450, 560, 1040, 1066))):
        b = a[y0:y1, x0:x1].reshape(-1, 3); l = L[y0:y1, x0:x1]
        m = b.mean(0)
        print(f" {nm}: rgb {m.round(0)} R/B {m[0]/m[2]:.2f} L {l.mean():.0f} std/mean {l.std()/l.mean():.3f}")
