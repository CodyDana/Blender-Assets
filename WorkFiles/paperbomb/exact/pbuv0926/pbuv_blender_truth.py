#!/usr/bin/env python
"""INDEPENDENT Blender-side truth for the Unreal verification of SM_PaperBomb.

Reads only the shipped bytes (Exports/PaperBomb/SM_PaperBomb.fbx) in a fresh
factory-startup Blender.  Nothing here is taken from the build report: every number the
Unreal gates compare against is re-derived from the file that will ship.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python v2_blender_truth.py
"""
import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "exact" / "pbuv0926"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
OUT = HERE / "pbuv_blender_truth.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tri_array(obj):
    """(V,3) verts in mm and (T,3) triangle indices, in Blender object space."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3, np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * 1000.0
    tris = np.array([list(t.vertices) for t in mesh.loop_triangles], np.int64)
    return co, tris


def hull_planes(verts, tris, tol=1e-4):
    """Outward half-planes of a (presumed) convex mesh, deduplicated."""
    planes = []
    for a, b, c in tris:
        p0, p1, p2 = verts[a], verts[b], verts[c]
        n = np.cross(p1 - p0, p2 - p0)
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n = n / ln
        d = float(np.dot(n, p0))
        for pn, pd in planes:
            if np.dot(pn, n) > 1.0 - 1e-6 and abs(pd - d) < tol:
                break
        else:
            planes.append((n, d))
    return planes


def corner_chamfer(verts, tris, card_w=70.0, card_h=156.0):
    """Measure the corner clip of the flat card outline from the mesh boundary.

    The card is a closed shell; its silhouette in plan (XY) is the outline the art is cut
    to.  For each of the four corners of the enclosing rectangle, walk the plan hull and
    find the two points where the outline leaves each edge: the chamfer leg length.
    """
    # plan-projected convex hull of the silhouette via supporting points per direction
    pts = verts[:, :2]
    xmin, ymin = pts.min(axis=0)
    xmax, ymax = pts.max(axis=0)
    out = {"plan_bbox_mm": [round(float(xmin), 4), round(float(ymin), 4),
                            round(float(xmax), 4), round(float(ymax), 4)],
           "plan_size_mm": [round(float(xmax - xmin), 4), round(float(ymax - ymin), 4)]}
    legs = {}
    chords = {}
    angles = {}
    for cx, sx in ((xmax, +1.0), (xmin, -1.0)):
        for cy, sy in ((ymax, +1.0), (ymin, -1.0)):
            # signed distance from the corner along each axis, for points near the corner
            dx = sx * (pts[:, 0] - cx)          # <= 0 inside
            dy = sy * (pts[:, 1] - cy)
            # the clip line is x*sx + y*sy = const near the corner; find its support
            s = dx + dy
            k = float(s.max())                  # closest approach to the corner (negative)
            on = np.abs(s - k) < 0.02           # points lying on the clip line
            if on.sum() >= 2:
                q = pts[on]
                span = q[:, :2]
                chord = float(np.hypot(np.ptp(span[:, 0]), np.ptp(span[:, 1])))
                leg = chord / math.sqrt(2.0)
                # true leg: distance from the corner to where the clip line meets each edge
                # clip line: sx*x + sy*y = sx*cx + sy*cy + k  ->  intercepts at k along axes
                leg_x = abs(k)
                ang = math.degrees(math.atan2(abs(np.ptp(span[:, 1])), abs(np.ptp(span[:, 0]))))
            else:
                chord = leg = leg_x = ang = float("nan")
            key = ("x+" if sx > 0 else "x-") + ("y+" if sy > 0 else "y-")
            legs[key] = round(leg_x, 4)
            chords[key] = round(chord, 4)
            angles[key] = round(ang, 4)
    out["corner_leg_mm"] = legs
    out["corner_chord_mm"] = chords
    out["corner_angle_deg"] = angles
    return out


def uv_stats(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    res = {"uv_layers": [l.name for l in mesh.uv_layers]}
    for idx, layer in enumerate(mesh.uv_layers):
        uv = np.empty(len(mesh.loops) * 2, np.float64)
        layer.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        res[f"uv{idx}_min"] = [round(float(uv[:, 0].min()), 6), round(float(uv[:, 1].min()), 6)]
        res[f"uv{idx}_max"] = [round(float(uv[:, 0].max()), 6), round(float(uv[:, 1].max()), 6)]
    return res


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX), automatic_bone_orientation=True)

    nodes = {}
    lod_verts = {}
    for obj in bpy.data.objects:
        e = {"type": obj.type,
             "parent": obj.parent.name if obj.parent else None,
             "location_m": [round(float(v), 8) for v in obj.location],
             "rotation_euler_deg": [round(math.degrees(v), 6) for v in obj.rotation_euler],
             "scale": [round(float(v), 8) for v in obj.scale]}
        if obj.type == "MESH":
            verts, tris = tri_array(obj)
            lod_verts[obj.name] = (verts, tris)
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            try:
                use = {}
                for f in bm.faces:
                    for ed in f.edges:
                        use[ed.index] = use.get(ed.index, 0) + 1
                hist = {}
                for v in use.values():
                    hist[str(v)] = hist.get(str(v), 0) + 1
                degen = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
            finally:
                bm.free()
            e.update({
                "triangles": int(len(tris)),
                "polygons": len(obj.data.polygons),
                "vertices": int(len(verts)),
                "materials": [m.name if m else None for m in obj.data.materials],
                "edge_use_histogram": hist,
                "degenerate_faces": degen,
                "extents_mm": {
                    "min": [round(float(x), 4) for x in verts.min(axis=0)],
                    "max": [round(float(x), 4) for x in verts.max(axis=0)],
                    "size": [round(float(x), 4) for x in np.ptp(verts, axis=0)],
                },
            })
            e.update(uv_stats(obj))
            # bounding sphere radius about the origin and about the bbox centre
            e["radius_about_origin_mm"] = round(float(np.linalg.norm(verts, axis=1).max()), 4)
            ctr = (verts.min(axis=0) + verts.max(axis=0)) * 0.5
            e["bbox_centre_mm"] = [round(float(x), 5) for x in ctr]
            e["radius_about_bbox_centre_mm"] = round(
                float(np.linalg.norm(verts - ctr, axis=1).max()), 4)
            if obj.name.endswith("LOD0") or obj.name.startswith("UCX"):
                e["chamfer"] = corner_chamfer(verts, tris)
            if obj.name.endswith(("LOD1", "LOD2")):
                e["chamfer"] = corner_chamfer(verts, tris)
        nodes[obj.name] = e

    # --- collision hull: convexity + containment of LOD0 -------------------------------
    hull_name = next((n for n in nodes if n.startswith("UCX_")), None)
    coll = {"hull": hull_name}
    if hull_name and hull_name in lod_verts:
        hv, ht = lod_verts[hull_name]
        planes = hull_planes(hv, ht)
        coll["distinct_planes"] = len(planes)
        # convexity: every hull vertex is on or inside every plane
        worst_self = 0.0
        for n, d in planes:
            worst_self = max(worst_self, float((hv @ n - d).max()))
        coll["hull_self_max_outside_mm"] = round(worst_self, 9)
        coll["is_convex"] = worst_self < 1e-4
        for lod in ("SM_PaperBomb_LOD0", "SM_PaperBomb_LOD1", "SM_PaperBomb_LOD2"):
            if lod not in lod_verts:
                continue
            lv = lod_verts[lod][0]
            worst = 0.0
            for n, d in planes:
                worst = max(worst, float((lv @ n - d).max()))
            coll[f"{lod}_max_outside_mm"] = round(worst, 9)
            coll[f"{lod}_contained"] = worst < 1e-4
        coll["hull_vertices"] = int(len(hv))
        coll["hull_triangles"] = int(len(ht))

    # --- whole-asset bounds Unreal will compute (union of LOD0 + collision) ------------
    allv = np.concatenate([lod_verts[k][0] for k in lod_verts], axis=0)
    bmin, bmax = allv.min(axis=0), allv.max(axis=0)
    ctr = (bmin + bmax) * 0.5
    ext = (bmax - bmin) * 0.5
    unionr = float(np.linalg.norm(allv - ctr, axis=1).max())
    lod0v = lod_verts.get("SM_PaperBomb_LOD0", (allv, None))[0]
    l0min, l0max = lod0v.min(axis=0), lod0v.max(axis=0)
    l0ctr = (l0min + l0max) * 0.5
    bounds = {
        "union_min_mm": [round(float(x), 5) for x in bmin],
        "union_max_mm": [round(float(x), 5) for x in bmax],
        "union_size_mm": [round(float(x), 5) for x in (bmax - bmin)],
        "union_centre_mm": [round(float(x), 5) for x in ctr],
        "union_box_extent_mm": [round(float(x), 5) for x in ext],
        "union_sphere_radius_about_centre_mm": round(unionr, 5),
        "box_corner_radius_mm": round(float(np.linalg.norm(ext)), 5),
        "lod0_sphere_radius_about_lod0_centre_mm": round(
            float(np.linalg.norm(lod0v - l0ctr, axis=1).max()), 5),
        "size_cm": [round(float(x) / 10.0, 6) for x in (bmax - bmin)],
    }

    report = {
        "fbx": str(FBX),
        "sha256": sha256(FBX),
        "bytes": FBX.stat().st_size,
        "blender": bpy.app.version_string,
        "object_count": len(bpy.data.objects),
        "object_names": sorted(o.name for o in bpy.data.objects),
        "socket_nodes_in_fbx": sorted(o.name for o in bpy.data.objects
                                      if o.name.upper().startswith("SOCKET")),
        "nodes": nodes,
        "collision": coll,
        "bounds": bounds,
    }
    HERE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[truth] ->", OUT)
    for n in sorted(nodes):
        e = nodes[n]
        if e["type"] == "MESH":
            ch = e.get("chamfer", {}).get("corner_leg_mm")
            print(f"  {n:32s} {e['triangles']:5d} tris {e['vertices']:5d} v  chamfer={ch}")
        else:
            print(f"  {n:32s} {e['type']}")
    print("  collision:", json.dumps(coll))
    print("  bounds:", json.dumps(bounds))


main()


def octagon_check():
    """Plan outline of the UCX hull and of LOD0: distinct XY corner points and edge directions."""
    rep = json.loads(OUT.read_text(encoding="utf-8"))
    import itertools
    res = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        co = np.array([v.co[:] for v in obj.data.vertices]) * 1000.0
        # 2D convex hull of the plan (X,Y) projection (monotone chain)
        pts = sorted(set((round(float(x), 3), round(float(y), 3)) for x, y in co[:, :2]))
        def cross(o, a, b):
            return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
        lower, upper = [], []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 1e-6:
                lower.pop()
            lower.append(p)
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 1e-6:
                upper.pop()
            upper.append(p)
        hull = lower[:-1] + upper[:-1]
        edges = []
        for i in range(len(hull)):
            a, b = hull[i], hull[(i + 1) % len(hull)]
            L = math.hypot(b[0]-a[0], b[1]-a[1])
            ang = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180.0
            edges.append({"len_mm": round(L, 4), "angle_deg": round(ang, 3)})
        res[obj.name] = {"plan_hull_vertices": len(hull), "plan_hull": hull, "edges": edges}
    rep["plan_outline"] = res
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    for k, v in res.items():
        print("[outline]", k, v["plan_hull_vertices"], [(e["len_mm"], e["angle_deg"]) for e in v["edges"]])


octagon_check()
