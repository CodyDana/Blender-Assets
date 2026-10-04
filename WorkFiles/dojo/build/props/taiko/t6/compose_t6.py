"""t6 (2026-10-03, adapted from t5/compose_t5.py: before = t5; the silhouette extents also with the bodies centred).
t5 (2026-10-03, adapted from t4/compose_t4.py; --sil-only: just the silhouette sheet): the review sheets. System Python + numpy + Pillow.
  compare_tacks.png       the t3 layout: the user's photo vs ours (photo-studio light), the tack-band crops (the photo;
                          ours t4 photo light; before = t3 photo light; ours t4 review-studio light)
  silhouette_overlay.png  A: the photo with its traced outline (green) and ours (red: the standing drum rendered from
                          the camera fitted to the photo, scaled to the same head width, heads aligned);
                          B: the same over our render; C: the perspective-free profiles r / crown radius vs z / crown
                          half-length: the photo's (traced points + fit), ours t4, ours t3
  tack_sides_18_vs_24.png the band close-up with 18-sided domes (shipped) vs 24-sided (t3), same camera and light
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t6"
T3 = HERE.parent / "t5"   # t6: "before" = t5
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "props" / "taiko"))
import taiko_uv as UVL  # noqa: E402

try:
    F = ImageFont.truetype("arial.ttf", 22)
    FS = ImageFont.truetype("arial.ttf", 17)
except OSError:
    F = FS = ImageFont.load_default()
ref = Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")


def flat(p, bg=(255, 255, 255)):
    im = Image.open(p).convert("RGBA")
    b = Image.new("RGBA", im.size, bg + (255,))
    return Image.alpha_composite(b, im).convert("RGB")


SIL_ONLY = "--sil-only" in sys.argv
if not SIL_ONLY:
    exec(open(HERE / "compose_t6_tacks.py", encoding="utf-8").read())



# ------------------------------------------------------------------ silhouette_overlay.png
def fit_ellipse(xs, ys):
    M = np.c_[xs ** 2, ys ** 2, xs, ys]
    A, C, D, E = np.linalg.lstsq(M, np.ones_like(xs), rcond=None)[0]
    cx, cy = -D / (2 * A), -E / (2 * C)
    k = 1 + A * cx ** 2 + C * cy ** 2
    return cx, cy, math.sqrt(k / A), math.sqrt(k / C)


def top_outline(mask, band):
    pts = []
    for x in range(mask.shape[1]):
        col = np.where(mask[:, x])[0]
        if len(col):
            pts.append((x, col.min()))
    pts = np.array(pts, float)
    y0 = pts[:, 1].min()
    return pts[pts[:, 1] < y0 + band]


def edge(mask):
    m = mask
    e = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    return e


ra = np.asarray(ref).astype(float)
ref_m = ra.min(2) < 240
from scipy.ndimage import binary_fill_holes  # noqa: E402
ref_m = binary_fill_holes(ref_m)               # the outer outline only (no highlight pockets on the head)
o_rgba = Image.open(HERE / "silhouette_ours_refcam.png").convert("RGBA")
o_m = binary_fill_holes(np.asarray(o_rgba)[..., 3] > 230)
OFF = 200                                       # our frame is 200 px taller at the top (render_t4 "sil")
# the head outlines: the photo's top crown (the back half, 60 px band like trace_ref_profile) and ours
tr = top_outline(ref_m, 60)
to = top_outline(o_m, 60)
er = fit_ellipse(tr[:, 0], tr[:, 1])
eo = fit_ellipse(to[:, 0], to[:, 1] - OFF)
s = er[2] / eo[2]                               # same head width
print("head ellipses ref", [round(v, 1) for v in er], "ours", [round(v, 1) for v in eo], "scale", round(s, 4))


def ours_to_ref(xy):
    """our render pixel (x, y) -> photo pixel: undo the 200 px pad, scale about our head centre, move onto the
    photo's head centre"""
    x, y = xy[..., 0], xy[..., 1] - OFF
    return np.stack([er[0] + (x - eo[0]) * s, er[1] + (y - eo[1]) * s], -1)


eo_pts = np.argwhere(edge(o_m))[:, ::-1].astype(float)
eo_ref = ours_to_ref(eo_pts)
er_pts = np.argwhere(edge(ref_m))[:, ::-1].astype(float)

# widths per photo row (ours resampled) for the numbers
o_t = Image.new("L", (1024, 1024 + 400), 0)
ow = o_rgba.split()[3].point(lambda v: 255 if v > 230 else 0)
nw, nh = round(ow.width * s), round(ow.height * s)
ow_s = ow.resize((nw, nh), Image.NEAREST)
ox = round(er[0] - eo[0] * s)
oy = round(er[1] - (eo[1] + OFF) * s) + 200
o_t.paste(ow_s, (ox, oy))
om = np.asarray(o_t)[200:200 + 1024] > 128
rows = {}
for yy in (150, 250, 312, 350, 412, 450, 512, 600, 706):
    rr = np.where(ref_m[yy])[0]
    oo = np.where(om[yy])[0]
    rows[yy] = {"ref_px": int(rr.max() - rr.min()) if len(rr) else None,
                "ours_px": int(oo.max() - oo.min()) if len(oo) else None}
# panel A: the photo with both outlines; panel B: our render (scaled, aligned) with both outlines
A = ref.copy()
dA = ImageDraw.Draw(A)
ours_rgb = flat(HERE / "silhouette_ours_refcam.png")
B = Image.new("RGB", (1024, 1024), "white")
B.paste(ours_rgb.resize((nw, nh), Image.LANCZOS), (ox, oy - 200))
dB = ImageDraw.Draw(B)
for dd in (dA, dB):
    for x, y_ in er_pts[::2]:
        dd.point((x, y_), fill=(0, 200, 0))
    for x, y_ in eo_ref[::2]:
        dd.point((x, y_), fill=(255, 0, 0))
for dd in (dA, dB):
    for x, y_ in er_pts:
        dd.rectangle((x - 1, y_ - 1, x + 1, y_ + 1), fill=(0, 190, 0))
    for x, y_ in eo_ref:
        dd.rectangle((x - 1, y_ - 1, x + 1, y_ + 1), fill=(235, 0, 0))

# panel C: the perspective-free profiles
rp = json.loads((HERE.parent / "t4" / "ref_profile.json").read_text(encoding="utf-8"))
a0, a2, a4 = rp["symmetric_fit_r(z)=a0+a2z^2+a4z^4"]
Lc = rp["crown_half_length_Lc"]
CW, CH = 1024, 1024
C = Image.new("RGB", (CW, CH), "white")
dC = ImageDraw.Draw(C)
X0, X1, Y0, Y1 = 90, CW - 30, 60, CH - 110       # plot box
zmin, zmax, rmin, rmax = -1.05, 1.05, 0.90, 1.32


def P(zr, r):
    return (X0 + (zr - zmin) / (zmax - zmin) * (X1 - X0), Y1 - (r - rmin) / (rmax - rmin) * (Y1 - Y0))


dC.rectangle((X0, Y0, X1, Y1), outline=(120, 120, 120))
for r in np.arange(0.90, 1.33, 0.05):
    dC.line([P(zmin, r), P(zmax, r)], fill=(232, 232, 232))
    dC.text((X0 - 60, P(0, r)[1] - 9), "%.2f" % r, fill="black", font=FS)
for z in np.arange(-1.0, 1.01, 0.25):
    dC.line([P(z, rmin), P(z, rmax)], fill=(232, 232, 232))
    dC.text((P(z, 0)[0] - 18, Y1 + 8), "%.2f" % z, fill="black", font=FS)
dC.text((X0, Y1 + 34), "z / crown half-length (0 = mid-length, +-1 = the lip crowns)", fill="black", font=FS)
dC.text((X0, 12), "C: body radius / head (lip outline) radius, perspective removed", fill="black", font=F)
dC.text((X0, 36), "green = photo (traced edges + fit)   red = ours t6 (same shape; z / crown half-length)   grey = ours t3", fill="black", font=FS)
for row in rp["per_side_profile_raw"]:
    for key in ("r_left", "r_right"):
        x_, y_ = P(row["z_over_Lc"], row[key])
        dC.ellipse((x_ - 4, y_ - 4, x_ + 4, y_ + 4), outline=(0, 150, 0), width=2)
zz = np.linspace(-0.55, 0.55, 200)
dC.line([P(z, a0 + a2 * (z * Lc) ** 2 + a4 * (z * Lc) ** 4) for z in zz], fill=(0, 170, 0), width=4)
zz2 = np.linspace(-1.0, 1.0, 300)
dC.line([P(z, a0 + a2 * (z * Lc) ** 2 + a4 * (z * Lc) ** 4) for z in zz2], fill=(150, 220, 150), width=1)
xs = np.linspace(-(UVL.X_ROOT), UVL.X_ROOT, 200)
dC.line([P(x / UVL.BODY_LC, UVL.body_r(x) / UVL.BODY_RC) for x in xs], fill=(220, 0, 0), width=2)
dC.line([P(x / UVL.BODY_LC, (0.600 - 0.052 * (x / 0.70) ** 2) / UVL.BODY_RC) for x in xs], fill=(140, 140, 140),
        width=2)
for zc_, col, lab in ((rp["collar_line_z_over_Lc_mean"], (0, 150, 0), "photo's collar line"),
                      ((0.5145 - UVL.D_SHIFT) / UVL.BODY_LC, (220, 0, 0), "ours lowest hem")):
    for sgn in (-1, 1):
        dC.line([P(sgn * zc_, rmin), P(sgn * zc_, rmax)], fill=col, width=1)
    dC.text((P(zc_, 0)[0] + 4, Y0 + 6 + (0 if col[1] else 22)), lab, fill=col, font=FS)
summ = ["head / belly: photo %.3f, ours t6 %.3f (t3 %.3f)" % (rp["RATIO_head_crown_d_over_max_body_d"],
                                                               UVL.BODY_RC / UVL.body_r(0), UVL.BODY_RC / 0.600),
        "belly / collar line: photo %.3f (at 0.53 Lc); ours t6 %.3f at the same 0.53 Lc" % (
            rp["RATIO_max_body_d_over_collar_d"], UVL.body_r(0) / UVL.body_r(0.526 * UVL.BODY_LC)),
        "crown half-length / belly radius: photo %.3f, ours t6 %.3f (t5 %.3f: wood shortened, drum scaled x %.4f)" % (
            rp["RATIO_crown_length_over_max_body_d"], UVL.BODY_LC / UVL.body_r(0), 1.149, UVL.DRUM_SCALE)]
for i, t in enumerate(summ):
    dC.text((X0, Y1 + 58 + 0 * i), "", fill="black")
LBL = 34
sheet = Image.new("RGB", (3 * 1024 + 40, 1024 + LBL + 110), "white")
ds = ImageDraw.Draw(sheet)
sheet.paste(A, (0, LBL))
sheet.paste(B, (1044 - 10, LBL))
sheet.paste(C, (2 * 1024 + 30, LBL))
ds.text((8, 6), "A: the user's photo; green = its traced outline, red = ours t6 (photo's fitted camera, same head width)",
        fill="black", font=FS)
ds.text((1040, 6), "B: ours t6 from the photo's fitted camera, scaled to the same head width, same outlines",
        fill="black", font=FS)
for i, t in enumerate(summ):
    ds.text((8, 1024 + LBL + 12 + 28 * i), t, fill="black", font=F)
sheet.save(HERE / "silhouette_overlay.png")
print("saved silhouette_overlay.png", sheet.size)

# t5: per-side outline extents (photo px) down the drum: left / right edge of the photo and of ours (aligned)
ext = {}
for yy in range(120, 780, 10):
    rr = np.where(ref_m[yy])[0]
    oo = np.where(om[yy])[0]
    if len(rr) and len(oo):
        ext[yy] = {"ref_l": int(rr.min()), "ours_l": int(oo.min()), "ref_r": int(rr.max()), "ours_r": int(oo.max()),
                   "ref_minus_ours_out_l": int(oo.min() - rr.min()), "ref_minus_ours_out_r": int(rr.max() - oo.max())}
rows["per_side_extents_every_10_rows"] = ext
# t6: the same with each outline centred on its own body (rows 300-700): the photo's body sits left of its head
# centre (a tilt or lens offset), which shifts every per-side number on one side and the other side the opposite way
cr = np.mean([0.5 * (ext[y]["ref_l"] + ext[y]["ref_r"]) for y in ext if 300 <= y <= 700])
co = np.mean([0.5 * (ext[y]["ours_l"] + ext[y]["ours_r"]) for y in ext if 300 <= y <= 700])
dxc = cr - co
rows["body_centre_px_ref_ours_rows300_700"] = [round(float(cr), 1), round(float(co), 1)]
rows["per_side_extents_centred_every_10_rows"] = {
    y: {"l": int(round(e["ours_l"] + dxc - e["ref_l"])), "r": int(round(e["ref_r"] - (e["ours_r"] + dxc)))} for y, e in ext.items()}
def _stat(dd, keys, lo=120, hi=770):
    v = [dd[y][k] for y in dd if lo <= y <= hi for k in keys]
    return [min(v), max(v)]
rows["summary"] = {
    "per_side_ref_minus_ours_out_px_min_max_rows120_770": _stat(ext, ("ref_minus_ours_out_l", "ref_minus_ours_out_r")),
    "per_side_centred_px_min_max_rows120_770": _stat(rows["per_side_extents_centred_every_10_rows"], ("l", "r")),
    "per_side_centred_px_min_max_rows300_700_body": _stat(rows["per_side_extents_centred_every_10_rows"], ("l", "r"), 300, 700),
    "belly_width_rows410_500_ref_ours_px": [[ext[y]["ref_r"] - ext[y]["ref_l"] for y in ext if 410 <= y <= 500],
                                             [ext[y]["ours_r"] - ext[y]["ours_l"] for y in ext if 410 <= y <= 500]]}
(HERE / "silhouette_widths.json").write_text(json.dumps({"head_ellipse_ref_px": [round(v, 2) for v in er],
                                                         "head_ellipse_ours_px": [round(v, 2) for v in eo],
                                                         "scale_ours_to_ref": round(s, 4),
                                                         "width_px_at_photo_rows": rows}, indent=1),
                                             encoding="utf-8")
print(json.dumps(rows))
