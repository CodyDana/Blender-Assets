"""hy_before_after.py -- PRIVATE / DO NOT SHIP. v1 (Hiyuki likeness) vs v2 (idol) sheet of MH_Hiyuki_Private.
    py -3 Scripts/MetaHuman/hy_before_after.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/hiyuki_private")
V1, V2 = OUT / "v1/verify_captures", OUT / "verify_captures"
VIEWS = ["Face_Front", "Face_TQ_L", "Face_Profile_L", "Face_Close"]
CROP = {"Face_Close": None}
W = 330


def tile(path: Path, text: str) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if CROP.get(path.stem.replace("hy_", ""), (130, 120, 870, 1060)):
        im = im.crop(CROP.get(path.stem.replace("hy_", ""), (130, 120, 870, 1060)))
    im = im.resize((W, round(im.height * W / im.width)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 20], fill=(0, 0, 0))
    d.text((6, 4), text, fill=(255, 255, 255))
    return im


rows = [[tile(V1 / f"hy_{v}.png", f"BEFORE v1 Hiyuki  {v}") for v in VIEWS],
        [tile(V2 / f"hy_{v}.png", f"AFTER v2 idol  {v}") for v in VIEWS]]
h = max(t.height for r in rows for t in r)
sheet = Image.new("RGB", (W * len(VIEWS) + 6 * (len(VIEWS) - 1), 2 * h + 36), (20, 20, 20))
ImageDraw.Draw(sheet).text((6, 8), "PRIVATE / DO NOT SHIP  -  MH_Hiyuki_Private v1 -> v2", fill=(255, 200, 80))
for r, row in enumerate(rows):
    for c, t in enumerate(row):
        sheet.paste(t, (c * (W + 6), 30 + r * (h + 6)))
dst = OUT / "sheets/before_after_v1_v2.png"
dst.parent.mkdir(parents=True, exist_ok=True)
sheet.save(dst)
print(dst, sheet.size)
