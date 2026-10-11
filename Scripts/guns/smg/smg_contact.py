"""SMG01 contact sheet of the realism_tex renders (plain Python, PIL):

    py -3 -B Scripts/guns/smg/smg_contact.py [--dir WorkFiles/guns/smg/review/realism_tex]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import REVIEW, ROOT  # noqa: E402

VIEWS = ["fp_35cm", "ads", "tp_3m", "hero_34", "hero_34_folded", "closeups/g1_receiver_rails",
         "closeups/g2_grip_trigger_sel", "closeups/g3_magazine_well", "closeups/g4_stock_extended",
         "closeups/g5_stock_folded", "closeups/g6_front_end", "closeups/g7_rear_sight"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(REVIEW / "realism_tex"))
    a = ap.parse_args()
    d = Path(a.dir)
    tiles = []
    for v in VIEWS:
        p = d / f"{v}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB").resize((640, 360), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 6), v.split("/")[-1], fill=(255, 255, 255))
        tiles.append(im)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    W = Image.new("RGB", (640 * cols, 360 * rows), (40, 40, 40))
    for k, im in enumerate(tiles):
        W.paste(im, ((k % cols) * 640, (k // cols) * 360))
    W.save(d / "contact.png")
    (d / "shots.json").write_text(json.dumps({
        "look": "FINAL MAPS (W2 surface): game materials on Exports/Guns/SMG01/Textures/T_SMG01_*; renders only from "
                "the baked maps (smg_texrender.py), the early-realism cameras and lights",
        "blend": "Assets/Guns/SMG01.blend", "views": [v for v in VIEWS if (d / f"{v}.png").exists()]}, indent=1))
    print("[contact]", d / "contact.png", len(tiles))


if __name__ == "__main__":
    main()
