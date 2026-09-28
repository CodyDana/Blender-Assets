"""pd_r2_linemetric.py -- thin-dark-line strength along the posterior jaw ramus in UE captures (no Unreal).

Two steps (Pillow lives in `py`, numpy only in Blender's Python):
  py Scripts/MetaHuman/pd_r2_linemetric.py convert <png> [<png> ...]       -> writes <png>.rgb next to a scratch copy
  "<blender>/python.exe" Scripts/MetaHuman/pd_r2_linemetric.py measure <out.json> <view>=<png> [...]

Metric (per capture, view-specific region of interest drawn around the ramus line of the FaceC captures):
  valley depth per row = min(max L over [x-b..x-a], max L over [x+a..x+b]) - L(x) (L = Rec.601 luma, 3-px vertical
  mean), best x inside a window that follows the line; reported: mean and max depth over the rows, rows with a
  depth > 10 (a visible line), and the black top-hat (grey closing - L, square element) p98 inside the ROI.
A smooth jaw-to-neck transition gives depths of a few units (skin texture); FaceC's crisp ramus line gives 15-30.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRATCH = Path(r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
               r"196b90e6-f654-4528-8611-24c12e60d4b5/scratchpad/r2fix/raw")

# view -> (row range, row step, path points [(y, x)...] of the FaceC line, window half-width, a, b, top-hat size)
VIEWS = {
    "Face_ThreeQuarter": ((740, 890), 5, [(740, 728), (780, 712), (830, 688), (880, 650)], 30, 4, 8, 11),
    "JawClose": ((250, 560), 6, [(250, 830), (350, 800), (450, 765), (550, 725)], 45, 10, 22, 31),
    # narrow scale (crisp lines only): a 1-2 mm line is ~8-16 px wide in JawClose, a soft contour 40+ px
    "JawClose_narrow": ((250, 560), 6, [(250, 830), (350, 800), (450, 765), (550, 725)], 45, 5, 11, 15),
    # controls: the same paths moved onto the smooth cheek (skin-texture noise floor of the metric)
    "Face_ThreeQuarter_ctl": ((740, 890), 5, [(740, 578), (780, 562), (830, 538), (880, 500)], 30, 4, 8, 11),
    "JawClose_ctl": ((250, 560), 6, [(250, 530), (350, 500), (450, 465), (550, 425)], 45, 10, 22, 31),
}


def convert(paths):
    from PIL import Image
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for p in paths:
        im = Image.open(p).convert("RGB")
        dst = SCRATCH / (Path(p).name + ".rgb")
        dst.write_bytes(im.tobytes())
        (SCRATCH / (Path(p).name + ".size")).write_text(f"{im.width} {im.height}")
    print("converted", len(paths))


def measure(out_json, pairs):
    import numpy as np

    def load(name):
        w, h = (int(v) for v in (SCRATCH / (name + ".size")).read_text().split())
        a = np.frombuffer((SCRATCH / (name + ".rgb")).read_bytes(), np.uint8).reshape(h, w, 3).astype(np.float64)
        return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]

    def maxf(a, k, axis):
        from numpy.lib.stride_tricks import sliding_window_view
        pad = [(0, 0), (0, 0)]
        pad[axis] = (k // 2, k // 2)
        return sliding_window_view(np.pad(a, pad, mode="edge"), k, axis=axis).max(-1)

    def minf(a, k, axis):
        from numpy.lib.stride_tricks import sliding_window_view
        pad = [(0, 0), (0, 0)]
        pad[axis] = (k // 2, k // 2)
        return sliding_window_view(np.pad(a, pad, mode="edge"), k, axis=axis).min(-1)

    res = {}
    for pair in pairs:
        view, png = pair.split("=", 1)
        name = Path(png).name
        (y0, y1), ystep, path, half, a, b, k = VIEWS[view]
        L = load(name)
        Lv = (L[:-2] + L[1:-1] + L[2:]) / 3.0
        Lv = np.vstack([L[:1], Lv, L[-1:]])
        py = np.array([p[0] for p in path], float)
        px = np.array([p[1] for p in path], float)
        rows = []
        for y in range(y0, y1 + 1, ystep):
            xc = float(np.interp(y, py, px))
            best = (-1e9, None)
            for x in range(int(xc - half), int(xc + half) + 1):
                if x - b < 0 or x + b >= L.shape[1]:
                    continue
                left = Lv[y, x - b:x - a + 1].max()
                right = Lv[y, x + a:x + b + 1].max()
                d = min(left, right) - Lv[y, x]
                if d > best[0]:
                    best = (d, x)
            rows.append([y, best[1], round(float(best[0]), 1)])
        depths = np.array([r[2] for r in rows])
        closing = minf(minf(maxf(maxf(L, k, 0), k, 1), k, 0), k, 1)
        th = closing - L
        mask = np.zeros_like(L, bool)
        for y in range(y0, y1 + 1):
            xc = int(np.interp(y, py, px))
            mask[y, max(0, xc - half):xc + half + 1] = True
        res[name] = {"view": view, "depth_mean": round(float(depths.mean()), 2),
                     "depth_max": round(float(depths.max()), 1),
                     "rows_gt10": int((depths > 10).sum()), "rows": len(rows),
                     "tophat_p98": round(float(np.percentile(th[mask], 98)), 1),
                     "tophat_px_gt15": int((th[mask] > 15).sum()), "trace": rows}
        print(f"{name:60s} depth mean {res[name]['depth_mean']:6.2f} max {res[name]['depth_max']:6.1f} "
              f"rows>10 {res[name]['rows_gt10']:3d}/{len(rows)} tophat p98 {res[name]['tophat_p98']:6.1f} "
              f"px>15 {res[name]['tophat_px_gt15']}")
    Path(out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "convert":
        convert(sys.argv[2:])
    else:
        measure(sys.argv[2], sys.argv[3:])
