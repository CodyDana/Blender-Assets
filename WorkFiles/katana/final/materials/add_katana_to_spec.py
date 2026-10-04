"""Finaliser (katana-wf, under the materials lock): add the basic katana + saya to Scripts/unreal/materials/material_spec.json
(additions only: 2 items, 10 instances, the Katana recolour group, changes_v8_katana). Idempotent: refuses if Katana
entries already exist. Writes a 'without katana' projection check: removing the added keys gives back the file it read.
    py -3 -B WorkFiles/katana/final/materials/add_katana_to_spec.py
"""
import copy
import json
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SPEC = ROOT / "Scripts/unreal/materials/material_spec.json"
raw = SPEC.read_text(encoding="utf-8")
d = json.loads(raw)
before = copy.deepcopy(d)
if any(i["item"].startswith("Katana") for i in d["items"]):
    raise SystemExit("Katana items already present")

T = "Exports/Katana/Textures"
GEN = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"


def steel_slot(index, slot, part, inst, stem, note, size=(2048, 2048)):
    return {"index": index, "slot_name": slot, "part": part, "instance": inst, "master": "M_Steel_Master",
            "recolourable": False,
            "textures": {"Base Colour Map": f"{T}/{stem}_BC.png", "ORM Map": f"{T}/{stem}_ORM.png",
                         "Normal Map": f"{T}/{stem}_N.png"},
            "texture_kinds": {"Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
            "orm_texture_settings": {"composite_texture": f"{stem}_N",
                                     "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
            "size": list(size), "params": {},
            "look_contract": {"BaseColor": f"{stem}_BC (sRGB) x Steel Tint (white = as shipped)", "Metallic": "ORM.B",
                              "Roughness": "ORM.G", "AO": "ORM.R", "Normal": f"{stem}_N (DirectX)"},
            "note": note, "base_instance": inst + "_Base"}


def fabric_slot(index, slot, part, inst, stem, detail, mfo, contract, note, uv_tile=None):
    s = {"index": index, "slot_name": slot, "part": part, "instance": inst, "master": "M_Fabric_Master",
         "recolourable": True, "tint_ready_shipped": True,
         "textures": {"Detail Map": f"{T}/Recolour/{detail}.png (NEW: 16-bit linear tint-ready detail, "
                                    "Scripts/Katana/katana_recolour.py)",
                      "Base Colour Map": f"{T}/{stem}_BC.png", "ORM Map": f"{T}/{stem}_ORM.png",
                      "Normal Map": f"{T}/{stem}_N.png"},
         "texture_kinds": {"Detail Map": "Detail16", "Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
         "orm_texture_settings": {"composite_texture": f"{stem}_N",
                                  "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
         "size": {"BC": 2048, "Detail": 1024, "ORM": 2048, "N": 2048},
         "params": {"Colour": GEN, "Detail Bias": GEN, "Detail Scale": GEN, "Detail Mean": GEN,
                    "Detail Highlight Ratio": GEN, "Detail Moments Low": GEN, "Detail Moments High": GEN,
                    "Specular Strength": 0.5, "Specular From ORM Alpha": False, "Cloth Sheen": False,
                    "Use Lettering": False, "Metal From ORM": mfo},
         "look_contract": contract, "note": note, "base_instance": inst + "_Base"}
    if uv_tile:
        s["uv_tile"] = uv_tile
    return s


katana = {"item": "Katana", "mesh": "SM_Katana", "fbx": "Exports/Katana/SM_Katana.fbx",
          "sidecar": "Exports/Katana/SM_Katana.sockets.json",
          "note": "ADDED 2026-10-03 (the katana finalise pass). The basic uchigatana: blade + fittings share the 2048 steel "
                  "atlas, the grip (ito over same) has its own 2048 atlas in UV0 tile u 1..2.",
          "slots": [
              steel_slot(0, "M_Katana_Blade", "Blade", "MI_Katana_Blade", "T_Katana_Steel",
                         "the blade (polished ji, burnished shinogi-ji and mune, frosted hamon) and the blackened iron "
                         "tsuba, fuchi and kashira (their colour is in BC; Steel Tint multiplies)"),
              steel_slot(1, "M_Katana_Fittings", "Fittings", "MI_Katana_Fittings", "T_Katana_Steel",
                         "habaki, seppa, menuki, kashira eyelets (brass) and the bamboo mekugi (metallic 0 from ORM); "
                         "Steel Tint recolours the brass"),
              fabric_slot(2, "M_Katana_Grip", "Grip", "MI_Katana_Grip", "T_Katana_Grip", "T_Katana_Grip_Detail16",
                          True,
                          {"BaseColor": "lerp(saturate(Colour x (Detail Bias + Detail Scale x Detail)), BC, "
                                        "max(ORM.B, saturate((lum(BC) - 0.2) x 5))): the black ito recolours, the "
                                        "ivory same keeps its baked colour",
                           "Metallic": "ORM.B (0: Metal From ORM on only for the keep ramp)", "Roughness": "ORM.G",
                           "AO": "ORM.R", "Normal": "T_Katana_Grip_N (DirectX)"},
                          "the ito (cord) wrap, the same (ray skin) in the diamond windows and the LOD2 tsuka shell; "
                          "default Colour = the black ito",
                          uv_tile="u 1..2 (Wrap addressing reads the same texels)")]}
saya = {"item": "Katana_Saya", "mesh": "SM_Katana_Saya", "fbx": "Exports/Katana/SM_Katana_Saya.fbx",
        "sidecar": "Exports/Katana/SM_Katana_Saya.sockets.json",
        "note": "ADDED 2026-10-03 (the katana finalise pass). The katana's saya: both slots sample the one 2048 atlas; the "
                "lacquer is recolourable, the horn + brass fittings take Steel Tint.",
        "slots": [
            fabric_slot(0, "M_Katana_Saya_Lacquer", "Lacquer", "MI_Katana_Saya_Lacquer", "T_Katana_Saya",
                        "T_Katana_Saya_Lacquer_Detail16", False,
                        {"BaseColor": "saturate(Colour x (Detail Bias + Detail Scale x Detail)) (v2 MF_TintDetail): "
                                      "the black roiro lacquer and its wear recolour",
                         "Metallic": "0 (Metal From ORM off)", "Roughness": "ORM.G", "AO": "ORM.R",
                         "Normal": "T_Katana_Saya_N (DirectX)"},
                        "the black gloss roiro lacquer body (subtle wear in roughness / colour) and the cavity"),
            steel_slot(1, "M_Katana_Saya_Fittings", "Fittings", "MI_Katana_Saya_Fittings", "T_Katana_Saya",
                       "black horn koiguchi, kurikata and kojiri (metallic 0 from ORM) and the brass shitodome; Steel "
                       "Tint multiplies")]}
d["items"] += [katana, saya]
for it in (katana, saya):
    for s in it["slots"]:
        parent = s["master"]
        d["instances"].append({"name": s["base_instance"], "parent": parent, "folder": "Base",
                               "role": "holds every texture and matched setting of the part"})
        d["instances"].append({"name": s["instance"], "parent": s["base_instance"],
                               "role": "buyer-facing: overrides only the colour(s)"})
d["build"]["recolour_maps"]["Katana"] = "Exports/Katana/Textures/Recolour/recolour_maps.json"
d["build"]["recolour_constants"]["Katana"] = "Exports/Katana/Textures/Recolour/recolour_constants.json"
d["changes_v8_katana"] = {
    "date": "2026-10-03",
    "what": "The basic katana (SM_Katana) and its saya (SM_Katana_Saya) join the pack (additions only): 10 instances "
            "(MI_Katana_Blade / _Fittings and MI_Katana_Saya_Fittings on M_Steel_Master, MI_Katana_Grip on "
            "M_Fabric_Master with Metal From ORM on, MI_Katana_Saya_Lacquer on M_Fabric_Master, each with its _Base); "
            "group Katana's recolour maps (written by Scripts/Katana/katana_recolour.py) and constants "
            "(maps/derive_constants_katana.py).",
    "masters": "unchanged",
    "code": "one new script maps/derive_constants_katana.py (a copy of the senbon's with the katana's group, maps and "
            "paths); nothing else in the code changed"}
SPEC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")
# additions-only proof: drop the added keys and compare with what was read
chk = json.loads(SPEC.read_text(encoding="utf-8"))
chk["items"] = [i for i in chk["items"] if not i["item"].startswith("Katana")]
chk["instances"] = [i for i in chk["instances"] if not i["name"].startswith("MI_Katana")]
del chk["build"]["recolour_maps"]["Katana"], chk["build"]["recolour_constants"]["Katana"], chk["changes_v8_katana"]
print("ADDITIONS_ONLY", chk == before, "items", len(d["items"]), "instances", len(d["instances"]))
