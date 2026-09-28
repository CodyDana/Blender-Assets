import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
W = ROOT + "WorkFiles/flashbang/measure_r2/"
a = sys.argv[sys.argv.index("--") + 1:]
out, box, ims = a[0], [int(x) for x in a[1].split(",")], a[2:]
x0, y0, x1, y1 = box
R = load(REFP)[..., :3][y0:y1, x0:x1]
cols = [R] + [load(W + f)[..., :3][y0:y1, x0:x1] for f in ims]
gap = np.full((R.shape[0], 6, 3), 128.0)
parts = []
for c in cols: parts += [c, gap]
sheet = np.concatenate(parts[:-1], 1)
k = min(1.0, 1900 / sheet.shape[1], 1000 / sheet.shape[0])
save(W + out, resize(sheet, k) if k < 1 else sheet)
