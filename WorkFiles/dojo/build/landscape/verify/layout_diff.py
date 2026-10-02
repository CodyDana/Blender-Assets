"""verify (landscape round): current layout_showcase.json vs the pre-landscape layouts (git HEAD and world/start_backup).
Read-only; writes verify/layout_diff.json."""
import json, sys
from pathlib import Path
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
cur = json.loads((B/"showcase/layout_showcase.json").read_text(encoding="utf-8"))
out = {}
def diff(a, b, path="", acc=None, lim=200):
    if acc is None: acc = []
    if len(acc) >= lim: return acc
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: acc.append(f"{path}/{k}: added")
            elif k not in b: acc.append(f"{path}/{k}: removed")
            else: diff(a[k], b[k], f"{path}/{k}", acc, lim)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): acc.append(f"{path}: len {len(a)} -> {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)): diff(x, y, f"{path}[{i}]", acc, lim)
    elif a != b:
        acc.append(f"{path}: {str(a)[:80]} -> {str(b)[:80]}")
    return acc
for name, p in [("git_head", B/"landscape/verify/layout_git_head.json"), ("world_start_backup", B/"landscape/world/start_backup/layouts/layout_showcase.json")]:
    if not p.exists(): out[name] = "missing"; continue
    old = json.loads(p.read_text(encoding="utf-8"))
    r = {}
    oi, ci = old["instances"], cur["instances"]
    r["n_instances"] = [len(oi), len(ci)]
    ch = []
    for n, (a, b) in enumerate(zip(oi, ci)):
        a2 = {k: v for k, v in a.items() if k not in ("removed", "hide_landscape", "note")}
        b2 = {k: v for k, v in b.items() if k not in ("removed", "hide_landscape", "note")}
        if a2 != b2: ch.append([n, diff(a2, b2)])
    r["instances_changed_ignoring_removed_flags"] = ch
    r["removed"] = sum(1 for i in ci if i.get("removed"))
    r["removed_already_in_old"] = sum(1 for i in oi if i.get("removed"))
    r["removed_folders"] = {}
    for i in ci:
        if i.get("removed"): r["removed_folders"][i["folder"]] = r["removed_folders"].get(i["folder"], 0) + 1
    for key in ("collision_classes", "traversal_markers", "player_starts", "climb_routes", "walk_routes", "numbers", "sun", "pieces"):
        r[key] = diff(old.get(key), cur.get(key))
    r["top_level_keys_added"] = sorted(set(cur) - set(old)); r["top_level_keys_removed"] = sorted(set(old) - set(cur))
    r["other_top_changed"] = [k for k in cur if k in old and k not in ("instances",) and old[k] != cur[k]]
    out[name] = r
# 1v1 group pieces vs removed
LO = json.loads((B/"outside/layout_outside.json").read_text(encoding="utf-8"))["onev1_only"]
g = {v["piece"] for v in LO["visible"]} | {v["piece"] for v in LO["invisible"]} | {"SM_DGB_Boundary_1v1"}
out["onev1_pieces_removed"] = [f"{i['piece']}__{n:04d}" for n, i in enumerate(cur["instances"]) if i["piece"] in g and i.get("removed")]
out["onev1_instances"] = sum(1 for i in cur["instances"] if i["piece"] in g)
# removed instances whose collision class blocks pawns and lie near the compound (within 3 m)
cc = cur["collision_classes"]
near = []
for n, i in enumerate(cur["instances"]):
    if i.get("removed"):
        x, y, z = i["loc"]
        if -4 < x < 48 and -4 < y < 40:
            near.append([f"{i['piece']}__{n:04d}", i["folder"], [round(v, 2) for v in i["loc"]], i["collision_class"]])
out["removed_within_3m_of_compound"] = near
(B/"landscape/verify/layout_diff.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items():
    if isinstance(v, dict):
        print(k, {kk: (vv if not isinstance(vv, list) or len(vv) < 8 else f"{len(vv)} items: {vv[:5]}") for kk, vv in v.items()})
    else: print(k, v if not isinstance(v, list) or len(v) < 10 else f"{len(v)}: {v[:10]}")
