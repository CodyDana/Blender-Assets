"""b2_rig_sheet.py - PRIVATE / DO NOT SHIP. Labelled contact sheet of the step C1 deformation renders (py -3, PIL).

  py -3 b2_rig_sheet.py <render_dir> <out.png> [title]
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont

ORDER = ["apose", "walk", "run", "squat", "arms_up", "arms_forward", "tpose", "twist45", "head_turn60", "fist"]


def font(sz):
    for f in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def label(im, text, sz=22, pos=(8, 6)):
    d = ImageDraw.Draw(im)
    f = font(sz)
    bb = d.textbbox(pos, text, font=f)
    d.rectangle((bb[0] - 5, bb[1] - 3, bb[2] + 5, bb[3] + 3), fill=(20, 20, 24))
    d.text(pos, text, font=f, fill=(255, 255, 255))


def main():
    rd, out = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "2B private - step C1 deformation test (PRIVATE / DO NOT SHIP)"
    cells = []
    for p in ORDER:
        for v in ("front", "side"):
            f = f"{rd}/{p}_{v}.png"
            if os.path.exists(f):
                cells.append((f"{p} - {v}", f))
    for s in ("l", "r"):
        f = f"{rd}/fist_close_{s}.png"
        if os.path.exists(f):
            cells.append((f"fist close {s}", f))
    W, H = 320, 440
    cols = 6
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W + 20, rows * (H + 8) + 64), (30, 30, 34))
    label(sheet, title, 26, (12, 14))
    for i, (lab, f) in enumerate(cells):
        im = Image.open(f).convert("RGB")
        im.thumbnail((W, H), Image.LANCZOS)
        tile = Image.new("RGB", (W, H), (40, 40, 44))
        tile.paste(im, ((W - im.size[0]) // 2, (H - im.size[1]) // 2))
        label(tile, lab, 18, (6, 6))
        r, c = divmod(i, cols)
        sheet.paste(tile, (10 + c * W, 60 + r * (H + 8)))
    sheet.save(out)
    print("sheet", out, sheet.size, len(cells))


main()
