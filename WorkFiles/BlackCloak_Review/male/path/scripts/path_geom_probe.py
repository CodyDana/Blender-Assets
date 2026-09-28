"""Path-to-exact critic: how is the fitted cloak built? Runs headless on a COPY of BlackCloak_MH_fit.blend (or the source copy).
Per piece: topology (regular grid?), custom construction props, front-projection fold-over (height-field test), radial undercut
(for wrapped pieces), developability (total |angle defect| and min-stretch unwrap distortion), inter-piece intersections.
Writes JSON to argv out path. Never saves the blend."""
import bpy, bmesh, sys, json, math
import numpy as np
from mathutils.bvhtree import BVHTree

out = sys.argv[sys.argv.index("--") + 1]
res = {"file": bpy.data.filepath, "pieces": {}}
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not any(c.name in ("FitReference_MH", "STUDIO_ExcludeFromExport") for c in o.users_collection) and o.name not in ("StudioFloor",)]
res["scene_props"] = {k: str(v)[:300] for k, v in bpy.context.scene.items()} if hasattr(bpy.context.scene, "items") else {}
trees = {}
for ob in meshes:
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    nv, nf = len(bm.verts), len(bm.faces)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    val = np.array([len(v.link_edges) for v in bm.verts])
    boundary = [v for v in bm.verts if v.is_boundary]
    interior4 = float(np.mean(val[[not v.is_boundary for v in bm.verts]] == 4)) if nv > len(boundary) else None
    area = np.array([f.calc_area() for f in bm.faces]); A = float(area.sum())
    nrm = np.array([f.normal[:] for f in bm.faces]); cen = np.array([f.calc_center_median()[:] for f in bm.faces])
    # front height-field test: fraction of area whose normal.y opposes the area-weighted majority
    ny = nrm[:, 1]; maj = np.sign((ny * area).sum()) or 1.0
    fold_front = float(area[np.sign(ny) == -maj].sum() / A)
    # radial undercut about the body axis (x=0,y=0): normals pointing against the majority radial direction
    rad = cen[:, :2].copy(); rn = np.linalg.norm(rad, axis=1, keepdims=True); rad = rad / np.maximum(rn, 1e-9)
    nr = (nrm[:, :2] * rad).sum(1); majr = np.sign((nr * area).sum()) or 1.0
    undercut = float(area[np.sign(nr) == -majr].sum() / A)
    # developability: sum |angle defect| over interior vertices (radians); a flat-cut, draped cloth stays near-isometric
    defect = []
    for v in bm.verts:
        if v.is_boundary or v.is_wire: continue
        s = sum(l.calc_angle() for l in v.link_loops)
        defect.append(2 * math.pi - s)
    defect = np.array(defect) if defect else np.zeros(1)
    # edge-length regularity (grid spacing)
    el = np.array([e.calc_length() for e in bm.edges])
    zs = np.array([v.co.z for v in bm.verts])
    props = {k: (list(ob[k]) if hasattr(ob[k], "__len__") and not isinstance(ob[k], str) else ob[k]) for k in ob.keys()}
    props = {k: (v if isinstance(v, (int, float, str, list)) else str(v)) for k, v in props.items()}
    res["pieces"][ob.name] = {
        "verts": nv, "faces": nf, "quad_frac": round(quads / max(nf, 1), 4), "interior_valence4_frac": interior4,
        "boundary_verts": len(boundary), "area_m2": round(A, 4), "z_range_m": [round(float(zs.min()), 3), round(float(zs.max()), 3)],
        "front_foldover_area_frac": round(fold_front, 4), "radial_undercut_area_frac": round(undercut, 4),
        "sum_abs_angle_defect_rad": round(float(np.abs(defect).sum()), 3), "sum_angle_defect_rad": round(float(defect.sum()), 3),
        "abs_defect_per_m2": round(float(np.abs(defect).sum() / max(A, 1e-9)), 2),
        "edge_len_mm_p5_p50_p95": [round(float(np.percentile(el, q)) * 1000, 2) for q in (5, 50, 95)],
        "modifiers": [m.type for m in ob.modifiers], "materials": [m.name if m else None for m in me.materials],
        "props": props,
    }
    trees[ob.name] = BVHTree.FromBMesh(bm)
    bm.free()

# min-stretch unwrap distortion per wool piece: can this surface be laid flat as a sewing pattern?
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    if len(ob.data.polygons) < 50: continue
    try:
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        ob.data.uv_layers.new(name="probe_flat"); ob.data.uv_layers.active = ob.data.uv_layers["probe_flat"]
        bpy.ops.uv.unwrap(method="CONFORMAL", margin=0.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        me = ob.data; uv = me.uv_layers["probe_flat"].data
        ratios = []; a3 = []
        for p in me.polygons:
            if len(p.loop_indices) < 3: continue
            li = list(p.loop_indices)
            u = np.array([uv[i].uv[:] for i in li]); w = np.array([(ob.matrix_world @ me.vertices[me.loops[i].vertex_index].co)[:] for i in li])
            au = 0.5 * abs(sum(u[k][0] * u[(k + 1) % len(u)][1] - u[(k + 1) % len(u)][0] * u[k][1] for k in range(len(u))))
            ratios.append(au); a3.append(p.area)
        ratios = np.array(ratios); a3 = np.array(a3)
        s = ratios.sum() / a3.sum(); r = (ratios / np.maximum(a3, 1e-12)) / s
        good = a3 > 0
        lr = np.log(np.maximum(r[good], 1e-6)); w = a3[good] / a3[good].sum()
        res["pieces"][ob.name]["conformal_unwrap_area_distortion"] = {
            "area_weighted_std_log": round(float(np.sqrt((w * lr ** 2).sum() - (w * lr).sum() ** 2)), 4),
            "p5_p95_ratio": [round(float(np.percentile(r[good], 5)), 3), round(float(np.percentile(r[good], 95)), 3)]}
        ob.select_set(False)
    except Exception as ex:
        res["pieces"][ob.name]["conformal_unwrap_area_distortion"] = "err %s" % ex
        try: bpy.ops.object.mode_set(mode="OBJECT")
        except Exception: pass

# inter-piece intersections (layers passing through each other)
names = sorted(trees)
inter = {}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        n = len(trees[a].overlap(trees[b]))
        if n: inter["%s|%s" % (a, b)] = n
res["interpiece_overlap_face_pairs"] = inter
res["interpiece_total"] = int(sum(inter.values()))
self_int = {}
for a in names:
    try: self_int[a] = len([p for p in trees[a].overlap(trees[a]) if p[0] != p[1]])
    except Exception as ex: self_int[a] = str(ex)
res["self_overlap_pairs_raw_incl_adjacent"] = self_int
json.dump(res, open(out, "w"), indent=1)
print("WROTE", out, len(meshes), "pieces")
