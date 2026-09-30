"""Round 3 side-by-side sheets (system Python, PIL + numpy):
  SBS_R3_UE_framing.png  Unreal r2 capture | ours r3 (UE-like rig) | ours r3 (neutral studio), for CAM_EstablishingRef2
                         and CAM_PlayerEyeSand, plus the same near-ground crop of each at 2x
  SBS_R3_ref2_crops.png  dojo1_reference2 near path / sand crop | ours C_Establish (sunset, the reference-fitted camera)
and region medians in sbs_r3_stats.json.  Run: py -3 Scripts/dojo/ground/r3/sbs_r3.py"""
import colorsys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/dojo/build/round3/ground_materials"
R = OUT / "renders"
UE = ROOT / "WorkFiles/dojo/build/unreal/showcase/captures"
REF = ROOT / "References/Dojo/dojo1_reference2.png"


def med(im, box):
    a = np.asarray(im.convert("RGB").crop(box)).reshape(-1, 3).astype(float)
    m = np.median(a, 0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255))
    return {"box": list(box), "median_srgb": [int(x) for x in m], "hue": round(h * 360, 1), "sat": round(s, 3)}


def label(im, t):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 7 * len(t), 18), fill=(0, 0, 0))
    d.text((4, 3), t, fill=(255, 230, 160))
    return im


def fit(im, w):
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)


def main():
    stats = {}
    rows = []
    for cam, crop in (("CAM_EstablishingRef2", (0.28, 0.62, 0.72, 1.0)), ("CAM_PlayerEyeSand", (0.45, 0.55, 1.0, 1.0))):
        srcs = [("UE r2 capture", Image.open(UE / f"{cam}.png").convert("RGB")),
                ("ours r3, UE-like rig", Image.open(R / "ue" / f"{cam}.png").convert("RGB")),
                ("ours r3, neutral studio", Image.open(R / "studio" / f"{cam}.png").convert("RGB"))]
        full = [label(fit(im, 640), f"{cam} - {t}") for t, im in srcs]
        crops = []
        for t, im in srcs:
            W, H = im.size
            b = (int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H))
            crops.append(label(fit(im.crop(b), 640), f"crop - {t}"))
            if cam == "CAM_EstablishingRef2":
                sx, sy = W / 1448, H / 1086
                stats[f"{cam} | {t}"] = {
                    "sand_near_left": med(im, (int(60 * sx), int(880 * sy), int(420 * sx), int(1080 * sy))),
                    "sand_mid_right": med(im, (int(1000 * sx), int(700 * sy), int(1350 * sx), int(860 * sy))),
                    "path_near": med(im, (int(600 * sx), int(900 * sy), int(840 * sx), int(1080 * sy)))}
        rows += [full, crops]
    W = 3 * 648 + 8
    H = sum(max(i.height for i in r) + 8 for r in rows) + 8
    sheet = Image.new("RGB", (W, H), (25, 25, 25))
    y = 8
    for r in rows:
        x = 8
        for im in r:
            sheet.paste(im, (x, y))
            x += 648
        y += max(i.height for i in r) + 8
    sheet.save(OUT / "SBS_R3_UE_framing.png")
    # reference crops vs the reference-fitted camera (sunset rig)
    ref = Image.open(REF).convert("RGB")
    ours = Image.open(R / "sunset" / "C_Establish.png").convert("RGB")
    boxes = [("near path + sand", (560, 640, 900, 950)), ("near sand left", (250, 760, 650, 940)),
             ("far sand + path", (600, 480, 900, 620))]
    rows = []
    for t, b in boxes:
        rows.append([label(fit(ref.crop(b), 700), f"REF dojo1_reference2 {t}"),
                     label(fit(ours.crop(b), 700), f"ours r3 C_Establish (sunset) {t}")])
        stats[f"ref2 crop {t}"] = {"ref": med(ref, b), "ours": med(ours, b)}
    H = sum(max(i.height for i in r) + 8 for r in rows) + 8
    sheet = Image.new("RGB", (2 * 708 + 8, H), (25, 25, 25))
    y = 8
    for r in rows:
        sheet.paste(r[0], (8, y))
        sheet.paste(r[1], (716, y))
        y += max(i.height for i in r) + 8
    sheet.save(OUT / "SBS_R3_ref2_crops.png")
    (OUT / "sbs_r3_stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


main()
