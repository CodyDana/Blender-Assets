"""VERIFY r8: my own look numbers, ref 2 vs round8/s2 CAM_Ref2Match (both resized to 1448 x 1086, the reference's
size). Boxes picked by this verifier on the gridded images (crops/grid_*.png), per image (the framings differ).
Out: verify_r8/look_ref2.json + crops/look_boxes_*.png"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VD = B / "WorkFiles/dojo/build/verify_r8"
IMGS = {"ref2": B / "References/Dojo/dojo1_reference2.png",
        "ours_s2": B / "WorkFiles/dojo/build/unreal/round8/s2/CAM_Ref2Match.png"}
# (x0, y0, x1, y1), mode: mean | top30 | bot50 | top10
BOX = {
    "ref2": {"sky_top": [(100, 0, 1300, 40)], "sky_horizon_behind_hall": [(250, 100, 480, 140), (960, 95, 1180, 135)],
             "roof_upper": [(560, 150, 880, 240)], "plaster_outbuilding_W": [(125, 250, 270, 330)],
             "sand_near": [(150, 700, 600, 880), (820, 700, 1300, 880)], "sand_far": [(780, 500, 1150, 600), (280, 500, 650, 600)],
             "gravel": [(220, 400, 340, 470)], "gravel_E": [(1080, 395, 1200, 440)], "shoji": [(490, 340, 560, 390), (900, 340, 960, 390)],
             "lantern": [(598, 392, 632, 422), (818, 392, 852, 422)], "veranda_timber": [(360, 405, 600, 440)],
             "content_crop": [(60, 0, 1390, 940)]},
    "ours_s2": {"sky_top": [(0, 0, 1448, 60)], "sky_horizon_behind_hall": [(0, 225, 490, 258), (960, 225, 1448, 258)],
                "roof_upper": [(560, 280, 880, 370)], "plaster_outbuilding_W": [(110, 410, 290, 500)],
                "sand_near": [(1050, 820, 1448, 1080)], "sand_far": [(800, 620, 1250, 700), (180, 620, 620, 690)],
                "gravel": [(0, 530, 160, 600)], "gravel_E": [(1100, 572, 1330, 600)], "shoji": [(500, 490, 555, 535), (890, 490, 945, 535)],
                "lantern": [(592, 548, 628, 578), (818, 548, 854, 578)], "veranda_timber": [(350, 540, 600, 570)],
                "content_crop": [(0, 0, 1448, 1086)]},
}
MODE = {"roof_upper": ["top30", "bot50"], "shoji": ["top30"], "lantern": ["top10"]}


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def desc(px):
    m = px.mean(axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
    return {"rgb": [round(float(x), 1) for x in m], "hue": round(h * 360, 1), "sat": round(s, 3),
            "R/B": round(float(m[0] / max(m[2], 1e-3)), 3), "luma": round(float(luma(m)), 1)}


def hist(a):
    L = luma(a.reshape(-1, 3))
    return {"under40_pct": round(float((L < 40).mean() * 100), 2), "mean": round(float(L.mean()), 1),
            "p10": round(float(np.percentile(L, 10)), 1), "p50": round(float(np.percentile(L, 50)), 1),
            "p90": round(float(np.percentile(L, 90)), 1),
            "clip_pct": round(float((a.reshape(-1, 3).min(axis=1) >= 250).mean() * 100), 3)}


res = {}
for k, p in IMGS.items():
    a = np.asarray(Image.open(p).convert("RGB").resize((1448, 1086), Image.LANCZOS)).astype(np.float64)
    r = {"whole_frame": hist(a)}
    x0, y0, x1, y1 = BOX[k]["content_crop"][0]
    r["content_crop_hist"] = hist(a[y0:y1, x0:x1])
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for reg, boxes in BOX[k].items():
        if reg == "content_crop":
            continue
        px = np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for (x0, y0, x1, y1) in boxes])
        for (x0, y0, x1, y1) in boxes:
            d.rectangle([x0, y0, x1, y1], outline=(0, 255, 0), width=2)
            d.text((x0 + 3, y0 + 3), reg, fill=(0, 255, 0))
        L = luma(px)
        for mode in MODE.get(reg, ["mean"]):
            sel = {"mean": px, "top30": px[L >= np.percentile(L, 70)], "bot50": px[L <= np.percentile(L, 50)],
                   "top10": px[L >= np.percentile(L, 90)]}[mode]
            r[f"{reg}{'' if mode == 'mean' else '_' + mode}"] = desc(sel)
        if reg.startswith("sand"):
            g = luma(a[boxes[0][1]:boxes[0][3], boxes[0][0]:boxes[0][2]])
            from PIL import ImageFilter
            bl = np.asarray(Image.fromarray(g.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(float)
            r[f"{reg}_texture"] = {"luma_std": round(float(g.std()), 2), "highpass_std_sigma3": round(float((g - bl).std()), 2)}
    im.save(VD / "crops" / f"look_boxes_{k}.png")
    res[k] = r
# framing (read off the gridded images by this verifier, 1448 x 1086 px)
res["framing_px"] = {"ref2": {"hall_main_ridge_y": 138, "hall_lower_eave_x": [400, 1060], "veranda_front_y": 445,
                              "sand_top_y": 490},
                     "ours_s2": {"hall_main_ridge_y": 257, "hall_lower_eave_x": [300, 1145], "veranda_front_y": 580,
                                 "sand_top_y": 612}}
fr = res["framing_px"]
res["framing_ratio"] = {"hall_width_ours_over_ref": round((fr["ours_s2"]["hall_lower_eave_x"][1] - fr["ours_s2"]["hall_lower_eave_x"][0])
                                                          / (fr["ref2"]["hall_lower_eave_x"][1] - fr["ref2"]["hall_lower_eave_x"][0]), 3),
                        "ridge_dy_px": fr["ours_s2"]["hall_main_ridge_y"] - fr["ref2"]["hall_main_ridge_y"]}
(VD / "look_ref2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
keys = [k for k in res["ref2"] if k in res["ours_s2"]]
for k in keys:
    print(f"{k:32s} REF {json.dumps(res['ref2'][k])}\n{'':32s} OUR {json.dumps(res['ours_s2'][k])}")
print(res["framing_ratio"])
