#!/usr/bin/env python
"""Build SM_BlackHat from scratch: geometry, UVs, maps, collision, socket, LODs, export, renders.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_black_hat.py -- [--quick] [--dev-dir DIR] [--no-render]

Every number in the report is measured on what was built.  ``--quick`` (only with --dev-dir)
lowers the AO and render samples for iterating; the shipped build is the one without flags.

HOW IT IS MADE (the way the hat is made)
----------------------------------------
    props_lib.blackhat_spec     REFERENCE_SPEC's numbers (MEASURED / INFERRED / DESIGNED)
    props_lib.blackhat_camera   REFERENCE_SPEC 1's camera in the build frame
    props_lib.blackhat_geom     the parts: a two-surface woven skin per rib bay, 13 round rods on
                                it, the domed crown cap and its rolled lip, the rolled rim tube and
                                its binding cord, 26 lashings of three cords, the band (one turn,
                                a twisted roll fanning into the knot), the knot, two torn tails
    props_lib.blackhat_atlas    the two 2048 atlases (straw, cloth), islands in strand / tape space
    props_lib.blackhat_paint    every texel painted from its own part's coordinates
    props_lib.blackhat_look     materials (the Unreal graph), AO bake, hulls, the reference view
    props_lib.blackhat_gallery  the pack gallery on the shared rig

WHAT IT READS: numbers only.  The reference PNG is opened by exactly two things, both after the
maps are written: the side-by-side / crops sheets and the fidelity metrics.

WHAT IT NEVER TOUCHES: the shuriken pack, the smoke bomb, the paused paper bomb, the generic
props_lib modules (used as they are) and Scripts/pipeline/** (used as it is).  Their hashes are
checked at the start and the end.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))

import bpy                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from pipeline.export_fbx import export_fbx                        # noqa: E402
from pipeline.helpers import make_lod_group, make_socket          # noqa: E402
from pipeline.qa_check import qa_check                            # noqa: E402
from props_lib import blackhat_atlas as A                         # noqa: E402
from props_lib import blackhat_camera as CAM                      # noqa: E402
from props_lib import blackhat_gallery as GAL                     # noqa: E402
from props_lib import blackhat_geom as G                          # noqa: E402
from props_lib import blackhat_look as LK                         # noqa: E402
from props_lib import blackhat_paint as BP                        # noqa: E402
from props_lib.blackhat_spec import BLACK_HAT, assert_clean, build_to, deny_hits, lashing_azimuths  # noqa: E402

LIB_VERSION = "1.2.1"      # close-out (2026-09-26): invented knot pleats, blocky wear, rim trough removed; 1.2.0 surface pass; see WorkFiles/blackhat/BLACKHAT_REPORT.md
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "BlackHat"
TEXTURES = EXPORTS / "Textures"
RENDERS = PROJECT / "Renders" / "BlackHat"
WORK = PROJECT / "WorkFiles" / "blackhat"
BUILD_WORK = WORK / "build"
REFERENCE = PROJECT / "References" / "BlackHat" / "blackhat_guide.png"
REFERENCE_SHA = "8244fd615b6c1575c57eba5a077a18c44da52a234a44b08997f7a2b94d7ec356"
#: REFERENCE_SPEC 9: the chromaticity of each part (the Tint's hue; its luminance is L_ref)
CHROMA = {"straw": (0.357, 0.326, 0.317), "cloth": (0.339, 0.330, 0.331)}
STEMS = {"straw": BLACK_HAT.straw_stem, "cloth": BLACK_HAT.cloth_stem}
MATS = {"straw": BLACK_HAT.straw_material, "cloth": BLACK_HAT.cloth_material}
#: ORM.G clip per part (final pass): no near-mirror straw (round 1 reached 0.05), matte cloth
ROUGH_RANGE = {"straw": (0.25, 1.0), "cloth": (0.85, 0.95)}
#: REFERENCE_SPEC 8's measured tip pixels (the torn ends' points) and the gate on them (x AND y)
TAIL_TIPS_PX = {t.name: tuple(t.tip_px) for t in BLACK_HAT.tails}
TAIL_TIP_TOL_PX = 6.0

T0 = time.time()


def log(*parts):
    print(f"[blackhat {time.time() - T0:7.1f}s]", *parts, flush=True)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =========================================================================== frozen assets
def _check_sums(sums: Path, resolve) -> dict:
    out, ok = {}, []
    for line in sums.read_text(encoding="utf8").splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        want, rel = parts[0], parts[-1].lstrip("*")
        path = resolve(rel)
        if path is None:
            continue
        got = sha256(path) if path.is_file() else None
        out[rel] = got == want
        ok.append(got == want)
    return {"checked": len(ok), "ok": int(sum(ok)), "all_ok": bool(ok) and all(ok),
            "failed": [k for k, v in out.items() if not v]}


def frozen_hashes() -> dict:
    shu = PROJECT / "WorkFiles" / "shuriken" / "regression" / "post_kunai_plain" / "SHA256SUMS.txt"

    def shu_path(rel):
        if rel == "Shuriken.blend":
            return PROJECT / "Assets" / "Shuriken.blend"
        if rel.startswith("export/"):
            return PROJECT / "Exports" / "Shuriken" / rel[len("export/"):]
        if rel.startswith("textures/"):
            p = PROJECT / "Exports" / "Shuriken" / "Textures" / rel[len("textures/"):]
            return p if p.is_file() else PROJECT / "Exports" / "Shuriken" / rel[len("textures/"):]
        return None
    pb = PROJECT / "WorkFiles" / "paperbomb" / "paused_2026-09-21" / "SHA256SUMS_exports.txt"
    sb = PROJECT / "WorkFiles" / "smokebomb" / "regression" / "post_smoke_bomb" / "SHA256SUMS.txt"

    def sb_path(rel):
        return PROJECT / rel if rel.split("/")[0] in ("Assets", "Exports", "Renders", "Scripts") else None
    return {"shuriken": _check_sums(shu, shu_path),
            "paperbomb": _check_sums(pb, lambda rel: PROJECT / rel),
            "smokebomb": _check_sums(sb, sb_path)}


# =========================================================================== geometry
def stage_geometry(spec, cam, report):
    builders, infos = [], []
    tails = None
    for lod in (0, 1, 2):
        mb, info, tails = G.build_lod(spec, lod, cam, tails)
        builders.append(mb)
        infos.append(info)
        log(f"  LOD{lod}: {mb.triangles()} triangles, {len(mb.P)} vertices, parts "
            f"{ {k: sum(len(mb.F[i]) - 2 for i in v) for k, v in mb.parts.items()} }")
    bad0 = A.fix_handedness(builders[0])
    # the tail walls' chunks: a coarse LOD's longer outline edges run up to one edge past a chunk's
    # end, so LOD0's wall members reserve 50 mm either side (texture only; LOD0 never uses it)
    for m in builders[0].members.values():
        if m.info.get("part") == "tail_wall":
            m.lo = m.lo - np.array([50.0, 0.0])
            m.hi = m.hi + np.array([50.0, 0.0])
    # the other LODs take LOD0's member flips (same parts, same local frames)
    mirrored_after = {"LOD0": int(sum(bad0.values()))}
    for i, mb in enumerate(builders[1:], 1):
        for k, m in mb.members.items():
            m.flip = builders[0].members[k].flip
        for fi, key in enumerate(mb.FM):
            if mb.members[key].flip < 0:
                mb.FL[fi] = mb.FL[fi] * np.array([1.0, -1.0])
    report["geometry"] = {"lods": {f"LOD{i}": {"triangles": mb.triangles(), "vertices": len(mb.P),
                                                "parts": {k: sum(len(mb.F[j]) - 2 for j in v) for k, v in mb.parts.items()},
                                                "members": len(mb.members)} for i, mb in enumerate(builders)},
                          "band": infos[0]["band"], "knot": infos[0]["knot"],
                          "tails": {k: {kk: (vv if not isinstance(vv, np.ndarray) else vv.tolist()) for kk, vv in v.items()}
                                    for k, v in infos[0]["tails"].items()},
                          "lashings": [{"theta": round(t, 2), "kind": k} for t, k in lashing_azimuths(spec)],
                          "ribs_deg": list(spec.ribs.all_deg),
                          "frame": {"apex_z_mm": round(spec.apex_z, 3), "tube_centre_mm": [round(spec.rim_centre_radius, 3),
                                                                                          round(spec.tube_centre_z, 3)],
                                    "skin_entry_rt": spec.rim.skin_entry_rt, "camera_z_offset_R": spec.camera.z_offset_R}}
    return builders, tails


def stage_atlas(spec, builders, report):
    mb0 = builders[0]
    at = {"straw": A.pack(mb0, "straw", spec.texture_size, spec.padding_px),
          "cloth": A.pack(mb0, "cloth", spec.texture_size, spec.padding_px, u_offset=1.0)}
    uvs, uvrep = [], {}
    for i, mb in enumerate(builders):
        missing = [k for k in mb.members if k not in mb0.members]
        if missing:
            raise RuntimeError(f"LOD{i} members not in LOD0's atlas: {missing}")
        u = A.apply_uvs(mb, at)
        uvs.append(u)
        r = A.uv_report(mb, u)
        # how far a coarse LOD's local coordinates fall outside LOD0's member (in texels)
        worst = 0.0
        for L, key in zip(mb.FL, mb.FM):
            m0 = mb0.members[key]
            if m0.kind == "rect":
                d = np.maximum.reduce([m0.lo[0] - L[:, 0], L[:, 0] - m0.hi[0], m0.lo[1] - L[:, 1], L[:, 1] - m0.hi[1]])
                sc = abs(np.linalg.det(at[m0.atlas].place[key].A)) ** 0.5
                worst = max(worst, float(d.max()) * sc)
        r["max_outside_lod0_member_px"] = round(worst, 3)
        uvrep[f"LOD{i}"] = r
    report["atlas"] = {k: v.to_json() for k, v in at.items()}
    report["uv"] = uvrep
    log(f"  atlas straw {at['straw'].ppmm:.3f} px/mm fill {at['straw'].fill:.3f}; cloth {at['cloth'].ppmm:.3f} px/mm "
        f"fill {at['cloth'].fill:.3f}")
    return at, uvs


# =========================================================================== textures
def stage_textures(spec, builders, at, uvs, report, quick=False):
    hat = G.Hat(spec)
    chs = {}
    for k in ("straw", "cloth"):
        chs[k] = BP.paint_atlas(builders[0], at[k], seed=spec.seed, hat=hat, log=log)
    # a first set of maps (no AO) so the materials exist for the bake
    TEXTURES.mkdir(parents=True, exist_ok=True)
    maps, paths = {}, {}
    for k in chs:
        maps[k] = BP.finish(chs[k], CHROMA[k], rough_range=ROUGH_RANGE[k])
        paths[k] = {kk: LK.write_png(TEXTURES / f"{STEMS[k]}_{kk}.png", maps[k][kk]) for kk in ("BC", "ORM", "N", "Detail")}
    tmp_mats = [_material(f"__bake_{k}", paths[k], maps[k], k, pack=False) for k in ("straw", "cloth")]
    lod0 = LK.to_blender(builders[0], uvs[0], "__AO_LOD0", tmp_mats)
    log("baking ambient occlusion (Cycles, LOD0 alone)")
    aos = LK.bake_ao(lod0, 1, spec.texture_size, samples=48 if quick else 256)
    me = lod0.data
    bpy.data.objects.remove(lod0, do_unlink=True)
    bpy.data.meshes.remove(me)
    ao_rep = {}
    for i, k in enumerate(("straw", "cloth")):
        a = aos[i]
        reached = a > 1e-6
        fill = float(a[reached].mean()) if reached.any() else 1.0
        a = np.where(reached, a, fill)
        ao_rep[k] = {"reached_fraction": round(float(reached.mean()), 4), "mean": round(fill, 4),
                     "p01": round(float(np.percentile(a[reached], 1)), 4)}
        chs[k]["ao"] = chs[k]["ao"] * a
        maps[k] = BP.finish(chs[k], CHROMA[k], rough_range=ROUGH_RANGE[k])
        paths[k] = {kk: LK.write_png(TEXTURES / f"{STEMS[k]}_{kk}.png", maps[k][kk]) for kk in ("BC", "ORM", "N", "Detail")}
    for m in tmp_mats:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image is not None:
                bpy.data.images.remove(n.image)
        bpy.data.materials.remove(m)
    mats = {k: _material(MATS[k], paths[k], maps[k], k, pack=True) for k in ("straw", "cloth")}
    tex = {"maps": {k: {kk: str(Path(v).relative_to(PROJECT)) for kk, v in p.items()} for k, p in paths.items()},
           "sha256": {k: {kk: sha256(v) for kk, v in p.items()} for k, p in paths.items()},
           "sizes": {k: {kk: int(maps[k][kk].shape[0]) for kk in ("BC", "ORM", "N", "Detail")} for k in maps},
           "tint_linear": {k: [round(float(x), 6) for x in maps[k]["tint_linear"]] for k in maps},
           "tint_srgb": {k: [round(float(x), 6) for x in maps[k]["tint_srgb"]] for k in maps},
           "L_ref": {k: round(maps[k]["L_ref"], 6) for k in maps},
           "detail_bias": {k: maps[k]["detail_bias"] for k in maps},
           "detail_scale": {k: maps[k]["detail_scale"] for k in maps},
           "spec_scale": dict(LK.SPEC_SCALE), "roughness_range": {k: list(v) for k, v in ROUGH_RANGE.items()},
           "roughness_stats": {k: maps[k]["roughness_stats"] for k in maps},
           "spec_mask_min_max": {k: maps[k]["spec_mask_min_max"] for k in maps},
           "recolour": {k: maps[k]["recolour"] for k in maps},
           "albedo_stats": {k: {kk: round(v, 5) for kk, v in maps[k]["albedo_stats"].items()} for k in maps},
           "spec_mask_mean": {k: round(maps[k]["spec_mask_mean"], 4) for k in maps},
           "ao_bake": ao_rep, "chroma": CHROMA,
           "colour_chunks": {k: {kk: [c for c in _png_chunks(v) if c in ("sRGB", "gAMA", "cHRM", "iCCP")]
                                 for kk, v in p.items()} for k, p in paths.items()},
           "unreal_material": {k: LK.unreal_material_spec(STEMS[k], maps[k], k) for k in maps}}
    tex["power_of_two"] = all((s & (s - 1)) == 0 for d in tex["sizes"].values() for s in d.values())
    tex["mip_parity"] = {k: mip_parity(maps[k]) for k in maps}
    report["textures"] = tex
    log(f"  tints (mean colour) {tex['tint_linear']}; bias {tex['detail_bias']} scale {tex['detail_scale']}; detail levels "
        f"{ {k: maps[k]['recolour']['detail_levels_used'] for k in maps} }")
    return mats, maps, paths


def _material(name, paths, m, part, pack):
    return LK.make_material(name, paths, m["tint_linear"], pack=pack, detail_bias=m["detail_bias"],
                            detail_scale=m["detail_scale"], spec_scale=LK.SPEC_SCALE[part])


def _png_chunks(path):
    b = Path(path).read_bytes()
    i, out = 8, []
    while i < len(b):
        n = int.from_bytes(b[i:i + 4], "big")
        out.append(b[i + 4:i + 8].decode("latin1"))
        i += 12 + n
    return out


def mip_parity(m) -> dict:
    """The recolour graph against BC through Unreal-style mips (2x2 box in LINEAR light: Detail and
    BC are both sRGB, decoded before filtering), each level re-quantised to 8 bits:
    lum(Tint) x (Bias + Scale x Detail) vs BC, mean over the map, mips 0-8 (and the far mip's value
    against lum(Tint): with Tint = the mean colour the far mips converge on the Tint)."""
    d = BP.srgb_decode(m["Detail"].astype(np.float64) / 255.0)
    bc = BP.srgb_decode(m["BC"].astype(np.float64) / 255.0) @ BP.LUMA
    tl = float(np.asarray(m["tint_linear"]) @ BP.LUMA)
    b, sc = m["detail_bias"], m["detail_scale"]
    out, per_texel = [], []
    for lvl in range(9):
        a8 = np.rint(BP.srgb_encode(d) * 255) / 255.0
        b8 = np.rint(BP.srgb_encode(bc) * 255) / 255.0
        a_lin = np.clip(tl * (b + sc * BP.srgb_decode(a8)), 0, 1)
        b_lin = BP.srgb_decode(b8)
        out.append(round(float(a_lin.mean() / max(b_lin.mean(), 1e-12) - 1.0) * 100.0, 3))
        per_texel.append(round(float(np.percentile(np.abs(a_lin - b_lin), 99)), 5))
        d = 0.25 * (d[0::2, 0::2] + d[1::2, 0::2] + d[0::2, 1::2] + d[1::2, 1::2])
        bc = 0.25 * (bc[0::2, 0::2] + bc[1::2, 0::2] + bc[0::2, 1::2] + bc[1::2, 1::2])
    return {"graph_vs_bc_mean_pct_mip0_8": out, "max_abs_pct": round(max(abs(x) for x in out), 3),
            "graph_vs_bc_p99_abs_linear_mip0_8": per_texel,
            "note": "the mean over the WHOLE map (padding texels hold the median) at each mip"}


# =========================================================================== objects
def stage_objects(spec, builders, uvs, mats, report):
    objs = []
    for i, mb in enumerate(builders):
        name = spec.mesh_name if i == 0 else f"{spec.mesh_name}_LOD{i}"
        assert_clean(name)
        objs.append(LK.to_blender(mb, uvs[i], name, [mats["straw"], mats["cloth"]]))
    return objs


def _hanging_tail_mask(spec, mb):
    P = np.asarray(mb.P)
    ids = np.array(sorted({v for fi in mb.parts.get("tails", []) for v in mb.F[fi]}), int)
    is_tail = np.zeros(len(P), bool)
    is_tail[ids] = True
    r = np.hypot(P[:, 0], P[:, 1])
    return is_tail & ((r > spec.rim_centre_radius) | (P[:, 2] < -0.5))


def stage_collision(spec, builders, objs, report):
    """ONE tight convex hull round the hat's body (cone, crown cap, rim, lashings, band, knot and the
    tails where they lie on the cone): support planes 1 mm out, at most 50 vertices.

    The hanging tails get NO collision (final pass; round 1 boxed them in a second hull): a limp
    cloth tail on a worn hat should not block or snag the wearer's capsule and shoulders, and on a
    hat lying on the ground they are a 9 cm strip of cloth.  Round 1's hulls stood 15 mm above the
    crown and 30 mm below the tail tips."""
    lod0 = objs[0]
    body, hang = [], []
    for mb in builders:
        P = np.asarray(mb.P)
        m = _hanging_tail_mask(spec, mb)
        body.append(P[~m])
        hang.append(P[m])
    body_pts = np.concatenate(body)
    # 49, not 50: Chaos's p.Chaos.ConvexParticlesWarningThreshold is 50; one under keeps a margin (the
    # surface pass's lid made the greedy fit land exactly on 50)
    Vb, hrep = LK.support_hull(body_pts, max_vertices=49)
    Vb2, Fb = LK.convex_faces(Vb)
    h0 = LK._hull_object(f"UCX_{lod0.name}_00", Vb2 * 0.001, Fb, lod0)
    worst = [float(_outside(Vb2, Fb, P).max()) for P in body]
    dw = _outside(Vb2, Fb, body_pts)
    worst_pt = body_pts[int(np.argmax(dw))].round(2).tolist()
    hang_all = np.concatenate(hang)
    lo = np.asarray(builders[0].P)
    report["collision"] = {"hulls": [h0.name], "vertices": [len(Vb2)], "faces": [len(Fb)],
                           "worst_point_mm": worst_pt,
                           "shape": "support-plane polytope: down, up, 13 horizontal (rim), 13 at the cone normal, "
                                    "plus greedy planes at the band / knot; each plane 1 mm outside the body",
                           "fit": hrep,
                           "body_worst_vertex_outside_mm_per_lod": [round(w, 4) for w in worst],
                           "contains_body_of_every_lod": bool(max(worst) <= 1e-6),
                           "hanging_tails": {"collision": "none (by design)",
                                             "vertices_per_lod": [int(len(h)) for h in hang],
                                             "lowest_z_mm": round(float(hang_all[:, 2].min()), 2),
                                             "lod0_mesh_z_range_mm": [round(float(lo[:, 2].min()), 2),
                                                                      round(float(lo[:, 2].max()), 2)]},
                           "naming": "UCX_<render mesh NODE name>_00, renamed with the node by make_lod_group"}
    log(f"  hull {len(Vb2)} vertices, gap mean {hrep['gap_to_points_convex_hull_mm']['mean']} mm; "
        f"worst body vertex outside {max(worst):.4f} mm")
    return [h0]


def _outside(V, F, P):
    V = np.asarray(V)
    cen = V.mean(0)
    d = np.full(len(P), -1e9)
    for f in F:
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        if (cen - a) @ n > 0:
            n = -n
        d = np.maximum(d, (P - a) @ n)
    return d


def stage_sockets(spec, objs, report):
    out = []
    for sd in spec.sockets():
        make_socket(objs[0], sd.name, tuple(v * 0.001 for v in sd.position_mm), tuple(math.radians(a) for a in sd.rotation_deg))
        out.append({"name": sd.name, "position_mm": list(sd.position_mm), "rotation_deg": list(sd.rotation_deg),
                    "use": sd.use})
    hs = spec.head_sphere_radius_mm
    report["sockets"] = out
    report["head_socket_derivation"] = {
        "head_circumference_mm": spec.head_circumference_mm, "head_sphere_radius_mm": round(hs, 3),
        "inner_cone_half_angle_deg": 90.0 - spec.slope_deg,
        "inner_apex_z_mm": round(spec.apex_z - spec.skin_thickness_R * spec.R / math.cos(math.radians(spec.slope_deg)), 3),
        "seat_below_inner_apex_mm": round(hs / math.sin(math.radians(90.0 - spec.slope_deg)) - hs, 3),
        "HEAD_z_mm": out[0]["position_mm"][2],
        "note": "DESIGNED (REFERENCE_SPEC 10): the top of a 57 cm head (sphere) touching the inner cone; "
                "the reference never shows the underside, so there is no head ring"}


# =========================================================================== measure
def stage_measure(spec, objs, at, report):
    lods = {}
    for i, o in enumerate(objs):
        me = o.data
        me.calc_loop_triangles()
        co = np.array([v.co[:] for v in me.vertices]) * 1000.0
        uv = np.empty(len(me.loops) * 2)
        me.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        tri_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
        tri_co = np.array([[co[v] for v in t.vertices] for t in me.loop_triangles])
        a3 = 0.5 * np.linalg.norm(np.cross(tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0]), axis=1)
        auv = 0.5 * ((tri_uv[:, 1, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 2, 1] - tri_uv[:, 0, 1])
                     - (tri_uv[:, 2, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 1, 1] - tri_uv[:, 0, 1]))
        mats = np.array([t.material_index for t in me.loop_triangles])
        band = spec.lod_bands[i]
        ntri = len(me.loop_triangles)
        e = {"object": o.name, "triangles": ntri, "vertices": len(me.vertices), "band": list(band),
             "in_band": bool(band[0] <= ntri <= band[1]),
             "triangles_per_slot": {"straw": int((mats == 0).sum()), "cloth": int((mats == 1).sum())},
             "bounds_mm": {"min": [round(float(x), 3) for x in co.min(0)], "max": [round(float(x), 3) for x in co.max(0)]},
             "uv_range": [round(float(uv.min()), 6), round(float(uv.max()), 6)],
             "collapsed_uv_triangles": int((np.abs(auv) < 1e-12).sum()),
             "mirrored_uv_triangles": int((auv < 0).sum()),
             "min_triangle_area_mm2": round(float(a3.min()), 6),
             "texel_density_px_per_cm": {k: round(float(math.sqrt(np.abs(auv[mats == s]).sum() / a3[mats == s].sum())
                                                         * spec.texture_size * 10.0), 3)
                                         for s, k in ((0, "straw"), (1, "cloth"))}}
        lods[f"LOD{i}"] = e
    # LOD deviation: LODn's vertices to LOD0's surface and back (mm)
    from mathutils.bvhtree import BVHTree
    trees = []
    for o in objs:
        me = o.data
        V = [v.co.copy() for v in me.vertices]
        Pg = [tuple(t.vertices) for t in me.loop_triangles]
        trees.append((BVHTree.FromPolygons(V, Pg), np.array([v[:] for v in V])))
    t0, v0 = trees[0]
    for i in (1, 2):
        ti, vi = trees[i]
        a = np.array([(t0.find_nearest(tuple(p))[3] or 0.0) for p in vi]) * 1000
        b = np.array([(ti.find_nearest(tuple(p))[3] or 0.0) for p in v0]) * 1000
        lods[f"LOD{i}"]["deviation_to_lod0_mm"] = {"lodn_to_lod0_p99": round(float(np.percentile(a, 99)), 3),
                                                  "lod0_to_lodn_p99": round(float(np.percentile(b, 99)), 3),
                                                  "lod0_to_lodn_max": round(float(b.max()), 3)}
    co = np.array([v.co[:] for v in objs[0].data.vertices]) * 1000.0
    c = 0.5 * (co.min(0) + co.max(0))
    radius = float(np.linalg.norm(co - c, axis=1).max())
    report["lods"] = lods
    report["lod_triangles"] = [lods[f"LOD{i}"]["triangles"] for i in range(3)]
    report["bounds_radius_mm"] = round(radius, 3)
    report["lod_screen_sizes"] = spec.lod_screen_sizes(radius)
    report["switch_distances_m"] = spec.switch_distances_m(radius)
    ss = report["lod_screen_sizes"]
    for i in (1, 2):
        px_per_mm = ss[i] * 1080.0 / (2.0 * radius)
        lods[f"LOD{i}"]["deviation_to_lod0_mm"]["one_px_at_switch_mm"] = round(1.0 / px_per_mm, 3)
    report["size_mm"] = [round(float(x), 2) for x in np.ptp(co, axis=0)]
    report["mass"] = {"design_g": spec.mass_g, "status": "DESIGNED (study: 0.21 - 0.30 kg for 40 - 51 cm kasa; ours "
                                                            "is 60 cm)"}


def stage_qa(spec, objs, report):
    names = [o.name for o in objs]
    target = report["lods"]["LOD0"]["texel_density_px_per_cm"]
    # qa_check grades ONE density per object; the object carries two slots at their own densities,
    # so the target is the object's area-weighted density (measured) with the documented slots
    me = objs[0].data
    result = qa_check(names, budget_tris=spec.lod_bands[0][1], texel_density=None, tolerance=0.25,
                      require_ucx=True, overlap_method="sat")
    failed = [c for c in result["checks"] if not c["passed"]]
    for c in failed:
        log(f"  QA FAIL {c['name']} on {c['object']}: {c['detail']}")
    log(f"qa_check {'PASS' if result['passed'] else 'FAIL'} ({len(result['checks']) - len(failed)}/{len(result['checks'])})")
    report["qa"] = {"passed": result["passed"], "n_checks": len(result["checks"]), "checks": result["checks"],
                    "triangles": result["triangles"], "budget_tris": spec.lod_bands[0][1],
                    "texel_density_note": f"two slots at their own densities {target} px/cm; qa_check grades one number "
                                          f"per object, so it reports the density without a target",
                    "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]} for c in failed]}
    return result


def stage_export(spec, group, report):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    fbx = EXPORTS / f"{spec.mesh_name}.fbx"
    result = export_fbx(str(fbx), [group.name], kind="static", lod_screen_sizes=report["lod_screen_sizes"])
    sidecar = result["sidecar"]
    if sidecar:
        payload = json.loads(Path(sidecar).read_text(encoding="utf-8"))
        tex = report.get("textures") or {}
        payload["materials"] = {
            MATS[k]: {"slot": i, "part": k, "textures": {kk: f"{STEMS[k]}_{kk}" for kk in ("BC", "ORM", "N", "Detail")},
                      "tint_default_linear": (tex.get("tint_linear") or {}).get(k),
                      "tint_default_srgb": (tex.get("tint_srgb") or {}).get(k),
                      "tint_is": "the part's MEAN colour: edit Tint to recolour",
                      "detail_bias_default": (tex.get("detail_bias") or {}).get(k),
                      "detail_scale_default": (tex.get("detail_scale") or {}).get(k),
                      "specular_scale": LK.SPEC_SCALE[k],
                      "orm_texture_settings": {**LK.ORM_COMPOSITE, "composite_texture": f"{STEMS[k]}_N"},
                      "graph": (tex.get("unreal_material") or {}).get(k)}
            for i, k in enumerate(("straw", "cloth"))}
        payload["materials_note"] = (
            "BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail.R)) (Detail sRGB ON, TC_Grayscale). "
            "Tint is the part's MEAN colour: set it to the colour the part should read as. At the defaults the graph "
            "equals BC at every mip at the source (8-bit PNG) level; in Unreal BC is BC1-compressed and Detail is "
            "uncompressed G8, so they differ by BC1 block error. Specular = specular_scale x ORM.A; Roughness = ORM.G "
            "(set the ORM texture's Composite Texture to the part's _N, mode CTM_NormalRoughnessToGreen); Metallic 0; "
            "N DirectX (flip green OFF). The cloth's UV0 lies in the second tile (U + 1): keep the address mode Wrap.")
        geo = (report.get("geometry") or {}).get("lods") or {}
        payload["triangle_budget"] = {
            "lod_triangles": report.get("lod_triangles"),
            "lod0_by_part": (geo.get("LOD0") or {}).get("parts"),
            "why_lod0_is_over_10k": "a 600 mm hat whose signature details are real geometry: 26 lashings of three "
                                    "cords, the rolled rim tube, its binding cord, 13 ribs, the band and two torn tails "
                                    "with walls; the pack's LOD rule switches LOD1 in at screen size 0.70, LOD2 at 0.25"}
        payload["collision_note"] = ("one convex hull (UCX_..._00, <= 50 vertices) round the hat's straw body (every "
                                     "straw vertex of every LOD is inside it); the cloth tails have no collision by "
                                     "design from where they leave the band over the rim edge, so a few tail "
                                     "vertices on the rim roll and all of the hanging tails lie outside it")
        Path(sidecar).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report["export"] = {
        "fbx": str(fbx.relative_to(PROJECT)),
        "sockets_sidecar": str(Path(sidecar).relative_to(PROJECT)) if sidecar else None,
        "objects": result["objects"], "warnings": result["warnings"],
        "lod_screen_sizes": result["lod_screen_sizes"], "sockets": result["sockets"],
        "axis": {"forward": result["settings"]["axis_forward"], "up": result["settings"]["axis_up"]},
        "sha256": {"fbx": sha256(fbx), "sidecar": sha256(sidecar) if sidecar else None},
        "bytes": {"fbx": fbx.stat().st_size}}
    log(f"exported {fbx.name} sha {report['export']['sha256']['fbx'][:16]}")


# =========================================================================== renders
#: [reference | render] crops at 3x (x0, y0, x1, y1): crown, knot, left worn bays, front rim and
#: lashings, the tails' ends, the right rim
CROPS3X = [(290, 135, 380, 185), (410, 190, 530, 280), (60, 250, 210, 350), (250, 380, 400, 440),
           (540, 400, 660, 540), (560, 250, 668, 350)]


def stage_render(spec, cam, objs, report, quick=False):
    RENDERS.mkdir(parents=True, exist_ok=True)
    BUILD_WORK.mkdir(parents=True, exist_ok=True)
    samples = 64 if quick else 512
    ref_png = RENDERS / "blackhat_reference_view.png"
    LK.reference_view(objs[0], cam, ref_png, BUILD_WORK, samples=samples)
    LK.side_by_side(str(REFERENCE), ref_png, RENDERS / "blackhat_side_by_side.png")
    LK.crops_sheet(str(REFERENCE), ref_png, RENDERS / "blackhat_crops_3x.png", CROPS3X, scale=3)
    rep = {"reference_view": str(ref_png.relative_to(PROJECT)),
           "side_by_side": "Renders/BlackHat/blackhat_side_by_side.png",
           "crops_3x": "Renders/BlackHat/blackhat_crops_3x.png",
           "camera": {**cam.blender(), "distance_R": spec.camera.distance_R,
                      "elevation_deg": spec.camera.elevation_deg, "roll_deg": spec.camera.roll_deg},
           "lights": [list(l) for l in LK.REF_LIGHTS], "world": LK.REF_WORLD, "samples": samples}
    gal = GAL.gallery(spec, objs, RENDERS, BUILD_WORK, samples=48 if quick else 256,
                      lod_screen_sizes=report["lod_screen_sizes"], tris=report["lod_triangles"])
    rep["gallery"] = gal
    sw = GAL.lod_switch_frame(objs, cam, report["bounds_radius_mm"], report["lod_screen_sizes"],
                              RENDERS / "blackhat_lod_switch.png", BUILD_WORK, samples=48 if quick else 192)
    rep["lod_switch"] = sw
    report["renders"] = rep
    report["fidelity"] = fidelity(ref_png)
    report["no_reference_in_maps"] = {"reference_sha256": sha256(REFERENCE), "expected": REFERENCE_SHA,
                                      "note": "the reference is first loaded in the render stage (side-by-side, crops, "
                                              "metrics), after every map was written"}


# =========================================================================== fidelity
def _outlines(L):
    H, W = L.shape
    bg, obj = 0.9960, float(np.median(L[L < 0.5]))
    thr = 0.5 * (bg + obj)
    top = np.full(W, np.nan)
    bot = np.full(W, np.nan)
    for x in range(W):
        col = L[:, x]
        idx = np.where(col < thr)[0]
        if len(idx) == 0:
            continue
        y = idx[0]
        if y > 0:
            a, b = col[y - 1], col[y]
            top[x] = (y - 1) + (a - thr) / (a - b)
        y = idx[-1]
        if y < H - 1:
            a, b = col[y], col[y + 1]
            bot[x] = y + (thr - a) / (b - a)
    return top, bot, L < thr


def _lines(top):
    out = {}
    for side, (a, b) in dict(left=(70, 285), right=(385, 545)).items():
        x = np.arange(a, b)
        y = top[a:b]
        ok = ~np.isnan(y)
        p = np.polyfit(x[ok], y[ok], 1)
        out[side] = [float(p[0]), float(p[1]), float((y[ok] - np.polyval(p, x[ok])).std())]
    m1, c1 = out["left"][:2]
    m2, c2 = out["right"][:2]
    xa = (c2 - c1) / (m1 - m2)
    out["apex"] = [xa, m1 * xa + c1]
    return out


def _tail_tips(mask):
    ys, xs = np.nonzero(mask[:, 520:])
    xs = xs + 520
    ia = int(np.argmax(ys + 1e-3 * xs))
    a = (float(xs[ia]), float(ys[ia]))
    sel = xs > a[0] + 25
    ib = int(np.argmax(np.where(sel, ys, -1)))
    return {"A": [a[0], a[1]], "B": [float(xs[ib]), float(ys[ib])]}


def fidelity(render_png) -> dict:
    """REFERENCE_SPEC 11's instruments on the SHIPPED render (outline lines, rim bottom, extents,
    region tones and chroma), the same code run on the reference."""
    ref = LK.load_png(REFERENCE)[..., :3].astype(np.float64)
    ren = LK.load_png(render_png)[..., :3].astype(np.float64)
    W = np.array([0.2126, 0.7152, 0.0722])
    out = {}
    for nm, img in (("reference", ref), ("render", ren)):
        top, bot, mask = _outlines(img @ W)
        xs = np.where(mask.any(0))[0]
        ys = np.where(mask.any(1))[0]
        lin = BP.srgb_decode(img) @ W
        out[nm] = {"lines": _lines(top), "rim_bottom_340": float(np.nanmedian(bot[328:353])),
                   "x_extent": [int(xs.min()), int(xs.max())], "y_extent": [int(ys.min()), int(ys.max())],
                   "crown_top_y_334": float(np.nanmin(top[326:343])),
                   "object_lum_lin_p10_50_90": [round(float(v), 4) for v in np.percentile(lin[mask], [10, 50, 90])],
                   "object_chroma": [round(float(v), 4) for v in (BP.srgb_decode(img)[mask].mean(0) /
                                                                  BP.srgb_decode(img)[mask].mean(0).sum())],
                   "_top": top, "_bot": bot, "_mask": mask}
    r, n = out["reference"], out["render"]
    g = {"top_left_line_dev_px": float(np.nanmean(n["_top"][70:285] - r["_top"][70:285])),
         "top_right_line_dev_px": float(np.nanmean(n["_top"][385:545] - r["_top"][385:545])),
         "rim_bottom_dev_px": n["rim_bottom_340"] - r["rim_bottom_340"],
         "crown_top_dev_px": n["crown_top_y_334"] - r["crown_top_y_334"],
         "x_extent_dev_px": [n["x_extent"][0] - r["x_extent"][0], n["x_extent"][1] - r["x_extent"][1]],
         "tail_tip_y_dev_px": n["y_extent"][1] - r["y_extent"][1],
         "mask_iou": float((r["_mask"] & n["_mask"]).sum() / (r["_mask"] | n["_mask"]).sum()),
         "bottom_outline_rms_px": float(np.sqrt(np.nanmean((n["_bot"][40:540] - r["_bot"][40:540]) ** 2)))}
    # the tails' pointed tips, in x AND y (round 1 gated y only): A = the lowest silhouette pixel,
    # B = the lowest one at least 25 px right of A
    for nm, d in (("reference", r), ("render", n)):
        d["tail_tips_px"] = _tail_tips(d["_mask"])
    g["tail_tip_dev_px"] = {k: [round(n["tail_tips_px"][k][0] - TAIL_TIPS_PX[k][0], 2),
                                round(n["tail_tips_px"][k][1] - TAIL_TIPS_PX[k][1], 2)] for k in ("A", "B")}
    g["tail_tip_reference_measured_px"] = r["tail_tips_px"]
    for d in (r, n):
        for k in ("_top", "_bot", "_mask"):
            d.pop(k)
    out["deviation"] = g
    return out


def fidelity_gates(fid) -> dict:
    d = fid["deviation"]
    r, n = fid["reference"], fid["render"]
    g = {"F1_top_lines_within_2px": abs(d["top_left_line_dev_px"]) <= 2.0 and abs(d["top_right_line_dev_px"]) <= 2.0,
         "F2_rim_bottom_within_2px": abs(d["rim_bottom_dev_px"]) <= 2.0,
         "F3_crown_top_within_2px": abs(d["crown_top_dev_px"]) <= 2.0,
         "F4_extent_within_3px": max(abs(v) for v in d["x_extent_dev_px"]) <= 3,
         "F5_mask_iou_ge_0.95": d["mask_iou"] >= 0.95,
         "F6_object_p50_within_20pct": abs(n["object_lum_lin_p10_50_90"][1] / r["object_lum_lin_p10_50_90"][1] - 1) <= 0.20,
         "F7_chroma_r_within_0.012": abs(n["object_chroma"][0] - r["object_chroma"][0]) <= 0.012,
         "F8_tail_tips_x_and_y_within_6px": all(abs(v) <= TAIL_TIP_TOL_PX for xy in d["tail_tip_dev_px"].values()
                                                 for v in xy)}
    return {k: bool(v) for k, v in g.items()}


def collect_gates(report) -> dict:
    lods = report.get("lods") or {}
    g = {}
    g["1_qa_check_clean"] = bool((report.get("qa") or {}).get("passed"))
    g["2_lod_triangles_in_band"] = bool(lods) and all(v["in_band"] for v in lods.values())
    tr = report.get("lod_triangles", [0, 0, 0])
    g["3_lod_triangles_descend"] = tr[0] > tr[1] > tr[2]
    g["4_no_collapsed_uv_triangles"] = bool(lods) and all(v["collapsed_uv_triangles"] == 0 for v in lods.values())
    g["5_no_mirrored_uv_triangles"] = bool(lods) and all(v["mirrored_uv_triangles"] == 0 for v in lods.values())
    g["6_uv0_in_two_tiles"] = bool(lods) and all(v["uv_range"][0] >= -1e-6 and v["uv_range"][1] <= 2 + 1e-6
                                                 for v in lods.values())
    g["6b_lod_uvs_inside_lod0_members"] = all(v.get("max_outside_lod0_member_px", 0) <= 8.0
                                              for v in (report.get("uv") or {}).values())
    col = report.get("collision") or {}
    g["7_hull_contains_body_of_every_lod"] = bool(col.get("contains_body_of_every_lod"))
    g["7b_one_hull_at_most_50_vertices_1mm_over_crown_and_rim"] = bool(
        len(col.get("hulls") or []) == 1 and (col.get("vertices") or [99])[0] <= 50
        and abs((col.get("fit") or {}).get("above_highest_vertex_mm", 99) - 1.0) < 0.05
        and abs((col.get("fit") or {}).get("below_lowest_vertex_mm", 99) - 1.0) < 0.05)
    g["8_head_socket"] = [s["name"] for s in report.get("sockets") or []] == ["HEAD"]
    tex = report.get("textures") or {}
    g["9_maps_power_of_two_no_colour_chunks"] = bool(tex.get("power_of_two")) and not any(
        c for d in (tex.get("colour_chunks") or {}).values() for c in d.values())
    ok9b = bool(tex)
    for k, rc in (tex.get("recolour") or {}).items():
        mm = rc["detail_min_max_code"]
        ok9b = (ok9b and rc["detail_levels_used"] >= 200 and mm[0] == 0 and mm[1] == 255
                and abs(rc["mean_of_bias_plus_scale_x_detail"] - 1.0) <= 0.002 and rc["max_abs_err_linear"] <= 0.0035)
    g["9b_recolour_detail_full_range_both_ends_tint_is_mean"] = ok9b
    g["9c_mip_parity_within_1pct"] = bool(tex) and all(v["max_abs_pct"] <= 1.0 for v in tex["mip_parity"].values())
    rs = tex.get("roughness_stats") or {}
    g["9d_roughness_floors_straw_0.25_cloth_0.85_0.95"] = bool(
        rs and rs["straw"]["min"] >= 0.245 and rs["cloth"]["min"] >= 0.845 and rs["cloth"]["max"] <= 0.955)
    g["10_frozen_assets_unchanged"] = bool((report.get("frozen") or {}).get("unchanged"))
    names = [report.get("asset"), *((report.get("build_to") or {}).get("materials") or []),
             *((report.get("build_to") or {}).get("textures") or [])]
    names += [v.get("object") for v in lods.values()] + list(col.get("hulls") or [])
    g["11_no_franchise_string"] = not deny_hits(*names)
    g["12_no_triangle_unreal_would_drop"] = bool(lods) and all(v["min_triangle_area_mm2"] >= 0.005 for v in lods.values())
    fid = report.get("fidelity")
    if fid:
        for k, v in fidelity_gates(fid).items():
            g["13_" + k] = v
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


# =========================================================================== main
def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--no-render", action="store_true")
    p.add_argument("--dev-dir", default=None)
    p.add_argument("--report-name", default="blackhat_report.json")
    return p.parse_args(argv)


def main(argv=None):
    global ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    if args.dev_dir:
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, WORK = dev / "Assets", dev / "Exports", dev / "Renders", dev
        TEXTURES, BUILD_WORK = EXPORTS / "Textures", dev / "build"
    elif args.quick or args.no_render:
        raise SystemExit("--quick / --no-render are DEV flags: use them with --dev-dir")
    spec = BLACK_HAT
    for d in (ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": spec.mesh_name, "library": f"props_lib blackhat {LIB_VERSION}",
              "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
              "build_script": str(Path(__file__).relative_to(PROJECT)), "quick": bool(args.quick),
              "build_to": build_to(spec), "frozen": {"before": frozen_hashes()}}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    cam = CAM.RefCamera(spec)
    log("geometry (props_lib.blackhat_geom)")
    builders, tails = stage_geometry(spec, cam, report)
    at, uvs = stage_atlas(spec, builders, report)
    log("painting + maps (props_lib.blackhat_paint)")
    mats, maps, paths = stage_textures(spec, builders, at, uvs, report, quick=args.quick)
    objs = stage_objects(spec, builders, uvs, mats, report)
    hulls = stage_collision(spec, builders, objs, report)
    stage_sockets(spec, objs, report)
    stage_measure(spec, objs, at, report)
    group = make_lod_group(spec.mesh_name, objs)
    assert_clean(group.name, *(o.name for o in objs), *(h.name for h in hulls))
    report["collision"]["hulls"] = [h.name for h in hulls]
    report["lod_names"] = [o.name for o in objs]
    for i, o in enumerate(objs):
        report["lods"][f"LOD{i}"]["object"] = o.name
    stage_qa(spec, objs, report)
    blend = ASSETS / "BlackHat.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report["blend"] = str(blend.relative_to(PROJECT))
    report["blend_sha256"] = sha256(blend)
    log(f"saved {blend}")
    stage_export(spec, group, report)
    if not args.no_render:
        stage_render(spec, cam, objs, report, quick=args.quick)
    report["frozen"]["after"] = frozen_hashes()
    a = report["frozen"]["after"]
    report["frozen"]["unchanged"] = bool(a["shuriken"]["all_ok"] and a["paperbomb"]["all_ok"] and a["smokebomb"]["all_ok"])
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    out = WORK / args.report_name
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
