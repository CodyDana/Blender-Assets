import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
W = ROOT + "WorkFiles/flashbang/measure_r2/"
a = sys.argv[sys.argv.index("--") + 1:]
src, out, box, k = a[0], a[1], [int(x) for x in a[2].split(",")], float(a[3])
im = load(REFP if src == "REF" else W + src)[..., :3]
x0, y0, x1, y1 = box
save(W + out, resize(im[y0:y1, x0:x1], k))
