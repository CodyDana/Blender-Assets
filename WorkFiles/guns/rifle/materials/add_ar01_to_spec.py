"""AR-01 pack-materials stage (materials lock owner ar01-gun-chat): add the Assault Rifle AR-01 to
Scripts/unreal/materials/material_spec.json. ADDITIONS ONLY: 3 items (SK_AR01 skeletal, SM_AR01 static twin,
SM_AR01_Mag), 6 instances (MI_AR01_Metal / MI_AR01_Mag on M_Steel_Master, MI_AR01_Furniture on M_Fabric_Master, each
with its _Base), the AR01 recolour group, the three Masks maps as not imported, and changes_v9_ar01.

    py -3 -B WorkFiles/guns/rifle/materials/add_ar01_to_spec.py [--bc-kind BC|BC_BC7]

Idempotent: if AR01 entries exist they are removed first and re-added (so a re-run with another furniture BC kind is
clean). Writes material_spec_before_ar01.json beside this script the first time, and checks that removing the added
keys gives back exactly that file (JSON equality). Keeps the file's own format (json indent 1, CRLF as checked out).
Paths derive from this file's location (the worktree).
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPEC = ROOT / "Scripts/unreal/materials/material_spec.json"
BEFORE = HERE / "material_spec_before_ar01.json"
ARGS = sys.argv[1:]
BC_KIND = ARGS[ARGS.index("--bc-kind") + 1] if "--bc-kind" in ARGS else "BC"

T = "Exports/Guns/AR01/Textures"
GEN = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"
ITEMS = ("AR01", "AR01_Static", "AR01_Mag")
INSTANCES = [f"MI_AR01_{p}{s}" for p in ("Metal", "Furniture", "Mag") for s in ("_Base", "")]
BC7_KIND = {"srgb": True, "compression": "TC_BC7", "sampler": "SAMPLERTYPE_COLOR", "address": "Wrap",
            "mips": "TMGS_FROM_TEXTURE_GROUP", "pc_format": "BC7 (1 byte/texel)",
            "note": "ADDED 2026-10-09 for the AR-01 furniture: its shipped default samples the BC itself (Use Original "
                    "Baked Colours ON), so the BC's compression IS the default look's error. Measured in Unreal "
                    "(UV-plane base-colour capture vs the PNG): BC1 p99.9 12 levels, dE00 mean 0.71 / p99 2.26; BC7 "
                    "p99.9 4 levels, dE00 mean 0.23 / p99 0.92 (WorkFiles/guns/rifle/gates/pack_materials.json); "
                    "+2.7 MiB with mips at 2048"}


def read_spec():
    raw = SPEC.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    d = json.loads(text)
    if json.dumps(d, indent=1, ensure_ascii=True) + "\n" != text:
        raise SystemExit("material_spec.json is not in json.dumps(indent=1) form: refusing to rewrite it")
    return d, crlf


def write_spec(d, crlf):
    text = json.dumps(d, indent=1, ensure_ascii=True) + "\n"
    SPEC.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def strip_ar01(d):
    d = copy.deepcopy(d)
    d["items"] = [i for i in d["items"] if i["item"] not in ITEMS]
    d["instances"] = [i for i in d["instances"] if i["name"] not in INSTANCES]
    for key in ("recolour_maps", "recolour_constants"):
        d["build"][key].pop("AR01", None)
    for rel in [k for k in d["build"]["not_imported"] if k.startswith("Exports/Guns/AR01/")]:
        d["build"]["not_imported"].pop(rel)
    d["texture_import"].pop("BC_BC7", None)
    d.pop("changes_v9_ar01", None)
    if d["build"]["texture_folder"].endswith(", Guns)"):
        d["build"]["texture_folder"] = d["build"]["texture_folder"][:-len(", Guns)")] + ")"
    return d


def steel_slot(index, slot, part, inst, stem, size, note, uv_tile=None):
    s = {"index": index, "slot_name": slot, "part": part, "instance": inst, "master": "M_Steel_Master",
         "recolourable": False,
         "textures": {"Base Colour Map": f"{T}/{stem}_BC.png", "ORM Map": f"{T}/{stem}_ORM.png",
                      "Normal Map": f"{T}/{stem}_N.png"},
         "texture_kinds": {"Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
         "orm_texture_settings": {"composite_texture": f"{stem}_N",
                                  "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
         "size": [size, size], "params": {},
         "look_contract": {"BaseColor": f"{stem}_BC (sRGB) x Steel Tint (white = as shipped)",
                           "Metallic": "ORM.B (0 lacquer / 1 bare and blued steel)", "Roughness": "ORM.G",
                           "AO": "ORM.R", "Normal": f"{stem}_N (DirectX, 16-bit source)"},
         "note": note, "base_instance": inst + "_Base"}
    if uv_tile:
        s["uv_tile"] = uv_tile
    return s


def furniture_slot(index, uv_tile=None):
    s = {"index": index, "slot_name": "M_AR01_Furniture", "part": "Furniture", "instance": "MI_AR01_Furniture",
         "master": "M_Fabric_Master", "recolourable": True, "tint_ready_shipped": True,
         "textures": {"Detail Map": f"{T}/Recolour/T_AR01_Furniture_Detail16.png (NEW: 16-bit linear tint-ready "
                                    "detail, Scripts/guns/rifle/rifle_recolour.py)",
                      "Base Colour Map": f"{T}/T_AR01_Furniture_BC.png", "ORM Map": f"{T}/T_AR01_Furniture_ORM.png",
                      "Normal Map": f"{T}/T_AR01_Furniture_N.png"},
         "texture_kinds": {"Detail Map": "Detail16", "Base Colour Map": BC_KIND, "ORM Map": "ORM_rgb",
                           "Normal Map": "N"},
         "orm_texture_settings": {"composite_texture": "T_AR01_Furniture_N",
                                  "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
         "size": {"BC": 2048, "Detail": 1024, "ORM": 2048, "N": 2048},
         "params": {"Colour": GEN, "Detail Bias": GEN, "Detail Scale": GEN, "Detail Mean": GEN,
                    "Detail Highlight Ratio": GEN, "Detail Moments Low": GEN, "Detail Moments High": GEN,
                    "Specular Strength": 0.5, "Specular From ORM Alpha": False, "Cloth Sheen": False,
                    "Use Lettering": False, "Metal From ORM": False, "Use Original Baked Colours": True},
         "look_contract": {
             "BaseColor": "shipped (Use Original Baked Colours ON): T_AR01_Furniture_BC exactly (the four pieces' own "
                          "tones); recolour (switch OFF): saturate(Colour x (Detail Bias + Detail Scale x Detail)) "
                          "(v2 MF_TintDetail): the four pieces move together, value ratios kept, hue offsets dropped",
             "Metallic": "0 (Metal From ORM off)", "Roughness": "ORM.G", "AO": "ORM.R",
             "Normal": "T_AR01_Furniture_N (DirectX, 16-bit source)"},
         "note": "the walnut buttstock, pistol grip and both handguards (shellac, grip checkering, handling wear); "
                 "default Colour = the furniture's covered-texel mean; the default instance shows the baked BC "
                 "because the scalar detail cannot carry the pieces' hue offsets (gates/recolour_precheck.json: "
                 "33 levels p99.9 on the tint path at the default)",
         "base_instance": "MI_AR01_Furniture_Base"}
    if uv_tile:
        s["uv_tile"] = uv_tile
    return s


METAL_NOTE = ("black lacquer over steel (receiver, dust cover, trunnions, sights, barrel, gas system, brake, trigger "
              "guard, butt plate; metallic 0 from ORM) and the blued small parts with bare-steel edge wear (bolt, "
              "carrier, selector, trigger, catch, pins, rod; metallic 1 from ORM); baked finish, not recolourable "
              "(user decision); Steel Tint multiplies")
MAG_NOTE = ("the black lacquered steel magazine (wear at the feed lips, lugs, spines at the well and floor plate); "
            "baked finish, not recolourable; Steel Tint multiplies")


def ar01_items():
    sk = {"item": "AR01", "kind": "skeletal", "folder": "/Game/NinjaPack/Meshes/AR01", "short": "AR01",
          "mesh": "SK_AR01", "fbx": "Exports/Guns/AR01/SK_AR01.fbx", "sidecar": "Exports/Guns/AR01/SK_AR01.skeletal.json",
          "note": "ADDED 2026-10-09 (the AR-01 pack-materials stage). The rigged assault rifle: 8 bones + root, 4 LODs "
                  "(SK_AR01_LOD1-3.fbx), 5 weapon clips, PHYS_AR01, 17 sockets; np_skeletal.py imports it into its "
                  "own folder from the sidecar (slots by name). The magazine is its own mesh (SM_AR01_Mag on the Mag "
                  "socket). Metal set 4096, furniture 2048, all UV0 in 0..1",
          "slots": [steel_slot(0, "M_AR01_Metal", "Metal", "MI_AR01_Metal", "T_AR01_Metal", 4096, METAL_NOTE),
                    furniture_slot(1)]}
    st = {"item": "AR01_Static", "mesh": "SM_AR01", "fbx": "Exports/Guns/AR01/SM_AR01.fbx",
          "sidecar": "Exports/Guns/AR01/SM_AR01.sockets.json",
          "note": "ADDED 2026-10-09. The static twin of SK_AR01 with a merged magazine copy (identical to SM_AR01_Mag "
                  "at every LOD): 4 LODs, UCX hulls, 17 sockets. Each slot's UV0 sits in its own U tile (Wrap "
                  "addressing reads the same texels); it shares the three instances with SK_AR01 and SM_AR01_Mag",
          "slots": [steel_slot(0, "M_AR01_Metal", "Metal", "MI_AR01_Metal", "T_AR01_Metal", 4096, METAL_NOTE,
                               uv_tile="u 0..1"),
                    furniture_slot(1, uv_tile="u 1..2 (Wrap addressing reads the same texels)"),
                    steel_slot(2, "M_AR01_Mag", "Mag", "MI_AR01_Mag", "T_AR01_Mag", 1024, MAG_NOTE,
                               uv_tile="u -1..0 (Wrap addressing reads the same texels)")]}
    mag = {"item": "AR01_Mag", "mesh": "SM_AR01_Mag", "fbx": "Exports/Guns/AR01/SM_AR01_Mag.fbx",
           "sidecar": "Exports/Guns/AR01/SM_AR01_Mag.sockets.json",
           "note": "ADDED 2026-10-09. The removable 30-round magazine (attached to SK_AR01's Mag socket; reload path "
                   "MagInsertStart -> MagRockStart -> Mag): 4 LODs, UCX hulls, 5 sockets",
           "slots": [steel_slot(0, "M_AR01_Mag", "Mag", "MI_AR01_Mag", "T_AR01_Mag", 1024, MAG_NOTE)]}
    return [sk, st, mag]


def main():
    d, crlf = read_spec()
    base = strip_ar01(d)
    if not BEFORE.exists():
        if base != d:
            raise SystemExit("AR01 entries already present but no before-file: refusing")
        BEFORE.write_text(json.dumps(d, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    if base != before:
        raise SystemExit("the spec without AR01 differs from material_spec_before_ar01.json: someone else changed it")
    new = copy.deepcopy(base)
    new["items"] += ar01_items()
    for p, master in (("Metal", "M_Steel_Master"), ("Furniture", "M_Fabric_Master"), ("Mag", "M_Steel_Master")):
        new["instances"].append({"name": f"MI_AR01_{p}_Base", "parent": master, "folder": "Base",
                                 "role": "holds every texture and matched setting of the part"})
        new["instances"].append({"name": f"MI_AR01_{p}", "parent": f"MI_AR01_{p}_Base",
                                 "role": "buyer-facing: overrides only the colour(s)"})
    new["build"]["recolour_maps"]["AR01"] = "Exports/Guns/AR01/Textures/Recolour/recolour_maps.json"
    new["build"]["recolour_constants"]["AR01"] = "Exports/Guns/AR01/Textures/Recolour/recolour_constants.json"
    for stem in ("Metal", "Furniture", "Mag"):
        new["build"]["not_imported"][f"{T}/T_AR01_{stem}_Masks.png"] = (
            "the rifle's shipped mask set (R edge-wear propensity, G handling, B cavity, A refinishable) for a buyer's "
            "own wear/dirt material; no pack master samples it")
    tf = new["build"]["texture_folder"]
    if tf.endswith(")"):
        new["build"]["texture_folder"] = tf[:-1] + ", Guns)"
    if BC_KIND == "BC_BC7":
        new["texture_import"]["BC_BC7"] = BC7_KIND
    new["changes_v9_ar01"] = {
        "date": "2026-10-09",
        "what": "The Assault Rifle AR-01 joins the pack (additions only): items AR01 (SK_AR01, kind 'skeletal', "
                "folder Meshes/AR01), AR01_Static (SM_AR01, the static twin with the merged magazine) and AR01_Mag "
                "(SM_AR01_Mag); 6 instances (MI_AR01_Metal and MI_AR01_Mag on M_Steel_Master, MI_AR01_Furniture on "
                "M_Fabric_Master, each with its _Base; SK_AR01 and SM_AR01 share the Metal and Furniture instances, "
                "SM_AR01 and SM_AR01_Mag share the Mag instance); group AR01's recolour map (written by "
                "Scripts/guns/rifle/rifle_recolour.py) and constants (maps/derive_constants_ar01.py); the three "
                "Masks maps not imported. MI_AR01_Furniture_Base ships Use Original Baked Colours ON (the four wood "
                "pieces' hue offsets live only in the BC); a buyer recolour switches it off on MI_AR01_Furniture."
                + (" The furniture BC imports as BC7 (new texture kind BC_BC7): the default look samples the BC "
                   "itself, and BC7 cuts its compression error to a third of BC1's (measured in Unreal)."
                   if BC_KIND == "BC_BC7" else ""),
        "masters": "unchanged",
        "code": "one new script maps/derive_constants_ar01.py (a copy of the katana's with the rifle's group and "
                "paths, no resolve() of export paths); nothing else in the code changed"}
    if strip_ar01(new) != before:
        raise SystemExit("projection check failed: removing the AR01 keys does not give back the before-file")
    write_spec(new, crlf)
    print(f"material_spec.json: +3 items, +6 instances, furniture BC kind {BC_KIND}; projection check OK")


main()
