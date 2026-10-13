"""SR01 W2c: per-texel painted maps from the bakes (plain Python: numpy + scipy + PIL; the SMG's smg_paint.py method
with the sniper's finishes, sr_surface.FIN / PART_FINISH; spec materials; CRAFT_STUDY 3):

    py -3 -B Scripts/guns/sniper/sr_paint.py [--sets Metal,Chassis,Mag] [--bake DIR] [--tex DIR]
    (SR01_SURFACE_TARGET=scope: the attachment's Scope_Body / Scope_Lens sets)

Every texel knows its 3D point (frame M, mm), normal, part, class and island (bake), so it is painted from its part's
finish. Material families keep their OWN value and roughness (the SMG close-up lesson: not one charcoal for all dark
parts):
  OD Cerakote over aluminium (chassis, butt, pad plate, riser): ceramic orange peel (0.5-1.2 mm cells, a few um) in the
    normal map + a fine grain, satin 0.58-0.68; edge rub along the exposed convex crests (lighter, smoother, continuous
    along the edge, never a blotch on a flat); CHIPS by cause only (sr_surface.CHIP_ZONES: the well lip, the forend
    front / belly / where the folded feet ride, butt toe / heel, guard bottom, tang, comb, the knob's strike):
    small clusters ON sharp convex edges, a dark hard-anodize rim and bright bare aluminium (metal 1) at the core of
    the larger ones, a 0.02 mm coat step in the normal map; burnish (rough -) in the handling zones; dust / grime in
    the recesses;
  hard-anodized black aluminium (rail, bipod body and legs): a cool satin black, fine grain, wear to bright aluminium
    only on the most-handled crests (rail tooth crests at random teeth, leg collars, clamp corners): thin lines, no
    per-tooth repeat (the SMG's fin-like teeth);
  manganese phosphate (receiver, handle, safety, trigger, release, pins, magazine body; the barrel and device darker /
    finer): dead-flat crystalline grain in the normal map, a dry / oiled roughness split, bare steel lines only at the
    named contact edges (sr_surface.STEEL_BRIGHT), soot at the device exit and the bore;
  polished bolt body and inner legs: bare steel (metal 1), fine fore-aft polishing lines, a few darker oil streaks;
  polymer grip: satin moulded skin + its own pebble panel on the sides, polished where the hand sits;
  rubber pad and feet: soft matte, dust in the grooves, scuffed crests;
  scope: matte anodized black, knurl crests read on the turrets, the lens opaque glossy (Q6).
Markings (user 2026-10-13: generic only): S / F letters engraved at the safety; never a maker / model / serial.
Outputs: <tex>/<STEM>_<Set>_{BC,ORM,N}.png (BC sRGB, ORM linear, N DirectX 16-bit), <STEM>_<Set>_Masks.png (half size:
R edge-wear propensity, G handling, B cavity, A refinishable = 1 ONLY on the OD paint). Report: <scratch>/paint/.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_surface as SS  # noqa: E402
from gunlib import paint as PT  # noqa: E402
from gunlib import edgemask as EM  # noqa: E402

GRIP = np.array(SS.GRIP_M, np.float32)
LW = np.array([0.2126, 0.7152, 0.0722], np.float32)
MIN_CHIP_PX = 10


def lin(rgb):
    return PT.srgb_to_lin(np.array(rgb, float)).astype(np.float32)


def log(*a):
    print("[SR01-paint]", *a, flush=True)


def zone_field(P, zones, is_mag=None):
    out = np.zeros(len(P), np.float32)
    for z in zones:
        dd = np.linalg.norm(P - np.array(z["center_M"], np.float32), axis=1)
        f = z["w"] * PT.smoothstep(z["radius"], z["radius"] * 0.3, dd)
        if "side" in z:
            f = f * (np.sign(P[:, 1] + 1e-6) == z["side"])
        if is_mag is not None and "part" in z:
            f = f * (is_mag if z["part"] == "mag" else ~is_mag)
        elif is_mag is not None:
            f = f * ~is_mag
        out = np.maximum(out, f.astype(np.float32))
    return out


def drop_small(mask_k, kk, idx, S, min_px):
    im = np.zeros(S * S, bool)
    im[idx[kk[mask_k]]] = True
    lab, nl = ndi.label(im.reshape(S, S), structure=np.ones((3, 3), int))
    if not nl:
        return mask_k
    sizes = np.bincount(lab.ravel())
    keep = sizes >= min_px
    keep[0] = False
    return mask_k & keep[lab.ravel()[idx[kk]]]


def geo_edges(bake, st, P, tp, N):
    cache = bake / f"{st}_geoedge.npz"
    src = [bake / f"{st}_tris.npz", bake / f"{st}_pos.npy"]
    if cache.exists() and all(cache.stat().st_mtime > f.stat().st_mtime for f in src):
        c = np.load(cache)
        if len(c["ef"]) == len(P):
            return c["ef"], c["eb"], c["dist"]
    t = np.load(bake / f"{st}_tris.npz")
    E, dist = EM.part_fields(t["V"], t["pid"], P, tp, (0.3, 1.0), QN=N)
    np.savez(cache, ef=E[0.3], eb=E[1.0], dist=dist)
    return E[0.3], E[1.0], dist


def glyph_mask(text, h_px=64):
    """A text glyph raster (PIL default font, scaled) -> bool array (rows top-down)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.load_default(size=h_px)
    except TypeError:                                             # older PIL
        font = ImageFont.load_default()
    im = Image.new("L", (h_px * len(text), int(h_px * 1.3)), 0)
    ImageDraw.Draw(im).text((0, 0), text, fill=255, font=font)
    a = np.asarray(im) > 127
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def stamp(P_uv_mm, glyph, origin, height_mm):
    """Texels (2D mm coords) inside a glyph of `height_mm` placed with its bottom-left at origin."""
    gh, gw = glyph.shape
    s = height_mm / gh
    u = (P_uv_mm[:, 0] - origin[0]) / s
    v = (origin[1] + height_mm - P_uv_mm[:, 1]) / s
    ok = (u >= 0) & (u < gw) & (v >= 0) & (v < gh)
    out = np.zeros(len(P_uv_mm), bool)
    out[ok] = glyph[v[ok].astype(int), u[ok].astype(int)]
    return out


def paint(st, meta, bake, tex):
    t0 = time.time()
    d = {k: np.load(bake / f"{st}_{k}.npy") for k in ("pos", "nrm", "ids", "ao")}
    S = d["pos"].shape[0]
    pid = d["ids"][..., 0].astype(np.int32)
    isl = d["ids"][..., 2].astype(np.int32)
    valid = pid > 0
    names = {v: k for k, v in meta["parts"].items()}
    idx = np.nonzero(valid.ravel())[0]
    P = d["pos"].reshape(-1, 3)[idx].astype(np.float32) * 1000.0 + GRIP
    N = d["nrm"].reshape(-1, 3)[idx].astype(np.float32) * 2.0 - 1.0
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
    ao = np.clip(d["ao"].reshape(-1)[idx].astype(np.float32), 0, 1)
    tp = pid.ravel()[idx]
    n = len(idx)
    part = np.array([names.get(int(k), "") for k in range(0, max(names) + 1)], object)
    pk = part[tp]
    fin = np.array([SS.finish_of(x) for x in part], object)[tp]
    if SS.TARGET == "gun":
        fin[(pk == "bolt") & (P[:, 0] < SS.BOLT_SHROUD_X)] = "phos"          # the shroud: phosphate (spec)
    is_mag = np.isin(pk, SS.MAG_PARTS)
    log(st, S, "texels", n, "load %.1fs" % (time.time() - t0))
    ef, eb, dist_e = geo_edges(bake, st, P, tp, N)
    log(st, "edges %.1fs" % (time.time() - t0))

    bc = np.zeros((n, 3), np.float32)
    rough = np.full(n, 0.6, np.float32)
    metal = np.zeros(n, np.float32)
    h = np.zeros(n, np.float32)
    m_edge = np.zeros(n, np.float32)
    m_hand = np.zeros(n, np.float32)
    cav = PT.smoothstep(0.85, 0.35, ao).astype(np.float32)
    refin = np.zeros(n, np.float32)
    info = {}

    expo = PT.smoothstep(0.55, 0.92, ao)
    edge_fine = PT.smoothstep(0.30, 0.80, ef) * (0.6 + 0.4 * PT.smoothstep(0.60, 0.90, ao))
    edge_broad = PT.smoothstep(0.30, 0.90, eb) * (0.6 + 0.4 * PT.smoothstep(0.60, 0.90, ao))
    v_lo = PT.chunked(PT.fbm3, P, 9.0, 3, 1)
    v_mid = PT.chunked(PT.fbm3, P, 2.6, 3, 2)
    flake = PT.chunked(PT.fbm3, P, 1.1, 3, 41)
    along = PT.chunked(PT.fbm3, P, 12.0, 2, 67)
    hz = zone_field(P, SS.POLISH) * (0.85 + 0.15 * PT.chunked(PT.fbm3, P, 6.0, 3, 70))   # (fix round: no mottle)
    cz = zone_field(P, SS.CHIP_ZONES)
    sz = zone_field(P, SS.STEEL_BRIGHT, is_mag=is_mag)
    az = zone_field(P, SS.ANOD_WEAR)
    soot = zone_field(P, SS.SOOT) * (0.55 + 0.45 * v_mid)
    grime = lin(SS.FIN["grime"]["srgb"])
    dust = lin((92, 88, 80))

    def dirt(k, col, r, amt=1.0):
        """recesses darker (occluded skin + grime), dust on the up-facing floors only (no blotches on flats)."""
        ck = cav[k]
        deep = PT.smoothstep(0.55, 0.9, ck) * PT.smoothstep(0.45, 0.70, PT.chunked(PT.fbm3, P[k], 4.0, 2, 99))
        col = col * (1.0 - 0.30 * ck * amt)[:, None]
        a_d = (0.12 * amt * deep * PT.smoothstep(0.15, 0.6, N[k][:, 2]))[:, None]
        col = col * (1.0 - a_d) + dust[None, :] * a_d
        return col, r + 0.10 * ck * amt

    # ---------------------------------------------------------------- OD Cerakote over aluminium
    k = fin == "od"
    if k.any():
        F = SS.FIN["od"]
        kk = np.nonzero(k)[0]
        Pk, Nk = P[k], N[k]
        base = lin(F["srgb"])
        peel = PT.chunked(PT.fbm3, Pk, 0.65, 2, 131)                  # ceramic orange peel
        grain = PT.chunked(PT.vnoise3, Pk / 0.22, 136)                # sprayed fine grain
        # (W2 judge fix round) the peel visible in the normal map (+-14 um at 0.65 mm) and in the sheen (+-0.08 rough
        # on its crests / valleys); the low-frequency colour / roughness clouds down to a trace (they read as blotches)
        var = 1.0 + 0.012 * (v_lo[k] - 0.5) + 0.03 * (peel - 0.5) + 0.025 * (grain - 0.5)
        col = base[None, :] * var[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.45 + 0.08 * (v_lo[k] - 0.5) + 0.3 * (grain - 0.5)) + 0.16 * (peel - 0.5)
        hh = 0.014 * (peel - 0.5) * 2.0 + 0.003 * (grain - 0.5) * 2.0
        # burnish where hands / cheek slide (roughness only: OD keeps its colour, the coat goes satin)
        pol = np.clip(hz[k], 0, 1)
        r = r - 0.12 * pol
        # edge rub: continuous along the crest, varied along the part, lighter + smoother (coat thinned to the primer)
        # (fix round) every exposed edge rubbed (the judges saw none): wider, stronger, the broad edge field too
        rb_w = 0.45 + 0.75 * PT.chunked(PT.fbm3, Pk, 6.0, 2, 134)
        rub = PT.smoothstep(rb_w, rb_w * 0.2, dist_e[k]) * np.maximum(edge_fine[k], 0.6 * edge_broad[k]) * expo[k] * \
            (0.55 + 0.45 * np.maximum(cz[k], pol)) * (0.6 + 0.4 * PT.smoothstep(0.3, 0.7, along[k]))
        rub = np.clip(1.3 * rub, 0, 1).astype(np.float32)
        a_r = (0.9 * rub)[:, None]
        col = col * (1.0 - a_r) + lin(F["rub_srgb"])[None, :] * a_r
        r = r - 0.12 * rub
        # chips by cause: on sharp convex edges, inside the cause zones (+ a rare base rate), in clusters
        wear = SS.CHIP_BASE + (1.0 - SS.CHIP_BASE) * cz[k]
        cfield = PT.chunked(PT.fbm3, Pk, 1.6, 3, 141)
        width = (0.35 + 1.5 * wear * PT.chunked(PT.fbm3, Pk, 3.0, 2, 142)) * (0.5 + 0.5 * expo[k])
        chip = (dist_e[k] < width) & (cfield > 0.82 - 0.26 * wear) & (edge_fine[k] > 0.2) & (expo[k] > 0.35)
        chip = drop_small(chip, kk, idx, S, MIN_CHIP_PX)
        core = chip & (dist_e[k] < 0.55 * width) & (cfield > 0.93 - 0.2 * wear)       # bright aluminium core
        an = lin(SS.FIN["od_chip_anod"]["srgb"])
        col[chip] = an[None, :] * (0.92 + 0.16 * v_mid[k][chip])[:, None]
        r[chip] = SS.FIN["od_chip_anod"]["rough"] + 0.08 * v_mid[k][chip]
        al = lin(SS.FIN["al_bare"]["srgb"])
        col[core] = al[None, :] * (0.94 + 0.08 * v_mid[k][core])[:, None]
        a0, a1 = SS.FIN["al_bare"]["rough"]
        r[core] = a0 + (a1 - a0) * v_mid[k][core]
        met = core.astype(np.float32)
        hh = np.where(chip, -0.02, hh).astype(np.float32)                   # the coat's step
        col, r = dirt(k, col, r)
        bc[k], rough[k], metal[k], h[k] = col, r, met, hh
        m_edge[k] = np.clip(np.maximum(rub, edge_fine[k] * wear), 0, 1)
        m_hand[k] = pol
        refin[k] = np.where(core, 0.0, 1.0)                               # A = 1 on the OD paint only
        info["od"] = {"chip_texels": int(chip.sum()), "bare_al_texels": int(core.sum()),
                      "chip_fraction": round(float(chip.mean()), 5), "rub_texels_gt_0.3": int((rub > 0.3).sum())}

    # ---------------------------------------------------------------- hard-anodized aluminium (+ the scope body)
    for f in ("anod", "scope_anod"):
        k = fin == f
        if not k.any():
            continue
        F = SS.FIN[f]
        kk = np.nonzero(k)[0]
        Pk, Nk, pkk = P[k], N[k], pk[k]
        base = lin(F["srgb"])
        grain = PT.chunked(PT.vnoise3, Pk / 0.18, 150)
        col = base[None, :] * (1.0 + 0.03 * (v_lo[k] - 0.5) + 0.03 * (grain - 0.5))[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.5 + 0.3 * (v_lo[k] - 0.5) + 0.3 * (grain - 0.5))
        hh = 0.002 * (grain - 0.5) * 2.0
        # handled crests: a faint satin rub, then bright aluminium only on the most-worn crests in the zones; the rail
        # teeth wear at RANDOM teeth (a 25 mm along-field gates them), never every tooth alike
        rub = PT.smoothstep(0.35, 0.80, edge_broad[k]) * expo[k] * (0.25 + 0.75 * az[k]) * \
            (0.3 + 0.7 * PT.smoothstep(0.35, 0.75, PT.chunked(PT.fbm3, Pk, 25.0, 2, 151)))
        col = col * (1.0 + 0.9 * rub)[:, None]                 # (fix round) crests rub to a lighter satin
        r = r - 0.12 * rub
        dash = PT.chunked(PT.fbm3, Pk, 4.0, 2, 152)
        wl = (dist_e[k] < 0.25 + 0.30 * az[k]) & (dash > 0.82 - 0.22 * az[k]) & (edge_fine[k] > 0.35) & \
            (expo[k] > 0.5) & (az[k] > 0.10)
        wl = drop_small(wl, kk, idx, S, MIN_CHIP_PX)
        col[wl] = lin(F["wear_srgb"])[None, :] * (0.95 + 0.08 * v_mid[k][wl])[:, None]
        r[wl] = 0.36 + 0.08 * v_mid[k][wl]
        # scope turret knurl: the crests of the modelled knurl read lighter (edge field on the drums)
        if f == "scope_anod":
            kn = (edge_fine[k] > 0.5) & (np.abs(Nk[:, 0]) < 0.4) & (Pk[:, 2] > 80.0)
            col[kn] *= 1.35
            r[kn] -= 0.08
        col, r = dirt(k, col, r)
        bc[k], rough[k], h[k] = col, r, hh
        metal[k] = wl.astype(np.float32)
        m_edge[k] = np.clip(edge_fine[k] * (0.3 + 0.7 * az[k]), 0, 1)
        info[f] = {"bright_wear_texels": int(wl.sum())}

    # ---------------------------------------------------------------- phosphate steel (two families)
    for f in ("phos", "phos_barrel", "phos_device"):
        k = fin == f
        if not k.any():
            continue
        F = SS.FIN[f]
        kk = np.nonzero(k)[0]
        Pk, Nk, pkk = P[k], N[k], pk[k]
        cell = 0.12 if f == "phos" else 0.09
        cry = PT.chunked(PT.vnoise3, Pk / cell, 60)
        col = lin(F["srgb"])[None, :] * (1.0 + 0.02 * (v_mid[k] - 0.5) + 0.07 * (cry - 0.5))[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.4 + 0.4 * (v_lo[k] - 0.5)) + 0.05 * (cry - 0.5) * 2.0
        oily = np.isin(pkk, ["bolt_handle", "barrel", "receiver"])
        # (fix round: "a draped blotch on the barrel") a faint, broad oiled sheen only, no colour step
        oil = 0.35 * PT.smoothstep(0.35, 0.85, PT.chunked(PT.fbm3, Pk, 40.0, 2, 61)) * (0.3 + 0.7 * oily)
        o0, o1 = F["oiled"]
        r = r * (1 - oil) + (o0 + (o1 - o0) * v_mid[k]) * oil
        hh = (0.004 * 2.0 * (cry - 0.5)).astype(np.float32)
        wear = SS.STEEL_BASE + (1.0 - SS.STEEL_BASE) * sz[k]
        rub = PT.smoothstep(0.35, 0.80, edge_broad[k]) * wear * (0.2 + 0.9 * flake[k]) * (0.3 + 1.0 * along[k]) * expo[k]
        a_p = (0.55 * np.clip(rub, 0, 1))[:, None]
        col = col * (1.0 - a_p) + lin((96, 96, 94))[None, :] * a_p
        r = r - 0.14 * rub
        met = np.zeros(int(k.sum()), np.float32)
        if f == "phos":
            dash = PT.chunked(PT.fbm3, Pk, 4.0, 2, 68)
            width = np.clip((0.15 + 0.30 * wear) * (0.4 + 0.6 * expo[k]), 0.0, 1.2)
            chip = (dist_e[k] < width) & (dash > 0.82 - 0.30 * sz[k]) & (edge_fine[k] > 0.25) & (expo[k] > 0.3) & \
                (sz[k] > 0.1)
            chip = drop_small(chip, kk, idx, S, MIN_CHIP_PX)
            col[chip] = lin(F["bare_srgb"])[None, :] * (0.93 + 0.10 * v_mid[k][chip])[:, None]
            b0, b1 = F["bare_rough"]
            r[chip] = b0 + (b1 - b0) * v_mid[k][chip]
            met = chip.astype(np.float32)
            hh = np.where(chip, -0.006, hh).astype(np.float32)
            # the bolt knob: a satin ball, the crown worn smoother (no bare speckle on a round ball)
            knob = (pkk == "bolt_handle") & (Pk[:, 1] < -45.0)
            r[knob] = np.minimum(r[knob], 0.50 + 0.08 * v_mid[k][knob])
            # (W2 look) the ball checkered (a machined knob, not a primitive sphere): crossed triangle waves in the
            # ball's longitude / latitude at ~1.3 mm pitch, 0.06 deep; the crests rubbed lighter and smoother
            kb = SS.KNOB
            ball = knob & (np.linalg.norm(Pk - np.array(kb["centre_M"], np.float32), axis=1) < kb["r"] + 0.6)
            if ball.any():
                q = (Pk[ball] - np.array(kb["centre_M"], np.float32)) / kb["r"]
                lon = np.arctan2(q[:, 2], q[:, 0])
                lat = np.arcsin(np.clip(q[:, 1], -1, 1))
                n_lon = 2.0 * math.pi * kb["r"] / kb["pitch_mm"]
                n_lat = math.pi * kb["r"] / kb["pitch_mm"]
                tri = lambda x: 1.0 - 2.0 * np.abs((x % 1.0) - 0.5)
                a_, b_ = lon / (2 * math.pi) * n_lon, lat / math.pi * n_lat
                chk = np.minimum(tri(a_ + b_), tri(a_ - b_)).astype(np.float32)
                band = PT.smoothstep(0.98, 0.80, np.abs(q[:, 1]))          # the poles stay smooth
                bi = np.nonzero(ball)[0]
                hh[bi] = kb["depth_mm"] * chk * band
                crest = PT.smoothstep(0.6, 0.95, chk) * band
                col[bi] *= (1.0 + 0.35 * crest)[:, None]
                r[bi] = r[bi] - 0.10 * crest + 0.08 * (1 - chk) * band
                info["knob_checker_texels"] = int(ball.sum())
            info["phos"] = {"bare_texels": int(chip.sum())}
            # markings: S / F engraved on the chassis is OD; on the safety lever's outer face a small S-F pictogram
        # soot: device exit / baffle / bore
        s_ = soot[k]
        col = col * (1 - 0.9 * s_)[:, None] + float(SS.FIN["soot"]["lin"]) * (0.9 * s_)[:, None]
        r = r * (1 - s_) + 0.90 * s_
        if f == "phos_barrel" or (pkk == "muzzle_device").any():
            rb = np.hypot(Pk[:, 1], Pk[:, 2])
            bore = np.isin(pkk, ["barrel", "muzzle_device"]) & (rb < 6.5)
            col[bore] *= 0.4
            r[bore] = 0.85
        col, r = dirt(k, col, r, 0.8)
        bc[k], rough[k], metal[k], h[k] = col, r, met, hh
        m_edge[k] = np.clip(edge_fine[k] * wear, 0, 1)
        m_hand[k] = np.clip(hz[k], 0, 1)

    # ---------------------------------------------------------------- polished steel (bolt body, inner legs)
    for f in ("bolt_polish", "leg_polish"):
        k = fin == f
        if not k.any():
            continue
        F = SS.FIN[f]
        Pk = P[k]
        l0, l1 = F["lin"]
        lines = PT.chunked(PT.aniso, Pk, (1.0, 0.0, 0.0), 16.0, 0.05, 2, 160)       # fore-aft polishing lines
        streak = PT.smoothstep(0.62, 0.80, PT.chunked(PT.aniso, Pk, (1.0, 0.0, 0.0), 30.0, 1.5, 2, 161))
        val = l0 + (l1 - l0) * v_mid[k]
        col = np.repeat(val[:, None], 3, 1) * np.array([1.0, 1.0, 1.015], np.float32)[None, :]
        col *= (1.0 - 0.12 * streak)[:, None]                                    # oil / carbon streaks
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.2 + 0.8 * lines) + 0.06 * streak
        col, r = dirt(k, col, r, 0.5)
        bc[k], rough[k], metal[k] = col, r, 1.0
        h[k] = 0.0015 * (lines - 0.5) * 2.0
        m_edge[k] = np.clip(edge_fine[k], 0, 1)

    # ---------------------------------------------------------------- polymer grip / floorplate, rubber
    for f in ("polymer", "rubber"):
        k = fin == f
        if not k.any():
            continue
        F = SS.FIN[f]
        Pk, Nk, pkk = P[k], N[k], pk[k]
        fine = PT.chunked(PT.fbm3, Pk, 0.6, 2, 130)
        spark = PT.chunked(PT.vnoise3, Pk / 0.25, 137)
        col = lin(F["srgb"])[None, :] * (1.0 + 0.015 * (v_lo[k] - 0.5) + 0.06 * (fine - 0.5))[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.4 + 0.3 * (v_lo[k] - 0.5) + 0.4 * (spark - 0.5))
        hh = 0.008 * (fine - 0.5) * 2.0 + 0.004 * (spark - 0.5) * 2.0
        if f == "polymer":
            gp = SS.GRIP_PANEL
            panel = (pkk == "grip") & (Pk[:, 2] > gp["z"][0]) & (Pk[:, 2] < gp["z"][1]) & (np.abs(Nk[:, 1]) > gp["abs_ny_min"])
            if panel.any():
                g = Pk[panel][:, [0, 2]] / gp["pitch"]
                # a moulded pyramid texture (two crossed triangle waves) -> its own read, not stipple pebbles
                tri = lambda x: 1.0 - 2.0 * np.abs((x % 1.0) - 0.5)
                pyr = np.minimum(tri(g[:, 0] + g[:, 1]), tri(g[:, 0] - g[:, 1])).astype(np.float32)
                ht = gp["height"][0] + (gp["height"][1] - gp["height"][0]) * PT.chunked(PT.fbm3, Pk[panel], 3.0, 2, 502)
                hh[panel] = ht * pyr
                r[panel] = 0.70 + 0.10 * PT.chunked(PT.fbm3, Pk[panel], 2.0, 2, 503) - 0.10 * pyr * hz[k][panel]
                col[panel] *= (1.08 + 0.10 * pyr)[:, None]
                info["grip_panel_texels"] = int(panel.sum())
            pol = np.clip(hz[k], 0, 1)
            r = r - 0.10 * pol
            cl = PT.smoothstep(0.25, 0.85, pol)
            r = r * (1.0 - cl) + np.minimum(r, F["rough_hand"] + 0.06 * (1 - pol)) * cl
            m_hand[k] = pol
        # scuffed crests (rubber greys, polymer rubs lighter), no blotches on flats
        rb = PT.smoothstep(0.35, 0.1, dist_e[k]) * edge_fine[k] * expo[k] * \
            (0.4 + 0.6 * PT.smoothstep(0.3, 0.7, PT.chunked(PT.fbm3, Pk, 8.0, 2, 135)))
        col = col * (1.0 - 0.5 * rb)[:, None] + lin((78, 78, 78))[None, :] * (0.5 * rb)[:, None]
        r = r - (0.12 if f == "polymer" else 0.04) * rb
        col, r = dirt(k, col, r, 1.0 if f == "rubber" else 0.8)
        bc[k], rough[k], metal[k], h[k] = col, r, 0.0, hh
        m_edge[k] = np.clip(rb, 0, 1)

    # ---------------------------------------------------------------- lens (opaque glossy, Q6)
    k = fin == "lens"
    if k.any():
        F = SS.FIN["lens"]
        r0, r1 = F["rough"]
        bc[k] = lin(F["srgb"])[None, :]
        rough[k] = r0 + (r1 - r0) * v_mid[k]
        metal[k] = 0.0

    # ---------------------------------------------------------------- markings (generic: S / F at the safety)
    if SS.TARGET == "gun" and st == "Chassis":
        m = SS.MARKINGS["safety_S_F"]
        sel = (pk == "chassis") & (N[:, 1] < -0.8) & (P[:, 1] < m["center_M"][1] + 0.5) & \
            (np.abs(P[:, 0] - m["center_M"][0]) < 14) & (np.abs(P[:, 2] - m["center_M"][2]) < 3.0)
        if sel.any():
            Q = P[sel][:, [0, 2]]
            Q[:, 0] = -Q[:, 0]                                      # seen from the right (-Y): +X runs to the left
            cx, cz = -m["center_M"][0], m["center_M"][2]
            hm = m["height_mm"]
            gS, gF = glyph_mask("S"), glyph_mask("F")
            inS = stamp(Q, gS, (cx - 5.5 - hm * gS.shape[1] / gS.shape[0], cz - hm / 2), hm)
            inF = stamp(Q, gF, (cx + 5.5, cz - hm / 2), hm)
            mk = inS | inF
            si = np.nonzero(sel)[0][mk]
            bc[si] = lin((150, 150, 140))[None, :]                   # engraved, paint-filled light grey
            rough[si] = 0.62
            h[si] = -0.03
            info["markings_texels"] = int(len(si))

    # ---------------------------------------------------------------- limits (B9 / G7)
    is_m = metal > 0.5
    metal = np.where(is_m, 1.0, 0.0).astype(np.float32)
    lo_d = PT.srgb_to_lin(np.array([30.0]))[0]
    lum_ = bc @ LW
    bc_d = bc * np.maximum(1.0, lo_d / np.maximum(lum_, 1e-6))[:, None]
    bc = np.where(is_m[:, None], np.maximum(bc, PT.srgb_to_lin(np.array([150.0]))[0]), bc_d)
    bc = np.clip(bc, 0.0, PT.srgb_to_lin(np.array([243.0]))[0])
    rough = np.clip(rough, 0.05, 0.95)

    def full(vals, ch, fill):
        a = np.empty((S * S, ch) if ch > 1 else S * S, np.float32)
        a[:] = fill
        a[idx] = vals
        return a.reshape((S, S, ch) if ch > 1 else (S, S))
    BC = PT.dilate_fill(full(bc, 3, 0.0), valid, 32)
    R = PT.dilate_fill(full(rough, 1, 0.6), valid, 32)
    M = np.where(PT.dilate_fill(full(metal, 1, 0.0), valid, 32) > 0.5, 1.0, 0.0)
    AO = PT.dilate_fill(full(ao, 1, 1.0), valid, 32)
    Hm = full(h, 1, 0.0)
    pos_mm = d["pos"].astype(np.float32) * 1000.0
    du, dv = PT.mm_per_px(pos_mm, valid, isl)
    nrm = PT.height_to_normal(Hm, np.where(valid, isl, -1), du, dv)
    nrm[~valid] = (0.0, 0.0, 1.0)
    tex.mkdir(parents=True, exist_ok=True)
    stem = f"{SS.STEM}_{st}"
    PT.write_png(tex / f"{stem}_BC.png", PT.lin_to_srgb(BC))
    PT.write_png(tex / f"{stem}_ORM.png", np.stack([AO, R, M], -1))
    PT.write_png16(tex / f"{stem}_N.png", PT.normal_to_dx(nrm))
    MK = np.stack([full(m_edge, 1, 0), full(m_hand, 1, 0), full(cav, 1, 0), full(refin, 1, 0)], -1)
    MK = MK.reshape(S // 2, 2, S // 2, 2, 4).mean((1, 3))
    PT.write_png(tex / f"{stem}_Masks.png", MK, "RGBA")
    rep = {"size": S, "texels_painted": int(n), "seconds": round(time.time() - t0, 1), "finishes": {}, "info": info}
    b8all = PT.lin_to_srgb(bc) * 255.0
    for f in np.unique(fin):
        s = fin == f
        b8 = b8all[s].round()
        diel = metal[s] < 0.5
        rep["finishes"][str(f)] = {
            "texels": int(s.sum()), "metal_fraction": round(float(metal[s].mean()), 5),
            "bc_srgb_dielectric_p1_p50_p99": [float(np.percentile(b8[diel].mean(1), q)) for q in (1, 50, 99)]
            if diel.any() else None,
            "bc_srgb_median_rgb": [float(np.median(b8[diel][:, c])) for c in range(3)] if diel.any() else None,
            "rough_p5_p50_p95": [round(float(np.percentile(rough[s], q)), 3) for q in (5, 50, 95)],
            "refinishable_A_mean": round(float(refin[s].mean()), 4)}
    rep["metallic_values"] = sorted(set(np.unique(M).tolist()))
    tilt = nrm.reshape(-1, 3)[idx][:, 2]
    rep["normal_tilt_gt_1deg_fraction"] = {str(f): round(float((tilt[fin == f] < math.cos(math.radians(1.0))).mean()), 4)
                                           for f in np.unique(fin)}
    # Masks A audit: 1 only on the OD paint (the user colour never tints rubber / polymer / metal)
    rep["masks_A_on_non_od_texels"] = int(((refin > 0.5) & (fin != "od")).sum())
    rep["masks_A_on_od_fraction"] = round(float(refin[fin == "od"].mean()), 4) if (fin == "od").any() else None
    log(st, "DONE %.1fs" % (time.time() - t0), json.dumps(info)[:300])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default=",".join(SS.SETS))
    ap.add_argument("--bake", default=str(SS.SCRATCH / "bake"))
    ap.add_argument("--tex", default=str(SS.TEX))
    ap.add_argument("--rep", default=str(SS.SCRATCH / "paint"))
    a = ap.parse_args()
    bake, tex, rep_dir = Path(a.bake), Path(a.tex), Path(a.rep)
    meta = json.loads((bake / "bake_meta.json").read_text())
    rep_dir.mkdir(parents=True, exist_ok=True)
    rp = rep_dir / "paint_report.json"
    report = json.loads(rp.read_text()) if rp.exists() else {}
    for st in a.sets.split(","):
        report[st] = paint(st, meta, bake, tex)
        rp.write_text(json.dumps(report, indent=1))
    print("[SR01-paint] PAINT_DONE")


if __name__ == "__main__":
    main()
