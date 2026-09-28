#!/usr/bin/env python
"""Modern-line gallery sheet: every built form's hero (top row) and top view (bottom row), side by side.

Plain Python with Pillow (no Blender, nothing rendered): it only lays out the gallery PNGs build_pack.py
already rendered from the baked maps, so the sheet always shows the shipped look.  Columns follow
WorkFiles/shuriken/pack_report.json "forms" (build order); each hero tile is labelled from that form's
report (across, plate thickness, finished = knife-ground mass).  The top views keep the rig's common
scale (one ortho frame for every form), so the sizes compare directly.

    py -3 Scripts/shuriken/line_sheet.py [--out Renders/Shuriken/modern_line_sheet.png] [--tile 800]

Re-run after every pack rebuild that changes the gallery (a new form, a material pass); a sheet older
than the renders it shows is stale (the pre-restyle sheet was archived for exactly that).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[2]
RENDERS = PROJECT / "Renders" / "Shuriken"
PACK_REPORT = PROJECT / "WorkFiles" / "shuriken" / "pack_report.json"
SHORT = {"four_point": "Four-point", "eight_point": "Eight-point", "square_plate": "Senban",
         "six_point": "Six-point", "spike": "Spike", "hooked_cross": "Hooked cross"}
FONT = Path("C:/Windows/Fonts/arial.ttf")


def label_for(form: str, report: dict) -> str:
    m = report["measured"]
    name = SHORT.get(form, report.get("title", form).split()[0])
    across = m.get("tip_to_tip_mm", m["across_mm"])      # the hooked cross: tip to tip (its tips are off the axes)
    return f"{name}  {across:.0f} mm  {m['thickness_mm']:.1f} mm  {m.get('ground_mass_g', m['mass_g']):.1f} g"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(RENDERS / "modern_line_sheet.png"))
    parser.add_argument("--tile", type=int, default=800, help="tile width in px (16:9 tiles)")
    args = parser.parse_args()
    pack = json.loads(PACK_REPORT.read_text(encoding="utf-8"))
    forms = list(pack["forms"])
    tile_w, tile_h = args.tile, args.tile * 9 // 16
    sheet = Image.new("RGB", (tile_w * len(forms), tile_h * 2), (40, 40, 40))
    font = ImageFont.truetype(str(FONT), max(12, tile_w * 22 // 800)) if FONT.exists() else ImageFont.load_default()
    pad = max(4, tile_w // 100)
    used = {}
    for col, form in enumerate(forms):
        report = json.loads(Path(pack["results"][form]["report"]).read_text(encoding="utf-8"))
        for row, shot in enumerate(("persp", "top")):
            src = RENDERS / f"{form}_{shot}.png"
            img = Image.open(src).convert("RGB")
            if img.size[0] * 9 != img.size[1] * 16:
                print(f"ERROR: {src} is not 16:9 ({img.size})")
                return 2
            sheet.paste(img.resize((tile_w, tile_h), Image.LANCZOS), (col * tile_w, row * tile_h))
            used[f"{form}_{shot}"] = str(src)
        text = label_for(form, report)
        draw = ImageDraw.Draw(sheet, "RGBA")
        x0, y0 = col * tile_w + pad, pad
        box = draw.textbbox((x0 + pad, y0 + pad // 2), text, font=font)
        draw.rectangle((x0, y0, box[2] + pad, box[3] + pad), fill=(20, 20, 20, 200))
        draw.text((x0 + pad, y0 + pad // 2), text, font=font, fill=(235, 235, 232, 255))
    out = Path(args.out).resolve()        # absolute: never relative to whatever the cwd is
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    print("LINE_SHEET " + json.dumps({"out": str(out), "size": list(sheet.size), "forms": forms,
                                      "labels": {f: label_for(f, json.loads(Path(pack["results"][f]["report"])
                                                                         .read_text(encoding="utf-8")))
                                                 for f in forms}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
