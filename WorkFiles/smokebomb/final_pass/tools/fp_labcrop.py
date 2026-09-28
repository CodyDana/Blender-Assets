import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png, read_png
a = read_png(sys.argv[1])[..., :3] / 255.0
x0, y0, w, h = map(int, sys.argv[3:7])
ims = [a[:, i * 627:(i + 1) * 627] for i in range(a.shape[1] // 627)]
c = [np.repeat(np.repeat(im[y0:y0+h, x0:x0+w], 2, 0), 2, 1) for im in ims]
write_png(sys.argv[2], np.concatenate(c, 1))
