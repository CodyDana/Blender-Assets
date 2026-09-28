"""PlayerBase conform input - step 3: measure the rest pose of the COPY and render
quick workbench views for a visual check. Read-only (never saves).

    blender -b WorkFiles/MetaHuman/player_base/src_Human_copy.blend --factory-startup \
        --python Scripts/MetaHuman/pb_measure_pose.py -- <out_dir>
"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import lock
lock.assert_owner("JinMuWon_v2", "claude")

import json
import math
import os

import bpy
from mathutils import Vector

COPY_DIR = os.path.normcase(os.path.abspath(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base"))
if os.path.normcase(os.path.dirname(os.path.abspath(bpy.data.filepath))) != COPY_DIR:
    raise SystemExit(f"Refusing to run on {bpy.data.filepath}: only the player_base copy is allowed")

out_dir = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out_dir, exist_ok=True)

BODY = "SK_JinMuWon_Human_Body"
arm_obj = bpy.data.objects["Armature"]
arm_obj.data.pose_position = "REST"
bpy.context.view_layer.update()
body = bpy.data.objects[BODY]
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
me = ev.to_mesh()
mw = ev.matrix_world.copy()
V = [mw @ v.co for v in me.vertices]


def bone(n):
    b = arm_obj.data.bones[n]
    return arm_obj.matrix_world @ b.head_local, arm_obj.matrix_world @ b.tail_local


def deg(v):
    return round(math.degrees(v), 2)


res = {}
zs = [v.z for v in V]
res["height_m"] = max(zs) - min(zs)
res["min_z_m"] = min(zs)
res["max_z_m"] = max(zs)
res["bounds_min_m"] = [min(v[i] for v in V) for i in range(3)]
res["bounds_max_m"] = [max(v[i] for v in V) for i in range(3)]

for side in ("L", "R"):
    sh, _ = bone(f"upperarm01.{side}")
    el, _ = bone(f"lowerarm01.{side}")
    wr, wr_t = bone(f"wrist.{side}")
    ua = el - sh
    fa = wr - el
    # frontal-plane angle below horizontal (ignore Y)
    ua_front = math.atan2(-ua.z, abs(ua.x))
    whole = wr - sh
    whole_front = math.atan2(-whole.z, abs(whole.x))
    # 3D angle of the upper arm below the horizontal plane
    ua_3d = math.asin(-ua.z / ua.length)
    # forward (−Y) swing of the upper arm
    ua_fwd = math.atan2(-ua.y, math.hypot(ua.x, ua.z))
    elbow = ua.angle(fa)
    res[f"arm_{side}"] = {
        "shoulder_joint": list(sh), "elbow_joint": list(el), "wrist_joint": list(wr),
        "upperarm_below_horizontal_frontal_deg": deg(ua_front),
        "upperarm_below_horizontal_3d_deg": deg(ua_3d),
        "upperarm_forward_swing_deg": deg(ua_fwd),
        "shoulder_to_wrist_below_horizontal_frontal_deg": deg(whole_front),
        "elbow_flexion_deg": deg(elbow),
        "forearm_dir": list(fa.normalized()),
    }
    hand_verts = [v for v in V if (v.x > 0.45 if side == "L" else v.x < -0.45)]
    if hand_verts:
        res[f"arm_{side}"]["hand_region_bounds_m"] = [[min(v[i] for v in hand_verts) for i in range(3)],
                                                      [max(v[i] for v in hand_verts) for i in range(3)]]

for side in ("L", "R"):
    fh, ft = bone(f"foot.{side}")
    th, tt = bone(f"toe1-1.{side}")
    ah, _ = bone(f"lowerleg02.{side}")
    fv = tt - fh
    res[f"foot_{side}"] = {"ankle": list(fh), "toe_tip": list(tt),
                           "foot_yaw_from_minusY_deg": deg(math.atan2(fv.x, -fv.y)),
                           "sole_min_z_m": min(v.z for v in V if (v.x > 0.05 if side == "L" else v.x < -0.05) and v.z < 0.15)}
res["feet_ankle_spacing_m"] = (Vector(res["foot_L"]["ankle"]) - Vector(res["foot_R"]["ankle"])).length
hipL, _ = bone("upperleg01.L")
ankL, _ = bone("foot.L")
lg = ankL - hipL
res["leg_L_abduction_deg"] = deg(math.atan2(lg.x, -lg.z))

# facing axis: eyes/nose relative to head centre
eyeL, eyeL_t = bone("eye.L")
headh, headt = bone("head")
res["eye_bone_dir"] = list((eyeL_t - eyeL).normalized())
nose = min((v for v in V if v.z > 1.70 and v.z < 1.76 and abs(v.x) < 0.02), key=lambda v: v.y)
res["nose_tip_m"] = list(nose)
res["facing_axis_blender"] = "-Y" if nose.y < headh.y else "+Y"

# lip gap at the midline: vertices near x=0 in the mouth band, front-most surface
mouth = [v for v in V if abs(v.x) < 0.004 and 1.64 < v.z < 1.71 and v.y < -0.10]
mouth.sort(key=lambda v: v.z)
res["midline_mouth_profile"] = [[round(v.y, 4), round(v.z, 4)] for v in mouth]

ev.to_mesh_clear()
with open(os.path.join(out_dir, "pbexp_pose_measure.json"), "w") as fh:
    json.dump(res, fh, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "midline_mouth_profile"}, indent=1))

# ---- quick workbench renders (body only) ----
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.name != BODY
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = 900
scene.render.resolution_y = 1200
scene.render.film_transparent = False
scene.world = scene.world or bpy.data.worlds.new("W")
cam_data = bpy.data.cameras.new("pbexp_cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("pbexp_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, loc, rot, ortho, rx=900, ry=1200):
    cam.location = loc
    cam.rotation_euler = rot
    cam_data.ortho_scale = ortho
    scene.render.resolution_x = rx
    scene.render.resolution_y = ry
    scene.render.filepath = os.path.join(out_dir, name)
    bpy.ops.render.render(write_still=True)


r90 = math.radians(90)
shoot("pbexp_rest_front.png", (0, -5, 0.95), (r90, 0, 0), 2.1)
shoot("pbexp_rest_side.png", (5, 0, 0.95), (r90, 0, r90), 2.1)
shoot("pbexp_rest_top.png", (0, 0, 5), (0, 0, 0), 1.6, 1200, 900)
shoot("pbexp_face_front.png", (0, -3, 1.72), (r90, 0, 0), 0.30, 900, 900)
shoot("pbexp_face_side.png", (3, -0.08, 1.72), (r90, 0, r90), 0.30, 900, 900)
print("RENDERS DONE")
