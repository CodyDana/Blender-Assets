"""Katana texture maps (runs inside Blender for mathutils.bvhtree; numpy only otherwise).

Every LOD0 face carries parametric attributes (katana_parts: the blade's mune-arc station s / across distance u /
region; a cord's path length / across offset; a part code). They are rasterised into each atlas together with the
3D position, and every texel is painted from them:

  blade    polished ji, burnished shinogi-ji + mune, frosted hardened zone from the spec's ko-notare hamon line and
           ko-maru boshi (the study's own polygon), soft nioi band, faint hada in roughness
  iron     tsuba / fuchi / kashira: blackened iron, faint hand-forged dimpling (<= 0.05 mm) in the normal map
  brass    habaki / seppa / menuki / eyelets (hole walls dark)
  same     white ray-skin nodules (0.6-1.2 mm) in the diamond windows; cord-dark under the edges
  ito      flat braid (chevron strands) in each ribbon's own path space, black, silk roughness
  mekugi   bamboo
  shell    (LOD2 tsuka) ray-cast onto the LOD0 wrap: colour, roughness, AO and the LOD0 normals in its tangent space

AO is the Cycles bake of the LOD0 game mesh (build stage ao). Outputs (shipped): T_Katana_Steel_{BC,ORM,N}.png and
T_Katana_Grip_{BC,ORM,N}.png, 2048^2; BC sRGB, ORM linear (R AO, G roughness, B metallic), N DirectX (green down).
"""
from __future__ import annotations

import json
import math
import pickle
import struct
import time
import zlib
from pathlib import Path

import numpy as np

import katana_spec as K
import katana_parts as KP
import katana_uvpack as UP

C = KP.CODES


def log(*a):
    print("[KAT]", *a, flush=True)


# ====================================================================== png
def write_png(path, arr):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, 2)
    h, w, c = a.shape
    ctype = {3: 2, 4: 6}[c]
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


# ====================================================================== noise
def _hash(ix, iy, iz, seed=0):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return ((h & 0xFFFFFF).astype(np.float64)) / float(0xFFFFFF)


def vnoise3(p, seed=0):
    """Value noise in [0, 1] at points p (N, 3)."""
    p = np.asarray(p, float)
    i = np.floor(p).astype(np.int64)
    f = p - i
    u = f * f * (3 - 2 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out += w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm3(p, octaves=4, seed=0):
    out = np.zeros(len(p))
    amp, tot = 1.0, 0.0
    q = np.asarray(p, float)
    for o in range(octaves):
        out += amp * vnoise3(q, seed + o)
        tot += amp
        amp *= 0.5
        q = q * 2.03 + 17.1
    return out / tot


def nodules(p, cell=0.95, hgt=0.10, seed=7):
    """Ray-skin: jittered spherical nodules (radius 0.30-0.60 mm) on a 3D cell grid; returns height (mm)."""
    q = np.asarray(p, float) / cell
    base = np.floor(q).astype(np.int64)
    best = np.zeros(len(q))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + np.array([dx, dy, dz])
                jx = _hash(c[:, 0], c[:, 1], c[:, 2], seed)
                jy = _hash(c[:, 0], c[:, 1], c[:, 2], seed + 1)
                jz = _hash(c[:, 0], c[:, 1], c[:, 2], seed + 2)
                rr = (0.30 + 0.30 * _hash(c[:, 0], c[:, 1], c[:, 2], seed + 3)) / cell
                d = np.sqrt((q[:, 0] - c[:, 0] - jx) ** 2 + (q[:, 1] - c[:, 1] - jy) ** 2 + (q[:, 2] - c[:, 2] - jz) ** 2)
                b = np.sqrt(np.clip(1 - (d / rr) ** 2, 0, 1)) * (rr * cell / 0.6)
                best = np.maximum(best, b)
    return best * hgt


# ====================================================================== raster
def raster(tris_uv, tris_attr, size, nch, cover_only=None):
    """tris_uv (T,3,2) in pixel units (row 0 = v 0); tris_attr (T,3,nch). Returns (img (size,size,nch), mask,
    tri index map). Pixel centres; barycentric interpolation; ties resolved by last write."""
    img = np.zeros((size, size, nch), np.float32)
    mask = np.zeros((size, size), bool)
    tid = np.full((size, size), -1, np.int32)
    for t in range(len(tris_uv)):
        tr = tris_uv[t]
        x0 = max(int(math.floor(tr[:, 0].min() - 0.5)), 0)
        x1 = min(int(math.ceil(tr[:, 0].max() + 0.5)), size)
        y0 = max(int(math.floor(tr[:, 1].min() - 0.5)), 0)
        y1 = min(int(math.ceil(tr[:, 1].max() + 0.5)), size)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = np.arange(x0, x1) + 0.5
        ys = np.arange(y0, y1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        (ax, ay), (bx, by), (cx, cy) = tr
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        l3 = 1 - l1 - l2
        eps = -1e-4
        ins = (l1 >= eps) & (l2 >= eps) & (l3 >= eps)
        if not ins.any():
            continue
        if tris_attr is not None:
            a = tris_attr[t]
            val = l1[..., None] * a[0] + l2[..., None] * a[1] + l3[..., None] * a[2]
            sub = img[y0:y1, x0:x1]
            sub[ins] = val[ins]
        mask[y0:y1, x0:x1] |= ins
        tsub = tid[y0:y1, x0:x1]
        tsub[ins] = t
    return img, mask, tid


def cover_mask(tris_uv, size, dilate=1):
    _, m, _ = raster(tris_uv, None, size, 1)
    for _ in range(dilate):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def edge_extend(img, valid):
    img = np.asarray(img, np.float32)
    squeeze = img.ndim == 2
    if squeeze:
        img = img[..., None]
    w = valid.astype(np.float32)
    pyr = [(img * w[..., None], w)]
    while pyr[-1][1].shape[0] > 1:
        a, ww = pyr[-1]
        h2, w2 = a.shape[0] // 2, a.shape[1] // 2
        a2 = a[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, -1).sum(axis=(1, 3))
        w2_ = ww[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum(axis=(1, 3))
        pyr.append((a2, w2_))
    lev = []
    for a, ww in pyr:
        with np.errstate(invalid="ignore", divide="ignore"):
            lev.append((np.where(ww[..., None] > 0, a / np.maximum(ww[..., None], 1e-12), 0.0), ww > 0))
    filled = lev[-1][0]
    for k in range(len(lev) - 2, -1, -1):
        col, ok = lev[k]
        up = np.repeat(np.repeat(filled, 2, axis=0), 2, axis=1)[:col.shape[0], :col.shape[1]]
        filled = np.where(ok[..., None], col, up)
    out = img.copy()
    out[~valid] = filled[~valid]
    return out[..., 0] if squeeze else out


# ====================================================================== part data -> triangles
def part_tris(mbs, atlas_of, atlases, u_shift):
    """Triangles of the given MBs in atlas pixel space, with per-corner attributes [pos(3), attr(4), island(1)]."""
    uvs, ats, isl_names = [], [], []
    for part, mb in mbs.items():
        at = atlases[atlas_of(part)]
        V = np.array(mb.verts)
        for fi, f in enumerate(mb.faces):
            isl = mb.fisl[fi]
            if isl not in isl_names:
                isl_names.append(isl)
            ii = isl_names.index(isl)
            uv = at.transform(isl, np.array(mb.fuv[fi])) * at.size
            uv[:, 0] -= u_shift(part) * at.size
            for k in range(1, len(f) - 1):
                cs = (0, k, k + 1)
                uvs.append(uv[list(cs)])
                ats.append([list(V[f[c]]) + list(mb.fattr[fi][c]) + [ii] for c in cs])
    return np.array(uvs), np.array(ats, np.float64), isl_names


# ====================================================================== painters
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def point_in_poly(px, pz, poly):
    inside = np.zeros(len(px), bool)
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        cond = (z1 > pz) != (z2 > pz)
        xi = (x2 - x1) * (pz - z1) / ((z2 - z1) if z2 != z1 else 1e-12) + x1
        inside ^= cond & (px < xi)
    return inside


def dist_to_polyline(px, pz, line):
    d = np.full(len(px), 1e9)
    for i in range(len(line) - 1):
        ax, az = line[i]
        bx, bz = line[i + 1]
        vx, vz = bx - ax, bz - az
        L2 = vx * vx + vz * vz or 1e-12
        t = np.clip(((px - ax) * vx + (pz - az) * vz) / L2, 0, 1)
        d = np.minimum(d, np.hypot(px - ax - t * vx, pz - az - t * vz))
    return d


def paint_blade(P, A, out):
    s, u, reg = A[:, 0], A[:, 1], np.rint(A[:, 2]).astype(int)
    side = np.where(P[:, 1] <= 0, -1, 1)
    bc = np.zeros((len(P), 3))
    rough = np.zeros(len(P))
    hard = np.zeros(len(P))
    nioi = np.zeros(len(P))
    for sg, phase in ((-1, 0.0), (1, 15.0)):
        sel = np.where(side == sg)[0]
        if not len(sel):
            continue
        poly, line = K.hamon_polygon(phase)
        px, pz = P[sel, 0], P[sel, 2]
        ins = point_in_poly(px, pz, poly)
        d = dist_to_polyline(px, pz, line)
        sd = np.where(ins, d, -d)
        band = K.SP["hamon"]["nioi_band"]
        hard[sel] = smoothstep(-0.55 * band, 0.55 * band, sd)
        nioi[sel] = np.exp(-(sd / (0.45 * band)) ** 2)
    ji, shin, ham = K.COL["blade_ji"], K.COL["blade_shinogi_ji_and_mune"], K.COL["blade_hamon"]
    # faint hada (itame-like grain, stretched along the blade) in colour and roughness only
    g = fbm3(np.c_[s * 0.35, u * 2.2, side * 50.0], 4, seed=3)
    g2 = fbm3(np.c_[s * 1.6, u * 6.0, side * 50.0 + 9], 3, seed=11)
    grain = (g - 0.5) * 0.6 + (g2 - 0.5) * 0.4
    ji_mix = ji[None] * (1 + 0.035 * grain[:, None])
    ham_mix = ham[None] * (1 + 0.025 * grain[:, None])
    # continuous (anti-aliased) region weights from the section coordinates: the colour boundaries sit exactly on the
    # geometric creases (shinogi, edge corners) but are softened over ~1 texel so they never stair-step
    Bp = K.B
    q = np.clip((s - K.S_Y) / (K.S_TIP - K.S_Y), 0, 1)
    w_s = np.where(s <= K.S_Y, Bp["motohaba"] + (Bp["sakihaba_at_yokote"] - Bp["motohaba"]) * np.clip(s / K.S_Y, 0, 1),
                   Bp["sakihaba_at_yokote"] * np.clip(1 - q ** 1.8, 0, 1) ** 0.7)
    sj = Bp["shinogi_ji_ratio"] * w_s
    texel = 0.4
    shin_w = 1 - smoothstep(sj - texel, sj + texel, u)
    edge_w = smoothstep(w_s - 0.25 - texel, w_s - 0.25 + texel, u)
    h = np.maximum(hard, edge_w)
    hira_bc = ji_mix * (1 - h[:, None]) + ham_mix * h[:, None]
    hira_bc = hira_bc * (1 + 0.06 * nioi[:, None])
    bc = shin[None] * (1 + 0.02 * grain[:, None]) * shin_w[:, None] + hira_bc * (1 - shin_w[:, None])
    hira_r = K.ROUGH["blade_ji"] * (1 - h) + K.ROUGH["blade_hamon"] * h + 0.02 * grain + 0.05 * nioi * (1 - h)
    rough = (K.ROUGH["blade_shinogi_ji_and_mune"] + 0.012 * grain) * shin_w + hira_r * (1 - shin_w)
    out["bc"], out["rough"], out["metal"], out["h"] = bc, rough, np.ones(len(P)), np.zeros(len(P))


def paint_iron(P, A, out):
    n1 = fbm3(P * 0.45, 4, seed=21)
    n2 = fbm3(P * 1.6, 3, seed=29)
    out["h"] = 0.035 * (n1 - 0.5) * 2 + 0.012 * (n2 - 0.5) * 2
    v = (n1 - 0.5)
    out["bc"] = K.COL["iron_fittings"][None] * (1 + 0.10 * v[:, None])
    out["rough"] = K.ROUGH["iron_fittings"] + 0.08 * (n2 - 0.5)
    out["metal"] = np.ones(len(P))


def paint_brass(P, A, out, key, code):
    n1 = fbm3(P * np.array([0.8, 0.8, 6.0]), 3, seed=31)        # fine lengthwise satin
    n2 = fbm3(P * 0.3, 3, seed=37)
    col = K.COL[key]
    out["bc"] = col[None] * (1 + 0.05 * (n2 - 0.5)[:, None])
    out["rough"] = K.ROUGH[key] + 0.06 * (n1 - 0.5)
    out["metal"] = np.ones(len(P))
    out["h"] = 0.004 * (n1 - 0.5)
    if code == C["eyelet"]:
        hole = A[:, 0] < 0.5
        out["bc"][hole] = np.array([0.012, 0.010, 0.008])
        out["rough"][hole] = 0.6
    if code == C["menuki"]:
        out["h"] = 0.008 * (fbm3(P * 1.2, 3, seed=41) - 0.5)


def paint_core(P, A, out):
    zc = P[:, 2]
    TS = K.TS
    t = np.clip((K.Z_FB - zc) / (K.Z_FB - K.Z_KT), -0.2, 1.2)
    ha = TS["ha_x"]["at_fuchi"] + (TS["ha_x"]["at_kashira"] - TS["ha_x"]["at_fuchi"]) * t
    cx = (TS["mune_x"] + ha) / 2
    a_ = (TS["mune_x"] - ha) / 2 - K.INSET
    lat = np.abs(P[:, 0] - cx) / a_
    win = 1 - smoothstep(0.88, 0.94, lat)
    nod = nodules(P)
    same = K.COL["same"][None] * (1 + 0.35 * (nod / 0.10 - 0.5)[:, None] * 0.18)
    dark = np.array([0.010, 0.010, 0.011])
    out["bc"] = same * win[:, None] + dark[None] * (1 - win[:, None])
    out["rough"] = K.ROUGH["same"] * win + 0.85 * (1 - win) - 0.10 * (nod / 0.10) * win
    out["metal"] = np.zeros(len(P))
    out["h"] = nod * win


def paint_cord(P, A, out):
    L, a = A[:, 0], A[:, 1]
    w = np.maximum(np.abs(a), 1e-6)
    lam = 1.55
    ph = (L + np.abs(a) * 1.05) / lam
    fr = ph - np.floor(ph)
    strand = np.sin(math.pi * fr) ** 0.6                       # rounded strand ridge, chevrons pointing along the cord
    centre = 1 - np.exp(-(a / 0.35) ** 2) * 0.6                # the braid's centre seam
    fib = fbm3(np.c_[L * 3.0, a * 0.6, A[:, 2] * 40], 2, seed=51)
    h = 0.055 * strand * centre + 0.01 * (fib - 0.5)
    out["h"] = h
    col = K.COL["ito"]
    out["bc"] = col[None] * (0.82 + 0.30 * strand[:, None] + 0.15 * (fib[:, None] - 0.5))
    out["rough"] = K.ROUGH["ito"] - 0.12 * strand + 0.06 * (fib - 0.5)
    out["metal"] = np.zeros(len(P))


def paint_mekugi(P, A, out):
    f = fbm3(np.c_[P[:, 0] * 0.4, P[:, 1] * 0.4, P[:, 2] * 5.0], 3, seed=61)
    out["bc"] = K.COL["mekugi"][None] * (0.85 + 0.3 * (f[:, None] - 0.5))
    out["rough"] = K.ROUGH["mekugi"] + 0.08 * (f - 0.5)
    out["metal"] = np.zeros(len(P))
    out["h"] = 0.01 * (f - 0.5)


def paint(P, A, codes):
    n = len(P)
    res = {"bc": np.zeros((n, 3)), "rough": np.full(n, 0.5), "metal": np.zeros(n), "h": np.zeros(n)}
    for code in np.unique(codes):
        sel = np.where(codes == code)[0]
        o = {}
        Ps, As = P[sel], A[sel]
        if code == C["blade"]:
            paint_blade(Ps, As, o)
        elif code == C["blade_cap"]:
            o = {"bc": np.tile(K.COL["blade_ji"], (len(sel), 1)), "rough": np.full(len(sel), 0.4),
                 "metal": np.ones(len(sel)), "h": np.zeros(len(sel))}
        elif code in (C["tsuba"], C["fuchi"], C["kashira"]):
            paint_iron(Ps, As, o)
        elif code == C["habaki"]:
            paint_brass(Ps, As, o, "habaki", code)
        elif code == C["seppa"]:
            paint_brass(Ps, As, o, "seppa", code)
        elif code == C["menuki"]:
            paint_brass(Ps, As, o, "menuki", code)
        elif code == C["eyelet"]:
            paint_brass(Ps, As, o, "eyelets_and_shitodome", code)
        elif code == C["core"]:
            paint_core(Ps, As, o)
        elif code in (C["cord"], C["band"]):
            paint_cord(Ps, As, o)
        elif code == C["mekugi"]:
            paint_mekugi(Ps, As, o)
        else:
            continue
        for k in res:
            res[k][sel] = o[k]
    return res


# ====================================================================== normal map from height
def height_to_normal(hmap, ppmm, valid):
    """Tangent-space normal (OpenGL, +v up) from a height map in mm; ppmm per texel (px per mm)."""
    hx = np.zeros_like(hmap)
    hy = np.zeros_like(hmap)
    hx[:, 1:-1] = (hmap[:, 2:] - hmap[:, :-2]) * 0.5
    hy[1:-1, :] = (hmap[2:, :] - hmap[:-2, :]) * 0.5
    gx = hx * ppmm
    gy = hy * ppmm
    n = np.stack([-gx, -gy, np.ones_like(hmap)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


# ====================================================================== main
def make_maps(WORK, BAKE_DIR, TEX_DIR):
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    t0 = time.time()
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    parts = pickle.load(open(WORK / "parts.pkl", "rb"))
    atl = {"steel": UP.load(WORK / "atlas_steel.json"), "grip": UP.load(WORK / "atlas_grip.json")}
    atlas_of = lambda part: "grip" if part in KP.GRIP_PARTS else "steel"
    u_shift = lambda part: 1.0 if part in KP.GRIP_PARTS else 0.0
    report = {}
    painted = {}
    for atlas, size, stem in (("steel", K.STEEL_MAP, "T_Katana_Steel"), ("grip", K.GRIP_MAP, "T_Katana_Grip")):
        sel0 = {p: m for p, m in parts["lod0"].items() if atlas_of(p) == atlas}
        uvs, ats, isl_names = part_tris(sel0, atlas_of, atl, u_shift)
        img, m0, tid = raster(uvs, ats.astype(np.float32), size, ats.shape[2])
        # coverage over every LOD (LOD1/LOD2-only texels get the edge-extended LOD0 paint)
        cov = m0.copy()
        for lv in ("lod1", "lod2"):
            selx = {p: m for p, m in parts[lv].items() if atlas_of(p) == atlas and p != "shell"}
            if selx:
                u2, _, _ = part_tris(selx, atlas_of, atl, u_shift)
                cov |= cover_mask(u2, size, 0)
        log(f"{atlas}: raster {m0.sum()} texels (+{(cov & ~m0).sum()} LOD1/2 only) {time.time() - t0:.1f}s")
        ii = np.where(m0)
        P = img[ii][:, 0:3].astype(np.float64)
        A = img[ii][:, 3:7].astype(np.float64)
        isl = np.rint(img[ii][:, 7]).astype(int)
        codes = np.rint(A[:, 3]).astype(int)
        res = paint(P, A, codes)
        log(f"{atlas}: painted {time.time() - t0:.1f}s")
        bc = np.zeros((size, size, 3), np.float32)
        rough = np.zeros((size, size), np.float32)
        metal = np.zeros((size, size), np.float32)
        hmap = np.zeros((size, size), np.float32)
        ppmm = np.zeros((size, size), np.float32)
        bc[ii] = res["bc"]
        rough[ii] = res["rough"]
        metal[ii] = res["metal"]
        hmap[ii] = res["h"]
        ppmm[ii] = np.array([atl[atlas].px_per_mm(isl_names[k]) for k in isl])
        painted[atlas] = dict(bc=bc, rough=rough, metal=metal, hmap=hmap, ppmm=ppmm, m0=m0, cov=cov, tid=tid,
                              uvs=uvs, ats=ats, isl_names=isl_names, P=img[..., 0:3])
    # ---------------------------------------------------------------- LOD2 tsuka shell: ray-cast onto the LOD0 wrap
    g = painted["grip"]
    aog = np.load(BAKE_DIR / "grip_AO.npy")
    shell = {"shell": parts["lod2"]["shell"]}
    su, sa, snames = part_tris(shell, atlas_of, atl, u_shift)
    simg, sm, stid = raster(su, sa.astype(np.float32), K.GRIP_MAP, sa.shape[2])
    wrap_parts = {p: parts["lod0"][p] for p in ("cords", "core", "menuki", "mekugi") if p in parts["lod0"]}
    verts, tris, tri_uv, tri_at = [], [], [], []
    off = 0
    for p, mb in wrap_parts.items():
        V = np.array(mb.verts)
        verts.append(V)
        an = atlas_of(p)
        at = atl[an]
        for fi, f in enumerate(mb.faces):
            uv = at.transform(mb.fisl[fi], np.array(mb.fuv[fi])) * at.size
            uv[:, 0] -= u_shift(p) * at.size
            for k in range(1, len(f) - 1):
                tris.append((f[0] + off, f[k] + off, f[k + 1] + off))
                tri_uv.append(uv[[0, k, k + 1]])
                tri_at.append(an)
        off += len(V)
    aos = np.load(BAKE_DIR / "steel_AO.npy")
    V = np.vstack(verts)
    T = np.array(tris)
    TUV = np.array(tri_uv)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, T[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    bvh = BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in T])
    # shell tangent frames per triangle (from its UV Jacobian), normals interpolated
    sV = np.array(shell["shell"].verts)
    s_ii = np.where(sm)
    sP = simg[s_ii][:, 0:3].astype(np.float64)
    st = stid[s_ii]
    s_tri = []
    for fi, f in enumerate(shell["shell"].faces):
        for k in range(1, len(f) - 1):
            s_tri.append((f[0], f[k], f[k + 1]))
    s_tri = np.array(s_tri)
    p0, p1, p2 = sV[s_tri[:, 0]], sV[s_tri[:, 1]], sV[s_tri[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    du1, dv1 = su[:, 1, 0] - su[:, 0, 0], su[:, 1, 1] - su[:, 0, 1]
    du2, dv2 = su[:, 2, 0] - su[:, 0, 0], su[:, 2, 1] - su[:, 0, 1]
    r = 1.0 / np.where(np.abs(du1 * dv2 - du2 * dv1) < 1e-12, 1e-12, du1 * dv2 - du2 * dv1)
    Tg = (e1 * dv2[:, None] - e2 * dv1[:, None]) * r[:, None]
    Bg = (e2 * du1[:, None] - e1 * du2[:, None]) * r[:, None]
    Ng = np.cross(e1, e2)
    Ng /= np.linalg.norm(Ng, axis=1, keepdims=True)
    # outward (shell is a loft about the tsuka axis)
    cen = (p0 + p1 + p2) / 3
    cxs = np.array([K.tsuka_dims(z)[0] for z in cen[:, 2]])
    outw = np.c_[cen[:, 0] - cxs, cen[:, 1], np.zeros(len(cen))]
    Ng *= np.sign(np.sum(Ng * outw, axis=1))[:, None]
    s_bc = np.zeros((len(sP), 3))
    s_r = np.zeros(len(sP))
    s_ao = np.ones(len(sP))
    s_n = np.zeros((len(sP), 3))
    s_n[:, 2] = 1.0
    hits = 0
    # smooth shell normal per texel (analytic superellipse normal of the shell loft at that height and direction):
    # this is what the shell's interpolated vertex normals approximate, so the encoded normals do not band per facet
    Ns = np.zeros((len(sP), 3))
    for i in range(len(sP)):
        cx_, D_, W_ = K.tsuka_dims(sP[i, 2])
        al = math.atan2(sP[i, 1], sP[i, 0] - cx_)
        _, _, nx_, ny_ = K.se_radial(D_ / 2 + 0.25, W_ / 2 - 0.1, K.NT, al)
        Ns[i] = (nx_, ny_, 0.0)
    for i in range(len(sP)):
        t_ = st[i]
        N_ = Ns[i]
        o = sP[i] + N_ * 8.0
        loc, nrm, idx, dist = bvh.ray_cast(Vector(o), Vector(-N_), 16.0)
        if idx is None:
            s_bc[i] = K.COL["same"]
            s_r[i] = 0.55
            continue
        hits += 1
        tri = T[idx]
        a, b, c = V[tri[0]], V[tri[1]], V[tri[2]]
        q = np.array(loc)
        v0, v1, v2 = b - a, c - a, q - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01 or 1e-12
        w1 = (d11 * d20 - d01 * d21) / den
        w2 = (d00 * d21 - d01 * d20) / den
        w0 = 1 - w1 - w2
        uvp = w0 * TUV[idx][0] + w1 * TUV[idx][1] + w2 * TUV[idx][2]
        x, y = int(min(max(uvp[0], 0), K.GRIP_MAP - 1)), int(min(max(uvp[1], 0), K.GRIP_MAP - 1))
        src = painted[tri_at[idx]]
        s_bc[i] = src["bc"][y, x] * (0.86 + 0.14 * (aog if tri_at[idx] == "grip" else aos)[y, x]) if tri_at[idx] == "steel" else src["bc"][y, x]
        s_r[i] = src["rough"][y, x]
        s_ao[i] = (aog if tri_at[idx] == "grip" else aos)[y, x]
        nn = w0 * vn[tri[0]] + w1 * vn[tri[1]] + w2 * vn[tri[2]]
        nn /= np.linalg.norm(nn) or 1.0
        Tt = Tg[t_] - N_ * (Tg[t_] @ N_)
        Tt /= np.linalg.norm(Tt) or 1.0
        sgn = 1.0 if np.cross(N_, Tt) @ Bg[t_] >= 0 else -1.0
        Bt = sgn * np.cross(N_, Tt)
        s_n[i] = (nn @ Tt, nn @ Bt, max(nn @ N_, 0.05))
    s_n /= np.linalg.norm(s_n, axis=1, keepdims=True)
    log(f"shell: {len(sP)} texels, {hits} hits {time.time() - t0:.1f}s")
    g["bc"][s_ii] = s_bc
    g["rough"][s_ii] = s_r
    g["metal"][s_ii] = 0.0
    g["m0"] |= sm
    g["cov"] |= sm
    shell_n = (s_ii, s_n)
    shell_ao = (s_ii, s_ao)
    # ---------------------------------------------------------------- compose + write
    for atlas, stem in (("steel", "T_Katana_Steel"), ("grip", "T_Katana_Grip")):
        d = painted[atlas]
        m0, cov = d["m0"], d["cov"]
        ao = np.load(BAKE_DIR / f"{atlas}_AO.npy").astype(np.float32)
        ao = np.clip(ao, 0, 1)
        if atlas == "grip":
            ao[shell_ao[0]] = shell_ao[1]
        hm = edge_extend(d["hmap"], m0)
        pp = edge_extend(d["ppmm"], m0)
        nrm = height_to_normal(hm, pp, m0)
        if atlas == "grip":
            nrm[shell_n[0]] = shell_n[1]
        bc = d["bc"]
        if atlas == "steel":
            # metals: mild cavity darkening of the albedo (Unreal's AO only touches indirect light)
            bc = bc * (0.86 + 0.14 * ao)[..., None]
        bc = edge_extend(bc, m0)
        rough = edge_extend(np.clip(d["rough"], 0.02, 1.0), m0)
        metal = edge_extend(d["metal"], m0)
        ao_e = edge_extend(ao, m0 | (cov & ~m0) if False else m0)
        nrm = edge_extend(nrm, m0)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        enc = nrm * 0.5 + 0.5
        enc[..., 1] = 1.0 - enc[..., 1]             # OpenGL -> DirectX
        flip = lambda a: a[::-1]
        write_png(TEX_DIR / f"{stem}_BC.png", flip(lin2srgb(bc)))
        write_png(TEX_DIR / f"{stem}_ORM.png", flip(np.stack([ao_e, rough, metal], -1)))
        write_png(TEX_DIR / f"{stem}_N.png", flip(enc))
        np.save(WORK / f"paint_{atlas}_cov.npy", cov)
        report[atlas] = {"size": int(m0.shape[0]), "coverage": float(cov.mean()),
                         "bc_mean_linear": [float(v) for v in bc[m0].mean(axis=0)],
                         "rough_mean": float(rough[m0].mean()), "ao_mean": float(ao_e[m0].mean())}
    json.dump(report, open(WORK / "maps_report.json", "w"), indent=1)
    log("maps", json.dumps(report), f"{time.time() - t0:.1f}s")
