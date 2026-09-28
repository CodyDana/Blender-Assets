import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
mpath = sys.argv[1] if len(sys.argv) > 1 else BASE + "/mask_refined.npy"
eps = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
minlen = float(sys.argv[3]) if len(sys.argv) > 3 else 40
m = np.load(mpath)
c = moore_trace(m)
idx = douglas_peucker(c, eps)
print("contour", len(c), "DP", eps, "vertices", len(idx))
for k in range(len(idx)):
    a, b = idx[k], idx[(k + 1) % len(idx)]
    p, q = c[a], c[b]; d = q - p; ln = np.hypot(*d)
    if ln >= minlen:
        print(f"{k:4d} i{a:6d}-{b:6d} ({p[0]:6.0f},{p[1]:6.0f})->({q[0]:6.0f},{q[1]:6.0f}) len {ln:6.0f} dir {np.degrees(np.arctan2(d[1], d[0])):7.1f}")
