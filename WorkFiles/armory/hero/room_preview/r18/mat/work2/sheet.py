"""sheet.py TAG : reference 2 / golden / night mat crops (2x) + an 8x field crop, and metrics"""
import sys, subprocess
from PIL import Image, ImageDraw
import numpy as np
W = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/hero/room_preview/r18/mat/work2"
REF = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/reference/armory3_reference2.png"
tag = sys.argv[1]
ims = [("ref", REF)] + [(p, f"{W}/it/{tag}/{p}/C1_EntryReveal_{p}.png") for p in ("golden", "night")]
tiles = []
for lab, p in ims:
    c = Image.open(p).convert("RGB").crop((340, 880, 1110, 1086)).resize((1540, 412), Image.LANCZOS)
    ImageDraw.Draw(c).text((6, 4), lab, fill=(255, 255, 0))
    tiles.append(c)
s = Image.new("RGB", (1540, 412 * 3))
for i, t in enumerate(tiles):
    s.paste(t, (0, 412 * i))
s.save(f"{W}/it/{tag}/sheet.png")
t2 = []
for lab, p in ims:
    t2.append(Image.open(p).convert("RGB").crop((640, 960, 800, 1060)).resize((640, 400), Image.BICUBIC))
s = Image.new("RGB", (640 * 3, 400))
for i, t in enumerate(t2):
    s.paste(t, (640 * i, 0))
s.save(f"{W}/it/{tag}/field4x.png")
