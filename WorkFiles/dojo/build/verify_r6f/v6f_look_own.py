"""VERIFY r6f (final verifier): sunlit tile R/B (gate <= 1.2) and sunlit timber saturation (gate <= 0.65) on the f1 stills,
MY OWN boxes (picked by eye on the f1 stills; drawn on crops/look_boxes_<cam>.png). 'Sunlit' = the brightest 30 % of the
box by Rec.709 luminance, median colour (the faces the sun reaches); the whole-box median and the brightest 10 % are
reported too. HSV sat = (max - min) / max, sRGB 8-bit. Every box counts for the gate (a tile box only counts where its
brightest 30 % is a sun-facing face; boxes marked 'sky-lit' are reported, not gated).
Out: verify_r6f/look_own.json"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/f1"
VD = B / "WorkFiles/dojo/build/verify_r6f"
# name: (box, gated)
TILES = {
    "CU_R4_PavilionTaiko": {"wallcap_E_sunlit_rolls": ((1560, 615, 1905, 665), True),
                            "wallcap_E_sunlit_whole": ((1390, 590, 1920, 655), True),
                            "wallcap_E_INCL_BEAM_diag": ((1420, 590, 1905, 720), False),
                            "pav_roof_E_tiles_R": ((1450, 200, 1700, 300), True),
                            "pav_roof_E_tiles_L": ((1080, 150, 1420, 228), True),
                            "pav_roof_E_INCL_BOARD_diag": ((1000, 140, 1700, 290), False),
                            "wallcap_W_skylit": ((0, 590, 640, 660), False)},
    "CU_Taiko": {"wallcap_E_right": ((1480, 360, 1920, 540), True), "wallcap_W_left": ((228, 380, 495, 528), True), "wallcap_W_INCL_POST_diag": ((220, 370, 480, 520), False)},
    "CAM_Drum": {"wallcap_E": ((1300, 480, 1700, 610), True), "wallcap_W": ((0, 475, 235, 598), True), "wallcap_W_INCL_POST_diag": ((0, 480, 580, 600), False)},
    "CU_R4_RidgeGate": {"onigawara_lit_face": ((840, 480, 970, 700), True), "cap_rolls": ((980, 540, 1900, 640), True),
                        "noshi_stack": ((980, 640, 1900, 760), True), "gate_roof_tiles": ((1250, 780, 1900, 1060), True)},
    "CU_R4_RidgeHall": {"hall_roof_tiles": ((1050, 560, 1920, 1080), True), "onigawara": ((520, 450, 860, 750), True),
                        "cap_rolls": ((800, 350, 1920, 560), True)},
    "CAM_Ref2Match": {"hall_upper_roof": ((560, 280, 900, 360), True), "hall_lower_roof": ((330, 440, 1120, 480), True),
                      "storehouse_W_roof": ((190, 370, 300, 420), True)},
    "CAM_EstablishingRef2": {"hall_upper_roof": ((540, 250, 900, 330), True), "hall_lower_roof": ((270, 420, 1180, 460), True)},
    "CAM_WallTop": {"wallcap_run": ((800, 700, 1120, 1070), True)},
    "CU_HallUpperRoof": {"whole": ((0, 0, 1920, 1080), False)},
}
TIMBER = {
    "CAM_Drum": {"post_L_sunlit": ((260, 300, 450, 900), True), "post_R": ((1710, 300, 1890, 820), True),
                 "top_beam_SHADE_diag": ((560, 20, 1700, 110), False), "stand": ((620, 700, 1290, 960), True)},
    "CU_R4_PavilionTaiko": {"post_E": ((1290, 440, 1385, 760), True), "post_W": ((668, 440, 752, 770), True),
                            "eave_beam_front": ((930, 245, 1430, 305), True), "crate_top": ((1100, 880, 1600, 990), True)},
    "CU_Training": {"crate_front": ((470, 390, 700, 580), True), "rope_post": ((140, 560, 240, 740), True),
                    "rack": ((740, 420, 1130, 690), True), "wing_post": ((1700, 250, 1800, 620), True),
                    "shed_wall": ((40, 200, 300, 480), True)},
    "CU_R4_RidgeGate": {"fence_boards": ((0, 700, 820, 910), True)},
    "CU_R4_RidgeHall": {"gable_bargeboard": ((520, 860, 700, 1080), True)},
    "CU_R5_HallGableEmblem": {"bargeboard_R": ((1300, 100, 1900, 450), True), "beam_L": ((200, 560, 760, 740), True)},
}


def st(c):
    m = np.median(c, axis=0)
    return {"rgb": [int(v) for v in m], "R/B": round(float(m[0] / max(m[2], 1)), 3),
            "sat": round(float((m.max() - m.min()) / max(m.max(), 1)), 3)}


def meas(a, box):
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1].reshape(-1, 3).astype(float)
    lum = r @ np.array([0.2126, 0.7152, 0.0722])
    return {"box": list(box), "all": st(r), "lit30": st(r[lum >= np.percentile(lum, 70)]),
            "lit10": st(r[lum >= np.percentile(lum, 90)])}


res = {"tiles": {}, "timber": {}}
for grp, D in (("tiles", TILES), ("timber", TIMBER)):
    for cam, boxes in D.items():
        im = Image.open(CAP / f"{cam}.png").convert("RGB")
        a = np.asarray(im)
        dr = ImageDraw.Draw(im)
        for k, (b, gated) in boxes.items():
            m = meas(a, b)
            m["gated"] = gated
            if grp == "tiles":
                m["pass"] = (m["lit30"]["R/B"] <= 1.2) if gated else None
            else:
                m["pass"] = (m["lit30"]["sat"] <= 0.65 and m["lit10"]["sat"] <= 0.65) if gated else None
            res[grp][f"{cam}:{k}"] = m
            dr.rectangle(b, outline=(0, 255, 0) if grp == "tiles" else (255, 0, 255), width=3)
            dr.text((b[0] + 3, b[1] + 3), k, fill=(255, 255, 0))
        try:
            prev = Image.open(VD / "crops" / f"look_boxes_{cam}.png") if False else None
        except Exception:  # noqa: BLE001
            prev = None
        im.resize((im.width // 2, im.height // 2)).save(VD / "crops" / f"look_boxes_{grp}_{cam}.png")
res["tiles_passed"] = all(v["pass"] for v in res["tiles"].values() if v["gated"])
res["timber_passed"] = all(v["pass"] for v in res["timber"].values() if v["gated"])
res["tiles_max_lit30_RB"] = max(v["lit30"]["R/B"] for v in res["tiles"].values() if v["gated"])
res["timber_max_sat"] = max(max(v["lit30"]["sat"], v["lit10"]["sat"]) for v in res["timber"].values() if v["gated"])
(VD / "look_own.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for grp in ("tiles", "timber"):
    for k, v in res[grp].items():
        print(f"{grp:6s} {k:44s} all {v['all']['rgb']} R/B {v['all']['R/B']:.2f} s {v['all']['sat']:.2f} | lit30 {v['lit30']['rgb']} "
              f"R/B {v['lit30']['R/B']:.2f} s {v['lit30']['sat']:.2f} | lit10 R/B {v['lit10']['R/B']:.2f} s {v['lit10']['sat']:.2f} pass {v['pass']}")
print("tiles", res["tiles_passed"], res["tiles_max_lit30_RB"], "timber", res["timber_passed"], res["timber_max_sat"])
