"""Comparison sheets for the rear dais round: reference | before (live) | ours, into rear/compare."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

R = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\hero\room_preview\rear")
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")
tag = sys.argv[1]
BEF = sys.argv[2] if len(sys.argv) > 2 else "before"
BEFN = "live" if BEF == "before" else BEF
OUT = R / "compare"
OUT.mkdir(exist_ok=True)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 11 * len(text) + 16, 30), fill=(0, 0, 0))
    d.text((8, 8), text, fill=(255, 255, 255))
    return im


def row(ims, names, h=None, gap=16):
    h = h or min(i.height for i in ims)
    ims = [label(i.resize((int(i.width * h / i.height), h)), n) for i, n in zip(ims, names)]
    out = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), (255, 255, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def col(ims, gap=16):
    w = max(i.width for i in ims)
    out = Image.new("RGB", (w, sum(i.height for i in ims) + gap * (len(ims) - 1)), (255, 255, 255))
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + gap
    return out


ref = Image.open(REF).convert("RGB").resize((1448, 1086))
for P in ("golden", "night"):
    before = Image.open(R / BEF / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    ours = Image.open(R / tag / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    row([ref, ours], ["reference 2", f"rear dais {tag} ({P})"]).save(OUT / f"C1_ref_vs_{tag}_{P}.png")
    box = (200, 20, 1250, 440)
    crops = [i.crop(box).resize((1575, 630)) for i in (ref, before, ours)]
    col([label(c, n) for c, n in zip(crops, ["reference 2", f"before: {BEFN} ({P})", f"rear dais {tag} ({P})"])]).save(
        OUT / f"C1_rear_crop_ref_before_{tag}_{P}.png")
    for cam in ("CX_FromPlatform", "C10_Hero", "CR_RearHigh"):
        b = Image.open(R / BEF / P / f"{cam}_{P}.png").convert("RGB")
        o = Image.open(R / tag / P / f"{cam}_{P}.png").convert("RGB")
        row([ref, b, o], ["reference 2", f"before: {BEFN} {cam}", f"rear dais {tag} {cam}"], h=700).save(
            OUT / f"{cam}_ref_before_{tag}_{P}.png")
print("sheets in", OUT)
