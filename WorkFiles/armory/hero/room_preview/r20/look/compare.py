"""r20 look: side-by-side sheets (reference 2 | night_r19 | r20 look) and whole-frame mean display luminance."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
H = Path(__file__).resolve().parent
A = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = A / "reference" / "armory3_reference2.png"
N19 = A / "build" / "renders" / "night_r19"
G19 = A / "hero" / "room_preview" / "r19" / "b"
NEW = H / "renders"
OUT = H / "compare"


def lum(p, box=None):
    a = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255
    if box:
        a = a[box[1]:box[3], box[0]:box[2]]
    return round(float((a @ np.array([0.2126, 0.7152, 0.0722])).mean()), 3)


def sheet(items, name, h=540):
    ims = []
    for lab, p in items:
        im = Image.open(p).convert("RGB")
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        ims.append((f"{lab}  (mean L {lum(p)})", im))
    W = sum(i.width for _, i in ims) + 10 * (len(ims) + 1)
    out = Image.new("RGB", (W, h + 40), (18, 18, 18))
    d = ImageDraw.Draw(out)
    x = 10
    for lab, im in ims:
        out.paste(im, (x, 30)); d.text((x, 8), lab, fill=(235, 235, 235)); x += im.width + 10
    out.save(OUT / name)


rep = {}
sheet([("reference 2", REF), ("night_r19", N19 / "ref_aspect" / "C1_EntryReveal_night.png"),
       ("r20 look night", NEW / "ref_aspect" / "C1_EntryReveal_night.png")], "C1_ref_vs_night_r19_vs_r20look.png")
sheet([("reference 2", REF), ("r19 b golden", G19 / "ref_aspect" / "C1_EntryReveal_golden.png"),
       ("r20 look golden", NEW / "ref_aspect" / "C1_EntryReveal_golden.png")], "C1_ref_vs_golden_r19_vs_r20look.png")
for cam in ("CW_WestAisle", "CX_FromPlatform", "CG_Garden"):
    sheet([("night_r19", N19 / f"{cam}_night.png"), ("r20 look night", NEW / f"{cam}_night.png")], f"{cam}_night_r19_vs_r20look.png")
    g = G19 / f"{cam}_golden.png"
    if g.exists():
        sheet([("r19 b golden", g), ("r20 look golden", NEW / f"{cam}_golden.png")], f"{cam}_golden_r19_vs_r20look.png")
for lab, p in [("ref", REF), ("C1 night_r19", N19 / "ref_aspect" / "C1_EntryReveal_night.png"),
               ("C1 r20", NEW / "ref_aspect" / "C1_EntryReveal_night.png"),
               ("C1 golden r19b", G19 / "ref_aspect" / "C1_EntryReveal_golden.png"),
               ("C1 golden r20", NEW / "ref_aspect" / "C1_EntryReveal_golden.png")] + \
        [(f"{c} {t}", d / f"{c}_night.png") for c in ("CW_WestAisle", "CX_FromPlatform", "CG_Garden")
         for t, d in (("night_r19", N19), ("r20", NEW))]:
    rep[lab] = lum(p)
# exterior seen through the entrance in CX (the door opening) and the C1 upper west windows
rep["CX door opening r19 / r20"] = [lum(N19 / "CX_FromPlatform_night.png", (700, 290, 900, 460)),
                                    lum(NEW / "CX_FromPlatform_night.png", (700, 290, 900, 460))]
(OUT / "luminance.json").write_text(json.dumps(rep, indent=1))
print(json.dumps(rep, indent=1))
