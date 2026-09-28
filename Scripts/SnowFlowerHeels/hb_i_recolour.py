"""Stage I: recolour detail maps for the colour system (DRAFT inputs for the Finalise agent; the pack materials and the
derived constants are the Finalise agent's job - WorkFiles/materials/MATERIALS_REPORT.md).

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_i_recolour.py

For the M_Fabric_Master parts (Leather, Insole): Y = linear luminance of the baked BC over covered texels,
d = (Y - Ylo) / (Yhi - Ylo) as a 16-bit LINEAR greyscale PNG (the kunai wrap recipe), plus Colour / Bias / Scale.
Covered texels = texels any shoe triangle maps to (rasterised from UV0 of SK_SnowFlowerHeels, right shoe).
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hb_common as C  # noqa: E402
import metro_png as P  # noqa: E402

TEX = C.EXPORT_DIR / "Textures"
OUT = TEX / "Recolour"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def srgb_decode(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def coverage(slot_index, tile, size):
    """Texel mask of the right shoe's UV0 triangles of one slot (numpy rasteriser)."""
    bpy.ops.wm.open_mainfile(filepath=str(C.ASSET_BLEND.with_name("SnowFlowerHeels_Build.blend")))
    ob = bpy.data.objects["SK_SnowFlowerHeels"]
    me = ob.data
    me.calc_loop_triangles()
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    W, H = size
    mask = np.zeros((H, W), dtype=bool)
    for t in me.loop_triangles:
        if t.material_index != slot_index:
            continue
        q = uv[list(t.loops)] - np.array(tile)
        if q[:, 0].min() < -0.01 or q[:, 0].max() > 1.01:
            continue            # the left shoe (+1 U) shares the texels
        px = np.column_stack([q[:, 0] * W, (1 - q[:, 1]) * H])
        x0, y0 = np.floor(px.min(0)).astype(int)
        x1, y1 = np.ceil(px.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
        a, b, c = px
        def edge(p0, p1):
            return (p1[0] - p0[0]) * (yy - p0[1]) - (p1[1] - p0[1]) * (xx - p0[0])
        e0, e1, e2 = edge(a, b), edge(b, c), edge(c, a)
        inside = ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
        mask[y0:y1 + 1, x0:x1 + 1] |= inside
    return mask


def save16(arr01, path):
    h, w = arr01.shape
    im = bpy.data.images.new(path.stem, w, h, float_buffer=True)
    im.colorspace_settings.name = "Non-Color"
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = arr01[::-1]
    im.pixels.foreach_set(rgba.ravel())
    sc = bpy.context.scene
    s = sc.render.image_settings
    s.file_format = "PNG"
    s.color_mode = "BW"
    s.color_depth = "16"
    sc.view_settings.view_transform = "Standard"
    s.color_management = "OVERRIDE"
    s.view_settings.view_transform = "Standard"
    s.linear_colorspace_settings.name = "Non-Color" if hasattr(s, "linear_colorspace_settings") else None
    im.save_render(str(path), scene=sc)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    slots = {"Leather": (0, (0.0, 0.0), (2048, 2048)), "Insole": (1, (0.0, 1.0), (2048, 1024))}
    record = {"schema": "ninjapack.recolour_maps/1 (DRAFT from the heels builder, round 1)", "item": "SnowFlowerHeels",
              "generated": str(date.today()), "generator": {"script": "Scripts/SnowFlowerHeels/hb_i_recolour.py",
                                                            "script_sha256": sha(__file__)},
              "note": "Finalise agent: derive the MF_TintDetail constants (derive_constants.py) and wire the instances; "
                      "Metal slot is M_Steel_Master (not recolourable; Steel Tint only).", "maps": {}, "parts": {}}
    for slot, (si, tile, size) in slots.items():
        mask = coverage(si, tile, size)
        bc = P.read(str(TEX / f"T_SnowFlowerHeels_{slot}_BC.png")).astype(np.float64) / 255.0
        lin = srgb_decode(bc[..., :3])
        Y = lin @ np.array([0.2126, 0.7152, 0.0722])
        cov = mask if mask.sum() > 100 else np.ones_like(mask)
        ylo, yhi = float(np.percentile(Y[cov], 0.1)), float(np.percentile(Y[cov], 99.9))
        ymean = float(Y[cov].mean())
        d = np.clip((Y - ylo) / max(yhi - ylo, 1e-6), 0, 1)
        d[~cov] = (ymean - ylo) / max(yhi - ylo, 1e-6)
        path = OUT / f"T_SnowFlowerHeels_{slot}_Detail16.png"
        save16(d.astype(np.float32), path)
        colour = lin[cov].mean(0).tolist()
        record["maps"][path.stem] = {"file": str(path.relative_to(C.ROOT)).replace("\\", "/"), "sha256": sha(path),
                                     "size": list(size), "format": "PNG 16-bit greyscale, LINEAR",
                                     "coverage_fraction": round(float(cov.mean()), 4)}
        record["parts"][slot] = {"slot_material": f"M_SnowFlowerHeels_{slot}", "master": "M_Fabric_Master",
                                 "instance": f"MI_SnowFlowerHeels_{slot}", "detail_map": path.stem,
                                 "params_draft": {"Colour": colour + [1.0], "DetailBias": ylo / ymean,
                                                  "DetailScale": (yhi - ylo) / ymean, "DetailMean": ymean},
                                 "base_colour_map_reference": {"file": f"Exports/SnowFlowerHeels/Textures/T_SnowFlowerHeels_{slot}_BC.png",
                                                               "sha256": sha(TEX / f"T_SnowFlowerHeels_{slot}_BC.png")}}
        print("RECOLOUR", slot, "cov", round(float(cov.mean()), 3), "Y lo/mean/hi", round(ylo, 4), round(ymean, 4), round(yhi, 4))
    (OUT / "recolour_maps.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print("RECOLOUR_OK")


main()
