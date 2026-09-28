import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
import bpy
OUTD = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/ref"
def load(p):
    im = bpy.data.images.load(p); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1, :, :3].copy(); return a
# common-scale tiles: D=200 px, axis col 220, bottom row 790. H(D) -> row = 790 - 200*H
PARTS = dict(head=(3.00, 3.97, -1.00, 1.15), sleeve_and_rowA=(2.15, 3.10, -0.62, 0.62), holes_rows=(0.85, 2.55, -0.62, 0.62),
             base_cap=(-0.04, 0.60, -0.62, 0.62), lever_lower=(0.70, 3.40, 0.35, 1.00))
for v in ['v1', 'v2', 'v3', 'v4']:
    t = load(f"{OUTD}/fb_ref_{v}_registered_common.png")
    for n, (h0, h1, x0, x1) in PARTS.items():
        r0 = max(0, int(round(790 - 200*h1))); r1 = min(t.shape[0], int(round(790 - 200*h0)))
        c0 = max(0, int(round(220 + 200*x0))); c1 = min(t.shape[1], int(round(220 + 200*x1)))
        save_png(f"{OUTD}/parts/fb_ref_{v}_{n}_common.png", t[r0:r1, c0:c1])
print("ok")
