"""Shared constants for the DojoLab SHOWCASE steps (dj_sc_import / dj_sc_materials / dj_sc_level / dj_sc_verify /
dj_sc_capture). Builds on dj_common (frame conversion, project paths, GASP constants); nothing here imports `unreal`.

Source of truth: WorkFiles/dojo/build/showcase/layout_showcase.json (Scripts/dojo/showcase/compose_showcase.py), which
merges the grey-box + KIT 1 layout.json, KIT 2 ground and the four prop kits, and blender_bounds.json beside it.
"""
import json
import math
from pathlib import Path

import dj_common as C  # noqa: F401  (re-exported helpers: loc_cm, yaw_deg, bbox_bl_to_ue, kelvin_rgb ...)

SC_BUILD = C.BUILD / "showcase"
SC_LAYOUT = SC_BUILD / "layout_showcase.json"
SC_BOUNDS = SC_BUILD / "blender_bounds.json"
SC_OUT = C.OUT / "showcase"
SC_CAPTURES = SC_OUT / "captures"
MASTER_DIR = "/Game/DojoKit/Materials/Masters"
GB_MAT_DIR = C.MAT_DEST                 # the grey-box flat instances (M_DGB_*), built by dj_materials.py
MANAGED_TAG = C.MANAGED_TAG             # the level step destroys exactly these actors on a re-run
NOCOL_CLASSES = {"nocollision"}
TEX_KINDS = ("BC", "ORM", "N", "M")
# The sunset look (round 2, 2026-09-28; measured with dj_sc_colour_probe.py, WorkFiles/dojo/build/unreal/round2_polish):
#  - EXPOSURE_OVER_ANALYTIC: the manual exposure sits +2.0 EV over the analytic Blender parity (0.6 - log2 K_LUX);
#  - LAMP_SCALE = 2^-2.0: the lamps are photometric conversions of the Blender review lights, so the same +2.0 EV made
#    them 4x too strong against the sun and sky (the gate ceiling and posts glowed orange); this keeps Blender's balance;
#  - SKY_FACTOR (sky luminance): the physical sky at a 13 deg sun reads deep blue and dark; this lifts it to the
#    Blender world's lilac-grey (the old (3.4, 2.6, 2.1) with a 4300 K sun turned the sky beige and the fill orange);
#  - SKYLIGHT_INTENSITY: the captured physical sky alone left a grey card in shade near black (probe C0: sRGB (0, 1, 6));
#    x 6 gives the Blender world's fill: a neutral 18 % card in shade reads lilac grey (104, 98, 117), the sun-lit one
#    warm (206, 178, 152) (probe D4);
#  - GRADE: neutral colour gain and saturation (the old gain (1.06, 1.0, 0.9) + saturation 0.85 tinted a neutral unlit
#    card from (145, 145, 144) to (153, 144, 134): a global orange filter); bloom and vignette as before.
EXPOSURE_OVER_ANALYTIC = 2.0
LAMP_SCALE = 2.0 ** -EXPOSURE_OVER_ANALYTIC
SKY_FACTOR = (2.6, 1.8, 1.6)
SKYLIGHT_INTENSITY = 6.0
GRADE = {"bloom_intensity": 0.35, "vignette_intensity": 0.15, "color_gain": (1.0, 1.0, 1.0, 1.0),
         "color_saturation": (1.0, 1.0, 1.0, 1.0)}


def load():
    return json.loads(SC_LAYOUT.read_text(encoding="utf-8"))


def bounds():
    return json.loads(SC_BOUNDS.read_text(encoding="utf-8"))


def mesh_path(layout, piece):
    return f"{layout['pieces'][piece]['ue_dir']}/{piece}"


def mat_path(layout, slot):
    if slot.startswith("M_DGB_"):
        return f"{GB_MAT_DIR}/{slot}"
    return f"{layout['materials'][slot]['ue_dir']}/{slot}"


def tex_path(layout, name):
    return f"{layout['textures'][name]['ue_dir']}/{name}"


def label(inst, n):
    return f"{inst['piece']}__{n:04d}"


def rot_matrix_bl(rot_xyz_deg):
    """Blender XYZ Euler (degrees) -> 3x3 rotation (rows), R = Rz Ry Rx."""
    rx, ry, rz = (math.radians(a) for a in rot_xyz_deg)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return [[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx]]


def ue_axes(rot_xyz_deg):
    """The Unreal actor's local X and Z axes for a Blender rotation: R_ue = S R_bl S with S = diag(1, -1, 1) (the Y
    mirror of the frame conversion; the FBX import mirrors the mesh's local Y the same way)."""
    R = rot_matrix_bl(rot_xyz_deg)
    S = (1.0, -1.0, 1.0)
    U = [[S[i] * R[i][j] * S[j] for j in range(3)] for i in range(3)]
    return (U[0][0], U[1][0], U[2][0]), (U[0][2], U[1][2], U[2][2])


def write_json(path, data):
    C.write_json(path, data)
