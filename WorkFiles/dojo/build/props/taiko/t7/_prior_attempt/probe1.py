import sys, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
T7 = Path(sys.argv[1])
sys.path.insert(0, str(T7))
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/props/taiko")
import photo_cam as PC
import taiko_uv as UVL
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
img = Image.open(ROOT / "References/Dojo/taiko_tacks_ref_user.webp").convert("RGB")
d = ImageDraw.Draw(img)
th = np.linspace(-math.pi, math.pi, 721)
for x, r, col in ((0.7016, 0.547, (255, 0, 255)), (-0.7016, 0.547, (255, 0, 255)),
                  (UVL.X_SK, UVL.body_r(UVL.X_SK) + 0.0045, (0, 0, 255)), (-UVL.X_SK, UVL.body_r(UVL.X_SK) + 0.0045, (0, 0, 255)),
                  (0.5145 - UVL.D_SHIFT, UVL.body_r(0.5145 - UVL.D_SHIFT), (0, 160, 0)),
                  (-(0.5145 - UVL.D_SHIFT), UVL.body_r(0.5145 - UVL.D_SHIFT), (0, 160, 0))):
    p = PC.project_design(PC.cyl(x, r, th))
    front = np.cos(th) < 0.05
    d.point([tuple(q) for q in p[front]], fill=col)
# body silhouettes
for side in (-1, 1):
    pts = []
    for x in np.linspace(-0.65, 0.65, 100):
        r = UVL.body_r(x)
        pts.append(tuple(PC.project_design(PC.cyl(x, r, PC.contour_th(r, side)))[0]))
    d.line(pts, fill=(255, 0, 0))
img.save(T7 / "probe1.png")
print("X_SK", UVL.X_SK, "band", 0.655 - UVL.D_SHIFT)
for x in (0.6016, 0.5796, 0.5344, 0.4391, -0.4391, -0.5344):
    print(x, PC.project_design(PC.cyl(x, UVL.body_r(x), math.pi))[0])
