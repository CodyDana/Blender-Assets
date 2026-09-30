"""VERIFY r5: rear-alley closure grid (fresh commandlet, read-only). Pawn capsule (r 30, hh 62.5 at floor+109.5) swept
north from Y 32.6 to Y 36.4 at every 0.25 m of X across both fence gaps (X 7.0..14.0 and 30.0..37.0), from the ground
(z 0) and from the veranda deck (z 0.5); the hidden 1v1 ring and the TRV markers are IGNORED, so only real kit
collision counts. Also sweeps along the alley itself (Y 35.0, X 1..43). Out: verify_r5/ue_alley_grid.json"""
import json
from pathlib import Path
import unreal
VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r5")
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
ign = [a for a in acts if a.get_actor_label().startswith("TRV_") or "Boundary" in a.get_actor_label()]
ctx = acts[0]
def sweep(x, z, y0=32.6, y1=36.4):
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, V(x*100, -y0*100, z*100+109.5), V(x*100, -y1*100, z*100+109.5),
                                                             30.0, 62.5, "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "y": round(-t[5].y/100, 3), "actor": t[9].get_actor_label() if t[9] else None}
rows, open_ = [], []
for x0, x1 in ((7.0, 14.0), (30.0, 37.0)):
    x = x0
    while x <= x1 + 1e-6:
        for z in (0.0, 0.5):
            b = sweep(x, z)
            rows.append({"x": round(x, 2), "z": z, "block": b})
            if b is None:
                open_.append([round(x, 2), z])
        x += 0.25
json.dump({"n": len(rows), "open": open_, "rows": rows, "passed": not open_}, open(VD / "ue_alley_grid.json", "w"), indent=1)
unreal.log(f"V5_ALLEY_DONE n={len(rows)} open={len(open_)}")
