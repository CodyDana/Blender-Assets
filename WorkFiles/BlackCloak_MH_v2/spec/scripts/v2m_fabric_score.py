"""Tone, fabric grain and edge-fray score of a photo-view beauty render vs the user's photo (gap_measure2 methods, v2).

blender -b --factory-startup --python v2m_fabric_score.py -- <render_dir> <tag> [<out_json>]
Needs <tag>.png (v2m_render.py --view photo beauty, Standard, white card 0.90), <tag>.json and <tag>_silhouette.json
(v2m_silhouette_score.py, for the alignment). No exposure matching: the tone target is absolute under the calibrated rig.
Our render: composited over white in LINEAR light, box-downsampled by mult in linear, back to sRGB, warped into the photo
frame with the silhouette fit. Garment pixels = aligned mask eroded 3 px.
Grain: 6 flattest 32x32 windows (as gap_measure2) -> high-pass relative std (hp_rel), radial band energies by period,
orientation anisotropy (max/min over 8 sectors) and v/h ratio, ACF half-width. Fray: thin residue after a 3x3 opening
at luma<200 along the hem and wing edges, hem-contour high-frequency RMS and spike counts (x 40..380)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import bpy
import v2m_lib as L

a = sys.argv[sys.argv.index("--") + 1:]
RD, TAG = os.path.abspath(a[0]), a[1]
OUTJ = os.path.abspath(a[2]) if len(a) > 2 else os.path.join(RD, TAG + "_fabric.json")
REF = "C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
REFJ = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out/ref_photo_measure.json"
TH = 115.0
info = json.load(open(os.path.join(RD, TAG + ".json"))); mult = int(info["args"]["mult"])
sil = json.load(open(os.path.join(RD, TAG + "_silhouette.json"))); s, tx, ty = sil["align"]["s"], sil["align"]["tx"], sil["align"]["ty"]
refj = json.load(open(REFJ))
ref = L.load(REF); H, W = ref.shape[:2]


def load_rgba(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; x = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(x); bpy.data.images.remove(im)
    return x.reshape(h, w, 4)[::-1].astype(np.float64)


im = load_rgba(os.path.join(RD, TAG + ".png"))
lin = L.srgb_to_lin01(im[..., :3]) * im[..., 3:4] + (1 - im[..., 3:4])
lin = lin.reshape(H, mult, W, mult, 3).mean((1, 3))
srgb = L.lin_to_srgb01(lin) * 255.0
ours = L.warp_to_ref_1x(srgb, s, tx, ty, H, W, fill=255.0)
L.save(os.path.join(RD, TAG + "_refframe.png"), ours)
np.save(os.path.join(RD, TAG + "_refframe.npy"), ours.astype(np.float32))
lum = L.lum(ours)
ma = np.load(os.path.join(RD, TAG + "_aligned_mask.npy"))
gm = L.blur2d(ma.astype(float), 7) > 0.99
R = {"render": os.path.join(RD, TAG + ".png"), "calibration": info.get("calibration"), "align": sil["align"]}
linl = L.lum(L.srgb_to_lin01(ours / 255.0))
R["tone"] = {"garment_sRGB_luma_p10_p50_p90": [float(np.percentile(lum[gm], q)) for q in (10, 50, 90)],
             "ref_p10_p50_p90": refj["tone"]["garment_sRGB_luma_p10_p50_p90"],
             "garment_linear_luma_median": float(np.median(linl[gm])),
             "garment_mean_rgb_sRGB": [float(ours[..., c][gm].mean()) for c in range(3)],
             "ref_mean_rgb_sRGB": refj["tone"]["garment_mean_rgb_sRGB"],
             "warmth_R_over_B_linear_mean": float(L.srgb_to_lin01(ours[..., 0][gm] / 255).mean() / max(1e-9, L.srgb_to_lin01(ours[..., 2][gm] / 255).mean()))}
N = 32
lf = L.blur2d(lum.astype(float), 9)
cands = []
for y in range(100, 620 - N, 8):
    for x in range(30, 390 - N, 8):
        if not gm[y:y + N, x:x + N].all(): continue
        w = lf[y:y + N, x:x + N]; gy, gx = np.gradient(w)
        cands.append((float(np.hypot(gx, gy).mean() / (w.mean() + 1)), x, y))
cands.sort(); chosen = []
for c in cands:
    if all(abs(c[1] - q[1]) >= N or abs(c[2] - q[2]) >= N for q in chosen): chosen.append(c)
    if len(chosen) == 6: break
rows = []
for _, x, y in chosen:
    p = lum[y:y + N, x:x + N].astype(float); hp = p - L.blur2d(p, 7)
    rows.append({"xy": [x, y], "mean_sRGB": float(p.mean()), "hp_std": float(hp[3:-3, 3:-3].std()), "hp_rel": float(hp[3:-3, 3:-3].std() / max(p.mean(), 1e-6)),
                 "spec": L.spectrum(p), "acf_halfwidth_px": L.acf_halfwidth(p)})
agg = {}
if rows:
    agg = {"hp_rel_mean": float(np.mean([r["hp_rel"] for r in rows])), "mean_sRGB": float(np.mean([r["mean_sRGB"] for r in rows])),
           "acf_halfwidth_px_mean": float(np.mean([r["acf_halfwidth_px"] for r in rows]))}
    for k in rows[0]["spec"]: agg["spec_" + k] = float(np.mean([r["spec"][k] for r in rows]))
R["fabric_flat_patches"] = {"patches": rows, "agg": agg, "ref_agg": refj["fabric_flat_patches"]["agg"]}
def erode(a_):
    e = a_.copy(); e[1:-1, 1:-1] = a_[1:-1, 1:-1] & a_[:-2, 1:-1] & a_[2:, 1:-1] & a_[1:-1, :-2] & a_[1:-1, 2:] & a_[:-2, :-2] & a_[2:, 2:] & a_[:-2, 2:] & a_[2:, :-2]; return e
def dilate(a_):
    d = a_.copy(); d[1:-1, 1:-1] = a_[1:-1, 1:-1] | a_[:-2, 1:-1] | a_[2:, 1:-1] | a_[1:-1, :-2] | a_[1:-1, 2:] | a_[:-2, :-2] | a_[2:, 2:] | a_[:-2, 2:] | a_[2:, :-2]; return d
ms = lum < 200; res = ms & ~dilate(erode(ms)); bd = L.boundary(ms)
fr = {}
for nm, (y0, y1, xa, xb) in {"hem_y590_674": (590, 674, 0, 417), "left_edge_y250_600": (250, 600, 0, 150), "right_edge_y250_600": (250, 600, 267, 417)}.items():
    rr = int(res[y0:y1, xa:xb].sum()); bl = int(((bd[:, 0] >= y0) & (bd[:, 0] < y1) & (bd[:, 1] >= xa) & (bd[:, 1] < xb)).sum())
    fr[nm] = {"thin_residue_px": rr, "outline_px": bl, "residue_per_100_outline_px": 100.0 * rr / max(bl, 1)}
fr["fringe_px_lum115_200_rows100_674"] = int(((lum >= 115) & (lum < 200))[100:674].sum())
low = L.hem_profile(lum < TH)[40:381].astype(float)
hp = low - L.smooth1d(low, 15)
fr["hem_contour_hf_rms_px"] = float(np.sqrt((hp[8:-8] ** 2).mean())); fr["hem_contour_spikes_gt1px"] = int((np.abs(hp[8:-8]) > 1.0).sum())
fr["hem_contour_spikes_gt2px"] = int((np.abs(hp[8:-8]) > 2.0).sum())
R["fray"] = fr; R["ref_fray"] = refj["fray"]
t = R["tone"]["garment_sRGB_luma_p10_p50_p90"]
P = {"tone_p50_28_36": 28.0 <= t[1] <= 36.0, "tone_p10_4_13": 4.0 <= t[0] <= 13.0, "tone_p90_35_46": 35.0 <= t[2] <= 46.0,
     "warmth_1.00_1.10": 1.00 <= R["tone"]["warmth_R_over_B_linear_mean"] <= 1.10}
if agg:
    ra = refj["fabric_flat_patches"]["agg"]
    P["grain_hp_rel_0.040_0.075"] = 0.040 <= agg["hp_rel_mean"] <= 0.075
    P["grain_bands_within_0.08"] = all(abs(agg["spec_" + k] - ra["spec_" + k]) <= 0.08 for k in ("p2_3", "p3_5", "p5_10", "p10_16"))
    P["grain_aniso_sector_le_3.5"] = agg["spec_aniso_sector_max_over_min"] <= 3.5
    P["grain_vh_0.6_1.6"] = 0.6 <= agg["spec_aniso_vfreq_over_hfreq"] <= 1.6
P["fray_hem_hf_rms_0.7_1.6"] = 0.7 <= fr["hem_contour_hf_rms_px"] <= 1.6
P["fray_hem_spikes_gt2px_12_40"] = 12 <= fr["hem_contour_spikes_gt2px"] <= 40
R["pass"] = {k: bool(v) for k, v in P.items()}; R["all_pass"] = all(R["pass"].values())
json.dump(R, open(OUTJ, "w"), indent=1, default=float)
print("V2M FAB", json.dumps({"tone": R["tone"], "agg": agg, "fray_hem_rms": fr["hem_contour_hf_rms_px"], "spikes2": fr["hem_contour_spikes_gt2px"], "pass": R["pass"]}, default=float))
