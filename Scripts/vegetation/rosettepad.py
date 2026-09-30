"""Niwaki pads as DOMES OF ROSETTES on a ramified twig lattice (numpy only). Pines v2, owner-approved method, step 2.

Replaces cloudpad.py (f1: flat needle slabs/drums of bursts on long bare arms with vertical twig strings; judged
4.5/10). CLAUDE.md: a construction that does not converge changes METHOD. The sheet's pad close-ups show:
  * a pad = 15-25 SEPARATE rosettes (vegetation/rosette.py) along the upper side of a twig lattice, sky between
    them; convex top, flatter open underside where the twigs show; 2.5-4x wider than tall;
  * the lattice: the limb enters the pad and ramifies in 2-3 orders of forks; every twig changes direction every
    15-30 cm (short knuckled segments, 1-2 cm thick) and tapers to the shoots; no vertical support strings.

Construction (pad-local plan coordinates lx, ly from the envelope; world z):
  1. rosette sites: a Poisson-disk sample of the footprint (spacing from the pad area and the rosette count), each
     at the dome surface minus about 0.4 of a rosette's height, pointing along the dome normal blended toward up
     (upper side: up; rim: out and up). 0-2 sky holes (no sites) on bigger pads.
  2. lattice: a recursive k-means split of the sites from the hub (k = 3, then 2-3): each group gets a fork node
     part-way toward its centroid, at a lattice height that rises level by level through the lower half of the pad
     (flatter underside, twigs visible from below); a group of <= 3 sites becomes shoots from its node (the little
     2-3 rosette stars at the twig ends of the close-ups).
  3. every lattice edge gets 0-2 zig-zag kinks (a direction change every ``seg`` metres, sideways + a little up);
     knuckle swellings at kinks and forks. The heaviest child continues its parent's chain (one tube), the others
     start new chains, so forks read as forks, not as tube caps.
  4. shoots: node -> a level run -> a short final rise along the rosette axis -> the site (the rosette's shoot ends
     there). Rise never steeper than about 45 degrees except the last few cm inside the rosette.
Returns chains (polylines with parent chain and node index) and the rosette sites, in the same shape treegen's
f1 fan-pad glue consumed (``arms`` / ``shoots``), so the tube, wind and foliage stages are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from cloudpad import _inside, _to_world, pad_surfaces
from skeleton import arclength

UP = np.array([0.0, 0.0, 1.0])


@dataclass
class RosettePadParams:
    n_min: int = 15                # rosettes per pad (task: 15-25)
    n_max: int = 25
    n_max_big: int = 34            # large pads (C) may go past 25 (recorded deviation)
    big_area: float = 0.85         # m^2 footprint above which n_max_big applies
    spacing: float = 0.15          # nominal rosette spacing (m); the count follows from the area
    ros_h: float = 0.12            # rosette height (m) (unit height, instance scale ~1)
    seg: float = 0.16              # lattice zig-zag segment (m): direction change every seg (15-30 cm on limbs)
    amp: float = 0.30              # sideways kink amplitude (share of the segment)
    holes: int = 1                 # sky holes on pads over ``hole_area``
    hole_area: float = 0.30
    max_thick_ratio: float = 0.34  # thickness <= this x width (2.5-4x wider than tall)
    top_cap: float = 0.0           # hand-traced dome height cap (m)
    lattice_lo: float = 0.02       # lattice height (share of the pad thickness above its base); v2f: 0.06 -> 0.02
    lattice_hi: float = 0.24       # ... v2f: 0.38 -> 0.24 (the twigs carry the brushes from below)
    rim_drop: float = 0.35         # rim rosettes sit this share of a rosette lower and point outward
    under_share: float = 0.0       # s5: fans under the rim (v2f: 0.08 -> 0, the judge-confirmed fringe)
    site_floor: float = 0.22       # v2f: brush bases at least this share of the local thickness above the underside
    base_drop: float = 0.18        # s8: underside lowered by this share of the local thickness
    inset: float = 0.055          # s7: surface inset (m), about half a fan
    lat_sp: float = 0.13           # v2 s2: internal lattice point spacing (m): twigs change direction about this often
    lat_max: float = 0.24          # longest lattice edge (m)
    skirt_rho: float = 0.55        # rim sites past this get a lower companion on the dome's side ...
    skirt_share: float = 0.75      # ... with this probability
    clump_sp: float = 0.0          # v2f: > 0 groups the rosettes into twig-end CLUMPS this far apart (m) ...
    clump_r: float = 0.065         # ... each clump the sites within this radius of its centre ...
    clump_in_sp: float = 0.055     # ... thinned to this spacing (3-6 rosettes per clump)


def _poisson_footprint(env, rng, spacing, n_target, margin=0.06, holes=()):
    """Dart-throwing Poisson disk on the footprint; the spacing shrinks until about n_target points fit."""
    best = None
    sp = spacing
    for _ in range(14):
        pts = []
        cand = rng.uniform(-1, 1, (4000, 2)) * np.array([env.rx, env.ry])
        ok = _inside(env, cand[:, 0], cand[:, 1], margin)
        cand = cand[ok]
        for q in cand:
            if any(np.hypot(*(q - hc)) < hr for hc, hr in holes):
                continue
            if pts and np.min(np.hypot(*(np.array(pts) - q).T)) < sp:
                continue
            pts.append(q)
        pts = np.array(pts) if pts else np.zeros((0, 2))
        if best is None or abs(len(pts) - n_target) < abs(len(best) - n_target):
            best = pts
        if len(pts) < n_target:
            sp *= 0.93
        elif len(pts) > n_target + 1:
            sp *= 1.05
        else:
            break
    if len(best) > n_target:
        # drop the points in the most crowded spots
        while len(best) > n_target:
            d = np.hypot(best[:, None, 0] - best[None, :, 0], best[:, None, 1] - best[None, :, 1])
            np.fill_diagonal(d, 9.0)
            best = np.delete(best, int(np.argmin(d.min(1))), 0)
    return best, sp


def _kmeans2(P, k, rng, iters=20):
    if len(P) <= k:
        return np.arange(len(P))
    # seed by angle around the centroid: groups become sectors (fans of twigs), not stripes
    c = P.mean(0)
    ang = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
    order = np.argsort(ang)
    lab = np.zeros(len(P), int)
    for j, idx in enumerate(np.array_split(order, k)):
        lab[idx] = j
    C = np.array([P[lab == j].mean(0) for j in range(k)])
    for _ in range(iters):
        lab = ((P[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([P[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
    return lab


def dome_sites(env, rng, prm, top, base, n_target, n_hi):
    """Poisson-disk rosette sites on the pad's dome surface (3D spacing), fans pointing up.

    The dome, in pad-local plan coordinates: along X the traced top/bottom profile (``top``/``base`` from
    ``pad_surfaces``, thickness-clamped); across Y a round fall-off z(s) = zb + (zt - zb)(1 - |s|^2.4)^0.5 with
    s = ly / half_y(lx), so the front silhouette is the traced outline and the side silhouette a rounded dome.
    Sites are sampled area-weighted on that surface, thinned to a 3D spacing (shrunk until the count reaches
    n_target, capped at n_hi), then each fan base is sunk along its axis so its needle tips reach the surface.
    Sky holes: 0-2 plan discs with no top-surface sites on the bigger pads (study rule 5)."""
    nx_, ns_ = 72, 36
    # s7: the fans' needles reach 6-9 cm past their bases, so the sampled surface is pulled in by about half a fan
    # (s6 XOR: every pad outline 5-10 % past the sheet's, most in the side view)
    kx = max(0.72, 1.0 - prm.inset / max(env.rx, 1e-3))
    ky = max(0.72, 1.0 - prm.inset / max(env.ry, 1e-3))
    lxs = np.linspace(-env.rx, env.rx, nx_)
    ss = np.linspace(-1.0, 1.0, ns_)
    LX, S = np.meshgrid(lxs, ss, indexing="ij")
    HY = np.maximum(env.half_y(LX), 1e-3)
    LY = S * HY * ky
    ZT = top(LX, np.zeros_like(LX))
    ZB = base(LX, LY)
    LX = LX * kx
    fall = np.clip(1.0 - np.abs(S) ** 2.4, 0.0, 1.0) ** 0.5
    Z = ZB + np.maximum(ZT - ZB, 0.0) * fall
    ok = (env.top_at(LX) + env.bot_at(LX)) > 0.02
    P = np.stack([LX, LY, Z], -1)
    # triangle areas per grid cell -> sampling weights
    a_ = P[:-1, :-1]
    b_ = P[1:, :-1]
    c_ = P[1:, 1:]
    d_ = P[:-1, 1:]
    A = 0.5 * np.linalg.norm(np.cross(b_ - a_, c_ - a_), axis=-1) + 0.5 * np.linalg.norm(np.cross(c_ - a_, d_ - a_), axis=-1)
    okc = ok[:-1, :-1] & ok[1:, :-1] & ok[1:, 1:] & ok[:-1, 1:]
    A = np.where(okc, A, 0.0)
    area = float(A.sum())
    if area <= 0:
        return []
    # surface normals (local frame; x/y plan, z up) by finite differences of the grid
    gx = np.gradient(P, axis=0)
    gs = np.gradient(P, axis=1)
    N = np.cross(gx, gs)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    N = np.where(N[..., 2:3] < 0, -N, N)
    # flanks: the outward side (N's plan part points away from the centre)
    radial = np.stack([LX / env.rx, LY / np.maximum(env.ry, 1e-3), np.zeros_like(LX)], -1)
    n_c = 60 * max(n_target, 10)
    # v2f l13: surface-area weights starved the dome TOP (the flanks carry more area per plan area), so small pads
    # showed a ring of rosettes round an empty crown from above; weight toward up-facing cells
    Nc = N[:-1, :-1, 2]
    Aw = A * (0.45 + 0.55 * np.clip(Nc, 0, 1))
    w = (Aw / Aw.sum()).ravel()
    idx = rng.choice(len(w), size=n_c, p=w)
    i, j = np.unravel_index(idx, A.shape)
    u, v = rng.random(n_c), rng.random(n_c)
    Q = (P[i, j] * (1 - u)[:, None] * (1 - v)[:, None] + P[i + 1, j] * u[:, None] * (1 - v)[:, None]
         + P[i, j + 1] * (1 - u)[:, None] * v[:, None] + P[i + 1, j + 1] * (u * v)[:, None])
    Nq = N[i, j]
    Rq = radial[i, j]
    # sky holes (plan discs on the top surface only)
    holes = []
    if np.pi * env.rx * env.ry > prm.hole_area:
        for _ in range(prm.holes):
            a = rng.uniform(0, 2 * np.pi)
            rr = np.sqrt(rng.uniform(0.10, 0.45))
            holes.append((np.array([np.cos(a) * rr * env.rx, np.sin(a) * rr * env.ry]),
                          rng.uniform(0.55, 0.8) * prm.spacing))
    keep = np.ones(n_c, bool)
    for hc, hr in holes:
        keep &= ~((np.hypot(Q[:, 0] - hc[0], Q[:, 1] - hc[1]) < hr) & (Nq[:, 2] > 0.6))
    Q, Nq, Rq = Q[keep], Nq[keep], Rq[keep]
    if prm.clump_sp > 0:
        # v2f (judge delta 4, checked on the sheet's pad-from-above and pad-side close-ups): the sheet's pads are
        # CLUMPS of 3-6 rosettes at the twig ends with darker gaps between them (branches show through), not an
        # even blanket; l3 lab: evenly spaced rosettes at tree distance read as a uniform hairy mat
        order = rng.permutation(len(Q))
        cen = []
        for k in order:
            if cen and np.linalg.norm(Q[cen] - Q[k], axis=1).min() < prm.clump_sp:
                continue
            cen.append(k)
        C = Q[cen]
        dd = np.linalg.norm(Q[:, None, :] - C[None, :, :], axis=2)
        near = dd.min(1)
        # clump radius varies 0.7-1.3x per clump (size rhythm)
        cr = prm.clump_r * rng.uniform(0.7, 1.3, len(C))
        inside = near < cr[dd.argmin(1)]
        # l12 pad-top: small pads (the A2 apex, 0.58 m) got 5-7 clumps round a hole; the sheet's small pads are
        # full ovals. Clumps first, then fill between them up to 62 % of the area target at 1.3 x the clump spacing
        order_all = rng.permutation(len(Q))
        idx_in = [k for k in order_all if inside[k]]
        chosen = []
        for k in idx_in:
            if chosen and np.linalg.norm(Q[chosen] - Q[k], axis=1).min() < prm.clump_in_sp:
                continue
            chosen.append(k)
        need = int(0.62 * n_target)
        if len(chosen) < need:
            for k in order_all:
                if len(chosen) >= need:
                    break
                if inside[k]:
                    continue
                if chosen and np.linalg.norm(Q[chosen] - Q[k], axis=1).min() < 1.3 * prm.clump_in_sp:
                    continue
                chosen.append(k)
        best = chosen
        sp = prm.clump_in_sp
        chosen = best[:n_hi]
    else:
        chosen = None
    # 3D Poisson thinning: shrink the spacing until the count reaches n_target (and not past n_hi)
    sp = prm.spacing
    best = chosen
    for _ in range(12 if chosen is None else 0):
        order = rng.permutation(len(Q))
        chosen = []
        for k in order:
            if chosen:
                dd = np.linalg.norm(Q[chosen] - Q[k], axis=1)
                if dd.min() < sp:
                    continue
            chosen.append(k)
        best = chosen
        if len(chosen) < n_target and sp > 0.6 * prm.spacing:
            sp *= 0.94
            continue
        break
    chosen = best[:n_hi]
    sites = []
    fan_h = prm.ros_h
    for k in chosen:
        q, nl, rq = Q[k], Nq[k], Rq[k]
        rho = float(np.hypot(rq[0], rq[1]))
        rpl = np.array([rq[0], rq[1], 0.0])
        rpl = rpl / max(np.linalg.norm(rpl), 1e-9)
        flank = float(np.clip(1.0 - nl[2], 0.0, 1.0))           # 0 on the top, ~1 on a vertical flank
        # s13: at most ~30 degrees off vertical on a flank (s12 pad close-up: tilted flank fans + a 64 degree cone
        # hung needles down the pad's ends like an umbrella; the sheet's fans all stand up)
        # v2f: rim brushes lean out up to ~36 degrees (was ~29) with the narrower brush cone: the dome's flanks
        # read green without needles hanging below the twigs
        d = UP * (1.0 - 0.25 * flank) + rpl * (0.15 + 0.40 * flank) + rng.normal(0, 0.08, 3)
        d /= np.linalg.norm(d)
        # the fan base sinks along its axis so the needle tips reach the dome surface
        p_l = q - d * (0.72 * fan_h) * (1.0 - 0.45 * flank)
        zb = float(base(q[0], q[1]))
        # v2f: no brush base below the twig lattice (l5 pad-side: rim brushes rooted under the limb read as a
        # hanging fringe; the sheet's brushes all stand on the twigs)
        zt_ = float(np.asarray(top(np.array([q[0]]), np.array([q[1]]))).ravel()[0])
        p_l[2] = max(p_l[2], zb + prm.site_floor * max(zt_ - zb, 0.0), zb + 0.012)
        pw = _to_world(env, np.array([p_l[0]]), np.array([p_l[1]]), np.array([p_l[2]]))[0]
        kind = 0 if flank < 0.45 else 1
        sites.append({"p": pw, "d": env.world_dir(d), "kind": kind, "lxy": p_l[:2].copy(), "rho": rho})
    # s5: fans under the rim, pointing out and 65-80 degrees from vertical, so needles fill the pad's side down to
    # the traced bottom outline (s4 XOR: the sheet's pads reach lower than ours under every pad); the middle of the
    # underside stays open, the twig net shows there (owner item 2)
    n_under = int(round(prm.under_share * len(sites)))
    tries = 0
    added = 0
    while added < n_under and tries < 20 * n_under + 20:
        tries += 1
        a = rng.uniform(0, 2 * np.pi)
        rr = rng.uniform(0.55, 0.95) * min(kx, ky)
        lx = np.cos(a) * rr * env.rx
        ly = np.sin(a) * rr * float(env.half_y(lx))
        if not _inside(env, lx, ly, 0.02):
            continue
        zb = float(base(lx, ly))
        zlow = float(env.centre[2] - env.bot_at(lx) * min(1.0, float(env.half_y(lx)) / max(env.ry, 1e-6) + 0.3))
        rpl = np.array([np.cos(a) * env.ry, np.sin(a) * env.rx, 0.0])
        rpl /= np.linalg.norm(rpl)
        tilt = np.deg2rad(rng.uniform(30, 46))       # s17: fewer, steeper (s16 pad-side: a hanging lower row)
        d = rpl * np.sin(tilt) + UP * np.cos(tilt) + rng.normal(0, 0.06, 3)
        d /= np.linalg.norm(d)
        z = zb - 0.6 * max(zb - zlow, 0.0) * rng.uniform(0.4, 1.0)
        pw = _to_world(env, np.array([lx]), np.array([ly]), np.array([z]))[0]
        sites.append({"p": pw, "d": env.world_dir(d), "kind": 2, "lxy": np.array([lx, ly]), "rho": rr})
        added += 1
    return sites


def grow_rosette_pad(env, hub: np.ndarray, d_in: np.ndarray, rng: np.random.Generator,
                     prm: RosettePadParams) -> Dict:
    top, base0, _ = pad_surfaces(env, _SurfPrm(prm.max_thick_ratio, prm.top_cap))

    def base(lx, ly):
        # s8: the flat underside sits lower (s7 XOR: the sheet's pads reach 5-10 cm below ours under every pad)
        b0 = base0(lx, ly)
        return b0 - prm.base_drop * np.maximum(top(lx, np.zeros_like(np.asarray(lx, float))) - b0, 0.0)
    width = 2 * env.rx
    area = float(np.pi * env.rx * env.ry)
    n_hi = prm.n_max_big if area > prm.big_area else prm.n_max
    n_target = int(np.clip(round(area / (prm.spacing ** 2 * 0.95)), prm.n_min, n_hi))
    # ---- v2 s1: rosette sites over the whole DOME SURFACE (top and flanks), not over the footprint. The sheet's pad
    # close-ups show upright fans packed over a rounded mass whose flanks are green down to the flat underside;
    # footprint sampling left the flanks bare (thin 'wing' pads) and the old rim rosettes, turned outward, hung
    # their needles down (the hairy fringe). Every fan now points UP, tilted at most ~35 degrees outward.
    sites = dome_sites(env, rng, prm, top, base, n_target, n_hi)
    holes = [0] * int(area > prm.hole_area) * prm.holes
    sp = prm.spacing
    # ---- v2 s2: the lattice is a spanning tree grown from the hub over internal twig points in the lower half of
    # the pad (Prim, costs favour short, level, outward edges), and every fan hangs on a SHORT shoot from its
    # nearest lattice node below it. s1 look: the recursive k-means lattice ran long twigs out to the rim and down
    # to the flank fans (loops and 'curtains' from above, a sparse net from below); the sheet's pads show a dense
    # knuckled twig net under the fans, twigs 10-20 cm between forks, shoots only a few cm long.
    Lh = env.local(hub[None, :])[0]
    X0 = np.array([Lh[0], Lh[1], float(hub[2])])
    g = prm.lat_sp
    nxg = max(2, int(np.ceil(2 * env.rx / g)))
    nyg = max(2, int(np.ceil(2 * env.ry / g)))
    gx_, gy_ = np.meshgrid((np.arange(nxg) + 0.5) / nxg * 2 - 1, (np.arange(nyg) + 0.5) / nyg * 2 - 1, indexing="ij")
    cand = np.stack([gx_.ravel() * env.rx, gy_.ravel() * env.ry], 1) + rng.normal(0, 0.28 * g, (gx_.size, 2))
    cand = cand[_inside(env, cand[:, 0], cand[:, 1], 0.12)]
    zt_c = top(cand[:, 0], cand[:, 1])
    zb_c = base(cand[:, 0], cand[:, 1])
    fz = rng.uniform(prm.lattice_lo, prm.lattice_hi, len(cand))
    I = np.column_stack([cand, zb_c + fz * np.maximum(zt_c - zb_c, 0.02)])
    Pn = np.vstack([X0[None, :], I])
    n = len(Pn)
    dh = np.hypot(Pn[:, 0] - X0[0], Pn[:, 1] - X0[1])
    par = np.full(n, -1)
    intree = np.zeros(n, bool)
    intree[0] = True
    nkids = np.zeros(n, int)
    INF = 1e9

    def edge_cost(a_i, bs):
        v = Pn[bs] - Pn[a_i]
        L = np.linalg.norm(v, axis=1)
        drop = np.maximum(0.0, -v[:, 2])
        rise = np.maximum(0.0, v[:, 2])
        inward = np.maximum(0.0, dh[a_i] - dh[bs])
        c = L * (1.0 + 1.5 * drop / np.maximum(L, 1e-6) + 0.8 * rise / np.maximum(L, 1e-6)) + 1.2 * inward
        c += 0.04 * max(0, nkids[a_i] - 1)
        return np.where((L <= prm.lat_max) | (a_i == 0), c + (0.0 if a_i else 0.5 * np.maximum(L - prm.lat_max, 0.0)), INF)

    key = np.full(n, INF)
    key_par = np.full(n, -1)
    out_idx = np.arange(1, n)
    key[out_idx] = edge_cost(0, out_idx)
    key_par[out_idx] = 0
    for _ in range(n - 1):
        k_ = np.where(intree, INF, key)
        b_i = int(np.argmin(k_))
        if k_[b_i] >= INF:
            break
        intree[b_i] = True
        par[b_i] = key_par[b_i]
        nkids[par[b_i]] += 1
        rest = np.nonzero(~intree)[0]
        if len(rest):
            c = edge_cost(b_i, rest)
            better = c < key[rest]
            key[rest[better]] = c[better]
            key_par[rest[better]] = b_i
    # attach every fan to the nearest tree node below it (short shoots)
    tree_nodes = np.nonzero(intree)[0]
    site_node = []
    for si, st in enumerate(sites):
        q = np.array([st["lxy"][0], st["lxy"][1], float(st["p"][2])])
        v = q - Pn[tree_nodes]
        hz = np.hypot(v[:, 0], v[:, 1])
        c = np.linalg.norm(v, axis=1) + 2.0 * np.maximum(0.0, -v[:, 2] - 0.01) + 0.6 * np.maximum(0.0, v[:, 2] - 1.2 * hz - 0.03)
        site_node.append(int(tree_nodes[int(np.argmin(c))]))
    # prune lattice points that carry no fan; renumber parents-first
    used = np.zeros(n, bool)
    for nd in site_node:
        k_ = nd
        while k_ >= 0 and not used[k_]:
            used[k_] = True
            k_ = par[k_]
    used[0] = True
    order_ = [0]
    kids_all = [[] for _ in range(n)]
    for i_ in range(1, n):
        if used[i_] and par[i_] >= 0:
            kids_all[par[i_]].append(i_)
    q_ = [0]
    while q_:
        a_i = q_.pop(0)
        for c_ in kids_all[a_i]:
            order_.append(c_)
            q_.append(c_)
    new_id = {old: k for k, old in enumerate(order_)}
    nodes, nlxy, parent, level = [], [], [], []
    for old in order_:
        X = Pn[old]
        nodes.append(_to_world(env, np.array([X[0]]), np.array([X[1]]), np.array([X[2]]))[0] if old else np.array(hub, float))
        nlxy.append(X[:2].copy())
        parent.append(-1 if old == 0 else new_id[par[old]])
    # fork order: the number of forks on the path from the hub (the 2-3 orders the sheet shows)
    nk = np.zeros(len(order_), int)
    for i_ in range(1, len(order_)):
        nk[parent[i_]] += 1
    level = [0] * len(order_)
    for i_ in range(1, len(order_)):
        pa = parent[i_]
        level[i_] = level[pa] + (1 if nk[pa] > 1 else 0)
    shoot_of: List[Tuple[int, int]] = [(new_id[nd], si) for si, nd in enumerate(site_node)]
    # ---- chains: heaviest child continues the parent's chain
    n = len(nodes)
    kids: List[List[int]] = [[] for _ in range(n)]
    for i in range(1, n):
        kids[parent[i]].append(i)
    weight = np.ones(n)
    for (ni, si) in shoot_of:
        weight[ni] += 1
    for i in range(n - 1, 0, -1):
        weight[parent[i]] += weight[i]
    chains = []          # each: {"nodes": [node ids], "parent_chain", "parent_pos"}
    chain_of_node: Dict[int, Tuple[int, int]] = {0: (-1, 0)}   # node -> (chain, index in chain polyline nodes)
    queue = [(0, c) for c in sorted(kids[0], key=lambda c: -weight[c])]
    while queue:
        start, c = queue.pop(0)
        ch = [start, c]
        cur = c
        while kids[cur]:
            ks = sorted(kids[cur], key=lambda k_: -weight[k_])
            for other in ks[1:]:
                queue.append((cur, other))
            cur = ks[0]
            ch.append(cur)
        ci = len(chains)
        chains.append(ch)
        for t, nd in enumerate(ch[1:], start=1):
            chain_of_node[nd] = (ci, t)
    # ---- polylines with zig-zag kinks; record where each tree node lands in its chain polyline
    arms = []
    node_poly_index: Dict[int, Tuple[int, int]] = {0: (-1, 0)}
    for ci, ch in enumerate(chains):
        pts = [nodes[ch[0]]]
        knots = []
        for a_, b_ in zip(ch[:-1], ch[1:]):
            A, B = nodes[a_], nodes[b_]
            v = B - A
            L = float(np.linalg.norm(v))
            nk = int(np.clip(np.floor(L / prm.seg), 0, 2))
            side = np.cross(v / max(L, 1e-9), UP)
            if np.linalg.norm(side) > 1e-6:
                side /= np.linalg.norm(side)
            sgn = 1.0 if rng.random() < 0.5 else -1.0
            for t in range(1, nk + 1):
                s = t / (nk + 1) + rng.normal(0, 0.06)
                kp = A + v * s + side * sgn * prm.amp * (L / (nk + 1)) * rng.uniform(0.6, 1.1) \
                    + UP * rng.normal(0.0, 0.18) * prm.amp * (L / (nk + 1))
                pts.append(kp)
                knots.append(len(pts) - 1)
                sgn = -sgn if rng.random() < 0.8 else sgn
            pts.append(B)
            knots.append(len(pts) - 1)
            node_poly_index[b_] = (ci, len(pts) - 1)
        P = np.array(pts)
        s_arc = arclength(P)
        pc, pj = node_poly_index.get(ch[0], (-1, 0))
        arms.append({"pts": P, "parent": pc, "parent_node": pj, "level": level[ch[1]],
                     "knuckles": s_arc[[k for k in knots if 0 < k < len(P) - 1]] if len(knots) else np.zeros(0),
                     "node_idx": {nd: node_poly_index[nd][1] for nd in ch[1:]}})
    # ---- shoots
    shoots = []
    for (ni, si) in shoot_of:
        s_ = sites[si]
        a = nodes[ni]
        b = s_["p"]
        d = s_["d"]
        v = b - a
        hz = np.array([v[0], v[1], 0.0])
        L = float(np.linalg.norm(v))
        if L < 0.02:
            b = a + d * 0.03
            v = b - a
            L = float(np.linalg.norm(v))
        # level-ish run out, then turn up along the rosette axis for the last few cm
        pre = b - d * min(0.045, 0.4 * L)
        mid = a + (pre - a) * rng.uniform(0.45, 0.6)
        mid[2] = a[2] + (pre[2] - a[2]) * rng.uniform(0.15, 0.35)
        side = np.cross(hz / max(np.linalg.norm(hz), 1e-9), UP) if np.linalg.norm(hz) > 1e-6 else np.zeros(3)
        mid = mid + side * rng.normal(0, 0.12) * L
        pts = np.array([a, mid, pre, b])
        ci, pj = node_poly_index[ni]
        shoots.append({"pts": pts, "arm": ci, "node": pj, "site": s_})
    # ---- stats
    rise = []
    for sh in shoots:
        P = sh["pts"]
        for u, w in zip(P[:-2], P[1:-1]):
            dv = w - u
            rise.append(np.degrees(np.arctan2(dv[2], np.hypot(dv[0], dv[1]) + 1e-9)))
    thick = float(np.median([float(top(s["lxy"][0], s["lxy"][1]) - base(s["lxy"][0], s["lxy"][1])) for s in sites])) \
        if sites else 0.0
    zs = np.array([s["p"][2] for s in sites]) if sites else np.zeros(1)
    return {"arms": arms, "shoots": shoots, "sites": [sh["site"] for sh in shoots], "n_rosettes": len(shoots),
            "n_target": n_target, "spacing": round(float(sp), 3), "n_arms": len(arms),
            "fork_levels": int(max(level)) if level else 0, "thickness": thick,
            "width": width, "max_shoot_rise_deg": round(float(max(rise)) if rise else 0.0, 1),
            "holes": len(holes), "site_z_span": round(float(zs.max() - zs.min()), 3)}


@dataclass
class _SurfPrm:
    max_thick_ratio: float
    top_cap: float
