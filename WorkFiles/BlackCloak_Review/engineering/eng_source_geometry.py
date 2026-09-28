"""Source-cage geometry audit on the COPY (never saved): cage-vs-cage intersections, normal orientation vs body axis,
UV0 texel density per panel, CLOTH_Pin distribution, solidify direction, gap between stacked layers."""
import bpy, bmesh, json, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

out = sys.argv[sys.argv.index("--") + 1]
objs = [o for o in bpy.data.collections["BLACK_CLOAK"].all_objects if o.type == "MESH"]
res = {"panels": {}}
# body axis: vertical line through the cowl's centre (neck)
cowl = bpy.data.objects["Cloak_WrappedCowl"]
cc = np.array([cowl.matrix_world @ v.co for v in cowl.data.vertices])
axis_xy = cc[:, :2].mean(axis=0)
res["body_axis_xy_m"] = axis_xy.round(4).tolist()
trees = {}
cage = {}
for o in objs:
    me = o.data
    me.calc_loop_triangles()
    mw = o.matrix_world
    co = np.array([mw @ v.co for v in me.vertices])
    polys = [p.vertices[:] for p in me.polygons]
    trees[o.name] = BVHTree.FromPolygons(co.tolist(), polys, epsilon=0.0)
    cage[o.name] = (co, polys)
    d = {}
    # normal orientation relative to body axis (horizontal radial component)
    cen = np.array([mw @ p.center for p in me.polygons])
    nrm = np.array([(mw.to_3x3() @ p.normal).normalized() for p in me.polygons])
    radial = cen[:, :2] - axis_xy
    rn = np.linalg.norm(radial, axis=1, keepdims=True)
    radial = radial / np.where(rn == 0, 1, rn)
    dots = (nrm[:, :2] * radial).sum(axis=1)
    horiz = np.linalg.norm(nrm[:, :2], axis=1) > 0.3
    d["faces"] = len(me.polygons)
    d["normals_outward_pct"] = round(100.0 * float((dots[horiz] > 0).mean()), 1) if horiz.any() else None
    bm = bmesh.new(); bm.from_mesh(me)
    d["inconsistent_winding_edges"] = sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous)
    bm.free()
    # UV0 texel density (source UV units are metres per README, so 1/0.128 m repeat is applied at export)
    if me.uv_layers:
        uv = np.array([l.uv[:] for l in me.uv_layers[0].data])
        ll = np.array([t.loops[:] for t in me.loop_triangles]); lv = np.array([t.vertices[:] for t in me.loop_triangles])
        u = uv[ll]; t3 = co[lv]
        uva = 0.5 * np.abs((u[:, 1, 0] - u[:, 0, 0]) * (u[:, 2, 1] - u[:, 0, 1]) - (u[:, 2, 0] - u[:, 0, 0]) * (u[:, 1, 1] - u[:, 0, 1]))
        wa = 0.5 * np.linalg.norm(np.cross(t3[:, 1] - t3[:, 0], t3[:, 2] - t3[:, 0]), axis=1)
        d["uv0_area_over_world_area"] = round(float(uva.sum() / wa.sum()), 4)
        # local stretch spread: per-triangle ratio percentiles
        r = np.sqrt(uva / np.maximum(wa, 1e-12))
        d["uv0_linear_scale_p5_p50_p95"] = [round(float(x), 3) for x in np.percentile(r, [5, 50, 95])]
        d["uv0_range"] = [uv.min(0).round(3).tolist(), uv.max(0).round(3).tolist()]
    g = o.vertex_groups.get("CLOTH_Pin")
    if g:
        w = np.zeros(len(me.vertices))
        for v in me.vertices:
            for ge in v.groups:
                if ge.group == g.index:
                    w[v.index] = ge.weight
        d["pin"] = {"eq1": int((w >= 0.999).sum()), "zero": int((w <= 0.001).sum()), "partial": int(((w > 0.001) & (w < 0.999)).sum()),
                    "mean": round(float(w.mean()), 3),
                    "pinned_z_range_m": [round(float(co[w >= 0.999, 2].min()), 3), round(float(co[w >= 0.999, 2].max()), 3)] if (w >= 0.999).any() else None}
    d["max_distance_prop_m"] = o.get("cloth_max_distance_m")
    res["panels"][o.name] = d
# cage-vs-cage intersections (single-sided authoring surfaces, no subdivision or thickness)
names = list(trees)
cross = {}
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        p = trees[names[i]].overlap(trees[names[j]])
        if p:
            cross[f"{names[i]} x {names[j]}"] = len(p)
res["cage_cross_intersecting_face_pairs"] = cross
res["cage_cross_total"] = sum(cross.values())
selfi = {}
for n in names:
    co, polys = cage[n]
    pairs = trees[n].overlap(trees[n])
    c = 0
    for a, b in pairs:
        if a < b and not (set(polys[a]) & set(polys[b])):
            c += 1
    selfi[n] = c
res["cage_self_intersecting_face_pairs"] = selfi
res["cage_self_total"] = sum(selfi.values())
# layer gap: for each fabric panel vertex, distance to the nearest OTHER fabric panel surface
fabric = [n for n in names if n.startswith("Cloak_")]
gaps = []
for n in fabric:
    co, _ = cage[n]
    idx = np.arange(0, len(co), 7)
    for k in idx:
        best = 1e9
        for m in fabric:
            if m == n:
                continue
            hit = trees[m].find_nearest(Vector(co[k]), 0.05)
            if hit[0] is not None:
                best = min(best, hit[3])
        if best < 1e9:
            gaps.append(best)
gaps = np.array(gaps)
res["stacked_layer_gap_m"] = {"samples_within_5cm": int(len(gaps)),
                              "lt_1_6mm_solidify_thickness": int((gaps < 0.0016).sum()),
                              "lt_3_2mm": int((gaps < 0.0032).sum()),
                              "p5_p50": [round(float(x), 4) for x in np.percentile(gaps, [5, 50])] if len(gaps) else None}
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print("SOURCE_GEOM_DONE", res["cage_cross_total"], res["cage_self_total"])
