"""SMG01 W6 pack-materials stage (materials lock owner smg01-gun-chat): add the Compact SMG SM-01 to
Scripts/unreal/materials/material_spec.json. ADDITIONS ONLY: 3 items (SK_SMG01 skeletal, SM_SMG01 static twin,
SM_SMG01_Mag), 6 instances (MI_SMG01_Metal on M_Steel_Master, MI_SMG01_Furniture and MI_SMG01_Mag on M_Fabric_Master,
each with its _Base), the SMG01 recolour group (one group, two members: the polymer furniture and the polymer magazine),
the three Masks maps as not imported, and changes_v10_smg01.

    py -3 -B WorkFiles/guns/smg/materials/add_smg01_to_spec.py [--bc-kind BC|BC_BC7] [--mag-bc-kind BC|BC_BC7]

The AR-01's add_ar01_to_spec.py, adapted: the AR-01 kept its walnut on the fabric master and its magazine on the steel
master; the SMG's furniture AND magazine are black polymer, both recolourable (spec materials.slots / recolour).
Idempotent: if SMG01 entries exist they are removed first and re-added (so a re-run with another BC kind is clean).
Writes material_spec_before_smg01.json beside this script the first time, and checks that removing the added keys
gives back exactly that file (JSON equality). Keeps the file's own format (json indent 1, CRLF as checked out).
Paths derive from this file's location (the worktree). The BC_BC7 texture kind already exists (added by the AR-01).
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SPEC = ROOT / "Scripts/unreal/materials/material_spec.json"
BEFORE = HERE / "material_spec_before_smg01.json"
ARGS = sys.argv[1:]
BC_KIND = ARGS[ARGS.index("--bc-kind") + 1] if "--bc-kind" in ARGS else "BC"
MAG_BC_KIND = ARGS[ARGS.index("--mag-bc-kind") + 1] if "--mag-bc-kind" in ARGS else "BC"

T = "Exports/Guns/SMG01/Textures"
GEN = "GENERATOR (recolour_constants.json, derived from recolour_maps.json over covered texels)"
ITEMS = ("SMG01", "SMG01_Static", "SMG01_Mag")
INSTANCES = [f"MI_SMG01_{p}{s}" for p in ("Metal", "Furniture", "Mag") for s in ("_Base", "")]
DATE = "2026-10-13"


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


def strip_smg01(d):
    d = copy.deepcopy(d)
    d["items"] = [i for i in d["items"] if i["item"] not in ITEMS]
    d["instances"] = [i for i in d["instances"] if i["name"] not in INSTANCES]
    for key in ("recolour_maps", "recolour_constants"):
        d["build"][key].pop("SMG01", None)
    for rel in [k for k in d["build"]["not_imported"] if k.startswith("Exports/Guns/SMG01/")]:
        d["build"]["not_imported"].pop(rel)
    d.pop("changes_v10_smg01", None)
    return d


METAL_NOTE = ("manganese-phosphate steel (top and bottom rails, sights, barrel and nut, muzzle device, bolt, charging "
              "handle, selector, trigger, release paddle, pins, hinge pin; metallic 0 from ORM) with bare-steel wear on "
              "the rail crests, sight ears, device rim, knob crown, selector tip and the bolt's sliding flanks "
              "(metallic 1 from ORM); baked finish, not recolourable (spec materials.slots); Steel Tint multiplies")


def steel_slot(index, uv_tile=None):
    stem = "T_SMG01_Metal"
    s = {"index": index, "slot_name": "M_SMG01_Metal", "part": "Metal", "instance": "MI_SMG01_Metal",
         "master": "M_Steel_Master", "recolourable": False,
         "textures": {"Base Colour Map": f"{T}/{stem}_BC.png", "ORM Map": f"{T}/{stem}_ORM.png",
                      "Normal Map": f"{T}/{stem}_N.png"},
         "texture_kinds": {"Base Colour Map": "BC", "ORM Map": "ORM_rgb", "Normal Map": "N"},
         "orm_texture_settings": {"composite_texture": f"{stem}_N",
                                  "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
         "size": [2048, 2048], "params": {},
         "look_contract": {"BaseColor": f"{stem}_BC (sRGB) x Steel Tint (white = as shipped)",
                           "Metallic": "ORM.B (0 phosphate / 1 bare steel wear)", "Roughness": "ORM.G",
                           "AO": "ORM.R", "Normal": f"{stem}_N (DirectX, 16-bit source)"},
         "note": METAL_NOTE, "base_instance": "MI_SMG01_Metal_Base"}
    if uv_tile:
        s["uv_tile"] = uv_tile
    return s


def polymer_slot(index, part, size, detail, note, bc_kind, uv_tile=None):
    stem = f"T_SMG01_{part}"
    inst = f"MI_SMG01_{part}"
    s = {"index": index, "slot_name": f"M_SMG01_{part}", "part": part, "instance": inst,
         "master": "M_Fabric_Master", "recolourable": True, "tint_ready_shipped": True,
         "textures": {"Detail Map": f"{T}/Recolour/{stem}_Detail16.png (NEW: 16-bit linear tint-ready detail, "
                                    "Scripts/guns/smg/smg_recolour.py)",
                      "Base Colour Map": f"{T}/{stem}_BC.png", "ORM Map": f"{T}/{stem}_ORM.png",
                      "Normal Map": f"{T}/{stem}_N.png"},
         "texture_kinds": {"Detail Map": "Detail16", "Base Colour Map": bc_kind, "ORM Map": "ORM_rgb",
                           "Normal Map": "N"},
         "orm_texture_settings": {"composite_texture": f"{stem}_N",
                                  "composite_texture_mode": "CTM_NORMAL_ROUGHNESS_TO_GREEN", "composite_power": 1.0},
         "size": {"BC": size, "Detail": detail, "ORM": size, "N": size},
         "params": {"Colour": GEN, "Detail Bias": GEN, "Detail Scale": GEN, "Detail Mean": GEN,
                    "Detail Highlight Ratio": GEN, "Detail Moments Low": GEN, "Detail Moments High": GEN,
                    "Specular Strength": 0.5, "Specular From ORM Alpha": False, "Cloth Sheen": False,
                    "Use Lettering": False, "Metal From ORM": False, "Use Original Baked Colours": True},
         "look_contract": {
             "BaseColor": f"shipped (Use Original Baked Colours ON): {stem}_BC exactly (the black polymer with its "
                          "whitening specks, scuffs and polish); recolour (switch OFF): saturate(Colour x (Detail Bias "
                          "+ Detail Scale x Detail)) (v2 MF_TintDetail): the polymer takes the buyer's colour, value "
                          "ratios kept",
             "Metallic": "0 (Metal From ORM off)", "Roughness": "ORM.G", "AO": "ORM.R",
             "Normal": f"{stem}_N (DirectX, 16-bit source)"},
         "note": note, "base_instance": inst + "_Base"}
    if uv_tile:
        s["uv_tile"] = uv_tile
    return s


FUR_NOTE = ("the black polymer furniture (upper and lower receiver shells, grip frame and cover, magwell, skeleton stock, "
            "butt pad, stock latch); default Colour = the set's covered-texel mean; the default instance shows the baked "
            "BC because the 2048 detail map cannot carry the 4096 BC's fine wear (gates/recolour_precheck.json: "
            "32 levels p99.9 on the tint path at the default, p50 1)")
MAG_NOTE = ("the black polymer 25-round magazine (body, floor plate, follower); default Colour = the magazine's "
            "covered-texel mean; the default instance shows the baked BC (gates/recolour_precheck.json: 5 levels "
            "p99.9 on the tint path at the default)")


def smg01_items():
    fur = lambda i, t=None: polymer_slot(i, "Furniture", 4096, 2048, FUR_NOTE, BC_KIND, t)  # noqa: E731
    mag = lambda i, t=None: polymer_slot(i, "Mag", 1024, 1024, MAG_NOTE, MAG_BC_KIND, t)  # noqa: E731
    sk = {"item": "SMG01", "kind": "skeletal", "folder": "/Game/NinjaPack/Meshes/SMG01", "short": "SMG01",
          "mesh": "SK_SMG01", "fbx": "Exports/Guns/SMG01/SK_SMG01.fbx",
          "sidecar": "Exports/Guns/SMG01/SK_SMG01.skeletal.json",
          "note": f"ADDED {DATE} (the SMG01 W6 pack-materials stage). The rigged compact SMG: 11 bones incl. root, 4 "
                  "LODs (SK_SMG01_LOD1-3.fbx), 8 weapon clips (incl. StockFold / StockUnfold / SightFlip), PHYS_SMG01 "
                  "(the body's bounds-envelope box has no collision and no mass), 21 sockets, bounds extension for "
                  "the folded stock; np_skeletal.py imports it into its own folder from the sidecar (slots by name). "
                  "The magazine is its own mesh (SM_SMG01_Mag on the Mag socket). Metal 2048, polymer 4096, all UV0 "
                  "in 0..1",
          "slots": [steel_slot(0), fur(1)]}
    st = {"item": "SMG01_Static", "mesh": "SM_SMG01", "fbx": "Exports/Guns/SMG01/SM_SMG01.fbx",
          "sidecar": "Exports/Guns/SMG01/SM_SMG01.sockets.json",
          "note": f"ADDED {DATE}. The static twin of SK_SMG01 (stock extended) with a merged magazine copy: 4 LODs, "
                  "UCX hulls, sockets. Each slot's UV0 sits in its own U tile (Wrap addressing reads the same texels); "
                  "it shares the three instances with SK_SMG01 and SM_SMG01_Mag",
          "slots": [steel_slot(0, uv_tile="u 0..1"),
                    fur(1, "u 1..2 (Wrap addressing reads the same texels)"),
                    mag(2, "u -1..0 (Wrap addressing reads the same texels)")]}
    mg = {"item": "SMG01_Mag", "mesh": "SM_SMG01_Mag", "fbx": "Exports/Guns/SMG01/SM_SMG01_Mag.fbx",
          "sidecar": "Exports/Guns/SMG01/SM_SMG01_Mag.sockets.json",
          "note": f"ADDED {DATE}. The removable 25-round polymer magazine (attached to SK_SMG01's Mag socket; straight "
                  "reload path MagInsertStart -> Mag along the magazine's -Z): 4 LODs, UCX hulls, sockets",
          "slots": [mag(0)]}
    return [sk, st, mg]


def main():
    d, crlf = read_spec()
    base = strip_smg01(d)
    if not BEFORE.exists():
        if base != d:
            raise SystemExit("SMG01 entries already present but no before-file: refusing")
        BEFORE.write_text(json.dumps(d, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    if base != before:
        raise SystemExit("the spec without SMG01 differs from material_spec_before_smg01.json: someone else changed it")
    if "BC_BC7" not in base["texture_import"]:
        raise SystemExit("texture kind BC_BC7 missing (the AR-01 added it): refusing")
    new = copy.deepcopy(base)
    new["items"] += smg01_items()
    for p, master in (("Metal", "M_Steel_Master"), ("Furniture", "M_Fabric_Master"), ("Mag", "M_Fabric_Master")):
        new["instances"].append({"name": f"MI_SMG01_{p}_Base", "parent": master, "folder": "Base",
                                 "role": "holds every texture and matched setting of the part"})
        new["instances"].append({"name": f"MI_SMG01_{p}", "parent": f"MI_SMG01_{p}_Base",
                                 "role": "buyer-facing: overrides only the colour(s)"})
    new["build"]["recolour_maps"]["SMG01"] = "Exports/Guns/SMG01/Textures/Recolour/recolour_maps.json"
    new["build"]["recolour_constants"]["SMG01"] = "Exports/Guns/SMG01/Textures/Recolour/recolour_constants.json"
    for stem in ("Metal", "Furniture", "Mag"):
        new["build"]["not_imported"][f"{T}/T_SMG01_{stem}_Masks.png"] = (
            "the SMG's shipped mask set (R edge-wear propensity, G handling, B cavity, A refinishable) for a buyer's "
            "own wear/dirt material; no pack master samples it")
    if not new["build"]["texture_folder"].endswith(", Guns)"):
        raise SystemExit("texture_folder does not list Guns (the AR-01 added it): refusing")
    bc7 = [n for n, k in (("furniture", BC_KIND), ("magazine", MAG_BC_KIND)) if k == "BC_BC7"]
    new["changes_v10_smg01"] = {
        "date": DATE,
        "what": "The Compact SMG SM-01 joins the pack (additions only): items SMG01 (SK_SMG01, kind 'skeletal', "
                "folder Meshes/SMG01), SMG01_Static (SM_SMG01, the static twin with the merged magazine) and SMG01_Mag "
                "(SM_SMG01_Mag); 6 instances (MI_SMG01_Metal on M_Steel_Master, MI_SMG01_Furniture and MI_SMG01_Mag "
                "on M_Fabric_Master, each with its _Base; SK_SMG01 and SM_SMG01 share the Metal and Furniture "
                "instances, SM_SMG01 and SM_SMG01_Mag share the Mag instance); group SMG01's recolour map (written "
                "by Scripts/guns/smg/smg_recolour.py, two members) and constants (maps/derive_constants_smg01.py); "
                "the three Masks maps not imported. Both polymer _Base instances ship Use Original Baked Colours ON "
                "(the polymer's fine wear lives only in the BC); a buyer recolour switches it off on "
                "MI_SMG01_Furniture and MI_SMG01_Mag and sets the same Colour on both."
                + (f" The {' and '.join(bc7)} BC imports as BC7 (texture kind BC_BC7): the default look samples the BC "
                   "itself (measured in Unreal, WorkFiles/guns/smg/gates/pack_materials.json)." if bc7 else ""),
        "masters": "unchanged",
        "code": "one new script maps/derive_constants_smg01.py (a copy of the AR-01's with the SMG's group and two "
                "parts, no resolve() of export paths); nothing else in the code changed"}
    if strip_smg01(new) != before:
        raise SystemExit("projection check failed: removing the SMG01 keys does not give back the before-file")
    write_spec(new, crlf)
    print(f"material_spec.json: +3 items, +6 instances, furniture BC kind {BC_KIND}, mag BC kind {MAG_BC_KIND}; "
          "projection check OK")


main()
