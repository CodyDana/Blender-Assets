"""AR-01 stages 5-6 look check from the EXPORTED bytes (fresh Blender process, Workbench):

    blender -b --factory-startup --python Scripts/guns/rifle/rifle_rig_render.py

SK_AR01.fbx + the A_AR01_ReloadEmpty / A_AR01_Fire clips re-imported, SM_AR01_Mag.fbx (LOD0) carried on the
'magazine' bone at the Mag socket (zero relative transform), rendered from the gun's right side at the reload's key
frames (seated, rocked out about the hook, at MagInsertStart, dropping), the bolt at its rear stop (charge) and mid
fire cycle, plus one 3/4-below view of the empty well. Frames go to WorkFiles/guns/rifle/review/rig/ (the contact
sheet is made by rifle_mag_sheets.py).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, REVIEW  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "AR01"
OUT = REVIEW / "rig"
OUT.mkdir(parents=True, exist_ok=True)


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def import_fbx(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(p), use_custom_normals=True, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


def main():
    clear()
    sk = import_fbx(EXP / "SK_AR01.fbx")
    arm = next(o for o in sk if o.type == "ARMATURE")
    acts = {}
    for c in ("A_AR01_ReloadEmpty", "A_AR01_Fire"):
        objs = import_fbx(EXP / f"{c}.fbx")
        a2 = next(o for o in objs if o.type == "ARMATURE")
        act = a2.animation_data.action
        act.name = c
        act.use_fake_user = True
        acts[c] = act
        slot = a2.animation_data.action_slot if hasattr(a2.animation_data, "action_slot") else None
        acts[c + "_slot"] = slot
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    mag = [o for o in import_fbx(EXP / "SM_AR01_Mag.fbx") if o.type == "MESH" or o.type == "EMPTY"]
    for o in mag:
        if o.type == "MESH" and not o.name.startswith("SM_AR01_Mag_LOD0"):
            o.hide_render = True
        if o.name.startswith("UCX_"):
            o.hide_render = True
    mag0 = next(o for o in mag if o.name.startswith("SM_AR01_Mag_LOD0"))
    mag0.parent = None
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"

    def look(eye, target, scale):
        cam.location = Vector(eye)
        d = Vector(target) - Vector(eye)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = scale

    def place_mag():
        pb = arm.pose.bones["magazine"]
        M = arm.matrix_world @ pb.matrix
        loc, rot, _s = M.decompose()
        mag0.matrix_world = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()

    shots = [("reload_f00_seated", "A_AR01_ReloadEmpty", 0), ("reload_f09_rocked18", "A_AR01_ReloadEmpty", 9),
             ("reload_f12_insertstart", "A_AR01_ReloadEmpty", 12), ("reload_f16_dropping", "A_AR01_ReloadEmpty", 16),
             ("reload_f74_bolt_rear", "A_AR01_ReloadEmpty", 74), ("fire_f03_bolt_rear", "A_AR01_Fire", 3)]
    if arm.animation_data is None:
        arm.animation_data_create()
    written = []
    for name, cname, f in shots:
        arm.animation_data.action = acts[cname]
        try:
            if acts.get(cname + "_slot") is not None:
                arm.animation_data.action_slot = acts[cname].slots[0]
        except Exception:  # noqa: BLE001
            pass
        off = int(round(acts[cname].frame_range[0]))          # the importer starts takes at frame 1
        sc.frame_set(f + off)
        bpy.context.view_layer.update()
        place_mag()
        # right side (Blender front view from -Y), around the receiver and magazine (frame B, metres)
        look((0.16, -0.9, 0.03), (0.16, 0.0, 0.03), 0.42)
        p = OUT / f"{name}.png"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        written.append(str(p))
    # the empty well from below-front-right with the magazine dropped away
    arm.animation_data.action = acts["A_AR01_ReloadEmpty"]
    sc.frame_set(25 + int(round(acts["A_AR01_ReloadEmpty"].frame_range[0])))
    place_mag()
    look((0.33, -0.35, -0.25), (0.16, 0.0, 0.055), 0.22)
    cam.data.type = "PERSP"
    cam.data.lens = 50
    p = OUT / "well_empty_below.png"
    sc.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    written.append(str(p))
    (OUT / "frames.json").write_text(json.dumps(written, indent=1))
    print("[AR01-rr] DONE", len(written))


main()
