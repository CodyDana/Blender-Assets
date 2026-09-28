import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_tracedart as TA
m=TA.reference_model(); L=m.L
np.set_printoptions(linewidth=250, precision=2, suppress=True)
for c in (249,250,251,252):
    print("col",c)
    print(" obs ", L.red_behind[580:600,c])
    print(" psf*d", (m.psf["red"]*L.density["red"])[580:600,c])
    print(" tone", m.tone["red"][580:600,c])
    print(" resid", m.resid["red"][580:600,c])
g=[g for g in m.traced["groups"] if g["group"]=="small_seal"][0]
for k in g["knockouts_mm"]: print(k["name"], k["params_px"], k["loss"], k["replaced_traced_holes"])
