import os, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT, "lum.npy"))
H, W = lum.shape
for y in [0,1,2,5,10,1210,1215,1218,1220,1221,1222,1223]:
    r = lum[y]
    print("row %4d: " % y + " ".join("%.2f" % r[x] for x in range(0, W, 60)))
for x in [0,1,2,5,10,1205,1210,1214,1216]:
    c = lum[:, x]
    print("col %4d: " % x + " ".join("%.2f" % c[y] for y in range(0, H, 60)))
