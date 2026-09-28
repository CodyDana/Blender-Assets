"""b2_rig_apose.py - PRIVATE / DO NOT SHIP. Step C1 stage 3b: clean weights, bake the A-pose rest, fix hands/feet,
skin head parts + garments, build the final armature. Writes WorkFiles/Characters/2B_private/2B_private_rig.blend.

  blender -b rig_work/c1_stage3a_heat.blend -P Scripts/Characters/b2_rig_apose.py

Posed -> A-pose per bone (rigid): T_b(x) = R_b^T (x - p'_b) + hA_b, blended with the cleaned weights (linear blend
skinning, exactly what the Armature modifier does), then:
  * left hand  := mirror of the (open, clean) right hand, weights mirrored too, blended in over the wrist
  * right foot := mirror of the corrected left foot (the boot crushed the right one), blended in over the ankle
  * left sole flattened (foot subtree rotated about the ankle until heel and ball touch the same floor)
  * everything shifted so the soles are at z = 0
The vertex mirror map is topological (the G8F-derived L1 shell is mirror-symmetric in topology), found by a
face-walk from a midline edge and checked for consistency.

Verifier fixes (2026-09-27, fix round 1):
  * rigid_face: face skin (Face / Lips / EyeSocket / Mouth + skin within 2.5 cm of teeth / eyes / lashes) is 100 % head,
    blending into the neck over 3 cm below the jaw / chin line; ears + scalp above the skull base blend over 4 cm
  * rebuild_top_right: the right half of CLO_BasicTop is re-cut as the topological mirror of the clean left half,
    slid along the skin to the left edge's height, with the front bridged (cleavage / under-bust) and relaxed
"""
import bpy, bmesh, os, sys, json, math, time
from collections import defaultdict, deque
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa

SOLVE = WORK + "/c1_rig_solve.json"
FIN = ("thumb", "index", "middle", "ring", "pinky")
HEAD_SRC = {"Face", "Lips", "Head", "Ears", "EyeSocket", "Mouth"}
MAX_INF = 8
TARGET_HEIGHT = 1.68
HAND_SRC_SIDE = "r"
PRUNE = 0.01


def other(n):
    if n.endswith("_l"):
        return n[:-2] + "_r"
    if n.endswith("_r"):
        return n[:-2] + "_l"
    return n


# ------------------------------------------------------------------------------------------------ topology mirror
def mirror_map(me, cx_fn):
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    co = [v.co.copy() for v in bm.verts]
    # candidate seed edges: near-vertical edges on the torso midline
    cands = []
    for e in bm.edges:
        a, b = e.verts
        if 0.95 < a.co.z < 1.35 and 0.95 < b.co.z < 1.35:
            da = abs(a.co.x - cx_fn(a.co.z)); db = abs(b.co.x - cx_fn(b.co.z))
            if da < 0.012 and db < 0.012 and abs(a.co.z - b.co.z) > abs(a.co.x - b.co.x) and len(e.link_faces) == 2:
                cands.append((da + db, e))
    cands.sort(key=lambda t: t[0])
    best = None
    for _, e in cands[:400]:
        res = walk(bm, e)
        if res is None:
            continue
        mv, nf = res
        if nf != len(bm.faces):
            continue
        # involution + geometric plausibility on the torso
        inv = all(mv[mv[i]] == i for i in range(len(mv)) if mv[i] >= 0)
        errs = sorted(abs(co[i].x - cx_fn(co[i].z) + (co[mv[i]].x - cx_fn(co[mv[i]].z))) + abs(co[i].z - co[mv[i]].z)
                      for i in range(0, len(mv), 7) if mv[i] >= 0 and 0.9 < co[i].z < 1.4)
        med = errs[len(errs) // 2]
        selfm = sum(1 for i in range(len(mv)) if mv[i] == i)
        if inv and selfm > 100 and (best is None or med < best[0]):
            best = (med, mv)
            if med < 0.01:
                break
    bm.free()
    return best


def walk(bm, e):
    fa, fb = e.link_faces
    v0, v1 = e.verts
    la = next(l for l in fa.loops if l.vert == v0 and l.link_loop_next.vert == v1) if any(
        l.vert == v0 and l.link_loop_next.vert == v1 for l in fa.loops) else None
    if la is None:
        la = next(l for l in fa.loops if l.vert == v1 and l.link_loop_next.vert == v0)
        v0, v1 = v1, v0
    lb = next((l for l in fb.loops if l.vert == v0), None)
    if lb is None:
        return None
    mv = [-1] * len(bm.verts)
    fmap = {}
    q = deque([(la, lb)])
    fmap[fa.index] = fb.index
    fmap[fb.index] = fa.index
    while q:
        l, m = q.popleft()
        if len(l.face.verts) != len(m.face.verts):
            return None
        a, b = l, m
        for _ in range(len(l.face.verts)):
            vi, wi = a.vert.index, b.vert.index
            if mv[vi] == -1:
                mv[vi] = wi
            elif mv[vi] != wi:
                return None
            if mv[wi] == -1:
                mv[wi] = vi
            elif mv[wi] != vi:
                return None
            r = a.link_loop_radial_next
            rb = b.link_loop_prev.link_loop_radial_next
            if r.face.index not in fmap:
                rb2 = rb.link_loop_next
                if rb2.face.index in fmap and fmap[rb2.face.index] != r.face.index:
                    return None
                fmap[r.face.index] = rb2.face.index
                fmap[rb2.face.index] = r.face.index
                q.append((r, rb2))
            a = a.link_loop_next; b = b.link_loop_prev
    return mv, len(fmap)


# ------------------------------------------------------------------------------------------------ helpers
def weights_matrix(obj, names):
    idx = {n: i for i, n in enumerate(names)}
    gi = {g.index: idx.get(g.name) for g in obj.vertex_groups}
    W = np.zeros((len(obj.data.vertices), len(names)))
    for v in obj.data.vertices:
        for g in v.groups:
            j = gi.get(g.group)
            if j is not None:
                W[v.index, j] = g.weight
    return W


def write_weights(obj, W, names):
    obj.vertex_groups.clear()
    groups = [obj.vertex_groups.new(name=n) for n in names]
    for j, g in enumerate(groups):
        col = W[:, j]
        nz = np.nonzero(col > 0)[0]
        for i in nz:
            g.add([int(i)], float(col[i]), 'REPLACE')


def limit_normalize(W, max_inf=MAX_INF, prune=PRUNE):
    W = np.where(W < prune, 0.0, W)
    if W.shape[1] > max_inf:
        idx = np.argsort(-W, axis=1)[:, max_inf:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1
    return W / s


def smooth_weights(W, adj, mask, iters, lam=0.5):
    for _ in range(iters):
        W2 = W.copy()
        for i in np.nonzero(mask)[0]:
            nb = adj[i]
            if nb:
                W2[i] = (1 - lam) * W[i] + lam * W[nb].mean(axis=0)
        W = W2
    return W


def lbs(X, W, Tm, Tt):
    """X (n,3) posed coords; W (n,b); Tm (b,3,3); Tt (b,3): out = sum_b w_b (Tm_b x + Tt_b)."""
    out = np.zeros_like(X)
    for j in range(W.shape[1]):
        w = W[:, j]
        nz = w > 0
        if not nz.any():
            continue
        out[nz] += w[nz, None] * (X[nz] @ Tm[j].T + Tt[j])
    return out


def geodesic_from(seeds, adj, co, allowed, max_d):
    """Dijkstra edge-length distance from a seed set over the allowed vertices, cut off at max_d."""
    import heapq
    dist = {int(i): 0.0 for i in seeds}
    pq = [(0.0, int(i)) for i in seeds]
    heapq.heapify(pq)
    while pq:
        d0, v = heapq.heappop(pq)
        if d0 > dist.get(v, 1e9):
            continue
        for w in adj[v]:
            if not allowed[w]:
                continue
            nd = d0 + float(np.linalg.norm(co[v] - co[w]))
            if nd < max_d and nd < dist.get(w, 1e9):
                dist[w] = nd
                heapq.heappush(pq, (nd, w))
    return dist


def rigid_face(Wfinal, order, bi, vsrc, region, adj, co, hp_co, head_joint, report):
    """Face skin rides 100% on the head, like the eyes / teeth / lashes (HeadParts are rigid head).

    Rigid face: every vertex of the Face, Lips, EyeSocket and Mouth surfaces and every body vertex within 2.5 cm of the
    teeth, eyes or lashes; below it head blends into the old (neck_01 / neck_02) weights over 3 cm of geodesic distance
    (smoothstep), so only the neck below the jaw / chin line bends.
    Rigid skull: the Ears and the "Head" surface (scalp) above the skull base (on this shell that surface also covers
    the whole neck, so only z > head joint + 1 cm counts as scalp); it blends over 4 cm, because a short blend under the
    ear / occiput crushed the side of the neck on a look over the shoulder.
    Each vertex keeps the larger head share of the two blends."""
    nv = len(co)
    face_mats = {"Face", "Lips", "EyeSocket", "Mouth"}
    headlike = np.array([str(r) in ("head", "body") for r in region])
    face = np.zeros(nv, dtype=bool)
    skull = np.zeros(nv, dtype=bool)
    for i in range(nv):
        if not headlike[i]:
            continue
        if vsrc[i] & face_mats:
            face[i] = True
        elif "Ears" in vsrc[i] or ("Head" in vsrc[i] and co[i, 2] > head_joint[2] + HEAD_SCALP_DZ):
            skull[i] = True
    kd = KDTree(len(hp_co))
    for k, c in enumerate(hp_co):
        kd.insert(Vector(c), k)
    kd.balance()
    near = 0
    for i in np.nonzero(headlike & ~face & (co[:, 2] > head_joint[2] - 0.12))[0]:
        if kd.find(Vector(co[i]))[2] < HEAD_PART_RADIUS:
            face[i] = True; near += 1
    tmin = np.ones(nv)
    for seeds, blend in ((face, HEAD_BLEND_FACE), (skull, HEAD_BLEND_SKULL)):
        for i, d in geodesic_from(np.nonzero(seeds)[0], adj, co, headlike, blend).items():
            u = min(1.0, d / blend)
            tmin[i] = min(tmin[i], u * u * (3 - 2 * u))
    hcol = bi["head"]
    rows = np.nonzero(tmin < 1.0)[0]
    t = tmin[rows][:, None]
    oh = np.zeros(Wfinal.shape[1]); oh[hcol] = 1.0
    Wfinal[rows] = Wfinal[rows] * t + oh[None, :] * (1.0 - t)
    report["rigid_face"] = {"face_rigid_verts": int(face.sum()), "skull_rigid_verts": int(skull.sum()),
                            "near_headparts_verts": near, "blend_verts": int(((tmin > 0) & (tmin < 1)).sum()),
                            "blend_face_m": HEAD_BLEND_FACE, "blend_skull_m": HEAD_BLEND_SKULL,
                            "scalp_cut_z_prescale": round(float(head_joint[2] + HEAD_SCALP_DZ), 4)}
    return Wfinal


HEAD_BLEND_FACE = 0.03    # geodesic head -> neck blend below the rigid face (jaw / chin line)
HEAD_BLEND_SKULL = 0.04   # ... below the rigid ears / skull base
HEAD_PART_RADIUS = 0.025  # skin this close to teeth / eyes / lashes is rigid head
HEAD_SCALP_DZ = 0.01      # "Head" surface counts as skull above head joint + 1 cm (the rest of it is neck)


def bridge_front(bm, under_i, skin_tree, iters=40):
    """Bridge the cleavage on the front of the bandeau again (the mirrored offsets do not bridge her higher right
    breast, which left a crease along its inner contour). Like build_top did in the source pose, each front vertex
    should lie on the 2D convex hull of its 6 mm horizontal slice: req = how far it must move out along the slice's
    radial direction to reach the hull. That field is smoothed as an upper envelope (s = max(req, mean of the
    neighbours), outward only) so the bridge has no slice steps; each rolled-lip vertex follows its edge vertex.
    Returns the number of vertices that needed a push."""
    import mathutils.geometry as mg
    topv = [v for v in bm.verts if any(f.material_index != under_i for f in v.link_faces)]
    tset = set(topv)
    lip = {v for v in topv if v.is_boundary}
    partner = {}
    for v in lip:
        o = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in tset and e.other_vert(v) not in lip]
        if o:
            partner[v] = o[0]
    outer = [v for v in topv if v not in lip]
    oset = set(outer)
    ycen = (min(v.co.y for v in topv) + max(v.co.y for v in topv)) / 2
    base = {v: v.co.copy() for v in topv}
    # 1) vertical: the fabric hangs straight from the bust to the lower edge (her right breast sits ~2 cm higher, so
    #    the mirrored band would dip into its under-bust fold): front vertices are moved forward (-Y) onto the
    #    (y, z) convex hull of their 6 mm vertical slice, smoothed the same way
    vfront = [v for v in outer if v.co.y < ycen - 0.02]
    vset = set(vfront)
    vb = defaultdict(list)
    for v in vfront:
        vb[int(math.floor(v.co.x / 0.006))].append(v)
    vreq = {v: 0.0 for v in outer}
    for k, vs in vb.items():
        if len(vs) < 8:
            continue
        pts = [Vector((v.co.y, v.co.z)) for v in vs]
        poly = [pts[i].copy() for i in mg.convex_hull_2d(pts)]
        for v, p in zip(vs, pts):
            best = None
            for i in range(len(poly)):
                a_ = poly[i]; b_ = poly[(i + 1) % len(poly)]
                e_ = b_ - a_
                if abs(e_.y) < 1e-12:
                    continue
                u = (p.y - a_.y) / e_.y
                if -1e-9 <= u <= 1 + 1e-9:
                    yh = a_.x + u * e_.x
                    t = p.x - yh  # forward (-Y) move to reach this hull edge
                    if t >= 0 and (best is None or t > best):
                        best = t
            if best is not None and best > 0.0005:
                vreq[v] = best
    vs_ = dict(vreq)
    for it in range(iters):
        ns = {}
        for v in vfront:
            nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in oset]
            avg = sum(vs_[w] for w in nb) / len(nb) if nb else vs_[v]
            ns[v] = max(vreq[v], 0.5 * vs_[v] + 0.5 * avg)
        vs_.update(ns)
    for v in outer:
        v.co.y -= vs_[v]
    # 2) horizontal (the cleavage), as in build_top
    bins = defaultdict(list)
    for v in outer:
        bins[int(math.floor(v.co.z / 0.006))].append(v)
    req = {v: 0.0 for v in outer}
    dirs = {v: Vector((0.0, 0.0)) for v in outer}
    for k, vs in bins.items():
        if len(vs) < 8:
            continue
        pts = [v.co.xy for v in vs]
        poly = [pts[i].copy() for i in mg.convex_hull_2d(pts)]
        cen = sum(poly, Vector((0, 0))) / len(poly)
        for v in vs:
            p = v.co.xy
            d = p - cen
            if d.length < 1e-6:
                continue
            d.normalize()
            dirs[v] = d
            if v.co.y >= ycen:
                continue  # front only
            # ray p + t d (t >= 0) against the hull edges
            best = None
            for i in range(len(poly)):
                a = poly[i]; b = poly[(i + 1) % len(poly)]
                e_ = b - a
                den = d.x * e_.y - d.y * e_.x
                if abs(den) < 1e-12:
                    continue
                w = a - p
                t = (w.x * e_.y - w.y * e_.x) / den
                u = (w.x * d.y - w.y * d.x) / den
                if t >= 0 and -1e-9 <= u <= 1 + 1e-9:
                    best = t if best is None else min(best, t)
            if best is not None and best > 0.0005:
                req[v] = best
    free = [v for v in outer if v.co.y < ycen]
    s = dict(req)
    for it in range(iters):
        ns = {}
        for v in free:
            nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in oset]
            avg = sum(s[w] for w in nb) / len(nb) if nb else s[v]
            ns[v] = max(req[v], 0.5 * s[v] + 0.5 * avg)
        s.update(ns)
    for v in outer:
        if s[v] > 0:
            v.co.x += dirs[v].x * s[v]; v.co.y += dirs[v].y * s[v]
    # 3) relax the rebuilt front (her right half + the cleavage, x < 7 cm) so the bridged areas meet the breast
    #    without a crease; the upper / lower edge rows stay put and the skin clearance stays >= 2 mm
    edge_rows = set(partner.values())
    relax = [v for v in outer if v.co.y < ycen and v.co.x < 0.07 and v not in edge_rows]
    for it in range(8):
        new = {}
        for v in relax:
            nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in oset]
            if nb:
                new[v] = v.co * 0.5 + (sum((w.co for w in nb), Vector()) / len(nb)) * 0.5
        for v, c in new.items():
            loc, nrm, fi, d = skin_tree.find_nearest(c, 0.03)
            if loc is not None and (c - loc).dot(nrm) < 0.002:
                c = loc + nrm * 0.002
            v.co = c
    for v, o in partner.items():
        v.co = base[v] + (o.co - base[o])
    return {"horizontal": sum(1 for v in outer if req[v] > 0), "vertical": sum(1 for v in outer if vreq[v] > 0),
            "vertical_max_mm": round(max(vs_.values()) * 1000, 1)}


def rebuild_top_right(gme, gXA, GW, side_rows, under_i, XA, polys, Wfinal, mv, report):
    """Re-cut the right half (her right, -X) of the bandeau as the topological mirror of the clean left half.

    The bandeau was cut from the skin shell's chest faces in the (asymmetric) source pose, so after the A-pose bake
    its right upper edge stepped down ~3 cm with a ragged edge and the upper-breast skin came out in front of it.
    Every bandeau vertex remembers its source skin vertex ("skin_vert"; lip vertices share their edge vertex's), and
    the skin shell has an exact topological mirror map (mv). So the right half is rebuilt from the left half:
      * left half = bandeau faces whose skin vertices are all on the left of / on the topological midline
      * each left vertex s is copied to the mirrored skin vertex r = mv[sv]: p' = X[r] + M(p_s - X[sv]), M: x -> -x
        (the same offset from the skin as on the left, so the copy follows HER right chest, which is not symmetric)
      * midline vertices (mv[sv] == sv) are shared, so the halves weld exactly
      * weights of the copies = the A-pose skin weights of r (exact source vertex, as the left half), with the same
        damped upper-arm share at the sides
    Underwear untouched."""
    bm = bmesh.new(); bm.from_mesh(gme)
    bm.verts.ensure_lookup_table()
    orig = bm.verts.layers.int.new("orig_idx")
    for v in bm.verts:
        v.co = Vector(gXA[v.index]); v[orig] = v.index
    svl = bm.verts.layers.int.get("skin_vert")
    kdl = KDTree(len(XA))
    for i, c in enumerate(XA):
        kdl.insert(Vector(c), i)
    kdl.balance()

    def sv_of(v):
        s = v[svl]
        if s < 0:  # no exact source vertex: nearest skin vertex
            s = kdl.find(v.co)[1]
        return int(s)

    def side(v):
        s = sv_of(v)
        if mv[s] == s:
            return 0
        return 1 if XA[s, 0] > XA[mv[s], 0] else -1
    top_faces = [f for f in bm.faces if f.material_index != under_i]
    n_top_before = len({v for f in top_faces for v in f.verts})
    vside = {v: side(v) for f in top_faces for v in f.verts}
    straddle = sum(1 for f in top_faces if {vside[v] for v in f.verts} >= {1, -1})
    right_faces = [f for f in top_faces if any(vside[v] < 0 for v in f.verts)]
    # free (outer) edge of the original left half, before the right half is cut away (the cut opens the midline)
    tz_med = float(np.median([v.co.z for v in vside]))
    left_edge = [(v.co.x, v.co.y, v.co.z) for v in vside if vside[v] > 0 and v.is_boundary and v.co.z > tz_med]
    bmesh.ops.delete(bm, geom=right_faces, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    left_faces = [f for f in bm.faces if f.material_index != under_i]
    left_verts = list({v for f in left_faces for v in f.verts})
    dup = bmesh.ops.duplicate(bm, geom=left_faces + list({e for f in left_faces for e in f.edges}) + left_verts)
    # vert_map holds both directions (old -> new and new -> old): keep only old -> new
    new_set = {g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)}
    vmap = {k: w for k, w in dup["vert_map"].items() if isinstance(k, bmesh.types.BMVert) and w in new_set and k not in new_set}
    new_faces = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    copy_src = {}
    weld = []
    for old, new in vmap.items():
        s = sv_of(old)
        if mv[s] == s:
            new.co = old.co.copy()
            weld += [old, new]
            continue
        r = int(mv[s])
        d = old.co - Vector(XA[s])
        new.co = Vector(XA[r]) + Vector((-d.x, d.y, d.z))
        new[svl] = r
        copy_src[new] = (old, r)
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    # her right breast sits ~2 cm higher than the left in the A-pose (a leftover of the source pose), so the plain
    # topological copy would put the right edge ~2 cm above the left one. Each copy therefore slides along the skin
    # to the height of its left source: its skin anchor X[r] is moved to the source's height and projected back onto
    # the skin (nearest point), and the mirrored offset is carried over, rotated from the old to the new skin normal.
    # Midline vertices do not move (zero height difference), so the halves still weld; the slide is smoothed a little.
    skin_tree = BVHTree.FromPolygons([Vector(x) for x in XA], polys)
    vn = np.zeros((len(XA), 3))
    for f in polys:
        a_, b_, c_ = (Vector(XA[f[k]]) for k in range(3))
        fn = (b_ - a_).cross(c_ - a_)
        for k in f:
            vn[k] += np.array(fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    # (the lateral position is NOT matched: the skin's topological midline wanders from x = -14 to +26 mm, so a
    # lateral mirror would drag the copies 3-10 cm across the skin; the midline x values are reported)
    mids = [v for v in weld[0::2]]
    mid_x = {"front": sorted(round(v.co.x * 1000, 1) for v in mids if v.co.y < 0.0),
             "back": sorted(round(v.co.x * 1000, 1) for v in mids if v.co.y >= 0.0)}
    # the upper edge of the left half as a height profile over |x| (front and back): where a copy lands at a
    # different |x| than its source (her back is not symmetric either), its target height follows the left edge's
    # slope, so the two edges match positionally (x -> -x) and not only topologically
    ycen = (min(v.co.y for v in left_verts) + max(v.co.y for v in left_verts)) / 2
    prof = {}
    LE = np.array(left_edge)
    for part, sel in (("front", LE[:, 1] < ycen), ("back", LE[:, 1] >= ycen)):
        e = np.stack([np.abs(LE[sel, 0]), LE[sel, 2]], axis=1)
        xs = np.arange(0.0, 0.16, 0.005)
        zs = np.array([e[np.abs(e[:, 0] - x0) < 0.005, 1].max() if (np.abs(e[:, 0] - x0) < 0.005).any() else np.nan for x0 in xs])
        ok = ~np.isnan(zs)
        zs = np.interp(xs, xs[ok], zs[ok])
        zs = np.convolve(np.pad(zs, 1, mode="edge"), np.ones(3) / 3, mode="valid")
        prof[part] = (xs, zs)

    def edge_z(part, x):
        xs, zs = prof[part]
        return float(np.interp(abs(x), xs, zs))
    slide = {}
    anchor = {}
    for new, (old, r) in copy_src.items():
        anc = Vector(XA[r]); n0 = Vector(vn[r]); off = new.co - anc
        p = new.co.copy()
        part = "front" if old.co.y < ycen else "back"
        for k in range(4):  # fixed point: the offset turns with the normal, so re-aim at the source height
            dz = p.z - (old.co.z + edge_z(part, p.x) - edge_z(part, old.co.x))
            loc, nT, fi, d = skin_tree.find_nearest(anc - Vector((0, 0, dz)), 0.06)
            if loc is None:
                break
            off = n0.rotation_difference(nT) @ off
            anc = loc; n0 = nT
            p = anc + off
        slide[new] = p - new.co
        anchor[new] = anc
    report_slide = [s_.length for s_ in slide.values()]
    for it in range(1):
        ns = {}
        for v, s_ in slide.items():
            nb = [slide[e.other_vert(v)] for e in v.link_edges if e.other_vert(v) in slide]
            ns[v] = s_ * 0.5 + (sum(nb, Vector()) / len(nb)) * 0.5 if nb else s_
        slide = ns
    for v, s_ in slide.items():
        v.co += s_
    bmesh.ops.remove_doubles(bm, verts=weld, dist=1e-7)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    bridged = bridge_front(bm, under_i, skin_tree)
    n = len(bm.verts)
    new_gXA = np.array([list(v.co) for v in bm.verts])
    new_GW = np.zeros((n, GW.shape[1]))
    new_side = np.zeros(n, dtype=bool)
    anchor_idx = np.full(n, -1)
    for v in bm.verts:
        if v in copy_src:
            old, r = copy_src[v]
            # skin weights of the skin vertex the copy now sits on (after the height slide)
            anchor_idx[v.index] = kdl.find(anchor[v])[1] if v in anchor else r
            new_GW[v.index] = Wfinal[anchor_idx[v.index]]
            new_side[v.index] = bool(side_rows[old[orig]])
        else:
            new_GW[v.index] = GW[v[orig]]
    bm.verts.layers.int.remove(orig)
    bm.to_mesh(gme); gme.update()
    bm.free()
    new_under = set()
    for p in gme.polygons:
        if p.material_index == under_i:
            new_under.update(p.vertices)
    report["top_right_rebuilt"] = {
        "method": "topological mirror of the left half onto the mirrored skin vertices (same skin offsets)",
        "top_verts_before": n_top_before, "top_verts_after": int(sum(1 for i in range(n) if i not in new_under)),
        "copied_verts": len(copy_src), "midline_welded": len(weld) // 2, "faces_straddling_midline": straddle,
        "right_faces_removed": len(right_faces),
        "midline_x_mm": mid_x,
        "cleavage_bridge_pushed_verts": bridged,
        "height_slide_mm": {"p50": round(float(np.median(report_slide)) * 1000, 1) if report_slide else None,
                            "max": round(float(max(report_slide)) * 1000, 1) if report_slide else None}}
    return new_gXA, new_GW, new_side, new_under, anchor_idx


def main():
    t0 = time.time()
    S = json.load(open(SOLVE))
    order = S["order"]; PAR = S["parent"]
    bi = {n: i for i, n in enumerate(order)}
    Q = {n: Matrix(S["Q"][n]) for n in order}
    R = {n: Matrix(S["R"][n]) for n in order}
    hA = {n: Vector(S["hA"][n]) for n in order}
    Pp = {n: Vector(S["Pp"][n]) for n in order}
    report = {"notes": []}
    skin = bpy.data.objects["SK_2B_Body"]
    me = skin.data
    nv = len(me.vertices)
    X = np.array([list(v.co) for v in me.vertices])
    src = np.zeros(len(me.polygons), dtype=int)
    me.attributes["src"].data.foreach_get("value", src)
    vsrc = [set() for _ in range(nv)]
    for p, s in zip(me.polygons, src):
        for v in p.vertices:
            vsrc[v].add(SHELL[s])
    adj = [[] for _ in range(nv)]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)

    # limb components (side by centroid x)
    def comps(mats):
        vset = {i for i in range(nv) if vsrc[i] & mats}
        seen = set(); out = []
        for s0 in vset:
            if s0 in seen:
                continue
            c = []; st = [s0]; seen.add(s0)
            while st:
                v = st.pop(); c.append(v)
                for w in adj[v]:
                    if w in vset and w not in seen:
                        seen.add(w); st.append(w)
            out.append(c)
        return {("l" if X[c, 0].mean() > 0 else "r"): np.array(c) for c in out}
    arms = comps({"Arms", "Fingernails"})
    legs = comps({"Legs", "Toenails"})
    region = np.array(["body"] * nv, dtype=object)
    for s, c in arms.items():
        region[c] = "arm_" + s
    for s, c in legs.items():
        region[c] = "leg_" + s
    zh = Pp["head"].z - 0.01
    for i in range(nv):
        if region[i] == "body" and vsrc[i] & HEAD_SRC and not vsrc[i] & {"Body"} and X[i, 2] > zh:
            region[i] = "head"

    # ------------------------------------------------ weights: region rules
    W = weights_matrix(skin, order)
    allowed = {}
    for s in ("l", "r"):
        allowed["arm_" + s] = {f"clavicle_{s}", f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}", "spine_05", "spine_04"} | \
            {n for n in order if n.startswith(FIN) and n.endswith("_" + s)}
        allowed["leg_" + s] = {"pelvis", "spine_01", f"thigh_{s}", f"calf_{s}", f"foot_{s}", f"ball_{s}"}
    allowed["head"] = {"head", "neck_02", "neck_01"}
    body_forbid = {n for n in order if n.startswith(FIN) or n.split("_")[0] in ("lowerarm", "hand", "calf", "foot", "ball")}
    allowed["body"] = set(order) - body_forbid
    M = {k: np.array([n in v for n in order]) for k, v in allowed.items()}
    for k, m in M.items():
        rows = region == k
        W[np.ix_(rows, ~m)] = 0.0
    # body: no opposite-side arm/leg weights beyond the midline
    side_bones = {s: np.array([n.endswith("_" + s) for n in order]) for s in ("l", "r")}
    body_rows = region == "body"
    rl = np.nonzero(body_rows & (X[:, 0] > 0.02))[0]; W[np.ix_(rl, np.nonzero(side_bones["r"])[0])] = 0.0
    rr = np.nonzero(body_rows & (X[:, 0] < -0.02))[0]; W[np.ix_(rr, np.nonzero(side_bones["l"])[0])] = 0.0
    # one finger per vertex (heat bleeds between touching fingers)
    for s in ("l", "r"):
        fcols = {f: np.array([bi[n] for n in order if n.startswith(f) and n.endswith("_" + s) and "metacarpal" not in n]) for f in FIN}
        tot = np.stack([W[:, c].sum(axis=1) for c in fcols.values()], axis=1)
        keep = tot.argmax(axis=1)
        for k, (f, c) in enumerate(fcols.items()):
            rows = np.nonzero((keep != k) & (tot.sum(axis=1) > 0))[0]
            W[np.ix_(rows, c)] = 0.0
    # fingers: heat smears the weights along the short phalanx segments (rubber fingers in a fist), so the finger
    # weights of the source (right) hand are rebuilt by projecting each finger vertex on its own joint chain with
    # narrow blends at the knuckles (MCP +-6 mm, PIP / DIP +-3 mm); the proximal remainder keeps the heat ratio
    # between the metacarpal and the hand
    ends = {k: Vector(v) for k, v in S["ends_posed"].items()}
    JX = json.load(open(JOINTS))["extra"]
    for s_ in ("l", "r"):
        for f in FIN:
            ends[f"{f}_03_{s_}"] = Vector(JX[f"{f}_tip_{s_}"])  # measured fingertips (posed)
    fing_report = {}
    for s in (HAND_SRC_SIDE,):
        hand_cols = [bi[f"hand_{s}"]] + [bi[n] for n in order if n.startswith(FIN) and n.endswith("_" + s)]
        cand = np.nonzero((region == "arm_" + s) & (W[:, hand_cols].sum(axis=1) > 0.3))[0]
        P = X[cand]
        chains = {}
        for f in FIN:
            chain = [f"{f}_01_{s}", f"{f}_02_{s}", f"{f}_03_{s}"]
            pts = [np.array(Pp[c]) for c in chain] + [np.array(ends[f"{f}_03_{s}"])]
            best_d = np.full(len(cand), 1e9); best_s = np.zeros(len(cand)); acc = 0.0
            for k in range(3):
                a_, b_ = pts[k], pts[k + 1]
                d = b_ - a_; L2 = d @ d
                t = np.clip(((P - a_) @ d) / L2, -10 if k == 0 else 0.0, 1.0)
                dist = np.linalg.norm(P - (a_ + t[:, None] * d), axis=1)
                better = dist < best_d
                best_d[better] = dist[better]; best_s[better] = acc + t[better] * np.sqrt(L2)
                acc += np.sqrt(L2)
            seglen = [float(np.linalg.norm(pts[k + 1] - pts[k])) for k in range(3)]
            chains[f] = (best_d, best_s, seglen, [bi[c] for c in chain])
        D_ = np.stack([chains[f][0] for f in FIN], axis=1)
        owner = D_.argmin(axis=1)
        # topological finger labels: fingers touch geometrically but are only connected through the webs, so a
        # join-tree sweep of the geodesic distance from the forearm (descending) labels every vertex beyond its web
        hand_set = set(cand.tolist())
        arm_rows = np.nonzero(region == "arm_" + s)[0]
        seeds = [int(i) for i in arm_rows if W[i, hand_cols].sum() < 0.2]
        import heapq
        dist = {i: 0.0 for i in seeds}
        pq = [(0.0, i) for i in seeds]; heapq.heapify(pq)
        arm_set = set(arm_rows.tolist())
        while pq:
            d0, v = heapq.heappop(pq)
            if d0 > dist.get(v, 1e9):
                continue
            for w in adj[v]:
                if w in arm_set:
                    nd = d0 + float(np.linalg.norm(X[v] - X[w]))
                    if nd < dist.get(w, 1e9):
                        dist[w] = nd; heapq.heappush(pq, (nd, w))
        tipv = {}
        for f in FIN:
            tp = np.array(ends[f"{f}_03_{s}"])
            tipv[f] = int(arm_rows[np.argmin(np.linalg.norm(X[arm_rows] - tp, axis=1))])
        parent_uf = {}

        def find(a):
            while parent_uf[a] != a:
                parent_uf[a] = parent_uf[parent_uf[a]]
                a = parent_uf[a]
            return a
        comp_tip = {}
        label = {}
        tip_of_vert = {v: f for f, v in tipv.items()}
        for v in sorted(dist, key=lambda i: -dist[i]):
            roots = {find(u) for u in adj[v] if u in parent_uf}
            parent_uf[v] = v
            tipped = [r for r in roots if comp_tip.get(r)]
            fins = {comp_tip[r] for r in tipped}
            for r in roots:
                parent_uf[r] = v
            if len(fins) > 1:
                comp_tip[v] = "palm"
            elif len(fins) == 1:
                comp_tip[v] = fins.pop() if "palm" not in [comp_tip[r] for r in tipped] else "palm"
            else:
                comp_tip[v] = tip_of_vert.get(v)
            if v in tip_of_vert and comp_tip[v] is None:
                comp_tip[v] = tip_of_vert[v]
            if comp_tip[v] in FIN:
                label[v] = comp_tip[v]
        # fold labels into the owner array (topology wins over geometry beyond the webs)
        topo = 0
        for j, v in enumerate(cand):
            f = label.get(int(v))
            if f is not None:
                owner[j] = FIN.index(f); topo += 1
        fing_report["_topological_labels"] = {f: sum(1 for x in label.values() if x == f) for f in FIN}

        def ramp(x, c, bw):
            u = np.clip((x - (c - bw)) / (2 * bw), 0, 1)
            return u * u * (3 - 2 * u)
        all_chain_cols = [c for f in FIN for c in chains[f][3]]
        for k, f in enumerate(FIN):
            best_d, best_s, seglen, cols = chains[f]
            sel = (owner == k) & (best_s > (-0.02 if f == "thumb" else -0.015)) & (best_d < 0.03)
            rows = cand[sel]; bs = best_s[sel]
            prox = bi[f"{f}_metacarpal_{s}"] if f != "thumb" else bi[f"hand_{s}"]
            joints_s = [0.0, seglen[0], seglen[0] + seglen[1]]
            bw0 = 0.012 if f == "thumb" else 0.006
            a1 = ramp(bs, joints_s[0], bw0); a2 = ramp(bs, joints_s[1], 0.003); a3 = ramp(bs, joints_s[2], 0.003)
            old = W[rows].copy()
            keep_total = np.clip(old[:, hand_cols].sum(axis=1), 0, 1)
            mc_h = old[:, prox]; hd_h = old[:, bi[f"hand_{s}"]]
            frac = np.where(mc_h + hd_h > 0, mc_h / np.maximum(mc_h + hd_h, 1e-9), 1.0) if f != "thumb" else np.ones(len(rows))
            W[np.ix_(rows, hand_cols)] = 0.0
            W[rows, cols[0]] = keep_total * (a1 - a2)
            W[rows, cols[1]] = keep_total * (a2 - a3)
            W[rows, cols[2]] = keep_total * a3
            pw = keep_total * (1 - a1)
            W[rows, prox] += pw * frac
            W[rows, bi[f"hand_{s}"]] += pw * (1 - frac)
            fing_report[f] = {"verts": int(len(rows)), "seg_mm": [round(x * 1000, 1) for x in seglen]}
        # palm vertices that were not claimed by a finger keep no finger-chain weights
        claimed = np.zeros(nv, dtype=bool)
        for k, f in enumerate(FIN):
            best_d, best_s, seglen, cols = chains[f]
            claimed[cand[(owner == k) & (best_s > (-0.02 if f == "thumb" else -0.015)) & (best_d < 0.03)]] = True
        rest_rows = cand[~claimed[cand]]
        moved = W[np.ix_(rest_rows, all_chain_cols)].sum(axis=1)
        W[np.ix_(rest_rows, all_chain_cols)] = 0.0
        W[rest_rows, bi[f"hand_{s}"]] += moved
        # soften the palm / knuckle / thumb-web transitions (the shafts beyond the PIP stay crisp)
        fixed = np.zeros(nv, dtype=bool)
        for k, f in enumerate(FIN):
            best_d, best_s, seglen, cols = chains[f]
            sel = (owner == k) & (best_s > seglen[0] - 0.004)
            fixed[cand[sel]] = True
        mask = np.zeros(nv, dtype=bool); mask[cand] = True; mask &= ~fixed
        W = smooth_weights(W, adj, mask, 4, 0.5)
    report["finger_rebuild"] = fing_report
    # nails ride rigidly on the distal phalanx / the toes (a nail split between two bones tears off in a fist)
    for s in ("l", "r"):
        rows = np.nonzero((region == "arm_" + s) & np.array(["Fingernails" in vs for vs in vsrc]))[0]
        tipsd = {f: np.array(ends[f"{f}_03_{s}"]) for f in FIN}
        for i in rows:
            f = min(FIN, key=lambda f: np.linalg.norm(X[i] - tipsd[f]))
            W[i] = 0.0; W[i, bi[f"{f}_03_{s}"]] = 1.0
        rows = np.nonzero((region == "leg_" + s) & np.array(["Toenails" in vs and len(vs) == 1 for vs in vsrc]))[0]
        W[rows] = 0.0; W[rows, bi[f"ball_{s}"]] = 1.0
    W = limit_normalize(W)
    zero = np.nonzero(W.sum(axis=1) == 0)[0]
    if len(zero):
        report["notes"].append(f"{len(zero)} verts lost all weights to the region rules -> copied from neighbours")
        for _ in range(20):
            for i in zero:
                nbw = W[adj[i]].sum(axis=0)
                if nbw.sum() > 0:
                    W[i] = nbw / nbw.sum()
            zero = np.nonzero(W.sum(axis=1) == 0)[0]
            if not len(zero):
                break
    # smoothing at the joints (heat weights are already smooth; one light pass everywhere except the fingers)
    fmask = np.array([not (region[i].startswith("arm") and W[i, [bi[n] for n in order if n.startswith(FIN)]].sum() > 0.5) for i in range(nv)])
    W = smooth_weights(W, adj, fmask, 2, 0.4)
    W = limit_normalize(W)
    W_posed = W.copy()

    # left hand = rigid in the posed bind (replaced by the mirrored right hand afterwards); right foot likewise
    lh = [bi[n] for n in order if n.endswith("_l") and (n.startswith(FIN))]
    W_bind = W.copy()
    W_bind[:, bi["hand_l"]] += W_bind[:, lh].sum(axis=1); W_bind[:, lh] = 0
    W_bind[:, bi["foot_r"]] += W_bind[:, bi["ball_r"]]; W_bind[:, bi["ball_r"]] = 0

    # ------------------------------------------------ posed -> A
    def transforms(R, hA):
        Tm = np.zeros((len(order), 3, 3)); Tt = np.zeros((len(order), 3))
        for n in order:
            Rt = np.array(R[n].transposed())
            Tm[bi[n]] = Rt
            Tt[bi[n]] = np.array(hA[n]) - Rt @ np.array(Pp[n])
        return Tm, Tt
    Tm, Tt = transforms(R, hA)
    XA = lbs(X, W_bind, Tm, Tt)

    # ------------------------------------------------ flatten the left sole (rotate the foot subtree about the ankle)
    def sole_tilt(XA, s):
        rows = np.nonzero(region == "leg_" + s)[0]
        fw = W_bind[rows][:, [bi[f"foot_{s}"], bi[f"ball_{s}"]]].sum(axis=1)
        foot = rows[fw > 0.6]
        P = XA[foot]
        ank = np.array(hA[f"foot_{s}"]); ball = np.array(hA[f"ball_{s}"])
        heel = P[P[:, 1] > ank[1] - 0.01]
        fore = P[np.abs(P[:, 1] - ball[1]) < 0.025]
        hz = np.percentile(heel[:, 2], 1.0); fz = np.percentile(fore[:, 2], 1.0)
        return hz, fz, abs(ball[1] - (heel[:, 1].mean()))
    for it in range(3):
        hz, fz, L = sole_tilt(XA, "l")
        phi = math.atan2(hz - fz, L)  # heel higher -> rotate toes down/heel down about lateral axis
        report.setdefault("sole_fix", []).append({"heel_z": round(hz, 4), "ball_z": round(fz, 4), "phi_deg": round(math.degrees(phi), 2)})
        if abs(phi) < math.radians(0.5):
            break
        rot = Matrix.Rotation(-phi, 3, Vector((1, 0, 0)))
        piv = hA["foot_l"].copy()
        for n in ("foot_l", "ball_l"):
            hA[n] = piv + rot @ (hA[n] - piv)
            R[n] = R[n] @ rot.transposed()
        Tm, Tt = transforms(R, hA)
        XA = lbs(X, W_bind, Tm, Tt)
    # the right foot / ball follow the (mirrored) left
    d = hA["ball_l"] - hA["foot_l"]
    hA["ball_r"] = hA["foot_r"] + Vector((-d.x, d.y, d.z))

    # ------------------------------------------------ mirror map + hand / foot replacement
    def cx_fn(z):
        return 0.0
    # torso centre line in the posed shell (x of the torso slice centre ~ -0.007 .. -0.03): estimate per height
    zs = np.linspace(0.9, 1.4, 11)
    body_v = np.nonzero(region == "body")[0]
    cxs = []
    for z in zs:
        sel = body_v[np.abs(X[body_v, 2] - z) < 0.01]
        cxs.append((X[sel, 0].min() + X[sel, 0].max()) / 2 if len(sel) else 0.0)

    def cx_fn(z):  # noqa
        return float(np.interp(z, zs, cxs))
    t1 = time.time()
    mm = mirror_map(me, cx_fn)
    assert mm is not None, "no consistent topological mirror found"
    mv = np.array(mm[1])
    report["mirror"] = {"median_err_m": mm[0], "self_mapped": int((mv == np.arange(nv)).sum()), "secs": round(time.time() - t1, 1)}
    log("mirror map", report["mirror"])
    perm = np.array([bi[other(n)] for n in order])  # column permutation l <-> r

    def replace(dst_side, src_side, groups, ramp, along=None, pivot="hand"):
        """Region of dst_side = mirror of src_side region, weights mirrored, blended by the source group weight
        (or, with along=(bone_a, bone_b), by the position along that segment in the A-pose, so any twist difference
        between the two sides is spread over the whole segment instead of making a seam)."""
        src_rows = np.nonzero(np.array([str(r).endswith("_" + src_side) for r in region]))[0]
        cols = [bi[g + "_" + src_side] for g in groups]
        dst_rows = mv[src_rows]
        a = np.clip((W_posed[src_rows][:, cols].sum(axis=1) - ramp[0]) / (ramp[1] - ramp[0]), 0, 1)
        if along:
            pa = np.array(hA[along[0] + "_" + src_side]); pb = np.array(hA[along[1] + "_" + src_side])
            d = pb - pa
            t = ((XA[src_rows] - pa) @ d) / (d @ d)
            lw = W_posed[src_rows][:, [bi[along[0] + "_" + src_side]]].sum(axis=1)
            ta = np.clip((t - ramp[0]) / (ramp[1] - ramp[0]), 0, 1)
            a = np.maximum(a * (a >= 1), np.where(lw + W_posed[src_rows][:, cols].sum(axis=1) > 0.5, ta, 0.0))
        a = a * a * (3 - 2 * a)
        # mirror about the pivot joints (the skeleton is only symmetric in its bone lengths, not in absolute x)
        ps = np.array(hA[pivot + "_" + src_side]); pd = np.array(hA[pivot + "_" + dst_side])
        mirrored = pd + (XA[src_rows] - ps) * np.array([-1, 1, 1])
        XA[dst_rows] = (1 - a[:, None]) * XA[dst_rows] + a[:, None] * mirrored
        Wm = W_posed[src_rows][:, perm]
        Wfinal[dst_rows] = (1 - a[:, None]) * Wfinal[dst_rows] + a[:, None] * Wm
        return int((a > 0).sum()), int((a >= 1).sum())
    Wfinal = W_posed.copy()
    # hand groups: hand + metacarpals + fingers
    hand_groups = ["hand"] + [f"{f}_metacarpal" for f in FIN[1:]] + [f"{f}_0{k}" for f in FIN for k in (1, 2, 3)]
    report["left_hand_from_right"] = replace("l", "r", hand_groups, (0.10, 0.90), along=("lowerarm", "hand"))
    report["right_foot_from_left"] = replace("r", "l", ["foot", "ball"], (0.10, 0.80), pivot="foot")
    # the right foot keeps its own weights where it was not replaced; left hand bind weights are now mirrored ones
    Wfinal = limit_normalize(Wfinal)

    # ------------------------------------------------ floor
    feet = np.nonzero((region == "leg_l") | (region == "leg_r"))[0]
    fz = XA[feet, 2].min()
    shift = np.array([0.0, 0.0, -fz])
    XA += shift
    for n in order:
        hA[n] = hA[n] + Vector(shift)
    report["floor_shift_m"] = float(-fz)

    # write skin coords + weights
    for v, c in zip(me.vertices, XA):
        v.co = Vector(c)
    write_weights(skin, Wfinal, order)
    report["skin_max_influences"] = int((Wfinal > 0).sum(axis=1).max())
    report["skin_mean_influences"] = float((Wfinal > 0).sum(axis=1).mean())

    # ------------------------------------------------ head parts (rigid head) + garments
    hp = bpy.data.objects["SK_2B_HeadParts"]
    Rt = R["head"].transposed()
    for v in hp.data.vertices:
        v.co = Rt @ (v.co - Pp["head"]) + hA["head"]
    hp.vertex_groups.clear()
    g = hp.vertex_groups.new(name="head"); g.add(list(range(len(hp.data.vertices))), 1.0, 'REPLACE')
    gar = bpy.data.objects["SK_2B_Garments"]
    gme = gar.data
    gX = np.array([list(v.co) for v in gme.vertices])
    under_i = [i for i, m in enumerate(gme.materials) if m.name == "M_2B_Underwear"][0]
    uv_set = set()
    for p in gme.polygons:
        if p.material_index == under_i:
            uv_set.update(p.vertices)
    skin_vert = np.zeros(len(gme.vertices), dtype=int)
    gme.attributes["skin_vert"].data.foreach_get("value", skin_vert)
    tree = BVHTree.FromPolygons([Vector(x) for x in X], [tuple(p.vertices) for p in me.polygons])
    GW = np.zeros((len(gme.vertices), len(order)))
    polys = [tuple(p.vertices) for p in me.polygons]
    for i in range(len(gme.vertices)):
        if i in uv_set or skin_vert[i] < 0:
            loc, nrm, fi, d = tree.find_nearest(Vector(gX[i]))
            vs = polys[fi]
            # barycentric weights of the nearest point in the nearest (quad -> 2 tris) skin face (posed space)
            import mathutils.geometry as mg
            cs = [Vector(X[v]) for v in vs]
            tri = (0, 1, 2) if len(vs) == 3 else min(((0, 1, 2), (0, 2, 3)), key=lambda t: (mg.closest_point_on_tri(loc, cs[t[0]], cs[t[1]], cs[t[2]]) - loc).length)
            a, b, c = (cs[k] for k in tri)
            v0, v1, v2 = b - a, c - a, loc - a
            d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
            den = max(d00 * d11 - d01 * d01, 1e-18)
            wb = (d11 * d20 - d01 * d21) / den; wc = (d00 * d21 - d01 * d20) / den; wa = 1 - wb - wc
            bw = np.clip(np.array([wa, wb, wc]), 0, 1); bw /= bw.sum()
            GW[i] = (W_bind[[vs[k] for k in tri]] * bw[:, None]).sum(axis=0)
        else:
            GW[i] = W_bind[skin_vert[i]]
    # the bandeau should not ride up with the arms: damp its upper-arm share (skin there keeps its own weights)
    # (only at the sides / armpits; the front edge keeps the skin weights so the chest does not push through it)
    top_rows = np.array([i not in uv_set for i in range(len(gme.vertices))])
    side_rows = top_rows & (np.abs(gX[:, 0] - float(np.median(gX[top_rows, 0]))) > 0.085)
    for s in ("l", "r"):
        GW[side_rows, bi[f"upperarm_{s}"]] *= 0.35
    GW = limit_normalize(GW)
    gXA = lbs(gX, GW, Tm, Tt) + shift
    # right half of the bandeau re-cut as the mirror of the clean left half (verifier fix, see rebuild_top_right)
    gXA, GW, new_side, uv_set, top_anchor = rebuild_top_right(gme, gXA, GW, side_rows, under_i, XA, polys, Wfinal, mv, report)
    for s in ("l", "r"):
        GW[new_side, bi[f"upperarm_{s}"]] *= 0.35
    GW = limit_normalize(GW)
    # garments follow the final (post-replacement) skin: none of them reach the hands/feet, so the bind weights are the
    # final ones; push out anything that ended within 1 mm of (or inside) the A-pose skin
    treeA = BVHTree.FromPolygons([Vector(x) for x in XA], polys)
    # no garment push-out (it snaps edge / lip vertices onto the skin and saw-tooths the edges); the skin is sunk
    # under the garments instead (below). Count how many garment verts end up inside the skin for the report.
    inside = 0
    for i in range(len(gXA)):
        p = Vector(gXA[i])
        loc, nrm, fi, d = treeA.find_nearest(p)
        vs = polys[fi]
        fn = (Vector(XA[vs[1]]) - Vector(XA[vs[0]])).cross(Vector(XA[vs[2]]) - Vector(XA[vs[0]])).normalized()
        if (p - loc).dot(fn) < 0.0005:
            inside += 1
    report["garment_verts_within_0.5mm_of_skin_before_sink"] = inside
    for v, c in zip(gme.vertices, gXA):
        v.co = Vector(c)
    # the garments are much coarser than the skin: sink any skin that still reaches within 1.2 mm of a garment
    # surface (only where skin and garment face the same way, so the top's rolled edge never dents the skin)
    gpolys = [tuple(p.vertices) for p in gme.polygons]
    gtree = BVHTree.FromPolygons([Vector(c) for c in gXA], gpolys)
    gbm = bmesh.new(); gbm.from_mesh(gme)
    bpts = [Vector(gXA[v.index]) for v in gbm.verts if v.is_boundary]
    gbm.free()
    gb_tree = KDTree(len(bpts))
    for k, q in enumerate(bpts):
        gb_tree.insert(q, k)
    gb_tree.balance()

    class _B:
        def find_nearest(self, p):
            co, idx, d = gb_tree.find(p)
            return co, None, idx, d
    gb_tree_q = _B()
    me.update()
    sunk = 0
    under_top_side = []
    for v in me.vertices:
        p = v.co
        loc, gn, fi, d = gtree.find_nearest(p, 0.008)
        if loc is None:
            continue
        vs = gpolys[fi]
        fn = (Vector(gXA[vs[1]]) - Vector(gXA[vs[0]])).cross(Vector(gXA[vs[2]]) - Vector(gXA[vs[0]])).normalized()
        if fn.dot(v.normal) < 0.6:
            continue
        sd = (p - loc).dot(fn)
        # deeper inside the garment footprint (skin is hidden there), 2 mm near the garment edges
        depth = 0.003 if gb_tree_q.find_nearest(loc)[3] > 0.006 else 0.002
        if sd > -depth:
            v.co = p + fn * (-depth - sd)
            sunk += 1
        if gme.polygons[fi].material_index != under_i and abs(p.x) > 0.085:
            under_top_side.append(v.index)
    report["skin_verts_sunk_under_garments"] = sunk
    # the skin under the bandeau's sides gets the same damped upper-arm share as the bandeau, so the two move together
    for s in ("l", "r"):
        Wfinal[under_top_side, bi[f"upperarm_{s}"]] *= 0.35
    Wfinal = limit_normalize(Wfinal)
    # face skin rigid on the head like the eyes / teeth / lashes (verifier fix, see rigid_face)
    coA = np.array([list(v.co) for v in me.vertices])
    hp_coA = np.array([list(v.co) for v in hp.data.vertices])
    Wfinal = limit_normalize(rigid_face(Wfinal, order, bi, vsrc, region, adj, coA, hp_coA, np.array(hA["head"]), report))
    write_weights(skin, Wfinal, order)
    report["skin_max_influences"] = int((Wfinal > 0).sum(axis=1).max())
    report["skin_mean_influences"] = float((Wfinal > 0).sum(axis=1).mean())
    report["skin_verts_under_top_sides_damped"] = len(under_top_side)
    # the rebuilt right half of the bandeau takes the FINAL weights of the skin vertex under it (after the side damping
    # above), so band and skin move together at her right armpit (the source-pose left half keeps its exact copies)
    cp = top_anchor >= 0
    GW[cp] = Wfinal[top_anchor[cp]]
    GW = limit_normalize(GW)
    write_weights(gar, GW, order)

    # ------------------------------------------------ 168 cm standing height
    # step A scaled the POSED skin to 1.68 m while she stood on tiptoe with a bent knee and a lowered head; flat-footed
    # in the A-pose she measures ~1.635 m, so everything is scaled uniformly about the floor origin to 1.68 m again
    top = max(v.co.z for v in me.vertices)
    k = TARGET_HEIGHT / top
    for o in (skin, hp, gar):
        for v in o.data.vertices:
            v.co = v.co * k
    for n in order:
        hA[n] = hA[n] * k
    report["uniform_scale_to_168cm"] = {"height_before_m": round(top, 4), "scale": round(k, 5)}

    # ------------------------------------------------ final armature rest = MH orientation at HER A-pose joints
    root = bpy.data.objects["root"]
    bpy.context.view_layer.objects.active = root
    for o in bpy.context.view_layer.objects:
        o.select_set(o == root)
    bpy.ops.object.mode_set(mode='EDIT')
    for n in order:
        eb = root.data.edit_bones[n]
        L = S["mh_taillen"][n] * 0.9
        eb.matrix = Matrix.Translation(hA[n]) @ Q[n].to_4x4()
        eb.length = L
    bpy.ops.object.mode_set(mode='OBJECT')
    # check: rest orientation equals MH exactly
    dev = max(math.degrees(root.data.bones[n].matrix_local.to_3x3().normalized().to_quaternion()
                           .rotation_difference(Q[n].to_quaternion()).angle) for n in order)
    report["rest_orientation_max_dev_from_MH_deg"] = dev
    for o in (skin, hp, gar):
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
        m = o.modifiers.new("Armature", 'ARMATURE'); m.object = root; m.use_vertex_groups = True; m.use_bone_envelopes = False
    wgt = bpy.data.objects.get("WGT_Posed")
    if wgt:
        d = wgt.data; bpy.data.objects.remove(wgt, do_unlink=True); bpy.data.armatures.remove(d)
    save_json(WORK + "/c1_apose_report.json", report)
    save_json(WORK + "/c1_apose_skeleton.json", {n: list(hA[n]) for n in order})
    bpy.ops.wm.save_as_mainfile(filepath=RIG_BLEND, compress=True)
    log("saved", RIG_BLEND, round(time.time() - t0, 1), "s", json.dumps(report)[:1500])


main()
