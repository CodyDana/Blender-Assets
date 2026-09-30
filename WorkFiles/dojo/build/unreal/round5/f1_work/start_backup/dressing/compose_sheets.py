"""ROUND 5 dressing review sheets (system Python + PIL): reference side-by-sides and decal before / after pairs.
Run: py -3 Scripts/dojo/dressing/compose_sheets.py [tag]   Out: WorkFiles/dojo/build/dressing/renders/<tag>/SHEET_*.png"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r3"
R = ROOT / "WorkFiles" / "dojo" / "build" / "dressing" / "renders" / TAG
REF = ROOT / "References" / "Dojo"


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def row(paths, labels, h, out):
    ims = [fit(Image.open(p).convert("RGB"), h) for p in paths]
    W = sum(i.width for i in ims) + 10 * (len(ims) + 1)
    canvas = Image.new("RGB", (W, h + 44), (24, 24, 24))
    x = 10
    d = ImageDraw.Draw(canvas)
    for im, lb in zip(ims, labels):
        canvas.paste(im, (x, 34))
        d.text((x + 4, 10), lb, fill=(230, 230, 230))
        x += im.width + 10
    canvas.save(out)
    print("SHEET", out)


row([REF / "dojo1_reference2.png", R / "EstablishingRef2.png", R / "EstablishingRef2_nodecals.png"],
    ["reference 2 (AI modelling reference)", "round 5 dressing (Blender preview)", "same view, decals off"], 760,
    R / "SHEET_ref2.png")
row([REF / "dojo1_reference1.png", R / "Overview.png"], ["reference 1", "round 5 dressing: overview"], 760,
    R / "SHEET_ref1.png")
for v in ("CU_WallFooting", "CU_StreetWall", "CU_PathStepBand", "CU_Storehouse", "CU_RoofLichen", "CU_Downpipe"):
    row([R / f"{v}_nodecals.png", R / f"{v}.png"], [f"{v}: decals off", f"{v}: decals on"], 620,
        R / f"SHEET_AB_{v}.png")
row([R / "GateFromStreet.png", R / "CU_GatePlaque.png"], ["gate from the street", "gate plaque close"], 620,
    R / "SHEET_emblem_gate.png")
row([R / "CU_HallGableW.png", R / "CU_HallGablePlaque.png", R / "EastYard.png"],
    ["west hall gable from the yard", "hall plaque close", "east yard (east gable)"], 560, R / "SHEET_emblem_hall.png")
