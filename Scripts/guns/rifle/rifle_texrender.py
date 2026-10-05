"""AR-01 renders from the BAKED MAPS only (headless Blender, Cycles): the game materials (M_AR01_Metal / _Furniture /
_Mag on T_AR01_<Set>_{BC,ORM,N}.png) on the LOD0 parts or the static twin's LODs; no procedural shading anywhere.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_texrender.py -- \
        --set side|realism|closeups|lods [--out DIR] [--samples 128] [--light 1.0]

side      the sheet-matched side view (the LEFT-labelled panel's px <-> mm frame, 3x), studio light, grey backdrop
          (126): the L5 colour comparison input -> <out>/tex_side.png
realism   the four realism-judge views of RIFLE_BUILD_PLAN 9 (first person 35 cm, ADS, third person 3 m, hero 3/4),
          the ADS one twice: the spec's Sight line (notch bottom -> post tip) and the post-level-with-notch-top hold
closeups  receiver right (c1 camera), front sight (c3 camera), grip, stock, magazine, butt plate
lods      SM_AR01_LOD0..3 side by side at their switch distances (same camera, 2560 x 1440, 90 deg)
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
from mathutils import Vector, Matrix  # noqa: E402

from gunlib import render as RD  # noqa: E402
from gunlib import look as LK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "side")
OUT = Path(arg("--out", str(REVIEW / "tex"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SAMPLES = int(arg("--samples", "128"))
LIGHT = float(arg("--light", "1.0"))
SPECF = float(arg("--spec", "1.0"))        # L5 rig: the lights' specular factor (fitted with the light scale)
sc = bpy.context.scene


def show_only(objs):
    keep = set(o.name for o in objs)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep


def lod0_parts():
    return [o for o in bpy.data.collections["AR01_Parts"].objects if o.type == "MESH"]


def B(p):
    return Vector(((np.asarray(p, float) - GRIP) / 1000.0).tolist())


def trace_frame(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    b = j["panel_box_sheet_px"]
    return j["px_per_mm"], j["bore_dir_px"], j["origin_px"], (b[3] - b[1] + 1, b[2] - b[0] + 1)


def studio_lights(k=1.0):
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    RD.area_light("Key", (0.35, -0.9, 0.75), (0.25, 0, -0.02), 1.6, 34 * k)
    RD.area_light("Fill", (0.9, -0.8, -0.2), (0.3, 0, 0.0), 2.0, 10 * k)
    RD.area_light("Top", (0.3, 0.1, 1.2), (0.3, 0, 0.0), 2.0, 16 * k)
    RD.area_light("Rim", (0.2, 0.9, 0.5), (0.3, 0, 0.0), 1.2, 10 * k)


def sheet_lights(k=1.0):
    """L5 rig (the sheet's look: highlights on the top surfaces, the side flats lit at a grazing angle so they show
    their own colour, not a reflected light): a large soft key above and slightly in front, a weak front fill high
    up, a rim behind. Positions in frame B metres round the gun's centre."""
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = (0.2, 0.0, 0.0)
    RD.area_light("Key", (0.25, -0.45, 1.3), c, 2.4, 60 * k)
    RD.area_light("Fill", (0.1, -1.6, 0.9), c, 2.0, 14 * k)
    RD.area_light("Rim", (0.2, 1.0, 0.6), c, 1.5, 10 * k)


def persp(cam, eye_M, target_M, fov_deg, res, up=(0.0, 0.0, 1.0)):
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


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def realism_shots():
    sl = SPEC.key["sight_line"]
    notch, post = np.array(sl["notch_M"], float), np.array(sl["post_tip_M"], float)
    d_spec = unit(post - notch)
    top = notch + np.array([0.0, 0.0, 48.0 - notch[2]])
    d_top = unit(post - top)
    fp_eye = np.array([350.0, 0.0, 0.0]) + 350.0 * unit([-0.93, 0.22, 0.30])
    hero_t = np.array([450.0, 0.0, -20.0])
    return [("fp_35cm", fp_eye, np.array([620.0, 0.0, 10.0]), 70.0, 1.1),
            ("ads_spec_line", notch - 250.0 * d_spec, post, 55.0, 1.1),
            ("ads_notch_top_hold", top - 250.0 * d_top, post, 55.0, 1.1),
            ("tp_3m", hero_t + 3000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, 3.2),
            ("hero_34", hero_t + 1500.0 * unit([0.55, -0.78, 0.30]), hero_t, 38.0, 1.6)]


def main():
    RD.engine(sc, "CYCLES", SAMPLES)
    sc.render.resolution_percentage = 100
    cam = RD.camera_object("TexCam")
    if SET == "side":
        show_only(lod0_parts())
        RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=0.25)
        sheet_lights(LIGHT)
        # Cycles ignores a light's specular factor: each light becomes a diffuse-only copy at (1 - s) of its energy
        # plus the full light at s, so the diffuse light stays k and the specular light is k x s
        for lo in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            if SPECF < 1.0:
                d = lo.copy()
                d.data = lo.data.copy()
                bpy.context.scene.collection.objects.link(d)
                d.data.energy = lo.data.energy * (1.0 - SPECF)
                d.visible_glossy = False
                lo.data.energy = lo.data.energy * SPECF
        s, u, p0, shape = trace_frame("LEFT")
        RD.ortho_side(cam, sc, s, u, p0, shape, GRIP, 3)
        RD.still(sc, OUT / "tex_side.png")
    elif SET == "realism":
        show_only(lod0_parts())
        for name, eye, tgt, fov, ld in realism_shots():
            LK.rough_world(sc, (126, 126, 126), 0.55)
            sc.render.film_transparent = False
            persp(cam, eye, tgt, fov, (1600, 900))
            bpy.context.view_layer.update()
            LK.rough_lights(cam, tuple(B(tgt)), ld, 1.35 * LIGHT)
            RD.still(sc, OUT / f"{name}.png")
    elif SET == "closeups":
        show_only(lod0_parts())
        RD.world_flat(sc, RD.srgb_to_lin((123, 123, 123)), 1.0, env=0.35)
        studio_lights(LIGHT)
        for k, nm in (("c1", "receiver_right"), ("c3", "front_sight")):
            camd = json.loads((SCRATCH / "q34" / f"camera_{k}.json").read_text())
            Rm = np.array(camd["R_rows_right_up_fwd_M"], float)
            c = np.array(camd["image_centre_point_M"], float)
            W, H = camd["panel_px"]
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2] = Rm[0], Rm[1], -Rm[2]
            M[:3, 3] = (c - Rm[2] * 800.0 - GRIP) / 1000.0
            cam.matrix_world = Matrix(M.tolist())
            cam.data.type = "ORTHO"
            cam.data.sensor_fit = "HORIZONTAL"
            cam.data.ortho_scale = camd["ortho_width_mm"] / 1000.0
            cam.data.shift_x = cam.data.shift_y = 0.0
            cam.data.clip_start = 0.05
            cam.data.clip_end = 5.0
            sc.render.resolution_x, sc.render.resolution_y = W * 3, H * 3
            RD.still(sc, OUT / f"cu_{nm}.png")
        for nm, (eye, tgt, fov) in {
                "grip_checker": ((330, -170, -70), (270, 0, -88), 30.0),
                "stock_r34": ((60, -420, 120), (110, 0, -40), 38.0),
                "mag_left": ((420, 330, -130), (440, 0, -95), 40.0),
                "buttplate": ((-160, -170, 0), (10, 0, -40), 34.0),
                "receiver_top": ((300, -150, 330), (360, 0, 10), 40.0),
                "muzzle_34": ((960, -150, 60), (840, 0, 0), 32.0)}.items():
            persp(cam, eye, tgt, fov, (1600, 1100))
            RD.still(sc, OUT / f"cu_{nm}.png")
    elif SET == "lods":
        sizes = json.loads((ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "game_lod_sizes.json").read_text())
        r = sizes["bounds_radius_m"]
        s_ = sizes["SM_AR01"]
        RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=0.45)
        studio_lights(LIGHT)
        V0 = np.array([v.co[:] for v in bpy.data.objects["SM_AR01_LOD0"].data.vertices])
        cB = 0.5 * (V0.min(0) + V0.max(0))
        for k in range(4):
            for j in ((k - 1, k) if k else (0, 1)):
                pass
        for k in range(1, 4):
            d = 1.778 * r / s_[k]
            for lv in (k - 1, k):
                show_only([bpy.data.objects[f"SM_AR01_LOD{lv}"]])
                eye = cB + np.array([0.35, -0.9, 0.2]) / np.linalg.norm([0.35, -0.9, 0.2]) * d
                cam.location = Vector(eye.tolist())
                cam.rotation_euler = (Vector(cB.tolist()) - cam.location).to_track_quat("-Z", "Y").to_euler()
                cam.data.type = "PERSP"
                cam.data.sensor_fit = "HORIZONTAL"
                cam.data.angle = math.radians(90.0)
                cam.data.clip_end = 100.0
                sc.render.resolution_x, sc.render.resolution_y = 2560, 1440
                RD.still(sc, OUT / f"lod_switch{k}_lod{lv}.png")
    print("[AR01] TEXRENDER_DONE", SET)


main()
