import bpy, numpy as np, json, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outline import full_polygon

D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
OUT = D
SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Manjiken.JPG"

img = bpy.data.images.load(SRC)
W, H = img.size
buf = np.empty(W * H * 4, dtype=np.float32)
img.pixels.foreach_get(buf)
rgb = buf.reshape(H, W, 4)[::-1, :, :3].copy()   # top-origin, sRGB-encoded stored values
print("image", W, H)

B = np.load(D + "contour/mask_final.npy").astype(bool)
A = np.unpackbits(np.load(D + "radial/mask.npy"))[: B.size].reshape(B.shape).astype(bool)

# ---- reconciled placement: centre + rotation + span, fitted to the consensus mask ----
CEN = np.array([1305.2, 1317.9])          # mean of the two methods' centres
SPAN = 2842.8                             # reconciled span, px
ROT = -0.47                               # piece rotation in the frame, deg (both methods agree)

def place(poly, cen, span, rot_deg, normalise=True):
    p = poly.copy()
    if normalise:
        p = p / (2.0 * np.hypot(p[:, 0], p[:, 1]).max())   # so tip-to-tip == 1
    a = math.radians(rot_deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    p = p @ R.T * span
    return np.stack([cen[0] + p[:, 0], cen[1] - p[:, 1]], 1)   # image y grows downward

rec_img = place(full_polygon("reconciled"), CEN, SPAN, ROT)
spec_img = place(full_polygon("spec"), CEN, SPAN, ROT)

# ---- validate the reconciled outline against both masks: signed radial residual ----
def radial_of_poly(poly_img, cen, thetas):
    """distance from cen to the polygon along each ray"""
    p = poly_img - cen
    p[:, 1] *= -1.0
    ang = np.degrees(np.arctan2(p[:, 1], p[:, 0])) % 360
    r = np.hypot(p[:, 0], p[:, 1])
    o = np.argsort(ang)
    return np.interp(thetas, ang[o], r[o], period=360)

th = np.arange(0, 360, 0.1)
def radial_of_mask(M, cen):
    rr = np.arange(0, 1600, 0.25)
    rad = np.deg2rad(th)
    X = cen[0] + np.outer(np.cos(rad), rr); Y = cen[1] - np.outer(np.sin(rad), rr)
    ins = M[np.clip(np.round(Y).astype(int), 0, H - 1), np.clip(np.round(X).astype(int), 0, W - 1)]
    idx = ins.shape[1] - 1 - np.argmax(ins[:, ::-1], axis=1)
    return np.where(ins.any(1), rr[idx], 0)

rp = radial_of_poly(rec_img, CEN, th)
for nm, M in (("A", A), ("B", B)):
    rm = radial_of_mask(M, CEN)
    d = rm - rp
    print("reconciled vs mask %s : mean %+.2f px  median %+.2f  rms %.2f  p05 %+.2f p95 %+.2f  (span frac rms %.4f)"
          % (nm, d.mean(), np.median(d), np.sqrt((d ** 2).mean()), np.percentile(d, 5), np.percentile(d, 95),
             np.sqrt((d ** 2).mean()) / SPAN))

# ---- drawing ----
def draw_poly(canvas, pts, colour, width=5.0, closed=True):
    h, w, _ = canvas.shape
    col = np.array(colour, np.float32)
    seq = np.vstack([pts, pts[:1]]) if closed else pts
    for i in range(len(seq) - 1):
        p0, p1 = seq[i], seq[i + 1]
        L = np.hypot(*(p1 - p0))
        n = max(int(L * 3), 2)
        for t in np.linspace(0, 1, n):
            x, y = p0 + (p1 - p0) * t
            x0, y0 = int(math.floor(x - width)), int(math.floor(y - width))
            x1, y1 = int(math.ceil(x + width)) + 1, int(math.ceil(y + width)) + 1
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, w), min(y1, h)
            if x1 <= x0 or y1 <= y0: continue
            gx = np.arange(x0, x1)[None, :]; gy = np.arange(y0, y1)[:, None]
            dd = np.hypot(gx - x, gy - y)
            a = np.clip(width - dd + 0.5, 0, 1)[..., None]
            canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - a) + col * a

def marks(canvas, pts, colour, r=13):
    h, w, _ = canvas.shape
    col = np.array(colour, np.float32)
    for (x, y) in pts:
        x0, y0 = max(int(x - r), 0), max(int(y - r), 0)
        x1, y1 = min(int(x + r) + 1, w), min(int(y + r) + 1, h)
        gx = np.arange(x0, x1)[None, :]; gy = np.arange(y0, y1)[:, None]
        dd = np.hypot(gx - x, gy - y)
        a = np.clip(r - dd + 0.5, 0, 1)[..., None]
        canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - a) + col * a

def save(canvas, path, half=False):
    c = canvas
    if half:
        hh, ww = c.shape[0] // 2 * 2, c.shape[1] // 2 * 2
        c = c[:hh, :ww].reshape(hh // 2, 2, ww // 2, 2, 3).mean((1, 3))
    h, w, _ = c.shape
    im = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    flat = np.concatenate([np.clip(c[::-1], 0, 1), np.ones((h, w, 1), np.float32)], 2).ravel()
    im.pixels.foreach_set(flat.astype(np.float32))
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
    print("wrote", path, w, "x", h)

RED = (0.95, 0.10, 0.10); CYAN = (0.05, 0.95, 0.95); YEL = (1.0, 0.85, 0.0); MAG = (1.0, 0.1, 0.8)

# 1. photo + reconciled outline
c1 = rgb.copy()
draw_poly(c1, rec_img, RED, 5.0)
tips = []
for k in range(4):
    a = math.radians(ROT + 35.0 + 90 * k)
    tips.append((CEN[0] + math.cos(a) * SPAN / 2, CEN[1] - math.sin(a) * SPAN / 2))
marks(c1, tips, YEL, 14)
marks(c1, [CEN], CYAN, 16)
save(c1, OUT + "manji_reconciled_outline.png")
save(c1, OUT + "manji_reconciled_outline_half.png", half=True)

# 2. photo + study SPEC outline, scaled so tip-to-tip spans match
c2 = rgb.copy()
draw_poly(c2, rec_img, RED, 4.0)
draw_poly(c2, spec_img, CYAN, 5.0)
marks(c2, tips, YEL, 12)
save(c2, OUT + "manji_spec_overlay.png")
save(c2, OUT + "manji_spec_overlay_half.png", half=True)

json.dump(dict(centre=CEN.tolist(), span=SPAN, rot_deg=ROT), open(D + "reconcile/placement.json", "w"), indent=1)
