"""ROUND 5 look pass: measured regions on the DojoLab captures (plain Python, read-only).

Run: py -3 WorkFiles/dojo/build/unreal/round5/measure_r5.py <capture_dir> [tag]
Per region (x0, y0, x1, y1 on the stills, picked on the round-5 it1 captures, drawn on <dir>/regions_r5/<cam>.png):
median sRGB, HSV hue / sat, R/B, near-black fraction (max channel < 12), dark fraction (< 25), clipped (any >= 254).
Groups (the brief's targets, dojo1_reference2):
  SHADE   crushed shade must hold detail: near-black fraction down, median lifted out of the toe
  SUN     sunlit timber hue 20-25 / sat 0.5-0.6 (ref 2 timber (81, 53, 33)); sunlit tiles R/B <= 1.2 (dark slate);
          sunlit plaster warm cream (not orange)
  GLOW    shoji / lantern / lamp glass: warm amber, only the cores clipping
  SKY     posterisation: after a 5 px median (kills the film grain) the fraction of 1-px steps >= 4 levels along rows
          inside cloud regions ("jumps"); and the number of flat plateaus (runs >= 6 px of identical median value)
  HAZE    far ridges vs the sky just above them and the far plain (the silhouettes must read: luminance contrast)
Out: <capture_dir>/regions_r5_<tag>.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CAP = Path(sys.argv[1])
TAG = sys.argv[2] if len(sys.argv) > 2 else CAP.name
R = {   # cam -> region -> (group, box)
    "CU_GateFront": {"gate_ceiling": ("SHADE", (620, 440, 1300, 500)), "gate_post_shade": ("SHADE", (330, 450, 440, 800)),
                     "gate_tiles_shade": ("SUN", (300, 225, 1600, 285)), "emblem_plaque": ("GLOW", (915, 330, 1005, 420))},
    "CAM_GateFromStreet": {},
    "CAM_Drum": {"pavilion_ceiling": ("SHADE", (800, 110, 1500, 220)), "drum_top": ("SHADE", (760, 235, 1200, 290)),
                 "post_sunlit": ("SUN", (270, 150, 430, 850)), "drum_body": ("SUN", (760, 330, 1180, 560))},
    "CU_Taiko": {},
    "CAM_HallVeranda": {"veranda_soffit": ("SHADE", (900, 95, 1600, 200)), "post_shade": ("SHADE", (1115, 160, 1165, 640)),
                        "plaster_shade": ("SHADE", (870, 320, 1000, 440)), "shoji_glow": ("GLOW", (1400, 300, 1580, 500)),
                        "lantern_glow": ("GLOW", (310, 495, 395, 545))},
    "CU_R4_CorridorOpen": {"lattice_rail": ("SHADE", (560, 760, 1270, 900)), "post": ("SHADE", (1285, 300, 1330, 1000)),
                           "inner_wall": ("SHADE", (800, 430, 1250, 630))},
    "CU_R5_AlleyFence": {"fence_boards": ("SHADE", (790, 320, 1300, 720)), "veranda_deck": ("SHADE", (700, 800, 1300, 1000)),
                         "post": ("SHADE", (520, 200, 620, 900))},
    "CU_R4_PavilionTaiko": {"tiles_sunlit": ("SUN", (600, 200, 900, 270)), "post_sunlit": ("SUN", (680, 480, 740, 760)),
                            "plinth_granite": ("SUN", (600, 900, 1050, 1050)), "wall_plaster_sun": ("SUN", (1450, 720, 1850, 850))},
    "CU_R4_RidgeGate": {"noshi": ("SUN", (1000, 640, 1900, 720)), "onigawara": ("SUN", (840, 480, 960, 690)),
                        "tiles": ("SUN", (1000, 850, 1500, 1000))},
    "CU_R4_StorehouseFront": {"plaster_lamp_lit": ("SUN", (1150, 600, 1350, 780)), "gable_plaster": ("SUN", (620, 320, 860, 460)),
                              "door_leaves": ("SHADE", (880, 640, 1050, 900))},
    "CU_R4_ResidenceFront": {"plaster": ("SUN", (450, 440, 650, 650)), "wood_door": ("SHADE", (720, 640, 920, 900)),
                             "lattice_glow": ("GLOW", (1040, 630, 1180, 770))},
    "CAM_EstablishingRef2": {"sky_clouds": ("SKY", (40, 15, 520, 150)), "hall_upper_roof": ("SUN", (520, 190, 900, 280)),
                             "veranda_band": ("SHADE", (300, 520, 1150, 560)), "shoji_front": ("GLOW", (600, 450, 850, 520)),
                             "sand_lit": ("SUN", (100, 700, 500, 900))},
    "CAM_Establishing": {"sky_clouds": ("SKY", (500, 40, 1100, 150))},
    "CU_R5_FarBackground": {"sky_clouds": ("SKY", (100, 20, 900, 200)), "sky_above_ridge": ("HAZE", (700, 230, 900, 280)),
                            "ridge_far": ("HAZE", (700, 310, 900, 350)), "ridge_near": ("HAZE", (700, 380, 900, 405)),
                            "far_plain": ("HAZE", (700, 430, 1300, 520)), "town_roofs": ("SUN", (550, 570, 700, 600))},
    "CU_R5_Skyline": {},
    "CU_R5_MossWallFoot": {"moss_foot": ("SUN", (0, 500, 450, 950)), "plaster": ("SUN", (600, 50, 1200, 250))},
    "CU_Lantern": {},
}


def stats(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(med / 255.0))
    mx = px.max(axis=1)
    return {"box": list(box), "median_srgb": [int(round(c)) for c in med], "hue_deg": round(h * 360, 1),
            "sat": round(s, 3), "val": round(v, 3), "r_over_b": round(float(med[0] / max(med[2], 1)), 3),
            "near_black_frac": round(float(np.mean(mx < 12)), 4), "dark25_frac": round(float(np.mean(mx < 25)), 4),
            "clip_any_frac": round(float(np.mean(mx >= 254)), 4),
            "p95_luma": round(float(np.percentile(px @ np.array([0.2126, 0.7152, 0.0722]), 95)), 1)}


def sky_banding(img, box):
    """rows of a 5 px median-filtered crop: fraction of 1-px steps >= 4 levels (posterisation edges) and the share of
    pixels in flat plateaus (runs >= 6 px of one value) - a smooth sky with grain has few of either after the median."""
    x0, y0, x1, y1 = box
    g = np.asarray(img.crop(box).convert("L").filter(ImageFilter.MedianFilter(5))).astype(np.int32)
    d = np.abs(np.diff(g, axis=1))
    flat = 0
    for row in g:
        run = 1
        for i in range(1, len(row)):
            if row[i] == row[i - 1]:
                run += 1
            else:
                if run >= 6:
                    flat += run
                run = 1
        if run >= 6:
            flat += run
    return {"jump4_frac": round(float(np.mean(d >= 4)), 4), "flat_run6_frac": round(flat / g.size, 4),
            "levels": int(len(np.unique(g)))}


def main():
    out = {"capture_dir": str(CAP), "tag": TAG, "cams": {}}
    (CAP / "regions_r5").mkdir(exist_ok=True)
    for cam, regs in R.items():
        p = CAP / f"{cam}.png"
        if not p.exists():
            continue
        img = Image.open(p).convert("RGB")
        a = np.asarray(img).astype(np.float64)
        mx = a.max(axis=2)
        rec = {"image": {"near_black_frac": round(float(np.mean(mx < 12)), 4),
                         "dark25_frac": round(float(np.mean(mx < 25)), 4),
                         "blown_frac": round(float(np.mean(a.min(axis=2) >= 250)), 5)}}
        d = ImageDraw.Draw(img)
        for k, (grp, box) in regs.items():
            r = stats(a, box)
            r["group"] = grp
            if grp == "SKY":
                r["banding"] = sky_banding(Image.open(p).convert("RGB"), box)
            rec[k] = r
            d.rectangle(box, outline=(0, 255, 255), width=3)
            d.text((box[0] + 4, box[1] + 4), k, fill=(0, 255, 255))
        img.save(CAP / "regions_r5" / f"{cam}.png")
        out["cams"][cam] = rec
    (CAP / f"regions_r5_{TAG}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for cam, rec in out["cams"].items():
        print(f"{cam:22s} IMAGE nb {rec['image']['near_black_frac']:.3f} dark25 {rec['image']['dark25_frac']:.3f}")
        for k, r in rec.items():
            if k == "image":
                continue
            extra = f" band {r['banding']}" if "banding" in r else ""
            print(f"   {r['group']:5s} {k:18s} {str(r['median_srgb']):16s} hue {r['hue_deg']:5.1f} sat {r['sat']:.2f} "
                  f"R/B {r['r_over_b']:.2f} nb {r['near_black_frac']:.3f} clip {r['clip_any_frac']:.3f}{extra}")


main()
