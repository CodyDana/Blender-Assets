"""Debug overlay: refined contour, initial contour, DP vertices, axes, centre, tip lines, crotch circles, blade arcs,
diamond + lens panels. Writes debug_overlay.png (full) and debug_overlay_centre.png (2x zoom of the junction)."""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
Q = np.load(ROOT + "contour_refined.npy"); P0 = np.load(ROOT + "contour_initial.npy")
O = json.load(open(ROOT + "outline_measurements.json")); PR = json.load(open(ROOT + "primitives.json"))
c0 = np.array(O["centre_px"])
axes = {k: np.array([np.cos(np.radians(v["dir_deg_imagecoords"])), np.sin(np.radians(v["dir_deg_imagecoords"]))]) for k, v in O["axes"].items()}
panel = np.load(ROOT + "panel_mask.npy")
img = rgb * 0.75 + 0.25 * rgb.mean(-1, keepdims=True)
def dot(x, y, col, r=0):
    xi, yi = int(round(x)), int(round(y))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if 0 <= yi + dy < h and 0 <= xi + dx < w: img[yi + dy, xi + dx] = col
def poly(Pts, col, closed=True, r=0):
    Z = np.vstack([Pts, Pts[:1]]) if closed else Pts
    for a, b in zip(Z[:-1], Z[1:]):
        n = int(np.ceil(np.linalg.norm(b - a) * 1.5)) + 1
        for f in np.linspace(0, 1, n): dot(a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), col, r)
def circle(c, rad, col, a0=0, a1=2 * np.pi):
    t = np.linspace(a0, a1, int(abs(a1 - a0) * rad) + 10)
    poly(np.stack([c[0] + rad * np.cos(t), c[1] + rad * np.sin(t)], 1), col, closed=False)
# panel tint
pe = panel & ~erode(panel, 1)
img[pe] = [0.2, 0.6, 1.0]
poly(P0, [0.0, 0.9, 0.9])
poly(Q, [1.0, 0.1, 0.1])
keep = dp_closed(Q, 1.5)
for p in Q[keep]: dot(p[0], p[1], [1, 1, 0], 1)
# axes
for k, d in axes.items():
    poly(np.array([c0, c0 + d * 700]), [0.2, 1.0, 0.2], closed=False)
dot(c0[0], c0[1], [1, 0, 1], 3)
# crotch circles (+-60 px fit)
for k, v in PR["crotch_arcs"].items():
    f = v["circle_fits"]["+-60px_arc"]; circle(np.array(f["centre_px"]), f["radius_px"], [1.0, 0.5, 0.0])
# blade convex arcs (max->tip-10) drawn in image coords
for name, sides in PR["arm_edges"].items():
    d = axes[name]; p = np.array([-d[1], d[0]])
    for side, sv in sides.items():
        f = sv["fit_convex_blade_max_to_tip-10"]
        if not f: continue
        sg = -1 if side == "neg_v" else 1
        cu, cv = f["centre_uv"]; rad = f["radius_px"]
        # sample the arc over its u-range
        us = np.linspace(f["u_range"][0], f["u_range"][1], 200)
        vv = cv + np.sign(-cv) * np.sqrt(np.maximum(rad ** 2 - (us - cu) ** 2, 0))
        pts = c0 + us[:, None] * d + (sg * vv)[:, None] * p
        poly(pts, [1.0, 0.0, 1.0], closed=False)
# tip lines (8-60 px window) drawn from fit apex back 120 px
for name, a in O["arms"].items():
    d = axes[name]; p = np.array([-d[1], d[0]])
    f = a["tip_line_fits"].get("8-60px_back")
    if not f: continue
    apex = c0 + f["apex_u_px"] * d + f["apex_v_px"] * p
    dot(apex[0], apex[1], [0, 1, 1], 2)
write_png(ROOT + "debug_overlay.png", np.clip(img, 0, 1))
cz = img[500:820, 530:860]
write_png(ROOT + "debug_overlay_centre.png", np.clip(np.repeat(np.repeat(cz, 2, 0), 2, 1), 0, 1))
# ---- second pass: tip lines (20-80 px window) from tips_inflection.json, diamond contour, then rewrite ----
TI = json.load(open(ROOT + "tips_inflection.json"))
for name, t in TI["tips"].items():
    wv = t["windows"].get("20-80")
    if not wv: continue
    d = axes[name]; p = np.array([-d[1], d[0]])
    apex_uv = np.array([t["u_line_apex_px"], wv["apex_v_px"]])
    for th in wv["edge_dir_deg"]:
        e = np.array([np.cos(np.radians(th)), np.sin(np.radians(th))])
        pts = [apex_uv - s * e for s in (0.0, 140.0)]
        P2 = np.array([c0 + q[0] * d + q[1] * p for q in pts])
        poly(P2, [0.0, 1.0, 1.0], closed=False)
    a = c0 + apex_uv[0] * d + apex_uv[1] * p
    dot(a[0], a[1], [0, 1, 1], 3)
Pd = np.load(ROOT + "diamond_contour.npy")
poly(Pd, [1.0, 1.0, 0.3])
write_png(ROOT + "debug_overlay.png", np.clip(img, 0, 1))
cz = img[500:820, 530:860]
write_png(ROOT + "debug_overlay_centre.png", np.clip(np.repeat(np.repeat(cz, 2, 0), 2, 1), 0, 1))
tz = img[0:260, 540:820]
write_png(ROOT + "debug_overlay_toptip.png", np.clip(np.repeat(np.repeat(tz, 2, 0), 2, 1), 0, 1))
