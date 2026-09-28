"""Before / after evidence for the hooked-cross maintenance (library 3.9.0 build -> 3.9.1), plain Python + Pillow:

    py -3 WorkFiles/shuriken/hooked_cross_maint/evidence_sheets.py <before_renders_dir> <before_textures_dir>

<before_*> are the pre-maintenance files (the hooked-cross build's snapshot, regression/post_hooked_cross/renders and
/textures, taken before this pass replaced it; a copy is kept in hooked_cross_maint/before/).  Writes next to this file:

  runout_compare.png         the blade run-out, before | after: the top view's right hook (x5) and the hero's two nearest
                             run-outs (x4); the before shows the square bright cap and the plunge highlight
  texture_sheets_compare.png T_Shuriken_HookedCross_BC before | after at 1/4 scale (the before's upper-left island is
                             the -Z plate seen from below: the mirrored form; after, both plate islands read left-facing)
  lodgrind_highlight.json    share of frame pixels over 0.9 luma (stored sRGB, Rec.709) in every form's <form>_lodgrind.png,
                             before and after (the visual review: hooked cross 18.1 %, stars 1.5-4.8 %)

Nothing here is a gate; the gates are in the build (texture_handedness, render gates) and in UnrealCheck6.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = Path(__file__).resolve().parent
RENDERS = PROJ / "Renders" / "Shuriken"
TEXTURES = PROJ / "Exports" / "Shuriken" / "Textures"
FONT = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
SMALL = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
FORMS = ("four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross")


def crop(path, box, scale):
    img = Image.open(path).convert("RGB").crop(box)
    return img.resize((img.size[0] * scale, img.size[1] * scale), Image.NEAREST)


def labelled(img, text):
    out = Image.new("RGB", (img.size[0], img.size[1] + 34), (24, 24, 26))
    out.paste(img, (0, 34))
    ImageDraw.Draw(out).text((8, 6), text, font=FONT, fill=(255, 225, 90))
    return out


def row(images, gap=8):
    w = sum(i.size[0] for i in images) + gap * (len(images) - 1)
    h = max(i.size[1] for i in images)
    out = Image.new("RGB", (w, h), (24, 24, 26))
    x = 0
    for i in images:
        out.paste(i, (x, 0))
        x += i.size[0] + gap
    return out


def column(images, gap=8):
    w = max(i.size[0] for i in images)
    h = sum(i.size[1] for i in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (w, h), (24, 24, 26))
    y = 0
    for i in images:
        out.paste(i, (0, y))
        y += i.size[1] + gap
    return out


def luma_over(path, threshold=0.9):
    img = Image.open(path).convert("RGB")
    px = img.getdata()
    over = sum(1 for r, g, b in px if (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0 > threshold)
    return round(over / (img.size[0] * img.size[1]), 4)


def main():
    before_r, before_t = Path(sys.argv[1]), Path(sys.argv[2])
    top_box, hero_a, hero_b = (1000, 150, 1110, 450), (1380, 440, 1500, 560), (920, 140, 1040, 240)
    rows = []
    for label, d in (("3.9.0 (before)", before_r), ("3.9.1 (after)", RENDERS)):
        rows.append(row([labelled(crop(d / "hooked_cross_top.png", top_box, 3), f"{label}: top, +X arm's hook x3"),
                         labelled(crop(d / "hooked_cross_persp.png", hero_a, 3), "hero, near run-out x3"),
                         labelled(crop(d / "hooked_cross_persp.png", hero_b, 3), "hero, far hook x3")]))
    sheet = column(rows)
    sheet.save(HERE / "runout_compare.png")
    tex = []
    for label, d in (("3.9.0: the -Z island (upper left) is the mirrored form", before_t),
                     ("3.9.1: both plate islands read as the +Z face", TEXTURES)):
        img = Image.open(d / "T_Shuriken_HookedCross_BC.png").convert("RGB").resize((768, 768), Image.LANCZOS)
        tex.append(labelled(img, label))
    row(tex, gap=16).save(HERE / "texture_sheets_compare.png")
    stats = {"threshold_luma": 0.9, "metric": "share of frame pixels with stored-sRGB Rec.709 luma > 0.9",
             "after": {f: luma_over(RENDERS / f"{f}_lodgrind.png") for f in FORMS},
             "before": {f: luma_over(before_r / f"{f}_lodgrind.png") for f in FORMS}}
    (HERE / "lodgrind_highlight.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("EVIDENCE", json.dumps(stats))


if __name__ == "__main__":
    main()
