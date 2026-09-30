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

G1_MESHES = ["SM_CSK_Card_Std", "SM_CSK_TopLoader_35pt", "SM_CSK_TopLoader_130pt", "SM_CSK_Slab_Std",
          "SM_CSK_Slab_Std_Filled", "SM_CSK_Pack_Std_Sealed", "SM_CSK_Box_Booster_S", "SM_CSK_Box_Booster_S_Lid",
          "SM_CSK_Box_Booster_S_Sealed",
          "SM_CSK_Showcase_Full_1778", "SM_CSK_Showcase_Full_Glass_1778", "SM_CSK_Showcase_Full_Door_1778"]
# The 12 families (csk_lib/fam_*.py, in geom.ALL_ITEMS order): imported, given materials and verified like G1.
FAMILY_MESHES = {
    "a_cases": ["SM_CSK_Showcase_Half_1219", "SM_CSK_Showcase_Half_Glass_1219", "SM_CSK_Showcase_Half_Door_1219",
        "SM_CSK_Showcase_Half_BayDoor_1219", "SM_CSK_Showcase_Half_1778", "SM_CSK_Showcase_Half_Glass_1778",
        "SM_CSK_Showcase_Half_Door_1778", "SM_CSK_Showcase_Half_BayDoor_1778", "SM_CSK_Showcase_Tower",
        "SM_CSK_Showcase_Tower_Glass", "SM_CSK_Showcase_Tower_Door", "SM_CSK_Showcase_Wall_1016",
        "SM_CSK_Showcase_Wall_Glass_1016", "SM_CSK_Showcase_Wall_Door_1016", "SM_CSK_Case_Counter_900",
        "SM_CSK_Case_Counter_Glass_900", "SM_CSK_Case_Counter_Lid_900", "SM_CSK_Case_WallSlab",
        "SM_CSK_Case_WallSlab_Door"],
    "a_display": ["SM_CSK_CardTable_08", "SM_CSK_CardTable_Lid_08", "SM_CSK_CardTable_10", "SM_CSK_CardTable_Lid_10",
        "SM_CSK_CardTable_12", "SM_CSK_CardTable_Lid_12", "SM_CSK_Easel_Slab", "SM_CSK_Easel_Card",
        "SM_CSK_Easel_Small", "SM_CSK_Riser_Slab_1", "SM_CSK_Riser_Slab_3", "SM_CSK_Stand_Card_1",
        "SM_CSK_Stand_Card_9", "SM_CSK_WallUnit_Oak"],
    "a_shelving": ["SM_CSK_Slatwall_1000x2400", "SM_CSK_Slatwall_2000x2400", "SM_CSK_Hook_Slat_102", "SM_CSK_Hook_Slat_203",
        "SM_CSK_Hook_Slat_305", "SM_CSK_Shelf_Slat_1000", "SM_CSK_Gondola_Single_1372", "SM_CSK_Gondola_Double_1372",
        "SM_CSK_Gondola_EndCap_1372", "SM_CSK_Gondola_Shelf_305", "SM_CSK_Gondola_Shelf_406",
        "SM_CSK_Gondola_Corner_1372", "SM_CSK_Rack_Wire_914", "SM_CSK_Shelf_BoxTier_1219"],
    "b_pack": ["SM_CSK_Pack_Std_Open", "SM_CSK_Pack_Std_Strip", "SM_CSK_Pack_Std_Wrapper", "SM_CSK_Box_Booster_L",
        "SM_CSK_Box_Booster_L_Lid", "SM_CSK_Box_Booster_L_Sealed", "SM_CSK_Box_Collector", "SM_CSK_Box_Collector_Lid",
        "SM_CSK_Deck_Tuck"],
    "b_ship": ["SM_CSK_Carton_Box6_Closed", "SM_CSK_Carton_Box6_Open", "SM_CSK_Carton_Box6_Flat", "SM_CSK_Box_Ship_S_Closed",
        "SM_CSK_Box_Ship_M_Closed", "SM_CSK_Box_Ship_L_Closed", "SM_CSK_Box_Ship_S_Open", "SM_CSK_Box_Ship_M_Open",
        "SM_CSK_Box_Ship_L_Open", "SM_CSK_Box_Ship_Flat", "SM_CSK_Blister_Pack"],
    "c_retail": ["SM_CSK_Card_Small", "SM_CSK_CardStack_10", "SM_CSK_CardStack_30", "SM_CSK_CardStack_90", "SM_CSK_Sleeve_Penny",
        "SM_CSK_Sleeve_Deck_Std", "SM_CSK_Sleeve_Deck_Small", "SM_CSK_TopLoader_35pt_Filled", "SM_CSK_Holder_SemiRigid",
        "SM_CSK_Holder_Magnetic", "SM_CSK_Holder_Magnetic_Front", "SM_CSK_Holder_Magnetic_Back",
        "SM_CSK_Holder_Magnetic_Filled", "SM_CSK_Retail_SleeveBox100", "SM_CSK_Retail_TopLoaderPack25",
        "SM_CSK_Retail_PennyPack100", "SM_CSK_Retail_DiceClam", "SM_CSK_Retail_BinderWrapped",
        "SM_CSK_Retail_PlaymatTube", "SM_CSK_Retail_DeckBoxPack", "SM_CSK_Retail_CleanerBottle"],
    "de_storage": ["SM_CSK_Slab_Thick", "SM_CSK_Box_GradeReturn", "SM_CSK_Box_GradeReturn_Lid", "SM_CSK_Box_Row_100",
        "SM_CSK_Box_Row_400", "SM_CSK_Box_Row_800", "SM_CSK_Box_Row_Lid_100", "SM_CSK_Box_Row_Lid_400",
        "SM_CSK_Box_Row_Lid_800", "SM_CSK_Box_Monster_3200", "SM_CSK_Box_Monster_5000", "SM_CSK_Box_Monster_Lid_3200",
        "SM_CSK_Box_Monster_Lid_5000"],
    "e_play": ["SM_CSK_Die_D6", "SM_CSK_Die_D20", "SM_CSK_Token_22", "SM_CSK_Playmat_Flat", "SM_CSK_Playmat_Rolled",
        "SM_CSK_DeckBox", "SM_CSK_DeckBox_Lid", "SM_CSK_Binder_Body", "SM_CSK_Binder_Cover", "SM_CSK_Binder_Page",
        "SM_CSK_Binder_Closed"],
    "fg_counter": ["SM_CSK_Table_Play_2", "SM_CSK_Table_Play_4", "SM_CSK_Table_Play_6", "SM_CSK_Chair_Folding",
        "SM_CSK_Chair_Folding_Folded", "SM_CSK_Counter_1397", "SM_CSK_Bag_Paper", "SM_CSK_Bag_Paper_Flat"],
    "g_devices": ["SM_CSK_CashDrawer", "SM_CSK_CashDrawer_Tray", "SM_CSK_Bills_Stack", "SM_CSK_Coin", "SM_CSK_Terminal_Card",
        "SM_CSK_Printer_Receipt", "SM_CSK_Printer_Receipt_Lid", "SM_CSK_POS_Screen", "SM_CSK_Scanner",
        "SM_CSK_Scanner_Cradle", "SM_CSK_PriceGun", "SM_CSK_Phone", "SM_CSK_Laptop", "SM_CSK_Laptop_Lid"],
    "h_backroom": ["SM_CSK_Rack_Warehouse_1829", "SM_CSK_Workbench_1524", "SM_CSK_Mailer_S", "SM_CSK_Mailer_L",
        "SM_CSK_Mailer_S_Open", "SM_CSK_Mailer_L_Open", "SM_CSK_TapeGun", "SM_CSK_TrashCan", "SM_CSK_TrashCan_Lid",
        "SM_CSK_TrashBag_Full", "SM_CSK_HandTruck"],
    "ij_shell": ["SM_CSK_Sign_OpenClosed", "SM_CSK_Sign_OpenClosed_Plate", "SM_CSK_PriceTag_Shelf", "SM_CSK_PriceTag_Tent",
        "SM_CSK_PriceTag_Hook", "SM_CSK_Poster_A2", "SM_CSK_Poster_A1", "SM_CSK_Sign_Storefront", "SM_CSK_Sign_Hanging",
        "SM_CSK_Shell_Wall_2000", "SM_CSK_Shell_Wall_Window_2000", "SM_CSK_Shell_Wall_Window_2000_Glass",
        "SM_CSK_Shell_Wall_Door_2000", "SM_CSK_Shell_Floor_2000", "SM_CSK_Shell_Ceiling_2000", "SM_CSK_Door_Entry",
        "SM_CSK_Door_Entry_Frame", "SM_CSK_Light_Panel600", "SM_CSK_Light_Track2000", "SM_CSK_Light_TrackHead",
        "SM_CSK_Light_TrackHead_Spot", "SM_CSK_Light_Pendant"],
}
MESHES = G1_MESHES + [n for names in FAMILY_MESHES.values() for n in names]
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
