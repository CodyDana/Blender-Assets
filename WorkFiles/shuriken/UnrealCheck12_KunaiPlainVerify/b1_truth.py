"""UnrealCheck12 (independent Unreal verifier, SM_Kunai_Plain) - Blender-side truth.  READ ONLY, never saves:

    blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python b1_truth.py

Two independent Blender readings, written fresh for this verification:
  BLEND  the kunai objects in Assets/Shuriken.blend (evaluated LOD meshes, per-slot triangles, UCX, SOCKET_ Empties,
         the LodGroup Empty)
  FBX    a factory-startup re-import of the exact shipped bytes (SHA-256 recorded before and after), world matrices
         applied: per-LOD arrays (positions, triangles, corner UV0, corner normals, material index per triangle), both
         UCX hulls (vertices, triangles, volume, centroid, convexity), LOD containment in each hull and in their union,
         the hull-derived centre of mass, the predicted Unreal bounds (legacy importer: X kept, Y negated, Z kept,
         metres -> cm; sphere radius = farthest vertex from the box centre) and the lettering band as the shipped FBX
         carries it (the wrap triangles whose UV0 lies in the report's band rectangle).
Writes b1_truth.json next to this file.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck12_KunaiPlainVerify"
MESH = "SM_Kunai_Plain"
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
REPORT = PROJ / "WorkFiles" / "shuriken" / "kunai_plain_report.json"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def mesh_arrays(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world.copy()
    m3 = mw.to_3x3()
    verts = [tuple(mw @ v.co) for v in me.vertices]
    out = {"verts": verts,
           "tris": [tuple(t.vertices) for t in me.loop_triangles],
           "tri_loops": [tuple(t.loops) for t in me.loop_triangles],
           "tri_mat": [int(t.material_index) for t in me.loop_triangles],
           "loop_vert": [lp.vertex_index for lp in me.loops],
           "uv_names": [uv.name for uv in me.uv_layers],
           "uv0": [tuple(d.uv) for d in me.uv_layers[0].data] if me.uv_layers else [],
           "loop_normals": [tuple((m3 @ n.vector).normalized()) for n in me.corner_normals],
           "polygons": len(me.polygons),
           "det": m3.determinant(),
           "slots": [s.material.name if s.material else None for s in ob.material_slots]}
    ev.to_mesh_clear()
    return out


def ue_cm(v):
    return (v[0] * 100.0, -v[1] * 100.0, v[2] * 100.0)


def bbox(pts):
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def volume_centroid(verts, tris):
    vol, c = 0.0, [0.0, 0.0, 0.0]
    for i, j, k in tris:
        a, b, cc = verts[i], verts[j], verts[k]
        d = dot(a, cross(b, cc)) / 6.0
        vol += d
        for m in range(3):
            c[m] += d * (a[m] + b[m] + cc[m]) / 4.0
    return vol, [x / vol for x in c] if abs(vol) > 1e-30 else None


def planes_of(verts, tris):
    cen = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    out = []
    for i, j, k in tris:
        n = cross(sub(verts[j], verts[i]), sub(verts[k], verts[i]))
        ln = math.sqrt(dot(n, n))
        if ln < 1e-18:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        if dot(n, sub(cen, verts[i])) > 0:
            n = (-n[0], -n[1], -n[2])
        out.append((n, verts[i]))
    return out


def outside(planes, p):
    return max(dot(n, sub(p, a)) for n, a in planes)


def per_slot(a):
    counts = {}
    for m in a["tri_mat"]:
        counts[m] = counts.get(m, 0) + 1
    return {str(k): v for k, v in sorted(counts.items())}


def lettering(a, rect):
    """Wrap triangles whose UV0 centroid lies inside the band rectangle (Blender UV)."""
    pts, uvs = [], []
    ntri = 0
    for tl, tv in zip(a["tri_loops"], a["tris"]):
        cu = sum(a["uv0"][li][0] for li in tl) / 3.0
        cv = sum(a["uv0"][li][1] for li in tl) / 3.0
        if rect["u_min"] - 1e-6 <= cu <= rect["u_max"] + 1e-6 and rect["v_min"] - 1e-6 <= cv <= rect["v_max"] + 1e-6:
            ntri += 1
            for li in tl:
                pts.append(a["verts"][a["loop_vert"][li]])
                uvs.append(a["uv0"][li])
    if not pts:
        return {"triangles": 0}

    def corr(x, y):
        mx, my = sum(x) / len(x), sum(y) / len(y)
        num = sum((p - mx) * (q - my) for p, q in zip(x, y))
        den = math.sqrt(sum((p - mx) ** 2 for p in x) * sum((q - my) ** 2 for q in y)) or 1.0
        return num / den
    xs, ys, zs = [p[0] * 1000 for p in pts], [p[1] * 1000 for p in pts], [p[2] * 1000 for p in pts]
    us, vs = [q[0] for q in uvs], [q[1] for q in uvs]
    return {"triangles": ntri, "x_mm": [min(xs), max(xs)], "y_mm": [min(ys), max(ys)], "z_mm": [min(zs), max(zs)],
            "u": [min(us), max(us)], "v": [min(vs), max(vs)],
            "corr_u_x": corr(us, xs), "corr_v_y_blender": corr(vs, ys),
            "angle_about_x_deg": [math.degrees(math.atan2(min(ys), max(zs))), math.degrees(math.atan2(max(ys), max(zs)))]}


def read_scene(full):
    rec = {"objects": sorted((o.name, o.type, o.parent.name if o.parent else None) for o in bpy.data.objects
                             if MESH in o.name),
           "lods": {}, "hulls": {}, "sockets": {}, "lod_group": None}
    arrays = {}
    for i in range(6):
        ob = bpy.data.objects.get(f"{MESH}_LOD{i}")
        if ob is None:
            break
        a = mesh_arrays(ob)
        arrays[i] = a
        lo, hi = bbox(a["verts"])
        ue = [ue_cm(v) for v in a["verts"]]
        ulo, uhi = bbox(ue)
        c = [(ulo[m] + uhi[m]) / 2.0 for m in range(3)]
        rec["lods"][f"LOD{i}"] = {
            "triangles": len(a["tris"]), "vertices": len(a["verts"]), "polygons": a["polygons"],
            "corners": len(a["loop_vert"]), "uv_layers": a["uv_names"], "material_slots": a["slots"],
            "triangles_per_slot": per_slot(a), "matrix_world_det": round(a["det"], 12),
            "parent": ob.parent.name if ob.parent else None,
            "parent_fbx_type": ob.parent.get("fbx_type") if ob.parent else None,
            "bbox_min_mm": [x * 1000.0 for x in lo], "bbox_max_mm": [x * 1000.0 for x in hi],
            "ue_bounds_min_cm": ulo, "ue_bounds_max_cm": uhi, "ue_size_cm": [uhi[m] - ulo[m] for m in range(3)],
            "ue_bounds_sphere_radius_cm": max(math.dist(p, c) for p in ue),
            "uv0_u_range": [min(u for u, _ in a["uv0"]), max(u for u, _ in a["uv0"])] if a["uv0"] else None,
            "uv0_v_range": [min(v for _, v in a["uv0"]), max(v for _, v in a["uv0"])] if a["uv0"] else None}
        if ob.parent and ob.parent.type == "EMPTY":
            rec["lod_group"] = {"name": ob.parent.name, "fbx_type": ob.parent.get("fbx_type")}
    hulls = {}
    for ob in sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("UCX_") and MESH in o.name),
                     key=lambda o: o.name):
        a = mesh_arrays(ob)
        pl = planes_of(a["verts"], a["tris"])
        vol, cen = volume_centroid(a["verts"], a["tris"])
        hulls[ob.name] = (a, pl)
        uniq = {tuple(round(c, 9) for c in v) for v in a["verts"]}
        h = {"triangles": len(a["tris"]), "vertices": len(a["verts"]), "unique_vertices": len(uniq),
             "parent": ob.parent.name if ob.parent else None,
             "convex_self_max_outside_mm": max(outside(pl, v) for v in a["verts"]) * 1000.0,
             "volume_mm3": vol * 1e9, "centroid_mm": [x * 1000.0 for x in cen] if cen else None,
             "bbox_min_mm": [x * 1000 for x in bbox(a["verts"])[0]], "bbox_max_mm": [x * 1000 for x in bbox(a["verts"])[1]]}
        for i, la in arrays.items():
            h[f"LOD{i}_max_outside_mm"] = max(outside(pl, v) for v in la["verts"]) * 1000.0
        rec["hulls"][ob.name] = h
    if hulls:
        for i, la in arrays.items():
            worst = 0.0
            for v in la["verts"]:
                worst = max(worst, min(outside(pl, v) for _a, pl in hulls.values()))
            rec[f"LOD{i}_max_outside_hull_union_mm"] = worst * 1000.0
        tv = sum(rec["hulls"][n]["volume_mm3"] for n in hulls)
        rec["hull_total_volume_mm3"] = tv
        rec["hull_derived_com_mm"] = [sum(rec["hulls"][n]["volume_mm3"] * rec["hulls"][n]["centroid_mm"][m]
                                          for n in hulls) / tv for m in range(3)]
    for ob in bpy.data.objects:
        if ob.name.startswith("SOCKET_") and MESH in ob.name:
            lod0 = bpy.data.objects.get(f"{MESH}_LOD0")
            m = (lod0.matrix_world.inverted() @ ob.matrix_world) if lod0 else ob.matrix_world
            loc, rot, scl = m.decompose()
            rec["sockets"][ob.name] = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                                       "location_mm": [x * 1000.0 for x in loc],
                                       "euler_deg": [math.degrees(e) for e in rot.to_euler()],
                                       "scale": list(scl), "predicted_ue_location_cm": list(ue_cm(loc))}
    return rec, arrays, hulls


def dump(a):
    return {"verts_m": [[round(c, 10) for c in v] for v in a["verts"]], "tris": a["tris"], "tri_loops": a["tri_loops"],
            "tri_mat": a["tri_mat"], "loop_vert": a["loop_vert"], "uv0": [[round(c, 9) for c in uv] for uv in a["uv0"]],
            "loop_normals": [[round(c, 7) for c in n] for n in a["loop_normals"]], "slots": a["slots"]}


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    rect = report["lettering"]["uv"]["uv0_blender"]
    out = {"blend": bpy.data.filepath, "blend_sha256": sha256(bpy.data.filepath), "blender": bpy.app.version_string,
           "fbx": str(FBX), "fbx_sha256": sha256(FBX), "sidecar_sha256": sha256(SIDECAR),
           "report_export_sha256": report.get("export_sha256"), "lettering_rect_blender": rect}
    out["blend_scene"], barr, _ = read_scene(True)
    if 0 in barr:
        out["blend_scene"]["lettering_band_LOD0"] = lettering(barr[0], rect)
    out["blend_negative_scale_objects"] = [o.name for o in bpy.data.objects
                                           if MESH in o.name and o.matrix_world.to_3x3().determinant() < 0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    out["fbx_scene"], arrays, hulls = read_scene(True)
    out["fbx_scene"]["all_nodes"] = sorted((o.name, o.type, o.parent.name if o.parent else None,
                                            o.get("fbx_type") if o.type == "EMPTY" else None,
                                            round(o.matrix_world.to_3x3().determinant(), 9)) for o in bpy.data.objects)
    out["fbx_scene"]["lettering_band"] = {f"LOD{i}": lettering(a, rect) for i, a in arrays.items()}
    out["fbx_arrays"] = {f"LOD{i}": dump(a) for i, a in arrays.items()}
    out["fbx_hull_arrays"] = {n: dump(a) for n, (a, _pl) in hulls.items()}
    out["fbx_sha256_after"] = sha256(FBX)
    (HERE / "b1_truth.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("UC12_B1_DONE")


main()
