"""LANDSCAPE ROUND (world stage): the prep patch of layout_showcase.json (plain Python, idempotent), run after
apply_round2.py / apply_look_r3.py by run_showcase_unreal.sh prep.

- REMOVED from the level (flag "removed": "landscape_round" on the instance; indices stay, so every label, bounds row
  and alley-check actor name is unchanged; the assets stay on disk): Outside/Street, Outside/Town, Outside/Ground,
  Outside/Far, and the modern props outside the compound walls (street lamps, utility poles, wires, guy, transformer)
  - LANDSCAPE_PLAN 3.14. Their lamp lights leave the lights list; the WornPath_07 floor decal that lay on the old road
  apron in front of the gate (y -3.3, now the gate stair head) leaves the decals list; the 22 old tree_slots move to
  landscape_round.removed_tree_slots (replaced by the CherrySlots, the pines and the forest zones).
- HIDDEN, collision kept: the two grey-box trees SM_DGB_Tree (flag "hide_landscape"): their trunk hulls are the CS01 /
  CS02 cherry slots' collision, so every walk and climb route stays identical; their canopies no longer render.
- KEPT: every compound piece, prop, decal, light and GASP marker; the alley / pocket fences and Boundary_1v1.
- CAMERAS added (level frame, same record as the other cameras): CAM_LandscapeRef (the plan's fitted reference camera,
  2:3 portrait like the reference), CAM_RiverRapids, CAM_StairPath, CAM_TerraceWall, CAM_FromGateOut, CAM_PeaksOverHall.
Run: py -3 -B apply_landscape.py        (prints LANDSCAPE_PREP ...)
"""
import json
import math
from pathlib import Path

LAYOUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json")
REMOVE_FOLDERS = {"Outside/Street", "Outside/Town", "Outside/Ground", "Outside/Far"}
COMPOUND = (-1.0, 45.0, -1.0, 37.0)
REMOVE_DECALS = {"WornPath_07"}


def cam_from_yaw(name, loc, yaw_from_north, pitch, hfov, wh, note):
    d = (math.sin(math.radians(yaw_from_north)) * math.cos(math.radians(pitch)),
         math.cos(math.radians(yaw_from_north)) * math.cos(math.radians(pitch)), math.sin(math.radians(pitch)))
    return {"name": name, "loc": list(loc), "look_at": [round(loc[i] + 100.0 * d[i], 4) for i in range(3)],
            "hfov_deg": hfov, "out_wh": list(wh), "note": note}


NEW_CAMERAS = [
    cam_from_yaw("CAM_LandscapeRef", (4.8, -61.6, 12.9), 24.2, -3.7, 60.0, (1280, 1920),
                 "landscape round: the plan's reference camera (LANDSCAPE_PLAN 3.13, weighted fit on 10 landmarks), "
                 "portrait 2:3 as dojo_landscape_ref.png (1024 x 1536); captured at 1280 x 1920"),
    {"name": "CAM_RiverRapids", "loc": [33.0, -25.0, -5.3], "look_at": [53.0, -7.0, -3.6], "hfov_deg": 72.0,
     "out_wh": [1920, 1080], "note": "landscape round: low over the rapids (1.4 m above the water) at the boulders, "
                                     "up the white water to the SE corner wall"},
    {"name": "CAM_StairPath", "loc": [3.3, -39.3, -5.35], "look_at": [11.0, -6.0, 0.5], "hfov_deg": 65.0,
     "out_wh": [1920, 1080], "note": "landscape round: player eye on the river landing L7, up the cliff stair path to "
                                     "the gate (the plan's CAM_StairClimb)"},
    {"name": "CAM_TerraceWall", "loc": [58.0, -9.5, -1.2], "look_at": [18.0, -7.0, -3.0], "hfov_deg": 70.0,
     "out_wh": [1920, 1080], "note": "landscape round: along the ishigaki (WR4 / WR2) above the river, looking west"},
    {"name": "CAM_FromGateOut", "loc": [22.0, -2.2, 1.65], "look_at": [14.0, -60.0, -6.0], "hfov_deg": 75.0,
     "out_wh": [1920, 1080], "note": "landscape round: player eye in the open gate looking out over the forecourt, "
                                     "the rapids and the valley"},
    {"name": "CAM_PeaksOverHall", "loc": [30.0, -7.0, 1.2], "look_at": [1800.0, 7200.0, 1300.0], "hfov_deg": 50.0,
     "out_wh": [1920, 1080], "note": "landscape round: the plan's forecourt eye-level camera toward the two peaks"},
]


def main():
    L = json.loads(LAYOUT.read_text(encoding="utf-8"))
    rec = L.get("landscape_round") or {}
    removed, hidden = [], []
    for n, i in enumerate(L["instances"]):
        x, y, _z = i["loc"]
        outside = x < COMPOUND[0] or x > COMPOUND[1] or y < COMPOUND[2] or y > COMPOUND[3]
        if i["folder"] in REMOVE_FOLDERS or (i["folder"] == "Props/Modern" and outside):
            i["removed"] = "landscape_round"
            removed.append(n)
        elif i["piece"] == "SM_DGB_Tree":
            i["hide_landscape"] = True
            hidden.append(n)
    gone = {f"__{n:04d}" for n in removed}
    lights_removed = [li for li in L["lights"] if any(li["name"].endswith(g) for g in gone)]
    L["lights"] = [li for li in L["lights"] if li not in lights_removed]
    decals_removed = [d for d in L.get("decals", []) if d["id"] in REMOVE_DECALS]
    L["decals"] = [d for d in L.get("decals", []) if d["id"] not in REMOVE_DECALS]
    if L.get("tree_slots"):
        rec["removed_tree_slots"] = L.pop("tree_slots")
    names = {c["name"] for c in NEW_CAMERAS}
    L["cameras"] = [c for c in L["cameras"] if c["name"] not in names] + NEW_CAMERAS
    by_folder = {}
    for n in removed:
        f = L["instances"][n]["folder"]
        by_folder[f] = by_folder.get(f, 0) + 1
    rec.update({"date": "2026-09-30", "removed_instances": len(removed), "removed_by_folder": by_folder,
                "removed_pieces": sorted({L["instances"][n]["piece"] for n in removed}),
                "hidden_collision_kept": [f"{L['instances'][n]['piece']}__{n:04d}" for n in hidden]})
    rec.setdefault("removed_lights", [])
    rec["removed_lights"] = sorted(set(rec["removed_lights"]) | {li["name"] for li in lights_removed})
    rec.setdefault("removed_decals", [])
    rec["removed_decals"] = sorted(set(rec["removed_decals"]) | {d["id"] for d in decals_removed})
    rec["cameras_added"] = sorted(names)
    L["landscape_round"] = rec
    LAYOUT.write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("LANDSCAPE_PREP removed", len(removed), json.dumps(by_folder), "hidden", len(hidden), "lights",
          rec["removed_lights"], "decals", rec["removed_decals"], "cameras", len(L["cameras"]))


main()
