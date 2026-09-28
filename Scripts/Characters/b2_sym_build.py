"""b2_sym_build.py - PRIVATE / DO NOT SHIP. 2B symmetry step: make the rig exactly left/right symmetric.

  blender -b WorkFiles/Characters/2B_private/rig_work/c1_stage3a_heat.blend -P Scripts/Characters/b2_sym_unsunk.py
  blender -b WorkFiles/Characters/2B_private/2B_private_rig.blend -P Scripts/Characters/b2_sym_build.py

Input (read-only): 2B_private_rig.blend (opened, never saved over) and checks_sym/c1_sink_capture.npz (the skin's
garment-sink displacement of the verified rig, recovered by b2_sym_unsunk.py). Output: 2B_private_rig_sym.blend and
checks_sym/sym_build.json (+ mirror map arrays).

  1. skin topological mirror map (face walk, G8F topology), verified: bijection, involution, every face mapped onto a
     face of the same material, midline vertices self-mapped
  2. skin: the garment sink is taken out (exact per-vertex displacement), then the twist-aware mirror average
     (b2_sym_twist): on the upper arm / forearm / thigh / calf the twin is first rotated back around the limb onto the
     vertex's own angle and the layout moved half way, p' = R(th/2) ((p + R(-th) M p_twin) / 2); elsewhere th = 0, i.e.
     p' = (p + M p_twin) / 2; midline x = 0; UVs / materials / topology untouched
  3. head parts follow the skin (local displacement of the nearby skin), then each left/right pair of parts is placed
     as the average of the two (eyes: rigid average of centre + gaze, teeth / lashes: centroid average) and the right
     one is replaced by the exact mirror copy of the left one (unpaired lash cards get a mirrored twin)
  4. garments follow the skin (barycentric displacement of the nearest skin point); the bandeau (topologically
     symmetric since step C1) is mirror-averaged over its own face-walk map; the briefs (decimated source topology,
     not symmetric) are cut at x = 0 and rebuilt as her left half + its mirror, welded on the cut
  5. skin sunk 2-3 mm under the new garments again (same rule as b2_rig_apose), computed on the left half + midline
     and mirrored
  6. weights: skin = mirror average (twin vertex, _l <-> _r columns), max 8 influences, prune 1 %; garments from the
     final skin (barycentric), mirror-averaged; head parts 100 % head
  7. skeleton: pairs = mirror average (head position, bone length, rest orientation in the MH mirrored-axis convention
     R_r = -M R_l); midline bones on x = 0 with their axes in / normal to the sagittal plane
  8. soles on z = 0, uniform scale about the floor origin to 168 cm
"""
import bpy, bmesh, os, sys, json, math, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.interpolate import poly_3d_calc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_sym_lib import *  # noqa
from b2_sym_twist import bone_axes, twist_average  # noqa

SINK_NPZ = CHECKS + "/c1_sink_capture.npz"
BUILD_JSON = CHECKS + "/sym_build.json"
MAX_INF = 8
PRUNE = 0.01
TARGET_HEIGHT = 1.68
EYE_MATS = {"M_2B_Sclera", "M_2B_Irises", "M_2B_Pupils", "M_2B_Cornea", "M_2B_EyeMoisture", "M_2B_Tear"}
MM = Matrix.Diagonal((-1.0, 1.0, 1.0))


def limit_normalize(W, max_inf=MAX_INF, prune=PRUNE):
    W = np.where(W < prune, 0.0, W)
    if W.shape[1] > max_inf:
        idx = np.argsort(-W, axis=1)[:, max_inf:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1
    return W / s


def write_weights(obj, W, names):
    obj.vertex_groups.clear()
    groups = [obj.vertex_groups.new(name=n) for n in names]
    for j, g in enumerate(groups):
        col = W[:, j]
        for i in np.nonzero(col > 0)[0]:
            g.add([int(i)], float(col[i]), 'REPLACE')


def vertex_normals(me):
    n = np.zeros(len(me.vertices) * 3)
    me.vertex_normals.foreach_get("vector", n)
    return n.reshape(-1, 3)


def bm_components(bm, faces=None):
    faces = set(bm.faces) if faces is None else set(faces)
    seen = set(); out = []
    for f0 in faces:
        if f0 in seen:
            continue
        st = [f0]; seen.add(f0); comp = []
        while st:
            f = st.pop(); comp.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g in faces and g not in seen:
                        seen.add(g); st.append(g)
        out.append(comp)
    return out


def bary_sample(tree, polys, Xsrc, p):
    """nearest point on the mesh (Xsrc, polys): returns (vertex indices, weights, loc, face normal, dist)."""
    loc, nrm, fi, d = tree.find_nearest(Vector(p))
    vs = polys[fi]
    w = poly_3d_calc([Vector(Xsrc[v]) for v in vs], loc)
    return vs, np.array(w), loc, nrm, d


def mirror_copy_faces(bm, faces):
    """Duplicate faces (with their edges / verts), mirror the copy x -> -x and flip its winding. Returns
    (new_faces, old_vert -> new_vert)."""
    verts = list({v for f in faces for v in f.verts})
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(faces) + edges + verts)
    new_set = {g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)}
    vmap = {k: w for k, w in dup["vert_map"].items() if isinstance(k, bmesh.types.BMVert) and w in new_set and k not in new_set}
    new_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    for v in new_set:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    return new_faces, vmap


# ------------------------------------------------------------------------------------------------ head parts
def symmetrize_headparts(hp, skin_X_old, skin_D, rep):
    me = hp.data
    mats = [m.name for m in me.materials]
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    kd = KDTree(len(skin_X_old))
    for i, c in enumerate(skin_X_old):
        kd.insert(Vector(c), i)
    kd.balance()
    comps = []
    for c in bm_components(bm):
        vs = list({v for f in c for v in f.verts})
        mat = mats[max(set(f.material_index for f in c), key=lambda k: sum(1 for f in c if f.material_index == k))]
        P = np.array([list(v.co) for v in vs])
        cen = P.mean(axis=0)
        grp = "teeth" if mat == "M_2B_Teeth" else (("eye_" if mat in EYE_MATS else "lash_") + ("l" if cen[0] > 0 else "r"))
        comps.append({"faces": c, "verts": vs, "mat": mat, "cen": cen, "cen0": cen.copy(), "grp": grp})
    # follow the skin rigidly per group (each eye, each lash row, the whole dentition): inverse-distance mean
    # displacement of the skin within 2 cm of the group
    follow = {}
    for grp in sorted({c["grp"] for c in comps}):
        P = np.array([list(v.co) for c in comps if c["grp"] == grp for v in c["verts"]])
        cen = P.mean(axis=0)
        rad = float(np.linalg.norm(P - cen, axis=1).max())
        near = kd.find_range(Vector(cen), rad + 0.02)
        idx = np.array([n[1] for n in near]); dist = np.array([n[2] for n in near])
        w = 1.0 / (np.maximum(dist - rad, 0.0) + 0.003)
        follow[grp] = (skin_D[idx] * w[:, None]).sum(axis=0) / w.sum()
    for c in comps:
        t = follow[c["grp"]]
        for v in c["verts"]:
            v.co += Vector(t)
        c["cen"] = c["cen"] + t
        c["follow_mm"] = float(np.linalg.norm(t)) * 1000
    rep["headparts_group_follow_mm"] = {g: [round(float(x) * 1000, 3) for x in t] for g, t in follow.items()}
    log("headparts follow", rep["headparts_group_follow_mm"])
    rep["headparts_follow_mm"] = {"max": round(max(c["follow_mm"] for c in comps), 3),
                                  "mean": round(float(np.mean([c["follow_mm"] for c in comps])), 3)}
    left = [c for c in comps if c["cen0"][0] > 0]
    right = [c for c in comps if c["cen0"][0] <= 0]
    straddle = [c for c in comps if abs(c["cen0"][0]) < 0.001]  # a part centred on the midline (none expected)
    rep["headparts_components"] = {"total": len(comps), "left": len(left), "right": len(right), "straddling_midline": len(straddle)}
    assert not straddle, "a head part straddles the midline"
    # pair left / right components: same material, nearest mirrored centroid
    pairs = []
    free_r = set(range(len(right)))
    for li in sorted(range(len(left)), key=lambda k: -len(left[k]["verts"])):
        L = left[li]
        # paired on the positions BEFORE the follow (the dentition follows the mouth skin as one block, which moves
        # it sideways; the parts themselves are symmetric to ~0.4 mm there)
        cands = [(np.linalg.norm(L["cen0"] - right[ri]["cen0"] * M3), ri) for ri in free_r if right[ri]["mat"] == L["mat"]]
        if cands:
            d, ri = min(cands)
            if d < 0.004:
                pairs.append((L, right[ri], d)); free_r.discard(ri)
    paired_l = {id(p[0]) for p in pairs}
    unpaired_l = [c for c in left if id(c) not in paired_l]
    unpaired_r = [right[ri] for ri in sorted(free_r)]
    rep["headparts_pairs"] = {"pairs": len(pairs), "pair_centroid_err_mm_max": round(max(p[2] for p in pairs) * 1000, 3),
                              "unpaired_left": [(c["mat"], len(c["verts"])) for c in unpaired_l],
                              "unpaired_right": [(c["mat"], len(c["verts"])) for c in unpaired_r],
                              "vert_count_mismatch_pairs": sum(1 for a, b, _ in pairs if len(a["verts"]) != len(b["verts"]))}
    # eyes: rigid average (centre of the sclera + gaze = iris centroid - sclera centre), applied to the left eye
    eye_l = [p for p in pairs if p[0]["mat"] in EYE_MATS]
    scl = [p for p in eye_l if p[0]["mat"] == "M_2B_Sclera"][0]
    iri = [p for p in eye_l if p[0]["mat"] == "M_2B_Irises"][0]
    cL = scl[0]["cen"]; cR = scl[1]["cen"] * M3
    gL = iri[0]["cen"] - cL; gR = iri[1]["cen"] * M3 - cR
    gL /= np.linalg.norm(gL); gR /= np.linalg.norm(gR)
    c = (cL + cR) / 2
    g = (gL + gR); g /= np.linalg.norm(g)
    q = Vector(gL).rotation_difference(Vector(g))
    rot = q.to_matrix()
    for L, R, _ in eye_l:
        for v in L["verts"]:
            v.co = rot @ (v.co - Vector(cL)) + Vector(c)
    rep["eyes"] = {"centre_L_mm": [round(x * 1000, 3) for x in cL], "centre_R_mirrored_mm": [round(x * 1000, 3) for x in cR],
                   "centre_diff_mm": round(float(np.linalg.norm(cL - cR)) * 1000, 3),
                   "gaze_diff_deg": round(math.degrees(math.acos(max(-1, min(1, float(gL @ gR))))), 3),
                   "left_eye_moved_mm": round(float(np.linalg.norm(c - cL)) * 1000, 3),
                   "left_eye_rotated_deg": round(math.degrees(q.angle), 3)}
    # teeth / lashes: centroid average
    moved = []
    for L, R, _ in pairs:
        if L["mat"] in EYE_MATS:
            continue
        t = (R["cen"] * M3 - L["cen"]) / 2
        for v in L["verts"]:
            v.co += Vector(t)
        moved.append(float(np.linalg.norm(t)) * 1000)
    rep["teeth_lash_pair_shift_mm_max"] = round(max(moved), 3) if moved else 0.0
    # rebuild: right members of pairs -> mirror copies of the left; unpaired parts get a mirrored twin
    del_faces = [f for _, R, _ in pairs for f in R["faces"]]
    src_faces = [f for L, _, _ in pairs for f in L["faces"]] + [f for c in unpaired_l + unpaired_r for f in c["faces"]]
    nf, _ = mirror_copy_faces(bm, src_faces)
    bmesh.ops.delete(bm, geom=del_faces, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    n0 = len(me.vertices)
    bm.to_mesh(me); bm.free(); me.update()
    rep["headparts_verts"] = [n0, len(me.vertices)]
    hp.vertex_groups.clear()
    gr = hp.vertex_groups.new(name="head"); gr.add(list(range(len(me.vertices))), 1.0, 'REPLACE')


# ------------------------------------------------------------------------------------------------ garments
def top_mirror_map(bm, top_faces, allow_unmapped=0):
    """Face-walk mirror map of the bandeau. With allow_unmapped > 0 a walk that misses at most that many faces is
    returned as (None, unmapped_faces) so the caller can remove those stray faces and map again."""
    top_set = set(top_faces)
    tv = {v for f in top_faces for v in f.verts}
    cands = []
    for e in {e for f in top_faces for e in f.edges}:
        a, b = e.verts
        if len(e.link_faces) == 2 and all(f in top_set for f in e.link_faces) and abs(a.co.x) < 0.004 and abs(b.co.x) < 0.004 \
                and abs(a.co.z - b.co.z) > abs(a.co.x - b.co.x):
            cands.append((abs(a.co.x) + abs(b.co.x), e))
    cands.sort(key=lambda t: t[0])
    best = None
    why = Counter()
    for _, e in cands[:200]:
        res = walk(bm, e)
        if res is None:
            why["walk_inconsistent"] += 1
            continue
        mv, fmap = res
        miss = [f for f in top_faces if f.index not in fmap]
        if miss or any(mv[v.index] < 0 for v in tv):
            why["partial_%d_of_%d" % (len(top_faces) - len(miss), len(top_faces))] += 1
            if miss and len(miss) <= allow_unmapped:
                log("bandeau map: stray faces", [(f.index, [tuple(round(x, 4) for x in v.co) for v in f.verts]) for f in miss])
                return None, miss
            continue
        idx = np.array([v.index for v in tv])
        mvi = np.array([mv[i] for i in idx])
        if not all(mv[mv[i]] == i for i in idx):
            continue
        P = np.array([list(bm.verts[i].co) for i in idx]); Q = np.array([list(bm.verts[j].co) for j in mvi])
        err = float(np.median(np.linalg.norm(P - Q * M3, axis=1)))
        if best is None or err < best[0]:
            best = (err, np.array(mv))
            if err < 0.003:
                break
    log("bandeau map: candidates", len(cands), dict(why), "best", None if best is None else best[0])
    return best


def symmetrize_garments(gar, Xnat, D, skin_polys, rep):
    me = gar.data
    mats = [m.name for m in me.materials]
    under_i = mats.index("M_2B_Underwear")
    tree = BVHTree.FromPolygons([Vector(x) for x in Xnat], skin_polys)
    G = co_array(me)
    disp = np.zeros_like(G)
    dist = np.zeros(len(G))
    for i, p in enumerate(G):
        vs, w, loc, nrm, d = bary_sample(tree, skin_polys, Xnat, p)
        disp[i] = (D[list(vs)] * w[:, None]).sum(axis=0)
        dist[i] = d
    G2 = G + disp
    rep["garment_follow_mm"] = {"max": round(float(np.linalg.norm(disp, axis=1).max()) * 1000, 2),
                                "mean": round(float(np.linalg.norm(disp, axis=1).mean()) * 1000, 2)}
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    for v in bm.verts:
        v.co = Vector(G2[v.index])
    # --- bandeau: topological mirror average
    top_faces = [f for f in bm.faces if f.material_index != under_i]
    tm = top_mirror_map(bm, top_faces, allow_unmapped=4)
    stray = []
    if tm is not None and tm[0] is None:
        # a stray lip quad left at the lower front midline by the step C1 weld (its mirror is not in the mesh, two of
        # its verts belong to no other face): removed, then mapped again with full coverage required
        stray = [[tuple(round(x, 4) for x in v.co) for v in f.verts] for f in tm[1]]
        assert all(all(v.is_boundary for v in f.verts) for f in tm[1])
        bmesh.ops.delete(bm, geom=tm[1], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.verts.index_update(); bm.edges.index_update(); bm.faces.index_update()
        bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
        top_faces = [f for f in bm.faces if f.material_index != under_i]
        tm = top_mirror_map(bm, top_faces)
    assert tm is not None, "no topological mirror map for the bandeau"
    tmv = tm[1]
    tv = sorted({v.index for f in top_faces for v in f.verts})
    P = {i: bm.verts[i].co.copy() for i in tv}
    for i in tv:
        j = int(tmv[i])
        q = P[j]
        v = bm.verts[i]
        v.co = (P[i] + Vector((-q.x, q.y, q.z))) / 2
        if j == i:
            v.co.x = 0.0
    rep["bandeau"] = {"method": "topological mirror average (face walk from a midline edge; the step C1 bandeau was "
                                "rebuilt as left half + topological mirror, so its topology is symmetric)",
                      "stray_faces_removed": stray,
                      "verts": len(tv), "self_mapped_midline_verts": int(sum(1 for i in tv if tmv[i] == i)),
                      "pre_average_median_mirror_err_mm": round(tm[0] * 1000, 2)}
    # --- briefs: cut at x = 0, keep her left half (+X), mirror it, weld on the cut
    uw_faces = [f for f in bm.faces if f.material_index == under_i]
    nu0 = len({v for f in uw_faces for v in f.verts})
    geom = list({v for f in uw_faces for v in f.verts}) + list({e for f in uw_faces for e in f.edges}) + uw_faces
    res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                                 clear_inner=True, clear_outer=False)
    cut = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMVert)]
    for v in cut:
        v.co.x = 0.0
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    uw_faces = [f for f in bm.faces if f.material_index == under_i]
    stray = [v for f in uw_faces for v in f.verts if v.co.x < -1e-6]
    assert not stray, "briefs: geometry left on the right of the cut"
    tw = bm.verts.layers.int.new("sym_twin")
    uvset = list({v for f in uw_faces for v in f.verts})
    for k, v in enumerate(uvset):
        v[tw] = k + 1
    new_faces, vmap = mirror_copy_faces(bm, uw_faces)
    cut_set = {v for v in uvset if abs(v.co.x) < 1e-9}
    targetmap = {vmap[v]: v for v in cut_set}
    bmesh.ops.weld_verts(bm, targetmap=targetmap)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    uw_verts = list({v for f in bm.faces if f.material_index == under_i for v in f.verts})
    rep["briefs"] = {"method": "cut at x = 0 (bisect), her left half (+X) kept, mirrored copy welded on the cut "
                               "(the step C1 briefs are the decimated / subdivided source mesh, not topologically symmetric)",
                     "verts_before": nu0, "verts_after": len(uw_verts), "cut_verts_welded": len(cut_set),
                     "faces_after": sum(1 for f in bm.faces if f.material_index == under_i)}
    bm.verts.index_update(); bm.edges.index_update(); bm.faces.index_update()
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    n_top = len({v for f in bm.faces if f.material_index != under_i for v in f.verts})
    # garment twin map over the final bmesh (bandeau: face walk map recomputed on the final indices; briefs: tags)
    bm.verts.ensure_lookup_table()
    gmv = np.full(len(bm.verts), -1)
    bytag = {}
    for v in uw_verts:
        bytag.setdefault(v[tw], []).append(v.index)
    for k, lst in bytag.items():
        if len(lst) == 1:
            gmv[lst[0]] = lst[0]
        else:
            assert len(lst) == 2
            gmv[lst[0]] = lst[1]; gmv[lst[1]] = lst[0]
    bm.verts.layers.int.remove(tw)
    top_faces = [f for f in bm.faces if f.material_index != under_i]
    tm2 = top_mirror_map(bm, top_faces)
    for v in {v for f in top_faces for v in f.verts}:
        gmv[v.index] = tm2[1][v.index]
    assert (gmv >= 0).all() and (gmv[gmv] == np.arange(len(gmv))).all()
    bm.normal_update()
    bm.to_mesh(me); bm.free(); me.update()
    Gf = co_array(me)
    rep["garments_final_mirror_err_mm_max"] = round(float(np.linalg.norm(Gf - Gf[gmv] * M3, axis=1).max()) * 1000, 6)
    rep["garments_verts"] = {"bandeau": n_top, "briefs": len(uw_verts), "total": len(me.vertices)}
    return gmv, under_i


def sink_skin(Xs, skin_me, gar, rep_mask, mv, selfm, under_i, rep, passes=10):
    """Skin under the garments, computed on the representative (left + midline) vertices and mirrored:
      A. b2_rig_apose's rule: skin within 8 mm under a garment surface (same facing, dot > 0.6) is pushed to 3 mm below
         it (2 mm within 6 mm of a garment edge)
      B. every garment vertex (except the bandeau's rolled lip) keeps >= 2 mm to the skin (briefs' edge rows 1.5 mm, the
         step C1 conform distance): skin within 5 mm of its nearest skin point sinks along its normal (linear falloff)
    repeated until nothing moves (a sunk vertex can end under a different garment face)."""
    gme = gar.data
    gX = co_array(gme)
    gpolys = [tuple(p.vertices) for p in gme.polygons]
    gtree = BVHTree.FromPolygons([Vector(c) for c in gX], gpolys)
    gbm = bmesh.new(); gbm.from_mesh(gme)
    gbm.verts.ensure_lookup_table()
    under = set()
    for p in gme.polygons:
        if p.material_index == under_i:
            under.update(p.vertices)
    bpts = [Vector(gX[v.index]) for v in gbm.verts if v.is_boundary]
    lip = set(); brief_edge = set()
    for v in gbm.verts:
        if v.is_boundary:
            if v.index in under:
                brief_edge.add(v.index)
            else:
                lip.add(v.index)
                lip.update(e.other_vert(v).index for e in v.link_edges)
    gbm.free()
    kb = KDTree(len(bpts))
    for k, q in enumerate(bpts):
        kb.insert(q, k)
    kb.balance()
    polys = [tuple(p.vertices) for p in skin_me.polygons]
    X = Xs.copy()
    reps = np.nonzero(rep_mask)[0]
    hist = []
    sunkA = set(); sunkB = set()
    for it in range(passes):
        set_co(skin_me, X)
        N = vertex_normals(skin_me)
        nA = 0
        for i in reps:
            # the rule is evaluated on the vertex AND on its mirror twin (mirrored back): skin and garments are exactly
            # symmetric, but at the bandeau's rolled edge the nearest garment face can be a tie that the BVH breaks
            # differently on the two sides; the deeper push of the two wins, so both sides end clean
            best = None
            for k, mir in ((i, False), (int(mv[i]), True)):
                if mir and k == i:
                    continue
                p = Vector(X[k])
                loc, gn, fi, d = gtree.find_nearest(p, 0.008)
                if loc is None:
                    continue
                vs = gpolys[fi]
                fn = (Vector(gX[vs[1]]) - Vector(gX[vs[0]])).cross(Vector(gX[vs[2]]) - Vector(gX[vs[0]])).normalized()
                if fn.dot(Vector(N[k])) < 0.6:
                    continue
                sd = (p - loc).dot(fn)
                depth = 0.003 if kb.find(loc)[2] > 0.006 else 0.002
                if sd > -depth + 1e-5:
                    q = np.array(p + fn * (-depth - sd))
                    if mir:
                        q = q * M3
                    if best is None or -depth - sd > best[0]:
                        best = (-depth - sd, q)
            if best is not None:
                X[i] = best[1]
                nA += 1; sunkA.add(int(i))
        X[~rep_mask] = X[mv[~rep_mask]] * M3
        X[selfm, 0] = 0.0
        set_co(skin_me, X)
        N = vertex_normals(skin_me)
        stree = BVHTree.FromPolygons([Vector(c) for c in X], polys)
        kd = KDTree(len(X))
        for i, c in enumerate(X):
            kd.insert(Vector(c), i)
        kd.balance()
        push = np.zeros(len(X))
        for g in range(len(gX)):
            if g in lip:
                continue
            target = 0.0015 if g in brief_edge else 0.002
            loc, nrm, fi, d = stree.find_nearest(Vector(gX[g]))
            sd = (Vector(gX[g]) - loc).dot(nrm)
            if sd < target:
                deficit = target - sd + 0.0002
                for co, i, dd in kd.find_range(loc, 0.005):
                    if rep_mask[i]:
                        push[i] = max(push[i], deficit * (1.0 - dd / 0.005))
        nB = int((push > 1e-6).sum())
        sunkB.update(int(i) for i in np.nonzero(push > 1e-6)[0])
        X[rep_mask] -= N[rep_mask] * push[rep_mask][:, None]
        X[~rep_mask] = X[mv[~rep_mask]] * M3
        X[selfm, 0] = 0.0
        hist.append({"rule_A_verts": nA, "rule_B_verts": nB, "rule_B_max_push_mm": round(float(push.max()) * 1000, 3)})
        if nA == 0 and nB == 0:
            break
    d = np.linalg.norm(X - Xs, axis=1)
    rep["skin_sink"] = {"passes": hist, "verts_moved_total": int((d > 1e-7).sum()),
                        "max_push_mm": round(float(d.max()) * 1000, 3), "lip_verts_excluded": len(lip),
                        "brief_edge_verts_1.5mm": len(brief_edge)}
    return X


# ------------------------------------------------------------------------------------------------ skeleton
def sym_rotation_pair(Rl, Rr):
    """MH convention: R_r = -M R_l (all three axes mirrored and negated). Returns the averaged (R_l, R_r)."""
    ql = Rl.to_quaternion()
    qr = ((MM @ Rr) * -1.0).to_quaternion()
    if ql.dot(qr) < 0:
        qr.negate()
    q = ql.slerp(qr, 0.5)
    Rl2 = q.to_matrix()
    return Rl2, (MM @ Rl2) * -1.0


def sym_rotation_mid(R):
    """midline bone: symmetric iff R = M R diag(1, 1, -1) (X and Y axes in the sagittal plane, Z normal to it)."""
    D = Matrix.Diagonal((1.0, 1.0, -1.0))
    q1 = R.to_quaternion(); q2 = (MM @ R @ D).to_quaternion()
    if q1.dot(q2) < 0:
        q2.negate()
    return q1.slerp(q2, 0.5).to_matrix()


def main():
    t0 = time.time()
    fp = bpy.data.filepath.replace("\\", "/")
    assert fp.endswith("2B_private/2B_private_rig.blend"), fp
    rep = {"input_blend": fp}
    skin = bpy.data.objects["SK_2B_Body"]; hp = bpy.data.objects["SK_2B_HeadParts"]; gar = bpy.data.objects["SK_2B_Garments"]
    arm = bpy.data.objects["root"]
    for o in (skin, hp, gar, arm):
        assert o.matrix_world == Matrix.Identity(4), o.name
    me = skin.data
    order = [b.name for b in arm.data.bones]
    bi = {n: i for i, n in enumerate(order)}
    perm = np.array([bi[other(n)] for n in order])
    X = co_array(me)
    nv = len(X)
    polys = [tuple(p.vertices) for p in me.polygons]

    # ---------------------------------------------------------------- 1. mirror map
    t = time.time()
    mm = mirror_map(me, 0.95, 1.35)
    assert mm is not None
    mv = mm["mv"]; fmap = mm["fmap"]
    selfm = mv == np.arange(nv)
    bij = bool(len(set(mv.tolist())) == nv and (mv[mv] == np.arange(nv)).all())
    fsrc = np.zeros(len(me.polygons), dtype=int); me.attributes["src"].data.foreach_get("value", fsrc)
    fmat = np.zeros(len(me.polygons), dtype=int); me.polygons.foreach_get("material_index", fmat)
    fm = np.array([fmap[i] for i in range(len(me.polygons))])
    # midline: self-mapped vertices should form closed loops (2 self-mapped neighbours each)
    adj = [[] for _ in range(nv)]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    mid_deg = [sum(1 for w in adj[i] if selfm[w]) for i in np.nonzero(selfm)[0]]
    # UV check: the twin face's UV area has the same size (mirror-symmetric UV layout or shared island)
    uv = np.zeros(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    uva = np.zeros(len(me.polygons))
    for p in me.polygons:
        a = uv[p.loop_start:p.loop_start + p.loop_total]
        uva[p.index] = 0.5 * abs(np.dot(a[:, 0], np.roll(a[:, 1], 1)) - np.dot(a[:, 1], np.roll(a[:, 0], 1)))
    ratio = uva / np.maximum(uva[fm], 1e-12)
    rep["mirror_map"] = {"method": "topological face walk (b2_rig_apose.walk) from a torso midline edge",
                         "secs": round(time.time() - t, 1), "seeds_tried": mm["seeds_tried"],
                         "bijection_and_involution": bij, "all_faces_mapped": len(fmap) == len(me.polygons),
                         "midline_self_mapped_verts": int(selfm.sum()),
                         "midline_verts_with_2_midline_neighbours": int(sum(1 for d in mid_deg if d == 2)),
                         "midline_verts_other_degree": {str(k): int(v) for k, v in Counter(mid_deg).items() if k != 2},
                         "faces_twin_same_material": float((fmat == fmat[fm]).mean()),
                         "faces_twin_same_src_surface": float((fsrc == fsrc[fm]).mean()),
                         "faces_twin_uv_area_ratio_p1_p99": [round(float(np.percentile(ratio, 1)), 4), round(float(np.percentile(ratio, 99)), 4)],
                         "ambiguous_vertices": 0,
                         "note": "the walk reaches every face with one consistent involution, so no vertex needed the "
                                 "UV-island + position fallback"}
    assert bij and len(fmap) == len(me.polygons) and (fmat == fmat[fm]).all()
    np.save(CHECKS + "/mirror_map.npy", mv)
    log("mirror map", rep["mirror_map"])

    # ---------------------------------------------------------------- 2. skin: un-sink, mirror average
    cap = np.load(SINK_NPZ)
    k1 = float(cap["k"])
    dev = float(np.abs(cap["final"] - X).max())
    rep["sink_capture_matches_rig_skin_max_m"] = dev
    assert dev < 1e-5, dev
    S = (cap["post"] - cap["pre"]) * k1
    Xnat = X - S
    rep["garment_sink_removed"] = {"verts": int((np.linalg.norm(S, axis=1) > 1e-7).sum()),
                                   "max_mm": round(float(np.linalg.norm(S, axis=1).max()) * 1000, 3)}
    # twist-aware mirror average (b2_sym_twist): on the upper arm / forearm / thigh / calf the topological twin is
    # rotated around the limb against its mirrored geometric partner, so the twin is rotated back first and the vertex
    # layout moved half way; everywhere else this is the plain chord average (p + M p_twin) / 2
    Wpre = weights_matrix(skin, order)
    Wsym_pre = limit_normalize((Wpre + Wpre[mv][:, perm]) / 2)
    axes = bone_axes(arm)
    Xs, rep["skin_twist_average"] = twist_average(Xnat, mv, Wsym_pre, order, axes, (Xnat[:, 0] > 0) | selfm, log)
    assert float(np.linalg.norm(Xs - Xs[mv] * M3, axis=1).max()) < 1e-9
    assert rep["skin_twist_average"]["both_sides_evaluated_mirror_err_mm_before_snap"] < 0.01
    D = Xs - Xnat
    dn = np.linalg.norm(D, axis=1)
    rep["skin_symmetrize_move_mm"] = {"mean": round(float(dn.mean()) * 1000, 3), "p95": round(float(np.percentile(dn, 95)) * 1000, 3),
                                      "max": round(float(dn.max()) * 1000, 3)}

    # ---------------------------------------------------------------- 3. head parts
    symmetrize_headparts(hp, Xnat, D, rep)
    # ---------------------------------------------------------------- 4. garments
    gmv, under_i = symmetrize_garments(gar, Xnat, D, polys, rep)
    # ---------------------------------------------------------------- 5. sink skin under the new garments
    repv = selfm | (Xs[:, 0] > Xs[mv, 0]) | ((Xs[:, 0] == Xs[mv, 0]) & (np.arange(nv) < mv))  # one of each pair
    assert (repv ^ repv[mv] | selfm).all()
    Xk = sink_skin(Xs, me, gar, repv, mv, selfm, under_i, rep)
    set_co(me, Xk)

    # ---------------------------------------------------------------- 6. weights
    W = weights_matrix(skin, order)
    W0 = W.copy()
    Ws = (W + W[mv][:, perm]) / 2
    Ws = limit_normalize(Ws)
    # the limit can cut a different column on the two sides when two weights tie: make it exact again
    Ws = (Ws + Ws[mv][:, perm]) / 2
    for _ in range(3):
        Ws = limit_normalize(Ws)
        Ws2 = (Ws + Ws[mv][:, perm]) / 2
        if np.abs(Ws2 - Ws).max() < 1e-9:
            break
        Ws = Ws2
    wsym = float(np.abs(Ws - Ws[mv][:, perm]).max())
    head_c = bi["head"]
    rigid_before = W0[:, head_c] > 0.999
    rep["skin_weights"] = {"max_influences_before": int((W0 > 0).sum(axis=1).max()),
                           "max_influences_after": int((Ws > 0).sum(axis=1).max()),
                           "mean_influences_after": round(float((Ws > 0).sum(axis=1).mean()), 3),
                           "mirror_weight_err_max": wsym,
                           "rigid_head_verts_before": int(rigid_before.sum()),
                           "rigid_head_verts_after": int((Ws[:, head_c] > 0.999).sum()),
                           "rigid_head_verts_lost": int((rigid_before & ~(Ws[:, head_c] > 0.999)).sum()),
                           "weight_change_max": round(float(np.abs(Ws - W0).max()), 4),
                           "weight_change_mean_per_vert_L1": round(float(np.abs(Ws - W0).sum(axis=1).mean()), 4)}
    # nails stay rigid (one bone)
    write_weights(skin, Ws, order)
    # garments: barycentric skin weights at the nearest final skin point, mirror averaged
    gX = co_array(gar.data)
    tree = BVHTree.FromPolygons([Vector(x) for x in Xk], polys)
    GW = np.zeros((len(gX), len(order)))
    for i, p in enumerate(gX):
        vs, w, loc, nrm, d = bary_sample(tree, polys, Xk, p)
        GW[i] = (Ws[list(vs)] * w[:, None]).sum(axis=0)
    GW = limit_normalize(GW)
    for _ in range(4):
        GW = limit_normalize((GW + GW[gmv][:, perm]) / 2)
    rep["garment_weights"] = {"max_influences": int((GW > 0).sum(axis=1).max()),
                              "mirror_weight_err_max": float(np.abs(GW - GW[gmv][:, perm]).max())}
    write_weights(gar, GW, order)

    # ---------------------------------------------------------------- 7. skeleton
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    old = {b.name: (b.head_local.copy(), b.tail_local.copy(), b.matrix_local.to_3x3().copy(), b.length) for b in arm.data.bones}
    new = {}
    for n in order:
        h, tl, R, L = old[n]
        if n == other(n):
            R2 = sym_rotation_mid(R)
            h2 = Vector((0.0, h.y, h.z))
            new[n] = (h2, R2, L)
        elif n.endswith("_l"):
            hr, tr, Rr, Lr = old[other(n)]
            h2 = (h + MM @ hr) / 2
            Rl2, Rr2 = sym_rotation_pair(R, Rr)
            L2 = (L + Lr) / 2
            new[n] = (h2, Rl2, L2)
            new[other(n)] = (MM @ h2, Rr2, L2)
    # ---------------------------------------------------------------- 8. floor + 168 cm
    zmin = float(Xk[:, 2].min())
    Xk[:, 2] -= zmin
    height = float(Xk[:, 2].max())
    k = TARGET_HEIGHT / height
    Xk *= k
    Xk[selfm, 0] = 0.0
    set_co(me, Xk)
    for o in (hp, gar):
        G = co_array(o.data)
        G[:, 2] -= zmin
        set_co(o.data, G * k)
    rep["floor_and_height"] = {"floor_shift_mm": round(-zmin * 1000, 3), "height_before_scale_m": round(height, 5),
                               "uniform_scale": round(k, 6)}
    bpy.ops.object.mode_set(mode='EDIT')
    for n in order:
        h2, R2, L2 = new[n]
        h3 = Vector((h2.x, h2.y, h2.z - zmin)) * k
        eb = arm.data.edit_bones[n]
        eb.matrix = Matrix.Translation(h3) @ R2.to_4x4()
        eb.length = L2 * k
    bpy.ops.object.mode_set(mode='OBJECT')
    bmove = {n: (arm.data.bones[n].head_local - old[n][0]).length for n in order}
    rdev = {n: math.degrees(arm.data.bones[n].matrix_local.to_3x3().to_quaternion().rotation_difference(old[n][2].to_quaternion()).angle)
            for n in order}
    rep["skeleton"] = {"bone_count": len(order), "head_moved_mm_max": round(max(bmove.values()) * 1000, 3),
                       "head_moved_mm_top": sorted(((n, round(v * 1000, 2)) for n, v in bmove.items()), key=lambda t: -t[1])[:8],
                       "rest_orientation_dev_from_before_deg_max": round(max(rdev.values()), 5),
                       "rest_orientation_dev_from_MH_deg_max": round(max(rdev.values()), 5),
                       "note": "the step C1 rest orientations equal metahuman_base_skel exactly (dev 0.0), so the deviation "
                               "from the old rest is the deviation from MH"}
    # ---------------------------------------------------------------- checks
    me.update(); gar.data.update(); hp.data.update()
    X_fin = co_array(me)
    rep["skin_final_mirror_err_mm_max"] = round(float(np.linalg.norm(X_fin - X_fin[mv] * M3, axis=1).max()) * 1000, 6)
    rep["height_m"] = round(float(X_fin[:, 2].max() - X_fin[:, 2].min()), 5)
    rep["garment_clearance"] = garment_clearance(me, gar, under_i)
    rep["skin_under_garments"] = skin_poke(me, gar)
    rep["eyes_vs_lids"] = eye_lid_check(me, hp)
    # feet: heel / ball contact
    reg = skin_regions(X_fin, Ws, order, vert_src(me))
    feet = {}
    for s, sel in (("l", X_fin[:, 0] > 0), ("r", X_fin[:, 0] < 0)):
        f = (reg == "feet") & sel
        ank = arm.data.bones[f"foot_{s}"].head_local
        P = X_fin[f]
        heel = P[P[:, 1] > ank.y - 0.01]
        ball = P[np.abs(P[:, 1] - arm.data.bones[f"ball_{s}"].head_local.y) < 0.025]
        feet[s] = {"heel_min_z_mm": round(float(heel[:, 2].min()) * 1000, 3), "ball_min_z_mm": round(float(ball[:, 2].min()) * 1000, 3),
                   "toe_y_min_m": round(float(P[:, 1].min()), 4)}
    rep["feet"] = feet
    rep["facing"] = "-Y (unchanged: whole-body best-fit plane yaw before -0.11 deg, the mirror plane is x = 0)"
    save_json(BUILD_JSON, rep)
    bpy.ops.wm.save_as_mainfile(filepath=SYM_BLEND, compress=True, copy=False)
    log("saved", SYM_BLEND, round(time.time() - t0, 1), "s")
    log(json.dumps(rep)[:4000])


main()
