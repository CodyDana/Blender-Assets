"""Preview the painted sky through a showcase camera (pinhole, Blender frame) without Unreal.
py -3 sky_preview.py <png> <out.png> cam_name [cam_name...]"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
L = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text())
cams = {c["name"]: c for c in L["cameras"]}
sky = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
H, W = sky.shape[:2]
tiles = []
for name in sys.argv[3:]:
    c = cams[name]
    w, h = c["out_wh"]; w //= 2; h //= 2
    loc, at = np.array(c["loc"]), np.array(c["look_at"])
    f = at - loc; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r); u = np.cross(r, f)
    fx = (w / 2) / math.tan(math.radians(c["hfov_deg"]) / 2)
    xs, ys = np.meshgrid(np.arange(w) - w / 2 + 0.5, np.arange(h) - h / 2 + 0.5)
    d = f[None, None] * fx + r[None, None] * xs[..., None] - u[None, None] * ys[..., None]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    dx, dy, dz = d[..., 0], -d[..., 1], d[..., 2]          # Blender -> UE (y flip)
    uu = np.arctan2(dy, dx) / (2 * math.pi) + 0.5
    vv = 1 - np.arcsin(np.clip(dz, 0, 1)) / (math.pi / 2)
    px = np.clip((uu * W).astype(int), 0, W - 1); py = np.clip((vv * H).astype(int), 0, H - 1)
    t = sky[py, px]; tiles.append(np.pad(t, ((0, 0), (0, 960 - t.shape[1]), (0, 0))))
Image.fromarray(np.concatenate(tiles, 0)).save(sys.argv[2])
