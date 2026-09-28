# Blind side-by-side builder (judge's own code; imports nothing from props_lib or m3).
# Reference vs pack front render (baked maps), matched to the reference grid, exposure-normalised.
# Left/right per element is decided by sha256("pbblind-v1:"+name) and written ONLY to _key_sealed.json.
import bpy, numpy as np, json, hashlib, os
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
REF = ROOT + "References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"
FRONT = ROOT + "Renders/PaperBomb/paperbomb_front.png"
OUT = ROOT + "WorkFiles/paperbomb/exact/blind/"
AFF = [1.210940782563025, 1.2142481124161075, 615.9877888655462, 50.69158976510067]  # m3 fit, verified below

def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels; a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1, :, :3].copy(); bpy.data.images.remove(im); return a

def save(a, p):
    a = np.clip(a, 0, 1).astype(np.float32); h, w = a.shape[:2]
    rgba = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)[::-1]
    im = bpy.data.images.new("o", w, h, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

def bil(img, xs, ys):
    h, w = img.shape[:2]
    x0 = np.clip(np.floor(xs).astype(int), 0, w-2); y0 = np.clip(np.floor(ys).astype(int), 0, h-2)
    fx = np.clip(xs-x0, 0, 1)[..., None]; fy = np.clip(ys-y0, 0, 1)[..., None]
    return (img[y0, x0]*(1-fx)*(1-fy) + img[y0, x0+1]*fx*(1-fy) + img[y0+1, x0]*(1-fx)*fy + img[y0+1, x0+1]*fx*fy)

def lum(a): return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
def warmth(a): return a[..., 0] - a[..., 2]   # paper is warm (R>>B); white/grey bg is not

ref = load(REF); fr = load(FRONT); H, W = ref.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def warp_front(p, dx=0.0, dy=0.0, src=None):
    src = fr if src is None else src
    return bil(src, p[0]*(xx+0.5+dx)+p[2]-0.5, p[1]*(yy+0.5+dy)+p[3]-0.5)

# light anti-alias prefilter for the 1.21x downsample (3x3 binomial)
k = np.array([1, 2, 1], np.float32)/4
frb = fr.copy()
frb = (np.roll(frb, 1, 1)*k[0] + frb*k[1] + np.roll(frb, -1, 1)*k[2])
frb = (np.roll(frb, 1, 0)*k[0] + frb*k[1] + np.roll(frb, -1, 0)*k[2])
ours_raw = warp_front(AFF, src=frb)

# alignment check: best sub-pixel shift of luminance correlation inside card interior
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
Lr = lum(ref)
best = None
for dx in np.arange(-1.5, 1.51, 0.5):
    for dy in np.arange(-1.5, 1.51, 0.5):
        Lo = lum(warp_front(AFF, dx, dy, frb))
        c = np.corrcoef(Lr[roi], Lo[roi])[0, 1]
        if best is None or c > best[0]: best = (float(c), float(dx), float(dy))
print("ALIGN best corr/dx/dy", best)

# exposure normalisation: per-channel gain on paper medians (global)
def paper_sel(a):
    L = lum(a); return roi & (L > np.percentile(L[roi], 40)) & (warmth(a) > 0.05)
g = np.median(ref[paper_sel(ref)], 0)/np.median(ours_raw[paper_sel(ours_raw)], 0)
ours = np.clip(ours_raw*g, 0, 1)
print("GAIN", g.tolist())
# illumination uniformity report (paper median luminance in 3x3 zones)
for nm, a in (("ref", ref), ("ours", ours)):
    ps = paper_sel(a); L = lum(a); zones = []
    for ys in ((30, 230), (230, 430), (430, 628)):
        row = []
        for xs_ in ((30, 110), (110, 190), (190, 270)):
            m = ps & (yy >= ys[0]) & (yy < ys[1]) & (xx >= xs_[0]) & (xx < xs_[1])
            row.append(round(float(np.median(L[m])), 3))
        zones.append(row)
    print("PAPER_ZONES", nm, zones)

# background: flood-fill non-paper from the border, set to same neutral grey in both
def bg_mask(a):
    cand = warmth(a) < 0.06
    m = np.zeros_like(cand); m[0, :] = cand[0, :]; m[-1, :] = cand[-1, :]; m[:, 0] = cand[:, 0]; m[:, -1] = cand[:, -1]
    while True:
        d = m.copy(); d[1:] |= m[:-1]; d[:-1] |= m[1:]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
        d &= cand
        if (d == m).all(): break
        m = d
    return m
GREY = np.array([0.45, 0.45, 0.45], np.float32)
refc = ref.copy(); refc[bg_mask(ref)] = GREY
oursc = ours.copy(); oursc[bg_mask(ours)] = GREY

# native-resolution front (for the 4x "native" variant): same gain, no downsample
fr_n = np.clip(fr*g, 0, 1)

BOX = {  # x0, x1, y0, y1 on the reference grid (judge's own boxes, placed on a 10px grid of the reference)
    "whole_card": (0, 300, 0, 653),
    "emblem": (98, 202, 82, 180),
    "centre_baku": (40, 280, 212, 415),
    "col_TL": (28, 100, 45, 230),
    "col_TR": (200, 275, 42, 228),
    "col_BR_yakujin": (200, 272, 408, 528),
    "col_BC_shungyo": (115, 185, 455, 598),
    "seal_big": (30, 116, 484, 604),
    "small_seal": (224, 270, 540, 612),
    "ring": (35, 280, 178, 448),
    "rule_top": (55, 245, 26, 46),
    "rule_left": (18, 42, 230, 480),
    "chain": (135, 165, 440, 645),
    "corner_TL": (12, 62, 14, 66),
    "corner_TR": (238, 290, 14, 66),
    "corner_BL": (12, 70, 590, 650),
    "corner_BR": (232, 290, 590, 650),
}
def up(a, f):  # bilinear resize by factor f (both images get the same op)
    h, w = a.shape[:2]; H2, W2 = max(1, int(round(h*f))), max(1, int(round(w*f)))
    yy2, xx2 = np.mgrid[0:H2, 0:W2].astype(np.float32)
    return bil(a, (xx2+0.5)/f-0.5, (yy2+0.5)/f-0.5)

def down(a, f):  # area-average downscale by 1/f (integer-ish), f<1
    n = int(round(1/f)); h, w = a.shape[:2]; h2, w2 = h//n, w//n
    return a[:h2*n, :w2*n].reshape(h2, n, w2, n, 3).mean((1, 3))

def pair(A, B, gap=6):
    h = max(A.shape[0], B.shape[0]); col = np.full((h, gap, 3), 0.2, np.float32)
    padA = np.full((h, A.shape[1], 3), 0.2, np.float32); padA[:A.shape[0]] = A
    padB = np.full((h, B.shape[1], 3), 0.2, np.float32); padB[:B.shape[0]] = B
    return np.concatenate([padA, col, padB], 1)

key = {}
os.makedirs(OUT + "pairs3", exist_ok=True)
for name, (x0, x1, y0, y1) in BOX.items():
    R = refc[y0:y1, x0:x1]; O = oursc[y0:y1, x0:x1]
    # native variant: crop the native render region that maps to the same box, resample to 4x ref grid
    f4 = 4.0
    hh, ww = (y1-y0)*4, (x1-x0)*4
    yq, xq = np.mgrid[0:hh, 0:ww].astype(np.float32)
    rx = x0 + (xq+0.5)/f4; ry = y0 + (yq+0.5)/f4
    On4 = bil(fr_n, AFF[0]*rx+AFF[2]-0.5, AFF[1]*ry+AFF[3]-0.5)
    if name == "whole_card":
        bgm = up(bg_mask(ours).astype(np.float32)[..., None].repeat(3, -1), 4) > 0.5
        On4 = np.where(bgm, GREY, On4)
    views = {
        "gallery": (R, O) if name != "whole_card" else (up(R, 1.21), up(O, 1.21)),
        "x4": (up(R, 4), up(O, 4)),
        "x4native": (up(R, 4), On4),
        "thumb": (down(R, 0.25), down(O, 0.25)) if name == "whole_card" else (down(R, 0.5), down(O, 0.5)),
    }
    if name == "whole_card":
        views["x4"] = (up(R, 2), up(O, 2)); views["x4native"] = (up(R, 2), down(On4, 0.5))
    for v, (r_, o_) in views.items():
        ours_on_left = int(hashlib.sha256(("pbblind-v2:" + name + "|" + v).encode()).hexdigest(), 16) % 2 == 1
        key[name + "|" + v] = "A" if ours_on_left else "B"
        A, B = (o_, r_) if ours_on_left else (r_, o_)
        save(pair(A, B), OUT + "pairs3/%s__%s.png" % (name, v))
with open(OUT + "_key_sealed.json", "w", encoding="utf-8") as f:
    json.dump({"rule": "sha256('pbblind-v2:'+name+'|'+view) odd -> ours is A (left)", "ours_is": key}, f)
print("DONE", len(key))


