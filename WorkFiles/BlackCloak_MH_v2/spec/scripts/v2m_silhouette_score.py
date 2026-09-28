"""Silhouette + hem score of a photo-view render against the user's photo (the review gap tools, adapted to v2).

blender -b --factory-startup --python v2m_silhouette_score.py -- <render_dir> <tag> [<out_json>]
Needs <tag>_alpha.png (garment-only Workbench render from v2m_render.py --view photo) and <tag>.json; optional
<tag>_id.png (with --body 1) for the visible-body count.

Method: garment alpha box-downsampled by --mult to the 417x674 reference frame -> mask (coverage > 0.5); reference
mask = photo luma < 115 (0.45), the review's threshold. IoU raw (no move) and after a similarity fit (scale + shift, no
rotation) that maximises IoU on rows >= 120 (the photo's cowl rows 0-119 are NOT scored: v2 has Jin's funnel collar).
Scale sanity: the fitted transform must put the projected floor (z = 0) within 6 px of photo row 662 (hem pools on the
floor as in the photo) and give 350..380 reference px per metre (nominal 365: the photo mapped onto him, see
TARGET_SPEC.md 2.1); outside that band the outline was matched by resizing the garment, which is a fail.
Optional 4th argument: a rest-pose *_silhouette.json whose fit is REUSED (no refit) - use it for settled / posed
renders framed from the bind shape (v2m_posed_resim.py), so a collapsed drape cannot be rescaled back onto the photo.
Bands (ref px rows): collar 0-120 (info only), shoulders 120-260, wings 260-480, lower 480-600, hem 600-674."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import bpy
import v2m_lib as L

a = sys.argv[sys.argv.index("--") + 1:]
RD, TAG = os.path.abspath(a[0]), a[1]
OUTJ = os.path.abspath(a[2]) if len(a) > 2 and a[2] != "-" else os.path.join(RD, TAG + "_silhouette.json")
FIXED = json.load(open(os.path.abspath(a[3])))["align"] if len(a) > 3 else None   # reuse the rest render's fit (settled / posed scoring)
REF = "C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
TH = 115.0
THRESH = {"iou_rows120_aligned": 0.96, "band_min_shoulders_wings_lower": 0.94, "band_min_hem": 0.90,
          "hem_jumps_ge8px_max": 4, "floor_row_tol_px": 6, "ref_px_per_m": [350.0, 380.0]}
BANDS = {"collar_0_120": (0, 120), "shoulders_120_260": (120, 260), "wings_260_480": (260, 480), "lower_480_600": (480, 600), "hem_600_674": (600, 674)}

ref = L.load(REF); H, W = ref.shape[:2]
refm = L.lum(ref) < TH
info = json.load(open(os.path.join(RD, TAG + ".json")))
mult = int(info["args"]["mult"])


def load_rgba(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; x = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(x); bpy.data.images.remove(im)
    return x.reshape(h, w, 4)[::-1]


al = load_rgba(os.path.join(RD, TAG + "_alpha.png"))[..., 3]
assert al.shape == (H * mult, W * mult), (al.shape, mult)
cov = al.reshape(H, mult, W, mult).mean((1, 3))
m = cov > 0.5
R = {"render_dir": RD, "tag": TAG, "mult": mult, "ref_mask": "photo luma<115", "ours_mask": "alpha coverage>0.5 after box-down",
     "thresholds": THRESH}
rows = np.zeros((H, W), bool); rows[120:] = True
R["iou_raw_full"] = L.iou(m, refm); R["iou_raw_rows120"] = L.iou(m & rows, refm & rows)


# similarity fit on rows >= 120 (garment rows below the cowl)
def sc(s, tx, ty):
    w = L.warp_to_ref_1x(cov, s, tx, ty, H, W) > 0.5
    return L.iou(w & rows, refm & rows)


ys, xs = np.nonzero(refm & rows); rb = (xs.min(), xs.max(), ys.min(), ys.max())
ys, xs = np.nonzero(m & rows); sb = (xs.min(), xs.max(), ys.min(), ys.max())
best = (sc(1, 0, 0), 1.0, 0.0, 0.0)
for s in np.linspace(0.90, 1.10, 21):
    cx = (rb[0] + rb[1]) / 2 - s * (sb[0] + sb[1]) / 2; cy = rb[3] - s * sb[3]
    for dx in range(-24, 25, 4):
        for dy in range(-24, 25, 4):
            v = sc(s, cx + dx, cy + dy)
            if v > best[0]: best = (v, s, cx + dx, cy + dy)
for st, ss in ((2, 0.005), (1, 0.0025), (0.5, 0.00125), (0.25, 0.000625)):
    imp = True
    while imp:
        imp = False
        v0, s0, tx0, ty0 = best
        for d in ((ss, 0, 0), (-ss, 0, 0), (0, st, 0), (0, -st, 0), (0, 0, st), (0, 0, -st)):
            q = (s0 + d[0], tx0 + d[1], ty0 + d[2]); vv = sc(*q)
            if vv > best[0] + 1e-7: best = (vv,) + q; imp = True
iou_a, s, tx, ty = best
if FIXED is not None:
    s, tx, ty = FIXED["s"], FIXED["tx"], FIXED["ty"]; iou_a = sc(s, tx, ty)
R["align"] = {"s": s, "tx": tx, "ty": ty, "fixed_from_rest": FIXED is not None, "note": "x_ref = s*x_ours + tx (1x frame, pixel centres)"}
ma = L.warp_to_ref_1x(cov, s, tx, ty, H, W) > 0.5
np.save(os.path.join(RD, TAG + "_aligned_mask.npy"), ma)
R["iou_aligned_rows120"] = iou_a; R["iou_aligned_full"] = L.iou(ma, refm)
R["bands_aligned"] = {k: L.iou(ma[y0:y1], refm[y0:y1]) for k, (y0, y1) in BANDS.items()}
R["bands_raw"] = {k: L.iou(m[y0:y1], refm[y0:y1]) for k, (y0, y1) in BANDS.items()}
# scale sanity from projected anchors
lp = info.get("landmarks_px", {})
def to_ref(p):
    x1, y1 = p[0] / mult, p[1] / mult
    return [s * x1 + tx, s * y1 + ty]
anch = {}
if "floor_origin" in lp: anch["floor_row"] = to_ref(lp["floor_origin"])[1]
if "shoulder_line_clothed_r" in lp: anch["shoulder_row"] = 0.5 * (to_ref(lp["shoulder_line_clothed_r"])[1] + to_ref(lp["shoulder_line_clothed_l"])[1])
R["anchors_in_ref_px"] = anch
R["anchor_errors_px"] = {"floor_vs_662": anch.get("floor_row", 1e9) - 662}
R["ref_px_per_m"] = (anch["floor_row"] - anch["shoulder_row"]) / 1.56 if "shoulder_row" in anch and "floor_row" in anch else None
# hem (aligned)
low_r = L.hem_profile(refm); low_o = L.hem_profile(ma)
po = low_o[40:381].astype(float); pr = low_r[40:381].astype(float)
R["hem"] = {"jumps_ge8px_x20_400": L.hem_jumps(ma), "ref_jumps": L.hem_jumps(refm),
            "jump_x": [int(20 + j) for j in np.nonzero(np.abs(np.diff(low_o[20:400].astype(float))) >= 8)[0]],
            "range_px_x40_380": float(po.max() - po.min()), "ref_range": float(pr.max() - pr.min()),
            "std_px_x40_380": float(po.std()), "ref_std": float(pr.std()),
            "corner_left_x30_y": int(low_o[30]), "corner_right_x385_y": int(low_o[385]), "ref_corners": [int(low_r[30]), int(low_r[385])],
            "mean_abs_dy_vs_ref_x40_380": float(np.abs(po - pr).mean()),
            "lowest_y_every_20px": {int(x): int(low_o[x]) for x in range(20, 401, 20)},
            "slit_columns_rows520_674": int(sum(1 for x in range(20, 400) if (lambda c: (lambda ys: len(ys) > 1 and (~c[ys[0]:ys[-1] + 1]).sum() >= 3)(np.nonzero(c)[0]))(ma[520:674, x])))}
# contour distances (aligned, rows >= 120)
br = L.boundary(refm & rows); bo = L.boundary(ma & rows)
if len(bo) and len(br):
    d1 = L.nn_dist(br, bo); d2 = L.nn_dist(bo, br)
    R["contour_rows120"] = {"ref_to_ours_mean": float(d1.mean()), "ref_to_ours_p90": float(np.percentile(d1, 90)), "ours_to_ref_mean": float(d2.mean()),
                            "hausdorff": float(max(d1.max(), d2.max()))}
# visible body (ID render, aligned) - counts in reference px
idp = os.path.join(RD, TAG + "_id.png")
if os.path.exists(idp):
    idi = load_rgba(idp); rgb = idi[..., :3]; A_ = idi[..., 3]
    def cls(c): return (np.abs(rgb - np.array(c)).sum(-1) < 0.3) & (A_ > 0.5)
    vis = {}
    for nm, c in {"torso": (1, 0, 0), "leg": (1, 1, 0), "arm": (0, 1, 0), "neck": (1, 0, 1), "head": (0, 0, 1)}.items():
        vis[nm + "_px_render"] = int(cls(c).sum())
        vis[nm + "_px_ref_equiv"] = round(float(cls(c).sum()) / mult / mult, 1)
    if "floor_origin" in lp and "shoulder_line_clothed_r" in lp:
        fy = lp["floor_origin"][1]; ppm_r = (fy - lp["shoulder_line_clothed_r"][1]) / 1.56
        cut = int(max(0, fy - 0.10 * ppm_r))       # rows above 10 cm over the floor
        vis["leg_px_render_above_10cm"] = int(cls((1, 1, 0))[:cut].sum())
        vis["torso_neck_px_render"] = int(cls((1, 0, 0)).sum() + cls((1, 0, 1)).sum())
    R["visible_body"] = vis
# pass/fail
bmin = min(R["bands_aligned"][k] for k in ("shoulders_120_260", "wings_260_480", "lower_480_600"))
R["pass"] = {"iou_rows120_aligned": iou_a >= THRESH["iou_rows120_aligned"],
             "bands_shoulders_wings_lower": bmin >= THRESH["band_min_shoulders_wings_lower"],
             "band_hem": R["bands_aligned"]["hem_600_674"] >= THRESH["band_min_hem"],
             "hem_jumps": R["hem"]["jumps_ge8px_x20_400"] <= THRESH["hem_jumps_ge8px_max"],
             "floor_anchor": abs(R["anchor_errors_px"]["floor_vs_662"]) <= THRESH["floor_row_tol_px"],
             "scale_px_per_m": R["ref_px_per_m"] is not None and THRESH["ref_px_per_m"][0] <= R["ref_px_per_m"] <= THRESH["ref_px_per_m"][1]}
R["pass"] = {k: bool(v) for k, v in R["pass"].items()}
R["all_pass"] = all(R["pass"].values())
json.dump(R, open(OUTJ, "w"), indent=1, default=float)
# overlay: ref-only red, ours-only blue, both grey
ov = np.full((H, W, 3), 255.0); ov[refm & ma] = (90, 90, 90); ov[refm & ~ma] = (230, 40, 40); ov[ma & ~refm] = (40, 80, 230)
ov[120, :] = (0, 170, 0)
L.save(os.path.join(RD, TAG + "_silhouette_overlay_2x.png"), np.repeat(np.repeat(ov, 2, 0), 2, 1))
print("V2M SIL", json.dumps({k: R[k] for k in ("iou_raw_rows120", "iou_aligned_rows120", "bands_aligned", "align", "anchor_errors_px", "ref_px_per_m", "pass", "all_pass")}, default=float))
print("V2M HEM", json.dumps({k: R["hem"][k] for k in ("jumps_ge8px_x20_400", "range_px_x40_380", "std_px_x40_380", "corner_left_x30_y", "corner_right_x385_y")}))
if "visible_body" in R: print("V2M VIS", json.dumps(R["visible_body"]))
