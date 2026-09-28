import os, sys, json, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
from props_lib import paperbomb_tracedart as TA
import xt_io
t0=time.time()
m = TA.reference_model()
print("model s", round(time.time()-t0,1))
L=m.L; fit=L.fit
np.set_printoptions(linewidth=250, precision=2, suppress=True)
# loops per group with area/centroid (mm)
for g in m.traced["groups"]:
    if g["group"] in ("seal_big","small_seal","frame"):
        for cj in g["curves_mm"]:
            c = T.Curve([np.asarray(p) for p in cj["pieces"]], bool(cj["periodic"]))
            q = c.sample(0.02); a = T.signed_area(q)
            print(g["group"], g["layer"], "area mm2 %.3f"%a, "centroid", q.mean(0).round(2), "bbox", q.min(0).round(2), q.max(0).round(2))
def crop(x0,y0,x1,y1,name,S=16):
    px0,py0 = fit.mm_to_px(x0,y0); px1,py1=fit.mm_to_px(x1,y1)
    i0,i1=int(py0),int(py1)+1; j0,j1=int(px0),int(px1)+1
    print("==",name,"px rows",i0,i1,"cols",j0,j1)
    ref=L.src.rgb[i0:i1,j0:j1]
    fields=[ref]
    for f in (L.black, L.red_behind, m.psf["black"], m.psf["red"], m.tone["black"], m.tone["red"], m.resid["black"], m.resid["red"]):
        fields.append(np.repeat(np.clip(f[i0:i1,j0:j1],0,1)[...,None],3,-1))
    sep=np.ones((i1-i0,1,3))
    row=[]
    for f in fields: row+=[f,sep]
    xt_io.write("probe_%s.png"%name, np.concatenate(row[:-1],1), scale=S)
    return (i0,i1,j0,j1)
w=crop(5.0,121.8,24.6,150.6,"sealbig",8)
w=crop(55.6,136.2,63.3,151.3,"smallseal",16)
w=crop(20,4.5,50,8.5,"ruletop",8)
w=crop(0,0,12.8,15.6,"cTL",16)
