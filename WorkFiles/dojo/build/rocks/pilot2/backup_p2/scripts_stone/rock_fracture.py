"""True fracture of a sheared granite mass for cliff chunks (pilot 2; STONE_BUILDING_STUDY.md 3.9 cliff rock, 4.9.3
own Voronoi fracture). bpy (mathutils) + numpy; returns convex plane sets / closed meshes for stone_sdf.SDFGraph.

Pilot 1 split the hull on an orthogonal grid of columns and beds and read as masonry. Here:
- the joint frame is SHEARED (yawed, the vertical family leaning) and the cells are a Voronoi partition of seeds on
  a jittered, anisotropic lattice (tall columns), so neighbouring blocks meet on planes of many directions;
- every shared face is tilted by its own random rotation (applied once per pair, so the partition stays a
  partition: +n for one cell, -n for the other);
- each block takes the hull eroded by its OWN recess (0-0.40 m: blocks protrude and recede by tens of cm, lower
  blocks prouder so ledges step back up the face), is shrunk by half a joint gap, and is cut by 1-2 tilted fracture
  facets on its exposed side (tilted faces, never parallel to the hull);
- a core (the hull eroded by more than the deepest recess) fills behind, so joints are deep re-entrant slots, not
  holes through the rock;
- chips break the arrises (stage 2) and a little rubble of the same rock lies at the foot.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

import stone_sdf as sd


def _rot_about(n, axis, deg):
    a = math.radians(deg)
    axis = sd.unit(axis)
    return sd.unit(n * math.cos(a) + np.cross(axis, n) * math.sin(a) + axis * float(axis @ n) * (1 - math.cos(a)))


def frame(yaw_deg, lean_deg, lean_dir_deg):
    """Rows of A map world p to frame q = A p (rotation: yaw about z, then the vertical axis leans)."""
    y = math.radians(yaw_deg)
    Rz = np.array([[math.cos(y), math.sin(y), 0], [-math.sin(y), math.cos(y), 0], [0, 0, 1.0]])
    ax = sd.rotz(np.array([1.0, 0.0, 0.0]), lean_dir_deg)
    l = math.radians(lean_deg)
    # rotation about ax by lean
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    Rl = np.eye(3) + math.sin(l) * K + (1 - math.cos(l)) * K @ K
    return Rl @ Rz


def seeds(lo, hi, spec, rng, A):
    """Jittered anisotropic lattice in the frame: columns ~col_w wide, rows ~row_d deep, levels per column drawn
    from level_h (random count per column so bed joints never run straight across)."""
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    Q = corners @ A.T
    qlo, qhi = Q.min(0), Q.max(0)
    nx = max(2, int(round((qhi[0] - qlo[0]) / spec["col_w"])))
    ny = max(1, int(round((qhi[1] - qlo[1]) / spec["row_d"])))
    out = []
    for ix in range(nx):
        for iy in range(ny):
            hz = qhi[2] - qlo[2]
            nz = int(rng.integers(spec["levels"][0], spec["levels"][1] + 1))
            cuts = np.sort(rng.uniform(0.18, 0.92, nz - 1)) if nz > 1 else np.array([])
            edges = np.concatenate([[0.0], cuts, [1.0]])
            for k in range(nz):
                qx = qlo[0] + (ix + 0.5 + rng.uniform(-spec["jit"], spec["jit"])) * (qhi[0] - qlo[0]) / nx
                qy = qlo[1] + (iy + 0.5 + rng.uniform(-spec["jit"], spec["jit"])) * (qhi[1] - qlo[1]) / ny
                qz = qlo[2] + (0.5 * (edges[k] + edges[k + 1]) + rng.uniform(-0.04, 0.04)) * hz
                out.append((np.array([qx, qy, qz]), ix, iy, k, nz))
    return out, (nx, ny)


def cells(lo, hi, spec, rng):
    """Voronoi cells (anisotropic metric: z compressed by ``zstretch`` in the frame) with tilted shared faces.
    Returns a list of dicts: planes [(n, d)] in world space (n.p <= d inside), seed (world), column index, level,
    number of levels in the column, top flag, V (polytope vertices)."""
    A = frame(spec["yaw_deg"], spec["lean_deg"], spec["lean_dir_deg"])
    S, (nx, ny) = seeds(lo, hi, spec, rng, A)
    zs = spec["zstretch"]
    M = np.diag([1.0, 1.0, 1.0 / zs]) @ A            # metric space m = M p
    Minv_T = M.T                                     # plane n_m . m <= d  ->  (M^T n_m) . p <= d
    ms = np.array([np.diag([1.0, 1.0, 1.0 / zs]) @ s[0] for s in S])
    box = []
    for k in range(3):
        e = np.zeros(3)
        e[k] = 1.0
        box += [(e, float(hi[k])), (-e, float(-lo[k]))]
    n = len(S)
    pair = {}
    for i in range(n):
        for j in range(i + 1, n):
            dvec = ms[j] - ms[i]
            dist = float(np.linalg.norm(dvec))
            if dist > spec.get("neigh", 3.0):
                continue
            nm = dvec / dist
            mid = 0.5 * (ms[i] + ms[j])
            # tilt the shared face about a random in-plane axis
            ax = sd.unit(np.cross(nm, rng.normal(0, 1, 3)))
            nm2 = _rot_about(nm, ax, rng.uniform(-spec["tilt"], spec["tilt"]))
            npw = Minv_T @ nm2
            L = float(np.linalg.norm(npw))
            pair[(i, j)] = (npw / L, float(nm2 @ mid) / L)
    out = []
    for i in range(n):
        pl = list(box)
        for (a, b), (nn, dd) in pair.items():
            if a == i:
                pl.append((nn, dd))
            elif b == i:
                pl.append((-nn, -dd))
        V = sd.polytope_vertices(pl)
        if len(V) < 4:
            continue
        seed_world = np.linalg.solve(A, np.array([S[i][0][0], S[i][0][1], S[i][0][2]]))
        out.append({"planes": pl, "seed": seed_world, "ix": S[i][1], "iy": S[i][2], "level": S[i][3],
                    "nlev": S[i][4], "top": S[i][3] == S[i][4] - 1, "V": V, "nx": nx, "ny": ny})
    return out, A


def shrink(planes, gap, keep_box=6):
    """Offset every non-box plane inward by ``gap`` (half the joint width)."""
    return [(n, d) if k < keep_box else (n, d - gap) for k, (n, d) in enumerate(planes)]


def recess_for(c, spec, rng):
    """Recess (m) of a block, negative = proud of the hull. Bands by the block's level in its column (lower blocks
    prouder, upper blocks set back: the sheet's ledges), and a wide random spread inside each band so neighbours
    protrude and recede by tens of cm (pilot 2 round 2: a level-only recess left a flat wall)."""
    t = c["level"] / max(c["nlev"] - 1, 1)
    lo, hi = spec["recess"]
    base = lo + (hi - lo) * (0.15 + 0.6 * t)
    return float(np.clip(base + rng.uniform(-0.5, 0.5) * spec["recess_jit"], lo, hi))


def exposed_dirs(c, centre_xy):
    v = c["seed"][:2] - centre_xy
    out = []
    if np.linalg.norm(v) > 1e-6:
        h = np.array([v[0], v[1], 0.0])
        out.append(sd.unit(h))
    if c["top"]:
        out.append(np.array([0.0, 0.0, 1.0]))
    return out


def facet_planes(c, Pin, centre_xy, spec, rng):
    """1-2 tilted fracture facets on a block's exposed side: plane normals 12-40 deg off the outward direction,
    cutting 4-18 cm under the block's support (a tilted face, deepest at the edge it tilts toward)."""
    dirs = exposed_dirs(c, centre_xy)
    out = []
    if not dirs or len(Pin) < 20:
        return out
    k = int(rng.integers(spec["facets"][0], spec["facets"][1] + 1))
    for _ in range(k):
        d0 = dirs[int(rng.integers(len(dirs)))]
        ax = sd.unit(np.cross(d0, rng.normal(0, 1, 3)))
        n = _rot_about(d0, ax, rng.uniform(*spec["facet_tilt"]))
        s = Pin @ n
        dd = float(s.max() - rng.uniform(*spec["facet_depth"]))
        out.append((n, dd))
    return out


def rubble(lo, hi, centre, rng, count, size=(0.10, 0.32), ring=(0.0, 0.25)):
    """Small fractured chunks of the same rock at the foot: convex hulls of jittered boxes, partly buried."""
    out = []
    for _ in range(count):
        side = rng.choice(["front", "left", "right", "front"])
        s = float(np.exp(rng.uniform(math.log(size[0]), math.log(size[1]))))
        if side == "front":
            x = rng.uniform(lo[0] + 0.1, hi[0] - 0.1)
            y = lo[1] - rng.uniform(*ring) + s * 0.25
        elif side == "left":
            x = lo[0] - rng.uniform(*ring) + s * 0.25
            y = rng.uniform(lo[1] + 0.1, hi[1] - 0.1)
        else:
            x = hi[0] + rng.uniform(*ring) - s * 0.25
            y = rng.uniform(lo[1] + 0.1, hi[1] - 0.1)
        c = np.array([x, y, s * rng.uniform(0.05, 0.25)])
        P = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    P.append(c + np.array([sx * s * rng.uniform(0.35, 0.6), sy * s * rng.uniform(0.3, 0.55),
                                           sz * s * rng.uniform(0.25, 0.45)]))
        P = np.array(P)
        yaw = rng.uniform(0, 360)
        P = np.array([c + sd.rotz(p - c, yaw) for p in P])
        # a couple of fresh fracture planes through the box: angular, not a cube
        V, F = sd.hull_mesh(P)
        out.append((V, F))
    return out


def edge_chips(V, F, H, rng, count, size=(0.02, 0.07), zmin=0.1):
    """Chips off the sharp arrises: at high-convexity vertices, a small convex cutter (the hull of points scattered
    in a flattened ellipsoid centred a little outside the surface) bites a conchoidal scar with an irregular outline
    (pilot 2 round 2: box-bounded half-spaces left square pockets)."""
    N = sd.vertex_normals(V, F)
    idx = np.nonzero((H > np.percentile(H, 97)) & (V[:, 2] > zmin))[0]
    if not len(idx):
        return []
    pick = rng.choice(idx, min(count, len(idx)), replace=False)
    out = []
    for i in pick:
        p = V[i]
        n = sd.jitter(N[i], 30.0, rng)
        s = float(np.exp(rng.uniform(math.log(size[0]), math.log(size[1]))))
        t = sd.unit(np.cross(n, rng.normal(0, 1, 3)))
        b = np.cross(n, t)
        cen = p + n * s * rng.uniform(0.25, 0.55)
        pts = []
        for _ in range(16):
            a = rng.uniform(0, 2 * math.pi)
            r = s * rng.uniform(0.6, 1.0)
            pts.append(cen + (t * math.cos(a) * rng.uniform(0.8, 1.3) + b * math.sin(a)) * r +
                       n * rng.uniform(-0.55, 0.6) * s)
        out.append(sd.hull_mesh(np.array(pts)))
    return out


def rubble_at_foot(Vh, rng, count, size=(0.10, 0.30)):
    """Rubble chunks of the same rock touching the foot: each sits just outside the hull's foot outline in a random
    direction (the outermost hull point of that direction sector below 0.25 m), sunk a little into the ground and
    overlapping the rock face by a few cm, so it reads as fallen from it, not scattered. Mostly at the front and
    the ends (the sheet's chunks drop rubble at the front)."""
    foot = Vh[Vh[:, 2] < 0.25]
    c = foot.mean(0)
    ang = np.arctan2(foot[:, 1] - c[1], foot[:, 0] - c[0])
    out = []
    for _ in range(count):
        th = rng.uniform(-math.pi * 0.95, -math.pi * 0.05) if rng.uniform() < 0.75 else rng.uniform(-math.pi,
                                                                                                    math.pi)
        sec = np.abs((ang - th + math.pi) % (2 * math.pi) - math.pi) < 0.12
        if not sec.any():
            continue
        P = foot[sec]
        rr = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
        edge = P[np.argmax(rr)]
        s = float(np.exp(rng.uniform(math.log(size[0]), math.log(size[1]))))
        d = np.array([math.cos(th), math.sin(th), 0.0])
        cen = edge + d * s * rng.uniform(0.15, 0.45)
        cen[2] = s * rng.uniform(0.05, 0.2)
        pts = []
        for _k in range(14):
            v = sd.unit(rng.normal(0, 1, 3)) * np.array([s * 0.55, s * 0.45, s * 0.35])
            pts.append(cen + v)
        pts = np.array(pts)
        yaw = rng.uniform(0, 360)
        pts = np.array([cen + sd.rotz(p - cen, yaw) for p in pts])
        out.append(sd.hull_mesh(pts))
    return out
