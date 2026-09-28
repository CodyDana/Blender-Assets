import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
x0, y0, x1, y1, k, name = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
c = np.repeat(np.repeat(rgb[y0:y1, x0:x1], k, 0), k, 1).copy()
# tick marks every 10 px along top and left border
for i in range(0, x1 - x0, 10): c[:6, i * k] = [1, 0, 0]
for j in range(0, y1 - y0, 10): c[j * k, :6] = [1, 0, 0]
write_png(ROOT + name, c)
