import sys, os
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
lum = 0.2126*rgb[...,0]+0.7152*rgb[...,1]+0.0722*rgb[...,2]
a = sys.argv[sys.argv.index("--")+1:]
mode = a[0]; y0, y1 = int(a[1]), int(a[2]); xs = list(map(int, a[3:]))
if mode == "col":
    print("   y " + " ".join("%5d" % x for x in xs))
    for y in range(y0, y1):
        print("%4d " % y + " ".join("%5.2f" % lum[y, x] for x in xs))
else:  # rows: y0..y1 are x range, xs are rows
    print("   x " + " ".join("%5d" % x for x in xs))
    for x in range(y0, y1):
        print("%4d " % x + " ".join("%5.2f" % lum[y, x] for y in xs))
