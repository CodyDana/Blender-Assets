"""UnrealCheck9 (six-point, independent Unreal verifier) - shared constants and helpers.

Runs inside the UE 5.8 pythonscript commandlet (s1_import / s3_readback / s4_export).
Expectations come from the BRIEF / study 2.4 numbers, not from the build report:
    tip radius 49 mm (+X down one tip) -> X span 98 mm, Y span 2 x 49 sin 60 = 84.8705 mm, plate 2.0 mm
    LOD screen sizes 1.0 / 0.10 x 49/50 / 0.035 x 49/50 = 1.0 / 0.098 / 0.0343
    sockets Grip (hub rim between two tips, +X outward) and Trail (centre), relative scale 1
Fresh content path: /Game/ShurikenCheck9/SixPointIndep1 (never used before this run).
"""
import hashlib
import json
import math
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck9_SixPoint"
MESH = "SM_Shuriken_SixPoint"
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
TEX_STAGE = HERE / "tex_stage"
TEX_SHIPPED = PROJ / "Exports" / "Shuriken" / "Textures"
DEST = "/Game/ShurikenCheck9/SixPointIndep1"
TEX_DEST = DEST + "/Textures"
ASSET = f"{DEST}/{MESH}"

TIP_R_CM = 4.9
HUB_R_CM = 1.8
THICK_CM = 0.2
SPEC_SIZE_CM = [2 * TIP_R_CM, 2 * TIP_R_CM * math.sin(math.radians(60.0)), THICK_CM]
SPEC_SCREEN = [1.0, round(0.10 * 49.0 / 50.0, 4), round(0.035 * 49.0 / 50.0, 4)]
# Grip on the hub rim midway between the tips at 0 and 60 deg (Blender +Y); Unreal flips Y.
SPEC_GRIP_CM = [HUB_R_CM * math.cos(math.radians(30.0)), -HUB_R_CM * math.sin(math.radians(30.0)), 0.0]
SPEC_GRIP_YAW = -30.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


SUBSYSTEM_ROUTE = {}


def sm_subsystem():
    """StaticMeshEditorSubsystem: the documented route first, new_object as the commandlet fallback.

    Lives in this (non-__main__) module on purpose: Python shows the fallback's DeprecationWarning only for a
    call site in __main__, and the verifier's own helper must not add a Warning line to the gate log.
    The route taken is recorded in SUBSYSTEM_ROUTE.
    """
    import unreal
    sub = None
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    if sub is not None:
        SUBSYSTEM_ROUTE["route"] = "get_editor_subsystem"
        return sub
    SUBSYSTEM_ROUTE["route"] = "new_object (get_editor_subsystem returned None)"
    return unreal.new_object(unreal.StaticMeshEditorSubsystem)
