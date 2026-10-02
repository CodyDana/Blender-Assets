"""Stone tracer (STONE_BUILDING_STUDY.md 6.8): writes and checks References/<Item>/trace_<crop>.json (stone_trace/1).

numpy + PIL only (no scipy / skimage / cv2 on this PC); no bpy. Track-neutral.

Modes
  manual   stones typed by hand in SOURCE-image pixels (x right, y down), read off 10-20x gridded crops (the
           `grid` command draws them). A stone may be typed as a polygon (`poly`) or as its traced extents
           `ext` = [x_left, x_right, y_top, y_bottom] plus an optional `lean` (px the top shifts right of the bottom)
           and `round` (0..0.5, the share of each extent cut at the corners); `expand` turns extents into an
           8-point outline. The extents are the joint lines read off the crop; the octagon is only their outline.
  seed     for crops where stones are >= ~12 px: a dark-joint mask (luma below k x the local mean) -> a two-pass
           chamfer distance -> seeds at distance maxima -> a priority flood (watershed) -> one convex outline per
           cell. Every seeded stone is written with mode "seed" and conf "partial"; correct them by hand.

CLI
  py -3 Scripts/stone/stone_trace.py grid <png> --box x0 y0 x1 y1 --k 20 --out <png>
  py -3 Scripts/stone/stone_trace.py expand <trace.json>            (fills poly from ext; validates; rewrites)
  py -3 Scripts/stone/stone_trace.py seed <png> --box x0 y0 x1 y1 --out <trace.json> [--px-per-m 32 --unc 6]
  py -3 Scripts/stone/stone_trace.py overlay <trace.json> --out <png> [--k 8]
  py -3 Scripts/stone/stone_trace.py validate <trace.json>
"""
from __future__ import annotations

import argparse
import heapq
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stone_measure as SM  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "stone_trace/1"


def tool_git():
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "Scripts/stone/stone_trace.py"],
                           capture_output=True, text=True, timeout=10)
        if r.stdout.strip():
            return "uncommitted"
        h = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                           timeout=10)
        return h.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


# ------------------------------------------------------------------------------------------------ grid
def grid(png, box, k, out, step=2, major=10):
    im = Image.open(png).convert("RGB")
    x0, y0, x1, y1 = box
    c = im.crop(box).resize(((x1 - x0) * k, (y1 - y0) * k), Image.BICUBIC)
    d = ImageDraw.Draw(c)
    for x in range(x0, x1 + 1):
        X = (x - x0) * k
        if x % step == 0:
            d.line([(X, 0), (X, c.height)], fill=(255, 0, 0) if x % major == 0 else (255, 230, 0), width=1)
        if x % major == 0:
            d.text((X + 2, 2), str(x), fill=(255, 255, 255))
    for y in range(y0, y1 + 1):
        Y = (y - y0) * k
        if y % step == 0:
            d.line([(0, Y), (c.width, Y)], fill=(255, 0, 0) if y % major == 0 else (255, 230, 0), width=1)
        if y % major == 0:
            d.text((2, Y + 2), str(y), fill=(255, 255, 255))
    c.save(out)
    return c.size


# ------------------------------------------------------------------------------------------------ manual
def ext_to_poly(ext, lean=0.0, rnd=0.28):
    """Traced extents -> an 8-point outline: the bounding lines x_left .. x_right, y_top .. y_bottom (image px), the
    top edge shifted `lean` px right of the bottom, each corner cut by `rnd` of the shorter extent."""
    xl, xr, yt, yb = ext
    w, h = xr - xl, yb - yt
    c = rnd * min(w, h)
    lt, lb = lean / 2.0, -lean / 2.0

    def sh(x, y):
        f = (yb - y) / max(h, 1e-9)            # 1 at the top, 0 at the bottom
        return (x + lb + (lt - lb) * f, y)
    pts = [(xl + c, yt), (xr - c, yt), (xr, yt + c), (xr, yb - c), (xr - c, yb), (xl + c, yb), (xl, yb - c), (xl, yt + c)]
    return [list(map(lambda v: round(v, 2), sh(x, y))) for x, y in pts]


def seg_intersect(p1, p2, q1, q2):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(q1, q2, p1), o(q1, q2, p2), o(p1, p2, q1), o(p1, p2, q2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def self_intersects(poly):
    n = len(poly)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if seg_intersect(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return True
    return False


def raster(poly, W, H, x0, y0, k=4):
    im = Image.new("L", (W * k, H * k), 0)
    ImageDraw.Draw(im).polygon([((x - x0) * k, (y - y0) * k) for x, y in poly], fill=1)
    return np.asarray(im, dtype=bool)


def validate(tr):
    """No self-intersections, overlaps between stones below 1 px^2 (study 6.8); returns a list of problems."""
    probs = []
    st = tr["stones"]
    for s in st:
        if len(s["poly"]) < 3:
            probs.append(f"stone {s['id']}: fewer than 3 points")
        elif self_intersects(s["poly"]):
            probs.append(f"stone {s['id']}: self-intersecting")
    x0, y0, x1, y1 = tr["crop_box_px"]
    W, H = int(x1 - x0) + 2, int(y1 - y0) + 2
    k = 4
    masks = {s["id"]: raster(s["poly"], W, H, x0, y0, k) for s in st if len(s["poly"]) >= 3}
    ids = list(masks)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            ov = float((masks[ids[i]] & masks[ids[j]]).sum()) / (k * k)
            if ov >= 1.0:
                probs.append(f"stones {ids[i]} / {ids[j]} overlap {ov:.1f} px^2")
    return probs


def expand(path):
    p = Path(path)
    tr = json.loads(p.read_text(encoding="utf-8"))
    for s in tr["stones"]:
        if "ext" in s:
            s["poly"] = ext_to_poly(s["ext"], s.get("lean", 0.0), s.get("round", 0.28))
    src = ROOT / tr["source"]["path"]
    tr["source"]["sha256"] = SM.sha256(src)
    tr["source"]["size_px"] = list(Image.open(src).size)
    tr["tool"] = "Scripts/stone/stone_trace.py"
    tr["tool_git"] = tool_git()
    tr["validation"] = validate(tr)
    p.write_text(json.dumps(tr, indent=1), encoding="utf-8")
    return tr


# ------------------------------------------------------------------------------------------------ seed mode
def box_mean(a, r):
    """Mean over a (2r+1)^2 window (integral image, edge-clamped)."""
    p = np.pad(a, r + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    H, W = a.shape
    n = 2 * r + 1
    s = c[n:n + H, n:n + W] - c[0:H, n:n + W] - c[n:n + H, 0:W] + c[0:H, 0:W]
    return s / (n * n)


def chamfer(mask_fg):
    """Two-pass 3-4 chamfer distance (px) from the background (False) for the True pixels."""
    H, W = mask_fg.shape
    INF = 10 ** 9
    d = np.where(mask_fg, INF, 0).astype(np.int64)
    for y in range(H):
        for x in range(W):
            if d[y, x] == 0:
                continue
            v = d[y, x]
            if x > 0:
                v = min(v, d[y, x - 1] + 3)
            if y > 0:
                v = min(v, d[y - 1, x] + 3)
                if x > 0:
                    v = min(v, d[y - 1, x - 1] + 4)
                if x < W - 1:
                    v = min(v, d[y - 1, x + 1] + 4)
            d[y, x] = v
    for y in range(H - 1, -1, -1):
        for x in range(W - 1, -1, -1):
            if d[y, x] == 0:
                continue
            v = d[y, x]
            if x < W - 1:
                v = min(v, d[y, x + 1] + 3)
            if y < H - 1:
                v = min(v, d[y + 1, x] + 3)
                if x < W - 1:
                    v = min(v, d[y + 1, x + 1] + 4)
                if x > 0:
                    v = min(v, d[y + 1, x - 1] + 4)
            d[y, x] = v
    return d / 3.0


def seed_trace(png, box, k=3, kd=0.72, win=6, min_seed=2.2, supp=3.5, min_px=20.0):
    """Seeded segmentation of a crop (source px box). k: working upscale. Returns stones [{poly, area_px}], the
    dark-joint fraction and the joint mask."""
    im = Image.open(png).convert("RGB")
    x0, y0, x1, y1 = box
    c = im.crop(box)
    c = c.resize((c.width * k, c.height * k), Image.BICUBIC)
    rgb = np.asarray(c, dtype=np.float64) / 255.0
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    loc = box_mean(luma, int(win * k))
    dark = luma < kd * loc
    h, s, v = SM.rgb_to_hsv(rgb)
    moss = (h >= 45) & (h <= 90) & (s >= 0.30)
    fg = ~dark & ~moss
    dist = chamfer(fg) / k                                    # source px
    H, W = dist.shape
    R = int(supp * k)
    seeds = []
    order = np.argsort(-dist.ravel())
    taken = np.zeros_like(fg)
    for idx in order:
        y, x = divmod(int(idx), W)
        if dist[y, x] < min_seed:
            break
        if taken[y, x]:
            continue
        seeds.append((y, x))
        taken[max(0, y - R):y + R + 1, max(0, x - R):x + R + 1] = True
    lab = np.zeros((H, W), np.int32)
    pq = []
    for i, (y, x) in enumerate(seeds, 1):
        lab[y, x] = i
        heapq.heappush(pq, (-dist[y, x], y, x))
    while pq:
        _, y, x = heapq.heappop(pq)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and lab[yy, xx] == 0 and fg[yy, xx]:
                lab[yy, xx] = lab[y, x]
                heapq.heappush(pq, (-dist[yy, xx], yy, xx))
    stones = []
    for i in range(1, len(seeds) + 1):
        ys, xs = np.nonzero(lab == i)
        area = len(xs) / (k * k)
        if area < min_px:
            continue
        pts = [(x0 + (x + 0.5) / k, y0 + (y + 0.5) / k) for x, y in zip(xs, ys)]
        hp = SM.hull(pts)
        cut = bool(xs.min() <= 1 or ys.min() <= 1 or xs.max() >= W - 2 or ys.max() >= H - 2)
        stones.append({"poly": [[round(a, 2), round(b, 2)] for a, b in hp], "area_px": round(area, 1),
                       "cut_by_crop": cut})
    return stones, float(dark.mean()), dark


# ------------------------------------------------------------------------------------------------ overlay
def overlay(tr, out, k=8):
    src = ROOT / tr["source"]["path"]
    im = Image.open(src).convert("RGB")
    x0, y0, x1, y1 = [int(v) for v in tr["crop_box_px"]]
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    col = {"cap": (0, 200, 255), "body": (255, 60, 40)}
    for s in tr["stones"]:
        pts = [((x - x0) * k, (y - y0) * k) for x, y in s["poly"]]
        cc = col.get(s["zone"], (255, 255, 0))
        if s.get("conf") == "guess" or s.get("cut_by_crop"):
            cc = (200, 200, 200)
        d.line(pts + [pts[0]], fill=cc, width=2)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        d.text((cx - 6, cy - 6), str(s["id"]), fill=(255, 255, 255))
    c.save(out)
    return c.size


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("grid")
    g.add_argument("png")
    g.add_argument("--box", nargs=4, type=int, required=True)
    g.add_argument("--k", type=int, default=20)
    g.add_argument("--out", required=True)
    e = sp.add_parser("expand")
    e.add_argument("json")
    s = sp.add_parser("seed")
    s.add_argument("png")
    s.add_argument("--box", nargs=4, type=int, required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--px-per-m", type=float, default=0.0)
    s.add_argument("--unc", type=float, default=0.0)
    o = sp.add_parser("overlay")
    o.add_argument("json")
    o.add_argument("--out", required=True)
    o.add_argument("--k", type=int, default=8)
    v = sp.add_parser("validate")
    v.add_argument("json")
    ns = ap.parse_args(argv)
    if ns.cmd == "grid":
        print(grid(ns.png, ns.box, ns.k, ns.out))
    elif ns.cmd == "expand":
        tr = expand(ns.json)
        print(json.dumps({"stones": len(tr["stones"]), "validation": tr["validation"]}, indent=1))
    elif ns.cmd == "seed":
        stones, dark_f, _ = seed_trace(ns.png, ns.box)
        tr = {"schema": SCHEMA, "source": {"path": rel(ns.png), "sha256": SM.sha256(ns.png),
                                           "size_px": list(Image.open(ns.png).size)},
              "crop_box_px": ns.box, "view": "", "scale": {"px_per_m": ns.px_per_m, "uncertainty": ns.unc, "cues": []},
              "resolution": {"stone_px_median": None, "joint_resolved": False, "trace_error_px": 2},
              "method": "seed", "tool": "Scripts/stone/stone_trace.py", "tool_git": tool_git(), "zones": [],
              "stones": [{"id": i + 1, "zone": "body", "poly": st["poly"], "conf": "partial",
                          "cut_by_crop": st["cut_by_crop"], "occluded_by": None, "mode": "seed"}
                         for i, st in enumerate(stones)],
              "packing": [], "joints": {"dark_fraction": round(dark_f, 4), "fwhm_px": None}, "notes": ""}
        Path(ns.out).write_text(json.dumps(tr, indent=1), encoding="utf-8")
        print(len(stones), "stones; dark fraction", round(dark_f, 3))
    elif ns.cmd == "overlay":
        tr = json.loads(Path(ns.json).read_text(encoding="utf-8"))
        print(overlay(tr, ns.out, ns.k))
    else:
        tr = json.loads(Path(ns.json).read_text(encoding="utf-8"))
        print(json.dumps(validate(tr), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
