"""Trace pilot: FRONT COMPARE at the reference view and scale.
Reads renders/front_throat_x4.png (ortho, the reference crop rows 20-190, cols 415-597 at 4 px per ref px) and writes
    front_compare.png   reference | ours | difference overlay (abs luminance difference, red; silhouette XOR:
                        magenta = ours only, cyan = reference only)
    front_compare_metrics.json   silhouette IoU (throat rows 28-172), mean abs lum diff, per-class tones ours vs ref
                                 (classes = the traced masks: rims, insets, petals; lacquer body rows 175-188)."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G
P = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot"
W = P + "/work"
R0, R1, C0, C1 = 20, 190, 415, 597
ref = np.load(W + "/ref_full.npy")[R0:R1, C0:C1, :3]
ours4 = tp_img.load(P + "/renders/front_throat_x4.png")[..., :3]
H, Wd = ref.shape[:2]
ours = ours4.reshape(H, 4, Wd, 4, 3).mean((1, 3))          # box-filter to the reference grid
L = lambda a: a @ np.array([0.2126, 0.7152, 0.0722])
lr, lo = L(ref), L(ours)
# silhouettes: the reference backdrop is ~0.99, ours is the studio backdrop (white, exposure-scaled): threshold on
# distance from each image's own backdrop colour
bg_r = np.median(np.r_[lr[:, :6].ravel(), lr[:, -6:].ravel()]); bg_o = np.median(np.r_[lo[:, :6].ravel(), lo[:, -6:].ravel()])
sr = np.abs(lr - bg_r) > 0.06; so = np.abs(lo - bg_o) > 0.06
rows = np.arange(R0, R1)[:, None] * np.ones((1, Wd))
zone = (rows >= 28) & (rows <= 172)
iou = float((sr & so & zone).sum() / max(((sr | so) & zone).sum(), 1))
both = sr & so & zone
mad = float(np.abs(lr - lo)[both].mean())
# classes
TP = json.load(open(W + "/trace_plates.json"))["plates"]; BF = json.load(open(W + "/blossom_fit.json"))
X, Y = G.grid(R0, R1, C0, C1)
rim = np.zeros((H, Wd), bool); ins = np.zeros((H, Wd), bool)
for nm, e in TP.items():
    if nm.startswith("crest"): continue
    o = G.pip(X, Y, np.array(e["outer"])); i = G.pip(X, Y, np.array(e["inset"])) if "inset" in e else np.zeros_like(o)
    rim |= o & ~i; ins |= i
cx, cy = BF["centre"]; bl = np.hypot(X - cx, Y - cy) < 34
rim = G.erode(rim & ~bl, 1); ins = G.erode(ins & ~bl, 1)
def petal_poly(phi, d0, d1, w, q, e, n=96, shrink=0.0):
    s = np.linspace(0, 1, n); hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    hw = np.maximum(hw - shrink, 0); u = d0 + shrink + s * (d1 - d0 - 2 * shrink)
    Q = np.vstack([np.c_[u, hw], np.c_[u[::-1], -hw[::-1]][1:-1]]); cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + Q[:, 0] * cu - Q[:, 1] * su, cy + Q[:, 0] * su + Q[:, 1] * cu]
pe = np.zeros((H, Wd), bool)
for pp in BF["petals"]: pe |= G.pip(X, Y, petal_poly(pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"], shrink=2.5))
lac = (rows >= 175) & (rows <= 188) & (np.arange(C0, C1)[None, :] > 478) & (np.arange(C0, C1)[None, :] < 492)
cls = {}
for nm, m in (("rims", rim), ("insets", ins), ("petals", pe), ("body_lacquer", lac)):
    cls[nm] = {"ref_p10_p50_p90": np.percentile(lr[m], [10, 50, 90]).round(3).tolist(),
               "ours_p10_p50_p90": np.percentile(lo[m], [10, 50, 90]).round(3).tolist(), "px": int(m.sum())}
met = {"frame": "reference rows 20-190, cols 415-597 (1 ref px = 0.687 mm); ours = ortho render at 4x box-filtered to 1x",
       "silhouette_iou_rows_28_172": round(iou, 4), "mean_abs_lum_diff_inside": round(mad, 4), "classes_display_lum": cls}
json.dump(met, open(P + "/front_compare_metrics.json", "w"), indent=1)
print(json.dumps(met, indent=1))
# image
r4 = tp_img.resize(ref, 4, kind='linear')
d = np.abs(lr - lo)
d4 = tp_img.resize(d, 4, kind='linear'); sr4 = tp_img.resize(sr.astype(float), 4) > 0.5; so4 = tp_img.resize(so.astype(float), 4) > 0.5
base = np.repeat(L(r4)[..., None], 3, 2) * 0.5 + 0.25
ov = base * (1 - np.clip(d4 * 2.5, 0, 1)[..., None]) + np.clip(d4 * 2.5, 0, 1)[..., None] * np.array([1.0, 0.1, 0.05])
ov[so4 & ~sr4] = [1, 0, 1]; ov[sr4 & ~so4] = [0, 0.9, 1]
gap = np.ones((r4.shape[0], 12, 3))
tp_img.save(P + "/front_compare.png", np.concatenate([r4, gap, ours4, gap, ov], 1))
