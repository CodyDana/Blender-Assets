"""ROUND 6 (copy of the verify_r5 script, output moved): probe the corridor-end slot (X ~10.4-10.7 / 33.3-33.6, between each corridor's north end wall and the
hall veranda frame) that the generous free-space flood (ue_alley_flood.json) found. Floor-following Pawn capsule walk
sweeps (r 30, hh 62.5, body floor+47..+172; step-up = the line trace from floor+47, as the verifier's in-engine walk
gate), EVERYTHING in the level counts except the TRV markers (the hidden 1v1 ring is kept: this is the 1v1 as played).
Also a vertical profile of the pawn surfaces in the slot. Out: verify_r5/ue_pocket_probe.json"""
import json, math
from pathlib import Path
import unreal
VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fxlight\checks\ue")
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
for side, sx in (("W", 1), ("E", -1)):
    def X(x):
        return x if sx == 1 else 44.0 - x
    for gx in (10.45, 10.5, 10.55, 10.6, 10.65, 10.7):
        R = {
            f"{side}_veranda_to_pocket_x{gx}": ([(X(11.6), 31.0), (X(gx), 31.0), (X(gx), 33.1), (X(9.0), 33.1), (X(9.0), 35.2)], 0.5),
            f"{side}_corridor_to_pocket_x{gx}": ([(X(9.0), 31.0), (X(gx), 31.0), (X(gx), 33.1), (X(9.0), 33.1), (X(9.0), 35.2)], 0.5),
            f"{side}_sideyard_to_pocket_x{gx}": ([(X(gx), 26.5), (X(gx), 33.1), (X(9.0), 33.1), (X(9.0), 35.2)], 0.0),
            f"{side}_veranda_rear_west_x{gx}": ([(X(11.6), 33.2), (X(gx), 33.2), (X(9.0), 33.2), (X(9.0), 35.2)], 0.5),
        }
        for k, (p, z) in R.items():
            out["routes"][k] = walk(p, z, trv)
    # pawn surfaces in the slot: line traces down from +2.9 m along X at Y 32.2 and along Y at X 10.55
    prof = []
    for i in range(0, 41):
        x = X(9.8 + i * 0.05)
        prof.append([round(x, 2), hi(unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(x*100, -32.2*100, 290), V(x*100, -32.2*100, -50),
                                                                                        "Pawn", False, trv, unreal.DrawDebugTrace.NONE, True))])
    out["profiles"][f"{side}_x_at_y32.2"] = prof
    prof = []
    for i in range(0, 61):
        y = 29.0 + i * 0.1
        prof.append([round(y, 2), hi(unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(X(10.55)*100, -y*100, 290), V(X(10.55)*100, -y*100, -50),
                                                                                        "Pawn", False, trv, unreal.DrawDebugTrace.NONE, True))])
    out["profiles"][f"{side}_y_at_x10.55"] = prof
out["any_clear"] = sorted(k for k, v in out["routes"].items() if v["clear"])
json.dump(out, open(VD / "ue_pocket_probe.json", "w"), indent=1)
unreal.log(f"V5_POCKET_DONE clear={len(out['any_clear'])}")
