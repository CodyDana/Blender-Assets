"""Saya texture maps (runs inside Blender; numpy). Every LOD0 face carries parametric attributes (saya_parts: arc
station s, around fraction, extra, part code). They are rasterised into the atlas with the 3D position and every
texel is painted from them:

  lacquer   black roiro gloss (spec #0C0C0D, roughness 0.12) with subtle wear: a faint orange-peel in the normal map,
            gloss dulled (roughness up to ~0.25, a hair lighter) where a hand holds the mouth end, where the obi rubs
            the flats at the kurikata station, along the high ha / mune ridges, and near the kojiri; sparse fine
            hairline scratches (roughness only, mostly lengthwise), denser in the worn zones
  horn      black buffalo horn (spec #16120F, 0.28): fine lengthwise grain with faint amber-grey streaks; the mouth
            round slightly polished, the kojiri end scuffed; the seam grooves darker
  brass     shitodome (spec #B8955E, 0.30, metallic) with cavity darkening from the AO
  cavity    inside the saya: lacquer black, matte (never seen except through the mouth)

AO is the Cycles bake of the LOD0 game mesh (stage ao). Outputs: T_Katana_Saya_{BC,ORM,N}.png 2048^2;
BC sRGB, ORM linear (R AO, G roughness, B metallic), N DirectX (green down).
"""
from __future__ import annotations

import json
import math
import pickle
import time

import numpy as np

import katana_spec as K
import katana_uvpack as UP
import saya_spec as S
from saya_parts import CODES
from katana_tex import (raster, cover_mask, edge_extend, height_to_normal, write_png, lin2srgb, fbm3, vnoise3,
                        _hash, smoothstep)

C = CODES


def log(*a):
    print("[SAYA-TEX]", *a, flush=True)


def tris_of(mbs, atlas):
    uvs, ats, names = [], [], []
    for part, mb in mbs.items():
        V = np.array(mb.verts)
        for fi, f in enumerate(mb.faces):
            isl = mb.fisl[fi]
            if isl not in names:
                names.append(isl)
            ii = names.index(isl)
            uv = atlas.transform(isl, np.array(mb.fuv[fi])) * atlas.size
            for k in range(1, len(f) - 1):
                cs = (0, k, k + 1)
                uvs.append(uv[list(cs)])
                ats.append([list(V[f[c]]) + list(mb.fattr[fi][c]) + [ii] for c in cs])
    return np.array(uvs), np.array(ats, np.float64), names


def bump(x, a, b, c, d):
    return smoothstep(a, b, x) * (1 - smoothstep(c, d, x))


def scratches(u, v, cell, seed, ang_spread, lmin, lmax, width):
    """Hairline scratch intensity (0..1) in a 2D coordinate system (mm): random segments per cell, mostly along u."""
    out = np.zeros(len(u))
    ci, cj = np.floor(u / cell).astype(np.int64), np.floor(v / cell).astype(np.int64)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            a, b = ci + di, cj + dj
            z = np.zeros_like(a)
            for k in range(2):
                pres = _hash(a, b, z + k, seed) < 0.55
                cx = (a + _hash(a, b, z + k, seed + 1)) * cell
                cy = (b + _hash(a, b, z + k, seed + 2)) * cell
                th = (_hash(a, b, z + k, seed + 3) - 0.5) * 2 * ang_spread
                L = lmin + (lmax - lmin) * _hash(a, b, z + k, seed + 4)
                dx, dy = u - cx, v - cy
                t = np.clip(dx * np.cos(th) + dy * np.sin(th), -L / 2, L / 2)
                px, py = cx + t * np.cos(th), cy + t * np.sin(th)
                d = np.hypot(u - px, v - py)
                inten = (0.35 + 0.65 * _hash(a, b, z + k, seed + 5)) * (1 - np.abs(t) / (L / 2 + 1e-9)) ** 0.5
                out = np.maximum(out, np.where(pres, inten * np.clip(1 - d / width, 0, 1), 0.0))
    return out


def paint(P, A):
    s, ar, ex, code = A[:, 0], A[:, 1], A[:, 2], np.rint(A[:, 3]).astype(int)
    n = len(P)
    bc = np.zeros((n, 3))
    rough = np.zeros(n)
    metal = np.zeros(n)
    h = np.zeros(n)
    # arc coords of every texel (for zones)
    s3, rho3, y3 = S.xyz_to_arc(P)
    tt = (np.clip(s3, S.S_MO, S.S_EN) - S.S_MO) / (S.S_EN - S.S_MO)
    D = S.SY["depth_x"]["mouth"] + (S.SY["depth_x"]["kojiri_end"] - S.SY["depth_x"]["mouth"]) * tt
    W = S.SY["width_y"]["mouth"] + (S.SY["width_y"]["kojiri_end"] - S.SY["width_y"]["mouth"]) * tt
    s_tab = np.arange(0.0, 724.0, 2.0)
    per_tab = np.array([S.outer_perimeter(v) for v in np.clip(s_tab, S.S_MO, S.S_EN)])
    rc = S.RHO_MUNE + D / 2
    # ---------------------------------------------------------------- lacquer
    m = code == C["lacquer"]
    if m.any():
        p = P[m]
        ss = s3[m]
        face = np.clip((np.abs(y3[m]) - 0.55 * W[m] / 2) / (0.45 * W[m] / 2), 0, 1)          # 1 on the flats
        ridge = np.clip((np.abs(rho3[m] - rc[m]) - 0.70 * D[m] / 2) / (0.30 * D[m] / 2), 0, 1)  # 1 on ha / mune
        brk = fbm3(p / 22.0, 3, seed=11)
        brk2 = fbm3(p / 7.0, 2, seed=12)
        w_hand = bump(ss, 20.0, 30.0, 70.0, 115.0) * 0.55
        w_obi = bump(ss, 55.0, 85.0, 190.0, 240.0) * face * 0.6
        w_ridge = ridge * 0.30
        w_end = smoothstep(560.0, 690.0, ss) * 0.35
        w = (w_hand + w_obi + w_ridge + w_end) * np.clip(0.45 + 1.0 * (brk - 0.45) + 0.2 * (brk2 - 0.5), 0, 1.2)
        w = np.clip(w, 0, 1)
        # hairlines in unrolled coords (s along, perimeter distance across)
        per = np.interp(ss, s_tab, per_tab)
        u_, v_ = ss, ar[m] * per
        sc = scratches(u_, v_, 7.0, 31, 0.45, 4.0, 22.0, 0.11)
        dens = smoothstep(0.15, 0.6, w + 0.25 * (fbm3(p / 25.0, 2, seed=13) - 0.3))
        sc = sc * (0.25 + 0.75 * dens)
        base = K.COL["saya_lacquer"]
        bc[m] = base[None, :] * (1.0 + 0.30 * w + 0.7 * sc)[:, None] * (0.97 + 0.06 * fbm3(p / 40.0, 2, seed=14))[:, None]
        rough[m] = (K.ROUGH["saya_lacquer"] + 0.010 * (fbm3(p / 60.0, 2, seed=15) - 0.5) + 0.08 * w + 0.12 * sc)
        h[m] = 0.0   # lacquer is flat: sub-LSB height detail only quantises into blocky 8-bit normal steps
    # ---------------------------------------------------------------- horn
    horn = np.isin(code, [C["koiguchi"], C["kojiri"], C["kojiri_end"], C["mouth"], C["pocket"], C["kurikata"], C["groove"]])
    if horn.any():
        p = P[horn]
        cd = code[horn]
        ss = s3[horn]
        # lengthwise grain: stretched noise (long along the saya, fine across)
        along = ss
        acr = np.c_[rho3[horn], y3[horn]]
        g1 = fbm3(np.c_[along / 25.0, acr[:, 0] / 0.55, acr[:, 1] / 0.55], 4, seed=21)
        g2 = fbm3(np.c_[along / 60.0, acr[:, 0] / 2.2, acr[:, 1] / 2.2], 3, seed=22)
        end_grain = np.isin(cd, [C["mouth"], C["kojiri_end"]])
        g_iso = fbm3(p / 0.5, 3, seed=23)
        g = np.where(end_grain, g_iso, g1)
        streak = np.clip((g2 - 0.55) / 0.25, 0, 1) ** 2
        base = K.COL["horn"]
        amber = np.array([0.030, 0.020, 0.012])
        col = base[None, :] * (0.82 + 0.36 * g)[:, None]
        col = col * (1 - 0.45 * streak[:, None]) + amber[None, :] * (0.45 * streak[:, None])
        r = K.ROUGH["horn"] + 0.05 * (g - 0.5) + 0.03 * streak
        # wear: the mouth round polished (koiguchi rows with shrink > 0 near the mouth) and the mouth face rim
        mouth_round = (cd == C["koiguchi"]) & (ss < 1.0)
        r = np.where(mouth_round, r - 0.06, r)
        col = np.where(mouth_round[:, None], col * 1.12, col)
        # kojiri end and round-over scuffed
        kj = np.isin(cd, [C["kojiri"], C["kojiri_end"]])
        scuff = kj * smoothstep(712.0, 722.0, ss) * np.clip(0.3 + 1.2 * (fbm3(p / 1.6, 3, seed=24) - 0.4), 0, 1)
        r = r + 0.14 * scuff
        col = col * (1 + 0.5 * scuff)[:, None]
        # pocket inside the koiguchi: darker, duller (seldom polished)
        pk = cd == C["pocket"]
        col = np.where(pk[:, None], col * 0.7, col)
        r = np.where(pk, 0.45, r)
        gr = cd == C["groove"]
        col = np.where(gr[:, None], col * 0.55, col)
        r = np.where(gr, 0.5, r)
        bc[horn] = col
        rough[horn] = r
        h[horn] = 0.012 * (g - 0.5)
    # ---------------------------------------------------------------- brass
    m = code == C["brass"]
    if m.any():
        p = P[m]
        nz = fbm3(p / 1.5, 3, seed=31)
        bc[m] = K.COL["eyelets_and_shitodome"][None, :] * (0.9 + 0.15 * nz)[:, None]
        rough[m] = K.ROUGH["eyelets_and_shitodome"] + 0.06 * (nz - 0.5)
        metal[m] = 1.0
        h[m] = 0.002 * (nz - 0.5)
    # ---------------------------------------------------------------- cavity
    m = code == C["cavity"]
    if m.any():
        bc[m] = K.COL["saya_lacquer"][None, :]
        rough[m] = 0.6
    return {"bc": bc, "rough": rough, "metal": metal, "h": h}


def make_maps(WORK, BAKE_DIR, TEX_DIR):
    t0 = time.time()
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    parts = pickle.load(open(WORK / "parts.pkl", "rb"))
    at = UP.load(WORK / "atlas_saya.json")
    size = at.size
    uvs, ats, names = tris_of(parts["lod0"], at)
    img, m0, tid = raster(uvs, ats.astype(np.float32), size, ats.shape[2])
    cov = m0.copy()
    for lv in ("lod1", "lod2"):
        u2, _, _ = tris_of(parts[lv], at)
        cov |= cover_mask(u2, size, 0)
    log(f"raster {m0.sum()} texels (+{(cov & ~m0).sum()} LOD1/2 only) {time.time() - t0:.1f}s")
    ii = np.where(m0)
    P = img[ii][:, 0:3].astype(np.float64)
    A = img[ii][:, 3:7].astype(np.float64)
    isl = np.rint(img[ii][:, 7]).astype(int)
    res = paint(P, A)
    log(f"painted {time.time() - t0:.1f}s")
    bc = np.zeros((size, size, 3), np.float32)
    rough = np.zeros((size, size), np.float32)
    metal = np.zeros((size, size), np.float32)
    hmap = np.zeros((size, size), np.float32)
    ppmm = np.zeros((size, size), np.float32)
    bc[ii] = res["bc"]
    rough[ii] = res["rough"]
    metal[ii] = res["metal"]
    hmap[ii] = res["h"]
    ppmm[ii] = np.array([at.px_per_mm(names[k]) for k in isl])
    ao = np.clip(np.load(BAKE_DIR / "saya_AO.npy").astype(np.float32), 0, 1)
    hm = edge_extend(hmap, m0)
    pp = edge_extend(ppmm, m0)
    nrm = height_to_normal(hm, pp, m0)
    # metals: mild cavity darkening of the albedo (Unreal's AO only touches indirect light)
    bc = np.where((metal > 0.5)[..., None], bc * (0.75 + 0.25 * ao)[..., None], bc)
    bc = edge_extend(bc, m0)
    rough = edge_extend(np.clip(rough, 0.02, 1.0), m0)
    metal = edge_extend(metal, m0)
    ao_e = edge_extend(ao, m0)
    nrm = edge_extend(nrm, m0)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    enc = nrm * 0.5 + 0.5
    enc[..., 1] = 1.0 - enc[..., 1]             # OpenGL -> DirectX
    flip = lambda a: a[::-1]
    stem = S.TEX_STEM
    # +-0.5 LSB dither before 8-bit quantisation: the near-black gloss lacquer otherwise shows terraced contours in
    # its roughness / colour reflections
    rng = np.random.default_rng(7)
    dith = lambda a: np.clip(a + (rng.random(a.shape, dtype=np.float32) - 0.5) / 255.0, 0, 1)
    write_png(TEX_DIR / f"{stem}_BC.png", flip(dith(lin2srgb(bc))))
    write_png(TEX_DIR / f"{stem}_ORM.png", flip(np.stack([ao_e, dith(rough), metal], -1)))
    write_png(TEX_DIR / f"{stem}_N.png", flip(dith(enc)))
    np.save(WORK / "paint_cov.npy", cov)
    codes = np.rint(A[:, 3]).astype(int)
    rep = {"size": size, "coverage": float(cov.mean()), "texels_lod0": int(m0.sum()),
           "per_code": {k: {"texels": int((codes == v).sum()),
                            "bc_mean_linear": [round(float(x), 5) for x in res["bc"][codes == v].mean(axis=0)] if (codes == v).any() else None,
                            "rough_mean": round(float(res["rough"][codes == v].mean()), 4) if (codes == v).any() else None,
                            "rough_p99": round(float(np.percentile(res["rough"][codes == v], 99)), 4) if (codes == v).any() else None}
                        for k, v in C.items()},
           "ao_mean": float(ao_e[m0].mean())}
    json.dump(rep, open(WORK / "maps_report.json", "w"), indent=1)
    log("maps", json.dumps(rep)[:1500], f"{time.time() - t0:.1f}s")
