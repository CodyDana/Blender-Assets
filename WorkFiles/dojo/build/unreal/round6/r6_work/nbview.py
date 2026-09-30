import sys
import numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
cams = sys.argv[3].split(",")
W, H = 960, 540
im = Image.new("RGB", (W * 2, H * ((len(cams) + 1) // 2)))
for i, c in enumerate(cams):
    a = np.asarray(Image.open(f"{src}/{c}.png").convert("RGB")).copy()
    nb = a.max(axis=2) < 12
    a[nb] = (255, 0, 0)
    im.paste(Image.fromarray(a).resize((W, H)), ((i % 2) * W, (i // 2) * H))
im.save(out)
