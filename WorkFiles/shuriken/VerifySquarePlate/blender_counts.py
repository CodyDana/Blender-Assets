"""Blender-side reference counts for the independent import verification (headless, saves nothing).

Two modes, picked by what Blender opened:
  * no file: re-import the SHIPPED FBX into an empty factory scene and record every node
      blender.exe -b --factory-startup --python-exit-code 3 --python blender_counts.py
    -> vsp_blender_fbx.json
  * Assets/Shuriken.blend opened read-only: evaluated triangle counts of the form's LOD objects
      blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python blender_counts.py
    -> vsp_blender_blend.json
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vsp_config as V  # noqa: E402

S = V.spec()


def plane_outside(hull_polys, pts):
    allv = [Vector(v) for poly in hull_polys for v in poly]
    centroid = sum(allv, Vector((0, 0, 0))) / len(allv)
    planes = []
    for poly in hull_polys:
        a, b, c = Vector(poly[0]), Vector(poly[1]), Vector(poly[2])
        n = (b - a).cross(c - a)
        if n.length < 1e-12:
            continue
        n.normalize()
        if n.dot(centroid - a) > 0:
            n = -n
        planes.append((n, a))
    return max(max(n.dot(Vector(p) - a) for n, a in planes) for p in pts), len(planes)


def mesh_record(ob):
    me = ob.data
    me.calc_loop_triangles()
    mw = ob.matrix_world
    ws = [(mw @ v.co) * 100.0 for v in me.vertices]
    rec = {
        "triangles": len(me.loop_triangles), "polygons": len(me.polygons), "vertices": len(me.vertices),
        "non_tri_polygons": sum(1 for p in me.polygons if len(p.vertices) != 3),
        "uv_layers": [uv.name for uv in me.uv_layers],
        "bounds_min_cm": [round(min(c[i] for c in ws), 6) for i in range(3)],
        "bounds_max_cm": [round(max(c[i] for c in ws), 6) for i in range(3)],
        "matrix_world_is_unit_scale_cm": [round(v, 6) for v in mw.to_scale()],
    }
    rec["size_cm"] = [round(rec["bounds_max_cm"][i] - rec["bounds_min_cm"][i], 6) for i in range(3)]
    return rec, ws, [[tuple((mw @ me.vertices[i].co) * 100.0) for i in p.vertices] for p in me.polygons]


def fbx_mode():
    out = {"mode": "fbx", "blender": bpy.app.version_string, "form": V.FORM, "fbx": str(S["fbx"]),
           "fbx_sha256_before_import": V.sha256(S["fbx"]), "sidecar_sha256": V.sha256(S["sidecar"])}
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(S["fbx"]))
    nodes, geo = {}, {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == "MESH":
            rec, ws, polys = mesh_record(ob)
            entry.update(rec)
            geo[ob.name] = (ws, polys)
        else:
            entry["custom_props"] = {k: str(ob[k]) for k in ob.keys() if not k.startswith("_")}
        nodes[ob.name] = entry
    out["nodes"] = nodes
    out["fbx_sha256_after_import"] = V.sha256(S["fbx"])
    out["lod_triangles"] = [nodes.get(n, {}).get("triangles") for n in S["lod_node"]]
    groups = [n for n, e in nodes.items() if e["type"] == "EMPTY" and e.get("custom_props", {}).get("fbx_type") == "LodGroup"]
    out["lod_group_nodes"] = groups
    out["lod_children_parented_to_group"] = all(nodes.get(n, {}).get("parent") in groups for n in S["lod_node"])
    out["socket_nodes_in_fbx"] = sorted(n for n in nodes if n.startswith("SOCKET_"))
    out["ucx_nodes"] = sorted(n for n in nodes if n.startswith("UCX_"))
    out["ucx_name_matches_lod0_node"] = out["ucx_nodes"] == [S["ucx_node"]]
    if S["ucx_node"] in geo:
        hws, hpolys = geo[S["ucx_node"]]
        uniq = {tuple(round(c, 5) for c in v) for v in hws}
        worst_self, _ = plane_outside(hpolys, hws)
        hull = {"verts_unique": len(uniq), "vertices": len(hws), "polygons": len(hpolys),
                "triangles": nodes[S["ucx_node"]]["triangles"], "size_cm": nodes[S["ucx_node"]]["size_cm"],
                "convex_self_check_max_cm": round(max(worst_self, 0.0), 7),
                "verts_cm": sorted([round(c, 5) for c in v] for v in uniq)}
        for i, n in enumerate(S["lod_node"]):
            if n in geo:
                worst, _ = plane_outside(hpolys, geo[n][0])
                hull[f"LOD{i}_max_outside_cm"] = round(max(worst, 0.0), 7)
        out["shipped_hull"] = hull
    # spec geometry, read from the shipped LOD0 in Blender's frame (+X at a corner, Z up)
    lod0 = geo.get(S["lod_node"][0], ([], []))[0]
    if lod0:
        ex = max(lod0, key=lambda p: p.x)
        ey = max(lod0, key=lambda p: p.y)
        radii = [math.hypot(p.x, p.y) for p in lod0]
        imin = min(range(len(lod0)), key=lambda i: radii[i])
        out["lod0_geometry_cm"] = {
            "max_x_vertex": [round(c, 6) for c in ex], "max_y_vertex": [round(c, 6) for c in ey],
            "corner_radius_cm": round(max(radii), 6),
            "hole_min_radius_cm": round(radii[imin], 6),
            "hole_min_radius_azimuth_deg": round(math.degrees(math.atan2(lod0[imin].y, lod0[imin].x)), 4),
            "hole_min_radius_vertex_count": sum(1 for r in radii if abs(r - radii[imin]) < 1e-5),
        }
        g = S["grip"]
        rim = {}
        for az in g["azimuths_deg"]:
            target = Vector((g["radius_cm"] * math.cos(math.radians(az)), g["radius_cm"] * math.sin(math.radians(az)), 0.0))
            near = min(lod0, key=lambda p: (p - target).length)
            ray = [p for p in lod0 if abs(math.degrees(math.atan2(p.y, p.x)) - az) < 1e-3]
            rim[str(az)] = {"nearest_vertex_cm": [round(c, 6) for c in near],
                            "nearest_distance_cm": round((near - target).length, 6),
                            "max_radius_on_azimuth_cm": round(max((math.hypot(p.x, p.y) for p in ray), default=-1), 6)}
        out["lod0_grip_rim_blender_frame"] = rim
    (V.HERE / "vsp_blender_fbx.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


def blend_mode():
    out = {"mode": "blend", "blender": bpy.app.version_string, "blend": bpy.data.filepath, "form": V.FORM,
           "is_dirty_after_load": bpy.data.is_dirty}
    dg = bpy.context.evaluated_depsgraph_get()
    tris, objs = [], {}
    for name in S["lod_node"] + [S["ucx_node"]]:
        ob = bpy.data.objects.get(name)
        if ob is None:
            objs[name] = None
            tris.append(None)
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        objs[name] = {"triangles": n, "vertices": len(me.vertices), "polygons": len(me.polygons),
                      "scale": list(ob.scale), "rotation_euler": list(ob.rotation_euler),
                      "parent": ob.parent.name if ob.parent else None,
                      "custom_props": {k: str(ob[k]) for k in ob.keys() if not k.startswith("_")}}
        ev.to_mesh_clear()
        if name in S["lod_node"]:
            tris.append(n)
    sockets = {o.name: {"type": o.type, "parent": o.parent.name if o.parent else None,
                        "location_m_world": [round(c, 7) for c in o.matrix_world.translation],
                        "rotation_euler_deg": [round(math.degrees(c), 4) for c in o.matrix_world.to_euler()]}
               for o in bpy.data.objects if o.name.startswith(f"SOCKET_{S['lod_node'][0]}_")}
    out.update({"objects": objs, "lod_triangles": tris, "socket_empties": sockets})
    (V.HERE / "vsp_blender_blend.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if bpy.data.filepath:
    blend_mode()
else:
    fbx_mode()
print("VSP_BLENDER_DONE")
