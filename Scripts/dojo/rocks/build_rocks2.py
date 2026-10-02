"""Pilot 2 rock BUILD (study 4.9.5 a, 4.10-4.15): dense source (rocks_form2.py) -> pilot 2 weathering fields
(stone_weather2: moss, lichen zone + rosette seeds, wet, olive, stain, cavity, arris) -> the shipped Nanite mid
(voxel remesh; + moss cushions; grass tufts on the cliff ledges) -> unique UV0 + UV1 -> bakes from the dense source
through the COMPOSITE material (rocks_material2: the regraded CC0 scan macro layer + the weathering layers):
BC (linear, written sRGB), N (DirectX), ORM (baked AO, baked roughness: wet gloss / moss / lichen), M (R moss,
G lichen, B wet) -> MI_DKR_<Rock> (BC x the tiling crystal grain detail) -> UCX + traversal -> qa_check -> export
through Scripts/pipeline -> rocks_catalog.json (with the CC0 provenance per texture) -> Assets/Dojo/DojoRocks.blend.

    blender -b --factory-startup --python Scripts/dojo/rocks/build_rocks2.py -- [rocks...] [--no-export]
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

import stone_sdf as sd  # noqa: E402
import stone_bake as sb  # noqa: E402
import stone_weather2 as sw2  # noqa: E402
import rocks_material2 as rm2  # noqa: E402
import build_rocks as b1  # noqa: E402   (pilot 1 helpers: ucx, climb_top, pick_sites, sha256)
import stone_moss as smo  # noqa: E402   (pilot 2 fix 1: moss as shoots)
from rocks_plans2 import PLANS  # noqa: E402
from pipeline import textures  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
WORK = BUILD / "work2"
EXPORT = ROOT / "Exports" / "DojoKit" / "Rocks"
TEX = EXPORT / "Textures"
BLEND = ROOT / "Assets" / "Dojo" / "DojoRocks.blend"
TEXEL = 5.12
SHORT = {"RiverRound": "BoulderRiver01", "RiverLong": "BoulderRiver02", "CliffChunk": "Cliff01"}

WEATHER = {
    # pilot 2 fix 1: ochre from the cavity (delta 5), the grime blotches cut to a faint mottle, the crust / spots
    # contrast halved (in rocks_material2.KIND); lichen zone sparser on the cliff and up-facing only (delta 6);
    # moss as a crest band with satellites on the river rocks (delta 7)
    "RiverRound": dict(lichen=dict(amount=0.9, c_lo=0.42, c_hi=0.60), lichen_seed=dict(per_m2=55, r=(0.015, 0.04)),
                       ochre=0.95, ochre_lo=0.44, streak=0.45, grime=0.9, mott_lo=0.47, mott_hi=0.53,
                       ochre_cavity=0.9, mott_keep=0.55, lichen_mi=dict(density=0.9, bias=-0.10),
                       moss_sites=dict(spacing=0.026, max_sites=600), fresh=dict(arris=0.6)),
    "RiverLong": dict(lichen=dict(amount=0.9, c_lo=0.46, c_hi=0.64), lichen_seed=dict(per_m2=55, r=(0.015, 0.04)),
                      ochre=0.95, ochre_lo=0.44, streak=0.45, grime=0.9, mott_lo=0.47, mott_hi=0.53,
                      ochre_cavity=0.9, mott_keep=0.55, lichen_mi=dict(density=0.6, bias=-0.06),
                      moss_sites=dict(spacing=0.026, max_sites=900), fresh=dict(arris=0.6)),
    "CliffChunk": dict(lichen=dict(amount=0.55, c_lo=0.50, c_hi=0.66, nz_lo=0.15, nz_hi=0.60),
                       lichen_seed=dict(per_m2=55, r=(0.014, 0.036)),
                       ochre=0.9, ochre_lo=0.50, streak=0.75, grime=0.85, mott_lo=0.42, mott_hi=0.60,
                       ochre_cavity=0.9, mott_keep=0.55, lichen_mi=dict(density=0.6, bias=-0.12),
                       moss_sites=dict(spacing=0.03, max_sites=900), tufts=dict(count=70, min_d=0.14),
                       fresh=dict(arris=0.8, patch=1.0, lo=0.56, hi=0.64)),
}

PROVENANCE = {
    "scans": {
        "rock_surface": "https://polyhaven.com/a/rock_surface (CC0 1.0); river boulders' macro albedo + relief",
        "tiger_rock": "https://polyhaven.com/a/tiger_rock (CC0 1.0); cliff macro albedo + relief (regraded grey)",
        "granite_tile_03": "https://polyhaven.com/a/granite_tile_03 (CC0 1.0); crystal grain detail (tile "
                           "interiors only, quilted, regraded to the sheet's grain panel)",
        "mossy_rock": "https://polyhaven.com/a/mossy_rock (CC0 1.0); moss albedo (regraded)",
    },
    "source_folder": "Assets/Dojo/SourceTextures/PolyHaven/<name>/SOURCE.md (2K maps, downloaded 2026-10-01 with "
                     "the owner's approval)",
    "fab_note": "List as CC0 textures (Poly Haven), not our own work; the forms, masks, lichen and bakes are ours.",
}


def log(*a):
    print("[build2]", *a, flush=True)


def set_vec(ob, name, vals):
    me = ob.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    a = me.attributes.new(name, "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(vals, np.float32).ravel())


def set_col4(ob, name, vals):
    me = ob.data
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    c = me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    c.data.foreach_set("color", np.clip(np.asarray(vals, np.float32), -100, 100).ravel())


def float_image(name, size, fill=(0, 0, 0, 1)):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    im = bpy.data.images.new(name, size, size, alpha=True, float_buffer=True, is_data=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.tile(np.array(fill, np.float32), size * size))
    return im


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def bake_emit(ob, dense, mat, img):
    dense.data.materials.clear()
    dense.data.materials.append(mat)
    sb.bake(ob, [dense], img, "EMIT", samples=8, extrusion=0.02, ray=0.06)


def smart_uv(ob, size, texel, log=print, angle=60.0, margin=0.0015):
    """Unique UV0 by angle-based Smart UV Project + average island scale + pack, for the fractured cliff (pilot 2:
    its 2000 box-direction charts folded under ABF and never cleared the SAT overlap test). Planar projections
    cannot fold; the result is checked with the same SAT test. UV1 = the full-tile packing (Fab lightmap set),
    UV0 scaled to the house texel as stone_bake.unique_uv does."""
    from pipeline.qa_check import uv_overlap_sat
    me = ob.data
    t0 = time.time()
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers.active = me.uv_layers["UVMap"]
    for e in me.edges:
        e.use_seam = False
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # pilot 2 fix 1: the partial re-projects below shrank the packing to fill 0.04 on the jointed cliff; first try
    # whole-mesh projections at a few nearby angles and keep the first with no overlap
    for ang0 in (angle, angle + 5.0, angle - 5.0, angle + 10.0, angle - 10.0):
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(ang0), island_margin=margin, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, shape_method="CONCAVE", margin_method="ADD", margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")
        uvt = sb.uv_arrays(me, "UVMap")
        ov = int(uv_overlap_sat(uvt.reshape(-1, 3, 2)))
        log("smart uv", ang0, "overlaps", ov, round(time.time() - t0, 1), "s")
        if not ov:
            angle = ang0
            break
        bpy.ops.object.mode_set(mode="EDIT")
    if bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    if ov and len(sb.overlap_faces(uvt.reshape(-1, 3, 2))) <= 400:
        # pilot 2 fix 1: isolate the few overlapping faces (slivers in curled joint walls) instead of re-projecting
        # (which collapsed the packing to fill 0.04): the islands shrink into [0, 0.985]^2 and each bad face gets
        # its own small cell in the band u > 0.985
        bad = np.asarray(sb.overlap_faces(uvt.reshape(-1, 3, 2)), np.int64)
        band = 0.985
        uv = sb.uv_arrays(me, "UVMap") * band
        lt = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get("loop_start", lt)
        nb = len(bad)
        side = max(1, int(math.ceil(math.sqrt(nb))))
        cw = (1.0 - band) / side
        for i, f in enumerate(bad):
            cu = band + (i % side) * cw
            cv = 0.99 - (i // side + 1) * cw
            ls = lt[f]
            for j, (a, b) in enumerate(((0.15, 0.15), (0.85, 0.15), (0.5, 0.85))):
                uv[ls + j] = (cu + a * cw, cv + b * cw)
        me.uv_layers["UVMap"].data.foreach_set("uv", uv.astype(np.float32).ravel())
        uvt = sb.uv_arrays(me, "UVMap")
        ov = int(uv_overlap_sat(uvt.reshape(-1, 3, 2)))
        log("smart uv isolated", nb, "faces; overlaps", ov)
    # re-project the faces that still overlap (curled slot walls inside one 60 deg island) at smaller angles,
    # growing the selection by one ring so the new islands are not slivers, then pack everything again
    for ang in (35.0, 20.0, 10.0, 5.0):
        if not ov:
            break
        bad = sb.overlap_faces(uvt.reshape(-1, 3, 2))
        sel = np.zeros(len(me.polygons), bool)
        sel[np.asarray(bad, np.int64)] = True
        me.polygons.foreach_set("select", sel)
        me.update()
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_more()
        bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=margin, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, shape_method="CONCAVE", margin_method="ADD", margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")
        uvt = sb.uv_arrays(me, "UVMap")
        ov = int(uv_overlap_sat(uvt.reshape(-1, 3, 2)))
        log("smart uv re-project", ang, "faces", int(sel.sum()), "overlaps", ov, round(time.time() - t0, 1), "s")
    if ov:
        raise RuntimeError(f"{ob.name} UV0 overlaps after smart project: {ov}")
    me.uv_layers.new(name="UV1", do_init=True)
    uv = sb.uv_arrays(me, "UVMap")
    a_uv = sb.uv_area(me, uv)
    a_m = float(sum(p.area for p in me.polygons))
    target = (texel * 100.0 / size) ** 2 * a_m
    k = min(1.0, math.sqrt(target / max(a_uv, 1e-9)))
    me.uv_layers["UVMap"].data.foreach_set("uv", (uv * k).ravel())
    me.uv_layers.active = me.uv_layers["UVMap"]
    S = math.sqrt(a_m / (a_uv * k * k))
    return {"method": "smart_project", "angle_deg": angle, "uv0_scale_k": round(k, 4),
            "uv0_fill_packed": round(a_uv, 4), "texel_px_cm": round(math.sqrt(a_uv * k * k / a_m) * size / 100.0, 3),
            "m_per_uv0": round(S, 4), "uv_seconds": round(time.time() - t0, 1)}


def attach_shoots(ob, items, uvi, strip=0.985):
    """Pilot 2 fix 1: join the foliage strips (moss shoots, grass blades) after the unwrap and bakes. The rock's
    UV0 / UV1 shrink uniformly into [0, strip]^2 and every strip gets its own tiny non-overlapping cell in the
    reserved band (u > strip): their materials read vertex colour only, so their texels are unused; QA's overlap /
    tile tests stay clean (curved blades projected by smart UV folded onto themselves: 5-8 SAT overlaps that the
    partial re-projects could only clear by wrecking the packing). items: [(V, F, C, material index, verts per
    strip)]."""
    me = ob.data
    for lname in ("UVMap", "UV1"):
        uv = sb.uv_arrays(me, lname)
        me.uv_layers[lname].data.foreach_set("uv", (uv * strip).ravel())
    uvi["m_per_uv0"] = round(uvi["m_per_uv0"] / strip, 4)
    uvi["uv_strip_for_foliage"] = strip
    n_total = sum(len(V) // vp for V, F, C, mi, vp in items)
    side = int(math.ceil(math.sqrt(n_total * (1.0 - strip)))) + 1
    cw = (1.0 - strip) / side
    rows = int(math.ceil(n_total / side))
    ch = min(cw, 1.0 / max(rows, 1))
    k0 = 0
    n_main = len(me.polygons)
    mats = []
    for V, F, C, mi, vp in items:
        sh = sb.make_obj("__foliage", V, F)
        shm = sh.data
        shm.uv_layers.new(name="UVMap")
        shm.uv_layers.new(name="UV1")
        loops_v = np.empty(len(shm.loops), np.int64)
        shm.loops.foreach_get("vertex_index", loops_v)
        k = loops_v // vp + k0
        j = loops_v % vp
        cu = strip + (k % side) * cw
        cv = (k // side) * ch
        u = cu + (0.15 + 0.7 * (j % 2)) * cw
        v = cv + (0.1 + 0.8 * (j // 2) / max(vp // 2 - 1, 1)) * ch
        uvs = np.column_stack([u, v]).astype(np.float32)
        for lname in ("UVMap", "UV1"):
            shm.uv_layers[lname].data.foreach_set("uv", uvs.ravel())
        sb.set_point_colour(sh, "Col", C)
        k0 += len(V) // vp
        mats.append((len(F), mi))
        bpy.ops.object.select_all(action="DESELECT")
        sh.select_set(True)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.join()
    mi_arr = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi_arr)
    while len(me.materials) < 4:
        me.materials.append(bpy.data.materials.new(f"__bake_slot{len(me.materials)}"))
    o = n_main
    for nf, mi in mats:
        mi_arr[o:o + nf] = mi
        o += nf
    me.polygons.foreach_set("material_index", mi_arr)
    me.update()
    log(ob.name, "foliage attached", n_total, "strips,", sum(m[0] for m in mats), "tris; UV band", strip,
        "cells", side, "x", rows)


def build_rock(name):
    plan = PLANS[name]
    short = SHORT[name]
    kind = plan["kind"]
    rng = np.random.default_rng(plan["seed"] + 900)
    t0 = time.time()
    prefix = plan["prefix"]
    b1.clear_rock(prefix)
    d = np.load(WORK / f"{name}_dense.npz", allow_pickle=True)
    V, F = d["V"].astype(float), d["F"].astype(np.int64)
    paths = [np.asarray(p, float) for p in d["paths"] if len(p) > 1]
    E = sd.edges_of(F)
    N = sd.vertex_normals(V, F)
    H = sd.mean_curvature(V, F, E, N, n_smooth=3)
    params = dict(WEATHER[name])
    params["wet"] = plan.get("wet")
    params["moss"] = plan["moss"]
    params["damp_h"] = plan.get("damp_h", 0.35)
    H0 = sd.mean_curvature(V, F, E, N, n_smooth=0)
    Mk, Mk2, fields = sw2.masks(V, F, N, H, kind, params, plan["seed"] + 77, paths, H_fine=H0)
    shares = sw2.shares(Mk, V, F)
    log(name, "masks", shares, round(time.time() - t0, 1), "s")
    ls = params["lichen_seed"]
    Lc, Lp, n_ros = sw2.lichen_fields(V, N, Mk[:, 1], plan["seed"] + 31, per_m2=ls["per_m2"],
                                      r=ls.get("r", (0.012, 0.03)), min_gap=ls.get("min_gap", 0.75), F=F)
    log(name, "lichen rosettes", n_ros, round(time.time() - t0, 1), "s")
    dense = sb.make_obj(f"__{name}_Dense", V, F)
    set_col4(dense, "Mk", Mk)
    set_col4(dense, "Mk2", Mk2 if Mk2.shape[1] == 4 else np.concatenate([Mk2, np.ones((len(V), 1))], 1))
    set_vec(dense, "Lc", Lc)
    set_col4(dense, "Lp", Lp)
    # ---- the shipped mid
    mid0 = sb.make_obj(f"__{name}_Mid", V, F)
    sb.remesh(mid0, plan["mid_voxel"])
    Vm, Fm = sb.mesh_arrays(mid0)
    me0 = mid0.data
    bpy.data.objects.remove(mid0)
    bpy.data.meshes.remove(me0)
    near, dist = sd.kd_nearest(V, Vm)
    moss_m = fields["moss_top"][near]
    log(name, "mid", len(Fm), "tris; mid-to-dense p95", round(float(np.percentile(dist, 95)) * 1000, 2), "mm")
    parts = [(Vm, Fm, 0)]
    shell = sb.cushion_shell(Vm, Fm, moss_m, plan["seed"] + 5)
    if shell is not None:
        parts.append((shell[0], shell[1], 1))
    tufts = None
    if kind == "cliff":
        Nm = sd.vertex_normals(Vm, Fm)
        led_m = fields["ledge"][near]
        tp = params.get("tufts", dict(count=40, min_d=0.20))
        # pilot 2 fix 1 (delta 3, checked: on the sheet's row 4 tufts sit on every ledge): grass on the benches
        w = ((moss_m > 0.3) | (led_m > 0.4)) & (Nm[:, 2] > 0.6) & (led_m > 0.25)
        sites, nrm = b1.pick_sites(Vm, Nm, w.astype(float), tp["count"], tp["min_d"], rng)
        tufts = sb.grass_tufts(sites, nrm, plan["seed"] + 9, blades=(14, 30), height=(0.05, 0.20), spread=0.045)
        # attached after the unwrap and bakes (attach_shoots), like the moss shoots
    # moss shoots on the cushions (pilot 2 fix 1, delta 7)
    shoots = None
    ms = params.get("moss_sites")
    if ms:
        Nm = sd.vertex_normals(Vm, Fm)
        mfield = fields["moss"][near]
        st, sn, sw = smo.pick_sites(Vm, Nm, mfield, ms["spacing"], rng, max_sites=ms["max_sites"])
        if shell is not None and len(st):
            # stand the shoots on the shell surface (lift by the local shell height ~ 1-2 cm max)
            st = st + sn * 0.006
        shoots = smo.moss_cushions(st, sn, sw, plan["seed"] + 21, shoots=(26, 44), height=(0.012, 0.032),
                                   radius=(0.014, 0.028))
        # attached AFTER the unwrap and the bakes (attach_shoots): 10k tiny strips would take the rock's UV room
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
    col = np.ones((len(V_all), 3))
    o2 = 0
    for (Vp, Fp, mi) in parts:
        if mi == 2 and tufts is not None:
            col[o2:o2 + len(Vp)] = tufts[2]
        if mi == 3 and shoots is not None:
            col[o2:o2 + len(Vp)] = shoots[2]
        o2 += len(Vp)
    sb.set_point_colour(ob, "Col", col)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me)
    bm.free()
    me.update()
    size = int(plan["map"])
    if plan.get("uv") == "smart":
        uvi = smart_uv(ob, size, TEXEL, log=lambda *a: log(name, *a), angle=plan.get("uv_angle", 45.0), margin=0.0008)
    else:
        sb.CHART_DIRS = sb.DIR26 if plan.get("uv") == "charts26" else None
        uvi = sb.unique_uv(ob, size, TEXEL, log=lambda *a: log(name, *a))
        uvi["chart_dirs"] = 26 if plan.get("uv") == "charts26" else 6
    log(name, "uv", uvi)
    # ---- bakes
    hidden = [o for o in bpy.data.objects if o not in (ob, dense) and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    tb = time.time()
    img_n = sb.new_image(f"__{short}_N_gl", size, (0.5, 0.5, 1.0, 1.0))
    sb.bake(ob, [dense], img_n, "NORMAL", extrusion=0.02, ray=0.06)
    img_bc = float_image(f"__{short}_BC_lin", size, (0.2, 0.2, 0.2, 1.0))
    bake_emit(ob, dense, rm2.composite_material(f"__comp_bc_{short}", kind, mode="BC"), img_bc)
    img_m = float_image(f"__{short}_M", size)
    bake_emit(ob, dense, rm2.composite_material(f"__comp_m_{short}", kind, mode="MASK"), img_m)
    img_f = float_image(f"__{short}_F", size, (0.3, 0.3, 0.3, 1.0))
    bake_emit(ob, dense, rm2.composite_material(f"__comp_f_{short}", kind, mode="FRESH"), img_f)
    img_r = float_image(f"__{short}_R", size, (0.8, 0.8, 0.8, 1.0))
    bake_emit(ob, dense, rm2.composite_material(f"__comp_r_{short}", kind, mode="ROUGH"), img_r)
    dense.hide_render = True
    sb.gpu(bpy.context.scene)
    ao = textures.bake_ao(ob, f"__{short}_ao", size=size, samples=96, margin=16)
    t_bake = round(time.time() - tb, 1)
    for o in hidden:
        o.hide_render = False
    TEX.mkdir(parents=True, exist_ok=True)
    gl = WORK / f"T_DKR_{short}_N_gl.png"
    textures.write_png(sb.image_px(img_n), gl)
    n_path = TEX / f"T_DKR_{short}_N.png"
    textures.flip_normal_green(gl, n_path)
    bc = sb.image_px(img_bc)
    bc_s = np.concatenate([lin_to_srgb(bc[..., :3]), np.ones(bc.shape[:2] + (1,), np.float32)], -1)
    bc_path = TEX / f"T_DKR_{short}_BC.png"
    textures.write_png(bc_s.astype(np.float32), bc_path)
    mpx = sb.image_px(img_m)
    mpx[..., 3] = np.clip(sb.image_px(img_f)[..., 0], 0, 1)        # M.A = grain weight (fresh), pilot 2 fix 1
    m_path = TEX / f"T_DKR_{short}_M.png"
    textures.write_png(np.clip(mpx, 0, 1), m_path)
    rough = bpy.data.images.new(f"__{short}_rough", size, size, alpha=False, float_buffer=False, is_data=True)
    rp = sb.image_px(img_r).copy()
    rp[..., 1] = rp[..., 2] = rp[..., 0]
    rp[..., 3] = 1.0
    rough.pixels.foreach_set(np.clip(rp, 0, 1).ravel())
    orm_path = TEX / f"T_DKR_{short}_ORM.png"
    textures.pack_orm(ao, rough, None, orm_path)
    aopx = sb.image_px(ao)[..., 0]
    bc_stats = {"p5_p50_p95_srgb_luma": [round(float(x), 4) for x in np.percentile(
        (0.2126 * bc_s[..., 0] + 0.7152 * bc_s[..., 1] + 0.0722 * bc_s[..., 2])[bc[..., 3] > 0.5], (5, 50, 95))]}
    for im in (img_n, img_bc, img_m, img_f, img_r, ao, rough):
        bpy.data.images.remove(im)
    fol = []
    if tufts is not None:
        fol.append((tufts[0], tufts[1], tufts[2], 2, 8))
    if shoots is not None:
        fol.append((shoots[0], shoots[1], shoots[2], 3, 6))
    if fol:
        attach_shoots(ob, fol, uvi)
    # ---- materials
    maps = {"BC": bc_path, "N": n_path, "ORM": orm_path, "M": m_path}
    lich = dict(rm2.LICHEN, **params.get("lichen_mi", {}))
    slots = [rm2.rock_material(f"MI_DKR_{short}", maps, uvi["m_per_uv0"], rm2.KIND[kind]["grain"], lichen=lich),
             rm2.moss_material(), rm2.grass_material(), rm2.moss_strand_material()]
    mi_keep = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi_keep)
    old = list(me.materials)
    me.materials.clear()
    for m in slots:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mi_keep)
    me.update()
    for m in old:
        if m is not None and m.users == 0:
            bpy.data.materials.remove(m)
    # ---- collision + traversal (study 4.13), as pilot 1
    rock_V = Vm
    above = rock_V[rock_V[:, 2] > -0.06]
    hulls, trav, climb = [], None, None
    if kind == "river":
        zt, ext, sag = b1.climb_top(rock_V)
        xs = np.linspace(above[:, 0].min(), above[:, 0].max(), 4)
        for k in range(3):
            a, b = xs[k] - 0.05, xs[k + 1] + 0.05
            P = above[(above[:, 0] >= a) & (above[:, 0] <= b)].copy()
            if zt is not None:
                P[:, 2] = np.minimum(P[:, 2], zt)
            hulls.append(b1.ucx(ob, P, k))
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
        xs = np.linspace(above[:, 0].min(), above[:, 0].max(), 6)
        for k in range(5):
            P = above[(above[:, 0] >= xs[k] - 0.04) & (above[:, 0] <= xs[k + 1] + 0.04)]
            if len(P) > 20:
                hulls.append(b1.ucx(ob, P, len(hulls)))
        climb = {"climbable": False, "reason": "3.08 m top exceeds the 2.75 m mantle limit; faces steeper than "
                                               "44.77 deg; no marker (study 4.13 item 2)"}
    pf, _ = sb.plane_fraction(V, F, k=6)
    up = V[:, 2] > 0
    info = {
        "rock": name, "object": prefix, "short": short, "sheet": plan["sheet"],
        "method": "pilot 2: corestone" if kind == "river" else "pilot 2: sheared-mass fracture",
        "size_above_grade_m": {"L": round(float(np.ptp(V[up, 0])), 3), "D": round(float(np.ptp(V[up, 1])), 3),
                               "H": round(float(V[:, 2].max()), 3)},
        "buried_skirt_m": round(float(-V[:, 2].min()), 3),
        "tris": int(len(me.polygons)), "tris_before_foliage": int(len(F_all)), "rock_tris": int(len(Fm)),
        "verts": int(len(me.vertices)),
        "foliage_tris": {"grass": int(len(tufts[1])) if tufts is not None else 0,
                         "moss_shoots": int(len(shoots[1])) if shoots is not None else 0},
        "verts_per_tri": round(len(me.vertices) / max(len(me.polygons), 1), 3),
        "moss_shell_tris": int(len(shell[1])) if shell is not None else 0,
        "grass_tris": int(len(tufts[1])) if tufts is not None else 0,
        "dense_tris": int(len(F)), "mid_voxel_m": plan["mid_voxel"],
        "mid_to_dense_mm_p50_p95": [round(float(np.percentile(dist, q)) * 1000, 2) for q in (50, 95)],
        "uv": uvi, "map_px": size, "bake_s": t_bake, "bc": bc_stats,
        "ao_p50": round(float(np.median(aopx[aopx > 0.02])), 3),
        "mask_shares_dense": shares, "lichen_rosettes": int(n_ros),
        "sg14": {"plane_fraction_k6_15deg_dense": round(pf, 3),
                 "sharp_crease_share_30deg": round(sb.crease_share(V, F), 4),
                 "arris_radius_m_p25_p50_p75": sb.arris_radius(V, F, H), "cracks": len(paths)},
        "collision": {"kind": "UCX convex", "count": len(hulls), "climb": climb, "traversal": trav},
        "maps": {k: str(Path(v).relative_to(ROOT)) for k, v in maps.items()},
        "detail_maps": {"grain_BC": "Exports/DojoKit/Rocks/Textures/T_DKR_GraniteGrain_BC.png",
                        "grain_N": "Exports/DojoKit/Rocks/Textures/T_DKR_GraniteGrain_N.png",
                        "grain_tile_m": rm2.GRAIN_TILE_M, "grain_params": rm2.GRAIN,
                        "moss_BC": "Exports/DojoKit/Rocks/Textures/T_DKR_MossDetail_BC.png"},
        "provenance": {"BC": ("baked from " + ("rock_surface" if kind == "river" else "tiger_rock") +
                              " (CC0, regraded) + mossy_rock (CC0) + our masks / lichen"),
                       "N": "baked from our dense mesh (scan relief of " +
                            ("rock_surface" if kind == "river" else "tiger_rock") + " applied as geometry)",
                       "ORM": "our AO bake + baked roughness", "M": "ours",
                       "GraniteGrain": "granite_tile_03 (CC0)", "MossDetail": "mossy_rock (CC0)"},
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
    if catalog.get("pilot") != 2:
        catalog = {"pilot": 2, "rocks": {}, "pilot1_backup": "WorkFiles/dojo/build/rocks/pilot/rocks_catalog.json"}
    built = {}
    for n in names:
        built[n] = build_rock(n)
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
    qa_path = BUILD / "qa_report.json"
    prev = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else {}
    res = prev.get("results", {}) if prev.get("pilot") == 2 else {}
    res.update(qa)
    qa_path.write_text(json.dumps({"pilot": 2, "waivers": [], "results": res}, indent=1), encoding="utf-8")
    exp = {}
    if not no_export:
        EXPORT.mkdir(parents=True, exist_ok=True)
        ex_path = BUILD / "export_report.json"
        prev = json.loads(ex_path.read_text(encoding="utf-8")) if ex_path.exists() else {}
        exp = prev.get("files", {}) if prev.get("pilot") == 2 else {}
        for n, (ob, info) in built.items():
            if not qa[n]["passed"]:
                log("QA FAILED, not exported:", n)
                continue
            path = EXPORT / f"{ob.name}.fbx"
            r = export_fbx(str(path), [ob], kind="static")
            exp[ob.name] = {"file": str(path.relative_to(ROOT)), "sha256": b1.sha256(path),
                            "bytes": path.stat().st_size, "warnings": r.get("warnings", []),
                            "objects": [x if isinstance(x, str) else getattr(x, "name", str(x))
                                        for x in r.get("objects", [])]}
            info["export"] = exp[ob.name]
        for f in sorted(TEX.glob("T_DKR_*.png")):
            exp[f.name] = {"file": str(f.relative_to(ROOT)), "sha256": b1.sha256(f), "bytes": f.stat().st_size}
        ex_path.write_text(json.dumps({"pilot": 2, "pipeline": "Scripts/pipeline/export_fbx.py kind=static",
                                       "files": exp}, indent=1), encoding="utf-8")
    for n, (ob, info) in built.items():
        info["qa"] = {"passed": qa[n]["passed"], "hard_fails": qa[n]["hard_fails"], "texel": qa[n]["texel"]}
        catalog["rocks"][n] = info
    catalog["provenance"] = PROVENANCE
    catalog["unreal_material"] = ("M_ST_RockUnique (not built yet): BaseColor = T_<Rock>_BC x lerp(1, (GrainBC / "
                                  "GrainMean)^GrainContrast, GrainAmount x (1 - max(M.R, M.G))); Normal = "
                                  "BlendAngleCorrectedNormals(T_<Rock>_N, GrainN); Roughness = ORM.G; AO = ORM.R; "
                                  "M = R moss, G lichen, B wet; params in rocks_material2.GRAIN")
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
