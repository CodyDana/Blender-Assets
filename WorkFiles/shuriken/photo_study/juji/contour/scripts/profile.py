import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
D = np.load(ROOT + "D.npy")
bg = np.load(ROOT + "bgfit.npy")
v, s = hsv(rgb)
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
def row(y, x0, x1):
    print(f"row y={y}")
    for x in range(x0, x1, 3):
        blk = slice(y-2, y+3)
        print(f"  x={x} L={L[blk, x].mean():.3f} S={s[blk, x].mean():.3f} D={D[blk, x].mean():.3f} rgb={rgb[blk, x].mean(0).round(3)} bgL={(bg[blk,x]@np.array([0.2126,0.7152,0.0722])).mean():.3f}")
row(350, 590, 660)
row(300, 740, 790)
