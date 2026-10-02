"""Measure the six reference petals (front + back) on dojo_petals_ref.png.

Plain Python 3 (numpy + PIL). Writes WorkFiles/dojo/build/fx/ref/petal_ref_measure.json and a mask overlay.
Per petal: length L (px, base to highest tip), max width W, W/L, the width profile at 10 stations from the base,
the station of max width, the tip notch depth (/L) and the colour of bands along the length (base claw, lower,
middle, upper, tip). The same code measures our renders (--image/--panels) so the numbers compare like for like.

    py -3 -B Scripts/dojo/fx/measure_petal_ref.py [--image path --panels json --out json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "References/Dojo/dojo_petals_ref.png"
OUT = ROOT / "WorkFiles/dojo/build/fx/ref/petal_ref_measure.json"
# Row 1 of the sheet: six panels (x0, x1) between the thin divider lines, y 12..226 (measured on the image).
REF_PANELS = [(14, 272), (278, 518), (524, 737), (743, 984), (990, 1190), (1196, 1440)]
REF_ROW = (12, 226)
# Row 2: the same petals edge-on / 3-4 (y 232..384).
REF_ROW2 = (234, 384)


def petal_mask(rgb: np.ndarray) -> np.ndarray:
    """Petal pixels: clearly brighter than the grey card or clearly pink (the claw is darker but saturated)."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    border = np.concatenate([rgb[:4].reshape(-1, 3), rgb[-4:].reshape(-1, 3)]).astype(np.float32)
    bg = np.median(border, axis=0)
    bright = rgb.max(axis=-1) > bg.max() + 38
    pink = (r - g > 28) & (r > bg[0] + 20)
    return bright | pink


def split_columns(mask: np.ndarray) -> list:
    """Split a panel mask into petals at empty column runs (the two petals never overlap in x)."""
    cols = mask.sum(axis=0) > 1
    runs, start = [], None
    for x, on in enumerate(np.append(cols, False)):
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start > 12:
                runs.append((start, x))
            start = None
    return runs


def measure_petal(rgb: np.ndarray, mask: np.ndarray) -> dict:
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min(), ys.max()
    length = float(y1 - y0 + 1)
    widths = np.array([mask[y].sum() for y in range(y0, y1 + 1)], dtype=np.float32)
    # the base is at the bottom of the sheet's petals (the claw points down)
    prof = []
    for f in np.linspace(0.05, 0.95, 10):
        y = int(round(y1 - f * (length - 1)))
        prof.append(round(float(mask[y].sum()) / length, 4))
    wmax = float(widths.max())
    y_wmax = int(y0 + np.argmax(widths))
    # tip notch: the top contour per column within the middle 70% of the width
    xs_on = np.nonzero(mask.any(axis=0))[0]
    xa, xb = xs_on.min(), xs_on.max()
    top = np.array([np.nonzero(mask[:, x])[0].min() if mask[:, x].any() else y1 for x in range(xa, xb + 1)])
    mid = len(top) // 2
    win = max(3, len(top) // 5)
    centre = top[mid - win: mid + win]
    notch_y = centre.max()
    lobe_l = top[: mid].min()
    lobe_r = top[mid:].min()
    notch = float(notch_y - max(lobe_l, lobe_r)) / length
    bands = {}
    for name, (fa, fb) in {"claw": (0.0, 0.12), "lower": (0.12, 0.3), "middle": (0.4, 0.6),
                           "upper": (0.65, 0.85), "tip": (0.85, 0.97)}.items():
        ya = int(round(y1 - fb * (length - 1)))
        yb = int(round(y1 - fa * (length - 1)))
        sub = mask[ya:yb + 1]
        pix = rgb[ya:yb + 1][sub]
        # drop the 10% darkest (edge shading / shadow) and brightest pixels
        if len(pix):
            lum = pix.mean(axis=1)
            lo, hi = np.percentile(lum, [10, 90])
            keep = pix[(lum >= lo) & (lum <= hi)]
            bands[name] = [round(float(v), 1) for v in keep.mean(axis=0)]
    allpix = rgb[mask]
    return {"length_px": length, "max_width_px": wmax, "w_over_l": round(wmax / length, 4),
            "max_width_at": round(float(y1 - y_wmax) / length, 3), "width_profile": prof,
            "notch_depth": round(notch, 4), "area_fill": round(float(mask.sum()) / (length * wmax), 4),
            "bands_rgb": bands, "mean_rgb": [round(float(v), 1) for v in allpix.mean(axis=0)],
            "bbox": [int(xa), int(y0), int(xb), int(y1)]}


def measure(image: Path, panels, row, row2=None) -> dict:
    rgb = np.asarray(Image.open(image).convert("RGB"))
    out = {"image": str(image), "petals": []}
    overlay = rgb.copy()
    for i, (x0, x1) in enumerate(panels):
        sub = rgb[row[0]:row[1], x0:x1]
        mask = petal_mask(sub)
        runs = split_columns(mask)
        if len(runs) == 1:
            # touching petals: split at the thinnest column in the middle 30-70 % of the run
            a, b = runs[0]
            colsum = mask[:, a:b].sum(axis=0)
            lo, hi = int((b - a) * 0.3), int((b - a) * 0.7)
            cut = a + lo + int(np.argmin(colsum[lo:hi]))
            runs = [(a, cut), (cut + 1, b)]
        if len(runs) < 2:
            out["petals"].append({"panel": i + 1, "error": f"found {len(runs)} petals"})
            continue
        runs = sorted(runs, key=lambda r: -(mask[:, r[0]:r[1]].sum()))[:2]
        runs.sort()
        for side, (a, b) in zip(("front", "back"), runs):
            m = np.zeros_like(mask)
            m[:, a:b] = mask[:, a:b]
            rec = measure_petal(sub, m)
            rec.update({"panel": i + 1, "side": side})
            out["petals"].append(rec)
            ov = overlay[row[0]:row[1], x0:x1]
            ov[m] = (ov[m] * 0.5 + np.array([0, 255, 0]) * 0.5).astype(np.uint8)
        if row2 is not None:
            sub2 = rgb[row2[0]:row2[1], x0:x1]
            m2 = petal_mask(sub2)
            runs2 = split_columns(m2)
            if runs2:
                a, b = max(runs2, key=lambda r: m2[:, r[0]:r[1]].sum())
                a2 = runs2[0]
                # left object = the 3/4 lying view: its height/length ratio is the cup + curl depth
                la, lb = a2
                ys = np.nonzero(m2[:, la:lb].any(axis=1))[0]
                out["petals"][-2]["side_view_h_over_l"] = round(float(ys.max() - ys.min() + 1) / float(lb - la), 3)
    ok = [p for p in out["petals"] if "error" not in p]
    front = [p for p in ok if p["side"] == "front"]
    flat = [p for p in front if p["panel"] in (1, 2, 4, 6)]
    out["summary"] = {
        "flat_front_w_over_l_mean": round(float(np.mean([p["w_over_l"] for p in flat])), 4) if flat else None,
        "flat_front_notch_mean": round(float(np.mean([p["notch_depth"] for p in flat])), 4) if flat else None,
        "flat_front_max_width_at_mean": round(float(np.mean([p["max_width_at"] for p in flat])), 3) if flat else None,
        "flat_front_profile_mean": [round(float(v), 4) for v in np.mean([p["width_profile"] for p in flat], axis=0)]
        if flat else None,
        "front_bands_mean": {k: [round(float(v), 1) for v in np.mean([p["bands_rgb"][k] for p in front], axis=0)]
                             for k in ("claw", "lower", "middle", "upper", "tip")} if front else None,
        "back_bands_mean": {k: [round(float(v), 1) for v in np.mean([p["bands_rgb"][k] for p in ok if p["side"] == "back"], axis=0)]
                            for k in ("claw", "lower", "middle", "upper", "tip")} if ok else None,
    }
    return out, overlay


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=str(REF))
    ap.add_argument("--panels", default=None, help="json file {panels:[[x0,x1],..], row:[y0,y1]}")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    if a.panels:
        spec = json.loads(Path(a.panels).read_text())
        panels, row, row2 = spec["panels"], spec["row"], spec.get("row2")
    else:
        panels, row, row2 = REF_PANELS, REF_ROW, REF_ROW2
    res, overlay = measure(Path(a.image), panels, row, row2)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    Image.fromarray(overlay).save(str(Path(a.out).with_suffix(".overlay.png")))
    print(json.dumps(res["summary"], indent=1))
    for p in res["petals"]:
        print(p.get("panel"), p.get("side"), p.get("w_over_l"), p.get("notch_depth"), p.get("max_width_at"),
              p.get("side_view_h_over_l", ""), p.get("error", ""))


if __name__ == "__main__" and "--outline" not in __import__("sys").argv:
    main()


# --------------------------------------------------------------------------- mean outline (trace authority)

def mean_outline(image: Path = REF, panels=REF_PANELS, row=REF_ROW, flat_panels=(1, 2, 4, 6), n=256,
                 out: Path = OUT.parent / "petal_outline.json") -> dict:
    """Average the flat petals' silhouettes (front + mirrored back) in a length-normalised frame and trace it.

    Frame: y = 0 at the base, 1 at the highest lobe; x in units of the length, 0 on the bbox centre line. The
    silhouettes are averaged, made symmetric and thresholded at 0.5; the boundary is returned as a polygon of
    half-width per y (right side) plus the top contour per x. Only the SHAPE is kept (a traced outline), never
    reference pixels.
    """
    rgb = np.asarray(Image.open(image).convert("RGB"))
    acc = np.zeros((n, n), np.float32)
    count = 0
    for i, (x0, x1) in enumerate(panels):
        if i + 1 not in flat_panels:
            continue
        sub = rgb[row[0]:row[1], x0:x1]
        mask = petal_mask(sub)
        runs = split_columns(mask)
        if len(runs) == 1:
            a, b = runs[0]
            colsum = mask[:, a:b].sum(axis=0)
            lo, hi = int((b - a) * 0.3), int((b - a) * 0.7)
            cut = a + lo + int(np.argmin(colsum[lo:hi]))
            runs = [(a, cut), (cut + 1, b)]
        for a, b in runs[:2]:
            m = np.zeros_like(mask)
            m[:, a:b] = mask[:, a:b]
            ys, xs = np.nonzero(m)
            y0, y1 = ys.min(), ys.max()
            length = y1 - y0 + 1
            # centre line: mean x of the lower half (the claw) and of the notch region
            cx = 0.5 * (xs.min() + xs.max())
            # grid: gy in [0,1] (base..top), gx in [-0.5, 0.5] L
            gy = np.linspace(0, 1, n)
            gx = np.linspace(-0.5, 0.5, n)
            py = (y1 - gy * (length - 1)).round().astype(int)
            px = (cx + gx * length).round().astype(int)
            valid_x = (px >= 0) & (px < m.shape[1])
            grid = np.zeros((n, n), np.float32)
            grid[:, valid_x] = m[py][:, px[valid_x]]
            acc += grid
            acc += grid[:, ::-1]
            count += 2
    mean = acc / count
    shape = mean >= 0.5
    gy = np.linspace(0, 1, n)
    gx = np.linspace(-0.5, 0.5, n)
    half = []
    for j in range(n):
        on = np.nonzero(shape[j])[0]
        half.append(float(gx[on.max()]) if len(on) else 0.0)
    top = []
    for k in range(n // 2, n):
        on = np.nonzero(shape[:, k])[0]
        top.append([float(gx[k]), float(gy[on.max()]) if len(on) else 0.0])
    rec = {"frame": "y 0 base -> 1 top of the lobes; x in units of length, centred", "n": n,
           "y": [round(float(v), 4) for v in gy], "half_width": [round(v, 4) for v in half],
           "top_contour_right": [[round(a, 4), round(b, 4)] for a, b in top],
           "w_over_l": round(2 * max(half), 4), "samples": count}
    out.write_text(json.dumps(rec))
    Image.fromarray((mean * 255).astype(np.uint8)[::-1]).save(str(out.with_suffix(".png")))
    return rec


if __name__ == "__main__" and "--outline" in __import__("sys").argv:
    r = mean_outline()
    print("outline w/l", r["w_over_l"], "samples", r["samples"])
