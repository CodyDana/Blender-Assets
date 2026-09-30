"""VERIFY r6: tight tile-only boxes (checked by eye on crops/pav_boxes.png: no timber, plaster or sky inside) for the
sunlit pavilion E roof face and the sunlit east wall cap; same statistic as v6_look_measure (brightest 30 % by
luminance, median colour). Out: verify_r6/look_measure_tight.json"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/r6"
VD = B / "WorkFiles/dojo/build/verify_r6"
BOX = {"tile_pav_E_tight": ("CU_R4_PavilionTaiko", (1080, 185, 1420, 232)),
       "tile_pav_E_tight2": ("CU_R4_PavilionTaiko", (1000, 150, 1420, 200)),
       "tile_wallcapE_tight": ("CU_R4_PavilionTaiko", (1560, 612, 1860, 660)),
       "tile_wallcapE_rolls_low_INCL_BEAM": ("CU_R4_PavilionTaiko", (1460, 640, 1890, 710)),
       "tile_wallcapE_far_right": ("CU_R4_PavilionTaiko", (1700, 600, 1900, 700)),
       "tile_wallcapE_sunlit_rolls_only": ("CU_R4_PavilionTaiko", (1673, 630, 1905, 672)),
       "tile_wallcapE_ridge_sunlit": ("CU_R4_PavilionTaiko", (1640, 590, 1905, 612))}
res = {}
for k, (cam, b) in BOX.items():
    a = np.asarray(Image.open(CAP / f"{cam}.png").convert("RGB"))
    x0, y0, x1, y1 = b
    r = a[y0:y1, x0:x1].reshape(-1, 3).astype(float)
    lum = r @ np.array([0.2126, 0.7152, 0.0722])
    def st(c):
        m = np.median(c, axis=0)
        return {"rgb": [int(v) for v in m], "R/B": round(float(m[0] / max(m[2], 1)), 3), "sat": round(float((m.max() - m.min()) / max(m.max(), 1)), 3)}
    res[k] = {"cam": cam, "box": b, "all": st(r), "lit": st(r[lum >= np.percentile(lum, 70)])}
    print(k, res[k]["all"], res[k]["lit"])
(VD / "look_measure_tight.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
