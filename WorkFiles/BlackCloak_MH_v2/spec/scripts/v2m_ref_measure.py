"""Measure the user's product photo (References/BlackCloak/blackcloak.png, 417x674) for the BlackCloak_MH_v2 target spec.
Writes spec/out/ref_photo_measure.json, ref_photo_mask.npy (bool, lum<0.45), ref_photo_contour.json (normalised outline)
and overlays. Blender 5.2 Python (numpy). Coordinates are reference px, y down.
Usage: blender -b --factory-startup --python v2m_ref_measure.py"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import v2m_lib as L

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
O = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
TH = 115.0   # garment mask threshold on sRGB luma 0..255 (= 0.45), same as the male review
ref = L.load(REF); H, W = ref.shape[:2]
lum = L.lum(ref); m = lum < TH
np.save(os.path.join(O, "ref_photo_mask.npy"), m)
R = {"source": REF, "size_wh": [W, H], "mask": "sRGB luma < 115 (0.45)"}
ys, xs = np.nonzero(m); top, bot, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
Hg, Wg = bot - top + 1, x1 - x0 + 1
R["bbox_x0y0x1y1"] = [x0, top, x1, bot]; R["height_px"] = Hg; R["width_px"] = Wg; R["h_over_w"] = Hg / Wg
fill = L.fill_holes_rows(m)


def ext(y):
    xx = np.nonzero(m[y])[0]
    return (int(xx[0]), int(xx[-1])) if len(xx) else (None, None)


# ---- normalised outline: per 1% of garment height, left/right extents, in units of garment height, x relative to the
#      bbox centre; plus width / height
cx = 0.5 * (x0 + x1)
cont = []
for k in range(0, 101):
    y = min(bot, int(round(top + k / 100 * (Hg - 1))))
    a, b = ext(y)
    cont.append({"t": k / 100, "y_px": y, "xl_n": None if a is None else (a - cx) / Hg, "xr_n": None if b is None else (b - cx) / Hg,
                 "w_over_h": None if a is None else (b - a + 1) / Hg})
json.dump({"about": "photo outline, t = (y-top)/height, x_n = (x - bbox_centre_x)/height; lum<0.45 mask", "bbox": R["bbox_x0y0x1y1"], "rows": cont},
          open(os.path.join(O, "ref_photo_contour.json"), "w"), indent=1)
# ---- width profile / shoulder line
wid = np.array([(ext(y)[1] - ext(y)[0] + 1) if ext(y)[0] is not None else 0 for y in range(H)])
R["width_at_rows"] = {y: int(wid[y]) for y in range(top, bot + 1, 10)}
# shoulder line = first row (from the top) where the width exceeds 2x the collar width at top+15
cw = wid[top + 15]
sh = next(y for y in range(top + 15, bot) if wid[y] > 2.0 * cw)
R["collar_width_top+15_px"] = int(cw); R["shoulder_line_row_px(width>2x collar)"] = int(sh)
R["shoulder_line_t"] = (sh - top) / Hg
# upper outline of the mantle per column (first garment row from the top) - the shoulder slopes
R["mantle_top_row_at_x"] = {x: int(np.nonzero(m[:, x])[0][0]) if m[:, x].any() else None for x in range(10, 410, 20)}
# ---- bands (same px bands as the male review, also expressed as t)
bands = {"collar_0_120": (0, 120), "shoulders_120_260": (120, 260), "wings_260_480": (260, 480), "lower_480_600": (480, 600), "hem_600_674": (600, 674)}
R["bands_px"] = bands
R["bands_t"] = {k: [(a - top) / Hg, (b - top) / Hg] for k, (a, b) in bands.items()}
R["band_area_px"] = {k: int(m[a:b].sum()) for k, (a, b) in bands.items()}
R["band_max_width_over_height"] = {k: float(wid[a:b].max() / Hg) for k, (a, b) in bands.items()}
R["background_inside_outline_px_by_band"] = {k: int((fill[a:b] & ~m[a:b]).sum()) for k, (a, b) in bands.items()}
# ---- hem: lowest garment row per column, scallops, stagger, flare/pool
low = np.array([np.nonzero(m[:, x])[0][-1] if m[:, x].any() else -1 for x in range(W)])
xsv = np.nonzero(low >= 0)[0]
prof = low[20:400].astype(float)
R["hem_lowest_y_every_10px"] = {int(x): int(low[x]) for x in range(0, W, 10) if low[x] >= 0}
R["hem_jumps_ge8px_x20_400"] = int((np.abs(np.diff(prof)) >= 8).sum())
R["hem_jump_x"] = [int(20 + j) for j in np.nonzero(np.abs(np.diff(prof)) >= 8)[0]]
p40 = low[40:381].astype(float)
R["hem_profile_std_px_x40_380"] = float(p40.std()); R["hem_range_px_x40_380"] = float(p40.max() - p40.min())
sm = L.smooth1d(p40, 9)
# scallops: local extrema of the smoothed hem profile with >= 4 px prominence
ext_pts = []
for i in range(3, len(sm) - 3):
    if sm[i] == max(sm[i - 3:i + 4]) or sm[i] == min(sm[i - 3:i + 4]):
        kind = "low_point" if sm[i] == max(sm[i - 3:i + 4]) else "high_point"
        if not ext_pts or ext_pts[-1][1] != kind: ext_pts.append((i + 40, kind, float(sm[i])))
        elif (kind == "low_point" and sm[i] > ext_pts[-1][2]) or (kind == "high_point" and sm[i] < ext_pts[-1][2]): ext_pts[-1] = (i + 40, kind, float(sm[i]))
depths = [abs(a[2] - b[2]) for a, b in zip(ext_pts, ext_pts[1:])]
R["hem_extrema_x_kind_y"] = [[int(a), k, round(v, 1)] for a, k, v in ext_pts]
R["hem_scallop_depths_px"] = [round(d, 1) for d in depths]
R["hem_scallops_ge4px"] = int(sum(d >= 4 for d in depths) // 2)
# flare: lowest-y at the outer corners vs 40 px inboard; pool: rows at the bottom where the garment is wider than the band above
R["hem_corner_left_x30_y"] = int(low[30]); R["hem_corner_right_x385_y"] = int(low[385])
R["hem_bottom_width_px_at_bot-5"] = int(wid[bot - 5]); R["hem_width_px_at_bot-40"] = int(wid[bot - 40]); R["hem_width_px_at_bot-100"] = int(wid[bot - 100])
R["hem_flare_ratio(width bot-5 / bot-100)"] = float(wid[bot - 5] / max(1, wid[bot - 100]))
R["hem_floor_contact_fraction(cols within 6px of bottom)"] = float((low[xsv] >= bot - 6).mean())
# ---- fray (thin residue after a 3x3 opening at a soft threshold) and fringe
def erode(a):
    e = a.copy(); e[1:-1, 1:-1] = a[1:-1, 1:-1] & a[:-2, 1:-1] & a[2:, 1:-1] & a[1:-1, :-2] & a[1:-1, 2:] & a[:-2, :-2] & a[2:, 2:] & a[:-2, 2:] & a[2:, :-2]; return e
def dilate(a):
    d = a.copy(); d[1:-1, 1:-1] = a[1:-1, 1:-1] | a[:-2, 1:-1] | a[2:, 1:-1] | a[1:-1, :-2] | a[1:-1, 2:] | a[:-2, :-2] | a[2:, 2:] | a[:-2, 2:] | a[2:, :-2]; return d
ms = lum < 200; res = ms & ~dilate(erode(ms)); bd = L.boundary(ms)
fr = {}
for nm, (y0, y1, xa, xb) in {"hem_y590_674": (590, 674, 0, 417), "left_edge_y250_600": (250, 600, 0, 150), "right_edge_y250_600": (250, 600, 267, 417)}.items():
    rr = int(res[y0:y1, xa:xb].sum()); bl = int(((bd[:, 0] >= y0) & (bd[:, 0] < y1) & (bd[:, 1] >= xa) & (bd[:, 1] < xb)).sum())
    fr[nm] = {"thin_residue_px": rr, "outline_px": bl, "residue_per_100_outline_px": 100.0 * rr / max(bl, 1)}
fr["fringe_px_lum115_200_rows100_674"] = int(((lum >= 115) & (lum < 200))[100:674].sum())
# loose threads: connected thin residue components that stick out >= 3 px beyond the smoothed outline (count along the hem + wings)
fr["outline_hf_rms_px_hem"] = None
hp = p40 - L.smooth1d(p40, 15)
fr["hem_contour_hf_rms_px"] = float(np.sqrt((hp[8:-8] ** 2).mean())); fr["hem_contour_spikes_gt1px"] = int((np.abs(hp[8:-8]) > 1.0).sum())
fr["hem_contour_spikes_gt2px"] = int((np.abs(hp[8:-8]) > 2.0).sum())
R["fray"] = fr
# ---- tone: garment percentiles (sRGB 0..255), linear median, warmth, in flat patches
lin = L.srgb_to_lin01(ref / 255.0); llin = L.lum(lin)
gm = L.blur2d(m.astype(float), 7) > 0.99
R["tone"] = {"garment_sRGB_luma_p10_p50_p90": [float(np.percentile(lum[gm], q)) for q in (10, 50, 90)],
             "garment_linear_luma_median": float(np.median(llin[gm])),
             "garment_mean_rgb_sRGB": [float(ref[..., c][gm].mean()) for c in range(3)],
             "garment_median_rgb_sRGB": [float(np.median(ref[..., c][gm])) for c in range(3)],
             "warmth_R_over_B_linear_median": float(np.median(lin[..., 0][gm]) / max(1e-6, np.median(lin[..., 2][gm]))),
             "backdrop_sRGB_median": float(np.median(lum[~fill & (lum > 230)]))}
# ---- fabric: 4 flattest 32x32 windows, high-pass stats + radial spectrum + anisotropy (gap_measure2 method) + autocorrelation scale
N = 32
lf = L.blur2d(lum.astype(float), 9)
cands = []
for y in range(100, 620 - N, 8):
    for x in range(30, 390 - N, 8):
        if not m[y:y + N, x:x + N].all(): continue
        w = lf[y:y + N, x:x + N]; gy, gx = np.gradient(w)
        cands.append((float(np.hypot(gx, gy).mean() / (w.mean() + 1)), x, y))
cands.sort(); chosen = []
for c in cands:
    if all(abs(c[1] - q[1]) >= N or abs(c[2] - q[2]) >= N for q in chosen): chosen.append(c)
    if len(chosen) == 6: break
rows = []
for _, x, y in chosen:
    p = lum[y:y + N, x:x + N].astype(float); hpp = p - L.blur2d(p, 7)
    rows.append({"xy": [x, y], "mean_sRGB": float(p.mean()), "hp_std": float(hpp[3:-3, 3:-3].std()), "hp_rel": float(hpp[3:-3, 3:-3].std() / p.mean()),
                 "spec": L.spectrum(p), "acf_halfwidth_px": L.acf_halfwidth(p)})
agg = {"hp_rel_mean": float(np.mean([r["hp_rel"] for r in rows])), "hp_std_mean": float(np.mean([r["hp_std"] for r in rows])),
       "mean_sRGB": float(np.mean([r["mean_sRGB"] for r in rows])), "acf_halfwidth_px_mean": float(np.mean([r["acf_halfwidth_px"] for r in rows]))}
for k in rows[0]["spec"]: agg["spec_" + k] = float(np.mean([r["spec"][k] for r in rows]))
R["fabric_flat_patches"] = {"patches": rows, "agg": agg}
json.dump(R, open(os.path.join(O, "ref_photo_measure.json"), "w"), indent=1, default=float)
# overlay: mask outline red, shoulder line blue, hem extrema green, fabric patches yellow
ov = ref.copy()
b = L.boundary(m); ov[b[:, 0], b[:, 1]] = (255, 0, 0)
ov[sh, :] = (0, 0, 255)
for x, k, v in ext_pts: ov[int(v) - 2:int(v) + 3, x - 2:x + 3] = (0, 255, 0) if k == "low_point" else (0, 160, 255)
for r in rows:
    x, y = r["xy"]; ov[y, x:x + N] = ov[y + N - 1, x:x + N] = (255, 255, 0); ov[y:y + N, x] = ov[y:y + N, x + N - 1] = (255, 255, 0)
L.save(os.path.join(O, "ref_photo_measure_overlay_2x.png"), np.repeat(np.repeat(ov, 2, 0), 2, 1))
print("REF", json.dumps({k: R[k] for k in ("bbox_x0y0x1y1", "h_over_w", "shoulder_line_row_px(width>2x collar)", "hem_jumps_ge8px_x20_400", "hem_scallops_ge4px", "tone")}, default=float))
print("FAB", json.dumps(agg))
