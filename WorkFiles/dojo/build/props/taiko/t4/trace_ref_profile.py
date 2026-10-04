"""t4 (2026-10-03, user: "see how the reference's barrel is wider in the middle? Lets do the same"): trace the drum
silhouette of References/Dojo/taiko_tacks_ref_user.webp and recover the body profile r(z) with the camera's
perspective removed.

Method (system Python + numpy + scipy + Pillow):
  1. Foreground = any channel < 240 on the white cut-out background.
  2. The two lip crowns: the top outline (the top head's back edge) and the bottom outline (the bottom head's front
     edge) are the two crown circles (same diameter on a nagado-daiko). A pinhole camera (focal f, camera on the
     -Y side at horizontal distance Dh and height Hc above the drum centre, pitch p down, principal point at the
     image centre row, a small roll) and the crown half-length Lc are fitted so both circles project onto the traced
     outlines (crown radius = 1 sets the unit).
  3. Left and right body edges row by row between the two collars. Each edge pixel is inverted to (z, r): the point
     of the surface of revolution whose contour-generator point (normal perpendicular to the view ray, r'(z)
     included, iterated) projects there. Outliers (the cut-out's notch on the right at y 460-485) are rejected
     against a smooth fit.
  4. Reported as ratios: r(z) / r(collar line), the crown (head) diameter / the max body diameter, the length /
     the max body diameter, and the collar lines' z / Lc.
Writes t4/ref_profile.json and t4/ref_trace_debug.png.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t4"
REF = ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp"
img = Image.open(REF).convert("RGB")
im = np.asarray(img).astype(float)
H, W = im.shape[:2]
fg = im.min(2) < 240

# ---- outlines
top, bot = [], []
for x in range(W):
    col = np.where(fg[:, x])[0]
    if len(col):
        top.append((x, col.min()))
        bot.append((x, col.max()))
top, bot = np.array(top, float), np.array(bot, float)
top = top[top[:, 1] < 100]          # the top crown's back half (the head's far edge), left to right ends
bot = bot[bot[:, 1] > 905]          # the bottom crown's front half

# ---- body edges between the collars (rows clear of the flaps on both sides)
Y0, Y1 = 312, 706
rows = np.arange(Y0, Y1 + 1)


def edge(y, side):
    xs = np.where(fg[y, 60:480] if side < 0 else fg[y, 560:980])[0]
    if not len(xs):
        return np.nan
    if side < 0:
        x = 60 + xs.min()
        a, b = im[y, x - 1].min(), im[y, x].min()
        return x - 1 + (a - 240) / max(a - b, 1e-6)
    x = 560 + xs.max()
    a, b = im[y, x].min(), im[y, x + 1].min()
    return x + (240 - a) / max(b - a, 1e-6)


L_edge = np.array([edge(y, -1) for y in rows])
R_edge = np.array([edge(y, 1) for y in rows])


def robust(yv, xv, deg=4, tol=2.5):
    keep = ~np.isnan(xv)
    for _ in range(6):
        c = np.polyfit(yv[keep], xv[keep], deg)
        res = xv - np.polyval(c, yv)
        keep = np.abs(res) < tol * max(0.4, np.std(res[keep]))
    return keep


kL, kR = robust(rows, L_edge), robust(rows, R_edge)


# ---- camera
def cam_basis(p, roll):
    fwd = np.array([0.0, math.cos(p), -math.sin(p)])
    right = np.array([1.0, 0.0, 0.0])
    up = np.cross(right, fwd)
    cr, sr = math.cos(roll), math.sin(roll)
    return fwd, cr * right + sr * up, -sr * right + cr * up


def project(P, prm):
    f, Dh, Hc, p, Lc, cx, roll = prm
    C = np.array([0.0, -Dh, Hc])
    fwd, right, up = cam_basis(p, roll)
    rel = P - C
    zc = rel @ fwd
    return np.c_[cx + f * (rel @ right) / zc, H / 2 - f * (rel @ up) / zc]


T = np.linspace(0, 2 * np.pi, 1440, endpoint=False)


def circle_img(z, r, prm):
    P = np.c_[r * np.cos(T), r * np.sin(T), np.full_like(T, z)]
    return project(P, prm)


def curve_dist(pts, curve):
    d = np.sqrt(((pts[:, None, :] - curve[None, :, :]) ** 2).sum(2))
    return d.min(1)


def resid(prm):
    Lc = prm[4]
    ct = circle_img(Lc, 1.0, prm)
    cb = circle_img(-Lc, 1.0, prm)
    ct = ct[np.sin(T) > -0.2]       # top: the far (+Y) half
    cb = cb[np.sin(T) < 0.2]        # bottom: the near (-Y) half
    return np.r_[curve_dist(top, ct), curve_dist(bot, cb)]


best = None
for D0 in (3.0, 5.0, 8.0, 14.0):
    for p0 in (0.15, 0.3, 0.5):
        x0 = [330.0 * D0, D0, D0 * math.tan(p0), p0, 1.25, 520.0, 0.0]
        try:
            fit = least_squares(resid, x0, x_scale=[100, 1, 1, 0.1, 0.1, 10, 0.01],
                                bounds=([100, 1.5, -5, -0.5, 0.4, 400, -0.1], [40000, 80, 60, 1.3, 3.0, 640, 0.1]))
        except ValueError:
            continue
        if best is None or fit.cost < best.cost:
            best = fit
fit = best
prm = fit.x
rms = float(np.sqrt(np.mean(fit.fun ** 2)))
print("camera", prm, "rms px", rms)
f, Dh, Hc, p, Lc, cx, roll = prm


def contour_point(z, r, dr, side):
    """the contour-generator point of the surface (radius r, slope dr at z) on the given image side"""
    # n = (cos t, sin t, -dr); (P - C) . n = 0 with C = (0, -Dh, Hc)  ->  r + Dh sin t - (z - Hc) dr = 0
    s = ((z - Hc) * dr - r) / Dh
    s = max(-1.0, min(1.0, s))
    c = math.sqrt(1 - s * s) * side
    return np.array([[r * c, r * s, z]])


def invert(u, v, side, drf):
    def g(q):
        z, r = q
        return project(contour_point(z, r, drf(z), side), prm)[0] - np.array([u, v])
    z0 = Lc * (1 - 2 * (v - 40) / (990 - 40))
    sol = least_squares(g, [z0, 1.1], bounds=([-3, 0.3], [3, 3]))
    return sol.x


drf = lambda z: 0.0   # noqa: E731
for it in range(3):
    zr = []
    for side, xs, keep in ((-1, L_edge, kL), (1, R_edge, kR)):
        for y, x, k in zip(rows, xs, keep):
            if k:
                z, r = invert(x, y, side, drf)
                zr.append((side, y, x, z, r))
    zr = np.array(zr)
    cpoly = np.polyfit(zr[:, 3], zr[:, 4], 4)
    dpoly = np.polyder(cpoly)
    drf = lambda z, d=dpoly: float(np.polyval(d, z))   # noqa: E731
    print("iter", it, "r(z) poly", cpoly)

zL = zr[zr[:, 0] < 0]
zR = zr[zr[:, 0] > 0]


def interp(zs, rs_, zg):
    o = np.argsort(zs)
    return np.interp(zg, zs[o], rs_[o])


zg = np.linspace(max(zL[:, 3].min(), zR[:, 3].min()), min(zL[:, 3].max(), zR[:, 3].max()), 41)
rL, rR = interp(zL[:, 3], zL[:, 4], zg), interp(zR[:, 3], zR[:, 4], zg)
A = np.c_[np.ones_like(zr[:, 3]), zr[:, 3] ** 2, zr[:, 3] ** 4]
sym = np.linalg.lstsq(A, zr[:, 4], rcond=None)[0]
sym_rms = float(np.sqrt(np.mean((A @ sym - zr[:, 4]) ** 2)))
A2 = np.c_[np.ones_like(zr[:, 3]), zr[:, 3], zr[:, 3] ** 2, zr[:, 3] ** 3, zr[:, 3] ** 4]
asy = np.linalg.lstsq(A2, zr[:, 4], rcond=None)[0]
asy_rms = float(np.sqrt(np.mean((A2 @ asy - zr[:, 4]) ** 2)))
zz = np.linspace(-0.8 * Lc, 0.8 * Lc, 2001)
r_asy = np.polyval(asy[::-1], zz)
z_belly = float(zz[np.argmax(r_asy)])
r_max = float(sym[0])
collar = {}
for name, y in (("top", 300.0), ("bottom", 718.0)):
    zs = []
    for side, xs, keep in ((-1, L_edge, kL), (1, R_edge, kR)):
        c = np.polyfit(rows[keep], xs[keep], 4)
        z, r = invert(np.polyval(c, y), y, side, drf)
        zs.append(z)
    collar[name] = float(np.mean(zs))
zc = 0.5 * (abs(collar["top"]) + abs(collar["bottom"]))
rs = lambda z: float(sym[0] + sym[1] * z ** 2 + sym[2] * z ** 4)   # noqa: E731
r_collar = rs(zc)
prof = []
for t in np.linspace(0, 1, 11):
    z = t * zc
    prof.append({"z_over_collar_z": round(float(t), 2), "z_over_crown_half_length": round(float(z / Lc), 4),
                 "diameter_over_collar_diameter": round(rs(z) / r_collar, 4),
                 "diameter_over_max_body_diameter": round(rs(z) / r_max, 4)})
wid = R_edge - L_edge
res = {
    "reference": str(REF.relative_to(ROOT)).replace("\\", "/"),
    "camera_fit": {"focal_px": round(float(f), 1), "horizontal_distance_in_crown_radii": round(float(Dh), 3),
                   "camera_height_above_drum_centre_in_crown_radii": round(float(Hc), 3),
                   "pitch_down_deg": round(math.degrees(p), 2), "roll_deg": round(math.degrees(roll), 2),
                   "principal_x_px": round(float(cx), 1), "crown_outline_rms_px": round(rms, 2),
                   "top_outline_pts": int(len(top)), "bottom_outline_pts": int(len(bot))},
    "unit": "crown (lip) radius = 1",
    "crown_half_length_Lc": round(float(Lc), 4),
    "edge_rows": [Y0, Y1], "edge_points_used": {"left": int(kL.sum()), "right": int(kR.sum())},
    "edge_points_rejected": {"left": int((~kL).sum()), "right": int((~kR).sum())},
    "symmetric_fit_r(z)=a0+a2z^2+a4z^4": [round(float(c), 5) for c in sym], "symmetric_fit_rms": round(sym_rms, 5),
    "asymmetric_fit_rms": round(asy_rms, 5),
    "belly_z_from_asymmetric_fit_over_Lc": round(z_belly / Lc, 3),
    "max_body_radius": round(r_max, 4),
    "collar_line_z": {k: round(v, 4) for k, v in collar.items()},
    "collar_line_z_over_Lc_mean": round(zc / Lc, 4),
    "collar_line_radius": round(r_collar, 4),
    "RATIO_max_body_d_over_collar_d": round(r_max / r_collar, 4),
    "RATIO_head_crown_d_over_max_body_d": round(1.0 / r_max, 4),
    "RATIO_crown_length_over_max_body_d": round(Lc / r_max, 4),
    "profile_symmetric": prof,
    "per_side_profile_raw": [{"z_over_Lc": round(float(z / Lc), 3), "r_left": round(float(a), 4),
                              "r_right": round(float(b), 4)} for z, a, b in zip(zg[::4], rL[::4], rR[::4])],
    "raw_px": {"widest_row": int(rows[np.nanargmax(wid)]), "widest_px": round(float(np.nanmax(wid)), 1),
               "top_crown_outline_width_px": round(float(top[:, 0].max() - top[:, 0].min()), 1),
               "width_px_at_rows": {int(y): round(float(w_), 1) for y, w_ in zip(rows[::40], wid[::40])}},
}
(HERE / "ref_profile.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))

dbg = img.copy()
d = ImageDraw.Draw(dbg)
for xs, keep in ((L_edge, kL), (R_edge, kR)):
    for y, x, k in zip(rows, xs, keep):
        if not np.isnan(x):
            d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(0, 200, 0) if k else (255, 0, 0))
for z_ in (Lc, -Lc):
    c = circle_img(z_, 1.0, prm)
    d.line([tuple(q) for q in c] + [tuple(c[0])], fill=(255, 0, 255), width=2)
for side in (-1, 1):
    pts = []
    for z_ in np.linspace(-zc * 1.05, zc * 1.05, 80):
        dr_ = float(2 * sym[1] * z_ + 4 * sym[2] * z_ ** 3)
        pts.append(tuple(project(contour_point(z_, rs(z_), dr_, side), prm)[0]))
    d.line(pts, fill=(0, 90, 255), width=2)
dbg.save(HERE / "ref_trace_debug.png")
print("saved", HERE / "ref_trace_debug.png")

# ---- check of the fit's extrapolation toward the heads: the hide outline between the top crown and the tack band
# (rows 104-146 on both sides; the hide lies on the body there) inverted with the same camera
chk = []
for y in range(104, 148, 4):
    for side in (-1, 1):
        x = edge(y, side) if side > 0 else edge(y, side)
        z, r = invert(x, y, side, drf)
        chk.append({"row": y, "side": side, "z_over_Lc": round(float(z / Lc), 3), "r_hide": round(float(r), 4),
                    "r_body_fit": round(rs(z), 4)})
res["head_end_check_hide_outline_vs_fit"] = chk
(HERE / "ref_profile.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for c_ in chk:
    print(c_)
