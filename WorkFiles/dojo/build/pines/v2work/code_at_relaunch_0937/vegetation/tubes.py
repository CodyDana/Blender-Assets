"""Branch tubes: rings on parallel-transport frames, sunk collared junctions, bark UV0 and plate displacement.

TREE_BUILDING_STUDY.md 4.5 / 4.6 (stage b). numpy only; the Blender side (meshio.py) turns the arrays into a mesh.

UV0 (tiling bark, in tile units):
  * U around: u = k * i / n. k is an INTEGER per branch (constant along it) when the circumference is at least
    half a tile, otherwise the fraction circumference / tile (thin twigs: the seam is sub-pixel).
  * V along: v = v0 + arclength / tile. An integer-k child starts at its parent's V (mod 1) at the attachment,
    so the bark does not restart at forks.
  * Every branch then gets an offset of whole tiles (integer-k) or any offset (fractional twigs) so that no two
    branches share UV space: the bark still tiles exactly (a whole-tile shift does not change a tiling texture)
    and UV0 no longer overlaps, so the pipeline's own SAT overlap test runs and passes on the trunk mesh.
  * Plates are GEOMETRY (house rule, study 4.5): the vertices are displaced by the same tiling height map the bark
    texture is made from, sampled at the vertex's UV0, so texture fissures and geometric fissures line up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from skeleton import Branch, arclength, pt_frames, resample


@dataclass
class TubeParams:
    tile_m: float = 1.0            # bark tile size (m) in U and V
    sink: float = 0.6              # sink a child's first ring this share of the parent radius (study 4.5)
    collar_amp: float = 0.35       # collar flare x1.35 ...
    collar_len: float = 1.2        # ... over 1.2 diameters
    flare_amp: float = 0.12        # extra root flare on top of the traced girth (G8: flare >= 1.3)
    flare_len: float = 1.5         # flare decay height as a multiple of the base radius
    plate_ratio: float = 0.10      # plate relief depth as a share of the radius ...
    plate_max: float = 0.028       # ... capped (m)
    plate_min_r: float = 0.07      # no geometric plates below this radius
    lobes: float = 0.05            # low-frequency trunk lobes (share of radius)
    cap_twig_r: float = 0.02       # end caps get a centre vertex
    plate_spacing: float = 0.025   # ring spacing where plates are geometry
    twist: float = 0.0             # lobe twist (radians per metre) on the trunk
    buttress: float = 0.0          # buttress lobe amplitude at the root flare (share of radius)
    ring_len: float = 0.028        # around-spacing of trunk ring vertices (m)
    ellipse_y: float = 1.0         # v2: trunk section squashed along world Y (side-panel girth / front girth)


def ring_count(r: float, ring_len: float = 0.028) -> int:
    if r >= 0.12:
        return int(np.clip(round(2 * np.pi * r / ring_len), 24, 96))
    if r >= 0.045:
        return int(np.clip(round(2 * np.pi * r / max(ring_len, 0.024)), 12, 32))
    if r >= 0.02:
        return 6
    if r >= 0.011:
        return 5
    if r >= 0.0075:
        return 4
    return 3


def ring_spacing(r: float, plates: bool, plate_spacing: float = 0.025) -> float:
    if plates:
        return plate_spacing
    if r < 0.02:
        return 0.07        # twigs: the colonisation step is 3.5-5 cm; every other node is enough
    return float(np.clip(1.2 * r, 0.03, 0.08))


def bilinear_wrap(H: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Sample a tiling height map (rows = V from the bottom, cols = U) at UVs in tile units."""
    h, w = H.shape
    x = (u % 1.0) * w - 0.5
    y = (v % 1.0) * h - 0.5
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    x0 %= w
    y0 %= h
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    return (H[y0, x0] * (1 - fx) * (1 - fy) + H[y0, x1] * fx * (1 - fy) + H[y1, x0] * (1 - fx) * fy
            + H[y1, x1] * fx * fy)


@dataclass
class TubeMesh:
    V: np.ndarray                     # (n, 3)
    faces: List[np.ndarray]           # list of (F, k) int arrays (k = 3 or 4)
    uv0: List[np.ndarray]             # matching (F, k, 2)
    vdata: Dict[str, np.ndarray]      # per-vertex: branch, s, junction, radius, order, pad, element
    rects: List[Dict] = field(default_factory=list)


def build_branch(b: Branch, bi: int, parent: Optional[Branch], params: TubeParams, height: Optional[np.ndarray],
                 v0: float, rng: np.random.Generator, is_trunk: bool = False,
                 flare_base_z: float = 0.0) -> Optional[Dict]:
    """Rings and faces for one branch. Returns None if the branch vanishes inside its parent."""
    P = np.asarray(b.pts, dtype=np.float64)
    R = np.asarray(b.r, dtype=np.float64)
    s = arclength(P)
    # --- sink the start into the parent (study 4.5)
    s0 = 0.0
    if parent is not None:
        pr = parent.r[min(b.parent_idx, len(parent.r) - 1)]
        s0 = max(0.0, (1.0 - params.sink) * pr)
        if s[-1] <= s0 + 0.01:
            return None
    r_max = float(R.max())
    # plate geometry (and its dense ring spacing) on the trunk only: limbs and roots use the tiling normal map
    plates = is_trunk and (r_max >= params.plate_min_r) and height is not None
    spacing = ring_spacing(float(np.median(R)), plates, params.plate_spacing)
    keep = s >= s0
    Pk = np.vstack([np.array([np.interp(s0, s, P[:, k]) for k in range(3)])[None, :], P[keep]]) if s0 > 0 else P
    Rk = np.concatenate([[np.interp(s0, s, R)], R[keep]]) if s0 > 0 else R
    # drop a duplicate first point
    if len(Pk) > 1 and np.linalg.norm(Pk[1] - Pk[0]) < 1e-5:
        Pk, Rk = np.delete(Pk, 1, 0), np.delete(Rk, 1)
    sk = arclength(Pk)
    Q = resample(Pk, spacing, min_points=2)
    sq = arclength(Q)
    Rq = np.interp(sq, sk * (sq[-1] / max(sk[-1], 1e-9)), Rk)
    # --- collar (children) and root flare (trunk)
    r0 = Rq[0]
    if parent is not None:
        Rq = Rq * (1.0 + params.collar_amp * np.exp(-sq / max(params.collar_len * 2 * r0, 1e-4)))
    if is_trunk:
        zrel = np.maximum(Q[:, 2] - flare_base_z, 0.0)
        Rq = Rq * (1.0 + params.flare_amp * np.exp(-zrel / max(params.flare_len * r0, 1e-3)))
    if b.knuckles is not None and len(b.knuckles) and b.knuckle_amp > 0:
        # gnarled knuckles at the angular nodes (judge r0: 'short angular twigs ... gnarled knuckle')
        sa = sq + s0
        bump = np.zeros_like(Rq)
        for kpos in np.asarray(b.knuckles, float):
            wdt = max(1.6 * float(np.interp(kpos, sa, Rq)), 0.006)
            bump = np.maximum(bump, np.exp(-((sa - kpos) / wdt) ** 2))
        Rq = Rq * (1.0 + b.knuckle_amp * bump)
    T, N, B = pt_frames(Q, b.seam_hint)
    n = ring_count(float(Rq.max()), params.ring_len)
    # the texture wraps once per k tiles for the WHOLE branch: size it on the median girth (not the flared collar),
    # and only snap to whole tiles where that stays within about +-33 % of true scale
    circ = 2 * np.pi * float(np.median(Rq))
    if circ >= 0.75 * params.tile_m:
        k = float(max(1, int(round(circ / params.tile_m))))
        integer_k = True
    else:
        k = circ / params.tile_m
        integer_k = False
    m = len(Q)
    theta = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    u_ring = k * np.arange(n + 1) / n                       # n+1 columns: the seam column is duplicated in UV
    v_ring = v0 + sq / params.tile_m
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    radial = cos_t[None, :, None] * N[:, None, :] + sin_t[None, :, None] * B[:, None, :]   # (m, n, 3)
    if is_trunk and params.ellipse_y != 1.0:
        radial = radial * np.array([1.0, params.ellipse_y, 1.0])
    Rr = np.repeat(Rq[:, None], n, axis=1)
    if is_trunk and params.lobes > 0:
        ph = rng.uniform(0, 2 * np.pi, 2)
        tw = params.twist                                   # radians of lobe twist per metre (pine D: twisted)
        lobes = (params.lobes * np.sin(3 * theta[None, :] + ph[0] + sq[:, None] * (0.9 + tw))
                 + 0.5 * params.lobes * np.sin(2 * theta[None, :] + ph[1] - sq[:, None] * (0.6 - 0.5 * tw)))
        taper = np.clip(Rq / max(Rq.max(), 1e-6), 0.3, 1.0)[:, None]
        # buttress lobes low on the trunk: the flare is not a smooth cone (study 3.2 root flare, nebari)
        zrel = np.maximum(Q[:, 2] - flare_base_z, 0.0)
        low = np.exp(-zrel / max(params.flare_len * r0, 1e-3))[:, None]
        butt = params.buttress * low * np.clip(np.sin(5 * theta[None, :] + ph[1] + zrel[:, None] * tw), 0, 1) ** 2
        Rr = Rr * (1.0 + lobes * taper + butt)
    if plates and integer_k:
        uu = np.repeat(u_ring[None, :n], m, axis=0)
        vv = np.repeat(v_ring[:, None], n, axis=1)
        h = bilinear_wrap(height, uu, vv)
        depth = np.clip(params.plate_ratio * Rq, 0.0, params.plate_max)[:, None]
        depth = depth * np.clip((Rq[:, None] - params.plate_min_r) / params.plate_min_r, 0.0, 1.0)
        Rr = Rr + depth * (h - 0.72)
    verts = Q[:, None, :] + Rr[:, :, None] * radial                                        # (m, n, 3)
    V = verts.reshape(-1, 3)
    idx = np.arange(m * n).reshape(m, n)
    # quads (ring j -> j+1)
    a = idx[:-1, :]
    bq = idx[:-1, np.r_[1:n, 0]]
    c = idx[1:, np.r_[1:n, 0]]
    d = idx[1:, :]
    quads = np.stack([a, bq, c, d], axis=-1).reshape(-1, 4)
    ua = np.repeat(u_ring[None, :n], m - 1, 0)
    ub = np.repeat(u_ring[None, 1:], m - 1, 0)
    va = np.repeat(v_ring[:-1, None], n, 1)
    vb = np.repeat(v_ring[1:, None], n, 1)
    uvq = np.stack([np.stack([ua, va], -1), np.stack([ub, va], -1), np.stack([ub, vb], -1),
                    np.stack([ua, vb], -1)], axis=2).reshape(-1, 4, 2)
    faces, uvs = [quads], [uvq]
    extra = []
    # caps: fans on a centre vertex, UV centre pushed off the tube's V range so the fan has area
    dv_end = max(Rq[-1], 0.002) / params.tile_m
    dv_start = max(Rq[0], 0.002) / params.tile_m
    base_index = m * n
    tip = Q[-1] + T[-1] * Rq[-1] * 0.6
    start = Q[0] - T[0] * Rq[0] * 0.3
    extra = np.vstack([tip[None, :], start[None, :]])
    V = np.vstack([V, extra])
    ring_last = idx[-1]
    ring_first = idx[0]
    ce, cs = base_index, base_index + 1
    tri_end = np.stack([ring_last, ring_last[np.r_[1:n, 0]], np.full(n, ce)], -1)
    uv_end = np.stack([np.stack([u_ring[:n], np.full(n, v_ring[-1])], -1),
                       np.stack([u_ring[1:], np.full(n, v_ring[-1])], -1),
                       np.stack([np.full(n, k * 0.5), np.full(n, v_ring[-1] + dv_end)], -1)], axis=1)
    tri_start = np.stack([ring_first[np.r_[1:n, 0]], ring_first, np.full(n, cs)], -1)
    uv_start = np.stack([np.stack([u_ring[1:], np.full(n, v_ring[0])], -1),
                         np.stack([u_ring[:n], np.full(n, v_ring[0])], -1),
                         np.stack([np.full(n, k * 0.5), np.full(n, v_ring[0] - dv_start)], -1)], axis=1)
    faces += [tri_end, tri_start]
    uvs += [uv_end, uv_start]
    s_vert = np.concatenate([np.repeat(sq, n), [sq[-1], 0.0]])
    r_vert = np.concatenate([Rr.reshape(-1), [Rq[-1] * 0.3, Rq[0]]])
    if parent is not None:
        junction = np.exp(-s_vert / max(1.5 * 2 * r0, 1e-3))
    else:
        junction = np.zeros(len(V))
    # outward direction per vertex (for moss / AO)
    nrm = np.vstack([radial.reshape(-1, 3), T[-1][None, :], -T[0][None, :]])
    rect = {"branch": bi, "u0": 0.0, "u1": k, "v0": v_ring[0] - dv_start, "v1": v_ring[-1] + dv_end,
            "integer": integer_k, "k": k, "v_start": v_ring[0]}
    return {"V": V, "faces": faces, "uvs": uvs, "s": s_vert, "r": r_vert, "junction": junction, "nrm": nrm,
            "rect": rect, "rings": Q, "ring_r": Rq, "v_ring": v_ring, "n": n, "k": k, "integer_k": integer_k,
            "circ_start": circ}


def pack_rects(rects: List[Dict], margin: float = 0.02) -> Tuple[Dict[int, Tuple[float, float]], Tuple[float, float]]:
    """Place each branch's UV rectangle without overlap. Integer-k rects move by whole tiles (their tiling phase is
    kept); fractional rects go anywhere. Shelf packing; returns ({branch: (du, dv)}, (width, height)) in tiles."""
    ints = [r for r in rects if r["integer"]]
    frees = [r for r in rects if not r["integer"]]
    offsets: Dict[int, Tuple[float, float]] = {}
    total_int = sum(np.ceil(r["u1"] - r["u0"] + 1e-9) * np.ceil(r["v1"] - np.floor(r["v0"]) + 1e-9) for r in ints)
    total_free = sum((r["u1"] - r["u0"] + margin) * (r["v1"] - r["v0"] + margin) for r in frees)
    width = max(4, int(np.ceil(np.sqrt((total_int + total_free) * 1.25))),
                int(max([np.ceil(r["u1"] - r["u0"]) for r in ints] + [1])))
    # integer shelves: each rect occupies whole cells from floor(v0) to ceil(v1)
    x, y, shelf_h = 0, 0, 0
    for r in sorted(ints, key=lambda r: -(r["v1"] - np.floor(r["v0"]))):
        w = int(np.ceil(r["u1"] - r["u0"] - 1e-9))
        fv = np.floor(r["v0"])
        h = int(np.ceil(r["v1"] - fv + 1e-9))
        if x + w > width:
            x, y, shelf_h = 0, y + shelf_h, 0
        offsets[r["branch"]] = (float(x) - r["u0"], float(y) - fv)
        x += w
        shelf_h = max(shelf_h, h)
    y_free = float(y + shelf_h)
    # free shelves (fractional twigs), tallest first
    x, y, shelf_h = 0.0, y_free, 0.0
    for r in sorted(frees, key=lambda r: -(r["v1"] - r["v0"])):
        w = r["u1"] - r["u0"] + margin
        h = r["v1"] - r["v0"] + margin
        if x + w > width:
            x, y, shelf_h = 0.0, y + shelf_h, 0.0
        offsets[r["branch"]] = (x + margin * 0.5 - r["u0"], y + margin * 0.5 - r["v0"])
        x += w
        shelf_h = max(shelf_h, h)
    height = y + shelf_h
    return offsets, (float(width), float(np.ceil(height)))
