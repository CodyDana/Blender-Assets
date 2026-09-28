"""wd_score - measure a winding against REFERENCE_SPEC (numbers only) and against itself.

    cuts      a boundary between two top samples where NEITHER side is at its own tape
              edge is a cut end or a visible key switch (there must be none, any view)
    voids     disc pixels no tape covers (there must be none, any view)
    probes    points inside each spec band must show that band's pass
    edges     each spec edge's control points vs the rendered boundary of the band that
              owns the edge (px); limb ends as image angles (deg)
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
from wd_png import write_png  # noqa: E402
import wd_fitlib as FL  # noqa: E402
from props_lib import smokebomb_wind as W  # noqa: E402

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_out"


def edge_dist_px(wd, lab):
    """per pixel: SCREEN distance (px) from the point to its top sample's nearer tape edge
    (the across direction foreshortened by the view)."""
    s = lab["sample"]
    v = lab["v"]
    has = s >= 0
    d_view, _r, _u = W.view_axes(lab["view"])
    b = wd.b[s[has]]
    bp = np.linalg.norm(b - (b @ d_view)[:, None] * d_view[None, :], axis=1)
    hw = np.zeros(s.shape)
    hw[has] = 0.5 * wd.w_eff()[s[has]] * lab["R"] * np.maximum(bp, 0.05)
    d = np.full(s.shape, np.inf)
    d[has] = (1 - np.abs(v[has])) * hw[has]
    return d


def cut_map(wd, lab, tol_px=2.0, rmax=0.97):
    s = lab["sample"]
    has = s >= 0
    ed = edge_dist_px(wd, lab)
    pas = lab["pass_"]
    cut = np.zeros(s.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        a = s[: s.shape[0] - dy, : s.shape[1] - dx]
        b = s[dy:, dx:]
        ea = ed[: s.shape[0] - dy, : s.shape[1] - dx]
        eb = ed[dy:, dx:]
        both = (a >= 0) & (b >= 0)
        # different stretches: far apart along the tape (a real boundary between layers)
        far = both & (np.abs(a - b) > 3 * max(1, int(round(2.0 / (wd.ds / W.DEG)))))
        bad = far & (ea > tol_px) & (eb > tol_px)
        cut[: s.shape[0] - dy, : s.shape[1] - dx] |= bad
        cut[dy:, dx:] |= bad
    size = lab["size"]
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx + 0.5 - lab["cx"], yy + 0.5 - lab["cy"]) / lab["R"]
    return cut & (r < rmax)


def void_map(lab):
    size = lab["size"]
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx + 0.5 - lab["cx"], yy + 0.5 - lab["cy"]) / lab["R"]
    return (lab["sample"] < 0) & (r < 0.985)


def edge_errors(wd, lab_full, owners):
    """owners: edge -> pass name on top along it.  Returns edge -> list of errors (px) at
    the control points; limb end points (r > 0.985) -> angle error (deg) at the limb."""
    pas = lab_full["pass_"]
    names = wd.names
    out = {}
    size = lab_full["size"]
    for e, owner in owners.items():
        if owner not in names:
            continue
        k = names.index(owner)
        m = pas == k
        bd = np.zeros_like(m)
        bd[:-1] |= m[:-1] != m[1:]
        bd[:, :-1] |= m[:, :-1] != m[:, 1:]
        ys, xs = np.nonzero(bd & (np.hypot(np.arange(size)[None, :] - lab_full["cx"], np.arange(size)[:, None] - lab_full["cy"]) < 0.985 * lab_full["R"]))
        B = np.stack([xs + 0.5, ys + 0.5], 1)
        pts = FL.EDGES_PX[e]
        errs = []
        for p in pts:
            r = np.hypot(p[0] - W.REF_CENTRE_PX[0], p[1] - W.REF_CENTRE_PX[1]) / W.REF_RADIUS_PX
            if r > 0.985:
                # where does the owner's region meet the limb near this angle?
                ang = math.degrees(math.atan2(-(p[1] - W.REF_CENTRE_PX[1]), p[0] - W.REF_CENTRE_PX[0])) % 360
                ring = []
                for a in np.arange(ang - 25, ang + 25, 0.25):
                    x = W.REF_CENTRE_PX[0] + 0.975 * W.REF_RADIUS_PX * math.cos(math.radians(a))
                    y = W.REF_CENTRE_PX[1] - 0.975 * W.REF_RADIUS_PX * math.sin(math.radians(a))
                    ring.append((a, pas[int(y), int(x)] == k))
                ring = np.array(ring, float)
                tr = ring[1:, 0][np.diff(ring[:, 1]) != 0]
                errs.append(("limb_deg", float(np.min(np.abs(tr - ang))) if tr.size else 99.0))
            else:
                d = np.hypot(B[:, 0] - p[0], B[:, 1] - p[1]).min() if len(B) else 99.0
                errs.append(("px", float(d)))
        out[e] = errs
    return out


def score(wd, probes, show_map, owners, tag=None, views=("front", "back", "left", "right", "top", "bottom"),
          size=627, full_front=True):
    rep = {}
    names = wd.names
    cut_imgs = []
    for vw in views:
        lab = W.render_labels(wd, vw, size)
        cm = cut_map(wd, lab)
        vm = void_map(lab)
        rep[f"cuts_{vw}"] = int(cm.sum())
        rep[f"voids_{vw}"] = int(vm.sum())
        img = np.ones((size, size, 3)) * 0.996
        has = lab["pass_"] >= 0
        g = 0.35 + 0.5 * ((lab["pass_"] * 37) % 11) / 10.0
        img[has] = np.stack([g, g, g], -1)[has]
        img[cm] = [1, 0, 0]
        img[vm] = [0, 0.6, 1]
        cut_imgs.append(img)
        if vw == "front":
            ok = {}
            sc = size / W.REF_SIZE_PX
            for band, P in probes.items():
                want = show_map.get(band)
                if want is None:
                    continue
                got = [lab["pass_"][int(y * sc), int(x * sc)] for x, y in P]
                okn = sum(1 for g_ in got if g_ >= 0 and names[g_] == want)
                ok[band] = round(okn / max(1, len(P)), 3)
            rep["probes"] = ok
    if tag:
        grid = np.concatenate([np.concatenate(cut_imgs[:3], 1), np.concatenate(cut_imgs[3:], 1)], 0)
        write_png(os.path.join(OUT, f"{tag}_cuts.png"), grid)
    if full_front:
        labF = W.render_labels(wd, "front", W.REF_SIZE_PX)
        rep["edges"] = edge_errors(wd, labF, owners)
        rep["cuts_front_full"] = int(cut_map(wd, labF).sum())
    return rep
