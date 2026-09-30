"""Conifer tufts as real geometry, instanced on shoot tips (numpy only). TREE_BUILDING_STUDY.md 4.7 and 8.4.

One tuft = the needles of the outer shoot plus a white candle (winter bud):
  * fascicles of TWO needles on a 137.5 degree spiral along the last ``shoot_len`` of the shoot;
  * the two needles of a fascicle share ONE welded base vertex inside the sheath (no coincident vertices, P39);
  * each needle is a 2-triangle strip (base, left/right at 42 %, tip) about 1 mm wide, bent once (droop), twisted;
  * needles near the tip point forward (30 deg), lower ones splay out (70 deg);
  * a 4-sided candle cone at the tip.
Local frame: the shoot runs along +Z and ends at the origin.

UV0 (needle texture, see make_pine_textures): every needle (and the candle) gets its own cell of
(1/CELLS_U x 1/CELLS_V) tiles; the texture repeats one needle image per cell, so a needle looks the same in any
cell, and no two needles share UV space (the pipeline's SAT overlap test can run on the whole foliage mesh).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

CELLS_U = 64
CELLS_V = 8
GOLDEN = np.deg2rad(137.5)


@dataclass
class Tuft:
    V: np.ndarray        # (nv, 3)
    T: np.ndarray        # (nt, 3)
    uv: np.ndarray       # (nt, 3, 2) UV inside a unit cell (0-1)
    cell: np.ndarray     # (nt,) local cell index (needle id; the candle uses its own cell)
    n_cells: int
    kind: np.ndarray     # (nv,) 0 needle base, 1 needle mid, 2 needle tip, 3 candle
    along: np.ndarray    # (nv,) 0 at the shoot base .. 1 at the tip (for the hierarchy weight)


def make_tuft(rng: np.random.Generator, n_fasc: int = 20, needle_len: Tuple[float, float] = (0.08, 0.105),
              width: float = 0.0035, shoot_len: float = 0.035, twig_r: float = 0.0035,
              splay: Tuple[float, float] = (86.0, 14.0), candle_len: float = 0.018) -> Tuft:
    verts, tris, uvs, cells, kinds, along = [], [], [], [], [], []

    def add(p, k, a):
        verts.append(np.asarray(p, dtype=np.float64))
        kinds.append(k)
        along.append(a)
        return len(verts) - 1

    cell = 0
    for f in range(n_fasc):
        t = (f + 0.5) / n_fasc
        t = t ** 0.8                                              # more fascicles toward the tip
        z = -shoot_len * (1.0 - t)
        phi = f * GOLDEN + rng.normal(0, 0.12)
        base_dir = np.array([np.cos(phi), np.sin(phi), 0.0])
        b = np.array([0.0, 0.0, z]) + base_dir * twig_r * 0.9
        bi = add(b, 0, t)
        alpha = np.deg2rad(splay[0] + (splay[1] - splay[0]) * t + rng.normal(0, 6))
        for side in (-1, 1):
            az = phi + side * np.deg2rad(rng.uniform(7, 16))
            d = np.array([np.sin(alpha) * np.cos(az), np.sin(alpha) * np.sin(az), np.cos(alpha)])
            L = rng.uniform(*needle_len)
            droop = np.deg2rad(rng.uniform(3, 12))
            d = d * np.cos(droop) - np.array([0, 0, 1.0]) * np.sin(droop)
            d /= np.linalg.norm(d)
            tip = b + d * L
            ref = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0, 0])
            w1 = np.cross(d, ref)
            w1 /= np.linalg.norm(w1)
            w2 = np.cross(d, w1)
            tw = rng.uniform(0, np.pi)
            wv = (np.cos(tw) * w1 + np.sin(tw) * w2) * width
            # one tapering triangle per needle: the welded fascicle base, a second base corner one needle-width
            # away (0.05 mm+ from anything else, P39) and the tip
            ci = add(b + wv + d * 0.004, 1, t)
            ti = add(tip, 2, t)
            tris.append((bi, ci, ti))
            uvs.append(((0.15, 0.04), (0.85, 0.04), (0.5, 0.97)))
            cells.append(cell)
            cell += 1
    # candle: 4-sided cone standing on the tip, its base above every needle base (no coincident vertices)
    cr = 0.0032
    c0 = [add((cr * np.cos(a), cr * np.sin(a), 0.002), 3, 1.0) for a in np.linspace(0, 2 * np.pi, 4, endpoint=False)]
    apex = add((0.0, 0.0, 0.002 + candle_len), 3, 1.0)
    # the candle samples the pale sheath/bud band at the base of the needle image (v < 0.07)
    cuv = [((0.02, 0.006), (0.23, 0.006), (0.125, 0.062)), ((0.27, 0.006), (0.48, 0.006), (0.375, 0.062)),
           ((0.52, 0.006), (0.73, 0.006), (0.625, 0.062)), ((0.77, 0.006), (0.98, 0.006), (0.875, 0.062))]
    for i in range(4):
        tris.append((c0[i], c0[(i + 1) % 4], apex))
        uvs.append(cuv[i])
        cells.append(cell)
    cell += 1
    return Tuft(np.array(verts), np.array(tris, dtype=np.int64), np.array(uvs, dtype=np.float64),
                np.array(cells, dtype=np.int64), cell, np.array(kinds), np.array(along))


def make_burst(rng: np.random.Generator, n_fasc: int = 26, needle_len: Tuple[float, float] = (0.08, 0.10),
               width: float = 0.0022, shoot_len: float = 0.028, twig_r: float = 0.0032,
               cone: Tuple[float, float] = (10.0, 98.0), candle_len: float = 0.016) -> Tuft:
    """f1 needle unit: a RADIAL BURST of straight, rigid 2-needle fascicles (judge r0: needles too soft, droopy and
    wide; the sheet's pads are rosettes from above and upright brushes from the side).

    Fascicles sit on a 137.5 degree spiral along the last ``shoot_len`` of the shoot (+Z, ending at the origin).
    The upper fascicles stand near the axis, the lower ones splay out to just below horizontal, so the burst is a
    wide cone: a star seen from above, a fan seen from the side. Needles are single tapering triangles, straight,
    ``width`` at the base (about half that on average), the two needles of a fascicle welded at the base (P39).
    A pale candle stands in the centre."""
    verts, tris, uvs, cells, kinds, along = [], [], [], [], [], []

    def add(p, k, a):
        verts.append(np.asarray(p, dtype=np.float64))
        kinds.append(k)
        along.append(a)
        return len(verts) - 1

    cell = 0
    for f in range(n_fasc):
        t = (f + 0.5) / n_fasc                     # 0 low on the shoot .. 1 at the tip
        z = -shoot_len * (1.0 - t) ** 0.9
        phi = f * GOLDEN + rng.normal(0, 0.15)
        base_dir = np.array([np.cos(phi), np.sin(phi), 0.0])
        b = np.array([0.0, 0.0, z]) + base_dir * twig_r * 0.9
        bi = add(b, 0, t)
        th = cone[1] + (cone[0] - cone[1]) * t ** 0.8 + rng.normal(0, 7)
        alpha = np.deg2rad(np.clip(th, 3.0, 110.0))
        for side in (-1, 1):
            az = phi + side * np.deg2rad(rng.uniform(5, 13))
            d = np.array([np.sin(alpha) * np.cos(az), np.sin(alpha) * np.sin(az), np.cos(alpha)])
            L = rng.uniform(*needle_len)
            tip = b + d * L
            ref = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0, 0])
            w1 = np.cross(d, ref)
            w1 /= np.linalg.norm(w1)
            w2 = np.cross(d, w1)
            tw = rng.uniform(0, np.pi)
            wv = (np.cos(tw) * w1 + np.sin(tw) * w2) * width * rng.uniform(0.85, 1.1)
            ci = add(b + wv + d * 0.003, 1, t)
            ti = add(tip, 2, t)
            tris.append((bi, ci, ti))
            uvs.append(((0.15, 0.04), (0.85, 0.04), (0.5, 0.97)))
            cells.append(cell)
            cell += 1
    cr = 0.0034
    c0 = [add((cr * np.cos(a), cr * np.sin(a), 0.003), 3, 1.0) for a in np.linspace(0, 2 * np.pi, 4, endpoint=False)]
    apex = add((0.0, 0.0, 0.003 + candle_len), 3, 1.0)
    cuv = [((0.02, 0.006), (0.23, 0.006), (0.125, 0.062)), ((0.27, 0.006), (0.48, 0.006), (0.375, 0.062)),
           ((0.52, 0.006), (0.73, 0.006), (0.625, 0.062)), ((0.77, 0.006), (0.98, 0.006), (0.875, 0.062))]
    for i in range(4):
        tris.append((c0[i], c0[(i + 1) % 4], apex))
        uvs.append(cuv[i])
        cells.append(cell)
    cell += 1
    return Tuft(np.array(verts), np.array(tris, dtype=np.int64), np.array(uvs, dtype=np.float64),
                np.array(cells, dtype=np.int64), cell, np.array(kinds), np.array(along))


def burst_variants(seed: int, counts=(22, 26, 30, 34), needle_len=(0.08, 0.10), width=0.0022) -> List[Tuft]:
    """4 burst variants (study 4.7 / P15) with different fascicle counts and cone spreads."""
    rng = np.random.default_rng(seed)
    cones = [(8.0, 96.0), (12.0, 104.0), (6.0, 90.0), (10.0, 100.0)]
    return [make_burst(rng, n_fasc=c, needle_len=needle_len, width=width, cone=cones[i % 4])
            for i, c in enumerate(counts)]


def make_clump(rng: np.random.Generator, n_blades: int = 12, height: Tuple[float, float] = (0.10, 0.24),
               width: float = 0.005, spread: float = 0.05) -> Tuft:
    """A grass / fern-like ground-cover clump (the sheet shows tufts at every tree's base and at the rock's foot):
    curved blades of 3 segments (6 triangles), bases on a small disc, leaning out. Blade UVs map onto one needle
    cell each (overlap-free like the needles)."""
    verts, tris, uvs, cells, kinds, along = [], [], [], [], [], []
    cell = 0
    for i in range(n_blades):
        a = rng.uniform(0, 2 * np.pi)
        r0 = spread * np.sqrt(rng.random())
        b = np.array([np.cos(a) * r0, np.sin(a) * r0, -0.02])
        H = rng.uniform(*height)
        lean = np.deg2rad(rng.uniform(15, 55))
        az = a + rng.normal(0, 0.5)
        out = np.array([np.cos(az), np.sin(az), 0.0])
        side = np.array([-np.sin(az), np.cos(az), 0.0])
        wid = width * rng.uniform(0.7, 1.4)
        pts = []
        for k in range(4):
            t = k / 3.0
            ang = lean * (0.3 + 0.9 * t)
            p = b + out * H * 0.55 * t * np.sin(ang) * 1.6 + np.array([0, 0, 1.0]) * H * t * np.cos(ang * 0.6)
            pts.append(p)
        vidx = []
        for k, p in enumerate(pts[:-1]):
            wk = wid * (1.0 - k / 3.0)
            vidx.append((len(verts), len(verts) + 1))
            for sgn in (-1, 1):
                verts.append(p + side * sgn * wk * 0.5)
                kinds.append(1)
                along.append(k / 3.0)
        verts.append(pts[-1])
        kinds.append(2)
        along.append(1.0)
        tip = len(verts) - 1
        vs = [(0.15, 0.04), (0.85, 0.04), (0.2, 0.36), (0.8, 0.36), (0.3, 0.67), (0.7, 0.67), (0.5, 0.97)]
        (a0, a1), (b0, b1), (c0, c1) = vidx
        for tri, uv in (((a0, a1, b1), (vs[0], vs[1], vs[3])), ((a0, b1, b0), (vs[0], vs[3], vs[2])),
                        ((b0, b1, c1), (vs[2], vs[3], vs[5])), ((b0, c1, c0), (vs[2], vs[5], vs[4])),
                        ((c0, c1, tip), (vs[4], vs[5], vs[6]))):
            tris.append(tri)
            uvs.append(uv)
            cells.append(cell)
        cell += 1
    return Tuft(np.array(verts), np.array(tris, dtype=np.int64), np.array(uvs, dtype=np.float64),
                np.array(cells, dtype=np.int64), cell, np.array(kinds), np.array(along))


def tuft_variants(seed: int, counts=(28, 34, 40, 46)) -> List[Tuft]:
    """3-5 variants (study 4.7 / P15). Fascicle counts span the momiage range up to the denser brushes."""
    rng = np.random.default_rng(seed)
    return [make_tuft(rng, n_fasc=c) for c in counts]


def frame_from_dir(d: np.ndarray, roll: float) -> np.ndarray:
    """3x3 rotation taking +Z to ``d`` with a roll about it."""
    d = d / np.linalg.norm(d)
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.97 else np.array([1.0, 0.0, 0.0])
    x = np.cross(ref, d)
    x /= np.linalg.norm(x)
    y = np.cross(d, x)
    c, s = np.cos(roll), np.sin(roll)
    x2 = c * x + s * y
    y2 = -s * x + c * y
    return np.stack([x2, y2, d], axis=1)


@dataclass
class FoliageMesh:
    V: np.ndarray
    T: np.ndarray
    uv0: np.ndarray       # (nt, 3, 2) in tiles
    tuft_id: np.ndarray   # (nv,)
    pad_id: np.ndarray    # (nv,)
    along: np.ndarray     # (nv,)
    kind: np.ndarray      # (nv,)
    cells_used: int
    grid_w: int           # cells per row
    tri_var: np.ndarray = None   # (nt,) variant index of the unit each triangle came from


def instance(tufts: List[Tuft], tips: List[Dict], rng: np.random.Generator) -> FoliageMesh:
    """Place one tuft per tip dict {p, d, pad, variant?}. Scale 0.88-1.12 and a random roll per instance."""
    Vs, Ts, UVs, tid, pid, alg, knd, cells, tvar = [], [], [], [], [], [], [], [], []
    off = 0
    cell_off = 0
    for i, tip in enumerate(tips):
        vi = tip.get("variant", int(rng.integers(len(tufts))))
        tf = tufts[vi]
        tvar.append(np.full(len(tf.T), vi))
        Rm = frame_from_dir(np.asarray(tip["d"], dtype=np.float64), rng.uniform(0, 2 * np.pi))
        sc = rng.uniform(0.88, 1.12) * float(tip.get("scale", 1.0))
        V = (tf.V * sc) @ Rm.T + np.asarray(tip["p"], dtype=np.float64)
        Vs.append(V)
        Ts.append(tf.T + off)
        UVs.append(tf.uv)
        cells.append(tf.cell + cell_off)
        tid.append(np.full(len(V), i))
        pid.append(np.full(len(V), tip["pad"]))
        alg.append(tf.along)
        knd.append(tf.kind)
        off += len(V)
        cell_off += tf.n_cells
    cell = np.concatenate(cells)
    grid_w = CELLS_U * max(1, int(np.ceil(np.sqrt(cell_off / (CELLS_U * CELLS_V)))))
    cu = cell % grid_w
    cv = cell // grid_w
    uv = np.concatenate(UVs)
    uv0 = np.empty_like(uv)
    uv0[..., 0] = (cu[:, None] + uv[..., 0]) / CELLS_U
    uv0[..., 1] = (cv[:, None] + uv[..., 1]) / CELLS_V
    return FoliageMesh(np.vstack(Vs), np.vstack(Ts), uv0, np.concatenate(tid), np.concatenate(pid),
                       np.concatenate(alg), np.concatenate(knd), cell_off, grid_w, np.concatenate(tvar))


def volume_normals(V: np.ndarray, T: np.ndarray, env_normal, blend: float = 0.6) -> np.ndarray:
    """Per-vertex normals bent toward the pad's proxy ellipsoid: n = normalize(lerp(n_geo, n_ell, blend)).
    ``env_normal(P) -> (n,3)`` gives the ellipsoid normal per vertex (study 4.7)."""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, T[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    ne = env_normal(V)
    sign = np.sign(np.sum(vn * ne, axis=1, keepdims=True))
    sign[sign == 0] = 1.0
    n = (1 - blend) * vn * sign + blend * ne
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def pad_core(env, rng: np.random.Generator, shrink=(0.55, 0.45, 0.3), bump: float = 0.14, level: int = 2):
    """An inset, bumpy shell inside a pad: the dense inner needle mass that geometry needles at 2 mm cannot cover at
    garden distances (deviation recorded in BUILD_NOTES: the sheet's pads read as solid masses). It sits below the
    outer tuft layer, so close up the tufts and twigs stay in front of it. Returns (V, T)."""
    from rock import icosphere
    D, T = icosphere(level)
    L = np.empty_like(D)
    L[:, 0] = D[:, 0] * env.rx * shrink[0]
    L[:, 1] = D[:, 1] * env.half_y(L[:, 0]) * shrink[0]
    tz = env.top_at(L[:, 0]) / np.sqrt(np.clip(1.0 - D[:, 0] ** 2, 0.05, 1.0))
    bz = env.bot_at(L[:, 0])
    L[:, 2] = np.where(D[:, 2] > 0, D[:, 2] * np.minimum(tz, env.rz_top) * shrink[1], D[:, 2] * bz * shrink[2])
    L[:, 2] -= 0.02 * env.rz_top
    L *= (1.0 + bump * (rng.random(len(L)) - 0.5) * 2)[:, None] ** 0.5
    return env.world_dir(L) + env.centre, T


def append_parts(fm: FoliageMesh, parts: List[Dict]) -> FoliageMesh:
    """Append extra triangle sets (pad cores) to a FoliageMesh; every triangle gets its own needle cell and samples
    the green body band of the needle image."""
    Vs, Ts, UVs, tid, pid, alg, knd = [fm.V], [fm.T], [fm.uv0], [fm.tuft_id], [fm.pad_id], [fm.along], [fm.kind]
    off = len(fm.V)
    cell = fm.cells_used
    base_uv = np.array([(0.2, 0.35), (0.8, 0.35), (0.5, 0.75)])
    next_id = int(fm.tuft_id.max()) + 1 if len(fm.tuft_id) else 0
    for k, p in enumerate(parts):
        V, T = p["V"], p["T"]
        c = cell + np.arange(len(T))
        cu = c % fm.grid_w
        cv = c // fm.grid_w
        uv = np.empty((len(T), 3, 2))
        uv[..., 0] = (cu[:, None] + base_uv[None, :, 0]) / CELLS_U
        uv[..., 1] = (cv[:, None] + base_uv[None, :, 1]) / CELLS_V
        Vs.append(V)
        Ts.append(T + off)
        UVs.append(uv)
        tid.append(np.full(len(V), next_id + k))
        pid.append(np.full(len(V), p["pad"]))
        alg.append(np.full(len(V), 0.5))
        knd.append(np.full(len(V), 4))
        off += len(V)
        cell += len(T)
    return FoliageMesh(np.vstack(Vs), np.vstack(Ts), np.vstack(UVs), np.concatenate(tid), np.concatenate(pid),
                       np.concatenate(alg), np.concatenate(knd), cell, fm.grid_w)
