import sys, os, secrets, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *; from mr_png import write_png
W = ROOT + "WorkFiles/flashbang/measure_r1/"
OUTD = ROOT + "WorkFiles/flashbang/blind_r1/"
os.makedirs(OUTD, exist_ok=False)
R = ref(); S = load_png(W + "mr_eight_views.png")[..., :3] * 255
A = load_png(W + "mr_row_alpha.png")[..., 3] > 0.5
RS = np.zeros((1254, 1254), bool)
for v in ("v1", "v2", "v3", "v4"):
    RS |= ref_sil(v)
def fill(m):
    bg = np.zeros_like(m); bg[0, :] = ~m[0, :]; bg[-1, :] = ~m[-1, :]; bg[:, 0] = ~m[:, 0]; bg[:, -1] = ~m[:, -1]
    free = ~m
    while True:
        n = bg.copy()
        n[1:] |= bg[:-1]; n[:-1] |= bg[1:]; n[:, 1:] |= bg[:, :-1]; n[:, :-1] |= bg[:, 1:]
        n &= free
        if (n == bg).all(): return ~bg
        bg = n
RS = fill(RS); A = fill(A)
RM = np.stack([RS * 255.0] * 3, -1); OM = np.stack([A * 255.0] * 3, -1)
def resize(a, k):
    h, w = a.shape[:2]; H, Wd = int(round(h * k)), int(round(w * k))
    ys = (np.arange(H) + 0.5) / k - 0.5; xs = (np.arange(Wd) + 0.5) / k - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1); x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1); x1 = np.clip(x0 + 1, 0, w - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]; fx = np.clip(xs - x0, 0, 1)[None, :, None]
    return (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y0][:, x1] * (1 - fy) * fx + a[y1][:, x0] * fy * (1 - fx) + a[y1][:, x1] * fy * fx)
BOXES = [
    ("img", (40, 30, 345, 725)), ("img", (345, 30, 615, 725)), ("img", (615, 30, 950, 725)), ("img", (950, 30, 1240, 725)),
    ("img", (6, 756, 318, 1220)), ("img", (52, 38, 340, 270)), ("img", (1070, 35, 1215, 620)), ("img", (360, 120, 575, 275)),
    ("img", (370, 260, 565, 640)), ("img", (946, 756, 1249, 1220)), ("img", (323, 756, 629, 1220)), ("img", (634, 756, 939, 1220)),
    ("img", (640, 600, 850, 725)), ("img", (60, 180, 260, 400)), ("img", (990, 35, 1215, 200)), ("mask", (40, 30, 1240, 725)),
]
key = []
for i, (kind, (x0, y0, x1, y1)) in enumerate(BOXES, 1):
    a = (RM if kind == "mask" else R)[y0:y1, x0:x1]; b = (OM if kind == "mask" else S)[y0:y1, x0:x1]
    h, w = a.shape[:2]
    k = min(4.0, 720.0 / h, 900.0 / w)
    a, b = resize(a, k), resize(b, k)
    ours_right = secrets.randbelow(2) == 1
    L, Rr = (a, b) if ours_right else (b, a)
    gap = np.full((a.shape[0], 10, 3), 128.0)
    write_png(OUTD + f"pair_{i:02d}.png", np.concatenate([L, gap, Rr], 1))
    key.append("right" if ours_right else "left")
print("MRKEY", ",".join(key))
