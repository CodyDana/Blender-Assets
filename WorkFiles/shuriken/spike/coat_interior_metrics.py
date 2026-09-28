"""Like-for-like face texture metrics: the coat INTERIOR of every form and the reference, same rig renders.

restyle_pass2/maint/visual_metrics.py measures the fine scratch / fleck texture on the "face" (object minus
facet and wall mask, eroded 2 px).  On a star that face is the plate; on the 6 mm spike it also holds the
arris round's first chord (|N.z| 0.98) and the worn polished band beside it, i.e. the bright edge line, so
its fine_bright / large_scale_var read the edge, not the coat.  This script measures the coat only, away from
every edge: mask R, G, B all < 0.5 (flat, up-facing, not ground) eroded by ERODE px (0.87 mm in the top view),
for the reference, every star and the spike, with the same 5x5 residual thresholds as visual_metrics.py.

    <blender python> coat_interior_metrics.py <render_dir> <mask_dir> <out.json> [forms]
"""
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

REF_DIR = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\style_reference")
W709 = np.array([0.2126, 0.7152, 0.0722])
PX_PER_MM = 900.0 / 130.0
ERODE = 6


def load(path):
    return np.asarray(oiio.ImageBuf(str(path)).get_pixels(oiio.FLOAT))


def erode(mask, steps):
    out = mask.copy()
    for _ in range(steps):
        nxt = out.copy()
        nxt[1:] &= out[:-1]; nxt[:-1] &= out[1:]; nxt[:, 1:] &= out[:, :-1]; nxt[:, :-1] &= out[:, 1:]
        out = nxt
    return out


def box(img, weight, r):
    def integ(a):
        s = np.zeros((a.shape[0] + 1, a.shape[1] + 1))
        s[1:, 1:] = a.cumsum(0).cumsum(1)
        return s
    h, w = img.shape
    si, sw = integ(img * weight), integ(weight)
    y0 = np.clip(np.arange(h) - r, 0, h); y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w); x1 = np.clip(np.arange(w) + r + 1, 0, w)

    def rect(s):
        return s[y1][:, x1] - s[y0][:, x1] - s[y1][:, x0] + s[y0][:, x0]
    return rect(si) / np.maximum(rect(sw), 1e-9)


def metrics(beauty, mask):
    px, mk = load(beauty), load(mask)
    lum = px[..., :3] @ W709
    obj = mk[..., 3] > 0.85
    blue = mk[..., 2] if mk.shape[-1] > 2 else np.zeros(obj.shape)
    coat = obj & (mk[..., 0] <= 0.5) & (mk[..., 1] <= 0.5) & (blue <= 0.5)
    core = erode(coat, ERODE)
    resid = lum - box(lum, core.astype(float), 2)
    n = max(int(core.sum()), 1)
    fd = float((core & (resid < -0.05)).sum() / n)
    fb = float((core & (resid > 0.05)).sum() / n)
    big = box(lum, core.astype(float), int(round(2 * PX_PER_MM)))
    return {"core_px": int(core.sum()), "fine_dark": round(fd, 4), "fine_bright": round(fb, 4),
            "fine_dark_to_bright": round(fd / max(fb, 1e-6), 2),
            "large_scale_std_2mm": round(float(big[core].std()), 4),
            "core_mean": round(float(lum[core].mean()), 4), "core_p50": round(float(np.median(lum[core])), 4)}


def main():
    argv = sys.argv[1:]
    render_dir, mask_dir, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    forms = argv[3].split(",") if len(argv) > 3 else ["four_point", "eight_point", "square_plate", "six_point", "spike"]
    res = {"method": __doc__.strip().splitlines()[0], "erode_px": ERODE}
    for kind, shot in (("top", "top"), ("hero", "persp")):
        res[f"reference_{kind}"] = metrics(REF_DIR / f"ref_rig_scaled100_{shot}.png",
                                           REF_DIR / f"ref_rig_scaled100_{shot}_mask.png")
        for form in forms:
            b, m = render_dir / f"{form}_{shot}.png", mask_dir / f"{form}_{shot}_mask.png"
            if b.exists() and m.exists():
                res[f"{form}_{kind}"] = metrics(b, m)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    keys = ["core_px", "fine_dark", "fine_bright", "fine_dark_to_bright", "large_scale_std_2mm", "core_mean", "core_p50"]
    for kind in ("top", "hero"):
        names = [k for k in res if k.endswith("_" + kind)]
        print(f"--- {kind}")
        print("key".ljust(22) + "".join(n.replace("_" + kind, "")[:12].rjust(13) for n in names))
        for k in keys:
            print(k.ljust(22) + "".join(str(res[n][k]).rjust(13) for n in names))


main()
