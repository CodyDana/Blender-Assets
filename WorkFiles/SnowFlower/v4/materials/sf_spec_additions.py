"""The Snow Flower sword + sheath entries of the pack's material spec (Scripts/unreal/materials/material_spec.json).

    py -3 WorkFiles/SnowFlower/v4/materials/sf_spec_additions.py apply        add them to the live spec (additions only;
                                                                             refuses if any Snow Flower entry exists)
    py -3 WorkFiles/SnowFlower/v4/materials/sf_spec_additions.py trial <out>  write a derived TRIAL spec: the three masters,
                                                                             the functions and ONLY the Snow Flower items,
                                                                             every /Game/NinjaPack path moved to /Game/SFMatTrial

Additions (2026-09-26, the Snow Flower final pass):
    items      SnowFlower (SM_SnowFlower: Blade / Fittings on M_Steel_Master, Grip on M_Fabric_Master, recolourable) and
               SnowFlower_Sheath (SM_SnowFlower_Sheath: Lacquer on M_Fabric_Master with Metal From ORM ON, recolourable;
               Fittings on M_Steel_Master)
    instances  MI_<Item>_<Part>_Base + MI_<Item>_<Part> for the five slots (10)
    master     M_Fabric_Master gains the static switch 'Metal From ORM' (default OFF: every existing instance compiles the
               graph it had).  Why not a new master: the lacquer IS the fabric master's job (a tintable dielectric with a
               detail map, like the fan's lacquered ribs); only the ~3.6 % of its texels that carry baked silver ornament
               need the baked colour + metal, which one default-off switch gives without a second 30-node graph to keep
               in step.
    build      recolour_maps / recolour_constants for group SnowFlower; the two shipped sRGB Detail PNGs not imported
               (the pack samples the lossless Recolour/*_Detail16)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
SPEC = PROJECT / "Scripts" / "unreal" / "materials" / "material_spec.json"
EXP = "Exports/SnowFlower/v4"
TEX = f"{EXP}/Textures"
REC = f"{TEX}/Recolour"
GEN = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"
GEN_KEYS = ["Colour", "Detail Bias", "Detail Scale", "Detail Mean", "Detail Highlight Ratio", "Detail Moments Low",
            "Detail Moments High"]


def steel_slot(index, slot_name, part, inst, stem, note):
    return {"index": index, "slot_name": slot_name, "part": part, "instance": inst, "master": "M_Steel_Master",
            "recolourable": False,
            "textures": {"Base Colour Map": f"{TEX}/{stem}_BC.png", "ORM Map": f"{TEX}/{stem}_ORM.png",
                         "Normal Map": f"{TEX}/{stem}_N.png"},
            "texture_kinds": {"Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
            "orm_texture_settings": {"composite_texture": f"{stem}_N", "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN",
                                     "composite_power": 1.0},
            "size": [4096, 4096], "params": {},
            "look_contract": {"BaseColor": f"{stem}_BC (sRGB) x Steel Tint (white = as shipped)", "Metallic": "ORM.B",
                              "Roughness": "ORM.G", "AO": "ORM.R", "Normal": f"{stem}_N (DirectX)"},
            "note": note, "base_instance": inst + "_Base"}


def fabric_slot(index, slot_name, part, inst, stem, detail16, bc_size, detail_size, metal_from_orm, note, contract):
    params = {k: GEN for k in GEN_KEYS}
    params.update({"Specular Strength": 0.5, "Specular From ORM Alpha": False, "Cloth Sheen": False,
                   "Use Lettering": False, "Metal From ORM": bool(metal_from_orm)})
    return {"index": index, "slot_name": slot_name, "part": part, "instance": inst, "master": "M_Fabric_Master",
            "recolourable": True, "tint_ready_shipped": True,
            "textures": {"Detail Map": f"{REC}/{detail16}.png (NEW: lossless linear copy of {detail16[:-2]})",
                         "Base Colour Map": f"{TEX}/{stem}_BC.png", "ORM Map": f"{TEX}/{stem}_ORM.png",
                         "Normal Map": f"{TEX}/{stem}_N.png"},
            "reference_only_textures": {"Detail_sRGB8": f"{TEX}/{detail16[:-2]}.png"},
            "texture_kinds": {"Detail Map": "Detail16", "Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
            "orm_texture_settings": {"composite_texture": f"{stem}_N", "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN",
                                     "composite_power": 1.0},
            "size": {"BC": bc_size, "Detail": detail_size, "ORM": bc_size, "N": bc_size},
            "params": params, "look_contract": contract, "note": note, "base_instance": inst + "_Base"}


def items():
    sword = {"item": "SnowFlower", "mesh": "SM_SnowFlower", "fbx": f"{EXP}/SM_SnowFlower.fbx",
             "sidecar": f"{EXP}/SM_SnowFlower.sockets.json",
             "note": "ADDED 2026-09-26 (the Snow Flower final pass): the hero dao, revision 4. Three slots: the blackened "
                     "blade and the silver fittings share the 4096 steel atlas; the grip cord has its own 2048 atlas.",
             "slots": [
                 steel_slot(0, "M_SnowFlower_Blade", "Blade", "MI_SnowFlower_Blade", "T_SnowFlower_Steel",
                            "the blade steel and its relief blossom proxies (blackened channel, polished bands, silver vine)"),
                 steel_slot(1, "M_SnowFlower_Fittings", "Fittings", "MI_SnowFlower_Fittings", "T_SnowFlower_Steel",
                            "guard, collar, pommel and the grip's silver sprigs (Steel Tint recolours the metal, e.g. gold)"),
                 fabric_slot(2, "M_SnowFlower_Grip", "Grip", "MI_SnowFlower_Grip", "T_SnowFlower_Wrap",
                             "T_SnowFlower_Wrap_Detail16", 2048, 1024, False,
                             "the two-cord grip wrap (near-black silk)",
                             {"BaseColor": "sidecar-free contract: saturate(Colour x (Detail Bias + Detail Scale x Detail)), "
                                           "Colour = the wrap's mean linear albedo; Detail = (albedo lum - 0.0100)/(a_hi - a_lo)",
                              "Metallic": "0", "Roughness": "ORM.G", "AO": "ORM.R", "Normal": "T_SnowFlower_Wrap_N (DirectX)"}),
             ]}
    sheath = {"item": "SnowFlower_Sheath", "mesh": "SM_SnowFlower_Sheath", "fbx": f"{EXP}/SM_SnowFlower_Sheath.fbx",
              "sidecar": f"{EXP}/SM_SnowFlower_Sheath.sockets.json",
              "note": "ADDED 2026-09-26 (the Snow Flower final pass): the sword's scabbard. Both slots sample the one "
                      "4096 atlas; the lacquer is recolourable, the fittings take Steel Tint.",
              "slots": [
                  fabric_slot(0, "M_SnowFlower_Sheath_Lacquer", "Lacquer", "MI_SnowFlower_Sheath_Lacquer",
                              "T_SnowFlower_Sheath", "T_SnowFlower_Sheath_Lacquer_Detail16", 4096, 2048, True,
                              "the marbled black lacquer body and cavity; its baked silver twigs and second stem and its pearl "
                              "buds and pods keep their baked colour (Metal From ORM)",
                              {"BaseColor": "lerp(saturate(Colour x (Detail Bias + Detail Scale x Detail)), BC, max(ORM.B, saturate((lum(BC) - 0.2) x 5))): "
                                            "the marble lacquer recolours, metallic and pearl texels keep the baked colour",
                               "Metallic": "ORM.B (Metal From ORM on)", "Roughness": "ORM.G", "AO": "ORM.R",
                               "Normal": "T_SnowFlower_Sheath_N (DirectX)"}),
                  steel_slot(1, "M_SnowFlower_Sheath_Fittings", "Fittings", "MI_SnowFlower_Sheath_Fittings",
                             "T_SnowFlower_Sheath", "throat, band, chape, the silver vine and the pearl blossoms (Steel "
                             "Tint recolours the metal; the pearl petals are dielectric in the ORM)"),
              ]}
    return [sword, sheath]


def instances():
    out = []
    for it in items():
        for s in it["slots"]:
            out.append({"name": s["instance"] + "_Base", "parent": s["master"], "folder": "Base",
                        "role": "holds every texture and matched setting of the part"})
            out.append({"name": s["instance"], "parent": s["instance"] + "_Base",
                        "role": "buyer-facing: overrides only the colour(s)"})
    return out


METAL_DESC_0927 = "On = texels the ORM map marks as metal (its blue channel) and baked pearl ornament (baked colour brighter than linear luminance 0.2-0.4, far above any recolourable surface) keep their original baked colour; metal stays metallic, while the rest recolours. Used where silver and pearl ornament is baked into a recolourable surface (the Snow Flower sheath's lacquer). Off by default: every other part is non-metal."
METAL_PARAM = {"name": "Metal From ORM", "type": "static_switch", "group": "09 Textures", "sort": 5, "default": False,
               "desc": "On = texels the ORM map marks metallic (blue channel) keep the original baked colour and render "
                       "as metal, so baked silver ornament on a tinted part stays silver. Off = the whole part is the "
                       "tinted, non-metal material."}


def add(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    names = {it["item"] for it in s["items"]}
    if names & {"SnowFlower", "SnowFlower_Sheath"}:
        raise SystemExit("the spec already has Snow Flower items: nothing changed")
    fab = s["masters"]["M_Fabric_Master"]
    if not any(p["name"] == METAL_PARAM["name"] for p in fab["parameters"]):
        fab["parameters"].append(dict(METAL_PARAM))
    for prm in fab["parameters"]:
        if prm["name"] == METAL_PARAM["name"]:
            prm["desc"] = METAL_DESC_0927
    fab["graph"]["BaseColor"] += ("; then MetalFromORM ? lerp(rgb, BaseColourMap.rgb, max(ORM.B, saturate((lum(BaseColourMap)"
                                  " - 0.2) x 5))) : rgb")
    fab["graph"]["Metallic"] = "MetalFromORM ? ORM.B : 0 (static switch, default off; 2026-09-26)"
    s["items"] += items()
    s["instances"] += instances()
    b = s["build"]
    b["recolour_maps"]["SnowFlower"] = f"{REC}/recolour_maps.json"
    b["recolour_constants"]["SnowFlower"] = f"{REC}/recolour_constants.json"
    b["not_imported"][f"{TEX}/T_SnowFlower_Wrap_Detail.png"] = \
        "superseded by the lossless 16-bit linear Recolour/T_SnowFlower_Wrap_Detail16 (the sRGB G8 builds as BGRA8)"
    b["not_imported"][f"{TEX}/T_SnowFlower_Sheath_Lacquer_Detail.png"] = \
        "superseded by the lossless 16-bit linear Recolour/T_SnowFlower_Sheath_Lacquer_Detail16 (the sRGB G8 builds as BGRA8)"
    b["texture_folder"] = b["texture_folder"].replace("Fan)", "Fan, SnowFlower)")
    s["changes_v4_snowflower"] = {
        "date": "2026-09-26/27",
        "what": "The Snow Flower sword (SM_SnowFlower) and sheath (SM_SnowFlower_Sheath) join the pack (additions only): "
                "10 instances (MI_SnowFlower_Blade / _Fittings on M_Steel_Master, MI_SnowFlower_Grip on M_Fabric_Master, "
                "MI_SnowFlower_Sheath_Lacquer on M_Fabric_Master with Metal From ORM on, MI_SnowFlower_Sheath_Fittings "
                "on M_Steel_Master, each with its _Base); group SnowFlower's recolour maps "
                "(maps/make_snowflower_recolour_maps.py) and constants (maps/derive_constants_snowflower.py); the two "
                "shipped 8-bit Detail PNGs not imported.",
        "masters": "M_Fabric_Master gains the static switch 'Metal From ORM' (default off; 2026-09-27: its keep weight also covers baked pearl, BC luminance ramp 0.2-0.4). Off compiles the old path "
                   "(append(rgb, 0) masked back), so no existing instance's look changes; proved by the dump comparison "
                   "and the default base-colour captures (WorkFiles/SnowFlower/v4/materials/).",
        "code": "np_spec.py: NP_SPEC_PATH / NP_ROOT overrides for isolated trial builds and texture_dirs() (the PNG "
                "accounting scans the folders the plan reads from, so the revision-3 Exports/SnowFlower/Textures is "
                "never mistaken for unaccounted maps); np_build.py: clean's disk check follows NP_ROOT; "
                "build_pack_materials.py: NP_OUT_DIR; np_masters.py: the switch.",
        "why_no_new_master": METAL_PARAM["desc"]}
    return s


def trial(spec: dict) -> dict:
    s = add(spec)
    keep = {"SnowFlower", "SnowFlower_Sheath"}
    s["items"] = [it for it in s["items"] if it["item"] in keep]
    inst = {sl["instance"] for it in s["items"] for sl in it["slots"]}
    s["instances"] = [i for i in s["instances"] if i["name"] in inst or i["name"][:-5] in inst]
    b = s["build"]
    b["recolour_maps"] = {"SnowFlower": b["recolour_maps"]["SnowFlower"]}
    b["recolour_constants"] = {"SnowFlower": b["recolour_constants"]["SnowFlower"]}
    b["not_imported"] = {k: v for k, v in b["not_imported"].items() if "SnowFlower" in k}
    txt = json.dumps(s, indent=1).replace("/Game/NinjaPack", "/Game/SFMatTrial")
    return json.loads(txt)


if __name__ == "__main__":
    cmd = sys.argv[1]
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if cmd == "apply":
        SPEC.write_text(json.dumps(add(spec), indent=1, ensure_ascii=False) + ("\n" if SPEC.read_text(encoding="utf-8").endswith("\n") else ""),
                        encoding="utf-8")
        print("applied to", SPEC)
    elif cmd == "trial":
        out = Path(sys.argv[2])
        out.write_text(json.dumps(trial(spec), indent=1, ensure_ascii=False), encoding="utf-8")
        print("trial spec", out)
    else:
        raise SystemExit("apply | trial <out>")
