"""Trigger guard detail round 2 helper: rectify the close-ups (c1 right side, c6 left side) onto the part's own XZ
plane at the solved part cameras, so the guard / trigger / catch housing outlines can be read in model mm and drawn
over our current outlines.

    py -3 -B Scripts/guns/rifle/parts/trigger_guard_r2.py rectify [--tag r1_final] [--k 12]

Writes scratch/detail/trigger_guard/rect_<panel>.png (reference left, our ROUGH LOOK render of <tag> right, both on a
1 mm grid with 5 mm labels, our current loop / trigger outlines drawn on both) and rect_<panel>.npz (the rectified
panel at k px/mm for tracing).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import trigger_guard_dev as D  # noqa: E402

X0, X1, Z0, Z1 = 290.0, 372.0, -76.0, -26.0


def bilinear(img, u, v):
    H, W = img.shape[:2]
    u = np.clip(u, 0, W - 1.001)
    v = np.clip(v, 0, H - 1.001)
    i0, j0 = np.floor(v).astype(int), np.floor(u).astype(int)
    fy, fx = (v - i0)[..., None], (u - j0)[..., None]
    a, b = img[i0, j0], img[i0, j0 + 1]
    c, d = img[i0 + 1, j0], img[i0 + 1, j0 + 1]
    return (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy)


def rectify(tag="r1_final", k=12):
    from PIL import Image, ImageDraw
    import importlib
    K = D.kit()
    tg = importlib.import_module("parts.trigger_guard")
    outl = {"loop": tg.loop_outline(), "trigger": tg.trigger_outline()}
    xs = np.arange(X0, X1, 1.0 / k)
    zs = np.arange(Z1, Z0, -1.0 / k)
    XX, ZZ = np.meshgrid(xs, zs)
    for key, yface in (("c1", -5.0), ("c6", 5.0)):
        cam = K.part_camera(D.PART, key)
        P3 = np.c_[XX.ravel(), np.full(XX.size, yface), ZZ.ravel()]
        uv = cam.project(P3)
        P = K.panel(key).astype(float)
        ref = bilinear(P, uv[:, 0], uv[:, 1]).reshape(XX.shape + (3,))
        ss = K.ss
        rp = K.scratch / "renders" / f"{D.PART}__{key}_{tag}.png"
        rgba = np.asarray(Image.open(rp).convert("RGBA")).astype(float)
        a = rgba[:, :, 3:4] / 255.0
        bg = np.array([128.0, 128.0, 128.0])
        comp = rgba[:, :, :3] * a + bg * (1 - a)
        ours = bilinear(comp, (uv[:, 0] + 0.5) * ss - 0.5, (uv[:, 1] + 0.5) * ss - 0.5).reshape(XX.shape + (3,))
        if key == "c6":                       # c6 is drawn from the true left (muzzle to the left): mirror to c1's sense
            pass                              # rectified images are in model X already (X right = toward the muzzle)
        np.savez_compressed(D.PRIV / f"rect_{key}.npz", ref=ref.astype(np.uint8), ours=ours.astype(np.uint8),
                            x0=X0, z1=Z1, k=k)
        ims = []
        for arr in (ref, ours):
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            d = ImageDraw.Draw(im)
            H, W = arr.shape[:2]
            for x in np.arange(np.ceil(X0), X1, 1.0):
                px = (x - X0) * k
                col = (0, 200, 0) if int(x) % 5 == 0 else (0, 90, 0)
                if int(x) % 5 == 0:
                    d.line([(px, 0), (px, H)], fill=col)
                    if int(x) % 10 == 0:
                        d.text((px + 2, 2), str(int(x)), fill=(255, 255, 0))
            for z in np.arange(np.ceil(Z0), Z1, 1.0):
                py = (Z1 - z) * k
                if int(z) % 5 == 0:
                    d.line([(0, py), (W, py)], fill=(0, 200, 0))
                    d.text((2, py + 1), str(int(z)), fill=(255, 255, 0))
            for nm, Q in outl.items():
                col = {"loop": (255, 40, 40), "band": (255, 160, 0), "trigger": (60, 160, 255)}[nm]
                pts = [((x - X0) * k, (Z1 - z) * k) for x, z in Q]
                d.line(pts + [pts[0]], fill=col, width=1)
            ims.append(im)
        W, H = ims[0].size
        out = Image.new("RGB", (W, 2 * H + 6), "white")
        out.paste(ims[0], (0, 0))
        out.paste(ims[1], (0, H + 6))
        out.save(D.PRIV / f"rect_{key}.png")
        print("rect", key, out.size)


# ============================================================================================ side L2, label convention
def side_l2_convention(tag, cheek_z=-54.5):
    """Side L2 with the trace's label convention applied to the extended cheeks. rifle_silhouette gives guard faces
    "forward of X 355.3, Z -52 .. -34.85" to the mag_catch label (the convention: the catch housing cheeks belong to
    the mag_catch label); -52 was the round-1 cheek bottom. The round-2 cheeks reach Z -53.87, so this runs the same
    code with that bound at `cheek_z` (forward of X 355.3 the guard has no loop faces: the loop ends at X 355.15).
    rifle_silhouette.py itself is not edited (not this part's file); the official number is reported beside this one
    and the bound change is proposed in review/detail/trigger_guard/spec_proposal.json."""
    import importlib.util
    import json
    src_path = HERE.parent / "rifle_silhouette.py"
    src = src_path.read_text(encoding="utf-8")
    old = "(tc[:, 2] > -52.0) & (tc[:, 2] <= -34.85)"
    if old not in src:
        raise RuntimeError("rifle_silhouette label convention line changed; update side_l2_convention")
    src = src.replace(old, f"(tc[:, 2] > {cheek_z}) & (tc[:, 2] <= -34.85)")
    spec = importlib.util.spec_from_loader("rifle_silhouette_conv", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(src_path)
    exec(compile(src, str(src_path), "exec"), mod.__dict__)
    res = mod.run(str(D.PRIV / "cur_tris.npz"), f"detail/{D.PART}/sil_{tag}_conv")
    sp = res["views"]["side"]["parts"]
    out = {k: sp[k] for k in ("trigger", "trigger_guard", "receiver", "mag_catch", "pistol_grip") if k in sp}
    out["_side_iou_fit"] = res["views"]["side"]["iou_fit"]
    out["_top_iou_fit_valid"] = res["views"]["top"]["iou_fit_valid"]
    (D.REVIEW_PART / f"{tag}_side_l2_convention.json").write_text(json.dumps(out, indent=1))
    print("side L2 (cheeks -> mag_catch label to Z", cheek_z, ")", json.dumps(out)[:1500])
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rectify", "sidel2"])
    ap.add_argument("--tag", default="r1_final")
    ap.add_argument("--k", type=int, default=12)
    a = ap.parse_args()
    if a.cmd == "rectify":
        rectify(a.tag, a.k)
    else:
        side_l2_convention(a.tag)
