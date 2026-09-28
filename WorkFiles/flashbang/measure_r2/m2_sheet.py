import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
W = ROOT + "WorkFiles/flashbang/measure_r2/"
args = sys.argv[sys.argv.index("--") + 1:]
out, y0, y1 = args[0], int(args[1]), int(args[2]); ims = args[3:]
R = load(REFP)[..., :3][y0:y1]
rows = [R] + [load(W + f)[..., :3][y0:y1] for f in ims]
sheet = np.concatenate(rows, 0)
save(W + out, resize(sheet, min(1.0, 1400 / sheet.shape[0])))
