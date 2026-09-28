"""Left/right silhouette extents (mm from the view's axis, image plane at the axis) per view and height, ref polygon
vs our alpha row.  usage: r2_extents.py alpha.png [label]"""
import sys, json, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import read_png
P = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/"
spec = json.load(open(P + "flashbang_spec.json"))
VIEW_CX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
VIEW_BOTTOM = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}
VIEW_BOX = {"v1": (40, 30, 345, 725), "v2": (345, 30, 615, 725), "v3": (615, 30, 950, 725), "v4": (950, 30, 1240, 725)}
D_PX = 175.31; MMPX = D_PX / 44.0
H, W = 1254, 1254
yy, xx = np.mgrid[0:H, 0:W]
def poly_mask(poly):
    poly = np.asarray(poly, float); m = np.zeros((H, W), bool)
    x0, y0 = poly.min(0).astype(int); x1, y1 = poly.max(0).astype(int) + 1
    sy, sx = yy[y0:y1, x0:x1] + 0.5, xx[y0:y1, x0:x1] + 0.5
    ins = np.zeros(sx.shape, bool)
    for i in range(len(poly)):
        xa, ya = poly[i]; xb, yb = poly[(i + 1) % len(poly)]
        ins ^= ((ya > sy) != (yb > sy)) & (sx < (xb - xa) * (sy - ya) / (yb - ya + 1e-12) + xa)
    m[y0:y1, x0:x1] = ins
    return m
a = read_png(sys.argv[1])
alpha = a[..., 3] / 255.0 if a.shape[2] == 4 else None
ours = alpha > 0.5
out = {}
for v in VIEW_CX:
    ref = poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"])
    bx0, by0, bx1, by1 = VIEW_BOX[v]
    rows = {}
    for Hd in (3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7):
        y = int(round(VIEW_BOTTOM[v] - Hd * D_PX))
        r = {}
        for tag, m in (("ref", ref), ("ours", ours)):
            row = np.nonzero(m[y, bx0:bx1])[0]
            r[tag] = [round((bx0 + row.min() - VIEW_CX[v]) / MMPX, 1), round((bx0 + row.max() + 1 - VIEW_CX[v]) / MMPX, 1)] if len(row) else None
        rows[f"H{Hd}"] = r
    # top of silhouette
    for tag, m in (("ref", ref), ("ours", ours)):
        ys = np.nonzero(m[by0:by1, bx0:bx1].any(1))[0]
        rows["top_H_D_" + tag] = round((VIEW_BOTTOM[v] - (by0 + ys.min())) / D_PX, 3)
    head = (slice(by0, int(VIEW_BOTTOM[v] - 3.0 * D_PX)), slice(bx0, bx1))
    rows["head_iou_above_3.0D"] = round(float((ref[head] & ours[head]).sum() / max((ref[head] | ours[head]).sum(), 1)), 4)
    out[v] = rows
print(json.dumps(out, indent=0).replace("\n", " ")[:6000])
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), indent=1)
