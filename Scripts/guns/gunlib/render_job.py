"""Render a list of review shots of a built gun blend in the ROUGH LOOK (headless Blender, Cycles):

    blender -b <gun.blend> --factory-startup --python Scripts/guns/gunlib/render_job.py -- --job <job.json>

job.json (written by gunlib/detail.py):
  {"offset_M": [x, y, z],              frame B = (M - offset) / 1000
   "ss": 3, "samples": 96,
   "wood_slots": ["M_AR01_Furniture"],  objects whose gun_part slot is listed get RL_Wood, the rest RL_Steel
   "worn_steel_objects": [...],         optional: objects in the lighter worn steel (RL_SteelWorn)
   "env": 0.45, "light": 1.0,
   "poses": [{"objects": [...], "pivot_M": [x, y, z], "axis_M": [ax, ay, az], "deg": d}]   optional: moving parts posed
            (a hinge rotation about the pivot) before every shot, e.g. a lever in the detent the reference draws,
   "shots": [{"name": ..., "camera": <closeup camera JSON>, "show": [object names] | null, "out": "<png>",
              "poses": [...] (optional, this shot only),
              "bg_rgb": [r, g, b], "target_M": [x, y, z]}]}
Each shot is rendered with a transparent film at panel size x ss (RGBA PNG); detail.py composites it onto the panel's
fitted backdrop and crops it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from gunlib import look as LK  # noqa: E402
from gunlib import render as RD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
JOB = json.loads(Path(argv[argv.index("--job") + 1]).read_text())
sc = bpy.context.scene
OFF = np.array(JOB["offset_M"], float)
SS = int(JOB.get("ss", 3))


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]


def is_wood(ob):
    try:
        rec = json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        rec = {}
    return rec.get("slot") in set(JOB.get("wood_slots", []))


def cam_ortho(cam, d):
    Rm = np.array(d["R_rows_right_up_fwd_M"], float)
    c = np.array(d["image_centre_point_M"], float)
    W, H = d["panel_px"]
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = Rm[0], Rm[1], -Rm[2]
    M[:3, 3] = (c - Rm[2] * 1500.0 - OFF) / 1000.0
    cam.matrix_world = Matrix(M.tolist())
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = d["ortho_width_mm"] / 1000.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.05
    cam.data.clip_end = 6.0
    sc.render.resolution_x, sc.render.resolution_y = W * SS, H * SS


def cam_persp(cam, d):
    W, H = d["panel_px"]
    RD.persp_from_solve(cam, sc, d, OFF, (H, W), SS)


def apply_poses(poses):
    from mathutils import Matrix as Mx, Vector as Vc
    for pz in poses:
        p = Vc(((np.array(pz["pivot_M"], float) - OFF) / 1000.0).tolist())
        R = Mx.Rotation(np.radians(float(pz["deg"])), 4, Vc(pz["axis_M"]).normalized())
        M = Mx.Translation(p) @ R @ Mx.Translation(-p)
        for n in pz["objects"]:
            ob = bpy.data.objects.get(n)
            if ob is not None:
                ob.matrix_world = M @ ob.matrix_world
                print("[gunlib] posed", n, pz["deg"])


def main():
    RD.engine(sc, "CYCLES", int(JOB.get("samples", 96)))
    sc.render.resolution_percentage = 100
    objs = meshes()
    rest = {o.name: o.matrix_world.copy() for o in objs}
    LK.apply_rough_look(objs, is_wood, JOB.get("worn_steel_objects", []))
    cam = RD.camera_object("RL_Cam")
    for shot in JOB["shots"]:
        LK.rough_world(sc, tuple(shot.get("bg_rgb", (126, 126, 126))), float(JOB.get("env", 0.45)))
        for o in objs:                                   # rest pose, then the job's and the shot's poses
            o.matrix_world = rest[o.name]
        apply_poses(list(JOB.get("poses", [])) + list(shot.get("poses", [])))
        show = shot.get("show")
        for o in objs:
            o.hide_render = bool(show) and o.name not in show
        d = shot["camera"]
        (cam_ortho if d["type"] == "ORTHO" else cam_persp)(cam, d)
        tgt = (np.array(shot["target_M"], float) - OFF) / 1000.0
        LK.rough_lights(cam, tuple(tgt), 1.1, float(JOB.get("light", 1.0)))
        sc.render.film_transparent = True
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.filepath = str(shot["out"])
        Path(shot["out"]).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.render.render(write_still=True)
        print("[gunlib] RENDERED", shot["name"])
    print("[gunlib] RENDER_JOB_DONE", len(JOB["shots"]))


main()
