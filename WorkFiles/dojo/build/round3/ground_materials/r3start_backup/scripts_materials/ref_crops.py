"""Reference crops for the shared dojo material library (measure, don't eyeball).

Every material the library ships is matched against crops of the AI-generated modelling reference sheets
(References/Dojo, see REFERENCE_LOG.md). Pixel boxes are in each sheet's own pixels (x0, y0, x1, y1). 'studio' crops
come from the grey-background model sheets (soft studio light); 'sunset' crops come from dojo1_reference2 (the chosen
time of day). No pixel of any crop goes into a texture: they are only for the swatch sheet and the median numbers.

Run with any Python that has Pillow + numpy (py -3):
  py -3 Scripts/dojo/materials/ref_crops.py
Writes WorkFiles/dojo/build/materials/refcrops/<material>__<n>.png and ref_medians.json.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "References" / "Dojo"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "materials" / "refcrops"

# material -> list of (sheet, box, light, note)
CROPS = {
    "TimberDark": [
        ("dojo_training_props_ref.png", (205, 225, 235, 290), "studio", "makiwara post"),
        ("dojo_training_props_ref.png", (1085, 100, 1125, 250), "studio", "wooden dummy body"),
        ("dojo_courtyard_stone_ref.png", (240, 842, 460, 952), "studio", "cistern boards"),
        ("dojo_drum_pavilion_ref.png", (1135, 770, 1420, 870), "studio", "taiko stand close-up"),
    ],
    "TimberAged": [
        ("dojo_gatehouse_ref.png", (386, 300, 490, 355), "studio", "gate leaf boards"),
        ("dojo_gatehouse_ref.png", (322, 300, 358, 420), "studio", "gate post"),
        ("dojo_drum_pavilion_ref.png", (515, 240, 545, 400), "studio", "pavilion post"),
    ],
    "Granite": [
        ("dojo_courtyard_stone_ref.png", (230, 210, 262, 255), "studio", "tall lantern shaft"),
        ("dojo_courtyard_stone_ref.png", (192, 302, 308, 338), "studio", "tall lantern base"),
        ("dojo_hall_front_ref.png", (752, 918, 875, 1018), "studio", "hall step close-up"),
        ("dojo_drum_pavilion_ref.png", (132, 442, 240, 500), "studio", "pavilion plinth"),
        ("dojo1_reference2.png", (690, 560, 752, 900), "sunset", "centre path slabs"),
    ],
    "GraniteRubble": [
        ("dojo_wall_ref.png", (120, 272, 600, 330), "studio", "wall footing"),
        ("dojo_gatehouse_ref.png", (835, 402, 1030, 500), "studio", "gate wall footing"),
    ],
    "Iron": [
        ("dojo_courtyard_stone_ref.png", (205, 824, 480, 834), "studio", "cistern band"),
        ("dojo_courtyard_stone_ref.png", (205, 960, 480, 970), "studio", "cistern lower band"),
    ],
    "Rope": [
        ("dojo_training_props_ref.png", (202, 100, 238, 195), "studio", "makiwara rope"),
    ],
    "PlasterCream": [
        ("dojo_hall_front_ref.png", (925, 615, 995, 730), "studio", "hall wall-bay plaster"),
        ("dojo1_reference2.png", (190, 268, 262, 300), "sunset", "storehouse wall (sunset)"),
    ],
    "PlasterEarth": [
        ("dojo_wall_ref.png", (140, 180, 580, 250), "studio", "perimeter wall body"),
        ("dojo_gatehouse_ref.png", (835, 290, 1030, 390), "studio", "gate wing wall"),
    ],
    "RoofTile": [
        ("dojo_wall_ref.png", (110, 440, 700, 530), "studio", "wall cap, top view"),
        ("dojo_hall_front_ref.png", (300, 100, 700, 180), "studio", "hall upper roof"),
        ("dojo1_reference2.png", (560, 150, 900, 230), "sunset", "hall roof (sunset)"),
    ],
    "Lacquer": [
        ("dojo_drum_pavilion_ref.png", (880, 585, 1000, 680), "studio", "taiko body"),
    ],
    "GlassAmber": [
        ("dojo_courtyard_stone_ref.png", (229, 120, 262, 150), "studio", "tall lantern window"),
        ("dojo_gatehouse_ref.png", (300, 264, 320, 292), "studio", "gate bracket lamp"),
        ("dojo1_reference2.png", (1392, 640, 1440, 712), "sunset", "gate lamp (sunset)"),
    ],
    "VendingPanel": [
        ("dojo_modern_props_ref.png", (1250, 769, 1273, 786), "studio", "vending display window"),
    ],
}
# the sheets show no clean end-grain face at readable size: end grain is judged against the rule (darker than faces)

GREY_BG = np.array([170.0, 170.0, 170.0])


def measure(sheet, box):
    im = np.asarray(Image.open(REF / sheet).convert("RGB")).astype(float)
    x0, y0, x1, y1 = box
    c = im[y0:y1, x0:x1].reshape(-1, 3)
    # drop pixels that are the neutral grey sheet background (only matters for thin parts)
    sat = c.max(1) - c.min(1)
    keep = ~((sat < 6) & (np.abs(c.mean(1) - 170) < 25))
    c = c[keep] if keep.sum() > 20 else c
    med = np.median(c, axis=0)
    lum = 0.2126 * c[:, 0] + 0.7152 * c[:, 1] + 0.0722 * c[:, 2]
    return {"median_srgb": [int(round(v)) for v in med], "lum_p10": round(float(np.percentile(lum, 10)), 1),
            "lum_p50": round(float(np.percentile(lum, 50)), 1), "lum_p90": round(float(np.percentile(lum, 90)), 1),
            "px": int(len(c))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for mat, crops in CROPS.items():
        res[mat] = []
        for i, (sheet, box, light, note) in enumerate(crops):
            m = measure(sheet, box)
            m.update({"sheet": sheet, "box": list(box), "light": light, "note": note,
                      "file": f"{mat}__{i}.png"})
            Image.open(REF / sheet).convert("RGB").crop(box).save(OUT / m["file"])
            res[mat].append(m)
            print(mat, i, light, note, m["median_srgb"], m["lum_p50"])
    (OUT.parent / "ref_medians.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
