"""Selector review helper (plain Python): stack the reference c1 crop and our c1 renders, zoomed on the lever.

    py -3 -B Scripts/guns/rifle/parts/selector_look.py s2a s2b [--box 60,80,250,145] [--zoom 4] [--out name.png]

Reads WorkFiles/guns/rifle/review/detail/selector/{ref_c1.png, <tag>_ours_c1.png}; writes the stack into the
selector's scratch folder (or --out).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RV = ROOT / "WorkFiles" / "guns" / "rifle" / "review" / "detail" / "selector"
WS = ROOT / "WorkFiles" / "guns" / "rifle" / "scratch" / "detail" / "selector"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--box", default="60,80,250,145")
    ap.add_argument("--zoom", type=int, default=4)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    x0, y0, x1, y1 = [int(v) for v in a.box.split(",")]
    z = a.zoom
    names = ["ref_c1.png"] + [f"{t}_ours_c1.png" for t in a.tags]
    labels = ["reference c1"] + a.tags
    tiles = []
    for n, lab in zip(names, labels):
        im = Image.open(RV / n).convert("RGB").crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), 3)
        ImageDraw.Draw(im).text((6, 4), lab, fill=(255, 80, 80))
        tiles.append(im)
    W, H = tiles[0].size
    out = Image.new("RGB", (W, H * len(tiles)), (255, 255, 255))
    for i, t in enumerate(tiles):
        out.paste(t, (0, i * H))
    path = Path(a.out) if a.out else WS / ("look_" + "_".join(a.tags) + ".png")
    out.save(path)
    print(path)


if __name__ == "__main__":
    main()
