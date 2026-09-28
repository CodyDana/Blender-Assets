"""Finish Unreal's beauty frames (Blender headless): 2:1 box downsample (anti-aliasing of the 2048 captures), opaque
alpha, one PNG per frame in ue_renders/frames/, and a contact sheet ue_renders/ninjapack_default_instances.png
(rows = items, columns = views). Deletes ue_renders/frames_raw/ afterwards unless --keep-raw.

    blender -b --factory-startup --python make_frames.py -- [--keep-raw]
"""
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np

R = Path(__file__).resolve().parents[4] / "WorkFiles" / "materials" / "ue_renders"
RAW, OUT = R / "frames_raw", R / "frames"
VIEWS = ("threequarter", "top", "low")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def load(p):
    img = bpy.data.images.load(str(p), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def save(p, a):
    h, w = a.shape[:2]
    im = bpy.data.images.new(p.stem, w, h, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    im.filepath_raw = str(p)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def down(a, f):
    h, w = a.shape[:2]
    return a[: h // f * f, : w // f * f].reshape(h // f, f, w // f, f, 4).mean(axis=(1, 3))


OUT.mkdir(parents=True, exist_ok=True)
items = sorted({p.stem.rsplit("_", 1)[0] for p in RAW.glob("*.png")})
rows = []
for item in items:
    tiles = []
    for v in VIEWS:
        p = RAW / f"{item}_{v}.png"
        if not p.is_file():
            continue
        a = down(load(p), 2)
        a[..., 3] = 1.0
        save(OUT / p.name, a)
        tiles.append(down(a, 2))
    if tiles:
        rows.append(np.concatenate(tiles, axis=1))
if rows:
    width = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, width - r.shape[1]), (0, 0))) for r in rows]
    sheet = np.concatenate(rows[::-1], axis=0)       # Blender pixel rows are bottom-up: first item on top
    sheet[..., 3] = 1.0
    save(R / "ninjapack_default_instances.png", sheet)
if "--keep-raw" not in ARGS:
    shutil.rmtree(RAW, ignore_errors=True)
print("FRAMES_DONE", len(items), "items")
