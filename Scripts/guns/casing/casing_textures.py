"""T_Casing_762x39_BC / _ORM / _N (DirectX): painted in the LOD0 profile layout (plain numpy, no bpy).

UV0 is the revolve layout: U = angle around the axis / 360 deg, V = the weighted profile parameter (casing_spec.lod0_v),
so a texture row is one ring of the case (base centre at the bottom, then the base face, rim, groove, body, shoulder,
neck, lip and the bore at the top). Everything is drawn per row from the physical (r, z) of that row.

Finish (spent, lacquered steel case; no headstamp or markings):
- lacquer: dark olive-brown lacquer over steel, semi-gloss (metallic 0.85, roughness ~0.33), faint mottling and a few
  longitudinal chamber scuffs;
- Berdan primer (5.50 mm) brass-copper cup with a struck dimple (geometry), the pocket seam and a red sealant ring;
- extractor bite on the rim front cone and an ejector scuff on the head (bare steel);
- spent: carbon soot on the shoulder and neck, uneven around the case (gas blow-back), rubbed steel lip, black bore.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

from casing_spec import CIP, EXTRA, lod0_v, profile_lod0, row_lookup, seg_len

RES = 512
SRGB = {
    "lacquer": (0.30, 0.295, 0.20),
    "primer": (0.70, 0.52, 0.34),
    "primer_dimple": (0.62, 0.45, 0.29),
    "seam": (0.11, 0.095, 0.08),
    "sealant": (0.47, 0.10, 0.13),
    "steel": (0.50, 0.49, 0.47),
    "soot": (0.115, 0.11, 0.105),
    "lip": (0.36, 0.35, 0.33),
    "bore": (0.055, 0.053, 0.05),
}
# (roughness, metallic) per finish
RM = {"lacquer": (0.26, 0.9), "primer": (0.34, 1.0), "primer_dimple": (0.30, 1.0), "seam": (0.6, 0.6),
      "sealant": (0.42, 0.0), "steel": (0.27, 1.0), "soot": (0.78, 0.15), "lip": (0.45, 0.8), "bore": (0.92, 0.0)}


def _noise(shape, sig_u, sig_v, seed):
    """Periodic smooth noise in [-1, 1] (Gaussian-filtered white noise; wraps in U, so no seam)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal(shape)
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    g = np.exp(-2.0 * (math.pi ** 2) * ((fx * sig_u) ** 2 + (fy * sig_v) ** 2))
    n = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    n -= n.mean()
    return n / (np.abs(n).max() + 1e-12)


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def paint(res: int = RES) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
    prof = profile_lod0()
    vs = lod0_v()
    H = W = res
    v = (np.arange(H) + 0.5) / H
    u = (np.arange(W) + 0.5) / W
    theta = 2.0 * math.pi * u                                            # radians, per column
    seg = np.zeros(H, int)
    R = np.zeros(H)
    Z = np.zeros(H)
    dLdv = np.zeros(H)
    for i, vv in enumerate(v):
        s, t, r, z = row_lookup(vv)
        seg[i], R[i], Z[i] = s, r, z
        dv = vs[s + 1] - vs[s]
        dLdv[i] = seg_len(prof[s], prof[s + 1]) / dv if dv > 0 else 0.0
    Rg = R[:, None] * np.ones((1, W))
    Zg = Z[:, None] * np.ones((1, W))
    Sg = seg[:, None] * np.ones((1, W), int)
    Tg = theta[None, :] * np.ones((H, 1))

    def fill(name):
        return np.array(SRGB[name], float)

    col = np.zeros((H, W, 3))
    rough = np.zeros((H, W))
    metal = np.zeros((H, W))
    ao = np.ones((H, W))
    height = np.zeros((H, W))                                            # mm, for the normal map

    def put(mask, name, alpha=1.0):
        a = (np.asarray(alpha, float) * mask)[..., None] if np.ndim(alpha) else (mask * alpha)[..., None]
        col[:] = col * (1 - a) + fill(name) * a
        r_, m_ = RM[name]
        rough[:] = rough * (1 - a[..., 0]) + r_ * a[..., 0]
        metal[:] = metal * (1 - a[..., 0]) + m_ * a[..., 0]

    # ------------------------------------------------------------------ lacquer everywhere on the outside first
    mott = _noise((H, W), 10.0, 6.0, 11) * 0.5 + _noise((H, W), 3.0, 2.0, 12) * 0.5
    put(np.ones((H, W), bool), "lacquer")
    col *= (1.0 + 0.05 * mott)[..., None]
    rough += 0.035 * _noise((H, W), 6.0, 4.0, 13)

    # ------------------------------------------------------------------ head: primer, seam, sealant (base face rows)
    head = (Sg <= 1)
    rp = EXTRA["primer_d"] / 2.0
    sw, slw = EXTRA["seam_w"], EXTRA["sealant_w"]
    put(head & (Rg < rp), "primer")
    put(head & (Rg < EXTRA["dimple_d"] / 2.0), "primer_dimple")
    seam = head & (Rg >= rp) & (Rg < rp + sw)
    put(seam, "seam")
    seal_n = 0.75 + 0.25 * _noise((H, W), 4.0, 1.0, 21)
    put(head & (Rg >= rp + sw) & (Rg < rp + sw + slw), "sealant", np.clip(seal_n, 0, 1))
    xc = (Rg - (rp + sw / 2.0)) / (sw / 2.0)
    height += np.where(seam, -0.05 * 0.5 * (1 + np.cos(np.clip(xc, -1, 1) * math.pi)), 0.0)
    height += np.where(head & (Rg >= rp + sw) & (Rg < rp + sw + slw), 0.008, 0.0)
    ao = np.where(seam, 0.55, ao)
    ao = np.where(head & (Rg < EXTRA["dimple_d"] / 2.0), 0.82, ao)
    # ejector scuff on the head face (bare steel, 0.9 x 0.5 mm, at 150 deg, r 4.4)
    ex, ey = 4.4 * math.cos(math.radians(150)), 4.4 * math.sin(math.radians(150))
    px, py = Rg * np.cos(Tg), Rg * np.sin(Tg)
    ej = head & (((px - ex) / 0.45) ** 2 + ((py - ey) / 0.25) ** 2 < 1.0) & (Rg > rp + sw + slw)
    put(ej, "steel", 0.85)
    height += np.where(ej, -0.015, 0.0)

    # ------------------------------------------------------------------ rim / groove
    rim_edge = (Sg == 2) | (Sg == 3)                                   # chamfer + rim band
    wear = _noise((H, W), 2.0, 1.0, 31)
    put(rim_edge & (wear > 0.7), "steel", 0.45)
    dth = np.abs(((Tg - math.radians(0.0)) + math.pi) % (2 * math.pi) - math.pi)
    # extractor claw bite: a short bright scratch on the outer half of the rim front cone
    bite = (Sg == 4) & (dth < math.radians(4.0)) & (Rg > 5.2)
    put(bite, "steel", 0.6 * (1.0 - dth / math.radians(4.0)))
    height += np.where(bite & (Sg == 4), -0.02, 0.0)
    ao = np.where(Sg == 5, 0.62, ao)                                    # groove floor
    ao = np.where((Sg == 4) | (Sg == 6), 0.8, ao)

    # ------------------------------------------------------------------ body: chamber scuffs (thin, low contrast)
    rng = np.random.default_rng(41)
    body = (Sg == 7)
    for th in rng.uniform(0, 2 * math.pi, 5):
        d = np.abs(((Tg - th) + math.pi) % (2 * math.pi) - math.pi) * Rg      # mm across
        z0 = rng.uniform(6, 16)
        z1 = z0 + rng.uniform(4, 10)
        line = body & (d < 0.05) & (Zg > z0) & (Zg < z1)
        fade = np.clip(np.minimum(Zg - z0, z1 - Zg) / 2.0, 0, 1)
        put(line, "steel", 0.1 * fade)

    # ------------------------------------------------------------------ spent: soot on shoulder + neck, lip, bore
    outer = Sg <= 9
    streak = 0.55 + 0.45 * _noise((H, W), 9.0, 40.0, 51)                # uneven around the case, streaky along it
    soot = (_smooth(Zg, 25.0, CIP["L3"]) * 0.85 + 0.12 * (Zg > CIP["L2"])) * np.clip(streak, 0.15, 1.0)
    soot *= outer & (Sg >= 7)
    put(np.ones((H, W), bool), "soot", np.clip(soot, 0, 0.92))
    put(Sg == 10, "lip")
    bore = Sg == 11
    put(bore, "bore")
    ao = np.where(bore, 0.25 - 0.15 * np.clip((CIP["L3"] - Zg) / 6.0, 0, 1), ao)
    ao = np.where(Sg == 10, 0.85, ao)

    col = np.clip(col, 0, 1)
    rough = np.clip(rough, 0.05, 1)
    metal = np.clip(metal, 0, 1)

    # ------------------------------------------------------------------ normal map (DirectX: green = -Y)
    dx = np.maximum(2.0 * math.pi * Rg / W, 0.004)                         # mm per texel along U
    dy = np.maximum(dLdv[:, None] / H, 0.004) * np.ones((1, W))          # mm per texel along V
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / (2 * dx)
    gy = np.zeros_like(height)
    gy[1:-1] = (height[2:] - height[:-2]) / (2 * dy[1:-1])
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    nrm = np.zeros((H, W, 4))
    nrm[..., 0] = n[..., 0] * 0.5 + 0.5
    nrm[..., 1] = -n[..., 1] * 0.5 + 0.5                                  # DirectX
    nrm[..., 2] = n[..., 2] * 0.5 + 0.5
    nrm[..., 3] = 1.0

    bc = np.ones((H, W, 4))
    bc[..., :3] = col
    orm = np.ones((H, W, 4))
    orm[..., 0], orm[..., 1], orm[..., 2] = ao, rough, metal
    info = {"res": res, "srgb": SRGB, "rough_metal": RM,
            "mean_lacquer_srgb": [round(float(x), 3) for x in col[seg == 7].reshape(-1, 3).mean(0)]}
    return bc, orm, nrm, info
