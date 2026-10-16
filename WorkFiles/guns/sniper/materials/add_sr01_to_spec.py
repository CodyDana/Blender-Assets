"""SR-01 pack-colours stage (materials lock owner sr01-pack): add the Sniper Rifle SR-01 to
Scripts/unreal/materials/material_spec.json. ADDITIONS ONLY: 4 items (SK_SR01 skeletal, SM_SR01 static twin,
SM_SR01_Mag, SM_Att_Scope_LongRange), 10 instances (MI_SR01_Metal / _Chassis / _Mag, MI_Att_Scope_LongRange_Body /
_Lens, each with its _Base), recolour group SR01 (one member, the OD paint on M_SR01_Chassis), the five Masks maps as
not imported, and changes_v11_sr01. Option D1-a: no master change; the OD ships as baked (Use Original Baked Colours ON).

    py -3 -B WorkFiles/guns/sniper/materials/add_sr01_to_spec.py [--bc-kind BC|BC_BC7] [--mag-bc-kind BC|BC_BC7]

The entries are the W6 proposal's (WorkFiles/guns/sniper/pack_materials_proposal.json, field shapes copied from the
SMG01 entries) with the notes and changes text made final. Default BC kinds are the proposal's (BC_BC7 for the chassis
and the magazine; the SMG needed BC7 to meet P1); pass --bc-kind BC / --mag-bc-kind BC to try BC1.
Idempotent: if SR01 entries exist they are removed first and re-added. Writes material_spec_before_sr01.json beside
this script the first time, and checks that removing the added keys gives back exactly that file (JSON equality).
Keeps the file's own format (json indent 1, CRLF as checked out). Paths derive from this file's location.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNIPER = HERE.parent
ROOT = HERE.parents[3]
SPEC = ROOT / "Scripts/unreal/materials/material_spec.json"
BEFORE = HERE / "material_spec_before_sr01.json"
PROPOSAL = SNIPER / "pack_materials_proposal.json"
ARGS = sys.argv[1:]
BC_KIND = ARGS[ARGS.index("--bc-kind") + 1] if "--bc-kind" in ARGS else "BC_BC7"
MAG_BC_KIND = ARGS[ARGS.index("--mag-bc-kind") + 1] if "--mag-bc-kind" in ARGS else "BC_BC7"

ITEMS = ("SR01", "SR01_Static", "SR01_Mag", "Att_Scope_LongRange")
PARTS = ("SR01_Metal", "SR01_Chassis", "SR01_Mag", "Att_Scope_LongRange_Body", "Att_Scope_LongRange_Lens")
INSTANCES = [f"MI_{p}{s}" for p in PARTS for s in ("_Base", "")]
DATE = "2026-10-16"
CHANGES = "changes_v11_sr01"


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


def strip_sr01(d):
    d = copy.deepcopy(d)
    d["items"] = [i for i in d["items"] if i["item"] not in ITEMS]
    d["instances"] = [i for i in d["instances"] if i["name"] not in INSTANCES]
    for key in ("recolour_maps", "recolour_constants"):
        d["build"][key].pop("SR01", None)
    for rel in [k for k in d["build"]["not_imported"] if k.startswith("Exports/Guns/SR01/")]:
        d["build"]["not_imported"].pop(rel)
    d.pop(CHANGES, None)
    return d


def finalise_items(prop):
    items = copy.deepcopy(prop["items"])
    for it in items:
        it["note"] = it["note"].replace("PROPOSED (SR-01 W6, unbuilt).", f"ADDED {DATE} (the SR-01 pack-colours stage).")
        it["note"] = it["note"].replace("PROPOSED.", f"ADDED {DATE}.")
        if "PROPOSED" in it["note"]:
            raise SystemExit(f"{it['item']}: note still says PROPOSED")
        for s in it["slots"]:
            tk = s["texture_kinds"]
            if s["slot_name"] == "M_SR01_Chassis":
                tk["Base Colour Map"] = BC_KIND
                s["textures"]["Detail Map"] = (
                    "Exports/Guns/SR01/Textures/Recolour/T_SR01_Chassis_Detail16.png (16-bit linear tint-ready detail "
                    "over the OD paint only, Masks A = 1; WorkFiles/guns/sniper/materials/sr01_recolour_maps.py)")
            elif s["slot_name"] == "M_SR01_Mag":
                # baked-only (no OD, not in group SR01): M_Fabric_Master's leaf must override Colour
                # (build.instance_chain.leaf_overrides), which a non-member has no value for, so the magazine takes
                # the proposal's equal alternative, M_Steel_Master, as the AR-01's magazine does
                tk["Base Colour Map"] = MAG_BC_KIND
                s["master"] = "M_Steel_Master"
                s["params"] = {}
                s["look_contract"] = {"BaseColor": "T_SR01_Mag_BC (sRGB) x Steel Tint (white = as shipped)",
                                      "Metallic": "ORM.B (0 phosphate and polymer / 1 bare steel wear)",
                                      "Roughness": "ORM.G", "AO": "ORM.R",
                                      "Normal": "T_SR01_Mag_N (DirectX, 16-bit source)"}
                s["note"] = ("the 10-round box magazine: phosphated steel body (87 % of its texels) and polymer parts; "
                             "no OD paint (Masks A = 0 everywhere), so it is not in recolour group SR01; baked finish, "
                             "not recolourable; on M_Steel_Master as the AR-01's magazine (M_Fabric_Master's leaf "
                             "needs a Colour, which a baked-only part has no value for); Steel Tint multiplies")
    return items


def main():
    d, crlf = read_spec()
    base = strip_sr01(d)
    if not BEFORE.exists():
        if base != d:
            raise SystemExit("SR01 entries already present but no before-file: refusing")
        BEFORE.write_text(json.dumps(d, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    if base != before:
        raise SystemExit("the spec without SR01 differs from material_spec_before_sr01.json: someone else changed it")
    for k in ("BC_BC7", "Detail16", "ORM_rgb", "N", "BC"):
        if k not in base["texture_import"]:
            raise SystemExit(f"texture kind {k} missing: refusing")
    if not base["build"]["texture_folder"].endswith(", Guns)"):
        raise SystemExit("texture_folder does not list Guns (the AR-01 added it): refusing")
    prop = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    names = {i["item"] for i in base["items"]}
    inst_names = {i["name"] for i in base["instances"]}
    clash = names & set(ITEMS) | inst_names & set(INSTANCES)
    if clash:
        raise SystemExit(f"name clash with existing entries: {sorted(clash)}")
    if sorted(i["name"] for i in prop["instances"]) != sorted(INSTANCES):
        raise SystemExit("proposal instances differ from the expected 10")
    new = copy.deepcopy(base)
    new["items"] += finalise_items(prop)
    insts = copy.deepcopy(prop["instances"])
    for i in insts:
        if i["name"] == "MI_SR01_Mag_Base":
            i["parent"] = "M_Steel_Master"
    new["instances"] += insts
    bme = prop["build_map_entries"]
    new["build"]["recolour_maps"].update(bme["recolour_maps"])
    new["build"]["recolour_constants"].update(bme["recolour_constants"])
    new["build"]["not_imported"].update(bme["not_imported"])
    bc7 = [n for n, k in (("chassis", BC_KIND), ("magazine", MAG_BC_KIND)) if k == "BC_BC7"]
    new[CHANGES] = {
        "date": DATE,
        "what": "The Sniper Rifle SR-01 joins the pack (additions only): items SR01 (SK_SR01, kind 'skeletal', "
                "folder Meshes/SR01), SR01_Static (SM_SR01, the static twin with the merged magazine), SR01_Mag "
                "(SM_SR01_Mag) and Att_Scope_LongRange (SM_Att_Scope_LongRange, folder Meshes/SR01); 10 instances "
                "(MI_SR01_Metal, MI_SR01_Mag, MI_Att_Scope_LongRange_Body and _Lens on M_Steel_Master; "
                "MI_SR01_Chassis on M_Fabric_Master with Metal From ORM ON; each with its _Base; the baked-only "
                "magazine is on M_Steel_Master as the AR-01's, because M_Fabric_Master's leaf must override a "
                "Colour that a non-member has no value for); group SR01's recolour "
                "map (one member, the OD paint, written by WorkFiles/guns/sniper/materials/sr01_recolour_maps.py) and "
                "constants (maps/derive_constants_sr01.py); the five Masks maps not imported. Option D1-a: the "
                "Chassis and Mag _Base instances ship Use Original Baked Colours ON (the OD ships as baked); "
                "M_Fabric_Master has no mask input, so switching it off would tint the whole Chassis set (grip, butt "
                "pad and bipod too): recolour is documented as not safe on this item until a future master switch. "
                "The Mag _Base on M_Steel_Master is BC x white Steel Tint (exactly the BC)."
                + (f" The {' and '.join(bc7)} BC imports as BC7 (texture kind BC_BC7), as the SMG's polymer needed "
                   "for P1 (WorkFiles/guns/sniper/gates/pack_materials.json)." if bc7 else ""),
        "masters": "unchanged (option D1-a)",
        "code": "one new script maps/derive_constants_sr01.py (derive_constants_smg01.py with group SR01 and one "
                "part); nothing else in the code changed"}
    if strip_sr01(new) != before:
        raise SystemExit("projection check failed: removing the SR01 keys does not give back the before-file")
    write_spec(new, crlf)
    print(f"material_spec.json: +4 items, +10 instances, chassis BC kind {BC_KIND}, mag BC kind {MAG_BC_KIND}; "
          "projection check OK (removing the SR01 keys gives back material_spec_before_sr01.json)")


main()
