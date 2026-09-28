import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts"); sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import fan_look as LK, fan_refview as RV
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/dev1/"
ref = LK.load_png(r"C:/Users/Cody/Desktop/Blender_Projects/References/Fan/fan2.png")[..., :3].astype(np.float64)
ren = LK.load_png(D + "Renders/Fan/fan_reference_view.png")[..., :3].astype(np.float64)
for nm, img in (("ref", ref), ("ren", ren)):
    m = RV.photo_mask(img)
    out = {}
    for side, (x0, x1) in (("left", (90, 330)), ("right", (460, 720))):
        xs, ys = [], []
        for x in range(x0, x1):
            col = np.nonzero(m[:, x])[0]
            col = col[col < 560]
            if len(col): xs.append(x); ys.append(col.max())
        p = np.polyfit(xs, ys, 1)
        out[side] = (round(math.degrees(math.atan(-p[0])), 3), round(np.polyval(p, 200 if side == "left" else 600), 2))
    # top arc radius about the rivet at several angles
    H, W = m.shape
    rads = []
    for ang in (30, 60, 90, 120, 150):
        a = math.radians(ang)
        r = 150
        while r < 420:
            x = int(round(RV.RIVET_PX[0] + r * math.cos(a))); y = int(round(RV.RIVET_PX[1] - r * math.sin(a)))
            if not m[y, x]: break
            r += 0.5
        rads.append(r)
    print(nm, out, "edge radius at 30..150", rads)
