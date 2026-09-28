"""pd_geodiag_lib.py -- numpy helpers for the offline MetaHuman mesh-dump diagnosis (no Unreal).

Run with Blender's bundled Python (it has numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/MetaHuman/pd_geodiag_*.py
Input dumps are the GeometryScript OBJ dumps written by pb_conform.py / pb_face_design.py
(UE world space, cm, Z up, character faces +Y, character left = +X).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
PB = ROOT / "WorkFiles/MetaHuman/player_base"
FD = PB / "faces/mesh_dump"
BD = PB / "mesh_dump"
OUT = ROOT / "WorkFiles/MetaHuman/player_default/geodiag"

DUMPS = {
    "FaceC_Face": FD / "FaceC_Face.obj", "FaceC_Body": FD / "FaceC_Body.obj",
    "ref_Face": FD / "ref_Face.obj", "ref_Body": FD / "ref_Body.obj",
    "kelvin_Face": BD / "baseline_apose_Face.obj", "kelvin_Body": BD / "baseline_apose_Body.obj",
    "mh_apose_Body": BD / "mh_apose_Body.obj", "source": BD / "source_input.obj",
}


def load_obj(path: Path):
    vs, fs = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                vs.append(line[2:].split())
            elif line.startswith("f "):
                fs.append([int(t.split("/")[0]) - 1 for t in line[2:].split()])
    return np.asarray(vs, dtype=np.float64), np.asarray(fs, dtype=np.int64)


def edges_of(F):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    return e


def edge_table(F):
    """Undirected edges with face incidence counts; returns (unique_edges[E,2], counts[E], inverse[3F])."""
    e = np.sort(edges_of(F), axis=1)
    uniq, inv, cnt = np.unique(e, axis=0, return_inverse=True, return_counts=True)
    return uniq, cnt, inv.ravel()


def boundary_loops(F):
    uniq, cnt, _ = edge_table(F)
    b = uniq[cnt == 1]
    adj = {}
    for a, c in b:
        adj.setdefault(int(a), []).append(int(c))
        adj.setdefault(int(c), []).append(int(a))
    seen = set()
    loops = []
    for start in adj:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        loops.append(loop)
    return loops, int((cnt == 1).sum()), int((cnt > 2).sum())


def components(nv, F):
    parent = np.arange(nv)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, c in F:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    roots = np.array([find(i) for i in range(nv)])
    return roots


def face_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-12)[:, None], 0.5 * a


def vertex_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], n)
    return vn / np.maximum(np.linalg.norm(vn, axis=1), 1e-12)[:, None]


def dihedral(V, F):
    """Per interior manifold edge: (edge verts, face pair, angle between face normals in degrees)."""
    fn, _ = face_normals(V, F)
    e = np.sort(edges_of(F), axis=1)
    fid = np.tile(np.arange(len(F)), 3)
    order = np.lexsort((e[:, 1], e[:, 0]))
    e, fid = e[order], fid[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    idx = np.nonzero(same)[0]
    # drop edges shared by >2 faces
    pairs_e = e[idx]
    f0, f1 = fid[idx], fid[idx + 1]
    cosang = np.clip(np.einsum("ij,ij->i", fn[f0], fn[f1]), -1, 1)
    return pairs_e, f0, f1, np.degrees(np.arccos(cosang))


def kabsch(A, B, scale=False):
    """Rigid (optionally similarity) transform mapping A->B (least squares). Returns R, t, s."""
    ca, cb = A.mean(0), B.mean(0)
    AA, BB = A - ca, B - cb
    H = AA.T @ BB
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    s = (S * np.diag(D)).sum() / (AA ** 2).sum() if scale else 1.0
    t = cb - s * (R @ ca)
    return R, t, s


def apply(R, t, s, P):
    return s * (P @ R.T) + t


def tri_tri_intersect(p, q):
    """Moller-style robust enough test via segment-triangle checks (both ways). p,q: (3,3)."""
    def seg_tri(a, b, t):
        e1, e2 = t[1] - t[0], t[2] - t[0]
        d = b - a
        h = np.cross(d, e2)
        det = e1 @ h
        if abs(det) < 1e-12:
            return False
        inv = 1.0 / det
        s = a - t[0]
        u = inv * (s @ h)
        if u < 1e-9 or u > 1 - 1e-9:
            return False
        qv = np.cross(s, e1)
        v = inv * (d @ qv)
        if v < 1e-9 or u + v > 1 - 1e-9:
            return False
        w = inv * (e2 @ qv)
        return 1e-9 < w < 1 - 1e-9
    for i in range(3):
        if seg_tri(p[i], p[(i + 1) % 3], q) or seg_tri(q[i], q[(i + 1) % 3], p):
            return True
    return False


def self_intersections(V, F, mask_faces, cell=0.6):
    """Brute-force-with-grid self-intersection test for faces in mask_faces (index array).
    Faces sharing a vertex are skipped. Returns list of (fa, fb)."""
    sel = np.asarray(mask_faces)
    T = V[F[sel]]
    lo, hi = T.min(1), T.max(1)
    grid = {}
    for k, (a, b) in enumerate(zip(np.floor(lo / cell).astype(int), np.floor(hi / cell).astype(int))):
        for x in range(a[0], b[0] + 1):
            for y in range(a[1], b[1] + 1):
                for z in range(a[2], b[2] + 1):
                    grid.setdefault((x, y, z), []).append(k)
    hits = set()
    tested = set()
    for cellk, ks in grid.items():
        if len(ks) < 2:
            continue
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = ks[i], ks[j]
                key = (a, b) if a < b else (b, a)
                if key in tested:
                    continue
                tested.add(key)
                fa, fb = F[sel[a]], F[sel[b]]
                if set(fa.tolist()) & set(fb.tolist()):
                    continue
                if np.any(lo[a] > hi[b]) or np.any(lo[b] > hi[a]):
                    continue
                if tri_tri_intersect(T[a], T[b]):
                    hits.add((int(sel[key[0]]), int(sel[key[1]])))
    return sorted(hits)
