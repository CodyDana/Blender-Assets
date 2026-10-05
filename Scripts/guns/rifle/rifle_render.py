"""AR-01 renders (headless Blender, run on a built blend):

    blender -b <blend> --factory-startup --python Scripts/guns/rifle/rifle_render.py -- --set preview|grey|crops [--out DIR]

preview  Workbench grey: side (panel-matched), top, 3/4 (solved camera), close views  -> scratch/preview/
grey     Cycles, neutral grey material, flat grey backdrop: side / top / 3/4 at 3x the panel resolution
         -> Renders/Guns/AR01/form_{side,top,q34}.png
crops    studio look like the sheet (grey backdrop, soft light, dark steel + reddish wood placeholders) with the
         cameras solved for close-ups c1 (receiver right) and c3 (front sight + muzzle)  -> review/early/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, TRACE, RENDERS, REVIEW  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from gunlib import render as RD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "preview")
OUT = Path(arg("--out", str(SCRATCH / "preview"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SS = int(arg("--ss", "3"))
sc = bpy.context.scene


def trace_frame(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    b = j["panel_box_sheet_px"]
    return j["px_per_mm"], j["bore_dir_px"], j["origin_px"], (b[3] - b[1] + 1, b[2] - b[0] + 1)


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]


def setup_grey():
    m = RD.principled("Grey", RD.srgb_to_lin((150, 150, 150)), 0.0, 0.55)
    RD.assign(meshes(), m)


def setup_studio():
    steel = RD.principled("Steel", RD.srgb_to_lin((53, 53, 53)), 0.0, 0.48)       # black lacquer #353535
    wood = RD.principled("Wood", RD.srgb_to_lin((107, 60, 39)), 0.0, 0.5)          # walnut shellac #6B3C27
    blue = RD.principled("Blued", RD.srgb_to_lin((120, 120, 120)), 1.0, 0.38)     # bluing #787878
    for o in meshes():
        rec = json.loads(o.get("gun_part", "{}")) if "gun_part" in o else {}
        slot = rec.get("slot", "M_AR01_Metal")
        o.data.materials.clear()
        if slot == "M_AR01_Furniture":
            o.data.materials.append(wood)
        elif rec.get("bone", "body") != "body":
            o.data.materials.append(blue)
        else:
            o.data.materials.append(steel)


def lights_studio(scale=1.0):
    RD.area_light("Key", (0.6, -0.9, 1.0), (0.15, 0, 0), 1.2, 600 * scale)
    RD.area_light("Fill", (-0.6, -1.2, 0.2), (0.15, 0, 0), 1.5, 180 * scale)
    RD.area_light("Rim", (0.2, 1.0, 0.8), (0.15, 0, 0), 1.0, 220 * scale)


def views_panel(prefix, transparent=False):
    cam = RD.camera_object()
    s, u, p0, shape = trace_frame("LEFT")
    RD.ortho_side(cam, sc, s, u, p0, shape, GRIP, SS)
    RD.still(sc, OUT / f"{prefix}side.png", transparent)
    s, u, p0, shape = trace_frame("TOP")
    RD.ortho_top(cam, sc, s, u, p0, shape, GRIP, SS)
    RD.still(sc, OUT / f"{prefix}top.png", transparent)
    camf = SCRATCH / "q34" / "camera.json"
    if camf.exists():
        RD.persp_from_solve(cam, sc, json.loads(camf.read_text()), GRIP, (279, 758), SS)
        RD.still(sc, OUT / f"{prefix}q34.png", transparent)
    return cam


def look_cam(cam, loc_M, target_M, lens=50.0, res=(1600, 1000)):
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.data.shift_x = cam.data.shift_y = 0.0
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = (np.array(loc_M) - GRIP) / 1000.0
    d = Vector((np.array(target_M) - np.array(loc_M)) / 1000.0)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def closeups(cam, prefix):
    shots = {
        "rec_r34": ((560, -420, 150), (360, 0, -5), 55),
        "rec_side": ((360, -520, 0), (360, 0, 0), 55),
        "front_r34": ((990, -260, 110), (780, 0, 5), 60),
        "rear_r34": ((110, -330, 90), (240, 0, -30), 50),
        "under": ((380, -250, -330), (360, 0, -40), 50),
        "top_rec": ((370, -60, 450), (370, 0, 10), 50),
        "left_rec": ((380, 520, 20), (380, 0, 0), 55),
    }
    for k, (loc, tgt, lens) in shots.items():
        look_cam(cam, loc, tgt, lens)
        RD.still(sc, OUT / f"{prefix}{k}.png")


def ortho_from_json(cam, camd, ss=3):
    """Orthographic camera from rifle_closeups.py (rows right/up/fwd in frame M, image-centre point, width mm)."""
    Rm = np.array(camd["R_rows_right_up_fwd_M"], float)
    c = np.array(camd["image_centre_point_M"], float)
    W, H = camd["panel_px"]
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = Rm[0], Rm[1], -Rm[2]
    M[:3, 3] = (c - Rm[2] * 800.0 - GRIP) / 1000.0
    from mathutils import Matrix
    cam.matrix_world = Matrix(M.tolist())
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = camd["ortho_width_mm"] / 1000.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.05
    cam.data.clip_end = 5.0
    sc.render.resolution_x, sc.render.resolution_y = W * ss, H * ss


def studio_lights():
    """Soft studio like the sheet: large key from the upper left-front, fill, rim; grey backdrop (world)."""
    k = float(arg("--light", "1.0"))
    RD.area_light("Key", (0.35, -0.9, 0.75), (0.25, 0, -0.02), 1.6, 34 * k)
    RD.area_light("Fill", (0.9, -0.8, -0.2), (0.3, 0, 0.0), 2.0, 10 * k)
    RD.area_light("Top", (0.3, 0.1, 1.2), (0.3, 0, 0.0), 2.0, 16 * k)
    RD.area_light("Rim", (0.2, 0.9, 0.5), (0.3, 0, 0.0), 1.2, 10 * k)


def main():
    if SET == "preview":
        RD.engine(sc, "WORKBENCH")
        sc.display.shading.light = "STUDIO"
        sc.display.shading.show_cavity = True
        sc.display.shading.cavity_type = "WORLD"
        setup_grey()
        cam = views_panel("pv_")
        closeups(cam, "pv_")
    elif SET == "grey":
        RD.engine(sc, "CYCLES", int(arg("--samples", "64")))
        RD.world_flat(sc, RD.srgb_to_lin((128, 128, 128)), 1.0, env=0.4)
        setup_grey()
        studio_lights()
        global OUT
        cam = views_panel("form_grey_")
        closeups(cam, "form_grey_")
    elif SET == "crops":
        RD.engine(sc, "CYCLES", int(arg("--samples", "128")))
        RD.world_flat(sc, RD.srgb_to_lin((123, 123, 123)), 1.0, env=float(arg("--env", "0.35")))
        setup_studio()
        studio_lights()
        cam = RD.camera_object()
        for k, nm in (("c1", "receiver"), ("c3", "frontsight")):
            camd = json.loads((SCRATCH / "q34" / f"camera_{k}.json").read_text())
            ortho_from_json(cam, camd, SS)
            RD.still(sc, OUT / f"ours_{nm}.png")
    print("[AR01] RENDER_DONE", SET)


main()
