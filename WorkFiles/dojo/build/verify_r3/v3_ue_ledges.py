"""VERIFY r3: ledge-by-ledge climb-surface check (pythonscript commandlet, -nullrhi, fresh, READ-ONLY).
For every traversal marker and each of its four top edges: samples every 0.25 m along the edge (0.30 m clamp from the
ends, as GASP clamps its contact point), inset 0.15 m inwards; a Pawn-profile line trace from 5 cm above the marker top
down 1.5 m. Per sample: 'on' = the pawn surface is within 3 cm of the marker top; 'occupied' = the trace starts inside a
pawn-blocking hull (a post / wall stands on the ledge there); 'low' = the surface is more than 3 cm below. A ledge is a
climb surface when >= 60 % of its samples are 'on'. Out: verify_r3/ue_ledges.json"""
import json
from pathlib import Path

import unreal

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VD = ROOT / "WorkFiles" / "dojo" / "build" / "verify_r3"
L = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector


def main():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
    actors = EAS.get_all_level_actors()
    ign = [a for a in actors if a.get_actor_label().startswith("TRV_") or "Boundary" in a.get_actor_label()]
    ctx = actors[0]
    need = {r["marker"] for r in L["climb_routes"] if r.get("marker")}
    faces = {}
    for r in L["climb_routes"]:
        if r.get("marker") and r.get("face"):
            faces.setdefault(r["marker"], set()).add(tuple(r["face"]))
    out = {}
    for m in L["traversal_markers"]:
        x0, x1, y0, y1, z0, z1 = m["box"]
        edges = {"S(y0)": ((x0, y0), (x1, y0), (0, 1), (0, -1)), "N(y1)": ((x0, y1), (x1, y1), (0, -1), (0, 1)),
                 "W(x0)": ((x0, y0), (x0, y1), (1, 0), (-1, 0)), "E(x1)": ((x1, y0), (x1, y1), (-1, 0), (1, 0))}
        row = {"box": m["box"], "route_faces": sorted(faces.get(m["name"], [])), "ledges": {}}
        for en, ((ax, ay), (bx, by), (ix, iy), outward) in edges.items():
            ln = abs(bx - ax) + abs(by - ay)
            n = max(1, int((ln - 0.6) / 0.25))
            cnt = {"on": 0, "occupied": 0, "low": 0, "none": 0}
            for k in range(n + 1):
                t = 0.30 + (ln - 0.6) * k / n if ln > 0.6 else ln / 2
                px = ax + (bx - ax) * t / ln + ix * 0.15
                py = ay + (by - ay) * t / ln + iy * 0.15
                h = unreal.SystemLibrary.line_trace_single_by_profile(ctx, V(px * 100, -py * 100, z1 * 100 + 5),
                                                                       V(px * 100, -py * 100, z1 * 100 - 150), "Pawn",
                                                                       False, ign, unreal.DrawDebugTrace.NONE, True)
                tt = h.to_tuple() if h is not None else None
                if tt is None or not (tt[0] or tt[1]):
                    cnt["none"] += 1
                elif tt[1]:
                    cnt["occupied"] += 1
                elif abs(tt[5].z - z1 * 100) <= 3.0:
                    cnt["on"] += 1
                else:
                    cnt["low"] += 1
            tot = sum(cnt.values())
            # the ledge a route arrives at: the route faces +Y (Blender) -> it climbs the marker's S(y0) edge, etc.
            used = any((f[0] == -outward[0] and f[1] == -outward[1]) for f in faces.get(m["name"], []))
            row["ledges"][en] = dict(cnt, n=tot, on_frac=round(cnt["on"] / tot, 3), used_by_route=used,
                                     climb_surface=cnt["on"] / tot >= 0.6)
        row["used_ledges_ok"] = all(v["climb_surface"] for v in row["ledges"].values() if v["used_by_route"])
        row["route_marker"] = m["name"] in need
        out[m["name"]] = row
    res = {"markers": out, "used_ledges_all_ok": all(r["used_ledges_ok"] for r in out.values()),
           "markers_without_route_face": sorted(k for k, r in out.items() if not r["route_faces"])}
    (VD / "ue_ledges.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    unreal.log(f"V3_LEDGES_DONE used_ok={res['used_ledges_all_ok']}")


main()
