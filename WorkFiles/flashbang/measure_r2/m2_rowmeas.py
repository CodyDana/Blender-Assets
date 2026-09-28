import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
import json
W = ROOT + "WorkFiles/flashbang/measure_r2/"
R = np.load(W + "m2_ref_rgb.npy"); O = load(W + "m2_row.png")[..., :3]; A = load(W + "m2_row_alpha.png")[..., 3] > 127
ref = np.zeros((1254, 1254), bool); ref[:745] = np.load(W + "m2_refmask.npy")
VB = {"v1": (40, 345), "v2": (345, 615), "v3": (615, 950), "v4": (950, 1240)}
lw = np.array([0.2126, 0.7152, 0.0722])
def paint(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (np.abs(r - g) <= 10) & ((g - b) >= 8) & (g >= 25)
out = {}
for v, (x0, x1) in VB.items():
    rs = ref.copy(); rs[:, :x0] = False; rs[:, x1:] = False
    os_ = A.copy(); os_[:, :x0] = False; os_[:, x1:] = False
    d = {"iou": round(float((rs & os_).sum() / (rs | os_).sum()), 3)}
    ys = np.flatnonzero(rs.any(1)); yo = np.flatnonzero(os_.any(1))
    d["top_bot_ref"] = [int(ys.min()), int(ys.max())]; d["top_bot_ours"] = [int(yo.min()), int(yo.max())]
    wr = {}
    for y in (120, 170, 250, 330, 450, 560, 640, 690):
        a = np.flatnonzero(rs[y]); b = np.flatnonzero(os_[y])
        wr[y] = [[int(a.min()), int(a.max())] if len(a) else None, [int(b.min()), int(b.max())] if len(b) else None]
    d["rows_ref_ours"] = wr
    for nm, im, s in (("ref", R, rs), ("ours", O, os_)):
        pm = paint(im) & s; l = im[pm] @ lw
        d["paint_frac_" + nm] = round(float(pm.sum() / s.sum()), 3)
        d["paint_p10_50_90_" + nm] = [int(np.percentile(l, q)) for q in (10, 50, 90)]
        d["paint_rgb_med_" + nm] = [int(x) for x in np.median(im[pm], 0)]
        # cap zone
        cz = s.copy(); cz[:650] = False; cz[705:] = False
        d["cap_p10_50_90_" + nm] = [int(np.percentile(im[cz] @ lw, q)) for q in (10, 50, 90)]
        hz = s.copy(); hz[:60] = False; hz[140:] = False
        d["head_p10_50_90_" + nm] = [int(np.percentile(im[hz] @ lw, q)) for q in (10, 50, 90)]
    out[v] = d; print("M2M", v, json.dumps(d))
bgr = np.median(R[20:100, 0:40].reshape(-1, 3), 0); bgo = np.median(O[20:100, 0:40].reshape(-1, 3), 0)
print("M2M bg_top ref/ours", bgr, bgo, "bg_floor", np.median(R[725:745, 0:40].reshape(-1, 3), 0), np.median(O[725:745, 0:40].reshape(-1, 3), 0))
json.dump(out, open(W + "m2_rowmeas.json", "w"), indent=1)
