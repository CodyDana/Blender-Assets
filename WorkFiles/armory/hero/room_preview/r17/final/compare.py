"""r17 fix round (test copy): side-by-sides reference 2 | r17 merge (before_fix/) | r17 fixed for C1 (1448 x 1086 and
1600 x 900; night and golden), r17 merge | r17 fixed (night, golden) for the other views, the corner niche and mat
close-ups against the niche / mat rounds' finals, and whole-frame mean display luminance. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = ROOT / "reference" / "armory3_reference2.png"
PREV = HERE / "before_fix"
R16 = ROOT / "build" / "renders" / "night_r16"
NICHE = HERE.parent / "niche" / "final"
MAT = HERE.parent / "mat" / "final"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)
CAMS = ("C1_EntryReveal", "CX_FromPlatform", "C10_Hero", "C3_Case3", "C4_ShurikenTray", "C5_CloakCase", "CW_WestAisle")


def side(paths, labels, out):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h), Image.LANCZOS) for i in ims]
    im = Image.new("RGB", (sum(i.width for i in ims) + 16 * (len(ims) - 1), h + 26), (20, 20, 20))
    d = ImageDraw.Draw(im)
    x = 0
    for i, lab in zip(ims, labels):
        d.text((x + 6, 6), lab, fill=(230, 230, 230))
        im.paste(i, (x, 26))
        x += i.width + 16
    im.save(out)
    print("wrote", out, im.size)


def lum(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    return round(float((a @ np.array([0.2126, 0.7152, 0.0722])).mean()), 3)


for P in ("night", "golden"):
    side([REF, PREV / "ref_aspect" / f"C1_EntryReveal_{P}.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", f"r17 merge ({P})", f"r17 fixed ({P})"], OUT / f"C1_ref_vs_r17merge_vs_r17fixed_{P}.png")
    side([REF, PREV / f"C1_EntryReveal_{P}.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", f"r17 merge ({P})", f"r17 fixed ({P})"], OUT / f"C1_ref_vs_r17merge_vs_r17fixed_{P}_1600x900.png")
    for cam in CAMS[1:]:
        side([PREV / f"{cam}_{P}.png", HERE / f"{cam}_{P}.png"], [f"r17 merge ({P})", f"r17 fixed ({P})"],
             OUT / f"{cam}_r17merge_vs_r17fixed_{P}.png")
    for cam in ("CN_WestNiche", "CN_EastNiche"):
        side([NICHE / P / f"{cam}_{P}.png", HERE / "closeups" / f"{cam}_{P}.png"],
             [f"r17 niche round ({P})", f"r17 fixed ({P})"], OUT / f"{cam}_r17niche_vs_r17fixed_{P}.png")
    side([MAT / P / f"CE_MatDown_{P}.png", HERE / "closeups" / f"CE_MatDown_{P}.png"],
         [f"r17 mat round ({P})", f"r17 fixed ({P})"], OUT / f"CE_MatDown_r17mat_vs_r17fixed_{P}.png")
# the mat at 2x in C1 (reference 2 | r17 merge | r17 fixed), both presets
box = (380, 900, 1080, 1086)
crops = [Image.open(REF).convert("RGB").crop(box)]
labels = ["reference 2"]
for P in ("night", "golden"):
    crops += [Image.open(PREV / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB").crop(box),
              Image.open(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB").crop(box)]
    labels += [f"r17 merge ({P})", f"r17 fixed ({P})"]
w, h = (box[2] - box[0]) * 2, (box[3] - box[1]) * 2
im = Image.new("RGB", (w, len(crops) * (h + 22)), (20, 20, 20))
d = ImageDraw.Draw(im)
for k, (c, lab) in enumerate(zip(crops, labels)):
    im.paste(c.resize((w, h), Image.LANCZOS), (0, k * (h + 22) + 22))
    d.text((6, k * (h + 22) + 5), lab, fill=(230, 230, 230))
im.save(OUT / "C1_mat_2x_ref_r17merge_r17fixed.png")

stats = {"reference2": lum(REF)}
for tag, dd in (("r17merge", PREV), ("r17fixed", HERE)):
    for P in ("night", "golden"):
        stats[f"{tag}/{P}/ref_aspect/C1"] = lum(dd / "ref_aspect" / f"C1_EntryReveal_{P}.png")
        for cam in CAMS:
            stats[f"{tag}/{P}/{cam}"] = lum(dd / f"{cam}_{P}.png")
stats["night_r16/night/ref_aspect/C1"] = lum(R16 / "ref_aspect" / "C1_EntryReveal_night.png")
json.dump(stats, open(OUT / "luminance.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
