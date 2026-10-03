"""INDEPENDENT VERIFIER: window paper vs the neighbouring lit paper, from the verifier's own -game stills.
Masks by switching emitters off in the same process (manual exposure):
  paper = luma drop >= 10 AND >= 50 % of the base luma when the window paper's emission is x0 (bloom halo excluded by the
          fractional rule), minus the noise mask (|base - base2| >= 4, dilated 2 px)
  shoji = the same rule with ONLY the transom shoji MI_DJA_AK_Shoji x0 (the lit paper strip directly above the windows)
  other = the same rule with all neighbours x0, minus shoji (lantern washi, facade shoji)
Writes verify/paper/stats.json and verify/paper/sheet.jpg (per view: base frame with masks outlined + a 2x crop)."""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

D = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\voices_paper\verify\paper")


def load(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def dilate(m, r):
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * r + 1))
    return np.asarray(im) > 0


def drop_mask(lb, loff, noise):
    d = lb - loff
    return (d >= 10.0) & (d >= 0.5 * np.maximum(lb, 1.0)) & ~noise


def stats(img, m):
    n = int(m.sum())
    if n < 50:
        return {"px": n}
    px = img[m]
    L = luma(px)
    mean = px.mean(0)
    h, s, v = colorsys.rgb_to_hsv(*[float(c) / 255.0 for c in mean])
    return {"px": n, "luma_mean": round(float(L.mean()), 1), "luma_p50": round(float(np.percentile(L, 50)), 1),
            "luma_p95": round(float(np.percentile(L, 95)), 1),
            "spread_p90_p10": round(float(np.percentile(L, 90) - np.percentile(L, 10)), 1),
            "cv": round(float(L.std() / max(L.mean(), 1e-3)), 3),
            "clip_any_ge250_pct": round(100.0 * float((px.max(1) >= 250).mean()), 2),
            "mean_rgb": [round(float(c), 1) for c in mean], "hue_deg": round(h * 360.0, 1), "sat": round(s, 3)}


def main():
    out, tiles = {}, []
    for b in sorted(D.glob("*__base.png")):
        v = b.name.split("__")[0]
        f = {t: D / f"{v}__{t}.png" for t in ("base2", "paperoff", "shojioff", "neighoff")}
        if not all(p.exists() for p in f.values()):
            out[v] = {"missing": [t for t, p in f.items() if not p.exists()]}
            continue
        base = load(b)
        lb = luma(base)
        L = {t: luma(load(p)) for t, p in f.items()}
        noise = dilate(np.abs(lb - L["base2"]) >= 4.0, 2)
        mp = drop_mask(lb, L["paperoff"], noise)
        ms = drop_mask(lb, L["shojioff"], noise) & ~mp
        mo = drop_mask(lb, L["neighoff"], noise) & ~mp & ~ms
        rec = {"noise_px": int(noise.sum()), "paper": stats(base, mp), "shoji": stats(base, ms), "other_lit_paper": stats(base, mo)}
        p, s = rec["paper"], rec["shoji"]
        if p.get("luma_mean") and s.get("luma_mean"):
            rec["paper_over_shoji_luma"] = round(p["luma_mean"] / s["luma_mean"], 3)
            dh = abs(p["hue_deg"] - s["hue_deg"])
            rec["hue_diff_deg"] = round(min(dh, 360 - dh), 1)
        if p.get("luma_mean") and rec["other_lit_paper"].get("luma_mean"):
            rec["paper_over_other_luma"] = round(p["luma_mean"] / rec["other_lit_paper"]["luma_mean"], 3)
        # the paper's own contribution: how much the frame outside the paper changes when it is switched off
        outside = ~mp & ~noise & ~dilate(mp, 6)
        rec["spill_outside_mean_luma_drop"] = round(float((lb - L["paperoff"])[outside].mean()), 3)
        out[v] = rec
        # sheet tile: full frame with outlines (paper red, shoji cyan, other yellow) + crop around the paper
        im = Image.open(b).convert("RGB")
        ov = im.copy()
        dr = ImageDraw.Draw(ov)
        for m, col in ((mp, (255, 40, 40)), (ms, (0, 220, 255)), (mo, (255, 220, 0))):
            e = m & ~(np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0)
            ys, xs = np.nonzero(e)
            for x, y in zip(xs[::1], ys[::1]):
                dr.point((int(x), int(y)), fill=col)
        full = ov.resize((640, 360))
        if mp.sum() >= 50:
            ys, xs = np.nonzero(mp)
            cx, cy = int(np.median(xs)), int(np.median(ys))
        else:
            cx, cy = 960, 540
        x0, y0 = max(0, min(1920 - 480, cx - 240)), max(0, min(1080 - 270, cy - 135))
        crop = im.crop((x0, y0, x0 + 480, y0 + 270)).resize((640, 360), Image.LANCZOS)
        t = Image.new("RGB", (1280, 392), (20, 20, 20))
        t.paste(full, (0, 32))
        t.paste(crop, (640, 32))
        txt = f"{v}  paper L {p.get('luma_mean')} h{p.get('hue_deg')} s{p.get('sat')} clip {p.get('clip_any_ge250_pct')}%  |  " \
              f"shoji L {s.get('luma_mean')} h{s.get('hue_deg')}  ratio {rec.get('paper_over_shoji_luma')}"
        ImageDraw.Draw(t).text((8, 8), txt, fill=(240, 240, 240))
        tiles.append(t)
    (D / "stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    if tiles:
        sheet = Image.new("RGB", (1280, 392 * len(tiles)), (0, 0, 0))
        for i, t in enumerate(tiles):
            sheet.paste(t, (0, 392 * i))
        sheet.save(D / "sheet.jpg", quality=88)
    for v, r in out.items():
        p, s, o = r.get("paper", {}), r.get("shoji", {}), r.get("other_lit_paper", {})
        print(f"{v:24s} paper px {p.get('px'):>7} L {p.get('luma_mean')} p95 {p.get('luma_p95')} clip {p.get('clip_any_ge250_pct')} "
              f"h/s {p.get('hue_deg')}/{p.get('sat')} cv {p.get('cv')} | shoji px {s.get('px')} L {s.get('luma_mean')} h/s "
              f"{s.get('hue_deg')}/{s.get('sat')} | other px {o.get('px')} L {o.get('luma_mean')} | ratio {r.get('paper_over_shoji_luma')} "
              f"dh {r.get('hue_diff_deg')} spill {r.get('spill_outside_mean_luma_drop')}")


main()
