"""r21/a: side-by-sides reference 2 | night_r20 (live) | r21/a for C1 (1448 x 1086 and 1600 x 900), CW and CX (night and
golden: the r20 golden baseline is r20/final2), and region stats of the upper windows. Usage: py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
REF = ROOT / "WorkFiles/armory/reference/armory3_reference2.png"
R20 = ROOT / "WorkFiles/armory/build/renders/night_r20"
R20G = ROOT / "WorkFiles/armory/hero/room_preview/r20/final2"
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


def arr(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0


def lum(p):
    return round(float((arr(p) @ np.array([0.2126, 0.7152, 0.0722])).mean()), 3)


def region(p, box):
    a = arr(p)[box[1]:box[3], box[0]:box[2]].reshape(-1, 3)
    return {"p90_srgb": [round(float(v) * 255) for v in np.percentile(a, 90, axis=0)],
            "mean_srgb": [round(float(v) * 255) for v in a.mean(0)]}


side([REF, R20 / "ref_aspect/C1_EntryReveal_night.png", HERE / "ref_aspect/C1_EntryReveal_night.png"],
     ["reference 2", "night_r20 (live)", "r21/a night"], OUT / "C1_ref_vs_night_r20_vs_r21a.png")
side([REF, R20 / "C1_EntryReveal_night.png", HERE / "C1_EntryReveal_night.png"],
     ["reference 2", "night_r20 (live)", "r21/a night"], OUT / "C1_ref_vs_night_r20_vs_r21a_1600x900.png")
side([REF, R20G / "ref_aspect/C1_EntryReveal_golden.png", HERE / "ref_aspect/C1_EntryReveal_golden.png"],
     ["reference 2", "r20 final2 golden", "r21/a golden"], OUT / "C1_ref_vs_r20golden_vs_r21a_golden.png")
for cam in ("CW_WestAisle", "CX_FromPlatform"):
    side([REF, R20 / f"{cam}_night.png", HERE / f"{cam}_night.png"], ["reference 2", "night_r20 (live)", "r21/a night"],
         OUT / f"{cam}_ref_vs_night_r20_vs_r21a.png")
    if (R20G / f"{cam}_golden.png").exists():
        side([REF, R20G / f"{cam}_golden.png", HERE / f"{cam}_golden.png"],
             ["reference 2", "r20 final2 golden", "r21/a golden"], OUT / f"{cam}_ref_vs_r20golden_vs_r21a_golden.png")
side([REF, HERE / "CU_WestWindow_night.png", HERE / "CU_EastWindow_night.png"],
     ["reference 2", "r21/a night west window", "r21/a night east window"], OUT / "CU_windows_night.png")
side([REF, HERE / "CU_WestWindow_golden.png", HERE / "CU_EastWindow_golden.png"],
     ["reference 2", "r21/a golden west window", "r21/a golden east window"], OUT / "CU_windows_golden.png")

stats = {"reference2": lum(REF), "night_r20/ref_aspect/C1": lum(R20 / "ref_aspect/C1_EntryReveal_night.png"),
         "r21a/ref_aspect/C1_night": lum(HERE / "ref_aspect/C1_EntryReveal_night.png"),
         "r21a/ref_aspect/C1_golden": lum(HERE / "ref_aspect/C1_EntryReveal_golden.png")}
for cam in ("C1_EntryReveal", "CW_WestAisle", "CX_FromPlatform"):
    stats[f"night_r20/{cam}"] = lum(R20 / f"{cam}_night.png")
    for pr in ("night", "golden"):
        stats[f"r21a/{cam}_{pr}"] = lum(HERE / f"{cam}_{pr}.png")
# the upper windows' paper between the bars (1600 x 900 frames)
boxes = {"CW_WestAisle": {"west_near": (270, 90, 370, 260), "west_far": (420, 130, 490, 290),
                          "east": (1440, 170, 1550, 290)},
         "CU_WestWindow": {"west_window": (500, 240, 1130, 640)},
         "CU_EastWindow": {"east_window": (480, 240, 1100, 640)}}
for cam, bx in boxes.items():
    for nm, b in bx.items():
        for pr in ("night", "golden"):
            stats[f"window/{cam}/{nm}/{pr}"] = region(HERE / f"{cam}_{pr}.png", b)
        if (R20 / f"{cam}_night.png").exists():
            stats[f"window/{cam}/{nm}/night_r20"] = region(R20 / f"{cam}_night.png", b)
json.dump(stats, open(OUT / "stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
