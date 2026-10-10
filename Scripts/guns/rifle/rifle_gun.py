"""AR-01 config for the gun-agnostic gate drivers (gunlib 0.2.0, gunlib.gunconf). Everything the AR-01's rifle_b3 /
rifle_b4 / rifle_b6a / rifle_measure / rifle_magfit_check / rifle_viewgates / rifle_g5_lods / rifle_rig_verify /
rifle_mag_fit scripts had hard-wired lives here; those scripts are now thin shims that call gunlib.drivers with CFG.

The AR-01 regression (WorkFiles/guns/smg/gates/gunlib_regression.json) proves the promoted drivers reproduce the
committed stage-2/4/5(/6) gate values with this config.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from rifle_common import CONTACT_PAIRS, SPEC_PATH, WORK  # noqa: E402

import numpy as np  # noqa: E402

from gunlib.gunconf import GunConfig  # noqa: E402

CFG = GunConfig("AR01", WORK, SPEC_PATH, log_tag="AR01")


# ------------------------------------------------------------------------------------------------ B3
def b3_groups(G, rec, cfg):
    def B(p):
        return np.asarray(p, float) - cfg.grip
    return {
        # (stage-7: the gas piston rides with the carrier, bone 'bolt')
        "bolt": {"parts": [n for n in ("bolt_carrier", "gas_piston") if n in G], "kind": "slide", "axis": [-1, 0, 0],
                 "range": [0.0, rec["bolt_carrier"]["joint"]["travel_mm"]], "row": "sliding"},
        "trigger": {"parts": ["trigger"], "kind": "rot", "pivot": B([318.0, 0, -20.0]), "axis": [0, 1, 0],
                    "range": [0.0, 12.0], "row": "hinge"},
        "selector": {"parts": ["selector"], "kind": "rot", "pivot": B([282.8, 0, -7.8]), "axis": [0, 1, 0],
                     "range": [0.0, 32.0], "row": "hinge"},
        "mag_release": {"parts": ["mag_catch"], "kind": "rot", "pivot": B([362.0, 0, -50.0]), "axis": [0, -1, 0],
                        "range": [0.0, 10.0], "row": "hinge"},
        "sight_rear": {"parts": ["rear_sight_leaf", "rear_sight_slider"], "kind": "rot", "pivot": B([504.0, 0, 41.0]),
                       "axis": [0, 1, 0], "range": [0.0, 6.0], "row": "hinge"},
    }


CFG.b3 = {"groups": b3_groups, "contact_pairs": CONTACT_PAIRS,
          "rows": {"sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "butt": [0.01, 0.05]}}

# ------------------------------------------------------------------------------------------------ B4 (notch sight)
CFG.b4 = {"kind": "notch", "socket": "Sight", "rear": ["rear_sight_leaf", "rear_sight_slider", "rear_sight_block"],
          "post": "front_sight_post", "ignore": ["front_sight_block"], "tol_mm": 0.2, "min_post_mm": 1.0,
          "img": CFG.review / "realism_form4" / "b4_sight_picture.png"}

# ------------------------------------------------------------------------------------------------ B6a
CFG.b6a = {"check_name": "SM_AR01_B6aCheck"}


# ------------------------------------------------------------------------------------------------ measure (L3 / L4)
def _features(M):
    import rifle_gun_measure
    rifle_gun_measure.features(M)


CFG.measure = {"px_per_mm": 0.822479, "features": _features}


# ------------------------------------------------------------------------------------------------ form magfit (rock)
def _magfit_header(S):
    import rifle_gun_magfit
    return rifle_gun_magfit.form_header(S)


def _magfit_gates(S):
    import rifle_gun_magfit
    return rifle_gun_magfit.form_gates(S)


CFG.magfit = {"path": "rock", "mag_parts": ("magazine", "magazine_floor_plate"), "catch": "mag_catch",
              "header": _magfit_header, "gates": _magfit_gates}

# ------------------------------------------------------------------------------------------------ stage-4 view gates
CFG.viewgates = {"radius": lambda rep: rep["bounds_radius_m"]["twin_with_mag_box_half_diagonal"],
                 "start_sizes": [1.0, 0.30, 0.12, 0.04],
                 "s2_requires": ["front_sight_post", "rear_sight_leaf"],
                 "s2_method": "rifle_b4 (occlusion-aware; post tip vs the notch TOP line, R48)",
                 "s2_notch_bottom_info": True, "notch_bottom_rear": ["rear_sight_leaf", "rear_sight_slider"]}

CFG.g5_lods = {}


# ------------------------------------------------------------------------------------------------ stage-5 rig verify
def _clips(rep):
    import rifle_clips as CL
    CL.configure(rep["motion"]["bolt_travel_mm"], rep["motion"]["rock_deg"], rep["motion"]["insert_mm"])
    return CL.all_clips(), CL.basis_from, CL.loop_rest       # stage-7: the selector held at AUTO is allowed


CFG.rig_verify = {
    "stage": "5 Rig + export rifle", "noun": "rifle", "clips": _clips, "clip_table_name": "rifle_clips",
    "bore_z_B": 78.544, "ucx_count": 7,
    "b3_coverage_text": "bolt 0..103.25 mm, trigger 0..12, selector 0..32, catch 0..10, leaf 0..6 deg (the ranges B3 swept "
                        "with 0 intersections: gates/form.json LOD0, gates/game.json LOD1)",
    "bounds_note": "LOD0-3 posed vs LOD0's bind box (Unreal's stored bounds); the extension covers what leaves it "
                   "(stage 8: LOD2 is 2.8 mm wider on the left); U5 re-checks in engine",
    "qa_budget_text": "pass (budget 57,000 = 50,000 rifle + 7,000 merged mag; UV1; UCX keyed to the node; texel = measured "
                      "aggregate +-25 %)"}


# ------------------------------------------------------------------------------------------------ stage-6 mag fit
def _fit_gates(F, out):
    import rifle_gun_magfit
    return rifle_gun_magfit.stage6_gates(F, out)


CFG.mag_fit = {"noun": "rifle", "gates": _fit_gates, "switch_m": {1: 2.705, 2: 6.762, 3: 20.287},
               "well_box_M": {"X": (368.8, 432.0), "Y": (-20.75, 20.75), "Z": (-30.85, 11.0)},
               "geom": CFG.scratch / "mag" / "fit_geom.npz"}
