"""VERIFY r6f: courtyard gravel colour (the final judge's r5 'cold grey-white / snow' gap). Boxes of open gravel only
(picked on crops/overview_gravel_boxes.png and the eye-level stills): median sRGB, HSV hue (deg), saturation, R/B.
Pass: hue 25-40 deg, sat >= 0.15 (not grey-white). The raked sand is reported for reference. Out: verify_r6f/gravel.json"""
import colorsys, json
from pathlib import Path
import numpy as np
from PIL import Image
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/f1"
VD = B / "WorkFiles/dojo/build/verify_r6f"
S = 1.5
def d(b):
    return tuple(int(round(v * S)) for v in b)
BOX = {
    "CAM_Overview": {"gravel_hallfront_W": (560, 400, 680, 450), "gravel_hallfront_E": (1300, 390, 1440, 450),
                     "gravel_yard_E": d((965, 400, 1020, 500)), "gravel_yard_W": d((225, 390, 290, 440)),
                     "sand_ref": (700, 600, 900, 800)},
    "CAM_PlayerEyeSand": {"gravel_eye_hallfront_W": (0, 700, 130, 750), "gravel_eye_hallfront_W2": (140, 735, 280, 752)},
    "CAM_Ref2Match": {"gravel_eye_hallfront_W": (55, 405, 230, 428)},
    "CAM_EastYard": {"gravel_eye_eastyard_front": (250, 800, 700, 900), "gravel_eye_eastyard_mid": (700, 690, 1150, 760)},
}
res = {}
for cam, boxes in BOX.items():
    a = np.asarray(Image.open(CAP / f"{cam}.png").convert("RGB")).astype(float)
    for k, (x0, y0, x1, y1) in boxes.items():
        m = np.median(a[y0:y1, x0:x1].reshape(-1, 3), axis=0)
        h, s, v = colorsys.rgb_to_hsv(*(m / 255))
        r = {"cam": cam, "box": [x0, y0, x1, y1], "rgb": [int(c) for c in m], "hue_deg": round(h * 360, 1),
             "sat": round(s, 3), "R/B": round(m[0] / max(m[2], 1), 3)}
        if k.startswith("gravel"):
            r["pass"] = bool(25 <= r["hue_deg"] <= 40 and r["sat"] >= 0.15)
        px = a[y0:y1, x0:x1].reshape(-1, 3) / 255
        mx, mn = px.max(1), px.min(1)
        hue = np.where(mx == mn, 0, np.where(px[:, 0] == mx, (60 * (px[:, 1] - px[:, 2]) / np.maximum(mx - mn, 1e-6)) % 360, 0))
        r["median_px_hue_deg_red_max_px"] = round(float(np.median(hue[(px[:, 0] == mx) & (mx > mn)])), 1)
        res[f"{cam}:{k}"] = r
        print(k, r)
res["passed"] = all(v["pass"] for v in res.values() if isinstance(v, dict) and "pass" in v)
(VD / "gravel.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("passed", res["passed"])
