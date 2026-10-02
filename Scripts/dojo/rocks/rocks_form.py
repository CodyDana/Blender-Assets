"""Pilot rock FORM stage (study 4.9.2 steps 1-6): traced visual hull -> joint cuts / joint-set blocks -> opening ->
flakes, cracks, chips -> lip opening -> Grid to Mesh (threshold 0) -> masked meso noise. Writes the dense source of
each rock to WorkFiles/dojo/build/rocks/work/<Rock>_dense.npz (+ _form.json). Headless Blender:

    blender -b --factory-startup --python Scripts/dojo/rocks/rocks_form.py -- [RiverRound RiverLong CliffChunk]

Two SDF stages, because the big operations need a wide band and the fine ones a fine voxel (study P15: band >=
r / voxel + 3): stage 1 at 1 cm (hull, joint cuts, the big river opening or the cliff's per-block erosion and
rounding), meshed and re-gridded for stage 2 at 5-6 mm (flakes, cracks, chips, the lip opening).
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
from rocks_plans import PLANS  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work"
REF = BUILD / "pilot" / "refcrops"


def log(*a):
    print("[form]", *a, flush=True)


def clear_scene():
    """Study P16: the factory-startup cube encloses a rock at the origin and blackens every AO bake."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def load_mask(rock, view, foot=0.12):
    """The traced sheet silhouette, with its bottom ``foot`` share clamped to the width at that height: the
    sheet's contact shadow survives the tracer's shadow rejection in the last ~10 px and became a 15 cm plinth
    when extruded (round 3 clay). Rock bottoms tuck in; they never flare."""
    m = np.load(REF / f"mask_{rock}_{view}.npy").copy()
    H = m.shape[0]
    r0 = int(round((1.0 - foot) * H))
    xs = np.nonzero(m[r0])[0]
    if len(xs):
        xl, xr = xs.min(), xs.max()
        m[r0:, :xl] = False
        m[r0:, xr + 1:] = False
    return m


def outlines(plan):
    s = plan["size"]
    L, H, D = s["L"], s["H"], s["D"]
    fr, fv = plan["views"]["front"]
    sr, sv = plan["views"]["side"]
    tr, tv = plan["views"]["top"]
    front = rf.fit_polygon(rf.mask_polygon(load_mask(fr, fv), 1, 1), L, H)
    side = rf.fit_polygon(rf.mask_polygon(load_mask(sr, sv), 1, 1), D, H)
    top = rf.fit_polygon(rf.mask_polygon(load_mask(tr, tv), 1, 1), L, D)
    top[:, 1] -= D / 2.0
    front = rf.extend_base(front, plan["base_cut"], -plan["bury"])
    side = rf.extend_base(side, plan["base_cut"], -plan["bury"])
    return front, side, top


def stage1_river(plan, front, side, top, rng):
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil(plan["r_big"] / plan["voxel1"])) + 5,
                    name="__DKR_S1")
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(V, F, f"__prism{k}") for k, (V, F) in enumerate(prisms)])
    # the joint cuts need the hull's points: a quick coarse hull of the prisms' intersection by sampling
    Vh = hull_points(front, side, top)
    cuts = []
    for n, depth in plan["joints"]:
        c = rf.joint_cut(Vh, np.array(n, float), depth)
        if c is not None:
            cuts.append(c)
    solid = g.difference(hull, [g.mesh(V, F, f"__joint{k}") for k, (V, F) in enumerate(cuts)])
    solid = g.opening(solid, plan["r_big"])
    V, F, info = g.to_mesh(solid)
    info["joint_cuts"] = len(cuts)
    return V, F, info


def sd_point_in_poly(px, py, poly):
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = (y1 > py) != (y2 > py)
        xint = (x2 - x1) * (py - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1
        inside ^= cond & (px < xint)
    return inside


def hull_points(front, side, top, step=0.02):
    """Points of the visual hull (grid samples inside all three outlines), for support distances."""
    lo = np.array([front[:, 0].min(), side[:, 0].min(), front[:, 1].min()])
    hi = np.array([front[:, 0].max(), side[:, 0].max(), front[:, 1].max()])
    xs = np.arange(lo[0], hi[0] + step, step)
    ys = np.arange(lo[1], hi[1] + step, step)
    zs = np.arange(max(lo[2], 0.0), hi[2] + step, step)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    X, Y, Z = X.ravel(), Y.ravel(), Z.ravel()
    m = sd_point_in_poly(X, Z, front) & sd_point_in_poly(Y, Z, side)
    if top is not None:
        m &= sd_point_in_poly(X, Y, top)
    return np.stack([X[m], Y[m], Z[m]], 1)


def stage1_cliff(plan, front, side, top, rng):
    """Columnar joint-set blocks: each cell takes the hull eroded by its own recess (blocks higher in their column
    step back: the sheet's ledges), the blocks are unioned (no per-block rounding: that left voids where four
    rounded blocks met), then one opening rounds every arris."""
    B = plan["blocks"]
    smax = max(max(r) for r in B["recess_by_level"])
    g = sd.SDFGraph(voxel=plan["voxel1"], band=int(math.ceil(max(smax, B["open_r"]) / plan["voxel1"])) + 6,
                    name="__DKR_S1c")
    prisms = rf.visual_hull_meshes(front, side, top)
    hull = g.intersect([g.mesh(V, F, f"__prism{k}") for k, (V, F) in enumerate(prisms)])
    lo = np.array([front[:, 0].min(), side[:, 0].min(), -plan["bury"]]) - 0.2
    hi = np.array([front[:, 0].max(), side[:, 0].max(), front[:, 1].max()]) + 0.2
    spec = dict(bbox=(lo, hi), x_splits=B["x_splits"], y_splits=B["y_splits"], jit=B["jit"], beds=B["beds"],
                dip_deg=B["dip_deg"], min_block=B["min_block"], top_z=plan["size"]["H"])
    cells, joints = rf.cliff_cells(spec, rng)
    eroded = {0.0: hull}
    blocks, meta = [], []
    below = {}
    for k, c in enumerate(cells):
        lev = min(c["level"], len(B["recess_by_level"]) - 1)
        s = float(rng.choice(B["recess_by_level"][lev]))
        # recess never decreases up a column: an upper block standing proud of the one under it read as a cave
        s = max(s, below.get((c["ix"], c["iy"]), 0.0))
        below[(c["ix"], c["iy"])] = s
        if s not in eroded:
            eroded[s] = g.offset(hull, -s)
        Vc, Fc = sd.hull_mesh(c["V"])
        blocks.append(g.intersect([eroded[s], g.mesh(Vc, Fc, f"__cell{k}")]))
        meta.append({"ix": c["ix"], "iy": c["iy"], "level": c["level"], "top": c["top"], "recess": s})
    solid = g.opening(g.union(blocks), B["open_r"])
    V, F, info = g.to_mesh(solid)
    info["blocks"] = meta
    info["cells"] = len(cells)
    info["beds_per_column"] = {int(k): len(v) for k, v in joints["beds"].items()}
    return V, F, info, cells, meta, joints


def joint_cracks(plan, bvh, cells, meta, joints, rng):
    """Crack traces where the joint planes meet the surface (study 4.9.2 step 4: cracks along the joint sets):
    vertical joints on the front / back (x family) and the ends (y family), bed joints along each column. A run is
    kept only where the blocks on both sides have the same recess (+-3 cm); otherwise the joint is already a step."""
    from mathutils import Vector
    B = plan["blocks"]
    rec = np.array([m["recess"] for m in meta])
    H = plan["size"]["H"]
    out = []

    def cast(o, dvec):
        hit = bvh.ray_cast(Vector(o), Vector(dvec), 25.0)
        return None if hit[0] is None else np.array(hit[0][:])

    def runs(pts, n):
        if len(pts) < 4:
            return []
        P = np.array(pts)
        a = rf.cell_of(P - n * 0.04, cells)
        b = rf.cell_of(P + n * 0.04, cells)
        ok = (a >= 0) & (b >= 0) & (a != b)
        ok &= np.abs(rec[np.maximum(a, 0)] - rec[np.maximum(b, 0)]) <= 0.03
        res, cur = [], []
        for p, k in zip(P, ok):
            if k:
                cur.append(p)
            else:
                if len(cur) >= 4:
                    res.append(np.array(cur))
                cur = []
        if len(cur) >= 4:
            res.append(np.array(cur))
        return res

    def vertical(plane, face):
        n, d = plane
        pts = []
        for z in np.arange(0.06, H - 0.04, 0.03):
            if face in ("front", "back"):
                y0, dv = (-9.0, (0, 1, 0)) if face == "front" else (9.0, (0, -1, 0))
                x = (d - n[2] * z - n[1] * 0.0) / n[0]
                p = cast((x, y0, z), dv)
                if p is not None:
                    x = (d - n[2] * z - n[1] * p[1]) / n[0]
                    p = cast((x, y0, z), dv)
            else:
                x0, dv = (-9.0, (1, 0, 0)) if face == "left" else (9.0, (-1, 0, 0))
                y = (d - n[2] * z) / n[1]
                p = cast((x0, y, z), dv)
                if p is not None:
                    y = (d - n[2] * z - n[0] * p[0]) / n[1]
                    p = cast((x0, y, z), dv)
            if p is not None and abs(float(n @ p) - d) < 0.02:
                pts.append(p)
        return runs(pts, n)

    def bed(plane, face, x0, x1):
        n, d = plane
        pts = []
        for x in np.arange(x0, x1, 0.03):
            y0, dv = (-9.0, (0, 1, 0)) if face == "front" else (9.0, (0, -1, 0))
            z = (d - n[0] * x) / n[2]
            p = cast((x, y0, z), dv)
            if p is not None:
                z = (d - n[0] * x - n[1] * p[1]) / n[2]
                p = cast((x, y0, z), dv)
            if p is not None and abs(float(n @ p) - d) < 0.02:
                pts.append(p)
        return runs(pts, n)

    for pl in joints["x"]:
        for face in ("front", "back"):
            out += [(r, face) for r in vertical(pl, face) if rng.uniform() < B["crack_p"]]
    for pl in joints["y"]:
        for face in ("left", "right"):
            out += [(r, face) for r in vertical(pl, face) if rng.uniform() < B["crack_p"]]
    xs = [-9.0] + list(B["x_splits"]) + [9.0]
    for ix, pls in joints["beds"].items():
        for pl in pls:
            for face in ("front", "back"):
                out += [(r, face) for r in bed(pl, face, max(xs[ix], -plan["size"]["L"] / 2) + 0.05,
                                               min(xs[ix + 1], plan["size"]["L"] / 2) - 0.05)
                        if rng.uniform() < B["bed_crack_p"]]
    return out


def facet_cuts(plan, V1, cells, rng):
    """Broad fresh-fracture planes per block (the sheet's 'flat fracture planes'): 1-3 cuts on the block's EXPOSED
    sides only (a cut on a covered top opened slots between tiers), normals 10-24 deg off the side, 3-10 cm deep,
    each boxed to its own cell (+1 cm) so a cut never bites the neighbour."""
    B = plan["blocks"]
    out = []
    for c in cells:
        inside = sd.plane_sdf(V1, c["planes"]) < 0
        P = V1[inside]
        if len(P) < 80:
            continue
        dirs = []
        if c["iy"] == 0:
            dirs.append((0.0, -1.0, 0.0))
        if c["iy"] == c["ny"]:
            dirs.append((0.0, 1.0, 0.0))
        if c["ix"] == 0:
            dirs.append((-1.0, 0.0, 0.0))
        if c["ix"] == c["nx"]:
            dirs.append((1.0, 0.0, 0.0))
        if c["top"]:
            dirs.append((0.0, 0.0, 1.0))
        if not dirs:
            continue
        k = int(rng.integers(B["facets"][0], B["facets"][1] + 1))
        for _ in range(k):
            d0 = np.array(dirs[rng.integers(len(dirs))])
            # tilt toward another EXPOSED side only: the cut is deepest at the edge it tilts toward, and an edge
            # against a taller neighbour became a black V-pocket (cliff pass 3)
            others = [np.array(d) for d in dirs if abs(float(np.dot(d, d0))) < 0.5]
            if others:
                t = others[rng.integers(len(others))]
                a = rng.uniform(*B["facet_tilt"])
                t = sd.unit(t + 0.35 * np.cross(d0, t) * rng.uniform(-1, 1))
            else:
                t = sd.unit(np.cross(d0, sd.unit(rng.normal(0, 1, 3))))
                a = rng.uniform(2.0, 6.0)
            n = sd.unit(d0 * np.cos(np.radians(a)) + t * np.sin(np.radians(a)))
            s_ = P @ n
            dd = float(s_.max() - rng.uniform(*B["facet_depth"]))
            pl = [(pn, pd + 0.01) for pn, pd in c["planes"]] + [(-n, -dd)]
            Vp = sd.polytope_vertices(pl)
            if len(Vp) >= 4:
                out.append(sd.hull_mesh(Vp))
    return out


def stage2(plan, V1, F1, rng, cells=None, meta=None, joints=None):
    fl = plan["flakes"]
    bvh = sd.bvh_of(V1, F1)
    cut_parts = []
    paths = []

    def add_crack(P, m, depth, w):
        tt = np.linspace(0, 1, len(P))
        prof = np.clip(np.sin(np.pi * tt) ** 0.5, 0.15, 1.0) * rng.uniform(0.75, 1.2, len(P))
        cut_parts.extend(rf.crack_wedge(P, m, depth * np.clip(prof, 0.35, 1.0), w * prof))
        paths.append(P)

    # planned cracks (read off the sheet's main views)
    for ck in plan["cracks"]:
        P, m = rf.project_path(bvh, ck["pts"], ck["face"], ck.get("wander", 0.007), rng)
        if len(P) >= 2:
            add_crack(P, m, ck["depth"], ck["w"])
    n_jc = n_facet = n_chip = 0
    if cells is not None:
        B = plan["blocks"]
        mdir = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (-1, 0, 0), "right": (1, 0, 0)}
        for P, face in joint_cracks(plan, bvh, cells, meta, joints, rng):
            add_crack(P, np.array(mdir[face], float), rng.uniform(*B["crack_depth"]), rng.uniform(*B["crack_w"]))
            n_jc += 1
        fc = facet_cuts(plan, V1, cells, rng)
        cut_parts += fc
        n_facet = len(fc)
        for c in cells:
            # chips only off column-top blocks: a chip off a corner under a taller neighbour left a black pocket
            if not c["top"] or rng.uniform() > B["chip_p"]:
                continue
            inside = sd.plane_sdf(V1, c["planes"]) < 0
            if inside.sum() < 80:
                continue
            ch = rf.corner_chip(V1[inside], rng, depth_share=(0.06, 0.14))
            if ch is not None:
                cut_parts.append(ch)
                n_chip += 1
    n_crack = len(paths)
    # flakes (spall scars), kept off the rounded arrises (they made spiky crests on the cliff's first pass)
    E1 = sd.edges_of(F1)
    H1 = sd.mean_curvature(V1, F1, E1, n_smooth=2)
    flat = 1.0 - sd.smoothstep(np.abs(H1), 3.0, 12.0)
    w_face = flat[F1].mean(1) + 0.02
    fparts = rf.flakes(V1, F1, rng, fl["count"], R=fl["R"], depth=fl["depth"], lean=fl["lean"],
                       jitter_deg=fl["jitter"], zmin=0.04, weights=w_face)
    cut_parts += fparts
    batches = sd.batch_disjoint(cut_parts)
    band = int(math.ceil(max(plan["lip_r"], 0.012) / plan["voxel2"])) + 4
    g = sd.SDFGraph(voxel=plan["voxel2"], band=band, name="__DKR_S2")
    base = g.mesh(V1, F1, "__stage1")
    solid = g.difference(base, [g.mesh(V, F, f"__cut{k}") for k, (V, F) in enumerate(batches)])
    solid = g.opening(solid, plan["lip_r"])
    V, F, info = g.to_mesh(solid)
    info.update({"cracks": n_crack, "joint_cracks": n_jc, "facet_cuts": n_facet, "chips": n_chip,
                 "flakes": len(fparts), "cutter_batches": len(batches)})
    return V, F, info, paths


def meso_noise(plan, V, F):
    """Study 4.9.2 step 6: masks first (arris = convex curvature), then 2-3 octaves of displacement along the
    normal, masked down on the rounded arrises so the opening's rounding survives."""
    E = sd.edges_of(F)
    N = sd.vertex_normals(V, F)
    H = sd.mean_curvature(V, F, E, N, n_smooth=3)
    arris = sd.smoothstep(H, 8.0, 30.0)
    disp = sd.fbm(V, plan["noise"], seed=plan["seed"]) * (1.0 - 0.7 * arris)
    V = V + N * disp[:, None]
    return V, {"noise_rms_mm": round(float(np.sqrt((disp ** 2).mean()) * 1000), 2)}


def build(name):
    plan = PLANS[name]
    rng = np.random.default_rng(plan["seed"])
    t0 = time.time()
    clear_scene()
    front, side, top = outlines(plan)
    if plan["kind"] == "river":
        V1, F1, i1 = stage1_river(plan, front, side, top, rng)
        cells = meta = joints = None
    else:
        V1, F1, i1, cells, meta, joints = stage1_cliff(plan, front, side, top, rng)
    log(name, "stage 1", {k: v for k, v in i1.items() if k != "blocks"}, round(time.time() - t0, 1), "s")
    t1 = time.time()
    V, F, i2, paths = stage2(plan, V1, F1, rng, cells, meta, joints)
    log(name, "stage 2", i2, round(time.time() - t1, 1), "s")
    V, i3 = meso_noise(plan, V, F)
    # size: the opening and the joint cuts shrink the hull a few %; scale the above-grade extents back to the
    # sheet's measured length / depth / height (x, y about the above-grade centre, z about the ground)
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
                        V1=V1.astype(np.float32), F1=F1.astype(np.int32),
                        front=front, side=side, top=top,
                        paths=np.array([np.asarray(p, np.float32) for p in paths], dtype=object))
    info = {"rock": name, "stage1": i1, "stage2": i2, "noise": i3, "seconds": round(time.time() - t0, 1),
            "bbox": [np.round(V.min(0), 3).tolist(), np.round(V.max(0), 3).tolist()],
            "dense_tris": int(len(F)), "dense_verts": int(len(V))}
    (WORK / f"{name}_form.json").write_text(json.dumps(info, indent=1, default=float), encoding="utf-8")
    log(name, "done", info["dense_tris"], "tris", info["bbox"], info["seconds"], "s")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = argv or list(PLANS)
    for n in names:
        build(n)


if __name__ == "__main__":
    main()
