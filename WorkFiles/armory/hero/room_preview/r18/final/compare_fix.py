"""r18 final fix: side-by-sides reference 2 | r18 combined (prev_r18/) | r18 fix (this folder) for C1 (1448 x 1086 and
1600 x 900), r18 combined | r18 fix for the other views and the niche / mat close-ups (night and golden), plus
whole-frame mean display luminance. Usage: py -3 compare_fix.py"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PREV = HERE / "prev_r18"
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")
OUT = HERE / "compare_fix"
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


def lum(p):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    return round(float((a @ np.array([0.2126, 0.7152, 0.0722])).mean()), 3)


stats = {"reference2": lum(REF)}
for P in ("night", "golden"):
    side([REF, PREV / "ref_aspect" / f"C1_EntryReveal_{P}.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", f"r18 combined ({P})", f"r18 fix ({P})"], OUT / f"C1_ref_vs_r18_vs_fix_{P}.png")
    side([REF, PREV / f"C1_EntryReveal_{P}.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", f"r18 combined ({P})", f"r18 fix ({P})"], OUT / f"C1_ref_vs_r18_vs_fix_{P}_1600x900.png")
    for cam in CAMS[1:]:
        side([PREV / f"{cam}_{P}.png", HERE / f"{cam}_{P}.png"], [f"r18 combined ({P})", f"r18 fix ({P})"],
             OUT / f"{cam}_r18_vs_fix_{P}.png")
    for cam in ("CN_WestNiche", "CN_EastNiche", "CE_MatDown"):
        side([PREV / "closeups" / f"{cam}_{P}.png", HERE / "closeups" / f"{cam}_{P}.png"],
             [f"r18 combined ({P})", f"r18 fix ({P})"], OUT / f"{cam}_r18_vs_fix_{P}.png")
    stats[f"r18/{P}/ref_aspect/C1"] = lum(PREV / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    stats[f"fix/{P}/ref_aspect/C1"] = lum(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    for cam in CAMS:
        stats[f"r18/{P}/{cam}"] = lum(PREV / f"{cam}_{P}.png")
        stats[f"fix/{P}/{cam}"] = lum(HERE / f"{cam}_{P}.png")
# the mat, measured as the r18 judge did: C1 golden ref aspect, a shaded field patch (x 700-900, y 960-1040)
for name, p in (("reference2", REF), ("r18", PREV / "ref_aspect" / "C1_EntryReveal_golden.png"),
                ("fix", HERE / "ref_aspect" / "C1_EntryReveal_golden.png")):
    a = np.asarray(Image.open(p).convert("RGB").crop((700, 960, 900, 1040)), dtype=np.float32).reshape(-1, 3)
    stats[f"mat_shade_rgb/{name}"] = [round(float(v), 1) for v in a.mean(0)]
json.dump(stats, open(OUT / "luminance.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
