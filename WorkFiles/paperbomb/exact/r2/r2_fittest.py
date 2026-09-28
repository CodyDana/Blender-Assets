import os, sys, json, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
from props_lib import paperbomb_finefit as FF
import xt_io
L = PT.load_layers(); fit=L.fit
data = PT.load_traced()
obs = L.red_behind; dens = L.density["red"]
def to_px(p):
    x,y = fit.mm_to_px(p[:,0],p[:,1]); return np.stack([x,y],1)
for spec in FF.KNOCKOUTS:
    g = next(g for g in data["groups"] if g["group"]==spec["group"] and g["layer"]==spec["layer"])
    curves=[T.Curve([np.asarray(p) for p in cj["pieces"]], bool(cj["periodic"])) for cj in g["curves_mm"]]
    polys=[to_px(c.sample(0.01)) for c in curves]
    areas=[T.signed_area(c.sample(0.02)) for c in curves]
    sgn=np.sign(areas[int(np.argmax(np.abs(areas)))])
    wx0,wy0,wx1,wy1=FF.window_mm(spec)
    keep=[]; removed=0
    for c,a,pp in zip(curves,areas,polys):
        q=c.sample(0.02); cen=q.mean(0)
        if not spec.get("keep_core") and np.sign(a)!=sgn and abs(a)<FF.MAX_REPLACED_HOLE_MM2 and wx0<=cen[0]<=wx1 and wy0<=cen[1]<=wy1:
            removed+=1; continue
        keep.append(pp)
    t=time.time()
    r = FF.fit_knockout(spec, keep, obs, dens, fit)
    # loss with the traced holes (as shipped r1)
    x0,y0,x1,y1=r["window_px"]
    win=FF._Window(polys,obs,dens,x0,y0,x1,y1)
    lr1=win.loss([])
    print(spec["name"], "removed holes",removed, "loss r1 traced %.4f  holes removed %.4f  init %.4f  fit %.4f  (%.1fs)"%(lr1,r["loss_traced_holes_removed"],r["loss_init"],r["loss_fit"],time.time()-t))
    print("  params", r["params_px"])
    win2=FF._Window(keep,obs,dens,x0,y0,x1,y1)
    pred=win2.render(r["polys_px"]); pr1=win.render([])
    # hi-res crisp view of the fitted mask (8x)
    S=16
    hh,ww=win2.h*S,win2.w*S
    base=T.fill_polys([ (q-win2.off)*S for q in keep],hh,ww,ss=2)
    er=T.fill_polys([ (q-win2.off)*S for q in r["polys_px"]],hh,ww,ss=2)
    crisp=base*(1-er)
    up=lambda a: np.repeat(np.repeat(a,S,0),S,1)
    ref=L.src.rgb[win2.gy0:win2.gy1,win2.gx0:win2.gx1]
    g3=lambda a: np.repeat(np.clip(a,0,1)[...,None],3,-1)
    sep=np.ones((hh,6,3))
    xt_io.write("fit_%s.png"%spec["name"], np.concatenate([up(ref),sep,g3(up(win2.obs)),sep,g3(up(pr1)),sep,g3(up(pred)),sep,g3(1-crisp)],1))
    np.set_printoptions(linewidth=250, precision=2, suppress=True)
    if spec["name"]=="seal_spark_TL":
        print("obs"); print(win2.obs[win2.inner].reshape(win2.y1-win2.y0,-1))
        print("fit - obs"); print((pred-win2.obs)[win2.inner].reshape(win2.y1-win2.y0,-1))
        print("r1 - obs"); print((pr1-win.obs)[win.inner].reshape(win.y1-win.y0,-1))
