import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
L=PT.load_layers(); fit=L.fit; data=PT.load_traced()
g=[g for g in data["groups"] if g["group"]=="seal_big"][0]
def to_px(p):
    x,y=fit.mm_to_px(p[:,0],p[:,1]); return np.stack([x,y],1)
base=[to_px(q) for q in PT.contour_only_polys_mm(g)]
spec=FF.KNOCKOUTS[0]; cx,cy=fit.mm_to_px(*spec["centre_mm"]); r=spec["half_mm"]*fit.ppmm
win=FF._Window(base,L.red_behind,L.density["red"],int(np.floor(cx-r)),int(np.floor(cy-r)),int(np.ceil(cx+r)),int(np.ceil(cy+r)))
f=lambda p: win.loss(FF.star_polys(p,4))
best=None
for c in [(52.5,509.0),(52.3,508.2),(52.0,507.6)]:
  for hs in (0.5,0.8):
    p0=np.array([c[0],c[1],0.8,0.4,0.4,0.4,0.4, math.radians(-90),9,hs,1.2, math.radians(90),8,hs,1.2, math.radians(229),9,hs,1.0, math.radians(31),9,hs,1.2])
    step=np.array([0.25,0.25,0.1,0.3,0.3,0.3,0.3]+[0.06,0.8,0.1,0.3]*4); mstep=np.array([0.01,0.01,0.004,0.01,0.01,0.01,0.01]+[0.003,0.03,0.004,0.01]*4)
    b,lb=FF.pattern_search(f,p0,step,mstep); b,lb=FF.pattern_search(f,b,step/3,mstep)
    print(c,hs,"init",round(f(p0),3),"fit",round(lb,3))
    if best is None or lb<best[1]: best=(b,lb)
print(best[0].round(3).tolist())
