"""r20 round live (night_r20): side-by-sides reference 2 | night_r19 | night_r20 for C1 (1448 x 1086 and 1600 x 900),
night_r19 | night_r20 for the other views, and whole-frame mean display luminance. CN_WestNiche is compared too
(night_r19 has one). Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")
PREV = HERE.parent / "night_r19"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)
CAMS = ("C1_EntryReveal", "CX_FromPlatform", "C10_Hero", "C3_Case3", "C5_CloakCase", "CW_WestAisle",
        "C4_ShurikenTray", "CG_Garden")


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


side([REF, PREV / "ref_aspect" / "C1_EntryReveal_night.png", HERE / "ref_aspect" / "C1_EntryReveal_night.png"],
     ["reference 2", "night_r19", "night_r20"], OUT / "C1_ref_vs_night_r19_vs_night_r20.png")
side([REF, PREV / "C1_EntryReveal_night.png", HERE / "C1_EntryReveal_night.png"],
     ["reference 2", "night_r19", "night_r20"], OUT / "C1_ref_vs_night_r19_vs_night_r20_1600x900.png")
for cam in CAMS[1:]:
    side([PREV / f"{cam}_night.png", HERE / f"{cam}_night.png"], ["night_r19", "night_r20"],
         OUT / f"{cam}_night_r19_vs_night_r20.png")

stats = {"reference2": lum(REF)}
for tag, d in (("night_r19", PREV), ("night_r20", HERE)):
    stats[f"{tag}/ref_aspect/C1"] = lum(d / "ref_aspect" / "C1_EntryReveal_night.png")
    for cam in CAMS:
        stats[f"{tag}/{cam}"] = lum(d / f"{cam}_night.png")
side([PREV / "CN_WestNiche_night.png", HERE / "CN_WestNiche_night.png"], ["night_r19", "night_r20"],
     OUT / "CN_WestNiche_night_r19_vs_night_r20.png")
for tag, d in (("night_r19", PREV), ("night_r20", HERE)):
    stats[f"{tag}/CN_WestNiche"] = lum(d / "CN_WestNiche_night.png")
json.dump(stats, open(OUT / "luminance.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
