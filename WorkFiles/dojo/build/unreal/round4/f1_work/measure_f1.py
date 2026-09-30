"""Round 4 fix f1: sRGB medians on the new-building close-ups (boxes x0, y0, x1, y1 on the 1920 x 1080 stills) and the
near-black fraction (max channel < 12) per image. Out: <capture_dir>/regions_f1_new.json"""
import colorsys, json, sys
from pathlib import Path
from PIL import Image
import numpy as np
CAP = Path(sys.argv[1])
BOX = {
 "CU_R4_StorehouseFront": {"door_leaves": (880, 640, 1050, 900), "plaster_lamp_lit": (1150, 600, 1350, 780),
                           "granite_band": (1150, 850, 1500, 980), "gable_plaster": (620, 320, 860, 460)},
 "CU_R4_ResidenceFront": {"wood_door": (720, 640, 920, 900), "wainscot": (430, 850, 650, 980),
                          "lattice_glow": (1040, 630, 1180, 770), "plaster": (450, 440, 650, 650),
                          "tie_beam": (450, 385, 1250, 402)},
 "CU_R4_CorridorOpen": {"lattice_rail": (560, 760, 1270, 900), "post": (1285, 300, 1330, 1000),
                        "inner_wall": (800, 430, 1250, 630)},
 "CU_R4_PavilionTaiko": {"tiles_sunlit": (600, 200, 900, 270), "drum_body": (880, 540, 1080, 640),
                         "plinth_granite": (600, 900, 1050, 1050), "post_sunlit": (680, 480, 740, 760)},
 "CU_R4_ShedVending": {"board_wall": (940, 400, 1240, 650), "roof_edge": (900, 352, 1750, 400),
                       "earth_floor": (1000, 680, 1250, 740)},
 "CU_R4_RidgeGate": {"noshi": (1000, 640, 1900, 720), "onigawara": (840, 480, 960, 690),
                     "tiles": (1000, 850, 1500, 1000)},
}
out = {}
for cam, boxes in BOX.items():
    a = np.asarray(Image.open(CAP / f"{cam}.png").convert("RGB"))
    r = {"near_black_frac": round(float((a.max(axis=2) < 12).mean()), 4)}
    for k, (x0, y0, x1, y1) in boxes.items():
        m = np.median(a[y0:y1, x0:x1].reshape(-1, 3), axis=0)
        h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
        r[k] = {"srgb": [int(x) for x in m], "sat": round(s, 2), "hue_deg": round(h * 360), "R_over_B": round(m[0] / max(m[2], 1), 2)}
    out[cam] = r
    print(cam, json.dumps(r))
(CAP / "regions_f1_new.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
