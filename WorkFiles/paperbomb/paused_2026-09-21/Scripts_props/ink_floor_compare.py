#!/usr/bin/env python
"""Render the SAME gallery frame with the ink floor on and off, so a human can decide.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/ink_floor_compare.py -- [--samples N] [--supersample N]

WHY THIS EXISTS
---------------
REFERENCE_SPEC row 1 is the single biggest number on the card, and it is a POLICY call
rather than a drawing error.  The first build clamped every channel of every map at
``DIELECTRIC_FLOOR_LINEAR`` = 0.0473 (60/255), which is the usual bottom of the non-metal
albedo band, and wrote the reason down on purpose.  The cost is measured: our black core
came out ten times lighter than the guide's and the card's paper-to-ink contrast was
11.7:1 against the real-glyph reference's 300.9:1 (the older guide read 170:1), with the
black's minimum, 0.1th percentile and 1st percentile all sitting at exactly the same
stored value - no dark tail at all.  The same
floor pins vermilion's green and blue, which is why our red measured 31 % short on
saturation.

The user asked for accuracy to the reference, so the asset SHIPS reference-matched and
the floored behaviour is kept whole behind one named flag,
``paperbomb_art.INK_FLOOR_DIELECTRIC``.  This script renders both so the decision can be
made by looking rather than by arguing:

    WorkFiles/paperbomb/ink_floor_compare/reference/paperbomb_front.png
    WorkFiles/paperbomb/ink_floor_compare/floored/paperbomb_front.png
    WorkFiles/paperbomb/ink_floor_compare/compare.png        (side by side)
    WorkFiles/paperbomb/ink_floor_compare/ink_floor_compare.json

Identical camera, identical lamps, identical samples, identical mesh, identical AO bake -
the ONLY difference between the two frames is the palette and the clamp.  Both the map's
own contrast and the rendered frame's are measured, because section 7 of the spec is
explicit that whether the ink reads as DARK depends on the shader and the lighting as
well as on the albedo, and must be judged in the shipped render.

Nothing here opens either guide image; the art is drawn inside ``no_guide_access()``.
"""
from __future__ import annotations

import argparse
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
from mathutils import Matrix                                      # noqa: E402

from props_lib import atlas as A                                  # noqa: E402
from props_lib import bake as B                                   # noqa: E402
from props_lib import geometry as G                               # noqa: E402
from props_lib import paper_material as PM                        # noqa: E402
from props_lib import render as R                                 # noqa: E402
from props_lib import sheet as S                                  # noqa: E402
from props_lib import paperbomb_art as art                        # noqa: E402
from props_lib import art_metrics as AM                           # noqa: E402
from props_lib.spec import PAPER_BOMB                             # noqa: E402

OUT = PROJECT / "WorkFiles" / "paperbomb" / "ink_floor_compare"
SEED = 20260919
FLAT_FILL = 0.86


def log(*parts):
    print("[ink-floor]", *parts, flush=True)


def linear_luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def srgb_to_linear(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def read_png(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        image.colorspace_settings.name = "Non-Color"
        w, h = image.size
        buf = np.empty(w * h * 4, np.float32)
        image.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1, :, :3]).astype(np.float64)
    finally:
        bpy.data.images.remove(image)


def rendered_contrast(png_path, mask_path):
    """Paper-to-ink contrast IN THE RENDER, which is where section 7 says to judge it."""
    rgb = srgb_to_linear(read_png(png_path))
    mask = read_png(mask_path)[..., 0] > 0.5
    if not mask.any():
        return {}
    lum = linear_luma(rgb)[mask]
    warm = (rgb[..., 0] - rgb[..., 2])[mask]
    # paper is the warm, bright population; sumi is the dark neutral one
    paper = lum[lum >= np.percentile(lum, 65)]
    ink = lum[lum <= np.percentile(lum, 4)]
    return {
        "paper_linear_luma_p50": round(float(np.median(paper)), 5),
        "ink_linear_luma_p50": round(float(np.median(ink)), 6),
        "ink_linear_luma_min": round(float(lum.min()), 6),
        "contrast_ratio": round(float(np.median(paper) / max(np.median(ink), 1e-9)), 1),
        "warmth_mean": round(float(warm.mean()), 4),
    }


def map_contrast(front, cfg):
    """The same number taken on the BASE COLOUR MAP, before any shading."""
    m = AM.ink_and_contrast(AM.Card(front, cfg.pad_mm))
    return {k: m[k] for k in ("paper_linear_luma_p50", "black_core_linear_luma_p01",
                              "black_core_stored_min", "contrast_ratio",
                              "red_saturation", "red_stored_mean",
                              "paper_stored_mean")}


def main(argv=None):
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:]
                                          if "--" in sys.argv else [])
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=160)
    ap.add_argument("--supersample", type=int, default=2)
    args = ap.parse_args(argv)

    spec = PAPER_BOMB
    plan = A.plan_for(spec)
    OUT.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    # ---- ONE mesh, built once, shared by both frames --------------------
    cfg0 = art.ArtConfig(ppmm=plan.ppmm, seed=SEED, supersample=1, pad_mm=plan.pad_mm)
    outline = art.card_outline_mm(cfg0)
    trim = S.Trim(outline, spec.width_mm, spec.height_mm)
    surface = S.Surface(
        width_mm=spec.width_mm, height_mm=spec.height_mm,
        curl_sagitta_mm=spec.curl.sagitta_mm,
        curl_deepen_sagitta_mm=spec.curl.deepen_sagitta_mm,
        curl_deepen_run_mm=spec.curl.deepen_run_mm,
        curl_crease_relief=spec.curl.crease_relief,
        curl_crease_sigma_mm=spec.curl.crease_relief_sigma_mm,
        bow_deg=spec.curl.bow_deg, bow_cycles=spec.curl.bow_cycles,
        folds=tuple((f.v_mm, f.turn_deg, f.half_width_mm, f.wander_mm) for f in spec.folds),
        seed=SEED)
    sm = S.build_sheet(spec, spec.lods[0], surface, trim, plan, seed=SEED)
    lod0 = G.make_object("SM_PaperBomb", sm)
    log(f"mesh {len(lod0.data.polygons)} faces, {sm.triangles} triangles")

    # ---- ONE AO bake: the geometry is identical in both modes ------------
    t0 = time.time()
    ao, ao_info = B.bake_ao_map(lod0, plan.size, samples=B.AO_SAMPLES)
    log(f"AO bake {time.time() - t0:.1f} s, mean {ao_info['reached_mean']:.4f}")

    rig = R.build_rig(spec)
    R.setup_render(samples=args.samples)
    flat_cam = rig["cam_flat"]
    flat_cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    flat_cam.location = (0.0, 0.0, 0.40)
    flat_cam.data.ortho_scale = (spec.height_mm / FLAT_FILL) * 0.001 * R.RES_X / R.RES_Y
    lod0.hide_render = True

    results = {}
    frames = {}
    for mode in art.INK_FLOOR_MODES:
        log(f"--- {mode} ---")
        d = OUT / mode
        d.mkdir(parents=True, exist_ok=True)
        cfg, front, back, provenance = B.draw_art(spec, plan, seed=SEED,
                                                  supersample=args.supersample,
                                                  ink_floor=mode)
        channels = B.transfer(plan, front, back, spec, cfg)
        written = B.write_maps(d, spec.texture_stem, channels, ao)
        material = PM.gallery_material(f"M_Compare_{mode}", written["paths"])
        lod0.data.materials.clear()
        lod0.data.materials.append(material)
        clone = lod0.copy()
        clone.data = lod0.data
        clone.name = f"PREVIEW_{mode}"
        bpy.context.scene.collection.objects.link(clone)
        clone.hide_render = False
        png = d / "paperbomb_front.png"
        mask = d / "front_mask.png"
        R.render_to(png, flat_cam, rig["flat"])
        R.render_mask(mask, flat_cam, [clone])
        bpy.data.objects.remove(clone, do_unlink=True)
        bpy.data.materials.remove(material)
        results[mode] = {
            "maps": {k: str(Path(v).relative_to(PROJECT)) for k, v in written["paths"].items()},
            "render": str(png.relative_to(PROJECT)),
            "base_colour_map": map_contrast(front, cfg),
            "rendered": rendered_contrast(png, mask),
            "guide_images_opened": provenance.get("guide_images_opened"),
        }
        frames[mode] = read_png(png)
        log(f"  map contrast   {results[mode]['base_colour_map']['contrast_ratio']}:1")
        log(f"  render contrast {results[mode]['rendered'].get('contrast_ratio')}:1")

    # ---- the pair, side by side -----------------------------------------
    a, b = frames[art.INK_FLOOR_REFERENCE], frames[art.INK_FLOOR_DIELECTRIC]
    h = min(a.shape[0], b.shape[0])
    sheet = np.concatenate([a[:h], np.ones((h, 12, 3)), b[:h]], axis=1)
    art.write_png(str(OUT / "compare.png"), np.clip(sheet, 0.0, 1.0))

    ref = results[art.INK_FLOOR_REFERENCE]
    flo = results[art.INK_FLOOR_DIELECTRIC]
    out = {
        "what_this_is": (
            "The same gallery frame rendered with the same camera, the same lamps, the "
            "same samples, the same mesh and the same AO bake.  The only difference is "
            "props_lib.paperbomb_art's ink-floor policy."),
        "default": art.DEFAULT_INK_FLOOR,
        "flag": {
            "module": "props_lib.paperbomb_art.ArtConfig.ink_floor",
            "values": list(art.INK_FLOOR_MODES),
            "build": "build_paper_bomb.py --ink-floor floored",
            "art_cli": "paperbomb_art.py -- --ink-floor floored",
        },
        "reference_target": {
            "paper_linear_luma": AM.TARGETS["paper_linear_luma"],
            "black_linear_luma": AM.TARGETS["black_linear_luma"],
            "contrast_ratio": AM.TARGETS["contrast_ratio"],
            "source": "References/PaperBomb/REFERENCE_SPEC.md row 1",
        },
        "modes": results,
        "left_right_in_compare_png": [art.INK_FLOOR_REFERENCE, art.INK_FLOOR_DIELECTRIC],
        "summary": (
            f"reference-matched: map {ref['base_colour_map']['contrast_ratio']}:1, "
            f"render {ref['rendered'].get('contrast_ratio')}:1;  "
            f"floored: map {flo['base_colour_map']['contrast_ratio']}:1, "
            f"render {flo['rendered'].get('contrast_ratio')}:1.  "
            f"The reference measures 300.9:1 - see REFERENCE_SPEC row 78, re-measured "
            f"on the real-glyph reference of record; the 170:1 figure was the older guide."),
        "samples": args.samples,
        "supersample": args.supersample,
        "sheet": str((OUT / "compare.png").relative_to(PROJECT)),
    }
    (OUT / "ink_floor_compare.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    log(out["summary"])
    log(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
