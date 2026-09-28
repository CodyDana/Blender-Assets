# helper: print luminance/saturation profiles. args: -- name:x:y:dx:dy:tmin:tmax ...
import numpy as np, os, sys
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
L = np.load(os.path.join(OUT, "L.npy")); S = np.load(os.path.join(OUT, "S.npy"))
def bil(A, x, y):
    x0 = int(np.floor(x)); y0 = int(np.floor(y)); fx = x - x0; fy = y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)
for spec in sys.argv[sys.argv.index("--") + 1:]:
    p = spec.split(":"); name = p[0]; x, y, dx, dy, t0, t1 = map(float, p[1:])
    n = np.hypot(dx, dy); dx /= n; dy /= n
    print("==", name)
    row = []
    for t in np.arange(t0, t1 + 0.01, 1.0):
        # average across 5 px along tangent to suppress texture
        vals = []; svals = []
        for s in (-4, -2, 0, 2, 4):
            xx = x + t * dx - s * dy; yy = y + t * dy + s * dx
            vals.append(bil(L, xx, yy)); svals.append(bil(S, xx, yy))
        row.append("%+3d L%.2f S%.2f" % (t, np.mean(vals), np.mean(svals)))
    for i in range(0, len(row), 6):
        print("   ".join(row[i:i + 6]))
