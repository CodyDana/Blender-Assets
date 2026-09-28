"""The flame emblem, traced vs reference: comparison PNGs (4x and 8x) + structural checks.

Panels: reference (Catmull-Rom upsample of the stored RGB) | traced (exact-area render of the
traced curves, sampled ink and paper colours) | overlay (reference in grey; traced outline
red; where only the traced shape has ink: magenta; where only the reference does: green).

usage: python pbt_emblem_report.py [traced.json] [tag]
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
import xt_io

traced = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pbt_traced_r1.json")
tag = sys.argv[2] if len(sys.argv) > 2 else "r1"
data = json.load(open(traced, encoding="utf-8"))
L = PT.load_layers()
fit = L.fit
H, W = L.black.shape
g = next(e for e in data["groups"] if e["group"] == "emblem" and e["layer"] == "black")
curves = []
for cj in g["curves_mm"]:
    pieces = []
    for p in cj["pieces"]:
        p = np.asarray(p, np.float64)
        x, y = fit.mm_to_px(p[:, 0], p[:, 1])
        pieces.append(np.stack([x, y], 1))
    curves.append(T.Curve(pieces, bool(cj["periodic"])))
polys = [c.sample(0.02) for c in curves]

WIN = (100, 80, 206, 184)                      # source px window around the emblem
x0, y0, x1, y1 = WIN
out_dir = os.path.dirname(HERE)                # WorkFiles/paperbomb/exact/

# ---- structure --------------------------------------------------------------------------
masks = PT.group_masks(L)
own = masks[("emblem", "black")]
lab, n = T.label(own)
areas = [T.signed_area(p) for p in polys]
outer_sign = np.sign(areas[int(np.argmax(np.abs(areas)))])
outers = [i for i, a in enumerate(areas) if np.sign(a) == outer_sign]
holes = [i for i, a in enumerate(areas) if np.sign(a) != outer_sign]
names = {}
for i in outers:
    p = polys[i]
    cx, cy = fit.px_to_mm(*p.mean(0))
    names[i] = (float(cx), float(cy))
order = sorted(outers, key=lambda i: names[i][0])
labels = ["hook_L", "tongue_L", "heart", "tongue_R", "hook_R"] if len(order) == 5 else ["c%d" % k for k in range(len(order))]
# heart = the lowest-centroid middle piece; relabel the middle three by position
comp = {}
for lbl, i in zip(labels, order):
    comp[lbl] = i

obs = np.where(PT.group_regions(L, masks)[("emblem", "black")], L.black, 0.0)
box = T.fill_polys(polys, H, W, ss=16).astype(np.float64)
pred = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX) * L.density["black"]
report = {"components": len(outers), "holes": len(holes), "expected_components": 5, "parts": {}}
for lbl, i in comp.items():
    pi = polys[i]
    own_i = T.fill_polys([pi] + [polys[h] for h in holes
                                 if T.fill_polys([pi], H, W, ss=2)[tuple(np.clip(np.floor(polys[h].mean(0)[::-1]).astype(int), 0, [H - 1, W - 1]))] > 0],
                         H, W, ss=16).astype(np.float64)
    reg = T.dilate(own_i > 0.02, 3) & (obs > -1)
    # the observed component this part covers
    pr = T.gauss_blur(own_i, T.SOURCE_PSF_SIGMA_PX) * L.density["black"]
    sc = PT.score_fields(pr, obs, reg & T.dilate(own_i > 0.5, 3), fit.ppmm)
    q = T.resample_closed(pi, 0.05)
    tips_idx = T.find_corners(q, 0.05, 0.6, 100.0)
    tip_pts = [q[k] for k in tips_idx]
    # residual ink near each tip: observed minus rendered, within 1.5 px - ~0 when the tip's
    # length matches the ink the source recorded there
    tip_res = []
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for tp in tip_pts:
        m = (np.hypot(xx - tp[0], yy - tp[1]) < 1.5)
        tip_res.append(round(float((obs - pred)[m].sum()), 3))
    tmm = [[round(float(v), 3) for v in fit.px_to_mm(tp[0], tp[1])] for tp in tip_pts]
    ncorn = sum(len(c.pieces) for c in [curves[i]])
    report["parts"][lbl] = {"centroid_mm": [round(v, 3) for v in names[i]],
                            "area_mm2": round(abs(areas[i]) / fit.ppmm ** 2, 3),
                            "iou": sc.get("iou"), "edge_mean_px": sc.get("edge_mean_px"),
                            "edge_p95_px": sc.get("edge_p95_px"), "edge_max_px": sc.get("edge_max_px"),
                            "sharp_tips": len(tip_pts), "tips_mm": tmm,
                            "tip_residual_ink_px": tip_res}
whole = PT.score_fields(pred, obs, PT.group_regions(L, masks)[("emblem", "black")], fit.ppmm)
report["whole"] = whole
# symmetry (informational: the design is symmetric, the trace is NOT forced to be)
axis_mm = np.mean([names[i][0] for i in order])
ax_px = fit.mm_to_px(axis_mm, 30.0)[0]
mir = [np.stack([2 * ax_px - p[:, 0], p[:, 1]], 1) for p in polys]
bm = T.fill_polys(mir, H, W, ss=16) > 0.5
bb = box > 0.5
report["mirror_iou"] = round(float((bm & bb).sum() / max(1, (bm | bb).sum())), 4)
report["axis_mm"] = round(float(axis_mm), 3)
# the heart: a solid comma - one piece, pointed tail below, groove (not a hole) spiralling in
if "heart" in comp:
    hp = polys[comp["heart"]]
    ymin_mm = fit.px_to_mm(*hp[np.argmin(hp[:, 1])])[1]; ymax_mm = fit.px_to_mm(*hp[np.argmax(hp[:, 1])])[1]
    report["heart"] = {"holes_inside": sum(1 for h in holes if T.fill_polys([hp], H, W, ss=2)[
        int(np.clip(polys[h].mean(0)[1], 0, H - 1)), int(np.clip(polys[h].mean(0)[0], 0, W - 1))] > 0),
        "top_mm": round(float(ymin_mm), 3), "tail_bottom_mm": round(float(ymax_mm), 3)}


# ---- pictures -----------------------------------------------------------------------------
def ref_up(f):
    chans = []
    for c in range(3):
        fine, gx0, gy0, st = T.upsample_window(L.src.rgb[..., c], x0, y0, x1, y1, f, "catmull")
        chans.append(fine)
    return np.clip(np.stack(chans, -1), 0, 1)


ink = np.array(g["colour"]["median_srgb"])
paper_rgb = np.median(L.src.rgb[y0:y1, x0:x1][(L.black[y0:y1, x0:x1] < 0.02)], 0)


def traced_up(f):
    cov = T.fill_polys([(p - [x0, y0]) * f for p in polys], (y1 - y0) * f, (x1 - x0) * f, ss=8).astype(np.float64)
    lin = lambda c: T.srgb_to_linear(c)
    img = T.linear_to_srgb(lin(paper_rgb)[None, None, :] * (1 - cov[..., None]) + lin(ink)[None, None, :] * cov[..., None])
    return img, cov


def obs_up(f):
    ob = np.where(PT.group_regions(L, masks)[("emblem", "black")], L.black / L.density["black"], 0.0)
    fine, *_ = T.upsample_window(ob, x0, y0, x1, y1, f, "bspline")
    return fine


for f in (4, 8):
    r = ref_up(f)
    t, cov = traced_up(f)
    o = obs_up(f)
    grey = r.mean(-1, keepdims=True) * 0.55 + 0.45
    ov = np.repeat(grey, 3, -1)
    tb = cov > 0.5; ob = o > 0.5
    ov[tb & ~ob] = [0.85, 0.1, 0.85]
    ov[ob & ~tb] = [0.1, 0.7, 0.2]
    edge = (cov > 0.08) & (cov < 0.92)
    edge = T.dilate(edge, 1) if f >= 8 else edge
    ov[edge] = [0.9, 0.05, 0.05]
    sep = np.ones((r.shape[0], 6, 3))
    panel = np.concatenate([r, sep, t, sep, ov], 1)
    p = xt_io.write(os.path.join(out_dir, "pb_emblem_compare_%s_x%d.png" % (tag, f)), panel)
    print("wrote", p)
json.dump(report, open(os.path.join(HERE, "pbt_emblem_report_%s.json" % tag), "w"), indent=1)
print(json.dumps(report, indent=1))
