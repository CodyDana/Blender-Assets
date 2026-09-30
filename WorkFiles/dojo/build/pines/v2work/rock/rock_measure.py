"""Rock stage look numbers (study 3.11 methods A/C via Scripts/stone/stone_measure.py): the sheet's D rock faces vs our
final front renders, on boxes over a bare rock face (no roots, no moss) chosen from render_meta.json.

py -3 -B rock_measure.py --renders WorkFiles/dojo/build/pines/renders/v2 --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
import stone_measure as sm  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--renders", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--boxes", default="")
a = ap.parse_args()
rd = Path(a.renders)
meta = json.loads((rd / "render_meta.json").read_text())
REF = ROOT / "References/Dojo/dojo_japanese_pine_ref.png"
ref_boxes = {"P4F_front_face": [940, 655, 1030, 722], "P4Q_front_face": [1290, 640, 1385, 718],
             "P4S_face": [1105, 670, 1200, 725]}
# our boxes in metres (x, z) on the rock's front view, over bare faces (looked at on the renders)
our_boxes = json.loads(a.boxes) if a.boxes else {"PineD1": [0.05, 0.25, 0.55, 0.62], "PineD2": [0.20, 0.25, 0.65, 0.70]}
out = {"reference": {}, "ours": {}}
for k, b in ref_boxes.items():
    out["reference"][k] = sm.measure_image(str(REF), b) if hasattr(sm, "measure_image") else None
for v, (x0, z0, x1, z1) in our_boxes.items():
    m = meta[f"{v}_front"]
    bx, by = m["base_px"]
    pxm = m["px_per_m"]
    box = [bx + x0 * pxm, by - z1 * pxm, bx + x1 * pxm, by - z0 * pxm]
    img = rd / f"{v}_front_final.png"
    # composite on the sheet grey first (the renders are transparent)
    im = Image.open(img).convert("RGBA")
    bg = Image.new("RGBA", im.size, (182, 182, 182, 255))
    bg.alpha_composite(im)
    tmp = rd.parent / f"_tmp_{v}.png"
    bg.convert("RGB").save(tmp)
    out["ours"][v] = {"box_px": [round(c, 1) for c in box], "box_m_xz": [x0, z0, x1, z1],
                      "stats": sm.measure_image(str(tmp), box) if hasattr(sm, "measure_image") else None}
    tmp.unlink()
Path(a.out).write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:3000])
