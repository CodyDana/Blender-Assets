"""Trace pilot stage 1: pixel classes + element ownership on the reference throat.  Output: work/seg.npz, overlays."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G, tp_rois as RO
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
R0, R1, C0, C1 = 20, 190, 415, 597
a = np.load(OUT + "/ref_full.npy")[R0:R1, C0:C1, :3]
lum = a @ np.array([0.2126, 0.7152, 0.0722])
H, W = lum.shape
X, Y = G.grid(R0, R1, C0, C1)          # pixel centres in ref px
# ---- background: flood from the border through bright pixels
border = np.zeros_like(lum, bool); border[0] = border[-1] = True; border[:, 0] = border[:, -1] = True
bg = G.flood(border & (lum > 0.86), lum > 0.86)
# below row 172 the body continues: everything non-bg is sheath
sil = ~bg
dark = (lum < 0.24) & sil
# ---- ownership
own = np.zeros((H, W), int)       # 0 = base shell
names = ["base"]
def mirror(poly): return [(2 * RO.AXIS - x, y) for x, y in poly]
for roi in RO.ROIS:
    name, kind = roi[0], roi[1]
    if roi[2] == "circle":
        (cx, cy), r = roi[3], roi[4]
        polys = {"L": [(cx + r*np.cos(t), cy + r*np.sin(t)) for t in np.linspace(0, 2*np.pi, 40, endpoint=False)]}
    else:
        polys = {"L": roi[2]}
    if kind == "pair":
        polys["R"] = mirror(polys["L"])
        for side, p in polys.items():
            names.append(f"{name}_{side}"); own[G.pip(X, Y, p) & sil] = len(names) - 1
    else:
        full = list(polys["L"]) + mirror(polys["L"])[::-1][1:-1]
        names.append(name); own[G.pip(X, Y, full) & sil] = len(names) - 1
np.savez(OUT + "/seg.npz", lum=lum, rgb=a, bg=bg, dark=dark, own=own, names=np.array(names), R0=R0, C0=C0)
# ---- overlay
rng = np.random.default_rng(3)
cols = rng.uniform(0.2, 1.0, (len(names), 3)); cols[0] = [0.5, 0.5, 0.5]
tint = a.copy()
m = sil
tint[m] = 0.55 * a[m] + 0.45 * cols[own[m]]
tint[dark] = tint[dark] * 0.6
S = 6
big = tp_img.resize(tint, S)
# boundaries of ownership
o6 = tp_img.resize(own.astype(float), S)
edge = (np.abs(np.diff(o6, axis=0, prepend=o6[:1])) > 0) | (np.abs(np.diff(o6, axis=1, prepend=o6[:, :1])) > 0)
big[edge] = [0, 0, 0]
tp_img.save(OUT + "/seg_overlay_x6.png", big)
print("names", list(names))
print("sil px", sil.sum(), "dark px", dark.sum())
