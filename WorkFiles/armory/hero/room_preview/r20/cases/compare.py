"""r20 cases: side-by-sides reference 2 | night_r19 (live) | r20 cases for C1 (1448 x 1086 and 1600 x 900; night and
golden), night_r19 | r20 cases for CX / CW / C4 / C5, and whole-frame mean display luminance. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = ROOT / "reference" / "armory3_reference2.png"
R19 = ROOT / "build" / "renders" / "night_r19"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)
CAMS = ("C1_EntryReveal", "CX_FromPlatform", "CW_WestAisle", "C4_ShurikenTray", "C5_CloakCase")


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
    side([REF, R19 / "ref_aspect" / "C1_EntryReveal_night.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r19 (live, night)", f"r20 cases ({P})"], OUT / f"C1_ref_vs_night_r19_vs_r20cases_{P}.png")
    side([REF, R19 / "C1_EntryReveal_night.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r19 (live, night)", f"r20 cases ({P})"],
         OUT / f"C1_ref_vs_night_r19_vs_r20cases_{P}_1600x900.png")
    for cam in CAMS[1:]:
        side([REF, R19 / f"{cam}_night.png", HERE / f"{cam}_{P}.png"],
             ["reference 2", "night_r19 (live, night)", f"r20 cases ({P})"],
             OUT / f"{cam}_ref_vs_night_r19_vs_r20cases_{P}.png")
stats = {"reference2": lum(REF), "night_r19/ref_aspect/C1": lum(R19 / "ref_aspect" / "C1_EntryReveal_night.png")}
for cam in CAMS:
    stats[f"night_r19/{cam}"] = lum(R19 / f"{cam}_night.png")
for P in ("night", "golden"):
    stats[f"r20cases/ref_aspect/C1_{P}"] = lum(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    for cam in CAMS:
        stats[f"r20cases/{cam}_{P}"] = lum(HERE / f"{cam}_{P}.png")
(OUT / "luminance.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(stats, indent=1))
