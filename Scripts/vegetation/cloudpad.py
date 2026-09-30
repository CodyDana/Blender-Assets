"""Niwaki cloud pads as an open lattice of angular forked twigs carrying separate needle bursts (numpy only).

Replaces the r0 construction (space colonisation toward shoot sites + a solid inset core shell per pad), which the
r0 judge rejected: the cores read as opaque saucers, the colonised network was smooth with vertical support sticks,
and the pads were dense domed hedges. CLAUDE.md: a construction that does not converge changes method.

The reference close-ups (pad from the side, pad from above) show a pad as:
  * a limb entering the pad and splitting, near the pad's FLAT UNDERSIDE, into a fan of angular arms that zig-zag
    and fork 1-2 more times toward the pad's outline (3-6 forked twig segments per pad);
  * short shoots rising from those arms, each ending in ONE radial needle burst (a rosette from above, a brush from
    the side); 5-12 bursts per arm; sky shows between bursts and the twig lattice shows from below and above;
  * a flat or slightly domed top, a clean flat underside, 2.5-4x wider than tall.

``grow_pad`` returns the arms and shoots as polylines (to become Branch objects in treegen) and the burst sites.
Pad-local frame: the envelope's local X/Y (plan) and world Z. All lengths in metres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from skeleton import angularize, arclength, chaikin, resample

UP = np.array([0.0, 0.0, 1.0])


@dataclass
class PadParams:
    burst_len: float = 0.09        # needle length (m); a burst is about 2 x this across
    spacing: float = 0.12          # burst centre spacing along an arm (m)
    arm_seg: float = 0.10          # zig-zag segment length of the arms (m)
    arm_amp: float = 0.45          # zig-zag sideways amplitude (share of a segment)
    holes: int = 1                 # sky holes per pad
    keep: float = 1.0              # share of candidate bursts kept (density control, G5 row fill)
    lower_layer: float = 0.25      # share of bursts that get a companion lower on the rim (thick pads)
    max_thick_ratio: float = 0.38  # pad thickness <= this x pad width (flat pads, judge r0: 2.5-4x wider)
    node_step: float = 0.035       # arm polyline node spacing (shoots attach at nodes)
    top_cap: float = 0.0           # hand-traced dome height (m); the pixel profile may not exceed it (0 = off)


def _inside(env, lx, ly, margin=0.0):
    lx = np.asarray(lx, float)
    ly = np.asarray(ly, float)
    hy = env.half_y(lx)
    ok = (np.abs(lx) < env.rx * (1.0 - margin)) & (np.abs(ly) < hy * (1.0 - margin))
    ok &= (env.top_at(lx) + env.bot_at(lx)) > 0.02
    return ok


def _dist_to_edge(env, o, phi, step=0.01, max_d=6.0):
    d = 0.0
    v = np.array([np.cos(phi), np.sin(phi)])
    while d < max_d:
        q = o + v * (d + step)
        if not _inside(env, q[0], q[1]):
            return d
        d += step
    return d


def pad_surfaces(env, prm: PadParams):
    """Top and base heights of the pad at local (lx, ly), thickness clamped (flat pads)."""
    width = 2.0 * env.rx
    tmax = prm.max_thick_ratio * width
    xs_ = np.linspace(-env.rx, env.rx, 101)
    t_peak = float(np.max(env.top_at(xs_))) if len(xs_) else env.rz_top
    if prm.top_cap > 0:
        t_peak = min(t_peak, prm.top_cap)
    raw_top = env.top_at

    def top_env(lx):
        """The traced top, clamped under a smooth dome (a traced spike at a pad's end put bursts high on long
        vertical shoots: the 'pendant' the r0 judge flagged on PineB1)."""
        lx = np.asarray(lx, float)
        dome = t_peak * np.clip(1.0 - (lx / env.rx) ** 2, 0.0, 1.0) ** 0.4
        return np.minimum(raw_top(lx), dome)

    def top(lx, ly):
        lx = np.asarray(lx, float)
        ly = np.asarray(ly, float)
        hy = np.maximum(env.half_y(lx), 1e-3)
        yn = np.clip(np.abs(ly) / hy, 0, 1)
        t = top_env(lx)
        b = env.bot_at(lx)
        tot = t + b
        scale = np.where(tot > tmax, tmax / np.maximum(tot, 1e-6), 1.0)
        dome = np.sqrt(np.clip(1.0 - yn ** 4, 0.0, 1.0))           # flat plan dome
        return env.centre[2] + (t * scale) * (0.45 + 0.55 * dome)

    def base(lx, ly):
        lx = np.asarray(lx, float)
        ly = np.asarray(ly, float)
        t = top_env(lx)
        b = env.bot_at(lx)
        tot = t + b
        scale = np.where(tot > tmax, tmax / np.maximum(tot, 1e-6), 1.0)
        rho = np.clip(np.sqrt((lx / env.rx) ** 2 + (ly / np.maximum(env.half_y(lx), 1e-3)) ** 2), 0, 1)
        # flat underside, arched up a little in the middle (the lattice under a pad sags to the rim)
        return env.centre[2] - b * scale * (0.85 - 0.3 * (1 - rho ** 2))

    def arm_z(lx, ly):
        """Arms run through the lower third of the pad (not on its underside), so the bursts above them sit on
        short diagonal shoots even in thick pads."""
        zb = base(lx, ly)
        return zb + 0.3 * (top(lx, ly) - zb)

    return top, base, arm_z


def _to_world(env, lx, ly, z):
    L = np.stack([np.asarray(lx, float), np.asarray(ly, float), np.zeros_like(np.asarray(lx, float))], -1)
    W = env.world_dir(L) + np.array([env.centre[0], env.centre[1], 0.0])
    W[..., 2] = z
    return W


def grow_pad(env, hub: np.ndarray, d_in: np.ndarray, rng: np.random.Generator, prm: PadParams,
             pre_arms: Optional[List[np.ndarray]] = None) -> Dict:
    """Build one pad.

    hub   : world point where the feeding branch ends (the arms fan out from here)
    d_in  : world direction of the feeding branch at the hub
    pre_arms : optional world polylines of the feeding branch inside the pad (bursts are also set along them)
    Returns {"arms": [{"pts", "parent", "parent_node", "level"}], "shoots": [{"pts", "arm", "node"}],
             "sites": [{"p", "d", "kind", "arm", "node"}], "thickness", "n_bursts"}
      parent = -1 means the arm starts at the hub (on the feeding branch); parent = k means arm k, at parent_node.
      Shoot arm index -1 - j means pre_arms[j].
    """
    top, base, arm_z = pad_surfaces(env, prm)
    Lh = env.local(hub[None, :])[0]
    o = Lh[:2].copy()
    # hub outside the footprint: pull the fan origin onto the footprint edge along the incoming direction
    if not _inside(env, o[0], o[1], 0.05):
        c = np.zeros(2)
        for t in np.linspace(0, 1, 40):
            q = o * (1 - t) + c * t
            if _inside(env, q[0], q[1], 0.08):
                o = q
                break
    din_l = env.local((hub + d_in)[None, :])[0] - Lh
    din_h = din_l[:2]
    phi0 = float(np.arctan2(din_h[1], din_h[0])) if np.linalg.norm(din_h) > 1e-3 else float(rng.uniform(0, 2 * np.pi))
    # angular range seen from the fan origin
    rho_o = float(np.sqrt((o[0] / env.rx) ** 2 + (o[1] / max(float(env.half_y(o[0])), 1e-3)) ** 2))
    area = np.pi * env.rx * env.ry
    K = int(np.clip(round(area / (3.2 * prm.spacing ** 2 * 6) + 2), 3, 8))
    if rho_o < 0.55:
        # interior hub: arms all round except straight back along the incoming limb
        span = np.linspace(phi0, phi0 + 2 * np.pi, K + 1)[:-1]
        back = phi0 + np.pi
        phis = [p for p in span if abs(np.angle(np.exp(1j * (p - back)))) > np.deg2rad(40)]
        if len(phis) < 3:
            phis = list(span)
    else:
        angs = []
        for a in np.linspace(0, 2 * np.pi, 72, endpoint=False):
            b = np.array([np.cos(a) * env.rx * 0.98, np.sin(a) * float(env.half_y(np.cos(a) * env.rx * 0.98)) * 0.98])
            v = b - o
            if np.linalg.norm(v) > 0.05:
                angs.append(np.angle(np.exp(1j * (np.arctan2(v[1], v[0]) - phi0))))
        angs = np.array(angs)
        lo, hi = float(np.percentile(angs, 6)), float(np.percentile(angs, 94))
        phis = list(phi0 + np.linspace(lo + 0.12 * (hi - lo) / K, hi - 0.12 * (hi - lo) / K, K))
    phis = [p + rng.normal(0, np.deg2rad(7)) for p in phis]
    z_hub = float(hub[2])
    arms: List[Dict] = []

    def make_arm(o2, phi, length, z_start, parent, parent_node, level):
        n = max(3, int(np.ceil(length / 0.03)))
        t = np.linspace(0, 1, n)
        lx = o2[0] + np.cos(phi) * length * t
        ly = o2[1] + np.sin(phi) * length * t
        zb = arm_z(lx, ly)
        rise = np.clip(t / 0.3, 0, 1)
        rise = rise * rise * (3 - 2 * rise)
        z = z_start * (1 - rise) + zb * rise
        P = _to_world(env, lx, ly, z)
        seg = prm.arm_seg * (1.0 if level == 0 else 0.75)
        N, _ = angularize(P, seg, prm.arm_amp, rng, up_amp=0.25)
        knots = arclength(N)
        Q = resample(chaikin(N, 0.18), prm.node_step, min_points=3)
        arms.append({"pts": Q, "parent": parent, "parent_node": parent_node, "level": level,
                     "phi": phi, "knuckles": knots[1:-1]})
        return len(arms) - 1

    def _fork(ai, depth):
        A = arms[ai]
        Q = A["pts"]
        L = float(arclength(Q)[-1])
        if depth >= 2 or L < 2.4 * prm.spacing:
            return
        s = arclength(Q)
        f = rng.uniform(0.40, 0.62)
        j = int(np.searchsorted(s, f * L))
        j = min(max(j, 1), len(Q) - 2)
        Lj = env.local(Q[j][None, :])[0]
        for sgn in ((-1, 1) if rng.random() < 0.35 and depth == 0 else (1 if rng.random() < 0.5 else -1,)):
            dphi = sgn * np.deg2rad(rng.uniform(28, 45))
            phi = A["phi"] + dphi
            d_edge = _dist_to_edge(env, Lj[:2], phi)
            ln = 0.86 * d_edge
            if ln < 1.3 * prm.spacing:
                continue
            k = make_arm(Lj[:2], phi, ln, float(Q[j][2]), ai, j, A["level"] + 1)
            _fork(k, depth + 1)

    for phi in phis:
        d_edge = _dist_to_edge(env, o, phi)
        length = 0.88 * d_edge
        if length < 1.1 * prm.spacing:
            continue
        ai = make_arm(o, phi, length, z_hub, -1, 0, 0)
        _fork(ai, 0)
    # ------------------------------------------------------------------ burst sites (f1b)
    # r0 of this module put bursts at the pad top on shoots rising straight up from base-level arms: the pads read
    # as cages of vertical sticks. Now: a jittered hex grid of burst positions over the footprint, in 1-3 layers
    # through the upper part of the pad (the top layer just under the flat top, lower layers stepping out toward
    # the rim), each on a shoot from the arm node that keeps the shoot at 45 degrees or flatter.
    tuft_h = prm.burst_len
    pre_nodes = [np.asarray(P, float) for P in (pre_arms or [])]
    all_paths = [(i, A["pts"], A["level"]) for i, A in enumerate(arms)] + \
                [(-1 - j, P, 0) for j, P in enumerate(pre_nodes)]
    nodes_all = [(ai, j, Q[j]) for ai, Q, level in all_paths for j in range(len(Q))]
    sp = prm.spacing
    cand = []
    xs = np.arange(-env.rx, env.rx + 1e-9, sp)
    ys = np.arange(-env.ry, env.ry + 1e-9, sp * 0.866)
    for r_i, y in enumerate(ys):
        for x in xs + (0.5 * sp if r_i % 2 else 0.0):
            q = np.array([x, y]) + rng.normal(0, 0.22 * sp, 2)
            if _inside(env, q[0], q[1], 0.03):
                cand.append((q, 0))
    for ai, Q, level in all_paths:          # the arm tips carry a burst each (the pad's rim)
        Lq = env.local(Q[-1][None, :])[0]
        if ai >= 0 and _inside(env, Lq[0], Lq[1], 0.0):
            cand.append((Lq[:2], 1))
    holes = []
    for _ in range(prm.holes):
        a = rng.uniform(0, 2 * np.pi)
        rr = np.sqrt(rng.uniform(0.1, 0.55))
        holes.append((np.array([np.cos(a) * rr * env.rx, np.sin(a) * rr * env.ry]), rng.uniform(0.6, 0.95) * sp))
    sites: List[Dict] = []

    def mk(lxy, z, kind, outward):
        rho = float(np.sqrt((lxy[0] / env.rx) ** 2 + (lxy[1] / max(float(env.half_y(lxy[0])), 1e-3)) ** 2))
        radial = np.array([lxy[0], lxy[1], 0.0])
        radial = env.world_dir(radial / max(np.linalg.norm(radial), 1e-6))
        w = 0.75 * rho ** 2 + outward
        d = UP * max(1.0 - 0.45 * rho ** 2 - 0.5 * outward, 0.25) + radial * w + rng.normal(0, 0.14, 3)
        d /= np.linalg.norm(d)
        p = _to_world(env, np.array([lxy[0]]), np.array([lxy[1]]), np.array([z]))[0]
        T_ = float(top(lxy[0], lxy[1]) - base(lxy[0], lxy[1]))
        return {"p": p, "d": d, "kind": kind, "rho": rho, "lxy": np.array(lxy), "T": T_}

    for q, kind in cand:
        if any(np.hypot(*(q - hc)) < hr for hc, hr in holes):
            continue
        if kind == 0 and prm.keep < 1.0 and rng.random() > prm.keep:
            continue
        z_top = float(top(q[0], q[1]))
        z_b = float(base(q[0], q[1]))
        T = z_top - z_b
        z0 = z_top - 0.62 * tuft_h
        sites.append(mk(q, max(z0, z_b + 0.03), kind, 0.0))
        # lower layers where the pad is thick: stepped out toward the rim, pointing more outward
        room = T - 1.3 * tuft_h
        n_extra = int(room / (0.9 * tuft_h)) if room > 0 else 0
        for k in range(min(n_extra, 2)):
            if rng.random() > 0.55 + prm.lower_layer:
                continue
            depth = (k + 1) * rng.uniform(0.75, 1.0) * 0.9 * tuft_h
            radial = q / max(np.linalg.norm(q / np.array([env.rx, max(env.ry, 1e-3)])), 1e-6)
            q2 = q + (radial / max(np.linalg.norm(radial), 1e-6)) * 0.25 * sp * (k + 1) + rng.normal(0, 0.15 * sp, 2)
            if not _inside(env, q2[0], q2[1], 0.0):
                q2 = q
            sites.append(mk(q2, z0 - depth, 2, 0.35 + 0.2 * k))
    # ------------------------------------------------------------------ shoots: diagonal, kinked
    shoots = []
    if nodes_all:
        NP = np.array([n[2] for n in nodes_all])
        for s_ in sites:
            b = s_["p"]
            dz = b[2] - NP[:, 2]
            h = np.hypot(NP[:, 0] - b[0], NP[:, 1] - b[1])
            want = np.maximum(dz * 1.05, 0.2 * sp)
            cost = np.abs(h - want) + 0.35 * h + np.where(dz < -0.01, 10.0, 0.0) + np.where(h > 2.8 * sp, 5.0, 0.0)                 + np.where(dz > max(0.22, 2.4 * tuft_h, 0.8 * s_["T"]), 5.0, 0.0)
            k = int(np.argmin(cost))
            if cost[k] >= 5.0:
                continue                   # no arm near enough: no burst (r0 of f1 hung curtains of long shoots)
            ai, j, a = nodes_all[k]
            v = b - a
            L = float(np.linalg.norm(v))
            if L < 0.012:
                continue
            side = np.cross(v / L, UP)
            if np.linalg.norm(side) > 1e-6:
                side /= np.linalg.norm(side)
            # angular: first run out nearly level, then turn up (the sheet's twigs leave the arm and bend up)
            mid = a + np.array([v[0], v[1], 0.0]) * rng.uniform(0.45, 0.65) + UP * v[2] * rng.uniform(0.1, 0.3) \
                + side * rng.normal(0, 0.12) * L
            pts = [a, mid, b]
            if L > 0.22:
                m2 = a + v * 0.8 + side * rng.normal(0, 0.08) * L
                pts = [a, mid, m2, b]
            s_["arm"], s_["node"] = ai, j
            shoots.append({"pts": np.array(pts), "arm": ai, "node": j, "site": s_})
    thick = float(np.median([float(top(s_["lxy"][0], s_["lxy"][1]) - base(s_["lxy"][0], s_["lxy"][1]))
                             for s_ in sites])) if sites else 0.0
    return {"arms": arms, "shoots": shoots, "sites": [sh["site"] for sh in shoots], "thickness": thick,
            "n_bursts": len(shoots), "fan_origin_local": o.tolist(), "n_arms": len(arms)}


def _base_on(N, base, env):
    Ln = env.local(N)
    return base(Ln[:, 0], Ln[:, 1])
