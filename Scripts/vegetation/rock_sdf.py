"""Tree rock v3: the stone study's rock method (STONE_BUILDING_STUDY.md 4.9.2, 4.9.3 "the tree rock", 8.3).

"Jointed block, then rounded, then cracked, then grained" (study rule 12), never noise on a sphere:
  1. lobes (primary): 2-3 convex granite blocks cut by 2-3 joint FAMILIES (two vertical sets + the sheeting plane),
     a few octagon corner planes and weathered chips; sizes set in metres from the sheet (x0.65, owner)
  2. per-lobe SDF (Geometry Nodes Mesh to SDF Grid) and a per-lobe OPENING (offset -r, +r): each lobe gets its own
     arris radius (study S1: CV of the arris radius >= 0.3; table 4.9.2: tree rock 4-8 %, weathered lobes more)
  3. SDF union, then a small CLOSING (+c, -c) that fillets the cleft where the lobes meet
  4. secondary: fresh FRACTURE chips (SDF difference of convex cutters: crisper arrises) and 1-3 CRACKS (wedges along
     the joint planes, 1-3 cm wide at the mouth, 10-40 cm deep) where the roots go
  5. a small lip opening (the cut arrises round to about 1 cm), Grid to Mesh at threshold 0 (P15)
  6. masks on the mesh (convexity, joins, cracks, up-normal), then meso noise masked down on the arrises (4.9.2 step 6)
The GN chain runs in the current Blender scene (headless). The numpy helpers have no bpy dependency.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np

try:
    import bpy
    import bmesh
    from mathutils import Vector, geometry
except ImportError:  # pragma: no cover - numpy-only use
    bpy = None


# ----------------------------------------------------------------------------------------------- small maths

def unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def rotz(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    v = np.asarray(v, float)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]])


def jitter(n, deg, rng):
    """Tilt a unit normal by up to ``deg`` degrees in a random direction (joint planes are not exactly parallel)."""
    n = unit(n)
    t = np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0])
    t = unit(t)
    b = np.cross(n, t)
    a = rng.uniform(0, 2 * math.pi)
    k = math.tan(math.radians(rng.uniform(0, deg)))
    return unit(n + k * (math.cos(a) * t + math.sin(a) * b))


def smoothstep(x, e0, e1):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF) * 2.0 - 1.0


def vnoise3(P, seed=0):
    """Value noise in [-1, 1] on a unit lattice, smooth (trilinear with smoothstep weights). P: (n, 3)."""
    P = np.asarray(P, float)
    i = np.floor(P).astype(np.int64)
    f = P - i
    u = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) *
                     (u[:, 2] if dz else 1 - u[:, 2]))
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, octaves: Sequence[Tuple[float, float]], seed=0):
    """Sum of value-noise octaves: [(amplitude, frequency per metre), ...]."""
    out = np.zeros(len(P))
    for k, (amp, fr) in enumerate(octaves):
        out += amp * vnoise3(np.asarray(P) * fr + 17.3 * k, seed + 101 * k)
    return out


# ----------------------------------------------------------------------------------------------- lobes (step 1)

def polytope_vertices(planes):
    """planes: [(n, d)] with n.p <= d inside. Vertices of the convex polytope (mathutils.points_in_planes)."""
    pl = [Vector((float(n[0]), float(n[1]), float(n[2]), -float(d))) for n, d in planes]
    verts, _ = geometry.points_in_planes(pl)
    return np.array([v[:] for v in verts], float)


def lobe_planes(L: Dict, yaw: float, rng) -> List[Tuple[np.ndarray, float]]:
    """A jointed granite block. L: c (x, y), a / b = half widths along the two vertical joint families (u = family A
    normal at ``yaw``, v = family B), top (z at the centre), slope (dz/du, dz/dv of the sheeting joint), bot (z),
    corner (0-1: the octagon cut at the vertical corners), chips (weathered chips before the opening)."""
    u = rotz([1.0, 0.0, 0.0], yaw + L.get("yaw", 0.0))
    v = rotz([0.0, 1.0, 0.0], yaw + L.get("yaw", 0.0))
    c = np.array([L["c"][0], L["c"][1], 0.0])
    a, b = float(L["a"]), float(L["b"])
    jd = float(L.get("jitter_deg", 5.0))
    planes = []
    z_wide = float(L.get("z_wide", 0.35)) * float(L["top"])      # the block is widest about a third up
    bat = float(L.get("batter", 9.0))
    sides = []
    for n0, h in ((u, a * rng.uniform(0.94, 1.06)), (-u, a * rng.uniform(0.94, 1.06)),
                  (v, b * rng.uniform(0.94, 1.06)), (-v, b * rng.uniform(0.94, 1.06))):
        be = math.radians(bat + rng.uniform(-5, 5))
        n = unit(n0 * math.cos(be) + np.array([0.0, 0.0, math.sin(be)]))   # batter: the face leans back
        n = jitter(n, jd, rng)
        p0 = c + n0 * h + np.array([0.0, 0.0, z_wide])
        planes.append((n, float(n @ p0)))
        sides.append((n0, h))
    su, sv = L.get("slope", (0.0, 0.0))
    top_n = unit(-su * u - sv * v + np.array([0.0, 0.0, 1.0]))
    top_n = jitter(top_n, 2.5, rng)
    planes.append((top_n, float(top_n @ np.array([c[0], c[1], L["top"]]))))
    planes.append((np.array([0.0, 0.0, -1.0]), -float(L["bot"])))
    # top chamfers along the four top arrises (the corestone's weathered shoulders: a domed, not flat, top)
    cham = L.get("chamfer", (0.06, 0.16))
    for n0, h in sides:
        th = math.radians(rng.uniform(44, 66))
        n = jitter(unit(n0 * math.sin(th) + np.array([0.0, 0.0, math.cos(th)])), 6.0, rng)
        V = polytope_vertices(planes)
        planes.append((n, float((V @ n).max()) - rng.uniform(*cham)))
    # octagon corner planes (the blocks are not boxes: 45 deg joints of a third family cut two or three corners)
    k_c = float(L.get("corner", 0.82))
    for su_, sv_ in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        if rng.uniform() < float(L.get("corner_p", 0.75)):
            n = unit(su_ * u / a + sv_ * v / b)
            n = jitter(n, 8.0, rng)
            n[2] *= 0.3
            n = unit(n)
            V = polytope_vertices(planes)
            h = float((V @ n).max())
            dmin = float((V @ n).min())
            planes.append((n, float(n @ c) + (h - float(n @ c)) * rng.uniform(k_c - 0.06, k_c + 0.06)))
    # weathered chips (rounded by the lobe's opening): corners and edges above ground, never the buried bottom
    for _ in range(int(L.get("chips", 5))):
        V = polytope_vertices(planes)
        cen = V.mean(0)
        up = V[V[:, 2] > float(L["bot"]) + 0.25 * (float(L["top"]) - float(L["bot"]))]
        if not len(up):
            break
        p = up[rng.integers(len(up))]
        n = unit(p - cen + np.array([0.0, 0.0, 0.15]))
        n = jitter(n, 20.0, rng)
        if n[2] < -0.3:
            continue
        span = float((V @ n).max() - (V @ n).min())
        depth = rng.uniform(*L.get("chip_depth", (0.05, 0.14))) * span
        planes.append((n, float((V @ n).max()) - depth))
    return planes


def _ellipsoid(L: Dict, yaw: float):
    u = rotz([1.0, 0.0, 0.0], yaw + L.get("yaw", 0.0))
    v = rotz([0.0, 1.0, 0.0], yaw + L.get("yaw", 0.0))
    w = np.array([0.0, 0.0, 1.0])
    top = float(L["top"])
    bot = float(L.get("bot", -0.12))
    zc = float(L.get("z_mid", 0.38)) * top if bot < 0.05 else 0.5 * (top + bot)
    cc = np.array([L["c"][0], L["c"][1], zc])
    return u, v, w, cc, (float(L["a"]), float(L["b"]), top - zc)


def lobe_planes_rounded(L: Dict, yaw: float, rng) -> List[Tuple[np.ndarray, float]]:
    """A CORESTONE lobe (study 3.9: a jointed block rounded from outside in): an ellipsoid (semi-axes a, b along the
    two vertical joint families, top - zc up) CUT by planes: the joint faces (two vertical families with a batter,
    the sheeting top) cut deep (s 0.86-0.93 of the ellipsoid's support: broad, near-flat faces) and 6-10 fracture
    facets cut shallow (0.93-0.985). Everything not cut stays ellipsoid; the lobe's SDF opening then rounds the
    arrises where the cuts meet. (l1-l3 box planes read as crates / pyramids; l4-l6 planes alone as prisms.)"""
    u, v, w, cc, (A, B, C) = _ellipsoid(L, yaw)
    R = np.stack([u, v, w], 1)

    def support(n):
        nl = R.T @ n
        return float(n @ cc) + math.sqrt((A * nl[0]) ** 2 + (B * nl[1]) ** 2 + (C * nl[2]) ** 2)

    planes = []
    s_f = L.get("s_family", (0.78, 0.85))
    bat = float(L.get("batter", 10.0))
    for n0 in (u, -u, v, -v):
        be = math.radians(bat + rng.uniform(-6, 6))
        n = jitter(unit(n0 * math.cos(be) + w * math.sin(be)), float(L.get("jitter_deg", 5.0)), rng)
        planes.append((n, float(n @ cc) + (support(n) - float(n @ cc)) * rng.uniform(*s_f)))
    su, sv = L.get("slope", (0.0, 0.0))
    tn = jitter(unit(-su * u - sv * v + w), 3.0, rng)
    planes.append((tn, float(tn @ cc) + (support(tn) - float(tn @ cc)) * rng.uniform(*L.get("s_top", (0.84, 0.90)))))
    planes.append((-w, -float(L.get("bot", -0.12))))
    s_x = L.get("s_extra", (0.87, 0.94))
    k = 0
    tries = 0
    while k < int(L.get("facets", 8)) and tries < 400:
        tries += 1
        n = unit(rng.normal(0, 1, 3))
        if n[2] < -0.35:
            continue
        if any(float(n @ p[0]) > 0.93 for p in planes):
            continue
        planes.append((n, float(n @ cc) + (support(n) - float(n @ cc)) * rng.uniform(*s_x)))
        k += 1
    return planes


def corestone_points(L: Dict, yaw: float, planes, level=4):
    """The lobe as points: the ellipsoid (icosphere level ``level``) with every point beyond a cut plane projected
    onto it (the hull of the result = ellipsoid clipped by the planes)."""
    from rock import icosphere
    u, v, w, cc, (A, B, C) = _ellipsoid(L, yaw)
    D, _ = icosphere(level)
    P = cc + (D[:, 0:1] * A) * u + (D[:, 1:2] * B) * v + (D[:, 2:3] * C) * w
    for _ in range(3):
        for n, d in planes:
            s = P @ n - d
            over = s > 0
            P[over] -= s[over, None] * n[None, :]
    return P


def hull_mesh(P):
    """Closed triangulated convex hull (bmesh) -> (V, F)."""
    bm = bmesh.new()
    for p in np.unique(np.round(np.asarray(P, float), 6), axis=0):
        bm.verts.new(tuple(map(float, p)))
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    for g in res.get("geom_interior", []) + res.get("geom_unused", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid:
            bm.verts.remove(g)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def cutter_planes(lobe_V, n, depth_share, margin=0.08):
    """A fresh-fracture chip as a convex CUTTER solid (SDF difference): the half-space beyond the chip plane,
    boxed to the lobe's corner region only (a small solid keeps the narrow band small)."""
    n = unit(n)
    s = lobe_V @ n
    d = float(s.max() - depth_share * (s.max() - s.min()))
    beyond = lobe_V[s > d - 0.04]
    lo = beyond.min(0) - margin
    hi = beyond.max(0) + margin
    planes = [(-n, -d)]
    for k in range(3):
        e = np.zeros(3)
        e[k] = 1.0
        planes += [(e, float(hi[k])), (-e, float(-lo[k]))]
    return planes, d


def crack_wedge(path, m, depth, mouth_w, tip_w=0.002, out=0.06):
    """A crack along a surface polyline ``path`` (k >= 2 points) as convex wedges, one per segment: the crack plane
    contains the segment and the opening direction ``m`` (outward, unit); the wedge is ``mouth_w`` wide at the
    surface (a scalar or one width per path point, so the crack can taper shut at its ends; wider outside the
    surface) and ``tip_w`` at ``depth`` inward (also scalar or per point). Returns a list of point clouds."""
    path = np.asarray(path, float)
    m = unit(m)
    W = np.broadcast_to(np.asarray(mouth_w, float), (len(path),))
    Dp = np.broadcast_to(np.asarray(depth, float), (len(path),))
    out_pts = []
    for k in range(len(path) - 1):
        A, B = path[k], path[k + 1]
        t = unit(B - A)
        mm = unit(m - t * float(t @ m))
        n = unit(np.cross(t, mm))
        pts = []
        for P, wk, dk in ((A, W[k], Dp[k]), (B, W[k + 1], Dp[k + 1])):
            wo = wk * 0.5 * (1.0 + out / max(dk, 1e-3))
            pts += [P + mm * out + n * wo, P + mm * out - n * wo,
                    P - mm * dk + n * tip_w * 0.5, P - mm * dk - n * tip_w * 0.5]
        out_pts.append(np.array(pts))
    return out_pts


def surface_point(lobe_planes_list, start, direction, step=0.004, max_len=3.0):
    """March from ``start`` along ``direction`` until inside the union of the lobe polytopes (plane SDF)."""
    p = np.asarray(start, float).copy()
    d = unit(direction)
    for _ in range(int(max_len / step)):
        s = min(float(plane_sdf(p[None], pl)[0]) for pl in lobe_planes_list)
        if s <= 0:
            return p
        p = p + d * max(step, 0.9 * s)
    return None


# ----------------------------------------------------------------------------------------------- SDF (steps 2-5)

def _mesh_object(name, V, F, coll):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(map(int, f)) for f in F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def sdf_rock(lobes: List[Tuple[np.ndarray, np.ndarray, float]], cutters: List[Tuple[np.ndarray, np.ndarray]],
             cracks: List[Tuple[np.ndarray, np.ndarray]], voxel=0.005, close_r=0.02, lip_r=0.008):
    """lobes: [(V, F, r_open)]; cutters / cracks: [(V, F)] convex solids to subtract. Returns (V, F triangles) of
    the Grid to Mesh surface (threshold 0) and timing."""
    import time
    t0 = time.time()
    coll = bpy.data.collections.new("__rock_sdf")
    bpy.context.scene.collection.children.link(coll)
    rmax = max(r for _, _, r in lobes)
    band = int(math.ceil(max(rmax, close_r, lip_r) / voxel)) + 6          # study P15: band >= r / voxel + 3
    ng = bpy.data.node_groups.new("__DKN_RockSDF", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, Lk = ng.nodes, ng.links
    go = N.new("NodeGroupOutput")
    objs = []

    def grid_of(V, F, name):
        ob = _mesh_object(name, V, F, coll)
        objs.append(ob)
        oi = N.new("GeometryNodeObjectInfo")
        oi.transform_space = "ORIGINAL"
        oi.inputs["Object"].default_value = ob
        m = N.new("GeometryNodeMeshToSDFGrid")
        m.inputs["Voxel Size"].default_value = voxel
        m.inputs["Band Width"].default_value = band
        Lk.new(oi.outputs["Geometry"], m.inputs["Mesh"])
        return m.outputs[0]

    def offset(sock, d):
        n = N.new("GeometryNodeSDFGridOffset")
        n.inputs["Distance"].default_value = d
        Lk.new(sock, n.inputs["Grid"])
        return n.outputs[0]

    def boolean(op, a, bs):
        n = N.new("GeometryNodeSDFGridBoolean")
        n.operation = op
        # probe (5.2): UNION / INTERSECT show only the multi-input (identifier "Grid 2", named "Grid");
        # DIFFERENCE subtracts every "Grid 2" link from "Grid 1"
        if op == "DIFFERENCE":
            Lk.new(a, n.inputs[0])
        else:
            Lk.new(a, n.inputs[1])
        for b in bs:
            Lk.new(b, n.inputs[1])
        return n.outputs[0]

    lobe_grids = []
    for k, (V, F, r) in enumerate(lobes):
        g = grid_of(V, F, f"__lobe{k}")
        if r > 0:
            g = offset(offset(g, -r), r)             # opening: erode then dilate (probe: + Distance grows)
        lobe_grids.append(g)
    g = lobe_grids[0] if len(lobe_grids) == 1 else boolean("UNION", lobe_grids[0], lobe_grids[1:])
    if close_r > 0:
        g = offset(offset(g, close_r), -close_r)      # closing: dilate then erode -> fillets the joins
    subs = [grid_of(V, F, f"__cut{k}") for k, (V, F) in enumerate(cutters)]
    subs += [grid_of(V, F, f"__crack{k}") for k, (V, F) in enumerate(cracks)]
    if subs:
        g = boolean("DIFFERENCE", g, subs)
    if lip_r > 0:
        g = offset(offset(g, -lip_r), lip_r)          # opening: the cut lips round
    gm = N.new("GeometryNodeGridToMesh")
    gm.inputs["Threshold"].default_value = 0.0
    gm.inputs["Adaptivity"].default_value = 0.0
    Lk.new(g, gm.inputs["Grid"])
    Lk.new(gm.outputs[0], go.inputs[0])
    host_me = bpy.data.meshes.new("__rock_host")
    host = bpy.data.objects.new("__rock_host", host_me)
    coll.objects.link(host)
    md = host.modifiers.new("sdf", "NODES")
    md.node_group = ng
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = host.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts], float)
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    bpy.data.meshes.remove(me)
    for ob in objs + [host]:
        d = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(d)
    bpy.data.collections.remove(coll)
    bpy.data.node_groups.remove(ng)
    return V, F, {"voxel": voxel, "band": band, "seconds": round(time.time() - t0, 2), "tris": int(len(F))}


# ----------------------------------------------------------------------------------------------- mesh analysis

def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def edges_of(F):
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E.sort(1)
    return np.unique(E, axis=0)


def smooth_field(x, E, n_iter=2):
    x = np.asarray(x, float).copy()
    deg = np.bincount(E.ravel(), minlength=len(x)).astype(float)
    for _ in range(n_iter):
        acc = np.zeros_like(x)
        np.add.at(acc, E[:, 0], x[E[:, 1]])
        np.add.at(acc, E[:, 1], x[E[:, 0]])
        dd = np.maximum(deg, 1)
        x = 0.5 * x + 0.5 * acc / (dd[:, None] if x.ndim > 1 else dd)
    return x


def mean_curvature(V, F, E=None, N=None, n_smooth=3):
    """Signed mean curvature (1/m) by the umbrella operator: + convex (arris), - concave (cleft)."""
    if E is None:
        E = edges_of(F)
    if N is None:
        N = vertex_normals(V, F)
    deg = np.bincount(E.ravel(), minlength=len(V)).astype(float)
    acc = np.zeros_like(V)
    np.add.at(acc, E[:, 0], V[E[:, 1]])
    np.add.at(acc, E[:, 1], V[E[:, 0]])
    lap = acc / np.maximum(deg, 1)[:, None] - V
    el = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    e2 = np.zeros(len(V))
    np.add.at(e2, E[:, 0], el ** 2)
    np.add.at(e2, E[:, 1], el ** 2)
    e2 = e2 / np.maximum(deg, 1)
    H = -2.0 * (lap * N).sum(1) / np.maximum(e2, 1e-12)
    return smooth_field(H, E, n_smooth)


def plane_sdf(P, planes):
    """Approximate signed distance to a convex polytope (max of the plane distances; exact inside)."""
    n = np.array([p[0] for p in planes])
    d = np.array([p[1] for p in planes])
    return (P @ n.T - d).max(1)


def point_segment_dist(P, A, B):
    AB = B - A
    t = np.clip(((P - A) @ AB) / max(float(AB @ AB), 1e-12), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1), t


def point_in_poly(px, py, poly):
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = (y1 > py) != (y2 > py)
        xint = (x2 - x1) * (py - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1
        inside ^= cond & (px < xint)
    return inside


def rasterise_iou(V, poly_xy, axes=(0, 2), px=0.01):
    """SG15: silhouette IoU of a DENSE surface (vertex spacing < px) projected on ``axes`` vs a traced polygon
    (metres), px pixels: the vertices are splatted and the mask closed by one pixel (numpy only)."""
    P = np.asarray(V, float)[:, list(axes)]
    poly = np.asarray(poly_xy, float)
    lo = np.minimum(P.min(0), poly.min(0)) - 0.05
    hi = np.maximum(P.max(0), poly.max(0)) + 0.05
    W, H = (np.ceil((hi - lo) / px).astype(int) + 1)
    A = np.zeros((H, W), bool)
    ix = ((P[:, 0] - lo[0]) / px).astype(int)
    iy = ((hi[1] - P[:, 1]) / px).astype(int)
    A[iy, ix] = True
    # closing (dilate then erode, 3x3)
    def dil(M):
        O = M.copy()
        O[1:] |= M[:-1]; O[:-1] |= M[1:]; O[:, 1:] |= M[:, :-1]; O[:, :-1] |= M[:, 1:]
        return O
    A = ~dil(~dil(A))
    gx, gy = np.meshgrid(lo[0] + (np.arange(W) + 0.5) * px, hi[1] - (np.arange(H) + 0.5) * px)
    B = point_in_poly(gx, gy, poly)
    return float((A & B).sum() / max((A | B).sum(), 1)), A, B
