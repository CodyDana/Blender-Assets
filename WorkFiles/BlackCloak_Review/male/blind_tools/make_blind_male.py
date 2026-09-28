# Blind A/B pair maker for the male-worn black cloak review.
# Run: blender -b --factory-startup --python make_blind_male.py -- <keyfile_in_scratchpad>
# The side key is drawn from an OS-entropy-seeded RNG and is written ONLY to the
# path given on the command line (a scratchpad temp file, deleted after reading).
import bpy, numpy as np, os, sys, json, random

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
OURS = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/unreal/shots/front_cloak_only_yaw+0.png"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blind/"
META = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blind_tools/blind_params.json"
keyfile = sys.argv[sys.argv.index("--") + 1]

def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1]
    bpy.data.images.remove(im)
    return np.ascontiguousarray(a[..., :3])

def save(a, p):
    h, w = a.shape[:2]
    a = np.concatenate([np.clip(a, 0, 1), np.ones((h, w, 1), np.float32)], 2)
    im = bpy.data.images.new("pair_out", w, h, alpha=False)
    im.pixels.foreach_set(np.ascontiguousarray(a[::-1]).astype(np.float32).ravel())
    im.filepath_raw = p; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

def lum(a): return 0.2126*a[..., 0] + 0.7152*a[..., 1] + 0.0722*a[..., 2]
def to_lin(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
def to_srgb(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)

def warp(src, s, tx, ty, out_shape, order=1):
    """out(x,y) = src((x-tx)/s, (y-ty)/s); x_ref = s*x_src + tx"""
    H, W = out_shape; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx = (xx+0.5-tx)/s-0.5; sy = (yy+0.5-ty)/s-0.5
    h, w = src.shape[:2]
    if order == 0:
        ix = np.clip(np.round(sx).astype(int), 0, w-1); iy = np.clip(np.round(sy).astype(int), 0, h-1)
        return src[iy, ix]
    sx = np.clip(sx, 0, w-1.001); sy = np.clip(sy, 0, h-1.001)   # clamp-to-edge
    x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int); fx = sx-x0; fy = sy-y0
    if src.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    return (src[y0, x0]*(1-fx)*(1-fy) + src[y0, x0+1]*fx*(1-fy)
            + src[y0+1, x0]*(1-fx)*fy + src[y0+1, x0+1]*fx*fy)

def iou(a, b): return float((a & b).sum()/max(1, (a | b).sum()))

ref = load(REF)                      # 674 x 417, sRGB-encoded
ours2 = load(OURS)                   # 1348 x 834
H, W = ref.shape[:2]
assert ours2.shape[0] == 2*H and ours2.shape[1] == 2*W, ours2.shape
# box-downsample 2x in linear light -> same pixel density as the reference photo
ol = to_lin(ours2); ol = ol.reshape(H, 2, W, 2, 3).mean((1, 3)); ours = to_srgb(ol).astype(np.float32)

THR = 0.45
refm = lum(ref) < THR
om = lum(ours) < THR
# similarity alignment of our garment mask onto the reference mask (max IoU)
ys, xs = np.nonzero(refm); rb = (xs.min(), xs.max(), ys.min(), ys.max())
ys, xs = np.nonzero(om); sb = (xs.min(), xs.max(), ys.min(), ys.max())
omf = om.astype(np.float32)
best = (iou(om, refm), (1.0, 0.0, 0.0))
for s in np.linspace(0.96, 1.04, 9):
    cx = (rb[0]+rb[1])/2 - s*(sb[0]+sb[1])/2; cy = (rb[2]+rb[3])/2 - s*(sb[2]+sb[3])/2
    for dx in range(-8, 9, 2):
        for dy in range(-12, 13, 2):
            m = warp(omf, s, cx+dx, cy+dy, (H, W), 0) > 0.5; v = iou(m, refm)
            if v > best[0]: best = (v, (s, cx+dx, cy+dy))
v0, (s, tx, ty) = best
for ds in (0.995, 1.0, 1.005):
    for dx in (-1, -0.5, 0, 0.5, 1):
        for dy in (-1, -0.5, 0, 0.5, 1):
            m = warp(omf, s*ds, tx+dx, ty+dy, (H, W), 0) > 0.5; vv = iou(m, refm)
            if vv > best[0]: best = (vv, (s*ds, tx+dx, ty+dy))
iou_best, (s, tx, ty) = best
ours_a = warp(ours, s, tx, ty, (H, W), 1).astype(np.float32)
# pixels that came from outside the capture -> studio white of our own backdrop
cov = warp(np.ones((H, W), np.float32), s, tx, ty, (H, W), 0)
om_a = lum(ours_a) < THR

# fair global exposure match: one monotone curve on linear light, f(x)=g x/(1+(g-1)x),
# chosen so our garment median luminance equals the reference garment median.
# It keeps 0->0 and 1->1 (backdrop unchanged) and does not touch contrast shape beyond gain.
rl = to_lin(ref); ol = to_lin(ours_a)
target = float(np.median(lum(rl)[refm]))
base = float(np.median(lum(ol)[om_a]))
def curve(x, g): return g*x/(1+(g-1)*x)
lo, hi = 1.0, 20.0
for _ in range(60):
    g = 0.5*(lo+hi)
    if np.median(lum(curve(ol, g))[om_a]) < target: lo = g
    else: hi = g
g = 0.5*(lo+hi)
ours_e = to_srgb(curve(ol, g)).astype(np.float32)
bgv = float(np.median(ref[~refm & (lum(ref) > 0.9)]))
ours_bg = float(np.median(ours_e[~om_a & (lum(ours_e) > 0.9)]))

def pct(a, m): L = lum(a)[m]*255; return [round(float(np.percentile(L, q)), 1) for q in (10, 50, 90)]
stats = {"ref_garment_sRGB_p10_p50_p90": pct(ref, refm),
         "ours_raw_aligned_sRGB_p10_p50_p90": pct(ours_a, om_a),
         "ours_matched_sRGB_p10_p50_p90": pct(ours_e, lum(ours_e) < THR)}

sil_r = np.where(refm, 0.0, 1.0).astype(np.float32)[..., None].repeat(3, 2)
sil_o = np.where(lum(ours_e) < THR, 0.0, 1.0).astype(np.float32)[..., None].repeat(3, 2)

# (kind, box x0,y0,x1,y1 in reference pixels, target long side px; 0 -> 440)
regions = [
    ("img", (0, 0, 417, 674), 674),      # full view, large
    ("img", (0, 0, 417, 674), 337),      # full view, small
    ("img", (115, 0, 295, 135), 0),      # collar / cowl
    ("img", (78, 48, 158, 128), 0),      # clasp
    ("img", (170, 140, 370, 300), 0),    # long diagonal mantle edge
    ("img", (220, 95, 390, 230), 0),     # upper stacked overlaps
    ("img", (0, 220, 150, 480), 0),      # wing, viewer left
    ("img", (285, 250, 417, 480), 0),    # wing, viewer right
    ("img", (140, 300, 300, 560), 0),    # layered front panels
    ("img", (120, 420, 270, 630), 0),    # inner opening
    ("img", (0, 520, 185, 674), 0),      # hem, viewer left
    ("img", (230, 520, 417, 674), 0),    # hem, viewer right
    ("img", (115, 540, 305, 674), 0),    # hem, centre
    ("img", (20, 410, 115, 560), 0),     # left panel end / ragged edge
    ("img", (310, 560, 417, 674), 0),    # right hem corner
    ("img", (240, 170, 340, 270), 0),    # fabric, 100 px patch
    ("img", (262, 192, 312, 242), 0),    # fabric, 50 px patch
    ("sil", (0, 0, 417, 674), 520),      # silhouette
    ("img", (30, 30, 390, 310), 0),      # whole upper body
    ("img", (0, 300, 417, 674), 0),      # whole lower body
]
assert len(regions) == 20

def crop_up(img, box, target):
    x0, y0, x1, y1 = box; c = img[y0:y1, x0:x1]; w, h = x1-x0, y1-y0
    k = (target or 440)/max(w, h); Wn, Hn = int(round(w*k)), int(round(h*k))
    return np.clip(warp(c, k, 0, 0, (Hn, Wn), 1) if abs(k-1) > 1e-6 else c.copy(), 0, 1)

os.makedirs(OUT, exist_ok=False)
rng = random.Random(int.from_bytes(os.urandom(16), 'little'))
key = []
for i, (kind, box, t) in enumerate(regions, 1):
    if kind == "sil": a, b = crop_up(sil_r, box, t), crop_up(sil_o, box, t)
    else: a, b = crop_up(ref, box, t), crop_up(ours_e, box, t)
    side = rng.choice(("left", "right")); key.append(side)
    L, R = (b, a) if side == "left" else (a, b)
    gap = np.full((a.shape[0], 16, 3), 0.5, np.float32)
    save(np.concatenate([L, gap, R], 1), OUT + f"pair_{i:02d}.png")

with open(keyfile, "w") as f: json.dump(key, f)
del key, rng
meta = {"source_ours": OURS, "source_ref": REF,
        "method": "ours 2x box-downsampled in linear to reference pixel density; similarity-aligned to the reference garment mask (lum<0.45) by max IoU; global exposure curve f(x)=g*x/(1+(g-1)x) in linear light matching garment medians; crops identical boxes, bilinear upscale; silhouettes are lum<0.45 masks",
        "align_s_tx_ty": [float(s), float(tx), float(ty)], "iou_after_align": round(iou_best, 4),
        "iou_unaligned": round(v0 if False else iou(om, refm), 4),
        "exposure_gain_linear": round(g, 3), "garment_median_lin_ref": target, "garment_median_lin_ours_raw": base,
        "backdrop_sRGB_ref": round(bgv*255, 1), "backdrop_sRGB_ours": round(ours_bg*255, 1),
        "tone": stats, "regions": [[k, list(b), t] for k, b, t in regions],
        "key": "not stored here"}
with open(META, "w") as f: json.dump(meta, f, indent=1)
print("DONE pairs=20")
