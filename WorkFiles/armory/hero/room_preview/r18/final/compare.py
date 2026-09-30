"""r18 combined test copy: side-by-sides reference 2 | night_r17 (live) | r18 combined for C1 (1448 x 1086 and
1600 x 900; night and golden), night_r17 | r18 combined (night, golden) for the other views, the corner niche and mat
close-ups against r17 live (r17/final/closeups) and the r18 niche / mat rounds' finals, and whole-frame mean display
luminance. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = ROOT / "reference" / "armory3_reference2.png"
R17 = ROOT / "build" / "renders" / "night_r17"
R17C = HERE.parent.parent / "r17" / "final" / "closeups"
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
    side([REF, R17 / "ref_aspect" / "C1_EntryReveal_night.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r17 (live, night)", f"r18 combined ({P})"], OUT / f"C1_ref_vs_night_r17_vs_r18_{P}.png")
    side([REF, R17 / "C1_EntryReveal_night.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r17 (live, night)", f"r18 combined ({P})"],
         OUT / f"C1_ref_vs_night_r17_vs_r18_{P}_1600x900.png")
    for cam in CAMS[1:]:
        side([R17 / f"{cam}_night.png", HERE / f"{cam}_{P}.png"], ["night_r17 (live, night)", f"r18 combined ({P})"],
             OUT / f"{cam}_night_r17_vs_r18_{P}.png")
    for cam in ("CN_WestNiche", "CN_EastNiche"):
        side([R17C / f"{cam}_{P}.png", NICHE / P / f"{cam}_{P}.png", HERE / "closeups" / f"{cam}_{P}.png"],
             [f"r17 live ({P})", f"r18 niche round ({P})", f"r18 combined ({P})"], OUT / f"{cam}_r17_vs_r18niche_vs_r18_{P}.png")
    side([R17C / f"CE_MatDown_{P}.png", MAT / P / f"CE_MatDown_{P}.png", HERE / "closeups" / f"CE_MatDown_{P}.png"],
         [f"r17 live ({P})", f"r18 mat round ({P})", f"r18 combined ({P})"], OUT / f"CE_MatDown_r17_vs_r18mat_vs_r18_{P}.png")

stats = {"reference2": lum(REF), "night_r17/ref_aspect/C1": lum(R17 / "ref_aspect" / "C1_EntryReveal_night.png")}
for cam in CAMS:
    stats[f"night_r17/{cam}"] = lum(R17 / f"{cam}_night.png")
for P in ("night", "golden"):
    stats[f"r18/{P}/ref_aspect/C1"] = lum(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    for cam in CAMS:
        stats[f"r18/{P}/{cam}"] = lum(HERE / f"{cam}_{P}.png")
json.dump(stats, open(OUT / "luminance.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
