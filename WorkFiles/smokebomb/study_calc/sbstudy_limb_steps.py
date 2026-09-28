"""SMOKEBOMB_STUDY.md section 3: the silhouette radius r(theta) of the reference at 0.25 deg, sub-pixel, and the
steps in it (a tape edge crossing the limb shows its thickness there in true profile).  Also fits an ellipse to the
outline.  Writes sbstudy_limb_steps.json.  Run: blender -b --factory-startup --python sbstudy_limb_steps.py"""
import bpy, numpy as np, os, json
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
HERE = os.path.dirname(os.path.abspath(__file__))
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
CX, CY = 627.29, 629.12
def bil(x, y):
    x0 = np.clip(np.floor(x).astype(int), 0, w - 2); y0 = np.clip(np.floor(y).astype(int), 0, h - 2)
    fx = x - x0; fy = y - y0
    return (L[y0, x0] * (1 - fx) * (1 - fy) + L[y0, x0 + 1] * fx * (1 - fy) + L[y0 + 1, x0] * (1 - fx) * fy
            + L[y0 + 1, x0 + 1] * fx * fy)
TH = 0.5
angles = np.arange(0.0, 360.0, 0.25)
rs = np.arange(380.0, 520.0, 0.1)
r_edge = []
for a in angles:
    t = np.radians(a)
    x = CX + rs * np.cos(t); y = CY - rs * np.sin(t)          # image y down; angle counter-clockwise from +x
    v = bil(x, y)
    # outermost crossing from dark to light (last index where v < TH)
    idx = np.nonzero(v < TH)[0]
    i = idx.max()
    if i + 1 < len(rs):
        f = (TH - v[i]) / (v[i + 1] - v[i])
        r_edge.append(rs[i] + f * 0.1)
    else:
        r_edge.append(rs[-1])
r = np.array(r_edge)
# ellipse fit (algebraic, least squares) to the outline points
X = CX + r * np.cos(np.radians(angles)); Y = CY - r * np.sin(np.radians(angles))
D = np.stack([X * X, X * Y, Y * Y, X, Y, np.ones_like(X)], 1)
_, _, vt = np.linalg.svd(D)
A, B, C, Dd, E, F = vt[-1]
M0 = np.array([[F, Dd / 2, E / 2], [Dd / 2, A, B / 2], [E / 2, B / 2, C]])
M = np.array([[A, B / 2], [B / 2, C]])
lam = np.linalg.eigvalsh(M)
x0 = (B * E - 2 * C * Dd) / (4 * A * C - B * B); y0 = (B * Dd - 2 * A * E) / (4 * A * C - B * B)
detM0 = np.linalg.det(M0); detM = np.linalg.det(M)
axes = np.sqrt(-detM0 / (detM * lam))
evals, evecs = np.linalg.eigh(M)
major_dir = evecs[:, np.argmin(evals)]
major_angle = float(np.degrees(np.arctan2(-major_dir[1], major_dir[0])) % 180.0)
# steps: change of r over 1 deg (4 samples), local maxima of |dr|
dr = np.roll(r, -2) - np.roll(r, 2)
steps = []
for i in range(len(r)):
    win = np.abs(dr[max(0, i - 6):i + 7])
    if abs(dr[i]) == win.max() and abs(dr[i]) >= 2.0:
        steps.append({"angle_deg": float(angles[i]), "dr_px_over_1deg": round(float(dr[i]), 2), "r_px": round(float(r[i]), 1)})
# high-pass of r (remove the ellipse / low orders with a 30-deg moving average), its sigma
k = 120
rp = np.concatenate([r[-k:], r, r[:k]])
lp = np.convolve(rp, np.ones(k) / k, mode='same')[k:-k]
hp = r - lp
out = {"threshold_stored_luma": TH, "centre_xy": [CX, CY], "samples": len(r),
       "r_px": {"min": round(float(r.min()), 2), "max": round(float(r.max()), 2), "mean": round(float(r.mean()), 2),
                "std": round(float(r.std()), 2)},
       "ellipse_fit": {"centre_xy": [round(float(x0), 2), round(float(y0), 2)],
                       "semi_axes_px": sorted([round(float(a), 2) for a in axes]),
                       "axis_ratio": round(float(max(axes) / min(axes)), 4),
                       "major_axis_angle_deg_ccw_from_x": round(major_angle, 1)},
       "highpass30deg_sigma_px": round(float(hp.std()), 2),
       "highpass30deg_p05_p95_px": [round(float(np.percentile(hp, 5)), 2), round(float(np.percentile(hp, 95)), 2)],
       "steps_ge_2px_per_deg": steps,
       "abs_step_px": {"n": len(steps), "median": round(float(np.median([abs(s["dr_px_over_1deg"]) for s in steps])), 2) if steps else None,
                       "p75": round(float(np.percentile([abs(s["dr_px_over_1deg"]) for s in steps], 75)), 2) if steps else None,
                       "max": round(float(max(abs(s["dr_px_over_1deg"]) for s in steps)), 2) if steps else None},
       "r_by_deg": [round(float(x), 2) for x in r[::4]]}
json.dump(out, open(os.path.join(HERE, "sbstudy_limb_steps.json"), "w"), indent=1)
print("SBLIMB", json.dumps({k: v for k, v in out.items() if k not in ("r_by_deg", "steps_ge_2px_per_deg")}))
print("SBLIMB steps", [(s["angle_deg"], s["dr_px_over_1deg"]) for s in steps])
