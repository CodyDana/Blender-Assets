"""Finalise: rest-pose component-space points (Unreal cm) for CR_HeelPose v2's toe contact (Blender headless, read only).

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/fin_cr_toe_points.py

* barefoot_toe_cs_cm: her lowest, most forward toe skin at rest (the barefoot toe tip on the floor)
* shoe_toe_cs_cm: the shoe vertex that is lowest within 12 mm of the toe tip when the heel pose is applied (the shoe's toe
  underside); its REST position is written, so ue_hc_build_cr.py can make it ball-local with the rig's initial pose
Writes WorkFiles/SnowFlowerHeels/final/cr_toe_points.json. Saves nothing.
"""
import json
import sys

import bpy
import numpy as np

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from SnowFlowerHeels.heel_pose import apply_heel_pose, clear_heel_pose, load_pose  # noqa: E402

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/final/cr_toe_points.json"
pose = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/heel_pose.json", encoding="utf-8"))
arm = bpy.data.objects["root"]
body = bpy.data.objects["FIT_MH_PlayerFemale_Body"]
shoe = bpy.data.objects["SK_SnowFlowerHeels"]


def ue(p):
    return [float(p[0] * 100.0), float(-p[1] * 100.0), float(p[2] * 100.0)]


def world(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([tuple(ob.matrix_world @ v.co) for v in me.vertices])
    ev.to_mesh_clear()
    return co


clear_heel_pose(arm)
bpy.context.view_layer.update()
body_rest = world(body)
shoe_rest = world(shoe)
feet, params = load_pose()
apply_heel_pose(arm, feet, params)
bpy.context.view_layer.update()
shoe_posed = world(shoe)
clear_heel_pose(arm)
out = {}
for s, sgn in (("l", 1.0), ("r", -1.0)):
    fwd = np.array(pose["solve"]["per_foot"][s]["forward_axis"], dtype=float)
    fwd[2] = 0.0
    fwd /= np.linalg.norm(fwd)
    b = body_rest[(body_rest[:, 0] * sgn > 0.02) & (body_rest[:, 2] < 0.05)]
    low = b[b[:, 2] < b[:, 2].min() + 0.004]
    toe = low[np.argmax(low @ fwd)]
    sh = np.nonzero(shoe_posed[:, 0] * sgn > 0.02)[0]
    proj = shoe_posed[sh] @ fwd
    front = sh[proj > proj.max() - 0.012]
    k = front[np.argmin(shoe_posed[front, 2])]
    kt = sh[np.argmax(proj)]
    out[s] = {"barefoot_toe_cs_cm": ue(toe), "barefoot_toe_rest_z_mm": float(toe[2] * 1000),
              "shoe_toe_cs_cm": ue(shoe_rest[k]), "shoe_toe_vertex": int(k),
              "shoe_tiptip_cs_cm": ue(shoe_rest[kt]), "shoe_tiptip_vertex": int(kt),
              "shoe_tiptip_posed_z_mm": float(shoe_posed[kt, 2] * 1000),
              "shoe_toe_posed_z_mm": float(shoe_posed[k, 2] * 1000),
              "shoe_toe_posed_forward_of_ball_mm": float((shoe_posed[k] @ fwd - shoe_posed[sh].min(0) @ fwd) * 1000)}
json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
print("TOE_POINTS", json.dumps(out))
