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
    lattice_lo: float = 0.18       # lattice height at the hub (share of the pad thickness above its base)
    lattice_hi: float = 0.55       # ... at the deepest fork level
    rim_drop: float = 0.35         # rim rosettes sit this share of a rosette lower and point outward
    under_share: float = 0.10      # share of rim sites turned out-and-down (a few needles under the rim)
    skirt_rho: float = 0.55        # rim sites past this get a lower companion on the dome's side ...
    skirt_share: float = 0.75      # ... with this probability


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


def grow_rosette_pad(env, hub: np.ndarray, d_in: np.ndarray, rng: np.random.Generator,
                     prm: RosettePadParams) -> Dict:
    top, base, _ = pad_surfaces(env, _SurfPrm(prm.max_thick_ratio, prm.top_cap))
    width = 2 * env.rx
    area = float(np.pi * env.rx * env.ry)
    n_hi = prm.n_max_big if area > prm.big_area else prm.n_max
    n_target = int(np.clip(round(area / (prm.spacing ** 2 * 0.95)), prm.n_min, n_hi))
    # ---- sky holes (study rule 5); only on bigger pads
    holes = []
    if area > prm.hole_area:
        for _ in range(prm.holes):
            a = rng.uniform(0, 2 * np.pi)
            rr = np.sqrt(rng.uniform(0.15, 0.5))
            holes.append((np.array([np.cos(a) * rr * env.rx, np.sin(a) * rr * env.ry]),
                          rng.uniform(0.45, 0.7) * prm.spacing))
    sites_l, sp = _poisson_footprint(env, rng, prm.spacing, n_target, 0.10, holes)
    # ---- rosette sites on the dome
    sites = []
    for q in sites_l:
        zt = float(top(q[0], q[1]))
        zb = float(base(q[0], q[1]))
        rho = float(np.sqrt((q[0] / env.rx) ** 2 + (q[1] / max(float(env.half_y(q[0])), 1e-3)) ** 2))
        # dome normal (finite differences of the top surface)
        e = 0.02
        gx = (float(top(q[0] + e, q[1])) - float(top(q[0] - e, q[1]))) / (2 * e)
        gy = (float(top(q[0], q[1] + e)) - float(top(q[0], q[1] - e))) / (2 * e)
        nl = np.array([-gx, -gy, 1.0])
        nl /= np.linalg.norm(nl)
        nw = env.world_dir(nl)
        radial = env.world_dir(np.array([q[0], q[1], 0.0]) / max(np.hypot(q[0], q[1]), 1e-6))
        rim = np.clip((rho - 0.55) / 0.45, 0, 1)
        d = 0.55 * nw + (0.75 - 0.35 * rim) * UP + (0.15 + 0.55 * rim) * radial + rng.normal(0, 0.10, 3)
        kind = 0 if rim < 0.5 else 1
        if kind == 1 and rng.random() < prm.under_share:
            d = radial * 0.9 + UP * 0.05 + rng.normal(0, 0.1, 3)
            kind = 2
        d /= np.linalg.norm(d)
        z = zt - (0.42 + prm.rim_drop * rim) * prm.ros_h - 0.25 * rim ** 1.5 * (zt - zb)
        z = max(z, zb + 0.35 * prm.ros_h)
        p = _to_world(env, np.array([q[0]]), np.array([q[1]]), np.array([z]))[0]
        sites.append({"p": p, "d": d, "kind": kind, "lxy": q.copy(), "rho": rho})
        # skirt (v2 r2 look: one layer of rosettes left the pads thin; the sheet's pads are green down their sides
        # to the flat underside): rim sites get a companion lower on the dome's side, pointing out and a little up
        if rho > prm.skirt_rho and rng.random() < prm.skirt_share and (zt - zb) > 0.6 * prm.ros_h:
            q2 = q * (1.0 + rng.uniform(0.0, 0.04))
            z2 = zt - rng.uniform(0.50, 0.72) * (zt - zb) - 0.2 * prm.ros_h
            z2 = max(z2, zb + 0.15 * prm.ros_h)
            d2 = radial * 0.85 + UP * rng.uniform(0.25, 0.55) + rng.normal(0, 0.10, 3)
            d2 /= np.linalg.norm(d2)
            p2 = _to_world(env, np.array([q2[0]]), np.array([q2[1]]), np.array([z2]))[0]
            sites.append({"p": p2, "d": d2, "kind": 1, "lxy": q2, "rho": rho})
    # ---- lattice by recursive grouping
    Lh = env.local(hub[None, :])[0]
    nodes = [np.array(hub, float)]          # world
    nlxy = [Lh[:2].copy()]
    parent = [-1]
    level = [0]
    shoot_of: List[Tuple[int, int]] = []    # (node, site)

    def lattice_z(lxy, lev):
        zt = float(top(lxy[0], lxy[1]))
        zb = float(base(lxy[0], lxy[1]))
        f = prm.lattice_lo + (prm.lattice_hi - prm.lattice_lo) * min(lev, 3) / 3.0
        return zb + f * max(zt - zb, 0.02)

    def recurse(ni, idx, lev):
        if len(idx) <= 3 or lev >= 4:
            for si in idx:
                shoot_of.append((ni, si))
            return
        k = 3 if (lev == 0 and len(idx) >= 9) else (3 if len(idx) >= 12 else 2)
        P = np.array([sites[i]["lxy"] for i in idx])
        lab = _kmeans2(P, k, rng)
        o = nlxy[ni]
        for j in range(k):
            g = [idx[t] for t in range(len(idx)) if lab[t] == j]
            if not g:
                continue
            c = np.array([sites[i]["lxy"] for i in g]).mean(0)
            # the fork node: part-way toward the group's centroid, never past its nearest site
            f = rng.uniform(0.42, 0.62) if len(g) > 3 else rng.uniform(0.55, 0.75)
            q = o + f * (c - o)
            if not _inside(env, q[0], q[1], 0.02):
                q = o + 0.5 * (c - o)
            z = lattice_z(q, lev + 1)
            p = _to_world(env, np.array([q[0]]), np.array([q[1]]), np.array([z]))[0]
            nodes.append(p)
            nlxy.append(q)
            parent.append(ni)
            level.append(lev + 1)
            recurse(len(nodes) - 1, g, lev + 1)

    recurse(0, list(range(len(sites))), 0)
    # ---- no steep strings: a node sits high enough that its shoots rise at most ~40 degrees to the rosette base
    # (minus the last few cm inside the rosette), and every lattice edge at most ~35 degrees; children are appended
    # after their parents, so one reverse pass lifts parents after their children
    tan_s, tan_e = np.tan(np.deg2rad(40.0)), np.tan(np.deg2rad(35.0))
    for (ni, si) in shoot_of:
        if ni == 0:
            continue
        b = sites[si]["p"] - sites[si]["d"] * 0.045
        h = float(np.hypot(*(b[:2] - nodes[ni][:2])))
        nodes[ni][2] = max(nodes[ni][2], b[2] - tan_s * h)
    for i in range(len(nodes) - 1, 0, -1):
        pa = parent[i]
        if pa == 0:
            continue
        h = float(np.hypot(*(nodes[i][:2] - nodes[pa][:2])))
        nodes[pa][2] = max(nodes[pa][2], nodes[i][2] - tan_e * h)
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
