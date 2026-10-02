"""Pilot rock BUILD (study 4.9.5 a, 4.10-4.15): dense source (rocks_form.py) -> weathering masks -> the shipped
Nanite mid (+ moss cushions; grass tufts on the cliff) -> unique UV0 + UV1 -> bakes (N DirectX, ORM, M) -> preview
materials (= the Unreal MI plan) -> UCX hulls + traversal -> qa_check -> export through Scripts/pipeline ->
rocks_catalog.json -> Assets/Dojo/DojoRocks.blend. Headless:

    blender -b --factory-startup --python Scripts/dojo/rocks/build_rocks.py -- [rocks...] [--no-export]

A subset rebuild opens the existing DojoRocks.blend and replaces only those rocks.
"""
from __future__ import annotations

import hashlib
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
import bmesh  # noqa: E402
from mathutils import Matrix  # noqa: E402

import stone_sdf as sd  # noqa: E402
import stone_bake as sb  # noqa: E402
import stone_weather as sw  # noqa: E402
import rocks_material as rmat  # noqa: E402
from rocks_plans import PLANS  # noqa: E402
from pipeline import helpers, textures  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work"
EXPORT = ROOT / "Exports" / "DojoKit" / "Rocks"
TEX = EXPORT / "Textures"
BLEND = ROOT / "Assets" / "Dojo" / "DojoRocks.blend"
TEXEL = 5.12
SHORT = {"RiverRound": "BoulderRiver01", "RiverLong": "BoulderRiver02", "CliffChunk": "Cliff01"}

# per-rock weathering parameters (study 4.11), from the sheet's regions (ref_measure.json): river boulders carry a
# dark wet band (bottom ~30 %: luma p50 0.20 vs 0.43 mid) and moss on the dry tops; the cliff, moss and grass on
# ledges and block tops and in the cracks
WEATHER = {
    "RiverRound": dict(moss=dict(top=0.55, brk_lo=0.50, brk_hi=0.63, crevice=0.6),
                       lichen=dict(per_m2=70, r_lo=0.006, r_hi=0.03, c_lo=0.55, c_hi=0.70),
                       ochre=0.9, streak=0.55, grime=0.9, mott_lo=0.46, mott_hi=0.68),
    "RiverLong": dict(moss=dict(top=0.52, brk_lo=0.40, brk_hi=0.54, crevice=0.6),
                      lichen=dict(per_m2=70, r_lo=0.006, r_hi=0.03, c_lo=0.55, c_hi=0.70),
                      ochre=0.9, streak=0.55, grime=0.9, mott_lo=0.46, mott_hi=0.68),
    "CliffChunk": dict(moss=dict(top=0.0, ledges=True, crevice=1.0, crev_lo=0.30), lichen=dict(per_m2=150),
                       ochre=0.95, streak=0.75, grime=0.9, mott_lo=0.46, mott_hi=0.68),
}


def log(*a):
    print("[build]", *a, flush=True)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clear_rock(prefix):
    for ob in list(bpy.data.objects):
        if ob.name == prefix or ob.name.startswith("UCX_" + prefix) or ob.name.startswith("__"):
            bpy.data.objects.remove(ob)


def pick_sites(P, N, w, n, min_d, rng):
    """Up to ``n`` tuft sites among points with weight ``w`` > 0.5, at least ``min_d`` apart."""
    idx = np.nonzero(w > 0.5)[0]
    rng.shuffle(idx)
    out = []
    for i in idx:
        if all(np.linalg.norm(P[i] - P[j]) > min_d for j in out):
            out.append(i)
            if len(out) >= n:
                break
    return P[out], N[out]


def climb_top(Vm, landing=(0.75, 0.6)):
    """The highest z whose horizontal section (points within 2 cm below it) spans >= landing (x, y) metres; the
    collision top is flattened there (study 4.13: GASP mantles need a top sloped < 2 deg, >= 0.49 m deep)."""
    top = float(Vm[:, 2].max())
    for z in np.arange(top, top * 0.5, -0.01):
        sec = Vm[(Vm[:, 2] <= z) & (Vm[:, 2] > z - 0.02)]
        if len(sec) < 10:
            continue
        ext = sec.max(0) - sec.min(0)
        if ext[0] >= landing[0] and ext[1] >= landing[1]:
            return float(z), ext[:2].tolist(), top - z
    return None, None, None


def ucx(parent, points, index):
    """UCX_<parent>_NN from a point cloud through the pipeline's make_ucx_hull (on a temporary hull object)."""
    pts = np.unique(np.round(np.asarray(points, float), 4), axis=0)
    V, F = sd.hull_mesh(pts)
    tmp = sb.make_obj("tmp_hull_src", V, F, smooth=False)
    hull = helpers.make_ucx_hull(tmp, index=0, max_verts=32)
    name = f"UCX_{parent.name}_{index:02d}"
    hull.name = name
    hull.data.name = name
    hull.parent = parent
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    me = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(me)
    return hull


def build_rock(name):
    plan = PLANS[name]
    short = SHORT[name]
    rng = np.random.default_rng(plan["seed"] + 900)
    t0 = time.time()
    prefix = plan["prefix"]
    clear_rock(prefix)
    d = np.load(WORK / f"{name}_dense.npz", allow_pickle=True)
    V, F = d["V"].astype(float), d["F"].astype(np.int64)
    paths = [np.asarray(p, float) for p in d["paths"]]
    E = sd.edges_of(F)
    N = sd.vertex_normals(V, F)
    H = sd.mean_curvature(V, F, E, N, n_smooth=3)
    params = dict(WEATHER[name])
    params["wet"] = plan.get("wet")
    M, fields = sw.masks(V, F, N, H, params, plan["seed"] + 77, paths)
    log(name, "masks", sw.shares(M, V, F), round(time.time() - t0, 1), "s")
    dense = sb.make_obj(f"__{name}_Dense", V, F)
    sb.set_point_colour(dense, "Mask", M[:, :3])
    sb.set_point_colour(dense, "MaskA", np.repeat(M[:, 3:4], 3, 1))
    # ---- the shipped mid: voxel remesh of the dense source (clean quads; collapse decimation folds the unwrap)
    mid0 = sb.make_obj(f"__{name}_Mid", V, F)
    sb.remesh(mid0, plan["mid_voxel"])
    Vm, Fm = sb.mesh_arrays(mid0)
    me0 = mid0.data
    bpy.data.objects.remove(mid0)
    bpy.data.meshes.remove(me0)
    near, dist = sd.kd_nearest(V, Vm)
    Mm = M[near]
    moss_top_m = fields["moss_top"][near]
    log(name, "mid", len(Fm), "tris; mid-to-dense p95", round(float(np.percentile(dist, 95)) * 1000, 2), "mm")
    parts = [(Vm, Fm, 0)]
    shell = sb.cushion_shell(Vm, Fm, moss_top_m, plan["seed"] + 5)
    if shell is not None:
        parts.append((shell[0], shell[1], 1))
    tufts = None
    if plan["kind"] == "cliff":
        Nm = sd.vertex_normals(Vm, Fm)
        w = (moss_top_m > 0.5) & (Nm[:, 2] > 0.6)
        sites, nrm = pick_sites(Vm, Nm, w.astype(float), 34, 0.22, rng)
        tufts = sb.grass_tufts(sites, nrm, plan["seed"] + 9)
        if tufts is not None:
            parts.append((tufts[0], tufts[1], 2))
    Vs, Fs, mids, off = [], [], [], 0
    for Vp, Fp, mi in parts:
        Vs.append(Vp)
        Fs.append(Fp + off)
        mids.append(np.full(len(Fp), mi, np.int32))
        off += len(Vp)
    V_all, F_all, mat_idx = np.vstack(Vs), np.vstack(Fs), np.concatenate(mids)
    ob = sb.make_obj(prefix, V_all, F_all)
    me = ob.data
    for mi in range(int(mat_idx.max()) + 1):
        tmp = bpy.data.materials.new(f"__bake_slot{mi}")
        tmp.use_nodes = True
        me.materials.append(tmp)
    me.polygons.foreach_set("material_index", mat_idx)
    # vertex colour 'Col' (UE imports one set): rock / moss white; tufts R = base->tip, G variation
    col = np.ones((len(V_all), 3))
    if tufts is not None:
        col[len(V_all) - len(tufts[0]):] = tufts[2]
    sb.set_point_colour(ob, "Col", col)
    # weld sub-micron remesh slivers (qa_check: zero-length edges / coincident vertices); attributes and material
    # indices ride along in bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me)
    bm.free()
    me.update()
    # ---- UVs
    size = int(plan["map"])
    uvi = sb.unique_uv(ob, size, TEXEL, log=lambda *a: log(name, *a))
    log(name, "uv", uvi)
    # ---- bakes
    hidden = [o for o in bpy.data.objects if o not in (ob, dense) and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    dense.data.materials.append(sb.emit_material("__mask_emit", "Mask"))
    tb = time.time()
    img_n = sb.new_image(f"__{short}_N_gl", size, (0.5, 0.5, 1.0, 1.0))
    sb.bake(ob, [dense], img_n, "NORMAL", extrusion=0.02, ray=0.06)
    img_m = sb.new_image(f"__{short}_M_rgb", size, (0.0, 0.0, 0.0, 1.0))
    sb.bake(ob, [dense], img_m, "EMIT", extrusion=0.02, ray=0.06)
    dense.data.materials.clear()
    dense.data.materials.append(sb.emit_material("__maskA_emit", "MaskA"))
    img_a = sb.new_image(f"__{short}_M_a", size, (0.0, 0.0, 0.0, 1.0))
    sb.bake(ob, [dense], img_a, "EMIT", extrusion=0.02, ray=0.06)
    dense.hide_render = True
    sb.gpu(bpy.context.scene)
    ao = textures.bake_ao(ob, f"__{short}_ao", size=size, samples=96, margin=16)
    t_bake = round(time.time() - tb, 1)
    for o in hidden:
        o.hide_render = False
    TEX.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    gl = WORK / f"T_DKR_{short}_N_gl.png"
    textures.write_png(sb.image_px(img_n), gl)
    n_path = TEX / f"T_DKR_{short}_N.png"
    textures.flip_normal_green(gl, n_path)
    mrgb = sb.image_px(img_m)
    ma = sb.image_px(img_a)
    mpx = np.concatenate([mrgb[..., :3], ma[..., :1]], -1)
    m_path = TEX / f"T_DKR_{short}_M.png"
    textures.write_png(mpx, m_path, alpha=True)
    rough = bpy.data.images.new(f"__{short}_rough", size, size, alpha=False, float_buffer=False, is_data=True)
    rp = np.ones((size, size, 4), np.float32)
    rv = np.clip(0.78 + 0.10 * mpx[..., 1] + 0.10 * np.abs(mpx[..., 3] - 0.5), 0, 1)   # lichen / stain matte
    rp[..., 0] = rp[..., 1] = rp[..., 2] = rv
    rough.pixels.foreach_set(rp.ravel())
    orm_path = TEX / f"T_DKR_{short}_ORM.png"
    textures.pack_orm(ao, rough, None, orm_path)
    aopx = sb.image_px(ao)[..., 0]
    for im in (img_n, img_m, img_a, ao, rough):
        bpy.data.images.remove(im)
    # ---- materials (the Unreal MI plan)
    maps = {"N": n_path, "ORM": orm_path, "M": m_path, "DBC": TEX / "T_DKR_GraniteDetail_BC.png",
            "DH": TEX / "T_DKR_GraniteDetail_H.png", "MOSS": TEX / "T_DKR_MossDetail_BC.png"}
    slots = [rmat.rock_material(f"MI_DKR_{short}", maps, uvi["m_per_uv0"])]
    if shell is not None:
        slots.append(rmat.moss_material(maps))
    if tufts is not None:
        slots.append(rmat.grass_material())
    old = [m for m in me.materials]
    mi_keep = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi_keep)
    me.materials.clear()                       # (clear() resets every face to slot 0: restore the indices)
    for m in slots:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mi_keep)
    me.update()
    for m in old:
        if m.users == 0:
            bpy.data.materials.remove(m)
    # ---- collision + traversal (study 4.13)
    rock_V = Vm
    above = rock_V[rock_V[:, 2] > -0.06]
    hulls = []
    trav = None
    climb = None
    if plan["kind"] == "river":
        zt, ext, sag = climb_top(rock_V)
        xs = np.linspace(above[:, 0].min(), above[:, 0].max(), 4)
        for k in range(3):
            a, b = xs[k] - 0.05, xs[k + 1] + 0.05
            P = above[(above[:, 0] >= a) & (above[:, 0] <= b)].copy()
            if zt is not None:
                P[:, 2] = np.minimum(P[:, 2], zt)
            hulls.append(ucx(ob, P, k))
        climb = {"climbable": zt is not None, "flat_top_z": round(zt, 3) if zt else None,
                 "landing_xy_m": [round(x, 3) for x in ext] if ext else None,
                 "visual_crown_above_flat_m": round(sag, 3) if sag else None,
                 "mantle_height_m": round(zt, 3) if zt else None,
                 "gasp": "mantle (<= 2.75 m); needs a hidden LevelBlock_Traversable marker on the traversal box"}
        if zt is not None:
            sec = rock_V[(rock_V[:, 2] <= zt) & (rock_V[:, 2] > zt - 0.02)]
            c = (sec.min(0) + sec.max(0)) / 2
            trav = {"center": [round(float(c[0]), 3), round(float(c[1]), 3), round(zt, 3)],
                    "extent": [round(float(x), 3) for x in (sec.max(0) - sec.min(0))[:2] / 2] + [0.02],
                    "top_slope_deg": 0.0}
    else:
        xs = [-9.0] + list(plan["blocks"]["x_splits"]) + [9.0]
        for k in range(len(xs) - 1):
            P = above[(above[:, 0] >= xs[k] - 0.04) & (above[:, 0] <= xs[k + 1] + 0.04)]
            if len(P) > 20:
                hulls.append(ucx(ob, P, len(hulls)))
        climb = {"climbable": False, "reason": "3.08 m top exceeds the 2.75 m mantle limit; faces steeper than "
                                               "44.77 deg; no marker (study 4.13 item 2)"}
    # ---- measures (SG14 on the dense source; the mid follows it within the remesh error)
    pf, _ = sb.plane_fraction(V, F, k=6)
    pf_mid, _ = sb.plane_fraction(Vm, Fm, k=6)
    up = V[:, 2] > 0
    info = {
        "rock": name, "object": prefix, "short": short, "sheet": plan["sheet"],
        "size_above_grade_m": {"L": round(float(np.ptp(V[up, 0])), 3), "D": round(float(np.ptp(V[up, 1])), 3),
                               "H": round(float(V[:, 2].max()), 3)},
        "buried_skirt_m": round(float(-V[:, 2].min()), 3),
        "tris": int(len(F_all)), "rock_tris": int(len(Fm)), "verts": int(len(V_all)),
        "verts_per_tri": round(len(V_all) / max(len(F_all), 1), 3),
        "moss_shell_tris": int(len(shell[1])) if shell is not None else 0,
        "grass_tris": int(len(tufts[1])) if tufts is not None else 0,
        "dense_tris": int(len(F)), "mid_voxel_m": plan["mid_voxel"],
        "mid_to_dense_mm_p50_p95": [round(float(np.percentile(dist, q)) * 1000, 2) for q in (50, 95)],
        "uv": uvi, "map_px": size, "bake_s": t_bake,
        "ao_p50": round(float(np.median(aopx[aopx > 0.02])), 3),
        "mask_shares_dense": sw.shares(M, V, F),
        "sg14": {"plane_fraction_k6_15deg_dense": round(pf, 3), "plane_fraction_k6_15deg_mid": round(pf_mid, 3),
                 "sharp_crease_share_30deg": round(sb.crease_share(V, F), 4),
                 "arris_radius_m_p25_p50_p75": sb.arris_radius(V, F, H),
                 "cracks": len(paths)},
        "collision": {"kind": "UCX convex", "count": len(hulls), "climb": climb, "traversal": trav},
        "maps": {k: str(Path(v).relative_to(ROOT)) for k, v in maps.items()},
        "materials": [m.name for m in me.materials],
        "seconds": round(time.time() - t0, 1),
    }
    bpy.data.objects.remove(dense)
    for m in [m for m in bpy.data.materials if m.name.startswith("__") and m.users == 0]:
        bpy.data.materials.remove(m)
    for mesh in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(mesh)
    log(name, "built", json.dumps({k: info[k] for k in ("tris", "verts_per_tri", "sg14", "collision")},
                                  default=str))
    return ob, info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    no_export = "--no-export" in argv
    names = [a for a in argv if not a.startswith("--")] or list(PLANS)
    if BLEND.exists() and set(names) != set(PLANS):
        bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    cat_path = BUILD / "rocks_catalog.json"
    catalog = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {"rocks": {}}
    built = {}
    for n in names:
        ob, info = build_rock(n)
        built[n] = (ob, info)
    # ---- QA (study 4.15: unique-UV rocks pass with no UV waiver; UV1 present for Fab)
    qa = {}
    for n, (ob, info) in built.items():
        r = qa_check([ob], require_uv1=True, require_ucx=True, texel_density=TEXEL, tolerance=0.25,
                     uv0_tile_range=(-0.001, 1.001))
        fails = [c for c in r["checks"] if not c["passed"]]
        qa[n] = {"passed": r["passed"], "hard_fails": len(fails),
                 "fails": [(c["name"], c["object"], c["detail"]) for c in fails],
                 "texel": [c["detail"] for c in r["checks"] if c["name"] == "texel_density"],
                 "triangles": r["triangles"]}
        log("QA", n, r["passed"], qa[n]["fails"][:5])
    (BUILD / "qa_report.json").write_text(json.dumps({"waivers": [], "results": qa}, indent=1), encoding="utf-8")
    exp = {}
    if not no_export:
        EXPORT.mkdir(parents=True, exist_ok=True)
        for n, (ob, info) in built.items():
            if not qa[n]["passed"]:
                log("QA FAILED, not exported:", n)
                continue
            path = EXPORT / f"{ob.name}.fbx"
            res = export_fbx(str(path), [ob], kind="static")
            exp[ob.name] = {"file": str(path.relative_to(ROOT)), "sha256": sha256(path),
                            "bytes": path.stat().st_size, "warnings": res.get("warnings", []),
                            "objects": [x if isinstance(x, str) else getattr(x, "name", str(x))
                                        for x in res.get("objects", [])]}
            info["export"] = exp[ob.name]
        for f in sorted(TEX.glob("T_DKR_*.png")):
            exp[f.name] = {"file": str(f.relative_to(ROOT)), "sha256": sha256(f), "bytes": f.stat().st_size}
        (BUILD / "export_report.json").write_text(json.dumps(
            {"pipeline": "Scripts/pipeline/export_fbx.py kind=static", "files": exp}, indent=1), encoding="utf-8")
    for n, (ob, info) in built.items():
        info["qa"] = {"passed": qa[n]["passed"], "hard_fails": qa[n]["hard_fails"], "texel": qa[n]["texel"]}
        catalog["rocks"][n] = info
    catalog["updated"] = time.strftime("%Y-%m-%d %H:%M")
    cat_path.write_text(json.dumps(catalog, indent=1, default=str), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    for im in bpy.data.images:
        if im.filepath:
            try:
                im.filepath = bpy.path.relpath(bpy.path.abspath(im.filepath), start=str(BLEND.parent))
            except ValueError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    log("saved", BLEND)


if __name__ == "__main__":
    main()
