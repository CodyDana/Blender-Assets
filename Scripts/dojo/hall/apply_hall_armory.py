"""HALL + ARMORY round (2026-10-01), DojoLab stage: the prep patch of layout_showcase.json (plain Python, idempotent),
run LAST by run_showcase_unreal.sh prep (after apply_round2 / apply_look_r3 / apply_landscape, which rebuild the CU_*
close-ups from look_r3.CLOSEUPS and would otherwise undo this round's camera moves).

- CU_R6_AlleyAbove: +11 m in y with the rear alley (compose_hall_armory.py moved it; look_r3 re-creates it at y 46);
  CU_R6_PocketAboveW: the note (it now stands over the new rear yard; kept as a rear-yard view).
- Cameras added (level frame, the same record as the others):
  - CAM_DoorwayIn: player eye in the courtyard, through the three open centre doors into the armory;
  - CAM_RearExtension: the lower rear roof (temple rear hall) from above / behind (north-east);
  - CAM_ArmoryEntry: just outside the open doors on the veranda, looking in along the aisle (the armory's C1_EntryReveal
    stands outside its own south wall, which in the hall is under the lower front roof: this is its hall equivalent);
  - CAM_AK_<name>: the armory chat's own Unreal capture cameras (WorkFiles/armory/build/unreal/capture.json, r20),
    converted exactly (ArmoryLab cm -> armory m -> hall-local (-6, 0, 0) -> world (+22, +24, +0.5)), same horizontal FOV
    and 1600 x 900, for the ARMORY_vs_OURS sheets;
  - CAM_ArmoryCeiling: the coffered ceiling and the lattice from the centre aisle, looking up and north.
- Carry-over (landscape verify 2026-10-01): the 5 BR walk routes that ran through the removed town (approach road,
  gate apron, verge, west lane kerb, lower lane) leave walk_routes for retired_walk_routes with the reason; LS_Valley
  terrain now blocks them by design (the town is gone), so they are dead routes, not regressions.
Run: py -3 -B apply_hall_armory.py        (prints HALL_ARMORY_PREP ...)
"""
import json
import math
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
LAYOUT = ROOT / "WorkFiles" / "dojo" / "build" / "showcase" / "layout_showcase.json"
AK_CAPTURE = ROOT / "WorkFiles" / "armory" / "build" / "unreal" / "capture.json"   # read only (armory chat's)
HL_TO_WORLD = (22.0, 24.0, 0.5)
AK_TO_HL = (-6.0, 0.0, 0.0)
DEAD_BR = {
    "BR_approach_road_along_the_crown": "the approach road",
    "BR_road_onto_the_gate_apron": "the gate apron (the plan already retired it)",
    "BR_verge_along_the_south_wall_foot_west": "the verge",
    "BR_road_up_the_kerb_into_the_west_lane_north": "the west lane kerb",
    "BR_lower_lane": "the lower lane",
}
AK_CAMS = ("C2_Case1", "C4_ShurikenTray", "C3_Case3", "C5_CloakCase", "C10_Hero", "CW_WestAisle", "CX_FromPlatform")


def cam(name, loc, look_at, hfov, wh, note):
    return {"name": name, "loc": [round(v, 4) for v in loc], "look_at": [round(v, 4) for v in look_at],
            "hfov_deg": round(hfov, 3), "out_wh": list(wh), "note": note}


def ak_cameras():
    out = []
    caps = json.loads(AK_CAPTURE.read_text(encoding="utf-8"))["captures"]
    for k in AK_CAMS:
        v = caps[k]
        x, y, z = (c / 100.0 for c in v["loc"])
        y = -y
        loc = (x + AK_TO_HL[0] + HL_TO_WORLD[0], y + AK_TO_HL[1] + HL_TO_WORLD[1], z + AK_TO_HL[2] + HL_TO_WORLD[2])
        p, yw = (math.radians(a) for a in v["rot"])
        d = (math.cos(p) * math.cos(yw), -math.cos(p) * math.sin(yw), math.sin(p))
        out.append(cam("CAM_AK_" + k, loc, [loc[i] + 10.0 * d[i] for i in range(3)], v["fov_deg"], (1600, 900),
                       f"hall + armory round: the armory chat's ArmoryLab capture camera {k} (capture.json r20), "
                       "converted exactly to the hall; pairs with WorkFiles/armory/build/unreal/captures/" + k + ".png"))
    return out


NEW_CAMERAS = [
    cam("CAM_DoorwayIn", (22.0, 17.2, 1.7), (22.0, 40.0, 1.15), 62.0, (1920, 1080),
        "hall + armory round: player eye (1.7 m) in the courtyard on the centre line, through the three open centre "
        "doors into the armory interior"),
    cam("CAM_RearExtension", (40.0, 64.0, 19.0), (22.0, 38.5, 5.0), 62.0, (1920, 1080),
        "hall + armory round: the lower rear roof (temple rear hall) from above and behind (north-east), with the main "
        "roof's back slope, the valley, the moved north wall and the rear alley"),
    cam("CAM_ArmoryEntry", (22.0, 22.9, 2.0), (22.0, 42.0, 1.55), 60.0, (1600, 900),
        "hall + armory round: on the veranda just outside the open centre doors, looking in along the aisle (the hall "
        "equivalent of the armory's C1_EntryReveal, which would stand under the hall's lower front roof)"),
    cam("CAM_ArmoryCeiling", (22.0, 29.0, 1.7), (22.0, 35.0, 5.0), 84.0, (1600, 900),
        "hall + armory round: the coffered ceiling and the lattice from the centre aisle, looking up and north"),
]


REAR_DOOR_ID, REAR_PLASTER_ID = "DKH_N0022", "DKH_N0084"


def rear_centre_bay(L):
    """FIX round (shared revision 2, 2026-10-01; judge delta 'outside and inside of the shell do not agree'): the
    extension's rear-wall centre bay X 21-23 was the old rear wall's closed lattice door (DKH_N0022), glowing dead
    centre on the rear wall while the armory's hero painting stands right behind it inside. It becomes a plaster bay
    (new id DKH_N0084, SM_DKH_Bay_Plaster, same place; DKH_N0022 kept in the list as removed: ids are never reused).
    Idempotent."""
    old = [i for i in L["instances"] if i.get("shell_id") == REAR_DOOR_ID]
    new = [i for i in L["instances"] if i.get("shell_id") == REAR_PLASTER_ID]
    done = {"removed": [], "added": []}
    for i in old:
        if not i.get("removed"):
            i["removed"] = "hall_armory_rev2"
            i["hall_armory_status"] = "replaced"
            i["replaced_by"] = f"SM_DKH_Bay_Plaster ({REAR_PLASTER_ID})"
            done["removed"].append(L["instances"].index(i))
    if old and not new:
        src = old[0]
        n = dict(src)
        for k in ("removed", "hall_armory_status", "replaced_by"):
            n.pop(k, None)
        n.update({"piece": "SM_DKH_Bay_Plaster", "source": f"hall_shell_layout.json {REAR_PLASTER_ID}",
                  "note": "extension rear wall centre bay X 21-23: plaster (fix round, shared rev 2; was the closed "
                          "lattice door DKH_N0022, which glowed behind the armory's hero painting)",
                  "hall_armory": "hall_armory_rev2", "shell_id": REAR_PLASTER_ID})
        L["instances"].append(n)
        done["added"].append(len(L["instances"]) - 1)
    return done


def main():
    L = json.loads(LAYOUT.read_text(encoding="utf-8"))
    rec = L.setdefault("hall_armory_round", {})
    moved = []
    for c in L["cameras"]:
        if c["name"] == "CU_R6_AlleyAbove" and abs(c["loc"][1] - 46.0) < 1e-6:
            c["loc"][1] = 57.0
            c["look_at"][1] = 43.5
            c["note"] = (c["note"].split(" (hall + armory")[0] + " (hall + armory round: +11 m in y with the alley)")
            moved.append(c["name"])
        if c["name"] == "CU_R6_PocketAboveW" and "hall + armory" not in c["note"]:
            c["note"] += " (hall + armory round: now over the new rear yard west of the extension)"
    ak = ak_cameras()
    names = {c["name"] for c in NEW_CAMERAS + ak}
    L["cameras"] = [c for c in L["cameras"] if c["name"] not in names] + NEW_CAMERAS + ak
    ret = L.setdefault("retired_walk_routes", {})
    retired = []
    for k, what in DEAD_BR.items():
        if k in L["walk_routes"]:
            ret[k] = dict(L["walk_routes"].pop(k), retired=(
                f"hall + armory round 2026-10-01 (landscape verify carry-over): ran through {what} of the town the "
                "landscape round removed; LS_Valley terrain blocks it by design. Dead route, not a regression."))
            retired.append(k)
    rec["dojolab_prep"] = {"cameras_added": sorted(names), "dead_br_routes_retired": sorted(ret)}
    fix = rear_centre_bay(L)
    rec["fix_round_rev2"] = fix
    LAYOUT.write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("HALL_ARMORY_PREP cameras", len(L["cameras"]), "added", len(names), "moved", moved, "retired_now", retired,
          "retired_total", len(ret), "walk_routes", len(L["walk_routes"]), "fix_rev2", fix)


main()
