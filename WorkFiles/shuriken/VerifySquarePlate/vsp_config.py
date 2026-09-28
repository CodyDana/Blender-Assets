"""Independent import verification of one shuriken form (verifier, not the build agent).

Parameterized version of the UnrealCheck6 gates. Everything the gates EXPECT is derived here from the
study (SHURIKEN_STUDY.md 2.x + 4) and ASSET_GUIDELINES 6.5, never from the build report or the
sidecar, so a build whose report and sidecar agree with each other but not with the spec cannot pass.
The comparison with the sidecar/report is done separately (it must ALSO agree).

Plain Python: imported by the Blender scripts, the Unreal commandlet passes and summarize.py.
Form and content path come from the environment (VSP_FORM, VSP_DEST) so nothing is copied per form.
The content path is deliberately NOT the build agent's /Game/ShurikenCheck6/Verify.
"""
import hashlib
import math
import os
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "VerifySquarePlate"
UPROJECT = PROJ / "WorkFiles" / "shuriken" / "UnrealShuriken" / "ShurikenValidation.uproject"
BUILD_AGENT_DEST = "/Game/ShurikenCheck6/Verify"

FORM = os.environ.get("VSP_FORM", "square_plate")
DEST = os.environ.get("VSP_DEST", "/Game/ShurikenVerifyIndep/SquarePlate")
assert DEST.rstrip("/") != BUILD_AGENT_DEST, "independent verifier must not reuse the build agent's content path"

# study 4 (amended 2026-09-17): 1.0 / 0.10 / 0.035 for a star of bounding radius ~50 mm, S = 1.778 R / d
PACK_SCREEN_SIZES = (1.0, 0.10, 0.035)
PACK_REFERENCE_RADIUS_MM = 50.0
SCREEN_MULTIPLE = 16.0 / 9.0          # 2 * 0.5 * ProjMatrix[1][1] at 90 deg hFOV, 16:9


def _override():
    """Negative control only: VSP_SPEC_OVERRIDE='{"side_mm": 76.0}' perturbs the spec so the gates must fail."""
    import json
    raw = os.environ.get("VSP_SPEC_OVERRIDE", "")
    return json.loads(raw) if raw else {}


def _square_plate():
    o = _override()
    side = o.get("side_mm", 76.2)      # study 2.3: [17] 3 in closest tips; build to the 76.2 mm square
    thick = o.get("thickness_mm", 1.9)  # study 2.3: 1.9 mm SOURCED
    sagitta = o.get("sagitta_mm", 6.0)  # study 2.3: ESTIMATE
    corner_r = side / math.sqrt(2.0)   # corners on +-X, +-Y
    grip_r = side / 2.0 - sagitta      # midpoint of a concave side, on the rim (chord midpoint minus sagitta)
    return {
        "mesh": "SM_Shuriken_SquarePlate",
        "study_section": "2.3",
        "side_mm": side,
        "thickness_mm": thick,
        "sagitta_mm": sagitta,
        "hole_mm": 12.7,
        "bounding_radius_mm": corner_r,
        "corner_to_corner_mm": 2.0 * corner_r,
        "corner_to_corner_study_rounded_mm": 108.0,
        "size_cm": [2.0 * corner_r / 10.0, 2.0 * corner_r / 10.0, thick / 10.0],
        "grip": {"radius_cm": grip_r / 10.0, "azimuths_deg": [45.0, 135.0, -135.0, -45.0], "z_cm": 0.0,
                 "note": "midpoint of any one concave side, on the rim; +X outward along the azimuth"},
        "trail": {"location_cm": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0], "note": "centre, +Z spin axis"},
        "physics_mass_kg": 0.06,
        "spec_override_negative_control": o or None,
    }


FORM_SPECS = {"square_plate": _square_plate}


def spec(form=FORM):
    s = FORM_SPECS[form]()
    r = s["bounding_radius_mm"]
    s["screen_sizes"] = [1.0] + [round(v * r / PACK_REFERENCE_RADIUS_MM, 4) for v in PACK_SCREEN_SIZES[1:]]
    s["pack_switch_distance_cm"] = [None] + [round(SCREEN_MULTIPLE * (PACK_REFERENCE_RADIUS_MM / 10.0) / v, 2)
                                            for v in PACK_SCREEN_SIZES[1:]]
    s["fbx"] = PROJ / "Exports" / "Shuriken" / f"{s['mesh']}.fbx"
    s["sidecar"] = PROJ / "Exports" / "Shuriken" / f"{s['mesh']}.sockets.json"
    s["asset"] = f"{DEST}/{s['mesh']}"
    s["lod_node"] = [f"{s['mesh']}_LOD{i}" for i in range(3)]
    s["ucx_node"] = f"UCX_{s['mesh']}_LOD0_00"          # ASSET_GUIDELINES 6.2: keyed to the LOD0 NODE name
    return s


TOL = {
    "size_cm": 1e-3,
    "socket_cm": 1e-3,
    "socket_deg": 1e-3,
    "screen_size": 1e-6,
    "roundtrip_position_cm": 1e-6,     # ASSET_GUIDELINES 6.5: positions round-trip within 1e-6 cm
    "hull_outside_cm": 1e-6,           # "LOD0 0.0 cm outside"
    "switch_distance_cm": 1.0,
}

LOG_PATTERN = r":\s*(Warning|Error)\s*:"      # same regex as UnrealCheck6 run_pass.ps1 / attach_engine_check


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
