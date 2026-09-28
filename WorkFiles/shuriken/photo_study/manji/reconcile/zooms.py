import bpy, numpy as np, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outline import full_polygon, TIP, HK, ELB, J_IN, P

D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Manjiken.JPG"
CEN = np.array([1305.2, 1317.9]); SPAN = 2842.8; ROT = -0.47
img = bpy.data.images.load(SRC); W, H = img.size
buf = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(buf)
rgb = buf.reshape(H, W, 4)[::-1, :, :3].copy()

def to_img(p, k=0):
    a = math.radians(ROT + 90 * k)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    q = np.asarray(p) @ R.T * SPAN
    return np.array([CEN[0] + q[0], CEN[1] - q[1]])

def place(poly):
    p = poly / (2.0 * np.hypot(poly[:, 0], poly[:, 1]).max())
    a = math.radians(ROT); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    p = p @ R.T * SPAN
    return np.stack([CEN[0] + p[:, 0], CEN[1] - p[:, 1]], 1)
rec = place(full_polygon("reconciled"))

def draw(canvas, pts, col, width=1.6):
    col = np.array(col, np.float32); h, w, _ = canvas.shape
    S = np.vstack([pts, pts[:1]])
    for i in range(len(S) - 1):
        p0, p1 = S[i], S[i + 1]; L = np.hypot(*(p1 - p0)); n = max(int(L * 4), 2)
        for t in np.linspace(0, 1, n):
            x, y = p0 + (p1 - p0) * t
            a0, b0 = max(int(x - width), 0), max(int(y - width), 0)
            a1, b1 = min(int(x + width) + 2, w), min(int(y + width) + 2, h)
            if a1 <= a0 or b1 <= b0: continue
            gx = np.arange(a0, a1)[None, :]; gy = np.arange(b0, b1)[:, None]
            al = np.clip(width - np.hypot(gx - x, gy - y) + 0.5, 0, 1)[..., None]
            canvas[b0:b1, a0:a1] = canvas[b0:b1, a0:a1] * (1 - al) + col * al
ov = rgb.copy(); draw(ov, rec, (1.0, 0.05, 0.05), 1.7)

def save(arr, path):
    h, w, _ = arr.shape
    im = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    im.pixels.foreach_set(np.concatenate([np.clip(arr[::-1], 0, 1), np.ones((h, w, 1), np.float32)], 2).ravel().astype(np.float32))
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)

def tile(centre, half, zoom=3, boost=False, src=None):
    cx = int(np.clip(centre[0], half, W - half)); cy = int(np.clip(centre[1], half, H - half))
    a = (src if src is not None else ov)[cy - half:cy + half, cx - half:cx + half].copy()
    if boost:
        lo, hi = np.percentile(a, 2), np.percentile(a, 98)
        a = np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)
    return np.repeat(np.repeat(a, zoom, 0), zoom, 1)

ZO = D + "reconcile/"
feats = {}
for k, name in ((0, "right"), (1, "top"), (2, "left"), (3, "bottom")):
    feats["tip_" + name] = to_img(TIP, k)
    feats["hookroot_" + name] = to_img(HK, k)
    feats["elbow_" + name] = to_img(ELB, k)
    feats["junction_" + name] = to_img(J_IN, k)
for n in ("tip_left", "tip_bottom", "hookroot_left", "hookroot_bottom", "junction_left", "elbow_bottom"):
    save(tile(feats[n], 70, 4), ZO + "zz_" + n + ".png")
# contrast-boosted raw tip (no overlay) to see the ground point
save(tile(feats["tip_left"], 90, 4, boost=True, src=rgb), ZO + "zz_tip_left_boost.png")
save(tile(feats["tip_bottom"], 90, 4, boost=True, src=rgb), ZO + "zz_tip_bottom_boost.png")
# montage row: 4 tips with the overlay
row = np.concatenate([tile(feats["tip_" + n], 70, 3) for n in ("right", "top", "left", "bottom")], 1)
save(row, ZO + "zz_tips_row.png")
row2 = np.concatenate([tile(feats["hookroot_" + n], 70, 3) for n in ("right", "top", "left", "bottom")], 1)
save(row2, ZO + "zz_hookroots_row.png")
row3 = np.concatenate([tile(feats["junction_" + n], 70, 3) for n in ("right", "top", "left", "bottom")], 1)
save(row3, ZO + "zz_junctions_row.png")
print("done")
for n, v in feats.items():
    if n.startswith("tip"): print(n, v)
