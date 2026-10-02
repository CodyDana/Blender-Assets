"""ROUND 6 (copy of the verify_r5 script, output moved): probe the corridor-end slot (X ~10.4-10.7 / 33.3-33.6, between each corridor's north end wall and the
hall veranda frame) that the generous free-space flood (ue_alley_flood.json) found. Floor-following Pawn capsule walk
sweeps (r 30, hh 62.5, body floor+47..+172; step-up = the line trace from floor+47, as the verifier's in-engine walk
gate), EVERYTHING in the level counts except the TRV markers (the hidden 1v1 ring is kept: this is the 1v1 as played).
Also a vertical profile of the pawn surfaces in the slot. Out: verify_r5/ue_pocket_probe2.json"""
import json, math
from pathlib import Path
import unreal
VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\world\checks\ue")
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
trv = [a for a in acts if a.get_actor_label().startswith("TRV_")]
ctx = acts[0]
def hi(h):
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "impact": [round(t[5].x/100, 3), round(-t[5].y/100, 3), round(t[5].z/100, 3)],
            "actor": t[9].get_actor_label() if t[9] else None}
def walk(pts, floor_z, ign):
    floor = floor_z * 100
    prev, path = None, []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
        for k in range(n + 1):
            x, y = (x0 + (x1 - x0) * k / n) * 100, -(y0 + (y1 - y0) * k / n) * 100
            f = hi(unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(x, y, floor + 47), V(x, y, floor - 120), "Pawn",
                                                                     False, ign, unreal.DrawDebugTrace.NONE, True))
            if f and not f["start_pen"]:
                floor = f["impact"][2] * 100
            c = V(x, y, floor + 109.5)
            if prev is not None:
                s = hi(unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, prev, c, 30.0, 62.5, "Pawn", False, ign,
                                                                            unreal.DrawDebugTrace.NONE, True))
                if s:
                    return {"clear": False, "at_m": [round(x/100, 2), round(-y/100, 2)], "floor_m": round(floor/100, 3), **s,
                            "floors": path[-6:]}
            prev = c
            path.append([round(x/100, 2), round(-y/100, 2), round(floor/100, 3)])
    return {"clear": True, "end_floor_m": round(floor/100, 3), "floors": path[::10]}
out = {"routes": {}, "profiles": {}}
for k, (p, z) in {
    "W_full_corridor_floor_to_behind_the_hall_centre": ([(9.0, 31.0), (10.45, 31.0), (10.45, 33.1), (9.0, 33.1), (9.0, 35.0), (22.0, 35.0)], 0.5),
    "E_full_corridor_floor_to_behind_the_hall_centre": ([(35.0, 31.0), (33.55, 31.0), (33.55, 33.1), (35.0, 33.1), (35.0, 35.0), (22.0, 35.0)], 0.5),
    "W_courtyard_side_yard_up_the_veranda_to_behind_the_hall": ([(10.0, 21.0), (11.6, 21.5), (11.6, 31.0), (10.45, 31.0), (10.45, 33.1), (9.0, 33.1), (9.0, 35.0), (22.0, 35.0)], 0.0),
}.items():
    out["routes"][k] = walk(p, z, trv)
out["any_clear"] = sorted(k for k, v in out["routes"].items() if v["clear"])
json.dump(out, open(VD / "ue_pocket_probe2.json", "w"), indent=1)
unreal.log(f"V5_POCKET2_DONE clear={len(out['any_clear'])}")
