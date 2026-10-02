"""Reference | ours sheets for the sunset petal drift, the fallen-petal tests and the decal (plain Python 3).

    py -3 -B Scripts/dojo/fx/compose_scenes.py --renders WorkFiles/dojo/build/fx/renders/scenes_final
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402

PANELS = {"drift_sunset": (12, 396, 835, 762), "fallen_pavers": (12, 775, 495, 1072),
          "fallen_moss": (508, 775, 1003, 1072), "fallen_gravel": (1017, 775, 1437, 1072)}


def fit(im, w, h):
    """Centre-crop to the target aspect, then resize."""
    r = w / h
    iw, ih = im.size
    if iw / ih > r:
        nw = int(ih * r)
        im = im.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
    else:
        nh = int(iw / r)
        im = im.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    return im.resize((w, h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    a = ap.parse_args()
    rd = Path(a.renders)
    ref = Image.open(fx.PETAL_REF).convert("RGB")
    rows = []
    for key, box in PANELS.items():
        r = ref.crop(box)
        w, h = r.size
        s = 640 / w
        W, H = 640, int(h * s)
        ours = fit(Image.open(rd / f"{key}.png").convert("RGB"), W, H)
        row = Image.new("RGB", (W * 2 + 12, H + 22), (35, 35, 35))
        row.paste(r.resize((W, H), Image.LANCZOS), (0, 22))
        row.paste(ours, (W + 12, 22))
        d = ImageDraw.Draw(row)
        d.text((4, 4), f"SHEET: {key}", fill=(230, 230, 230))
        d.text((W + 16, 4), f"OURS: {key} (Cycles, 9 deg warm sun; our kit ground maps)", fill=(230, 230, 230))
        rows.append(row)
    total_h = sum(r.height for r in rows)
    out = Image.new("RGB", (rows[0].width, total_h), (35, 35, 35))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    out.save(rd / "SBS_petal_scenes_ref_vs_ours.png")
    print(rd / "SBS_petal_scenes_ref_vs_ours.png")


if __name__ == "__main__":
    main()
