"""t7 (judge r6 item 4): the tack band in the photo's fitted camera, simulated (system Python + numpy + scipy), to pick
the axial row spacing, the collar's radial step under the band and the tack size BEFORE the build. The judge's metric
(judge_r6/tack_rows.py): each tack's visible dark disc -> its inscribed-circle centre (distance-transform peak); the
row-centre spacing over the tack width (the photo 21.5 / 25.4 = 0.85; ours t6 25.3 / 26.2 = 0.97).
The domes are rasterised far-to-near (painter's) at 4x the photo's pixel scale from their exact profile (taiko build
TACK_PROF), seated on the collar profile r = body_r + COLLAR_T + the row-ring offsets, tilted to the local chord.
Also the 3D gap between diagonal neighbours (dense surface samples)."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

T7 = Path(__file__).resolve().parent
sys.path.insert(0, str(T7))
SCR = Path(sys.argv[sys.argv.index("--scripts") + 1]) if "--scripts" in sys.argv else Path(
    "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/props/taiko")
sys.path.insert(0, str(SCR))
import photo_cam as PC  # noqa: E402
import taiko_uv as UVL  # noqa: E402

S = UVL.DRUM_SCALE
COLLAR_T = 0.0045
PROF_T3 = [(0.0, 1.0), (0.40, 0.95), (0.72, 0.74), (0.93, 0.38), (1.00, 0.0)]


def collar_r(x, xt, dx, off0, off1):
    """design collar radius with the t7 row rings (offset off0 at the body-side row, off1 at the head-side row,
    band0 / band2 at xt -+ 0.040 unchanged)"""
    xs = [xt - 0.040, xt - dx / 2, xt + dx / 2, xt + 0.040]
    ofs = [0.0, off0, off1, 0.0]
    base = UVL.body_r(x) + COLLAR_T
    return base + np.interp(x, xs, ofs)


def chord_r(x, xt, dx, off0, off1):
    """the lathe's piecewise-linear profile through the rings (band0, row0, row1, band2)"""
    xs = [xt - 0.040, xt - dx / 2, xt + dx / 2, xt + 0.040]
    rs = [collar_r(q, xt, dx, off0, off1) for q in xs]
    return float(np.interp(x, xs, rs)), xs, rs


def tacks(xt, dx, off0, off1, R, Hh, n_row=81, prof=PROF_T3, sides=48, rings=12, th_win=0.25):
    out = []
    for row in (0, 1):
        xx = xt + (row - 0.5) * dx
        r0, xs, rs = chord_r(xx, xt, dx, off0, off1)
        i = 1 + row
        sl = 0.5 * ((rs[i] - rs[i - 1]) / (xs[i] - xs[i - 1]) + (rs[i + 1] - rs[i]) / (xs[i + 1] - xs[i]))
        for k in range(n_row):
            th = 2 * math.pi * (k + 0.5 * row) / n_row
            th = (th + math.pi) % (2 * math.pi) - math.pi
            if abs(th) > th_win:
                continue
            radial = np.array([0.0, math.cos(th), math.sin(th)])
            seat = np.array([xx, 0, 0]) + radial * r0
            nrm = radial - np.array([sl, 0, 0])
            nrm /= np.linalg.norm(nrm)
            t = np.array([1.0, 0, 0]) - nrm * nrm[0]
            t /= np.linalg.norm(t)
            b = np.cross(nrm, t)
            # dense dome surface: profile interpolated
            pr = np.array(prof)
            rr = np.linspace(0, 1, rings)
            zz = np.interp(rr, pr[:, 0], pr[:, 1])
            a = np.linspace(0, 2 * math.pi, sides, endpoint=False)
            P = (seat[None, None, :] + (rr[:, None, None] * R) * (np.cos(a)[None, :, None] * t + np.sin(a)[None, :, None] * b)
                 + (zz[:, None, None] * Hh) * nrm[None, None, :])
            out.append({"row": row, "th": th, "seat": seat, "n": nrm, "P": P.reshape(-1, 3)})
    return out


def raster(ts, z=4, win=(380, 660, 140, 280)):
    u0, u1, v0, v1 = win
    W, Hh = (u1 - u0) * z, (v1 - v0) * z
    img = Image.new("L", (W, Hh), 0)
    lab = np.zeros((Hh, W), int)
    order = sorted(range(len(ts)), key=lambda i: -float(PC.depth_design(ts[i]["seat"][None])[0]))
    for i in order:
        q = PC.project_design(ts[i]["P"])
        q = (q - np.array([u0, v0])) * z
        from scipy.spatial import ConvexHull
        h = ConvexHull(q)
        poly = [tuple(q[j]) for j in h.vertices]
        m = Image.new("L", (W, Hh), 0)
        ImageDraw.Draw(m).polygon(poly, fill=255)
        mm = np.asarray(m) > 0
        lab[mm] = i + 1
    return lab


def metric(ts, z=4):
    lab = raster(ts, z)
    cents, widths = [], []
    for i, t in enumerate(ts):
        m = lab == i + 1
        if m.sum() < 50:
            continue
        dist = ndi.distance_transform_edt(m)
        yx = np.unravel_index(np.argmax(dist), dist.shape)
        q = PC.project_design(t["P"])
        cents.append((t["row"], yx[0] / z, yx[1] / z, float(q[:, 0].max() - q[:, 0].min())))
    up = [c[1] for c in cents if c[0] == 1]
    lo = [c[1] for c in cents if c[0] == 0]
    wd = np.median([c[3] for c in cents])
    dy = np.mean(lo) - np.mean(up)
    return dy, wd, dy / wd


def diag_gap(ts):
    """min 3D distance between the domes of diagonal neighbours (dense samples, above the hide)"""
    best = 1e9
    r0 = [t for t in ts if t["row"] == 0]
    r1 = [t for t in ts if t["row"] == 1]
    for a in r1:
        for b in sorted(r0, key=lambda q: abs(q["th"] - a["th"]))[:2]:
            d = np.linalg.norm(a["P"][:, None, :] - b["P"][None, :, :], axis=2).min()
            best = min(best, d)
    inrow = 1e9
    for rw in (r0, r1):
        rw = sorted(rw, key=lambda q: q["th"])
        for a, b in zip(rw, rw[1:]):
            inrow = min(inrow, np.linalg.norm(a["P"][:, None, :] - b["P"][None, :, :], axis=2).min())
    return best, inrow


def run(xt, dx, off0, off1, R, Hh, n_row=81):
    ts = tacks(xt, dx, off0, off1, R, Hh, n_row)
    dy, wd, ratio = metric(ts)
    g, gi = diag_gap(tacks(xt, dx, off0, off1, R, Hh, n_row, sides=96, rings=24, th_win=0.12))
    r_rows = [chord_r(xt + (row - 0.5) * dx, xt, dx, off0, off1)[0] for row in (0, 1)]
    return {"xt": xt, "dx_real_mm": round(1000 * S * dx, 2), "radial_step_real_mm": round(1000 * S * (r_rows[0] - r_rows[1]), 2),
            "d_real_mm": round(2000 * S * R, 2), "dy_px": round(dy, 2), "w_px": round(wd, 2), "ratio": round(ratio, 3),
            "diag_gap_real_mm": round(1000 * S * g, 3), "inrow_gap_real_mm": round(1000 * S * gi, 3)}


if __name__ == "__main__":
    XT6 = 0.655 - UVL.D_SHIFT
    R6, H6 = 0.021375, 0.018
    res = {"t6": run(XT6, 0.0355, 0.0, 0.0, R6, H6)}
    print("t6", res["t6"])
    if "--t6-only" in sys.argv:
        sys.exit()
    cands = []
    for dmm in (47.3, 46.0, 45.0):
        R = dmm / 2000 / S
        Hh = H6 * R / R6
        for dx_real in (32.0, 33.0, 34.0, 35.0, 36.3):
            for step in (-6.0, -3.0, 0.0, 3.0):     # extra radial step (real mm) split over the two rows
                o = step / 1000 / S / 2
                r_ = run(XT6, dx_real / 1000 / S, o, -o, R, Hh)
                cands.append(r_)
                print(dmm, dx_real, step, r_)
    res["cands"] = cands
    (T7 / "tack_sim_t7.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
