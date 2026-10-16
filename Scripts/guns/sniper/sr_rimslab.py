"""(Realism R2) edge radii built into the generator: the "rim slab".

Round 1 rounded the chassis / butt / riser / grip with an unclamped weighted bevel plus exclusion boxes; it tore
slivers wherever the round overlapped itself (judges: torn grip base, jagged riser and pad edges, zig-zag forend nose,
wavy chassis underside). The rim slab never runs a bevel:

1. side-view CSG in 2D (the traced rings, boxes and seat cuts united / subtracted as thin prisms with the exact solver,
   then the +Y face's boundary read back), so seams between traced pieces vanish before any 3D work;
2. the outline faired (Gaussian, real corners pinned), then every corner filleted with a radius larger than the rim
   radius (so the inward offsets below stay simple polygons; checked per ring);
3. rings: per-edge offsets of the outline by r(1 - sin phi) at y = W - r + r cos(phi) (phi 0..90 deg in `seg` steps),
   one vertex per outline vertex, mirrored to -y and lofted; joint edges (a predicate) take offset 0, so a joint face
   stays flat and sharp; the side caps are scanline-filled (holes allowed);
4. the plan width as a shear: each side's vertices move by h(x, z) - W along y; the caps are bisected at the plan
   breakpoints first (the outline already carries vertices there), so every cap strip stays planar.

Each ring is a 1:1 offset of a curvature-limited outline: no ring can fold, so no torn slivers or steps can appear.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import bl
from gunlib import geo2d as G
from gunlib import mesh as MS


# ------------------------------------------------------------------------------------------------ 2D
def rect(x0, x1, z0, z1):
    return np.array([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], float)


def csg2d(adds, subs=(), tag="csg"):
    """Side-view polygon CSG through Blender's exact boolean on thin XZ prisms. Returns [outer, holes...] (outer CCW,
    holes CW), mm (x, z), collinear points dropped."""
    import bpy
    import bmesh
    coll = bpy.context.scene.collection
    ob = MS.prism(G.ccw(np.asarray(adds[0], float)), -1.0, 1.0).to_object("_csg_" + tag, coll, (0, 0, 0), None)
    if len(adds) > 1:
        bl.boolean_many(ob, [MS.prism(G.ccw(np.asarray(a, float)), -1.0, 1.0) for a in adds[1:]], "UNION")
    if subs:
        bl.boolean_many(ob, [MS.prism(G.ccw(np.asarray(s, float)), -2.0, 2.0) for s in subs], "DIFFERENCE")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    top = {f for f in bm.faces if f.normal.y > 0.999 and abs(f.calc_center_median().y * 1000.0 - 1.0) < 1e-3}
    bnd = [e for e in bm.edges if sum(1 for f in e.link_faces if f in top) == 1]
    adj = {}
    for e in bnd:
        a, b = e.verts
        adj.setdefault(a.index, []).append(b.index)
        adj.setdefault(b.index, []).append(a.index)
    co = {v.index: (v.co.x * 1000.0, v.co.z * 1000.0) for v in bm.verts}
    seen, loops = set(), []
    for s in adj:
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            nx = [n for n in adj[cur] if n != prev and (n not in seen or (n == s and len(loop) > 2))]
            if not nx or nx[0] == s:
                break
            prev, cur = cur, nx[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(np.array([co[i] for i in loop], float))
    bm.free()
    bpy.data.objects.remove(ob, do_unlink=True)
    loops = [G.dp_simplify(L, 0.01) for L in loops if len(L) >= 3]
    loops.sort(key=lambda L: -abs(G.area(L)))
    out = [G.ccw(loops[0])] + [G.ccw(L)[::-1] for L in loops[1:]]
    return out


def hull(P):
    """2D convex hull (monotone chain), CCW."""
    pts = sorted(set(map(tuple, np.round(np.asarray(P, float), 6))))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1], float)


def lower_hull_run(P, x0, x1, zmax):
    """Replace the outline's bottom run inside x0..x1 (vertices under zmax, one contiguous run) by its lower convex
    hull: bumps the trace put on a convex belly go, the end points stay."""
    P = np.asarray(P, float)
    m = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] < zmax)
    idx = np.nonzero(m)[0]
    if len(idx) < 3:
        return P
    k = int(np.argmax(np.diff(np.r_[idx, idx[0] + len(P)])))     # rotate so the run is contiguous
    P = np.roll(P, -(idx[(k + 1) % len(idx)]), 0)
    m = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] < zmax)
    idx = np.nonzero(m)[0]
    if not np.all(np.diff(idx) == 1):
        return P
    run = P[idx]
    order = np.argsort(run[:, 0])
    pts = run[order]
    lo = []
    for p in pts:
        while len(lo) >= 2 and ((lo[-1][0] - lo[-2][0]) * (p[1] - lo[-2][1]) - (lo[-1][1] - lo[-2][1]) * (p[0] - lo[-2][0])) <= 0:
            lo.pop()
        lo.append(p)
    lo = np.array(lo)
    if run[0, 0] > run[-1, 0]:
        lo = lo[::-1]
    return np.vstack([P[:idx[0]], lo, P[idx[-1] + 1:]])


def fillet_adaptive(P, rc, keep=None):
    """Round every corner turning more than 12 deg with radius rc (tangent clamped to 45 % of the shorter edge), arc
    segments <= 22.5 deg so the inner rings' chords stay > 0.05 mm. keep: vertex mask left sharp (joint corners)."""
    P = np.asarray(P, float)
    n = len(P)
    out = []
    for i in range(n):
        if keep is not None and keep[i]:
            out.append(P[i])
        else:
            out.extend(_corner(P[i - 1], P[i], P[(i + 1) % n], rc))
    return _dedupe(np.array(out), 0.05)


def _dedupe(P, tol):
    keep = [P[0]]
    for p in P[1:]:
        if np.linalg.norm(p - keep[-1]) >= tol:
            keep.append(p)
    if len(keep) > 2 and np.linalg.norm(keep[0] - keep[-1]) < tol:
        keep.pop()
    return np.array(keep)


def _turns(P):
    E = np.roll(P, -1, 0) - P
    Ein = np.roll(E, 1, 0)
    a = np.arctan2(E[:, 1], E[:, 0]) - np.arctan2(Ein[:, 1], Ein[:, 0])
    return np.degrees((a + np.pi) % (2 * np.pi) - np.pi)


def destep(P, lmax, keep=None, rounds=200):
    """Remove outline features smaller than the rim can turn round: a step (an edge shorter than lmax between two
    > 30 deg turns of opposite sign) becomes one vertex at the edge's midpoint; a spike / notch (a > 100 deg turn with
    both edges shorter than lmax) loses its vertex. keep(p) -> True protects a vertex (joint corners)."""
    P = np.asarray(P, float)
    n_done = 0
    for _ in range(rounds):
        n = len(P)
        if n < 5:
            break
        T = _turns(P)
        E = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
        hit = None
        for i in range(n):
            j = (i + 1) % n
            if keep is not None and (keep(P[i]) or keep(P[j])):
                continue
            if E[i] < lmax and abs(T[i]) > 30 and abs(T[j]) > 30 and T[i] * T[j] < 0:
                hit = ("step", i, j)
                break
            if abs(T[i]) > 100 and E[i] < lmax and E[i - 1] < lmax:
                hit = ("spike", i, None)
                break
        if hit is None:
            break
        kind, i, j = hit
        if kind == "step":
            mid = 0.5 * (P[i] + P[j])
            P = np.array([mid if q == i else P[q] for q in range(n) if q != j])
        else:
            P = np.delete(P, i, 0)
        n_done += 1
    return P


def prep(P, sigma=1.5, corner=40.0, rc=2.0, dp=0.2, joint=None, step=None):
    """Fair (corners pinned), DP, fillet. Corners touching a joint edge (predicate on the two end points) stay sharp."""
    P = np.asarray(P, float)
    if sigma > 0:
        P = G.clean_smooth(P, step=1.0, sigma_mm=max(sigma, 0.6 * rc), corner_deg=corner)
    P = G.ccw(G.dp_simplify(P, dp))
    if step:
        jpt = None
        if joint is not None:
            JP = [P[i] for i in range(len(P)) for q in (i - 1, i) if joint(P[q], P[(q + 1) % len(P)])]
            jpt = (lambda p: any(np.linalg.norm(p - q) < 1e-6 for q in JP)) if JP else None
        P = G.ccw(destep(P, step, jpt))
    n = len(P)
    jv = np.zeros(n, bool)
    if joint is not None:
        for i in range(n):
            if joint(P[i], P[(i + 1) % n]):
                jv[i] = jv[(i + 1) % n] = True
    return G.ccw(fillet_adaptive(P, rc, jv))


def _corner(a, b, c, rc, pin_deg=12.0, step_deg=22.5):
    u, v = a - b, c - b
    lu, lv = np.linalg.norm(u), np.linalg.norm(v)
    if lu < 1e-9 or lv < 1e-9:
        return [b]
    u, v = u / lu, v / lv
    ang = math.acos(float(np.clip(u @ v, -1, 1)))
    if math.degrees(math.pi - ang) < pin_deg:
        return [b]
    r = rc
    t = r / math.tan(ang / 2)
    tmax = 0.45 * min(lu, lv)
    if t > tmax:
        t = tmax
        r = t * math.tan(ang / 2)
    bis = (u + v) / np.linalg.norm(u + v)
    ctr = b + bis * (r / math.sin(ang / 2))
    p0, p1 = b + u * t, b + v * t
    a0 = math.atan2(*(p0 - ctr)[::-1])
    a1 = math.atan2(*(p1 - ctr)[::-1])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    seg = max(1, int(math.ceil(abs(math.degrees(da)) / step_deg)))
    return [ctr + r * np.array([math.cos(a0 + da * k / seg), math.sin(a0 + da * k / seg)]) for k in range(seg + 1)]


def insert_breaks(P, xs=(), zs=(), tol=0.3):
    """Add outline vertices where an edge crosses x = xb or z = zb (unless a vertex is already within tol)."""
    P = np.asarray(P, float)
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        out.append(a)
        pts = []
        for ax, vals in ((0, xs), (1, zs)):
            for q in vals:
                if (a[ax] - q) * (b[ax] - q) < 0:
                    t = (q - a[ax]) / (b[ax] - a[ax])
                    p = a + t * (b - a)
                    if np.linalg.norm(p - a) > tol and np.linalg.norm(p - b) > tol:
                        pts.append((t, p))
        out.extend(p for _, p in sorted(pts, key=lambda tp: tp[0]))
    return np.array(out)


def offset_edges(P, d, jmask):
    """Per-edge offset of a closed ring (CCW outer / CW hole: the right-hand normal points out of the material);
    edges with jmask True offset 0 (joint faces), the others by d (negative = into the material)."""
    n = len(P)
    E = np.roll(P, -1, 0) - P
    L = np.maximum(np.linalg.norm(E, axis=1), 1e-12)
    N = np.c_[E[:, 1], -E[:, 0]] / L[:, None]
    D = np.where(jmask, 0.0, d)
    out = np.empty_like(P)
    for i in range(n):
        j = i - 1                                   # incoming edge j, outgoing edge i
        n0, n1 = N[j], N[i]
        c0 = n0 @ P[i] + D[j]
        c1 = n1 @ P[i] + D[i]
        det = n0[0] * n1[1] - n0[1] * n1[0]
        if abs(det) < 1e-6:
            out[i] = P[i] + n1 * D[i]
            continue
        q = np.array([(c0 * n1[1] - c1 * n0[1]) / det, (n0[0] * c1 - n1[0] * c0) / det])
        lim = 3.0 * max(abs(D[j]), abs(D[i]))
        dq = q - P[i]
        if np.linalg.norm(dq) > lim > 0:
            q = P[i] + dq / np.linalg.norm(dq) * lim
        out[i] = q
    return out


def unfold(R, rounds=40):
    """Swallowtail cleanup of an offset ring, vertex count kept (the loft stays 1:1): the vertices of the shorter
    span of a self-intersection go to the crossing point, spread 0.06 mm along the ring (UD1 edges >= 0.05 mm)."""
    R = np.array(R, float)
    n = len(R)
    k = 0
    for k in range(rounds):
        w = _first_cross(R)
        if w is None:
            return R, k
        i, j = w
        f = j - i                                      # forward span i+1..j
        span = list(range(i + 1, j + 1)) if f <= n - f else [q % n for q in range(j + 1, i + n + 1)]
        a, b = R[i], R[(i + 1) % n]
        c, d = R[j], R[(j + 1) % n]
        den = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
        t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / den if abs(den) > 1e-12 else 0.5
        X = a + t * (b - a)
        lo, hi = R[(span[0] - 1) % n], R[(span[-1] + 1) % n]
        u = hi - lo
        u = u / max(np.linalg.norm(u), 1e-12)
        m = len(span)
        for q, vi in enumerate(span):
            R[vi] = X + (q - (m - 1) / 2.0) * 0.06 * u
    return R, k


def _first_cross(A):
    B = np.roll(A, -1, 0)
    n = len(A)

    def orient(p, q, r):
        return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
    for i in range(n):
        j = np.arange(i + 2, n)
        if i == 0:
            j = j[j != n - 1]
        if not len(j):
            continue
        hit = (orient(A[i], B[i], A[j]) * orient(A[i], B[i], B[j]) < 0) &               (orient(A[j], B[j], A[i][None]) * orient(A[j], B[j], B[i][None]) < 0)
        if np.any(hit):
            return i, int(j[hit][0])
    return None


def simple(P, where=False):
    """True when a closed polygon has no self-intersections (vectorised segment test)."""
    A = np.asarray(P, float)
    B = np.roll(A, -1, 0)
    n = len(A)

    def orient(p, q, r):
        return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])
    for i in range(n):
        j = np.arange(i + 2, n)
        if i == 0:
            j = j[j != n - 1]
        if not len(j):
            continue
        o1 = orient(A[i], B[i], A[j])
        o2 = orient(A[i], B[i], B[j])
        o3 = orient(A[j], B[j], A[i][None])
        o4 = orient(A[j], B[j], B[i][None])
        hit = (o1 * o2 < 0) & (o3 * o4 < 0)
        if np.any(hit):
            return False if not where else (A[i].round(2).tolist(), A[j[hit][0]].round(2).tolist())
    return True


# ------------------------------------------------------------------------------------------------ 3D
def slab_object(name, coll, loops, W, r, seg, offset_mm, hfun=None, breaks_x=(), breaks_z=(), joint=None,
                smooth_deg=40.0, report=None):
    """The rim slab as a Blender object (vertices (mm - offset_mm) * 0.001). loops: [outer CCW, holes CW] in (x, z).
    hfun(x, z) -> half-width (mm) for the plan shear; W the nominal half-width the rings are built at."""
    import bpy
    import bmesh
    off = np.asarray(offset_mm, float)
    bm = bmesh.new()
    phis = np.linspace(0.0, math.pi / 2, seg + 1)
    rep = {"rings_simple": True, "loops": len(loops), "ring_verts": [len(L) for L in loops]}
    cap_loops = {1: [], -1: []}
    brk_by_loop, loops2d = [], [np.asarray(L, float) for L in loops]
    for L in loops:
        L = np.asarray(L, float)
        n = len(L)
        jm = np.array([bool(joint(L[i], L[(i + 1) % n])) if joint else False for i in range(n)])
        rings2d = [offset_edges(L, -r * (1.0 - math.sin(p)), jm) for p in phis]
        # plan breakpoints: the outline's break vertices sit on straight edges, so on every ring they stay on the offset
        # line; slide each to the exact X (Z) of its break so the cap strips between breaks are planar after the shear
        brk = []
        for i in range(n):
            for ax, vals in ((0, breaks_x), (1, breaks_z)):
                for q in vals:
                    if abs(L[i, ax] - q) < 1e-6:
                        brk.append((i, ax, q))
        ok = []
        for i, ax, q in brk:                     # snap only where every ring moves < 0.3 mm (else no constraint)
            mv = []
            for R in rings2d:
                d = R[(i + 1) % n] - R[i - 1]
                mv.append(d * ((q - R[i, ax]) / d[ax]) if abs(d[ax]) > 1e-9 else np.array([9.0, 9.0]))
            if max(np.linalg.norm(m) for m in mv) < 0.3:
                for R, m in zip(rings2d, mv):
                    R[i] = R[i] + m
                ok.append((i, ax, q))
        rep["breaks_snapped"] = rep.get("breaks_snapped", 0) + len(ok)
        rep["breaks_skipped"] = rep.get("breaks_skipped", 0) + len(brk) - len(ok)
        brk_by_loop.append(ok)
        for q in range(len(rings2d) - 1):
            w = simple(rings2d[q], where=True)
            if w is not True:
                rings2d[q], nfix = unfold(rings2d[q])
                rep.setdefault("ring_folds_fixed", []).append([q, w, nfix])
                if simple(rings2d[q]) is not True:
                    rep["rings_simple"] = False
        ys = [W - r + r * math.cos(p) for p in phis]
        seq = [(R, y) for R, y in zip(rings2d, ys)] + [(R, -y) for R, y in zip(rings2d[::-1], ys[::-1])]
        vr = []
        for R, y in seq:
            vr.append([bm.verts.new(((R[k, 0] - off[0]) * 1e-3, (y - off[1]) * 1e-3, (R[k, 1] - off[2]) * 1e-3))
                       for k in range(n)])
        for a, b in zip(vr[:-1], vr[1:]):
            for k in range(n):
                k2 = (k + 1) % n
                if len({a[k], a[k2], b[k2], b[k]}) == 4:
                    bm.faces.new((a[k], a[k2], b[k2], b[k]))
        cap_loops[1].append(vr[0])
        cap_loops[-1].append(vr[-1])
    # side caps: constrained Delaunay (outer + hole loops; max-min-angle, so no needle ears between near-collinear
    # boundary vertices: the scanline fill made them on the long faired runs)
    from mathutils import Vector as _V
    from mathutils.geometry import delaunay_2d_cdt
    for side in (1, -1):
        verts = [v for L in cap_loops[side] for v in L]
        co = [_V((v.co.x, v.co.z)) for v in verts]
        faces, o = [], 0
        for L in cap_loops[side]:
            faces.append(list(range(o, o + len(L))))
            o += len(L)
        cons = []
        for ax, vals in ((0, breaks_x), (1, breaks_z)):
            for q in vals:
                ids = [o_ + i for li, (o_, brk) in enumerate(zip(np.cumsum([0] + [len(L) for L in cap_loops[side]][:-1]),
                                                                 brk_by_loop)) for i, a_, q_ in brk if a_ == ax and q_ == q]
                ids.sort(key=lambda t: co[t][1 - ax])
                for a_, b_ in zip(ids[:-1], ids[1:]):
                    mid = 0.5 * (np.array(co[a_]) + np.array(co[b_])) * 1000.0 + off[[0, 2]]
                    if G.point_in_poly(mid, loops2d[0]) and not any(G.point_in_poly(mid, h) for h in loops2d[1:]):
                        cons.append((int(a_), int(b_)))
        out = delaunay_2d_cdt(co, cons, faces, 2, 1e-9, True)
        ov, of, orig = out[0], out[2], out[3]
        if len(ov) != len(co):
            rep["cdt_new_verts_%+d" % side] = len(ov) - len(co)
        mp = {}
        ycap = (side * W - off[1]) * 1e-3
        for i, ids in enumerate(orig):
            if ids:
                mp[i] = verts[ids[0]]
            else:                                # a crossing of two constraint lines: an interior cap vertex
                mp[i] = bm.verts.new((ov[i][0], ycap, ov[i][1]))
        made = 0
        for f in of:
            if all(i in mp for i in f) and len({mp[i] for i in f}) == 3:
                try:
                    bm.faces.new([mp[i] for i in f])
                    made += 1
                except ValueError:
                    pass
        rep["cap_tris_%+d" % side] = made
    # inner-ring chords under 0.05 mm (clamped fillets, squeezed folds) welded: moves <= 0.03 mm, UD1 edges >= 0.05
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=6e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    seen, dup = set(), []                       # the weld can fold two cap triangles onto the same three vertices
    for f in bm.faces:
        key = frozenset(v.index for v in f.verts)
        (dup.append(f) if key in seen else seen.add(key))
    if dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
        rep["dup_faces_removed"] = len(dup)
    if hfun is not None:
        y0 = (W - off[1]) * 1e-3
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        for v in bm.verts:
            x, y, z = v.co.x * 1e3 + off[0], v.co.y * 1e3 + off[1], v.co.z * 1e3 + off[2]
            s = 1.0 if y > 0 else -1.0
            v.co.y = (y + s * (hfun(x, z) - W) - off[1]) * 1e-3
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.set_sharp_from_angle(angle=math.radians(smooth_deg))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    rep["manifold"] = bl.manifold_report(ob)
    if report is not None:
        report.update(rep)
    return ob


def ud_locate(ob, offset_mm, cell=2.0, top=12):
    """Where an object's UD-failing triangles sit (gunlib's UD1 / UD2 rule), clustered on a cell-mm grid, frame M."""
    from gunlib import ud as _ud
    V, T = bl.tris_np(ob, offset_mm=tuple(np.asarray(offset_mm, float)))
    if not len(T):
        return []
    area, L, hgt, drop, _c = _ud._tri_metrics(V, T)
    bad = drop | (area < _ud.MIN_AREA_MM2) | (L.min(1) < _ud.MIN_EDGE_MM) | (hgt < _ud.MIN_HEIGHT_MM)
    if not bad.any():
        return []
    C = V[T[bad]].mean(1)
    keys, cnt = np.unique(np.round(C / cell) * cell, axis=0, return_counts=True)
    order = np.argsort(-cnt)[:top]
    return [(keys[i].round(1).tolist(), int(cnt[i])) for i in order]


def nonmanifold_locate(ob, offset_mm, cell=5.0, top=10):
    """Where an object's boundary / multi-face edges sit (frame M, cell-mm clusters)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    P = [((e.verts[0].co + e.verts[1].co) * 0.5) for e in bm.edges if len(e.link_faces) != 2]
    bm.free()
    if not P:
        return []
    C = np.array([p[:] for p in P]) * 1000.0 + np.asarray(offset_mm, float)
    keys, cnt = np.unique(np.round(C / cell) * cell, axis=0, return_counts=True)
    order = np.argsort(-cnt)[:top]
    return [(keys[i].round(1).tolist(), int(cnt[i])) for i in order]
