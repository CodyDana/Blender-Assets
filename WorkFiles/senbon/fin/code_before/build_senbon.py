#!/usr/bin/env python
"""Build the senbon set: SM_Senbon_Needle (130 mm, double-pointed) and SM_Senbon_Heavy (170 mm, three-facet point,
thread-wrapped tail), to WorkFiles/senbon/senbon_spec.json + SENBON_DESIGN_SHEET.png (the Study) and
SENBON_BUILD_PLAN.md (frame, sockets, collision, LODs, maps).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_senbon.py -- [--stages mesh,textures,save,qa,export,render,report] [--quick]
        [--dev-dir DIR]

HOW IT IS MADE
--------------
props_lib.senbon_spec     the numbers (read from the Study's spec; BUILD choices marked)
props_lib.senbon_geom     every LOD analytically: revolved profiles at the LOD's side count, the heavy point's round
                          lands + three planar facets, analytic per-corner normals, the same UV function on every LOD
props_lib.senbon_paint    island layout + the numpy painter (finish in real mm on the real surface)
props_lib.senbon_gallery  renders from the BAKED maps only + the design compare sheet

WHAT IT NEVER TOUCHES: the frozen items (Exports/Shuriken, Scripts/shuriken, the other props), Scripts/pipeline/**
(used as it is), Scripts/unreal/materials/** (recolour_common is loaded read-only without bytecode).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))

import bmesh                                                       # noqa: E402
import bpy                                                         # noqa: E402
import numpy as np                                                 # noqa: E402
from mathutils import Matrix, Vector                               # noqa: E402
from mathutils.bvhtree import BVHTree                              # noqa: E402

from pipeline.export_fbx import export_fbx                         # noqa: E402
from pipeline.helpers import make_lod_group, make_socket           # noqa: E402
from pipeline.qa_check import qa_check                             # noqa: E402
from props_lib import bake as PB                                   # noqa: E402
from props_lib import senbon_geom as G                             # noqa: E402
from props_lib import senbon_paint as P                            # noqa: E402
from props_lib import senbon_spec as S                             # noqa: E402
from props_lib.spec import scaled_lod_screen_sizes, screen_size_distance_m   # noqa: E402

LIB_VERSION = "1.0.0"
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "Senbon"
TEXTURES = EXPORTS / "Textures"
RECOLOUR = TEXTURES / "Recolour"
RENDERS = PROJECT / "Renders" / "Senbon"
WORK = PROJECT / "WorkFiles" / "senbon"
BUILD_WORK = WORK / "build"
ALL_STAGES = ("mesh", "textures", "save", "qa", "export", "render", "report")
MM = 0.001
T0 = time.time()


def log(*a):
    print(f"[senbon {time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def r6(x):
    return round(float(x), 6)


# =========================================================================== frozen
def frozen_hashes() -> dict:
    pre = WORK / "regression" / "pre_build" / "SHA256SUMS.txt"
    ok, bad = 0, []
    for line in pre.read_text(encoding="utf8").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        h, rel = parts[0], parts[1].lstrip("*").strip()
        p = PROJECT / rel
        if p.is_file() and sha256(p) == h:
            ok += 1
        else:
            bad.append(rel)
    return {"baseline": str(pre.relative_to(PROJECT)), "identical": ok, "differing_or_missing": bad}


# =========================================================================== mesh -> blender
def make_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def to_blender(mb, name, islands, mats, shift_x_mm=0.0):
    V, T, N, UV, slot, part, isl = mb.arrays()
    verts = (V - np.array([shift_x_mm, 0.0, 0.0])) * MM
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(int(i) for i in t) for t in T])
    me.update()
    assert len(me.polygons) == len(T)
    uvl = me.uv_layers.new(name="UVMap")
    uv = np.zeros((len(T), 3, 2))
    for k in range(len(T)):
        il = islands[isl[k]]
        u, v = P.to_uv(il, UV[k, :, 0], UV[k, :, 1])
        uv[k, :, 0] = u + (1.0 if il.tex == "wrap" else 0.0)
        uv[k, :, 1] = v
    # from_pydata keeps the face vertex order: loop 3k + j is corner j of triangle k
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    assert (lv.reshape(-1, 3) == T).all()
    uvl.data.foreach_set("uv", uv.reshape(-1).astype(np.float32))
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", slot.astype(np.int32))
    me.shade_smooth()
    me.normals_split_custom_set([tuple(n) for n in N.reshape(-1, 3)])
    # part attribute (renders / measurements)
    names = sorted(set(part))
    a = me.attributes.new("sb_part", "INT", "FACE")
    a.data.foreach_set("value", np.array([names.index(p) for p in part], np.int32))
    me["sb_part_names"] = names
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# =========================================================================== stage: mesh
def stage_mesh(report):
    out = {}
    nb = [G.build_needle(l) for l in range(3)]
    hb = [G.build_heavy(l) for l in range(3)]
    ext = P.island_extents(nb + hb)
    lay = {}
    lay.update(P.layout_needle(ext))
    lay.update(P.layout_heavy(ext))
    lay.update(P.layout_wrap(ext))
    mass_n = G.needle_round_mass()
    mass_h = G.heavy_round_mass()
    com_h = mass_h["com_from_butt_mm"]
    mats = {"needle": [make_material(S.MAT_NEEDLE_STEEL)],
            "heavy": [make_material(S.MAT_HEAVY_STEEL), make_material(S.MAT_HEAVY_WRAP)]}
    out["needle"] = [to_blender(mb, f"{S.NEEDLE_MESH}_LOD{l}", lay, mats["needle"], 0.0) for l, mb in enumerate(nb)]
    out["heavy"] = [to_blender(mb, f"{S.HEAVY_MESH}_LOD{l}", lay, mats["heavy"], com_h) for l, mb in enumerate(hb)]
    report["layout"] = {k: {"texture": v.tex, "kind": v.kind, "U_mm": [r6(v.Umin), r6(v.Umax)],
                            "V_mm": [r6(v.Vmin), r6(v.Vmax)], "u0_px": round(v.u0, 3), "vc_px": round(v.vc, 3)}
                        for k, v in lay.items()}
    report["mass_model"] = {
        "needle": {"round_volume_mm3": r6(mass_n[0]), "round_com_x_mm": r6(mass_n[1]),
                   "mass_g": r6(mass_n[0] * S.STEEL_DENSITY_G_MM3),
                   "derived_mass_g": S.SPEC["derived"]["SM_Senbon_Needle"]["mass_g"]},
        "heavy": {k: r6(v) for k, v in mass_h.items()},
        "method": "as-built profile stations with a ROUND section (frustum sums / the Study's facet area law); "
                  "the mesh is the inscribed 12-gon of that section (see mesh_volume)"}
    report["mass_model"]["heavy"]["derived_mass_g"] = S.SPEC["derived"]["SM_Senbon_Heavy"]["mass_g"]
    report["mass_model"]["heavy"]["derived_com_from_butt_mm"] = S.SPEC["derived"]["SM_Senbon_Heavy"]["com_from_butt_mm"]
    return out, {"needle": nb, "heavy": hb}, lay, mats, {"needle_com_mm": 0.0, "heavy_com_mm": com_h,
                                                          "needle_mass_g": mass_n[0] * S.STEEL_DENSITY_G_MM3,
                                                          "heavy_mass_g": mass_h["mass_g"]}


# =========================================================================== stage: textures
def _gpu(scene):
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in pr.devices) else "CPU"
    except Exception:
        scene.cycles.device = "CPU"
    return scene.cycles.device


def bake_ao(obj, targets, samples=64, distance_m=0.004):
    """Cycles AO of LOD0 ALONE into one float image per material (non-square sizes).  The wrap's UV tile (u 1..2)
    is moved back to 0..1 on a temporary UV layer for the bake (blackhat convention)."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    dev = _gpu(scene)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("W_AO")
    scene.world.light_settings.distance = distance_m
    me = obj.data
    src = me.uv_layers["UVMap"]
    tmp = me.uv_layers.new(name="__bake")
    uv = np.empty(len(me.loops) * 2, np.float32)
    src.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    uv[:, 0] = np.where(uv[:, 0] > 1.0 + 1e-6, uv[:, 0] - 1.0, uv[:, 0])
    tmp.data.foreach_set("uv", uv.reshape(-1))
    me.uv_layers.active = tmp
    hidden = [(o, o.hide_render) for o in bpy.data.objects if o is not obj]
    imgs, nodes = {}, []
    try:
        for o, _w in hidden:
            o.hide_render = True
        for mat, (w, h) in targets.items():
            img = bpy.data.images.new(f"__ao_{mat.name}", width=w, height=h, alpha=False, float_buffer=True,
                                      is_data=True)
            imgs[mat.name] = img
            nt = mat.node_tree
            nd = nt.nodes.new("ShaderNodeTexImage")
            nd.image = img
            for other in nt.nodes:
                other.select = False
            nd.select = True
            nt.nodes.active = nd
            nodes.append((mat, nd))
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        sc = scene.render.bake
        sc.margin = 16
        sc.margin_type = "EXTEND"
        res = bpy.ops.object.bake(type="AO", margin=16, margin_type="EXTEND", use_clear=True,
                                  use_selected_to_active=False)
        if "FINISHED" not in res:
            raise RuntimeError(f"AO bake failed: {res}")
        out = {}
        for name, img in imgs.items():
            w, h = img.size
            px = np.empty(w * h * 4, np.float32)
            img.pixels.foreach_get(px)
            out[name] = px.reshape(h, w, 4)[..., 0].copy()            # bottom-up
    finally:
        for o, w in hidden:
            o.hide_render = w
        for mat, nd in nodes:
            mat.node_tree.nodes.remove(nd)
        for img in imgs.values():
            bpy.data.images.remove(img)
        me.uv_layers.active = src
        me.uv_layers.remove(me.uv_layers["__bake"])
    return out, dev


def uv_tris_px(objs_lod0, tex_key, islands):
    """LOD0..2 UV triangles of one texture, in its px (for the coverage raster)."""
    t = P.tex_of(tex_key)
    tris = []
    for o in objs_lod0:
        me = o.data
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["UVMap"].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 3, 2).astype(np.float64)
        mi = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", mi)
        for k in range(len(uv)):
            is_wrap = uv[k, :, 0].min() > 1.0 - 1e-9
            if (tex_key == "wrap") != is_wrap:
                continue
            q = uv[k].copy()
            if is_wrap:
                q[:, 0] -= 1.0
            tris.append(q * np.array(t.size, float))
    return tris


def write_set(stem, maps, ao, cover, report_key, tex_rep):
    TEXTURES.mkdir(parents=True, exist_ok=True)
    flip = lambda a: np.ascontiguousarray(a[::-1])
    ao_f = np.where(cover, ao, np.nan)
    fill = float(np.nanmean(ao_f))
    ao2, k = P.grow(np.where(cover, ao, 0).astype(np.float32), cover, 16)
    ao2[~k] = fill
    bc = PB.linear_to_srgb(np.clip(maps["albedo"], 0, 1))
    orm = np.stack([np.clip(ao2, 0, 1), np.clip(maps["rough"], 0.02, 1.0), maps["metal"]], -1)
    n = maps["N"] * 0.5 + 0.5
    n_dx = n.copy()
    n_dx[..., 1] = 1.0 - n_dx[..., 1]                     # DirectX: green flipped on write
    paths = {"BC": PB.write_png(TEXTURES / f"{stem}_BC.png", flip(bc)),
             "ORM": PB.write_png(TEXTURES / f"{stem}_ORM.png", flip(orm)),
             "N": PB.write_png(TEXTURES / f"{stem}_N.png", flip(n_dx))}
    tilt = np.degrees(np.arccos(np.clip(maps["N"][..., 2], -1, 1)))
    tex_rep[report_key] = {
        "maps": {k: str(Path(v).relative_to(PROJECT)).replace("\\", "/") for k, v in paths.items()},
        "sha256": {k: sha256(v) for k, v in paths.items()},
        "size": [int(maps["albedo"].shape[1]), int(maps["albedo"].shape[0])],
        "power_of_two": all((x & (x - 1)) == 0 for x in maps["albedo"].shape[:2]),
        "colour_chunks": {k: [c for c in PB.png_chunks(v) if c in ("sRGB", "gAMA", "cHRM", "iCCP")]
                          for k, v in paths.items()},
        "covered_fraction": round(float(cover.mean()), 4),
        "ao_covered": {"mean": round(float(ao[cover].mean()), 4), "min": round(float(ao[cover].min()), 4),
                       "p01": round(float(np.percentile(ao[cover], 1)), 4), "unused_fill": round(fill, 4)},
        "roughness_covered": {"mean": round(float(maps["rough"][cover].mean()), 4),
                              "p01": round(float(np.percentile(maps["rough"][cover], 1)), 4),
                              "p99": round(float(np.percentile(maps["rough"][cover], 99)), 4)},
        "albedo_covered_mean_linear": [round(float(x), 5) for x in maps["albedo"][cover].mean(axis=0)],
        "normal_tilt_deg_covered": {"mean": round(float(tilt[cover].mean()), 4),
                                    "p99": round(float(np.percentile(tilt[cover], 99)), 4),
                                    "max": round(float(tilt[cover].max()), 4)},
        "stats": maps.get("stats", {})}
    return paths


def stage_textures(objs, lay, mats, report, quick=False):
    tex_rep = {}
    paths = {}
    # needle
    n0 = objs["needle"][0]
    ao, dev = bake_ao(n0, {mats["needle"][0]: S.NEEDLE_TEX.size}, samples=16 if quick else 64)
    report["bake_device"] = dev
    cov = P.raster_cover((S.NEEDLE_TEX.size[1], S.NEEDLE_TEX.size[0]), uv_tris_px(objs["needle"], "needle", lay))
    m = P.paint_needle(lay["needle"])
    m = P.finish_maps(m, cov, S.NEEDLE_TEX, 1.0)
    paths["needle"] = write_set(S.NEEDLE_TEX.stem, m, ao[S.MAT_NEEDLE_STEEL], cov, "needle", tex_rep)
    log("needle maps written")
    # heavy steel + wrap
    h0 = objs["heavy"][0]
    ao, _ = bake_ao(h0, {mats["heavy"][0]: S.HEAVY_TEX.size, mats["heavy"][1]: S.WRAP_TEX.size},
                    samples=16 if quick else 64)
    hl = {k: v for k, v in lay.items() if v.tex == "heavy"}
    cov = P.raster_cover((S.HEAVY_TEX.size[1], S.HEAVY_TEX.size[0]), uv_tris_px(objs["heavy"], "heavy", lay))
    m = P.paint_heavy_steel(hl)
    m = P.finish_maps(m, cov, S.HEAVY_TEX, 1.0)
    paths["heavy"] = write_set(S.HEAVY_TEX.stem, m, ao[S.MAT_HEAVY_STEEL], cov, "heavy", tex_rep)
    covw = P.raster_cover((S.WRAP_TEX.size[1], S.WRAP_TEX.size[0]), uv_tris_px(objs["heavy"], "wrap", lay))
    mw = P.paint_wrap(lay["wrap"])
    mw = P.finish_maps(mw, covw, S.WRAP_TEX, 0.0)
    mw = P.normalise_wrap(mw)
    paths["wrap"] = write_set(S.WRAP_TEX.stem, mw, ao[S.MAT_HEAVY_WRAP], covw, "wrap", tex_rep)
    log("heavy + wrap maps written")
    report["textures"] = tex_rep
    return paths, {"wrap": mw}


def stage_recolour(maps_w, paths, report):
    """Detail16 (lossless 16-bit linear copy of the wrap's sRGB detail) + recolour_maps.json (flashbang / fan
    convention; recolour_constants.json is the finaliser's, under the materials lock)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        "np_recolour_common_ro", str(PROJECT / "Scripts/unreal/materials/maps/recolour_common.py"))
    rc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(rc)
    RECOLOUR.mkdir(parents=True, exist_ok=True)
    alb = maps_w["albedo"]
    cover = maps_w["cover"]
    lum = alb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    colour = alb[cover].mean(axis=0)
    a_lo, a_hi = float(np.percentile(lum[cover], 0.05)), float(np.percentile(lum[cover], 99.95))
    d = np.clip((lum - a_lo) / max(a_hi - a_lo, 1e-6), 0, 1)
    ext = P.grow(np.where(cover, d, 0.0).astype(np.float32), cover, 3)[0]
    ext_mask = P.grow(cover.astype(np.float32), cover, 3)[1]
    d_mean = float(d[cover].mean())
    fill = round(float(PB.linear_to_srgb(np.array([d_mean]))[0]) * 255.0) / 255.0
    det8 = np.where(ext_mask, PB.linear_to_srgb(np.clip(ext, 0, 1)), fill)
    det8 = np.rint(det8 * 255.0) / 255.0
    src8 = PB.write_png(BUILD_WORK / f"{S.WRAP_TEX.stem}_Detail_source8.png", np.ascontiguousarray(det8[::-1]))
    lev = np.rint(det8 * 255.0).astype(np.int64)
    dec = rc.s2l(lev / 255.0)
    d16 = np.rint(dec * 65535.0) / 65535.0
    name = f"{S.WRAP_TEX.stem}_Detail16"
    p16 = PB.write_png(RECOLOUR / f"{name}.png", np.ascontiguousarray(d16[::-1]), bits=16)
    back8 = np.rint(rc.l2s(np.rint(dec * 65535.0) / 65535.0) * 255.0).astype(np.int64)
    lossless = bool((back8 == lev).all())
    lum_c = float(colour @ rc.LUM)
    bias = a_lo / lum_c
    scale = (a_hi - a_lo) / lum_c
    n = bias + scale * dec[cover]
    kc = rc.fabric_constants(n)
    rel = lambda p: str(Path(p).relative_to(PROJECT)).replace("\\", "/")
    out = {"schema": "ninjapack.recolour_maps/1", "item": "Senbon", "generated": time.strftime("%Y-%m-%d"),
           "generator": {"script": "Scripts/props/build_senbon.py", "script_sha256": sha256(__file__),
                         "module": "Scripts/props/props_lib/senbon_paint.py",
                         "module_sha256": sha256(PROJECT / "Scripts/props/props_lib/senbon_paint.py"),
                         "version": LIB_VERSION, "blender": bpy.app.version_string},
           "sidecar": {"file": "Exports/Senbon/SM_Senbon_Heavy.sockets.json"},
           "maps": {name: {"file": rel(p16), "sha256": sha256(p16), "size": [int(d16.shape[1]), int(d16.shape[0])],
                           "format": "PNG, 16-bit greyscale, no colour chunks, row 0 = top",
                           "encoding": "LINEAR: value / 65535 = the linear detail d (sRGB-decoded Detail8)",
                           "uv": "the wrap's UV tile u 1..2 (same texel grid as T_Senbon_Heavy_Wrap_BC; Wrap addressing)",
                           "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                                             "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE",
                                             "mips": "TMGS_FROM_TEXTURE_GROUP", "address": "Wrap"},
                           "source": {"file": rel(src8), "sha256": sha256(src8),
                                      "stored_levels": int(len(np.unique(lev)))},
                           "recipe": "d16 = round(65535 * sRGBdecode(Detail8 / 255)); lossless (one code per 8-bit level)",
                           "gates": {"lossless_back_to_8bit": lossless}}},
           "parts": {"Heavy/Wrap": {"slot_material": S.MAT_HEAVY_WRAP, "slot_index": 1,
                                    "instance": S.MI[S.MAT_HEAVY_WRAP], "master": "M_Fabric_Master",
                                    "detail_map": name,
                                    "switches": {"Metal From ORM": False, "Cloth Sheen": True, "Use Lettering": False,
                                                 "Specular From ORM Alpha": False},
                                    "base_colour_map_reference": {"file": rel(paths["wrap"]["BC"]),
                                                                  "sha256": sha256(paths["wrap"]["BC"])},
                                    "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0],
                                               "Detail Bias": round(bias, 6), "Detail Scale": round(scale, 6),
                                               "Detail Mean": kc["mean"], "Detail Highlight Ratio": kc["highlight_ratio"],
                                               "Detail Moments Low": kc["moments_low"],
                                               "Detail Moments High": kc["moments_high"],
                                               "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING,
                                               "Specular Strength": 0.5},
                                    "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
                                    "covered_texels": int(cover.sum()),
                                    "param_notes": {"Colour": "linear RGBA; the wrap's MEAN colour over its texels "
                                                              "(default = the spec's #373532, the kunai grip colour)",
                                                    "switches": "PROPOSED for the finaliser: Cloth Sheen as the "
                                                                "kunai wrap; check against MI_Kunai_Plain_Wrap"},
                                    "derivation": "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail)); "
                                                  "v1 fields over the covered wrap texels; recolour_constants.json "
                                                  "(v2) is written by the finaliser under the materials lock"}},
           "other_slots": {"Needle/Steel": {"slot_material": S.MAT_NEEDLE_STEEL, "instance": S.MI[S.MAT_NEEDLE_STEEL],
                                            "master": "M_Steel_Master", "recolourable": False},
                           "Heavy/Steel": {"slot_material": S.MAT_HEAVY_STEEL, "instance": S.MI[S.MAT_HEAVY_STEEL],
                                           "master": "M_Steel_Master", "recolourable": False}}}
    out["pass"] = lossless
    path = RECOLOUR / "recolour_maps.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    paths["wrap"]["Detail16"] = p16
    report["recolour"] = {"file": rel(path), "detail16": rel(p16), "lossless": lossless,
                          "colour_linear": out["parts"]["Heavy/Wrap"]["params"]["Colour"],
                          "colour_srgb8": [int(round(float(x) * 255)) for x in PB.linear_to_srgb(colour)],
                          "spec_srgb8": [int(S.WRAP_HEX[i:i + 2], 16) for i in (1, 3, 5)],
                          "detail_mean": kc["mean"]}


def preview_material(mat, paths, wrap_tile=False):
    """Principled from the SHIPPED PNGs: BC sRGB, ORM linear (G rough, B metal), N DirectX (green flipped back)."""
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])

    def img(p, data):
        im = bpy.data.images.load(str(p), check_existing=True)
        im.colorspace_settings.name = "Non-Color" if data else "sRGB"
        nd = nt.nodes.new("ShaderNodeTexImage")
        nd.image = im
        nd.interpolation = "Linear"
        return nd
    bc, orm, n = img(paths["BC"], False), img(paths["ORM"], True), img(paths["N"], True)
    nt.links.new(bc.outputs["Color"], bs.inputs["Base Color"])
    nt.nodes.active = bc                                  # Workbench TEXTURE mode shows the active image (the BC)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(n.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs["Green"], inv.inputs[1])
    cm = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs["Red"], cm.inputs["Red"])
    nt.links.new(inv.outputs["Value"], cm.inputs["Green"])
    nt.links.new(sn.outputs["Blue"], cm.inputs["Blue"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(cm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    mat["sb_normal_map_node"] = nm.name


# =========================================================================== collision + sockets
def hull_object(name, pts_m, parent):
    bm = bmesh.new()
    for p in pts_m:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    inner = [v for v in bm.verts if not v.link_faces]
    if inner:
        bmesh.ops.delete(bm, geom=inner, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.hide_render = True
    ob.display_type = "WIRE"
    ob["ue_collision"] = "UCX"
    return ob


def outside_dist(hull, pts):
    me = hull.data
    d = np.full(len(pts), -1e9)
    for poly in me.polygons:
        n = np.array(poly.normal)
        c = np.array(poly.center)
        d = np.maximum(d, pts @ n - n @ c)
    return d


def obj_verts(o):
    co = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def obj_tris(o):
    me = o.data
    me.calc_loop_triangles()
    t = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    return t.reshape(-1, 3)


def stage_finish(objs, pivots, report):
    rep, groups = {}, {}
    for key, mesh in (("needle", S.NEEDLE_MESH), ("heavy", S.HEAVY_MESH)):
        lod0 = objs[key][0]
        if key == "needle":
            pts = G.needle_hull_points()
            shift = 0.0
        else:
            pts = G.heavy_hull_points()
            shift = pivots["heavy_com_mm"]
        pts = (pts - np.array([shift, 0, 0])) * MM
        hull = hull_object(f"UCX_{lod0.name}_00", pts, lod0)
        worst = []
        for o in objs[key]:
            worst.append(float(outside_dist(hull, obj_verts(o)).max()) * 1000.0)
        hv, hc = G.mesh_volume_com(obj_verts(hull) * 1000.0, obj_tris(hull))
        mv, mc = G.mesh_volume_com(obj_verts(lod0) * 1000.0, obj_tris(lod0))
        rep[key] = {"hull": hull.name, "vertices": len(hull.data.vertices), "faces": len(hull.data.polygons),
                    "triangles": len(obj_tris(hull)),
                    "worst_outside_mm_per_lod": [round(w, 5) for w in worst],
                    "contains_every_lod": all(w <= 1e-6 for w in worst),
                    "hull_volume_mm3": round(hv, 3), "lod0_mesh_volume_mm3": round(mv, 3),
                    "volume_ratio_hull_over_lod0": round(hv / mv, 4),
                    "hull_centroid_mm": [round(float(x), 4) for x in hc],
                    "hull_com_offset_cm": [round(float(x) / 10.0, 4) for x in hc],
                    "shape": ("octagonal prism (inradius = belly 1.4 mm) over x -50..50 + 4-vertex tip flats at "
                              "+-65 (0.05 mm half width)" if key == "needle" else
                              "octagonal prism (inradius = binding 2.3 mm) over s 0..159 (where the ridges start) + "
                              "the apex at s 170")}
        # sockets
        socks = []
        if key == "needle":
            sx = S.needle_sockets_x()
        else:
            ss = S.heavy_sockets_s()
            sx = {k: v - shift for k, v in ss.items()}
            sx["Throw"] = 0.0
        for nm in S.SOCKET_NAMES:
            x = sx[nm]
            make_socket(lod0, nm, (x * MM, 0.0, 0.0), (0.0, 0.0, 0.0))
            socks.append({"name": nm, "position_mm": [r6(x), 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0],
                          "use": S.SOCKET_USE[nm]})
        rep[key]["sockets"] = socks
        bpy.context.view_layer.update()
        groups[key] = make_lod_group(mesh, objs[key])
    report["collision_sockets"] = rep
    return groups


# =========================================================================== measure
def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def bounds_radius_mm(o):
    co = obj_verts(o) * 1000.0
    c = 0.5 * (co.min(axis=0) + co.max(axis=0))
    return float(np.linalg.norm(co - c, axis=1).max()), co


def uv_stats(o):
    me = o.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 3, 2).astype(np.float64)
    mi = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi)
    V = obj_verts(o) * 1000.0
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    tco = V[lv.reshape(-1, 3)]
    wrap = uv[:, :, 0].min(axis=1) > 1.0 - 1e-9
    size = np.where(wrap[:, None], np.array(S.WRAP_TEX.size, float)[None, :],
                    np.array(S.HEAVY_TEX.size if "Heavy" in o.name else S.NEEDLE_TEX.size, float)[None, :])
    px = uv * size[:, None, :]
    e1, e2 = tco[:, 1] - tco[:, 0], tco[:, 2] - tco[:, 0]
    d1, d2 = px[:, 1] - px[:, 0], px[:, 2] - px[:, 0]
    det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    n3 = np.cross(e1, e2)
    a3 = 0.5 * np.linalg.norm(n3, axis=1)
    apx = 0.5 * np.abs(det)
    sd = np.where(np.abs(det) < 1e-20, 1e-20, det)
    dpu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / sd[:, None]
    dpv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / sd[:, None]
    hand = (np.cross(dpu, dpv) * n3).sum(axis=1)
    dens = np.sqrt(apx / np.maximum(a3, 1e-30))
    out = {"uv_u_range": [r6(uv[:, :, 0].min()), r6(uv[:, :, 0].max())],
           "uv_v_range": [r6(uv[:, :, 1].min()), r6(uv[:, :, 1].max())],
           "collapsed_uv_triangles": int((apx < 1e-9).sum()), "mirrored_uv_triangles": int((hand < 0).sum()),
           "min_triangle_area_mm2": r6(a3.min()),
           "density_px_per_mm_area_weighted": {}}
    for key, sel in (("steel", ~wrap), ("wrap", wrap)):
        if sel.any():
            w = a3[sel]
            out["density_px_per_mm_area_weighted"][key] = {
                "mean": round(float((dens[sel] * w).sum() / w.sum()), 4),
                "p01": round(float(np.percentile(dens[sel], 1)), 4), "p99": round(float(np.percentile(dens[sel], 99)), 4)}
    return out


def lod_deviation(objs, ss, radius_mm):
    """Two-sided surface deviation LOD0 <-> LODn (mm), points: 4 per triangle; limit = 1 px at the switch (1080p)."""
    def samples(o):
        V = obj_verts(o)
        T = obj_tris(o)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        pts = [w[0] * a + w[1] * b + w[2] * c for w in ((1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2),
                                                         (0.2, 0.2, 0.6))]
        return np.concatenate(pts + [V])

    def tree(o):
        return BVHTree.FromPolygons([Vector(v) for v in obj_verts(o)], [tuple(t) for t in obj_tris(o)])
    out = {}
    p0 = samples(objs[0])
    t0 = tree(objs[0])
    for i in (1, 2):
        ti = tree(objs[i])
        d1 = np.array([ti.find_nearest(Vector(p))[3] for p in p0]) * 1000.0
        pi = samples(objs[i])
        d2 = np.array([t0.find_nearest(Vector(p))[3] for p in pi]) * 1000.0
        d = np.concatenate([d1, d2])
        lim = 2.0 * radius_mm / (ss[i] * 1080.0)
        out[f"LOD{i}"] = {"p50": round(float(np.percentile(d, 50)), 4), "p99": round(float(np.percentile(d, 99)), 4),
                          "max": round(float(d.max()), 4), "mm_per_px_at_switch_1080p": round(lim, 4),
                          "p99_px_at_switch": round(float(np.percentile(d, 99)) / lim, 4),
                          "max_px_at_switch": round(float(d.max()) / lim, 4),
                          "pass": bool(np.percentile(d, 99) < lim)}
    return out


def silhouette(item, o, shift_mm):
    """LOD0 side (Z extents, seen from -Y) and top (Y extents, seen from +Z) at every 1 mm station vs the design."""
    V = obj_verts(o) * 1000.0 + np.array([shift_mm, 0, 0])
    T = obj_tris(o)
    if item == "needle":
        stations = np.arange(-65.0, 65.0 + 1e-9, 1.0)
        edges = [-65.0, 65.0]
    else:
        stations = np.arange(0.0, 170.0 + 1e-9, 1.0)
        edges = [0.0, 6.0, 7.5, 52.5, 54.0, 170.0]
    rows, worst, worst_at = [], 0.0, None
    excluded = []
    for s in stations:
        sm = min(max(s, stations[0] + 1e-4), stations[-1] - 1e-4)
        m = G.mesh_section_extents(V, T, sm)
        dsg = G.design_section_extents(item, sm)
        if m is None:
            continue
        dev = {k: m[k] - dsg[k] for k in ("+Y", "-Y", "+Z", "-Z")}
        near_edge = any(abs(s - e) < 0.21 for e in edges)
        rows.append({"s_mm": float(s), "design": {k: round(v, 4) for k, v in dsg.items()},
                     "mesh": {k: round(v, 4) for k, v in m.items()}, "dev": {k: round(v, 4) for k, v in dev.items()},
                     "excluded": bool(near_edge)})
        if near_edge:
            excluded.append(float(s))
            continue
        w = max(abs(v) for v in dev.values())
        if w > worst:
            worst, worst_at = w, float(s)
    return {"stations": len(rows), "worst_abs_dev_mm": round(worst, 4), "worst_at_mm": worst_at,
            "excluded_stations_at_profile_steps": excluded, "pass_0.05mm": worst <= 0.05 + 1e-9, "rows": rows}


def stage_measure(objs, pivots, report):
    rep = {}
    for key, mesh in (("needle", S.NEEDLE_MESH), ("heavy", S.HEAVY_MESH)):
        ol = objs[key]
        tris = [tri_count(o) for o in ol]
        rad, co = bounds_radius_mm(ol[0])
        ss = scaled_lod_screen_sizes(rad)
        shift = 0.0 if key == "needle" else pivots["heavy_com_mm"]
        V0 = obj_verts(ol[0]) * 1000.0
        T0 = obj_tris(ol[0])
        mv, mc = G.mesh_volume_com(V0, T0)
        ent = {"triangles": tris, "descending": all(tris[i] > tris[i + 1] for i in range(2)),
               "lod0_within_budget": tris[0] <= S.BUDGETS[mesh]["lod0_max"],
               "bounds_radius_mm_bbox_centre": round(rad, 4), "screen_sizes": ss,
               "switch_distances_m": [round(screen_size_distance_m(s, rad * MM), 3) for s in ss[1:]],
               "bounds_mm": {"min": [round(float(x), 4) for x in co.min(axis=0)],
                             "max": [round(float(x), 4) for x in co.max(axis=0)]},
               "length_mm": round(float(co[:, 0].max() - co[:, 0].min()), 4),
               "uv": {f"LOD{i}": uv_stats(o) for i, o in enumerate(ol)},
               "closed_manifold": [G.closed_manifold(obj_tris(o)) for o in ol],
               "mesh_volume_mm3_lod0": round(mv, 3), "mesh_centroid_mm_lod0": [round(float(x), 4) for x in mc],
               "lod_deviation": lod_deviation(ol, ss, rad),
               "silhouette_lod0": silhouette(key, ol[0], shift)}
        # symmetry: C_n about X on 1 nm-snapped positions (the needle also mirror x -> -x)
        n = (S.NEEDLE_LODS if key == "needle" else S.HEAVY_LODS)[0].sides
        q = np.round(V0, 6)
        sym = {}
        for i, o in enumerate(ol):
            Vi = np.round(obj_verts(o) * 1000.0, 6)
            nn = (S.NEEDLE_LODS if key == "needle" else S.HEAVY_LODS)[i].sides
            k = 3 if key == "heavy" else nn          # the heavy is C3 (three facets); the needle C_n
            ang = 2 * math.pi / k
            R = np.array([[1, 0, 0], [0, math.cos(ang), -math.sin(ang)], [0, math.sin(ang), math.cos(ang)]])
            Vr = Vi @ R.T
            tree = BVHTree.FromPolygons([Vector(v) for v in Vi], [tuple(t) for t in obj_tris(o)])
            dmax = max(float(np.linalg.norm(np.array(v) - np.array(tree.find_nearest(Vector(v))[0]))) for v in Vr)
            ent_s = {"rotation_deg": round(360.0 / k, 3), "max_dev_mm": round(dmax, 6)}
            if key == "needle":
                Vm = Vi * np.array([-1, 1, 1])
                ent_s["mirror_x_max_dev_mm"] = round(max(float(np.linalg.norm(np.array(v) - np.array(tree.find_nearest(Vector(v))[0]))) for v in Vm), 6)
            sym[f"LOD{i}"] = ent_s
        ent["symmetry"] = sym
        # tip socket = apex: the max-x vertex
        tipx = float(V0[:, 0].max())
        ent["tip_vertex_x_mm"] = round(tipx, 6)
        if key == "needle":
            ent["dimensions"] = needle_dims(ol[0])
        else:
            ent["dimensions"] = heavy_dims(ol[0], shift)
        rep[key] = ent
    report["measure"] = rep


def needle_dims(o):
    V = obj_verts(o) * 1000.0
    T = obj_tris(o)
    def D(x):
        m = G.mesh_section_extents(V, T, x)
        return round(m["+Z"] + m["-Z"], 4), round(m["+Y"] + m["-Y"], 4)
    return {"D_at_0_side_top": D(1e-4), "D_at_+50": D(50.0 - 1e-4), "D_at_-50": D(-50.0 + 1e-4),
            "tips_x_mm": [round(float(V[:, 0].min()), 4), round(float(V[:, 0].max()), 4)],
            "tip_flat_diameter_mm": round(2 * float(np.hypot(V[:, 1], V[:, 2])[V[:, 0] > 64.999].max()), 4),
            "spec": {"D0": [2.80, 0.02], "D50": [2.30, 0.02], "tips": [65.0, 0.1]}}


def heavy_dims(o, shift):
    V = obj_verts(o) * 1000.0 + np.array([shift, 0, 0])
    T = obj_tris(o)
    def D(s):
        m = G.mesh_section_extents(V, T, s)
        return round(m["+Z"] + m["-Z"], 4)
    # ridge start: the land vertex at a ridge azimuth with the largest s below the tip
    r = np.hypot(V[:, 1], V[:, 2])
    th = (np.degrees(np.arctan2(V[:, 2], V[:, 1])) + 360) % 360
    ridge = (np.abs(((th - 30) % 120)) < 1e-3) & (np.abs(r - S.H_R_FRONT) < 1e-4) & (V[:, 0] > S.H_PT0 + 1)
    return {"wrap_D_at_30": D(30.0), "rear_binding_D_at_6.75": D(6.75), "front_binding_D_at_53.25": D(53.25),
            "steel_D_at_3": D(3.0), "steel_D_at_55": D(55.0),
            "D_at_147.99": D(147.99), "ridges_start_s_mm": sorted({round(float(x), 4) for x in V[ridge, 0]}),
            "tip_s_mm": round(float(V[:, 0].max()), 4), "butt_s_mm": round(float(V[:, 0].min()), 4),
            "spec": {"wrap": [4.20, 0.03], "bindings": [4.60, 0.03], "steel_tail": [2.80, 0.02],
                     "front_148": [4.50, 0.02], "ridges_start": [159.0, 0.3], "tip": [170.0, 0.1]}}


# =========================================================================== qa / export
def stage_qa(objs, report):
    res, allp = {}, True
    for key in ("needle", "heavy"):
        names = [o.name for o in objs[key]]
        r = qa_check(names, budget_tris=1000, texel_density=None, require_uv1=False, require_ucx=True,
                     overlap_method="sat")
        failed = [c for c in r["checks"] if not c["passed"]]
        for c in failed:
            log(f"  QA FAIL {key} {c['name']} on {c['object']}: {c['detail']}")
        res[key] = {"passed": r["passed"], "checks": len(r["checks"]),
                    "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]} for c in failed],
                    "triangles": r["triangles"],
                    "details": {c["name"] + "@" + str(c["object"]): c["detail"] for c in r["checks"]
                                if c["name"] in ("texel_density", "uv_no_overlap", "no_zero_length_edges",
                                                 "no_degenerate_faces", "no_coincident_vertices", "ucx_present")}}
        allp = allp and r["passed"]
        log(f"qa_check {key}: {'PASS' if r['passed'] else 'FAIL'} ({len(r['checks']) - len(failed)}/{len(r['checks'])})")
    report["qa"] = {"passed": allp, "per_mesh": res,
                    "settings": "budget 1000 (plan 5.2 cap), no texel target (non-square maps: measured separately "
                                "in measure.uv), UV1 generated at import (plan 7.2), SAT overlap"}
    return allp


def stage_export(groups, report, pivots):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    rep = {}
    for key, mesh in (("needle", S.NEEDLE_MESH), ("heavy", S.HEAVY_MESH)):
        fbx = EXPORTS / f"{mesh}.fbx"
        ss = report["measure"][key]["screen_sizes"]
        r = export_fbx(str(fbx), [groups[key].name], kind="static", lod_screen_sizes=ss)
        side = r["sidecar"]
        payload = json.loads(Path(side).read_text(encoding="utf-8"))
        mass_g = pivots["needle_mass_g"] if key == "needle" else pivots["heavy_mass_g"]
        cs = report["collision_sockets"][key]
        payload["mass_kg"] = round(mass_g / 1000.0, 5)
        payload["centre_of_mass_mm"] = [0.0, 0.0, 0.0]
        payload["hull_com_offset_cm"] = cs["hull_com_offset_cm"]
        payload["use_ccd"] = True
        payload["physics_note"] = ("mass override = the as-built ROUND profile x 7.85 g/cm3 (+ cotton wrap 0.6 g/cm3 on "
                                   "the heavy); pivot = that centre of mass. Unreal derives the COM from the hull: set "
                                   "Center Of Mass Offset = -hull_com_offset_cm if it matters. CCD on, angular damping "
                                   "0.5-1.0 for dropped needles only (plan 4.3)")
        payload["embed"] = {"default_depth_mm": S.EMBED_DEFAULT_MM, "by_surface_mm": S.EMBED_BY_SURFACE_MM,
                            "max_incidence_deg": 70, "direction": "along the incoming velocity, +-2 deg jitter"}
        payload["throw"] = {"method": "direct (jiki-daho), point first, no spin", "rotation_follows_velocity": True,
                            "volley": "3 needles fanned +-4 deg" if key == "needle" else "single"}
        if key == "needle":
            payload["material"] = {"slots": [f"0 {S.MAT_NEEDLE_STEEL} -> {S.MI[S.MAT_NEEDLE_STEEL]} (M_Steel_Master)"],
                                   "textures": {"BC": "T_Senbon_Needle_BC (sRGB)",
                                                "ORM": "T_Senbon_Needle_ORM (linear: R AO, G roughness, B metallic)",
                                                "N": "T_Senbon_Needle_N (DirectX, flip green OFF)"}}
        else:
            payload["material"] = {"slots": [f"0 {S.MAT_HEAVY_STEEL} -> {S.MI[S.MAT_HEAVY_STEEL]} (M_Steel_Master)",
                                             f"1 {S.MAT_HEAVY_WRAP} -> {S.MI[S.MAT_HEAVY_WRAP]} (M_Fabric_Master, "
                                             "recolourable; UV tile u 1..2)"],
                                   "textures": {"BC": "T_Senbon_Heavy_BC (sRGB)", "ORM": "T_Senbon_Heavy_ORM (linear)",
                                                "N": "T_Senbon_Heavy_N (DirectX)",
                                                "Wrap_BC": "T_Senbon_Heavy_Wrap_BC (sRGB)",
                                                "Wrap_ORM": "T_Senbon_Heavy_Wrap_ORM (linear, B = 0)",
                                                "Wrap_N": "T_Senbon_Heavy_Wrap_N (DirectX)",
                                                "Wrap_Detail16": "Recolour/T_Senbon_Heavy_Wrap_Detail16 (linear G16)"},
                                   "wrap_default_colour_srgb": S.WRAP_HEX}
        Path(side).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rep[key] = {"fbx": str(fbx.relative_to(PROJECT)).replace("\\", "/"),
                    "sidecar": str(Path(side).relative_to(PROJECT)).replace("\\", "/"),
                    "objects": r["objects"], "warnings": r["warnings"], "lod_screen_sizes": r["lod_screen_sizes"],
                    "sockets": [{k: v for k, v in s.items() if k in ("socket", "location", "rotation", "mesh")}
                                for s in r["sockets"]],
                    "sha256": {"fbx": sha256(fbx), "sidecar": sha256(side)}, "bytes": fbx.stat().st_size}
        log(f"exported {fbx.name} ({fbx.stat().st_size} bytes)")
    report["export"] = rep


# =========================================================================== gates
def collect_gates(report):
    g = {}
    m = report.get("measure") or {}
    g["01_qa_check_both"] = bool((report.get("qa") or {}).get("passed"))
    for key in ("needle", "heavy"):
        e = m.get(key) or {}
        g[f"02_{key}_lod0_budget"] = bool(e.get("lod0_within_budget"))
        g[f"03_{key}_lods_descend"] = bool(e.get("descending"))
        g[f"04_{key}_closed"] = bool(e.get("closed_manifold")) and all(e["closed_manifold"])
        uv = list((e.get("uv") or {}).values())
        g[f"05_{key}_uv_no_collapsed_or_mirrored"] = bool(uv) and all(
            u["collapsed_uv_triangles"] == 0 and u["mirrored_uv_triangles"] == 0 for u in uv)
        g[f"06_{key}_lod_deviation_under_1px"] = bool(e.get("lod_deviation")) and all(
            v["pass"] for v in e["lod_deviation"].values())
        g[f"07_{key}_silhouette_0.05mm"] = bool((e.get("silhouette_lod0") or {}).get("pass_0.05mm"))
        cs = (report.get("collision_sockets") or {}).get(key) or {}
        g[f"08_{key}_hull_contains_every_lod"] = bool(cs.get("contains_every_lod"))
        g[f"09_{key}_hull_le_24_verts"] = cs.get("vertices", 99) <= 24
        g[f"10_{key}_five_sockets"] = len(cs.get("sockets") or []) == 5
        if e:
            tipx = e["tip_vertex_x_mm"]
            sock = {s["name"]: s["position_mm"][0] for s in cs.get("sockets", [])}
            g[f"11_{key}_tip_socket_is_apex"] = abs(sock.get("Tip", 1e9) - tipx) <= 0.01
    tex = report.get("textures") or {}
    g["12_maps_pot_no_colour_chunks"] = bool(tex) and all(
        v["power_of_two"] and not any(v["colour_chunks"].values()) for v in tex.values())
    g["13_recolour_detail16_lossless"] = bool((report.get("recolour") or {}).get("lossless"))
    mm = report.get("mass_model") or {}
    if mm:
        n, h = mm["needle"], mm["heavy"]
        g["14_needle_mass_within_3pct"] = abs(n["mass_g"] / n["derived_mass_g"] - 1) <= 0.03
        g["15_heavy_mass_within_3pct"] = abs(h["mass_g"] / h["derived_mass_g"] - 1) <= 0.03
        g["16_heavy_com_within_1mm"] = abs(h["com_from_butt_mm"] - h["derived_com_from_butt_mm"]) <= 1.0
    if m:
        nd = m["needle"]["dimensions"]
        g["17_needle_dims"] = (abs(nd["D_at_0_side_top"][0] - 2.8) <= 0.02 and abs(nd["D_at_+50"][0] - 2.3) <= 0.02
                               and abs(nd["tips_x_mm"][1] - 65) <= 0.1 and abs(nd["tips_x_mm"][0] + 65) <= 0.1)
        hd = m["heavy"]["dimensions"]
        g["18_heavy_dims"] = (abs(hd["wrap_D_at_30"] - 4.2) <= 0.03 and abs(hd["rear_binding_D_at_6.75"] - 4.6) <= 0.03
                              and abs(hd["front_binding_D_at_53.25"] - 4.6) <= 0.03
                              and abs(hd["steel_D_at_3"] - 2.8) <= 0.02 and abs(hd["D_at_147.99"] - 4.5) <= 0.02
                              and all(abs(x - 159.0) <= 0.3 for x in hd["ridges_start_s_mm"])
                              and len(hd["ridges_start_s_mm"]) >= 1
                              and abs(hd["tip_s_mm"] - 170.0) <= 0.1)
    fr = report.get("frozen") or {}
    g["19_frozen_unchanged"] = bool(fr.get("after")) and not fr["after"]["differing_or_missing"]
    names = [o for v in (report.get("export") or {}).values() for o in v.get("objects", [])]
    g["20_no_franchise_string"] = not S.deny_hits(*names)
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default=",".join(ALL_STAGES))
    p.add_argument("--quick", action="store_true")
    p.add_argument("--dev-dir", default=None)
    return p.parse_args(argv)


def main(argv=None):
    global ASSETS, EXPORTS, TEXTURES, RECOLOUR, RENDERS, BUILD_WORK
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    if args.dev_dir:
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, BUILD_WORK = dev / "Assets", dev / "Exports", dev / "Renders", dev / "build"
        TEXTURES, RECOLOUR = EXPORTS / "Textures", EXPORTS / "Textures" / "Recolour"
    elif args.quick:
        raise SystemExit("--quick is a DEV flag: use it with --dev-dir")
    for d in (ASSETS, EXPORTS, TEXTURES, RENDERS, BUILD_WORK):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": "Senbon", "meshes": [S.NEEDLE_MESH, S.HEAVY_MESH], "library": f"props_lib senbon {LIB_VERSION}",
              "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
              "build_script": "Scripts/props/build_senbon.py", "quick": bool(args.quick), "build_to": S.build_to(),
              "spec_sha256": sha256(S.SPEC_PATH), "sheet_sha256": sha256(S.SHEET_PATH),
              "frozen": {"before": frozen_hashes()},
              "lods": {"needle": [l.__dict__ for l in S.NEEDLE_LODS], "heavy": [l.__dict__ for l in S.HEAVY_LODS]}}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    objs, builders, lay, mats, pivots = stage_mesh(report)
    report["pivots"] = {k: r6(v) for k, v in pivots.items()}
    log("objects: " + ", ".join(f"{k}: {[tri_count(o) for o in v]}" for k, v in objs.items()))
    paths = None
    if "textures" in stages:
        paths, maps = stage_textures(objs, lay, mats, report, quick=args.quick)
        stage_recolour(maps["wrap"], paths, report)
        preview_material(mats["needle"][0], paths["needle"])
        preview_material(mats["heavy"][0], paths["heavy"])
        preview_material(mats["heavy"][1], paths["wrap"])
    groups = stage_finish(objs, pivots, report)
    stage_measure(objs, pivots, report)
    if "qa" in stages:
        stage_qa(objs, report)
    if "save" in stages:
        for im in bpy.data.images:
            if im.source == "FILE" and im.filepath:
                im.pack()
        blend = ASSETS / "Senbon.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
        report["blend"] = str(blend.relative_to(PROJECT)).replace("\\", "/")
        report["blend_sha256"] = sha256(blend)
        log(f"saved {blend}")
    if "export" in stages:
        stage_export(groups, report, pivots)
    if "render" in stages and paths:
        from props_lib import senbon_gallery as GAL
        report["renders"] = GAL.render_all(objs, report, RENDERS, WORK, BUILD_WORK, quick=args.quick, log=log)
    report["frozen"]["after"] = frozen_hashes()
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    if "report" in stages:
        out = (WORK if not args.dev_dir else dev) / "senbon_report.json"
        out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        log(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
