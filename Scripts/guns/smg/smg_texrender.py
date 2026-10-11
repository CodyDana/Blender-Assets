"""SMG01 renders from the BAKED MAPS only (headless Blender, Cycles): the game materials (M_SMG01_Metal / _Furniture /
_Mag on T_SMG01_<Set>_{BC,ORM,N}.png, gunlib.game.game_material) on the LOD0 parts; no procedural shading anywhere.

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_texrender.py -- \
        --set side|realism|closeups [--tex DIR] [--out DIR] [--samples 128] [--light 1.0]

side      the LEFT panel's px <-> mm map (3x), the physical L5 rig (one overhead key tipped toward the camera, a rim,
          the grey world 126 as fill / environment; specular factor 1): the L5 input -> <out>/tex_side.png (+ RIGHT)
realism   the realism judges' views (SMG_BUILD_PLAN 14.1 L7): fp_35cm, ads (the B4 eye 0.25 m behind the aperture on
          the sight line, 55 deg, 2560 x 1440), tp_3m, hero_34, and hero_34_folded (stock folded); the same cameras as
          the early-realism set (smg_realism.shots), the rough-look lights
closeups  the seven part groups at 35 cm (g1..g7, as smg_realism) from the maps -> <out>/closeups/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, GRIP, REVIEW, PARTS_COLL, PanelMap, trace, socket, dims  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import smg_surface as SS  # noqa: E402
from gunlib import render as RD  # noqa: E402
from gunlib import look as LK  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import fit as F  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "side")
TEX = Path(arg("--tex", str(ROOT / "Exports" / "Guns" / "SMG01" / "Textures"))).resolve()
OUT = Path(arg("--out", str(REVIEW / "realism_tex"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SAMPLES = int(arg("--samples", "128"))
LIGHT = float(arg("--light", "1.0"))
KEY_ELEV = float(arg("--key-elev", "70"))
ENV = float(arg("--env", "0.20"))
SSF = int(arg("--ss", "3"))
sc = bpy.context.scene
STOCK = ["stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad"]


def parts():
    return [o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"]


def B(p):
    return Vector(((np.asarray(p, float) - GRIP) / 1000.0).tolist())


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def assign_game_materials():
    mats = {st: GM.game_material(cfg["slot"], f"T_SMG01_{st}", TEX) for st, cfg in SS.SETS.items()}
    for o in parts():
        st = SS.SLOT_SET[json.loads(o.get("gun_part", "{}"))["slot"]]
        o.data.materials.clear()
        o.data.materials.append(mats[st])
        o.hide_render = False
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in parts():
            o.hide_render = True


def physical_rig(k=1.0, elev_deg=70.0):
    """The AR-01's physical L5 rig (rifle_texrender.sheet_lights_physical)."""
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = np.array((0.0, 0.0, 0.05))
    e = math.radians(elev_deg)
    RD.area_light("Key", tuple(c + 1.4 * np.array((0.05, -math.cos(e), math.sin(e)))), tuple(c), 2.4, 60 * k)
    RD.area_light("Rim", (0.0, 1.0, 0.6), tuple(c), 1.5, 10 * k)


def panel_cam(cam, view, look, up):
    j = trace(view)
    b = j["panel_box_sheet_px"]
    W, H = b[2] - b[0] + 1, b[3] - b[1] + 1
    PM = PanelMap(view)
    c = PM.mm([[W / 2.0 - 0.5, H / 2.0 - 0.5]], raw=True)[0]
    cM = np.array([c[0], 0.0, c[1]])
    look = Vector(look).normalized()
    cam.location = Vector(((cM - GRIP) / 1000.0).tolist()) - look * 2.0
    q = look.to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    upv = q @ Vector((0, 1, 0))
    if upv.dot(Vector(up)) < 0.99:
        ang = math.atan2(look.dot(upv.cross(Vector(up))), upv.dot(Vector(up)))
        cam.rotation_euler = (Matrix.Rotation(ang, 4, look) @ q.to_matrix().to_4x4()).to_euler()
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = W / PM.s / 1000.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.1
    cam.data.clip_end = 10.0
    sc.render.resolution_x, sc.render.resolution_y = W * SSF, H * SSF


def persp(cam, eye_M, target_M, fov_deg, res):
    eye, tgt = B(eye_M), B(target_M)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(fov_deg)
    cam.data.clip_start = 0.01
    cam.data.clip_end = 60.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    sc.render.resolution_x, sc.render.resolution_y = res


def shots():
    """smg_realism.shots (the early-realism cameras), copied: PIL is not available inside Blender."""
    sight = np.array(socket("Sight")["M_mm"], float)
    post = np.array(socket("SightFront")["M_mm"], float)
    ads_eye = sight - 250.0 * unit(post - sight)
    out = {}
    for name, tgt, d in [("g1_receiver_rails", (430.0, 0.0, 20.0), (-0.25, 0.75, 0.62)),
                         ("g2_grip_trigger_sel", (330.0, 0.0, -60.0), (0.1, 1.0, -0.05)),
                         ("g3_magazine_well", (440.0, 0.0, -75.0), (0.65, 0.7, 0.0)),
                         ("g4_stock_extended", (190.0, 0.0, 0.0), (-0.45, -0.8, 0.4)),
                         ("g5_stock_folded", (380.0, -60.0, 0.0), (0.0, -1.0, 0.35)),
                         ("g6_front_end", (575.0, 0.0, 25.0), (0.75, 0.6, 0.25)),
                         ("g7_rear_sight", (300.0, 0.0, 55.0), (-0.5, 0.6, 0.62))]:
        t = np.asarray(tgt, float)
        out[name] = (t + 350.0 * unit(d), t, 40.0, 0.6, (1600, 900))
    fp_r = np.array([360.0, 0.0, 10.0])
    out["fp_35cm"] = (fp_r + 350.0 * unit([-0.93, 0.22, 0.30]), np.array([620.0, 0.0, 10.0]), 70.0, 1.1, (1600, 900))
    out["ads"] = (ads_eye, post, 55.0, 1.1, (2560, 1440))
    hero_t = np.array([380.0, 0.0, -30.0])
    out["hero_34"] = (hero_t + 1500.0 * unit([0.55, 0.78, 0.30]), hero_t, 38.0, 1.6, (1600, 900))
    out["tp_3m"] = (hero_t + 3000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, 3.2, (1600, 900))
    out["hero_34_folded"] = (hero_t + 1500.0 * unit([0.40, -0.85, 0.35]), hero_t, 38.0, 1.6, (1600, 900))
    return out


def fold(on):
    SH = dims("stock_hinge")
    ax = (np.array([SH["axis_X"], SH["axis_Y"], 0.0]) - GRIP) / 1000.0
    for nm in STOCK:
        ob = bpy.data.objects.get(nm)
        if ob is None:
            continue
        ob.matrix_world = Matrix(F.rot_matrix(ax, (0, 0, 1), 180.0).tolist()) @ ob.matrix_world if on \
            else Matrix.Identity(4)


def render_shot(cam, name, spec, out):
    eye, tgt, fov, ld, res = spec
    LK.rough_world(sc, (126, 126, 126), 0.3)
    sc.render.film_transparent = False
    persp(cam, eye, tgt, fov, res)
    bpy.context.view_layer.update()
    LK.rough_lights(cam, tuple(B(tgt)), ld, 0.85 * LIGHT)
    RD.still(sc, out / f"{name}.png")


def main():
    RD.engine(sc, "CYCLES", SAMPLES)
    sc.render.resolution_percentage = 100
    assign_game_materials()
    cam = RD.camera_object("TexCam")
    if SET == "side":
        RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=ENV * LIGHT)
        physical_rig(LIGHT, KEY_ELEV)
        panel_cam(cam, "LEFT", (0, -1, 0), (0, 0, 1))
        RD.still(sc, OUT / "tex_side.png")
        if "--right" in argv:
            panel_cam(cam, "RIGHT", (0, 1, 0), (0, 0, 1))
            RD.still(sc, OUT / "tex_side_right.png")
    elif SET == "realism":
        sh = shots()
        for name in ("fp_35cm", "ads", "tp_3m", "hero_34"):
            render_shot(cam, name, sh[name], OUT)
        fold(True)
        render_shot(cam, "hero_34_folded", sh["hero_34_folded"], OUT)
        fold(False)
    elif SET == "closeups":
        sh = shots()
        od = OUT / "closeups"
        od.mkdir(parents=True, exist_ok=True)
        for name in ("g1_receiver_rails", "g2_grip_trigger_sel", "g3_magazine_well", "g4_stock_extended",
                     "g5_stock_folded", "g6_front_end", "g7_rear_sight"):
            if name == "g5_stock_folded":
                fold(True)
            render_shot(cam, name, sh[name], od)
            if name == "g5_stock_folded":
                fold(False)
    print("[SMG01] TEXRENDER_DONE", SET)


main()
