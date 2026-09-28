"""Add the flashbang to Scripts/unreal/materials/material_spec.json (additions only).  Run ONLY while holding the
materials lock as flashbang-chat.  Idempotent: refuses if a Flashbang item already exists."""
import json
import sys
from pathlib import Path

SPEC = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/material_spec.json")
s = json.loads(SPEC.read_text(encoding="utf-8"))
if any(i["item"].startswith("Flashbang") for i in s["items"]):
    sys.exit("Flashbang already in the spec")

T = "Exports/Flashbang/Textures"
GEN = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"


def paint_slot():
    return {
        "index": 0, "slot_name": "M_Flashbang_Paint", "part": "Paint", "instance": "MI_Flashbang_Paint",
        "master": "M_Fabric_Master", "recolourable": True, "tint_ready_shipped": True,
        "textures": {
            "Detail Map": f"{T}/Recolour/T_Flashbang_Paint_Detail16.png (NEW: 16-bit linear tint-ready detail of the paint, Scripts/props/build_flashbang.py stage textures)",
            "Base Colour Map": f"{T}/T_Flashbang_BC.png",
            "ORM Map": f"{T}/T_Flashbang_ORM.png",
            "Normal Map": f"{T}/T_Flashbang_N.png"},
        "texture_kinds": {"Detail Map": "Detail16", "Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
        "orm_texture_settings": {"composite_texture": "T_Flashbang_N",
                                 "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
        "size": {"BC": 2048, "Detail": 2048, "ORM": 2048, "N": 2048},
        "params": {"Colour": GEN, "Detail Bias": GEN, "Detail Scale": GEN, "Detail Mean": GEN,
                   "Detail Highlight Ratio": GEN, "Detail Moments Low": GEN, "Detail Moments High": GEN,
                   "Specular Strength": 0.5, "Specular From ORM Alpha": False, "Cloth Sheen": False,
                   "Use Lettering": False, "Metal From ORM": True},
        "look_contract": {
            "BaseColor": "lerp(saturate(Colour x (Detail Bias + Detail Scale x Detail)), BC, max(ORM.B, saturate((lum(BC) - 0.2) x 5))): the olive paint recolours; chips, scratches and hole walls (ORM.B = 1) keep the baked colour",
            "Metallic": "ORM.B (Metal From ORM on)", "Roughness": "ORM.G", "AO": "ORM.R",
            "Normal": "T_Flashbang_N (DirectX)"},
        "note": "the painted canister (body, sleeve) and its hole walls; default Colour = the reference olive (the paint's mean albedo)",
        "base_instance": "MI_Flashbang_Paint_Base"}


def steel_slot(index):
    return {
        "index": index, "slot_name": "M_Flashbang_Steel", "part": "Steel", "instance": "MI_Flashbang_Steel",
        "master": "M_Steel_Master", "recolourable": False,
        "textures": {"Base Colour Map": f"{T}/T_Flashbang_BC.png", "ORM Map": f"{T}/T_Flashbang_ORM.png",
                     "Normal Map": f"{T}/T_Flashbang_N.png"},
        "texture_kinds": {"Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
        "orm_texture_settings": {"composite_texture": "T_Flashbang_N",
                                 "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
        "size": [2048, 2048], "params": {},
        "look_contract": {"BaseColor": "T_Flashbang_BC (sRGB) x Steel Tint (white = as shipped)", "Metallic": "ORM.B",
                          "Roughness": "ORM.G", "AO": "ORM.R", "Normal": "T_Flashbang_N (DirectX)"},
        "note": "the base cap, collar, fuze head, lever, pull ring and pin, and the brass cans (their colour is in BC)",
        "base_instance": "MI_Flashbang_Steel_Base"}


NOTE = ("ADDED 2026-09-27 (the flashbang's finalise pass). Four static meshes split from the same geometry share ONE "
        "atlas and the SAME two instances: MI_Flashbang_Paint (M_Fabric_Master, Metal From ORM, recolourable) and "
        "MI_Flashbang_Steel (M_Steel_Master).")
items = [
    {"item": "Flashbang", "mesh": "SM_Flashbang", "fbx": "Exports/Flashbang/SM_Flashbang.fbx",
     "sidecar": "Exports/Flashbang/SM_Flashbang.sockets.json", "note": NOTE + " The assembled grenade.",
     "slots": [paint_slot(), steel_slot(1)]},
    {"item": "Flashbang_Body", "mesh": "SM_Flashbang_Body", "fbx": "Exports/Flashbang/SM_Flashbang_Body.fbx",
     "sidecar": "Exports/Flashbang/SM_Flashbang_Body.sockets.json",
     "note": "The held body without ring and lever (and the spent canister); the same instances as SM_Flashbang.",
     "slots": [paint_slot(), steel_slot(1)]},
    {"item": "Flashbang_PullRing", "mesh": "SM_Flashbang_PullRing", "fbx": "Exports/Flashbang/SM_Flashbang_PullRing.fbx",
     "sidecar": "Exports/Flashbang/SM_Flashbang_PullRing.sockets.json",
     "note": "The pull ring + pin, pivot at the Pin socket frame; steel only.", "slots": [steel_slot(0)]},
    {"item": "Flashbang_Lever", "mesh": "SM_Flashbang_Lever", "fbx": "Exports/Flashbang/SM_Flashbang_Lever.fbx",
     "sidecar": "Exports/Flashbang/SM_Flashbang_Lever.sockets.json",
     "note": "The spoon lever, pivot at the LeverHinge socket frame; steel only.", "slots": [steel_slot(0)]},
]
s["items"].extend(items)
s["build"]["recolour_maps"]["Flashbang"] = f"{T}/Recolour/recolour_maps.json"
s["build"]["recolour_constants"]["Flashbang"] = f"{T}/Recolour/recolour_constants.json"
s["changes_v6_flashbang"] = {
    "date": "2026-09-27",
    "what": ("The flashbang (SM_Flashbang + _Body, _PullRing, _Lever) joins the pack (additions only): 4 instances "
             "(MI_Flashbang_Paint on M_Fabric_Master with Metal From ORM, MI_Flashbang_Steel on M_Steel_Master, each "
             "with its _Base) shared by the four meshes; group Flashbang's recolour maps (written by "
             "Scripts/props/build_flashbang.py) and constants (maps/derive_constants_flashbang.py)."),
    "masters": "unchanged",
    "code": ("none: one new script maps/derive_constants_flashbang.py (a copy of the heels' with the flashbang's "
             "group and paths); four mesh entries share the two slot instances (np_spec resolves each instance once)")}
SPEC.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("material_spec.json: flashbang added")
