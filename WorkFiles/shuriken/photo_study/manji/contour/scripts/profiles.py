import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
m = np.load(BASE + "/mask_solid.npy")
c = moore_trace(m)
print("coarse contour points", len(c))
np.save(BASE + "/coarse_contour.npy", c)
idx = douglas_peucker(c, 6.0)
print("DP(6px) vertices", len(idx))
V = c[idx]
segs = []
for k in range(len(idx)):
    a, b = idx[k], idx[(k + 1) % len(idx)]
    p, q = c[a], c[b]
    ln = np.hypot(*(q - p))
    segs.append((k, a, b, p, q, ln))
# averaged normal profiles for long segments
for (k, a, b, p, q, ln) in segs:
    if ln < 150: continue
    t = (q - p) / ln
    n = np.array([t[1], -t[0]])  # for clockwise contour in y-down coords, outward normal = (ty, -tx)
    # check outward: point p + 5n should be outside the mask
    mid = (p + q) / 2
    if m[int(mid[1] + 8 * n[1]), int(mid[0] + 8 * n[0])]: n = -n
    ss = np.linspace(0.15, 0.85, 60)
    ts = np.arange(-60, 50, 1.0)
    prof = np.zeros(len(ts))
    for s in ss:
        base = p + s * (q - p)
        prof += bilinear(L, base[0] + ts * n[0], base[1] + ts * n[1])
    prof /= len(ss)
    ang = np.degrees(np.arctan2(n[1], n[0]))
    print(f"seg {k:2d} len {ln:6.0f} normal_ang {ang:7.1f} mid ({mid[0]:.0f},{mid[1]:.0f})")
    print("   ", " ".join(f"{v:.2f}" for v in prof[::3]))
