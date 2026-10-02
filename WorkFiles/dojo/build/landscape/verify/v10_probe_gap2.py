"""VERIFY LANDSCAPE ROUND: the veranda / corridor end-gable seams (W and E). Read-only; writes probe_gap2.json.
1. seam width: Pawn line traces from z 1.0 m down to -1.0 m every 1 cm in x across the junction, y 30.0..31.4 every
   0.1 m: x where the first hit is below 0.40 m (= through the deck level).
2. support: a GASP capsule (r 30 / 35, hh 86) with its feet 2 cm over the deck (0.52 m) at every 2 cm across the
   seam: does it fit, and where does a 1.2 m downward sweep stop (feet z)? A capsule that stops at ~0.5 m is carried by
   the deck edges (it cannot fall into the seam)."""
import json
from pathlib import Path

import unreal

VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\verify")
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
ACTS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
CTX = ACTS[0]
TRV = [a for a in ACTS if a.get_actor_label().startswith("TRV_")]


def first(x, y):
    h = unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x * 100, -y * 100, 100.0), V(x * 100, -y * 100, -100.0),
                                                          "Pawn", False, TRV, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    if not t or not t[0]:
        return None, None
    return round(t[5].z / 100, 3), (t[9].get_actor_label() if t[9] else None)


def cap(x, y, r):
    a = V(x * 100, -y * 100, 52.0 + 87.0)
    s = unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, a, V(a.x + 0.1, a.y, a.z), r, 86.0, "Pawn", False, TRV,
                                                             unreal.DrawDebugTrace.NONE, True)
    fits = not (s and s.to_tuple()[0])
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, a, V(a.x, a.y, a.z - 120.0), r, 86.0, "Pawn", False, TRV,
                                                             unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    if not t or not t[0]:
        return {"fits": fits, "rest_feet_m": None}
    return {"fits": fits, "rest_feet_m": round((t[4].z - 87.0) / 100, 3), "on": t[9].get_actor_label() if t[9] else None,
            "start_pen": bool(t[1])}


rep = {}
for side, x0, x1 in (("W", 10.2, 11.4), ("E", 32.6, 33.8)):
    rows = {}
    for k in range(15):
        y = round(30.0 + 0.1 * k, 2)
        gaps = []
        n = int(round((x1 - x0) / 0.01))
        for i in range(n + 1):
            x = round(x0 + 0.01 * i, 2)
            z, a = first(x, y)
            if z is None or z < 0.40:
                gaps.append([x, z, a])
        caps = {}
        if gaps:
            xs = [g[0] for g in gaps]
            for r in (30.0, 35.0):
                caps[f"r{int(r)}"] = [[round(xs[0] - 0.4 + 0.02 * j, 2), cap(round(xs[0] - 0.4 + 0.02 * j, 2), y, r)]
                                      for j in range(int((xs[-1] - xs[0] + 0.8) / 0.02) + 1)]
        rows[str(y)] = {"seam_x": [gaps[0][0], gaps[-1][0]] if gaps else None, "n_seam_samples": len(gaps),
                        "seam_hits": gaps[:3], "capsules": caps}
    rep[side] = rows
(VD / "probe_gap2.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
unreal.log("V10_PROBE2_DONE")
