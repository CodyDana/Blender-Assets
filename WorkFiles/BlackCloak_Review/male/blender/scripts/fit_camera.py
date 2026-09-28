import sys, os, json, bpy
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from imgutil import load, save, lum
from align import best_align, warp, iou

set_visible(True, False)
ref = load(REF); refm = lum(ref) * 255 < 235
refm_h = refm[::2, ::2]
lo, hi = eval_bbox([cloak()])
tgt = (lo + hi) / 2; Hh = hi[2] - lo[2]
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.render.film_transparent = True
sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "SINGLE"
sc.render.resolution_x = 209; sc.render.resolution_y = 337; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
tmp = D + "logs/_fit_tmp.png"
res = []
grid = [(f, y, p) for f in (50, 85, 100, 135) for y in range(-20, 21, 5) for p in (-5, 0, 5, 10, 15)]
if len(sys.argv) > sys.argv.index("--") + 1:  # refine around a given best
    f0, y0, p0 = map(float, sys.argv[sys.argv.index("--") + 1:][:3])
    grid = [(f0 + df, y0 + dy, p0 + dp) for df in (-15, 0, 15) for dy in (-4, -2, 0, 2, 4) for dp in (-4, -2, 0, 2, 4)]
for f, y, p in grid:
    dist = (Hh / 2 * 1.08) / (12 / f)
    make_camera(tgt, y, p, f, dist)
    sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
    m = load(tmp)[..., 3] > 0.5
    v, (s, tx, ty) = best_align(m, refm_h)
    res.append((float(v), f, y, p, float(s), float(tx), float(ty)))
    print("FIT", f, y, p, round(v, 4), flush=True)
res.sort(reverse=True)
tag = "refine" if len(grid) < 100 else "coarse"
json.dump({"target": list(map(float, tgt)), "height_m": float(Hh), "ref_mask": "lum<235 at half res",
           "cols": "iou, focal_mm, yaw_deg, pitch_deg, s, tx, ty (half-res ref px)", "top": res[:15]},
          open(D + "logs/camfit_male_%s.json" % tag, "w"), indent=1)
os.remove(tmp)
print("BEST", res[:5])
