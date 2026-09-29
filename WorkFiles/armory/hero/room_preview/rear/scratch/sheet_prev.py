"""reference | previous build | this build, C1 rear crop and the CR_RearHigh / C10 / CX views: rear/compare.
usage: py -3 sheet_prev.py <prev tag> <tag>"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

R = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\rear")
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")
prev, tag = sys.argv[1:3]
OUT = R / "compare"


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 7 * len(text) + 16, 22), fill=(0, 0, 0))
    d.text((8, 5), text, fill=(255, 255, 255))
    return im


ref = Image.open(REF).convert("RGB").resize((1448, 1086))
for P in ("golden", "night"):
    a = Image.open(R / prev / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    b = Image.open(R / tag / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    box = (180, 0, 1270, 440)
    w, h = box[2] - box[0], box[3] - box[1]
    s = 1.4
    cw, ch = int(w * s), int(h * s)
    out = Image.new("RGB", (cw, ch * 3 + 16), (255, 255, 255))
    for i, (im, n) in enumerate(((ref, "reference 2"), (a, f"{prev} ({P})"), (b, f"{tag} ({P})"))):
        out.paste(label(im.crop(box).resize((cw, ch)), n), (0, i * (ch + 8)))
    out.save(OUT / f"C1_rear_crop_ref_{prev}_{tag}_{P}.png")
    full = Image.new("RGB", (1448 * 2 + 16, 1086), (255, 255, 255))
    full.paste(label(ref.copy(), "reference 2"), (0, 0))
    full.paste(label(b.copy(), f"rear dais {tag} ({P})"), (1464, 0))
    full.save(OUT / f"C1_ref_vs_{tag}_{P}.png")
    for cam in ("CX_FromPlatform", "C10_Hero", "CR_RearHigh"):
        ims = [ref] + [Image.open(R / t / P / f"{cam}_{P}.png").convert("RGB") for t in (prev, tag)]
        hh = 700
        ims = [label(i.resize((int(i.width * hh / i.height), hh)), n)
               for i, n in zip(ims, ["reference 2", f"{prev} {cam}", f"{tag} {cam}"])]
        o = Image.new("RGB", (sum(i.width for i in ims) + 32, hh), (255, 255, 255))
        x = 0
        for i in ims:
            o.paste(i, (x, 0))
            x += i.width + 16
        o.save(OUT / f"{cam}_ref_{prev}_{tag}_{P}.png")
print("sheets in", OUT)
