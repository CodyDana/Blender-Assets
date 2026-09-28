import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import paperbomb_trace as PT
L = PT.load_layers()
x0, x1, y0, y1 = map(int, sys.argv[1:5])
np.set_printoptions(linewidth=250, precision=0, suppress=True)
print("cols", list(range(x0, x1)))
for y in range(y0, y1):
    print(y, " ".join("%3d" % int(v * 100) for v in L.red_behind[y, x0:x1]))
