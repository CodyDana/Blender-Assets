"""(Realism R2) before / after crops of the judges' geometry items: round 1 (review/w4b/set) beside round 2
(review/r2/set), same cameras, same crop boxes (fractions of the frame). Plain Python:
    py -3 -B Scripts/guns/sniper/sr_r2_compare.py
Writes review/r2/compare/<item>.png (left = round 1, right = round 2) and a contact sheet compare_all.png.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
REV = ROOT / "WorkFiles" / "guns" / "sniper" / "review"
OUT = REV / "r2" / "compare"
ITEMS = [  # name, image, (x0, y0, x1, y1) as frame fractions
    ("grip_base", "close_stock_right", (0.72, 0.80, 0.94, 0.95)),
    ("grip_side", "close_action_right", (0.0, 0.58, 0.19, 1.0)),
    ("riser", "close_stock_right", (0.22, 0.13, 0.66, 0.37)),
    ("butt_pad", "close_stock_right", (0.02, 0.19, 0.20, 0.45)),
    ("stock_body", "close_stock_right", (0.18, 0.30, 0.80, 0.74)),
    ("chassis_underside", "close_action_right", (0.50, 0.55, 1.0, 0.72)),
    ("trigger_guard", "close_action_right", (0.25, 0.55, 0.53, 0.76)),
    ("forend_nose", "close_forend_right", (0.55, 0.25, 1.0, 0.80)),
]


def crop(p, box):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    return im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tiles = []
    for name, src, box in ITEMS:
        a, b = REV / "w4b" / "set" / f"{src}.png", REV / "r2" / "set" / f"{src}.png"
        if not (a.exists() and b.exists()):
            print("missing", name)
            continue
        A, B = crop(a, box), crop(b, box)
        s = 700.0 / max(A.size)
        A = A.resize((int(A.width * s), int(A.height * s)), Image.LANCZOS)
        B = B.resize(A.size, Image.LANCZOS)
        im = Image.new("RGB", (A.width * 2 + 10, A.height + 30), (255, 255, 255))
        im.paste(A, (0, 30))
        im.paste(B, (A.width + 10, 30))
        d = ImageDraw.Draw(im)
        d.text((6, 8), f"{name}: round 1 (W4b)", fill=(0, 0, 0))
        d.text((A.width + 16, 8), "round 2 (rim slab)", fill=(0, 0, 0))
        im.save(OUT / f"{name}.png")
        tiles.append(im)
    if tiles:
        W = max(t.width for t in tiles)
        sheet = Image.new("RGB", (W, sum(t.height + 8 for t in tiles)), (255, 255, 255))
        y = 0
        for t in tiles:
            sheet.paste(t, (0, y))
            y += t.height + 8
        sheet.save(OUT / "compare_all.png")
    print("COMPARE_DONE", len(tiles))


if __name__ == "__main__":
    main()
