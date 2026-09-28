"""Independent skeptic measurements (verify role). Blender -b --factory-startup --python vf_measure.py
Reads images only; writes JSON + PNG crops to male/verify/."""
import bpy, numpy as np, json, os
M = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/"
OUT = M + "verify/"
REF = "C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
UE = M + "unreal/shots/front_cloak_only_yaw+0.png"
UEP = M + "unreal/shots/front_cloak_only_yaw+10.png"
UEB = M + "unreal/shots/front_with_body.png"
UES = M + "unreal/shots/front_with_body_cloth_SIE_settled.png"
BL = M + "blender/compare/a_ref_cloak_game_refframe_2x.png"
BLT = M + "blender/compare/a2_ref_cloak_tiled_refframe_2x.png"
CAL = M + "unreal/shots/calib_all_lights.png"
BLRAW = M + "blender/renders/a_ref_cloak_game.png"

def load(p):
    im = bpy.data.images.load(p, check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    w, h = im.size
    a = np.empty(w * h * im.channels, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, im.channels)[::-1]  # top-down
    bpy.data.images.remove(im)
    return a

def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def l2s(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)

def rgb_over_white(a):
    rgb = a[..., :3]
    if a.shape[2] == 4:
        al = a[..., 3:4]
        rgb = l2s(s2l(rgb) * al + (1 - al))  # composite over white in linear
    return rgb

def lum_s(rgb):  # sRGB-coded luminance 0..255 computed in linear then encoded
    L = s2l(rgb) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    return l2s(L) * 255.0

def down2(a):  # box downsample 2x in linear
    h, w = a.shape[:2]
    a = a[:h // 2 * 2, :w // 2 * 2]
    lin = s2l(a)
    lin = (lin[0::2, 0::2] + lin[1::2, 0::2] + lin[0::2, 1::2] + lin[1::2, 1::2]) / 4
    return l2s(lin)

def warp(mask_or_img, s, tx, ty, shape):
    # x_ref = s*x + tx  -> sample source at (x_ref - tx)/s (nearest)
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx = np.round((xx - tx) / s).astype(int); sy = np.round((yy - ty) / s).astype(int)
    h, w = mask_or_img.shape[:2]
    ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
    out = np.zeros((H, W) + mask_or_img.shape[2:], mask_or_img.dtype)
    if mask_or_img.dtype != bool:
        out[...] = 1.0
    out[ok] = mask_or_img[sy[ok], sx[ok]]
    return out

def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))

def best_align(ref_m, m):
    best = (-1, 1, 0, 0)
    for s in np.arange(0.94, 1.061, 0.01):
        for tx in range(-20, 21, 2):
            for ty in range(-20, 21, 2):
                v = iou(ref_m, warp(m, s, tx, ty, ref_m.shape))
                if v > best[0]: best = (v, s, tx, ty)
    v, s0, tx0, ty0 = best
    for s in np.arange(s0 - 0.01, s0 + 0.0101, 0.0025):
        for tx in np.arange(tx0 - 2, tx0 + 2.01, 0.5):
            for ty in np.arange(ty0 - 2, ty0 + 2.01, 0.5):
                v = iou(ref_m, warp(m, s, tx, ty, ref_m.shape))
                if v > best[0]: best = (v, s, tx, ty)
    return [float(x) for x in best]

def erode(m, n=2):
    for _ in range(n):
        m = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    return m

def border_bg_fill(m):
    bg = ~m
    reach = np.zeros_like(bg)
    reach[0, :] = bg[0, :]; reach[-1, :] = bg[-1, :]; reach[:, 0] = bg[:, 0]; reach[:, -1] = bg[:, -1]
    for _ in range(2000):
        n = reach | np.roll(reach, 1, 0) | np.roll(reach, -1, 0) | np.roll(reach, 1, 1) | np.roll(reach, -1, 1)
        n &= bg
        if (n == reach).all(): break
        reach = n
    return reach

def shape_stats(m):
    H, W = m.shape
    ys, xs = np.nonzero(m)
    top, bot, left, right = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    enclosed = int((~m & ~border_bg_fill(m)).sum())
    rowspan_bg = 0
    for y in range(H):
        r = np.nonzero(m[y])[0]
        if len(r): rowspan_bg += int((~m[y, r.min():r.max() + 1]).sum())
    # lowest y per column (hem profile)
    low = np.full(W, -1)
    for x in range(W):
        c = np.nonzero(m[:, x])[0]
        if len(c): low[x] = c.max()
    samp = [int(low[x]) for x in np.linspace(30, 385, 10).astype(int)]
    cols = low[left + 10:right - 10]
    jumps = int((np.abs(np.diff(np.array(samp))) >= 8).sum())
    # hem profile of the central 60% of width
    cen = low[int(left + 0.2 * (right - left)):int(left + 0.8 * (right - left))]
    widths = {}
    for d in (5, 15, 40, 70):
        r = np.nonzero(m[top + d])[0]
        widths["top+%d" % d] = int(r.max() - r.min() + 1) if len(r) else 0
    for yy in (150, 250, 400, 550):
        r = np.nonzero(m[yy])[0]
        widths["y%d" % yy] = [int(r.min()), int(r.max())] if len(r) else None
    return dict(bbox=[left, top, right, bot], h_over_w=round((bot - top + 1) / (right - left + 1), 3),
                area=int(m.sum()), enclosed_bg_px=enclosed, rowspan_bg_px=rowspan_bg,
                hem_samples_x30_385=samp, hem_sample_jumps_ge8=jumps, hem_sample_range=int(max(samp) - min(samp)),
                hem_sample_std=round(float(np.std(samp)), 2), hem_col_std_inner=round(float(np.std(cols)), 2),
                hem_col_std_central60=round(float(np.std(cen)), 2), widths=widths,
                touches_bottom=bool(m[-1].any()), touches_top=bool(m[0].any()))

def box(img, r):
    # box blur radius r (separable, edge replicate)
    k = 2 * r + 1
    p = np.pad(img, r, mode='edge')
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)

def patch_stats(lum_lin, m, x0, y0, n=32):
    P = lum_lin[y0:y0 + n, x0:x0 + n].astype(np.float64)
    pm = m[y0:y0 + n, x0:x0 + n]
    if pm.mean() < 0.98: return None
    Ls = l2s(P) * 255
    hp = Ls - box(Ls, 3)
    gy, gx = np.gradient(box(Ls, 1))
    J = np.array([[np.sum(gx * gx), np.sum(gx * gy)], [np.sum(gx * gy), np.sum(gy * gy)]])
    ev = np.linalg.eigvalsh(J)
    # unique-level count: 8-bit quantisation check
    return dict(mean_s=round(float(Ls.mean()), 2), hp_std_s=round(float(hp[3:-3, 3:-3].std()), 3),
                hp_rel=round(float(hp[3:-3, 3:-3].std() / Ls.mean()), 4), aniso=round(float(ev[1] / max(ev[0], 1e-9)), 2),
                distinct_levels=int(len(np.unique(np.round(Ls)))))

R = {}
ref = rgb_over_white(load(REF)); H, W = ref.shape[:2]
refL = lum_s(ref); ref_m = refL < 115
R["ref"] = dict(size=[W, H], backdrop_p50=float(np.median(refL[~ref_m])), shape=shape_stats(ref_m))

srcs = {"UE": UE, "UE_yaw+10": UEP, "BL": BL, "BL_tiled": BLT, "UE_body": UEB, "UE_settled": UES}
aligned = {}
for k, p in srcs.items():
    a = rgb_over_white(load(p))
    raw_size = [a.shape[1], a.shape[0]]
    a = down2(a) if a.shape[0] > 1000 else a
    L = lum_s(a); m = L < 115
    unal = iou(ref_m, m[:H, :W]) if m.shape == ref_m.shape else None
    v, s, tx, ty = best_align(ref_m, m)
    ma = warp(m, s, tx, ty, ref_m.shape)
    Lw = warp(L, s, tx, ty, ref_m.shape)
    aligned[k] = (ma, Lw)
    bands = {}
    for name, (y0, y1) in dict(collar=(0, 120), shoulders=(120, 260), wings=(260, 480), lower=(480, 600), hem=(600, 674)).items():
        bands[name] = round(iou(ref_m[y0:y1], ma[y0:y1]), 3)
    R[k] = dict(raw_size=raw_size, iou_unaligned=None if unal is None else round(unal, 4), iou_aligned=round(v, 4),
                s_tx_ty=[round(s, 4), tx, ty], band_iou=bands, ref_only=int((ref_m & ~ma).sum()),
                ours_only=int((ma & ~ref_m).sum()), shape=shape_stats(ma),
                backdrop_p50=float(np.median(L[~m])), backdrop_p5=float(np.percentile(L[~m], 5)))

# tone inside eroded masks (UE / BL cloak-only, aligned)
def tone(L, m):
    e = erode(m, 3)
    v = L[e]
    return dict(p5=round(float(np.percentile(v, 5)), 1), p10=round(float(np.percentile(v, 10)), 1),
                p50=round(float(np.percentile(v, 50)), 1), p90=round(float(np.percentile(v, 90)), 1),
                p95=round(float(np.percentile(v, 95)), 1), mean_lin=round(float(s2l(v / 255).mean()), 5))
R["tone"] = {"REF": tone(refL, ref_m)}
for k in ("UE", "BL", "BL_tiled"):
    R["tone"][k] = tone(aligned[k][1], aligned[k][0])

# grain patches (same ref-frame boxes for all; only fully inside every mask)
refLin = s2l(refL / 255)
patch_boxes = {"mantle": (250, 200), "mantle2": (290, 260), "front_panel": (175, 430), "front_panel2": (230, 480),
               "left_fall": (60, 420), "right_wing": (330, 420), "collar": (190, 40)}
R["grain"] = {}
for name, (x0, y0) in patch_boxes.items():
    row = {"REF": patch_stats(refLin, ref_m, x0, y0)}
    for k in ("UE", "BL", "BL_tiled"):
        ma, Lw = aligned[k]
        row[k] = patch_stats(s2l(Lw / 255), ma, x0, y0)
    R["grain"][name] = row

# calibration card: grey sphere in UE calib
cal = rgb_over_white(load(CAL)); cL = lum_s(cal)
R["ue_calib"] = dict(size=[cal.shape[1], cal.shape[0]], p50=float(np.median(cL)), p1=float(np.percentile(cL, 1)),
                     hist_dark=int((cL < 200).sum()))
# find non-white blob stats
blob = cL < 240
if blob.any():
    ys, xs = np.nonzero(blob)
    R["ue_calib"]["blob_bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    R["ue_calib"]["blob_p50"] = float(np.median(cL[blob])); R["ue_calib"]["blob_p90"] = float(np.percentile(cL[blob], 90))

# UE floor / backdrop band just below the hem vs reference
R["floor_band"] = {"REF_rows_655_674": float(np.median(refL[655:674][~ref_m[655:674]]))}
maU, LU = aligned["UE"]
R["floor_band"]["UE_rows_655_674"] = float(np.median(LU[655:674][~maU[655:674]]))
R["floor_band"]["UE_rows_300_400_sides"] = float(np.median(np.concatenate([LU[300:400, :8].ravel(), LU[300:400, -8:].ravel()])))
R["floor_band"]["REF_rows_300_400_sides"] = float(np.median(np.concatenate([refL[300:400, :8].ravel(), refL[300:400, -8:].ravel()])))

# save aligned masks overlay + crops for eyeballing
def save_png(arr, path):
    h, w = arr.shape[:2]
    im = bpy.data.images.new("o", w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = arr[..., :3] if arr.ndim == 3 else arr[..., None]
    im.pixels.foreach_set(rgba[::-1].ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

for k in ("UE", "BL"):
    ma, _ = aligned[k]
    ov = np.ones((H, W, 3), np.float32)
    both = ref_m & ma
    ov[both] = 0.45; ov[ref_m & ~ma] = [0.9, 0.1, 0.1]; ov[ma & ~ref_m] = [0.1, 0.3, 0.95]
    save_png(ov, OUT + "vf_overlay_ref_red_%s_blue.png" % k)

json.dump(R, open(OUT + "vf_measure.json", "w"), indent=1)
print("VF_DONE")
