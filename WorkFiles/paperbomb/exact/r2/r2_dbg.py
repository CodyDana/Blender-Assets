import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
L=PT.load_layers(); fit=L.fit
spec=FF.KNOCKOUTS[2]
bx0,by0=fit.mm_to_px(*spec["box_mm"][:2]); bx1,by1=fit.mm_to_px(*spec["box_mm"][2:])
print(bx0,by0,bx1,by1)
win=FF._Window([],L.red_behind,L.density["red"],int(bx0),int(by0),int(math.ceil(bx1)),int(math.ceil(by1)))
win.base[:]=1
p,n=FF._slots_init(win,(bx0,by0,bx1,by1),4); print(p.round(2),n)
