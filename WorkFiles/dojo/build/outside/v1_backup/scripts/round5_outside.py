"""ROUND 5 OUTSIDE track: what the combined DojoLab compose needs from this track (plain Python, no bpy / unreal), in
the shape of Scripts/dojo/showcase/round4.py. This file is the OUTSIDE track's; the showcase compose (another chat's)
imports it read-only when it integrates round 5.

  KIT              kit name -> (FBX folder, texture folder, Unreal content root)
  LAYOUT           layout_outside.json exactly as build_outside.py wrote it
  replaced_greybox()   SM_DGB_Ground_Outside and SM_DGB_AlleyFence -> 'outside' (drop their pieces and instances)
  modern_street()  (pieces, rows): drop EVERY showcase instance of the modern kit's street pieces (lamps A / B, poles,
                   transformer, guys, conductor / telecom spans, the gatehouse drop) and place the returned rows instead.
                   The modern kit's files and layout_modern.json are untouched; compose_showcase.lamp_lights() derives the
                   street-lamp point lights from the moved lamp instances (both lamps already have LAMP_LIGHTS
                   entries there; the bulb centre is measured from each mesh)
  recipes()        this track's material instances (M_DKX_*) on the showcase's existing masters
  textures()       texture name -> {png, ue_dir, kind}: T_DKX_* are this track's (Exports/DojoKit/Outside/Textures,
                   /Game/DojoKit/Outside/Textures); T_DKG_Soil_* / T_DKG_Macro_M (ground kit) and T_DJ_WearMask_M
                   (library) are already in the showcase's texture table
  WALK_ROUTES / CLIMB_ROUTES   the routes this track added to its checks layout (BR street routes, the alley-fence
                   CONTROLs, the outside wall climbs)
  TREE_SLOTS       the empty tree slots for the vegetation pass
ROUND 6 (2026-09-29), same module, no new call needed for the level (the pieces and instances come in with the layout):
  ONEV1_ONLY       layout_outside.json 'onev1_only': the pocket fences, the alley fences and the SM_DKX_1v1_* invisible
                   blockers (class 'boundary', folder Boundary_1v1). The duel level places them; the BR copy drops them
  RETIRED_MATERIALS  the round-5 f1 flat far-town instances no longer used by any mesh (M_DKX_FarRoofA/B,
                   M_DKX_FarWallPlaster/Wood): the showcase may delete them from DojoLab
  WALK_ROUTES now also carries the round-6 CONTROL_alley_pocket_* routes (same 'CONTROL_alley' prefix)
"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BUILD = ROOT / "WorkFiles" / "dojo" / "build"
EXP = ROOT / "Exports" / "DojoKit"
KIT = {"outside": (EXP / "Outside", EXP / "Outside" / "Textures", "/Game/DojoKit/Outside")}
LAYOUT_FILE = BUILD / "outside" / "layout_outside.json"
CHECK_LAYOUT_FILE = BUILD / "outside" / "layout_outside_checks.json"
LAYOUT = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))


def replaced_greybox():
    return {n: "outside" for n in LAYOUT["replaces_greybox"]}


def modern_street():
    return list(LAYOUT["modern_replaces"]["pieces"]), [dict(r) for r in LAYOUT["modern_instances"]]


def recipes():
    return json.loads(json.dumps(LAYOUT["materials"]))


def textures():
    return json.loads(json.dumps(LAYOUT["textures"]))


def _routes():
    L = json.loads(CHECK_LAYOUT_FILE.read_text(encoding="utf-8"))
    walk = {k: v for k, v in L["walk_routes"].items() if k.startswith(("BR_", "CONTROL_alley"))}
    climb = [r for r in L["climb_routes"] if r.get("route") == "O"]
    return walk, climb


WALK_ROUTES, CLIMB_ROUTES = _routes()
TREE_SLOTS = LAYOUT["tree_slots"]
ONEV1_ONLY = LAYOUT.get("onev1_only", {})
RETIRED_MATERIALS = ["M_DKX_FarRoofA", "M_DKX_FarRoofB", "M_DKX_FarWallPlaster", "M_DKX_FarWallWood"]
