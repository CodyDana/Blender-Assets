"""wd_run - fit the visible passes, solve their order from the probes, render previews.

usage: python wd_run.py <tag> [arcs|full]
Outputs (scratch): WorkFiles/smokebomb/rewind/wind/wd_out/<tag>_*.png / .json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
from wd_png import write_png  # noqa: E402
import wd_fitlib as FL  # noqa: E402
import wd_passes as TP  # noqa: E402
from props_lib import smokebomb_wind as W  # noqa: E402

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_out"
os.makedirs(OUT, exist_ok=True)
REF = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology/sb_ref_srgb.npy")

PAL = np.array([
    (0.90, 0.10, 0.10), (0.10, 0.60, 0.95), (0.95, 0.75, 0.10), (0.20, 0.80, 0.30), (0.80, 0.30, 0.90),
    (0.10, 0.85, 0.85), (0.95, 0.45, 0.10), (0.55, 0.35, 0.95), (0.60, 0.95, 0.30), (0.95, 0.40, 0.65),
    (0.35, 0.55, 0.20), (0.20, 0.35, 0.75), (0.75, 0.55, 0.30), (0.40, 0.90, 0.65), (0.85, 0.85, 0.45),
    (0.55, 0.10, 0.35), (0.10, 0.45, 0.45), (0.95, 0.60, 0.95), (0.45, 0.25, 0.10), (0.65, 0.75, 0.95),
    (0.30, 0.30, 0.30), (0.95, 0.95, 0.95), (0.70, 0.20, 0.10), (0.15, 0.70, 0.55)])


NAMED = {"W": (0.97, 0.62, 0.95), "A": (0.10, 0.45, 0.45), "B": (0.20, 0.35, 0.75), "C": (0.55, 0.10, 0.35),
         "X": (0.95, 0.45, 0.10), "R2": (0.62, 0.52, 0.30), "R3": (0.45, 0.25, 0.10), "Rin": (0.65, 0.75, 0.95),
         "U0": (0.95, 0.75, 0.10), "U1": (0.95, 0.40, 0.65), "U2": (0.55, 0.35, 0.95), "U3": (0.10, 0.85, 0.85),
         "U4": (0.80, 0.30, 0.90), "U5": (0.20, 0.80, 0.30), "L3": (0.40, 0.90, 0.65), "L4": (0.75, 0.55, 0.30),
         "Da": (0.85, 0.85, 0.45), "Db": (0.35, 0.55, 0.20), "Dc": (0.60, 0.95, 0.30), "E": (0.10, 0.60, 0.95)}


def pass_colour(k, names):
    nm = names[k]
    if nm.startswith("core") or nm.startswith("hid"):
        return np.array([0.16, 0.16, 0.18])
    if nm in NAMED:
        return np.array(NAMED[nm])
    return PAL[k % len(PAL)]


def tuck_ranges(passes, tucks, order):
    """[(pass idx, phi0, phi1, under name)] from the TUCKS table (image points -> phi)."""
    names = [p.name for p in passes]
    out = []
    for pn, px, side, under in tucks:
        if under.startswith("@all:"):
            under = tuple(under[5:].split(","))
        elif under.startswith("@first:"):
            cand = under[7:].split(",")
            under = (min(cand, key=lambda n: order.index(n)),)
        else:
            under = (under,)
        k = names.index(pn)
        ps = passes[k]
        ph, _ = ps.coords(FL.px2cam(px))
        ph = float(ph[0])
        out.append((k, ps.phi_a - 1, ph, under) if side == "before" else (k, ph, ps.phi_b + 1, under))
    return out


def arcs_winding(passes, order_keys=None, truns=()):
    """the passes' FRONT arcs only (no connectors), keyed by their order."""
    cs, ws, gs, pi, ph, keys = [], [], [], [], [], []
    tt = []
    for k, ps in enumerate(passes):
        phi = np.arange(ps.phi_a, ps.phi_b, 0.2)
        c = ps.point(phi)
        t = np.gradient(c, axis=0)
        t = W.normalize(t - np.einsum("ij,ij->i", t, c)[:, None] * c)
        cs.append(c)
        tt.append(t)
        ws.append(ps.width_rad(phi))
        gs.append(ps.gather_at(phi))
        pi.append(np.full(phi.size, k))
        ph.append(phi)
        base = k if order_keys is None else order_keys[k]
        kk = base * 1000.0 + np.arange(phi.size) * 1e-3
        for (ti, p0, p1, under) in truns:
            if ti == k:
                nms = [p.name for p in passes]
                ub = min((nms.index(u) if order_keys is None else order_keys[nms.index(u)]) for u in under)
                m = (phi >= p0) & (phi <= p1)
                kk[m] = (ub - 0.5) * 1000.0 + np.arange(m.sum()) * 1e-6
        keys.append(kk)
    c = np.vstack(cs)
    t = np.vstack(tt)
    b = W.normalize(np.cross(c, t))
    s = np.arange(len(c)) * 0.2 * W.DEG
    return W.Winding(s=s, c=c, t=t, b=b, w=np.concatenate(ws), gather=np.concatenate(gs),
                     pass_idx=np.concatenate(pi), phi=np.concatenate(ph), tail=np.full(len(c), np.nan),
                     key=np.concatenate(keys), passes=list(passes), tucks=[])


def colour_labels(lab, names, edge_dark=True):
    size = lab["size"]
    pas = lab["pass_"]
    img = np.ones((size, size, 3)) * 0.996
    has = pas >= 0
    cols = np.array([pass_colour(k, names) for k in range(len(names))])
    img[has] = cols[pas[has]]
    if edge_dark:
        v = lab["v"]
        # darken the outer ~2 px of each top band (its edges)
        R = lab["R"]
        # approximate: |v| close to 1
        e = has & (np.abs(np.nan_to_num(v)) > 0.93)
        img[e] *= 0.45
    return img


def ref_small(size):
    k = W.REF_SIZE_PX // size
    a = REF[: size * k, : size * k, :3].reshape(size, k, size, k, 3).mean((1, 3))
    return np.clip(a, 0, 1) ** 0.55


def draw_pts(img, pts_px, col, scale, r=1):
    h, w = img.shape[:2]
    for x, y in pts_px:
        xi, yi = int(round(x * scale)), int(round(y * scale))
        if 0 <= xi < w and 0 <= yi < h:
            img[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1] = col


def edges_overlay(base, lab, names):
    """draw every top band's boundary (label change) on ``base``."""
    pas = lab["pass_"]
    out = base.copy()
    bd = np.zeros_like(pas, bool)
    bd[:-1] |= pas[:-1] != pas[1:]
    bd[:, :-1] |= pas[:, :-1] != pas[:, 1:]
    cols = np.array([pass_colour(k, names) for k in range(len(names))])
    has = bd & (pas >= 0)
    out[has] = cols[pas[has]]
    return out


def spec_edges_overlay(img, scale, col=(1, 1, 1)):
    for nm, P in FL.EDGES_PX.items():
        Q = FL.resample_poly(P, 2.0)
        draw_pts(img, Q, np.array(col), scale, 0)


def probe_report(lab, passes, probes, show_map, scale):
    names = [p.name for p in passes]
    rep = {}
    pas = lab["pass_"]
    for band, P in probes.items():
        want = show_map.get(band)
        if want is None:
            continue
        ok, bad = 0, {}
        for x, y in P:
            xi, yi = int(x * scale), int(y * scale)
            k = pas[yi, xi]
            got = names[k] if k >= 0 else "bg"
            if got == want:
                ok += 1
            else:
                bad[got] = bad.get(got, 0) + 1
        rep[band] = dict(want=want, ok=ok, n=len(P), frac=round(ok / max(1, len(P)), 3), wrong=bad)
    return rep


def covers(ps: W.PassSpec, P: np.ndarray) -> np.ndarray:
    ph, lam = ps.coords(P)
    inside = (ph >= ps.phi_a) & (ph <= ps.phi_b)
    be = ps.beta_rad(ph)
    hw = 0.5 * (ps.width_rad(ph) * (1 - ps.gather_at(ph)) + W.CORD_W * ps.gather_at(ph))
    return inside & (np.abs(lam - be) <= hw)


def solve_order(passes, probes, show_map, truns=()):
    """pairwise constraints i < j from probes (a tucked stretch gives under < j)."""
    names = [p.name for p in passes]
    idx = {n: i for i, n in enumerate(names)}
    cons = {}
    for band, P in probes.items():
        j = show_map.get(band)
        if j is None or j not in idx:
            continue
        Pc = FL.px2cam(P)
        for i, ps in enumerate(passes):
            if ps.name == j:
                continue
            cv = covers(ps, Pc)
            if cv.any():
                ph, _ = ps.coords(Pc)
                tk = np.zeros(len(Pc), bool)
                for (ti, p0, p1, under) in truns:
                    if ti == i:
                        m = cv & (ph >= p0) & (ph <= p1)
                        tk |= m
                m = cv & ~tk
                if m.any():
                    cons[(ps.name, j)] = cons.get((ps.name, j), 0) + int(m.sum())
    return cons


def best_order(names, cons, iters=20000, seed=1):
    """permutation minimising the weight of violated i<j constraints (feedback arc set,
    greedy + random swaps).  Returns (order, violated list)."""
    rng = np.random.default_rng(seed)
    n = len(names)
    idx = {nm: i for i, nm in enumerate(names)}
    Wm = np.zeros((n, n))
    for (a, b), w in cons.items():
        Wm[idx[a], idx[b]] += 1.0 + 0.02 * w     # ~ one tuck per violated pair
    for (a, b) in getattr(TP, "PINS", []):
        if a in idx and b in idx:
            Wm[idx[a], idx[b]] += 1000.0
    def cost(perm):
        pos = np.empty(n, int); pos[perm] = np.arange(n)
        viol = pos[:, None] > pos[None, :]
        return float((Wm * viol).sum())
    # greedy: repeatedly take the node with max (out - in) weight among remaining ... (Eades)
    rem = list(range(n)); left, right = [], []
    while rem:
        sub = np.ix_(rem, rem)
        outw = Wm[sub].sum(1); inw = Wm[sub].sum(0)
        k = int(np.argmax(inw - outw))
        right.insert(0, rem[k]) if False else None
        k = int(np.argmin(inw - outw))
        left.append(rem.pop(k))
    perm = np.array(left)
    c = cost(perm)
    for it in range(iters):
        i, j = rng.integers(0, n, 2)
        if i == j: continue
        q = list(perm); x = q.pop(i); q.insert(j, x); q = np.array(q)
        cq = cost(q)
        if cq <= c:
            perm, c = q, cq
    pos = np.empty(n, int); pos[perm] = np.arange(n)
    viol = [(names[a], names[b], Wm[a, b]) for a in range(n) for b in range(n) if Wm[a, b] > 0 and pos[a] > pos[b]]
    return [names[k] for k in perm], viol, c


def auto_tucks(passes, probes, show_map, order, truns, margin=6.0):
    """stretches of pass i that cover probes of a band ordered BELOW i -> tucked under the
    earliest such band.  Returns extra tuck runs [(i, phi0, phi1, under)]."""
    names = [p.name for p in passes]
    pos = {n: order.index(n) for n in names}
    out = []
    for i, ps in enumerate(passes):
        own = set(ps.shows)
        hits = []   # (phi, band pass name)
        for band, P in probes.items():
            j = show_map.get(band)
            if j is None or j == ps.name:
                continue
            Pc = FL.px2cam(P)
            cv = covers(ps, Pc)
            if not cv.any():
                continue
            ph, _ = ps.coords(Pc[cv])
            # already tucked there?
            key_ok = np.zeros(len(ph), bool)
            for (ti, p0, p1, under) in truns:
                if ti == i:
                    key_ok |= (ph >= p0) & (ph <= p1) & (j in under)
            for f, okk in zip(ph, key_ok):
                if pos[ps.name] > pos[j] and not okk:
                    hits.append((float(f), j))
        if not hits:
            continue
        hits.sort()
        # own visible probes: phi values that must stay on top
        ownph = []
        for band in own:
            if band in probes:
                ph, _ = ps.coords(FL.px2cam(probes[band]))
                ownph += list(ph)
        ownph = np.array(ownph) if ownph else np.zeros(0)
        # group hits into runs
        runs = []
        for f, j in hits:
            if runs and f - runs[-1][1] <= 2 * margin:
                runs[-1][1] = f
                runs[-1][2].add(j)
            else:
                runs.append([f, f, {j}])
        for f0, f1, js in runs:
            under = tuple(sorted(js, key=lambda n: pos[n]))
            a, b = f0 - margin, f1 + margin
            # a real conflict: the covering pass also covers this pass's OWN visible probes
            for band in own:
                if band not in probes:
                    continue
                Pc = FL.px2cam(probes[band])
                for u in under:
                    cu = covers(passes[names.index(u)], Pc)
                    if cu.any():
                        print(f"   !! {u} covers {int(cu.sum())} of {ps.name}'s own visible probes ({band}) - geometry conflict")
            out.append((i, a, b, under))
    return out


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "t0"
    mode = sys.argv[2] if len(sys.argv) > 2 else "arcs"
    t0 = time.time()
    table = TP.pass_table()
    passes = []
    fitrep = {}
    for pf in table:
        ps = FL.fit_pass(pf)
        passes.append(ps)
        rr = {}
        for t in pf.terms:
            if t.kind == "own" and len(t.pts) and getattr(t, "cam", None) is None:
                d = FL.true_edge_residual_px(ps, t)
                rr[t.label] = dict(rms=round(float(np.sqrt((d ** 2).mean())), 1), max=round(float(d.max()), 1))
        st, _, _ = FL.pass_strain(ps)
        rr["strain%"] = round(st * 100, 1)
        be = np.degrees(ps.beta_rad(np.linspace(ps.phi_a, ps.phi_b, 200)))
        rr["beta"] = (round(float(be.min())), round(float(be.max())))
        wf = np.array(ps.width) 
        rr["w"] = (round(float(wf.min()), 3), round(float(wf.max()), 3))
        fitrep[pf.name] = rr
    print("fit residuals (own edges, px):")
    for k, v in fitrep.items():
        print("  ", k.ljust(5), v)
    probes = TP.band_probes()
    show_map = {}
    for ps in passes:
        for b in ps.shows:
            show_map[b] = ps.name
    truns0 = tuck_ranges(passes, TP.TUCKS, [p.name for p in passes])
    # iterate: the '@first' resolution depends on the order
    order = [p.name for p in passes]
    for _it in range(3):
        truns = tuck_ranges(passes, TP.TUCKS, order)
        cons = solve_order(passes, probes, show_map, truns)
        order, viol, c = best_order([p.name for p in passes], cons)
    print("order constraints (i under j):")
    for (i, j), n in sorted(cons.items(), key=lambda x: -x[1]):
        print(f"   {i:>5s} < {j:<5s} ({n})")
    names = [p.name for p in passes]
    if "autotuck" in sys.argv:
        extra = auto_tucks(passes, probes, show_map, order, truns)
        print("auto tucks:", [(names[i], round(a), round(b), u) for i, a, b, u in extra])
        truns = list(truns) + extra
    print("best order (bottom -> top):", " ".join(order))
    print("violated (i should be under j):", [(a, b, int(w)) for a, b, w in viol], "total", c)
    okeys = [order.index(nm) for nm in names]
    size = 627
    sc = size / W.REF_SIZE_PX
    wd = arcs_winding(passes, okeys, truns)
    lab = W.render_labels(wd, "front", size)
    img = colour_labels(lab, names)
    rep = probe_report(lab, passes, probes, show_map, sc)
    print("probe report:")
    for b, r in rep.items():
        print("  ", b.ljust(9), r)
    ref = ref_small(size)
    ov = edges_overlay(ref, lab, names)
    spec_edges_overlay(img, sc, (1, 1, 1))
    for band, P in probes.items():
        draw_pts(img, P, np.array([0, 0, 0]), sc, 1)
    write_png(os.path.join(OUT, f"{tag}_front.png"), np.concatenate([ref, img, ov], 1))
    if "full" in sys.argv:
        labF = W.render_labels(wd, "front", 1254)
        imgF = colour_labels(labF, names)
        spec_edges_overlay(imgF, 1.0, (1, 1, 1))
        refF = np.clip(REF[:, :, :3], 0, 1) ** 0.55
        ovF = edges_overlay(refF, labF, names)
        for rn, (x0, y0, x1, y1) in dict(bottom=(170, 780, 1100, 1110), upper=(380, 130, 1010, 600),
                                          left=(150, 250, 560, 950), right=(800, 330, 1100, 900)).items():
            write_png(os.path.join(OUT, f"{tag}_crop_{rn}.png"),
                      np.concatenate([ovF[y0:y1, x0:x1], imgF[y0:y1, x0:x1]], 1))
        np.save(os.path.join(OUT, f"{tag}_passF.npy"), labF["pass_"].astype(np.int16))
    json.dump(dict(fit=fitrep, probes=rep, cons={f"{a}<{b}": n for (a, b), n in cons.items()}),
              open(os.path.join(OUT, f"{tag}_report.json"), "w"), indent=1)
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
