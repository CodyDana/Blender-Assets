import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
ref = np.load(D+"ref_rgb.npy"); lum = ref.mean(2); sat = ref.max(2)-ref.min(2)
bgm = lum > 0.95
print("BG", np.median(ref[bgm], 0), "corner", ref[5:30, 1100:1200].reshape(-1,3).mean(0), ref[5:30,380:420].reshape(-1,3).mean(0))
fg = (lum < 0.93) | (sat > 0.06)
for y0, y1 in [(0, 530), (560, 862), (885, 1195)]:
    m = fg[y0:y1, 790:1222]
    ys = np.where(m.any(1))[0]; xs = np.where(m.any(0))[0]
    print("PANEL", y0+ys.min(), y0+ys.max(), 790+xs.min(), 790+xs.max())
