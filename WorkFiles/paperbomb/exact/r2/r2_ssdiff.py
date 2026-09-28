import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT
L=PT.load_layers(); fit=L.fit; H,W=L.black.shape
def to_px(p):
    x,y=fit.mm_to_px(p[:,0],p[:,1]); return np.stack([x,y],1)
def pred(path):
    d=json.load(open(path,encoding="utf-8"))
    polys=[];er=[]
    for g in d["groups"]:
        if g["layer"]=="red":
            polys+=[to_px(q) for q in PT.group_polys_mm(g,0.01)]; er+=[to_px(q) for q in PT.knockout_polys_mm(g)]
    box=T.fill_polys(polys,H,W,ss=16).astype(float)
    if er: box*=1-T.fill_polys(er,H,W,ss=16)
    return T.gauss_blur(box,0.4)*L.density["red"]
masks=PT.group_masks(L); regs=PT.group_regions(L,masks); er_=PT.element_regions(L,masks,regs)
reg=er_[("small_seal","red")] & ~(L.black>0.85)
obs=L.red_behind
for nm,path in (("r1","bak_r1/paperbomb_traced.json"),("r2",r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_traced.json")):
    p=pred(path)
    wrong=reg&((p>0.5)!=(obs>0.5))
    ys,xs=np.nonzero(wrong)
    print(nm, PT.score_fields(p,obs,reg,fit.ppmm)["iou"], "wrong px", len(ys))
    print("  ", [(int(y),int(x),round(float(obs[y,x]),2),round(float(p[y,x]),2)) for y,x in zip(ys,xs)])
