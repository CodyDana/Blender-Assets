# helper: RGB profiles. args: -- name:x:y:dx:dy:tmin:tmax
import numpy as np, os, sys
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
rgb = np.load(os.path.join(OUT, "rgb.npy"))
def bil(A, x, y):
    x0 = int(np.floor(x)); y0 = int(np.floor(y)); fx = x - x0; fy = y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)
for spec in sys.argv[sys.argv.index("--") + 1:]:
    p = spec.split(":"); name = p[0]; x, y, dx, dy, t0, t1 = map(float, p[1:])
    n = np.hypot(dx, dy); dx /= n; dy /= n
    print("==", name); row = []
    for t in np.arange(t0, t1 + 0.01, 1.0):
        v = np.mean([bil(rgb, x + t * dx - s * dy, y + t * dy + s * dx) for s in range(-6, 7, 2)], axis=0)
        row.append("%+3d %.2f,%.2f,%.2f" % (t, v[0], v[1], v[2]))
    for i in range(0, len(row), 6): print("  ".join(row[i:i + 6]))
