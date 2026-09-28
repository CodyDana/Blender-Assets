# profile along a line from (x0,y0) to (x1,y1): lum, r-b, g-b, local 3x3 std of lum
import sys, os
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
lum = 0.2126*rgb[...,0]+0.7152*rgb[...,1]+0.0722*rgb[...,2]
a = list(map(float, sys.argv[sys.argv.index("--")+1:]))
for i in range(0, len(a), 4):
    x0,y0,x1,y1 = a[i:i+4]
    n = int(max(abs(x1-x0),abs(y1-y0)))+1
    print("profile (%g,%g)->(%g,%g)" % (x0,y0,x1,y1))
    for t in np.linspace(0,1,n):
        x = int(round(x0+t*(x1-x0))); y = int(round(y0+t*(y1-y0)))
        w = lum[y-1:y+2, x-1:x+2]
        r,g,b = rgb[y,x]
        print("  %4d %4d lum %.2f r-b %+.3f g-b %+.3f std %.3f" % (x,y,lum[y,x],r-b,g-b,w.std()))
