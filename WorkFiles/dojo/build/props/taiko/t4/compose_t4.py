"""t4 (2026-10-03): the review sheets. System Python + numpy + Pillow.
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
HERE = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t4"
T3 = HERE.parent / "t3"
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


# ------------------------------------------------------------------ compare_tacks.png (the t3 layout)
ours = flat(HERE / "drum_front_standing_photo.png")
band_p = flat(HERE / "closeup_tack_band_photo.png")
band_s = flat(HERE / "closeup_tack_band.png")
W = 2000
im = Image.new("RGB", (W, 1960), "white")
d = ImageDraw.Draw(im)
top = 40
im.paste(ref.resize((760, 760), Image.LANCZOS), (10, top))
im.paste(ours.resize((760, 760), Image.LANCZOS), (800, top))
d.text((10, 8), "REFERENCE (user photo)", fill="black", font=F)
d.text((800, 8), "OURS t4: bulged barrel, drum standing on a head, camera 15 deg above (photo-studio light)",
       fill="black", font=F)
y = top + 780
im.paste(ref.crop((300, 150, 700, 330)).resize((990, 446), Image.LANCZOS), (10, y + 30))
d.text((10, y), "reference tack band (crop)", fill="black", font=F)
im.paste(band_p.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y + 30))
d.text((1005, y), "ours t4: tack band close-up (photo-studio light)", fill="black", font=F)
y2 = y + 500
im.paste(band_s.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS), (1005, y2 + 30))
d.text((1005, y2), "ours t4: same close-up, review-studio light", fill="black", font=F)
im.paste(flat(T3 / "closeup_tack_band_photo.png").crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS),
         (10, y2 + 30))
d.text((10, y2), "before (t3): rows 40 mm apart, 74 per row, 24-sided domes, tube hems (photo-studio light)",
       fill="black", font=F)
im = im.crop((0, 0, W, y2 + 30 + 446 + 10))
im.save(HERE / "compare_tacks.png")
print("saved compare_tacks.png", im.size)


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
rp = json.loads((HERE / "ref_profile.json").read_text(encoding="utf-8"))
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
dC.text((X0, 36), "green = photo (traced edges + fit)   red = ours t4   grey = ours t3", fill="black", font=FS)
for row in rp["per_side_profile_raw"]:
    for key in ("r_left", "r_right"):
        x_, y_ = P(row["z_over_Lc"], row[key])
        dC.ellipse((x_ - 4, y_ - 4, x_ + 4, y_ + 4), outline=(0, 150, 0), width=2)
zz = np.linspace(-0.55, 0.55, 200)
dC.line([P(z, a0 + a2 * (z * Lc) ** 2 + a4 * (z * Lc) ** 4) for z in zz], fill=(0, 170, 0), width=4)
zz2 = np.linspace(-1.0, 1.0, 300)
dC.line([P(z, a0 + a2 * (z * Lc) ** 2 + a4 * (z * Lc) ** 4) for z in zz2], fill=(150, 220, 150), width=1)
xs = np.linspace(-0.555, 0.555, 200)
dC.line([P(x / UVL.BODY_LC, UVL.body_r(x) / UVL.BODY_RC) for x in xs], fill=(220, 0, 0), width=2)
dC.line([P(x / UVL.BODY_LC, (0.600 - 0.052 * (x / 0.70) ** 2) / UVL.BODY_RC) for x in xs], fill=(140, 140, 140),
        width=2)
for zc_, col, lab in ((rp["collar_line_z_over_Lc_mean"], (0, 150, 0), "photo's collar line"),
                      (0.520 / UVL.BODY_LC, (220, 0, 0), "ours t4 hem line")):
    for sgn in (-1, 1):
        dC.line([P(sgn * zc_, rmin), P(sgn * zc_, rmax)], fill=col, width=1)
    dC.text((P(zc_, 0)[0] + 4, Y0 + 6 + (0 if col[1] else 22)), lab, fill=col, font=FS)
summ = ["head / belly: photo %.3f, ours t4 %.3f (t3 %.3f)" % (rp["RATIO_head_crown_d_over_max_body_d"],
                                                               UVL.BODY_RC / UVL.body_r(0), UVL.BODY_RC / 0.600),
        "belly / collar line: photo %.3f (at 0.53 Lc); ours t4 %.3f at the same 0.53 Lc, %.3f at our hem line (0.67 Lc)"
        % (rp["RATIO_max_body_d_over_collar_d"], UVL.body_r(0) / UVL.body_r(0.526 * UVL.BODY_LC),
           UVL.body_r(0) / UVL.body_r(0.520)),
        "length / belly: photo %.3f, ours t4 %.3f (head and length kept)" % (rp["RATIO_crown_length_over_max_body_d"],
                                                                          UVL.BODY_LC / UVL.body_r(0))]
for i, t in enumerate(summ):
    dC.text((X0, Y1 + 58 + 0 * i), "", fill="black")
LBL = 34
sheet = Image.new("RGB", (3 * 1024 + 40, 1024 + LBL + 110), "white")
ds = ImageDraw.Draw(sheet)
sheet.paste(A, (0, LBL))
sheet.paste(B, (1044 - 10, LBL))
sheet.paste(C, (2 * 1024 + 30, LBL))
ds.text((8, 6), "A: the user's photo; green = its traced outline, red = ours t4 (photo's fitted camera, same head width)",
        fill="black", font=FS)
ds.text((1040, 6), "B: ours t4 from the photo's fitted camera, scaled to the same head width, same outlines",
        fill="black", font=FS)
for i, t in enumerate(summ):
    ds.text((8, 1024 + LBL + 12 + 28 * i), t, fill="black", font=F)
sheet.save(HERE / "silhouette_overlay.png")
print("saved silhouette_overlay.png", sheet.size)

# ------------------------------------------------------------------ tack_sides_18_vs_24.png
b18 = flat(HERE / "closeup_tack_band_photo.png")
b24 = flat(HERE / "closeup_tack_band_24sides_photo.png")
box = (300, 260, 900, 500)
z = 2
c18 = b18.crop(box).resize(((box[2] - box[0]) * z, (box[3] - box[1]) * z), Image.LANCZOS)
c24 = b24.crop(box).resize(((box[2] - box[0]) * z, (box[3] - box[1]) * z), Image.LANCZOS)
T = Image.new("RGB", (c18.width * 2 + 20, c18.height + 50), "white")
T.paste(c18, (0, 50))
T.paste(c24, (c18.width + 20, 50))
dT = ImageDraw.Draw(T)
dT.text((8, 10), "18-sided domes (t4, shipped): 162 tris per tack, drum LOD0 85,520", fill="black", font=F)
dT.text((c18.width + 28, 10), "24-sided domes (t3): 216 tris per tack, drum LOD0 101,936", fill="black", font=F)
T.save(HERE / "tack_sides_18_vs_24.png")
print("saved tack_sides_18_vs_24.png", T.size)
(HERE / "silhouette_widths.json").write_text(json.dumps({"head_ellipse_ref_px": [round(v, 2) for v in er],
                                                         "head_ellipse_ours_px": [round(v, 2) for v in eo],
                                                         "scale_ours_to_ref": round(s, 4),
                                                         "width_px_at_photo_rows": rows}, indent=1),
                                             encoding="utf-8")
print(json.dumps(rows))
