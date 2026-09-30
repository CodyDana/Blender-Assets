"""r19 b (reference order: rear tall pairs, compact case 8): side-by-sides reference 2 | night_r18 (live) | r19 b for C1 (1448 x 1086 and 1600 x 900;
night and golden), night_r18 | r19 b for CX / CW / C4 / C5, a box overlay (reference boxes red, ours from c1_boxes.json
green) on reference 2 and on our C1, and whole-frame mean display luminance. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = ROOT / "reference" / "armory3_reference2.png"
R18 = ROOT / "build" / "renders" / "night_r18"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)
CAMS = ("C1_EntryReveal", "CX_FromPlatform", "CW_WestAisle", "C4_ShurikenTray", "C5_CloakCase")
# r19 b: reference 2's rear slot is a staggered pair per side: the near tall (G4 / G5) behind the scroll / hat case, its
# foot hidden by it (box bottom drawn at the front case's foot), and the far tall by the stairs (G3 / G2)
REFBOX = {"5": (28, 195, 545, 855), "4": (130, 312, 307, 700), "G1": (255, 407, 400, 590), "G4": (287, 400, 272, 590),
          "G3": (357, 450, 257, 470), "8": (1260, 1407, 627, 855), "7": (1180, 1410, 472, 715), "6": (1078, 1210, 344, 575),
          "G5": (1048, 1130, 272, 575), "G2": (1000, 1087, 257, 472)}
NAMES = {"5": "kunai", "4": "cloak", "G1": "scrolls", "G4": "W near tall", "G3": "W far tall", "8": "shuriken",
         "7": "boots", "6": "hat", "G5": "E near tall", "G2": "E far tall"}


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


def overlay(src, out, ours):
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    for k, b in REFBOX.items():
        d.rectangle([b[0], b[2], b[1], b[3]], outline=(255, 60, 60), width=2)
        d.text((b[0] + 4, b[2] + 4), f"ref {NAMES[k]}", fill=(255, 90, 90))
    for k, b in ours.items():
        if k in REFBOX:
            d.rectangle([b[0], b[2], b[1], b[3]], outline=(60, 255, 90), width=2)
            d.text((b[0] + 4, b[3] - 14), f"ours {k}", fill=(90, 255, 120))
    im.save(out)
    print("wrote", out)


boxes = {k: v["box"] for k, v in json.loads((HERE / "c1_boxes.json").read_text())["cases"].items()}
for P in ("night", "golden"):
    side([REF, R18 / "ref_aspect" / "C1_EntryReveal_night.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r18 (live, night)", f"r19 b reference order ({P})"], OUT / f"C1_ref_vs_night_r18_vs_r19b_{P}.png")
    side([REF, R18 / "C1_EntryReveal_night.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r18 (live, night)", f"r19 b reference order ({P})"],
         OUT / f"C1_ref_vs_night_r18_vs_r19b_{P}_1600x900.png")
    for cam in CAMS[1:]:
        side([R18 / f"{cam}_night.png", HERE / f"{cam}_{P}.png"], ["night_r18 (live, night)", f"r19 b ({P})"],
             OUT / f"{cam}_night_r18_vs_r19b_{P}.png")
overlay(REF, OUT / "C1_boxes_on_reference.png", boxes)
overlay(HERE / "ref_aspect" / "C1_EntryReveal_golden.png", OUT / "C1_boxes_on_r19b_golden.png", boxes)
side([OUT / "C1_boxes_on_reference.png", OUT / "C1_boxes_on_r19b_golden.png"],
     ["reference 2: red = measured reference boxes, green = ours", "r19 b golden: the same boxes"], OUT / "C1_boxes_ref_vs_r19b.png")
stats = {"reference2": lum(REF), "night_r18/ref_aspect/C1": lum(R18 / "ref_aspect" / "C1_EntryReveal_night.png")}
for cam in CAMS:
    stats[f"night_r18/{cam}"] = lum(R18 / f"{cam}_night.png")
for P in ("night", "golden"):
    stats[f"r19b/ref_aspect/C1_{P}"] = lum(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    for cam in CAMS:
        stats[f"r19b/{cam}_{P}"] = lum(HERE / f"{cam}_{P}.png")
(OUT / "luminance.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(stats, indent=1))
