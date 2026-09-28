"""Look-match round 1 (sword): the comparison views, one definition shared by the design preview (high-poly) and
the shipped-asset renders, so both land on the same pixel grid as the reference crops (sfv4_lm_compose.py).

Ortho views use the sheet's own grid: sheet row r <-> z = (r - 10) * MM_PER_PX + Z_POMMEL_TOP, the sword axis on the
crop's centre column.  'hilt_*' = sheet rows 0..346 at 4x; 'full_*' = the whole view at 1x.
Perspective 'det_*' views are framed like the sheet's guard / blade / pommel detail crops.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector

import sfv4_render as R
import sfv4_spec as S

MMPX = S.MM_PER_PX
HILT_ROWS = (0, 346)
HILT_COLS = 150          # sheet px across the crop
HILT_K = 4               # zoom
#: studio environment (top / horizon / floor) seen in reflections
ENV = [float(x) for x in __import__('os').environ.get('SF4_ENV', '1.0,0.55,0.12').split(',')]
#: pommel detail camera: (angle off the end-face axis, azimuth, distance m, roll deg, aim z offset m)
POM_CAM = [float(x) for x in __import__('os').environ.get('SF4_POMCAM', '20,-120,0.2,228,0.012').split(',')]


def z_of_row(r):
    return (r - 10.0) * MMPX + S.Z_POMMEL_TOP


def _clear():
    for o in list(bpy.data.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o, do_unlink=True)


def _setup(samples, transparent):
    R.base_settings(samples, transparent=transparent)


def render_view(name, path, samples=48):
    _clear()
    sc = bpy.context.scene
    view = name.split("_", 1)[1]
    if name.startswith("hilt_"):
        _setup(samples, True)
        r0, r1 = HILT_ROWS
        h = (r1 - r0) * HILT_K
        w = HILT_COLS * HILT_K
        zc = z_of_row((r0 + r1 - 1) / 2.0)
        R.world_studio(bg=(1, 1, 1), env_top=ENV[0], env_mid=ENV[1], env_bot=ENV[2], env_strength=1.0)
        zfull = ((R.RENDER_H - 1) / 2.0 - 10.0) * MMPX + S.Z_POMMEL_TOP
        R.lights_sheet(zfull / 1000.0)      # the same light rig as the full views
        R.cam_ortho(view, zc, 0.0, h * MMPX / HILT_K / 1000.0, w, h)
    elif name.startswith("full_"):
        _setup(samples, True)
        H = R.RENDER_H
        zc = ((H - 1) / 2.0 - 10.0) * MMPX + S.Z_POMMEL_TOP
        R.world_studio(bg=(1, 1, 1), env_top=ENV[0], env_mid=ENV[1], env_bot=ENV[2], env_strength=1.0)
        R.lights_sheet(zc / 1000.0)
        R.cam_ortho(view, zc, 0.0, H * MMPX / 1000.0, R.RENDER_W, H)
    elif name == "det_guard":
        _setup(samples, True)
        R.world_studio(bg=(1, 1, 1), env_top=ENV[0], env_mid=ENV[1], env_bot=ENV[2])
        g = S.GUARD_BLOSSOM_Z / 1000.0
        R.lights_sheet(g, size=0.45)
        # sheet crop: the guard seen from the front, a little from the grip side, the axis leaning ~8 deg
        R.cam_persp((0.035, -0.42, g - 0.085), (0.0, 0.0, g + 0.012), lens=85, roll=math.radians(-173), w=828, h=1060)
    elif name == "det_pommel":
        _setup(samples, True)
        R.world_studio(bg=(1, 1, 1), env_top=ENV[0], env_mid=ENV[1], env_bot=ENV[2])
        zp = S.Z_POMMEL_TOP / 1000.0
        R.lights_sheet(zp + 0.1, size=0.45)
        R.area("PommelKey", (-0.35, -0.30, zp - 0.45), (0, 0, zp), 60, 0.35, (1.0, 0.98, 0.95))
        R.area("PommelFill", (0.40, -0.10, zp - 0.30), (0, 0, zp), 25, 0.35, (0.9, 0.95, 1.0))
        # sheet crop: the end face seen ~35 deg off its axis, the grip running to the lower left
        th, ph, dist = math.radians(POM_CAM[0]), math.radians(POM_CAM[1]), POM_CAM[2]
        loc = (dist * math.sin(th) * math.cos(ph), dist * math.sin(th) * math.sin(ph), zp - dist * math.cos(th))
        R.cam_persp(loc, (0.0, 0.0, zp + POM_CAM[4]), lens=85, roll=math.radians(POM_CAM[3]), w=1240, h=950)
    elif name == "det_blade":
        _setup(samples, True)
        R.world_studio(bg=(1, 1, 1), env_top=ENV[0], env_mid=ENV[1], env_bot=ENV[2])
        z = 0.26
        R.lights_sheet(z, size=0.45)
        R.cam_persp((0.033, -0.20, z + 0.028), (-0.003, 0.0, z), lens=85, roll=math.radians(-125), w=1266, h=858)
    else:
        raise ValueError(name)
    # the sheet lights every view from the viewer's side: turn the light rig with the camera for side / back views
    rot = {"back": math.pi, "side": math.pi / 2}.get(view, 0.0) if name.startswith(("hilt_", "full_")) else 0.0
    if rot:
        from mathutils import Matrix
        M = Matrix.Rotation(rot, 4, "Z")
        bpy.context.view_layer.update()      # matrix_world is stale until the depsgraph is evaluated
        for o in bpy.data.objects:
            if o.type == "LIGHT":
                o.matrix_world = M @ o.matrix_world
    R.render(path)
