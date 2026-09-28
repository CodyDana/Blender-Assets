"""Compose the Unreal recolour swatches (WorkFiles/flashbang/r2/fin2/ue_swatches/swatch_*.png) into one sheet:
the frames side by side (centre-cropped), each with a chip of the picked colour underneath (the default: the shipped
olive #474730 (round 2 constants) as the chip).  Output: Renders/Flashbang/flashbang_recolour_swatches.png.
    blender -b --factory-startup --python fin_swatch_sheet.py
"""
import json
from pathlib import Path

import bpy
import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
SW = P / "WorkFiles/flashbang/r2/fin2/ue_swatches"
OUT = P / "Renders/Flashbang/flashbang_recolour_swatches.png"
meta = json.loads((SW / "swatches.json").read_text(encoding="utf-8"))
DEFAULT_HEX = "474730"


def load(p):
    im = bpy.data.images.load(str(p), check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1, :, :3]


tiles = []
for name, rec in meta["frames"].items():
    if "png" not in rec:
        continue
    a = load(rec["png"])
    h, w = a.shape[:2]
    a = a[int(h * 0.04):int(h * 0.96), int(w * 0.22):int(w * 0.78)]
    hexc = rec.get("hex") or DEFAULT_HEX
    chip = np.array([int(hexc[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
    band = np.ones((70, a.shape[1], 3), np.float32) * 0.12
    band[12:58, 20:-20] = chip
    tiles.append(np.concatenate([a, band], 0))
    tiles.append(np.full((tiles[-1].shape[0], 8, 3), 0.9, np.float32))
sheet = np.concatenate(tiles[:-1], 1)
h, w = sheet.shape[:2]
im = bpy.data.images.new("sheet", w, h, alpha=False)
im.colorspace_settings.name = "Non-Color"
im.pixels.foreach_set(np.concatenate([sheet, np.ones((h, w, 1), np.float32)], 2)[::-1].ravel())
im.filepath_raw = str(OUT)
im.file_format = "PNG"
im.save()
print("sheet", OUT, sheet.shape)
