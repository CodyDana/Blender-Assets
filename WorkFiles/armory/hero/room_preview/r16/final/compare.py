"""r16 combined test copy: side-by-sides reference 2 | live night_20m | this copy (C1 at 1448 x 1086), plus whole-frame
mean display luminance for every rendered view against night_20m. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")
LIVE = HERE.parents[3] / "build" / "renders" / "night_20m"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)


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


live_c1 = LIVE / "ref_aspect" / "C1_EntryReveal_night.png"
for P in ("golden", "night"):
    ours = HERE / P / "ref_aspect" / f"C1_EntryReveal_{P}.png"
    side([REF, live_c1, ours], ["reference 2", "live night_20m (night)", f"r16 final ({P})"],
         OUT / f"C1_ref_vs_night_20m_vs_r16final_{P}.png")
    ours16 = HERE / P / f"C1_EntryReveal_{P}.png"
    side([live_c1.parent.parent / "C1_EntryReveal_night.png", ours16], ["live night_20m (night)", f"r16 final ({P})"],
         OUT / f"C1_1600x900_night_20m_vs_r16final_{P}.png")
for cam in ("CX_FromPlatform", "C10_Hero", "C3_Case3", "C5_CloakCase", "CW_WestAisle"):
    side([LIVE / f"{cam}_night.png", HERE / "night" / f"{cam}_night.png"], ["live night_20m", "r16 final (night)"],
         OUT / f"{cam}_night_20m_vs_r16final_night.png")

stats = {"reference2": lum(REF)}
for P in ("golden", "night"):
    for p in sorted((HERE / P).rglob("*.png")):
        stats[f"{P}/{p.relative_to(HERE / P).as_posix()}"] = lum(p)
for p in sorted(LIVE.rglob("*_night.png")):
    if "compare" not in p.parts:
        stats[f"night_20m/{p.relative_to(LIVE).as_posix()}"] = lum(p)
json.dump(stats, open(OUT / "luminance.json", "w"), indent=1)
print(json.dumps(stats, indent=1))

# r16 fix round (2026-09-29): the judged set (prev_7of10, 7/10) against this round, and reference 2 | judged | now
PREV = HERE / "prev_7of10"
for P in ("golden", "night"):
    side([REF, PREV / P / "ref_aspect" / f"C1_EntryReveal_{P}.png", HERE / P / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", f"judged 7/10 ({P})", f"fix round ({P})"], OUT / f"C1_ref_vs_judged_vs_fix_{P}.png")
    for cam in ("CX_FromPlatform", "C10_Hero", "C3_Case3", "C5_CloakCase", "CW_WestAisle", "CE_EntryDown"):
        side([PREV / P / f"{cam}_{P}.png", HERE / P / f"{cam}_{P}.png"], [f"judged 7/10 ({P})", f"fix round ({P})"],
             OUT / f"{cam}_judged_vs_fix_{P}.png")
# the entry crop (reference 2's foreground) and the painting's top band, zoomed
ENTRY = (200, 760, 1300, 1086)
for P in ("golden", "night"):
    ims = [Image.open(p).convert("RGB").resize((1448, 1086)).crop(ENTRY) for p in
           (REF, PREV / P / "ref_aspect" / f"C1_EntryReveal_{P}.png", HERE / P / "ref_aspect" / f"C1_EntryReveal_{P}.png")]
    im = Image.new("RGB", (ims[0].width, 3 * ims[0].height + 52), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for k, (i, lab) in enumerate(zip(ims, ["reference 2", "judged 7/10", "fix round"])):
        im.paste(i, (0, k * (i.height + 26)))
        d.text((6, k * (i.height + 26) + 4), lab, fill=(255, 255, 255))
    im.save(OUT / f"C1_entry_crop_ref_judged_fix_{P}.png")
    print("wrote", OUT / f"C1_entry_crop_ref_judged_fix_{P}.png")
