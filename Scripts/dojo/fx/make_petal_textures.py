"""Paint the Yoshino petal texture sets (plain Python 3: numpy + PIL). No reference pixel is copied.

Outline: the traced mean outline of the sheet's flat petals (petal_outline.json from measure_petal_ref.py --outline).
Colour: the sheet's measured bands (petal_ref_measure.json) converted to albedo by the grey-card ratio
(albedo = lin(petal) / lin(card) * 0.18, per channel, so the card's warm cast is neutralised), then painted with our
own veins, claw, speckle and rim and renormalised row by row so every band's mean hits its target.

Outputs (Exports/DojoKit/FX/Textures, 1024 px):
  T_DKF_Petal_BC      sRGB, RGB front colour, A opacity (masked)
  T_DKF_PetalBack_BC  sRGB, RGB back colour (same UVs; TwoSidedSign lerp in the material), A opacity
  T_DKF_Petal_N       linear, DirectX tangent normal (veins, ribbing, cell crinkle)
  T_DKF_Petal_ORM     linear, R AO, G roughness, B metal 0
  T_DKF_Petal_SSS     linear, white = thin (transmits), claw and veins thicker
  T_DKF_PetalOld_*    browned old petal: BC (A = ragged shrunken opacity), N (crumpled), ORM, SSS

    py -3 -B Scripts/dojo/fx/make_petal_textures.py [--size 1024]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402

CARD_ALBEDO = 0.18
NOTCH_GAIN = 1.25
# rendered upper/tip bands read ~5 % under the sheet (cup shading at the rim): lift their targets to match
BAND_GAIN = {"claw": 1.0, "lower": 1.0, "middle": 1.02, "upper": 1.05, "tip": 1.07}
BAND_Y = {"claw": 0.06, "lower": 0.21, "middle": 0.50, "upper": 0.75, "tip": 0.91}


# --------------------------------------------------------------------------- outline

def load_outline():
    rec = fx.load_json(fx.WORK / "ref/petal_outline.json")
    y = np.array(rec["y"])
    hw = np.convolve(np.pad(np.array(rec["half_width"]), 3, mode="edge"), np.ones(7) / 7, mode="valid")
    top = np.array(rec["top_contour_right"])
    tx, ty = top[:, 0], top[:, 1]
    valid = ty > 0.05
    tx, ty = tx[valid], ty[valid]
    ty = np.convolve(np.pad(ty, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    # the mean of 16 silhouettes blurs the V: restore the sheet's measured notch depth (0.075 L, per-petal mean)
    lobe = ty.max()
    notch_zone = tx < tx[np.argmax(ty)]
    ty = np.where(notch_zone, lobe - (lobe - ty) * NOTCH_GAIN, ty)
    return y, hw, tx, ty


def half_width_at(y, outline):
    oy, hw, _tx, _ty = outline
    return np.interp(y, oy, hw, left=0.0, right=0.0)


def top_at(x, outline):
    _oy, _hw, tx, ty = outline
    return np.interp(np.abs(x), tx, ty, left=ty[0], right=0.0)


def inside(x, y, outline, scale=1.0, ragged=None):
    xs, ys = x / scale, y / scale
    ok = (ys >= 0) & (np.abs(xs) <= half_width_at(ys, outline)) & (ys <= top_at(xs, outline))
    if ragged is not None:
        ok = ok & ragged
    return ok


# --------------------------------------------------------------------------- veins

def vein_polylines(outline, rng, n_primary=15, old=False):
    """Fan of primaries from the claw to the rim, each with 1-2 forks; returns [(points(N,2), width, strength)]."""
    oy, hw, tx, ty = outline
    # rim points: left side y 0.28 -> top -> right side
    rim = []
    for yy in np.linspace(0.28, 0.9, 12):
        rim.append((-half_width_at(yy, outline), yy))
    for xx in np.linspace(-0.3, 0.3, 13):
        rim.append((xx, top_at(xx, outline)))
    for yy in np.linspace(0.9, 0.28, 12):
        rim.append((half_width_at(yy, outline), yy))
    rim = np.array(rim)
    seg = np.linalg.norm(np.diff(rim, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    s /= s[-1]
    lines = []
    base = np.array([0.0, 0.015])
    ts = np.linspace(0.04, 0.96, n_primary) + rng.uniform(-0.02, 0.02, n_primary)
    for i, t in enumerate(ts):
        end = np.array([np.interp(t, s, rim[:, 0]), np.interp(t, s, rim[:, 1])]) * 0.95
        ctrl = np.array([end[0] * 0.2, 0.45 * end[1] + 0.05])
        tt = np.linspace(0, 1, 40)[:, None]
        pts = (1 - tt) ** 2 * base + 2 * (1 - tt) * tt * ctrl + tt ** 2 * end
        wig = np.cumsum(rng.normal(0, 0.0018, (40, 2)), axis=0)
        wig -= tt * wig[-1]
        pts = pts + wig
        central = abs(t - 0.5) < 0.06
        width = 0.0042 if central else 0.0028
        lines.append((pts, width, 1.0 if central else 0.8))
        # forks
        for _ in range(rng.integers(1, 3)):
            k = int(rng.uniform(0.35, 0.65) * 40)
            t2 = np.clip(t + rng.choice([-1, 1]) * rng.uniform(0.02, 0.05), 0.0, 1.0)
            end2 = np.array([np.interp(t2, s, rim[:, 0]), np.interp(t2, s, rim[:, 1])]) * 0.96
            p0 = pts[k]
            tt2 = np.linspace(0, 1, 24)[:, None]
            c2 = p0 + (end2 - p0) * 0.35 + (pts[min(k + 5, 39)] - p0) * 0.8
            q = (1 - tt2) ** 2 * p0 + 2 * (1 - tt2) * tt2 * c2 + tt2 ** 2 * end2
            lines.append((q, 0.0020, 0.55))
    return lines


def vein_field(lines, size, px_per_unit, origin_uv):
    """Max over veins of a gaussian ridge (distance in texture px); also the along-vein param for fading."""
    field = np.zeros((size, size))
    fade = np.zeros((size, size))
    for pts, width, strength in lines:
        u, v = fx.petal_to_uv(pts[:, 0], pts[:, 1])
        px = np.stack([u * size, (1 - v) * size], axis=1)
        wpx = max(0.8, width * px_per_unit)
        total = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
        total /= max(total[-1], 1e-9)
        for a in range(len(px) - 1):
            p0, p1 = px[a], px[a + 1]
            # taper: veins thin toward the rim
            w = wpx * (1.0 - 0.55 * total[a])
            pad = int(w * 3 + 2)
            x0, x1 = int(max(0, min(p0[0], p1[0]) - pad)), int(min(size, max(p0[0], p1[0]) + pad + 1))
            y0, y1 = int(max(0, min(p0[1], p1[1]) - pad)), int(min(size, max(p0[1], p1[1]) + pad + 1))
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
            d = p1 - p0
            ll = max(float(d @ d), 1e-9)
            t = np.clip(((xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]) / ll, 0, 1)
            dist = np.hypot(xx - (p0[0] + t * d[0]), yy - (p0[1] + t * d[1]))
            val = strength * np.exp(-(dist / w) ** 2)
            sub = field[y0:y1, x0:x1]
            upd = val > sub
            sub[upd] = val[upd]
            fsub = fade[y0:y1, x0:x1]
            fsub[upd] = (total[a] + t * (total[a + 1] - total[a]))[upd]
    return field, fade


# --------------------------------------------------------------------------- targets

def band_targets():
    m = fx.load_json(fx.WORK / "ref/petal_ref_measure.json")
    from PIL import Image
    ref = np.asarray(Image.open(fx.PETAL_REF).convert("RGB")).astype(np.float64) / 255.0
    card = np.median(ref[180:224, 16:40].reshape(-1, 3), axis=0)  # the grey card under petal 1
    card_lin = fx.srgb_to_lin(card)
    out = {}
    for side, key in (("front", "front_bands_mean"), ("back", "back_bands_mean")):
        bands = m["summary"][key]
        out[side] = {b: fx.srgb_to_lin(np.array(bands[b]) / 255.0) / card_lin * CARD_ALBEDO * BAND_GAIN[b] for b in BAND_Y}
    return out, card


def target_rows(targets, ys):
    names = list(BAND_Y)
    yk = np.array([BAND_Y[n] for n in names])
    cols = np.array([targets[n] for n in names])
    return np.stack([np.interp(ys, yk, cols[:, c]) for c in range(3)], axis=-1)


def renormalise_rows(col, alpha, ys_rows, target):
    """Scale each row so its alpha-weighted mean equals the target row colour (smoothed along y)."""
    w = alpha[..., None]
    mean = (col * w).sum(axis=1) / np.maximum(w.sum(axis=1), 1e-6)
    ratio = np.where(alpha.sum(axis=1)[:, None] > 2, target / np.maximum(mean, 1e-6), 1.0)
    k = np.ones(25) / 25
    ratio = np.stack([np.convolve(np.pad(ratio[:, c], 12, mode="edge"), k, mode="valid") for c in range(3)], axis=-1)
    return col * ratio[:, None, :]


# --------------------------------------------------------------------------- painter

def paint(size=1024, seed=7, old=False):
    rng = np.random.default_rng(seed + (50 if old else 0))
    outline = load_outline()
    ss = 2
    n2 = size * ss
    uu = (np.arange(n2) + 0.5) / n2
    U, V = np.meshgrid(uu, 1 - uu)
    X, Y = fx.uv_to_petal(U, V)
    ragged = None
    scale = 1.0
    if old:
        scale = 0.9
        edge_noise = fx.fbm(n2, 18, 3, seed + 9)
        # shrink + tears: pull the outline in by up to 5 % of the length where the noise is high
        hw = half_width_at(Y / scale, outline)
        rim_dist = np.minimum(hw - np.abs(X / scale), top_at(X / scale, outline) - Y / scale)
        ragged = rim_dist > 0.018 + 0.03 * np.clip(edge_noise, 0, None)
    m2 = inside(X, Y, outline, scale, ragged).astype(np.float64)
    alpha = m2.reshape(size, ss, size, ss).mean(axis=(1, 3))
    Xs, Ys = X[::ss, ::ss], Y[::ss, ::ss]
    ys_rows = Ys[:, 0] / scale
    px_per_unit = fx.UV_SCALE * size

    lines = vein_polylines(outline, rng)
    if old:
        lines = [(p * scale, w, s) for p, w, s in lines]
    vein, vfade = vein_field(lines, size, px_per_unit, 0)
    vein_front = vein * (1 - 0.65 * vfade)  # pink veins fade toward the rim

    # fine reticulate veinlets / cell crinkle (noise ridges)
    cell = fx.fbm(size, 60, 3, seed + 3, aniso=(2.2, 1.0))
    ridge = 1 - np.abs(fx.fbm(size, 22, 3, seed + 4, aniso=(2.8, 1.0)))
    ridge = np.clip((ridge - 0.55) / 0.45, 0, 1)
    speck = fx.fbm(size, 160, 2, seed + 5)

    yy = Ys / scale
    xx = Xs / scale
    hw = np.maximum(half_width_at(yy, outline), 1e-3)
    rim_dist = np.clip(np.minimum(hw - np.abs(xx), top_at(xx, outline) - yy), 0, None)
    rim = 1 - fx.smoothstep(0.0, 0.035, rim_dist)

    targets, card = band_targets()
    result = {}
    if not old:
        # claw: strong pink at the base, concentrated on the midline and along the lower veins
        claw = np.exp(-np.clip(yy, 0, None) / 0.05) * np.exp(-(xx / (0.04 + 0.3 * yy)) ** 2)
        claw = np.clip(claw + vein_front * np.exp(-yy / 0.22) * 1.1, 0, 1)
        for side in ("front", "back"):
            t = targets[side]
            pale = target_rows({k: t[k] for k in BAND_Y}, np.clip(yy, 0, 1))
            pink = np.array([0.80, 0.22, 0.36]) if side == "front" else np.array([0.72, 0.42, 0.47])
            ca = claw * (1.0 if side == "front" else 0.45)
            col = pale * (1 - ca[..., None]) + pink * ca[..., None]
            if side == "front":
                vc = vein_front * (1 - np.exp(-yy / 0.32))
                col = col * (1 - 0.62 * vc[..., None]) + np.array([0.70, 0.30, 0.42]) * 0.62 * vc[..., None]
            else:
                col = col * (1 + 0.30 * vein[..., None] * np.array([1.0, 1.04, 1.03]))
                col = col * (1 - 0.20 * ridge[..., None])
            col = col * (1 + 0.035 * cell[..., None] + 0.02 * speck[..., None])
            col = col * (1 + 0.06 * rim[..., None])  # the thin rim reads whiter
            # tiny ochre point at the very base (stalk scar)
            stalk = np.exp(-((xx / 0.02) ** 2 + (np.clip(yy, 0, None) / 0.022) ** 2))
            col = col * (1 - stalk[..., None]) + np.array([0.62, 0.52, 0.30]) * stalk[..., None]
            rows_target = target_rows(t, np.clip(ys_rows, 0, 1))
            col = renormalise_rows(col, alpha, ys_rows, rows_target)
            result[side] = np.clip(col, 0, 0.92)
    else:
        blot = fx.fbm(size, 7, 4, seed + 21)
        tan = np.array(fx.srgb_to_lin(np.array([158, 116, 84]) / 255.0))
        dark = np.array(fx.srgb_to_lin(np.array([108, 66, 44]) / 255.0))
        pinkish = np.array(fx.srgb_to_lin(np.array([190, 150, 138]) / 255.0))
        w_dark = np.clip(0.35 * rim + 0.35 * vein + 0.25 * np.clip(blot, 0, None), 0, 1)
        w_pink = np.clip(-blot * 0.25, 0, 0.2) * (1 - rim)
        col = tan * (1 - w_dark[..., None] - w_pink[..., None]) + dark * w_dark[..., None] + pinkish * w_pink[..., None]
        col = col * (1 + 0.06 * cell[..., None] + 0.04 * speck[..., None])
        result["front"] = np.clip(col, 0, 0.9)

    # height -> normal
    if not old:
        h = -0.9 * vein * (1 - 0.5 * vfade) + 0.30 * ridge + 0.10 * cell + 0.02 * speck
        strength = 0.0020
    else:
        crumple = np.abs(fx.fbm(size, 9, 4, seed + 31))
        h = -1.2 * crumple + 0.5 * ridge - 0.5 * vein + 0.05 * speck
        strength = 0.0022
    h = h * (alpha > 0.01)
    nrm = fx.height_to_normal_dx(h, strength)
    ao = np.clip(1 - 0.08 * vein - (0.12 * np.clip(-h, 0, None) if old else 0.0), 0.75, 1)
    rough = np.clip((0.52 if not old else 0.78) + 0.05 * cell + 0.04 * speck, 0.3, 0.95)
    orm = np.stack([ao, rough, np.zeros_like(ao)], axis=-1)
    if not old:
        claw_t = np.exp(-np.clip(yy, 0, None) / 0.12)
        sss = np.clip(0.88 - 0.5 * claw_t - 0.12 * vein + 0.08 * rim, 0.25, 1.0)
    else:
        sss = np.clip(0.45 - 0.15 * vein + 0.05 * rim, 0.1, 1.0)
    return alpha, result, nrm, orm, sss, targets, card


def write_set(prefix, alpha, colours, nrm, orm, sss, size):
    files = {}
    a = alpha
    for side, col in colours.items():
        name = f"T_DKF_{prefix}_BC" if side == "front" else f"T_DKF_{prefix}Back_BC"
        rgb = fx.dilate_rgb(fx.lin_to_srgb(col), a, iters=40)
        files[name] = fx.save_png(np.dstack([rgb, a]), fx.TEX / f"{name}.png")
    files[f"T_DKF_{prefix}_N"] = fx.save_png(nrm, fx.TEX / f"T_DKF_{prefix}_N.png")
    files[f"T_DKF_{prefix}_ORM"] = fx.save_png(orm, fx.TEX / f"T_DKF_{prefix}_ORM.png")
    files[f"T_DKF_{prefix}_SSS"] = fx.save_png(sss * (a > 0.01) + 0.0, fx.TEX / f"T_DKF_{prefix}_SSS.png")
    return files


def band_means(col_lin, alpha, ys_rows):
    out = {}
    for name, (fa, fb) in {"claw": (0.0, 0.12), "lower": (0.12, 0.3), "middle": (0.4, 0.6),
                           "upper": (0.65, 0.85), "tip": (0.85, 0.97)}.items():
        rows = (ys_rows >= fa) & (ys_rows < fb)
        w = alpha[rows][..., None]
        out[name] = [round(float(v), 4) for v in ((col_lin[rows] * w).sum(axis=(0, 1)) / w.sum())]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    a = ap.parse_args()
    size = a.size
    alpha, cols, nrm, orm, sss, targets, card = paint(size)
    files = write_set("Petal", alpha, cols, nrm, orm, sss, size)
    ys_rows = fx.uv_to_petal(0.5, 1 - (np.arange(size) + 0.5) / size)[1]
    report = {"size": size, "card_srgb": [round(float(c) * 255, 1) for c in card], "card_albedo_assumed": CARD_ALBEDO,
              "targets_albedo_lin": {s: {b: [round(float(x), 4) for x in v] for b, v in t.items()} for s, t in targets.items()},
              "painted_band_means_lin": {s: band_means(c, alpha, ys_rows) for s, c in cols.items()},
              "opacity_coverage": round(float(alpha.mean()), 4)}
    alpha_o, cols_o, nrm_o, orm_o, sss_o, _t, _c = paint(size, old=True)
    files.update(write_set("PetalOld", alpha_o, cols_o, nrm_o, orm_o, sss_o, size))
    report["old_opacity_coverage"] = round(float(alpha_o.mean()), 4)
    report["files"] = files
    fx.write_json(fx.WORK / "petal_textures.json", report)
    print(report["painted_band_means_lin"], report["targets_albedo_lin"]["front"]["middle"])


if __name__ == "__main__":
    main()
