#!/usr/bin/env python3
"""G1 placeholder print art for the Card Shop Kit standards spike (system Python 3 + Pillow; not for sale).

The pictures exist to prove the art paths in Unreal (gate G1 test 1), so every image is built to reveal a wrong
mapping at a glance: a big asymmetric letter (F front, B back, L label), "TOP" with an arrow at the top edge, and a
different colour in each corner (top-left RED, top-right GREEN, bottom-left BLUE, bottom-right YELLOW). A mirrored
or flipped face swaps the corner colours; a wrong atlas cell shows the wrong line name or number.

    py -3 Scripts/cardshop/art/g1_placeholder_art.py [--src DIR] [--tex DIR]

Writes the source faces to ``WorkFiles/cardshop/g1/art/`` and, into ``Exports/CardShopKit/G1/Textures/``:
* atlases through ``tools/csk_pack_cards.py``: T_CSK_G1_Cards_BC (4096), T_CSK_G1_Packs_BC (4096),
  T_CSK_G1_Labels_BC (2048), each with its .json cell index
* plain power-of-two textures for the plain-texture path: T_CSK_G1_{CardFront,CardBack,PackFront,PackBack,
  Label,BoxDieline}_BC

The user's own card illustrations replace the card faces later (CARD_ART_BRIEF.md); this script is only the test
pattern. Brand names are the picked fictional ones (BRAND_NAMES.md).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "Scripts" / "cardshop" / "tools"))
import csk_pack_cards as P  # noqa: E402

PX = 10                       # source art at 10 px/mm
CORNERS = {"TL": (220, 30, 30), "TR": (30, 170, 60), "BL": (40, 80, 220), "BR": (235, 200, 20)}
LINES = {"PYRECALL": (178, 58, 24), "LUMENFOLD": (26, 96, 140), "RIMVAULT": (46, 120, 64)}
GRADERS = {"CLEARMARK GRADING": (240, 240, 236), "HALCYON GRADING": (236, 242, 248)}


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:          # Pillow < 10.1: fixed-size bitmap font
        return ImageFont.load_default()


def centred(d: ImageDraw.ImageDraw, xy, text, size, fill=(255, 255, 255)):
    f = font(size)
    box = d.textbbox((0, 0), text, font=f)
    d.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2 - box[1]), text, font=f, fill=fill)


def test_face(w_mm: float, h_mm: float, bg, letter: str, title: str, sub: str) -> Image.Image:
    w, h = int(round(w_mm * PX)), int(round(h_mm * PX))
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    b = max(6, int(min(w, h) * 0.035))
    d.rectangle([0, 0, w - 1, h - 1], outline=(20, 20, 20), width=b)
    s = max(10, int(min(w, h) * 0.12))
    for key, (x, y) in {"TL": (b, b), "TR": (w - b - s, b), "BL": (b, h - b - s), "BR": (w - b - s, h - b - s)}.items():
        d.rectangle([x, y, x + s, y + s], fill=CORNERS[key])
    big = int(min(w, h) * (0.55 if h > w * 0.5 else 0.6))
    ink = (20, 20, 20) if sum(bg) > 450 else (255, 255, 255)    # dark letters on light grounds (labels)
    centred(d, (w / 2, h / 2), letter, big, ink)
    t = max(10, int(min(w, h) * 0.07))
    top_y = b + s / 2
    centred(d, (w / 2, top_y), "TOP", t)
    d.polygon([(w / 2 - t, top_y + t * 1.1), (w / 2 + t, top_y + t * 1.1), (w / 2, top_y + t * 0.3)],
              fill=(255, 255, 255))
    if h > w * 0.5:
        centred(d, (w / 2, h * 0.22), title, max(10, int(w * 0.075)))
        centred(d, (w / 2, h * 0.80), sub, max(8, int(w * 0.05)))
        centred(d, (w / 2, h - b - s * 1.4), "G1 PLACEHOLDER - NOT FOR SALE", max(8, int(w * 0.035)))
    else:
        centred(d, (w * 0.30, h / 2), title, max(8, int(h * 0.16)), (20, 20, 20))
        centred(d, (w * 0.80, h / 2), sub, max(8, int(h * 0.22)), (20, 20, 20))
    return im


def dieline(line: str) -> Image.Image:
    """Booster box S dieline, 440 x 305 mm (spec 3.B, sheet 5): front | right | back | left, bottom under the front,
    lid over the back with its tuck-flap tab above it. Each panel labelled and with an up arrow in its own 'up'
    direction. The lid's inside (the display header) samples the LID panel from the back tile."""
    W, D, H = 140, 80, 125
    TW, TH = 77, 20
    SH = H + 2 * D + TH
    px = 4
    im = Image.new("RGB", (440 * px, SH * px), (250, 250, 250))
    d = ImageDraw.Draw(im)
    col = LINES[line]
    # panels in dieline mm, origin bottom-left (v up) -> image rows flipped
    panels = {"FRONT": (0, D, W, H), "RIGHT": (W, D, D, H), "BACK": (W + D, D, W, H), "LEFT": (2 * W + D, D, D, H),
              "BOTTOM": (0, 0, W, D), "LID": (W + D, D + H, W, D),
              "TAB": (W + D + (W - TW) / 2, D + H + D, TW, TH)}
    for name, (x, y, w, h) in panels.items():
        x0, x1 = x * px, (x + w) * px
        y0, y1 = (SH - (y + h)) * px, (SH - y) * px
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=col if name in ("FRONT", "BACK", "LID", "TAB") else
                    tuple(int(c * 0.7) for c in col), outline=(20, 20, 20), width=4)
        centred(d, ((x0 + x1) / 2, (y0 + y1) / 2), name, int(min(x1 - x0, y1 - y0) * 0.22))
        if name != "TAB":
            centred(d, ((x0 + x1) / 2, y0 + 40), "^ UP", 36)
    centred(d, (W * px / 2, (SH - D - H * 0.25) * px), line, 64)
    s = 60
    for key, (x, y) in {"TL": (0, 0), "TR": (440 * px - s, 0), "BL": (0, SH * px - s),
                        "BR": (440 * px - s, SH * px - s)}.items():
        d.rectangle([x, y, x + s, y + s], fill=CORNERS[key])
    return im


def pot(im: Image.Image, size) -> Image.Image:
    return im.resize(size, Image.LANCZOS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(PROJECT / "WorkFiles" / "cardshop" / "g1" / "art"))
    ap.add_argument("--tex", default=str(PROJECT / "Exports" / "CardShopKit" / "G1" / "Textures"))
    a = ap.parse_args(argv)
    src, tex = Path(a.src), Path(a.tex)
    for sub in ("cards", "packs", "labels", "boxes"):
        (src / sub).mkdir(parents=True, exist_ok=True)
    tex.mkdir(parents=True, exist_ok=True)
    made = []
    # cards: 2 fronts per line + 1 shared back (atlas order: file name order)
    k = 0
    for line, col in LINES.items():
        for n in (1, 2):
            im = test_face(63, 88, col, "F", line, f"CARD {n:02d}  (cell {k})")
            p = src / "cards" / f"{k:02d}_{line.lower()}_{n:02d}_front.png"
            im.save(p)
            made.append(p)
            k += 1
    back = test_face(63, 88, (60, 60, 70), "B", "CARD BACK", f"(cell {k})")
    back.save(src / "cards" / f"{k:02d}_back.png")
    # packs: front then back per line
    k = 0
    for line, col in LINES.items():
        for side, letter in (("front", "F"), ("back", "B")):
            im = test_face(67, 117, col if side == "front" else tuple(int(c * 0.6) for c in col), letter,
                           line, f"PACK {side.upper()} (cell {k})")
            im.save(src / "packs" / f"{k:02d}_{line.lower()}_{side}.png")
            k += 1
    # slab labels, one per grader
    for k, (g, col) in enumerate(GRADERS.items()):
        im = test_face(76, 24, col, "L", g, f"GRADE 9  c{k}")
        im.save(src / "labels" / f"{k:02d}_{g.split()[0].lower()}.png")
    die = dieline("PYRECALL")
    die.save(src / "boxes" / "00_pyrecall_dieline.png")

    # atlases (buyer tool, the same code a buyer runs)
    for preset, name in (("cards", "T_CSK_G1_Cards_BC"), ("packs", "T_CSK_G1_Packs_BC"),
                         ("labels", "T_CSK_G1_Labels_BC")):
        pr = P.PRESETS[preset]
        files = sorted((src / preset).glob("*.png"))
        P.pack(files, tex / f"{name}.png", pr["size"], pr["grid"], pr["cell"], pr["content"], 16, preset,
               pr["px_per_mm"])
    # plain power-of-two textures (the plain-texture path: the image fills the 0-1 tile)
    cards = sorted((src / "cards").glob("*.png"))
    packs = sorted((src / "packs").glob("*.png"))
    labels = sorted((src / "labels").glob("*.png"))
    pot(Image.open(cards[0]), (512, 1024)).save(tex / "T_CSK_G1_CardFront_BC.png")
    pot(Image.open(cards[-1]), (512, 1024)).save(tex / "T_CSK_G1_CardBack_BC.png")
    pot(Image.open(packs[0]), (512, 1024)).save(tex / "T_CSK_G1_PackFront_BC.png")
    pot(Image.open(packs[1]), (512, 1024)).save(tex / "T_CSK_G1_PackBack_BC.png")
    pot(Image.open(labels[0]), (1024, 256)).save(tex / "T_CSK_G1_Label_BC.png")
    pot(die, (2048, 1024)).save(tex / "T_CSK_G1_BoxDieline_BC.png")
    for line in ("LUMENFOLD", "RIMVAULT"):          # the other two lines' colourways (box variety in the shop room)
        pot(dieline(line), (2048, 1024)).save(tex / f"T_CSK_G1_BoxDieline_{line.title()}_BC.png")
    print(f"CSK_G1_ART done: {len(list(tex.glob('*.png')))} textures in {tex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
