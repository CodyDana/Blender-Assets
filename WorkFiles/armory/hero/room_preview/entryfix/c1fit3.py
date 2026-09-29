import numpy as np, math, c1fit
from c1fit import *
c1fit.LM[:] = [l for l in c1fit.LM if l[0][2] != 1.45]   # drop the glass tops (a design difference, not the camera)
from c1fit2 import fitc
import sys
for f in (24.5,28,30,32,35,38,40):
    e,cam,s=fitc(f)
    m=lantern_metrics(cam,f,s)
    r=resid(cam,f,s)
    print(f"f {f}: rms {e:.1f} cam ({cam[1]:.2f},{cam[2]:.2f}) shift {s:.3f} front {m['front_ratio']:.3f} top/front {m['top_over_front']:.3f} box {[round(v) for v in m['box']]} case_bot {round(proj((5.1,3.05,0),cam,f,s)[1])} bar {round(proj((6,2.72,0),cam,f,s)[1])}-{round(proj((6,2.56,0),cam,f,s)[1])} paint {[round(v) for v in proj((4.8,15.9,3.8),cam,f,s)]} {[round(v) for v in proj((7.2,15.9,1.5),cam,f,s)]}")
