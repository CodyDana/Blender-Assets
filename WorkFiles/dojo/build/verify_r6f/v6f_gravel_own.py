"""VERIFY r6f (final verifier): courtyard gravel colour on the f1 stills, MY OWN boxes (open gravel only, picked by eye on
the f1 stills; drawn on crops/gravel_boxes_<cam>.png to check). Median sRGB, HSV hue (deg), HSV sat, R/B; and the
per-pixel hue median. Gate as given to this verifier: hue 25-40 deg and not grey-white (HSV sat >= 0.15). The builder's
proposed band (13-30 deg, R/B >= 1.2, sat >= 0.15) is reported alongside, not used for the verdict.
Out: verify_r6f/gravel_own.json"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/f1"
VD = B / "WorkFiles/dojo/build/verify_r6f"
BOX = {
    "CAM_Overview": {"hallfront_W_shade": (480, 415, 660, 455), "hallfront_E_shade": (1300, 410, 1470, 455),
                     "yard_W_sunlit": (300, 580, 420, 640), "yard_E_mixed": (1410, 590, 1480, 660),
                     "side_strip_E_by_hall": (1320, 330, 1440, 390), "side_strip_W_by_hall": (470, 330, 600, 390)},
    "CU_Training": {"fore_sunlit": (300, 950, 1600, 1070), "mid_sunlit": (1150, 700, 1600, 780),
                    "shadow_band": (700, 845, 1400, 880)},
    "CAM_Ref2Match": {"hallfront_W": (180, 545, 320, 600), "hallfront_E": (1130, 545, 1270, 590),
                      "yard_W_sunlit_edge": (0, 640, 50, 690)},
    "CAM_EstablishingRef2": {"hallfront_W": (60, 540, 260, 600), "hallfront_E": (1190, 540, 1400, 585)},
    "CAM_PlayerEyeSand": {}, "CAM_EastYard": {},
}


def stats(px):
    m = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255))
    p = px / 255
    mx, mn = p.max(1), p.min(1)
    ok = (p[:, 0] == mx) & (mx > mn)
    hue = (60 * (p[:, 1] - p[:, 2]) / np.maximum(mx - mn, 1e-6)) % 360
    return {"rgb": [int(c) for c in m], "hue_deg": round(h * 360, 1), "sat": round(s, 3), "val": round(v, 3),
            "R/B": round(float(m[0] / max(m[2], 1)), 3),
            "px_hue_median": round(float(np.median(hue[ok])), 1) if ok.any() else None}


res = {}
for cam, boxes in BOX.items():
    if not boxes:
        continue
    im = Image.open(CAP / f"{cam}.png").convert("RGB")
    a = np.asarray(im).astype(float)
    dr = ImageDraw.Draw(im)
    for k, (x0, y0, x1, y1) in boxes.items():
        r = stats(a[y0:y1, x0:x1].reshape(-1, 3))
        r.update({"cam": cam, "box": [x0, y0, x1, y1]})
        r["pass_25_40"] = bool(25 <= r["hue_deg"] <= 40 and r["sat"] >= 0.15)
        r["pass_builder_13_30"] = bool(13 <= r["hue_deg"] <= 30 and r["R/B"] >= 1.2 and r["sat"] >= 0.15)
        res[f"{cam}:{k}"] = r
        dr.rectangle((x0, y0, x1, y1), outline=(0, 255, 255), width=3)
        dr.text((x0 + 3, y0 + 3), k, fill=(0, 255, 255))
        print(f"{cam}:{k:24s} {r['rgb']} hue {r['hue_deg']:5.1f} px {r['px_hue_median']} s {r['sat']:.3f} R/B {r['R/B']:.2f} "
              f"25-40 {r['pass_25_40']} 13-30 {r['pass_builder_13_30']}")
    im.save(VD / "crops" / f"gravel_boxes_{cam}.png")
res["passed_25_40"] = all(v["pass_25_40"] for v in res.values() if isinstance(v, dict))
res["n_pass_25_40"] = sum(1 for v in res.values() if isinstance(v, dict) and v["pass_25_40"])
res["n_boxes"] = sum(1 for v in res.values() if isinstance(v, dict))
res["passed_builder_band"] = all(v["pass_builder_13_30"] for k, v in res.items() if isinstance(v, dict))
(VD / "gravel_own.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("25-40:", res["n_pass_25_40"], "/", res["n_boxes"], "builder band all:", res["passed_builder_band"])
