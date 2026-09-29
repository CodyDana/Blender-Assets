"""Comparison sheets for the Unreal captures (system Python with Pillow: `py -3 ak_compare_sheet.py`).

For every capture in WorkFiles/armory/build/unreal/captures/<name>.png: Blender render of the preset (env AK_PRESET,
default night: renders/night_live2; golden: renders/hero_live) | Unreal
capture, same height, labelled; C1 at the reference aspect also gets the LOOK reference on the left. Out:
WorkFiles/armory/build/unreal/compare/<name>_blender_vs_unreal.png (C1 ref aspect: reference_blender_unreal_C1.png).
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
CAP = ROOT / "build" / "unreal" / "captures"
PRESET = os.environ.get("AK_PRESET", "night").strip().lower() or "night"   # night + genkan (2026-09-28)
BL = ROOT / "build" / "renders" / ("night_live2" if PRESET == "night" else "hero_live")   # golden: hero round (was stage_f2)
REF = ROOT / "reference" / "armory3_reference2.png"
OUT = ROOT / "build" / "unreal" / "compare"
H = 540
GAP = 12


def tile(p, label):
    im = Image.open(p).convert("RGB")
    im = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 * len(label) + 10, 18), fill=(0, 0, 0))
    d.text((5, 3), label, fill=(255, 255, 255))
    return im


def sheet(tiles, out):
    w = sum(t.width for t in tiles) + GAP * (len(tiles) - 1)
    im = Image.new("RGB", (w, H), (30, 30, 30))
    x = 0
    for t in tiles:
        im.paste(t, (x, 0))
        x += t.width + GAP
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print("wrote", out)


def main():
    for p in sorted(CAP.glob("*.png")):
        name = p.stem
        if name.endswith("_ref_aspect"):
            cam = name.replace("_ref_aspect", "")
            b = BL / "ref_aspect" / f"{cam}_{PRESET}.png"
            tiles = [tile(REF, "reference 2")] + ([tile(b, f"Blender {PRESET}")] if b.exists() else []) + \
                [tile(p, f"Unreal {PRESET}")]
            sheet(tiles, OUT / f"reference_blender_unreal_{cam.split('_')[0]}.png")
            continue
        b = BL / f"{name}_{PRESET}.png"
        tiles = ([tile(b, f"Blender {PRESET}")] if b.exists() else []) + [tile(p, f"Unreal {PRESET}")]
        sheet(tiles, OUT / f"{name}_blender_vs_unreal.png")


main()
