"""Tree generator core: spec (metres) -> branch graph, pads, tufts, trunk and foliage arrays (numpy only).

TREE_BUILDING_STUDY.md section 4 (stages a-c, e): orders 0-1 (trunk, limbs) come from the traced spec; order 2+
(the twig network inside each pad) is grown by space colonisation toward the pad's shoot-tip sites; radii follow
the pipe model with the traced girth as a floor; nebari are swept root tubes (study 4.5: model the nebari as root
tubes when an SDF weld is not used). Species hooks (the tuft unit, the bark height map) are passed in.

Spec keys used here (all metres, Blender axes: X right, -Y front, Z up, origin at the trunk base / rock contact):
  trunk: {pts, min_r}            limbs: [{pad, pts, min_r, parent ('trunk' | limb list index), parent_t}]
  pads:  [{centre, rx, ry, rz_top, rz_bot, yaw, spacing?, holes?}]   apex_pad: int
  nebari: {count, reach, depth, r_share}   or   roots: [[p, ...], ...] (already on a rock surface)
  seed, pipe_n, tip_r, sink_below_m
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

import cloudpad as cp
import colonize as col
from skeleton import Branch, angularize, arclength, catmull_rom, chaikin, link_children, pipe_radii, resample, \
    smooth_resample
from tubes import TubeParams, build_branch, pack_rects

UP = np.array([0.0, 0.0, 1.0])


def _interp_profile(P_src: np.ndarray, r_src: np.ndarray, P_dst: np.ndarray) -> np.ndarray:
    s = arclength(P_src)
    t = arclength(P_dst)
    if s[-1] <= 0:
        return np.full(len(P_dst), float(r_src[0]))
    return np.interp(t / max(t[-1], 1e-9) * s[-1], s, r_src)


def _nearest_node(P: np.ndarray, q: np.ndarray) -> int:
    return int(np.argmin(((P - q) ** 2).sum(1)))


def build_skeleton(spec: Dict, rng: np.random.Generator) -> Dict:
    branches: List[Branch] = []
    # ---- trunk (order 0): traced, smoothed, continued below grade (study 4.2: sink for sloped placement)
    tp = np.asarray(spec["trunk"]["pts"], dtype=np.float64)
    tr = np.asarray(spec["trunk"]["min_r"], dtype=np.float64)
    sink = float(spec.get("sink_below_m", 0.2))
    below = tp[0] - np.array([0.0, 0.0, sink])
    tp_full = np.vstack([below[None, :], tp])
    tr_full = np.concatenate([[tr[0]], tr])
    T = smooth_resample(tp_full, 0.05)
    trunk = Branch(pts=T, parent=-1, order=0, kind="trunk", element=0, min_r=_interp_profile(tp_full, tr_full, T),
                   tip_r=float(spec.get("tip_r", 0.003)), seam_hint=(0.0, 1.0, 0.0),
                   exact_r=bool(spec.get("trunk_exact", False)))
    tk = spec.get("trunk_knuckles")
    if tk:
        sT = arclength(T)
        trunk.knuckles = np.array([float(t) * sT[-1] for t in tk["t"]])
        trunk.knuckle_amp = float(tk.get("amp", 0.1))
    branches.append(trunk)
    # v2: broken stubs on the trunk (C), short blunt branches with no pad
    sT = arclength(T)
    for st in spec.get("stubs", []):
        j = int(np.searchsorted(sT, float(st["t"]) * sT[-1]))
        j = min(max(j, 1), len(T) - 2)
        a, el = np.deg2rad(float(st["az"])), np.deg2rad(float(st["elev"]))
        d = np.array([np.cos(a) * np.cos(el), np.sin(a) * np.cos(el), np.sin(el)])
        L = float(st["length"])
        r0 = float(trunk.min_r[j]) * float(st["r_share"])
        P = np.array([T[j], T[j] + d * L * 0.5 + np.array([0, 0, -0.02]), T[j] + d * L])
        Q = resample(P, 0.03, min_points=3)
        branches.append(Branch(pts=Q, parent=0, parent_idx=j, order=1, kind="stub", min_r=np.linspace(r0, 0.8 * r0, len(Q)),
                               tip_r=0.8 * r0, seam_hint=(0.0, 0.0, 1.0), exact_r=True))
    limb_branch: Dict[int, int] = {}        # limb list index -> branch index
    feed: Dict[int, int] = {}               # pad -> feeding branch index
    apex = int(spec.get("apex_pad", 0))
    feed[apex] = 0
    trunk.pad = apex
    # ---- limbs (order 1-2): traced; attach to the trunk or a parent limb
    pending = list(enumerate(spec.get("limbs", [])))
    guard = 0
    while pending and guard < 1000:
        guard += 1
        li, L = pending.pop(0)
        par = L.get("parent", "trunk")
        if par != "trunk" and int(par) not in limb_branch:
            pending.append((li, L))
            continue
        P = np.asarray(L["pts"], dtype=np.float64)
        r = np.asarray(L["min_r"], dtype=np.float64)
        if par == "trunk":
            pb = 0
            j = _nearest_node(branches[0].pts, P[0])
        else:
            pb = limb_branch[int(par)]
            parent_pts = branches[pb].pts
            s = arclength(parent_pts)
            j = int(np.searchsorted(s, float(L.get("parent_t", 0.5)) * s[-1]))
            j = min(max(j, 1), len(parent_pts) - 2)
        start = branches[pb].pts[j]
        P = np.vstack([start[None, :], P[1:]]) if np.linalg.norm(P[0] - start) < 0.6 else np.vstack([start, P])
        zig = spec.get("zig")
        knots = None
        if zig:
            # angular zig-zag limbs (judge r0: 'one smooth tube from the trunk to the pad'): direction changes every
            # zig.seg metres, knuckles at the nodes; the traced path stays the authority (ends fixed)
            Ps = catmull_rom(P, per_segment=8)
            N, kn = angularize(Ps, float(zig["seg"]), float(zig["amp"]), rng, up_amp=0.3)
            Q = resample(chaikin(N, 0.2), 0.035, min_points=3)
            knots = kn[1:-1]
        else:
            Q = smooth_resample(P, 0.04)
        high = float(np.mean(Q[:, 2])) > 1.7
        b = Branch(pts=Q, parent=pb, parent_idx=j, order=branches[pb].order + 1, kind="limb", pad=int(L["pad"]),
                   min_r=_interp_profile(np.asarray(L["pts"]), r, Q), tip_r=float(spec.get("tip_r", 0.003)),
                   seam_hint=(0.0, 0.0, 1.0) if high else (0.0, 1.0, 0.0), knuckles=knots,
                   knuckle_amp=float(zig.get("knuckle", 0.0)) if zig else 0.0)
        branches.append(b)
        limb_branch[li] = len(branches) - 1
        feed[int(L["pad"])] = len(branches) - 1
    # v2f (judge delta 5, the fork close-up: two limbs passing through each other): push limb centrelines apart
    # where two limbs (or a limb and the trunk) come closer than 1.25 x their radii, away from their own junction;
    # the ends stay (the pad hubs)
    r_est = spec.get("_branch_r_est")
    if r_est:
        for bi_ in [0] + sorted(limb_branch.values()):
            if str(bi_) in r_est and len(r_est[str(bi_)]) == len(branches[bi_].pts):
                branches[bi_].r_est = np.asarray(r_est[str(bi_)], float)
    _separate_limbs(branches, sorted(limb_branch.values()))
    # ---- pads: envelopes, sites, colonisation (order 2+)
    envs: List[col.Envelope] = []
    tips: List[Dict] = []
    pad_info: List[Dict] = []
    for pi, pd in enumerate(spec["pads"]):
        if "profile" in pd:
            pr = pd["profile"]
            env = col.ProfileEnvelope(np.asarray(pr["centre"], dtype=np.float64), pr["hx"], pd["ry"],
                                      float(max(pr["top"])), float(max(pr["bot"])), pd.get("yaw", 0.0),
                                      np.asarray(pr["x"], float), np.asarray(pr["top"], float),
                                      np.asarray(pr["bot"], float))
        else:
            env = col.Envelope(np.asarray(pd["centre"], dtype=np.float64), pd["rx"], pd["ry"], pd["rz_top"],
                               pd["rz_bot"], pd.get("yaw", 0.0))
        envs.append(env)
        fb = feed.get(pi, 0)
        fpts = branches[fb].pts
        if spec.get("pad_method") == "fan":
            _fan_pad(spec, pi, pd, env, fb, branches, tips, pad_info, rng)
            continue
        if spec.get("pad_method") == "rosette":
            _rosette_pad(spec, pi, pd, env, fb, branches, tips, pad_info, rng)
            continue
        rho = env.rho(fpts)
        inside = np.nonzero(rho < 1.4)[0]
        if len(inside) == 0:
            inside = np.array([_nearest_node(fpts, env.centre)])
        if len(inside) > 3:
            near = _nearest_node(fpts, env.centre)
            cand = inside[np.argsort(np.abs(inside - near))]
            pick = [cand[0]]
            for c in cand[1:]:
                if all(abs(c - q) >= max(2, len(inside) // 3) for q in pick):
                    pick.append(c)
                if len(pick) == 3:
                    break
            inside = np.array(sorted(pick))
        anchors = fpts[inside]
        prng = np.random.default_rng(int(pd.get("seed", rng.integers(1 << 30))))
        sites, dirs, kind = col.tuft_sites(env, prng, spacing=float(pd.get("spacing", spec.get("tuft_spacing", 0.10))),
                                           holes=int(pd.get("holes", 1)), under_share=float(spec.get("under_share", 0.25)))
        nodes, parent = col.colonize(anchors, sites, D=float(spec.get("col_D", 0.035)),
                                     dk=float(spec.get("col_dk", 0.03)), di=float(spec.get("col_di", 0.45)))
        nodes, parent, tip_nodes = col.attach_tips(nodes, parent, len(anchors), sites, dirs)
        chs = col.chains(nodes, parent, len(anchors))
        node_ref: Dict[int, Tuple[int, int]] = {int(a_i): (fb, int(inside[a_i])) for a_i in range(len(anchors))}
        first_twig = len(branches)
        for ch in chs:
            attach = ch[0]
            pb, pj = node_ref[attach]
            pts = nodes[ch]
            b = Branch(pts=pts, parent=pb, parent_idx=pj, order=branches[pb].order + 1, kind="twig", pad=pi,
                       tip_r=float(spec.get("tip_r", 0.003)), seam_hint=(0.0, 0.0, 1.0))
            branches.append(b)
            bi = len(branches) - 1
            for k, nd in enumerate(ch[1:], start=1):
                node_ref[nd] = (bi, k)
        n_twigs = len(branches) - first_twig
        for tn, si in tip_nodes:
            tips.append({"p": nodes[tn], "d": dirs[si], "pad": pi, "kind": int(kind[si])})
        pad_info.append({"pad": pi, "feed_branch": fb, "anchors": len(anchors), "sites": len(sites),
                         "tips": len(tip_nodes), "twig_chains": n_twigs, "nodes": int(len(nodes))})
    # ---- nebari / rock roots
    base_r = float(tr[0])
    if "roots" in spec:
        root_b = {}
        for ri, R in enumerate(spec["roots"]):
            P = np.asarray(R["pts"], dtype=np.float64)
            pr = R.get("parent_root")
            if pr is not None and int(pr) in root_b:
                pb = root_b[int(pr)]
                j = _nearest_node(branches[pb].pts, P[0])
                start = branches[pb].pts[j]
                order = 2
            else:
                pb = 0
                j = _nearest_node(branches[0].pts, P[0])
                start = branches[0].pts[j]
                order = 1
            if "profile" in R:
                Q = np.vstack([start, P])
                Q = resample(Q, 0.03, min_points=3)
                s_ = arclength(Q)
                prof = np.interp(s_ / max(s_[-1], 1e-9), np.linspace(0, 1, len(R["profile"])), R["profile"])
            else:
                Q = smooth_resample(np.vstack([start, P]), 0.04)
                prof = np.linspace(R.get("r0", 0.35 * base_r), R.get("r1", 0.015), len(Q))
            branches.append(Branch(pts=Q, parent=pb, parent_idx=j, order=order, kind="root", min_r=prof, tip_r=0.01,
                                   seam_hint=(0.0, 0.0, 1.0), exact_r=bool(R.get("exact", False))))
            root_b[ri] = len(branches) - 1
    elif "nebari" in spec:
        nb = spec["nebari"]
        cnt = int(nb.get("count", 6))
        az0 = rng.uniform(0, 2 * np.pi)
        for i in range(cnt):
            az = az0 + i * 2 * np.pi / cnt + rng.normal(0, 0.35)
            reach = float(nb.get("reach", 3.0 * base_r)) * rng.uniform(0.7, 1.25)
            h0 = float(nb.get("start_z", 0.6 * base_r)) * rng.uniform(0.7, 1.2)
            j = _nearest_node(branches[0].pts, np.array([0, 0, h0]))
            start = branches[0].pts[j]
            dirv = np.array([np.cos(az), np.sin(az), 0.0])
            ctrl = np.array([start,
                             start + dirv * base_r * 0.9 + np.array([0, 0, -0.35 * h0]),
                             start + dirv * (base_r + 0.45 * reach) + np.array([0, 0, -0.8 * h0]),
                             start + dirv * (base_r + reach) + np.array([0, 0, -h0 - float(nb.get("depth", 0.12))])])
            Q = smooth_resample(ctrl, 0.04)
            prof = np.linspace(float(nb.get("r_share", 0.42)) * base_r, 0.018, len(Q))
            branches.append(Branch(pts=Q, parent=0, parent_idx=j, order=1, kind="root", min_r=prof, tip_r=0.012,
                                   seam_hint=(0.0, 0.0, 1.0)))
    # v2: limbs truncated at their pad hub; children attached past the new end move to the end
    for b in branches:
        if b.parent >= 0:
            b.parent_idx = min(b.parent_idx, len(branches[b.parent].pts) - 1)
    pipe_radii(branches, n=float(spec.get("pipe_n", 2.3)), min_r=float(spec.get("min_twig_r", 0.0)))
    return {"branches": branches, "envs": envs, "tips": tips, "pad_info": pad_info, "feed": feed,
            "limb_branch": limb_branch,
            "branch_r": {str(bi_): branches[bi_].r.tolist() for bi_ in [0] + sorted(limb_branch.values())
                         if branches[bi_].r is not None}}


def build_skeleton_separated(spec, rng):
    """v2f: two passes. Pass 1 gives the final (pipe-model) limb radii; pass 2 repeats the same random sequence and
    separates the limbs with those radii (pass 1's min_r floors under-estimated the fork close-up's overlaps)."""
    state = rng.bit_generator.state
    sk = build_skeleton(spec, rng)
    spec["_branch_r_est"] = sk["branch_r"]
    rng.bit_generator.state = state
    sk = build_skeleton(spec, rng)
    spec.pop("_branch_r_est", None)
    return sk


def _separate_limbs(branches, ids, iters=8):
    def rad(b):
        r = np.asarray(b.min_r if b.min_r is not None else np.full(len(b.pts), 0.03), float)
        re_ = getattr(b, "r_est", None)       # final radii from a first pass (the pipe model thickens limbs)
        if re_ is not None and len(re_) == len(r):
            r = np.maximum(r, 0.9 * re_)
        return r
    for _ in range(iters):
        worst = 0.0
        for bi in ids:
            b = branches[bi]
            P = b.pts.copy()
            R = rad(b)
            s = arclength(P)
            disp = np.zeros_like(P)
            for oj in [0] + list(ids):
                if oj == bi:
                    continue
                o = branches[oj]
                Q = o.pts
                Ro = rad(o)
                so = arclength(Q)
                if o is branches[b.parent] if b.parent >= 0 else False:
                    guard_b = 1.6 * float(Ro[min(b.parent_idx, len(Ro) - 1)]) + 0.04
                else:
                    guard_b = 0.0
                guard_o = (1.6 * float(R[0]) + 0.04) if (o.parent == bi) else 0.0
                for k in range(1, len(P) - 2):
                    if s[k] < guard_b:
                        continue
                    d = np.linalg.norm(Q - P[k], axis=1)
                    if guard_o > 0:
                        d = np.where(so < guard_o, 9.0, d)
                    j = int(np.argmin(d))
                    need = 1.25 * (float(R[min(k, len(R) - 1)]) + float(Ro[min(j, len(Ro) - 1)])) + 0.008
                    if d[j] < need:
                        v = P[k] - Q[j]
                        n = np.linalg.norm(v)
                        if n < 1e-6:
                            v = np.cross(np.gradient(P, axis=0)[k], [0.0, 0.0, 1.0])
                            n = max(np.linalg.norm(v), 1e-9)
                        disp[k] += v / n * (need - d[j]) * 0.6
                        worst = max(worst, need - d[j])
            if np.abs(disp).max() > 0:
                # smooth the push along the limb (no kinks), keep the ends
                for _s in range(3):
                    disp[1:-1] = 0.25 * disp[:-2] + 0.5 * disp[1:-1] + 0.25 * disp[2:]
                disp[0] = 0.0
                disp[-2:] = 0.0
                b.pts = P + disp
        if worst < 0.004:
            break


def _fan_pad(spec, pi, pd, env, fb, branches, tips, pad_info, rng):
    """f1 pad: an open lattice of angular forked arms + one radial burst per shoot (cloudpad.py)."""
    fpts = branches[fb].pts
    fp = spec.get("fan", {})
    prm = cp.PadParams(burst_len=float(fp.get("burst_len", 0.09)),
                       spacing=float(pd.get("spacing", fp.get("spacing", 0.12))),
                       arm_seg=float(fp.get("arm_seg", 0.10)), arm_amp=float(fp.get("arm_amp", 0.45)),
                       holes=int(pd.get("holes", fp.get("holes", 1))), keep=float(pd.get("keep", fp.get("keep", 1.0))),
                       lower_layer=float(fp.get("lower_layer", 0.25)),
                       max_thick_ratio=float(fp.get("max_thick_ratio", 0.38)),
                       top_cap=1.15 * float(pd.get("rz_top", 0.0)))
    prng = np.random.default_rng(int(pd.get("seed", rng.integers(1 << 30))))
    # hub: where the feeding branch ends inside (or nearest to) the pad
    L = env.local(fpts)
    ins = cp._inside(env, L[:, 0], L[:, 1], 0.0) & (L[:, 2] > -1.5 * env.rz_bot - 0.15) & (L[:, 2] < env.rz_top)
    if branches[fb].kind == "trunk":
        j_hub = len(fpts) - 1
    else:
        j_hub = len(fpts) - 1 if ins[-1] else _nearest_node(fpts, env.centre)
    hub = fpts[j_hub]
    d_in = fpts[j_hub] - fpts[max(j_hub - 3, 0)]
    d_in = d_in / max(np.linalg.norm(d_in), 1e-9)
    pre_idx = np.nonzero(ins)[0]
    pre_idx = pre_idx[pre_idx <= j_hub]
    pre = [fpts[pre_idx]] if len(pre_idx) >= 3 else []
    if not pre:
        pre_idx = np.zeros(0, int)
    res = cp.grow_pad(env, hub, d_in, prng, prm, pre_arms=pre)
    tip_r = float(spec.get("tip_r", 0.0032))
    arm_b = {}
    arm_shift = {}
    base_order = branches[fb].order + 1
    for ai, A in enumerate(res["arms"]):
        P = A["pts"]
        shift = 0
        if A["parent"] < 0:
            pb, pj = fb, j_hub
            if np.linalg.norm(P[0] - hub) > 1e-3:
                P = np.vstack([hub[None, :], P])
                shift = 1
        else:
            pb, pj = arm_b[A["parent"]], int(A["parent_node"]) + arm_shift[A["parent"]]
            pj = min(pj, len(branches[pb].pts) - 1)
            P = P.copy()
            P[0] = branches[pb].pts[pj]
        b = Branch(pts=P, parent=pb, parent_idx=pj, order=(branches[pb].order + 1) if A["parent"] >= 0 else base_order,
                   kind="twig", pad=pi, tip_r=tip_r, seam_hint=(0.0, 0.0, 1.0),
                   knuckles=np.asarray(A["knuckles"], float), knuckle_amp=float(fp.get("knuckle", 0.14)))
        branches.append(b)
        arm_b[ai] = len(branches) - 1
        arm_shift[ai] = shift
    for sh in res["shoots"]:
        ai = sh["arm"]
        if ai >= 0:
            pb = arm_b[ai]
            pj = min(int(sh["node"]) + arm_shift[ai], len(branches[pb].pts) - 1)
        else:
            pb = fb
            pj = int(pre_idx[int(sh["node"])])
        P = sh["pts"].copy()
        P[0] = branches[pb].pts[pj]
        b = Branch(pts=P, parent=pb, parent_idx=pj, order=branches[pb].order + 1, kind="twig", pad=pi, tip_r=tip_r,
                   seam_hint=(0.0, 0.0, 1.0))
        branches.append(b)
        s_ = sh["site"]
        tips.append({"p": P[-1], "d": s_["d"], "pad": pi, "kind": int(s_["kind"])})
    pad_info.append({"pad": pi, "feed_branch": fb, "method": "fan", "arms": res["n_arms"], "bursts": res["n_bursts"],
                     "thickness_m": round(res["thickness"], 3), "width_m": round(2 * float(env.rx), 3)})


def _rosette_pad(spec, pi, pd, env, fb, branches, tips, pad_info, rng):
    """v2 pad: a dome of 15-25 rosettes on a ramified, knuckled twig lattice (rosettepad.py). The feeding limb
    ends at the hub inside the pad (it disappears into the pad); the lattice fans out from there."""
    import rosettepad as rp_
    fpts = branches[fb].pts
    rp = spec.get("rosette_pad", {})
    prm = rp_.RosettePadParams(**{k: v for k, v in rp.items() if k in rp_.RosettePadParams.__dataclass_fields__})
    prm.top_cap = 1.15 * float(pd.get("rz_top", 0.0))
    for k in ("holes", "n_min", "n_max", "max_thick_ratio"):
        if k in pd:
            setattr(prm, k, pd[k])
    prng = np.random.default_rng(int(pd.get("seed", rng.integers(1 << 30))))
    L = env.local(fpts)
    ins = cp._inside(env, L[:, 0], L[:, 1], 0.0) & (L[:, 2] > -1.5 * env.rz_bot - 0.15) & (L[:, 2] < env.rz_top)
    if branches[fb].kind == "trunk":
        j_hub = len(fpts) - 1
    else:
        idx = np.nonzero(ins)[0]
        if len(idx):
            # the limb node inside the footprint closest (in plan) to a point 30 % in from the pad centre toward
            # the limb's entry: the hub sits on the trunk side of the pad centre
            e0 = L[idx[0], :2]
            tgt = 0.30 * e0
            j_hub = int(idx[np.argmin(((L[idx, :2] - tgt) ** 2).sum(1))])
        else:
            j_hub = _nearest_node(fpts, env.centre)
        j_hub = max(j_hub, 2)
        if j_hub < len(fpts) - 1:
            b = branches[fb]
            b.pts = b.pts[: j_hub + 1]
            if b.min_r is not None:
                # s4: the limb tapers to about 45 % of its base floor where it enters the pad (s3: a thick log end at
                # the hub; the sheet's limbs thin to a few cm and split into the twig net)
                mr = np.asarray(b.min_r)[: j_hub + 1]
                b.min_r = mr * np.linspace(1.0, 0.45, len(mr))
            if b.knuckles is not None:
                b.knuckles = np.asarray(b.knuckles)[np.asarray(b.knuckles) < arclength(b.pts)[-1]]
            fpts = b.pts
    hub = fpts[j_hub]
    d_in = fpts[j_hub] - fpts[max(j_hub - 3, 0)]
    d_in = d_in / max(np.linalg.norm(d_in), 1e-9)
    res = rp_.grow_rosette_pad(env, hub, d_in, prng, prm)
    tip_r = float(spec.get("tip_r", 0.004))
    kn_amp = float(rp.get("knuckle", 0.22))
    arm_b = {}
    for ai, A in enumerate(res["arms"]):
        P = A["pts"].copy()
        if A["parent"] < 0:
            pb, pj = fb, j_hub
        else:
            pb, pj = arm_b[A["parent"]], int(A["parent_node"])
            pj = min(pj, len(branches[pb].pts) - 1)
        P[0] = branches[pb].pts[pj]
        b = Branch(pts=P, parent=pb, parent_idx=pj, order=branches[pb].order + 1, kind="twig", pad=pi, tip_r=tip_r,
                   seam_hint=(0.0, 0.0, 1.0), knuckles=np.asarray(A["knuckles"], float), knuckle_amp=kn_amp)
        branches.append(b)
        arm_b[ai] = len(branches) - 1
    for sh in res["shoots"]:
        ai = sh["arm"]
        if ai >= 0:
            pb = arm_b[ai]
            pj = min(int(sh["node"]), len(branches[pb].pts) - 1)
        else:
            pb, pj = fb, j_hub
        P = sh["pts"].copy()
        P[0] = branches[pb].pts[pj]
        b = Branch(pts=P, parent=pb, parent_idx=pj, order=branches[pb].order + 1, kind="twig", pad=pi, tip_r=tip_r,
                   seam_hint=(0.0, 0.0, 1.0))
        branches.append(b)
        s_ = sh["site"]
        tips.append({"p": P[-1], "d": s_["d"], "pad": pi, "kind": int(s_["kind"])})
    pad_info.append({"pad": pi, "feed_branch": fb, "method": "rosette", "rosettes": res["n_rosettes"],
                     "target": res["n_target"], "arms": res["n_arms"], "fork_levels": res["fork_levels"],
                     "thickness_m": round(res["thickness"], 3), "width_m": round(res["width"], 3),
                     "max_shoot_rise_deg": res["max_shoot_rise_deg"], "holes": res["holes"],
                     "spacing_m": res["spacing"]})


# ----------------------------------------------------------------------------- trunk mesh

def build_trunk_arrays(sk: Dict, height: Optional[np.ndarray], params: TubeParams, rng: np.random.Generator,
                       ground_z: float = 0.0) -> Dict:
    branches: List[Branch] = sk["branches"]
    link_children(branches)
    parts = {}
    v_ring_of: Dict[int, np.ndarray] = {}
    s_of: Dict[int, np.ndarray] = {}
    # parents first so a child can continue its parent's V
    from skeleton import topo_order
    for bi in topo_order(branches):
        b = branches[bi]
        parent = branches[b.parent] if b.parent >= 0 else None
        v0 = 0.0
        if parent is not None and b.parent in v_ring_of:
            # parent's V at the attachment (its rings are resampled: map by arclength)
            ps = arclength(parent.pts)
            s_att = ps[min(b.parent_idx, len(ps) - 1)]
            v0 = float(np.interp(s_att, s_of[b.parent], v_ring_of[b.parent])) % 1.0
        part = build_branch(b, bi, parent, params, height, v0, rng, is_trunk=(bi == 0), flare_base_z=ground_z)
        if part is None:
            continue
        parts[bi] = part
        v_ring_of[bi] = part["v_ring"]
        # arclength of the (resampled) ring centres measured on the ORIGINAL polyline frame
        s_of[bi] = arclength(part["rings"]) + (arclength(b.pts)[-1] - arclength(part["rings"])[-1])
    offsets, (uw, vh) = pack_rects([p["rect"] for p in parts.values()])
    Vs, Fq, Fq_uv, Ft, Ft_uv = [], [], [], [], []
    vb, vs, vr, vj, vo, vn, vp = [], [], [], [], [], [], []
    off = 0
    for bi, p in parts.items():
        du, dv = offsets[bi]
        Vs.append(p["V"])
        for f, uv in zip(p["faces"], p["uvs"]):
            uv2 = uv.copy()
            uv2[..., 0] += du
            uv2[..., 1] += dv
            if f.shape[1] == 4:
                Fq.append(f + off)
                Fq_uv.append(uv2)
            else:
                Ft.append(f + off)
                Ft_uv.append(uv2)
        n = len(p["V"])
        b = branches[bi]
        vb.append(np.full(n, bi))
        vs.append(p["s"])
        vr.append(p["r"])
        vj.append(p["junction"])
        vo.append(np.full(n, b.order))
        vn.append(p["nrm"])
        vp.append(np.full(n, b.pad))
        off += n
    return {"V": np.vstack(Vs), "quads": np.vstack(Fq), "quads_uv": np.vstack(Fq_uv), "tris": np.vstack(Ft),
            "tris_uv": np.vstack(Ft_uv), "branch": np.concatenate(vb), "s": np.concatenate(vs),
            "r": np.concatenate(vr), "junction": np.concatenate(vj), "order": np.concatenate(vo),
            "nrm": np.vstack(vn), "pad": np.concatenate(vp), "uv_extent": (uw, vh), "parts": parts,
            "offsets": offsets}


def canopy_ao(P: np.ndarray, envs: List[col.Envelope], strength: float = 0.55) -> np.ndarray:
    """Cheap per-point occlusion from the pad envelopes: points inside or under a pad are darker (study 4.8)."""
    ao = np.ones(len(P))
    for e in envs:
        L = e.local(P)
        rho_xy = np.sqrt((L[:, 0] / (e.rx * 1.15)) ** 2 + (L[:, 1] / (e.ry * 1.15)) ** 2)
        under = np.clip(1.0 - rho_xy, 0.0, 1.0)
        dz = L[:, 2]
        # inside the pad: strong; below it (within ~1 pad radius): shadowed, fading with the distance down
        fall = np.where(dz > -e.rz_bot, 1.0, np.exp((dz + e.rz_bot) / max(0.8 * max(e.rx, e.ry), 0.05)))
        occ = strength * under ** 0.7 * fall * np.where(dz > e.rz_top, 0.0, 1.0)
        ao *= 1.0 - np.clip(occ, 0.0, 0.85)
    return np.clip(ao, 0.15, 1.0)


def foliage_ao(P: np.ndarray, pad: np.ndarray, envs: List[col.Envelope]) -> np.ndarray:
    """UV3.U AO for needles (study 4.8): normalised depth inside the pad blended with height in the pad."""
    ao = np.ones(len(P))
    for pi, e in enumerate(envs):
        m = pad == pi
        if not m.any():
            continue
        rho = e.rho(P[m])
        h = np.clip((P[m, 2] - e.bot_z) / max(e.top_z - e.bot_z, 1e-3), 0.0, 1.0)
        own = np.clip(0.18 + 0.5 * np.clip(rho, 0, 1.1) + 0.42 * h, 0.15, 1.0)
        others = [o for j, o in enumerate(envs) if j != pi]
        # the other pads (mostly those above) shade this one
        ao[m] = own * (canopy_ao(P[m], others, 0.35) ** 0.5 if others else 1.0)
    return np.clip(ao, 0.12, 1.0)
