"""Pilot 2 SURFACE GATE (before any rock is re-baked): a test patch carrying the layered surface (scanned macro relief
as real displacement + regraded macro albedo + the tiling crystal grain + lichen / wet layers), rendered close-up the
way the sheet frames its close-ups, then measured against the sheet panels by Scripts/dojo/rocks/rocks_measure2.py.

    blender -b --factory-startup --python Scripts/dojo/rocks/rocks_surface_test.py -- [grain lichen wet]

Writes WorkFiles/dojo/build/rocks/pilot2/surface/patch_<shot>.png.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "Scripts" / "stone", ROOT / "Scripts" / "dojo" / "rocks", ROOT / "Scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import rocks_render as R  # noqa: E402
import rocks_material2 as rm  # noqa: E402
import stone_bake as sb  # noqa: E402
import stone_sdf as sd  # noqa: E402
import stone_weather2 as sw2  # noqa: E402

OUT = ROOT / "WorkFiles" / "dojo" / "build" / "rocks" / "pilot2" / "surface"


def patch(size=0.5, step=0.002, kind="cliff", amp=None):
    n = int(size / step) + 1
    xs = np.linspace(-size / 2, size / 2, n)
    X, Y = np.meshgrid(xs, xs)
    Z = 0.10 * (1 - (X / size * 2) ** 2) * (1 - (Y / size * 2) ** 2) * 0.4
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    F = np.vstack([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    N = sd.vertex_normals(V, F)
    V = sw2.scan_displace(V, N, kind, amp=amp)
    return V, F


def set_attrs(ob, Lc, Lp):
    me = ob.data
    for nm in ("Lc", "Lp"):
        if nm in me.attributes:
            me.attributes.remove(me.attributes[nm])
    a = me.attributes.new("Lc", "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(Lc, np.float32).ravel())
    c = me.color_attributes.new("Lp", "FLOAT_COLOR", "POINT")
    c.data.foreach_set("color", np.asarray(Lp, np.float32).ravel())


def shot(name, kind, mk, mk2, width, res=(720, 1000), elev=90.0, seed=0):
    sc = R.reset()
    R.world_colour((0.62, 0.64, 0.68), 0.9)
    R.sun("Key", 48.0, 300.0, 3.2, (1.0, 0.97, 0.92), angle_deg=6.0)
    sc.cycles.samples = 256
    sc.render.film_transparent = False
    V, F = patch(kind=kind)
    ob = sb.make_obj("Patch", V, F)
    n = len(V)
    sb.set_point_colour(ob, "Mk", np.tile(np.asarray(mk, float)[None, :3], (n, 1)))
    ca = ob.data.color_attributes["Mk"]
    cols = np.empty(n * 4, np.float32)
    ca.data.foreach_get("color", cols)
    cols = cols.reshape(n, 4)
    cols[:, 3] = mk[3]
    ca.data.foreach_set("color", cols.ravel())
    sb.set_point_colour(ob, "Mk2", np.tile(np.asarray(mk2, float)[None, :], (n, 1)))
    Lc, Lp, nl = sw2.lichen_fields(V, sd.vertex_normals(V, F), np.full(n, float(mk[1])), seed + 5, F=F)
    set_attrs(ob, Lc, Lp)
    mat = rm.composite_material(f"Preview_{name}", kind, mode="PREVIEW")
    ob.data.materials.append(mat)
    lens = 100.0
    dist = width * lens / 36.0 * (max(res) / res[0])
    e = math.radians(elev)
    loc = Vector((0.0, -math.cos(e) * dist, math.sin(e) * dist + 0.04))
    R.camera("Cam", tuple(loc), (0.0, 0.0, 0.04), lens=lens)
    R.render(OUT / f"patch_{name}.png", res=res)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    shots = argv or ["grain", "lichen", "wet", "mid"]
    for s in shots:
        if s == "grain":
            shot("grain", "cliff", (0, 0, 0, 0.5), (0, 0, 0), 0.055)
        elif s == "lichen":
            shot("lichen", "cliff", (0, 1, 0, 0.45), (0, 0, 0), 0.20)
        elif s == "wet":
            shot("wet", "river", (0, 0, 1, 0.5), (0, 0.6, 0), 0.30)
        elif s == "mid":
            shot("mid", "cliff", (0, 0, 0, 0.5), (0, 0, 0), 0.40)


if __name__ == "__main__":
    main()
