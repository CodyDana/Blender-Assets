# Method B step 8: local circle fits at notch bottoms, refined silhouette mask (fitted lines + measured notch
# bottoms), comparison with the raw Otsu(L+S) mask, hole-speck listing.
import bpy, sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
res = json.load(open(os.path.join(OUT, "b7_results.json")))
seg = json.load(open(os.path.join(OUT, "b1_segment.json")))
M0 = np.load(os.path.join(OUT, "mask_filled.npy")); Mraw = np.load(os.path.join(OUT, "mask_raw.npy"))
H, W = M0.shape
span = res["centre"]["span_px"]; C0 = np.array(res["centre"]["tip_circle_centre"])
T = {int(k): v for k, v in res["tips"].items()}; N = {int(k): v for k, v in res["notches"].items()}
nf = {}
for k in range(8):
    t = N[k]; P = np.array(t["boundary_pts"]); V = np.array(t["vertex"]); bis = np.array(t["bisector"])
    B = np.array(t["bottom_pt"]) if t["bottom_pt"] else V
    fits = {}
    for D in (8, 10, 12, 15):
        sel = P[np.hypot(*(P - B).T) <= D]
        if len(sel) >= 6:
            Cc, rr, cres = circle_fit(sel)
            fits[D] = dict(n=int(len(sel)), radius_px=rr, radius_ratio=rr / span, rms_px=float(np.sqrt(np.mean(cres ** 2))),
                           centre_side=("notch_opening" if np.dot(Cc - B, bis) > 0 else "material"))
    nf[k] = fits
    t["local_circle_fits"] = fits
    rs = [f["radius_px"] for D, f in fits.items() if D in (10, 12) and f["centre_side"] == "notch_opening"]
    t["local_radius_px"] = float(np.mean(rs)) if rs else None
    t["gap_ratio"] = t["bottom_gap_px"] / span
    print("N%d gap %.2f px (%.4f)  model rho %.1f  gap-rho %.1f  local fits %s" % (
        k, t["bottom_gap_px"], t["gap_ratio"], t["fillet_radius_px"], t["fillet_from_gap_px"],
        {D: "%.1f/%.2f/%s/%d" % (f["radius_px"], f["rms_px"], f["centre_side"][0], f["n"]) for D, f in fits.items()}))

# refined silhouette polygon: tip vertices and notch bottoms joined by the fitted straight edges; notch bottoms
# rounded with the tangent fillet of radius equal to the local radius (bounded by the gap-implied fillet)
poly = []
for k in range(8):
    poly.append(np.array(T[k]["vertex"]))
    t = N[k]; V = np.array(t["vertex"]); bis = np.array(t["bisector"]); beta = np.radians(t["opening_deg"])
    rho = t["fillet_from_gap_px"] or 0
    ua = np.array(T[k]["vertex"]) - V; ua /= np.linalg.norm(ua)
    ub = np.array(T[(k + 1) % 8]["vertex"]) - V; ub /= np.linalg.norm(ub)
    if rho > 0:
        C = V + bis * rho / np.sin(beta / 2); st = rho / np.tan(beta / 2)
        Ta = V + ua * st; Tb = V + ub * st
        a1 = np.arctan2(*(Ta - C)[::-1]); a2 = np.arctan2(*(Tb - C)[::-1])
        am = np.arctan2(*(V - C)[::-1])
        # sweep from a1 to a2 through am
        d12 = (a2 - a1) % (2 * np.pi)
        if ((am - a1) % (2 * np.pi)) <= d12: angs = a1 + np.linspace(0, d12, 24)
        else: angs = a1 - np.linspace(0, (2 * np.pi - d12), 24)
        for a in angs: poly.append(C + rho * np.array([np.cos(a), np.sin(a)]))
    else:
        poly.append(V)
poly = np.array(poly)
# rasterise (even-odd, supersampled 2x2)
def raster(poly):
    Mm = np.zeros((H, W), float)
    for oy in (0.25, 0.75):
        for ox in (0.25, 0.75):
            yy, xx = np.mgrid[0:H, 0:W]; yy = yy + oy - 0.5; xx = xx + ox - 0.5
            inside = np.zeros((H, W), bool)
            x1, y1 = poly[:, 0], poly[:, 1]; x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
            for a, b, c, d in zip(x1, y1, x2, y2):
                if b == d: continue
                cond = ((b > yy) != (d > yy))
                xint = a + (yy - b) * (c - a) / (d - b)
                inside ^= cond & (xx < xint)
            Mm += inside
    return Mm / 4
Mref = raster(poly)
Mb = Mref >= 0.5
area_ref = float(Mref.sum()); area_otsu = float(M0.sum())
diff_out = float((M0 & ~Mb).sum()); diff_in = float((Mb & ~M0).sum())
print("areas: refined %.0f  otsu %.0f  otsu-only %.0f  refined-only %.0f" % (area_ref, area_otsu, diff_out, diff_in))
# polygon area check vs ideal star with measured radii
res["refined_mask"] = dict(area_px=area_ref, area_ratio_to_span2=area_ref / span ** 2, otsu_area_px=area_otsu,
                           otsu_only_px=diff_out, refined_only_px=diff_in, polygon=poly.tolist())
# ideal regular star area with R, r: 16 triangles of (R, r, 22.5deg)
Rt = res["centre"]["tip_circle_R_px"]; Rn = res["centre"]["notch_circle_R_px"]
res["refined_mask"]["ideal_star_area_ratio_to_span2"] = 16 * 0.5 * Rt * Rn * np.sin(np.pi / 8) / span ** 2

# hole specks
hl = []
for h in seg["holes"]:
    r = np.hypot(h["cx"] - C0[0], h["cy"] - C0[1])
    # distance of speck to the refined silhouette boundary (approx: to polygon vertices densified)
    hl.append(dict(area=h["area"], x=h["cx"], y=h["cy"], r_ratio=r / span, inside_refined=bool(Mb[int(round(h["cy"])), int(round(h["cx"]))])))
hl.sort(key=lambda d: d["r_ratio"])
print("specks nearest centre:", hl[:5])
res["hole_specks"] = hl
json.dump(res, open(os.path.join(OUT, "b8_results.json"), "w"), indent=1, default=float)

# save refined mask png (white = silhouette), and a comparison png (green = both, red = Otsu only, blue = refined only)
def save(img, path):
    h, w, _ = img.shape
    im = bpy.data.images.new("o", w, h, alpha=True)
    aa = np.ones((h, w, 4), np.float32); aa[..., :3] = np.clip(img, 0, 1)
    im.pixels.foreach_set(aa[::-1].ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
img = np.zeros((H, W, 3), np.float32); img[Mb] = 1
save(img, os.path.join(OUT, "mask_refined.png"))
cmp_ = np.zeros((H, W, 3), np.float32)
cmp_[M0 & Mb] = (0.2, 0.6, 0.2); cmp_[M0 & ~Mb] = (1, 0.1, 0.1); cmp_[Mb & ~M0] = (0.2, 0.4, 1)
save(cmp_, os.path.join(OUT, "mask_compare.png"))
