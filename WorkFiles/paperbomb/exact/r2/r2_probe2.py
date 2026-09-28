import os, sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_tracedart as TA
import xt_io
m = TA.reference_model(); L=m.L; fit=L.fit
np.set_printoptions(linewidth=250, precision=2, suppress=True)
def show(cx,cy,r,name,f):
    px,py = fit.mm_to_px(cx,cy); i=int(py); j=int(px); R=int(r*fit.ppmm)+1
    print("==",name,"centre px",round(px,2),round(py,2),"rows",i-R,i+R+1,"cols",j-R,j+R+1)
    print(f[i-R:i+R+1,j-R:j+R+1])
    return i-R,i+R+1,j-R,j+R+1
for nm,(cx,cy) in (("spkTL",(9.6,126.9)),("spkBR",(20.8,146.3))):
    i0,i1,j0,j1=show(cx,cy,2.2,nm+" red_behind",L.red_behind)
    show(cx,cy,2.2,nm+" density",L.density["red"])
    xt_io.write("probe_%s.png"%nm, np.concatenate([L.src.rgb[i0:i1,j0:j1], np.repeat(L.red_behind[i0:i1,j0:j1,None],3,-1)],1), scale=24)
i0,i1,j0,j1=show(59.4,147.8,1.8,"dou_box red_behind",L.red_behind)
xt_io.write("probe_dou.png", np.concatenate([L.src.rgb[i0:i1,j0:j1], np.repeat(L.red_behind[i0:i1,j0:j1,None],3,-1)],1), scale=24)
show(3.6,8.6,1.6,"cTL black",L.black)
show(3.6,8.6,1.6,"cTL red_behind",L.red_behind)
i0,i1,j0,j1=show(3.6,8.6,1.6,"cTL tone black",m.tone["black"])
xt_io.write("probe_cTLknob.png", np.concatenate([L.src.rgb[i0:i1,j0:j1], np.repeat(L.black[i0:i1,j0:j1,None],3,-1), np.repeat(L.red_behind[i0:i1,j0:j1,None],3,-1)],1), scale=24)
