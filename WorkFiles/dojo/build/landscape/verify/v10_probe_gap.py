"""VERIFY LANDSCAPE ROUND: probe the veranda -> west corridor junction where the in-engine walk route
'veranda_front_to_west_side_to_corridor' now drops to the landscape (x 11.0, y 30.62). Read-only; writes probe_gap.json.
Per sample: every Pawn-blocking line hit from z 3 m down to -1 m, and where a GASP capsule (r 30 / 35, hh 86) dropped
from z 2.5 m comes to rest (its feet). Also the mirror (east) junction."""
import json
from pathlib import Path

import unreal

VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\verify")
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
ACTS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
CTX = ACTS[0]
TRV = [a for a in ACTS if a.get_actor_label().startswith("TRV_")]


def hits(x, y):
    out = []
    z = 3.0
    for _ in range(6):
        h = unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x * 100, -y * 100, z * 100), V(x * 100, -y * 100, -100.0),
                                                              "Pawn", False, TRV, unreal.DrawDebugTrace.NONE, True)
        t = h.to_tuple() if h else None
        if not t or not t[0]:
            break
        zz = t[5].z / 100
        out.append([round(zz, 3), t[9].get_actor_label() if t[9] else None, round(t[7].z, 3)])
        z = zz - 0.02
        if z < -0.99:
            break
    return out


def cap_rest(x, y, r):
    a = V(x * 100, -y * 100, 250.0 + 87.0)
    b = V(x * 100, -y * 100, -100.0 + 87.0)
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, a, b, r, 86.0, "Pawn", False, TRV, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    if not t or not t[0]:
        return None
    return [round((t[4].z - 87.0) / 100, 3), t[9].get_actor_label() if t[9] else None, bool(t[1])]


rep = {}
for side, xs in (("W", [12.2 - 0.05 * i for i in range(90)]), ("E", [31.8 + 0.05 * i for i in range(90)])):
    for y in (30.3, 30.5, 30.62, 30.75, 31.0):
        rows = []
        for x in xs:
            rows.append({"x": round(x, 2), "line_hits": hits(x, y), "cap30_feet": cap_rest(x, y, 30.0), "cap35_feet": cap_rest(x, y, 35.0)})
        rep[f"{side}_y{y}"] = rows
(VD / "probe_gap.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
unreal.log("V10_PROBE_DONE")
