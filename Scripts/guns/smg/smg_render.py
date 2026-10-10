"""SMG01 grey renders (headless Blender, Cycles) on the built blend, matched to the sheet panels:

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_render.py -- [--ss 3]
            [--samples 64] [--out Renders/Guns/SMG01]

form_grey_left.png   orthographic from +Y, the LEFT panel's px <-> mm map (muzzle to screen left)
form_grey_right.png  orthographic from -Y, the RIGHT panel as drawn (muzzle to screen right)
form_grey_top.png    orthographic from +Z, the TOP panel's map (muzzle left, gun left image-down)
form_grey_q34.png    the solved 3/4 FRONT (LEFT) camera (scratch/q34/camera_form.json, else camera_blockout.json)
form_grey_folded_right.png  the stock folded, from -Y (the same framing as the right view)
then (plain Python, after the renders) the render-vs-sheet blends are written by smg_gates / smg_overlays.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import GRIP, SCRATCH, RENDERS, REVIEW, PanelMap, trace, dims  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from gunlib import render as RD  # noqa: E402
from gunlib import fit as F  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


OUT = Path(arg("--out", str(RENDERS))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SS = int(arg("--ss", "3"))
sc = bpy.context.scene


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]


def panel_cam(cam, view, look, up):
    j = trace(view)
    b = j["panel_box_sheet_px"]
    W, H = b[2] - b[0] + 1, b[3] - b[1] + 1
    PM = PanelMap(view)
    c = PM.mm([[W / 2.0 - 0.5, H / 2.0 - 0.5]], raw=True)[0]
    if view == "TOP":
        cM = np.array([c[0], c[1], 0.0])
    else:
        cM = np.array([c[0], 0.0, c[1]])
    look = Vector(look).normalized()
    cam.location = Vector(((cM - GRIP) / 1000.0).tolist()) - look * 2.0
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    q = look.to_track_quat("-Z", "Y")
    upv = q @ Vector((0, 1, 0))
    if upv.dot(Vector(up)) < 0.99:                      # roll so the image-up is `up`
        ang = math.atan2(look.dot(upv.cross(Vector(up))), upv.dot(Vector(up)))
        cam.rotation_euler = (Matrix.Rotation(ang, 4, look) @ q.to_matrix().to_4x4()).to_euler()
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = W / PM.s / 1000.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.1
    cam.data.clip_end = 10.0
    sc.render.resolution_x, sc.render.resolution_y = W * SS, H * SS


def studio_lights():
    k = float(arg("--light", "0.5"))
    RD.area_light("Key", (0.35, 0.9, 0.75), (0.25, 0, -0.02), 1.6, 34 * k)
    RD.area_light("Fill", (0.9, -0.8, -0.2), (0.3, 0, 0.0), 2.0, 10 * k)
    RD.area_light("Top", (0.3, 0.1, 1.2), (0.3, 0, 0.0), 2.0, 16 * k)
    RD.area_light("Rim", (0.2, -0.9, 0.5), (0.3, 0, 0.0), 1.2, 10 * k)


def fold(on):
    SH = dims("stock_hinge")
    ax = (np.array([SH["axis_X"], SH["axis_Y"], 0.0]) - GRIP) / 1000.0
    for n in ("stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad"):
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        if on:
            M = F.rot_matrix(ax, (0, 0, 1), 180.0)
            ob.matrix_world = Matrix(M.tolist()) @ ob.matrix_world
        else:
            ob.matrix_world = Matrix.Identity(4)


def main():
    RD.engine(sc, "CYCLES", int(arg("--samples", "64")))
    RD.world_flat(sc, RD.srgb_to_lin((128, 128, 128)), 1.0, env=0.4)
    m = RD.principled("Grey", RD.srgb_to_lin((150, 150, 150)), 0.0, 0.55)
    RD.assign(meshes(), m)
    studio_lights()
    cam = RD.camera_object()
    panel_cam(cam, "LEFT", (0, -1, 0), (0, 0, 1))
    RD.still(sc, OUT / "form_grey_left.png")
    panel_cam(cam, "RIGHT", (0, 1, 0), (0, 0, 1))
    RD.still(sc, OUT / "form_grey_right.png")
    panel_cam(cam, "TOP", (0, 0, -1), (0, -1, 0))
    RD.still(sc, OUT / "form_grey_top.png")
    camf = SCRATCH / "q34" / "camera_form.json"
    if not camf.exists():
        camf = SCRATCH / "q34" / "camera_blockout.json"
    qres = REVIEW / "form" / "q34_result.json"
    if not qres.exists():
        qres = REVIEW / "blockout" / "q34_result.json"
    if camf.exists() and qres.exists():
        bx = json.loads(qres.read_text())["panel_box_sheet_px"]
        RD.persp_from_solve(cam, sc, json.loads(camf.read_text()), GRIP, (bx[3] - bx[1] + 1, bx[2] - bx[0] + 1), SS)
        RD.still(sc, OUT / "form_grey_q34.png")
    fold(True)
    panel_cam(cam, "RIGHT", (0, 1, 0), (0, 0, 1))
    RD.still(sc, OUT / "form_grey_folded_right.png")
    panel_cam(cam, "TOP", (0, 0, -1), (0, -1, 0))
    RD.still(sc, OUT / "form_grey_folded_top.png")
    fold(False)
    print("[SMG01] RENDER_DONE", OUT)


main()
