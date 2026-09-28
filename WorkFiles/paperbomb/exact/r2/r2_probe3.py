import os, sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_tracedart as TA
m = TA.reference_model(); L=m.L; fit=L.fit
np.set_printoptions(linewidth=250, precision=2, suppress=True)
for g in m.traced["groups"]:
    if g["group"]=="frame":
        for s in g["strokes_mm"]:
            if s["side"]=="T":
                c=np.array(s["centre_mm"]); w=np.array(s["width_mm"])
                print(g["layer"], "T stroke x range", c[0,0], c[-1,0], "n", len(w))
                for x in np.arange(12,58,0.5):
                    i=np.argmin(abs(c[:,0]-x)); print("  x %.1f y %.3f w %.3f"%(c[i,0],c[i,1],w[i]))
# black field around top rule rows
px0,py=fit.mm_to_px(20,6.56); px1,_=fit.mm_to_px(50,6.56)
print("row py",py)
i=int(py)
for r in range(i-2,i+3):
    print(r, L.black[r,int(px0):int(px1)])
print("red")
for r in range(i-2,i+3):
    print(r, L.red_behind[r,int(px0):int(px1)])
print("psf black"); 
for r in range(i-2,i+3): print(r, m.psf["black"][r,int(px0):int(px1)])
print("tone black"); 
for r in range(i-1,i+2): print(r, m.tone["black"][r,int(px0):int(px1)])
print("resid black"); 
for r in range(i-2,i+3): print(r, m.resid["black"][r,int(px0):int(px1)])
