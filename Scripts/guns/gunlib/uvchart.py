"""Projection charts -> UV islands for gun parts built by booleans and bevels (numpy only; runs anywhere).

The katana's parts carried parametric UVs from their generators. Gun parts are boolean / bevel solids, so their UVs are
made after the build by a DETERMINISTIC rule per part, which every LOD of the part can re-apply (GUN_BUILDING_STUDY
4.5: "LOD1-3 reuse the islands"):

  box  a 3x3 frame (rows = the part's axes in the gun frame). A face goes to the chart of the axis its normal is most
       aligned with (6 charts); it is projected on that axis' plane with the in-plane axes chosen so U x V = the chart
       direction, so no island is ever mirrored. UV-up = gun-up on the four side charts.
  cyl  an axis (point c, direction w, seam reference u0): side faces (|n.r| >= 0.5) unwrap to (theta r, t) (inward
       faces mirrored back by -theta), caps (|n.w| >= 0.7) project along w, the rest (radial walls of slots and
       vents) fall back to a box chart in the (u0, w x u0, w) frame.

Islands are the faces connected through shared edges with the same chart, the same texel class and equal UVs on both
edge ends (the cylinder seam splits). An island whose projection overlaps itself (undercuts) is split into layers by a
greedy conflict colouring and each layer's connected pieces become islands. All UVs here are in millimetres.

Inputs are plain arrays (PartMesh), so the same code serves the LOD0 islands, the LOD1 UV1 charts and the tests.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

SIDE_MIN = 0.5            # |n . r| above this: cylinder side chart
CAP_MIN = 0.7             # |n . w| above this: cylinder cap chart


class PartMesh:
    """A polygon mesh as arrays (mm). loops: loop_v (vertex per loop), poly_start / poly_total (per face)."""

    def __init__(self, name, V, loop_v, poly_start, poly_total, fn=None):
        self.name = name
        self.V = np.asarray(V, float)
        self.loop_v = np.asarray(loop_v, np.int64)
        self.ps = np.asarray(poly_start, np.int64)
        self.pt = np.asarray(poly_total, np.int64)
        self.nf = len(self.ps)
        self.loop_f = np.repeat(np.arange(self.nf), self.pt)
        P = self.V[self.loop_v]
        self.fc = np.add.reduceat(P, self.ps) / self.pt[:, None]
        # Newell normal + area (polygons may be non-planar quads after bevels)
        nxt = np.arange(len(self.loop_v)) + 1
        last = self.ps + self.pt - 1
        nxt[last] = self.ps
        Q = P[nxt]
        cr = np.cross(P, Q)
        nv = np.add.reduceat(cr, self.ps) * 0.5
        self.farea = np.linalg.norm(nv, axis=1)
        if fn is None:
            fn = nv / np.maximum(self.farea[:, None], 1e-12)
        self.fn = np.asarray(fn, float)
        self._edges = None

    def edges(self):
        """(edge key array (m, 2) sorted vertex pairs, face, loop at the edge start, loop at the edge end)."""
        if self._edges is None:
            nl = len(self.loop_v)
            nxt = np.arange(nl) + 1
            last = self.ps + self.pt - 1
            nxt[last] = self.ps
            a, b = self.loop_v, self.loop_v[nxt]
            key = np.sort(np.c_[a, b], axis=1)
            self._edges = (key, self.loop_f, np.arange(nl), nxt)
        return self._edges

    def tris(self):
        """Fan triangulation: (T, 3) loop indices and their face."""
        out, fo = [], []
        for k in range(3, int(self.pt.max()) + 1 if self.nf else 3):
            sel = np.nonzero(self.pt == k)[0]
            if not len(sel):
                continue
            s = self.ps[sel]
            for j in range(1, k - 1):
                out.append(np.c_[s, s + j, s + j + 1])
                fo.append(sel)
        if not out:
            return np.zeros((0, 3), np.int64), np.zeros(0, np.int64)
        return np.vstack(out), np.concatenate(fo)


# ====================================================================== frames and charts
def box_frame(R=None):
    R = np.eye(3) if R is None else np.asarray(R, float)
    return {"mode": "box", "R": R}


def cyl_frame(c, w, u0=(0.0, 0.0, 1.0)):
    w = np.asarray(w, float) / np.linalg.norm(w)
    u0 = np.asarray(u0, float)
    u0 = u0 - (u0 @ w) * w
    u0 /= np.linalg.norm(u0)
    return {"mode": "cyl", "c": np.asarray(c, float), "w": w, "u0": u0, "v0": np.cross(w, u0)}


def rot_y(deg):
    """Frame rows for a part raked about Y by deg (e.g. a pistol grip: +deg tips the part's up axis toward -X)."""
    a = math.radians(deg)
    ex = np.array([math.cos(a), 0.0, math.sin(a)])
    ez = np.array([-math.sin(a), 0.0, math.cos(a)])
    return np.array([ex, [0.0, 1.0, 0.0], ez])


def _box_axes(R, key):
    """In-plane axes (a, b) for box chart key = 2k + (0: +axis, 1: -axis), with a x b = the chart direction."""
    e0, e1, e2 = R
    k, neg = divmod(int(key), 2)
    if k == 0:
        return (e1, e2) if not neg else (-e1, e2)
    if k == 1:
        return (-e0, e2) if not neg else (e0, e2)
    return (e0, e1) if not neg else (e0, -e1)


def box_keys(n, R):
    d = n @ np.asarray(R, float).T
    k = np.argmax(np.abs(d), axis=1)
    neg = d[np.arange(len(d)), k] < 0
    return 2 * k + neg.astype(int)


def chart_keys(pm: PartMesh, fr) -> np.ndarray:
    if fr["mode"] == "box":
        return box_keys(pm.fn, fr["R"])
    c, w, u0, v0 = fr["c"], fr["w"], fr["u0"], fr["v0"]
    d = pm.fc - c
    rad = d - np.outer(d @ w, w)
    rl = np.linalg.norm(rad, axis=1)
    rh = rad / np.maximum(rl[:, None], 1e-9)
    nw = pm.fn @ w
    nr = np.einsum("ij,ij->i", pm.fn, rh)
    keys = np.full(pm.nf, -1)
    keys[nw >= CAP_MIN] = 2
    keys[nw <= -CAP_MIN] = 3
    side = (keys < 0) & (np.abs(nr) >= SIDE_MIN) & (rl > 1e-6)
    keys[side & (nr >= 0)] = 0
    keys[side & (nr < 0)] = 1
    rest = keys < 0
    if rest.any():
        keys[rest] = 4 + box_keys(pm.fn[rest], np.array([u0, v0, w]))
    return keys


def _cyl_theta(P, fr):
    d = P - fr["c"]
    t = d @ fr["w"]
    rad = d - np.outer(t, fr["w"])
    r = np.linalg.norm(rad, axis=1)
    th = np.arctan2(rad @ fr["v0"], rad @ fr["u0"])
    return th, r, t


def project_loops(P, keys, fr, theta_ref=None) -> np.ndarray:
    """UV (mm) of points P (n, 3) under per-point chart keys. For cylinder side charts theta is unwrapped to within pi
    of theta_ref (per point; the face's own centre angle), so a face never straddles the seam."""
    P = np.asarray(P, float)
    keys = np.asarray(keys)
    out = np.zeros((len(P), 2))
    if fr["mode"] == "box":
        R = fr["R"]
        for k in np.unique(keys):
            s = keys == k
            a, b = _box_axes(R, k)
            out[s] = np.c_[P[s] @ a, P[s] @ b]
        return out
    frame = np.array([fr["u0"], fr["v0"], fr["w"]])
    for k in np.unique(keys):
        s = keys == k
        if k in (0, 1):
            th, r, t = _cyl_theta(P[s], fr)
            if theta_ref is not None:
                ref = np.asarray(theta_ref)[s]
                th = ref + (th - ref + math.pi) % (2 * math.pi) - math.pi
            sg = 1.0 if k == 0 else -1.0
            # u = theta x a constant radius per side chart (the part's own median): with u = theta x r, a face on a
            # hole's bevel (vertices at several radii) can flip; with a constant radius the radial projection onto
            # the cylinder keeps every outward face's orientation
            R0 = fr.get("R0" if k == 0 else "R1")
            out[s] = np.c_[sg * th * (R0 if R0 else r), t]
        elif k in (2, 3):
            if fr.get("polar_caps"):
                # annulus chart (a curved magazine's sides): u = -/+ theta x R_mid, v = r; straight strips instead of
                # bananas (arc lengths scale by r / R_mid: +-14 % on the AR-01 magazine)
                th, r, t = _cyl_theta(P[s], fr)
                if theta_ref is not None:
                    ref = np.asarray(theta_ref)[s]
                    th = ref + (th - ref + math.pi) % (2 * math.pi) - math.pi
                Rm = fr.get("Rcap", float(np.median(r)))
                out[s] = np.c_[(-1.0 if k == 2 else 1.0) * th * Rm, r]
            else:
                a, b = (fr["u0"], fr["v0"]) if k == 2 else (fr["u0"], -fr["v0"])
                out[s] = np.c_[P[s] @ a, P[s] @ b]
        else:
            a, b = _box_axes(frame, k - 4)
            out[s] = np.c_[P[s] @ a, P[s] @ b]
    return out


def face_theta(pm: PartMesh, fr, faces=None) -> np.ndarray:
    """Centre angle of each face (cylinder frames; 0 for box)."""
    if fr["mode"] != "cyl":
        return np.zeros(pm.nf if faces is None else len(faces))
    fc = pm.fc if faces is None else pm.fc[faces]
    return _cyl_theta(fc, fr)[0]


def loop_uv(pm: PartMesh, keys, fr) -> np.ndarray:
    lk = keys[pm.loop_f]
    ref = face_theta(pm, fr)[pm.loop_f]
    if fr["mode"] == "cyl" and fr.get("polar_caps") and "Rcap" not in fr:
        sel = np.isin(keys, (2, 3))
        if sel.any():
            fr["Rcap"] = float(np.median(_cyl_theta(pm.fc[sel], fr)[1]))
    return project_loops(pm.V[pm.loop_v], lk, fr, ref)


# ====================================================================== islands
class _UF:
    def __init__(self, n):
        self.p = np.arange(n)

    def find(self, a):
        p = self.p
        r = a
        while p[r] != r:
            r = p[r]
        while p[a] != r:
            p[a], a = r, p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def connected(pm: PartMesh, group, luv, tol=1e-5, faces_mask=None) -> np.ndarray:
    """Face labels: faces joined across shared edges with the same group value and equal UVs at both edge ends."""
    key, lf, la, lb = pm.edges()
    order = np.lexsort((key[:, 1], key[:, 0]))
    ks = key[order]
    same = np.all(ks[1:] == ks[:-1], axis=1)
    uf = _UF(pm.nf)
    idx = np.nonzero(same)[0]
    for i in idx:
        e1, e2 = order[i], order[i + 1]
        f, g = lf[e1], lf[e2]
        if f == g or group[f] != group[g]:
            continue
        if faces_mask is not None and not (faces_mask[f] and faces_mask[g]):
            continue
        # loops of the shared vertices in both faces: e1 runs a->b, e2 runs b->a (or a->b on flipped faces)
        va, vb = pm.loop_v[la[e1]], pm.loop_v[lb[e1]]
        if pm.loop_v[la[e2]] == va:
            ok = (np.abs(luv[la[e1]] - luv[la[e2]]).max() < tol and np.abs(luv[lb[e1]] - luv[lb[e2]]).max() < tol)
        else:
            ok = (np.abs(luv[la[e1]] - luv[lb[e2]]).max() < tol and np.abs(luv[lb[e1]] - luv[la[e2]]).max() < tol)
        if ok:
            uf.union(f, g)
    lab = np.array([uf.find(i) for i in range(pm.nf)])
    _, lab = np.unique(lab, return_inverse=True)
    return lab


def _tri_aabb(T):
    return T.min(axis=1), T.max(axis=1)


def overlap_pairs(T: np.ndarray, eps=1e-4, qa=False) -> np.ndarray:
    """Pairs (i, j) of 2D triangles T (n, 3, 2) whose interiors overlap (separating-axis test; touching = apart).
    qa=True uses Scripts/pipeline/qa_check.uv_overlap_sat's exact rules: triangles with 2 x area <= 1e-12 ignored,
    and an axis separates only when one interval ends within eps of the other's start (so a sliver thinner than eps
    lying inside another triangle IS an overlap there)."""
    n = len(T)
    if n < 2:
        return np.zeros((0, 2), np.int64)
    lo, hi = _tri_aabb(T)
    ext = np.maximum(hi - lo, 1e-9)
    # degenerate (collapsed) triangles never overlap anything: leave them out of the grid, and size the cells from
    # the real triangles (a median of collapsed zero extents made a micro grid and an endless bucket loop)
    if qa:
        e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
        real = np.nonzero(np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 1e-12)[0]
    else:
        real = np.nonzero(ext.max(1) > 1e-9 * max(1.0, float(np.abs(T).max())))[0]
    if len(real) < 2:
        return np.zeros((0, 2), np.int64)
    span = float((hi[real] - lo[real]).max())
    cell = max(float(np.median(ext[real])) * 2.0, span / 256.0, 1e-9)
    T, lo, hi, ext = T[real], lo[real], hi[real], ext[real]
    remap = real
    gx0 = np.floor(lo / cell).astype(np.int64)
    gx1 = np.floor(hi / cell).astype(np.int64)
    buckets: Dict[tuple, list] = {}
    for i in range(len(T)):
        for cx in range(gx0[i, 0], gx1[i, 0] + 1):
            for cy in range(gx0[i, 1], gx1[i, 1] + 1):
                buckets.setdefault((cx, cy), []).append(i)
    cand = set()
    for lst in buckets.values():
        if len(lst) < 2:
            continue
        a = np.array(lst)
        I, J = np.triu_indices(len(a), 1)
        for p, q in zip(a[I], a[J]):
            cand.add((p, q) if p < q else (q, p))
    if not cand:
        return np.zeros((0, 2), np.int64)
    C = np.array(sorted(cand), np.int64)
    n = len(T)
    # bbox prefilter (qa: apart only when one box ends within eps of the other's start, per axis)
    if qa:
        ok = ~(np.any(hi[C[:, 0]] <= lo[C[:, 1]] + eps, axis=1) | np.any(hi[C[:, 1]] <= lo[C[:, 0]] + eps, axis=1))
    else:
        ok = np.all((np.maximum(lo[C[:, 0]], lo[C[:, 1]]) < np.minimum(hi[C[:, 0]], hi[C[:, 1]]) - eps), axis=1)
    C = C[ok]
    if not len(C):
        return C
    A, B = T[C[:, 0]], T[C[:, 1]]
    sep = np.zeros(len(C), bool)
    for X in (A, B):
        for k in range(3):
            e = X[:, (k + 1) % 3] - X[:, k]
            ax = np.c_[-e[:, 1], e[:, 0]]
            ln = np.linalg.norm(ax, axis=1, keepdims=True)
            ax = ax / np.maximum(ln, 1e-15)
            pa = np.einsum("nij,nj->ni", A, ax)
            pb = np.einsum("nij,nj->ni", B, ax)
            if qa:
                sep |= (pa.max(1) <= pb.min(1) + eps) | (pb.max(1) <= pa.min(1) + eps)
            else:
                gap = np.maximum(pa.min(1), pb.min(1)) - np.minimum(pa.max(1), pb.max(1))
                sep |= gap > -eps
    return remap[C[~sep]]


def split_overlapping(pm: PartMesh, lab, luv, eps=1e-4):
    """Split every island whose UV triangles overlap: faces sorted by area, each placed in the first layer holding none
    of its conflicts; the connected pieces of each layer become islands. Returns (new labels, number split)."""
    T, tf = pm.tris()
    TU = luv[T]
    out = lab.copy()
    nxt = lab.max() + 1 if len(lab) else 0
    nsplit = 0
    for isl in np.unique(lab):
        tsel = np.nonzero(lab[tf] == isl)[0]
        if len(tsel) < 2:
            continue
        pr = overlap_pairs(TU[tsel], eps)
        if not len(pr):
            continue
        fa, fb = tf[tsel[pr[:, 0]]], tf[tsel[pr[:, 1]]]
        conf: Dict[int, set] = {}
        for a, b in zip(fa, fb):
            if a != b:
                conf.setdefault(int(a), set()).add(int(b))
                conf.setdefault(int(b), set()).add(int(a))
        if not conf:
            continue
        nsplit += 1
        faces = np.nonzero(lab == isl)[0]
        order = faces[np.argsort(-pm.farea[faces])]
        layer = {}
        for f in order:
            used = {layer[g] for g in conf.get(int(f), ()) if g in layer}
            k = 0
            while k in used:
                k += 1
            layer[int(f)] = k
        grp = np.full(pm.nf, -1)
        for f, k in layer.items():
            grp[f] = k
        mask = np.zeros(pm.nf, bool)
        mask[faces] = True
        sub = connected(pm, np.where(mask, grp, -2 - np.arange(pm.nf)), luv, faces_mask=mask)
        for s in np.unique(sub[faces]):
            sel = faces[sub[faces] == s]
            out[sel] = nxt
            nxt += 1
    _, out = np.unique(out, return_inverse=True)
    return out, nsplit


GROW_MIN = 0.5            # region growing: a face joins a box chart while its normal is within 60 deg of the axis


def grow_box_keys(pm: PartMesh, R, group, grow_min=GROW_MIN) -> np.ndarray:
    """Box charts by region growing (instead of one cut at 45 deg between every pair of axes): seeds are the largest
    unassigned faces in their own dominant axis; a region takes edge neighbours of the same group whose normal is
    within acos(grow_min) of that axis. Bevel bands then stay on the flats they belong to instead of becoming thin
    strip islands (each strip costs its packing margin twice)."""
    R = np.asarray(R, float)
    dirs = np.vstack([R[0], -R[0], R[1], -R[1], R[2], -R[2]])
    own = box_keys(pm.fn, R)
    dots = pm.fn @ dirs.T                                  # (nf, 6)
    key, lf, la, lb = pm.edges()
    order = np.lexsort((key[:, 1], key[:, 0]))
    ks = key[order]
    same = np.nonzero(np.all(ks[1:] == ks[:-1], axis=1))[0]
    nb = [[] for _ in range(pm.nf)]
    for i in same:
        f, g = lf[order[i]], lf[order[i + 1]]
        if f != g:
            nb[f].append(g)
            nb[g].append(f)
    out = np.full(pm.nf, -1)
    for seed in np.argsort(-pm.farea):
        if out[seed] >= 0:
            continue
        k = int(own[seed])
        out[seed] = k
        stack = [seed]
        while stack:
            f = stack.pop()
            for g in nb[f]:
                if out[g] < 0 and group[g] == group[seed] and dots[g, k] >= grow_min:
                    out[g] = k
                    stack.append(g)
    return out


def _tri_area(U):
    return 0.5 * np.abs((U[:, 1, 0] - U[:, 0, 0]) * (U[:, 2, 1] - U[:, 0, 1])
                        - (U[:, 2, 0] - U[:, 0, 0]) * (U[:, 1, 1] - U[:, 0, 1]))


def rectangularize(pm: PartMesh, lab, luv, min_ratio=0.78, min_area=150.0, gain=0.88, depth=6, max_aspect=3.5,
                   aspect_area=600.0):
    """Split islands that fill their bounding box poorly (curved strips, L shapes) by guillotine cuts: for an island
    with area / box < min_ratio and area >= min_area (mm^2), try cuts across U and V at face-centre quantiles and keep
    the one with the smallest summed child box area if it is < gain x the parent's; recurse on the connected pieces.
    Packers (Blender's included) place near-rectangles far better; the seams cost nothing here because every texel is
    painted from its own 3D position."""
    T, tf = pm.tris()
    TU = luv[T]
    ta = _tri_area(TU)
    fa = np.bincount(tf, weights=ta, minlength=pm.nf)
    fcu = np.zeros((pm.nf, 2))
    np.add.at(fcu, tf, TU.mean(1))
    cnt = np.bincount(tf, minlength=pm.nf)
    fcu /= np.maximum(cnt[:, None], 1)
    lmin = np.full((pm.nf, 2), np.inf)
    lmax = np.full((pm.nf, 2), -np.inf)
    np.minimum.at(lmin, pm.loop_f, luv)
    np.maximum.at(lmax, pm.loop_f, luv)
    out = lab.copy()
    nxt = int(lab.max()) + 1
    nsplit = 0

    def box(fs):
        return float(np.prod(lmax[fs].max(0) - lmin[fs].min(0)))

    def span(fs):
        return lmax[fs].max(0) - lmin[fs].min(0)

    def split_conn(part, d):
        mask = np.zeros(pm.nf, bool)
        mask[part] = True
        sub = connected(pm, np.where(mask, 0, -1 - np.arange(pm.nf)), luv, faces_mask=mask)
        out_ = []
        for sid in np.unique(sub[part]):
            out_ += rec(part[sub[part] == sid], d + 1)
        return out_

    def rec(fs, d):
        nonlocal nxt, nsplit
        A = float(fa[fs].sum())
        B = box(fs)
        ext = lmax[fs].max(0) - lmin[fs].min(0)
        # long strips (a stock comb, a receiver side) limit any packer's scale: halve them across their length
        if d < depth and A >= aspect_area and len(fs) >= 4 and ext.max() > max_aspect * max(ext.min(), 1e-9):
            ax = int(np.argmax(ext))
            c = fcu[fs, ax]
            t = float(np.median(c))
            L, R = fs[c <= t], fs[c > t]
            # accept only a cut that really shortens the strip (an island of faces as long as itself cannot be
            # halved by face centres: the halves would interleave as thin full-length rows)
            if len(L) and len(R) and max(span(L)[ax], span(R)[ax]) <= 0.75 * ext[ax]:
                nsplit += 1
                return split_conn(L, d) + split_conn(R, d)
        if d >= depth or A < min_area or B <= 0 or A / B >= min_ratio or len(fs) < 4:
            return [fs]
        best = None
        for ax in (0, 1):
            c = fcu[fs, ax]
            for q in np.linspace(0.15, 0.85, 15):
                t = np.quantile(c, q)
                L, R = fs[c <= t], fs[c > t]
                if len(L) == 0 or len(R) == 0:
                    continue
                # no slivers: both pieces keep >= 15 % of the area and >= 3 mm across
                if min(fa[L].sum(), fa[R].sum()) < 0.15 * A or min(span(L).min(), span(R).min()) < 3.0:
                    continue
                tot = box(L) + box(R)
                if best is None or tot < best[0]:
                    best = (tot, L, R)
        if best is None or best[0] >= gain * B:
            return [fs]
        nsplit += 1
        return split_conn(best[1], d) + split_conn(best[2], d)
    for isl in np.unique(lab):
        fs = np.nonzero(lab == isl)[0]
        pieces = rec(fs, 0)
        if len(pieces) > 1:
            for pc in pieces:
                out[pc] = nxt
                nxt += 1
    _, out = np.unique(out, return_inverse=True)
    return out, nsplit


def _neighbours(pm: PartMesh):
    key, lf, la, lb = pm.edges()
    order = np.lexsort((key[:, 1], key[:, 0]))
    ks = key[order]
    same = np.nonzero(np.all(ks[1:] == ks[:-1], axis=1))[0]
    nb = [[] for _ in range(pm.nf)]
    for i in same:
        f, g = lf[order[i]], lf[order[i + 1]]
        if f != g:
            nb[f].append(g)
            nb[g].append(f)
    return nb


def absorb_slivers(pm: PartMesh, fr, keys, cls, min_dot=0.26, thin_mm=1.2, long_mm=4.0, small_mm2=6.0, rounds=3):
    """Box charts: islands that are slivers (a bevel band's long thin triangles left between two grown regions) or
    tiny join a neighbouring region of the same class whose axis is within acos(min_dot) of their normal. A sliver
    island costs its packing gap twice along its whole length and its length orders it first in any packer."""
    R = np.asarray(fr["R"], float)
    dirs = np.vstack([R[0], -R[0], R[1], -R[1], R[2], -R[2]])
    keys = keys.copy()
    nb = _neighbours(pm)
    moved = 0
    for _ in range(rounds):
        luv = loop_uv(pm, keys, fr)
        lab = connected(pm, keys * 1000 + cls, luv)
        lo = np.full((lab.max() + 1, 2), np.inf)
        hi = np.full((lab.max() + 1, 2), -np.inf)
        np.minimum.at(lo, lab[pm.loop_f], luv)
        np.maximum.at(hi, lab[pm.loop_f], luv)
        ext = hi - lo
        area = np.bincount(lab, weights=pm.farea, minlength=len(ext))
        bad = ((ext.min(1) < thin_mm) & (ext.max(1) > long_mm)) | (area < small_mm2)
        if not bad.any():
            break
        new = keys.copy()
        for f in np.nonzero(bad[lab])[0]:
            best, bd = None, min_dot
            for g in nb[f]:
                if bad[lab[g]] or cls[g] != cls[f]:
                    continue
                d = float(pm.fn[f] @ dirs[keys[g]])
                if d >= bd:
                    best, bd = keys[g], d
            if best is not None and best != keys[f]:
                new[f] = best
                moved += 1
        if np.array_equal(new, keys):
            break
        keys = new
    return keys, moved


def signed_uv_area(luv, pm: PartMesh) -> np.ndarray:
    """Per-face SIGNED UV area of loop UVs (shoelace; > 0 = counter-clockwise = not mirrored)."""
    nl = len(pm.loop_v)
    nxt = np.arange(nl) + 1
    last = pm.ps + pm.pt - 1
    nxt[last] = pm.ps
    cr = luv[:, 0] * luv[nxt, 1] - luv[nxt, 0] * luv[:, 1]
    return np.add.reduceat(cr, pm.ps) * 0.5


def _unflip_polar_caps(pm: PartMesh, fr, keys):
    """Polar cap charts (u = -/+ theta Rcap, v = r) are orientation-preserving at every point, but a face is mapped
    through its corners only: a long thin face (a rib flank's sliver, ~30 mm long and < 0.5 mm wide) whose straight
    edge spans enough angle has its chord's sagitta in (theta, r) exceed its width, and its UV triangle folds over
    (AR-01 R51 magazine: one flank triangle). Such faces take the frame's planar chart along w instead (key 4 + box key
    in the (u0, v0, w) frame: U x V = the chart direction, so never mirrored); they become their own islands."""
    if not fr.get("polar_caps"):
        return keys
    cap = np.isin(keys, (2, 3))
    if not cap.any():
        return keys
    sa = signed_uv_area(loop_uv(pm, keys, fr), pm)
    bad = cap & (sa <= 0.0)
    if bad.any():
        keys = keys.copy()
        keys[bad] = 4 + box_keys(pm.fn[bad], np.array([fr["u0"], fr["v0"], fr["w"]]))
        fr["unflipped_cap_faces"] = int(fr.get("unflipped_cap_faces", 0)) + int(bad.sum())
    return keys


def make_islands(pm: PartMesh, fr, cls) -> dict:
    """Charts + class -> islands for one part. Returns {'keys', 'luv' (loops, mm), 'lab' (face -> local island),
    'n_split', 'overlaps_left'}."""
    cls = np.asarray(cls)
    absorbed = 0
    if fr["mode"] == "box":
        keys = grow_box_keys(pm, fr["R"], cls)
        keys, absorbed = absorb_slivers(pm, fr, keys, cls)
    else:
        keys = chart_keys(pm, fr)
        for k, nm in ((0, "R0"), (1, "R1")):
            sel = keys == k
            if sel.any() and nm not in fr:
                fr[nm] = float(np.median(_cyl_theta(pm.fc[sel], fr)[1]))
        keys = _unflip_polar_caps(pm, fr, keys)
    luv = loop_uv(pm, keys, fr)
    grp = keys * 1000 + cls
    lab = connected(pm, grp, luv)
    lab, nsplit = split_overlapping(pm, lab, luv)
    lab, nrect = rectangularize(pm, lab, luv)
    # verify
    T, tf = pm.tris()
    left = 0
    for isl in np.unique(lab):
        tsel = np.nonzero(lab[tf] == isl)[0]
        if len(tsel) > 1:
            left += len(overlap_pairs(luv[T][tsel], 1e-5 * 100.0))   # mm: qa's 1e-5 UV epsilon at ~100 mm per UV unit
    return {"keys": keys, "luv": luv, "lab": lab, "n_split": nsplit, "n_rect_cuts": nrect, "overlaps_left": left,
            "absorbed_faces": absorbed}


def uv_area(luv, pm: PartMesh) -> np.ndarray:
    """Per-face UV area of loop UVs (shoelace over each polygon)."""
    nl = len(pm.loop_v)
    nxt = np.arange(nl) + 1
    last = pm.ps + pm.pt - 1
    nxt[last] = pm.ps
    cr = luv[:, 0] * luv[nxt, 1] - luv[nxt, 0] * luv[:, 1]
    return np.abs(np.add.reduceat(cr, pm.ps)) * 0.5


def fit_affine(src, dst):
    """Least-squares 2D affine dst = A @ src + t (returns 2x3)."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    X = np.c_[src, np.ones(len(src))]
    M, *_ = np.linalg.lstsq(X, dst, rcond=None)
    return M.T


def apply_affine(M, uv):
    uv = np.asarray(uv, float)
    return uv @ M[:, :2].T + M[:, 2]


def unwrapped_theta(fr, key, luv_face) -> float:
    """The unwrapped angle a cylinder-frame face carries in its island (from its loop UVs): side charts u = +-theta R,
    polar caps u = -/+ theta Rcap. 0 for planar charts (they ignore it)."""
    if fr["mode"] != "cyl":
        return 0.0
    u = float(np.mean(np.asarray(luv_face)[:, 0]))
    if key == 0 and fr.get("R0"):
        return u / fr["R0"]
    if key == 1 and fr.get("R1"):
        return -u / fr["R1"]
    if key in (2, 3) and fr.get("polar_caps") and fr.get("Rcap"):
        return (-u if key == 2 else u) / fr["Rcap"]
    return 0.0
