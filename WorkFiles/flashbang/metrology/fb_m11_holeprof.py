import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb()
pm = np.load(DBG + "/fb_paint.npy")
g = ref[..., 1] - 0.5*(ref[..., 0] + ref[..., 2])   # greenness
# for each centre hole, report paint-green boundary along the horizontal line through centre and vertical line through centre
for name, (cx, cy) in dict(v2A=(469, 324), v2B=(469, 442), v2C=(469, 562), v3A=(760, 325), v3B=(760, 443), v3C=(760, 562)).items():
    row = g[cy-2:cy+3, cx-50:cx+51].mean(0); colv = g[cy-55:cy+56, cx-2:cx+3].mean(1)
    # half-max threshold between paint level and hole level
    def cross(p, off):
        p = gauss_blur(np.tile(p[None], (3, 1)), 0.7)[1]
        paint = np.median(np.r_[p[:6], p[-6:]]); inner = np.median(p[len(p)//2-8:len(p)//2+8])
        t = 0.5*(paint + inner)
        c = len(p)//2
        i = c
        while i > 0 and p[i] < t: i -= 1
        l = i + (t - p[i])/(p[i+1]-p[i]+1e-9)
        j = c
        while j < len(p)-1 and p[j] < t: j += 1
        r = j - 1 + (t - p[j-1])/(p[j]-p[j-1]+1e-9)
        return l + off, r + off, paint, inner
    l, r, pp, ii = cross(row, cx-50); t, b, _, _ = cross(colv, cy-55)
    print(name, f"x {l:.1f}..{r:.1f} w={r-l:.1f} cx={0.5*(l+r):.1f} | y {t:.1f}..{b:.1f} h={b-t:.1f} cy={0.5*(t+b):.1f} | paint {pp:.3f} inner {ii:.3f}")
