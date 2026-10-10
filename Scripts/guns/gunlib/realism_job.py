"""Realism review shots of a built gun blend in the ROUGH LOOK (headless Blender, Cycles): perspective cameras placed
by eye / target / field of view in the gun's frame M (mm), e.g. the first-person crop, the ADS sight picture, the
third-person distance view and a hero 3/4. Review only: nothing here is exported.

    blender -b <gun.blend> --factory-startup --python Scripts/guns/gunlib/realism_job.py -- --job <job.json>

job.json:
  {"offset_M": [x, y, z],              frame B = (M - offset) / 1000
   "samples": 128, "wood_slots": [...], "worn_steel_objects": [...], "env": 0.55, "light": 1.35,
   "bg_rgb": [126, 126, 126],           world / background colour (sRGB; rendered opaque)
   "polymer_slots": [...], "steel_style": "phosphate"   (0.2.1) black polymer on those slots, phosphate on the rest
   "poses": {object: 4x4}, "hide": [object, ...]        (0.2.1) rigid review poses (frame B, metres) / hidden objects
   "shots": [{"name": ..., "eye_M": [x, y, z], "target_M": [x, y, z], "fov_deg": 55.0, "res": [w, h],
              "light_dist_m": 1.1, "out": "<png>"}]}
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from gunlib import look as LK  # noqa: E402
from gunlib import render as RD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
JOB = json.loads(Path(argv[argv.index("--job") + 1]).read_text())
sc = bpy.context.scene
OFF = np.array(JOB["offset_M"], float)


def B(p):
    return Vector(((np.asarray(p, float) - OFF) / 1000.0).tolist())


def is_wood(ob):
    try:
        rec = json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        rec = {}
    return rec.get("slot") in set(JOB.get("wood_slots", []))


def main():
    RD.engine(sc, "CYCLES", int(JOB.get("samples", 128)))
    sc.render.resolution_percentage = 100
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
    LK.apply_rough_look(objs, is_wood, JOB.get("worn_steel_objects", []))
    if JOB.get("polymer_slots") or JOB.get("steel_style") == "phosphate":     # gunlib 0.2.1 (SMG): polymer + phosphate
        poly = LK.rough_polymer()
        phos = LK.rough_steel("RL_Phosphate", LK.PHOS_BASE, LK.PHOS_EDGE, metallic=0.55, rough_add=0.12)             if JOB.get("steel_style") == "phosphate" else None
        for ob in objs:
            try:
                slot = json.loads(ob.get("gun_part", "{}")).get("slot")
            except Exception:  # noqa: BLE001
                slot = None
            if slot in set(JOB.get("polymer_slots", [])):
                ob.data.materials.clear()
                ob.data.materials.append(poly)
            elif phos is not None and not is_wood(ob):
                ob.data.materials.clear()
                ob.data.materials.append(phos)
    for nm, pose in JOB.get("poses", {}).items():               # optional rigid poses: {object: 4x4 frame-B metres}
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            from mathutils import Matrix
            ob.matrix_world = Matrix(pose) @ ob.matrix_world
    for nm in JOB.get("hide", []):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            ob.hide_render = True
    cam = RD.camera_object("RL_RealismCam")
    for shot in JOB["shots"]:
        LK.rough_world(sc, tuple(JOB.get("bg_rgb", (126, 126, 126))), float(JOB.get("env", 0.55)))
        sc.render.film_transparent = False
        eye, tgt = B(shot["eye_M"]), B(shot["target_M"])
        cam.location = eye
        up = Vector(shot.get("up_M", (0.0, 0.0, 1.0)))
        cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
        if abs((tgt - eye).normalized().dot(up)) > 0.999:
            cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "X").to_euler()
        cam.data.type = "PERSP"
        cam.data.sensor_fit = "HORIZONTAL"
        cam.data.angle = math.radians(float(shot["fov_deg"]))
        cam.data.clip_start = 0.01
        cam.data.clip_end = 50.0
        cam.data.shift_x = cam.data.shift_y = 0.0
        w, h = shot.get("res", [1600, 900])
        sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
        bpy.context.view_layer.update()
        LK.rough_lights(cam, tuple(tgt), float(shot.get("light_dist_m", 1.1)), float(JOB.get("light", 1.0)))
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.filepath = str(shot["out"])
        Path(shot["out"]).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.render.render(write_still=True)
        print("[gunlib] REALISM RENDERED", shot["name"])
    print("[gunlib] REALISM_JOB_DONE", len(JOB["shots"]))


main()
