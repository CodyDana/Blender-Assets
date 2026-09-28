"""b2_rig_geo.py - PRIVATE / DO NOT SHIP. Geometry helpers for the step C1 joint fit (pure python + mathutils).

Geodesic level-set skeletons of limbs on the welded skin shell: Dijkstra distance from a seam over a vertex subset,
banded; each band split into connected components; centroid per component = medial-axis node.
"""
import heapq, math
from collections import defaultdict
from mathutils import Vector


class Mesh:
    def __init__(self, me, src_attr="src", matrix=None, weld=False):
        raw = [(matrix @ v.co) if matrix is not None else v.co.copy() for v in me.vertices]
        remap = list(range(len(raw)))
        if weld:  # FBX-imported meshes are split along UV seams: merge exact duplicates so slices close
            key = {}
            for i, c in enumerate(raw):
                k = (round(c.x, 6), round(c.y, 6), round(c.z, 6))
                remap[i] = key.setdefault(k, i)
        self.remap = remap
        self.co = raw
        self.n = len(self.co)
        self.adj = [[] for _ in range(self.n)]
        seen_e = set()
        for e in me.edges:
            a, b = remap[e.vertices[0]], remap[e.vertices[1]]
            if a == b or (min(a, b), max(a, b)) in seen_e:
                continue
            seen_e.add((min(a, b), max(a, b)))
            d = (self.co[a] - self.co[b]).length
            self.adj[a].append((b, d)); self.adj[b].append((a, d))
        src = [0] * len(me.polygons)
        if src_attr and src_attr in me.attributes:
            me.attributes[src_attr].data.foreach_get("value", src)
        self.vsrc = [set() for _ in range(self.n)]
        self.faces = [tuple(remap[v] for v in p.vertices) for p in me.polygons]
        self.fsrc = src
        for p, s in zip(self.faces, src):
            for v in p:
                self.vsrc[v].add(s)


def dijkstra(mesh, seeds, allowed):
    dist = {s: 0.0 for s in seeds}
    pq = [(0.0, s) for s in seeds]
    heapq.heapify(pq)
    while pq:
        d, v = heapq.heappop(pq)
        if d > dist.get(v, 1e18):
            continue
        for w, l in mesh.adj[v]:
            if w not in allowed:
                continue
            nd = d + l
            if nd < dist.get(w, 1e18):
                dist[w] = nd
                heapq.heappush(pq, (nd, w))
    return dist


def band_nodes(mesh, dist, step):
    """Face-based geodesic bands. Returns nodes {id, band, d, verts, faces, c, r, parent, children}.
    A face belongs to band int(mean vertex distance / step); a band's faces are split into edge-connected components
    (faces tile the surface, so a band around a limb is one closed ring). Centroid = area-weighted face centres."""
    fb = {}
    vfaces = defaultdict(list)
    for fi, f in enumerate(mesh.faces):
        if all(v in dist for v in f):
            fb[fi] = int(sum(dist[v] for v in f) / len(f) / step)
            for v in f:
                vfaces[v].append(fi)
    bands = defaultdict(list)
    for fi, b in fb.items():
        bands[b].append(fi)
    nodes = []
    node_of_face = {}
    for b in sorted(bands):
        fs = set(bands[b]); seen = set()
        for s0 in bands[b]:
            if s0 in seen:
                continue
            comp = []; st = [s0]; seen.add(s0)
            while st:
                f = st.pop(); comp.append(f)
                fv = mesh.faces[f]
                for i in range(len(fv)):
                    a, c = fv[i], fv[(i + 1) % len(fv)]
                    for g in vfaces[a]:
                        if g in fs and g not in seen and c in mesh.faces[g]:
                            seen.add(g); st.append(g)
            verts = sorted({v for f in comp for v in mesh.faces[f]})
            ctot = Vector(); atot = 0.0
            for f in comp:
                fv = mesh.faces[f]
                cc = sum((mesh.co[v] for v in fv), Vector()) / len(fv)
                a = ((mesh.co[fv[2]] - mesh.co[fv[0]]).cross(mesh.co[fv[1]] - mesh.co[fv[0]])).length
                if len(fv) == 4:
                    a = 0.5 * a + 0.5 * ((mesh.co[fv[3]] - mesh.co[fv[0]]).cross(mesh.co[fv[2]] - mesh.co[fv[0]])).length
                ctot += cc * a; atot += a
            c = ctot / max(atot, 1e-12)
            r = sum((mesh.co[v] - c).length for v in verts) / len(verts)
            votes = defaultdict(int)
            for f in comp:
                for v in mesh.faces[f]:
                    for g in vfaces[v]:
                        if fb.get(g) == b - 1 and g in node_of_face:
                            votes[node_of_face[g]] += 1
            parent = max(votes, key=votes.get) if votes else None
            nodes.append({"id": len(nodes), "band": b, "d": (b + 0.5) * step, "verts": verts, "faces": comp, "c": c,
                          "r": r, "area": atot, "parent": parent, "children": []})
        for nd in nodes:
            if nd["band"] == b:
                for f in nd["faces"]:
                    node_of_face[f] = nd["id"]
    for nd in nodes:
        if nd["parent"] is not None:
            nodes[nd["parent"]]["children"].append(nd["id"])
    return nodes


def subtree_size(nodes, i, memo=None):
    memo = {} if memo is None else memo
    if i in memo:
        return memo[i]
    s = len(nodes[i]["verts"]) + sum(subtree_size(nodes, c, memo) for c in nodes[i]["children"])
    memo[i] = s
    return s


def main_path(nodes, start):
    """Follow the heaviest child from start (trunk of the limb)."""
    memo = {}
    path = [start]
    while nodes[path[-1]]["children"]:
        ch = nodes[path[-1]]["children"]
        path.append(max(ch, key=lambda c: subtree_size(nodes, c, memo)))
    return path


def leaf_paths(nodes, start):
    """All root->leaf paths below start."""
    out = []
    st = [(start, [start])]
    while st:
        i, p = st.pop()
        if not nodes[i]["children"]:
            out.append(p)
        for c in nodes[i]["children"]:
            st.append((c, p + [c]))
    return out


def polyline_len(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def point_at(pts, s):
    """Point at arc length s along a polyline."""
    acc = 0.0
    for i in range(len(pts) - 1):
        l = (pts[i + 1] - pts[i]).length
        if acc + l >= s and l > 0:
            return pts[i].lerp(pts[i + 1], (s - acc) / l)
        acc += l
    return pts[-1].copy()


def arclen_at(pts, idx):
    return polyline_len(pts[:idx + 1])


def fit_line(pts):
    """Least-squares 3D line: (centroid, unit direction)."""
    import numpy as np
    P = np.array([list(p) for p in pts])
    c = P.mean(axis=0)
    u, s, vt = np.linalg.svd(P - c)
    d = Vector(vt[0].tolist())
    return Vector(c.tolist()), d.normalized()


def smooth_poly(pts, it=2):
    p = [q.copy() for q in pts]
    for _ in range(it):
        p = [p[0]] + [(p[i - 1] + 2 * p[i] + p[i + 1]) / 4 for i in range(1, len(p) - 1)] + [p[-1]]
    return p


def iso_contours(mesh, dist, t, allowed_faces=None):
    """Level-set curves dist == t on the faces whose verts all have a distance.
    Returns list of components: {"c": length-weighted centroid, "len": curve length, "pts": [edge points], "closed": bool}."""
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    pts = {}
    segs = []
    faces = allowed_faces if allowed_faces is not None else range(len(mesh.faces))
    for fi in faces:
        f = mesh.faces[fi]
        if not all(v in dist for v in f):
            continue
        cr = []
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            da, db = dist[a] - t, dist[b] - t
            if (da < 0) != (db < 0):
                key = (a, b) if a < b else (b, a)
                if key not in pts:
                    w = da / (da - db)
                    pts[key] = mesh.co[a].lerp(mesh.co[b], w)
                    parent[key] = key
                cr.append(key)
        if len(cr) == 2:
            segs.append((cr[0], cr[1]))
        elif len(cr) == 4:
            segs.append((cr[0], cr[1])); segs.append((cr[2], cr[3]))
    for a, b in segs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = defaultdict(list)
    for a, b in segs:
        groups[find(a)].append((a, b))
    out = []
    for g in groups.values():
        L = 0.0; c = Vector()
        deg = defaultdict(int)
        for a, b in g:
            l = (pts[a] - pts[b]).length
            L += l; c += (pts[a] + pts[b]) * 0.5 * l
            deg[a] += 1; deg[b] += 1
        if L <= 0:
            continue
        keys = list(deg)
        out.append({"c": c / L, "len": L, "pts": [pts[k] for k in keys], "closed": all(d == 2 for d in deg.values()),
                    "t": t})
    return out


def iso_skeleton(mesh, dist, step, min_len=0.004):
    """Stack of iso-contours every `step`; nodes linked to the nearest node of the previous level."""
    maxd = max(dist.values())
    nodes = []
    prev = []
    t = step * 0.5
    while t < maxd:
        cur = []
        for comp in iso_contours(mesh, dist, t):
            if comp["len"] < min_len:
                continue
            comp["id"] = len(nodes); comp["children"] = []; comp["parent"] = None
            if prev:
                p = min(prev, key=lambda q: (nodes[q]["c"] - comp["c"]).length)
                comp["parent"] = p
                nodes[p]["children"].append(comp["id"])
            comp["r"] = comp["len"] / (2 * math.pi)
            nodes.append(comp); cur.append(comp["id"])
        prev = cur if cur else prev
        t += step
    return nodes


def heaviest_path(nodes, start):
    memo = {}

    def size(i):
        if i not in memo:
            memo[i] = 1 + sum(size(c) for c in nodes[i]["children"])
        return memo[i]
    path = [start]
    while nodes[path[-1]]["children"]:
        path.append(max(nodes[path[-1]]["children"], key=size))
    return path


def slice_loops(mesh, origin, axis, ts, faces=None):
    """Planar slices perpendicular to axis at signed distances ts from origin -> {t: [loops]}."""
    ax = Vector(axis).normalized(); o = Vector(origin)
    dist = {i: (c - o).dot(ax) for i, c in enumerate(mesh.co)}
    return {t: iso_contours(mesh, dist, t, faces) for t in ts}


def pick_loop(loops, near, max_off=0.12, closed=True):
    """Longest loop whose centroid is within max_off of `near` (full 3D)."""
    c = [l for l in loops if (not closed or l["closed"]) and (l["c"] - Vector(near)).length < max_off]
    return max(c, key=lambda l: l["len"]) if c else None
