"""Render the SHIPPED BlackCloak_MH_v2 FBX on the male for measurement / judging (Blender 5.2 headless).

blender -b --factory-startup --python v2m_render.py -- --view photo|jin|front|q34|q34_other|side_r|side_l|back|face|hem
      [--fbx Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx] [--tex <Textures dir>] [--params <material_params.json>]
      [--pose down|rest] [--body 0|1] [--mult 3] [--samples 256] [--yaw Y --pitch P --focal F] --out <dir> --tag <name>

Writes <out>/<tag>.png (Cycles beauty, Standard, white card = 0.90, film transparent), <out>/<tag>_id.png (Workbench flat
ID: garment black, torso red, legs yellow, arms green, neck magenta, head blue; with --body 1), <out>/<tag>_alpha.png
(garment-only alpha) and <out>/<tag>.json (camera, calibration, materials, projected 3D landmarks).
--pose down = ARMS_DOWN_V2 (the look / drape pose); the garment is spine-skinned so its bind shape is unchanged by it.
The photo view frames the garment bbox like the review camfit (focal 100, yaw 0, pitch 0, H*1.08) at 417x674 * mult."""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import numpy as np
from v2m_common import *

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--view", required=True); ap.add_argument("--fbx", default=DEFAULT_FBX)
ap.add_argument("--tex", default=None); ap.add_argument("--params", default=None)
ap.add_argument("--pose", default="down"); ap.add_argument("--body", type=int, default=0)
ap.add_argument("--mult", type=int, default=3); ap.add_argument("--samples", type=int, default=256)
ap.add_argument("--yaw", type=float); ap.add_argument("--pitch", type=float); ap.add_argument("--focal", type=float)
ap.add_argument("--out", required=True); ap.add_argument("--tag", required=True)
ap.add_argument("--no-beauty", action="store_true")
ap.add_argument("--clasp-keys", default="clasp,button", help="material-name keys of the clasp slot")
A = ap.parse_args(argv)
# Blender resolves relative render paths against the drive root in -b mode: make every path absolute
os.chdir(ROOT)
A.out = os.path.abspath(A.out); A.fbx = os.path.abspath(A.fbx)
if A.tex: A.tex = os.path.abspath(A.tex)
if A.params: A.params = os.path.abspath(A.params)
os.makedirs(A.out, exist_ok=True)
tex = A.tex or os.path.join(os.path.dirname(A.fbx), "Textures")
params = A.params or os.path.splitext(A.fbx)[0] + ".material_params.json"
info = {"args": vars(A), "fbx": A.fbx, "textures": tex, "params_file": params if os.path.exists(params) else None}

fit = fitbody()
drop_haircards()
arm = fit["armature"]
meshes = import_garment(A.fbx, arm)
info["garment_meshes"] = [o.name for o in meshes]
apply_pose(arm, ARMS_DOWN_V2 if A.pose == "down" else None)
info["pose"] = A.pose
bpy.context.view_layer.update()
info["hands_world"] = {s: list(arm.matrix_world @ arm.pose.bones["hand_" + s].head) for s in ("l", "r")}
info["materials"] = assign_shipped_materials(meshes, tex, params)
body_objs = [fit["body"], fit["head"], fit["hair_proxy"]]
for key in ("head_parts",):
    if fit.get(key): fit[key].hide_render = not A.body
for o in body_objs: o.hide_render = not A.body
arm.hide_render = True
ov = {k: getattr(A, k) for k in ("yaw", "pitch", "focal") if getattr(A, k) is not None}
v = dict(VIEWS[A.view])
if A.view == "photo":
    ov["res"] = (REF_W * A.mult, REF_H * A.mult)
cam, camrec = make_camera(A.view, meshes, ov)
info["camera"] = camrec
# landmarks to project (garment + body), read back from the scene
lm3 = {}
lo, hi = bbox_of(meshes); info["garment_bbox"] = [list(lo), list(hi)]
lm3["floor_origin"] = [0.0, 0.0, 0.0]; lm3["shoulder_line_clothed_r"] = [-0.18, 0.0, 1.56]; lm3["shoulder_line_clothed_l"] = [0.18, 0.0, 1.56]
try:
    L = json.load(open(os.path.join(SPEC_OUT, "male_landmarks.json")))
    for k in ("nose_tip", "subnasale", "stomion_mouth_line", "eye_l_centre", "eye_r_centre"):
        lm3[k] = L[k]
except Exception as e:
    info["landmarks_error"] = str(e)
for o in meshes:
    if "clasp" in o.name.lower():
        c, _ = evaluated_coords(o); lm3["clasp_centre_mesh_" + o.name] = list(c.mean(0))
# clasp by material slot (joined export): centroid of the vertices of the clasp slot
for o in meshes:
    for i, s in enumerate(o.material_slots):
        if s.material and any(k in s.material.name.lower() for k in A.clasp_keys.lower().split(",")):
            c, polys = evaluated_coords(o)
            idx = sorted({vi for p, poly in zip(o.data.polygons, polys) if p.material_index == i for vi in poly})
            if idx: lm3["clasp_centre"] = list(c[idx].mean(0))
info["landmarks_3d"] = lm3
info["landmarks_px"] = {k: v2 for k, v2 in zip(lm3.keys(), project(cam, lm3.values()))}
# is each face landmark hidden by the garment from this camera? (ray from the camera to a point 3 mm in front of it)
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
gtrees = [BVHTree.FromObject(o, dg) for o in meshes]
vis = {}
for k in ("nose_tip", "subnasale", "upper_lip", "stomion_mouth_line", "chin_point", "eye_l_centre", "eye_r_centre"):
    if k not in lm3 and k in ("upper_lip", "chin_point"):
        try: lm3[k] = json.load(open(os.path.join(SPEC_OUT, "male_landmarks.json")))[k]
        except Exception: continue
    if k not in lm3: continue
    tgt = Vector(lm3[k]) + Vector((0, -0.003, 0)); org = cam.location; d = tgt - org
    hidden = False
    for t, o in zip(gtrees, meshes):
        # BVH trees are in object space: move the ray into it
        Mi = o.matrix_world.inverted(); ol = Mi @ org; tl = Mi @ tgt; dl = tl - ol
        hit = t.ray_cast(ol, dl.normalized(), dl.length)
        if hit[0] is not None: hidden = True
    vis[k] = "hidden_by_garment" if hidden else "visible"
info["face_landmark_visibility"] = vis
info["resolution"] = [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y]

sc = bpy.context.scene
if not A.no_beauty:
    lights(camrec["yaw"])
    info["device"] = cycles_setup(A.samples)
    chest = Vector((0.0, -0.25, 1.30)) if A.view != "hem" else Vector((0.0, -0.3, 0.15))
    info["calibration"] = calibrate_white(cam, chest, A.out)
    sc.render.filepath = os.path.join(A.out, A.tag + ".png"); bpy.ops.render.render(write_still=True)
# garment-only alpha (Workbench, garment black)
for o in body_objs + [fit.get("head_parts")]:
    if o: o.hide_render = True
ids = []
workbench_id_render(os.path.join(A.out, A.tag + "_alpha.png"), meshes, [])
if A.body:
    ids = region_colour_body(fit)
    workbench_id_render(os.path.join(A.out, A.tag + "_id.png"), meshes, ids)
json.dump(info, open(os.path.join(A.out, A.tag + ".json"), "w"), indent=1, default=str)
log("RENDER_DONE", A.tag, json.dumps({"cal": info.get("calibration"), "cam": camrec.get("cam_loc")}, default=str))
