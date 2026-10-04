"""probe: draw candidate slit columns on 4x crops of the photo's skirts"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
T7 = Path(__file__).resolve().parent
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
img = Image.open(ROOT / "References/Dojo/taiko_tacks_ref_user.webp").convert("RGB")
UP = [int(x) for x in sys.argv[1].split(",")]
LO = [int(x) for x in sys.argv[2].split(",")]


def crop(box, name, marks, k=3):
    c = img.crop(box).resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for x in marks:
        if box[0] <= x < box[2]:
            X = (x - box[0]) * k
            d.line([(X, 0), (X, 18)], fill=(255, 0, 0), width=2)
            d.line([(X, c.height - 18), (X, c.height)], fill=(255, 0, 0), width=2)
            d.text((X + 3, 2), str(x), fill=(255, 0, 0))
    c.save(T7 / name)


crop((100, 240, 520, 345), "p4_u0.png", UP)
crop((500, 240, 920, 345), "p4_u1.png", UP)
crop((130, 700, 530, 915), "p4_l0.png", LO)
crop((500, 700, 900, 915), "p4_l1.png", LO)
