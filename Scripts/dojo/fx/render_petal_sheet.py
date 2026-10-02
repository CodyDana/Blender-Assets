"""Render our petals in the sheet's layout (front + back on a grey card; lying 3/4 + edge-on) for the side-by-side.

    blender -b Assets/Dojo/DojoFX.blend --factory-startup --python Scripts/dojo/fx/render_petal_sheet.py -- --out DIR

Each panel is its own Cycles render (Standard view). The exposure is calibrated so the 0.18 grey card renders at the
sheet's card value (measured 101/99/98 sRGB), which is the frame the petal colour targets were derived in.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_bl as B  # noqa: E402
import fx_common as fx  # noqa: E402

PANEL = (480, 428)  # 2x the sheet's panel size (240 x 214)
ROW2 = (480, 300)
ORDER = ["A", "B", "C", "D", "E", "F"]


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(fx.WORK / "renders/sheet"))
    p.add_argument("--samples", type=int, default=96)
    return p.parse_args(a)


def build(sc, samples):
    B.cycles(sc, samples=samples, res=PANEL)
    sc.unit_settings.system = "METRIC"
    card_mat = B.simple_material("M_Card", (0.18, 0.18, 0.18), rough=0.9)
    me = bpy.data.meshes.new("Card")
    me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)])
    card = bpy.data.objects.new("Card", me)
    card.data.materials.append(card_mat)
    sc.collection.objects.link(card)
    light_data = bpy.data.lights.new("Key", "AREA")
    light_data.energy = 6.0
    light_data.size = 0.35
    key = bpy.data.objects.new("Key", light_data)
    sc.collection.objects.link(key)
    key.location = (-0.12, 0.10, 0.30)
    B.look_at(key, (0, 0, 0))
    B.world_color(sc, (1, 1, 1), 0.55)
    return card, key


def place(src, sc, mode):
    """A linked duplicate of the petal posed for a panel; returns it."""
    ob = bpy.data.objects.new(src.name + "_" + mode, src.data)
    sc.collection.objects.link(ob)
    if mode == "front":
        rot = Euler((0, 0, 0))
    elif mode == "back":
        rot = Euler((0, math.pi, 0))
    elif mode == "lying":  # length along X (base to +X), seen from the front-low camera
        rot = Euler((0, 0, -math.pi / 2 + 0.25))
    else:  # edge: standing up, base down, rolled ~75 deg about its length
        rot = Euler((math.radians(90), math.radians(-10), math.radians(62)), "XYZ")
    ob.rotation_euler = rot
    sc.view_layers[0].update()
    zmin = min((ob.matrix_world @ v.co).z for v in ob.data.vertices)
    ob.location.z = -zmin + 0.0002
    sc.view_layers[0].update()
    return ob


def centre_of(ob):
    pts = np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])
    return Vector(((pts.min(0) + pts.max(0)) / 2).tolist()), pts


def render(sc, path):
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=sc.name)


def main():
    a = args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    src_scene = bpy.data.scenes[0]
    petals = {k: bpy.data.objects[f"SM_DKF_Petal_{k}"] for k in ORDER}
    sc = bpy.data.scenes.new("PetalSheet")
    card, key = build(sc, a.samples)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start = 0.001
    cam.data.lens = 85
    # calibrate exposure on the bare card
    sc.render.resolution_x, sc.render.resolution_y = 128, 128
    cam.location = (0, 0, 0.12)
    B.look_at(cam, (0, 0, 0))
    render(sc, out / "_calib.png")
    img = bpy.data.images.load(str(out / "_calib.png"))
    px = np.array(img.pixels[:]).reshape(128, 128, 4)[32:96, 32:96, :3].mean(axis=(0, 1))
    target = np.array([101.5, 98.9, 97.5]) / 255.0
    ratio = float(fx.srgb_to_lin(target).mean() / max(fx.srgb_to_lin(px).mean(), 1e-6))
    sc.view_settings.exposure = math.log2(ratio)
    print("CALIB card", px * 255, "exposure", sc.view_settings.exposure)
    for i, k in enumerate(ORDER):
        src = petals[k]
        # row 1: front + back side by side, seen from above (slight perspective like the sheet)
        f = place(src, sc, "front")
        b = place(src, sc, "back")
        cf, pf = centre_of(f)
        cb, pb = centre_of(b)
        wf = pf[:, 0].max() - pf[:, 0].min()
        wb = pb[:, 0].max() - pb[:, 0].min()
        gap = 0.0006
        f.location.x += -(cf.x) - wf / 2 - gap / 2
        b.location.x += -(cb.x) + wb / 2 + gap / 2
        f.location.y -= cf.y
        b.location.y -= cb.y
        sc.render.resolution_x, sc.render.resolution_y = PANEL
        cam.data.lens = 85
        cam.location = (0, -0.002, 0.060)
        B.look_at(cam, (0, 0, 0))
        render(sc, out / f"row1_{k}.png")
        for o in (f, b):
            bpy.data.objects.remove(o)
        # row 2: lying 3/4 (left) + edge-on standing (right)
        l = place(src, sc, "lying")
        e = place(src, sc, "edge")
        cl, pl = centre_of(l)
        ce, pe = centre_of(e)
        l.location.x += -cl.x - 0.0055
        l.location.y -= cl.y
        e.location.x += -ce.x + 0.0085
        e.location.y -= ce.y
        sc.render.resolution_x, sc.render.resolution_y = ROW2
        cam.location = (0.0, -0.058, 0.036)
        B.look_at(cam, (0.0012, 0, 0.0038))
        render(sc, out / f"row2_{k}.png")
        for o in (l, e):
            bpy.data.objects.remove(o)
    print("DONE", out)


if __name__ == "__main__":
    main()
