"""SMG01 config for the gun-agnostic gate drivers (gunlib 0.2.x, gunlib.gunconf): paths, names, the spec and the
per-driver data / hooks (B3 moving groups, B4 aperture sight picture, B6a, measure (L3 / L4), the straight-insert
magazine fit).

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/gunlib/drivers/run.py --
            --gun Scripts/guns/smg/smg_gun.py --driver b3
    py -3 -B Scripts/guns/gunlib/drivers/run.py --gun Scripts/guns/smg/smg_gun.py --driver b4 --npz ...
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from smg_common import CODE, SPEC_PATH, WORK, SPEC, D, dims, box, bone_head  # noqa: E402

import numpy as np  # noqa: E402

from gunlib.gunconf import GunConfig  # noqa: E402

CFG = GunConfig(CODE, WORK, SPEC_PATH, log_tag=CODE)

# ------------------------------------------------------------------------------------------------ B4 (aperture sight)
CFG.b4 = {"kind": "aperture", "socket": "Sight", "rear": ["sight_rear_leaf"], "post": "sight_front_leaf",
          "ignore": [], "tol_mm": 0.2, "fov": 55.0, "relief": 250.0, "W": 2560, "H": 1440, "ss": 8, "half": 110,
          "img": CFG.review / "b4" / "b4_sight_picture.png"}

# ------------------------------------------------------------------------------------------------ B6a
CFG.b6a = {"check_name": f"SM_{CODE}_B6aCheck"}


# ------------------------------------------------------------------------------------------------ B3 (filled below)
def b3_groups(G, rec, cfg):
    import smg_b3groups
    return smg_b3groups.groups(G, rec, cfg)


CFG.b3 = {"groups": b3_groups, "contact_pairs": [],
          "rows": {"sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "butt": [0.01, 0.05]}}


# ------------------------------------------------------------------------------------------------ measure (L3 / L4)
def _features(M):
    import smg_measure
    smg_measure.features(M)


CFG.measure = {"px_per_mm": __import__("smg_common").sheet_px_per_mm("LEFT"),
               "features": _features}

# ------------------------------------------------------------------------------------------------ form magfit (straight)
_mf = D["frames"]["mag"]
_mr = dims("mag_release")
_mag = dims("magazine_body")
CFG.magfit = {
    "path": "straight", "mag_parts": ("magazine", "magazine_follower", "magazine_floor_plate"), "catch": "mag_release",
    "catch_pivot_M": [_mr["pivot_XZ"][0], 0.0, _mr["pivot_XZ"][1]], "catch_axis": [0.0, 1.0, 0.0],
    "release_deg": float(_mr["release_rot_Y_deg"]), "mag_origin_M": _mf["Mag_in_M"],
    "mag_axes_M": {"x": _mf["x_axis_in_M"], "z": _mf["z_axis_in_M"]},
    "insert_mm": float(np.linalg.norm(np.array(SPEC.socket("MagInsertStart")["M_mm"]) - np.array(_mf["Mag_in_M"]))),
    "well_band": [0.0, float(_mag["top_along_axis"]) - 4.0], "lip_z": 0.0,
    "well_parts": ("lower_receiver",), "catch_zone_mm": 6.0,
    "half_thickness": float(_mag["thickness"]) / 2.0, "half_length": float(_mag["foreaft"]) / 2.0,
    "header": lambda S: {"stage": "form: magazine fit (straight insert, SMG_BUILD_PLAN 12.2 at form time)",
                         "spec": "smg_spec.json frames.mag, sockets Mag / MagInsertStart, mag_release dims"}}

CFG.viewgates = {}
CFG.g5_lods = {}
