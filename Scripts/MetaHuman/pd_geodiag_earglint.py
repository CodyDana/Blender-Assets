"""pd_geodiag_earglint.py -- which capture light makes the white patch in the image-left (-X, character-right) ear.

Uses the per-pixel position/normal passes written by pd_geodiag_pixmap.py (FaceC, UE front camera) and the UE capture
FaceC_Face_Front.png. For the near-white ear pixels it reports the mesh location and, per light of the capture rig,
N.L, N.H (Blinn half vector towards the camera) and whether a shadow ray from the pixel to the light is blocked.
Also runs the same test on the mirrored +X ear to explain the asymmetry.
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P Scripts/MetaHuman/pd_geodiag_earglint.py
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, load_obj  # noqa: E402

NH = 24049
P = OUT / "pixmap"
CAP = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/faces/captures")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def load(path, raw=False):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1][..., :3]
    bpy.data.images.remove(img)
    return a


pos = load(P / "pos_Front.exr") - np.array((100.0, 100.0, 0.0), np.float32)
nrm = load(P / "nrm_Front.exr") * 2 - 1
ue = load(CAP / "FaceC_Face_Front.png")
# mesh for shadow rays (Blender coords = UE with y negated)
Vf, Ff = load_obj(DUMPS["FaceC_Face"])
Vb, Fb = load_obj(DUMPS["FaceC_Body"])
for name, V, F in (("head", Vf, Ff), ("body", Vb, Fb)):
    V = V.copy()
    V[:, 1] *= -1
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], F.tolist())
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
dg = bpy.context.evaluated_depsgraph_get()


def ue_dir(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return np.array((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)))


LIGHTS = {"key(4, shadows)": ue_dir(-27, -117), "fill(2, no shadows)": ue_dir(-12, -58), "rim(2, no shadows)": ue_dir(-37, 90)}
CAM = np.array((0.0, 5.959721088409424 + 70, 173.6))
report = {}
for side, (x0, x1) in (("imageLeft_-X_ear", (200, 330)), ("imageRight_+X_ear", (670, 800))):
    sub = ue[480:760, x0:x1]
    white = (sub.min(2) > 140 / 255.0) & ((sub.max(2) - sub.min(2)) < 30 / 255.0)   # bright AND neutral (specular)
    ys, xs = np.nonzero(white)
    ys, xs = ys + 480, xs + x0
    fg = pos[ys, xs].max(1) > -50
    Pw = pos[ys, xs].copy()
    Pw[:, 1] *= -1                  # UE coords
    N = nrm[ys, xs].copy()
    N[:, 1] *= -1
    r = {"white_pixels": int(len(ys)), "pixel_bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(ys) else None}
    if len(ys):
        r["surface_pos_ue_mean"] = np.round(Pw.mean(0), 2).tolist()
        r["normal_ue_mean"] = np.round(N.mean(0) / np.linalg.norm(N.mean(0)), 3).tolist()
        V = CAM - Pw
        V /= np.linalg.norm(V, axis=1)[:, None]
        for lname, travel in LIGHTS.items():
            L = -travel
            H = L + V
            H /= np.linalg.norm(H, axis=1)[:, None]
            ndl = N @ L
            ndh = (N * H).sum(1)
            blocked = 0
            for p, n in zip(Pw, N):
                o = Vector((p[0], -p[1], p[2])) + Vector((n[0], -n[1], n[2])) * 0.01
                blocked += int(scene.ray_cast(dg, o, Vector((L[0], -L[1], L[2])))[0])
            r[lname] = {"N.L_median": round(float(np.median(ndl)), 3), "N.H_median": round(float(np.median(ndh)), 4),
                        "shadow_ray_blocked_fraction": round(blocked / len(Pw), 3)}
    report[side] = r
(OUT / "earglint_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))
