"""Read-only audit of ONE exported cloak file, imported into a fresh empty Blender scene.
Usage: blender -b --factory-startup --python eng_audit_export.py -- <file> <out.json> [--qa]
Never writes anything except <out.json> (in the review folder).
"""
import bpy, bmesh, json, sys, hashlib, math, os
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
path, out = argv[0], argv[1]
RUN_QA = "--qa" in argv
ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
REVIEW = ROOT + "/WorkFiles/BlackCloak_Review/engineering"
res = {"file": path, "bytes": os.path.getsize(path),
       "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------------------------------------------------------- FBX header / node structure
if path.lower().endswith(".fbx"):
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(path)
    res["fbx_version"] = version
    gs = {}
    models = {}
    deformers = {}
    def walk(e, depth=0):
        if e.id == b"GlobalSettings":
            for c in e.elems:
                if c.id == b"Properties70":
                    for p in c.elems:
                        k = p.props[0].decode("utf-8", "replace")
                        if k in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign",
                                 "UnitScaleFactor", "OriginalUnitScaleFactor", "OriginalUpAxis", "OriginalUpAxisSign"):
                            gs[k] = p.props[4]
        if e.id == b"Model" and len(e.props) >= 3:
            t = e.props[2].decode("utf-8", "replace") if isinstance(e.props[2], bytes) else str(e.props[2])
            models[t] = models.get(t, 0) + 1
        if e.id == b"Deformer" and len(e.props) >= 3:
            t = e.props[2].decode("utf-8", "replace") if isinstance(e.props[2], bytes) else str(e.props[2])
            deformers[t] = deformers.get(t, 0) + 1
        if e.id == b"Creator":
            res["fbx_creator"] = e.props[0].decode("utf-8", "replace") if e.props and isinstance(e.props[0], bytes) else str(e.props)
        for c in e.elems:
            walk(c, depth + 1)
    walk(root)
    res["fbx_global_settings"] = gs
    res["fbx_model_node_types"] = models
    res["fbx_deformer_types"] = deformers
    bpy.ops.import_scene.fbx(filepath=path, use_anim=False)
else:
    bpy.ops.import_scene.gltf(filepath=path)

meshes = [o for o in sc.objects if o.type == "MESH"]
arms = [o for o in sc.objects if o.type == "ARMATURE"]
res["objects"] = {o.name: {"type": o.type, "parent": o.parent.name if o.parent else None} for o in sc.objects}
res["object_type_counts"] = {}
for o in sc.objects:
    res["object_type_counts"][o.type] = res["object_type_counts"].get(o.type, 0) + 1
res["lod_group_empties"] = [o.name for o in sc.objects if o.type == "EMPTY" and o.get("fbx_type") == "LodGroup"]


def raster(tris, lo, hi, res_px):
    """Coverage counts of UV triangles (n,3,2) on a res_px grid spanning lo..hi."""
    grid = np.zeros((res_px, res_px), dtype=np.uint16)
    span = np.maximum(hi - lo, 1e-9)
    t = (tris - lo) / span * res_px
    mins = np.floor(t.min(axis=1)).astype(int).clip(0, res_px - 1)
    maxs = np.ceil(t.max(axis=1)).astype(int).clip(0, res_px - 1)
    for i in range(len(t)):
        x0, y0 = mins[i]; x1, y1 = maxs[i]
        xs = np.arange(x0, x1 + 1) + 0.5; ys = np.arange(y0, y1 + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        a, b, c = t[i]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        grid[y0:y1 + 1, x0:x1 + 1] += inside.astype(np.uint16)
    return grid


def raster_ids(tris, ids, res_px):
    grid = np.zeros((res_px, res_px), dtype=np.int32)
    t = tris * res_px
    mins = np.floor(t.min(axis=1)).astype(int).clip(0, res_px - 1)
    maxs = np.ceil(t.max(axis=1)).astype(int).clip(0, res_px - 1)
    for i in range(len(t)):
        x0, y0 = mins[i]; x1, y1 = maxs[i]
        xs = np.arange(x0, x1 + 1) + 0.5; ys = np.arange(y0, y1 + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        a, b, c = t[i]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        inside = (l1 >= 0) & (l2 >= 0) & (1 - l1 - l2 >= 0)
        sub = grid[y0:y1 + 1, x0:x1 + 1]
        sub[inside] = ids[i] + 1
    return grid


def min_gap_px(grid, rmax=10):
    """Smallest Chebyshev distance (px) between pixels of two different islands, up to rmax."""
    H, W = grid.shape
    for r in range(1, rmax + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                a = grid[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
                b = grid[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
                if np.any((a > 0) & (b > 0) & (a != b)):
                    return r
    return None


def uv_islands(me, layer_index):
    """Face -> island id via shared-edge + matching-UV union-find."""
    uv = me.uv_layers[layer_index].data
    parent = list(range(len(me.polygons)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edge_map = {}
    for p in me.polygons:
        loops = list(p.loop_indices)
        n = len(loops)
        for k in range(n):
            la, lb = loops[k], loops[(k + 1) % n]
            va, vb = me.loops[la].vertex_index, me.loops[lb].vertex_index
            key = (min(va, vb), max(va, vb))
            uva = tuple(round(c, 6) for c in uv[la].uv); uvb = tuple(round(c, 6) for c in uv[lb].uv)
            uvs = {va: uva, vb: uvb}
            if key in edge_map:
                q, quvs = edge_map[key]
                if quvs[va] == uvs[va] and quvs[vb] == uvs[vb]:
                    ra, rb = find(p.index), find(q)
                    if ra != rb:
                        parent[ra] = rb
            else:
                edge_map[key] = (p.index, uvs)
    return [find(i) for i in range(len(me.polygons))]


dg = bpy.context.evaluated_depsgraph_get()
all_uv0 = []; all_uv1 = []; all_uv1_ids = []; island_offset = 0
tot = {"tris": 0, "verts": 0, "area_m2": 0.0}
mesh_out = {}
all_world_tris = []
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    mw = o.matrix_world
    co = np.array([mw @ v.co for v in me.vertices]) if len(me.vertices) else np.zeros((0, 3))
    lt = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64)
    ll = np.array([t.loops[:] for t in me.loop_triangles], dtype=np.int64)
    tri_co = co[lt]
    area = 0.5 * np.linalg.norm(np.cross(tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0]), axis=1)
    d = {"verts": len(me.vertices), "tris": len(me.loop_triangles), "polys": len(me.polygons),
         "ngons": sum(1 for p in me.polygons if len(p.vertices) > 4),
         "materials": [m.name if m else None for m in me.materials],
         "uv_layers": [u.name for u in me.uv_layers],
         "color_attributes": [c.name for c in me.color_attributes],
         "bounds_cm": [(co.min(axis=0) * 100).round(2).tolist(), (co.max(axis=0) * 100).round(2).tolist()] if len(co) else None,
         "area_m2": float(area.sum()),
         "zero_area_tris": int((area < 1e-12).sum()),
         "smooth_faces": sum(1 for p in me.polygons if p.use_smooth),
         "has_custom_normals": me.has_custom_normals,
         "sharp_edges": int(np.count_nonzero([e.use_edge_sharp for e in me.edges])) if len(me.edges) else 0,
         "matrix_world_identity": all(abs(mw[i][j] - (1 if i == j else 0)) < 1e-5 for i in range(4) for j in range(4)),
         "scale": list(o.scale), "rotation": list(o.rotation_euler)}
    bm = bmesh.new(); bm.from_mesh(me)
    d["boundary_edges"] = sum(1 for e in bm.edges if e.is_boundary)
    d["nonmanifold_3plus"] = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    d["loose_verts"] = sum(1 for v in bm.verts if not v.link_edges)
    d["inconsistent_winding_edges"] = sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous)
    bm.free()
    tot["tris"] += d["tris"]; tot["verts"] += d["verts"]; tot["area_m2"] += d["area_m2"]
    all_world_tris.append((o.name, tri_co))
    # UVs
    for li, layer in enumerate(me.uv_layers):
        uv = np.array([l.uv[:] for l in layer.data]) if len(layer.data) else np.zeros((0, 2))
        uvt = uv[ll]
        uva = 0.5 * np.abs((uvt[:, 1, 0] - uvt[:, 0, 0]) * (uvt[:, 2, 1] - uvt[:, 0, 1]) -
                           (uvt[:, 2, 0] - uvt[:, 0, 0]) * (uvt[:, 1, 1] - uvt[:, 0, 1]))
        info = {"name": layer.name, "u_range": [float(uv[:, 0].min()), float(uv[:, 0].max())],
                "v_range": [float(uv[:, 1].min()), float(uv[:, 1].max())], "uv_area": float(uva.sum())}
        if d["area_m2"] > 0:
            # px/cm at 2048
            info["texel_px_per_cm_at_2048"] = math.sqrt(uva.sum() / (d["area_m2"] * 1e4)) * 2048
        lo = uv.min(axis=0); hi = uv.max(axis=0)
        g = raster(uvt, lo, hi, 512)
        cov = int((g > 0).sum())
        info["overlap_pct_of_covered_512"] = round(100.0 * int((g > 1).sum()) / max(cov, 1), 2)
        info["inside_0_1"] = bool(uv.min() >= -1e-5 and uv.max() <= 1 + 1e-5)
        d.setdefault("uv", []).append(info)
        if li == 0:
            all_uv0.append(uvt)
        if li == 1:
            all_uv1.append(uvt)
            isl = uv_islands(me, 1)
            tri_island = np.array([isl[t.polygon_index] for t in me.loop_triangles]) + island_offset
            all_uv1_ids.append(tri_island)
            island_offset = int(tri_island.max()) + 1 if len(tri_island) else island_offset
            info["islands"] = len(set(isl))
    # skin
    if arms and any(m.type == "ARMATURE" for m in o.modifiers):
        arm = [m.object for m in o.modifiers if m.type == "ARMATURE"][0]
        bone_names = {b.name for b in arm.data.bones}
        gi = {g.index: g.name for g in o.vertex_groups}
        hist = {}; per_bone = {}; unweighted = 0; max_err = 0.0; nonbone_groups = [g.name for g in o.vertex_groups if g.name not in bone_names]
        for v in me.vertices:
            ws = [(gi[g.group], g.weight) for g in v.groups if gi.get(g.group) in bone_names and g.weight > 0]
            hist[len(ws)] = hist.get(len(ws), 0) + 1
            s = sum(w for _, w in ws)
            if s <= 0:
                unweighted += 1
            else:
                max_err = max(max_err, abs(s - 1))
            for n, w in ws:
                per_bone[n] = per_bone.get(n, 0) + 1
        d["skin"] = {"armature": arm.name, "influence_histogram": hist, "verts_per_bone": per_bone,
                     "unweighted": unweighted, "max_weight_sum_error": max_err,
                     "non_bone_vertex_groups": nonbone_groups}
    mesh_out[o.name] = d
res["meshes"] = mesh_out
res["totals"] = tot
if meshes:
    allco = np.concatenate([t.reshape(-1, 3) for _, t in all_world_tris])
    res["bounds_cm"] = [(allco.min(axis=0) * 100).round(2).tolist(), (allco.max(axis=0) * 100).round(2).tolist()]
    res["size_cm"] = ((allco.max(axis=0) - allco.min(axis=0)) * 100).round(2).tolist()
# combined UV0 / UV1
if all_uv0:
    t0 = np.concatenate(all_uv0)
    ua = 0.5 * np.abs((t0[:, 1, 0] - t0[:, 0, 0]) * (t0[:, 2, 1] - t0[:, 0, 1]) - (t0[:, 2, 0] - t0[:, 0, 0]) * (t0[:, 1, 1] - t0[:, 0, 1]))
    res["uv0_combined"] = {"u_range": [float(t0[..., 0].min()), float(t0[..., 0].max())],
                           "v_range": [float(t0[..., 1].min()), float(t0[..., 1].max())],
                           "texel_px_per_cm_at_2048": math.sqrt(ua.sum() / (tot["area_m2"] * 1e4)) * 2048 if tot["area_m2"] else None,
                           "tile_repeat_cm_if_1uv_eq_1tile": 1.0 / math.sqrt(ua.sum() / (tot["area_m2"] * 1e4)) if ua.sum() else None}
    g = raster(t0, t0.reshape(-1, 2).min(axis=0), t0.reshape(-1, 2).max(axis=0), 1024)
    res["uv0_combined"]["overlap_pct_of_covered_1024"] = round(100.0 * int((g > 1).sum()) / max(int((g > 0).sum()), 1), 2)
    res["uv0_combined"]["max_stack"] = int(g.max())
if all_uv1:
    t1 = np.concatenate(all_uv1); ids = np.concatenate(all_uv1_ids)
    g = raster(t1, np.array([0.0, 0.0]), np.array([1.0, 1.0]), 1024)
    cov = int((g > 0).sum())
    res["uv1_combined"] = {"inside_0_1": bool(t1.min() >= -1e-5 and t1.max() <= 1 + 1e-5),
                           "coverage_pct_1024": round(100.0 * cov / 1024 ** 2, 2),
                           "overlap_pct_of_covered_1024": round(100.0 * int((g > 1).sum()) / max(cov, 1), 2),
                           "islands": int(len(np.unique(ids)))}
    gi = raster_ids(t1, ids, 512)
    res["uv1_combined"]["min_island_gap_px_at_512"] = min_gap_px(gi, 8)
    gi = raster_ids(t1, ids, 1024)
    res["uv1_combined"]["min_island_gap_px_at_1024"] = min_gap_px(gi, 16)
    # per-mesh uv1 overlap between different meshes (all were packed together?)
# self / cross intersections of the exported surfaces
if meshes and "--intersect" in argv:
    inter = {}
    trees = {}
    for name, tc in all_world_tris:
        verts = tc.reshape(-1, 3).tolist()
        polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tc))]
        trees[name] = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    names = list(trees)
    cross = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs = trees[names[i]].overlap(trees[names[j]])
            if pairs:
                cross[f"{names[i]} x {names[j]}"] = len(pairs)
    res["cross_object_intersecting_tri_pairs"] = cross
    res["cross_object_intersecting_tri_pairs_total"] = sum(cross.values())
    # self intersection within each object, ignoring pairs sharing a vertex (real mesh indices)
    selfi = {}
    for o in meshes:
        me = o.data
        mw = o.matrix_world
        verts = [(mw @ v.co)[:] for v in me.vertices]
        polys = [t.vertices[:] for t in me.loop_triangles]
        tree = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
        pairs = tree.overlap(tree)
        n = 0
        for a, b in pairs:
            if a >= b:
                continue
            if set(polys[a]) & set(polys[b]):
                continue
            n += 1
        selfi[o.name] = n
    res["self_intersecting_tri_pairs"] = selfi
    res["self_intersecting_tri_pairs_total"] = sum(selfi.values())
# armature
if arms:
    a = arms[0]
    bones = a.data.bones
    res["armature"] = {"object_name": a.name, "data_name": a.data.name, "bone_count": len(bones),
                       "roots": [b.name for b in bones if b.parent is None],
                       "bone_names": [b.name for b in bones],
                       "dotted_names": sum(1 for b in bones if "." in b.name),
                       "deform_flags_false": [b.name for b in bones if not b.use_deform],
                       "object_matrix_identity": all(abs(a.matrix_world[i][j] - (1 if i == j else 0)) < 1e-5 for i in range(4) for j in range(4)),
                       "object_scale": list(a.scale), "object_rotation": list(a.rotation_euler)}
    # pose == rest?
    maxdev = 0.0
    for pb in a.pose.bones:
        m = pb.matrix_basis
        maxdev = max(maxdev, max(abs(m[i][j] - (1 if i == j else 0)) for i in range(4) for j in range(4)))
    res["armature"]["pose_basis_max_dev_from_identity"] = maxdev
    # compare to JinMuWon skeleton (asset_report) and MetaHuman body bones
    jmw = json.load(open(REVIEW + "/eng_jmw_skeleton_from_asset_report.json"))
    jnames = [b["name"] for b in jmw["bones"]]
    mh = json.load(open(ROOT + "/WorkFiles/MetaHuman/player_default/rig/bones.json"))["/Game/MetaHumans/MH_PlayerDefault/Body/SKM_MH_PlayerDefault_BodyMesh"]["bones"]
    names = [b.name for b in bones]
    res["armature"]["vs_jinmuwon_152"] = {"same_names": set(names) == set(jnames), "missing": sorted(set(jnames) - set(names))[:20],
                                         "extra": sorted(set(names) - set(jnames))[:20]}
    jm = {b["name"]: b for b in jmw["bones"]}
    dmax = 0.0; parent_mismatch = []
    for b in bones:
        if b.name in jm:
            h = a.matrix_world @ b.head_local
            dmax = max(dmax, (Vector(jm[b.name]["head"]) - h).length)
            jp = jm[b.name]["parent"]
            if (b.parent.name if b.parent else None) != jp:
                parent_mismatch.append(b.name)
    res["armature"]["vs_jinmuwon_152"]["max_head_delta_m"] = dmax
    res["armature"]["vs_jinmuwon_152"]["parent_mismatch"] = parent_mismatch[:20]
    res["armature"]["vs_metahuman_body_342"] = {"shared_names": sorted(set(names) & set(mh)),
                                                "mh_bones_missing": len(set(mh) - set(names))}
    res["armature"]["bone_heads_of_weighted"] = {}
if RUN_QA and meshes:
    sys.path.insert(0, ROOT + "/Scripts")
    from pipeline.qa_check import qa_check
    objs = [o.name for o in meshes] + ([a.name for a in arms] if arms else [])
    kw = dict(budget_tris=30000, texel_density=5.12, require_uv1=not arms, require_ucx=True)
    try:
        r = qa_check(objs, **kw)
        failed = [c for c in r["checks"] if not c["passed"]]
        agg = {}
        for c in failed:
            agg.setdefault(c["name"], []).append(f'{c["object"]}: {c["detail"]}')
        res["qa_check"] = {"args": {k: v for k, v in kw.items()}, "passed": r["passed"],
                           "n_checks": len(r["checks"]), "n_failed": len(failed),
                           "failed_by_name": {k: {"count": len(v), "examples": v[:4]} for k, v in agg.items()},
                           "passed_names": sorted({c["name"] for c in r["checks"] if c["passed"]})}
    except Exception as exc:
        res["qa_check"] = {"error": repr(exc)}
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print("AUDIT_DONE", path, res["totals"])
