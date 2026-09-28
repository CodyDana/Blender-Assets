"""wd_final - score and preview the FROZEN winding (props_lib.smokebomb_wind.reference_winding).

Everything here measures the module's output against REFERENCE_SPEC numbers (the JSON twin);
the reference image is used only as the left panel of the side-by-side previews.
Writes WorkFiles/smokebomb/rewind/wind/wd_final/ (PNGs) and wd_final_score.json.
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
import wd_score as SC  # noqa: E402
from props_lib import smokebomb_wind as W  # noqa: E402

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind"
OUTD = os.path.join(ROOT, "wd_final")
os.makedirs(OUTD, exist_ok=True)

#: REFERENCE_SPEC 4.4 rows: (row, text, edge, x-range or None, top pass(es), under pass(es))
ROWS = [
    ("1", "W > A", "WLO", None, ("W",), ("A",)),
    ("2", "W > X", "WUP", (705, 1048), ("W",), ("X",)),
    ("3", "W > B (B's tip ends at W)", "WUP", (612, 700), ("W",), ("B",)),
    ("4", "W > U0", "WTW", (470, 540), ("W",), ("U0",)),
    ("5", "R_in > W (W's twisted end comes out of R_in's crevice)", "LIN", (330, 400), ("Rin",), ("W", "A", "U0")),
    ("6", "R_in > A", "LIN", (280, 330), ("Rin",), ("A", "L3", "L4")),
    ("7", "R_in > U0", "LIN", (400, 505), ("Rin",), ("U0",)),
    ("8", "B > X", "BLO", None, ("B",), ("X",)),
    ("9", "B > U1..U5", "BUP", (640, 1060), ("B",), ("U1", "U2", "U3", "U4", "U5")),
    ("10", "A > C", "ALO", (365, 625), ("A",), ("C",)),
    ("11", "A > L3", "ALO", (282, 340), ("A",), ("L3",)),
    ("12", "A > D family, E", "ALO", (640, 1028), ("A",), ("Da", "Db", "Dc", "E", "L4", "L3")),
    ("13", "C > L3, L4, L5", "CUP", None, ("C",), ("L3", "L4", "Rin")),
    ("14", "C > D family", "CLO", None, ("C",), ("Da", "Db", "Dc", "L3", "L4")),
    ("15", "L4 > L3 (spec: LOW confidence, shading rule only) - built the other way: L3 > L4", "L3L", None, ("L3",), ("L4",)),
]


def side_points(edge, xr, off=7.0, step=10.0):
    P = FL.edge_px(edge, xr=xr, step=step)
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    return P, P + off * N, P - off * N


def crossing_checks(wd, lab):
    names = wd.names
    pas = lab["pass_"]
    out = []
    for row, text, edge, xr, tops, unders in ROWS:
        P, Pa, Pb = side_points(edge, xr)
        ok = 0
        tot = 0
        for a, b in zip(Pa, Pb):
            ia, ib = pas[int(a[1]), int(a[0])], pas[int(b[1]), int(b[0])]
            na = names[ia] if ia >= 0 else "bg"
            nb = names[ib] if ib >= 0 else "bg"
            tot += 1
            if (na in tops and nb in unders) or (nb in tops and na in unders):
                ok += 1
        out.append(dict(row=row, crossing=text, edge=edge, samples=tot, holds=ok, frac=round(ok / max(tot, 1), 3)))
    return out


def vgap_checks(wd, lab):
    names = wd.names
    pas = lab["pass_"]
    key = lab["key"]
    # whorl V-gap: the wedge must show a LOWER layer than the strips around it
    res = {}
    top_bands = {"R2", "R3", "Rin", "U0", "U1", "U2"}
    got = [names[pas[int(y), int(x)]] if pas[int(y), int(x)] >= 0 else "bg" for x, y in TP.VGAP]
    res["whorl_vgap"] = dict(points=len(got), deep=sum(1 for g in got if g not in top_bands), shows=sorted(set(got)))
    # U0/U1 V-gap: between U0's right edge and UA, 0 px at W's twist opening to 30 px at (585,390)
    ua = FL.edge_px("UA", yr=(330, 470))
    mid = TP.shift_toward(ua, (450, 300), 1.0)
    gap = np.interp(ua[:, 1], [262, 330, 390, 486], [4, 22, 30, 0])
    Pm = ua + (mid - ua) * (0.5 * gap)[:, None]
    got = [names[pas[int(y), int(x)]] if pas[int(y), int(x)] >= 0 else "bg" for x, y in Pm]
    res["u0_u1_vgap"] = dict(points=len(got), deep=sum(1 for g in got if g not in ("U0", "U1")), shows=sorted(set(got)))
    return res


def woven_cycle(wd, lab):
    """R_in > A (row 6), A > C (row 10), C > R_in's own lower end L5 (at (258,712))."""
    names = wd.names
    pas = lab["pass_"]
    # C over L5: points just below CUP near (240-270, 715-735) show C; just above show R_in or L4
    P, Pa, Pb = side_points("CUP", (215, 285))
    got_a = [names[pas[int(y), int(x)]] for x, y in Pa]
    got_b = [names[pas[int(y), int(x)]] for x, y in Pb]
    return dict(C_over_L5_sides=[sorted(set(got_a)), sorted(set(got_b))])


def outline_estimate(wd, cap=None):
    """layers under the surface along the limb (z = 0 ring, 720 samples): the radius steps a
    lift of STEP_R per layer would make at the silhouette."""
    ang = np.radians(np.arange(0, 360, 0.5))
    ring = np.stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)], 1)
    g = wd.stack_grid(256)
    ci = W._cube_index(ring, 256)
    cnt = g.count[ci].astype(float)
    if cap is not None:
        cnt = np.minimum(cnt, cap)
    r_px = W.REF_RADIUS_PX * W.STEP_R * (cnt - cnt.mean())
    steps = np.abs(np.diff(np.concatenate([r_px, r_px[:1]])))
    big = steps >= 4.0
    return dict(layers_min=int(cnt.min()), layers_max=int(cnt.max()), layers_mean=round(float(cnt.mean()), 2),
                radius_rms_px=round(float(np.sqrt((r_px ** 2).mean())), 2), steps_ge_4px=int(big.sum()),
                step_median_px=round(float(np.median(steps[big])), 2) if big.any() else 0.0,
                step_max_px=round(float(steps.max()), 2), cap=cap)


def main():
    t0 = time.time()
    wd = W.reference_winding()
    names = wd.names
    probes = TP.band_probes()
    show_map = {b: p.name for p in wd.passes for b in p.shows}
    rep = SC.score(wd, probes, show_map, TP.OWNERS, tag=None)
    labF = W.render_labels(wd, "front", W.REF_SIZE_PX)
    rep["crossings_4_4"] = crossing_checks(wd, labF)
    rep["vgaps"] = vgap_checks(wd, labF)
    rep["woven_cycle"] = woven_cycle(wd, labF)
    rep["ends"] = [W.end_hidden(wd, "start"), W.end_hidden(wd, "end")]
    cv = W.coverage(wd, 128)
    rep["coverage"] = {k: cv[k] for k in ("min", "mean", "p05", "max", "void_cells")}
    rep["outline_all_layers"] = outline_estimate(wd)
    rep["outline_top3_layers"] = outline_estimate(wd, cap=None)
    st = wd.edge_strain()
    per = {}
    for k, nm in enumerate(names):
        m = wd.pass_idx == k
        arc = m & ~np.isnan(wd.phi)
        con = m & np.isnan(wd.phi)
        vis = arc & (wd.c[:, 2] > 0)
        per[nm] = dict(samples=int(m.sum()),
                       front_strain_p95=round(100 * float(np.percentile(st[vis], 95)), 1) if vis.any() else None,
                       front_strain_max=round(100 * float(st[vis].max()), 1) if vis.any() else None,
                       connector_strain_p95=round(100 * float(np.percentile(st[con], 95)), 1) if con.any() else None,
                       width_fracD_front=[round(float(wd.w[vis].min() / 2), 3), round(float(wd.w[vis].max() / 2), 3)] if vis.any() else None,
                       gather_max=round(float(wd.gather[m].max()), 2))
    rep["per_pass"] = per
    rep["tape"] = dict(samples=int(wd.s.size), length_unit_radii=round(float(wd.s[-1]), 2),
                       length_m_at_70mm=round(float(wd.s[-1]) * 0.035, 2), passes=len(names) - 1,
                       weaves=[dict(lower=w.lower, upper=w.upper if isinstance(w.upper, str) else list(w.upper),
                                    why=w.why) for w in wd.weaves],
                       order=names)
    # edges summary against the spec tolerances (primary W, A, B, C edges 6 px; others 10 px; limb 6 deg)
    prim = {"WUP", "WLO", "WTW", "ALO", "BUP", "BLO", "CUP", "CLO"}
    summ = {}
    for e, errs in rep["edges"].items():
        tol = 6.0 if e in prim else 10.0
        px = [v for k_, v in errs if k_ == "px"]
        lb = [v for k_, v in errs if k_ == "limb_deg"]
        summ[e] = dict(max_px=round(max(px), 1) if px else None, within=sum(1 for v in px if v <= tol), of=len(px),
                       limb_deg=[round(v, 1) for v in lb], limb_within=sum(1 for v in lb if v <= 6.0), tol_px=tol)
    rep["edges_summary"] = summ
    json.dump(rep, open(os.path.join(ROOT, "wd_final_score.json"), "w"), indent=1, default=float)
    # ---------------------------------------------------------------- previews
    ref = RR.ref_small(627)
    lab = W.render_labels(wd, "front", 627)
    img = RR.colour_labels(lab, names)
    RR.spec_edges_overlay(img, 627 / W.REF_SIZE_PX, (1, 1, 1))
    ov = RR.edges_overlay(ref, lab, names)
    write_png(os.path.join(OUTD, "wd_front_vs_reference.png"), np.concatenate([ref, img, ov], 1))
    imgF = RR.colour_labels(labF, names)
    RR.spec_edges_overlay(imgF, 1.0, (1, 1, 1))
    write_png(os.path.join(OUTD, "wd_front_1254.png"), imgF)
    refF = np.clip(RR.REF[:, :, :3], 0, 1) ** 0.55
    ovF = RR.edges_overlay(refF, labF, names)
    for rn, (x0, y0, x1, y1) in dict(whorl=(540, 130, 1000, 520), left=(150, 250, 600, 950), bottom=(170, 780, 1100, 1110),
                                      right=(780, 330, 1100, 900), belt=(330, 380, 1100, 900)).items():
        write_png(os.path.join(OUTD, f"wd_crop_{rn}.png"), np.concatenate([ovF[y0:y1, x0:x1], imgF[y0:y1, x0:x1]], 1))
    views = []
    cuts = []
    for v in ("front", "back", "left", "right", "top", "bottom"):
        lb = W.render_labels(wd, v, 627)
        im = RR.colour_labels(lb, names)
        views.append(im)
        cm = SC.cut_map(wd, lb)
        vm = SC.void_map(lb)
        ci = im * 0.55 + 0.45
        ci[cm] = [1, 0, 0]
        ci[vm] = [0, 0.5, 1]
        cuts.append(ci)
    grid = np.concatenate([np.concatenate(views[:3], 1), np.concatenate(views[3:], 1)], 0)
    write_png(os.path.join(OUTD, "wd_six_views.png"), grid)
    grid = np.concatenate([np.concatenate(cuts[:3], 1), np.concatenate(cuts[3:], 1)], 0)
    write_png(os.path.join(OUTD, "wd_six_views_cuts_voids.png"), grid)
    # the far side and the poles, bigger
    for v in ("back", "top", "bottom"):
        lb = W.render_labels(wd, v, 900)
        write_png(os.path.join(OUTD, f"wd_{v}_900.png"), RR.colour_labels(lb, names))
    # layer depth map from the reference camera (how many stretches lie under the top one)
    g = wd.stack_grid(256)
    s_ = labF["sample"]
    has = s_ >= 0
    yy, xx = np.nonzero(has)
    P = W.img_to_cam(xx + 0.5, yy + 0.5)
    depth = np.zeros(s_.shape)
    depth[has] = wd.layers_below(P, s_[has], g) + 1
    dimg = np.ones(s_.shape + (3,))
    dn = np.clip(depth / max(1.0, depth.max()), 0, 1)
    dimg[has] = np.stack([dn, dn, dn], -1)[has]
    write_png(os.path.join(OUTD, "wd_front_layers.png"), dimg)
    rep["front_layers"] = dict(min=int(depth[has].min()), max=int(depth[has].max()), mean=round(float(depth[has].mean()), 2))
    json.dump(rep, open(os.path.join(ROOT, "wd_final_score.json"), "w"), indent=1, default=float)
    print(json.dumps(dict(probes=rep["probes"], cuts={k: v for k, v in rep.items() if k.startswith("cuts")},
                          voids={k: v for k, v in rep.items() if k.startswith("voids")}, ends=rep["ends"],
                          coverage=rep["coverage"], crossings=[(r["row"], r["frac"]) for r in rep["crossings_4_4"]],
                          vgaps=rep["vgaps"], woven=rep["woven_cycle"], outline=rep["outline_all_layers"],
                          layers=rep["front_layers"]), indent=0, default=float)[:6000])
    print("done %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
