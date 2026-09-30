"""Mean sRGB / HSV of every probe card (boxes projected by dj_sc_colour_probe.py) in every variant's probe captures.
Run: py -3 measure_probe.py <probe dir>   ->  <probe dir>/probe_cards.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

d = Path(sys.argv[1])
P = json.loads((d / "probe.json").read_text(encoding="utf-8"))
out = {}
for vname, rec in P["variants"].items():
    out[vname] = {}
    for cam, boxes in P["cards"].items():
        f = d / vname / f"{cam}.png"
        if not f.exists():
            continue
        im = np.asarray(Image.open(f).convert("RGB"), dtype=np.float64)
        for name, b in boxes.items():
            x0, y0, x1, y1 = b["box_px"]
            a = im[max(y0, 0):y1, max(x0, 0):x1].reshape(-1, 3)
            m = a.mean(0)
            h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
            out[vname][name] = {"rgb": [round(float(c), 1) for c in m], "sat": round(s, 3), "hue": round(h * 360, 1)}
(d / "probe_cards.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for vname, cards in out.items():
    print(vname)
    print("   " + "  ".join(f"{k}={tuple(int(round(c)) for c in v['rgb'])} s{v['sat']:.2f}" for k, v in cards.items()))
