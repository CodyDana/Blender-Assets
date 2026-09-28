"""Look-match round 1 (sword): fast DESIGN preview - builds the high-poly (and/or LOD meshes) straight from the
build code and renders them in the sheet's views with the high materials (no bake).  Used to iterate a part's
design before the bake; the shipped-asset renders (sfv4_lm_render.py) are the proof.

    blender -b --factory-startup --python sfv4_lm_preview.py -- --out <dir> [--parts pommel,collar] \
        [--views hilt_front,hilt_side,det_pommel] [--what high|low0|low1|low2] [--samples 48]
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_assemble as A  # noqa: E402
import sfv4_blade as BL  # noqa: E402
import sfv4_look as LK  # noqa: E402
import sfv4_render as R  # noqa: E402
import sfv4_spec as S  # noqa: E402
import sfv4_lm_views as LV  # noqa: E402

ROOT = HERE.parents[2]


def build_high(parts):
    col = bpy.data.collections.new("HIGH")
    bpy.context.scene.collection.children.link(col)
    L = BL.relief_layout(-1)
    Lb = BL.relief_layout(1)
    bc, rough, meta = LK.paint_blade_pattern(L["samples"], Lb["samples"])
    img_bc = bpy.data.images.new("SF4_PATTERN_BC", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_bc.pixels.foreach_set(np.concatenate([bc, np.ones(bc.shape[:2] + (1,))], -1).astype(np.float32).ravel())
    img_r = bpy.data.images.new("SF4_PATTERN_ROUGH", meta["W"], meta["H"], float_buffer=True, is_data=True)
    img_r.pixels.foreach_set(np.stack([rough] * 3 + [np.ones_like(rough)], -1).astype(np.float32).ravel())
    hmats = LK.make_high_materials(img_bc, img_r, metal_bump=(0.03, 0.12))
    LK.set_bake_channel(hmats, "SHADED")
    high = A.build_high(parts)
    n = 0
    for part, d in high.items():
        for mkey, mb in d.items():
            if not mb.faces:
                continue
            n += mb.tri_count()
            mb.to_object(f"H_{part}_{mkey}", col, materials=hmats, recalc=True, smooth_angle=50.0)
    print("[LMP] high tris", n, flush=True)


def build_low(level, parts):
    col = bpy.data.collections.new("LOW")
    bpy.context.scene.collection.children.link(col)
    m = bpy.data.materials.new("clay")
    m.use_nodes = True
    bs = next(x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.55, 0.56, 0.58, 1)
    bs.inputs["Metallic"].default_value = 0.8
    bs.inputs["Roughness"].default_value = 0.35
    low = A.build_low(level)
    n = 0
    for part, mb in low.items():
        if parts and part not in parts and not (part in ("fbloom", "pbloom")):
            continue
        n += mb.tri_count()
        mb.to_object(f"L_{part}", col, materials=[m, m, m], smooth_angle=40.0)
    print("[LMP] low tris", n, flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--parts", default="")
    ap.add_argument("--views", default="hilt_front,hilt_side,hilt_back")
    ap.add_argument("--what", default="high")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--tag", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    if not str(out).lower().startswith(str(ROOT.resolve()).lower()):
        raise SystemExit(f"refusing to write outside the project: {out}")
    out.mkdir(parents=True, exist_ok=True)
    parts = [p for p in a.parts.split(",") if p] or None
    t = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if a.what == "high":
        build_high(parts)
    else:
        build_low(int(a.what[-1]), parts)
    print("[LMP] built", f"{time.time() - t:.1f}s", flush=True)
    for v in a.views.split(","):
        LV.render_view(v, out / f"{a.tag}{v}.png", samples=a.samples)
        print("[LMP] view", v, f"{time.time() - t:.1f}s", flush=True)
    print("LMP_DONE")


if __name__ == "__main__":
    main()
