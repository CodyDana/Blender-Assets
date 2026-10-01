"""r20 look: floor pixel stats in C1 (1448x1086): floor mask = boxes on open floor; split into dark / mid / bright thirds
by value. Usage: floorstats.py img [img...]"""
import sys, json
import numpy as np
from PIL import Image
import colorstats as C
BOXES = [(200, 700, 520, 880), (930, 700, 1230, 880), (420, 470, 600, 560), (860, 460, 1000, 560), (600, 830, 900, 880)]
def stats(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255
    px = np.concatenate([a[b[1]:b[3], b[0]:b[2]].reshape(-1, 3) for b in BOXES])
    v = px.max(1); out = {}
    for lo, hi, n in ((0, .33, "dark"), (.33, .66, "mid"), (.66, 1.0, "bright")):
        q = np.quantile(v, [lo, hi]); m = px[(v >= q[0]) & (v <= q[1])]
        s = C.srgb(C.lin(m).mean(0)); out[n] = ([int(round(float(x) * 255)) for x in s], C.hsv_of(s))
    s = C.srgb(C.lin(px).mean(0)); out["all"] = ([int(round(float(x) * 255)) for x in s], C.hsv_of(s))
    return out
for p in sys.argv[1:]:
    print(p.replace("\\", "/").split("/")[-3:], json.dumps(stats(p)))
