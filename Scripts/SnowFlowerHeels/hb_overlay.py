"""Overlay projected local-frame points on the reference (numpy only; Blender's bundled python).

    python hb_overlay.py out.png npz:key[,key...] ...  [--cam camera.json] [--box x0,y0,x1,y1]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402
import metro_png as png  # noqa: E402


def main():
    args = sys.argv[1:]
    out = args[0]
    cam_path = C.CACHE / "camera.json"
    box = (0, 0, 900, 1210)
    items = []
    i = 1
    while i < len(args):
        if args[i] == "--cam":
            cam_path = Path(args[i + 1])
            i += 2
            continue
        if args[i] == "--box":
            box = tuple(int(x) for x in args[i + 1].split(","))
            i += 2
            continue
        items.append(args[i])
        i += 1
    if cam_path.exists():
        d = json.loads(Path(cam_path).read_text())
        cam = HC.Cam(d["az"], d["el"], d["s"], d["tx"], d["ty"], d.get("roll", 0.0))
    else:
        cam = HC.Cam(53.03, 33.05, 3.52, 145.02, 928.65, 0.0)
    img = png.read(str(C.REF_PNG)).astype(float)
    if img.max() > 1.5:
        img /= 255.0
    img = img[..., :3] * 0.6 + 0.4
    cols = [(1, 0, 0), (0, 0.6, 1), (0, 0.8, 0), (1, 0.5, 0), (0.8, 0, 0.8), (0.5, 0.3, 0)]
    ci = 0
    for it in items:
        f, keys = it.split(":")
        z = np.load(f)
        for k in keys.split(","):
            p = z[k].reshape(-1, 3)
            q = cam.project(p)
            q = np.round(q).astype(int)
            ok = (q[:, 0] >= 0) & (q[:, 0] < img.shape[1]) & (q[:, 1] >= 0) & (q[:, 1] < img.shape[0])
            img[q[ok, 1], q[ok, 0]] = cols[ci % len(cols)]
            ci += 1
    x0, y0, x1, y1 = box
    png.write(out, (np.clip(img[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8))
    print("OVERLAY", out)


main()
