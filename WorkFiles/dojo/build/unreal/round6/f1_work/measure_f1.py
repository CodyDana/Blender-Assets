"""ROUND 6 FIX f1 capture measures (plain Python, read-only): py -3 measure_f1.py <capture dir> [out.json]
Runs the round-6 measure (measure_r6.py: near-black cells, blown px, sunlit tile R/B boxes, timber, downpipes) and adds
the round-6 judge / verifier regions: median sRGB, HSV hue, HLS lightness and saturation (the judge's numbers), R/B.
  tiles_look   the hall roof (CAM_Overview, CU_HallUpperRoof) vs ref 1 (57, 56, 68) h 245 s 0.09 L 0.24
  town         the town lots / streets in CAM_Overview vs ref 1 street (77, 75, 87)
  gravel       the verify_r6 v6_gravel.py boxes (CAM_Ref2Match's box re-picked for the new framing) + CU_Training,
               the alley (CU_R6_AlleyAbove / PocketAboveW); targets ref 2 (150, 119, 107) s 0.17, refs hue 13-18
  sand         CAM_Overview (ref 1) and CAM_Ref2Match (ref 2 s 0.32 L 0.61)"""
import colorsys, json, runpy, sys
from pathlib import Path
import numpy as np
from PIL import Image
CAP = Path(sys.argv[1]); OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else CAP / "measure_f1.json"
sys.argv = [sys.argv[0], str(CAP), str(CAP / "measure_r6_boxes.json")]
runpy.run_path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round6\r6_work\measure_r6.py")
S = 1.5
def d(b):
    return tuple(int(round(v * S)) for v in b)
R2 = json.loads(Path(__file__).with_name("ref2match_boxes.json").read_text()) if Path(__file__).with_name("ref2match_boxes.json").exists() else {}
BOX = {
    "tiles_look": {"CAM_Overview": {"hall_upper_front": (760, 140, 1140, 200), "hall_lower_front": (640, 305, 1270, 330)},
                   "CU_HallUpperRoof": {"upper_roof_mid": (300, 500, 1100, 800)},
                   "CAM_Ref2Match": R2.get("tiles", {})},
    "town": {"CAM_Overview": {"lot_W": (40, 120, 160, 200), "lot_NE": (1300, 120, 1400, 200), "street_NW": (330, 100, 420, 160)}},
    "gravel": {"CAM_Overview": {"hallfront_W": (560, 400, 680, 450), "hallfront_E": (1300, 390, 1440, 450),
                                "yard_E": d((965, 400, 1020, 500)), "yard_W": d((225, 390, 290, 440))},
               "CAM_PlayerEyeSand": {"eye_hallfront_W": (0, 700, 130, 750), "eye_hallfront_W2": (140, 735, 280, 752)},
               "CAM_EastYard": {"eastyard_front": (250, 800, 700, 900), "eastyard_mid": (700, 690, 1150, 760)},
               "CU_Training": {"yard_front": (300, 900, 1300, 1060)},
               "CU_R6_AlleyAbove": {"alley_strip": (400, 600, 1500, 630)},
               "CAM_Ref2Match": R2.get("gravel", {})},
    "sand": {"CAM_Overview": {"sand_ref": (700, 600, 900, 800)}, "CAM_Ref2Match": R2.get("sand", {}),
             "CU_SandEye": {"near": (200, 700, 1700, 1000)}},
}
res = {}
for grp, cams in BOX.items():
    for cam, boxes in cams.items():
        p = CAP / f"{cam}.png"
        if not p.exists():
            continue
        a = np.asarray(Image.open(p).convert("RGB")).astype(float)
        for k, (x0, y0, x1, y1) in boxes.items():
            m = np.median(a[y0:y1, x0:x1].reshape(-1, 3), axis=0)
            h, s, v = colorsys.rgb_to_hsv(*(m / 255))
            hh, ll, ss = colorsys.rgb_to_hls(*(m / 255))
            r = {"box": [x0, y0, x1, y1], "rgb": [int(c) for c in m], "hue": round(h * 360, 1), "hsv_s": round(s, 3),
                 "hls_s": round(ss, 3), "L": round(ll, 3), "R/B": round(m[0] / max(m[2], 1), 3)}
            if grp == "gravel":
                r["band_ref_13_30"] = bool(13 <= r["hue"] <= 30 and r["R/B"] >= 1.2 and r["hsv_s"] >= 0.15)
                r["band_orig_25_40"] = bool(25 <= r["hue"] <= 40 and r["hsv_s"] >= 0.15)
            res[f"{grp}:{cam}:{k}"] = r
            print(f"{grp:10s} {cam}:{k:22s} {r['rgb']} h {r['hue']:5.1f} s {r['hsv_s']:.2f} hls_s {r['hls_s']:.2f} L {r['L']:.2f} R/B {r['R/B']:.2f}"
                  + (f" ref-band {r['band_ref_13_30']} orig-band {r['band_orig_25_40']}" if grp == "gravel" else ""))
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
