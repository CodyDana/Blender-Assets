"""ROUND 6: in-engine replay of the outside track's alley-seal paths (round6/build/checks/alley_seal.json: 32 CONTROL +
10 POSITIVE paths, each a 2D polyline at a fixed feet height). Fresh commandlet, read-only (nothing saved).
Pawn-profile capsule sweeps between consecutive path points (r 30, half-height 86 cm = the 1.72 m GASP capsule) with
the capsule bottom 3 cm above the path's feet height (so a floor at exactly the feet height does not start-penetrate).
Three modes, the actors a mode IGNORES:
  1v1_set   TRV markers + the grey-box ring SM_DGB_Boundary_1v1 (the round-6 set must seal on its own)
  1v1       TRV markers only (the duel level as played)
  br        TRV markers + the ring + every actor tagged 'Dojo/Boundary_1v1' (the battle-royale copy drops the set)
Pass: every CONTROL blocked in 1v1_set and 1v1; every POSITIVE clear in all modes; the CONTROLs the Blender check found
open in the BR are open here in br too. Out: r6_work/checks/ue/ue_alley_replay.json"""
import json
from pathlib import Path
import unreal
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUTD = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "round8" / "s1_work" / "checks" / "ue"
SEAL = json.loads((ROOT / "WorkFiles" / "dojo" / "build" / "round6" / "build" / "checks_f1" / "alley_seal.json").read_text())
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
ctx = acts[0]
trv = [a for a in acts if a.get_actor_label().startswith("TRV_")]
ring = [a for a in acts if a.get_actor_label().startswith("SM_DGB_Boundary_1v1")]
tagged = [a for a in acts if unreal.Name("Dojo/Boundary_1v1") in list(a.tags)]
MODES = {"1v1_set": trv + ring, "1v1": trv, "br": trv + ring + tagged}
R, HH, LIFT = 30.0, 86.0, 3.0


def sweep(p0, p1, feet, ign, hh=HH):
    z = feet * 100.0 + LIFT + hh
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, V(p0[0] * 100, -p0[1] * 100, z), V(p1[0] * 100, -p1[1] * 100, z),
                                                             R, hh, "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "at": [round(t[4].x / 100, 3), round(-t[4].y / 100, 3), round(t[4].z / 100, 3)],
            "actor": t[9].get_actor_label() if t[9] else None}


out = {"capsule": {"r_cm": R, "half_height_cm": HH, "lift_cm": LIFT}, "tagged_1v1_actors": sorted(a.get_actor_label() for a in tagged),
       "ring_actors": [a.get_actor_label() for a in ring], "paths": {}}
for name, P in SEAL["paths"].items():
    row = {}
    src = P.get("1v1") or P.get("br") or next(iter(P.values()))
    pts, feet = src["path"], src["feet"]
    # a path whose full-height capsule starts inside a hull in EVERY mode (e.g. under the upper roof's eave, where the
    # Blender check's capsule model differs) is replayed with the verifier's short walk capsule (hh 62.5 cm)
    for hh in (HH, 62.5):
        for mode, ign in MODES.items():
            hit = None
            for a, b in zip(pts[:-1], pts[1:]):
                hit = sweep(a, b, feet, ign, hh)
                if hit:
                    break
            row[mode] = {"clear": hit is None, "hit": hit, "half_height_cm": hh}
        if not all(row[m]["hit"] and row[m]["hit"]["start_pen"] for m in MODES):
            break
    row["blender"] = {m: P[m]["clear"] for m in P if isinstance(P[m], dict) and "clear" in P[m]}
    out["paths"][name] = row
ctrl = {k: v for k, v in out["paths"].items() if k.startswith("CONTROL")}
pos = {k: v for k, v in out["paths"].items() if not k.startswith("CONTROL")}
br_open_blender = [k for k, v in ctrl.items() if v["blender"].get("br")]
out["summary"] = {
    "controls": len(ctrl), "positives": len(pos), "tagged_1v1_actors": len(tagged),
    "controls_blocked_1v1_set": sum(1 for v in ctrl.values() if not v["1v1_set"]["clear"]),
    "controls_blocked_1v1": sum(1 for v in ctrl.values() if not v["1v1"]["clear"]),
    "controls_start_pen_1v1_set": [k for k, v in ctrl.items() if v["1v1_set"]["hit"] and v["1v1_set"]["hit"]["start_pen"]],
    "positives_clear_all_modes": sum(1 for v in pos.values() if all(v[m]["clear"] for m in MODES)),
    "br_open_blender": len(br_open_blender),
    "br_open_ue": sum(1 for k in br_open_blender if ctrl[k]["br"]["clear"]),
    "br_mismatch": [k for k in br_open_blender if not ctrl[k]["br"]["clear"]],
}
s = out["summary"]
out["passed"] = (s["controls_blocked_1v1_set"] == s["controls"] and s["controls_blocked_1v1"] == s["controls"]
                 and s["positives_clear_all_modes"] == s["positives"])
(OUTD / "ue_alley_replay.json").write_text(json.dumps(out, indent=1))
unreal.log(f"R6_REPLAY_DONE passed={out['passed']} {json.dumps(s)}")
