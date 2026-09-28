import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
L=PT.load_layers(); fit=L.fit; data=PT.load_traced()
g=[g for g in data["groups"] if g["group"]=="seal_big"][0]
def to_px(p):
    x,y=fit.mm_to_px(p[:,0],p[:,1]); return np.stack([x,y],1)
base=[to_px(q) for q in PT.contour_only_polys_mm(g)]
k=g["knockouts_mm"][0]; er=[to_px(np.asarray(q)) for q in k["polys_mm"]]
x0,y0,x1,y1=k["params_px"] and [int(v) for v in (0,0,0,0)]
spec=FF.KNOCKOUTS[0]; cx,cy=fit.mm_to_px(*spec["centre_mm"]); r=spec["half_mm"]*fit.ppmm
win=FF._Window(base,L.red_behind,L.density["red"],int(np.floor(cx-r)),int(np.floor(cy-r)),int(np.ceil(cx+r)),int(np.ceil(cy+r)))
np.set_printoptions(linewidth=250, precision=2, suppress=True)
pr=win.render(er); d=(pr-win.obs)
print("loss", (d[win.inner]**2).sum(), "dens", win.dens[0,0])
print(d[win.inner].reshape(win.y1-win.y0,-1))
