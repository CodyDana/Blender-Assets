import sys, os
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
lum = 0.2126*rgb[...,0]+0.7152*rgb[...,1]+0.0722*rgb[...,2]
rb = rgb[...,0]-rgb[...,2]
a = sys.argv[sys.argv.index("--")+1:]
y0, y1 = int(a[0]), int(a[1]); xs = list(map(int, a[2:]))
print("   y " + " ".join("   x=%4d   " % x for x in xs))
for y in range(y0, y1):
    print("%4d " % y + " ".join(" %4.2f %+5.3f " % (lum[y, x], rb[y, x]) for x in xs))
