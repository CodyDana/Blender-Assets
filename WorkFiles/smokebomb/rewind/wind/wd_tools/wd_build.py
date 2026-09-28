"""wd_build - the whole tape: fitted visible passes (ordered, directed, tucked) after an
evenly precessing core, joined by far-side connectors, ending in a tucked tail.

usage: python wd_build.py <tag> [--views] [--full] [--design <json>]
Writes wd_out/<tag>_design.json (everything smokebomb_wind_fit needs) and previews.
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
import wd_run as RR  # noqa: E402
from props_lib import smokebomb_wind as W  # noqa: E402

OUT = RR.OUT


def fit_all():
    table = TP.pass_table()
    passes = [FL.fit_pass(pf) for pf in table]
    return table, passes


def solve(passes, probes, show_map):
    order = [p.name for p in passes]
    for _ in range(3):
        truns = RR.tuck_ranges(passes, TP.TUCKS, order)
        cons = RR.solve_order(passes, probes, show_map, truns)
        order, viol, c = RR.best_order([p.name for p in passes], cons)
    truns = RR.tuck_ranges(passes, TP.TUCKS, order)
    extra = RR.auto_tucks(passes, probes, show_map, order, truns, margin=14.0)
    return order, list(truns) + extra, viol


def connector_cost(pa: W.PassSpec, pb: W.PassSpec):
    P, h, info = W._connector_pts(pa.point(pa.phi_b)[0], pa.tangent(pa.phi_b)[0], pb.point(pb.phi_a)[0], pb.tangent(pb.phi_a)[0])
    Wd = (1 - h) * pa.width_rad(pa.phi_b)[0] + h * pb.width_rad(pb.phi_a)[0]
    C = np.vstack([pa.point(pa.phi_b), P, pb.point(pb.phi_a)])
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    Tg = np.gradient(C, s, axis=0)
    Tg = W.normalize(Tg - np.einsum("ij,ij->i", Tg, C)[:, None] * C)
    dT = np.gradient(Tg, s, axis=0)
    kg = np.einsum("ij,ij->i", dT, np.cross(C, Tg))
    hw = 0.5 * np.concatenate([[pa.width_rad(pa.phi_b)[0]], Wd, [pb.width_rad(pb.phi_a)[0]]])
    strain = float(np.max(np.abs(kg[2:-2]) * hw[2:-2])) if len(kg) > 4 else 0.0
    front = float(np.max(C[4:-4, 2])) if len(C) > 8 else -1.0
    return info["cost"], strain, front, info


def choose_directions(seq):
    """DP over the passes in winding order: flip each or not to minimise connector cost."""
    n = len(seq)
    opts = [(p, p.reversed()) for p in seq]
    best = [[0.0, 0.0]]
    back = []
    for k in range(1, n):
        row, brow = [], []
        for b in (0, 1):
            cands = []
            for a in (0, 1):
                c, st, fr, _ = connector_cost(opts[k - 1][a], opts[k][b])
                cands.append(best[-1][a] + c + 30.0 * max(st - 0.04, 0.0) + 50.0 * max(fr, 0.0))
            a = int(np.argmin(cands))
            row.append(cands[a])
            brow.append(a)
        best.append(row)
        back.append(brow)
    flips = [0] * n
    flips[-1] = int(np.argmin(best[-1]))
    for k in range(n - 1, 0, -1):
        flips[k - 1] = back[k - 1][flips[k]]
    return [opts[k][flips[k]] for k in range(n)], flips


def tucks_for(seq, flips, truns, passes_by_idx):
    """tuck runs (pass idx in the fitted list, phi range, under names) -> one W.Weave per
    (lower stretch, upper pass), on the (possibly reversed) passes; overlapping ranges of the
    same pair merged."""
    names = [p.name for p in seq]
    pairs = {}
    for (i, a, b, under) in truns:
        nm = passes_by_idx[i].name
        k = names.index(nm)
        if flips[k]:
            a, b = -b, -a
        for u in under:
            pairs.setdefault((nm, u), []).append((float(a), float(b)))
    res = []
    fan = {}
    for (nm, u), rs in list(pairs.items()):
        if nm in ("R2", "R3", "Rin") and u in FAN:
            fan.setdefault(nm, []).extend(rs)
            del pairs[(nm, u)]
    for nm, rs in fan.items():
        a = min(r[0] for r in rs)
        b = max(r[1] for r in rs)
        res.append(W.Weave(nm, (a, b), tuple(sorted(FAN | FAN_EXTRA)), None, upper_where=FAN_WHERE, stop_hidden=False,
                           why="the pinwheel: the R strips dive under the U fan at the whorl, as one group"))
    for (nm, u), rs in pairs.items():
        rs.sort()
        cur = list(rs[0])
        for a, b in rs[1:]:
            if a <= cur[1] + 2:
                cur[1] = max(cur[1], b)
            else:
                res.append(_mk_weave(nm, tuple(cur), u))
                cur = [a, b]
        res.append(_mk_weave(nm, tuple(cur), u))
    return res


FAN = {"U1", "U2", "U3", "U4", "U5"}
FAN_WHERE = "front" if "--fan-front" in sys.argv else ("front+45" if "--fan-45" in sys.argv else "all")
FAN_EXTRA = {"Da"} if "--fan-da" in sys.argv else set()


def _mk_weave(lower, rng, upper):
    """the R family under the U fan: the whole U pass (its far-side stretch too), because the
    R strips leave the front under the fan and run on beneath it."""
    if lower in ("R2", "R3", "Rin") and upper in FAN:
        return W.Weave(lower, rng, upper, None, upper_where="all", why="the pinwheel: under the U fan at the whorl")
    return W.Weave(lower, rng, upper, why="woven crossing")


def core_start_covered(CP, CW, k, nf=256):
    """is the cap at core sample k hidden under the core laid at least one loop later?"""
    cell = (math.pi / 2) / nf
    per = 1800
    later = np.zeros(6 * nf * nf, bool)
    Pl = CP[k + per:]
    # the later core's footprint, coarsely (centre +- half width)
    tl = W.normalize(np.gradient(Pl, axis=0))
    bl = W.normalize(np.cross(Pl, tl))
    for vv in np.linspace(-0.95, 0.95, 41):
        a = 0.5 * CW[k + per:] * vv
        later[W._cube_index(W.normalize(np.cos(a)[:, None] * Pl + np.sin(a)[:, None] * bl), nf)] = True
    t0 = W.normalize(CP[k + 1] - CP[k])
    b0 = W.normalize(np.cross(CP[k], t0))
    cap = [W.normalize(np.cos(0.5 * CW[k] * vv) * CP[k] + np.sin(0.5 * CW[k] * vv) * b0) for vv in np.linspace(-1, 1, 11)]
    return bool(later[W._cube_index(np.array(cap), nf)].all())


CORE = dict(n=24, width=0.20, first_axis=(0.2, 0.9, 0.3))


def split_weaves(wd0, weaves, nf=512):
    """one weave per CROSSING: the lower stretch's samples whose section meets the upper
    pass's footprint, split into connected runs (a gap of > 3 deg splits)."""
    out = []
    v = np.linspace(-1.0, 1.0, 11)
    fps = {}
    for w in weaves:
        if not isinstance(w.upper, str):
            out.append(w)
            continue
        idx = wd0.samples_of(w.lower, w.lower_range, w.lower_where)
        if idx.size == 0:
            continue
        fk = (w.upper, w.upper_where)
        if fk not in fps:
            up = wd0.passes[wd0.names.index(w.upper)]
            if w.upper_where == "all":
                fps[fk] = W.footprint_mask(wd0, wd0.samples_of(w.upper), nf)
            else:
                fps[fk] = W.footprint_mask(wd0, wd0.samples_of(w.upper, (up.phi_a, up.phi_b), "front"), nf)
        fp = fps[fk]
        hit = np.array([fp[W._cube_index(wd0.points(v, idx=[q])[0], nf)].any() for q in idx])
        if not hit.any():
            continue
        hs = idx[hit]
        cuts = np.nonzero(np.diff(hs) > int(3.0 / 0.2))[0]
        starts = np.concatenate([[0], cuts + 1])
        ends = np.concatenate([cuts, [len(hs) - 1]])
        for a, b in zip(starts, ends):
            ia, ib = hs[a], hs[b]
            if w.lower_where == "tail":
                rng = (float(wd0.tail[ia]), float(wd0.tail[ib]))
            else:
                rng = (float(wd0.phi[ia]), float(wd0.phi[ib]))
            out.append(W.Weave(w.lower, rng, w.upper, w.upper_range, w.lower_where, w.upper_where, w.why,
                               w.extend, w.stop_hidden))
    return out


TAIL_FOLD = 0.9


def build_winding(seq, weaves, tail_deg=70.0):
    first = np.array(seq[0].n)
    ax = W.core_axes(CORE["n"], W.normalize(CORE["first_axis"]), first)
    CP, CW = W.core_path(ax, CORE["width"])
    k = W.core_start_trim(CP, CW)
    # end the core where its last loop meets the first pass most gently
    p0 = seq[0]
    B0, tB = p0.point(p0.phi_a)[0], p0.tangent(p0.phi_a)[0]
    best = None
    for ke in range(len(CP) - 1800, len(CP), 30):
        A0, tA = CP[ke], W.normalize(CP[ke] - CP[ke - 1])
        P, h, info = W._connector_pts(A0, tA, B0, tB, wall=False)
        C = np.vstack([A0, P, B0])
        d = np.diff(C, axis=0)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        turn = float(np.max(np.arccos(np.clip(np.einsum("ij,ij->i", d[1:], d[:-1]), -1, 1))))
        score = (info["cost"] if info["cost"] is not None else 1e9) + 50.0 * turn
        if best is None or score < best[0]:
            best = (score, ke)
    ke = best[1]
    CP, CW = CP[:ke + 1], CW[:ke + 1]
    wd0 = W.assemble(list(seq), [], tail_deg=tail_deg, core=(CP[k:], CW[k:]), tail_fold=TAIL_FOLD)
    ws = split_weaves(wd0, weaves)
    conns = [dict(La=c["La"], Lb=c["Lb"]) for c in wd0.notes["connectors"]]
    wd = W.assemble(list(seq), ws, tail_deg=tail_deg, core=(CP[k:], CW[k:]), connectors=conns, tail_fold=TAIL_FOLD)
    wd.notes["core_trim"] = k
    wd.notes["core_end"] = int(ke)
    wd.notes["core_axes"] = ax.tolist()
    wd.notes["frozen_connectors"] = conns
    wd.notes["tail_deg"] = float(tail_deg)
    return wd


def end_tuck(wd, min_tail=30.0, late=40):
    """the free end: along the far-side tail, the first point (>= min_tail deg) where the
    folded cap lies wholly inside the footprint of one of the ``late`` passes laid just
    before the last (the later the better: fewer stretches lie between them, so the
    crossing is clean), with the tail clear of that pass somewhere before it (where the
    weave starts).  Returns (tail length deg, pass name, (cover, weave start deg))."""
    k_last = len(wd.passes) - 1
    tail = np.nonzero((wd.pass_idx == k_last) & ~np.isnan(wd.tail))[0]
    zc = wd.c[tail, 2] + np.sin(0.5 * wd.w_eff()[tail])
    behind = np.nonzero(zc < -0.02)[0]
    if behind.size:
        front = np.nonzero(zc > -0.02)[0]
        front = front[front > behind[0]]
        if front.size:
            tail = tail[:front[0]]
    tl = wd.tail[tail]
    cand = tail[(tl >= min_tail)][::3]
    wsave, gsave = wd.w.copy(), wd.gather.copy()
    wd.gather[cand] = 0.75          # a margin: the real fold (TAIL_FOLD) is narrower
    cover = W.end_cap_cover(wd, cand)
    wd.w[:], wd.gather[:] = wsave, gsave
    names = wd.names
    lates = list(range(k_last - 1, max(0, k_last - 1 - late), -1))
    vv = np.linspace(-1, 1, 9)
    v11 = np.linspace(-1.05, 1.05, 13)          # a margin beyond the edges
    fold_deg = 30.0
    for j in lates:
        m = W.footprint_mask(wd, np.nonzero(wd.pass_idx == j)[0], 256)
        m512 = W.footprint_mask(wd, np.nonzero(wd.pass_idx == j)[0], 512, dilate=False)
        for i in cover:
            if j not in cover[i]:
                continue
            # the whole folded stretch (the last fold_deg before this end) must lie under j
            L_i = float(wd.tail[i])
            ok = True
            for q2 in range(i, max(tail[0], i - int(12.0 / 0.2)), -5):      # the folded tip (last 12 deg)
                g = TAIL_FOLD * float(W.smootherstep((wd.tail[q2] - (L_i - fold_deg)) / fold_deg))
                hw = 0.5 * (wd.w[q2] * (1 - g) + W.CORD_W * g)
                a = hw * v11
                P = W.normalize(np.cos(a)[:, None] * wd.c[q2] + np.sin(a)[:, None] * wd.b[q2])
                if not m512[W._cube_index(P, 512)].all():
                    ok = False
                    break
            if not ok:
                continue
            q = i
            while q > tail[0] and m[W._cube_index(wd.points(vv, idx=[q])[0], 256)].any():
                q -= 1
            if q > tail[0] + 10:
                return float(wd.tail[i]), names[j], (cover, float(wd.tail[q]))
    return None, None, (cover, None)


FIT_PATH = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/smokebomb_wind_fit.py"


def _t(v, nd=9):
    return "(" + ", ".join(repr(round(float(x), nd)) for x in v) + ("," if len(v) == 1 else "") + ")"


def write_fit_module(wd, tag):
    """freeze the design: every number reference_winding() needs, as a plain module."""
    L = []
    L.append('"""props_lib.smokebomb_wind_fit - the FROZEN winding of SM_SmokeBomb (generated, do not edit).')
    L.append("")
    L.append("Written by WorkFiles/smokebomb/rewind/wind/wd_tools/wd_build.py (design %s) from the fit of" % tag)
    L.append("every visible pass to REFERENCE_SPEC's traced edges (the spec numbers only; the reference")
    L.append("pixels are never read).  props_lib.smokebomb_wind.reference_winding() assembles the tape")
    L.append("from these numbers alone.")
    L.append("")
    L.append("Camera frame (REFERENCE_SPEC 0): X right, Y up, Z toward the camera; unit sphere.")
    L.append("PassSpec angles in degrees, widths in frac D; weave ranges in the pass's own phi (deg) or,")
    L.append('with lower_where="tail", in degrees of arc past the end of the last front arc.')
    L.append('"""')
    L.append("")
    L.append("DESIGN = %r" % tag)
    L.append("#: the core: a continuous precessing winding round these loop axes (core_path), trimmed")
    L.append("CORE_WIDTH = %r" % float(CORE["width"]))
    L.append("CORE_AXES = (")
    for a in wd.notes["core_axes"]:
        L.append("    %s," % _t(a))
    L.append(")")
    L.append("CORE_TRIM = %d          # first core sample kept (the inner end, buried)" % wd.notes["core_trim"])
    L.append("CORE_END = %d          # last core sample kept (where it joins the first pass)" % wd.notes["core_end"])
    L.append("#: the fitted passes, in the order they are wound (later = on top)")
    L.append("PASSES = (")
    for p in wd.passes[1:]:
        L.append("    dict(name=%r, shows=%r, role=%r," % (p.name, tuple(p.shows), p.role))
        L.append("         n=%s, e1=%s," % (_t(p.n), _t(p.e1)))
        L.append("         phi_a=%r, phi_b=%r," % (float(p.phi_a), float(p.phi_b)))
        L.append("         beta=%s," % _t(p.beta, 6))
        L.append("         width=%s," % _t(p.width, 6))
        L.append("         gather=%s," % (_t(p.gather, 6) if p.gather else "()"))
        L.append("         note=%r)," % p.note)
    L.append(")")
    L.append("#: the far-side joins (core -> first pass, then pass k -> k+1): run-on lengths, deg")
    L.append("CONNECTORS = (")
    for c in wd.notes["frozen_connectors"]:
        L.append("    (%r, %r)," % (float(c["La"]), float(c["Lb"])))
    L.append(")")
    L.append("#: the free end: the last pass runs on this far past its front arc, folded (gathered)")
    L.append("TAIL_DEG = %r" % wd.notes["tail_deg"])
    L.append("TAIL_FOLD = %r" % TAIL_FOLD)
    L.append("#: the weaves (crossing-local layering)")
    L.append("WEAVES = (")
    for w in wd.weaves:
        up = w.upper if isinstance(w.upper, str) else tuple(w.upper)
        L.append("    dict(lower=%r, lower_range=%s, upper=%r, upper_range=%s," % (
            w.lower, _t(w.lower_range, 4), up, "None" if w.upper_range is None else _t(w.upper_range, 4)))
        L.append("         lower_where=%r, upper_where=%r, extend=%r, stop_hidden=%r," % (
            w.lower_where, w.upper_where, w.extend, w.stop_hidden))
        L.append("         why=%r)," % w.why)
    L.append(")")
    open(FIT_PATH, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", FIT_PATH)


def views(wd, tag, names, size=627):
    imgs = []
    for v in ("front", "back", "left", "right", "top", "bottom"):
        lab = W.render_labels(wd, v, size)
        img = RR.colour_labels(lab, names)
        imgs.append(img)
        np.save(os.path.join(OUT, f"{tag}_{v}_pass.npy"), lab["pass_"].astype(np.int16))
    grid = np.concatenate([np.concatenate(imgs[:3], 1), np.concatenate(imgs[3:], 1)], 0)
    write_png(os.path.join(OUT, f"{tag}_views.png"), grid)
    return imgs


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "b0"
    t0 = time.time()
    table, passes = fit_all()
    probes = TP.band_probes()
    show_map = {b: p.name for p in passes for b in p.shows}
    order, truns, viol = solve(passes, probes, show_map)
    print("order:", " ".join(order))
    byname = {p.name: p for p in passes}
    seq = [byname[n] for n in order]
    seq, flips = choose_directions(seq)
    print("flips:", dict(zip(order, flips)))
    idx_of = {p.name: i for i, p in enumerate(passes)}
    tucks = tucks_for(seq, flips, truns, passes)
    print("weaves:", [(t.lower, round(t.lower_range[0]), round(t.lower_range[1]), t.upper) for t in tucks])
    wd = build_winding(seq, tucks, tail_deg=240.0)
    L, jn, _cov = end_tuck(wd)
    print("tape: samples", wd.s.size, "length (unit radii)", round(float(wd.s[-1]), 2), "end tail", L, "under", jn)
    if L is not None:
        t_from = _cov[1]
        tucks = tucks + [W.Weave(wd.names[-1], (t_from, L + 1.0), jn, None, lower_where="tail", upper_where="all",
                                 stop_hidden=False,
                                 why="the free end: folded and pushed under %s on the far side" % jn)]
        wd = build_winding(seq, tucks, tail_deg=L)
    else:
        wd = build_winding(seq, tucks, tail_deg=60.0)
    names = wd.names
    # connector report
    for c in wd.notes["connectors"]:
        pass
    st = wd.edge_strain()
    conn = np.isnan(wd.phi) & (wd.pass_idx > 0)
    arc = ~np.isnan(wd.phi)
    corem = wd.pass_idx == 0
    print("strain: front arcs max %.1f%% p95 %.1f%% | connectors max %.1f%% p95 %.1f%% | core max %.1f%% p95 %.1f%%" % (
        100 * st[arc].max(), 100 * np.percentile(st[arc], 95), 100 * st[conn].max(), 100 * np.percentile(st[conn], 95),
        100 * st[corem].max(), 100 * np.percentile(st[corem], 95)))
    cv = W.coverage(wd, 128)
    print("coverage: min %d mean %.2f voids %d" % (cv["min"], cv["mean"], cv["void_cells"]))
    print("ends:", W.end_hidden(wd, "start"), W.end_hidden(wd, "end"))
    lab = W.render_labels(wd, "front", 627)
    rep = RR.probe_report(lab, wd.passes, probes, show_map, 627 / W.REF_SIZE_PX)
    bad = {b: r for b, r in rep.items() if r["frac"] < 1.0}
    print("probe misses:", bad)
    img = RR.colour_labels(lab, names)
    RR.spec_edges_overlay(img, 627 / W.REF_SIZE_PX, (1, 1, 1))
    ref = RR.ref_small(627)
    ov = RR.edges_overlay(ref, lab, names)
    write_png(os.path.join(OUT, f"{tag}_front.png"), np.concatenate([ref, img, ov], 1))
    if "--views" in sys.argv:
        views(wd, tag, names)
    if "--score" in sys.argv:
        import wd_score as SC
        rep = SC.score(wd, probes, show_map, TP.OWNERS, tag=tag)
        worst = {e: max(v for k_, v in errs) for e, errs in rep["edges"].items()}
        print("cuts:", {k: v for k, v in rep.items() if k.startswith("cuts")})
        print("voids:", {k: v for k, v in rep.items() if k.startswith("voids")})
        print("edge worst (px or limb deg):", {e: round(v, 1) for e, v in worst.items()})
        json.dump(rep, open(os.path.join(OUT, f"{tag}_score.json"), "w"), indent=1, default=float)
    import pickle
    pickle.dump(wd, open(os.path.join(OUT, f"{tag}_wd.pkl"), "wb"))
    # the design record
    rec = dict(order=[p.name for p in wd.passes], flips=dict(zip(order, flips)), core=CORE,
               core_trim=wd.notes.get("core_trim"), tail_deg=float(np.nanmax(wd.tail[wd.pass_idx == len(wd.passes) - 1])),
               weaves=[dict(lower=t.lower, lower_range=list(t.lower_range), upper=t.upper,
                            upper_range=None if t.upper_range is None else list(t.upper_range),
                            lower_where=t.lower_where, upper_where=t.upper_where, why=t.why) for t in wd.weaves],
               passes=[dict(name=p.name, shows=list(p.shows), n=list(p.n), e1=list(p.e1), phi_a=p.phi_a,
                            phi_b=p.phi_b, beta=list(p.beta), width=list(p.width), gather=list(p.gather),
                            role=p.role, note=p.note) for p in wd.passes],
               connectors=wd.notes["connectors"])
    json.dump(rec, open(os.path.join(OUT, f"{tag}_design.json"), "w"), indent=1, default=float)
    if "--freeze" in sys.argv:
        write_fit_module(wd, tag)
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
