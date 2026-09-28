"""Stage 5: dark marks continuing each flank line past the root corner into the hub.
For each root: walk from the model corner along the flank-line extension into the hub
(s = 0..40 px), take the minimum luminance across a +-4 px strip normal to the line, and
report how far a continuous very-dark run (lum < 0.15, below the plate face 10th percentile
0.225) extends. Also report the same statistic along the flank itself (toward the tip) for control.
blender -b --factory-startup --python s5_rootmarks.py -- <photo> <outdir> <tag>
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir, tag = argv[0], argv[1], argv[2]
rgb = imgio.load_rgb(photo).astype(np.float64)
H, W, _ = rgb.shape
lum = rgb.mean(2)
R = json.load(open(os.path.join(outdir, f"radial_{tag}.json")))
D = json.load(open(os.path.join(outdir, f"details_{tag}.json")))


def bil(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

res = []
for rt in D["roots"]:
    k, side = rt["k"], rt["side"]
    f = R["points"][k][side]
    d = np.array(f["dir"]); n = np.array([-d[1], d[0]])
    p0 = np.array(f["p0"])
    C = np.array(rt["corner_xy"])
    # project corner onto the line
    C = p0 + np.dot(C - p0, d) * d
    nout = np.array(f["outward_normal"])
    s = np.arange(0, 40.5, 1.0)
    offs = np.arange(-4, 4.5, 0.5)
    # into hub = -d direction; strip centred on the line shifted 2 px inward (plate side)
    def strip(sign):
        P = C[None, None, :] + sign * s[:, None, None] * d[None, None, :] + offs[None, :, None] * n[None, None, :]
        return bil(lum, P[..., 0], P[..., 1]).min(1)
    into = strip(-1)
    along = strip(+1)
    def run_len(v, thr=0.15):
        L = 0
        for x in v:
            if x < thr:
                L += 1
            else:
                break
        return L
    # allow the run to start within 4 px of the corner
    def best_run(v):
        return max(run_len(v[i:]) + (i if run_len(v[i:]) > 0 else 0) for i in range(0, 5))
    res.append({"k": k, "side": side, "corner": C.tolist(),
                "dark_run_into_hub_px": int(best_run(into)),
                "dark_px_into_hub_0_20": int((into[:21] < 0.15).sum()),
                "dark_px_along_flank_0_20": int((along[:21] < 0.15).sum()),
                "min_lum_into": [round(float(v), 2) for v in into[::2]]})
json.dump(res, open(os.path.join(outdir, f"rootmarks_{tag}.json"), "w"), indent=1)
for r in res:
    print(r["k"], r["side"], "corner (%.0f,%.0f)" % tuple(r["corner"]), "dark run into hub %d px | dark px 0-20 into hub %d, along flank %d" % (
        r["dark_run_into_hub_px"], r["dark_px_into_hub_0_20"], r["dark_px_along_flank_0_20"]), r["min_lum_into"])
