"""VERIFY r3 (independent verifier): region colour measurement on the round-3 f1 captures (plain Python, read-only).
Boxes are picked by the verifier on each image (not the builder's regions_f1.json). Targets (task brief):
  timber   sat 0.45-0.60, hue 20-25 deg
  tiles    R/B 0.90-1.10
  plaster  cream: hue 22-50 deg, sat <= 0.45 (calibrated on reference 2 sunlit plaster: s 0.43, hue 24)
  sand     warm: hue 20-45 deg, sat 0.15-0.40
  health   no black or blown regions beyond the glow cores
Out: verify_r3/capture_measure.json, verify_r3/regions/<cam>.png (boxes drawn)
"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round3/f1"
VD = B / "WorkFiles/dojo/build/verify_r3"
REF = B / "References/Dojo/dojo1_reference2.png"
(VD / "regions").mkdir(exist_ok=True)

TARGET = {"timber": lambda r: 0.45 <= r["sat"] <= 0.60 and 20 <= r["hue_deg"] <= 25,
          "tiles": lambda r: 0.90 <= r["r_over_b"] <= 1.10,
          "plaster": lambda r: 22 <= r["hue_deg"] <= 50 and r["sat"] <= 0.45,  # cream, calibrated on ref 2 lit plaster (s 0.43, hue 24)
          "sand": lambda r: 20 <= r["hue_deg"] <= 45 and 0.15 <= r["sat"] <= 0.40}

# cam -> {region: (kind, box x0,y0,x1,y1)}; kind in TARGET or "info"
R = {
    "CAM_GateFromCourtyard": {
        "gate_tiles_sunlit_slope": ("tiles", (620, 365, 1300, 430)),
        "gate_ridge": ("tiles", (560, 308, 1360, 328)),
        "wallcap_tiles_left": ("tiles", (20, 628, 470, 658)),
        "wallcap_tiles_right": ("tiles", (1450, 628, 1900, 658)),
        "wall_plaster_left": ("plaster", (20, 690, 470, 780)),
        "wall_plaster_right": ("plaster", (1450, 690, 1780, 780)),
        "gate_post_left_by_lamp": ("timber", (500, 640, 545, 820)),
        "gate_post_right_by_lamp": ("timber", (1380, 650, 1425, 820)),
        "gate_leaf_left": ("timber", (670, 560, 712, 840)),
        "sand_left": ("sand", (50, 930, 700, 1060)),
        "sand_right": ("sand", (1200, 930, 1880, 1060)),
        "path": ("info", (800, 950, 940, 1070)),
        "footing": ("info", (20, 800, 460, 855)),
    },
    "CU_GateFront": {
        "gate_tiles_shade": ("tiles", (300, 205, 1600, 255)),
        "gate_ridge_face": ("tiles", (300, 140, 1600, 185)),
        "gate_post_left": ("timber", (345, 450, 430, 1000)),
        "gate_post_right": ("timber", (1480, 450, 1575, 1000)),
        "gate_leaf_left": ("timber", (460, 450, 580, 1000)),
        "gate_ceiling": ("info", (620, 395, 1300, 495)),
        "lamp_glass_left": ("info", (0, 510, 60, 600)),
        "hall_lower_roof": ("tiles", (620, 620, 1300, 660)),
        "sand_left": ("sand", (600, 860, 850, 1000)),
    },
    "CU_WallFooting": {
        "wall_plaster_shade": ("plaster", (700, 350, 1200, 600)),
        "wall_plaster_sunpatch": ("plaster", (20, 300, 160, 600)),
        "wallcap_tiles": ("tiles", (800, 175, 1500, 235)),
        "wallcap_beam_timber": ("timber", (200, 195, 1000, 235)),
        "footing_stone": ("info", (600, 770, 1200, 1000)),
        "gravel": ("info", (1300, 900, 1900, 1070)),
    },
    "CAM_HallVeranda": {
        "hall_post_shade": ("timber", (1120, 200, 1165, 660)),
        "hall_post_right": ("timber", (1610, 80, 1690, 740)),
        "veranda_deck": ("timber", (1200, 640, 1580, 700)),
        "hall_plaster_lower_bay_shade": ("plaster", (870, 310, 1030, 440)),
        "hall_plaster_upper": ("plaster", (1400, 60, 1600, 180)),
        "hall_lower_roof_tiles": ("tiles", (800, 5, 1000, 50)),
        "shoji_glow": ("info", (1400, 280, 1540, 520)),
        "sand_lit": ("sand", (0, 900, 200, 1000)),
    },
    "CAM_EstablishingRef2": {
        "upper_roof_tiles": ("tiles", (520, 200, 940, 262)),
        "lower_roof_tiles": ("tiles", (460, 378, 1000, 412)),
        "clerestory_boarding_timber": ("timber", (600, 322, 680, 362)),
        "hall_plaster_lower": ("plaster", (505, 448, 580, 500)),
        "sand_left": ("sand", (50, 650, 600, 1000)),
        "sand_right": ("sand", (850, 650, 1400, 1000)),
        "path": ("info", (620, 700, 700, 1000)),
        "gravel": ("info", (20, 555, 160, 590)),
        "sky": ("info", (200, 30, 1250, 150)),
    },
    "CAM_Establishing": {
        "gate_ceiling_top25": ("info", (100, 0, 1348, 270)),
        "gate_beam_lintel": ("info", (100, 280, 1348, 350)),
        "gate_post_left_shade": ("timber", (0, 380, 90, 1080)),
        "gate_post_right_sunlit": ("timber", (1360, 380, 1440, 1080)),
        "sand_left": ("sand", (150, 600, 600, 1050)),
        "hall_lower_roof": ("tiles", (300, 372, 1150, 400)),
    },
    "CAM_Drum": {
        "pavilion_ceiling": ("info", (300, 20, 1100, 150)),
        "greybox_post": ("info", (30, 100, 230, 1000)),
        "taiko_stand_beam": ("timber", (830, 700, 1180, 760)),
        "taiko_stand_leg": ("timber", (720, 690, 800, 980)),
        "taiko_lacquer": ("info", (780, 380, 1150, 560)),
        "wallcap_tiles_right_sun": ("tiles", (1550, 520, 1900, 600)),
        "wallcap_tiles_left": ("tiles", (260, 480, 560, 600)),
        "wall_plaster_right": ("plaster", (1650, 700, 1900, 900)),
    },
}
REF_R = {  # dojo1_reference2 (1448 x 1086)
    "upper_roof_tiles": ("tiles", (560, 160, 900, 225)),
    "lower_roof_tiles": ("tiles", (440, 290, 1010, 318)),
    "side_building_plaster_lit": ("plaster", (180, 280, 270, 360)),
    "veranda_posts_deck_timber": ("timber", (360, 410, 1080, 440)),
    "sand_left": ("sand", (150, 560, 600, 880)),
    "path": ("info", (660, 600, 780, 900)),
}


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64)


def region(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(med / 255.0))
    return {"box": list(box), "median_srgb": [int(round(c)) for c in med], "hue_deg": round(h * 360, 1),
            "sat": round(s, 3), "val": round(v, 3), "r_over_b": round(float(med[0] / max(med[2], 1)), 3),
            "near_black_frac": round(float(np.mean(px.max(axis=1) < 12)), 4),
            "blown_frac": round(float(np.mean(px.min(axis=1) >= 250)), 4)}


def health(a):
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    h, w = mx.shape
    t = 32
    def tiles(mask):
        return mask[: h // t * t, : w // t * t].reshape(h // t, t, w // t, t).swapaxes(1, 2).reshape(h // t, w // t, t * t).mean(axis=2)
    bt = tiles(mx < 12) > 0.9
    wt = tiles(mn >= 250) > 0.5
    dark = tiles(mx < 25) > 0.9
    return {"size": [w, h], "near_black_frac(max<12)": round(float(np.mean(mx < 12)), 4),
            "very_dark_frac(max<25)": round(float(np.mean(mx < 25)), 4),
            "black_tiles_32px": int(bt.sum()), "dark_tiles_32px(max<25)": int(dark.sum()), "n_tiles": int(bt.size),
            "black_tile_rc": [[int(r), int(c)] for r, c in zip(*np.nonzero(bt))][:40],
            "blown_frac(min>=250)": round(float(np.mean(mn >= 250)), 4), "blown_tiles_32px": int(wt.sum()),
            "blown_tile_rc": [[int(r), int(c)] for r, c in zip(*np.nonzero(wt))][:40],
            "any_255_frac": round(float(np.mean(mx >= 255)), 4)}


res = {"cams": {}, "reference2": {}, "health": {}}
for cam, regs in R.items():
    a = load(CAP / f"{cam}.png")
    im = Image.open(CAP / f"{cam}.png").convert("RGB")
    d = ImageDraw.Draw(im)
    res["cams"][cam] = {}
    for n, (kind, box) in regs.items():
        r = region(a, box)
        r["kind"] = kind
        r["pass"] = bool(TARGET[kind](r)) if kind in TARGET else None
        res["cams"][cam][n] = r
        d.rectangle(box, outline=(0, 255, 0) if r["pass"] in (True, None) else (255, 0, 0), width=3)
        d.text((box[0] + 4, box[1] + 2), n, fill=(255, 255, 0))
    im.save(VD / "regions" / f"{cam}.png")
a = load(REF)
for n, (kind, box) in REF_R.items():
    r = region(a, box)
    r["kind"] = kind
    r["pass"] = bool(TARGET[kind](r)) if kind in TARGET else None
    res["reference2"][n] = r
for p in sorted(CAP.glob("C*_*.png")):
    res["health"][p.stem] = health(load(p))
summ = {k: {"n": 0, "pass": 0, "fails": []} for k in TARGET}
for cam, regs in res["cams"].items():
    for n, r in regs.items():
        if r["kind"] in TARGET:
            summ[r["kind"]]["n"] += 1
            if r["pass"]:
                summ[r["kind"]]["pass"] += 1
            else:
                summ[r["kind"]]["fails"].append(f"{cam}/{n} {r['median_srgb']} h{r['hue_deg']} s{r['sat']} R/B {r['r_over_b']}")
res["summary"] = summ
(VD / "capture_measure.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for cam, regs in res["cams"].items():
    for n, r in regs.items():
        print(f"{cam:22s} {n:32s} {r['kind']:8s} {str(r['median_srgb']):16s} h{r['hue_deg']:6.1f} s{r['sat']:.3f} v{r['val']:.3f} R/B {r['r_over_b']:.2f} nb {r['near_black_frac']:.3f} blown {r['blown_frac']:.3f} {r['pass']}")
print("--- reference2")
for n, r in res["reference2"].items():
    print(f"{n:32s} {r['kind']:8s} {str(r['median_srgb']):16s} h{r['hue_deg']:6.1f} s{r['sat']:.3f} R/B {r['r_over_b']:.2f} {r['pass']}")
print("--- health")
for k, v in res["health"].items():
    print(f"{k:22s} nb {v['near_black_frac(max<12)']:.4f} dark25 {v['very_dark_frac(max<25)']:.4f} blacktiles {v["black_tiles_32px"]:4d} darktiles {v['dark_tiles_32px(max<25)']:4d}/{v['n_tiles']} blown {v['blown_frac(min>=250)']:.4f} blowntiles {v['blown_tiles_32px']} any255 {v['any_255_frac']:.4f}")
for k, v in summ.items():
    print(k, v["pass"], "/", v["n"])
