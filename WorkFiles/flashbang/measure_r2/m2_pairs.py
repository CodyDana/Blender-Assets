"""Blind pairs (round 2): reference crop vs OUR render crop, same box, same scale; side chosen at random.
The key is printed to stdout only (never written to disk)."""
import sys, os, secrets, zlib, struct
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
W = ROOT + "WorkFiles/flashbang/measure_r2/"
OUTD = ROOT + "WorkFiles/flashbang/blind_r2/"
os.makedirs(OUTD, exist_ok=False)


def write_png(path, arr):  # plain RGB 8-bit PNG, no text/time chunks
    a = np.clip(np.round(arr), 0, 255).astype(np.uint8)
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


R = np.load(W + "m2_ref_rgb.npy")
S = np.load(W + "m2_ours_sheet.npy")
# silhouettes: reference mask (own segmentation) vs our alpha, both smoothed the same way
ref = np.zeros((1254, 1254), bool); ref[:745] = np.load(W + "m2_refmask.npy")
A = load(W + "m2_row_alpha.png")[..., 3] > 127


def boxm(m, r):
    f = m.astype(np.float32)
    c = np.cumsum(np.cumsum(np.pad(f, ((r + 1, r), (r + 1, r))), 0), 1)
    return (c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]) / (2 * r + 1) ** 2


def smooth(m):  # identical treatment for both: close (r 3), then 7x7 majority
    m = boxm(m, 3) > 0.01
    m = boxm(m, 3) > 0.99
    return boxm(m, 3) > 0.5


RM = np.stack([smooth(ref) * 225.0 + 15] * 3, -1); OM = np.stack([smooth(A) * 225.0 + 15] * 3, -1)
BOXES = [
    ("img", (40, 30, 345, 725)),      # 1 view 1 overall
    ("img", (345, 30, 615, 725)),     # 2 view 2 overall
    ("img", (615, 30, 950, 725)),     # 3 view 3 overall
    ("img", (950, 30, 1240, 725)),    # 4 view 4 overall
    ("img", (6, 756, 318, 1220)),     # 5 fuze head close-up
    ("img", (95, 35, 340, 300)),      # 6 ring and pin (view 1)
    ("img", (1075, 35, 1220, 580)),   # 7 lever and its tip (view 4)
    ("img", (360, 100, 590, 290)),    # 8 top collar and sleeve (view 2)
    ("img", (360, 260, 590, 630)),    # 9 hole rows and spacing (view 2)
    ("img", (946, 756, 1249, 1220)),  # 10 inner brass tube close-up
    ("img", (645, 330, 870, 560)),    # 11 ring line between rows (view 3)
    ("img", (360, 600, 585, 725)),    # 12 base cap side (view 2)
    ("img", (634, 756, 939, 1220)),   # 13 base cap notched end face
    ("img", (323, 756, 629, 1220)),   # 14 paint wear and chipping close-up
    ("img", (975, 35, 1215, 205)),    # 15 steel finish (fuze head, view 4)
    ("mask", (40, 30, 1240, 725)),    # 16 silhouettes only
]
key = []
for i, (kind, (x0, y0, x1, y1)) in enumerate(BOXES, 1):
    a = (RM if kind == "mask" else R)[y0:y1, x0:x1]; b = (OM if kind == "mask" else S)[y0:y1, x0:x1]
    h, w = a.shape[:2]
    k = min(3.0, 720.0 / h, 900.0 / w)
    a, b = resize(a, k), resize(b, k)
    ours_right = secrets.randbelow(2) == 1
    L, Rt = (a, b) if ours_right else (b, a)
    gap = np.full((a.shape[0], 10, 3), 128.0)
    write_png(OUTD + f"pair_{i:02d}.png", np.concatenate([L, gap, Rt], 1))
    key.append("right" if ours_right else "left")
print("M2KEY", ",".join(key))
