"""SMG01 W3 look check from the EXPORTED bytes (fresh Blender process, Workbench; the AR-01's rifle_rig_render.py):

    blender -b --factory-startup --python Scripts/guns/smg/smg_rig_render.py

SK_SMG01.fbx + clips re-imported (ReloadEmpty, Fire, StockFold, SightFlip, Selector), SM_SMG01_Mag.fbx (LOD0)
carried on the 'magazine' bone at the Mag socket (zero relative transform), rendered from the gun's right side at the
reload's key frames (seated, the paddle pressed, at MagInsertStart, dropping, re-seated), the bolt held open and at its
rear stop, the stock mid-fold and folded (from above), the sights folded, the selector at SAFE / AUTO (left side),
plus the empty well from below. Frames + a contact sheet go to WorkFiles/guns/smg/review/rig/.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, REVIEW  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SMG01"
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
    sk = import_fbx(EXP / "SK_SMG01.fbx")
    arm = next(o for o in sk if o.type == "ARMATURE")
    acts = {}
    for c in ("A_SMG01_ReloadEmpty", "A_SMG01_Fire", "A_SMG01_StockFold", "A_SMG01_SightFlip", "A_SMG01_Selector"):
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
    mag = [o for o in import_fbx(EXP / "SM_SMG01_Mag.fbx") if o.type == "MESH" or o.type == "EMPTY"]
    for o in mag:
        if o.type == "MESH" and not o.name.startswith("SM_SMG01_Mag_LOD0"):
            o.hide_render = True
        if o.name.startswith("UCX_"):
            o.hide_render = True
    mag0 = next(o for o in mag if o.name.startswith("SM_SMG01_Mag_LOD0"))
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

    R = (0.12, -0.9, 0.06)
    shots = [("reload_f00_seated_bolt_open", "A_SMG01_ReloadEmpty", 0, R, (0.12, 0, 0.06), 0.46),
             ("reload_f03_paddle_pressed", "A_SMG01_ReloadEmpty", 3, R, (0.12, 0, 0.06), 0.46),
             ("reload_f09_insertstart", "A_SMG01_ReloadEmpty", 9, R, (0.12, 0, 0.0), 0.5),
             ("reload_f14_dropping", "A_SMG01_ReloadEmpty", 14, R, (0.12, 0, -0.05), 0.6),
             ("reload_f46_camming_in", "A_SMG01_ReloadEmpty", 46, R, (0.12, 0, 0.0), 0.5),
             ("reload_f67_handle_rear", "A_SMG01_ReloadEmpty", 67, R, (0.12, 0, 0.06), 0.46),
             ("fire_f03_bolt_rear", "A_SMG01_Fire", 3, R, (0.12, 0, 0.06), 0.46),
             ("stock_f12_midfold_top", "A_SMG01_StockFold", 12, (0.0, -0.05, 0.9), (0.0, -0.05, 0.0), 0.75),
             ("stock_f24_folded_top", "A_SMG01_StockFold", 24, (0.1, -0.05, 0.9), (0.1, -0.05, 0.0), 0.55),
             ("stock_f24_folded_right", "A_SMG01_StockFold", 24, (0.1, -0.9, 0.05), (0.1, 0, 0.05), 0.5),
             ("sights_f10_folded", "A_SMG01_SightFlip", 10, R, (0.12, 0, 0.12), 0.4),
             ("selector_f07_safe_left", "A_SMG01_Selector", 7, (0.03, 0.9, 0.05), (0.03, 0, 0.05), 0.2),
             ("selector_f23_auto_left", "A_SMG01_Selector", 23, (0.03, 0.9, 0.05), (0.03, 0, 0.05), 0.2)]
    if arm.animation_data is None:
        arm.animation_data_create()
    written = []
    for name, cname, f, eye, tgt, scale in shots:
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
        look(eye, tgt, scale)
        p = OUT / f"{name}.png"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        written.append(str(p))
    arm.animation_data.action = acts["A_SMG01_ReloadEmpty"]
    sc.frame_set(25 + int(round(acts["A_SMG01_ReloadEmpty"].frame_range[0])))
    place_mag()
    look((0.33, -0.35, -0.2), (0.13, 0.0, 0.03), 0.22)
    cam.data.type = "PERSP"
    cam.data.lens = 50
    p = OUT / "well_empty_below.png"
    sc.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    written.append(str(p))
    try:
        from PIL import Image, ImageDraw
        ims = [Image.open(x).convert("RGB").resize((560, 400)) for x in written]
        cols = 4
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 560, rows * 420), (255, 255, 255))
        for i, (im, x) in enumerate(zip(ims, written)):
            r_, c_ = divmod(i, cols)
            sheet.paste(im, (c_ * 560, r_ * 420 + 20))
            ImageDraw.Draw(sheet).text((c_ * 560 + 6, r_ * 420 + 4), Path(x).stem, fill=(0, 0, 0))
        sheet.save(OUT / "rig_contact_sheet.png")
    except Exception as e:  # noqa: BLE001
        print("[SMG01-rr] contact sheet skipped", e)
    (OUT / "frames.json").write_text(json.dumps(written, indent=1))
    print("[SMG01-rr] DONE", len(written))


main()
