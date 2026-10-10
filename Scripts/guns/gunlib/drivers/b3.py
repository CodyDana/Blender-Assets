"""Gate B3 (motion clearance: rest + extremes + sweep) and G5 static contacts on a gun's built parts (inside Blender).
Promoted from the AR-01's rifle_b3.py (gunlib 0.2.0); the AR-01 values reproduce exactly (gates/gunlib_regression.json).

    blender -b <gun>.blend --factory-startup --python <shim or drivers/run.py> -- [--quick] [--suffix _LOD1]
            [--collection <name>] [--out json]

Config ``cfg.b3``:
  groups(G, rec, cfg) -> {name: group}   the moving groups (pivots in frame B, mm); G = {part: (V, T)}, rec = part
                                         records (gun_part JSON)
  contact_pairs                          part pairs that touch at butt / fixed joints (G5 gap check), besides each
                                         part's joint parent
  rows                                   clearance rows {row: [lo, hi]} (default: the spec's joints_clearance_mm, else
                                         the line standard)
  out, out_quick                         default result paths
A group: {"parts": [...], "kind": "slide" | "rot", "axis": [x, y, z], "range": [a, b], "row": "sliding" | "hinge",
"pivot": [x, y, z] (rot)}, plus the optional keys the SMG needs (unused by the AR-01, so its path is unchanged):
  "step"           an explicit step (mm or deg) instead of the study rule
  "fine"           [[lo, hi, step], ...]: extra values at a finer step inside these windows (a latch zone)
  "coarse_proof"   true: every step outside the fine windows must prove a clearance >= r_max x step / 2 (the plan's
                   0.25 deg stock-fold alternative to the 0.023 deg step); clearance measured at every step;
                   "radius" (gunlib 0.2.1): the proof per sample, each >= its own r x step / 2 (an axle in its bore
                   keeps 0.15 at every angle and moves 0 between steps: the r_max rule can never pass there)
  "allowances"     [{"with": [fixed parts], "window": [lo, hi], "max_depth_mm": d, "why": "..."}]: declared contacts
                   (polymer snap, detents) accepted when every part hit lies in an allowance whose window holds the
                   value and the penetration depth (ray parity, 0.25 mm samples) is <= d
  "pre"            {part: 4x4 frame-B matrix}: a pre-pose applied to those parts (moving or fixed) before the sweep
                   (gunlib 0.2.1: the stock fold with the latch button pressed, the handle lock at full travel)
  "exclude"        parts left out of the fixed set for this group
  "sample_mm"      the surface sampling of the clearance measure (default 0.5; a long sweep of a large part may use
                   1.0: the clearance is a two-way nearest distance, so the sampling error stays far under the step)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .. import fit as F
from .. import gateutil as GU

DEFAULT_ROWS = {"sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "butt": [0.01, 0.05]}


def _values(d, lo, quick, rmax=None):
    """The sweep values and the clearance cadence (the AR-01 rule unless the group overrides the step)."""
    if d["kind"] == "slide":
        step = min(lo / 2.0, 1.0)
        if "step" in d:
            step = float(d["step"])
        if quick:
            step = 1.0
        vals = np.arange(d["range"][0], d["range"][1] + 1e-9, step)
        if vals[-1] < d["range"][1] - 1e-9:
            vals = np.r_[vals, d["range"][1]]
        every = max(1, int(round(1.0 / step)))
    else:
        step = min(1.0, math.degrees(lo / rmax))
        if "step" in d:
            step = float(d["step"])
        if quick:
            step = 1.0
        sgn = 1.0 if d["range"][1] >= d["range"][0] else -1.0      # a descending range (a release at -11 deg)
        vals = np.arange(d["range"][0], d["range"][1] + sgn * 1e-9, sgn * step)
        if sgn * (d["range"][1] - vals[-1]) > 1e-9:
            vals = np.r_[vals, d["range"][1]]
        every = 1 if len(vals) < 200 else 2
    if d.get("fine") and not quick:
        extra = [np.arange(a, b + 1e-9, s) for a, b, s in d["fine"]]
        vals = np.unique(np.round(np.concatenate([vals] + extra), 9))
        lo_r, hi_r = min(d["range"]), max(d["range"])
        vals = vals[(vals >= lo_r - 1e-9) & (vals <= hi_r + 1e-9)]
        if d["range"][0] > d["range"][1]:
            vals = vals[::-1]
    if d.get("coarse_proof"):
        every = 1
    return step, vals, every


def _in_fine(d, v):
    return any(min(a, b) - 1e-9 <= v <= max(a, b) + 1e-9 for a, b, _ in d.get("fine", []))


def _allowance_check(d, recs, mov, G, motion):
    """Declared contacts: steps whose every hit part lies in an allowance window, depth <= its maximum."""
    al = d.get("allowances") or []
    if not al:
        return None
    MV = np.vstack([G[n][0] for n in d["parts"]])
    MT, off = [], 0
    for n in d["parts"]:
        MT.append(G[n][1] + off)
        off += len(G[n][0])
    MT = np.vstack(MT)
    ms = F.bl.surface_samples(MV, MT, 0.25)
    trees = {}
    out = {"allowed_steps": 0, "worst_depth_mm": 0.0, "not_allowed": []}
    for r in recs:
        if not r["intersections"]:
            continue
        v = r["value"]
        ok = True
        worst = 0.0
        for part in r["hit_parts"]:
            a = next((x for x in al if part in x["with"] and min(x["window"]) - 1e-9 <= v <= max(x["window"]) + 1e-9),
                     None)
            if a is None:
                ok = False
                break
            Vf, Tf = G[part]
            if part not in trees:
                trees[part] = GU.tree(Vf, Tf)
            M = motion(v)
            Q = F.apply(M, MV)
            dep = GU.depth_inside(F.apply(M, ms), trees[part], Vf.min(0), Vf.max(0))
            fs = F.bl.surface_samples(Vf, Tf, 0.25)
            dep = max(dep, GU.depth_inside(fs, GU.tree(Q, MT), Q.min(0), Q.max(0)))
            worst = max(worst, dep)
            if dep > a["max_depth_mm"] + 1e-6:
                ok = False
        r["allowance_depth_mm"] = round(worst, 4)
        if ok:
            out["allowed_steps"] += 1
            out["worst_depth_mm"] = max(out["worst_depth_mm"], round(worst, 4))
        else:
            out["not_allowed"].append(round(v, 4))
    return out


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    C = cfg.b3
    quick = "--quick" in argv
    suffix = GU.opt(argv, "--suffix", "")
    out_path = GU.opt(argv, "--out")
    coll = GU.opt(argv, "--collection")
    rows = C.get("rows") or cfg.spec.d.get("joints_clearance_mm") or DEFAULT_ROWS
    objs = [o for o in (bpy.data.collections[coll].objects if coll else bpy.data.objects) if o.type == "MESH"
            and not o.name.startswith("_") and o.name.endswith(suffix) and not o.name.startswith(("SM_", "UCX_"))]

    def _base(n):
        return n[:len(n) - len(suffix)] if suffix else n

    G = {_base(k): v for k, v in F.geom(objs).items()}
    rec = {_base(o.name): json.loads(o["gun_part"]) for o in objs if "gun_part" in o}
    groups = C["groups"](G, rec, cfg)
    only = [v for v in (GU.opt(argv, "--only") or "").split(",") if v]      # gunlib 0.2.1: run a subset of groups
    if only:
        groups = {k: v for k, v in groups.items() if k in only}
    out = {"groups": {}, "rule": "translation step <= min(c_min/2, 1 mm); rotation step <= min(1 deg, c_min / r_max); "
                                 "0 intersections at every step; clearance (min distance to anything) >= the row's lower "
                                 "bound at rest, over the sweep and at both extremes; the guide clearance (the minimum) "
                                 "<= the row's upper bound"}
    G0 = G
    for g, d in groups.items():
        G = G0
        if d.get("pre"):                     # a pre-pose (gunlib 0.2.1): {part: 4x4 (frame B, mm)} before the sweep
            G = dict(G0)
            for n, M4 in d["pre"].items():
                if n in G:
                    G[n] = (F.apply(np.asarray(M4, float), G[n][0]), G[n][1])
        mov = {n: G[n] for n in d["parts"]}
        fixed = {n: v for n, v in G.items() if n not in d["parts"] and n not in d.get("exclude", ())}
        lo, hi = rows[d["row"]]
        rmax = None
        if d["kind"] == "slide":
            motion = (lambda ax: (lambda v: F.trans_matrix(ax, v)))(d["axis"])
        else:
            V = np.vstack([G[n][0] for n in d["parts"]])
            rmax = float(np.linalg.norm(V - d["pivot"], axis=1).max())
            motion = (lambda pv, ax: (lambda v: F.rot_matrix(pv, ax, v)))(d["pivot"], d["axis"])
        step, vals, every = _values(d, lo, quick, rmax)
        proof = None
        if d.get("coarse_proof") == "radius" and d["kind"] == "rot":       # gunlib 0.2.1: radius-aware proof
            proof = {"pivot": d["pivot"], "axis": d["axis"], "step_deg": step,
                     "skip": (lambda dd: (lambda v: _in_fine(dd, v)))(d)}
        recs, summ = F.sweep(mov, fixed, motion, vals, clearance_every=every,
                             sample_mm=float(d.get("sample_mm", 0.5)), proof=proof)
        summ["row_mm"] = [lo, hi]
        allow = _allowance_check(d, recs, mov, G, motion)
        n_int = summ["intersecting_steps"]
        if allow is not None:
            summ["allowances"] = allow
            n_int = len(allow["not_allowed"])
        summ["pass_intersections"] = n_int == 0
        if allow is not None and allow.get("allowed_steps"):
            # gunlib 0.2.1: the clearance rows hold outside the declared contact windows (a snap's contact is 0 by
            # design, and so is the clearance at its edges)
            wins = [x["window"] for x in d.get("allowances", [])]
            ok = [r["clearance_mm"] for r in recs if "clearance_mm" in r and not r["intersections"]
                  and not any(min(w) - 1e-9 <= r["value"] <= max(w) + 1e-9 for w in wins)]
            summ["min_clearance_mm_all_steps"] = summ["min_clearance_mm"]
            if ok:
                summ["min_clearance_mm"] = float(min(ok))
        summ["pass_clearance_lower"] = summ["min_clearance_mm"] >= lo - 1e-4
        summ["pass_guide_upper"] = summ["min_clearance_mm"] <= hi + 1e-4
        summ["pass"] = summ["pass_intersections"] and summ["pass_clearance_lower"] and summ["pass_guide_upper"]
        if d.get("coarse_proof") == "radius" and rmax:
            bad = [r["value"] for r in recs if r.get("proof_fails")]
            margins = [r["proof_margin"] for r in recs if r.get("proof_margin") is not None]
            summ["coarse_proof"] = {"rule": "radius-aware: every sample >= its own r x step / 2 from the other surface "
                                            "at every coarse step (r = distance from the axis)",
                                    "step_deg": step, "steps_checked": sum(1 for r in recs if "proof_fails" in r),
                                    "failing_values": bad[:20], "worst_margin_mm": min(margins) if margins else None}
            summ["pass"] = summ["pass"] and not bad
        elif d.get("coarse_proof") and rmax:
            need = rmax * math.radians(step) / 2.0
            bad = [r["value"] for r in recs if "clearance_mm" in r and not _in_fine(d, r["value"])
                   and r["clearance_mm"] < need and not r["intersections"]]
            summ["coarse_proof"] = {"needed_mm": round(need, 4), "failing_values": bad[:20]}
            summ["pass"] = summ["pass"] and not bad
        if d["kind"] == "rot":
            summ["r_max_mm"] = round(rmax, 2)
        out["groups"][g] = {"summary": summ, "worst_steps": sorted([r for r in recs if r["intersections"]],
                                                                   key=lambda r: -r["intersections"])[:8]}
        print("[B3]", g, json.dumps(summ))
    G = G0
    # static: every pair intersecting at rest (G5)
    pairs = F.pair_intersections(G)
    out["static_intersections"] = pairs
    print("[B3] static intersecting pairs:", len(pairs), pairs[:12])
    # contact gaps for every butt joint parent pair present in the records + the gun's contact pairs
    contact = []
    for n, r in rec.items():
        par = r.get("joint", {}).get("parent")
        if par and par in G:
            contact.append((n, par))
    contact += list(C.get("contact_pairs", []))
    seen = set()
    cp = []
    for a, b in contact:
        k = tuple(sorted((a, b)))
        if k not in seen:
            seen.add(k)
            cp.append(k)
    gaps = F.min_gaps(G, cp)
    out["contact_gaps"] = gaps
    print("[B3] gaps:", json.dumps(gaps))
    out["suffix"] = suffix
    dflt = C.get("out_quick" if quick else "out") or (cfg.scratch / ("b3_result_quick.json" if quick else "b3_result.json"))
    (Path(out_path) if out_path else Path(dflt)).write_text(json.dumps(out, indent=1))
    print("[B3] DONE")
    return out
