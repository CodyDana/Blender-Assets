import os, sys, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT, "lum.npy")); tex = np.load(os.path.join(OUT, "tex.npy"))
a = sys.argv[sys.argv.index("--")+1:]
for i in range(0, len(a), 3):
    x, y0, y1 = int(a[i]), int(a[i+1]), int(a[i+2])
    print("column x=%d" % x)
    for y in range(y0, y1):
        print("   y %4d lum %.2f tex %.4f" % (y, lum[y, x], tex[y, x]))
