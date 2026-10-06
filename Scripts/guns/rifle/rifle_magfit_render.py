"""AR-01 magazine-fit look renders (R51 loop-back), Cycles grey, on a built blend:

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_magfit_render.py -- [--out DIR]

1 well_below_seated     the well from below / front-left with the magazine seated (the seams, the lug channel)
2 well_below_empty      the same view with the magazine hidden (trunnion lower rear, pocket, ledge, ramp, catch nose)
3 well_cut_section      a half-section at Y = 0 (parts cut by a boolean copy) with the magazine seated
4 side_seam             the side view close-up of the well's front and rear seams (magazine seated)
5 rock_start            the magazine at MagRockStart (8 deg) from the side, the receiver cut at Y = 0
6 insert_start          the magazine at MagInsertStart, cut at Y = 0
7 trunnion_from_below_rear  the front trunnion's lower rear face up through the empty well
Default out: WorkFiles/guns/rifle/review/magfit/.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import GRIP, REVIEW  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from gunlib import render as RD  # noqa: E402
import rifle_magfit as MF  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else REVIEW / "magfit"
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
MAGS = ("magazine", "magazine_floor_plate")


def B(m):
    return Vector((np.asarray(m, float) - GRIP) / 1000.0)


def parts():
    col = bpy.data.collections.get("AR01_Parts")
    return [o for o in (col.objects if col else bpy.data.objects) if o.type == "MESH"]


def setup():
    for o in list(bpy.data.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in bpy.data.collections:
        if c.name != "AR01_Parts":
            c.hide_render = True
    RD.engine(sc, "CYCLES", 96)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
    RD.world_flat(sc, RD.srgb_to_lin((128, 128, 128)), 0.35)
    grey = RD.principled("Grey", RD.srgb_to_lin((165, 165, 165)), 0.0, 0.5)
    magm = RD.principled("MagGrey", RD.srgb_to_lin((95, 105, 125)), 0.0, 0.5)
    for o in parts():
        RD.assign([o], magm if o.name in MAGS else grey)
    c = B((400.0, 0.0, -30.0))
    RD.area_light("Key", c + Vector((0.15, -0.25, -0.05)), c, 0.25, 2.5)
    RD.area_light("Fill", c + Vector((-0.2, 0.2, -0.15)), c, 0.3, 1.2)
    RD.area_light("Top", c + Vector((0.0, 0.0, 0.3)), c, 0.3, 1.0)


def shoot(name, eye_M, target_M, lens=60.0, ortho=None):
    cam = RD.camera_object("MFCam")
    cam.location = B(eye_M)
    d = B(target_M) - B(eye_M)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho / 1000.0
    else:
        cam.data.lens = lens
    cam.data.clip_start = 0.001
    sc.camera = cam
    RD.still(sc, str(OUT / f"{name}.png"))
    bpy.data.objects.remove(cam, do_unlink=True)


def set_mag(visible=True, phi=0.0, s=0.0):
    piv = B((MF.PIVOT[0], 0.0, MF.PIVOT[1]))
    # base forward = Unreal pitch +phi = Blender rotation about +Y by -phi (rotation_euler.y = -theta, plan 2.3);
    # the insert moves s along the tilted -Z
    R = Matrix.Rotation(-phi, 4, "Y")
    T = Matrix.Translation(piv) @ R @ Matrix.Translation(-piv)
    off = Matrix.Translation(Vector((math.sin(phi) * s, 0.0, -math.cos(phi) * s)) / 1000.0)
    for o in parts():
        if o.name in MAGS:
            if "_m0" not in o:
                o["_m0"] = [list(r) for r in o.matrix_world]
            o.matrix_world = off @ T @ Matrix(o["_m0"])
            o.hide_render = not visible


def cut_y0(on):
    """Half-section: a boolean DIFFERENCE box (Y < 0 removed) on every part."""
    for o in parts():
        m = o.modifiers.get("_cut")
        if on and not m:
            if "_cutbox" not in bpy.data.objects:
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                b = bpy.context.active_object
                b.name = "_cutbox"
                b.scale = (2.0, 0.2, 2.0)
                b.location = (0.0, -0.1 - 1e-5, 0.0)
                b.hide_render = True
            m = o.modifiers.new("_cut", "BOOLEAN")
            m.operation = "DIFFERENCE"
            m.solver = "EXACT"
            m.object = bpy.data.objects["_cutbox"]
        elif not on and m:
            o.modifiers.remove(m)


def main():
    setup()
    set_mag(True)
    shoot("1_well_below_seated", (470.0, 70.0, -95.0), (400.0, 0.0, -31.0), 50.0)
    set_mag(False)
    shoot("2_well_below_empty", (470.0, 70.0, -95.0), (410.0, 0.0, -25.0), 50.0)
    # the front trunnion's lower rear face (lug channel, ledge, pocket, ramp) seen up through the empty well
    shoot("7_trunnion_from_below_rear", (372.0, 30.0, -70.0), (427.0, 0.0, -20.0), 55.0)
    set_mag(True)
    cut_y0(True)
    shoot("3_well_cut_section", (400.0, -300.0, -25.0), (400.0, 0.0, -25.0), ortho=95.0)
    set_mag(True, math.radians(MF.ROCK_DEG), 0.0)
    shoot("5_rock_start", (400.0, -300.0, -25.0), (400.0, 0.0, -25.0), ortho=95.0)
    set_mag(True, math.radians(MF.ROCK_DEG), MF.INSERT_D)
    shoot("6_insert_start", (400.0, -300.0, -25.0), (400.0, 0.0, -25.0), ortho=95.0)
    cut_y0(False)
    set_mag(True)
    shoot("4_side_seam", (400.0, -300.0, -32.0), (400.0, 0.0, -32.0), ortho=80.0)
    print("[AR01-mfr] RENDERS_DONE", OUT)


main()
