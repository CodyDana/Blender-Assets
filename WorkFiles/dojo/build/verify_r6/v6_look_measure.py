"""VERIFY r6: sunlit tiles R/B and sunlit timber saturation, my own boxes (picked by eye on the f1 stills). Sunlit =
the brightest 30 % of the box's pixels by luminance (the faces the sun reaches); also the whole-box median. HSV
saturation = (max - min) / max on the median colour, sRGB 8-bit. Out: verify_r6/look_measure.json"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round6/r6"
VD = B / "WorkFiles/dojo/build/verify_r6"
TILES = {
    "CU_R4_PavilionTaiko": {"pav_roof_E_face_sunlit": (1000, 140, 1680, 290), "wallcap_E_sunlit": (1420, 600, 1900, 720),
                            "wallcap_W": (0, 590, 640, 660)},
    "CU_R4_RidgeGate": {"onigawara_lit_face": (840, 480, 970, 700), "noshi_stack": (980, 640, 1900, 760),
                        "cap_rolls": (980, 540, 1900, 640), "gate_roof_tiles": (1250, 780, 1900, 1060),
                        "storehouse_roof_far": (150, 120, 1250, 320)},
    "CU_R4_RidgeHall": {"hall_roof_tiles_lower_right": (1050, 560, 1920, 1080), "onigawara": (520, 450, 860, 750),
                        "cap_rolls": (800, 350, 1920, 560)},
    "CAM_Ref2Match": {"hall_upper_roof": (470, 80, 980, 175), "hall_lower_roof": (230, 250, 1230, 295)},
    "CAM_EstablishingRef2": {"hall_upper_roof": (450, 190, 1000, 285), "hall_lower_roof": (140, 365, 1320, 420)},
    "CU_HallUpperRoof": {"whole": (0, 0, 1920, 1080)},
}
TIMBER = {
    "CU_R4_PavilionTaiko": {"post_E_sunlit": (1290, 440, 1385, 760), "post_W": (668, 440, 752, 770),
                            "eave_beam_front": (930, 245, 1430, 305), "crate_top": (1100, 880, 1600, 990)},
    "CAM_Drum": {}, "CU_Training": {}, "CAM_GateFromStreet": {}, "CU_GateFront": {},
    "CU_R4_RidgeGate": {"fence_boards": (0, 700, 820, 910), "house_posts": (140, 350, 170, 700)},
    "CU_R4_RidgeHall": {"gable_bargeboard": (520, 860, 700, 1080)},
}


def meas(a, box):
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1].reshape(-1, 3).astype(float)
    lum = r @ np.array([0.2126, 0.7152, 0.0722])
    top = r[lum >= np.percentile(lum, 70)]
    def st(c):
        m = np.median(c, axis=0)
        return {"rgb": [int(v) for v in m], "R/B": round(float(m[0] / max(m[2], 1)), 3),
                "sat": round(float((m.max() - m.min()) / max(m.max(), 1)), 3)}
    return {"box": box, "all": st(r), "sunlit_top30": st(top)}


res = {"tiles": {}, "timber": {}}
for grp, D in (("tiles", TILES), ("timber", TIMBER)):
    for cam, boxes in D.items():
        if not boxes:
            continue
        a = np.asarray(Image.open(CAP / f"{cam}.png").convert("RGB"))
        for k, b in boxes.items():
            res[grp][f"{cam}:{k}"] = meas(a, b)
(VD / "look_measure.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for grp in res:
    for k, v in res[grp].items():
        print(f"{grp:6s} {k:48s} all {v['all']['rgb']} R/B {v['all']['R/B']:.2f} s {v['all']['sat']:.2f} | lit {v['sunlit_top30']['rgb']} R/B {v['sunlit_top30']['R/B']:.2f} s {v['sunlit_top30']['sat']:.2f}")
