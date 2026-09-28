"""Visual metrics of a pack render against the reference through the SAME rig (maintenance pass).

    <blender python> visual_metrics.py <render_dir> <mask_dir> [--out metrics.json] [--forms f1,f2]

Measures, per beauty shot, what the visual review asked for:

top (spec) view, 6.92 px/mm:
  edge_profile      luminance vs distance (px) inward from the outer silhouette, arm zone only
                    (radius > 0.5 R_tip, so the hub scallops and the hole are excluded); the bright
                    band width is the run of distances whose p50 is above 0.60, and its peak
  bright_share      share of object pixels brighter than 0.60 (the visible bright edge)
  facet_share       share of object pixels on the geometric facets (mask green)
  hole_ring_range   max - min of the face's mean luminance over 1 mm annuli from the hole edge
                    out to 10 mm (the soot ring)
  large_scale_var   std of the face luminance box-blurred over 2 mm, minus its radial mean
                    profile (non-radial large-scale variation; reference 0.0079)
  fine_dark / fine_bright  share of face pixels 0.05 below / above their 5x5 box mean
                    (scratches, flecks, pits), and their ratio
hero (persp):
  bright_facet_share  share of object pixels that are facets AND brighter than 0.60
  facet_share, near facet p50, fine_dark / fine_bright on the face, and the hole halo
  (face luminance vs distance from the hole in px, first 40 px).
"""
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

REF_DIR = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\style_reference")
PX_PER_MM = 900.0 / 130.0
W709 = np.array([0.2126, 0.7152, 0.0722])


def load(path):
    buf = oiio.ImageBuf(str(path))
    return np.asarray(buf.get_pixels(oiio.FLOAT))


def box(img, weight, r):
    """Weighted box mean of radius r (integral images)."""
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
    num, den = rect(si), rect(sw)
    return num / np.maximum(den, 1e-9), den


def erode_steps(inside, steps):
    """Chessboard distance (px) from the outside for pixels of ``inside`` (capped at steps)."""
    dist = np.full(inside.shape, steps, dtype=np.int32)
    cur = inside.copy()
    for k in range(steps):
        nxt = cur.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    nxt &= np.roll(np.roll(cur, dy, 0), dx, 1)
        dist[cur & ~nxt] = k
        cur = nxt
    dist[~inside] = -1
    return dist


def outside_region(obj):
    """Background connected to the image border (flood fill by iterative dilation)."""
    bg = ~obj
    out = np.zeros_like(bg)
    out[0, :] = bg[0, :]; out[-1, :] = bg[-1, :]; out[:, 0] = bg[:, 0]; out[:, -1] = bg[:, -1]
    while True:
        grown = out.copy()
        grown[1:] |= out[:-1]; grown[:-1] |= out[1:]; grown[:, 1:] |= out[:, :-1]; grown[:, :-1] |= out[:, 1:]
        grown &= bg
        if (grown == out).all():
            return out
        out = grown


def shot_metrics(beauty, mask, kind):
    px = load(beauty)
    mk = load(mask)
    lum = px[..., :3] @ W709
    obj = mk[..., 3] > 0.85
    facet = obj & (mk[..., 1] > 0.5)
    wall = obj & (mk[..., 0] > 0.5)
    rows, cols = np.nonzero(obj)
    cy, cx = 0.5 * (rows.min() + rows.max()), 0.5 * (cols.min() + cols.max())
    yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]]
    rad = np.hypot(yy - cy, xx - cx)
    r_tip = rad[obj].max()
    out = {"object_px": int(obj.sum()),
           "facet_share": round(float(facet.sum() / obj.sum()), 4),
           "bright_share": round(float((obj & (lum > 0.60)).sum() / obj.sum()), 4),
           "bright_facet_share": round(float((facet & (lum > 0.60)).sum() / obj.sum()), 4),
           "object_mean": round(float(lum[obj].mean()), 4), "object_p50": round(float(np.median(lum[obj])), 4)}
    face = obj & ~facet & ~wall
    # erode the face by 2 px so facet/wall anti-aliasing does not count
    solid = erode_steps(face, 3) >= 2
    blur5, _ = box(lum, solid.astype(float), 2)
    resid = lum - blur5
    fd = float((solid & (resid < -0.05)).sum() / max(solid.sum(), 1))
    fb = float((solid & (resid > 0.05)).sum() / max(solid.sum(), 1))
    out["fine_dark"], out["fine_bright"] = round(fd, 4), round(fb, 4)
    out["fine_dark_to_bright"] = round(fd / max(fb, 1e-6), 2)
    outside = outside_region(obj)
    holes = ~obj & ~outside
    if kind == "top":
        inside = ~outside
        dist = erode_steps(inside, 30)
        arm = obj & (rad > 0.5 * r_tip) & (rad < 0.93 * r_tip)
        prof = []
        for d in range(0, 26):
            pick = arm & (dist == d)
            if pick.sum() < 20:
                prof.append(None)
                continue
            v = lum[pick]
            prof.append([round(float(np.median(v)), 3), round(float(np.percentile(v, 90)), 3)])
        out["edge_profile_p50_p90"] = prof
        band = 0
        for p in prof:
            if p is None:
                break
            if p[0] > 0.60:
                band += 1
            elif band:
                break
        out["edge_bright_band_px"] = band
        out["edge_bright_band_mm"] = round(band / PX_PER_MM, 3)
        out["edge_peak_p50"] = max(p[0] for p in prof if p)
        out["edge_peak_p90"] = max(p[1] for p in prof if p)
        # hole ring: face luminance in 1 mm annuli from the hole edge
        if holes.any():
            hole_r = rad[holes].max()
            ring = []
            for k in range(0, 11):
                r0 = hole_r + k * PX_PER_MM
                pick = solid & (rad >= r0) & (rad < r0 + PX_PER_MM)
                ring.append(round(float(lum[pick].mean()), 4) if pick.sum() > 30 else None)
            vals = [v for v in ring[1:] if v is not None]
            out["hole_ring_mm_means"] = ring
            out["hole_ring_range"] = round(max(vals) - min(vals), 4) if vals else None
        # non-radial large-scale variation (2 mm box)
        big, cover = box(lum, solid.astype(float), int(round(2 * PX_PER_MM)))
        ok = solid & (cover > 0.6 * (2 * int(round(2 * PX_PER_MM)) + 1) ** 2)
        radial = np.zeros_like(lum)
        rbin = (rad / PX_PER_MM).astype(int)
        for b in np.unique(rbin[ok]):
            pick = ok & (rbin == b)
            radial[pick] = big[pick].mean()
        out["large_scale_var"] = round(float((big - radial)[ok].std()), 4)
        # hub zone (inside 0.45 R) large-scale variation
        hub = ok & (rad < 0.45 * r_tip)
        out["hub_large_scale_var"] = round(float((big - radial)[hub].std()), 4) if hub.sum() > 100 else None
    else:
        near = facet & (yy > cy)
        if near.any():
            out["near_facet_p50"] = round(float(np.median(lum[near])), 4)
            out["near_facet_share"] = round(float(near.sum() / obj.sum()), 4)
            out["near_facet_bright_share"] = round(float((near & (lum > 0.60)).sum() / max(near.sum(), 1)), 4)
        # hole halo: face luminance vs distance from the hole (px), first 40 px
        if holes.any():
            hd = erode_steps(~holes, 45)
            halo = []
            for d in range(2, 42, 4):
                pick = solid & (hd >= d) & (hd < d + 4)
                halo.append(round(float(np.median(lum[pick])), 3) if pick.sum() > 20 else None)
            out["hole_halo_p50_every_4px"] = halo
    return out


def main():
    argv = sys.argv[1:]
    render_dir, mask_dir = Path(argv[0]), Path(argv[1])
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else None
    forms = (argv[argv.index("--forms") + 1].split(",") if "--forms" in argv
             else ["four_point", "eight_point", "square_plate"])
    result = {}
    for kind, shot in (("top", "top"), ("hero", "persp")):
        result[f"reference_{kind}"] = shot_metrics(REF_DIR / f"ref_rig_scaled100_{shot}.png",
                                                   REF_DIR / f"ref_rig_scaled100_{shot}_mask.png", kind)
        for form in forms:
            b, m = render_dir / f"{form}_{shot}.png", mask_dir / f"{form}_{shot}_mask.png"
            if b.exists() and m.exists():
                result[f"{form}_{kind}"] = shot_metrics(b, m, kind)
    keys_top = ["bright_share", "facet_share", "edge_bright_band_mm", "edge_peak_p50", "edge_peak_p90",
                "hole_ring_range", "large_scale_var", "hub_large_scale_var", "fine_dark", "fine_bright",
                "fine_dark_to_bright", "object_mean", "object_p50"]
    keys_hero = ["bright_share", "bright_facet_share", "facet_share", "near_facet_p50", "near_facet_bright_share",
                 "fine_dark", "fine_bright", "fine_dark_to_bright", "object_mean", "object_p50"]
    for kind, keys in (("top", keys_top), ("hero", keys_hero)):
        print(f"--- {kind}")
        names = [n for n in result if n.endswith("_" + kind)]
        print("key".ljust(24) + "".join(n.replace("_" + kind, "")[:13].rjust(14) for n in names))
        for k in keys:
            print(k.ljust(24) + "".join(str(result[n].get(k)).rjust(14) for n in names))
        for n in names:
            if kind == "top":
                print(n, "profile p50:", [p[0] if p else None for p in result[n]["edge_profile_p50_p90"][:18]])
                print(n, "hole ring:", result[n].get("hole_ring_mm_means"))
            else:
                print(n, "halo:", result[n].get("hole_halo_p50_every_4px"))
    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=1))


main()
