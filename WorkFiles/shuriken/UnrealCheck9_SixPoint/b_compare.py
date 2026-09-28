"""UnrealCheck9 Blender half (headless, saves nothing): Blender truth + Unreal re-export round trip for the six-point.

  blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python b_compare.py

  B0 Blender truth from Assets/Shuriken.blend (opened read-only, never saved): per-LOD evaluated triangles, the
     UCX object's vertices, the socket Empties' world transforms.
  B1 the shipped FBX (exact bytes, SHA-256 recorded) re-imported: per-LOD triangles, UCX vertices.
  R1 hull: Unreal's STORED hull (from s4's export with collision) == shipped UCX_SM_Shuriken_SixPoint_LOD0_00:
     same unique vertex set (1e-5 cm), same triangle count, same volume, two-sided vertex distance; LOD0/1/2
     max distance OUTSIDE the stored hull (shipped and Unreal positions).
  R2 per LOD: Unreal triangles == Blender == shipped FBX; two-sided position distance.
  R3 UV1 (Unreal-generated lightmap UVs, render data): inside [0,1], exact pairwise triangle overlap area
     (convex clipping), zero-area/flipped triangles, texel sharing between charts at the asset's lightmap
     resolution (informational), plus a negative control that must detect an injected overlap.
  R4 sockets: Unreal Grip/Trail (s3 read-back) mapped to Blender axes (x, -y, z) == .blend Empties; Grip lies on
     the LOD0 hub rim between two tips with its +X axis along the outward wall normal.
  R5 tips: the six LOD0 extreme vertices sit at 0, 60, ... 300 deg, +X down one tip, radius 4.9 cm.
Writes b_compare.json.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck9_SixPoint")
PROJ = HERE.parents[2]
MESH = "SM_Shuriken_SixPoint"
SHIPPED = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
UE_FBX = HERE / "roundtrip" / f"{MESH}_from_unreal.fbx"
S3 = json.loads((HERE / "s3_readback.json").read_text(encoding="utf-8"))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ B0 blend truth
def blend_truth():
    out = {"blend": bpy.data.filepath, "unit_scale_length": bpy.context.scene.unit_settings.scale_length,
           "unit_system": bpy.context.scene.unit_settings.system, "lods": {}, "sockets": {}}
    dg = bpy.context.evaluated_depsgraph_get()
    to_cm = 100.0 * bpy.context.scene.unit_settings.scale_length
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith(f"{MESH}_LOD"):
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            out["lods"][ob.name] = {"triangles": len(me.loop_triangles), "vertices": len(me.vertices),
                                    "modifiers": [m.type for m in ob.modifiers]}
            ev.to_mesh_clear()
        elif ob.type == "MESH" and ob.name.startswith(f"UCX_{MESH}"):
            me = ob.data
            mw = ob.matrix_world
            out["ucx"] = {"name": ob.name, "verts_cm": [[c * to_cm for c in (mw @ v.co)] for v in me.vertices],
                          "faces": len(me.polygons)}
        elif ob.type == "EMPTY" and ob.name.startswith(f"SOCKET_{MESH}"):
            mw = ob.matrix_world
            loc = mw.to_translation() * to_cm
            x_axis = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
            out["sockets"][ob.name.rsplit("_", 1)[-1]] = {
                "name": ob.name, "location_cm_blender": [round(c, 6) for c in loc],
                "x_axis_blender": [round(c, 6) for c in x_axis],
                "scale": [round(c, 6) for c in mw.to_scale()], "parent": ob.parent.name if ob.parent else None}
    return out


# ------------------------------------------------------------------ FBX loading
def load_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    nodes = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        mw = ob.matrix_world
        verts = [tuple(c * 100.0 for c in (mw @ v.co)) for v in me.vertices]
        nodes[ob.name] = {
            "obj": ob.name,
            "verts": verts,
            "tris": [tuple(t.vertices) for t in me.loop_triangles],
            "tri_loops": [tuple(t.loops) for t in me.loop_triangles],
            "loop_vert": [lp.vertex_index for lp in me.loops],
            "uv_names": [uv.name for uv in me.uv_layers],
            "uvs": {uv.name: [tuple(d.uv) for d in uv.data] for uv in me.uv_layers},
            "loop_normals": [tuple(lp.normal) for lp in me.loops],
            "polys": len(me.polygons),
        }
    empties = sorted(ob.name for ob in bpy.data.objects if ob.type == "EMPTY")
    return nodes, empties


def kdt(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(p, i)
    t.balance()
    return t


def two_sided(a, b):
    ka, kb = kdt(a), kdt(b)
    return max(max(kb.find(p)[2] for p in a), max(ka.find(p)[2] for p in b))


# ------------------------------------------------------------------ hull
def planes_of(node):
    vs = [Vector(v) for v in node["verts"]]
    cen = sum(vs, Vector()) / len(vs)
    planes = []
    for (i, j, k) in node["tris"]:
        n = (vs[j] - vs[i]).cross(vs[k] - vs[i])
        if n.length < 1e-12:
            continue
        n.normalize()
        if n.dot(cen - vs[i]) > 0:
            n = -n
        planes.append((n, vs[i]))
    return planes


def max_outside(planes, pts):
    return max(max(n.dot(Vector(p) - a) for n, a in planes) for p in pts)


def convexity_violation(node):
    """Max distance of any hull vertex outside the hull's own face planes (0 for a convex solid)."""
    return max_outside(planes_of(node), node["verts"])


def volume(node):
    vs = [Vector(v) for v in node["verts"]]
    cen = sum(vs, Vector()) / len(vs)
    return sum(abs((vs[i] - cen).dot((vs[j] - cen).cross(vs[k] - cen))) / 6.0 for i, j, k in node["tris"])


def uniq(vs, nd=5):
    return sorted({tuple(round(c, nd) + 0.0 for c in v) for v in vs})


# ------------------------------------------------------------------ UV1 overlap (exact, convex clipping)
def area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def ccw(t):
    return t if area2(*t) >= 0 else (t[0], t[2], t[1])


def clip_convex(subject, clipper):
    out = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        src, out = out, []
        if not src:
            return []
        for k in range(len(src)):
            p, q = src[k - 1], src[k]
            pin = area2(a, b, p) >= 0
            qin = area2(a, b, q) >= 0
            if qin:
                if not pin:
                    out.append(_isect(p, q, a, b))
                out.append(q)
            elif pin:
                out.append(_isect(p, q, a, b))
    return out


def _isect(p, q, a, b):
    d1 = area2(a, b, p)
    d2 = area2(a, b, q)
    t = d1 / (d1 - d2) if d1 != d2 else 0.0
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


def poly_area(poly):
    return 0.5 * abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                         for i in range(len(poly))))


def uv_overlap(tris, res):
    """Exact overlap between every pair of UV triangles whose boxes intersect (uniform grid broad phase)."""
    cell = 1.0 / 64.0
    grid = {}
    boxes = []
    for ti, t in enumerate(tris):
        bx = (min(p[0] for p in t), max(p[0] for p in t), min(p[1] for p in t), max(p[1] for p in t))
        boxes.append(bx)
        for gx in range(int(math.floor(bx[0] / cell)), int(math.floor(bx[1] / cell)) + 1):
            for gy in range(int(math.floor(bx[2] / cell)), int(math.floor(bx[3] / cell)) + 1):
                grid.setdefault((gx, gy), []).append(ti)
    seen = set()
    n_pairs, n_over, total, worst = 0, 0, 0.0, 0.0
    for members in grid.values():
        for ai in range(len(members)):
            for bi in range(ai + 1, len(members)):
                i, j = members[ai], members[bi]
                key = (min(i, j), max(i, j))
                if key in seen:
                    continue
                seen.add(key)
                a, b = boxes[i], boxes[j]
                if a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2]:
                    continue
                n_pairs += 1
                poly = clip_convex(ccw(tris[i]), ccw(tris[j]))
                if len(poly) >= 3:
                    ar = poly_area(poly)
                    if ar > 1e-12:
                        n_over += 1
                        total += ar
                        worst = max(worst, ar)
    # charts by shared UV corners; texel centres covered by two charts at the lightmap resolution
    parent = list(range(len(tris)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    corner = {}
    for ti, t in enumerate(tris):
        for c in t:
            k = (round(c[0], 7), round(c[1], 7))
            if k in corner:
                ra, rb = find(ti), find(corner[k])
                if ra != rb:
                    parent[ra] = rb
            else:
                corner[k] = ti
    owner, shared = {}, set()
    for ti, t in enumerate(tris):
        t = ccw(t)
        bx = boxes[ti]
        ch = find(ti)
        for x in range(max(int(math.floor(bx[0] * res)), 0), min(int(math.ceil(bx[1] * res)), res)):
            for y in range(max(int(math.floor(bx[2] * res)), 0), min(int(math.ceil(bx[3] * res)), res)):
                p = ((x + 0.5) / res, (y + 0.5) / res)
                if area2(t[0], t[1], p) >= 0 and area2(t[1], t[2], p) >= 0 and area2(t[2], t[0], p) >= 0:
                    prev = owner.setdefault((x, y), ch)
                    if prev != ch:
                        shared.add((x, y))
    us = [p[0] for t in tris for p in t]
    vs = [p[1] for t in tris for p in t]
    signs = [area2(*t) for t in tris]
    return {"u_range": [min(us), max(us)], "v_range": [min(vs), max(vs)],
            "inside_0_1": min(us) >= 0.0 and min(vs) >= 0.0 and max(us) <= 1.0 and max(vs) <= 1.0,
            "strictly_inside_0_1": min(us) > 0.0 and min(vs) > 0.0 and max(us) < 1.0 and max(vs) < 1.0,
            "candidate_pairs": n_pairs, "overlapping_pairs": n_over, "overlap_area_total": total,
            "overlap_area_max": worst,
            "zero_area_triangles": sum(1 for s in signs if abs(s) < 1e-14),
            "negative_winding_triangles": sum(1 for s in signs if s < -1e-14),
            "charts": len({find(i) for i in range(len(tris))}), "lightmap_res": res,
            "texels_covered_by_two_charts": len(shared)}


def uv_tris(node, layer_index):
    uv = node["uvs"][node["uv_names"][layer_index]]
    return [tuple(uv[li] for li in tl) for tl in node["tri_loops"]]


def render_vertex_estimate(node, nd=4):
    """Unique (position, split normal, UV0) triples: what an importer that keeps the FBX normals must emit."""
    uv = node["uvs"][node["uv_names"][0]] if node["uv_names"] else None
    keys = set()
    for li, vi in enumerate(node["loop_vert"]):
        p = tuple(round(c, 5) for c in node["verts"][vi])
        n = tuple(round(c, nd) for c in node["loop_normals"][li])
        u = tuple(round(c, 6) for c in uv[li]) if uv else ()
        keys.add((p, n, u))
    return len(keys)


# ------------------------------------------------------------------ main
def main():
    res = {"shipped_fbx": str(SHIPPED), "shipped_sha256": sha256(SHIPPED),
           "unreal_fbx": str(UE_FBX), "unreal_fbx_sha256": sha256(UE_FBX)}
    truth = blend_truth()
    res["blend_truth"] = {k: v for k, v in truth.items() if k != "ucx"}
    res["blend_truth"]["ucx"] = {"name": truth.get("ucx", {}).get("name"), "verts": len(truth.get("ucx", {}).get("verts_cm", [])),
                                 "faces": truth.get("ucx", {}).get("faces")}
    blend_tris = [truth["lods"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]

    ship, ship_empties = load_fbx(SHIPPED)
    back, back_empties = load_fbx(UE_FBX)
    res["shipped_nodes"] = {k: {"tris": len(v["tris"]), "verts": len(v["verts"]), "uv": v["uv_names"]} for k, v in ship.items()}
    res["unreal_nodes"] = {k: {"tris": len(v["tris"]), "verts": len(v["verts"]), "uv": v["uv_names"]} for k, v in back.items()}
    res["shipped_empties"], res["unreal_empties"] = ship_empties, back_empties

    ship_lods = [ship[f"{MESH}_LOD{i}"] for i in range(3)]
    back_lod_names = sorted((k for k in back if not k.upper().startswith("UCX_")), key=lambda k: -len(back[k]["tris"]))
    back_lods = [back[k] for k in back_lod_names]
    ue_tris = S3["mesh"]["lod_triangles"]

    # R2 per LOD
    r2 = {"unreal_readback_tris": ue_tris, "blend_tris": blend_tris,
          "shipped_fbx_tris": [len(n["tris"]) for n in ship_lods],
          "unreal_export_tris": [len(n["tris"]) for n in back_lods],
          "unreal_export_nodes": back_lod_names, "per_lod": []}
    for i in range(3):
        s, b = ship_lods[i], back_lods[i]
        r2["per_lod"].append({
            "lod": i, "two_sided_position_cm": two_sided(s["verts"], b["verts"]),
            "shipped_uv_layers": s["uv_names"], "unreal_uv_layers": b["uv_names"],
            "render_vertex_estimate_from_shipped": render_vertex_estimate(s),
            "unreal_render_vertices": S3["mesh"]["lod_vertices"][i]})
    r2["ok"] = (len(ue_tris) == 3 and ue_tris == blend_tris == r2["shipped_fbx_tris"] == r2["unreal_export_tris"]
                and all(p["two_sided_position_cm"] <= 1e-5 for p in r2["per_lod"]))
    res["R2_lods"] = r2

    # R1 hull
    sh_names = [k for k in ship if k.upper().startswith("UCX_")]
    bh_names = [k for k in back if k.upper().startswith("UCX_")]
    r1 = {"shipped_hull_nodes": sh_names, "unreal_hull_nodes": bh_names}
    if len(sh_names) == 1 and len(bh_names) == 1:
        sh, bh = ship[sh_names[0]], back[bh_names[0]]
        planes = planes_of(bh)
        us_, ub_ = uniq(sh["verts"]), uniq(bh["verts"])
        ucx_blend = uniq(truth["ucx"]["verts_cm"]) if "ucx" in truth else []
        r1.update({
            "shipped": {"unique_verts": len(us_), "tris": len(sh["tris"]), "volume_cm3": volume(sh)},
            "unreal": {"unique_verts": len(ub_), "tris": len(bh["tris"]), "volume_cm3": volume(bh)},
            "blend_ucx_unique_verts": len(ucx_blend),
            "vertex_sets_equal_1e-5cm": us_ == ub_,
            "blend_ucx_equals_shipped_1e-5cm": ucx_blend == us_,
            "two_sided_vertex_distance_cm": two_sided(sh["verts"], bh["verts"]),
            "unreal_hull_convexity_violation_cm": convexity_violation(bh),
            "lod_max_outside_unreal_hull_cm": {
                "shipped": [max_outside(planes, n["verts"]) for n in ship_lods],
                "unreal": [max_outside(planes, n["verts"]) for n in back_lods]},
            "hull_extent_cm": [max(v[k] for v in bh["verts"]) - min(v[k] for v in bh["verts"]) for k in range(3)],
        })
        vol_rel = abs(r1["shipped"]["volume_cm3"] - r1["unreal"]["volume_cm3"]) / r1["shipped"]["volume_cm3"]
        r1["volume_rel_diff"] = vol_rel
        r1["lod0_outside_cm_rounded_1dp"] = round(max(r1["lod_max_outside_unreal_hull_cm"]["unreal"][0],
                                                      r1["lod_max_outside_unreal_hull_cm"]["shipped"][0], 0.0), 1)
        r1["ok"] = (r1["vertex_sets_equal_1e-5cm"] and r1["shipped"]["tris"] == r1["unreal"]["tris"]
                    and r1["two_sided_vertex_distance_cm"] <= 1e-5 and vol_rel < 1e-6
                    and max(r1["lod_max_outside_unreal_hull_cm"]["shipped"][0],
                            r1["lod_max_outside_unreal_hull_cm"]["unreal"][0]) <= 1e-6)
    else:
        r1["ok"] = False
    res["R1_hull"] = r1

    # R3 UV1
    lm_res = int(S3["mesh"]["light_map_resolution"])
    r3 = {"light_map_coordinate_index": S3["mesh"]["light_map_coordinate_index"], "per_lod": []}
    ok3 = True
    for i, b in enumerate(back_lods):
        if len(b["uv_names"]) < 2:
            r3["per_lod"].append({"lod": i, "error": "no UV1 in Unreal export", "uv_names": b["uv_names"]})
            ok3 = False
            continue
        o = uv_overlap(uv_tris(b, 1), lm_res)
        o["lod"] = i
        o["uv1_layer_name"] = b["uv_names"][1]
        r3["per_lod"].append(o)
        ok3 = ok3 and o["inside_0_1"] and o["overlapping_pairs"] == 0 and o["zero_area_triangles"] == 0
        if i == 0:
            tris = uv_tris(b, 1)
            d = 0.3 / lm_res
            ctl = uv_overlap(tris + [tuple((p[0] + d, p[1] + d) for p in tris[len(tris) // 2])], lm_res)
            r3["negative_control_lod0"] = {"overlapping_pairs": ctl["overlapping_pairs"],
                                           "overlap_area_total": ctl["overlap_area_total"],
                                           "detects": ctl["overlapping_pairs"] >= 1}
            ok3 = ok3 and r3["negative_control_lod0"]["detects"]
    # UV0 unchanged by the round trip (handedness): shipped vs Unreal LOD0 UV0 keyed by position
    r3["ok"] = ok3 and r3["light_map_coordinate_index"] == 1
    res["R3_uv1"] = r3

    # R4 sockets
    lod0 = ship_lods[0]
    bm = bmesh.new()
    for v in lod0["verts"]:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    for t in lod0["tris"]:
        try:
            bm.faces.new([bm.verts[k] for k in t])
        except ValueError:
            pass
    bm.normal_update()
    bvh = BVHTree.FromBMesh(bm)
    r4 = {}
    ok4 = True
    for name in ("Grip", "Trail"):
        ue = S3["mesh"]["component_sockets"][name]
        loc_ue = ue["location_cm"]
        loc_bl = [loc_ue[0], -loc_ue[1], loc_ue[2]]
        yaw_ue = ue["rotator"]["yaw"]
        x_axis_bl = [math.cos(math.radians(-yaw_ue)), math.sin(math.radians(-yaw_ue)), 0.0]
        bt = truth["sockets"].get(name, {})
        rec = {"unreal_location_cm": loc_ue, "unreal_yaw": yaw_ue, "as_blender_axes_cm": loc_bl,
               "blend_empty_cm": bt.get("location_cm_blender"), "blend_empty_x_axis": bt.get("x_axis_blender"),
               "blend_empty_scale": bt.get("scale"), "scale_unreal": ue["scale"],
               "radius_cm": math.hypot(loc_bl[0], loc_bl[1]),
               "polar_deg_blender": math.degrees(math.atan2(loc_bl[1], loc_bl[0]))}
        if bt:
            rec["delta_to_blend_empty_cm"] = max(abs(a - b) for a, b in zip(loc_bl, bt["location_cm_blender"]))
            # pipeline.helpers model: the Empty carries a baked local Ry(180) (ue_correction) and Unreal mirrors Y,
            # so rot_ue = M R M Ry(180) and the Unreal +X axis is -M (R x) = -(x_b, -y_b, z_b) of the Empty's X axis.
            bx = bt["x_axis_blender"]
            ue_x_expected = [-bx[0], bx[1], -bx[2]]
            ue_x_actual = [math.cos(math.radians(yaw_ue)), math.sin(math.radians(yaw_ue)), 0.0]
            rec["unreal_x_axis"] = [round(c, 6) for c in ue_x_actual]
            rec["unreal_x_axis_expected_from_blend_empty"] = [round(c, 6) for c in ue_x_expected]
            rec["x_axis_delta_to_blend"] = max(abs(a - b) for a, b in zip(ue_x_actual, ue_x_expected))
        hit = bvh.find_nearest(Vector(loc_bl))
        if hit[0] is not None:
            rec["distance_to_lod0_surface_cm"] = hit[3]
            rec["nearest_face_normal"] = [round(c, 6) for c in hit[1]]
        rec["inside_lod0_outline"] = None
        if name == "Grip":
            n = Vector(rec.get("nearest_face_normal", (0, 0, 0)))
            rec["x_axis_dot_outward_normal"] = n.dot(Vector(x_axis_bl)) if n.length > 0 else None
            ok = (abs(rec["radius_cm"] - 1.8) < 1e-3 and abs(rec["polar_deg_blender"] - 30.0) < 1e-2
                  and rec.get("distance_to_lod0_surface_cm", 1.0) < 0.01
                  and (rec["x_axis_dot_outward_normal"] or 0.0) > 0.99
                  and rec.get("delta_to_blend_empty_cm", 1.0) < 1e-4 and rec.get("x_axis_delta_to_blend", 1.0) < 1e-4)
        else:
            ok = rec["radius_cm"] < 1e-6 and abs(loc_bl[2]) < 1e-6 and rec.get("delta_to_blend_empty_cm", 1.0) < 1e-6
        ok = ok and ue["scale"] == [1.0, 1.0, 1.0]
        rec["ok"] = ok
        ok4 = ok4 and ok
        r4[name] = rec
    r4["ok"] = ok4
    res["R4_sockets"] = r4
    bm.free()

    # R5 tips
    pts = lod0["verts"]
    rmax = max(math.hypot(p[0], p[1]) for p in pts)
    tips = sorted({round(math.degrees(math.atan2(p[1], p[0])) % 360.0, 3)
                   for p in pts if math.hypot(p[0], p[1]) > rmax - 1e-4})
    res["R5_tips"] = {"max_radius_cm": rmax, "tip_angles_deg": tips,
                      "ok": abs(rmax - 4.9) < 1e-4 and len(tips) == 6
                      and all(min(abs(t - k * 60.0), 360 - abs(t - k * 60.0)) < 1e-2 for t, k in zip(tips, range(6)))}
    res["passed"] = all(res[k]["ok"] for k in ("R1_hull", "R2_lods", "R3_uv1", "R4_sockets", "R5_tips"))
    (HERE / "b_compare.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print("U9_BCOMPARE_DONE passed=%s" % res["passed"])


main()
