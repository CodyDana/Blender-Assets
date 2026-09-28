import json, sys
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
p = json.loads((P / "Exports/PaperBomb/Textures/Recolour/recolour_maps.json").read_text())["parts"]["Tag"]["params"]
pd8, _, _ = rc.png_read(P / "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_PaperDetail.png")
iw8, _, _ = rc.png_read(P / "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_InkWeights.png")
w = rc.s2l(pd8[..., :3] / 255.0) * p["Paper Weight Scale"]
iw = iw8 / 255.0; pa = pd8[..., 3] / 255.0
paper = np.array(p["Paper Colour"][:3])
print("W max per channel", w.reshape(-1, 3).max(0), "p99.9", np.percentile(w.reshape(-1, 3), 99.9, axis=0), "p99", np.percentile(w.reshape(-1, 3), 99, axis=0))
print("default P x Wmax", paper * w.reshape(-1, 3).max(0))
# total with default inks
black = np.array(p["Black Ink Colour"][:3]); red = np.array(p["Red Ink Colour"][:3])
def tot(P_):
    bd = (black + (P_ - black) * p["Black Ink Dry Paper Mix"]) * np.array(p["Black Ink Dry Gain"][:3])
    rd = rc.s2l(np.clip(p["Red Ink Dry Value Scale"] * rc.l2s(red), 0, 1))
    y = red @ rc.LUM; rp = (y + (red - y) * p["Red Ink Pool Saturation"]) * np.array(p["Red Ink Pool Gain"][:3])
    return P_ * w + black * iw[..., 0:1] + bd * iw[..., 1:2] + red * iw[..., 2:3] + rd * iw[..., 3:4] + rp * pa[..., None]
t = tot(paper)
print("default total max per channel", t.reshape(-1, 3).max(0), "frac > 0.962", (t > 0.962).any(-1).mean())
wm = w.reshape(-1, 3).max(0)
for h in ["FFFFFF", "FF0000", "0000FF", "F2E8D5", "E7E7E7"]:
    pk = rc.s2l(np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0)
    s = min(1.0, 0.962 / float((pk * wm).max()))
    tt = tot(pk * s)
    print(h, "scale", round(s, 4), "eff", np.round(pk * s, 4), "hex", "".join(f"{v:02X}" for v in rc.q8_srgb(pk * s)), "max tot", tt.reshape(-1, 3).max(0).round(4), "clip frac", (tt > 0.962).any(-1).mean())
