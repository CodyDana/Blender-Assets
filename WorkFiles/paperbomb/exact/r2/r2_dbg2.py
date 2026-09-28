import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
L=PT.load_layers(); fit=L.fit
spec=FF.KNOCKOUTS[0]
cx,cy=fit.mm_to_px(*spec["centre_mm"]); r=spec["half_mm"]*fit.ppmm
win=FF._Window([],L.red_behind,L.density["red"],int(cx-r),int(cy-r),int(cx+r)+1,int(cy+r)+1)
win.base[:]=1
print(FF._star_centre_and_angles(win,cx,cy))
c2=FF._star_centre_and_angles(win,cx,cy)
for th in np.radians([31,95,229,270]):
    s,w=FF._ray_profile(win,52.6,509.0,th); print(round(math.degrees(th)), w.round(2))
