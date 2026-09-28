"""Survey: how the shipped tint-ready Detail maps behave under a LIGHT recolour (read-only).

For each part: n = bias + scale * decode(Detail) (mean ~1), and for Colour = c:
  - E[n^C] for C = 0.5 / 0.75 (the normalisers the softening needs)
  - fraction of texels whose albedo = c * n^C / E[n^C] exceeds 0.80 / 0.95 / 1.0 for a white c = 0.75
Run: blender -b --factory-startup --python survey_recolour_headroom.py -- out.json
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Exports")
OUT = Path(sys.argv[sys.argv.index("--") + 1])


def grey(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[..., 0].astype(np.float64)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


parts = {}
sb = json.loads((ROOT / "SmokeBomb/SM_SmokeBomb.sockets.json").read_text())["material"]
d = s2l(grey(ROOT / "SmokeBomb/Textures/T_SmokeBomb_Detail.png"))
m = d.mean()
parts["SmokeBomb_Cloth"] = (d, 0.0, 1.0 / m, [t * m for t in sb["tint_default_linear"]])
bh = json.loads((ROOT / "BlackHat/SM_BlackHat.sockets.json").read_text())["materials"]
for part in ("Straw", "Cloth"):
    mm = bh[f"M_BlackHat_{part}"]
    d = s2l(grey(ROOT / f"BlackHat/Textures/T_BlackHat_{part}_Detail.png"))
    parts[f"BlackHat_{part}"] = (d, mm["detail_bias_default"], mm["detail_scale_default"], mm["tint_default_linear"])

res = {}
for name, (d, bias, scale, colour) in parts.items():
    n = bias + scale * d
    r = {"bias": bias, "scale": scale, "colour_default_linear": [round(c, 6) for c in colour],
         "colour_default_luminance": round(0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2], 6),
         "n_mean": round(float(n.mean()), 6), "n_max": round(float(n.max()), 4),
         "default_albedo_max": round(float(max(colour) * n.max()), 4)}
    for C in (1.0, 0.75, 0.5):
        nc = np.power(np.maximum(n, 1e-6), C)
        e = float(nc.mean())
        r[f"E[n^{C}]"] = round(e, 6)
        a = 0.75 * nc / e
        r[f"white0.75_C{C}"] = {f"frac_over_{t}": round(float((a > t).mean()), 5) for t in (0.8, 0.95, 1.0)}
        r[f"white0.75_C{C}"]["p99"] = round(float(np.percentile(a, 99)), 4)
        r[f"white0.75_C{C}"]["p50"] = round(float(np.percentile(a, 50)), 4)
    res[name] = r
OUT.write_text(json.dumps(res, indent=1))
print("WROTE", OUT)
