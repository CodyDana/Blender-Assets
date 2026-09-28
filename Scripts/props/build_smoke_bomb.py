#!/usr/bin/env python
"""Build SM_SmokeBomb from scratch as ONE wound tape: LODs, UVs, maps, collision, sockets, export.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_smoke_bomb.py -- [--stages ...] [--quick] [--dev-dir DIR]

Stages (in order): mesh, textures, save, qa, export, render, report.  ``--quick`` drops the
atlas to 2048 / 1024 and the samples; it is for iterating (always with --dev-dir).  The
shipped build is the one without it.  Every number in the report is measured on what was
built.

HOW IT IS MADE (the method, and why it changed)
-----------------------------------------------
Round 3 laid the ball as separate strips on a sphere; three measured rounds showed what
that cannot do (short cut tabs, black voids, a twisted bundle for a pinwheel, flat painted
ribbons, grey piping for rolled edges, a square weave, UV stretch).  This build makes the
ball the way the real object is made:

    props_lib.smokebomb_wind   the ONE continuous tape: a buried core winding and 20 passes
                               fitted to REFERENCE_SPEC's control points (numbers only),
                               each a near-great-circle, joined behind the ball, crossing-
                               local weaves (REFERENCE_SPEC 4.4's woven cycle)
    props_lib.smokebomb_tape   the tape: a padded section with a rolled cord at each edge,
                               swept along any path, the atlas, the crevice fields and the
                               maps: BC / ORM / N and a full-range greyscale DETAIL map with
                               the default TINT
    props_lib.smokebomb_cloth  (round 2) the cloth in TAPE space (u along, t across): a plain
                               weave of warp floats and weft cross-dashes, the rolled edge
                               carrying the SAME weave with its selvedge wraps and irregular
                               knuckles, crisp sparse glints, a soft crevice with the covering
                               edge's fibres falling across it; painted in parallel worker
                               processes (Blender's bundled Python)
    props_lib.smokebomb_threads (round 2) T1-T5: curly, lifted, forked plies; T4 a curled loop
                               (round 4: the plies lie apart and split from the middle; T5 three stubs)
    props_lib.smokebomb_ball   exposure (what the viewer can see of the 9.6 m tape), the
                               lifted, bridged, draped layers, the buried-face cull, the
                               LODs from the same winding, the chunk atlas, the threads
    props_lib.smokebomb_look   M_SmokeBomb (the Unreal-reproducible graph), collision and
                               every render, from the BAKED maps only

WHAT IT READS
-------------
REFERENCE_SPEC's numbers (through smokebomb_wind_fit, smokebomb_tape's ClothSpec / THREAD_PRESETS
and the outline target).  The reference PNG is opened by exactly two things, both after the
maps are written: the side-by-side sheet and the metrics comparing the reference view with it.

WHAT IT NEVER TOUCHES
---------------------
Scripts/shuriken/**, Assets/Shuriken.blend, Exports/Shuriken/**, Renders/Shuriken/**, the paused
paper bomb (Assets/PaperBomb.blend, Exports/PaperBomb/**, Renders/PaperBomb/**, props_lib
paperbomb_art / trace / art_metrics / photo_metrics) and the generic props_lib modules (used
as they are).  The shuriken and paper bomb export hashes are checked against their recorded
lists at the start and the end.  Scripts/pipeline/** is used exactly as it is.
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
from props_lib import bake as PB                                  # noqa: E402
from props_lib import smokebomb_ball as SB                        # noqa: E402
from props_lib import smokebomb_cloth as C                        # noqa: E402
from props_lib import smokebomb_look as LK                        # noqa: E402
from props_lib import smokebomb_metrics as MT                     # noqa: E402
from props_lib import smokebomb_tape as T                         # noqa: E402
from props_lib import smokebomb_wind as W                         # noqa: E402
from props_lib.smokebomb_spec import SMOKE_BOMB, assert_clean, build_to, deny_hits  # noqa: E402

LIB_VERSION = "8.0.0"          # final pass (maintainer): shingled fan + hidden widening + span, ClothSpec6, mip-safe maps
#                               (7.0.0 = round 4: round LOD0 outline + real rolled cord, ClothSpec5, loose threads)
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "SmokeBomb"
TEXTURES = EXPORTS / "Textures"
RENDERS = PROJECT / "Renders" / "SmokeBomb"
WORK = PROJECT / "WorkFiles" / "smokebomb"
BUILD_WORK = WORK / "rewind" / "build" / "ship"
REFERENCE = PROJECT / "References" / "SmokeBomb" / "smokebomb.png"
REFERENCE_SHA = "813105ecd7192c72b20058a206ea8916912aecdba0abfa02cfb47bc9f7b6e1c2"
ALL_STAGES = ("mesh", "textures", "save", "qa", "export", "render", "report")

T0 = time.time()


def log(*parts):
    print(f"[smokebomb {time.time() - T0:7.1f}s]", *parts, flush=True)


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
    return {"checked": len(ok), "ok": int(sum(ok)), "all_ok": bool(ok) and all(ok)}


def frozen_hashes() -> dict:
    """The shuriken pack's exports + blend against WorkFiles/shuriken/regression/post_kunai_plain,
    the paper bomb's exports against its paused SHA256SUMS."""
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
    return {"shuriken": _check_sums(shu, shu_path),
            "paperbomb": _check_sums(pb, lambda rel: PROJECT / rel),
            "shuriken_live_exports": {p.name: sha256(p) for p in sorted((PROJECT / "Exports" / "Shuriken").rglob("*"))
                                      if p.is_file()}}


# =========================================================================== mesh
def stage_ball(report, rounds: int = 2):
    """The winding, the stretches, and the OUTLINE solve: the base sphere and the lift's
    low-order shape term are corrected against the ball's own analytic outline (the largest
    projected radius of the exposed surface per image angle) until it carries the reference's
    mean radius and low-order harmonics (REFERENCE_SPEC 1)."""
    spec = SB.BALL
    log("winding + stack (props_lib.smokebomb_wind.reference_winding)")
    ball = SB.Ball(spec, log=log).build()
    hist = []
    for it in range(rounds):
        out = ball.outline_report(spec.outline_harmonics)
        hist.append({k: v for k, v in out.items() if not k.startswith("_")})
        log(f"  outline round {it}: mean {out['mean_mm']:.4f} mm, harmonic error rms {out['harmonic_err_rms_px']} px")
        core = ball.spec.core_mm + (spec.outline_mm - out["mean_mm"])
        spec1 = dataclasses.replace(ball.spec, core_mm=round(core, 4))
        shape = ball.shape.with_correction(-out["_err"])
        ball = SB.Ball(spec1, log=lambda *a: None, winding=ball.wd, drape=ball.drape, shape=shape,
                       expfrac=ball.expfrac).build()
    final = ball.outline_report(spec.outline_harmonics)
    hist.append({k: v for k, v in final.items() if not k.startswith("_")})
    log(f"  outline final: mean {final['mean_mm']:.4f} mm, harmonic error rms {final['harmonic_err_rms_px']} px, "
        f"core {ball.spec.core_mm:.4f} mm")
    spec1 = ball.spec
    est1 = final
    wd = ball.wd
    report["winding"] = {
        "design": wd.notes.get("design"), "samples": int(wd.s.size),
        "length_mm": round(float(wd.s[-1]) * ball.R, 1),
        "passes": [p.name for p in wd.passes],
        "weaves": [dict(lower=w.lower, upper=w.upper if isinstance(w.upper, str) else list(w.upper), why=w.why)
                   for w in wd.weaves],
        "ends_hidden": [W.end_hidden(wd, "start"), W.end_hidden(wd, "end")],
        "source": "props_lib.smokebomb_wind.reference_winding() from props_lib.smokebomb_wind_fit (frozen)",
    }
    report["ball"] = {
        "spec": dataclasses.asdict(spec1), "outline_solve": hist,
        "outline_shape": {"source": "REF_OUTLINE_PX (typed-in measurement of the reference outline, round 3's "
                                     "instrument), harmonics 2..%d, weighted (1 - z^2) so it acts on the limb"
                                     % spec.outline_harmonics,
                           "measured_correction_px": [[round(float(a) / spec.outline_mm * SB.REF_OUTLINE_R_PX, 3),
                                                       round(float(b) / spec.outline_mm * SB.REF_OUTLINE_R_PX, 3)]
                                                      for a, b in ball.shape.measured]},
        "height_guard": {**(getattr(ball, "guard", None) or {}),
                         "what": "smokebomb_ball.Ball.guard_heights: a covering stretch's top is kept "
                                 f"{SB.GUARD_CLEAR_MM} mm + its LOD0 body-chord sag above the highest top beneath it, "
                                 f"wherever it can be seen (exposed or within {SB.GUARD_VIS_MM} mm of it)"},
        "sink": {"sink_mm": spec1.sink_mm, "ramp_mm": [SB.SINK_D0_MM, SB.SINK_D1_MM], "speck_mm": SB.SPECK_MM,
                 "what": "a buried run dives this far below its stacked height from ramp[0] to ramp[1] mm in under "
                         "its cover (hidden), so no buried vertex or cord stands through a cover's chords"},
        "stretches": len(ball.stretches),
        "exposed_tape_mm": round(sum(st.u_range[1] - st.u_range[0] for st in ball.stretches), 1),
        "exposed_area_mm2": round(sum(st.exposed_area_mm2 for st in ball.stretches), 1),
        "top_lift_mean_mm": round(ball.lift_mean_top, 4),
        "per_stretch": [{"key": st.key, "pass": st.pass_name, "samples": [st.i0, st.i1],
                         "u_mm": [round(st.u_range[0], 3), round(st.u_range[1], 3)],
                         "exposed_mm2": round(st.exposed_area_mm2, 2)} for st in ball.stretches],
        "lods": {str(k): {"cord_deg": list(v.cord_deg), "body_fracs": list(v.body_fracs), "ds_mm": v.ds_mm,
                          "groove": bool(getattr(v, "groove", True)),
                          "skirt": v.skirt, "ring_tol_mm": SB.RING_TOL_MM[k],
                          "layer_scale": spec1.lod_layer_scale[k],
                          "section_points": int(len(SB.section_points(ball.prof, v)))} for k, v in SB.LODS.items()},
        "section": dataclasses.asdict(ball.prof.spec),
    }
    return ball


def stage_faces(ball, spec, atlas_size, report):
    pad = spec.padding_px * atlas_size // 4096 if atlas_size < 4096 else spec.padding_px
    pad_mm_guess = pad / 19.0 * (4096 / atlas_size)
    reqs = []
    facesets = {}
    for st in ball.stretches:
        SB.plan_chunks(ball, st, pad_mm_guess)
        fss = [SB.lod_faces(ball, st, lod) for lod in (0, 1, 2)]
        facesets[st.key] = fss
        for c, r in enumerate(SB.chunk_t_ranges(ball, st, fss)):
            if r is not None:
                reqs.append(SB.ChunkBlock(st.key, c, st.chunks[c], st.chunks[c + 1], r[0], r[1]))
    log(f"  {len(reqs)} chunks; faces LOD0/1/2 {[sum(len(f[l].faces) for f in facesets.values()) for l in (0, 1, 2)]}")
    return facesets, reqs, pad


def stage_atlas(reqs, thread_req, size, pad, report):
    key, u0, u1, th = thread_req
    reqs = list(reqs) + [SB.ChunkBlock(key, 0, u0, u1, -th, th)]
    atlas = SB.ChunkAtlas.pack_chunks(reqs, size, pad)
    log(f"  atlas {size}: {len(atlas.blocks)} blocks, {atlas.ppmm:.3f} px/mm, fill {atlas.fill_fraction():.3f}")
    report["atlas"] = {**atlas.to_json(), "requested_area_mm2": round(sum((r.u1 - r.u0) * (r.t_hi - r.t_lo) for r in reqs), 1),
                       "layout": "one block per chunk: u along +x, t (across, centred) up the image, "
                                 "one texel = 1/ppmm mm of cloth everywhere; V = t so no island is mirrored"}
    return atlas


def _uv_handedness(verts, faces, luv):
    a, b, c = (verts[faces[:, i]] for i in range(3))
    n = np.cross(b - a, c - a)
    d1, d2 = luv[:, 1] - luv[:, 0], luv[:, 2] - luv[:, 0]
    s = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    return s, n


def stage_meshes(spec, ball, facesets, atlas, thread_parts, thread_offsets, report):
    objs = []
    rep = {}
    uv_out = 0.0
    part_store = {}
    for lod in (0, 1, 2):
        parts = []
        tris = 0
        dropped = 0
        collapsed = 0
        for st in ball.stretches:
            mp = SB.build_part(ball, st, facesets[st.key][lod], lod)
            if mp is None:
                continue
            uv = atlas.mesh_uv_part(mp)
            uv_out = max(uv_out, SB.uv_bounds_check(atlas, mp, uv)["max_outside_px"])
            parts.append((mp.verts, mp.faces, uv, mp.normals))
            tris += mp.tris
            dropped += mp.dropped
            collapsed += getattr(mp, "collapsed", 0)
        n_tape_verts = sum(len(p[0]) for p in parts)
        thr_tris = 0
        if lod == 0 and thread_parts:
            tp = T.thread_uv(atlas, thread_parts, thread_offsets, key="threads")
            fixed = []
            for (V, F, UV, NN) in tp:
                s, _n = _uv_handedness(V, F, UV)
                if np.median(s) < 0:           # a thread tube wound the other way: turn its t
                    UV = UV.copy()
                    UV[..., 1] = 2 * np.mean(UV[..., 1]) - UV[..., 1]
                fixed.append((V, F, UV, NN))
                thr_tris += int(np.sum(np.where(F[:, 3] == F[:, 2], 1, 2)))
            parts += fixed
        name = spec.mesh_name if lod == 0 else f"{spec.mesh_name}_LOD{lod}"
        assert_clean(name)
        ob = T.to_blender(parts, name)
        objs.append(ob)
        part_store[lod] = {"tape_verts": n_tape_verts}
        rep[f"LOD{lod}"] = {"parts": len(parts), "triangles_tape": tris, "triangles_threads": thr_tris,
                            "slivers_dropped_under_mm2": [SB.MIN_TRI_MM2, dropped],
                            "short_edges_collapsed_vertices": collapsed}
        log(f"  {name}: {tris + thr_tris} triangles ({len(parts)} parts, {dropped} slivers dropped)")
    rep["uv_corner_max_outside_block_px"] = round(uv_out, 3)
    rep["uv_corner_within_padding"] = bool(uv_out <= atlas.pad)
    report["mesh"] = rep
    return objs, part_store


def stage_threads(ball, report):
    parts, rep, tones = SB.thread_parts2(ball, log=log)
    req, offs = T.thread_block_request(parts)
    ranges = [(float(o), float(o + p[2][..., 0].max()), tn) for p, o, tn in zip(parts, offs, tones)]
    report["threads"] = {"presets": "props_lib.smokebomb_threads.THREAD_PRESETS2 (REFERENCE_SPEC 6: exactly T1-T5)",
                         "per_thread": rep, "lods": "LOD0 only", "tones": tones}
    ball.thread_ranges = ranges
    return parts, req, offs


# =========================================================================== textures
#: The cloth is props_lib.smokebomb_cloth.ClothSpec6 (final pass; ClothSpec5 was round 4): its defaults ARE the whole-ball
#: calibration, measured on the reference-view render of this ball against REFERENCE_SPEC's
#: instruments (tones, sparkle, warp pitch, chroma), per-patch linear statistics (p90/p10,
#: p99/p50, sparkle) and the edge profiles (rim / crevice logs along the traced edges), and
#: looked at 2-8x against the reference crops (round 4: WorkFiles/smokebomb/rewind/build5, c01 ... c21,
#: with the round-3 measurer's own instruments and a per-patch texture fingerprint, build5/tools/b5_tex.py).
#: Its tones are DETAIL units (0..1): the shipped Detail is full range by design.  Final pass: WorkFiles/smokebomb/
#: final_pass c6a ... c6e (the tells taken out: piping cords, speck / squiggle static, heather, round glints).
CLOTH_OVERRIDES_EXTRA: dict = {}          # DEV ONLY (--cloth-json): tried on top of ClothSpec6

#: M_SmokeBomb's shading (final pass, MIP-SAFE): BaseColor = Detail.R x Tint with the Detail
#: stored sRGB-encoded and imported sRGB ON (Unreal decodes before filtering and builds its mips in
#: linear light, as for BC - the round-3/4 gamma-2 Detail squared a filtered value and ran 8-29 %
#: dark at mips 1-8); Specular = 0.5 x ORM.A, ORM.A = saturate(d)^2 BAKED from the float detail
#: (the same 0.5 x d^2 as round 4's 0.5 x Detail^4, but averaged BEFORE quantisation and in every
#: mip - round 4's pow() of a filtered sample lost 13 % of the specular at the reference view and
#: 32-84 % at mips 1-8); sheen 0, Lambert diffuse
SHADING = dataclasses.replace(T.SHADING, specular=0.5, spec_detail_gain=0.0, spec_detail_power=1.0,
                              detail_power=1.0, detail_encoding="srgb", spec_mask_power=2.0)


def build_cloth() -> "C.ClothSpec6":
    kw = dict(CLOTH_OVERRIDES_EXTRA)
    base = C.ClothSpec()
    for k, v in list(kw.items()):
        if isinstance(getattr(base, k), tuple):
            kw[k] = tuple(v)
    return dataclasses.replace(base, **kw)


def bundled_python() -> str:
    """Blender's own Python (numpy, no bpy) - the painter's worker processes."""
    exe = Path(bpy.app.binary_path).parent
    ver = "%d.%d" % bpy.app.version[:2]
    cand = [exe / ver / "python" / "bin" / "python.exe", exe / ver / "python" / "bin" / "python3",
            Path(sys.executable)]
    for c in cand:
        if c.is_file() and "blender" not in c.name.lower():
            return str(c)
    return ""


PAINT_WORKERS = 24


def stage_textures(spec, ball, atlas, objs, report, quick=False):
    cloth = build_cloth()
    shading = SHADING
    log("crevices (every stretch's edges on every stretch beneath)")
    crev, crev_rep = SB.crevices(ball, atlas, log=log)
    log("painting the cloth in tape space (props_lib.smokebomb_cloth)")
    widths = {st.key: C.WidthTable(st.sweep.s, st.sweep.w, st.sweep.tape_id, st.sweep.profile, st.sweep.g)
              for st in ball.stretches}
    # supersample: enough that the warp pitch spans >= 10 samples, capped at 3x3
    ss = int(min(3, max(2, math.ceil(10.0 / (cloth.warp_pitch_mm * atlas.ppmm)))))
    py = bundled_python()
    workers = PAINT_WORKERS if py else 0
    ch = C.paint_blocks(atlas, widths, cloth, spec.seed, crev, ss, special_keys=("threads",), workers=workers,
                        thread_ranges=getattr(ball, "thread_ranges", None), python_exe=py,
                        work_dir=str(BUILD_WORK / "_paint"), log=log)
    # the atlas's rows run with t DOWN; the image stores t UP (V = t, nothing mirrored)
    chs = {k: np.ascontiguousarray(v[::-1]) for k, v in ch.items()}
    small = spec.texture_size("ORM") if not quick else atlas.size // 2
    log(f"baking ambient occlusion (Cycles, LOD0 alone, {small} px)")
    tmp = bpy.data.materials.new("M_SmokeBomb_AOBake")
    objs[0].data.materials.clear()
    objs[0].data.materials.append(tmp)
    ao_b, ao_info = PB.bake_ao_map(objs[0], small, samples=64 if quick else 192)
    objs[0].data.materials.clear()
    bpy.data.materials.remove(tmp)
    maps = SB.finish_maps(chs, cloth, atlas.ppmm, shading, small=small, geometric_ao_small=ao_b)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    paths = SB.write_maps(maps, TEXTURES, prefix=spec.texture_stem)
    mat = LK.make_material(spec.material_name, paths, maps["tint_linear"], shading)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
    ue = T.unreal_material_spec(maps, shading, prefix=spec.texture_stem)
    report["textures"] = {
        "maps": {k: str(Path(v).relative_to(PROJECT)) for k, v in paths.items()},
        "sha256": {k: sha256(v) for k, v in paths.items()},
        "sizes": maps["sizes"], "px_per_mm": round(atlas.ppmm, 4),
        "px_per_mm_orm_n": round(atlas.ppmm * maps["sizes"]["ORM"] / atlas.size, 4),
        "colour_chunks": {k: [c for c in PB.png_chunks(v) if c in ("sRGB", "gAMA", "cHRM", "iCCP")] for k, v in paths.items()},
        "power_of_two": all((s & (s - 1)) == 0 for s in maps["sizes"].values()),
        "tint_linear": [round(float(x), 6) for x in maps["tint_linear"]],
        "tint_srgb": [round(float(x), 6) for x in maps["tint_srgb"]], "L_ref": round(maps["L_ref"], 6),
        "recolour": maps["recolour"], "specular_mask": maps.get("specular_mask"),
        "albedo_stats": maps["albedo_stats"], "ao_bake": ao_info,
        "crevices": crev_rep, "supersample": ss, "cloth": dataclasses.asdict(cloth), "shading": dataclasses.asdict(shading),
        "cloth_module": "props_lib.smokebomb_cloth.ClothSpec6 (defaults = the whole-ball calibration; Detail units)",
        "cloth_dev_overrides": dict(CLOTH_OVERRIDES_EXTRA), "paint_workers": workers,
        "unreal_material": ue,
        "how_each_channel_is_made": {
            "Detail": "sRGB-ENCODED LINEAR detail, full range: sRGB(d) of the linear float detail d (0..1) "
                      "painted in TAPE space (smokebomb_cloth.cloth_texels, ClothSpec6: warp ribs with weft ticks "
                      "in most breaks and cross-dots along the picks (a thin crosshatch), elongated glints on the "
                      "crests, few curled fibres and specks, the rolled edge as the weave turning over with "
                      "irregular knuckles, sparse wraps and long stretches where it fades out, a soft crevice under "
                      "each covering edge), quantised once; import sRGB ON; linear albedo = Detail x Tint",
            "BC": "sRGB8 of sRGBdecode(Detail8 / 255) x Tint (so a material doing Detail x Tint reproduces it, "
                  "at every mip)",
            "ORM.A": "the SPECULAR mask saturate(d)^2, box-filtered from the float detail to the ORM size before "
                     "quantisation (Specular = 0.5 x ORM.A)",
            "ORM.R": "the analytic crevice / groove occlusion x a Cycles AO bake of LOD0 alone (Unreal's indirect AO)",
            "ORM.G": "roughness 0.90 +- 0.03 on the weave, 0.68 on glints and specks, 0.70 on fibres, 0.95 in "
                     "crevices", "ORM.B": "0 (cotton)",
            "N": "DirectX, from the cloth's micro height (ribs, knuckles, fibres) plus the section relief "
                 "(the true rolled cord, groove and crown minus LOD0's section chords, "
                 "smokebomb_cloth.section_relief); the macro shape is geometry"},
    }
    log(f"  tint linear {np.round(maps['tint_linear'], 5)}; recolour {maps['recolour']}")
    return mat, paths, maps


# =========================================================================== finish
def stage_finish(spec, objs, report):
    lod0 = objs[0]
    co = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs])
    r_max = float(np.linalg.norm(co, axis=1).max())
    hull = LK.make_hull(lod0, r_max)
    outside = max(LK.hull_worst_outside_m(hull, o) for o in objs)
    vol = LK.hull_volume_m3(hull)
    sockets = []
    for sd in spec.sockets:
        make_socket(lod0, sd.name, tuple(v * 0.001 for v in sd.position_mm), tuple(math.radians(a) for a in sd.rotation_deg))
        sockets.append({"name": sd.name, "position_mm": list(sd.position_mm), "rotation_deg": list(sd.rotation_deg),
                        "use": sd.use})
    group = make_lod_group(spec.mesh_name, objs)
    assert_clean(group.name, hull.name, *(o.name for o in objs))
    report["collision"] = {"hull": hull.name, "vertices": len(hull.data.vertices), "faces": len(hull.data.polygons),
                           "shape": "pentakis dodecahedron, all 60 faces tangent to the mesh's r_max",
                           "r_max_mm": round(r_max * 1000, 4), "volume_cm3": round(vol * 1e6, 3),
                           "volume_over_rmax_sphere": round(vol / (4 / 3 * math.pi * r_max ** 3), 4),
                           "worst_vertex_outside_mm_all_lods": round(outside * 1000, 7),
                           "contains_every_lod": bool(outside <= 1e-9),
                           "naming": "UCX_<render mesh NODE name>_00 (renamed with the node by make_lod_group)"}
    report["sockets"] = sockets
    return group, hull


def unreal_bounds_radius_mm(obj) -> float:
    co = np.array([v.co[:] for v in obj.data.vertices]) * 1000.0
    c = 0.5 * (co.min(axis=0) + co.max(axis=0))
    return float(np.linalg.norm(co - c, axis=1).max())


def outline_from_vertices(obj, n_bins: int = 720):
    """The reference view's outline from LOD0's vertices: max projected radius per bin."""
    co = np.array([v.co[:] for v in obj.data.vertices]) * 1000.0
    th = np.degrees(np.arctan2(co[:, 2], co[:, 0])) % 360.0
    r = np.hypot(co[:, 0], co[:, 2])
    b = np.floor(th / 360.0 * n_bins).astype(int)
    rmax = np.full(n_bins, np.nan)
    np.fmax.at(rmax, b, r)
    ok = np.isfinite(rmax)
    return {"mean_mm": round(float(np.nanmean(rmax)), 4), "min_mm": round(float(np.nanmin(rmax)), 4),
            "max_mm": round(float(np.nanmax(rmax)), 4), "rms_dev_pct": round(float(np.nanstd(rmax) / np.nanmean(rmax) * 100), 3),
            "bins_filled": int(ok.sum())}


def visible_surface_mm(ball, step: int = 3) -> np.ndarray:
    """The VISIBLE surface of the ball, all round: every stretch's exposed grid points (the
    stack says nothing lies above them) at their true top (lift + the section's top), mm."""
    out = []
    for st in ball.stretches:
        if st.exposed.any():
            Q, _u, _a = SB._exposed_top_points(ball, st, step)
            out.append(Q)
    return np.concatenate(out)


def stage_measure(spec, objs, part_store, report, ball=None):
    from mathutils.bvhtree import BVHTree
    lods = {}
    trees = []
    vis = visible_surface_mm(ball) if ball is not None else None
    for i, o in enumerate(objs):
        me = o.data
        me.calc_loop_triangles()
        V = [v.co.copy() for v in me.vertices]
        P = [tuple(t.vertices) for t in me.loop_triangles]
        trees.append((BVHTree.FromPolygons(V, P), np.array([v[:] for v in V])))
    tex = int((report.get("atlas") or {}).get("size") or spec.texture_size("BC"))
    for i, (o, band) in enumerate(zip(objs, spec.lod_bands)):
        me = o.data
        co = np.array([v.co[:] for v in me.vertices]) * 1000.0
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        tri_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
        tri_co = np.array([[co[v] for v in t.vertices] for t in me.loop_triangles])
        uv_area = 0.5 * ((tri_uv[:, 1, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 2, 1] - tri_uv[:, 0, 1])
                         - (tri_uv[:, 2, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 1, 1] - tri_uv[:, 0, 1]))
        n3 = np.cross(tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0])
        area3 = 0.5 * np.linalg.norm(n3, axis=1)
        e1, e2 = tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0]
        d1, d2 = tri_uv[:, 1] - tri_uv[:, 0], tri_uv[:, 2] - tri_uv[:, 0]
        det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
        det = np.where(np.abs(det) < 1e-20, 1e-20, det)
        dpu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
        dpv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
        hand = (np.cross(dpu, dpv) * n3).sum(axis=1)
        # UV stretch: the singular values of the texel -> surface map (1 = no stretch)
        J = np.stack([dpu, dpv], -1)                          # (F, 3, 2) mm per UV unit
        sv = np.linalg.svd(J, compute_uv=False) / (tex / max(report["atlas"]["ppmm"], 1e-9))
        stretch = sv[:, 0] / np.maximum(sv[:, 1], 1e-12)
        outward = (n3 * tri_co.mean(axis=1)).sum(axis=1) > 0
        entry = {
            "object": o.name, "triangles": len(me.loop_triangles), "vertices": len(me.vertices), "band": list(band),
            "in_band": bool(band[0] <= len(me.loop_triangles) <= band[1]),
            "bounds_mm": {"min": [round(float(x), 4) for x in co.min(axis=0)],
                          "max": [round(float(x), 4) for x in co.max(axis=0)],
                          "size": [round(float(x), 4) for x in np.ptp(co, axis=0)]},
            "max_radius_mm": round(float(np.linalg.norm(co, axis=1).max()), 4),
            "uv_range": [round(float(uv.min()), 6), round(float(uv.max()), 6)],
            "collapsed_uv_triangles": int((np.abs(uv_area) < 1e-12).sum()),
            "mirrored_uv_triangles": int((hand < 0).sum()),
            "uv_stretch_p50_p99_max": [round(float(np.percentile(stretch, 50)), 4),
                                       round(float(np.percentile(stretch, 99)), 4), round(float(stretch.max()), 4)],
            "inward_facing_triangles_informational": int((~outward).sum()),
            "min_triangle_area_mm2": round(float(area3.min()), 6),
            "texel_density_px_per_cm": round(float(math.sqrt(np.abs(uv_area).sum() / area3.sum()) * tex * 10.0), 3),
        }
        if i > 0:
            t0, v0 = trees[0]
            ti, vi = trees[i]
            nt = part_store[0]["tape_verts"]
            a = max(((t0.find_nearest(tuple(p))[3] or 0.0) for p in vi), default=0.0)
            b = max(((ti.find_nearest(tuple(p))[3] or 0.0) for p in v0[:nt]), default=0.0)
            entry["deviation_to_lod0_mm"] = {"lodn_to_lod0": round(a * 1000, 4), "lod0_tape_to_lodn": round(b * 1000, 4),
                                             "two_sided": round(max(a, b) * 1000, 4),
                                             "note": "ALL vertices, buried ones included (informational): a coarse "
                                                     "LOD keeps longer faces under the covers, whose distance to LOD0's "
                                                     "surface is a depth under another tape, not a visible change; "
                                                     "LOD0's loose threads (LOD0 only) are left out of lod0->lodn"}
        if vis is not None and i > 0:
            ti, _vi = trees[i]
            t0, _v0 = trees[0]
            # the visible points snapped onto LOD0's own surface first, so the number is LODn
            # against LOD0 (not against the analytic surface LOD0 itself approximates)
            on0 = [t0.find_nearest(tuple(p * 0.001))[0] for p in vis]
            d = np.array([((ti.find_nearest(q)[3]) or 0.0) * 1000.0 for q in on0 if q is not None])
            entry["visible_surface_deviation_mm"] = {
                "p50": round(float(np.percentile(d, 50)), 4), "p95": round(float(np.percentile(d, 95)), 4),
                "p99": round(float(np.percentile(d, 99)), 4), "max": round(float(d.max()), 4), "points": int(d.size),
                "what": "distance from LOD0's VISIBLE surface (every exposed grid point of every stretch, at its "
                        "true top, all round the ball, every 3rd point, snapped onto LOD0's mesh) to this LOD's mesh"}
        lods[f"LOD{i}"] = entry
    radius = unreal_bounds_radius_mm(objs[0])
    report["lods"] = lods
    report["lod_triangles"] = [lods[f"LOD{i}"]["triangles"] for i in range(3)]
    report["bounds_radius_mm"] = round(radius, 4)
    report["lod_screen_sizes"] = spec.lod_screen_sizes(radius)
    report["switch_distances_m"] = spec.switch_distances_m(radius)
    report["size_cm"] = [round(v / 10.0, 6) for v in lods["LOD0"]["bounds_mm"]["size"]]
    report["outline_from_lod0_vertices"] = outline_from_vertices(objs[0])
    vol_cm3 = 4.0 / 3.0 * math.pi * (spec.diameter_mm / 20.0) ** 3
    report["mass"] = {"design_g": spec.mass_g, "physics_mass_kg": spec.physics_mass_kg,
                      "ball_volume_cm3": round(vol_cm3, 2), "density_g_cm3": round(spec.mass_g / vol_cm3, 3),
                      "status": "DERIVED (study 4): tape 14.5 g + washi shell 10.6 g + dry fill 96 g"}


def stage_qa(spec, objs, report):
    names = [o.name for o in objs]
    target = report["lods"]["LOD0"]["texel_density_px_per_cm"]
    result = qa_check(names, budget_tris=spec.lod_bands[0][1], texel_density=target, tolerance=0.15,
                      require_ucx=True, overlap_method="sat")
    failed = [c for c in result["checks"] if not c["passed"]]
    for c in failed:
        log(f"  QA FAIL {c['name']} on {c['object']}: {c['detail']}")
    log(f"qa_check {'PASS' if result['passed'] else 'FAIL'} ({len(result['checks']) - len(failed)}/{len(result['checks'])})")
    report["qa"] = {"passed": result["passed"], "checks": result["checks"], "triangles": result["triangles"],
                    "texel_target_px_per_cm": target, "budget_tris": spec.lod_bands[0][1],
                    "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]} for c in failed]}
    return result


def stage_export(spec, group, report):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    fbx = EXPORTS / f"{spec.mesh_name}.fbx"
    result = export_fbx(str(fbx), [group.name], kind="static", lod_screen_sizes=report["lod_screen_sizes"])
    sidecar = result["sidecar"]
    # the recolour step reads the material block from the sidecar: the default Tint and the
    # shading the look depends on (sockets and LOD sizes are untouched)
    if sidecar:
        payload = json.loads(Path(sidecar).read_text(encoding="utf-8"))
        tex = report.get("textures") or {}
        payload["material"] = {
            "name": spec.material_name,
            "graph": (tex.get("unreal_material") or {}),
            "tint_default_linear": tex.get("tint_linear"), "tint_default_srgb": tex.get("tint_srgb"),
            "textures": {"BC": f"{spec.texture_stem}_BC (sRGB, TC_Default)",
                         "Detail": f"{spec.texture_stem}_Detail (sRGB ON, TC_Grayscale, R; sRGB-encoded linear "
                                   f"detail: BaseColor = Detail.R x Tint, equal to BC at the default Tint at every mip)",
                         "ORM": f"{spec.texture_stem}_ORM (linear, TC_Masks, RGBA: R AO, G roughness, B metallic 0, "
                                f"A specular mask: Specular = 0.5 x ORM.A)",
                         "look_depends_on": "Specular = 0.5 x ORM.A and Sheen 0. A constant Specular 0.5 greys the "
                                            "cloth (p50 +53 %, p10 +111 % at the reference view).",
                         "memory": "one material path loads BC OR Detail, not both (see the report's texture "
                                   "budget)",
                         "N": f"{spec.texture_stem}_N (TC_Normalmap, DirectX, flip green OFF)",
                         "mips": "TMGS_FROM_TEXTURE_GROUP on every map"},
        }
        Path(sidecar).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report["export"] = {
        "fbx": str(fbx.relative_to(PROJECT)),
        "sockets_sidecar": str(Path(sidecar).relative_to(PROJECT)) if sidecar else None,
        "objects": result["objects"], "warnings": result["warnings"],
        "lod_screen_sizes": result["lod_screen_sizes"], "sockets": result["sockets"],
        "axis": {"forward": result["settings"]["axis_forward"], "up": result["settings"]["axis_up"]},
        "sha256": {"fbx": sha256(fbx), "sidecar": sha256(sidecar) if sidecar else None},
        "bytes": {"fbx": fbx.stat().st_size},
    }
    log(f"exported {fbx.name} sha {report['export']['sha256']['fbx'][:16]}")


# =========================================================================== render
CROPS = {"whorl": (540, 130, 1000, 520), "belt": (330, 380, 1100, 900), "left": (150, 250, 600, 950),
         "bottom": (170, 780, 1100, 1110), "right": (780, 330, 1100, 900)}
CROPS3X = [(560, 150, 820, 330), (720, 650, 980, 830), (180, 380, 440, 560), (330, 560, 590, 740),
           (880, 380, 1140, 560), (420, 880, 680, 1060)]


def stage_render(spec, objs, report, quick=False, ref_only=False):
    RENDERS.mkdir(parents=True, exist_ok=True)
    BUILD_WORK.mkdir(parents=True, exist_ok=True)
    maps_mtime = {k: Path(PROJECT / v).stat().st_mtime for k, v in report["textures"]["maps"].items()}
    views = LK.reference_views([objs[0]], spec.diameter_mm, str(REFERENCE), RENDERS, BUILD_WORK,
                               samples=64 if quick else 512)
    if ref_only:
        ref = LK.load_png(REFERENCE)[..., :3].astype(np.float64)
        ren = LK.load_png(views["reference_view"])[..., :3].astype(np.float64)
        report["fidelity"] = {"reference": MT.measure_all(ref), "render": MT.measure_all(ren)}
        LK.crops_sheet(str(REFERENCE), views["reference_view"], BUILD_WORK / "crops_3x_bright.png", CROPS3X,
                       scale=3, bright=2.2)
        report["renders"] = {"reference_views": views, "ref_only": True}
        return
    LK.clay_reference([objs[0]], spec.diameter_mm, BUILD_WORK / "clay_reference_view.png", BUILD_WORK,
                      samples=32 if quick else 128)
    LK.crops_sheet(str(REFERENCE), views["reference_view"], RENDERS / "smokebomb_crops_3x.png", CROPS3X, scale=3)
    LK.crops_sheet(str(REFERENCE), views["reference_view"], BUILD_WORK / "crops_3x_bright.png", CROPS3X, scale=3,
                   bright=2.2)
    report["renders"] = {"reference_views": views, "clay": str((BUILD_WORK / "clay_reference_view.png").relative_to(PROJECT)),
                         "crops_3x": "Renders/SmokeBomb/smokebomb_crops_3x.png"}
    gal = LK.gallery(spec, [[objs[0]], [objs[1]], [objs[2]]], RENDERS, BUILD_WORK, samples=48 if quick else 256,
                     lod_screen_sizes=report["lod_screen_sizes"], bounds_radius_mm=report["bounds_radius_mm"])
    report["renders"]["gallery"] = gal
    sw = LK.lod_switch_frame([[objs[0]], [objs[1]], [objs[2]]], spec.diameter_mm, report["bounds_radius_mm"],
                             report["lod_screen_sizes"], RENDERS / "smokebomb_lod_switch.png", BUILD_WORK,
                             samples=64 if quick else 256)
    report["renders"]["lod_switch"] = sw
    ref = LK.load_png(REFERENCE)[..., :3].astype(np.float64)
    ren = LK.load_png(views["reference_view"])[..., :3].astype(np.float64)
    report["fidelity"] = {"reference": MT.measure_all(ref), "render": MT.measure_all(ren)}
    report["no_reference_in_maps"] = {"reference_sha256": sha256(REFERENCE), "expected": REFERENCE_SHA,
                                      "maps_mtime": maps_mtime,
                                      "note": "the maps were written in the textures stage; the reference is first "
                                              "loaded in this render stage, for the side-by-side, crops and metrics only"}


def fidelity_gates(fid) -> dict:
    ref, ren = fid["reference"], fid["render"]
    g = {}
    rs, ns = ref["silhouette"], ren["silhouette"]
    g["F1_diameter_within_1pct"] = abs(ns["diameter_px"] / rs["diameter_px"] - 1.0) <= 0.01
    g["F2_centre_within_3px"] = (abs(ns["centre_px"][0] - 627.4) <= 3 and abs(ns["centre_px"][1] - 628.9) <= 3)
    g["F3_circularity_0.8_1.8pctR"] = 0.8 <= ns["rms_dev_pctR"] <= 1.8
    g["F4_steps_8_to_16"] = 8 <= ns["steps"]["count_ge_4px"] <= 16
    for p in ("p10", "p50", "p90"):
        g[f"F5_tone_{p}_within_12pct"] = abs(ren["tones"][p] / ref["tones"][p] - 1.0) <= 0.12
    for q in ("upper_left", "upper_right", "lower_left", "lower_right"):
        a = ren["lighting"][q] / ren["lighting"]["centre"]
        b = ref["lighting"][q] / ref["lighting"]["centre"]
        g[f"F6_quadrant_{q}_within_15pct"] = abs(a / b - 1.0) <= 0.15
    c = ren["colour"]["chromaticity_lin"]
    g["F7_chromaticity"] = abs(c[0] - 0.378) <= 0.012 and abs(c[1] - 0.325) <= 0.008
    wp = ren["weave"]["dominant_period_px_median"] or 0
    g["F8_warp_pitch_3.4_5.5px"] = 3.4 <= wp <= 5.5
    g["F9_sparkle_fraction_3_to_5.5pct"] = 0.03 <= ren["sparkle"]["fraction"] <= 0.055
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
    g["6_uv_inside_0_1"] = bool(lods) and all(v["uv_range"][0] >= -1e-6 and v["uv_range"][1] <= 1 + 1e-6 for v in lods.values())
    g["6b_uv_corners_within_block_padding"] = bool((report.get("mesh") or {}).get("uv_corner_within_padding"))
    g["7_hull_contains_every_lod"] = bool((report.get("collision") or {}).get("contains_every_lod"))
    g["8_two_sockets"] = len(report.get("sockets") or []) == 2
    tex = report.get("textures") or {}
    g["9_maps_power_of_two_no_colour_chunks"] = bool(tex.get("power_of_two")) and not any(
        v for v in (tex.get("colour_chunks") or {}).values())
    # round 3: FULL RANGE means the useful values fill 0..1, not just that 256 levels occur somewhere:
    # every level used, the median at or above 32/255 and the 10th percentile at or above 12/255
    # (round 2's linear Detail had its median at 5/255)
    dpc = (tex.get("recolour") or {}).get("detail_percentiles_of_255") or {} if tex else {}
    g["9b_recolour_detail_full_range"] = bool(tex) and (tex["recolour"]["detail_levels_used"] >= 200)         and float(dpc.get("50", 0)) >= 32 and float(dpc.get("10", 0)) >= 12 and float(dpc.get("99.9", 0)) >= 230
    fr = report.get("frozen") or {}
    g["10_frozen_assets_unchanged"] = bool(fr.get("unchanged"))
    names = [report.get("asset"), (report.get("build_to") or {}).get("material")]
    names += (report.get("build_to") or {}).get("textures") or []
    names += [v.get("object") for v in lods.values()]
    names += [(report.get("collision") or {}).get("hull")]
    g["11_no_franchise_string"] = not deny_hits(*names)
    # the visible surface may move at most ONE PIXEL (p99) of a 1080p screen at the LOD's switch
    # size (the bounds sphere's diameter is screen_size x 1080 px there)
    ss = report.get("lod_screen_sizes") or [1.0, 0.0, 0.0]
    rad = float(report.get("bounds_radius_mm") or 36.5)
    ok12 = bool(lods)
    for i in (1, 2):
        v = (lods.get(f"LOD{i}", {}).get("visible_surface_deviation_mm") or {}).get("p99")
        px_per_mm = ss[i] * 1080.0 / (2.0 * rad)
        lim = 1.0 / max(px_per_mm, 1e-9)
        if f"LOD{i}" in lods:
            lods[f"LOD{i}"].setdefault("visible_surface_deviation_mm", {})["limit_p99_mm_one_px_at_switch"] = round(lim, 4)
        ok12 = ok12 and v is not None and v <= lim
    g["12_lod_visible_deviation_under_1px_at_switch"] = ok12
    g["14_no_triangle_unreal_would_drop"] = bool(lods) and all(v.get("min_triangle_area_mm2", 0.0) >= 0.005 for v in lods.values())
    ends = (report.get("winding") or {}).get("ends_hidden") or []
    g["15_both_tape_ends_hidden"] = bool(ends) and all(e.get("all_covered") for e in ends)
    fid = report.get("fidelity")
    if fid:
        for k, v in fidelity_gates(fid).items():
            g["13_" + k] = v
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default=",".join(ALL_STAGES))
    p.add_argument("--quick", action="store_true")
    p.add_argument("--cloth-json", default=None, help="DEV ONLY: ClothSpec overrides (JSON) on top of the calibration")
    p.add_argument("--ref-only", action="store_true", help="DEV ONLY: render the reference view only")
    p.add_argument("--ball-json", default=None, help="DEV ONLY: smokebomb_ball.BallSpec overrides (JSON)")
    p.add_argument("--report-name", default="smokebomb_report.json")
    p.add_argument("--dev-dir", default=None,
                   help="DEV ONLY: write every output (blend, exports, renders, report) under this folder")
    return p.parse_args(argv)


def main(argv=None):
    global ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    if args.dev_dir:
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, WORK = dev / "Assets", dev / "Exports", dev / "Renders", dev
        TEXTURES, BUILD_WORK = EXPORTS / "Textures", dev / "build"
    elif args.quick or args.cloth_json or args.ref_only or args.ball_json:
        raise SystemExit("--quick / --cloth-json / --ref-only are DEV flags: use them with --dev-dir, never over "
                         "the shipped files")
    if args.cloth_json:
        CLOTH_OVERRIDES_EXTRA.update(json.loads(args.cloth_json))
    if args.ball_json:
        SB.BALL = dataclasses.replace(SB.BALL, **json.loads(args.ball_json))
    spec = SMOKE_BOMB
    for d in (ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": spec.mesh_name, "library": f"props_lib smokebomb {LIB_VERSION}",
              "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
              "build_script": str(Path(__file__).relative_to(PROJECT)), "quick": bool(args.quick),
              "method": "ONE continuous tape wound on a core (smokebomb_wind), swept with the tape section "
                        "(smokebomb_tape), exposed stretches only (smokebomb_ball)",
              "build_to": build_to(spec), "frozen": {"before": frozen_hashes()}}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"

    atlas_size = 2048 if args.quick else spec.texture_size("BC")
    ball = stage_ball(report)
    facesets, reqs, pad = stage_faces(ball, spec, atlas_size, report)
    thread_parts, thread_req, thread_offs = stage_threads(ball, report)
    atlas = stage_atlas(reqs, thread_req, atlas_size, pad, report)
    objs, part_store = stage_meshes(spec, ball, facesets, atlas, thread_parts, thread_offs, report)
    if "textures" in stages:
        stage_textures(spec, ball, atlas, objs, report, quick=args.quick)
    group, hull = stage_finish(spec, objs, report)
    stage_measure(spec, objs, part_store, report, ball=ball)
    if "qa" in stages:
        stage_qa(spec, objs, report)
    if "save" in stages:
        blend = ASSETS / "SmokeBomb.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        report["blend"] = str(blend.relative_to(PROJECT))
        report["blend_sha256"] = sha256(blend)
        log(f"saved {blend}")
    if "export" in stages:
        stage_export(spec, group, report)
    if "render" in stages and "textures" in stages:
        stage_render(spec, objs, report, quick=args.quick, ref_only=args.ref_only)
    report["frozen"]["after"] = frozen_hashes()
    b, a = report["frozen"]["before"], report["frozen"]["after"]
    report["frozen"]["unchanged"] = bool(a["shuriken"]["all_ok"] and a["paperbomb"]["all_ok"]
                                         and b["shuriken_live_exports"] == a["shuriken_live_exports"])
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    if "report" in stages:
        out = WORK / args.report_name
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        log(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
