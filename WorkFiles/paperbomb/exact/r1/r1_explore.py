import os, sys, json, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
t0=time.time()
L = PT.load_layers()
print("layers", time.time()-t0)
ak, behind, unm = T.ink_layers(L.src, L.fit)
H,W = ak.shape
data = PT.load_traced()
fit=L.fit
def to_px(p):
    x,y = fit.mm_to_px(p[:,0],p[:,1]); return np.stack([x,y],1)
pred={}
for layer in ("black","red"):
    polys=[]
    for g in data["groups"]:
        if g["layer"]==layer: polys += [to_px(p) for p in PT.group_polys_mm(g,0.02)]
    box = T.fill_polys(polys,H,W,ss=16).astype(np.float64)
    pred[layer]=T.gauss_blur(box,0.4)
for layer, obs in (("black",ak),("red",behind)):
    d = L.density[layer]; p=pred[layer]
    ins = L.inside
    print(layer, "density pct", np.percentile(d[ins & (obs>0.5)],[1,10,50,90,99]).round(3))
    print(layer, "obs in core pct", np.percentile(obs[ins&(p>0.95)],[1,5,10,50,90]).round(3))
    r = np.clip(obs - p*d, 0, 1)
    far = ins & (p<0.05)
    print(layer, "resid far from shapes pct", np.percentile(r[far],[50,90,99,99.9]).round(3), "count>0.1", int((r[far]>0.1).sum()), ">0.25", int((r[far]>0.25).sum()))
    near = ins & (p>=0.05)&(p<0.5)
    print(layer, "resid near edge pct", np.percentile(r[near],[50,90,99]).round(3))
    neg = np.clip(p*d-obs,0,1)
    print(layer, "missing inside pct", np.percentile(neg[ins&(p>0.5)],[50,90,99]).round(3))
print("unassigned", data.get("unassigned_ink_px"))
# paper
rgb = L.src.rgb
paper_px = L.inside & (ak+behind<0.03)
print("paper px", paper_px.sum(), "of inside", L.inside.sum())
sm = T.norm_conv(rgb, paper_px.astype(float), 3.0, [0.96,0.89,0.75])
det = (rgb-sm)
lum = det@np.array([0.2126,0.7152,0.0722])
print("paper detail luma std", lum[paper_px].std(), "pct", np.percentile(lum[paper_px],[1,50,99]).round(4))
print("paper median stored", np.median(rgb[paper_px],0).round(4))
print("black core stored median", np.median(rgb[L.inside&(ak>0.95)],0).round(4))
# spectrum of paper detail: variance of differences at lag 1
d1 = lum[:,1:]-lum[:,:-1]; m1 = paper_px[:,1:]&paper_px[:,:-1]
print("lag1 diff std", d1[m1].std())
