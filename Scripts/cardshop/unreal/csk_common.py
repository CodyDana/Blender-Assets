"""Shared constants for the Card Shop Kit G1 Unreal steps (import / materials / map / verify). No ``unreal`` import here,
so it also loads in plain Python (make_project.py, tests).

Unreal frame: the pipeline's conversion (``pipeline.helpers.ue_socket_transform``): a Blender point (x, y, z) in metres
is (100 x, -100 y, 100 z) cm in Unreal, so the customer side of a fixture (Blender -Y) faces Unreal +Y. The G1 scripts
never re-derive this: grid slots come pre-converted in ``.csk.json`` (``slots_ue``), and sockets are read from the
imported meshes (recreated from the pipeline sidecars).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
G1 = ROOT / "Exports" / "CardShopKit" / "G1"
TEX = G1 / "Textures"
OUT = ROOT / "WorkFiles" / "cardshop" / "g1" / "unreal"       # step reports (JSON, committed)

PROJECT_DIR = Path(r"C:\Users\Cody\Documents\Unreal Projects\CardShopKit")
UPROJECT = PROJECT_DIR / "CardShopKit.uproject"

MESH_DEST = "/Game/CardShopKit/G1/Meshes"
TEX_DEST = "/Game/CardShopKit/G1/Textures"
MAT_DEST = "/Game/CardShopKit/G1/Materials"
LEVEL = "/Game/CardShopKit/G1/Maps/L_CSK_G1"
STRESS_LEVEL = "/Game/CardShopKit/G1/Maps/L_CSK_G1_Stress"
MANAGED_TAG = "CSK_G1"

MESHES = ["SM_CSK_Card_Std", "SM_CSK_TopLoader_35pt", "SM_CSK_Slab_Std", "SM_CSK_Slab_Std_Filled",
          "SM_CSK_Pack_Std_Sealed", "SM_CSK_Box_Booster_S", "SM_CSK_Box_Booster_S_Lid",
          "SM_CSK_Showcase_Full_1778", "SM_CSK_Showcase_Full_Glass_1778", "SM_CSK_Showcase_Full_Door_1778"]
SHOWCASE = "SM_CSK_Showcase_Full_1778"
TEXTURES = ["T_CSK_G1_Cards_BC", "T_CSK_G1_Packs_BC", "T_CSK_G1_Labels_BC", "T_CSK_G1_CardFront_BC",
            "T_CSK_G1_CardBack_BC", "T_CSK_G1_PackFront_BC", "T_CSK_G1_PackBack_BC", "T_CSK_G1_Label_BC",
            "T_CSK_G1_BoxDieline_BC"]

SEAT_TOL_CM = 0.1          # G1 test 2: seat error <= 1 mm
SOCKET_LIMIT = 40          # G1 test 2: <= 40 sockets on the showcase


def csk(name):
    return json.loads((G1 / f"{name}.csk.json").read_text(encoding="utf-8"))


def sidecar(name):
    p = G1 / f"{name}.sockets.json"
    return p if p.exists() else None


def atlas_index(tex_name):
    return json.loads((TEX / f"{tex_name}.json").read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")


def blender_mm_to_ue_cm(p):
    """A Blender-frame point in mm -> Unreal cm (the pipeline's mirror on Y)."""
    return [p[0] / 10.0, -p[1] / 10.0, p[2] / 10.0]
