"""Pilot 2 rock FORM stage (method change). Headless Blender:

    blender -b --factory-startup --python Scripts/dojo/rocks/rocks_form2.py -- [RiverRound RiverLong CliffChunk]

RIVER (corestone): lumpy superellipsoid lobe(s) (equator ~0.23 H above grade, the flank tucking under) -> fused
(closing) -> 4-6 old joint planes + 24-34 shallow soft facets -> clamped by the traced visual hull grown by a few cm
(the hull is only a clamp now) -> water rounding: an opening at r = 16 % of the short axis -> stage 2 at 5 mm: cracks
(the RiverLong join crack), lip opening -> Grid to Mesh -> lumpy meso noise + the scanned relief (rock_surface).

CLIFF (fracture): the traced visual hull -> Voronoi cells of a sheared anisotropic lattice with tilted shared faces
-> each block = hull eroded by its own recess (0-0.40 m) cut to its shrunk cell and 1-2 tilted fracture facets ->
union with a core (joints become deep slots) + rubble at the foot -> opening r 1.2 cm (sharp arrises) -> stage 2 at
6 mm: arris chips, spall flakes, lip opening -> mesh -> fine noise + the scanned relief (tiger_rock).

Both rescale the above-grade extents to the sheet's measured L / D / H and write work2/<Rock>_dense.npz + _form.json.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT / "Scripts" / "stone", ROOT / "Scripts" / "dojo" / "rocks", ROOT / "Scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import bpy  # noqa: E402

import stone_sdf as sd  # noqa: E402
import rock_forms as rf  # noqa: E402
import rock_corestone as rc  # noqa: E402
import rock_fracture as fr  # noqa: E402
import stone_weather2 as sw2  # noqa: E402
import rocks_form as f1  # noqa: E402   (pilot 1 helpers: masks, outlines, hull points)
from rocks_plans2 import PLANS  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work2"


def log(*a):
    print("[form2]", *a, flush=True)


# ----------------------------------------------------------------------------------------------- river
def river_stage1(plan, front, side, top, rng):
    r = plan["r_open"]
    clamp = plan["clamp"]
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil((r + 0.1) / plan["voxel1"])) + 6, name="__P2_S1")
    lobes = []
    pts = []
    for k, spec in enumerate(plan["lobes"]):
        V, F = rc.corestone_lobe(spec, rng)
        lobes.append(g.mesh(V, F, f"__lobe{k}"))
        pts.append(rc.hull_points(V, F, 30000, rng))
    solid = g.union(lobes)
    if len(lobes) > 1:
        solid = g.closing(solid, plan.get("fuse_r", 0.08))
    P = np.vstack(pts)
    P = P[P[:, 2] > -0.02]
    cuts = rc.joint_cuts(P, plan["joints"])
    fac = rc.facet_cuts(P, rng, plan["facets"]["count"], depth=plan["facets"]["depth"])
    parts = sd.batch_disjoint(cuts + fac)
    solid = g.difference(solid, [g.mesh(V, F, f"__cut{k}") for k, (V, F) in enumerate(parts)])
    # the traced visual hull, grown by ``clamp``: a clamp only
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(V, F, f"__prism{k}") for k, (V, F) in enumerate(prisms)])
    solid = g.intersect([solid, g.offset(hull, clamp)])
    solid = g.opening(solid, r)
    V, F, info = g.to_mesh(solid)
    info.update({"lobes": len(lobes), "joint_cuts": len(cuts), "facets": len(fac), "r_open": r, "clamp": clamp})
    return V, F, info


def _inside_hull(P, front, side, top):
    m = f1.sd_point_in_poly(P[:, 0], P[:, 2], front) & f1.sd_point_in_poly(P[:, 1], P[:, 2], side)
    if top is not None:
        m &= f1.sd_point_in_poly(P[:, 0], P[:, 1], top)
    return m


def river_stage1_faceted(plan, front, side, top, rng):
    """Pilot 2 fix 1: faceted water-worn block. dome mass (lumpy superellipsoid) ∩ traced hull (+clamp) minus
    10-16 broad designed facets -> one big opening (the planes survive, meeting at soft ridges) -> the joints split
    the mass into lobes along meandering surfaces; each lobe is stepped down by its own amount and opened on its
    own (rounded lips both sides), a core behind keeps the joint a groove 10-16 cm deep, not a slot through."""
    r = plan["r_open"]
    clamp = plan["clamp"]
    lip = plan.get("lip_open", 0.05)
    steps = [j.get("step", 0.0) for j in plan.get("split", [])]
    big = max([r, lip] + [s + lip for s in steps] + [plan.get("core", 0.14)])
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil((big + 0.08) / plan["voxel1"])) + 6, name="__F1_S1")
    spec = plan["lobes"][0]
    V, F = rc.corestone_lobe(spec, rng)
    lobe = g.mesh(V, F, "__lobe0")
    P = rc.hull_points(V, F, 40000, rng)
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(Vp, Fp, f"__prism{k}") for k, (Vp, Fp) in enumerate(prisms)])
    mass = g.intersect([lobe, g.offset(hull, clamp)])
    # support points of the clamped mass: the dome's surface points inside the hull + the hull's own points inside
    # the dome (both approximate the clamped surface well enough for the cap depths)
    Ph = f1.hull_points(front, side, top, step=0.03)
    Pin = P[_inside_hull(P, front, side, top)]
    Ps = np.vstack([Pin, Ph])
    Ps = Ps[Ps[:, 2] > -0.05]
    cuts = rc.broad_facet_cuts(Ps, plan["facets_broad"], rng)
    mass = g.difference(mass, [g.mesh(Vc, Fc, f"__fac{k}") for k, (Vc, Fc) in enumerate(sd.batch_disjoint(cuts))])
    mass = g.opening(mass, r)
    lobes_info = []
    if plan.get("split"):
        gap = plan.get("joint_gap", 0.012)
        cutters = []
        for k, j in enumerate(plan["split"]):
            Vw, Fw = rc.wavy_halfspace(j["p0"], j["n"], amp=j.get("amp", 0.04), freq=j.get("freq", 1.2),
                                       seed=plan["seed"] + 13 * k, meander=j.get("meander"))
            cutters.append(g.mesh(Vw, Fw, f"__split{k}"))
        # regions: lobe 0 = outside cutter 0; lobe k = inside cutter k-1, outside cutter k; last = inside the last
        regions = []
        for k in range(len(cutters) + 1):
            parts = [mass]
            if k > 0:
                parts.append(g.offset(cutters[k - 1], -gap))
            reg = g.intersect(parts) if len(parts) > 1 else mass
            if k < len(cutters):
                reg = g.difference(reg, [g.offset(cutters[k], gap)])
            regions.append(reg)
        lobe_steps = plan.get("lobe_steps", [0.0] * len(regions))
        lobes = []
        for k, reg in enumerate(regions):
            s = lobe_steps[k]
            reg = g.offset(reg, -s) if s > 0 else reg
            lobes.append(g.opening(reg, lip))
            lobes_info.append({"lobe": k, "step_m": s})
        core = g.offset(mass, -plan.get("core", 0.14))
        extra = []
        zones = [j["zone"] for j in plan["split"] if j.get("zone")]
        if zones:
            # the joint dies out: outside its zone (balls) the groove is filled to the deepest step level, so the
            # joint is a crack that runs part-way over the rock and fades, as on the sheet
            balls = []
            for zk, (zc, zr) in enumerate(zones):
                Vb, Fb = rc.unit_sphere(4)
                balls.append(g.mesh(np.asarray(zc) + Vb * zr, Fb, f"__zone{zk}"))
            fill = g.offset(mass, -(max(lobe_steps) + 0.004))
            extra.append(g.difference(fill, balls))
        mass = g.closing(g.union(lobes + [core] + extra), plan.get("joint_close", 0.012))
    Vo, Fo, info = g.to_mesh(mass)
    info.update({"method": "faceted water-worn block", "broad_facets": len(cuts), "r_open": r, "clamp": clamp,
                 "lobes": lobes_info, "lip_open": lip})
    return Vo, Fo, info


def river_stage2(plan, V1, F1, rng):
    bvh = sd.bvh_of(V1, F1)
    parts, paths = [], []
    for ck in plan["cracks"]:
        P, m = rf.project_path(bvh, ck["pts"], ck["face"], ck.get("wander", 0.007), rng)
        if len(P) < 2:
            continue
        tt = np.linspace(0, 1, len(P))
        prof = np.clip(np.sin(np.pi * tt) ** 0.5, 0.15, 1.0) * rng.uniform(0.8, 1.15, len(P))
        parts.extend(rf.crack_wedge(P, m, ck["depth"] * np.clip(prof, 0.35, 1.0), ck["w"] * prof))
        paths.append(P)
    # second, finer facet pass on the water-rounded surface: the sheet's lumpy secondary facets, re-rounded at a
    # smaller radius so their edges stay soft but readable
    f2 = plan.get("facets2")
    r2 = f2["r"] if f2 else 0.0
    band = int(math.ceil(max(plan["lip_r"], r2, 0.012) / plan["voxel2"])) + 4
    g = sd.SDFGraph(voxel=plan["voxel2"], band=band, name="__P2_S2")
    base = g.mesh(V1, F1, "__stage1")
    n2 = 0
    if f2:
        Ps = rc.hull_points(V1, F1, 40000, rng)
        fac2 = rc.facet_cuts(Ps, rng, f2["count"], depth=f2["depth"], nz_min=-0.05, zmin=0.2)
        n2 = len(fac2)
        b2 = sd.batch_disjoint(fac2)
        base = g.difference(base, [g.mesh(V, F, f"__fac2_{k}") for k, (V, F) in enumerate(b2)])
        base = g.opening(base, r2)
    batches = sd.batch_disjoint(parts)
    solid = g.difference(base, [g.mesh(V, F, f"__crk{k}") for k, (V, F) in enumerate(batches)])
    solid = g.opening(solid, plan["lip_r"])
    V, F, info = g.to_mesh(solid)
    info["cracks"] = len(paths)
    info["facets2"] = n2
    return V, F, info, paths


# ----------------------------------------------------------------------------------------------- cliff
def cliff_stage1(plan, front, side, top, rng):
    S = plan["fracture"]
    smax = S["recess"][1]
    jd_max = S["joint_depth"][1]
    off_max = smax + jd_max
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil(off_max / plan["voxel1"])) + 6, name="__P2_C1")
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(V, F, f"__prism{k}") for k, (V, F) in enumerate(prisms)])
    lo = np.array([front[:, 0].min(), side[:, 0].min(), -plan["bury"]]) - 0.15
    hi = np.array([front[:, 0].max(), side[:, 0].max(), front[:, 1].max()]) + 0.15
    cells, A = fr.cells(lo, hi, S, rng)
    Vh = f1.hull_points(front, side, top, step=0.04)
    centre_xy = np.array([0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1])])
    eroded = {}

    def er(s):
        s = round(s, 3)
        if s not in eroded:
            eroded[s] = g.offset(hull, -s) if s != 0 else hull
        return eroded[s]
    blocks, meta = [], []
    step = S["recess_step"]
    for k, c in enumerate(cells):
        inside = sd.plane_sdf(Vh, c["planes"]) < 0
        Pin = Vh[inside]
        if len(Pin) < 10:
            continue
        s = round(fr.recess_for(c, S, rng) / step) * step
        jd = round(rng.uniform(*S["joint_depth"]) / step) * step
        pl = fr.shrink(c["planes"], S["gap"])
        pl += fr.facet_planes(c, Pin, centre_xy, S, rng)
        Vc = sd.polytope_vertices(pl)
        if len(Vc) < 4:
            continue
        Vm, Fm = sd.hull_mesh(Vc)
        blocks.append(g.intersect([er(s), g.mesh(Vm, Fm, f"__cell{k}")]))
        # the block's own core: the full (unshrunk) cell eroded ``jd`` deeper, so neighbouring cores touch and the
        # joints are deep slots of depth jd behind the faces, never holes through the rock
        Vu, Fu = sd.hull_mesh(c["V"])
        blocks.append(g.intersect([er(s + jd), g.mesh(Vu, Fu, f"__core{k}")]))
        meta.append({"ix": int(c["ix"]), "iy": int(c["iy"]), "level": int(c["level"]), "nlev": int(c["nlev"]),
                     "top": bool(c["top"]), "recess": float(s), "joint_depth": float(jd)})
    rub = fr.rubble_at_foot(Vh, rng, plan["rubble"]["count"], size=plan["rubble"]["size"])
    rub_g = [g.mesh(V, F, f"__rub{k}") for k, (V, F) in enumerate(sd.batch_disjoint(rub))]
    solid = g.union(blocks + rub_g)
    solid = g.opening(solid, S["open_r"])
    V, F, info = g.to_mesh(solid, keep_largest=False)
    V, F, nsh = keep_shells(V, F, 1500)
    info.update({"cells": len(cells), "blocks": len(meta), "offsets": sorted(eroded), "rubble": len(rub),
                 "shells": nsh})
    return V, F, info, meta


def cliff_stage1_jointset(plan, front, side, top, rng):
    """Pilot 2 fix 1: jointed granite. Cuboid blocks of three joint families (fr.jointset_cells: beds every
    0.4-1.2 m + two near-vertical sets), each block = its shrunk cell ∩ the hull eroded by its own recess (upper beds
    step back -> benches; neighbours protrude / recede 10-40 cm) ∩ a tilted outward face, an optional chamfer and a
    broken top on the crown; a core per block keeps every joint a deep slot; crisp arrises (opening 2.2 cm)."""
    S = plan["jointset"]
    smax = S["recess"][1]
    jd_max = S["joint_depth"][1]
    off_max = smax + jd_max
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil(off_max / plan["voxel1"])) + 6, name="__F1_C1")
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(V, F, f"__prism{k}") for k, (V, F) in enumerate(prisms)])
    lo = np.array([front[:, 0].min(), side[:, 0].min(), -plan["bury"]]) - 0.15
    hi = np.array([front[:, 0].max(), side[:, 0].max(), front[:, 1].max()]) + 0.15
    if S.get("columns"):
        cells, jinfo = fr.jointset_cells_cols(lo, hi, S, rng)
        ncol = max(c["col"] for c in cells) + 1
        col_base = rng.uniform(-0.5, 0.5, ncol) * S.get("col_jit", 0.3)
        S = dict(S, H=float(front[:, 1].max()))
    else:
        cells, jinfo = fr.jointset_cells(lo, hi, S, rng)
        col_base = None
    Vh = f1.hull_points(front, side, top, step=0.04)
    centre_xy = np.array([0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1])])
    eroded = {}

    def er(s):
        s = round(s, 3)
        if s not in eroded:
            eroded[s] = g.offset(hull, -s) if s != 0 else hull
        return eroded[s]
    blocks, meta = [], []
    step = S["recess_step"]
    for k, c in enumerate(cells):
        inside = sd.plane_sdf(Vh, c["planes"]) < 0
        Pin = Vh[inside]
        if len(Pin) < 10:
            continue
        s = fr.jointset_recess_cols(c, S, rng, col_base) if col_base is not None else fr.jointset_recess(c, S, rng)
        s = round(s / step) * step
        jd = round(rng.uniform(*S["joint_depth"]) / step) * step
        pl = fr.shrink(c["planes"], S["gap"])
        pl += fr.block_face_planes(c, Pin, centre_xy, S, rng)
        if S.get("facets"):
            # round 3: 2-4 tilted fracture facets per block on its exposed side (the sheet's blocks are rough,
            # multi-faceted, never one flat brick face)
            pl += fr.facet_planes(dict(c, seed=c["centre"]), Pin, centre_xy, S, rng)
        Vc = sd.polytope_vertices(pl)
        if len(Vc) < 4:
            continue
        Vm, Fm = sd.hull_mesh(Vc)
        blocks.append(g.intersect([er(s), g.mesh(Vm, Fm, f"__cell{k}")]))
        Vu, Fu = sd.hull_mesh(c["V"])
        blocks.append(g.intersect([er(max(s, 0.0) + jd), g.mesh(Vu, Fu, f"__core{k}")]))
        meta.append({"bed": int(c["bed"]), "nbeds": int(c["nbeds"]), "col": int(c["col"]), "row": int(c["row"]),
                     "top": bool(c["top"]), "recess": float(s), "joint_depth": float(jd)})
    rub = fr.rubble_at_foot(Vh, rng, plan["rubble"]["count"], size=plan["rubble"]["size"])
    rub_g = [g.mesh(V, F, f"__rub{k}") for k, (V, F) in enumerate(sd.batch_disjoint(rub))]
    solid = g.union(blocks + rub_g)
    solid = g.opening(solid, S["open_r"])
    V, F, info = g.to_mesh(solid, keep_largest=False)
    V, F, nsh = keep_shells(V, F, 1500)
    info.update({"method": "joint-set fracture", "cells": len(cells), "blocks": len(meta), "joints": jinfo,
                 "offsets": sorted(eroded), "rubble": len(rub), "shells": nsh})
    return V, F, info, meta


def keep_shells(V, F, min_tris):
    """Keep every connected shell with >= min_tris (the rock + the rubble at its foot); drop slivers."""
    n = len(V)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]]])
    lab = np.arange(n)
    for _ in range(4000):
        a = np.minimum(lab[E[:, 0]], lab[E[:, 1]])
        new = lab.copy()
        np.minimum.at(new, E[:, 0], a)
        np.minimum.at(new, E[:, 1], a)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    fl = lab[F[:, 0]]
    ids, cnt = np.unique(fl, return_counts=True)
    # signed volume per shell: internal voids (joint pockets sealed by the core) come out negative -> dropped
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol6 = np.einsum("ij,ij->i", A, np.cross(B, C))
    svol = {int(i): float(vol6[fl == i].sum() / 6.0) for i in ids[cnt >= min_tris]}
    keep_ids = set(i for i, v in svol.items() if v > 0)
    keepf = np.array([l in keep_ids for l in fl])
    Fk = F[keepf]
    used = np.unique(Fk)
    remap = -np.ones(n, np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[Fk], len(keep_ids)


def cliff_stage2(plan, V1, F1, rng):
    E1 = sd.edges_of(F1)
    N1 = sd.vertex_normals(V1, F1)
    H1 = sd.mean_curvature(V1, F1, E1, N1, n_smooth=1)
    parts = fr.edge_chips(V1, F1, H1, rng, plan["chips"]["count"], size=plan["chips"]["size"])
    n_chip = len(parts)
    fl = plan["flakes"]
    flat = 1.0 - sd.smoothstep(np.abs(H1), 3.0, 12.0)
    fparts = rf.flakes(V1, F1, rng, fl["count"], R=fl["R"], depth=fl["depth"], lean=fl["lean"],
                       jitter_deg=fl["jitter"], zmin=0.04, weights=flat[F1].mean(1) + 0.02)
    parts += fparts
    band = int(math.ceil(max(plan["lip_r"], 0.012) / plan["voxel2"])) + 4
    g = sd.SDFGraph(voxel=plan["voxel2"], band=band, name="__P2_C2")
    base = g.mesh(V1, F1, "__stage1")
    batches = sd.batch_disjoint(parts)
    solid = g.difference(base, [g.mesh(V, F, f"__chip{k}") for k, (V, F) in enumerate(batches)])
    solid = g.opening(solid, plan["lip_r"])
    V, F, info = g.to_mesh(solid, keep_largest=False)
    V, F, nsh = keep_shells(V, F, 800)
    info.update({"chips": n_chip, "flakes": len(fparts), "shells": nsh})
    return V, F, info, []


# ----------------------------------------------------------------------------------------------- common
def surface_relief(plan, V, F):
    """Masked meso noise (lumps on the river rocks, fine on the cliff) + the scanned relief, along the normal, both
    turned down on the rounded / sharp arrises so the rounding and the crisp edges survive."""
    E = sd.edges_of(F)
    N = sd.vertex_normals(V, F)
    H = sd.mean_curvature(V, F, E, N, n_smooth=3)
    arris = sd.smoothstep(H, 8.0, 30.0)
    m = 1.0 - 0.7 * arris
    disp = sd.fbm(V, plan["meso"], seed=plan["seed"]) * m
    V = V + N * disp[:, None]
    N = sd.vertex_normals(V, F)
    V2 = sw2.scan_displace(V, N, plan["kind"], mask=m)
    d2 = np.linalg.norm(V2 - V, axis=1)
    return V2, {"meso_rms_mm": round(float(np.sqrt((disp ** 2).mean()) * 1000), 2),
                "scan_rms_mm": round(float(np.sqrt((d2 ** 2).mean()) * 1000), 2)}


def build(name):
    plan = PLANS[name]
    rng = np.random.default_rng(plan["seed"])
    t0 = time.time()
    f1.clear_scene()
    front, side, top = f1.outlines(plan)
    meta = None
    if plan["kind"] == "river":
        if plan.get("method") == "faceted":
            V1, F1, i1 = river_stage1_faceted(plan, front, side, top, rng)
        else:
            V1, F1, i1 = river_stage1(plan, front, side, top, rng)
        log(name, "stage 1", i1, round(time.time() - t0, 1), "s")
        t1 = time.time()
        V, F, i2, paths = river_stage2(plan, V1, F1, rng)
    else:
        if plan.get("method") == "jointset":
            V1, F1, i1, meta = cliff_stage1_jointset(plan, front, side, top, rng)
        else:
            V1, F1, i1, meta = cliff_stage1(plan, front, side, top, rng)
        log(name, "stage 1", {k: v for k, v in i1.items()}, round(time.time() - t0, 1), "s")
        t1 = time.time()
        V, F, i2, paths = cliff_stage2(plan, V1, F1, rng)
    log(name, "stage 2", i2, round(time.time() - t1, 1), "s")
    V, i3 = surface_relief(plan, V, F)
    s = plan["size"]
    up = V[:, 2] > 0.0
    lo, hi = V[up].min(0), V[up].max(0)
    c = (lo + hi) / 2
    k = np.array([s["L"] / (hi[0] - lo[0]), s["D"] / (hi[1] - lo[1]), s["H"] / hi[2]])
    V = np.column_stack([(V[:, 0] - c[0]) * k[0], (V[:, 1] - c[1]) * k[1], V[:, 2] * k[2]])
    paths = [np.column_stack([(p[:, 0] - c[0]) * k[0], (p[:, 1] - c[1]) * k[1], p[:, 2] * k[2]]) for p in paths]
    i3["size_correction_xyz"] = [round(float(x), 4) for x in k]
    WORK.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(WORK / f"{name}_dense.npz", V=V.astype(np.float32), F=F.astype(np.int32),
                        V1=V1.astype(np.float32), F1=F1.astype(np.int32), front=front, side=side, top=top,
                        paths=np.array([np.asarray(p, np.float32) for p in paths] + [np.zeros((0, 3), np.float32)],
                                       dtype=object))
    info = {"rock": name, "method": "corestone" if plan["kind"] == "river" else "fracture", "stage1": i1,
            "stage2": i2, "relief": i3, "blocks": meta, "seconds": round(time.time() - t0, 1),
            "bbox": [np.round(V.min(0), 3).tolist(), np.round(V.max(0), 3).tolist()],
            "dense_tris": int(len(F)), "dense_verts": int(len(V))}
    (WORK / f"{name}_form.json").write_text(json.dumps(info, indent=1, default=float), encoding="utf-8")
    log(name, "done", info["dense_tris"], "tris", info["bbox"], info["seconds"], "s")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for n in (argv or list(PLANS)):
        build(n)


if __name__ == "__main__":
    main()
