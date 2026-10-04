"""t7: the skirt (taiko_skirt.py, design units) seen from the photo's fitted camera (photo_cam.py), BEFORE the Blender
build: (1) its traced hem drawn back over the photo, (2) the drum's outline per row through the skirt rows (the
lathe + tacks + skirts rasterised) against the photo's outline, per side. System Python + numpy + Pillow.
Usage: py check_skirt_t7.py [--scripts DIR] [--png out.png]"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

T7 = Path(__file__).resolve().parent
sys.path.insert(0, str(T7))
SCR = Path(sys.argv[sys.argv.index("--scripts") + 1]) if "--scripts" in sys.argv else Path(
    "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/props/taiko")
sys.path.insert(0, str(SCR))
import photo_cam as PC  # noqa: E402
import taiko_uv as UVL  # noqa: E402
import taiko_skirt as SK  # noqa: E402

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
D = UVL.D_SHIFT
LIP_XC, LIP_RC, LIP_RHO = 0.758 - D, 0.528, 0.019
X_TACK, TACK_DX, TACK_R, TACK_H = 0.5835, 0.028894, 0.020767, 0.017488
SK.A_LOW_MAX = UVL.X_SK - (0.450 + 0.0035) / UVL.DRUM_SCALE - 0.5 * SK.SK_T - 0.001


def lathe_outline_pts(side_th):
    """dense points of the drum's surface of revolution (body, collar, tack band envelope, lip) near the
    silhouette angles"""
    xs = list(np.linspace(-UVL.X_SK, UVL.X_SK, 160))
    rs = [UVL.body_r(abs(x)) + (SK.COLLAR_T if abs(x) > UVL.X_SK - 1e-9 else 0.0) for x in xs]
    for sgn in (-1, 1):
        for x in np.linspace(UVL.X_SK, LIP_XC, 60):
            r = UVL.body_r(x) + SK.COLLAR_T
            for row in (0, 1):
                xr = X_TACK + (row - 0.5) * TACK_DX
                if abs(x - xr) < TACK_R:
                    r = max(r, UVL.body_r(xr) + SK.COLLAR_T + TACK_H * math.sqrt(max(0.0, 1 - ((x - xr) / TACK_R) ** 2)))
            xs.append(sgn * x)
            rs.append(r)
        for a in np.linspace(0, math.pi * 0.8, 30):
            xs.append(sgn * (LIP_XC + LIP_RHO * math.sin(a)))
            rs.append(LIP_RC + LIP_RHO * math.cos(a))
    th = np.radians(np.linspace(side_th - 25, side_th + 25, 101))
    P = np.array([[x, r * math.cos(t), r * math.sin(t)] for x, r in zip(xs, rs) for t in th])
    return P


def raster_mask(polys, size=(1024, 1024)):
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([tuple(q) for q in p], fill=255)
    return np.asarray(im) > 0


def main():
    ref = Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")
    tr = json.loads((SCR / "skirt_trace_t7.json").read_text(encoding="utf-8"))
    polys, hems, infos = [], {}, {}
    for s in (1, -1):
        v, f, _uv, info = SK.mesh(s)
        infos[s] = info
        P = PC.project_design(np.array(v))
        polys += [P[list(q)] for q in f]
        V = np.array(v)
        hems[s] = (V, P)
    mask = raster_mask(polys)
    # the lathe outline points near both silhouettes, as tiny discs
    lp = np.vstack([lathe_outline_pts(-84), lathe_outline_pts(84)])
    q = PC.project_design(lp)
    lim = Image.fromarray((mask * 255).astype(np.uint8))
    d = ImageDraw.Draw(lim)
    for u, v_ in q:
        d.rectangle((u - 0.7, v_ - 0.7, u + 0.7, v_ + 0.7), fill=255)
    full = np.asarray(lim) > 0
    res = {"rows": {}}
    for key, rows in (("upper", range(180, 335)), ("lower", range(680, 830))):
        for side in ("left", "right"):
            ph = dict((int(vv), uu) for vv, uu in tr["silhouette_rows_v_u"][f"{key}_{side}"])
            diffs = []
            for vv in rows:
                xs = np.where(full[vv])[0]
                if not len(xs) or vv not in ph:
                    continue
                ours = xs.min() - 0.5 if side == "left" else xs.max() + 0.5
                dd = (ph[vv] - ours) if side == "left" else (ours - ph[vv])   # + = ours further out
                diffs.append((vv, round(float(ours), 1), ph[vv], round(float(dd), 1)))
            res["rows"][f"{key}_{side}"] = diffs
    # overlay
    ov = ref.copy()
    od = ImageDraw.Draw(ov, "RGBA")
    edge = full & ~(np.roll(full, 1, 0) & np.roll(full, -1, 0) & np.roll(full, 1, 1) & np.roll(full, -1, 1))
    for vv, uu in zip(*np.nonzero(edge)):
        od.point((uu, vv), fill=(255, 0, 0, 255))
    for s in (1, -1):
        V, P = hems[s]
    out = Path(sys.argv[sys.argv.index("--png") + 1]) if "--png" in sys.argv else T7 / "check_skirt.png"
    # the skirt mask tinted
    tint = Image.new("RGBA", ref.size, (0, 0, 0, 0))
    tm = np.zeros((1024, 1024, 4), np.uint8)
    tm[mask] = (0, 120, 255, 70)
    ov = Image.alpha_composite(ov.convert("RGBA"), Image.fromarray(tm)).convert("RGB")
    ov.save(out)
    for k, v_ in res["rows"].items():
        dd = [x[3] for x in v_]
        print(k, "ours - photo (+ = ours further out) min/max", min(dd), max(dd))
        print("   ", [(x[0], x[3]) for x in v_[::6]])
    for s in (1, -1):
        print(s, json.dumps(infos[s]))
    (T7 / "check_skirt.json").write_text(json.dumps({"rows": res["rows"], "info": {str(k): v_ for k, v_ in infos.items()}},
                                                     indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
