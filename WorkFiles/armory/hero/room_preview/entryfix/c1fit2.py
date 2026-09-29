import numpy as np, math
from c1fit import *
def lintel_ok(cam, f, s):
    top = (13.5 + s * 36) / f     # 4:3 frame top slope
    return cam[2] + top * (0.24 - cam[1]) <= 3.63
def fitc(f):
    best=None
    idx = [2*i+1 for i in range(len(LM))] + list(range(2*len(LM), 2*len(LM)+len(BAR)))
    for yc in np.arange(-8.0, 0.01, 0.05):
        for zc in np.arange(2.0, 3.64, 0.02):
            cam=(6.0,yc,zc)
            r0=resid(cam,f,0.0)
            s=-float(np.mean(r0[idx]))/W
            if not lintel_ok(cam,f,s): continue
            e=rms(resid(cam,f,s))
            if best is None or e<best[0]: best=(e,cam,s)
    return best
for f in (24.5,28,30,32,35,38,40,45):
    e,cam,s=fitc(f)
    m=lantern_metrics(cam,f,s); m2=lantern_metrics(cam,f,s,w=1600,h=900)
    print(f"f {f}: rms {e:.1f} cam ({cam[1]:.2f},{cam[2]:.2f}) shift {s:.3f} sil {m['sil_ratio']:.3f} front {m['front_ratio']:.3f} top/front {m['top_over_front']:.3f} box43 {[round(v) for v in m['box']]} box169 {[round(v) for v in m2['box']]}")
