"""Hall + armory round (wf_ac6d2186-d40), stage 1: SURVEY + DESIGN (2026-10-01).

Reads the armory chat's r20 build data READ-ONLY (WorkFiles/armory/build/layout.json, its Unreal import / materials /
level reports, Exports/ArmoryKit) and the dojo showcase layout, and writes:
  WorkFiles/shared/armory_hall/{interior_layout,lights_design,interface,hall_shell_layout,manifest}.json  (revision 1)
  WorkFiles/dojo/build/hall_armory/survey/survey_report.json                                            (numbers, checks)
The plan image is drawn by draw_plan.py from the jsons written here.

Frames (all metres):
  dojo layout frame: x east, y north, z up, courtyard z 0; Unreal cm = (x*100, -y*100, z*100), yaw = -rot_z.
  HALL-LOCAL: origin = the hall's centre door threshold (bay sill centre line Y 24.0, X 22.0) at finished floor level
              (+0.50); +X east, +Y north into the hall, +Z up.  world = hall_local + (22.0, 24.0, 0.5).
  armory frame (the armory chat's layout.json): origin = the interior's SW corner at floor level, X across 0..12,
              Y along the axis 0..20 from the south door.  hall_local = armory + (-6.0, 0.0, 0.0) (a pure translation:
              the armory's door axis X 6.0 lands on the hall's centre line, its south inner face on the hall's front
              wall line, its floor on the hall's floor).
No Blender, no Unreal: plain Python 3.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
ARMORYLAB_CONTENT = Path("C:/Users/Cody/Documents/Unreal Projects/ArmoryLab/Content")
SH = ROOT / "WorkFiles/shared/armory_hall"
SV = ROOT / "WorkFiles/dojo/build/hall_armory/survey"
DATE = "2026-10-01"
REV = 1
CHAT = "dojo (hall + armory round wf_ac6d2186-d40, stage 1 survey + design)"

HALL_ORIGIN_WORLD = (22.0, 24.0, 0.5)
ARMORY_TO_HALL = (-6.0, 0.0, 0.0)


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jdump(p, obj):
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def r4(v):
    return [round(float(x), 4) for x in v]


def a2h(p, dz=0.0):
    return r4((p[0] + ARMORY_TO_HALL[0], p[1] + ARMORY_TO_HALL[1], p[2] + ARMORY_TO_HALL[2] + dz))


def h2w(p):
    return r4((p[0] + HALL_ORIGIN_WORLD[0], p[1] + HALL_ORIGIN_WORLD[1], p[2] + HALL_ORIGIN_WORLD[2]))


def w2h(p):
    return r4((p[0] - HALL_ORIGIN_WORLD[0], p[1] - HALL_ORIGIN_WORLD[1], p[2] - HALL_ORIGIN_WORLD[2]))


def ue_cm(p):
    return [round(p[0] * 100, 2), round(-p[1] * 100, 2), round(p[2] * 100, 2)]


def bbox_a2h(b, dz=0.0):
    lo = a2h(b[0:3], dz)
    hi = a2h(b[3:6], dz)
    return lo + hi


# ================================================================================================ inputs (read-only)
AL = jload(ROOT / "WorkFiles/armory/build/layout.json")
AIMP = jload(ROOT / "WorkFiles/armory/build/unreal/import.json")
AMAT = jload(ROOT / "WorkFiles/armory/build/unreal/materials.json")
ALEV = jload(ROOT / "WorkFiles/armory/build/unreal/level.json")
AQA = jload(ROOT / "WorkFiles/armory/build/qa_report.json")
AEXP = jload(ROOT / "WorkFiles/armory/build/export_report.json")
AWALK = jload(ROOT / "WorkFiles/armory/build/walk_check.json")
DL = jload(ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json")
HL = jload(ROOT / "WorkFiles/dojo/build/hall/layout_hall.json")
BB = jload(ROOT / "WorkFiles/dojo/build/showcase/blender_bounds.json")["instances"]
WL = jload(ROOT / "WorkFiles/dojo/build/landscape/fix/json/world_layout.json")
HANDOFF = ROOT / "WorkFiles/armory/ARMORY_HANDOFF_DOJO.md"

EXPORTS_AK = ROOT / "Exports/ArmoryKit"
EXPORTS_HALL = ROOT / "Exports/DojoKit/Hall"

# ================================================================================================ hall numbers
HN = HL["numbers"]
FLOOR = HN["floor"]                                   # +0.50
BX0, BX1, BY0, BY1 = HN["body"]                        # 13, 31, 24, 34
PLATE_BOT, PLATE_TOP = HN["wall_plate"]               # 5.4472, 5.6872
CPLATE = HN["upper_centre_plane"]["wall_plate"]       # 5.62, 5.86
UP = HN["upper_roof"]
UP_EAVE, (UPX0, UPX1, UPY0, UPY1) = UP["eave"], UP["rect"]
UP_PITCH = UP["pitch_deg"]
UP_ZR = UP["planes_meet"]                              # 8.9064
UP_CAP = UP["ridge_cap_top"]                           # 9.3649
UP_END = UP["ridge_end_top"]                           # 9.6064
HP = 0.24                                             # hall post
KAMOI_UNDER = 1.90 - 0.012                            # head track underside above the floor (build_hall KAMOI)
SILL_TOP = 0.045                                      # bay sill top above the floor (build_hall bay_sill)
SILL_Y = (-0.08, 0.08)
TILE_TOP = 0.030 + 0.052 + 0.024 + 0.005              # kit1_geo TILE_TOP (0.111)
T25, T30 = math.tan(math.radians(25.0)), math.tan(math.radians(30.0))


def under(pitch):
    """roof_kit: collision plane -> rafter underside (base_off + sarking + rafter + gap)."""
    return TILE_TOP / math.cos(math.radians(pitch)) + 0.004 + 0.025 + 0.10


assert abs((UP_EAVE + (BY0 - HP / 2 - UPY0) * T30 - under(30.0) - 0.006) - PLATE_TOP) < 2e-4, "plate formula drift"

# ================================================================================================ armory interior
ROOM = AL["room"]
assert (ROOM["width_x"], ROOM["length_y"], ROOM["ceiling_z"]) == (12.0, 20.0, 4.8), ROOM
assert AL["openings"]["door_x"] == [4.0, 8.0]

EXCLUDE = {
    "SM_AK_Entrance_12": "the armory's own south wall with its 4.0 x 3.65 m entrance frame, lintel and ranma: the hall's "
                         "front wall and its three centre door bays replace it (the armory's exterior wall is not used)",
    "SM_AK_Threshold_4": "the armory's exterior threshold sill (outside its south wall)",
    "SM_AK_GenkanFloor": "the armory's sunken genkan (-0.12) is not used: the hall's veranda (+0.50) and door sill "
                         "(+0.545) are the entry; the armory floor runs flush to the hall's front wall",
    "SM_AK_StepBeam": "the genkan's agari-kamachi (black step beam) goes with the genkan",
    "SM_AK_Floor_Plank_EntryBand": "the plank band cut round the genkan: replaced by eight ordinary SM_AK_Floor_Plank_2x2 "
                                   "tiles in the armory's own A-D pattern (AKI_9001..9008)",
    "SM_AK_DoorLeaf": "the armory's own entrance leaves (3.9 m) belong to its 4 m entrance; in the hall the hall's door "
                      "leaves are the doors",
    "SM_AK_DoorLeaf_R": "as SM_AK_DoorLeaf",
    "SM_AK_Post_Jamb_480": "entrance jamb posts at hall-local x +-3.83..4.45: rev 1 decision D2 = not placed (they would "
                           "stand in the parked hall door leaves, decision D1)",
    "SM_AK_H_WallSconce": "the wall lanterns hang on the jamb posts (decision D2)",
}
SOUTH_CORNER = "south corner post SM_AK_Corner_5 (armory Y -0.3..0): it would stand through the hall's front wall and " \
               "show 0.18 m outside its outer face"
GENKAN_Z = -0.12
Z_SHIFT_PIECES = {"SM_AK_Lantern", "SM_AK_EntryMat"}   # stood on the genkan floor (-0.12): lifted onto the hall floor


def group_of(p):
    if p.startswith("SM_AK_Floor_Plank"):
        return "floor"
    if p.startswith("SM_AK_Case_"):
        return "case"
    if p.startswith(("SM_AK_Ceiling_", "SM_AK_H_Ceiling_")):
        return "ceiling"
    if p.startswith(("SM_AK_WallLower", "SM_AK_WallUpper", "SM_AK_Corner_5", "SM_AK_Window_Lattice", "SM_AK_SillLedge",
                     "SM_AK_Post_480", "SM_AK_Post_260", "SM_AK_WallPanel_LitWide")):
        return "wall"
    if p.startswith(("SM_AK_Platform_", "SM_AK_Steps_", "SM_AK_StairCheek", "SM_AK_EmblemDisc", "SM_AK_Post_Heavy",
                     "SM_AK_H_LanternStand")):
        return "dais_stairs"
    if p.startswith(("SM_AK_PaintingPanel", "SM_AK_H_PaintingBase", "SM_AK_RearScreen", "SM_AK_Post_LED",
                     "SM_AK_H_Canopy", "SM_AK_H_TopBeam", "SM_AK_H_Downlight", "SM_AK_RearAlcove",
                     "SM_AK_H_CornerNiche")):
        return "rear_wall_painting_alcoves_niches"
    if p.startswith("SM_AK_DSP_"):
        return "display_mount"
    return "dressing"


def collision_class(p):
    """DojoLab collision classes (layout_showcase collision_classes) + the new 'glass' class (proposal)."""
    if p.startswith("SM_AK_Case_") and p.endswith("_Glass"):
        return "glass"
    if p.startswith("SM_AK_Case_") and p.endswith("_Plinth"):
        return "propblock"
    if p.startswith(("SM_AK_Floor_Plank", "SM_AK_Platform_", "SM_AK_Steps_", "SM_AK_EntryMat")):
        return "ground"
    if p.startswith(("SM_AK_Lantern", "SM_AK_H_LanternStand", "SM_AK_Vase_Plum_L")):
        return "propblock"
    if p.startswith(("SM_AK_Vase_Plum_S", "SM_AK_SillCaddy", "SM_AK_Banner")):
        return "thin"
    if p.startswith("SM_AK_DSP_"):
        return "nocollision"
    return "building"


HERO = AL["hero_pieces"]
SLOTS = {k: v["slots"] for k, v in AMAT["meshes"].items()}

interior = []
not_used = []
envelope_viol = []
ENV = {"x": (-6.30, 6.30), "y": (0.0, 20.30), "z": (-0.12, 5.00)}
TOL = 0.012

for idx, ins in enumerate(AL["instances"]):
    p, b = ins["piece"], ins["bbox_min_max"]
    reason = None
    if p.startswith("SM_AKX_"):
        reason = "the armory's own exterior (garden, facades, roof, foundations, scenery): the hall supplies the shell"
    elif p in EXCLUDE:
        reason = EXCLUDE[p]
    elif p == "SM_AK_Corner_5" and b[1] < -0.01:
        reason = SOUTH_CORNER
    if reason:
        not_used.append({"piece": p, "armory_layout_index": idx, "armory_loc": r4(ins["loc"]), "reason": reason})
        continue
    dz = (-GENKAN_Z) if (p in Z_SHIFT_PIECES and abs(ins["loc"][2] - GENKAN_Z) < 1e-6) else 0.0
    hb = bbox_a2h(b, dz)
    rec = {"id": f"AKI_{idx:04d}", "piece": p, "loc_m": a2h(ins["loc"], dz), "rot_z_deg": ins["rot_z"],
           "bbox_m": hb, "group": group_of(p), "hero_module": HERO.get(p), "collision_class": collision_class(p),
           "src_armory": {"layout_index": idx, "loc": r4(ins["loc"])}}
    if dz:
        rec["z_shift_m"] = round(dz, 3)
        rec["note"] = "stood on the armory's sunken genkan (-0.12): lifted +0.12 onto the hall floor"
    if "cast_shadow" in ins:
        rec["cast_shadow"] = ins["cast_shadow"]
    interior.append(rec)
    for ax, (lo, hi) in zip("xyz", (ENV["x"], ENV["y"], ENV["z"])):
        k = "xyz".index(ax)
        if hb[k] < lo - TOL or hb[k + 3] > hi + TOL:
            envelope_viol.append({"id": rec["id"], "piece": p, "axis": ax, "bbox": hb})

# the eight floor tiles that replace SM_AK_Floor_Plank_EntryBand (armory pattern: 'ABCD'[(i % 2) + 2 * (j % 2)])
for k, (x, y) in enumerate([(2, 0), (4, 0), (6, 0), (8, 0), (2, 2), (4, 2), (6, 2), (8, 2)]):
    v = "ABCD"[(x // 2) % 2 + 2 * ((y // 2) % 2)]
    p = f"SM_AK_Floor_Plank_2x2_{v}"
    interior.append({"id": f"AKI_{9001 + k}", "piece": p, "loc_m": a2h((x, y, 0.0)), "rot_z_deg": 0.0,
                     "bbox_m": bbox_a2h((x, y, -0.1, x + 2, y + 2, 0.0)), "group": "floor", "hero_module": None,
                     "collision_class": "ground",
                     "src_armory": {"layout_index": None, "loc": [x, y, 0.0],
                                    "note": "new in the hall variant: fills the EntryBand + genkan footprint"}})

used_pieces = sorted({r["piece"] for r in interior})
not_used_pieces = sorted({r["piece"] for r in not_used} - set(used_pieces))

# ------------------------------------------------------------------------------------------------ cases + items
PLANNED = {"1": "smoke bombs, paper tags, kunai + tag, stars (planned; EMPTY in the build)",
           "2": "folding fan (planned; EMPTY)", "3": "Snow Flower drawn + empty sheath (planned; EMPTY)",
           "5": "kunai (+ future tanto etc.) (planned; EMPTY)", "G1": "growth slot (EMPTY)",
           "4": "cloak on a full mannequin (planned; EMPTY)", "G3": "growth slot (EMPTY)",
           "8": "shuriken assortment: the tray SM_AK_DSP_ShurikenTray with six forms is PLACED (items below)",
           "7": "Snow Flower heels on tiers (planned; EMPTY)", "6": "kasa with attire, mannequin (planned; EMPTY)",
           "G2": "growth slot (EMPTY)", "10": "hero table on the dais: Snow Flower sheathed (planned; EMPTY)",
           "G4": "growth slot (EMPTY)", "G5": "growth slot (EMPTY)"}
case_ids = {}
for r in interior:
    if r["group"] == "case":
        case_ids.setdefault((round(r["src_armory"]["loc"][0], 3), round(r["src_armory"]["loc"][1], 3)), []).append(r["id"])
cases = []
for c in AL["cases"]:
    W, D, H, G = c["width_depth_plinth_glass_m"]
    z0 = 0.6 if c["type"] == "Hero" else 0.0
    key = (round(c["loc"][0], 3), round(c["loc"][1], 3))
    cases.append({"label": c["label"], "type": c["type"], "loc_m": a2h((c["loc"][0], c["loc"][1], z0)),
                  "rot_z_deg": c["rot_z"], "width_depth_plinth_glass_m": [W, D, H, G],
                  "plinth_piece": f"SM_AK_Case_{c['type']}_Plinth",
                  "glass_piece": (f"SM_AK_Case_{c['type']}_Glass" if G > 0 else None),
                  "instance_ids": case_ids.get(key, []), "glass_top_m": round(z0 + H + G, 3),
                  "contents": PLANNED.get(c["label"], "")})

items = []
for it in AL["items"]:
    fbx = Path(it["fbx"])
    items.append({"name": it["name"], "case": it["case"], "form": it.get("form"), "loc_m": a2h(it["loc"]),
                  "rot_z_deg": it["rot_z"], "mirror": it["mirror"], "ue_asset": it["ue_asset"],
                  "fbx": str(fbx.relative_to(ROOT)).replace("\\", "/"),
                  "fbx_sha256": sha256(fbx) if fbx.exists() else None,
                  "textures": str(Path(it["textures"]).relative_to(ROOT)).replace("\\", "/"),
                  "collision_class": "nocollision"})

# ------------------------------------------------------------------------------------------------ lights
UEL = {L["name"]: L for L in ALEV["local_lights"]}
lights = []
level_only = []
for L in AL["lights"]:
    if L["type"] == "sun":
        level_only.append({"name": L["name"], "type": "directional", "design": L,
                           "why": "sky / sun / moon / time of day stay per level (SYNC.md 6)"
                           + ("; Sun_WindowFill is an interior-only fill through the armory's west windows: in the hall "
                              "those windows face closed side strips and cavities, the shell's window backers "
                              "(SM_DKH_Rear_WindowBacker + BackerLight_*) take its role" if L["name"] == "Sun_WindowFill"
                              else "")})
        continue
    dz = 0.12 if (L["name"].startswith("Lantern_") and L["loc"][1] < 2.4 and L["loc"][2] < 0.5) else 0.0
    rec = {"name": L["name"], "type": L["type"], "role": L.get("role"), "loc_m": a2h(L["loc"], dz),
           "design": {k: v for k, v in L.items() if k not in ("loc", "aim")}}
    if "aim" in L:
        rec["aim_m"] = a2h(L["aim"], dz)
    if dz:
        rec["z_shift_m"] = dz
    u = UEL.get(L["name"])
    if u:
        rec["ue_armorylab_night"] = {k: u[k] for k in u if k not in ("loc_cm", "name", "type", "role")}
    lights.append(rec)
missing_ue = [L["name"] for L in lights if "ue_armorylab_night" not in L]
light_env_viol = [L["name"] for L in lights
                  if not (ENV["x"][0] - TOL <= L["loc_m"][0] <= ENV["x"][1] + TOL
                          and ENV["y"][0] - TOL <= L["loc_m"][1] <= ENV["y"][1] + TOL
                          and ENV["z"][0] - TOL <= L["loc_m"][2] <= ENV["z"][1] + TOL)]
n_shadow_design = sum(1 for L in lights if L["design"].get("shadows"))
n_shadow_ue = sum(1 for L in lights if L.get("ue_armorylab_night", {}).get("shadows"))
roles = {}
for L in lights:
    roles[L["role"]] = roles.get(L["role"], 0) + 1

DOJO_EXPOSURE_BIAS = DL["sun"]["exposure_bias"]                       # -6.0439 (sunset, K = 100)
ARMORY_EXPOSURE_BIAS = ALEV["environment"]["post_process"]["auto_exposure_bias"]   # -2.68 (night)
DOJO_SCALE = 2 ** (abs(DOJO_EXPOSURE_BIAS) - abs(ARMORY_EXPOSURE_BIAS))

# ------------------------------------------------------------------------------------------------ cameras (reference)
cams = []
for c in AL["cameras"]:
    if c["name"] == "CG_Garden":
        continue
    rec = {"name": c["name"], "loc_m": a2h(c["loc"]), "look_at_m": a2h(c["look_at"]), "lens_mm": c["lens_mm"]}
    if "shift_y" in c:
        rec["shift_y"] = c["shift_y"]
    if c["loc"][1] < 0:
        rec["note"] = ("outside the armory's south wall: in the hall it stands at world (%.2f, %.2f, %.2f) on the "
                       "veranda / step band under the lower roof (eave +3.0 at Y 21.5): the lower roof blocks it; "
                       "the hall needs its own entry camera (proposed CAM_HallArmoryEntry)" % tuple(h2w(rec["loc_m"])))
    cams.append(rec)

# ================================================================================================ the extension design
EXT = {"x0": 15.0, "x1": 29.0, "y0": BY1, "y1": 45.0}          # post centre lines (the hall's 2 m grid)
OUT = {"x0": EXT["x0"] - HP / 2, "x1": EXT["x1"] + HP / 2, "y1": EXT["y1"] + HP / 2}
REAR_PITCH = 25.0
OVH = 0.90                                                     # eave / verge overhang (the main upper roof's 0.9)
RIDGE_Y = (EXT["y0"] + EXT["y1"]) / 2                          # 39.5
EAVE_Y = EXT["y1"] + OVH                                       # 45.9
VERGE_X = (EXT["x0"] - OVH, EXT["x1"] + OVH)                   # 14.1 / 29.9
ARM_TOP_W = FLOOR + 5.00                                       # armory wall / coffer tops (world 5.50)
CLEAR = 0.02
# the junction: the rear roof's south slope meets the main back slope in a level valley; both slopes' rafter
# undersides must stay CLEAR above the armory's coffer tops there (the lowest point over the interior)
z_valley = ARM_TOP_W + CLEAR + max(under(UP_PITCH), under(REAR_PITCH))
y_valley = UPY1 - (z_valley - UP_EAVE) / T30
ZR = z_valley + (RIDGE_Y - y_valley) * T25                     # rear planes meet at the ridge
ZE = ZR - (EAVE_Y - RIDGE_Y) * T25                             # north eave (collision plane)
plane_post = ZE + (EAVE_Y - OUT["y1"]) * T25
REAR_PLATE_TOP = plane_post - under(REAR_PITCH) - 0.006
REAR_PLATE_BOT = REAR_PLATE_TOP - 0.24
CAP_ABOVE = UP_CAP - UP_ZR                                     # main ridge stack heights, reused
END_ABOVE = UP_END - UP_ZR
REAR_CAP = ZR + CAP_ABOVE
REAR_END = ZR + END_ABOVE


def rear_plane(y):
    return ZR - abs(y - RIDGE_Y) * T25


def main_back_plane(y):
    return UP_EAVE + (UPY1 - y) * T30


rear_under_at_armory_north = rear_plane(44.30) - under(REAR_PITCH)   # over the armory's north wall (outer face Y 44.30)
# rafter underside clearance over the armory along the rear roof (worst point = the valley)
clear_samples = []
for i in range(0, 201):
    y = y_valley + (44.30 - y_valley) * i / 200
    clear_samples.append(rear_plane(y) - under(REAR_PITCH) - ARM_TOP_W)
min_clear_rear = min(clear_samples)
main_under_at_valley = main_back_plane(y_valley) - under(UP_PITCH)

REAR = {
    "type": "gable (kirizuma) rear hall roof, ridge E-W (parallel to the main ridge), roof_kit.gable_roof language",
    "pitch_deg": REAR_PITCH,
    "eave_north": {"y": EAVE_Y, "z_collision": round(ZE, 4), "x": list(VERGE_X)},
    "verges_x": list(VERGE_X), "overhang_m": OVH,
    "ridge": {"y": RIDGE_Y, "x": list(VERGE_X), "planes_meet_z": round(ZR, 4),
              "cap_top_z_est": round(REAR_CAP, 4), "end_top_z_est": round(REAR_END, 4),
              "style": "the main hall's: r4 noshi courses + cap row, plain onigawara ends (roof_kit ridge(..., "
                       "ends='onigawara'))"},
    "valley": {"y": round(y_valley, 4), "z_collision": round(z_valley, 4), "x": list(VERGE_X),
               "note": "level valley where the rear south slope meets the main back slope (gongen-zukuri style); "
                       "the main back slope is cut along it for X 14.1-29.9 (new SM_DKH_RoofUpper_BackValley) and keeps "
                       "its eave (+5.5 at Y 34.9) only outside X 14.1-29.9, ending in end boards under the rear verges"},
    "gable_faces_x": [EXT["x0"], EXT["x1"]],
    "gable_style": "plaster in a timber frame (the hall's upper gable style), bargeboards with gegyo",
    "wall_plate": [round(REAR_PLATE_BOT, 4), round(REAR_PLATE_TOP, 4)],
    "rafters": "closely spaced capped rafters at 0.30 m (the upper roof's), soffit, eave blocking; no gutter (as the "
               "main upper roof)",
    "collision": "one walkable slab per slope (25 deg < GASP 44.77 deg), verge rolls without collision",
    "vs_main": {"main_planes_meet": UP_ZR, "main_cap_top": UP_CAP, "main_end_top": UP_END, "main_eave": UP_EAVE,
                "ridge_below_main_m": round(UP_ZR - ZR, 3), "cap_below_main_m": round(UP_CAP - REAR_CAP, 3),
                "eave_below_main_m": round(UP_EAVE - ZE, 3)},
    "clearance_over_the_armory": {"armory_top_world": ARM_TOP_W, "rule": "rafter undersides >= armory coffer / wall "
                                  "tops + 0.02", "rear_rafters_min_m": round(min_clear_rear, 4),
                                  "main_rafters_at_valley_m": round(main_under_at_valley - ARM_TOP_W, 4),
                                  "rear_rafters_over_the_armory_north_wall_m": round(rear_under_at_armory_north - ARM_TOP_W, 4)},
    "alternative_D4": "eave +5.58 / ridge +8.57 (wall plates level with the main hall's 5.447-5.687, valley at Y 34.02): "
                      "simpler walls, but the rear ridge then sits only 0.34 m under the main ridge; rejected for rev 1 "
                      "(the owner asked for a LOWER rear roof)",
}

# ================================================================================================ visibility (silhouette)


def halfspaces_box(x0, x1, y0, y1, z0, z1):
    return [((-1, 0, 0), -x0), ((1, 0, 0), x1), ((0, -1, 0), -y0), ((0, 1, 0), y1), ((0, 0, -1), -z0), ((0, 0, 1), z1)]


MAIN_SOLIDS = [
    # hip-and-gable body: below the front, back and both hip planes, above the soffit (approx. +5.0)
    [((0, -T30, 1), UP_EAVE - UPY0 * T30), ((0, T30, 1), UP_EAVE + UPY1 * T30),
     ((-T30, 0, 1), UP_EAVE - UPX0 * T30), ((T30, 0, 1), UP_EAVE + UPX1 * T30), ((0, 0, -1), -5.0),
     ((-1, 0, 0), -UPX0), ((1, 0, 0), UPX1), ((0, -1, 0), -UPY0), ((0, 1, 0), UPY1)],
    # the gabled upper part out to the verges, above the gable foot
    [((0, -T30, 1), UP_EAVE - UPY0 * T30), ((0, T30, 1), UP_EAVE + UPY1 * T30), ((0, 0, -1), -UP["gable_foot_z"]),
     ((-1, 0, 0), -UP["verge_x"][0]), ((1, 0, 0), UP["verge_x"][1])],
    halfspaces_box(14.068, 29.932, 28.72, 29.28, 8.70, UP_CAP),            # ridge cap row
    halfspaces_box(14.068, 14.60, 28.72, 29.28, 8.70, UP_END),              # onigawara ends
    halfspaces_box(29.40, 29.932, 28.72, 29.28, 8.70, UP_END),
]
T2494 = math.tan(math.radians(24.9439))
OCCLUDERS = MAIN_SOLIDS + [
    # the hall body (walls to the plates; the open door bays look into the closed armory, not through the building)
    halfspaces_box(BX0 - HP / 2, BX1 + HP / 2, BY0 - HP / 2, BY1 + HP / 2, 0.0, PLATE_TOP),
    # the lower front roof band (eave +3.0 at Y 21.5 rising to +4.17 at the wall), as its bounding slab
    [((0, -T25, 1), 3.0 - 21.5 * T25), ((0, 0, -1), -2.75), ((-1, 0, 0), -10.35), ((1, 0, 0), 33.65),
     ((0, -1, 0), -21.33), ((0, 1, 0), 24.06)],
    # the extension body (walls to its plate)
    halfspaces_box(EXT["x0"] - HP / 2, EXT["x1"] + HP / 2, EXT["y0"], EXT["y1"] + HP / 2, 0.0, REAR_PLATE_TOP),
    # the rear roof itself (self-occlusion of the far slope)
    [((0, -T25, 1), ZR - RIDGE_Y * T25), ((0, T25, 1), ZR + RIDGE_Y * T25), ((0, 0, -1), -5.0),
     ((-1, 0, 0), -VERGE_X[0]), ((1, 0, 0), VERGE_X[1]), ((0, -1, 0), -y_valley), ((0, 1, 0), EAVE_Y)],
    # storehouse / residence gable roofs (ridge N-S, planes meet +5.25, 24.94 deg) and their walls
    [((T2494, 0, 1), 5.25 + 3.3 * T2494), ((-T2494, 0, 1), 5.25 - 3.3 * T2494), ((0, 0, -1), 0.0),
     ((-1, 0, 0), 1.08), ((1, 0, 0), 7.68), ((0, -1, 0), -27.4), ((0, 1, 0), 36.0)],
    [((T2494, 0, 1), 5.25 + 40.7 * T2494), ((-T2494, 0, 1), 5.25 - 40.7 * T2494), ((0, 0, -1), 0.0),
     ((-1, 0, 0), -36.32), ((1, 0, 0), 45.08), ((0, -1, 0), -27.4), ((0, 1, 0), 36.0)],
]


def seg_hits(p, q, hs):
    t0, t1 = 0.0, 1.0
    d = [q[i] - p[i] for i in range(3)]
    for n, c in hs:
        num = c - sum(n[i] * p[i] for i in range(3))
        den = sum(n[i] * d[i] for i in range(3))
        if abs(den) < 1e-12:
            if num < 0:
                return False
            continue
        t = num / den
        if den > 0:
            t1 = min(t1, t)
        else:
            t0 = max(t0, t)
        if t0 > t1:
            return False
    return t1 - t0 > 1e-6 and t0 < 0.999


def rear_samples():
    pts = []
    x = VERGE_X[0] + 0.25
    while x <= VERGE_X[1] - 0.25 + 1e-6:
        pts.append(("ridge_cap", (x, RIDGE_Y, REAR_CAP)))
        pts.append(("north_slope_mid", (x, (RIDGE_Y + EAVE_Y) / 2, rear_plane((RIDGE_Y + EAVE_Y) / 2) + 0.05)))
        pts.append(("north_eave", (x, EAVE_Y + 0.02, ZE + 0.06)))
        pts.append(("south_slope_mid", (x, (RIDGE_Y + y_valley) / 2, rear_plane((RIDGE_Y + y_valley) / 2) + 0.05)))
        x += 0.5
    for xe in (VERGE_X[0] + 0.25, VERGE_X[1] - 0.25):
        pts.append(("ridge_end", (xe, RIDGE_Y, REAR_END)))
    for xv in VERGE_X:
        y = y_valley
        while y <= EAVE_Y + 1e-6:
            pts.append(("verge", (xv, y, rear_plane(y) + 0.12)))
            y += 0.5
    return pts


def in_frustum(cam, pt):
    loc, at = cam["loc"], cam["look_at"]
    f = [at[i] - loc[i] for i in range(3)]
    fl = math.sqrt(sum(v * v for v in f))
    f = [v / fl for v in f]
    up0 = (0.0, 0.0, 1.0)
    r = [f[1] * up0[2] - f[2] * up0[1], f[2] * up0[0] - f[0] * up0[2], f[0] * up0[1] - f[1] * up0[0]]
    rl = math.sqrt(sum(v * v for v in r)) or 1.0
    r = [v / rl for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    v = [pt[i] - loc[i] for i in range(3)]
    zf = sum(v[i] * f[i] for i in range(3))
    if zf <= 0.1:
        return False
    w, h = cam.get("out_wh", [1920, 1080])
    th = math.tan(math.radians(cam["hfov_deg"]) / 2)
    tv = th * h / w
    return abs(sum(v[i] * r[i] for i in range(3)) / zf) <= th and abs(sum(v[i] * u[i] for i in range(3)) / zf) <= tv


samples = rear_samples()
vis = {}
for cam in DL["cameras"]:
    infr = [s for s in samples if in_frustum(cam, s[1])]
    visible = [s for s in infr if not any(seg_hits(cam["loc"], s[1], hs) for hs in OCCLUDERS)]
    loc = cam["loc"]
    el_main = math.degrees(math.atan2(UP_CAP - loc[2], math.hypot(22.0 - loc[0], 29.0 - loc[1])))
    el_rear = math.degrees(math.atan2(REAR_CAP - loc[2], math.hypot(22.0 - loc[0], RIDGE_Y - loc[1])))
    kinds = {}
    for k, _p in visible:
        kinds[k] = kinds.get(k, 0) + 1
    # how far each visible sample stands above whatever hides the rest (pixels at the camera's output height)
    w, h = cam.get("out_wh", [1920, 1080])
    vfov = 2 * math.atan(math.tan(math.radians(cam["hfov_deg"]) / 2) * h / w)
    excess_px = []
    for _k, pt in visible:
        lo, hi = 0.0, pt[2] - 4.0
        if not any(seg_hits(loc, (pt[0], pt[1], pt[2] - hi), hs) for hs in OCCLUDERS):
            excess_px.append(None)
            continue
        for _ in range(30):
            mid = (lo + hi) / 2
            if any(seg_hits(loc, (pt[0], pt[1], pt[2] - mid), hs) for hs in OCCLUDERS):
                hi = mid
            else:
                lo = mid
        q = (pt[0], pt[1], pt[2] - hi)
        a = [pt[i] - loc[i] for i in range(3)]
        b2 = [q[i] - loc[i] for i in range(3)]
        cosang = sum(a[i] * b2[i] for i in range(3)) / (math.sqrt(sum(v * v for v in a)) * math.sqrt(sum(v * v for v in b2)))
        excess_px.append(math.degrees(math.acos(max(-1.0, min(1.0, cosang)))) / math.degrees(vfov) * h)
    ex = [e for e in excess_px if e is not None]
    vis[cam["name"]] = {"loc": cam["loc"], "samples_in_frustum": len(infr), "visible": len(visible),
                        "visible_by_kind": kinds,
                        "max_rise_above_occluders_px": round(max(ex), 1) if ex else 0.0,
                        "free_standing_samples": sum(1 for e in excess_px if e is None),
                        "out_h_px": cam.get("out_wh", [1920, 1080])[1],
                        "centre_ridge_elev_deg": {"main_cap": round(el_main, 2), "rear_cap": round(el_rear, 2),
                                                  "rear_minus_main": round(el_rear - el_main, 2)}}
COURTYARD_CAMS = ["CAM_GateFromCourtyard", "CAM_Establishing", "CAM_PlayerEyeSand", "CAM_HallVeranda",
                  "CAM_EstablishingRef2", "CAM_Ref2Match", "CAM_Overview", "CAM_GateFromStreet", "CAM_LandscapeRef",
                  "CAM_FromGateOut", "CAM_PeaksOverHall", "CU_R5_FarBackground", "CU_R5_Skyline", "CAM_EastYard",
                  "CAM_WallTop", "CAM_HallRoofClimb", "CU_HallUpperRoof"]

# ================================================================================================ hall shell layout
hall_inst = []
for i, ins in enumerate(DL["instances"]):
    if ins.get("kit") != "hall":
        continue
    p, (x, y, z), rz = ins["piece"], ins["loc"], ins["rot_z"]
    status, note, repl = "kept", "", None
    if p.startswith("SM_DKH_Bay") and abs(y - BY1) < 1e-6 and abs(rz - 180.0) < 1e-6 and 17.0 <= x <= 29.0:
        status, note = "removed", "main rear wall bay X %.0f-%.0f: opened into the extension" % (x - 2, x)
    elif p == "SM_DKH_Bay_Door" and abs(y - BY0) < 1e-6 and abs(rz) < 1e-6:
        status, repl, note = "replaced", "SM_DKH_Bay_DoorOpen", "centre door bay X %.0f-%.0f: doors open" % (x, x + 2)
    elif p == "SM_DKH_Frame":
        status, repl = "replaced", "SM_DKH_Frame_Open"
        note = "rear posts X 17-27 (Y 34) and their foundation / sill / skirting X 15-29 removed; collision = wall and " \
               "strip hulls with the three door openings (no closed body)"
    elif p == "SM_DKH_RoofUpper_Back":
        status, repl = "replaced", "SM_DKH_RoofUpper_BackValley"
        note = "back slope cut along the valley Y %.2f for X %.1f-%.1f" % (y_valley, VERGE_X[0], VERGE_X[1])
    b = BB.get(str(i))
    rec = {"id": f"DKH_S{i:04d}", "showcase_index": i, "piece": p, "loc_world_m": r4((x, y, z)), "rot_z_deg": rz,
           "loc_hall_m": w2h((x, y, z)), "status": status, "collision_class": ins.get("collision_class")}
    if repl:
        rec["replaced_by"] = repl
    if note:
        rec["note"] = note
    if b:
        rec["bbox_world_m"] = r4(b["min"]) + r4(b["max"])
    hall_inst.append(rec)

new_inst = []


def add_new(piece, loc_world, rz, note="", cls="building", **kw):
    rec = {"id": f"DKH_N{len(new_inst) + 1:04d}", "piece": piece, "loc_world_m": r4(loc_world), "rot_z_deg": rz,
           "loc_hall_m": w2h(loc_world), "status": "new", "collision_class": cls}
    if note:
        rec["note"] = note
    rec.update(kw)
    new_inst.append(rec)


for x in (19.0, 21.0, 23.0):
    add_new("SM_DKH_Bay_DoorOpen", (x, BY0, FLOOR), 0.0, "centre door bay X %.0f-%.0f, doors open" % (x, x + 2))
LEAF_W, LEAF_T, LEAF_Y1, LEAF_Y2 = 0.922, 0.035, BY0 + HP / 2 + 0.01, BY0 + HP / 2 + 0.05
for side in (-1, 1):
    for (xa, yy) in ((17.04, LEAF_Y1), (17.04 + LEAF_W, LEAF_Y1), (17.50, LEAF_Y2)):
        x0 = xa if side < 0 else 44.0 - xa - LEAF_W
        add_new("SM_DKH_DoorLeaf_Parked", (x0, yy, FLOOR), 0.0,
                "a hall door leaf lifted out of its track and stood against the inner face of plaster bay X %s "
                "(decision D1-A); its left edge at the loc, %.3f wide, %.3f thick, sill +0.04 to head +1.90"
                % ("17-19" if side < 0 else "25-27", LEAF_W, LEAF_T), cls="thin")
add_new("SM_DKH_Frame_Open", (22.0, 29.0, 0.0), 0.0, "replaces SM_DKH_Frame")
add_new("SM_DKH_RoofUpper_BackValley", (22.0, 29.0, 0.0), 0.0, "replaces SM_DKH_RoofUpper_Back", cls="roof")
add_new("SM_DKH_Rear_Frame", (22.0, RIDGE_Y, 0.0), 0.0,
        "extension frame: 0.24 m posts, rubble-granite foundation, sills, skirting, wall plates %.4f-%.4f, sub-floor"
        % (REAR_PLATE_BOT, REAR_PLATE_TOP))
REAR_WALL_TYPES = {29: "Lattice", 27: "Plaster", 25: "Plaster", 23: "Door", 21: "Plaster", 19: "Plaster", 17: "Lattice"}
for x, t in REAR_WALL_TYPES.items():
    add_new(f"SM_DKH_Bay_{t}", (float(x), EXT["y1"], FLOOR), 180.0,
            "extension rear wall bay X %d-%d (the old rear wall's type, moved 11 m back)%s"
            % (x - 2, x, "; closed" if t == "Door" else ""))
    add_new("SM_DKH_Bay_Transom", (float(x), EXT["y1"], FLOOR), 180.0)
    add_new("SM_DKH_Rear_Bay_ClerePlaster", (float(x), EXT["y1"], FLOOR), 180.0)
for y in (45.0, 43.0, 41.0, 39.0, 37.0):     # west wall, rot -90 spans y -> y-2
    add_new("SM_DKH_Bay_Plaster", (EXT["x0"], y, FLOOR), -90.0, "extension west wall Y %.0f-%.0f" % (y - 2, y))
    add_new("SM_DKH_Bay_Transom", (EXT["x0"], y, FLOOR), -90.0)
    add_new("SM_DKH_Rear_Bay_ClerePlaster", (EXT["x0"], y, FLOOR), -90.0)
for y in (35.0, 37.0, 39.0, 41.0, 43.0):     # east wall, rot 90 spans y -> y+2
    add_new("SM_DKH_Bay_Plaster", (EXT["x1"], y, FLOOR), 90.0, "extension east wall Y %.0f-%.0f" % (y, y + 2))
    add_new("SM_DKH_Bay_Transom", (EXT["x1"], y, FLOOR), 90.0)
    add_new("SM_DKH_Rear_Bay_ClerePlaster", (EXT["x1"], y, FLOOR), 90.0)
for (x, y, rz) in ((EXT["x0"], 35.0, -90.0), (EXT["x1"], 34.0, 90.0)):
    for t in ("Plaster", "Transom", "ClerePlaster"):
        add_new(f"SM_DKH_Rear_Bay1_{t}", (x, y, FLOOR), rz, "1 m junction bay Y 34-35 (the connecting band)")
add_new("SM_DKH_Rear_Roof", (22.0, RIDGE_Y, 0.0), 0.0, "both slopes, verges, bargeboards, soffit, rafters, valley "
        "flashing", cls="roof")
add_new("SM_DKH_Rear_RoofRidge", (22.0, RIDGE_Y, 0.0), 0.0, cls="roof")
add_new("SM_DKH_Rear_RoofGable", (22.0, RIDGE_Y, 0.0), 0.0, "west gable (plaster in a timber frame)", cls="roof")
add_new("SM_DKH_Rear_RoofGable", (22.0, RIDGE_Y, 0.0), 180.0, "east gable (the west one turned 180 deg)", cls="roof")
WIN_Y = AL["openings"]["windows_y"]
WIN_Z = AL["openings"]["window_z"]
BACKER_X = 6.45
backers = []
for side in (-1, 1):
    for (ya, yb) in WIN_Y:
        cx = side * BACKER_X
        loc_h = (cx, (ya + yb) / 2, (WIN_Z[0] + WIN_Z[1]) / 2)
        name = "BackerLight_%s%d" % ("W" if side < 0 else "E", int(ya))
        add_new("SM_DKH_Rear_WindowBacker", h2w(loc_h), -90.0 if side < 0 else 90.0,
                "lit shoji-paper panel 3.60 x 1.55 m behind armory window Y %.2f-%.2f (hall-local), facing the "
                "window; in the %s" % (ya, yb, "west side strip of the main hall" if yb <= 10.0 else
                                       ("extension cavity" if ya >= 10.0 else "side strip / cavity (crosses Y 10)")),
                cls="nocollision")
        backers.append({"light": name, "loc_m": r4(loc_h), "faces": "+x" if side < 0 else "-x"})

SHELL_PIECES_NEW = {
    "SM_DKH_Bay_DoorOpen": "the door bay's sill, head track (kamoi) and head beam (nageshi) without leaves: the "
                           "opening is clear from the sill top +0.045 to the head-track underside +1.888 (above the "
                           "floor), X 0.12-1.88 of the bay; collision only on the head (z >= 1.888)",
    "SM_DKH_DoorLeaf_Parked": "one hall door leaf (lattice over 70 %, board foot, iron pull) as a separate piece, "
                              "0.922 x 0.035 x 1.86, pivot at its left edge, sill side",
    "SM_DKH_Frame_Open": "SM_DKH_Frame without the rear posts X 17-27 at Y 34 and their foundation / sill / skirting "
                         "X 15-29; the rear plate over the opening becomes a 0.167 m beam (5.52-5.687) clear of the "
                         "armory coffers; collision: front wall hulls either side of the door band, the two door "
                         "posts, the door-head lintel hull (+2.388 up), side walls, the rear wall X 13-15 / 29-31, and "
                         "solid fills of the closed side strips X 13.12-15.70 / 28.30-30.88 (Y 24.12-33.88, +0.5 to "
                         "+5.45)",
    "SM_DKH_RoofUpper_BackValley": "SM_DKH_RoofUpper_Back with a notch X 14.1-29.9 north of the valley line Y %.2f, "
                                   "valley flashing, and end boards on the cut eave stubs" % y_valley,
    "SM_DKH_Rear_Frame": "the extension's frame: posts on X 15 / 29 at Y 35-45 (2 m) and on Y 45 at X 17-27, foundation "
                         "band (rubble granite, 0.40 wide, top +0.20), ground sill, skirting, wall plates; collision: "
                         "wall + cavity hulls (west X 14.88-15.70, east 28.30-29.12, north Y 44.30-45.12) and the "
                         "sub-floor slab X 15.12-28.88, Y 34.0-44.88, 0-0.50",
    "SM_DKH_Rear_Bay_ClerePlaster": "SM_DKH_Bay_ClerePlaster cut to the extension's lower plate: band +3.70 to %.3f "
                                    "above the floor" % (REAR_PLATE_BOT - FLOOR),
    "SM_DKH_Rear_Bay1_Plaster": "1 m version of SM_DKH_Bay_Plaster", "SM_DKH_Rear_Bay1_Transom": "1 m Bay_Transom",
    "SM_DKH_Rear_Bay1_ClerePlaster": "1 m version of SM_DKH_Rear_Bay_ClerePlaster",
    "SM_DKH_Rear_Roof": "the rear gable roof's two slopes (south from the valley, north to the eave), verges, "
                        "bargeboards, soffit, capped rafters, valley flashing",
    "SM_DKH_Rear_RoofRidge": "the rear ridge (r4 noshi courses + cap row, plain onigawara ends)",
    "SM_DKH_Rear_RoofGable": "a plaster gable in a timber frame at the extension's side wall (placed twice)",
    "SM_DKH_Rear_WindowBacker": "a lit shoji-paper panel (unit-UV cells on M_DJ_ShojiPaper, 3.60 x 1.55) on a dark "
                                "board, stood 0.15 m outside an armory window so the open lattice reads lit",
}

shell_lights = []
for bk in backers:
    shell_lights.append({"name": bk["light"], "type": "rect", "role": "window_backer", "loc_m": bk["loc_m"],
                         "faces": bk["faces"], "size_m": [3.5, 1.45], "kelvin": 3200, "shadows": False,
                         "note": "borrowed sunset light through the armory's window lattice; intensity per level "
                                 "(relight stage)"})

# ================================================================================================ site (DojoLab only)
NORTH_SHIFT = 11.0
north_wall_moves = []
for i, ins in enumerate(DL["instances"]):
    if ins.get("kit") != "kit1" or not ins["piece"].startswith("SM_DK_Wall"):
        continue
    b = BB.get(str(i))
    if not b:
        continue
    if b["min"][1] >= 35.7 and b["max"][1] <= 37.3:
        north_wall_moves.append({"showcase_index": i, "piece": ins["piece"], "from": r4(ins["loc"]),
                                 "to": r4((ins["loc"][0], ins["loc"][1] + NORTH_SHIFT, ins["loc"][2])),
                                 "rot_z_deg": ins["rot_z"]})
side_wall_adds = []
for (y_end, L) in ((40.0, 4), (44.0, 4), (46.0, 2), (47.0, 1)):
    for p, z in (("Footing", 0.0), ("Body", 0.6), ("Cap", 1.6248)):
        piece = f"SM_DK_Wall{p}_{L}m" + ("_T200" if p == "Body" else "")
        side_wall_adds.append({"piece": piece, "loc": [0.0, y_end, z], "rot_z_deg": -90.0,
                               "covers": "west wall X -1..0, Y %.0f-%.0f" % (y_end - L, y_end)})
        side_wall_adds.append({"piece": piece, "loc": [44.0, y_end - L, z], "rot_z_deg": 90.0,
                               "covers": "east wall X 44..45, Y %.0f-%.0f" % (y_end - L, y_end)})

gravel_copy = []
for i, ins in enumerate(DL["instances"]):
    if ins["piece"].startswith("SM_DKG_Gravel") and 33.9 <= ins["loc"][1] <= 36.0 and 10.0 <= ins["loc"][0] <= 34.0:
        if ins.get("removed"):
            continue
        gravel_copy.append({"showcase_index": i, "piece": ins["piece"], "from": r4(ins["loc"]),
                            "copy_to": r4((ins["loc"][0], ins["loc"][1] + NORTH_SHIFT, ins["loc"][2]))})

terrace_old = 44.0
terrace_new = 56.0
cyp = [a for a in WL["actors"] if a["group"] == "forest" and a["label"].startswith("Cypress")]
cherry_moves = [{"label": a["label"], "from": r4(a["loc"]), "to": r4((a["loc"][0], a["loc"][1] + NORTH_SHIFT, 0.0))}
                for a in WL["actors"] if a["label"] in ("CherrySlot_CS19", "CherrySlot_CS20")]
fir_drop = []
grass_in_ext = 0
grass_in_new_yards = 0
for ism in WL["ism"]:
    for r in ism["rows"]:
        x, y = r[0], r[1]
        if ism["name"].startswith("Forest") and -10 < x < 52 and terrace_old < y < terrace_new + 3.0:
            fir_drop.append({"ism": ism["name"], "xy": [round(x, 2), round(y, 2)]})
        if ism["name"].startswith("Grass"):
            if 14.6 <= x <= 29.4 and 33.8 <= y <= 45.4:
                grass_in_ext += 1
            elif -1 <= x <= 45 and 37 <= y <= 48:
                grass_in_new_yards += 1

B = {a["label"]: a for a in WL["actors"] if a["group"] == "boundary"}


def bline(label, new_centre, new_len):
    a = B[label]
    return {"label": label, "old": {"loc": r4(a["loc"]), "rot_z_deg": a["rot_z"], "size_m": a["scale"]},
            "new": {"loc": r4(new_centre), "rot_z_deg": a["rot_z"], "size_m": [new_len] + a["scale"][1:]}}


b5 = B["Boundary1v1_B5_east_edge"]
b7 = B["Boundary1v1_B7_west_edge"]
b5_y0 = b5["loc"][1] - b5["scale"][0] / 2
b7_y0 = b7["loc"][1] - b7["scale"][0] / 2
boundary_lines = [
    bline("Boundary1v1_B6_north_edge", (B["Boundary1v1_B6_north_edge"]["loc"][0], terrace_new,
                                        B["Boundary1v1_B6_north_edge"]["loc"][2]), B["Boundary1v1_B6_north_edge"]["scale"][0]),
    bline("Boundary1v1_B5_east_edge", (b5["loc"][0], (b5_y0 + terrace_new) / 2, b5["loc"][2]), terrace_new - b5_y0),
    bline("Boundary1v1_B7_west_edge", (b7["loc"][0], (b7_y0 + terrace_new) / 2, b7["loc"][2]), terrace_new - b7_y0),
]

wr5 = [a for a in WL["actors"] if a["label"].startswith("WR2_WR3_WR4_WR5_") and a["loc"][0] == 49.0 and a["loc"][1] >= 34]
wr5_end = [a for a in wr5 if "EndR" in a["label"]]

blk = {ins["piece"]: (i, BB[str(i)]) for i, ins in enumerate(DL["instances"]) if ins.get("collision_class") == "boundary"}


def box_of(piece):
    i, b = blk[piece]
    return r4(b["min"]) + r4(b["max"])


SITE = {
    "frame": "dojo layout frame (world m)",
    "extension_footprint": {"posts_x": [EXT["x0"], EXT["x1"]], "posts_y": [EXT["y0"], EXT["y1"]],
                            "outer_faces": {"x": [OUT["x0"], OUT["x1"]], "y_north": OUT["y1"]},
                            "foundation_band": {"x": [EXT["x0"] - 0.20, EXT["x1"] + 0.20], "y_north": EXT["y1"] + 0.20},
                            "roof_plan": {"x": list(VERGE_X), "y": [round(y_valley, 4), EAVE_Y]},
                            "depth_m": EXT["y1"] - EXT["y0"], "width_m": EXT["x1"] - EXT["x0"]},
    "north_wall": {
        "shift_m": NORTH_SHIFT,
        "old": {"body": [-1.0, 45.0, 36.0, 37.0], "footing_y": [35.94, 37.06], "cap_y": [35.76, 37.24]},
        "new": {"body": [-1.0, 45.0, 47.0, 48.0], "footing_y": [46.94, 48.06], "cap_y": [46.76, 48.24],
                "walk_top_z": 2.0, "cap_visual_top_z": 2.13},
        "why_11": "keeps the rear alley's section: old hall rear post face Y 34.12 -> wall Y 36.0 = 1.88 m; new extension "
                  "rear post face Y 45.12 -> wall Y 47.0 = 1.88 m; the rear eave overhang (0.9 m) is the same",
        "moved_instances": north_wall_moves,
        "side_wall_additions": side_wall_adds,
        "side_wall_note": "the kit1 run is footing + body (T200) + cap per module (4 / 2 / 1 m); the existing pieces keep "
                          "their places; the NW / NE corner sets move +11 with the north wall (listed in "
                          "moved_instances)",
    },
    "rear_alley": {"old": {"y": [34.12, 36.0], "x": [10.5, 33.5]},
                   "new": {"y": [OUT["y1"], 47.0], "x": [OUT["x0"], OUT["x1"]],
                           "note": "behind the extension; beside it the rear yards X 0-14.88 and 29.12-44, Y 34-47 (out of "
                                   "the 1v1, reachable in the BR)"},
                   "gravel_copies": gravel_copy,
                   "gravel_note": "the old alley strip stays (hidden under the extension where it is covered); its "
                                  "pieces are COPIED +11 m to the new alley; the new rear yards get landscape gravel / "
                                  "grass at z 0.0"},
    "closure_1v1": {
        "rule": "the alley closure stays: everything north of the hall's rear line is out of the 1v1 except the hall "
                "interior, which now runs on into the extension; every 1v1 blocker is Pawn-only, hidden, to +20.0",
        "unchanged": ["SM_DKX_1v1_PocketSide_W", "SM_DKX_1v1_PocketSide_E", "SM_DKX_1v1_CorridorRoof_W",
                      "SM_DKX_1v1_CorridorRoof_E", "SM_DKX_1v1_OutbuildingRoof_W", "SM_DKX_1v1_OutbuildingRoof_E",
                      "SM_DKX_1v1_HallUpperRear", "SM_DKX_AlleyFence_W", "SM_DKX_AlleyFence_E",
                      "SM_DKX_PocketFence_W", "SM_DKX_PocketFence_E"],
        "SM_DKX_1v1_HallRear": {"old_box": box_of("SM_DKX_1v1_HallRear"),
                                "new": [{"name": "SM_DKX_1v1_HallRear_W", "box": [10.4, 34.0, 0.0, OUT["x0"], 34.1, 20.0]},
                                        {"name": "SM_DKX_1v1_HallRear_E", "box": [OUT["x1"], 34.0, 0.0, 33.6, 34.1, 20.0]}],
                                "why": "its middle X 14.88-29.12 would cut the interior; the extension's closed walls "
                                       "take over there"},
        "SM_DKX_1v1_RearRoof (new)": {"box": [VERGE_X[0] - 0.2, 34.1, round(REAR_PLATE_BOT + 0.10, 3),
                                              VERGE_X[1] + 0.2, EAVE_Y + 0.2, 20.0],
                                      "why": "caps the extension and its rear roof (out of the 1v1); bottom above the "
                                             "armory ceiling (world +5.30) and the interior"},
        "SM_DKX_1v1_NorthWallTop": {"old_box": box_of("SM_DKX_1v1_NorthWallTop"),
                                    "new_box": [-1.0, 47.0, 2.0, 45.0, 48.0, 20.0]},
        "SM_DGB_Boundary_1v1 (ring, 11 UCX)": {"old_bbox": box_of("SM_DGB_Boundary_1v1"),
                                              "new_bbox": [-1.1, -1.1, 0.0, 45.1, 48.1, 20.1],
                                              "how": "north hull +11 m, west / east hulls 11 m longer (mesh rebuild "
                                                     "in the grey-box builder or two added box actors)"},
        "terrace_lines": boundary_lines,
        "proof_needed": "1v1 CONTROLs: veranda corners into the rear yards (both sides), corridor / outbuilding roofs "
                        "north, the extension walls from inside, the rear roof from the main roof and from the side "
                        "lower roofs, the new alley ends",
    },
    "traversal_markers": {"Wall_N": {"old": [-1, 45, 36, 37, 0, 2.0], "new": [-1, 45, 47, 48, 0, 2.0]},
                          "Wall_W_N": {"old": [-1, 0, 27.4, 36, 0, 2.0], "new": [-1, 0, 27.4, 47, 0, 2.0]},
                          "Wall_E_N": {"old": [44, 45, 27.4, 36, 0, 2.0], "new": [44, 45, 27.4, 47, 0, 2.0]},
                          "climb_route_O_north": {"old_stance": [22.0, 37.45], "new_stance": [22.0, 48.45]},
                          "all_others": "unchanged"},
    "terrace_and_terrain": {
        "north_strip": {"old_y": [37.0, terrace_old], "new_y": [48.0, terrace_new], "z": 0.0},
        "terrace_north_edge": {"old_y": terrace_old, "new_y": terrace_new,
                               "why_12_not_11": "the east terrace wall WR5 is built of 4 m / 2 m modules: + 4 + 4 + 2 + 2 "
                                                "m ends it at Y 56 (the closest whole-module edge that keeps the old 7 m "
                                                "strip behind the wall; Y 54 would leave 6 m)"},
        "compound_yards_new": {"x": [0.0, 44.0], "y": [37.0, 47.0], "z": 0.0,
                               "under_the_extension": {"x": [14.6, 29.4], "y": [33.8, 45.4], "z": -0.30}},
        "LS_Valley_north_hill_spot_heights": {"old": {"44": 0, "60": 6, "100": 20, "200": 45, "400": 90},
                                              "new": {"56": 0, "72": 6, "112": 20, "200": 45, "400": 90}},
        "WR5_east_terrace_wall": {"existing_north_end": [{"label": a["label"], "loc": a["loc"]} for a in wr5],
                                  "add": [{"piece": "SM_DKT_Wall_4m_H3", "loc": [49.0, 44.0, 0.0], "rot_z_deg": 90.0},
                                          {"piece": "SM_DKT_Wall_4m_H3", "loc": [49.0, 48.0, 0.0], "rot_z_deg": 90.0},
                                          {"piece": "SM_DKT_Wall_2m_H3", "loc": [49.0, 52.0, 0.0], "rot_z_deg": 90.0},
                                          {"piece": "SM_DKT_Wall_2m_H3", "loc": [49.0, 54.0, 0.0], "rot_z_deg": 90.0}],
                                  "move": [{"label": a["label"], "from": a["loc"], "to": [49.0, terrace_new, 0.0]}
                                           for a in wr5_end],
                                  "note": "the foot of the extension at x 49-58, y 44-56 is the river bank (rocks at "
                                          "-1.4..-3.5): H3 fits; re-check the bank rocks BankB_25 / 30 / 48 for "
                                          "intersection"},
        "cherry_slots": cherry_moves,
        "cypress_front_row": {"old": [{"label": a["label"], "loc": r4(a["loc"])} for a in cyp],
                              "new_y": "old y + 12 (behind the new terrace edge; z re-snapped to LS_Valley)"},
        "forest_FZ1": {"old_south_edge_y": 46.0, "new_south_edge_y": 58.0, "fir_instances_to_drop_or_reseat":
                       len(fir_drop), "list": fir_drop},
        "grass_ism": {"inside_the_extension_footprint_remove": grass_in_ext,
                      "in_the_new_rear_yards_keep_or_thin": grass_in_new_yards,
                      "new_north_strip": "re-scatter y 48-56 as the old strip"},
        "dead_BR_route_note": "BR_road_up_the_kerb_into_the_west_lane_north ends along y 43 into x 20: that leg now "
                              "crosses the extended west wall (it is one of the dead routes through the removed town; "
                              "mark it with the other four)",
    },
    "dojolab_cameras_to_reaim": {"CU_R6_AlleyAbove": "+11 m in y (the alley moved)", "CU_R6_PocketAboveW":
                                 "stands at (4, 39, 9): now over the new rear yard; re-aim or retire",
                                 "CU_R5_AlleyFence": "unchanged (the fence stays)"},
}

# ================================================================================================ interface
interface = {
    "revision": REV, "date": DATE,
    "units": "metres; hall-local unless a key says world",
    "frames": {
        "hall_local": "origin = the hall's centre door threshold (the door-bay sill centre line, world X 22.0 / Y 24.0) "
                      "at finished floor level (world +0.50); +X east, +Y north into the hall, +Z up",
        "hall_local_to_dojo_world": "world = hall_local + (22.0, 24.0, 0.5); Unreal cm = (x*100, -y*100, z*100), "
                                    "yaw = -rot_z",
        "armory_frame_to_hall_local": "hall_local = armory + (-6.0, 0.0, 0.0) (pure translation; rotations unchanged)",
        "hall_local_to_armorylab": "to keep ArmoryLab's interior where it is: armorylab_world = hall_local + (6.0, 0.0, "
                                   "0.0); the hall's courtyard grade is then at armorylab z -0.50",
    },
    "floor_levels": {
        "hall_ffl_world": FLOOR,
        "armory_floor": "armory z 0.00 = hall-local 0.00 = world +0.50 (the armory planks' tops)",
        "approach_world": {"courtyard": 0.0, "step_band_plinth_top": 0.15, "stair_treads_X20-24": [0.1667, 0.3333, 0.5],
                           "veranda_deck": 0.5, "door_sill_top": round(FLOOR + SILL_TOP, 3), "armory_floor": FLOOR},
        "genkan": "NOT used: the armory's sunken genkan (-0.12), its step beam and its +0.04 exterior sill are dropped; "
                  "the hall's step band + veranda + door sill are the entry; largest step inside the door = the sill "
                  "0.045",
        "lifted_pieces": "the two entry floor lanterns and the entry mat stood on the genkan floor: lifted +0.12 onto "
                         "the floor (the mat's top is then +0.084, decision D3)",
        "rear_dais": {"flight_foot_y": 15.85, "risers": 4, "riser_m": 0.15, "deck_z": 0.60, "deck_front_y": 16.90,
                      "deck_world_z": round(FLOOR + 0.60, 2)},
    },
    "envelope": {
        "inner_faces": {"west_x": -6.0, "east_x": 6.0, "south_y": 0.0, "north_y": 20.0},
        "with_walls": {"x": list(ENV["x"]), "y": list(ENV["y"]), "z": list(ENV["z"])},
        "floor_z": 0.0, "ceiling_z": 4.80, "coffer_underside_z": 4.635, "beam_underside_z": 4.40, "top_z": 5.00,
        "rule": "every interior piece and light stays inside 'with_walls' (tolerance 0.012); the shell stays outside it "
                "except the listed intrusions",
        "shell_intrusions": [
            {"what": "front wall infill / posts / sill", "x": [-6.0, 6.0], "y": [-0.12, 0.12], "z": [-0.02, 5.36]},
            {"what": "parked door leaves (D1-A)", "x": [-4.96, -3.04], "y": [round(LEAF_Y1 - BY0, 3),
                                                                                  round(LEAF_Y2 + LEAF_T - BY0, 3)],
             "z": [0.04, 1.90], "mirror": "x [3.04, 4.96]"},
            {"what": "front wall plate (outer bays) over the armory side walls / south coffers: hidden 5.3 cm "
                     "overlap inside the wall", "x": [-6.3, -5.0], "y": [0.0, 0.12], "z": [round(PLATE_BOT - FLOOR, 3), 5.0],
             "mirror": "x [5.0, 6.3]"},
        ],
        "measured_clearances": {
            "extension_cavity_m": round((16.0 - 0.30) - (EXT["x0"] + HP / 2), 3),
            "extension_rear_cavity_m": round((EXT["y1"] - HP / 2) - (44.0 + 0.30), 3),
            "side_strip_clear_m": round((16.0 - 0.30) - (BX0 + HP / 2), 3),
            "rear_roof_rafters_over_armory_min_m": round(min_clear_rear, 4),
            "main_rear_plate_beam": "raised to 5.52-5.687 world over the opening (SM_DKH_Frame_Open): 0.02 over the "
                                    "coffer tops",
        },
    },
    "door_openings": {
        "bays_x": [[-3.0, -1.0], [-1.0, 1.0], [1.0, 3.0]],
        "clear_x": [[-2.88, -1.12], [-0.88, 0.88], [1.12, 2.88]],
        "posts_x": [-3.0, -1.0, 1.0, 3.0], "post_w": HP,
        "sill": {"y": list(SILL_Y), "top_z": SILL_TOP},
        "head_track_underside_z": round(KAMOI_UNDER, 3),
        "clear_height_over_sill_m": round(KAMOI_UNDER - SILL_TOP, 3),
        "clear_width_each_m": 1.76,
        "state": "open: leaves lifted out and parked (D1-A)",
        "entry_apron": {"x": [-3.12, 3.12], "y": [0.0, 1.20], "rule": "the interior keeps it free of pieces"},
        "gasp_capsule": {"radius": 0.30, "height": 1.72, "headroom_margin_m": round(KAMOI_UNDER - SILL_TOP - 1.72, 3)},
    },
    "sun_through_the_doors": {
        "sun": {k: DL["sun"][k] for k in ("elev_deg", "azimuth_deg_from_x", "travel_dir")},
        "result": "grazing: the sunset travels east-north-east at 7.3 deg to the front wall; the lower front roof "
                  "(eave +3.0 at Y 21.5) and the veranda keep it off the door band except low rays from the west along "
                  "the veranda, which land within ~0.4 m inside the sills; the interior is lit by the design lights "
                  "and sky / bounce through the doors (check in engine at the relight stage)",
    },
    "bays_the_interior_may_touch": {
        "front_wall_inner_face": [
            {"bay_x": [-7.0, -5.0], "type": "Lattice (closed; dark board inside)", "interior_may_dress": "x -6.0..-5.0"},
            {"bay_x": [-5.0, -3.0], "type": "Plaster", "interior_may_dress": "no (parked leaves, D1-A)"},
            {"bay_x": [-3.0, 3.0], "type": "DoorOpen x3", "interior_may_dress": "no (entry apron)"},
            {"bay_x": [3.0, 5.0], "type": "Plaster", "interior_may_dress": "no (parked leaves, D1-A)"},
            {"bay_x": [5.0, 7.0], "type": "Lattice", "interior_may_dress": "x 5.0..6.0"},
        ],
        "main_rear_wall_line_y10": "opened over x -7..7 (posts at x -5..5 removed): the interior runs through",
        "extension_walls": "never touched (0.58 m cavity on three sides)",
        "side_strips": "never touched (closed shell volumes x -9..-6.30 and 6.30..9 for y 0..10)",
        "ceiling": "nothing of the shell below z 5.02 over the envelope except the front plate overlap",
    },
    "window_backers": {"armory_windows_y": WIN_Y, "window_z": WIN_Z, "backer_x": [-BACKER_X, BACKER_X],
                       "backers": backers, "owner": "shell (hall_shell_layout.json, lights BackerLight_*)"},
    "gameplay": {
        "collision_classes": {**DL["collision_classes"],
                              "glass": {"pawn": "block", "camera": "ignore", "visibility": "ignore",
                                        "note": "PROPOSED for the display-case glass hoods: blocks the player, the camera "
                                                "and line-of-sight pass (see-through)"}},
        "unwalkable_props": "display cases (plinth + glass), lanterns, vases: CanCharacterStepUpOn = No and an "
                            "unwalkable slope override (decision D6: no standing on the cases)",
        "interior_in_1v1": True,
        "walk_routes_new_world": {},
        "controls_new_world": {},
        "notes": ["CONTROL_into_the_hall (22,23)->(22,26) passed through the closed body; it now PASSES (centre door): "
                  "renamed to a walk route; new CONTROLs through the closed lattice bays X 15-17 / 27-29",
                  "every other walk / climb / alley / GASP number stays; the rear roof is out of the 1v1 "
                  "(SM_DKX_1v1_RearRoof) and walkable in the BR (25 deg slabs)"],
    },
    "site": SITE,
    "decisions": [
        {"id": "D1", "q": "the centre doors", "rev1": "A: the six leaves lifted out of their tracks and parked in two "
                                                      "layers against the inner face of plaster bays X 17-19 / 25-27: "
                                                      "three clear 1.76 x 1.84 m openings",
         "alt": "B: slid within each bay (both leaves stacked at one jamb): 0.85 m clear per bay, no parked leaves"},
        {"id": "D2", "q": "the armory's jamb posts + wall lanterns (SM_AK_Post_Jamb_480, SM_AK_H_WallSconce)",
         "rev1": "not placed (they would stand in the parked leaves)",
         "alt": "with D1-B or leaves stored out of view: place them at hall-local x +-3.83..4.45, y 0..0.86"},
        {"id": "D3", "q": "the entry mat (made for the sunken genkan)", "rev1": "lifted +0.12 onto the floor (top +0.084)",
         "alt": "drop it, or the armory chat makes a flush variant"},
        {"id": "D4", "q": "rear roof height", "rev1": "eave +%.2f, ridge +%.2f (0.76 under the main ridge)" % (ZE, ZR),
         "alt": REAR["alternative_D4"]},
        {"id": "D5", "q": "the armory's side windows (they face closed strips / cavities in the hall)",
         "rev1": "lit backers behind each window (shell)", "alt": "the armory chat closes the windows (its kit has "
                                                                     "west_closed_windows_y)"},
        {"id": "D6", "q": "standing on display cases", "rev1": "no (unwalkable)", "alt": "allow (parkour)"},
        {"id": "D7", "q": "interior shadow budget in DojoLab", "rev1": "the armory's 12 shadowed case lights; DojoLab "
                                                                      "may switch more off per level (perf)",
         "alt": "MegaLights"},
    ],
}

# walk routes (armory routes that stay inside, plus door entries); world coords at floor +0.5
SKIP_ROUTES = {"outside_through_entrance_to_mat", "mat_up_the_step_beam_to_case1", "genkan_axis_up_the_beam",
               "genkan_up_the_beam_beside_west_lantern", "genkan_up_the_beam_beside_east_lantern",
               "courtyard_start_along_path_through_entrance", "outside_through_gate_to_start",
               "courtyard_round_west_to_tsukubai_front", "courtyard_round_east_past_lantern",
               "CONTROL_must_hit_stone_lantern", "inside_along_west_parked_leaf_to_jamb_post",
               "inside_along_east_parked_leaf_to_jamb_post", "genkan_west_end_up_the_return_to_wall_walk",
               "genkan_east_end_up_the_return_to_wall_walk"}
wr = {}
cr = {}
for name, r in AWALK["routes"].items():
    if name in SKIP_ROUTES:
        continue
    pts = [h2w(a2h((p[0], p[1], 0.0)))[:2] for p in r["points"]]
    rec = {"floor_z": FLOOR, "points": pts, "source": "armory walk_check.json '%s' (hall frame)" % name}
    (cr if name.startswith("CONTROL") else wr)["ARM_" + name] = rec
wr["HALL_veranda_through_centre_door_round_case1_to_west_aisle"] = {
    "floor_z": FLOOR, "points": [[22.0, 23.0], [22.0, 25.2], [20.25, 26.4], [20.1, 39.0]]}
wr["HALL_veranda_through_west_door_past_the_lantern"] = {
    "floor_z": FLOOR, "points": [[20.0, 23.0], [20.0, 24.9], [20.4, 25.3], [20.4, 27.0], [20.1, 30.0]]}
wr["HALL_veranda_through_east_door_past_the_lantern"] = {
    "floor_z": FLOOR, "points": [[24.0, 23.0], [24.0, 24.9], [23.6, 25.3], [23.6, 27.0], [23.9, 30.0]]}
wr["HALL_gate_path_steps_veranda_door_to_dais"] = {
    "floor_z": 0.0, "points": [[22.0, 0.5], [22.0, 21.0], [22.0, 23.0], [22.0, 25.2], [20.25, 26.4], [20.1, 39.45],
                               [20.3, 39.45], [20.3, 41.42]], "note": "ends on the dais deck +1.10"}
cr["CONTROL_hall_front_lattice_bay_W"] = {"floor_z": FLOOR, "points": [[16.0, 23.0], [16.0, 25.5]]}
cr["CONTROL_hall_front_lattice_bay_E"] = {"floor_z": FLOOR, "points": [[28.0, 23.0], [28.0, 25.5]]}
cr["CONTROL_hall_front_plaster_bay_W"] = {"floor_z": FLOOR, "points": [[18.0, 23.0], [18.0, 25.5]]}
cr["CONTROL_interior_into_west_strip"] = {"floor_z": FLOOR, "points": [[17.0, 30.5], [14.5, 30.5]]}
cr["CONTROL_interior_into_east_strip"] = {"floor_z": FLOOR, "points": [[27.0, 30.5], [29.5, 30.5]]}
cr["CONTROL_interior_into_west_cavity"] = {"floor_z": FLOOR, "points": [[17.0, 38.0], [14.0, 38.0]]}
cr["CONTROL_interior_into_east_cavity"] = {"floor_z": FLOOR, "points": [[27.0, 38.0], [30.0, 38.0]]}
cr["CONTROL_dais_through_the_north_wall"] = {"floor_z": FLOOR + 0.6, "points": [[22.0, 43.2], [22.0, 46.0]],
                                             "note": "hits the hero table / painting wall first"}
cr["CONTROL_veranda_W_corner_into_rear_yard"] = {"floor_z": FLOOR, "points": [[12.1, 33.2], [14.2, 36.0]]}
cr["CONTROL_veranda_E_corner_into_rear_yard"] = {"floor_z": FLOOR, "points": [[31.9, 33.2], [29.8, 36.0]]}
interface["gameplay"]["walk_routes_new_world"] = wr
interface["gameplay"]["controls_new_world"] = cr

# ================================================================================================ interior_layout.json
interior_layout = {
    "revision": REV, "date": DATE, "owner": "armory chat (interior)", "written_by": CHAT,
    "source": {"armory_layout": "WorkFiles/armory/build/layout.json (r20, night_r20, 618 instances, 116 pieces)",
               "handoff": "WorkFiles/armory/ARMORY_HANDOFF_DOJO.md did not exist at survey time (%s): derived from the "
                          "armory's own layout data, scripts, notes and renders" % ("present" if HANDOFF.exists() else "absent"),
               "armory_unreal": "WorkFiles/armory/build/unreal/{import,materials,level}.json (ArmoryLab r20)"},
    "units": "metres, HALL-LOCAL (interface.json frames); rot_z in degrees about +Z (Unreal yaw = -rot_z)",
    "frame_conversion": interface["frames"],
    "room": {"interior_x": [-6.0, 6.0], "interior_y": [0.0, 20.0], "ceiling_z": 4.8, "dais_deck_z": 0.6,
             "dais_front_y": AL["room"]["platform_front_y"], "windows_y": WIN_Y, "window_z": WIN_Z,
             "door": "the hall's three centre door bays (interface.json door_openings); the armory's own 4 m entrance "
                     "is not used"},
    "pieces": {p: {"fbx": f"Exports/ArmoryKit/{p}.fbx", "ue_mesh": f"/Game/ArmoryKit/Meshes/{p}",
                   "slots": SLOTS.get(p, {}), "hero_module": HERO.get(p), "group": group_of(p),
                   "collision_class": collision_class(p), "ucx": AIMP["meshes"].get(p, {}).get("convex"),
                   "tris_lod0": AIMP["meshes"].get(p, {}).get("tris_lod0"),
                   "nanite_armorylab": AIMP["meshes"].get(p, {}).get("nanite")} for p in used_pieces},
    "instances": interior,
    "cases": cases,
    "items": items,
    "not_used_in_the_hall": {"pieces_with_no_instance_used": not_used_pieces, "instances": not_used},
    "cameras_reference": cams,
    "counts": {},
}
grp = {}
for r in interior:
    grp[r["group"]] = grp.get(r["group"], 0) + 1
interior_layout["counts"] = {"instances": len(interior), "pieces": len(used_pieces), "by_group": grp,
                             "cases": len(cases), "items": len(items), "not_used_instances": len(not_used),
                             "not_used_ext_akx": sum(1 for r in not_used if r["piece"].startswith("SM_AKX_")),
                             "envelope_violations": len(envelope_viol)}

lights_design = {
    "revision": REV, "date": DATE, "owner": "armory chat (interior design lights)", "written_by": CHAT,
    "units": "hall-local metres; Unreal values as ArmoryLab's night preset (K = 100 lux per Blender W/m2, manual "
             "exposure bias %.2f)" % ARMORY_EXPOSURE_BIAS,
    "travels_with_the_interior": "every light below (SYNC.md 6); sky / sun / moon / fog / exposure stay per level",
    "level_scale": {"ArmoryLab": 1.0,
                    "DojoLab": round(DOJO_SCALE, 3),
                    "derivation": "DojoLab's sunset exposure bias %.4f vs ArmoryLab night %.2f: 2^(%.4f - %.2f) = %.3f "
                                  "(starting value; the relight stage measures and sets it)"
                                  % (DOJO_EXPOSURE_BIAS, ARMORY_EXPOSURE_BIAS, abs(DOJO_EXPOSURE_BIAS),
                                     abs(ARMORY_EXPOSURE_BIAS), DOJO_SCALE)},
    "shadow_policy": {"design_shadowed": n_shadow_design, "armorylab_ue_shadowed": n_shadow_ue,
                      "armorylab_budget": 12, "dojolab": "decision D7"},
    "counts": {"lights": len(lights), "by_role": roles, "missing_ue_values": missing_ue,
               "outside_the_envelope": light_env_viol},
    "lights": lights,
    "level_only_not_travelling": level_only,
}

# ================================================================================================ hall_shell_layout
hall_shell = {
    "revision": REV, "date": DATE, "owner": "dojo chat (shell)", "written_by": CHAT, "status": "DRAFT (rev 1 design; "
                                                                                              "SM_DKH_Rear* not built yet)",
    "units": "metres; loc_world_m in the dojo layout frame, loc_hall_m in hall-local",
    "frames": interface["frames"],
    "hall": {"floor": FLOOR, "body": HN["body"], "veranda": HN["veranda"], "bays_m": 2.0,
             "front": "P W P D D D P W P (X 13-31)", "head_beam_world": round(FLOOR + 2.17, 3),
             "door_head_track_underside_world": round(FLOOR + KAMOI_UNDER, 3),
             "wall_plate_world": HN["wall_plate"], "centre_plate_world": CPLATE,
             "lower_roof": {"eave": HN["lower_roof"]["eave"], "at_wall": HN["lower_roof"]["at_wall"]},
             "upper_roof": {"eave": UP_EAVE, "rect": UP["rect"], "pitch": UP_PITCH, "planes_meet": UP_ZR,
                            "ridge_cap_top": UP_CAP, "ridge_end_top": UP_END,
                            "note": "the brief's '+8.7' matches the hip / gable-end tops (+8.729); the planes meet at "
                                    "+8.906 and the ridge cap tops out at +9.365: all unchanged"}},
    "extension": {"posts": EXT, "outer_faces": OUT, "depth_m": EXT["y1"] - EXT["y0"], "width_m": EXT["x1"] - EXT["x0"],
                  "floor_world": FLOOR, "wall_plate_world": [round(REAR_PLATE_BOT, 4), round(REAR_PLATE_TOP, 4)],
                  "bays": {"rear_Y45": REAR_WALL_TYPES, "sides": "plaster, 2 m bays Y 35-45 + a 1 m junction bay "
                                                                  "Y 34-35"},
                  "roof": REAR},
    "pieces_existing": {p: {"fbx": f"Exports/DojoKit/Hall/{p}.fbx", "note": v.get("note"), "class": v.get("class")}
                        for p, v in HL["pieces"].items()},
    "pieces_new": SHELL_PIECES_NEW,
    "instances_existing": hall_inst,
    "instances_new": new_inst,
    "lights": shell_lights,
    "counts": {"existing": len(hall_inst),
               "kept": sum(1 for r in hall_inst if r["status"] == "kept"),
               "removed": sum(1 for r in hall_inst if r["status"] == "removed"),
               "replaced": sum(1 for r in hall_inst if r["status"] == "replaced"),
               "new": len(new_inst), "new_pieces": len(SHELL_PIECES_NEW)},
}

# ================================================================================================ manifest
fbx_list = {}
drift = []
for p in used_pieces:
    f = EXPORTS_AK / f"{p}.fbx"
    s = sha256(f)
    fbx_list[p] = {"path": f"Exports/ArmoryKit/{p}.fbx", "sha256": s, "bytes": f.stat().st_size, "owner": "armory",
                   "ue_mesh": f"/Game/ArmoryKit/Meshes/{p}"}
    s_ue = AIMP["meshes"].get(p, {}).get("sha256")
    if s_ue and s_ue != s:
        drift.append(p)
for p in HL["pieces"]:
    f = EXPORTS_HALL / f"{p}.fbx"
    if f.exists():
        rec = {"path": f"Exports/DojoKit/Hall/{p}.fbx", "sha256": sha256(f), "bytes": f.stat().st_size, "owner": "dojo",
               "ue_mesh": f"/Game/DojoKit/Hall/Meshes/{p}"}
        sc = f.with_suffix(".sockets.json")
        if sc.exists():
            rec["sidecar_sha256"] = sha256(sc)
        rec["used_in_rev1"] = p not in ("SM_DKH_Frame", "SM_DKH_RoofUpper_Back")
        fbx_list[p] = rec
item_fbx = {it["name"]: {"path": it["fbx"], "sha256": it["fbx_sha256"], "ue_mesh": it["ue_asset"]} for it in items}

mi_used = sorted({mi for p in used_pieces for mi in SLOTS.get(p, {})})
masters = sorted({AMAT["instances"][mi]["master"] for mi in mi_used if mi in AMAT["instances"]})
tex_used = sorted({t for mi in mi_used for t in AMAT["instances"].get(mi, {}).get("textures", {}).values()})
tex = {}
for t in tex_used:
    rec = {}
    png = EXPORTS_AK / "Textures" / f"{t}.png"
    if png.exists():
        rec["png"] = f"Exports/ArmoryKit/Textures/{t}.png"
        rec["png_sha256"] = sha256(png)
    ua = ARMORYLAB_CONTENT / "ArmoryKit/Textures" / f"{t}.uasset"
    if ua.exists():
        rec["armorylab_uasset_sha256"] = sha256(ua)
    if not rec:
        rec["missing"] = True
    tex[t] = rec
mat_assets = {}
for m in mi_used + masters:
    ua = ARMORYLAB_CONTENT / "ArmoryKit/Materials" / f"{m}.uasset"
    mat_assets[m] = {"armorylab_uasset": f"ArmoryLab/Content/ArmoryKit/Materials/{m}.uasset",
                     "sha256": sha256(ua) if ua.exists() else None,
                     "kind": "master" if m in masters else "instance",
                     "master": AMAT["instances"].get(m, {}).get("master")}

PENDING = sorted(set(SHELL_PIECES_NEW))
manifest = {
    "revision": REV,
    "date": DATE,
    "chat": CHAT,
    "lock": "WorkFiles/locks/armoryhall.json (asset name ArmoryHall)",
    "change_log": [{"rev": 1, "date": DATE, "chat": "dojo",
                    "summary": "created the shared armory_hall folder: the armory's r20 interior converted to hall-local "
                               "(%d instances, %d pieces, %d design lights, %d cases, %d items), the hall shell with the "
                               "rear extension design (%d new instances, %d new SM_DKH pieces pending build), interface, "
                               "SYNC rules" % (len(interior), len(used_pieces), len(lights), len(cases), len(items),
                                               len(new_inst), len(SHELL_PIECES_NEW)),
                    "files": ["SYNC.md", "manifest.json", "interior_layout.json", "hall_shell_layout.json",
                              "lights_design.json", "interface.json"]}],
    "last_synced": {"DojoLab": None, "ArmoryLab": None,
                    "note": "each project records the revision it last synced in its own notes (SYNC.md 3)"},
    "fbx": fbx_list,
    "item_fbx": item_fbx,
    "retired": [],
    "pending_fbx": {p: {"owner": "dojo", "status": "designed in rev 1; build in the Blender stage"} for p in PENDING},
    "materials": {"source": "ArmoryLab/Content/ArmoryKit/Materials (file copy into DojoLab, never an edit)",
                  "masters": masters, "instances": mi_used, "assets": mat_assets},
    "textures": tex,
    "checks": {"armorylab_import_sha_drift": drift},
}

# ================================================================================================ write
SH.mkdir(parents=True, exist_ok=True)
SV.mkdir(parents=True, exist_ok=True)
jdump(SH / "interior_layout.json", interior_layout)
jdump(SH / "lights_design.json", lights_design)
jdump(SH / "interface.json", interface)
jdump(SH / "hall_shell_layout.json", hall_shell)
jdump(SH / "manifest.json", manifest)

report = {
    "date": DATE, "handoff_present": HANDOFF.exists(),
    "interior": interior_layout["counts"], "envelope_violations": envelope_viol,
    "lights": lights_design["counts"], "light_shadows": lights_design["shadow_policy"],
    "level_scale_dojolab": round(DOJO_SCALE, 3),
    "rear_roof": REAR,
    "extension": {"posts": EXT, "outer": OUT, "plate": [REAR_PLATE_BOT, REAR_PLATE_TOP]},
    "visibility": vis,
    "visibility_courtyard_cams_visible_total": sum(vis[c]["visible"] for c in COURTYARD_CAMS if c in vis),
    "shell_counts": hall_shell["counts"],
    "fbx": {"armory_used": len(used_pieces), "hall_existing": sum(1 for p in fbx_list if p.startswith("SM_DKH")),
            "items": len(item_fbx), "pending_new": len(PENDING), "armorylab_sha_drift": drift},
    "materials": {"masters": len(masters), "instances": len(mi_used), "textures": len(tex_used),
                  "textures_missing": [t for t, r in tex.items() if r.get("missing")]},
    "site": {"north_wall_moved": len(north_wall_moves), "side_wall_added": len(side_wall_adds),
             "gravel_copies": len(gravel_copy), "fir_drop": len(fir_drop), "grass_in_ext": grass_in_ext,
             "grass_in_new_yards": grass_in_new_yards},
    "walk_routes_new": len(wr), "controls_new": len(cr),
}
jdump(SV / "survey_report.json", report)
print(json.dumps({k: report[k] for k in ("interior", "lights", "light_shadows", "shell_counts", "fbx", "materials",
                                          "site", "walk_routes_new", "controls_new",
                                          "visibility_courtyard_cams_visible_total", "level_scale_dojolab")}, indent=1))
print("rear roof:", json.dumps({k: REAR[k] for k in ("eave_north", "ridge", "valley", "wall_plate", "vs_main",
                                                      "clearance_over_the_armory")}, indent=1))
print("envelope violations:", envelope_viol[:5])
