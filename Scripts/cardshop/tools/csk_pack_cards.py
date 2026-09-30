#!/usr/bin/env python3
"""csk_pack_cards: pack a folder of images into a Card Shop Kit atlas + JSON index (a buyer tool, ships with the kit).

Standalone Python 3 + Pillow (``pip install pillow``). Unreal's embedded Python has no image library, so this runs
outside the engine; import the PNG it writes into Unreal (sRGB on) and point the kit material at the JSON cell rects.

    python csk_pack_cards.py <folder> <out.png> [--preset cards|packs|labels|boxes] [--pad 16]
                             [--grid COLSxROWS --cell WxH --content WxH --size N]

Images are taken in file-name order and placed left to right, top to bottom. Each is resized to the preset's
content size (the print face's exact aspect at the kit's px/mm, CARDSHOP_KIT_SPEC.md 4.1), centred in its cell, and
its edge pixels are repeated into a ``pad``-pixel border so mipmaps do not bleed the neighbour's colours.

The JSON lists every cell with ``rect_px`` [x, y, w, h] and ``rect_uv`` [u, v, du, dv], both with a TOP-LEFT origin,
which is Unreal's texture UV convention.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("csk_pack_cards needs Pillow: python -m pip install pillow")

TOOL_VERSION = "1.0.0"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"}

# CARDSHOP_KIT_SPEC.md 4.1 (cards: 8 x 8 of 512 at 5 px/mm = 315 x 440; packs: one face per 512 cell at 3 px/mm =
# 201 x 351; labels: 4 x 16 of 512 x 128 at 4 px/mm = 304 x 96; boxes: 4 x 4 of 1024 at 2 px/mm = 880 x 570)
PRESETS = {
    "cards": {"size": 4096, "grid": (8, 8), "cell": (512, 512), "content": (315, 440), "px_per_mm": 5},
    # packs 8 px/mm (was 3: soft close up in Unreal, 2026-09-29); 16 faces of 67 x 117 mm in 1024 cells
    "packs": {"size": 4096, "grid": (4, 4), "cell": (1024, 1024), "content": (536, 936), "px_per_mm": 8},
    "labels": {"size": 2048, "grid": (4, 16), "cell": (512, 128), "content": (304, 96), "px_per_mm": 4},
    "boxes": {"size": 4096, "grid": (4, 4), "cell": (1024, 1024), "content": (880, 570), "px_per_mm": 2},
}


def _pair(text: str):
    a, b = text.lower().split("x")
    return int(a), int(b)


def dilate_into(atlas: "Image.Image", tile: "Image.Image", x: int, y: int, pad: int) -> None:
    """Paste ``tile`` at (x, y) and repeat its edge pixels ``pad`` px outward (clamped to the atlas)."""
    w, h = tile.size
    big = Image.new(atlas.mode, (w + 2 * pad, h + 2 * pad))
    big.paste(tile, (pad, pad))
    left, right = tile.crop((0, 0, 1, h)), tile.crop((w - 1, 0, w, h))
    for i in range(pad):
        big.paste(left, (i, pad))
        big.paste(right, (pad + w + i, pad))
    top, bottom = big.crop((0, pad, w + 2 * pad, pad + 1)), big.crop((0, pad + h - 1, w + 2 * pad, pad + h))
    for i in range(pad):
        big.paste(top, (0, i))
        big.paste(bottom, (0, pad + h + i))
    atlas.paste(big, (x - pad, y - pad))


def pack(files, out_png: Path, size: int, grid, cell, content, pad: int = 16, preset: str = "custom",
         px_per_mm=None) -> dict:
    cols, rows = grid
    cw, ch = cell
    tw, th = content
    if cols * cw > size or rows * ch > size:
        raise ValueError(f"grid {cols}x{rows} of {cw}x{ch} does not fit a {size} atlas")
    if tw + 2 * pad > cw or th + 2 * pad > ch:
        raise ValueError(f"content {tw}x{th} + {pad} px padding does not fit a {cw}x{ch} cell")
    if len(files) > cols * rows:
        raise ValueError(f"{len(files)} images but only {cols * rows} cells")
    atlas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cells = []
    for i, f in enumerate(files):
        col, row = i % cols, i // cols
        x = col * cw + (cw - tw) // 2
        y = row * ch + (ch - th) // 2
        img = Image.open(f).convert("RGBA").resize((tw, th), Image.LANCZOS)
        dilate_into(atlas, img, x, y, pad)
        cells.append({"index": i, "file": Path(f).name, "col": col, "row": row, "rect_px": [x, y, tw, th],
                      "rect_uv": [x / size, y / size, tw / size, th / size]})
    out_png.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(out_png)
    index = {"tool": "csk_pack_cards", "version": TOOL_VERSION, "atlas": out_png.name, "size": size,
             "preset": preset, "grid": [cols, rows], "cell_px": [cw, ch], "content_px": [tw, th], "pad_px": pad,
             "px_per_mm": px_per_mm, "uv_origin": "top-left (Unreal)", "cells": cells}
    out_png.with_suffix(".json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return index


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder")
    ap.add_argument("out_png")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="cards")
    ap.add_argument("--grid", type=_pair)
    ap.add_argument("--cell", type=_pair)
    ap.add_argument("--content", type=_pair)
    ap.add_argument("--size", type=int)
    ap.add_argument("--pad", type=int, default=16)
    a = ap.parse_args(argv)
    p = dict(PRESETS[a.preset])
    for key in ("grid", "cell", "content", "size"):
        if getattr(a, key):
            p[key] = getattr(a, key)
    files = sorted(f for f in Path(a.folder).iterdir() if f.suffix.lower() in IMAGE_EXT)
    if not files:
        print(f"no images in {a.folder}", file=sys.stderr)
        return 1
    idx = pack(files, Path(a.out_png), p["size"], p["grid"], p["cell"], p["content"], a.pad, a.preset,
               p.get("px_per_mm"))
    print(f"CSK_PACK_CARDS packed {len(idx['cells'])} images -> {a.out_png} (+ .json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
