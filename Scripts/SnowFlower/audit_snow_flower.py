"""Read-only structural audit; run with Blender --background <blend> --python this.py.

No source datablocks are changed or saved. Distinct intersecting ornamental shells
are intentionally not treated as topology defects. This is not gameplay approval.
"""
from pathlib import Path
from collections import Counter, defaultdict
import datetime
import hashlib
import json
import math
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUTPUT = ROOT / "WorkFiles/SnowFlower/audit_report.json"
RASTER_SIZE = 128


def finite(values):
    return all(math.isfinite(float(x)) for x in values)


def bounds(points):
    points = [tuple(p) for p in points if finite(p)]
    if not points:
        return None
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)]}


def uv_audit(mesh):
    result = {}
    for layer in mesh.uv_layers:
        uv = [tuple(d.uv) for d in layer.data]
        valid = [p for p in uv if finite(p)]
        entry = {
            "loops": len(uv), "expected_loops": len(mesh.loops),
            "nonfinite_loops": len(uv) - len(valid),
            "loops_outside_0_1": sum(any(v < -1e-6 or v > 1 + 1e-6 for v in p) for p in valid),
            "bounds": {"min": [min(p[i] for p in valid) for i in range(2)],
                       "max": [max(p[i] for p in valid) for i in range(2)]} if valid else None,
        }
        occupied = bytearray(RASTER_SIZE * RASTER_SIZE)
        collapsed = 0
        total_area = 0.0
        for tri in mesh.loop_triangles:
            a, b, c = (uv[i] for i in tri.loops)
            if not all(finite(p) for p in (a, b, c)):
                continue
            ab = (b[0] - a[0], b[1] - a[1])
            ac = (c[0] - a[0], c[1] - a[1])
            det = ab[0] * ac[1] - ab[1] * ac[0]
            area = abs(det) * 0.5
            total_area += area
            if area <= 1e-14:
                collapsed += 1
                continue
            xmin = max(0, math.ceil(min(a[0], b[0], c[0]) * RASTER_SIZE - 0.5))
            xmax = min(RASTER_SIZE - 1, math.floor(max(a[0], b[0], c[0]) * RASTER_SIZE - 0.5))
            ymin = max(0, math.ceil(min(a[1], b[1], c[1]) * RASTER_SIZE - 0.5))
            ymax = min(RASTER_SIZE - 1, math.floor(max(a[1], b[1], c[1]) * RASTER_SIZE - 0.5))
            for y in range(ymin, ymax + 1):
                py = (y + 0.5) / RASTER_SIZE - a[1]
                for x in range(xmin, xmax + 1):
                    index = y * RASTER_SIZE + x
                    if occupied[index]:
                        continue
                    px = (x + 0.5) / RASTER_SIZE - a[0]
                    u = (px * ac[1] - py * ac[0]) / det
                    v = (ab[0] * py - ab[1] * px) / det
                    if u >= -1e-10 and v >= -1e-10 and u + v <= 1 + 1e-10:
                        occupied[index] = 1
        entry.update({"collapsed_uv_triangles": collapsed, "summed_triangle_uv_area": total_area,
                      "estimated_unique_0_1_coverage": sum(occupied) / len(occupied),
                      "coverage_method": f"{RASTER_SIZE}x{RASTER_SIZE} pixel-center union estimate; not an overlap proof"})
        result[layer.name] = entry
    return result


def image_nodes(tree, visited=None):
    visited = set() if visited is None else visited
    if tree is None or tree.as_pointer() in visited:
        return []
    visited.add(tree.as_pointer())
    result = []
    for node in tree.nodes:
        if node.type == "TEX_IMAGE":
            result.append(node)
        elif node.type == "GROUP":
            result.extend(image_nodes(node.node_tree, visited))
    return result


def textures(objects):
    mats = {m for obj in objects for m in obj.data.materials if m is not None}
    references, missing = [], []
    for mat in sorted(mats, key=lambda x: x.name):
        for node in image_nodes(mat.node_tree):
            img = node.image
            item = {"material": mat.name, "node": node.name, "image": img.name if img else None}
            if img is None:
                item["problem"] = "Image Texture node has no image assigned"
                missing.append(item)
            else:
                item.update({"source": img.source, "filepath": img.filepath,
                             "packed": bool(img.packed_file or len(img.packed_files)),
                             "has_data": img.has_data, "dimensions": list(img.size)})
                if img.source in {"FILE", "MOVIE", "SEQUENCE", "TILED"} and not item["packed"]:
                    path = bpy.path.abspath(img.filepath, library=img.library)
                    if img.source == "TILED":
                        checks = [Path(path.replace("<UDIM>", str(t.number))) for t in img.tiles]
                    else:
                        checks = [Path(path)]
                    item["resolved_paths"] = [str(p) for p in checks]
                    item["missing_paths"] = [str(p) for p in checks if not p.is_file()]
                    if item["missing_paths"]:
                        missing.append(item)
            references.append(item)
    return {"material_count": len(mats), "image_references": references, "missing_references": missing,
            "note": "Procedural materials can have zero image references; shader portability is outside this audit."}


def mesh_audit(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    coords = [v.co.copy() for v in mesh.vertices]
    wb = bounds([obj.matrix_world @ p for p in coords])
    diag = Vector(wb["size"]).length if wb else 0
    length_epsilon = max(diag * 1e-10, 1e-12)
    area_epsilon = max(diag * diag * 1e-14, 1e-22)
    zero_edges = [e.index for e in bm.edges if e.calc_length() <= length_epsilon]
    degenerate = []
    for i, tri in enumerate(mesh.loop_triangles):
        a, b, c = [obj.matrix_world @ coords[j] for j in tri.vertices]
        if (b - a).cross(c - a).length * 0.5 <= area_epsilon:
            degenerate.append(i)
    canonical_faces = Counter(tuple(sorted(p.vertices)) for p in mesh.polygons)
    topo = {
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "nonmanifold_edges_with_3_or_more_faces": sum(len(e.link_faces) > 2 for e in bm.edges),
        "wire_edges": sum(e.is_wire for e in bm.edges),
        "loose_vertices": sum(not v.link_edges for v in bm.verts),
        "nonmanifold_vertices": sum(not v.is_manifold for v in bm.verts),
        "inconsistent_winding_edges": sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
        "zero_length_edges": len(zero_edges), "zero_length_edge_examples": zero_edges[:20],
        "degenerate_triangles": len(degenerate), "degenerate_triangle_examples": degenerate[:20],
        "duplicate_indexed_faces": sum(n - 1 for n in canonical_faces.values() if n > 1),
        "nonfinite_vertices": sum(not finite(v.co) for v in mesh.vertices),
        "triangle_area_epsilon_world_units_squared": area_epsilon,
    }
    component_by_vertex = {}
    components = []
    for vert in bm.verts:
        if vert.index in component_by_vertex:
            continue
        cid = len(components)
        queue, indices = [vert], []
        component_by_vertex[vert.index] = cid
        while queue:
            current = queue.pop()
            indices.append(current.index)
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor.index not in component_by_vertex:
                    component_by_vertex[neighbor.index] = cid
                    queue.append(neighbor)
        components.append({"vertices": len(indices), "origin": coords[indices[0]], "volume": 0.0,
                           "closed": True, "triangles": 0})
    for edge in bm.edges:
        if not edge.is_manifold:
            components[component_by_vertex[edge.verts[0].index]]["closed"] = False
    for tri in mesh.loop_triangles:
        comp = components[component_by_vertex[tri.vertices[0]]]
        a, b, c = [coords[j] - comp["origin"] for j in tri.vertices]
        comp["volume"] += a.dot(b.cross(c)) / 6.0
        comp["triangles"] += 1
    topo["connected_components"] = len(components)
    topo["closed_components"] = sum(c["closed"] and c["triangles"] > 0 for c in components)
    topo["inward_closed_components"] = sum(c["closed"] and c["triangles"] > 0 and c["volume"] < -1e-20 for c in components)
    topo["inward_component_examples"] = [
        {"component": i, "vertices": c["vertices"], "signed_volume_local": c["volume"]}
        for i, c in enumerate(components) if c["closed"] and c["triangles"] > 0 and c["volume"] < -1e-20
    ][:20]
    bm.free()
    transform = {"location": list(obj.location), "rotation_euler": list(obj.rotation_euler),
                 "scale": list(obj.scale), "world_determinant": obj.matrix_world.determinant(),
                 "parent": obj.parent.name if obj.parent else None,
                 "local_identity": all(abs(v) < 1e-7 for v in obj.location)
                 and all(abs(v) < 1e-7 for v in obj.rotation_euler)
                 and all(abs(v - 1) < 1e-7 for v in obj.scale),
                 "world_matrix_finite": finite(v for row in obj.matrix_world for v in row)}
    uv = uv_audit(mesh)
    defects = []
    for key in ("nonmanifold_edges_with_3_or_more_faces", "wire_edges", "loose_vertices",
                "inconsistent_winding_edges", "zero_length_edges", "degenerate_triangles",
                "duplicate_indexed_faces", "nonfinite_vertices", "inward_closed_components"):
        if topo[key]:
            defects.append(f"{key}: {topo[key]}")
    review = []
    if topo["boundary_edges"]:
        review.append(f"{topo['boundary_edges']} boundary edges: verify intentional open surfaces")
    if not uv:
        review.append("No UV map; add a UV map before texture baking or textured export")
    for name, entry in uv.items():
        for key in ("nonfinite_loops", "collapsed_uv_triangles"):
            if entry[key]:
                defects.append(f"UV {name} {key}: {entry[key]}")
        if entry["loops_outside_0_1"]:
            review.append(f"UV {name} has {entry['loops_outside_0_1']} loops outside tile 0–1")
    if not transform["local_identity"]:
        review.append("Non-identity local transform: preserve deliberately or apply before export")
    if transform["world_determinant"] <= 0:
        defects.append("World transform is reflected or singular")
    if not transform["world_matrix_finite"]:
        defects.append("World transform contains nonfinite values")
    return {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "polygons": len(mesh.polygons),
            "triangles": len(mesh.loop_triangles), "bounds_world": wb, "bounds_local": bounds(coords),
            "topology": topo, "uv_layers": uv, "transforms": transform,
            "modifiers": [{"name": m.name, "type": m.type, "viewport": m.show_viewport,
                           "render": m.show_render} for m in obj.modifiers],
            "materials": [m.name if m else None for m in mesh.materials],
            "defects": defects, "review_notes": review}


source = Path(bpy.data.filepath)
source_hash_before = hashlib.sha256(source.read_bytes()).hexdigest()
objects = sorted([o for o in bpy.context.scene.objects if o.type == "MESH" and o.get("sf_export")], key=lambda o: o.name)
report = {
    "audit_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": str(source), "source_sha256": source_hash_before, "blender_version": bpy.app.version_string,
    "scope": "Base mesh datablocks of sf_export=True objects. No renders, writes to .blend, geometric intersection checks, or gameplay approval.",
    "unit_system": bpy.context.scene.unit_settings.system,
    "meters_per_blender_unit": bpy.context.scene.unit_settings.scale_length,
    "objects": {o.name: mesh_audit(o) for o in objects}, "textures": textures(objects),
}
report["totals"] = {key: sum(o[key] for o in report["objects"].values()) for key in ("vertices", "edges", "polygons", "triangles")}
report["totals"]["mesh_objects"] = len(objects)
report["overall_bounds_world"] = bounds([o.matrix_world @ v.co for o in objects for v in o.data.vertices])
report["defects"] = [{"object": name, "finding": finding} for name, obj in report["objects"].items() for finding in obj["defects"]]
report["review_notes"] = [{"object": name, "finding": finding} for name, obj in report["objects"].items() for finding in obj["review_notes"]]
report["source_unchanged_on_disk"] = hashlib.sha256(source.read_bytes()).hexdigest() == source_hash_before
report["status"] = "DEFECTS_FOUND" if report["defects"] or report["textures"]["missing_references"] or not objects else "NO_CHECKED_STRUCTURAL_DEFECTS_FOUND"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"report": str(OUTPUT), "status": report["status"], "totals": report["totals"],
                  "defects": report["defects"], "review_notes": report["review_notes"],
                  "missing_texture_references": len(report["textures"]["missing_references"]),
                  "source_unchanged_on_disk": report["source_unchanged_on_disk"]}, indent=2))
