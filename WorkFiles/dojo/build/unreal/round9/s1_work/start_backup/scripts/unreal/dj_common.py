"""Shared constants and conversions for the DojoLab Unreal assembly (grey-box stage).

Imported by the Unreal-side scripts (dj_import / dj_materials / dj_level / dj_verify / dj_capture / dj_gasp_*) and by the
plain-Python helpers. Nothing here imports `unreal`, so it can be checked outside the engine.

Frame (DOJO_ARENA_SPEC section 1, layout.json): metres, origin = the inside south-west corner of the compound at courtyard
level, X east (0-44), Y north (0-36), Z up. Unreal: centimetres, left-handed, the armory mapping:
    UE location = (x*100, -y*100, z*100),  UE yaw = -rot_z (degrees).
"""
import json
import math
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BUILD = ROOT / "WorkFiles" / "dojo" / "build"
LAYOUT = BUILD / "layout.json"
EXPORTS = ROOT / "Exports" / "DojoKit"
OUT = BUILD / "unreal"
CAPTURES = OUT / "captures"
BLENDER_BOUNDS = OUT / "blender_bounds.json"
BLEND = ROOT / "Assets" / "Dojo" / "DojoGreybox.blend"

SOURCE_DIR = Path(r"C:\Users\Cody\Documents\Unreal Projects\GameAnimationSample")   # READ-ONLY copy source
PROJECT_DIR = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab")
UPROJECT = PROJECT_DIR / "DojoLab.uproject"

MESH_DEST = "/Game/DojoKit/Greybox/Meshes"
MAT_DEST = "/Game/DojoKit/Greybox/Materials"
LEVEL = "/Game/Dojo/Maps/L_Dojo"
MANAGED_TAG = "DJ_Managed"     # every actor dj_level spawns; a re-run destroys exactly these and nothing else
MESH_PREFIX = "SM_DGB_"

# GASP (copied into DojoLab from the sample, never edited in place)
GASP_GAME_MODE = "/Game/Blueprints/GM_Sandbox"
GASP_CHARACTER = "/Game/Blueprints/SandboxCharacter_CMC"
TRAVERSABLE_BLOCK = "/Game/Levels/LevelPrototyping/LevelBlock_Traversable"
DOJO_GAME_MODE = "/Game/Dojo/Blueprints/GM_Dojo"   # child of GM_Sandbox whose default pawn is SandboxCharacter_CMC
TRAVERSAL_PROFILE = "TraversalObjectPreset"         # GASP's collision profile: WorldDynamic, blocks the Traversable channel


def loc_cm(v):
    x, y, z = v
    return (x * 100.0, -y * 100.0, z * 100.0)


def yaw_deg(rot_z):
    return -float(rot_z)


def bbox_bl_to_ue(bmin, bmax):
    """Blender AABB (m) -> Unreal AABB (cm): Y flips, so min/max swap on Y."""
    return ([bmin[0] * 100.0, -bmax[1] * 100.0, bmin[2] * 100.0],
            [bmax[0] * 100.0, -bmin[1] * 100.0, bmax[2] * 100.0])


def dir_bl_to_ue(d):
    return (d[0], -d[1], d[2])


def pitch_yaw_of(d):
    x, y, z = d
    n = math.sqrt(x * x + y * y + z * z)
    return math.degrees(math.asin(z / n)), math.degrees(math.atan2(y, x))


def hfov_deg(lens_mm, sensor_mm=36.0):
    return math.degrees(2.0 * math.atan(sensor_mm / 2.0 / lens_mm))


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5))


def kelvin_rgb(k):
    """Tanner Helland's blackbody fit (as the armory uses it)."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def folder_of(inst):
    """Outliner folder of a layout.json instance (the Blender build writes it per instance)."""
    return "Dojo/" + inst.get("folder", "Misc")


def n_meshes():
    return len(list(EXPORTS.glob(MESH_PREFIX + "*.fbx")))


def load_layout():
    return json.loads(LAYOUT.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
