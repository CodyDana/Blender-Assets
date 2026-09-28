"""Target sheet: the photo's garment outline mapped onto the male (nominal 365 ref px per metre, floor at photo row 662,
his midline at photo column 200) drawn over a render of the fitting body in ARMS_DOWN_V2 seen by a photo-like camera
(focal 100, yaw 0), plus the Jin-derived targets (funnel rim heights, clasp, opening band). Writes
spec/out/spec_target_overlay.png (2x of 417x674) and spec/out/spec_photo_on_male_rows.json (photo outline in metres)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import numpy as np
from mathutils import Vector
from v2m_common import *
import v2m_lib as L

PPM, FLOOR_ROW, MID_COL = 365.0, 662.0, 200.0
os.chdir(ROOT)
fit = fitbody(); drop_haircards(); arm = fit["armature"]
apply_pose(arm, ARMS_DOWN_V2)
arm.hide_render = True
if fit.get("head_parts"): fit["head_parts"].hide_render = True
span = REF_H / PPM
zc = (FLOOR_ROW - REF_H / 2) / PPM          # world z at the frame centre row
xc = (REF_W / 2 - MID_COL) / PPM
cam, rec = make_camera("photo", None, {"frame": "fixed", "target": (xc, 0.0, zc), "span_m": span, "res": (REF_W * 2, REF_H * 2)})
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.85, 0.72, 0.64)
sc.render.film_transparent = False
p = os.path.join(SPEC_OUT, "_spec_body_photo_cam.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
img = L.load(p)
refm = np.load(os.path.join(SPEC_OUT, "ref_photo_mask.npy"))
ov = img.copy()
b = L.boundary(refm)
for y, x in b:
    ov[2 * y:2 * y + 2, 2 * x:2 * x + 2] = (220, 30, 30)
def px(pt):
    q = project(cam, [pt])[0]; return int(q[0]), int(q[1])
def dot(pt, col, r=5):
    x, y = px(pt); ov[max(0, y - r):y + r, max(0, x - r):x + r] = col
def hline(z, x0, x1, col):
    a_ = px((x0, -0.2, z)); b_ = px((x1, -0.2, z)); ov[a_[1]:a_[1] + 2, min(a_[0], b_[0]):max(a_[0], b_[0])] = col
LM = json.load(open(os.path.join(SPEC_OUT, "male_landmarks.json")))
hline(1.690, -0.06, 0.06, (0, 160, 255))    # funnel rim front target
hline(1.710, -0.10, -0.035, (0, 160, 255)); hline(1.710, 0.035, 0.10, (0, 160, 255))
hline(1.745, -0.14, 0.14, (0, 90, 200))      # funnel back rim
dot((-0.185, -0.12, 1.48), (40, 40, 40), 7)  # clasp
hline(0.95, -0.28, -0.18, (0, 170, 0))       # opening band at the hand
hline(0.0, -0.6, 0.6, (120, 120, 120))
L.save(os.path.join(SPEC_OUT, "spec_target_overlay.png"), ov)
os.remove(p)
# photo outline in metres on him
rows = []
for y in range(7, 661, 6):
    xs = np.nonzero(refm[y])[0]
    if len(xs): rows.append({"z_m": round((FLOOR_ROW - y) / PPM, 4), "x_right_m(his right, -X)": round((xs[0] - MID_COL) / PPM, 4), "x_left_m(his left, +X)": round((xs[-1] - MID_COL) / PPM, 4), "width_m": round((xs[-1] - xs[0] + 1) / PPM, 4)})
json.dump({"mapping": {"ref_px_per_m": PPM, "floor_row": FLOOR_ROW, "midline_col": MID_COL, "front_view_camera": rec}, "rows": rows},
          open(os.path.join(SPEC_OUT, "spec_photo_on_male_rows.json"), "w"), indent=1, default=float)
print("V2M OVERLAY done")
