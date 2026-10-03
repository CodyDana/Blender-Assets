"""voices_paper stage, B: measure the upper-window paper against the other lit paper in -game stills.

Masks by difference in the SAME process / camera (manual exposure, so only the switched emitters change):
  paper  = pixels whose display luma drops >= THR when the window paper's emission goes to 0 (<view>__paperoff)
  neigh  = pixels whose luma drops >= THR when the neighbouring lit paper goes to 0 (<view>__neighoff): the armory
           shoji (MI_DJA_AK_Shoji), the lantern washi (MI_DJA_AK_HWashi), the hall's facade shoji (M_DJ_ShojiPaper)
Per variant and region: luma (Rec.709 on the 8-bit display values) mean / p50 / p95, the share of pixels with any channel
>= 250 (clipped), the share >= 245 in luma (near white), the spread (p90 - p10: a flat light box has none), the mean
colour and its hue / saturation (HSV on the mean sRGB), and the paper / neighbour mean-luma ratio.
Usage: paper_stats.py <capture dir> [--views a,b] -> <dir>/stats.json + printed table
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

THR = 6.0


def load(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def region(img, m):
    if m.sum() < 50:
        return None
    px = img[m]
    L = luma(px)
    mean = px.mean(0)
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in mean / 255.0])
    return {"px": int(m.sum()), "luma_mean": round(float(L.mean()), 2), "luma_p50": round(float(np.percentile(L, 50)), 2),
            "luma_p95": round(float(np.percentile(L, 95)), 2), "spread_p90_p10": round(float(np.percentile(L, 90) - np.percentile(L, 10)), 2),
            "clip_any_ge250": round(float((px.max(1) >= 250).mean()), 4), "luma_ge245": round(float((L >= 245).mean()), 4),
            "mean_rgb": [round(float(c), 1) for c in mean], "hue_deg": round(h * 360.0, 1), "sat": round(s, 3)}


def main():
    d = Path(sys.argv[1])
    only = None
    if "--views" in sys.argv:
        only = set(sys.argv[sys.argv.index("--views") + 1].split(","))
    files = sorted(d.glob("*__base.png"))
    out = {}
    for b in files:
        view = b.name.split("__")[0]
        if only and view not in only:
            continue
        base = load(b)
        po, no = d / f"{view}__paperoff.png", d / f"{view}__neighoff.png"
        if not po.exists():
            continue
        lb = luma(base)
        # noise: what changes between two identical shots (clouds, foliage, Lumen); a switched emitter's own pixels go
        # (almost) black when it is off, a surface it only lights (Lumen bounce) keeps most of its value
        b2 = d / f"{view}__base2.png"
        noise = np.abs(lb - luma(load(b2))) >= 4.0 if b2.exists() else np.zeros(lb.shape, bool)
        lp = luma(load(po))
        pm = ((lb - lp) >= 20.0) & (lp <= 0.35 * lb) & ~noise
        if no.exists():
            ln = luma(load(no))
            nm = ((lb - ln) >= 20.0) & (ln <= 0.35 * lb) & ~noise & ~pm
        else:
            nm = np.zeros_like(pm)
        rec = {"mask_px": {"paper": int(pm.sum()), "neigh": int(nm.sum()), "noise": int(noise.sum())}, "variants": {}}
        np.save(d / f"{view}__mask_paper.npy", pm)
        np.save(d / f"{view}__mask_neigh.npy", nm)
        for f in sorted(d.glob(f"{view}__*.png")):
            tag = f.stem.split("__", 1)[1]
            if tag in ("paperoff", "neighoff", "base2"):
                continue
            img = base if tag == "base" else load(f)
            rp, rn = region(img, pm), region(img, nm)
            ratio = round(rp["luma_mean"] / rn["luma_mean"], 3) if rp and rn and rn["luma_mean"] > 0 else None
            rec["variants"][tag] = {"paper": rp, "neigh": rn, "paper_over_neigh_luma": ratio,
                                    "frame_luma_mean": round(float(luma(img).mean()), 2)}
        out[view] = rec
    (d / "stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for v, r in out.items():
        print(f"== {v}  mask paper {r['mask_px']['paper']} px, neigh {r['mask_px']['neigh']} px")
        for t, x in r["variants"].items():
            p, n = x["paper"], x["neigh"]
            ps = (f"L {p['luma_mean']:6.1f} p95 {p['luma_p95']:6.1f} clip {p['clip_any_ge250']:.3f} spread {p['spread_p90_p10']:5.1f} "
                  f"hue {p['hue_deg']:5.1f} sat {p['sat']:.2f}") if p else "-"
            ns = (f"L {n['luma_mean']:6.1f} p95 {n['luma_p95']:6.1f} clip {n['clip_any_ge250']:.3f} hue {n['hue_deg']:5.1f} sat {n['sat']:.2f}") if n else "-"
            print(f"  {t:10s} paper[{ps}]  neigh[{ns}]  ratio {x['paper_over_neigh_luma']}")


main()
