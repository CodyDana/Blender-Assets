import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
M = np.load(ROOT + "M.npy")
def row(y, x0, x1, step=2):
    print(f"row y={y}: " + " ".join(f"{x}:{M[y-1:y+2, x].mean():.1f}" for x in range(x0, x1, step)))
def col(x, y0, y1, step=2):
    print(f"col x={x}: " + " ".join(f"{y}:{M[y, x-1:x+2].mean():.1f}" for y in range(y0, y1, step)))
row(350, 600, 670); row(450, 610, 680); row(300, 730, 790); row(1100, 590, 650); row(1100, 780, 830)
col(300, 540, 600); col(300, 720, 780); col(1100, 520, 580); col(1100, 680, 750)
