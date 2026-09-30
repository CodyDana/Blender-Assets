"""ROUND 5 OUTSIDE: the review sheet: the references beside the matching renders, then the close-ups.
Run: py -3 Scripts/dojo/outside/make_sheet.py [tag]   Out: WorkFiles/dojo/build/outside/renders/<tag>/SHEET_OUTSIDE_<tag>.png"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "r5"
R = ROOT / "WorkFiles" / "dojo" / "build" / "outside" / "renders" / TAG
REF = ROOT / "References" / "Dojo"
W = 1000


def tile(path, label):
    im = Image.open(path).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 26), fill=(0, 0, 0))
    d.text((8, 6), label, fill=(255, 255, 255))
    return im


rows = [[tile(REF / "dojo1_reference1.png", "REFERENCE dojo1_reference1 (AI modelling reference)"),
         tile(R / "ref1_overview.png", "render: ref1_overview (Cycles, denoised; trees = grey-box, vegetation later)")],
        [tile(REF / "dojo1_reference2.png", "REFERENCE dojo1_reference2"),
         tile(R / "ref2_establishing.png", "render: ref2_establishing (roofs + ridges beyond the walls)")],
        [tile(R / "road_gate.png", "road_gate: cobble road, kerb, gutter, verge, kit-1 apron"),
         tile(R / "road_east.png", "road_east: poles + wires, lamp A, landing, rail fence, houses")],
        [tile(R / "terrace.png", "terrace: rubble retaining wall + coping from the lower lane"),
         tile(R / "walltop_W.png", "walltop_W: from the west wall top (lane, houses, ridges)")],
        [tile(R / "alley_W.png", "alley_W: rear-alley fence W (wicket gate at veranda level)"),
         tile(R / "alley_E.png", "alley_E: rear-alley fence E")],
        [tile(R / "skyline_NW.png", "skyline_NW: from the courtyard"),
         tile(R / "junction_W.png", "junction_W: road + gutter + kerb at the apron's front step")]]
H = sum(max(t.height for t in r) for r in rows)
sheet = Image.new("RGB", (2 * W + 10, H + 10 * len(rows)), (30, 30, 30))
y = 0
for r in rows:
    x = 0
    for t in r:
        sheet.paste(t, (x, y))
        x += W + 10
    y += max(t.height for t in r) + 10
out = R / f"SHEET_OUTSIDE_{TAG}.png"
sheet.save(out)
print(out, sheet.size)
