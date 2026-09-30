"""Pad envelopes, shoot-tip sites and space colonisation inside an envelope (numpy only).

TREE_BUILDING_STUDY.md 4.4 and 8.3: a niwaki pad is a half-ellipsoid, domed on top and nearly flat underneath.
The attraction points are the pad's SHOOT-TIP SITES (where the needle tufts go): denser on the dome and the rim,
sparse underneath, with a few sky holes (study 3.5: irregular spacing, sparse zones). Space colonisation
(Runions et al. 2007) grows the twig network from the limb nodes inside the pad to every site, which gives the
zig-zag branch structure the sheet's pad close-up shows under the needles.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

UP = np.array([0.0, 0.0, 1.0])


@dataclass
class Envelope:
    centre: np.ndarray       # (3,) the centre of the pad's base ellipse (dome above, flat part below)
    rx: float
    ry: float
    rz_top: float
    rz_bot: float
    yaw: float = 0.0          # rotation of the ellipse about Z (radians)

    def local(self, P: np.ndarray) -> np.ndarray:
        c, s = np.cos(-self.yaw), np.sin(-self.yaw)
        d = np.asarray(P, dtype=np.float64) - self.centre
        return np.stack([c * d[..., 0] - s * d[..., 1], s * d[..., 0] + c * d[..., 1], d[..., 2]], axis=-1)

    def world_dir(self, V: np.ndarray) -> np.ndarray:
        c, s = np.cos(self.yaw), np.sin(self.yaw)
        return np.stack([c * V[..., 0] - s * V[..., 1], s * V[..., 0] + c * V[..., 1], V[..., 2]], axis=-1)

    def rho(self, P: np.ndarray) -> np.ndarray:
        L = self.local(P)
        rz = np.where(L[..., 2] >= 0, self.rz_top, self.rz_bot)
        return np.sqrt((L[..., 0] / self.rx) ** 2 + (L[..., 1] / self.ry) ** 2 + (L[..., 2] / rz) ** 2)

    def normal(self, P: np.ndarray) -> np.ndarray:
        L = self.local(P)
        rz = np.where(L[..., 2] >= 0, self.rz_top, self.rz_bot)
        g = np.stack([L[..., 0] / self.rx ** 2, L[..., 1] / self.ry ** 2, L[..., 2] / rz ** 2], axis=-1)
        g = self.world_dir(g)
        return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12)

    # --- shape along the pad's X axis (front view); a ProfileEnvelope replaces these with the traced outline
    def top_at(self, lx: np.ndarray) -> np.ndarray:
        return self.rz_top * np.sqrt(np.clip(1.0 - (np.asarray(lx) / self.rx) ** 2, 0.0, 1.0))

    def bot_at(self, lx: np.ndarray) -> np.ndarray:
        return self.rz_bot * np.clip(1.0 - (np.asarray(lx) / self.rx) ** 2, 0.0, 1.0) ** 0.25

    def half_y(self, lx: np.ndarray) -> np.ndarray:
        return self.ry * np.sqrt(np.clip(1.0 - (np.asarray(lx) / self.rx) ** 2, 0.0, 1.0))

    @property
    def top_z(self) -> float:
        return float(self.centre[2] + self.rz_top)

    @property
    def bot_z(self) -> float:
        return float(self.centre[2] - self.rz_bot)


@dataclass
class ProfileEnvelope(Envelope):
    """A pad whose front outline is TRACED: top and bottom offsets sampled along local X (study 4.4: tracing is the
    2D outline authority). The footprint is still elliptical in plan; the dome falls off toward the back/front
    (local Y) as an ellipse, so the silhouette seen from the front is exactly the traced outline."""
    px: np.ndarray = None
    pt: np.ndarray = None
    pb: np.ndarray = None

    def top_at(self, lx):
        return np.interp(np.asarray(lx, dtype=np.float64), self.px, self.pt, left=0.0, right=0.0)

    def bot_at(self, lx):
        return np.interp(np.asarray(lx, dtype=np.float64), self.px, self.pb, left=0.0, right=0.0)

    def half_y(self, lx):
        return self.ry * np.maximum(np.sqrt(np.clip(1.0 - (np.asarray(lx) / self.rx) ** 2, 0.0, 1.0)), 0.3)


def _poisson_keep(P: np.ndarray, min_d: float, rng: np.random.Generator) -> np.ndarray:
    """Greedy dart-throw thinning on a grid hash (keeps a subset with pairwise distance >= min_d)."""
    order = rng.permutation(len(P))
    cell = min_d
    grid: Dict[Tuple[int, int, int], List[int]] = {}
    keep = []
    for i in order:
        p = P[i]
        key = tuple((p // cell).astype(int))
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if np.sum((P[j] - p) ** 2) < min_d * min_d:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            keep.append(i)
            grid.setdefault(key, []).append(i)
    return np.array(sorted(keep), dtype=int)


def value_noise2(x: np.ndarray, y: np.ndarray, seed: int, scale: float) -> np.ndarray:
    """Smooth 2D value noise in 0-1 (for density breakup)."""
    rng = np.random.default_rng(seed)
    table = rng.random((64, 64))
    gx, gy = x / scale, y / scale
    x0, y0 = np.floor(gx).astype(int), np.floor(gy).astype(int)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    t = lambda a, b: table[a % 64, b % 64]
    return (t(x0, y0) * (1 - fx) * (1 - fy) + t(x0 + 1, y0) * fx * (1 - fy) + t(x0, y0 + 1) * (1 - fx) * fy
            + t(x0 + 1, y0 + 1) * fx * fy)


def tuft_sites(env: Envelope, rng: np.random.Generator, spacing: float = 0.10, holes: int = 1,
               under_share: float = 0.25, rim_share: float = 1.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Shoot-tip sites for one pad. Returns (P (K,3), D (K,3) tuft directions, kind (K,) 0 top 1 rim 2 under)."""
    area = np.pi * env.rx * env.ry
    n_cand = int(area / (spacing * spacing) * 8) + 60
    # --- top layer: points under the dome surface
    x = rng.uniform(-env.rx, env.rx, n_cand)
    hy = env.half_y(x)
    keep_area = rng.random(n_cand) < hy / max(env.ry, 1e-6)
    y = (rng.random(n_cand) * 2 - 1) * hy
    yn = np.clip(np.abs(y) / np.maximum(hy, 1e-6), 0, 1)
    rho = np.sqrt((x / env.rx) ** 2 + (y / env.ry) ** 2)
    tz = env.top_at(x)
    zs = tz * np.sqrt(np.maximum(0.0, 1.0 - yn ** 2))
    depth = rng.random(n_cand) ** 1.3 * (0.55 * tz + 0.03)
    z = zs - depth
    # density: denser at the rim, broken by a low-frequency noise (irregular spacing, study 3.5)
    seed = int(rng.integers(1 << 30))
    nz = value_noise2(x + 7.3, y - 2.1, seed, max(0.18, 0.45 * min(env.rx, env.ry)))
    w = (0.55 + 0.45 * np.minimum(rho, 1)) * (0.45 + 0.9 * nz)
    keep = keep_area & (rng.random(n_cand) < np.clip(w, 0, 1)) & (tz > 0.01)
    L = np.stack([x, y, z], axis=1)[keep]
    # sky holes through the pad (study rule 5)
    for _ in range(holes):
        ha = rng.random() * 2 * np.pi
        hr = np.sqrt(rng.uniform(0.15, 0.7))
        hc = np.array([np.cos(ha) * hr * env.rx, np.sin(ha) * hr * env.ry])
        hrad = rng.uniform(0.14, 0.24) * min(env.rx, env.ry) + 0.03
        L = L[np.hypot(L[:, 0] - hc[0], L[:, 1] - hc[1]) > hrad]
    top = L[_poisson_keep(L, spacing * 0.85, rng)] if len(L) else L
    # --- rim: around the footprint, from the flat underside to the lower dome
    per = np.pi * (3 * (env.rx + env.ry) - np.sqrt((3 * env.rx + env.ry) * (env.rx + 3 * env.ry)))
    n_rim = int(per / spacing * 1.4 * rim_share) + 4
    a = rng.random(n_rim) * 2 * np.pi
    rr = rng.uniform(0.88, 1.02, n_rim)
    xr = rr * np.cos(a) * env.rx
    yr = rr * np.sin(a) * env.half_y(np.clip(xr, -0.97 * env.rx, 0.97 * env.rx))
    zr = rng.uniform(-0.6, 0.35, n_rim)
    zr = np.where(zr < 0, zr * env.bot_at(xr), zr * env.top_at(xr))
    rim = np.stack([xr, yr, zr], axis=1)
    rim = rim[(env.top_at(xr) + env.bot_at(xr)) > 0.01]
    rim = rim[_poisson_keep(rim, spacing * 0.9, rng)] if len(rim) else rim
    # --- underside: sparse, hanging a little below the flat base
    n_under = int(len(top) * under_share * 0.4) + 1
    xu = rng.uniform(-0.85, 0.85, n_under) * env.rx
    yu = (rng.random(n_under) * 2 - 1) * 0.85 * env.half_y(xu)
    zu = -env.bot_at(xu) * rng.uniform(0.1, 0.5, n_under)
    under = np.stack([xu, yu, zu], axis=1)
    Lall = np.vstack([top, rim, under])
    kind = np.concatenate([np.zeros(len(top), int), np.ones(len(rim), int), np.full(len(under), 2)])
    # directions: top follows the dome normal and up; rim points out; underside points out and down
    radial = Lall.copy()
    radial[:, 2] = 0.0
    radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-9)
    P = env.world_dir(Lall) + env.centre
    n_surf = env.normal(P)
    radial_w = env.world_dir(radial)
    jitter = rng.normal(0, 0.18, (len(P), 3))
    D = np.where(kind[:, None] == 0, 0.45 * n_surf + 0.25 * radial_w + 0.55 * UP,
                 np.where(kind[:, None] == 1, 0.85 * radial_w + 0.15 * UP, 0.85 * radial_w - 0.2 * UP)) + jitter
    D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9)
    return P, D, kind


def colonize(anchors: np.ndarray, sites: np.ndarray, D: float = 0.035, dk: float = 0.03, di: float = 0.45,
             tropism: float = 0.12, max_iter: int = 220) -> Tuple[np.ndarray, np.ndarray]:
    """Space colonisation from ``anchors`` (K0,3) toward ``sites`` (A,3).

    Returns (nodes (N,3), parent (N,)): nodes[:K0] are the anchors (parent -1); every later node has a parent
    index. Growth stops when every site is within ``dk`` of a node, or no node is influenced, or after
    ``max_iter`` steps.
    """
    nodes = [np.asarray(a, dtype=np.float64) for a in anchors]
    parent = [-1] * len(nodes)
    alive = np.ones(len(sites), dtype=bool)
    N = np.array(nodes)
    for _ in range(max_iter):
        if not alive.any():
            break
        S = sites[alive]
        d2 = ((S[:, None, :] - N[None, :, :]) ** 2).sum(-1)
        near = d2.argmin(1)
        dmin = np.sqrt(d2[np.arange(len(S)), near])
        # kill sites already reached
        reached = dmin < dk
        if reached.any():
            idx = np.nonzero(alive)[0][reached]
            alive[idx] = False
        infl = (~reached) & (dmin < di)
        if not infl.any():
            # nothing in range: let the nearest node reach toward the closest unreached site
            if not alive.any():
                break
            infl = ~reached
        grow: Dict[int, np.ndarray] = {}
        for s_i, n_i in zip(np.nonzero(infl)[0], near[infl]):
            v = S[s_i] - N[n_i]
            v /= max(np.linalg.norm(v), 1e-12)
            grow[n_i] = grow.get(n_i, 0.0) + v
        added = 0
        new_pts = []
        for n_i, v in grow.items():
            v = v / max(np.linalg.norm(v), 1e-12) + tropism * UP
            v /= max(np.linalg.norm(v), 1e-12)
            p = N[n_i] + D * v
            if new_pts and min(np.sum((q - p) ** 2) for q in new_pts) < (0.3 * D) ** 2:
                continue
            if np.min(((N - p) ** 2).sum(-1)) < (0.3 * D) ** 2:
                continue
            nodes.append(p)
            parent.append(int(n_i))
            new_pts.append(p)
            added += 1
        if added == 0:
            break
        N = np.array(nodes)
    return np.array(nodes), np.array(parent, dtype=int)


def attach_tips(nodes: np.ndarray, parent: np.ndarray, n_anchor: int, sites: np.ndarray, dirs: np.ndarray,
                shoot: float = 0.05, reach: float = 0.14) -> Tuple[np.ndarray, np.ndarray, List[Tuple[int, int]]]:
    """Add a short shoot to every site: node (site - dir * shoot) then the tip node at the site.

    Returns the extended (nodes, parent) and [(tip node index, site index)]. Sites farther than ``reach`` from any
    grown node are dropped (the pad stays irregular rather than growing long bare twigs).
    """
    nodes = list(nodes)
    parent = list(parent)
    N = np.array(nodes)
    tips = []
    for si, (s, d) in enumerate(zip(sites, dirs)):
        base = s - d * shoot
        d2 = ((N - base) ** 2).sum(-1)
        if len(N) > n_anchor:
            d2[:n_anchor] += 1e6 if (d2[n_anchor:].min() < reach * reach) else 0.0
        j = int(d2.argmin())
        if d2[j] > reach * reach:
            continue
        if d2[j] > (0.012) ** 2:
            nodes.append(base)
            parent.append(j)
            j = len(nodes) - 1
        nodes.append(np.asarray(s, dtype=np.float64))
        parent.append(j)
        tips.append((len(nodes) - 1, si))
    return np.array(nodes), np.array(parent, dtype=int), tips


def chains(nodes: np.ndarray, parent: np.ndarray, n_anchor: int) -> List[List[int]]:
    """Split the grown node tree into chains. Each chain is [attach node, own nodes...]; the attach node is an
    anchor or a node of an earlier chain. The heaviest child continues a chain, the others start new ones."""
    n = len(nodes)
    kids: List[List[int]] = [[] for _ in range(n)]
    for i in range(n_anchor, n):
        kids[parent[i]].append(i)
    weight = np.ones(n)
    for i in range(n - 1, n_anchor - 1, -1):
        if parent[i] >= 0:
            weight[parent[i]] += weight[i]
    out: List[List[int]] = []
    queue = []
    for a in range(n_anchor):
        for c in kids[a]:
            queue.append((a, c))
    while queue:
        start, c = queue.pop(0)
        ch = [start, c]
        cur = c
        while kids[cur]:
            ks = sorted(kids[cur], key=lambda k: -weight[k])
            for other in ks[1:]:
                queue.append((cur, other))
            cur = ks[0]
            ch.append(cur)
        out.append(ch)
    return out
