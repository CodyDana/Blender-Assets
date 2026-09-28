"""DEV: stack the reference top row (rows y0..y1) above a render's same rows (and optional more renders).
blender -b --factory-startup --python fb_stack.py -- out.png y0 y1 render1.png [render2.png ...]"""
import sys
from pathlib import Path
P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/props"))
import numpy as np
from props_lib import flashbang_look as LK
a = sys.argv[sys.argv.index("--") + 1:]
out, y0, y1 = a[0], int(a[1]), int(a[2])
ref = np.load(P / "WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3]
rows = [ref[y0:y1]]
for r in a[3:]:
    im = LK.load_png(str(Path(r).resolve()))
    rows.append(np.full((6, im.shape[1], 3), 1.0))
    rows.append(im[y0:y1])
LK.save_png(str(Path(out).resolve()), np.concatenate(rows, 0))
