"""pf_overlay.py -- draw face-landmark indices onto a pf_female.py capture (plain Python + Pillow).

The capture camera is a pinhole with horizontal fov `fov` (SceneCapture2D fov_angle), image 1000x1200, aimed from
`cam` at `look` (UE world cm, Z up). Landmarks come from a pf report / preset data json.
usage: py pf_overlay.py <image> <landmarks.json-key-path> <out>   (see __main__ for the explore1 default)
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1000, 1200


def project(p, cam, look, fov):
    f = [look[i] - cam[i] for i in range(3)]
    n = math.sqrt(sum(x * x for x in f))
    f = [x / n for x in f]
    up0 = (0.0, 0.0, 1.0)
    r = [up0[1] * f[2] - up0[2] * f[1], up0[2] * f[0] - up0[0] * f[2], up0[0] * f[1] - up0[1] * f[0]]  # up x f
    n = math.sqrt(sum(x * x for x in r))
    r = [x / n for x in r]
    u = [f[1] * r[2] - f[2] * r[1], f[2] * r[0] - f[0] * r[2], f[0] * r[1] - f[1] * r[0]]  # f x r
    d = [p[i] - cam[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    k = (W / 2) / math.tan(math.radians(fov / 2))
    x = W / 2 + sum(d[i] * r[i] for i in range(3)) / z * k
    y = H / 2 - sum(d[i] * u[i] for i in range(3)) / z * k
    return x, y


def overlay(img_path, lms, cam, look, fov, out, only=None):
    im = Image.open(img_path).convert("RGB")
    dr = ImageDraw.Draw(im)
    for i, p in enumerate(lms):
        if only and i not in only:
            continue
        x, y = project(p, cam, look, fov)
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 40, 40))
        dr.text((x + 4, y - 6), str(i), fill=(255, 255, 0))
    im.save(out)


if __name__ == "__main__":
    root = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_female")
    rep = json.loads((root / "pf_explore1_1.json").read_text(encoding="utf-8"))["explore1"]
    pdata = json.loads((root / "pf_preset_data.json").read_text(encoding="utf-8"))
    fc = rep["face_center"]
    cam_front = (fc[0], fc[1] + 58.0, fc[2])
    lms = pdata["Aera"]["landmarks"]
    overlay(root / "explore1_captures/p_Aera_Face_Front.png", lms, cam_front, fc, 30.0, sys.argv[1] if len(sys.argv) > 1 else
            r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/196b90e6-f654-4528-8611-24c12e60d4b5/scratchpad/pf_lm_front.png")
    a = math.radians(90)
    cam_side = (fc[0] + 58.0, fc[1], fc[2])
    overlay(root / "explore1_captures/v_M3_Face_Profile_L.png", rep["variants"]["M3"]["landmarks"], cam_side, fc, 30.0,
            r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/196b90e6-f654-4528-8611-24c12e60d4b5/scratchpad/pf_lm_side.png")
