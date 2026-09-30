"""Round 4: sRGB region medians on the NEW round-4 close-ups (the round-3 regions are measured by round3/measure_r3.py).
Boxes (x0, y0, x1, y1) picked on the r4 captures and drawn into <capture_dir>/regions/<cam>.png.
Run: py -3 WorkFiles/dojo/build/unreal/round4/measure_r4_new.py [capture_dir]
Out: <capture_dir>/regions_r4_new.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
CAP = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "r4"
REGIONS = {
    "CU_R4_StorehouseFront": {"plaster_lamp_lit": (1180, 640, 1380, 780), "plaster_left_of_door": (660, 620, 800, 770),
                              "granite_band": (1200, 850, 1480, 1000), "roof_tiles": (1000, 290, 1300, 380),
                              "steel_door": (880, 700, 1060, 900), "wall_plaster_kit1": (40, 740, 300, 850)},
    "CU_R4_ResidenceFront": {"plaster_lamp_lit": (500, 640, 620, 800), "wainscot_boards": (440, 860, 600, 980),
                             "roof_tiles": (600, 290, 900, 380), "lattice_glow": (1030, 640, 1140, 760),
                             "wood_door": (700, 650, 880, 900), "granite_step": (640, 970, 960, 1000)},
    "CU_R4_CorridorOpen": {"rail_lattice": (620, 760, 1200, 900), "roof_tiles": (700, 140, 1250, 200),
                           "inner_plaster": (820, 450, 1250, 620), "storehouse_gable": (60, 200, 420, 700)},
    "CU_R4_ShedVending": {"shed_back_wall": (850, 430, 960, 660), "rack": (890, 540, 980, 660),
                          "floor_earth": (900, 650, 1280, 700), "vending_front": (330, 540, 540, 860)},
    "CU_R4_PavilionTaiko": {"roof_tiles_sunlit": (480, 180, 900, 250), "post_sunlit": (680, 480, 740, 760),
                            "plinth_granite": (700, 880, 1050, 1000), "ceiling": (820, 380, 1250, 470),
                            "drum_lacquer": (880, 520, 1080, 640)},
    "CU_R4_RidgeHall": {"noshi_courses": (1150, 560, 1550, 640), "cap_row": (900, 480, 1450, 560),
                        "onigawara": (600, 470, 770, 700), "tile_field": (1400, 720, 1900, 1000)},
    "CU_R4_RidgeGate": {"noshi_courses": (1100, 630, 1700, 720), "cap_row": (1000, 540, 1700, 620),
                        "onigawara": (840, 490, 970, 700), "tile_field": (1300, 820, 1900, 1000)},
}


def stats(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*[float(c) / 255.0 for c in med])
    return {"box": list(box), "median_srgb": [int(round(c)) for c in med], "hue_deg": round(h * 360, 1),
            "sat": round(s, 3), "r_over_b": round(float(med[0] / max(med[2], 1)), 3),
            "near_black_frac": round(float(np.mean(px.max(axis=1) < 12)), 4),
            "blown_frac": round(float(np.mean(np.all(px >= 250, axis=1))), 4)}


out = {"capture_dir": str(CAP), "cams": {}}
(CAP / "regions").mkdir(exist_ok=True)
for cam, boxes in REGIONS.items():
    p = CAP / f"{cam}.png"
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    out["cams"][cam] = {k: stats(a, b) for k, b in boxes.items()}
    d = ImageDraw.Draw(im)
    for k, b in boxes.items():
        d.rectangle(b, outline=(0, 255, 0), width=3)
        d.text((b[0] + 4, b[1] + 4), k, fill=(0, 255, 0))
    im.save(CAP / "regions" / f"{cam}.png")
(CAP / "regions_r4_new.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for cam, rs in out["cams"].items():
    for k, v in rs.items():
        print(cam, k, v["median_srgb"], "s", v["sat"], "hue", v["hue_deg"], "R/B", v["r_over_b"], "black", v["near_black_frac"])
