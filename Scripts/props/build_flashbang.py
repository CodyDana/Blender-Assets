#!/usr/bin/env python
"""Build SM_Flashbang (+ _Body, _PullRing, _Lever) from scratch: parts, LODs, atlas, bakes, maps, recolour maps,
collision, sockets, QA, export, renders.  Round 1 + the FINALISE pass (2026-09-27, lib 2.0.0: the craft review's
blockers and majors - fuze front panel and shorter plate, channel lever with hinge cheeks and one joggle, thick ring
through the pin head on one centreline at every LOD, brass cans + dividers inside, 24-point holes, the notched base
end face and foot cut-outs, the new wear model; the 8-bit Paint_Detail is no longer shipped).  ROUND 2 (lib 3.0.0):
the fuze head as a mechanism (striker plate + knuckle, side lug with rolled edge and cross pins, screw, coil, spring
post and ball), the ring re-posed, V-groove ring lines, brass tubes with a geometric seam step and shoulder pushed into
the wall, a 2.2 mm wall, the faceted sleeve chamfer and 12-flat cap, the new wear model, the strip-softbox studio.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_flashbang.py -- [--stages ...] [--quick] [--dev-dir DIR]

Stages: mesh, textures, save, qa, export, render, report.  ``--quick`` (DEV, with --dev-dir) lowers the bake / render
samples.  Every number in the report is measured on what was built.

HOW IT IS MADE
--------------
props_lib.flashbang_spec     the numbers (Study metrology in D units, D = 44 mm; the plan's frame and sockets)
props_lib.flashbang_geom     every part as real geometry, generated per LOD, with analytic UV parameters on named
                             islands packed once for all LODs (MaxRects, 16 px padding, no rotation / mirroring)
props_lib.flashbang_blender  -> Blender meshes, the four-mesh split, socket frames, mass model
props_lib.flashbang_paint    Cycles bakes of LOD0 (position, normal, ids, edge masks, AO, bevel normal) + the
                             numpy painter (olive paint over steel, chips, grime, antiqued steel, brass tube)
props_lib.flashbang_gallery  renders from the BAKED maps only, in the reference's style and camera

WHAT IT NEVER TOUCHES: the frozen items (shuriken pack, kunai, smoke bomb, black hat, fan, paper bomb),
Scripts/pipeline/** (used as it is), Scripts/unreal/materials/** (read-only: recolour_common is loaded without
bytecode), the reference PNG (opened only by the render stage's comparisons).
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

import bmesh                                                       # noqa: E402
import bpy                                                         # noqa: E402
import numpy as np                                                 # noqa: E402
from mathutils import Matrix, Vector                               # noqa: E402
from mathutils.bvhtree import BVHTree                              # noqa: E402

from pipeline.export_fbx import export_fbx                         # noqa: E402
from pipeline.helpers import make_lod_group, make_socket           # noqa: E402
from pipeline.qa_check import qa_check                             # noqa: E402
from props_lib import bake as PB                                   # noqa: E402
from props_lib import flashbang_blender as FB                      # noqa: E402
from props_lib import flashbang_geom as G                          # noqa: E402
from props_lib import flashbang_paint as FP                        # noqa: E402
from props_lib.flashbang_spec import FLASHBANG, build_to, assert_clean, deny_hits, D_MM  # noqa: E402

LIB_VERSION = "3.0.0"                     # round 2 (finalise 2.0.0, round 1 1.0.0)
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "Flashbang"
TEXTURES = EXPORTS / "Textures"
RECOLOUR = TEXTURES / "Recolour"
RENDERS = PROJECT / "Renders" / "Flashbang"
WORK = PROJECT / "WorkFiles" / "flashbang"
BUILD_WORK = WORK / "build"
R1 = WORK / "r2" / "compare"          # ROUND 2: reference | round 1 | round 2 part compares
REFERENCE = PROJECT / "References" / "Flashbang" / "flashbang_reference.png"
REFERENCE_SHA = "64d1f560"
ALL_STAGES = ("mesh", "textures", "save", "qa", "export", "render", "report")
T0 = time.time()


def log(*a):
    print(f"[flashbang {time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =========================================================================== frozen
FROZEN_DIRS = ["Exports/Shuriken", "Exports/SmokeBomb", "Exports/BlackHat", "Exports/PaperBomb", "Exports/Fan",
               "Scripts/unreal/materials"]


MATERIAL_SPEC = "Scripts/unreal/materials/material_spec.json"


def spec_without_flashbang() -> str:
    """FINALISE: the flashbang's own additions to the pack's material_spec.json (made under the materials lock) removed
    again, serialised the way the file is written - equal to the pre-flashbang snapshot iff the change was additions
    only."""
    s = json.loads((PROJECT / MATERIAL_SPEC).read_text(encoding="utf-8"))
    s["items"] = [i for i in s["items"] if not i["item"].startswith("Flashbang")]
    for k in ("recolour_maps", "recolour_constants"):
        s["build"].get(k, {}).pop("Flashbang", None)
    s.pop("changes_v6_flashbang", None)
    s["build"]["texture_folder"] = s["build"]["texture_folder"].replace(", Flashbang)", ")")
    text = (json.dumps(s, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    if b"\r\n" in (PROJECT / MATERIAL_SPEC).read_bytes()[:64]:
        text = text.replace(b"\n", b"\r\n")           # the file is written with Windows line ends
    return hashlib.sha256(text).hexdigest()


def frozen_hashes() -> dict:
    pre = WORK / "regression" / "pre_flashbang" / "SHA256SUMS.txt"
    ok, bad, own = 0, [], []
    for line in pre.read_text(encoding="utf8").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        h, rel = parts[0], parts[1].lstrip("*").strip()
        p = PROJECT / rel
        if p.is_file() and sha256(p) == h:
            ok += 1
        elif rel == MATERIAL_SPEC and p.is_file() and spec_without_flashbang() == h:
            own.append(rel)                   # the flashbang's additions only (everything else byte-identical)
        else:
            bad.append(rel)
    return {"baseline": str(pre.relative_to(PROJECT)), "identical": ok, "differing_or_missing": bad,
            "flashbang_additions_only": own}


# =========================================================================== mesh
def stage_mesh(spec, report):
    builders, infos = [], []
    for lod in range(len(spec.lods)):
        mb, info = G.build_lod(spec, lod)
        builders.append(mb)
        infos.append(info)
    flips = [FB.fix_island_handedness(mb) for mb in builders]
    packing = G.pack_islands(builders, spec.atlas_px, spec.padding_px)
    lm_packing = G.pack_islands(builders, spec.atlas_px, 96)
    report["lightmap_uv1"] = {"layout": "the same islands re-packed with 96 px padding at 2048 (3 px at a 64 px "
                                        "lightmap, 6 px at 128): non-overlapping, inside 0-1",
                              "fill": round(lm_packing.fill, 4)}
    log(f"atlas {spec.atlas_px}: {len(packing.place)} islands, {packing.ppmm:.3f} px/mm, fill {packing.fill:.3f}")
    report["atlas"] = {"size": spec.atlas_px, "padding_px": spec.padding_px, "ppmm": round(packing.ppmm, 4),
                       "px_per_cm": round(packing.ppmm * 10, 3), "fill": round(packing.fill, 4),
                       "islands": len(packing.place), "flipped_islands_per_lod": flips,
                       "density_factors": {k: v for k, v in sorted(G.DENSITY.items())},
                       "layout": "MaxRects, no rotation or mirroring, analytic UV parameters (mm) per island; the "
                                 "long revolved islands are cut in two on an exact grid line so the atlas packs"}
    report["parts_info"] = {f"LOD{i}": {k: v for k, v in inf.items() if k != "body"} for i, inf in enumerate(infos)}
    report["body_layout"] = {k: v for k, v in infos[0]["body"].items() if k != "holes"}
    report["holes"] = {"per_row": len(spec.hole_thetas()), "thetas_deg": spec.hole_thetas(),
                       "rows_z_mm": list(spec.hole_rows_z), "size_mm": [round(spec.body_r * math.radians(spec.hole_ang_w_deg), 3),
                                                                        spec.hole_h],
                       "count_lod0": len(infos[0]["body"]["holes"])}
    return builders, infos, packing, lm_packing


def make_materials(spec):
    mp = bpy.data.materials.new(spec.material_paint)
    ms = bpy.data.materials.new(spec.material_steel)
    return mp, ms


def stage_objects(spec, builders, packing, mats, com_mm, lm_packing=None):
    """The four meshes x 3 LODs.  Part meshes are expressed in their socket frame (the pivot)."""
    frames = FB.socket_frames(spec, com_mm)
    fr_pin = FB.frame_matrix(*frames["Pin"])
    fr_lev = FB.frame_matrix(*frames["LeverHinge"])
    out = {}
    specs = [("assembled", spec.mesh_name, None, None, list(mats)),
             ("body", spec.body_mesh, FB.PART_SETS["body"], None, list(mats)),
             ("pullring", spec.ring_mesh, FB.PART_SETS["pullring"], fr_pin, list(mats)),
             ("lever", spec.lever_mesh, FB.PART_SETS["lever"], fr_lev, list(mats))]
    for key, name, parts, frame, ms in specs:
        objs = []
        for lod, mb in enumerate(builders):
            nm = name if lod == 0 else f"{name}_LOD{lod}"
            assert_clean(nm)
            objs.append(FB.to_blender(mb, packing, nm, parts=parts, frame=frame, materials=ms, lm_packing=lm_packing))
        # part meshes carry only the Steel slot's faces: drop the empty Paint slot so their FBX has ONE section
        if key in ("pullring", "lever"):
            for o in objs:
                mi = np.empty(len(o.data.polygons), np.int32)
                o.data.polygons.foreach_get("material_index", mi)
                assert (mi == 1).all(), key
                o.data.materials.pop(index=0)
                o.data.polygons.foreach_set("material_index", np.zeros(len(mi), np.int32))
        out[key] = objs
    return out, frames


# =========================================================================== collision
def _hull_object(name, pts_m, parent):
    bm = bmesh.new()
    for p in pts_m:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    inner = [v for v in bm.verts if not v.link_faces]
    if inner:
        bmesh.ops.delete(bm, geom=inner, context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
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


def _verts_mm(objs, parts=None, builder=None):
    return np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs]) * 1000.0


def hull_points(spec, builders):
    """Analytic hulls that CONTAIN their parts by construction (plan 6.1)."""
    allv = {}
    for mb in builders:
        V = np.array(mb.verts)
        for f in mb.faces:
            allv.setdefault(f.part, set()).update(f.v)
    pts_by_part = {}
    for mb in builders:
        V = np.array(mb.verts)
        for part in ("tube", "sleeve", "cap", "fuze", "lever", "ring", "pin"):
            ids = sorted({i for f in mb.faces if f.part == part for i in f.v})
            if ids:
                pts_by_part.setdefault(part, []).append(V[ids])
    P = {k: np.concatenate(v) for k, v in pts_by_part.items()}
    # canister: circumscribed 16-gon prism, z 0 .. the sleeve's top
    body = np.concatenate([P["tube"], P["sleeve"], P["cap"]])
    rmax = float(np.hypot(body[:, 0], body[:, 1]).max())
    zt = float(body[:, 2].max())
    R = rmax / math.cos(math.pi / 16) + 0.01
    can = [(R * math.cos(2 * math.pi * k / 16 + math.pi / 16), R * math.sin(2 * math.pi * k / 16 + math.pi / 16), z)
           for z in (float(body[:, 2].min()) - 0.01, zt + 0.01) for k in range(16)]
    # fuze: circumscribed octagon prism over the collar + a box over everything above it
    f = P["fuze"]
    low = f[f[:, 2] <= spec.collar_z1 + 1e-6]
    high = f[f[:, 2] > spec.collar_z1 + 1e-6]
    rc = float(np.hypot(low[:, 0], low[:, 1]).max()) / math.cos(math.pi / 8) + 0.01
    fz = [(rc * math.cos(2 * math.pi * k / 8 + math.pi / 8), rc * math.sin(2 * math.pi * k / 8 + math.pi / 8), z)
          for z in (float(low[:, 2].min()) - 0.01, spec.collar_z1 + 0.01) for k in range(8)]
    lo_, hi_ = high.min(axis=0) - 0.01, high.max(axis=0) + 0.01
    fz += [(x, y, z) for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (spec.collar_z1 - 0.3, hi_[2])]
    # lever: the lower straight's box + the upper straight / curl box (the joggle lies between them)
    lv = P["lever"]
    zj = spec.lever_joggle_z[1]
    a = lv[lv[:, 2] <= zj + 1e-6]
    b = lv[lv[:, 2] > zj + 1e-6]
    lev = []
    for part in (a, b):
        lo_, hi_ = part.min(axis=0) - 0.01, part.max(axis=0) + 0.01
        lev += [(x, y, z) for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (lo_[2], hi_[2])]
    ring = np.concatenate([P["ring"], P["pin"]])
    return {"canister": np.array(can), "fuze": np.array(fz), "lever": np.array(lev), "ring": ring, "all": P}


def _inside_hull_dist(hull_obj, pts_m):
    """Largest distance (m) of points outside a convex hull object (plane test)."""
    me = hull_obj.data
    planes = []
    M = hull_obj.matrix_world
    for poly in me.polygons:
        n = (M.to_3x3() @ poly.normal).normalized()
        c = M @ poly.center
        planes.append((np.array(n), float(np.dot(np.array(n), np.array(c)))))
    d = np.full(len(pts_m), -1e9)
    for n, c in planes:
        d = np.maximum(d, pts_m @ n - c)
    return d


def stage_finish(spec, objs, frames, builders, report):
    hp = hull_points(spec, builders)
    MMm = 0.001
    hulls = {}
    # assembled: 3 hulls; body: 2; parts: 1 each
    lod0 = objs["assembled"][0]
    hulls["assembled"] = [_hull_object(f"UCX_{lod0.name}_{i:02d}", hp[k] * MMm, lod0)
                          for i, k in enumerate(("canister", "fuze", "lever"))]
    # plan 6.1: the ring protrudes > 3 mm from the three hulls (it hangs ~17 mm off the sleeve), so a thin fourth
    # hull - the ring + pin's oriented bounding box (PCA axes, 8 vertices) - keeps it out of the floor when the
    # grenade lies on its ring side
    rp = hp["ring"]
    c = rp.mean(axis=0)
    _u, _s, vt = np.linalg.svd(rp - c, full_matrices=False)
    loc = (rp - c) @ vt.T
    lo_, hi_ = loc.min(axis=0) - 0.01, loc.max(axis=0) + 0.01
    obb = np.array([[x, y, z] for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (lo_[2], hi_[2])]) @ vt + c
    hulls["assembled"].append(_hull_object(f"UCX_{lod0.name}_03", obb * MMm, lod0))
    b0 = objs["body"][0]
    hulls["body"] = [_hull_object(f"UCX_{b0.name}_{i:02d}", hp[k] * MMm, b0) for i, k in enumerate(("canister", "fuze"))]
    fr_pin = FB.frame_matrix(*frames["Pin"])
    fr_lev = FB.frame_matrix(*frames["LeverHinge"])
    r0 = objs["pullring"][0]
    Rl = np.array([v.co[:] for o in objs["pullring"] for v in o.data.vertices])
    lo_, hi_ = Rl.min(axis=0) - 1e-5, Rl.max(axis=0) + 1e-5
    box = [(x, y, z) for x in (lo_[0], hi_[0]) for y in (lo_[1], hi_[1]) for z in (lo_[2], hi_[2])]
    hulls["pullring"] = [_hull_object(f"UCX_{r0.name}_00", np.array(box), r0)]
    l0 = objs["lever"][0]
    inv = np.array(fr_lev.inverted())
    levp = (inv[:3, :3] @ (hp["lever"] * MMm).T).T + inv[:3, 3]
    hulls["lever"] = [_hull_object(f"UCX_{l0.name}_00", levp, l0)]
    # containment gates
    rep = {}
    for key, hl in hulls.items():
        pts = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs[key]])
        if key in ("assembled",):
            # the ring and pin are exempt (plan 6.1): test every other vertex
            ring_ids = []
            pts_all = []
            for o in objs[key]:
                pass
        d = np.min(np.stack([_inside_hull_dist(h, pts) for h in hl]), axis=0)
        rep[key] = {"hulls": [h.name for h in hl], "vertices_per_hull": [len(h.data.vertices) for h in hl],
                    "worst_outside_mm_all_vertices": round(float(d.max()) * 1000, 4)}
    # assembled / body: everything but the ring and pin must be inside (<= 0.5 mm)
    nonring = np.concatenate([hp["all"][k] for k in ("tube", "sleeve", "cap", "fuze", "lever")]) * MMm
    d = np.min(np.stack([_inside_hull_dist(h, nonring) for h in hulls["assembled"]]), axis=0)
    rep["assembled"]["worst_outside_mm_non_ring"] = round(float(d.max()) * 1000, 4)
    ringd = np.min(np.stack([_inside_hull_dist(h, hp["ring"] * MMm) for h in hulls["assembled"]]), axis=0)
    rep["assembled"]["ring_protrusion_mm"] = round(float(ringd.max()) * 1000, 3)
    rep["assembled"]["ring_note"] = ("plan 6.1: a fourth thin hull (_03, the ring + pin's oriented box) was added "
                                     "because the ring stands ~17 mm outside the three body hulls; the protrusion "
                                     "above is measured against all four")
    h3 = np.min(np.stack([_inside_hull_dist(h, hp["ring"] * MMm) for h in hulls["assembled"][:3]]), axis=0)
    rep["assembled"]["ring_protrusion_mm_three_hulls"] = round(float(h3.max()) * 1000, 3)
    bodyp = np.concatenate([hp["all"][k] for k in ("tube", "sleeve", "cap", "fuze")]) * MMm
    d = np.min(np.stack([_inside_hull_dist(h, bodyp) for h in hulls["body"]]), axis=0)
    rep["body"]["worst_outside_mm_body_vertices"] = round(float(d.max()) * 1000, 4)
    rep["gate_contained"] = bool(rep["assembled"]["worst_outside_mm_non_ring"] <= 0.5
                                 and rep["body"]["worst_outside_mm_body_vertices"] <= 0.5
                                 and rep["pullring"]["worst_outside_mm_all_vertices"] <= 0.5
                                 and rep["lever"]["worst_outside_mm_all_vertices"] <= 0.5)
    hcom, hvol = FB.hull_com(hulls["assembled"][:3])
    rep["hull_volume_cm3"] = round(hvol * 1e6, 2)
    rep["hull_centroid_mm"] = hcom
    report["collision"] = rep
    # sockets on the assembled and body LOD0
    socks = []
    for key in ("assembled", "body"):
        o = objs[key][0]
        for sd in spec.sockets:
            pos, rot = frames[sd.name]
            make_socket(o, sd.name, tuple(v * MMm for v in pos), tuple(math.radians(a) for a in rot))
            if key == "assembled":
                socks.append({"name": sd.name, "position_mm": list(pos), "rotation_deg": list(rot), "rule": sd.rule,
                              "use": sd.use})
    report["sockets"] = socks
    groups = {}
    for key, name in (("assembled", spec.mesh_name), ("body", spec.body_mesh), ("pullring", spec.ring_mesh),
                      ("lever", spec.lever_mesh)):
        groups[key] = make_lod_group(name, objs[key])
    return groups, hulls


# =========================================================================== textures
def stage_textures(spec, objs, packing, mats, report, quick=False):
    size = spec.atlas_px
    lod0 = objs["assembled"][0]
    log("baking inputs (Cycles, LOD0 alone)")
    bk = FP.bake_inputs(lod0, size, samples=8 if quick else 32, log=log)
    log("painting")
    look = FP.LOOK
    maps, stats = FP.paint(bk, spec, packing, look, log=log)
    cover = maps["cover"]
    isl_tab = FB.island_index_table(packing)
    ppmm = {i: packing.place[n][4] for n, i in isl_tab.items()}
    det = FP.detail_normal(maps["height"], maps["island"], cover, ppmm)
    nrm = FP.combine_normals(maps["bevel_n"], det)
    # FINALISE: a used texel whose baked bevel normal points INTO the surface (a bake ray that could not leave a
    # contact, e.g. round 1's hidden housing top: (0.50, 0.50, 0.005)) is invalid - replaced by the flat normal
    bad_n = cover & (nrm[..., 2] < 0.05)
    n_bad = int(bad_n.sum())
    nrm[bad_n] = (0.0, 0.0, 1.0)
    # extend every map into the padding (EXTEND margin)
    alb = FP._grow(maps["albedo"], cover, 24)
    rough = FP._grow(maps["rough"], cover, 24)
    metal = FP._grow(maps["metal"], cover, 24)
    nrm = FP._grow(nrm, cover, 24)
    ao = maps["ao"]
    # fill never-reached texels with neutral values
    far = ~FP._grow(cover.astype(np.float32), cover, 24).astype(bool) if False else None
    TEXTURES.mkdir(parents=True, exist_ok=True)
    stem = spec.texture_stem
    flip = lambda a: np.ascontiguousarray(a[::-1])                       # bottom-up -> row 0 at the top
    bc_s = PB.linear_to_srgb(np.clip(alb, 0, 1))
    paths = {}
    paths["BC"] = PB.write_png(TEXTURES / f"{stem}_BC.png", flip(bc_s))
    metal_q = (metal > 0.5).astype(np.float32)
    orm = np.stack([np.clip(ao, 0, 1), np.clip(rough, 0.02, 1.0), metal_q], -1)
    paths["ORM"] = PB.write_png(TEXTURES / f"{stem}_ORM.png", flip(orm))
    n_enc = nrm * 0.5 + 0.5
    n_dx = n_enc.copy()
    n_dx[..., 1] = 1.0 - n_dx[..., 1]                                   # DirectX: green flipped on write
    paths["N"] = PB.write_png(TEXTURES / f"{stem}_N.png", flip(n_dx))
    # the paint's recolour Detail (fan / Snow Flower convention): sRGB-encoded linear d over the dielectric paint
    # texels (+3 px extension), one constant elsewhere
    paint = maps["paint_mask"] > 0.5
    lum = alb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    colour = alb[paint].mean(axis=0)
    a_lo, a_hi = float(np.percentile(lum[paint], 0.05)), float(np.percentile(lum[paint], 99.95))
    d = np.clip((lum - a_lo) / max(a_hi - a_lo, 1e-6), 0, 1)
    ext = FP._grow(np.where(paint, d, 0.0).astype(np.float32), paint, 3)
    ext_mask = FP._grow(paint.astype(np.float32), paint, 3) > 0.5
    d_mean = float(d[paint].mean())
    fill = round(float(PB.linear_to_srgb(np.array([d_mean]))[0]) * 255.0) / 255.0
    det8 = np.where(ext_mask, PB.linear_to_srgb(np.clip(ext, 0, 1)), fill)
    det8 = np.rint(det8 * 255.0) / 255.0
    # FINALISE: the 8-bit sRGB detail is the SOURCE of the lossless Recolour/..._Paint_Detail16 only; it is no longer
    # shipped (imported as the README said it builds as BGRA8, ~21 MB) - it stays in the build's work folder
    paths["Paint_Detail"] = PB.write_png(BUILD_WORK / f"{stem}_Paint_Detail_source8.png", flip(det8))
    lum_c = float(colour @ np.array([0.2126, 0.7152, 0.0722]))
    tex_rep = {
        "maps": {k: str(Path(v).relative_to(PROJECT)) for k, v in paths.items()},
        "sha256": {k: sha256(v) for k, v in paths.items()},
        "size": size, "power_of_two": (size & (size - 1)) == 0,
        "colour_chunks": {k: [c for c in PB.png_chunks(v) if c in ("sRGB", "gAMA", "cHRM", "iCCP")] for k, v in paths.items()},
        "paint": stats, "look": dataclasses.asdict(look),
        "paint_default_colour_linear": [round(float(x), 6) for x in colour],
        "paint_default_colour_srgb8": [int(round(float(x) * 255)) for x in PB.linear_to_srgb(colour)],
        "paint_luminance_range": [round(a_lo, 6), round(a_hi, 6)],
        "detail_fill_srgb8": int(round(fill * 255)), "detail_bias": round(a_lo / lum_c, 6),
        "detail_scale": round((a_hi - a_lo) / lum_c, 6),
        "gates": {
            "paint_dielectric_lum_max": round(float(lum[paint].max()), 5),
            "paint_dielectric_lum_below_0.18": bool(lum[paint].max() < 0.18),
            "orm_b_binary_fraction_partial": float(((orm[..., 2] > 0.02) & (orm[..., 2] < 0.98))[cover].mean()),
            "normal_invalid_texels_replaced": n_bad,
            "normal_used_texels_b_below_half_after": int((cover & (n_dx[..., 2] < 0.5)).sum()),
        },
        "how": {
            "BC": "sRGB8 of the painter's linear albedo (props_lib.flashbang_paint.paint)",
            "ORM": "R = Cycles AO of LOD0 alone (pipeline.textures.bake_ao, 16 px EXTEND); G = roughness; B = metallic "
                   "exactly 0 (paint) or 1 (chips, hole walls, every steel and brass part)",
            "N": "DirectX (green flipped on write): the tangent-space bake of a Bevel node (r 0.3 mm) on LOD0 UDN-blended "
                 "with the painter's height detail (ring-line grooves, paint step at chips, scratches, pits, seams, "
                 "panel lines) differentiated per island",
            "Paint_Detail": "recolour detail: sRGB-encoded linear d = (lum - a_lo) / (a_hi - a_lo) over the dielectric "
                            "paint texels (+3 px), one constant elsewhere (M_Fabric_Master, Metal From ORM keeps chips "
                            "and steel at their baked colour)"},
    }
    report["textures"] = tex_rep
    maps_out = {"albedo": alb, "rough": rough, "metal": metal_q, "ao": ao, "N": nrm, "paint": paint, "d": d,
                "det8": det8, "colour": colour, "a_lo": a_lo, "a_hi": a_hi, "cover": cover}
    return paths, maps_out


def stage_recolour(spec, maps, paths, report):
    """Detail16 (a lossless 16-bit linear copy of the Paint Detail) + recolour_maps.json (v1 fields), fan convention."""
    import importlib.util
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        sp = importlib.util.spec_from_file_location(
            "np_recolour_common_ro", str(PROJECT / "Scripts/unreal/materials/maps/recolour_common.py"))
        rc = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(rc)
    finally:
        sys.dont_write_bytecode = old
    RECOLOUR.mkdir(parents=True, exist_ok=True)
    det8 = maps["det8"]
    lev = np.rint(det8 * 255.0).astype(np.int64)
    dec = rc.s2l(lev / 255.0)
    d16 = np.rint(dec * 65535.0) / 65535.0
    p16 = PB.write_png(RECOLOUR / f"{spec.texture_stem}_Paint_Detail16.png", np.ascontiguousarray(d16[::-1]), bits=16)
    back8 = np.rint(rc.l2s(np.rint(dec * 65535.0) / 65535.0) * 255.0).astype(np.int64)
    lossless = bool((back8 == lev).all())
    colour = maps["colour"]
    lum_c = float(colour @ rc.LUM)
    bias = maps["a_lo"] / lum_c
    scale = (maps["a_hi"] - maps["a_lo"]) / lum_c
    covered = maps["paint"]
    n = bias + scale * dec[covered]
    kc = rc.fabric_constants(n)
    name = f"{spec.texture_stem}_Paint_Detail16"
    out = {"schema": "ninjapack.recolour_maps/1", "item": "Flashbang", "generated": time.strftime("%Y-%m-%d"),
           "generator": {"script": "Scripts/props/build_flashbang.py", "script_sha256": sha256(__file__),
                         "module": "Scripts/props/props_lib/flashbang_paint.py",
                         "module_sha256": sha256(PROJECT / "Scripts/props/props_lib/flashbang_paint.py"),
                         "version": LIB_VERSION, "blender": bpy.app.version_string},
           "sidecar": {"file": "Exports/Flashbang/SM_Flashbang.sockets.json"},
           "maps": {name: {"file": f"Exports/Flashbang/Textures/Recolour/{name}.png", "sha256": sha256(p16),
                           "size": list(d16.shape), "format": "PNG, 16-bit greyscale, no colour chunks, row 0 = top",
                           "encoding": "LINEAR: value / 65535 = the linear detail d (sRGB-decoded shipped Detail)",
                           "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                                             "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                                             "address": "Wrap"},
                           "source": {"file": str(Path(paths["Paint_Detail"]).relative_to(PROJECT)).replace("\\", "/"),
                                      "sha256": sha256(paths["Paint_Detail"]), "stored_levels": int(len(np.unique(lev)))},
                           "recipe": "d16 = round(65535 * sRGBdecode(Detail8 / 255)); lossless (one code per 8-bit level)",
                           "gates": {"lossless_back_to_8bit": lossless}}},
           "parts": {"Paint": {"slot_material": spec.material_paint, "instance": "MI_Flashbang_Paint",
                               "master": "M_Fabric_Master", "detail_map": name,
                               "switches": {"Metal From ORM": True, "Cloth Sheen": False, "Use Lettering": False,
                                            "Specular From ORM Alpha": False},
                               "base_colour_map_reference": {"file": f"Exports/Flashbang/Textures/{spec.texture_stem}_BC.png",
                                                             "sha256": sha256(paths["BC"])},
                               "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0],
                                          "Detail Bias": round(bias, 6), "Detail Scale": round(scale, 6),
                                          "Detail Mean": kc["mean"], "Detail Highlight Ratio": kc["highlight_ratio"],
                                          "Detail Moments Low": kc["moments_low"], "Detail Moments High": kc["moments_high"],
                                          "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING,
                                          "Specular Strength": 0.5},
                               "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
                               "covered_texels": int(covered.sum()),
                               "fill_level": int(round(float(maps["det8"][~FP._grow(covered.astype(np.float32), covered, 3).astype(bool)].mean()) * 255))
                               if (~covered).any() else None,
                               "param_notes": {"Colour": "linear RGBA; the paint's MEAN colour over its dielectric texels "
                                                         "(default = the reference olive)"},
                               "derivation": "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail)) on the paint; "
                                             "Metal From ORM keeps the baked BC and metal where ORM.B = 1 (chips, walls); "
                                             "v1 fields over the COVERED (paint) texels; recolour_constants.json (v2) is "
                                             "written by the Finalise step under the materials lock"}},
           # FINALISE: "parts" lists only the recolourable part (np_spec.load_recolour reads every part that names an
           # instance and expects its params); the Steel slot is described here instead
           "other_slots": {"Steel": {"slot_material": spec.material_steel, "steel_instance": "MI_Flashbang_Steel",
                                     "master": "M_Steel_Master", "recolourable": False,
                                     "note": "optional Steel Tint only (white = as shipped); covers the fuze, collar, "
                                             "base cap, lever, ring, pin and the brass cans (their colour is in BC)"}}}
    out["pass"] = lossless
    path = RECOLOUR / "recolour_maps.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    report["recolour"] = {"file": str(path.relative_to(PROJECT)), "detail16": str(Path(p16).relative_to(PROJECT)),
                          "lossless": lossless, "colour_linear": out["parts"]["Paint"]["params"]["Colour"],
                          "detail_mean": kc["mean"]}
    paths["Paint_Detail16"] = p16


def assign_preview(objs, paths, spec):
    from props_lib import flashbang_look as LK
    mp, ms = LK.preview_materials(paths, spec.material_paint, spec.material_steel)
    for key, ol in objs.items():
        for o in ol:
            names = [m.name for m in o.data.materials]
            mi = np.empty(len(o.data.polygons), np.int32)
            o.data.polygons.foreach_get("material_index", mi)
            o.data.materials.clear()
            if len(names) == 2:
                o.data.materials.append(mp)
                o.data.materials.append(ms)
            else:
                o.data.materials.append(ms)
            o.data.polygons.foreach_set("material_index", mi)      # materials.clear() reset them
            o.data.update()
    return mp, ms


# =========================================================================== measure
def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


def bounds_radius_mm(objs):
    co = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs]) * 1000.0
    c = 0.5 * (co.min(axis=0) + co.max(axis=0))
    return float(np.linalg.norm(co - c, axis=1).max()), co


def uv_stats(o, tex):
    me = o.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.array([v.co[:] for v in me.vertices]) * 1000.0
    tl = np.array([t.loops[:] for t in me.loop_triangles])
    tv = np.array([t.vertices[:] for t in me.loop_triangles])
    tuv = uv[tl]
    tco = co[tv]
    a_uv = 0.5 * ((tuv[:, 1, 0] - tuv[:, 0, 0]) * (tuv[:, 2, 1] - tuv[:, 0, 1]) -
                  (tuv[:, 2, 0] - tuv[:, 0, 0]) * (tuv[:, 1, 1] - tuv[:, 0, 1]))
    n3 = np.cross(tco[:, 1] - tco[:, 0], tco[:, 2] - tco[:, 0])
    a3 = 0.5 * np.linalg.norm(n3, axis=1)
    e1, e2 = tco[:, 1] - tco[:, 0], tco[:, 2] - tco[:, 0]
    d1, d2 = tuv[:, 1] - tuv[:, 0], tuv[:, 2] - tuv[:, 0]
    det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    det = np.where(np.abs(det) < 1e-20, 1e-20, det)
    dpu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
    dpv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
    hand = (np.cross(dpu, dpv) * n3).sum(axis=1)
    return {"uv_range": [round(float(uv.min()), 6), round(float(uv.max()), 6)],
            "collapsed_uv_triangles": int((np.abs(a_uv) < 1e-12).sum()),
            "mirrored_uv_triangles": int((hand < 0).sum()),
            "min_triangle_area_mm2": round(float(a3.min()), 6),
            "texel_density_px_per_cm": round(float(math.sqrt(np.abs(a_uv).sum() / a3.sum()) * tex * 10.0), 3)}


def visible_deviation(objs, looks_visible=(0, 1, 4, 5)):
    """Points on LOD0's visible outer surfaces (every face of a visible LOOK, 4 samples per triangle) -> distance
    to each LODn (mm), and LODn's vertices -> LOD0 (mm)."""
    o0 = objs[0]
    me = o0.data
    me.calc_loop_triangles()
    V = np.array([v.co[:] for v in me.vertices])
    lk = np.empty(len(me.polygons), np.int32)
    me.attributes["fb_look"].data.foreach_get("value", lk)
    pts = []
    for t in me.loop_triangles:
        if lk[t.polygon_index] in looks_visible:
            a, b, c = (V[i] for i in t.vertices)
            for w in ((1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)):
                pts.append(w[0] * a + w[1] * b + w[2] * c)
    pts = np.array(pts)
    out = {}
    for i, o in enumerate(objs[1:], start=1):
        m = o.data
        m.calc_loop_triangles()
        tree = BVHTree.FromPolygons([v.co.copy() for v in m.vertices], [tuple(t.vertices) for t in m.loop_triangles])
        d = np.array([(tree.find_nearest(tuple(p))[3] or 0.0) for p in pts]) * 1000.0
        out[f"LOD{i}"] = {"p50": round(float(np.percentile(d, 50)), 4), "p95": round(float(np.percentile(d, 95)), 4),
                          "p99": round(float(np.percentile(d, 99)), 4), "max": round(float(d.max()), 4),
                          "points": int(len(pts))}
    return out


def stage_measure(spec, objs, packing, mass, report):
    tex = spec.atlas_px
    rep = {}
    for key, ol in objs.items():
        tris = [tri_count(o) for o in ol]
        rad, co = bounds_radius_mm(ol[:1])
        ent = {"triangles": tris, "descending": all(tris[i] > tris[i + 1] for i in range(len(tris) - 1)),
               "bounds_radius_mm": round(rad, 3), "screen_sizes": spec.lod_screen_sizes(rad),
               "switch_distances_m": spec.switch_distances_m(rad),
               "bounds_mm": {"min": [round(float(x), 3) for x in co.min(axis=0)],
                             "max": [round(float(x), 3) for x in co.max(axis=0)]},
               "uv": {f"LOD{i}": uv_stats(o, tex) for i, o in enumerate(ol)},
               "faces_per_slot": [[int(c) for c in np.bincount(
                   np.array([p.material_index for p in o.data.polygons]), minlength=len(o.data.materials))]
                   for o in ol],
               "slots": [m.name for m in ol[0].data.materials]}
        rep[key] = ent
    a = rep["assembled"]["triangles"]
    parts_sum = [rep["body"]["triangles"][i] + rep["pullring"]["triangles"][i] + rep["lever"]["triangles"][i]
                 for i in range(3)]
    rep["parts_sum_equals_assembled"] = parts_sum == a
    band = [list(l.tri_band) for l in spec.lods]
    rep["assembled"]["in_band"] = [band[i][0] <= a[i] <= band[i][1] for i in range(3)]
    dev = visible_deviation(objs["assembled"])
    ss = rep["assembled"]["screen_sizes"]
    rad = rep["assembled"]["bounds_radius_mm"]
    for i in (1, 2):
        lim = 1.0 / (ss[i] * 1080.0 / (2.0 * rad))
        dev[f"LOD{i}"]["limit_p99_mm_one_px_at_switch"] = round(lim, 4)
        dev[f"LOD{i}"]["pass"] = dev[f"LOD{i}"]["p99"] <= lim
    rep["visible_deviation_mm"] = dev
    # scale checks (plan 11.1)
    co0 = np.array([v.co[:] for v in objs["assembled"][0].data.vertices]) * 1000.0
    lk = np.empty(len(objs["assembled"][0].data.polygons), np.int32)
    objs["assembled"][0].data.attributes["fb_look"].data.foreach_get("value", lk)
    rep["scale"] = {"D_mm": D_MM, "mm_per_D": D_MM, "overall_height_mm": round(float(co0[:, 2].max() - co0[:, 2].min()), 3),
                    "overall_height_D": round(float(co0[:, 2].max() - co0[:, 2].min()) / D_MM, 4),
                    "spec_overall_height_D": 3.77}
    rep["mass"] = mass
    report["measure"] = rep
    report["lod_triangles"] = a


def stage_qa(spec, groups, objs, report):
    res = {}
    all_pass = True
    for key, ol in objs.items():
        names = [o.name for o in ol]
        target = report["measure"][key]["uv"]["LOD0"]["texel_density_px_per_cm"]
        r = qa_check(names, budget_tris=spec.lods[0].tri_band[1], texel_density=target, tolerance=0.25,
                     require_uv1=True, require_ucx=True, overlap_method="sat")
        failed = [c for c in r["checks"] if not c["passed"]]
        for c in failed:
            log(f"  QA FAIL {key} {c['name']} on {c['object']}: {c['detail']}")
        res[key] = {"passed": r["passed"], "checks": len(r["checks"]), "failed": [
            {"name": c["name"], "object": c["object"], "detail": c["detail"]} for c in failed],
            "triangles": r["triangles"], "informational": [c for c in r["checks"] if "boundary" in c["name"]][:4]}
        all_pass = all_pass and r["passed"]
        log(f"qa_check {key}: {'PASS' if r['passed'] else 'FAIL'} ({len(r['checks']) - len(failed)}/{len(r['checks'])})")
    report["qa"] = {"passed": all_pass, "per_mesh": res}
    return all_pass


def stage_export(spec, groups, objs, frames, report):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    rep = {}
    px, pz = spec.pin_c
    pin_travel = round((spec.block_y[1] - 1.0) - spec.pin_boss_y1 + 2.0, 2)        # ROUND 2: boss outer end
    for key, name in (("assembled", spec.mesh_name), ("body", spec.body_mesh), ("pullring", spec.ring_mesh),
                      ("lever", spec.lever_mesh)):
        fbx = EXPORTS / f"{name}.fbx"
        ss = report["measure"][key]["screen_sizes"]
        r = export_fbx(str(fbx), [groups[key].name], kind="static", lod_screen_sizes=ss)
        side = r["sidecar"]
        payload = json.loads(Path(side).read_text(encoding="utf-8"))
        payload["mass_kg"] = {"assembled": spec.physics_mass_kg, "body": round(spec.physics_mass_kg - spec.lever_mass_kg
                                                                                 - spec.ring_mass_kg, 3),
                              "pullring": spec.ring_mass_kg, "lever": spec.lever_mass_kg}[key]
        payload["use_ccd"] = key in ("assembled", "body")
        if key in ("assembled", "body"):
            payload["parts"] = {
                "PullRing": {"mesh": spec.ring_mesh, "attach_socket": "Pin", "relative_transform": "identity",
                             "pull_axis": "socket +X", "pin_travel_mm": pin_travel, "mass_kg": spec.ring_mass_kg},
                "Lever": {"mesh": spec.lever_mesh, "attach_socket": "LeverHinge", "relative_transform": "identity",
                          "open_axis": "socket Y", "open_sign_ue": "+pitch", "release_angle_deg": 100,
                          "mass_kg": spec.lever_mass_kg}}
        else:
            payload["pivot"] = {"pullring": "the Pin socket frame of SM_Flashbang / _Body",
                                "lever": "the LeverHinge socket frame of SM_Flashbang / _Body"}[key]
        payload["material"] = {
            "slots": (["0 M_Flashbang_Paint -> MI_Flashbang_Paint (M_Fabric_Master, Metal From ORM ON)",
                       "1 M_Flashbang_Steel -> MI_Flashbang_Steel (M_Steel_Master)"]
                      if key in ("assembled", "body") else ["0 M_Flashbang_Steel -> MI_Flashbang_Steel (M_Steel_Master)"]),
            "textures": {"BC": f"{spec.texture_stem}_BC (sRGB)", "ORM": f"{spec.texture_stem}_ORM (linear: R AO, G "
                                                                         "roughness, B metallic 0/1)",
                         "N": f"{spec.texture_stem}_N (DirectX, flip green OFF)",
                         "Paint_Detail16": f"{spec.texture_stem}_Paint_Detail16 (linear G16, the recolour detail)"},
            "paint_default_colour_linear": (report.get("textures") or {}).get("paint_default_colour_linear")}
        Path(side).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rep[key] = {"fbx": str(fbx.relative_to(PROJECT)), "sidecar": str(Path(side).relative_to(PROJECT)),
                    "objects": r["objects"], "warnings": r["warnings"], "lod_screen_sizes": r["lod_screen_sizes"],
                    "sockets": r["sockets"], "sha256": {"fbx": sha256(fbx), "sidecar": sha256(side)},
                    "bytes": fbx.stat().st_size}
        log(f"exported {fbx.name} ({fbx.stat().st_size} bytes)")
    report["export"] = rep
    report["pin_travel_mm"] = pin_travel


def assembly_identity(objs, frames):
    """Blender check (plan 11.3): the part meshes placed at their socket frames reproduce the assembled LOD0's
    ring / pin / lever vertices."""
    out = {}
    a0 = objs["assembled"][0]
    A = np.array([v.co[:] for v in a0.data.vertices])
    tree = BVHTree.FromPolygons([Vector(p) for p in A], [tuple(p.vertices) for p in a0.data.polygons])
    for key, sname in (("pullring", "Pin"), ("lever", "LeverHinge")):
        M = np.array(FB.frame_matrix(*frames[sname]))
        P = np.array([v.co[:] for v in objs[key][0].data.vertices])
        W = (M[:3, :3] @ P.T).T + M[:3, 3]
        d = np.array([np.min(np.linalg.norm(A - w, axis=1)) for w in W]) * 1000.0
        out[key] = {"max_mm": round(float(d.max()), 6), "pass": bool(d.max() <= 0.01)}
    return out


def lever_open_sign(objs, frames):
    """Plan 11.4 (Blender side): a NEGATIVE rotation about the LeverHinge's local +Y (= +pitch in Unreal) swings the
    lever's tip outward (+X in the socket frame)."""
    P = np.array([v.co[:] for v in objs["lever"][0].data.vertices])
    tip = P[np.argmin(P[:, 2])]
    R = np.array(Matrix.Rotation(math.radians(-100.0), 3, "Y"))
    t2 = R @ tip
    return {"tip_before_mm": [round(float(x) * 1000, 3) for x in tip], "tip_after_mm": [round(float(x) * 1000, 3) for x in t2],
            "outward": bool(t2[0] > tip[0])}


# =========================================================================== gates
def collect_gates(report) -> dict:
    g = {}
    m = report.get("measure") or {}
    g["01_qa_check_all_four"] = bool((report.get("qa") or {}).get("passed"))
    g["02_lod0_within_cap_6000"] = bool(m) and m["assembled"]["triangles"][0] <= 6000
    g["03_lods_descend_all_four"] = bool(m) and all(m[k]["descending"] for k in ("assembled", "body", "pullring", "lever"))
    g["04_parts_sum_equals_assembled"] = bool(m.get("parts_sum_equals_assembled"))
    uv = [v for k in ("assembled", "body", "pullring", "lever") for v in (m.get(k) or {}).get("uv", {}).values()]
    g["05_no_collapsed_uv"] = bool(uv) and all(u["collapsed_uv_triangles"] == 0 for u in uv)
    g["06_no_mirrored_uv"] = bool(uv) and all(u["mirrored_uv_triangles"] == 0 for u in uv)
    g["07_uv_inside_0_1"] = bool(uv) and all(u["uv_range"][0] >= -1e-6 and u["uv_range"][1] <= 1 + 1e-6 for u in uv)
    g["08_no_triangle_unreal_would_drop"] = bool(uv) and all(u["min_triangle_area_mm2"] >= 0.005 for u in uv)
    g["09_collision_contains"] = bool((report.get("collision") or {}).get("gate_contained"))
    g["10_five_sockets"] = len(report.get("sockets") or []) == 5
    tex = report.get("textures") or {}
    g["11_maps_pot_no_colour_chunks"] = bool(tex.get("power_of_two")) and not any(v for v in (tex.get("colour_chunks") or {}).values())
    g["12_paint_dielectric_lum_below_0.18"] = bool((tex.get("gates") or {}).get("paint_dielectric_lum_below_0.18"))
    g["13_recolour_detail16_lossless"] = bool((report.get("recolour") or {}).get("lossless"))
    dv = m.get("visible_deviation_mm") or {}
    g["14_lod_visible_deviation_under_1px"] = bool(dv) and all(v.get("pass") for v in dv.values())
    g["15_assembly_identity"] = bool(report.get("assembly_identity")) and all(v["pass"] for v in report["assembly_identity"].values())
    g["16_lever_opens_outward"] = bool((report.get("lever_open") or {}).get("outward"))
    fr = report.get("frozen") or {}
    g["17_frozen_unchanged"] = bool(fr.get("after")) and not fr["after"]["differing_or_missing"]
    names = [report.get("asset")] + [o for k in ("export",) for v in (report.get(k) or {}).values() for o in v.get("objects", [])]
    g["18_no_franchise_string"] = not deny_hits(*[n for n in names if n])
    fps = {k: (m.get(k) or {}).get("faces_per_slot") for k in ("assembled", "body", "pullring", "lever")}
    g["20_no_invalid_normal_texel"] = (tex.get("gates") or {}).get("normal_used_texels_b_below_half_after") == 0
    rm = (report.get("renders") or {}).get("row_metrics") or {}
    if rm:
        g["21_no_background_through_the_body"] = all((rm.get(v) or {}).get("see_through_px", 1) == 0
                                                       for v in ("v1", "v2", "v3", "v4"))
    lp = (report.get("renders") or {}).get("lod_pop") or {}
    if lp:
        g["22_lod_pop_under_2pct"] = bool(lp.get("pass"))
    if "coverage_pass" in (report.get("renders") or {}):
        g["23_gallery_renders_show_the_object"] = bool(report["renders"]["coverage_pass"])
    g["19_every_slot_used_on_every_lod"] = bool(m) and all(
        v and all(len(lod) == (2 if k in ("assembled", "body") else 1) and all(c > 0 for c in lod) for lod in v)
        for k, v in fps.items())
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default=",".join(ALL_STAGES))
    p.add_argument("--quick", action="store_true")
    p.add_argument("--dev-dir", default=None)
    p.add_argument("--report-name", default="flashbang_report.json")
    return p.parse_args(argv)


def main(argv=None):
    global ASSETS, EXPORTS, TEXTURES, RECOLOUR, RENDERS, WORK, BUILD_WORK, R1
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    if args.dev_dir:
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, BUILD_WORK = dev / "Assets", dev / "Exports", dev / "Renders", dev / "build"
        TEXTURES, RECOLOUR = EXPORTS / "Textures", EXPORTS / "Textures" / "Recolour"
        R1 = dev / "compare"
    elif args.quick:
        raise SystemExit("--quick is a DEV flag: use it with --dev-dir")
    spec = FLASHBANG
    for d in (ASSETS, EXPORTS, TEXTURES, RENDERS, BUILD_WORK, R1):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": spec.mesh_name, "library": f"props_lib flashbang {LIB_VERSION}",
              "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
              "build_script": str(Path(__file__).relative_to(PROJECT)), "quick": bool(args.quick),
              "build_to": build_to(spec), "frozen": {"before": frozen_hashes()},
              "reference": {"file": str(REFERENCE.relative_to(PROJECT)), "sha256": sha256(REFERENCE)}}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    builders, infos, packing, lm_packing = stage_mesh(spec, report)
    mass = FB.mass_model(spec)
    mats = make_materials(spec)
    objs, frames = stage_objects(spec, builders, packing, mats, mass["com_mm"], lm_packing)
    log("objects: " + ", ".join(f"{k}: {[tri_count(o) for o in v]}" for k, v in objs.items()))
    paths = None
    if "textures" in stages:
        paths, maps = stage_textures(spec, objs, packing, mats, report, quick=args.quick)
        stage_recolour(spec, maps, paths, report)
        assign_preview(objs, paths, spec)
    report["assembly_identity"] = assembly_identity(objs, frames)
    report["lever_open"] = lever_open_sign(objs, frames)
    groups, hulls = stage_finish(spec, objs, frames, builders, report)
    stage_measure(spec, objs, packing, mass, report)
    if "qa" in stages:
        stage_qa(spec, groups, objs, report)
    if "save" in stages:
        for im in bpy.data.images:
            if im.source == "FILE" and im.filepath:
                im.pack()
        blend = ASSETS / "Flashbang.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
        report["blend"] = str(blend.relative_to(PROJECT))
        report["blend_sha256"] = sha256(blend)
        log(f"saved {blend}")
    if "export" in stages:
        stage_export(spec, groups, objs, frames, report)
    if "render" in stages and paths:
        from props_lib import flashbang_gallery as GAL
        report["renders"] = GAL.render_all(spec, objs, report, RENDERS, R1, BUILD_WORK, quick=args.quick, log=log)
    report["frozen"]["after"] = frozen_hashes()
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    if "report" in stages:
        out = (WORK if not args.dev_dir else Path(args.dev_dir) if Path(args.dev_dir).is_absolute()
               else PROJECT / args.dev_dir) / args.report_name
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        log(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
