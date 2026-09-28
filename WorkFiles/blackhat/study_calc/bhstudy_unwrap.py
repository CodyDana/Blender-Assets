"""bhstudy_unwrap.py - fit the cone/rim projection of blackhat_guide.png and unwrap the visible front half.

Orthographic model (checked by the two independent estimates of D below):
  rim circle radius R seen at elevation e -> ellipse semi-axes A = R (horizontal), B = R sin e (vertical)
  apex at height h above the rim plane    -> image offset D = h cos e above the ellipse centre
Writes bhstudy_unwrap.json and views/unwrap_*.png (viewing aids only).
"""
import json, os
import numpy as np
import OpenImageIO as oiio

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
REF = ROOT + "/References/BlackHat/blackhat_guide.png"
OUT = ROOT + "/WorkFiles/blackhat/study_calc"
VIEWS = OUT + "/views"

px = oiio.ImageBuf(REF).get_pixels(oiio.FLOAT)
H, W = px.shape[:2]
rgb = px[..., :3].astype(np.float64)
luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
mask = luma < 0.93

def save(name, img):
    img = np.clip(img, 0, 1).astype(np.float32)
    if img.ndim == 2:
        img = np.repeat(img[..., None], 3, axis=2)
    h, w = img.shape[:2]
    o = oiio.ImageBuf(oiio.ImageSpec(w, h, 3, oiio.UINT8))
    o.set_pixels(oiio.ROI(0, w, 0, h, 0, 1, 0, 3), img)
    o.write(VIEWS + "/" + name)

def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    if img.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

res = {}
# --- silhouette columns
top = np.array([np.nonzero(mask[:, x])[0].min() if mask[:, x].any() else -1 for x in range(W)])
bot = np.array([np.nonzero(mask[:, x])[0].max() if mask[:, x].any() else -1 for x in range(W)])
xs_all = np.nonzero(mask.any(axis=0))[0]
xl, xr = int(xs_all.min()), int(xs_all.max())
xc = 0.5 * (xl + xr)
A_out = 0.5 * (xr - xl + 1)
res["outer_semi_major_px"] = A_out
res["centre_x_px"] = xc

# --- side-silhouette lines (cone contour generators), fit on the clean spans
def linefit(x0, x1):
    xx = np.arange(x0, x1)
    yy = top[x0:x1].astype(float)
    k, c = np.polyfit(xx, yy, 1)
    r = yy - (k * xx + c)
    return float(k), float(c), float(np.abs(r).max())
kl, cl, rl = linefit(60, 280)
kr, cr, rr = linefit(390, 600)
xa = (cr - cl) / (kl - kr)
ya = kl * xa + cl
res["contour_left"] = {"slope": kl, "max_resid_px": rl}
res["contour_right"] = {"slope": kr, "max_resid_px": rr}
res["virtual_apex_px"] = [xa, ya]
res["cap_top_y_px"] = int(top[int(round(xc))])

# --- front rim: lower silhouette, x in [xl+15, 540] (tails beyond), model y = Y0 + B sqrt(1-u^2)
xx = np.arange(xl + 15, 541)
u = (xx - xc) / A_out
sq = np.sqrt(np.clip(1 - u * u, 0, 1))
M = np.stack([np.ones_like(sq), sq], 1)
(Y0, Bb), *_ = np.linalg.lstsq(M, bot[xx].astype(float), rcond=None)
resid = bot[xx] - (Y0 + Bb * sq)
res["front_rim_bottom_fit"] = {"Y0": float(Y0), "B": float(Bb), "rms_px": float(np.sqrt((resid ** 2).mean())),
                               "max_px": float(np.abs(resid).max())}
# side extremes y (roll mid-height at the widest point)
lrows = np.nonzero(mask[:, xl:xl + 3].any(axis=1))[0]
rrows = np.nonzero(mask[:380, xr - 2:xr + 1].any(axis=1))[0]
yc_ext = 0.5 * (0.5 * (lrows.min() + lrows.max()) + 0.5 * (rrows.min() + rrows.max()))
res["side_extreme_rows"] = [[int(lrows.min()), int(lrows.max())], [int(rrows.min()), int(rrows.max())]]
res["ellipse_centre_y_from_extremes"] = float(yc_ext)

# roll half-height: bottom silhouette minus ellipse through extremes -> offset at front
roll_half = float(Y0 - yc_ext)
res["roll_bottom_offset_px"] = roll_half

# elevation & height (orthographic)
# roll centreline semi-major: the outer silhouette minus the roll tube radius. The bottom-fit offset (Y0 - yc) came
# out NEGATIVE (perspective / non-round roll), so it cannot give the tube radius; use half the front roll height
# read by eye on crop_rimfront_x3 / ruler_rim_*: 18-20 px tall -> r ~ 9.5 px.
ROLL_R_PX = 9.5
A = A_out - ROLL_R_PX
res["roll_tube_radius_px_assumed"] = ROLL_R_PX
sin_e = Bb / A
e = np.degrees(np.arcsin(sin_e))
D_direct = yc_ext - ya
slope = 0.5 * (abs(kl) + abs(kr))
# tangent-from-apex relation: slope = (D/A) sqrt(1 - (B/D)^2) -> solve D
Ds = np.linspace(Bb * 1.01, 600, 20000)
f = (Ds / A_out) * np.sqrt(1 - (Bb / Ds) ** 2) - slope
D_slope = float(Ds[np.argmin(np.abs(f))])
res["projection"] = {"A_roll_centre_px": float(A), "B_px": float(Bb), "elevation_deg": float(e),
                     "D_direct_px": float(D_direct), "D_from_contour_slope_px": D_slope}
for tag, D in (("direct", D_direct), ("slope", D_slope)):
    h = D / np.cos(np.radians(e))
    res["projection"]["h_over_R_" + tag] = float(h / A)
    res["projection"]["pitch_deg_" + tag] = float(np.degrees(np.arctan(h / A)))
    res["projection"]["apex_full_angle_deg_" + tag] = float(180 - 2 * np.degrees(np.arctan(h / A)))

json.dump(res, open(OUT + "/bhstudy_unwrap.json", "w"), indent=1)

# --- unwrap the visible cone: phi in [-90, 90] (0 = toward camera), f = slant fraction apex->rim
D = D_direct
phis = np.radians(np.linspace(-89, 89, 1068))
fs = np.linspace(0.02, 1.06, 520)
P, F = np.meshgrid(phis, fs)
X = xc + F * A * np.sin(P)
Y = ya + F * (D + Bb * np.cos(P))
un = bilinear(rgb, X, Y)
save("unwrap_cone.png", np.clip(un * 3, 0, 1))
# high-pass along phi for rib detection, on luma
ul = 0.2126 * un[..., 0] + 0.7152 * un[..., 1] + 0.0722 * un[..., 2]
k = 9
pad = np.pad(ul, ((0, 0), (k, k)), mode="edge")
blur = np.stack([pad[:, i:i + ul.shape[1]] for i in range(2 * k + 1)], 0).mean(0)
hp = ul - blur
save("unwrap_cone_hp.png", np.clip(0.5 + hp * 6, 0, 1))
np.save(OUT + "/bhstudy_unwrap_hp.npy", hp.astype(np.float32))
json.dump({"phis_deg": np.degrees(phis).tolist(), "fs": fs.tolist()}, open(OUT + "/bhstudy_unwrap_axes.json", "w"))

# --- unwrap the rim band: f in [0.90, 1.10]
fs2 = np.linspace(0.88, 1.10, 160)
P2, F2 = np.meshgrid(np.radians(np.linspace(-89, 89, 1780)), fs2)
X2 = xc + F2 * A * np.sin(P2)
Y2 = ya + F2 * D + Bb * np.cos(P2) * F2
save("unwrap_rim.png", np.clip(bilinear(rgb, X2, Y2) * 3, 0, 1))
print(json.dumps(res, indent=1))
