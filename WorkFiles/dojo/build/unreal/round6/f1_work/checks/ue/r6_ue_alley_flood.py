"""ROUND 6 (copy of the verify_r5 script, output moved): rear-alley connectivity (fresh commandlet, read-only). Free-space grid at 0.1 m: a Pawn-profile capsule
(r 30, hh 62.5) centred at z 1.595 m (bottom 0.97 m: anything lower counts as walkable, i.e. GENEROUS / conservative
for a leak test) is tested for overlap at each cell (tiny sweep; start-penetration = blocked). 4-connected flood fill
from the courtyard side yard; the alley cells (Y 34.3..35.7) must not be reached. The hidden 1v1 ring and the TRV
markers are IGNORED. Both sides: X 4..14 and 30..40, Y 24..35.9. Out: verify_r5/ue_alley_flood.json"""
import json
from pathlib import Path
import unreal
VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round6\f1_work\checks\ue")
V = unreal.Vector
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
ign = [a for a in acts if a.get_actor_label().startswith("TRV_") or "Boundary" in a.get_actor_label()]
ctx = acts[0]
import os
ZC = float(os.environ.get("DJ_ZC", "159.5"))
def free(x, y):
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(ctx, V(x*100, -y*100, ZC), V(x*100 + 0.1, -y*100, ZC),
                                                             30.0, 62.5, "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    return not (t and (t[0] or t[1]))
out = {}
for side, (x0, x1, seed) in {"W": (4.0, 14.0, (10.2, 25.0)), "E": (30.0, 40.0, (33.8, 25.0))}.items():
    nx, ny = int(round((x1 - x0) / 0.1)) + 1, int(round((35.9 - 24.0) / 0.1)) + 1
    g = [[free(x0 + i * 0.1, 24.0 + j * 0.1) for j in range(ny)] for i in range(nx)]
    si, sj = int(round((seed[0] - x0) / 0.1)), int(round((seed[1] - 24.0) / 0.1))
    seen, stack = set(), [(si, sj)] if g[si][sj] else []
    while stack:
        i, j = stack.pop()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        for a, b in ((i+1, j), (i-1, j), (i, j+1), (i, j-1)):
            if 0 <= a < nx and 0 <= b < ny and g[a][b] and (a, b) not in seen:
                stack.append((a, b))
    maxy = max((24.0 + j * 0.1) for i, j in seen) if seen else None
    alley = sorted({(round(x0 + i * 0.1, 1), round(24.0 + j * 0.1, 1)) for i, j in seen if 24.0 + j * 0.1 >= 34.3})
    alley_free = sum(1 for i in range(nx) for j in range(ny) if g[i][j] and 24.0 + j * 0.1 >= 34.3)
    out[side] = {"seed_free": bool(g[si][sj]), "reached": len(seen), "max_y_reached": maxy, "alley_cells_free": alley_free,
                 "alley_cells_reached": alley[:50], "n_alley_reached": len(alley), "grid": ["".join("#" if not g[i][j] else ("o" if (i, j) in seen else ".") for i in range(nx)) for j in range(ny)]}
out["passed"] = all(v["seed_free"] and v["n_alley_reached"] == 0 and v["alley_cells_free"] > 0 for v in out.values() if isinstance(v, dict))
json.dump(out, open(VD / os.environ.get("DJ_OUT", "ue_alley_flood.json"), "w"), indent=1)
unreal.log(f"V5_FLOOD_DONE {out['passed']}")
