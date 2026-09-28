"""Dev tool (look-match round 1): build a part (LOD0 low or the high) with plain preview materials and render it at the
reference's own grid next to the reference crop.  NOT a deliverable render (those come from the baked maps only).

    blender -b --factory-startup --python shv4_dev_preview.py -- --part throat --level high --out <png>
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "shv4_lib"))
import sfv4_png as PNG  # noqa: E402
import sfv4_render as R  # noqa: E402
import shv4_spec as S  # noqa: E402
import shv4_parts as P  # noqa: E402
from sfv4_mesh import MB  # noqa: E402

REF = S.ROOT / "References" / "SnowFlower" / "SnowFlower_sheath_reference.png"
CROPS = {"throat": (25, 178, 425, 590), "chape": (1240, 1500, 440, 570), "band": (262, 345, 430, 580),
         "vine": (440, 780, 440, 575), "upper": (20, 340, 420, 590), "full": (0, 1536, 0, 1024)}

MATS = [("lacq", (0.022, 0.025, 0.032), 0.2, 0.0), ("silver", (0.80, 0.80, 0.81), 0.14, 1.0),
        ("pearl", (0.80, 0.81, 0.83), 0.2, 0.0), ("recess", (0.03, 0.03, 0.035), 0.4, 1.0),
        ("inset", (0.030, 0.034, 0.045), 0.44, 0.0), ("branch", (0.78, 0.78, 0.79), 0.18, 1.0),
        ("cavity", (0.01, 0.01, 0.01), 0.6, 0.0), ("antique", (0.40, 0.40, 0.41), 0.3, 1.0)]


def mats():
    out = []
    for name, c, r, m in MATS:
        mt = bpy.data.materials.new("DEV_" + name)
        mt.use_nodes = True
        bs = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value = (*c, 1)
        bs.inputs["Roughness"].default_value = r
        bs.inputs["Metallic"].default_value = m
        out.append(mt)
    return out


def load_ref():
    im = bpy.data.images.load(str(REF))
    w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1][..., :3].copy()


def build(parts, level):
    import sfv4_rev3 as R3
    ms = mats()
    col = bpy.context.scene.collection
    objs = []

    def emit(mb, name, low=False):
        if not mb.faces:
            return
        if low:
            ob = mb.to_object(name, col, materials=[ms[0], ms[1]], recalc=True, smooth_angle=50.0)
        else:
            ob = mb.to_object(name, col, materials=ms, recalc=True, smooth_angle=50.0)
            ob.data.polygons.foreach_set("material_index", mb.fmat)
        objs.append(ob)

    lv = level if level == "high" else int(level)
    high = lv == "high"
    if "body" in parts:
        mb = MB("body")
        P.build_core(mb, lv if not high else "high", uvmode="pattern" if high else "atlas")
        if high:
            mb.fmat = [P.H_LACQ if m == P.H_LACQ else m for m in mb.fmat]
        emit(mb, "body", low=not high)
    if "throat" in parts:
        mb = MB("throat")
        P.build_throat(mb, lv, high=high)
        emit(mb, "throat", low=not high)
        mb = MB("tplates")
        P.build_plates(mb, "throat", lv, high=high)
        emit(mb, "tplates", low=not high)
    if "chape" in parts:
        mb = MB("chape")
        P.build_chape(mb, lv, high=high)
        emit(mb, "chape", low=not high)
        mb = MB("cplates")
        P.build_plates(mb, "chape", lv, high=high)
        emit(mb, "cplates", low=not high)
    if "band" in parts:
        mb = MB("band")
        P.build_band(mb, lv, high=high)
        emit(mb, "band", low=not high)
        mb = MB("bplates")
        P.build_plates(mb, "band", lv, high=high)
        emit(mb, "bplates", low=not high)
    if "bloom" in parts:
        if high:
            sink = R3.Sink("bl")
            P.build_pearl_blooms(None, "high", high_sink=sink)
            for k, mb in sink.mbs.items():
                emit(mb, f"bl{k}")
        else:
            mb = MB("bloom")
            P.build_pearl_blooms(mb, lv)
            emit(mb, "bloom", low=True)
    if "stem" in parts:
        mb = MB("stem")
        P.build_stem(mb, lv if not high else "high", high=high, mat=P.H_BRANCH if high else P.SILV)
        emit(mb, "stem", low=not high)
    tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print("DEV_TRIS", tri, {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}, flush=True)
    return objs


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="body,throat,bloom,stem")
    ap.add_argument("--level", default="high")
    ap.add_argument("--crop", default="throat")
    ap.add_argument("--scale", type=int, default=5)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--view", default="front")
    ap.add_argument("--out", required=True)
    ap.add_argument("--light", default="sheath")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build(a.parts.split(","), a.level)
    R.base_settings(a.samples, transparent=True)
    R.world_studio(bg=(1, 1, 1), env_top=0.9, env_mid=0.24, env_bot=0.04, env_strength=1.0)
    r0, r1, x0, x1 = CROPS[a.crop]
    sc = a.scale
    zc = float(S.zr(0.5 * (r0 + r1)))
    if a.light == "sheath":
        import shv4_render as SR
        SR.lights_sheet_sheath(zc / 1000.0, size=0.8)
    else:
        R.lights_sheet(zc / 1000.0, size=0.8)
    w_px, h_px = (x1 - x0) * sc, (r1 - r0) * sc
    scale = max(w_px, h_px) / sc * S.K / 1000.0
    if a.view == "front":
        R.cam_ortho("front", zc, float(S.xp(0.5 * (x0 + x1))), scale, w_px, h_px)
    elif a.view == "side":
        R.cam_ortho("side", zc, 0.0, scale, w_px, h_px)
    else:
        z = zc / 1000.0
        R.cam_persp((0.16, -0.22, z - 0.10), (0.0, 0.0, z), lens=85, roll=math.radians(180), w=1200, h=1200)
    tmp = Path(a.out).with_suffix(".render.png")
    bpy.context.scene.render.filepath = str(tmp)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(tmp))
    w, h = im.size
    d = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    d = d[..., :3] * d[..., 3:4] + (1 - d[..., 3:4])
    if a.view == "front":
        ref = load_ref()
        crop = PNG.upscale(ref[r0:r1, x0:x1], sc)
        hh, ww = min(crop.shape[0], d.shape[0]), min(crop.shape[1], d.shape[1])
        sheet = np.concatenate([crop[:hh, :ww], np.ones((hh, 12, 3)), d[:hh, :ww]], 1)
    else:
        sheet = d
    PNG.write_png(a.out, sheet)
    print("DEV_PREVIEW_OK", a.out, flush=True)


if __name__ == "__main__":
    main()
