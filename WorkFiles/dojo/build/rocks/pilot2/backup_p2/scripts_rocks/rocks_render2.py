"""Pilot 2 renders (study 6.4): headless Cycles, denoised. Modes:

  clay    grey clay (untextured), studio: front / side / top + the 3/4 view (form check)   -> pilot2/form/
  sil     silhouettes (alpha) for IoU: ortho front / side / back / top + oblique views over a grid of azimuths and
          elevations (the sheet's smaller views are elevated 3/4 views)                     -> pilot2/sil/
  sheet   the sheet's row layout per rock: main view with the 1.8 m figure, main-only, top (oblique), side; plus
          the 3/4 view textured and clay, on the light-grey studio                           -> pilot2/sheet/
  close   close-ups framed like the sheet's (grain, fracture edge, moss, wet zone, lichen)   -> pilot2/close/
  river   the small sunset riverbank test (the dojo's 9 deg western sun)                    -> pilot2/river/

    blender -b --factory-startup --python Scripts/dojo/rocks/rocks_render2.py -- <mode> [rocks...] [--src dense|blend]
"""
from __future__ import annotations

import json
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
import rocks_render_final as RF  # noqa: E402
from rocks_plans2 import PLANS  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work2"
OUT = BUILD / "pilot2"
BLEND = ROOT / "Assets" / "Dojo" / "DojoRocks.blend"
R.BLEND = BLEND

Q34 = dict(azim=35.0, elev=22.0)          # the 3/4 view: 35 deg round from the front, 22 deg up


def log(*a):
    print("[render2]", *a, flush=True)


def get_rock(r, src):
    if src == "dense":
        return R.mesh_from_npz(r, WORK / f"{r}_dense.npz")
    objs = R.append_from_blend([PLANS[r]["prefix"]])
    return objs[PLANS[r]["prefix"]]


def persp(target, dist, azim, elev, lens):
    return RF.persp_cam(target, dist, azim, elev, lens)


def fit(w, h, lens, res, margin=1.15):
    return RF.fit_dist(w, h, lens, res, margin)


def q34_cam(lo, hi, lens=60.0, res=(1400, 1000), margin=1.18):
    L, D, H = hi[0] - lo[0], hi[1] - lo[1], hi[2]
    a = math.radians(Q34["azim"])
    w = abs(L * math.cos(a)) + abs(D * math.sin(a))
    h = H * math.cos(math.radians(Q34["elev"])) + (L * math.sin(a) + D * math.cos(a)) * \
        math.sin(math.radians(Q34["elev"])) * 0.5
    tgt = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, H * 0.42)
    return persp(tgt, fit(w, h, lens, res, margin), Q34["azim"], Q34["elev"], lens)


# ----------------------------------------------------------------------------------------------- clay
def mode_clay(rocks, src):
    out = OUT / "form"
    for r in rocks:
        sc = R.reset()
        R.studio()
        ob = get_rock(r, src)
        for c in ob.children:
            c.hide_render = True
        ob.data.materials.clear()
        ob.data.materials.append(R.clay_material())
        RF.holdout_below()
        lo, hi = R.bbox_of(ob)
        sc.cycles.samples = 64
        for v, el in (("front", 8.0), ("side", 8.0), ("top", 90.0)):
            sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
            R.view_cam((lo, hi), v, elev=el, ortho=True)
            R.render(out / f"clay_{r}_{v}.png", res=(1400, 1000))
        q34_cam(lo, hi)
        R.render(out / f"clay_{r}_q34.png", res=(1400, 1000))


# ----------------------------------------------------------------------------------------------- silhouettes
SIL_OBLIQUE = [(az, el) for az in (-40, -25, -10, 0, 10, 25, 40) for el in (25, 35, 45, 55, 65)]


def mode_sil(rocks, src):
    out = OUT / "sil"
    meta = {}
    for r in rocks:
        sc = R.reset()
        R.world_colour((1, 1, 1), 1.0)
        ob = get_rock(r, src)
        for o in list(bpy.data.objects):
            if o.name.startswith("UCX_"):
                bpy.data.objects.remove(o)
        ob.data.materials.clear()
        ob.data.materials.append(R.clay_material(0.0))
        R.holdout_ground()
        lo, hi = R.bbox_of(ob)
        meta[r] = {"bbox": [lo.tolist(), hi.tolist()]}
        sc.cycles.samples = 4
        sc.cycles.use_denoising = False
        res = (800, 800)
        sc.render.resolution_x, sc.render.resolution_y = res
        for v, e in [("front", e) for e in (0, 5, 10, 15)] + [("side", e) for e in (0, 5, 10, 15)] + \
                [("back", 0), ("top", 90)]:
            R.view_cam((lo, hi), v, elev=e, ortho=True, margin=1.1)
            R.render(out / f"sil_{r}_{v}_e{e:02d}.png", res=res)
        # oblique views (orthographic, any azimuth): the sheet's elevated small views
        c = (lo + hi) / 2
        c[2] = hi[2] / 2
        ext = float(np.linalg.norm(hi - lo))
        for az, el in SIL_OBLIQUE:
            a, e = math.radians(az), math.radians(el)
            d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
            loc = Vector(c) + d * 30.0
            R.camera("CamO", tuple(loc), tuple(c), ortho=ext * 1.05)
            R.render(out / f"sil_{r}_obl_a{az:+03d}_e{el:02d}.png", res=res)
        # the 3/4 view as rendered in the sheet mode (perspective)
        sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
        q34_cam(lo, hi)
        R.render(out / f"sil_{r}_q34.png", res=(1400, 1000))
    (out / "sil_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    src = "dense"
    if "--src" in argv:
        i = argv.index("--src")
        src = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    mode = argv[0]
    rocks = argv[1:] or list(PLANS)
    if mode in ("clay", "sil"):
        globals()["mode_" + mode](rocks, src)
    else:
        import rocks_render2_final as rf2
        getattr(rf2, "mode_" + mode)(rocks, src)


if __name__ == "__main__":
    main()
