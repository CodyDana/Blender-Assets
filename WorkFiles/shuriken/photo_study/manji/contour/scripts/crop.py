# crop.py x0 y0 x1 y1 scale out.png  -- crop of original with mask edge (red) overlaid, nearest-neighbour upscaled
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
x0, y0, x1, y1, sc = map(int, sys.argv[1:6]); out = sys.argv[6]
px = np.load(BASE + "/manji_pixels.npy")
m = np.load(BASE + "/mask_solid.npy") if len(sys.argv) < 8 else np.load(sys.argv[7])
c = px[y0:y1, x0:x1].copy(); mm = m[y0:y1, x0:x1]
edge = (mm ^ np.roll(mm, 1, 0)) | (mm ^ np.roll(mm, 1, 1))
edge[0, :] = False; edge[:, 0] = False
c[edge] = [1, 0, 0]
c = np.repeat(np.repeat(c, sc, 0), sc, 1)
write_png(out, c)
