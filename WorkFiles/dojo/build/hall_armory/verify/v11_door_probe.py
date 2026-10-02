# VERIFIER: probe the centre door opening: free vertical window per y slice, and horizontal sweeps at several bottoms
import json, unreal
from pathlib import Path
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
CTX = A[0]; TRV = [a for a in A if a.get_actor_label().startswith("TRV_")]
V = unreal.Vector; HH = 86.0
def sw(a, b, r):
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, a, b, r, HH, "Pawn", False, TRV, unreal.DrawDebugTrace.NONE, True)
    if h is None: return None
    t = h.to_tuple()
    if not (t[0] or t[1]): return None
    return {"sp": bool(t[1]), "time": round(t[2], 4), "imp": [round(t[5].x,1), round(t[5].y,1), round(t[5].z,1)], "n": [round(t[7].x,3), round(t[7].y,3), round(t[7].z,3)], "actor": t[9].get_actor_label() if t[9] else None}
def lt(x, y, z0, z1):
    h = unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x*100,-y*100,z0*100), V(x*100,-y*100,z1*100), "Pawn", False, TRV, unreal.DrawDebugTrace.NONE, True)
    if h is None: return None
    t = h.to_tuple()
    return None if not t[0] else [round(t[5].z/100,4), t[9].get_actor_label() if t[9] else None]
out = {"profile": {}, "sweeps": {}}
for x in (20.0, 22.0, 24.0, 21.3, 22.7):
    rows = []
    for k in range(-20, 21):
        y = 24.0 + k * 0.02
        rows.append([round(y,2), lt(x, y, 1.2, 0.0), lt(x, y, 1.2, 3.0)])
    out["profile"][str(x)] = rows
for r in (30.0, 35.0):
    for bz in (0.52, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68):
        a = V(22*100, -23.3*100, bz*100 + HH); b = V(22*100, -25.0*100, bz*100 + HH)
        out["sweeps"][f"r{int(r)}_b{bz}"] = sw(a, b, r)
Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/json/door_probe.json").write_text(json.dumps(out, indent=1))
unreal.log("VHA_DOOR_DONE")
