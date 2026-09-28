"""Print a compact summary of the legacy and Interchange verification reports (system Python, stdlib only)."""
import json
import math
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/pipeline_test")
LEGACY = ROOT / "UnrealTest" / "Validation"
INTERCHANGE = ROOT / "UnrealTest_Interchange" / "Validation"


def mesh_line(m):
    lods = [(l["index"], l.get("triangles"), l.get("triangles_static_mesh_api"), l.get("render_vertices")) for l in m["lods"]]
    hull = m["convex_count"]
    elems = [(e.get("vertex_count"), e.get("elem_box_min"), e.get("elem_box_max")) for e in m["convex_elems"]]
    sockets = [(s["name"], s.get("relative_location"), s.get("relative_rotation")) for s in m["sockets"]]
    extra = {k: m.get(k) for k in ("convex_count_subsystem", "simple_collision_count_subsystem", "box_count", "nanite_enabled")}
    return f"    {m['asset'].split('/')[-1]}: hulls={hull} {elems} sockets={sockets} lods={m['lod_count']} {lods} bounds_ext={m['bounds_extent_cm']} {extra} problems={m['problems']}"


def show(report_path, key):
    r = json.loads(report_path.read_text(encoding="utf-8"))
    print(f"##### {report_path.name}: status={r['status']} engine={r['engine_version']} cvar={r.get('interchange_fbx_cvar')}")
    if r.get("errors"):
        print("ERRORS:", [e[-500:] for e in r["errors"]])
    if r.get("option_problems"):
        print("option problems:", r["option_problems"])
    for name, e in r[key].items():
        print(f"== {name} [{e.get('pipeline', 'legacy')}] {e['description']}")
        if e.get("error"):
            print("   ERROR:", e["error"][-600:])
            continue
        print("   imported:", e.get("imported_object_paths"), "| in destination:", e.get("assets_in_destination"))
        for m in e.get("meshes", []):
            print(mesh_line(m))
    for k in ("pipelines", "pipeline_source", "pipeline_source_class", "engine_default_recompute_normals", "generic_assets_pipelines_in_registry",
              "normals_reference", "normals_comparison", "registry_scan_error", "registry_query_error"):
        if k in r:
            print(k, "=", json.dumps(r[k], indent=1) if isinstance(r[k], dict) else r[k])
    if "common_meshes_properties_names" in r:
        print("common_meshes_properties:", [n for n in r["common_meshes_properties_names"] if "normal" in n or "tangent" in n or "socket" in n or "lod" in n or "bake" in n])
        print("mesh_pipeline:", [n for n in r["mesh_pipeline_property_names"] if "collision" in n or "convex" in n or "nanite" in n or "combine" in n or "lod" in n])
    return r


def compare(reference, candidate):
    def key(p):
        return tuple(round(c, 2) for c in p)

    def angle(a, b):
        dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
        return math.degrees(math.acos(dot))

    by_pos = {}
    for p, n in candidate:
        by_pos.setdefault(key(p), []).append(n)
    angles, unmatched = [], 0
    for p, n in reference:
        c = by_pos.get(key(p))
        if not c:
            unmatched += 1
            continue
        angles.append(min(angle(n, x) for x in c))
    angles.sort()
    if not angles:
        return {"matched": 0, "unmatched": unmatched}
    return {"ref": len(reference), "cand": len(candidate), "matched": len(angles), "unmatched": unmatched, "max": round(angles[-1], 3),
            "mean": round(sum(angles) / len(angles), 3), "over1deg": sum(a > 1 for a in angles), "over5deg": sum(a > 5 for a in angles)}


if __name__ == "__main__":
    legacy = show(LEGACY / "legacy_report.json", "static_meshes") if (LEGACY / "legacy_report.json").is_file() else None
    if legacy:
        for k in ("character", "mannequin"):
            m = legacy.get(k) or {}
            print(k, "facing", (m.get("facing") or {}).get("facing_axis"), "votes", (m.get("facing") or {}).get("facing_votes"),
                  "bounds origin/extent", m.get("bounds_origin_cm"), m.get("bounds_extent_cm"), "bones via", (m.get("bones") or {}).get("method"))
    if (INTERCHANGE / "interchange_report.json").is_file():
        show(INTERCHANGE / "interchange_report.json", "imports")
    lv, iv = LEGACY / "legacy_lod0_vertices.json", INTERCHANGE / "interchange_lod0_vertices.json"
    if lv.is_file() and iv.is_file():
        L, I = json.loads(lv.read_text()), json.loads(iv.read_text())
        print("legacy vertex sets:", {k: len(v) for k, v in L.items()})
        print("interchange vertex sets:", {k: len(v) for k, v in I.items()})
        ref = L.get("SM_TestCrate_Single")
        if ref:
            for name, verts in I.items():
                print("offline normals legacy Single vs interchange", name, compare(ref, verts))
            for name, verts in L.items():
                if name != "SM_TestCrate_Single":
                    print("offline normals legacy Single vs legacy", name, compare(ref, verts))
