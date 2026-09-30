"""r18 niche round sheets: reference 2 | night_r17 (live) | r18 niche for C1 (1448x1086); r17 (live state) | r18 for the
corner close-ups. The live night_r17 set has no golden or CN renders: those baselines are r17/final (the state made live
as night_r17)."""
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np, json
A = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
N = A / "hero/room_preview/r18/niche"
REF = A / "reference/armory3_reference2.png"
R17 = A / "build/renders/night_r17"
R17F = A / "hero/room_preview/r17/final"
def sheet(items, out, h=720):
    ims = []
    for p, t in items:
        im = Image.open(p).convert("RGB"); im = im.resize((round(im.width * h / im.height), h))
        d = ImageDraw.Draw(im); d.rectangle((0, 0, 9 * len(t) + 16, 24), fill=(0, 0, 0)); d.text((8, 6), t, fill=(255, 255, 255))
        ims.append(im)
    W = sum(i.width for i in ims) + 12 * (len(ims) - 1)
    s = Image.new("RGB", (W, h), (40, 40, 40)); x = 0
    for i in ims: s.paste(i, (x, 0)); x += i.width + 12
    s.save(out); print(out)
def lum(p, box=None):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=float) / 255
    if box: a = a[box[1]:box[3], box[0]:box[2]]
    return round(float((0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).mean()), 4)
C = N / "compare"
sheet([(REF, "reference 2"), (R17 / "ref_aspect/C1_EntryReveal_night.png", "night_r17"),
       (N / "final/night/ref_aspect/C1_EntryReveal_night.png", "r18 niche night")], C / "C1_ref_vs_night_r17_vs_r18niche_night.png")
sheet([(REF, "reference 2"), (R17 / "ref_aspect/C1_EntryReveal_night.png", "night_r17"),
       (R17F / "ref_aspect/C1_EntryReveal_golden.png", "r17 golden"),
       (N / "final/golden/ref_aspect/C1_EntryReveal_golden.png", "r18 niche golden")], C / "C1_ref_vs_night_r17_vs_r18niche_golden.png")
for cam in ("CN_WestNiche", "CN_EastNiche"):
    for pre in ("golden", "night"):
        sheet([(R17F / f"closeups/{cam}_{pre}.png", f"r17 (live) {pre}"), (N / f"final/{pre}/{cam}_{pre}.png", f"r18 niche {pre}")],
              C / f"{cam}_r17_vs_r18niche_{pre}.png", h=900)
# corners of C1 at 2x (x 330-500 / 950-1120, y 120-270): r17 night | r18 night | r17 golden | r18 golden
cols = [R17 / "ref_aspect/C1_EntryReveal_night.png", N / "final/night/ref_aspect/C1_EntryReveal_night.png",
        R17F / "ref_aspect/C1_EntryReveal_golden.png", N / "final/golden/ref_aspect/C1_EntryReveal_golden.png"]
S = Image.new("RGB", (4 * 340 + 36, 600), (40, 40, 40))
for i, p in enumerate(cols):
    im = Image.open(p).convert("RGB")
    for j, b in enumerate(((330, 120, 500, 270), (950, 120, 1120, 270))):
        S.paste(im.crop(b).resize((340, 300)), (i * 352, j * 300))
S.save(C / "C1_corners_2x_r17night_r18night_r17golden_r18golden.png")
# numbers: whole frame, and the cabinet front vs the wall pier beside it in the close-ups
stats = {"C1_night": [lum(R17 / "ref_aspect/C1_EntryReveal_night.png"), lum(N / "final/night/ref_aspect/C1_EntryReveal_night.png")],
         "C1_golden": [lum(R17F / "ref_aspect/C1_EntryReveal_golden.png"), lum(N / "final/golden/ref_aspect/C1_EntryReveal_golden.png")]}
R = {"CN_WestNiche": ((700, 560, 870, 780), (570, 560, 650, 780)), "CN_EastNiche": ((740, 560, 905, 760), (950, 560, 1030, 760))}
for cam, (cab, wall) in R.items():
    for pre in ("golden", "night"):
        for tag, p in (("r17", R17F / f"closeups/{cam}_{pre}.png"), ("r18", N / f"final/{pre}/{cam}_{pre}.png")):
            stats[f"{cam}_{pre}_{tag}"] = {"frame": lum(p), "cabinet": lum(p, cab), "wall": lum(p, wall),
                                          "cab_over_wall": round(lum(p, cab) / max(lum(p, wall), 1e-4), 2)}
(C / "luminance.json").write_text(json.dumps(stats, indent=1)); print(json.dumps(stats, indent=1))
