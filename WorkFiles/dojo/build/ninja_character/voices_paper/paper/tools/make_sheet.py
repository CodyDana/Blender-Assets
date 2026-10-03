"""voices_paper stage, B: before / after sheet of the upper-window paper.
Before = sweep2/<view>__base.png (the level as synced at rev 5: night-tinted copies, x1.0); after = final/<view>__base.png
(the saved level after dj_armory_look's change). Per view: the full frame pair and a crop around the paper mask, labelled
with the measured paper / neighbour numbers from each folder's stats.json. -> ../before_after.jpg"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent.parent
B, A = HERE / "sweep2", HERE / "final"
VIEWS = ["CAM_AK_CW_WestAisle", "CAM_AK_CX_FromPlatform", "V1_EastAisle_to_W", "V2_WestAisle_to_E", "V3_Platform_S",
         "CAM_DoorwayIn", "V5_CourtyardSteps"]
sb = json.loads((B / "stats.json").read_text(encoding="utf-8"))
sa = json.loads((A / "stats.json").read_text(encoding="utf-8"))
W = 760


def label(st, view):
    v = st.get(view, {}).get("variants", {}).get("base") or {}
    p, n = v.get("paper"), v.get("neigh")
    if not p:
        return "paper not in view"
    s = f"paper L {p['luma_mean']:.0f} p95 {p['luma_p95']:.0f} clip {100 * p['clip_any_ge250']:.1f}% hue {p['hue_deg']:.0f} sat {p['sat']:.2f}"
    if n:
        s += f" | neighbour L {n['luma_mean']:.0f} hue {n['hue_deg']:.0f} | ratio {v['paper_over_neigh_luma']}"
    return s


rows = []
for view in VIEWS:
    fb, fa = B / f"{view}__base.png", A / f"{view}__base.png"
    if not (fb.exists() and fa.exists()):
        continue
    ib, ia = Image.open(fb).convert("RGB"), Image.open(fa).convert("RGB")
    mfile = A / f"{view}__mask_paper.npy"
    crop = None
    if mfile.exists():
        m = np.load(mfile)
        if m.sum() > 200:
            ys, xs = np.nonzero(m)
            x0, x1 = np.percentile(xs, 1), np.percentile(xs, 99)
            y0, y1 = np.percentile(ys, 1), np.percentile(ys, 99)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w = max(x1 - x0 + 120, 480)
            h = w * 9 / 16
            crop = (int(max(0, cx - w / 2)), int(max(0, cy - h / 2)), int(min(1920, cx + w / 2)), int(min(1080, cy + h / 2)))
    tiles = [ib.resize((W, int(W * 9 / 16))), ia.resize((W, int(W * 9 / 16)))]
    if crop:
        tiles += [ib.crop(crop).resize((W, int(W * 9 / 16))), ia.crop(crop).resize((W, int(W * 9 / 16)))]
    th = int(W * 9 / 16)
    r = Image.new("RGB", (2 * W, 26 + th * (len(tiles) // 2) + 36), "black")
    d = ImageDraw.Draw(r)
    d.text((6, 6), f"{view}   BEFORE (as synced, rev 5)", fill="white")
    d.text((W + 6, 6), "AFTER (day paper colour, x0.18, no shadow)", fill="white")
    for i, t in enumerate(tiles):
        r.paste(t, ((i % 2) * W, 26 + (i // 2) * th))
    d.text((6, 26 + th * (len(tiles) // 2) + 4), "before: " + label(sb, view), fill=(255, 210, 120))
    d.text((6, 26 + th * (len(tiles) // 2) + 19), "after:  " + label(sa, view), fill=(140, 230, 140))
    rows.append(r)
H = sum(r.size[1] for r in rows)
sheet = Image.new("RGB", (2 * W, H), "black")
y = 0
for r in rows:
    sheet.paste(r, (0, y))
    y += r.size[1]
sheet.save(HERE / "before_after.jpg", quality=86)
print(HERE / "before_after.jpg", sheet.size)
