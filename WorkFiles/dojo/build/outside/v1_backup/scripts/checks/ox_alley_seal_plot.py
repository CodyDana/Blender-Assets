"""ROUND 6 OUTSIDE track: plan picture of ox_alley_seal.py's flood (X 4..40, Y 26..37, 0.1 m cells), one panel per
mode (r5 = before this round, 1v1 = now, br = the battle royale), north up.
  orange  reached by the flying capsule standing at ground / deck level (bottom <= +0.6)
  yellow  reached only higher up (roofs, jumps)
  grey    free space the courtyard never reaches (sealed or closed interiors)
  black   solid everywhere (walls, buildings, blockers)
  cyan    this round's 1v1 blocker boxes (outline) and the pocket fences (filled)
Run: py -3 Scripts/dojo/outside/checks/ox_alley_seal_plot.py
Out: WorkFiles/dojo/build/round6/build/checks/alley_seal_plan.png"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
C = ROOT / "WorkFiles" / "dojo" / "build" / "round6" / "build" / "checks"
LX = json.loads((ROOT / "WorkFiles" / "dojo" / "build" / "outside" / "layout_outside.json").read_text(encoding="utf-8"))
plans = json.loads((C / "alley_seal_plan.json").read_text(encoding="utf-8"))
S = 4                                   # px per 0.1 m cell
COL = {"2": (235, 120, 40), "1": (240, 210, 80), "0": (120, 120, 120), "9": (15, 15, 15)}
panels = []
for mode in ("r5", "1v1", "br"):
    if mode not in plans:
        continue
    P = plans[mode]
    rows = P["rows_y_up"]
    h, w = len(rows), len(rows[0])
    im = Image.new("RGB", (w * S, h * S + 40), (255, 255, 255))
    px = im.load()
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            col = COL[c]
            for a in range(S):
                for b in range(S):
                    px[i * S + a, (h - 1 - j) * S + b + 40] = col
    d = ImageDraw.Draw(im)

    def to_px(x, y):
        return ((x - P["x0"]) / P["dx"] * S, (h - (y - P["y0"]) / P["dx"]) * S + 40)
    if mode == "1v1":
        for e in LX["onev1_only"]["invisible"]:
            for b in e["boxes_world"]:
                x0, x1, y0, y1 = b[:4]
                a, bb = to_px(x0, y1), to_px(x1, y0)
                d.rectangle([a[0], a[1], bb[0], bb[1]], outline=(0, 220, 255), width=2)
        for n in ("SM_DKX_PocketFence_W", "SM_DKX_PocketFence_E"):
            for hb in LX["pieces"][n]["extra"]["hull_world_min_max"]:
                a, bb = to_px(hb[0], hb[4]), to_px(hb[3], hb[1])
                d.rectangle([a[0], a[1], bb[0], bb[1]], fill=(0, 220, 255))
    label = {"r5": "ROUND 5 (verify_r5): the rear area is reached", "1v1": "ROUND 6, 1v1: sealed",
             "br": "ROUND 6, battle royale (1v1 set removed): open"}[mode]
    d.text((10, 12), label, fill=(0, 0, 0))
    panels.append(im)
W = max(p.width for p in panels)
out = Image.new("RGB", (W, sum(p.height for p in panels) + 10 * len(panels)), (255, 255, 255))
y = 0
for p in panels:
    out.paste(p, (0, y))
    y += p.height + 10
out.save(C / "alley_seal_plan.png")
print("PLOT", C / "alley_seal_plan.png", out.size)
