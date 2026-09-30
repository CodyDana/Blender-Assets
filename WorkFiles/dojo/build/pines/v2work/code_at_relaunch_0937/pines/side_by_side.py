"""Reference crop | ours, same height, labelled (system Python + PIL). compose_pines.py builds the whole set with it.

    py -3 -B Scripts/dojo/pines/side_by_side.py <reference.png> <x0,y0,x1,y1 | full> <ours.png> <out.png> [label_l] [label_r]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_pines import on_grey, pair  # noqa: E402


def main():
    ref, box, ours, out = sys.argv[1:5]
    labels = (sys.argv[5] if len(sys.argv) > 5 else "reference", sys.argv[6] if len(sys.argv) > 6 else "ours")
    left = Image.open(ref).convert("RGB")
    if box != "full":
        left = left.crop(tuple(int(v) for v in box.split(",")))
    right, _ = on_grey(ours)
    pair(left, right, labels, out)


if __name__ == "__main__":
    main()
