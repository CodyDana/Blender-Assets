"""SMG01 W2c: per-texel painted maps from the bakes (plain Python: numpy + scipy + PIL; the AR-01's rifle_paint.py
method with the SMG's finishes):

    py -3 -B Scripts/guns/smg/smg_paint.py [--sets Metal,Furniture,Mag] [--bake DIR] [--uv DIR] [--tex DIR]

Every texel knows its 3D point (frame M, mm), normal, part, texel class and island (bake), so it is painted from the
part's finish (smg_surface.PART_FINISH; spec materials.finishes / wear_logic; GUN_BUILDING_STUDY 3.3 / 3.4):

  black glass-filled polymer (receiver shells, grip frame, stock, latch button; metallic 0, sRGB 46/47/50, rough
    0.58-0.66): a moulded matte surface (EDM-spark class texture at real scale: roughness grain + a faint normal
    grain), faint flow mottle, mould parting lines where a two-half tool parts (the stock's and the grip / guard /
    magwell mid-plane), the grip's stipple panels (pebbles 0.5-0.8 mm pitch, 0.10-0.15 mm tall: normal + cavity,
    rough 0.78-0.88, crowns polished in the hand), and wear that never shows metal: POLISH where hands slide (rough
    -0.10..-0.18, base -2 levels: grip straps and web, fore-end belly and left side, magwell flare, cheek weld,
    selector arcs, latch button) and stress WHITENING on struck sharp edges (base +15..+35 levels, rough +0.05, 0.3-1.0
    mm bands broken by flakes: corners, front-face rim, fore-end lower edge, vent / port lips, magwell lip, guard
    bottom, grip base lip, butt toe / heel, magazine floor-plate corners and lips); insertion scratches into the
    magwell mouth and on the magazine's upper body; dust in the deep cavities (ladder floors, pad rib roots), grime
    in the tight ones;
  polymer magazine (sRGB 41/42/45, rough 0.55-0.65), the same rules on its own zones;
  rubber butt pad (sRGB 42/42/44, rough 0.82-0.92): dust in the rib roots, scuffed toe and heel;
  manganese-phosphate steel (a DIELECTRIC coat, metallic 0, sRGB 48-54, rough 0.66-0.80 dry / 0.55-0.65 oiled):
    crystalline mottle, oil on the bolt and its rails, and wear to BARE steel (metallic 1, sRGB ~194, rough
    0.25-0.40) only in hard flecks on sharp convex edges where the spec puts bright edges (rail slot edges and flank
    crests, sight ears, device rim, knob crown, selector tips, trigger face, paddle face); the bolt's flanks polished
    bare where they slide (rough 0.15-0.25); soot in the device slots and crown, light at the port's rear edge;
  normal map: painted height (stipple, parting lines, mould grain, chip steps) -> tangent space per texel's own UV
    frame (island-aware), DirectX, 16-bit.

Same-side geometric edge masks (gunlib.edgemask) from the first paint; bare steel only within 0.6 mm of a real sharp
convex edge (1.2 mm in a wear zone); polymer whitening only within its band of a real sharp convex edge.
Outputs: <tex>/T_SMG01_<Set>_{BC,ORM,N}.png (BC sRGB, ORM linear R AO / G rough / B metal, N DirectX 16-bit),
T_SMG01_<Set>_Masks.png (half size; R edge-wear propensity, G handling, B cavity, A refinishable). Report:
scratch/paint/paint_report.json (+ the wear audits).
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
from smg_common import ROOT, SCRATCH, dims  # noqa: E402

import smg_surface as SS  # noqa: E402
from gunlib import paint as PT  # noqa: E402
from gunlib import edgemask as EM  # noqa: E402

GRIP = np.array(SS.GRIP_M, np.float32)
LW = np.array([0.2126, 0.7152, 0.0722], np.float32)
GEOEDGE_VERSION = 1


def lin(rgb):
    return PT.srgb_to_lin(np.array(rgb, float)).astype(np.float32)


def log(*a):
    print("[SMG01-paint]", *a, flush=True)


def zone_field(P, zones, part_names=None, is_mag=None):
    """max_z w_z x smoothstep falloff over the zones (frame M centres); 'side' limits a zone to one half (+1 left /
    -1 right), 'part' == 'mag' to the magazine's texels (else the gun's)."""
    out = np.zeros(len(P), np.float32)
    for z in zones:
        dd = np.linalg.norm(P - np.array(z["center_M"], np.float32), axis=1)
        f = z["w"] * PT.smoothstep(z["radius"], z["radius"] * 0.3, dd)
        if "side" in z:
            f = f * (np.sign(P[:, 1] + 1e-6) == z["side"])
        if is_mag is not None:
            f = f * (is_mag if z.get("part") == "mag" else ~is_mag)
        out = np.maximum(out, f.astype(np.float32))
    return out


def worley_domes(Q2, pitch, seed):
    """Pebble field on 2D points (mm): jittered cells of size `pitch`; returns (height 0..1 dome, cell id hash)."""
    g = Q2 / pitch
    i = np.floor(g).astype(np.int64)
    best = np.full(len(Q2), 9.0, np.float32)
    rad = np.zeros(len(Q2), np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = i[:, 0] + dx, i[:, 1] + dy
            jx = PT._hash(cx, cy, np.zeros_like(cx), seed)
            jy = PT._hash(cx, cy, np.ones_like(cx), seed)
            rr = 0.36 + 0.12 * PT._hash(cx, cy, np.full_like(cx, 2), seed)        # dome radius / pitch
            px = cx + 0.15 + 0.7 * jx
            py = cy + 0.15 + 0.7 * jy
            d = np.hypot(g[:, 0] - px, g[:, 1] - py).astype(np.float32)
            upd = d / rr < best
            best = np.where(upd, d / rr, best)
            rad = np.where(upd, rr, rad)
    h = np.clip(1.0 - best * best, 0.0, 1.0)
    return np.sqrt(h).astype(np.float32)


def geo_edges(bake, st, P, tp, N):
    cache = bake / f"{st}_geoedge.npz"
    src = [bake / f"{st}_tris.npz", bake / f"{st}_pos.npy", bake / f"{st}_ids.npy", bake / f"{st}_nrm.npy"]
    if cache.exists() and all(cache.stat().st_mtime > f.stat().st_mtime for f in src):
        c = np.load(cache)
        if len(c["ef"]) == len(P) and int(c["ver"]) == GEOEDGE_VERSION:
            return c["ef"], c["eb"], c["dist"]
    t = np.load(bake / f"{st}_tris.npz")
    E, dist = EM.part_fields(t["V"], t["pid"], P, tp, (0.3, 1.0), QN=N)
    np.savez(cache, ef=E[0.3], eb=E[1.0], dist=dist, ver=np.int32(GEOEDGE_VERSION))
    return E[0.3], E[1.0], dist


def paint(st, meta, bake, uvd, tex, rep_dir):
    t0 = time.time()
    d = {k: np.load(bake / f"{st}_{k}.npy") for k in ("pos", "nrm", "ids", "edge", "ao")}
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
    del d["edge"]
    n = len(idx)
    part = np.array([names.get(int(k), "") for k in range(0, max(names) + 1)], object)
    pk = part[tp]
    fin = np.array([SS.finish_of(x) for x in part], object)[tp]
    is_mag = np.isin(pk, SS.MAG_PARTS)
    log(st, S, "texels", n, "load %.1fs" % (time.time() - t0))
    ef, eb, dist_e = geo_edges(bake, st, P, tp, N)
    log(st, "edges %.1fs" % (time.time() - t0))

    bc = np.zeros((n, 3), np.float32)
    rough = np.zeros(n, np.float32)
    metal = np.zeros(n, np.float32)
    h = np.zeros(n, np.float32)
    m_edge = np.zeros(n, np.float32)
    m_hand = np.zeros(n, np.float32)
    cav = PT.smoothstep(0.85, 0.35, ao).astype(np.float32)
    refin = np.ones(n, np.float32)

    # ---------------------------------------------------------------- shared fields
    open_ = 0.6 + 0.4 * PT.smoothstep(0.60, 0.90, ao)
    edge_fine = PT.smoothstep(0.30, 0.80, ef) * open_
    edge_broad = PT.smoothstep(0.30, 0.90, eb) * open_
    v_lo = PT.chunked(PT.fbm3, P, 9.0, 3, 1)
    v_mid = PT.chunked(PT.fbm3, P, 2.6, 3, 2)
    v_far = PT.chunked(PT.fbm3, P, 25.0, 2, 4)
    flake = PT.chunked(PT.fbm3, P, 1.1, 3, 41)
    flk = PT.chunked(PT.fbm3, P, 0.7, 3, 44)
    hz = zone_field(P, SS.POLISH, is_mag=is_mag) * (0.55 + 0.45 * PT.chunked(PT.fbm3, P, 6.0, 3, 70))
    wz = zone_field(P, SS.WHITEN, is_mag=is_mag)
    sz = zone_field(P, SS.STEEL_BRIGHT)
    soot = zone_field(P, SS.SOOT) * (0.55 + 0.45 * v_mid)
    grime = lin(SS.FIN["grime"]["srgb"])
    bare = lin(SS.FIN["bare"]["srgb"])
    bare_all = np.zeros(n, bool)
    white_all = np.zeros(n, np.float32)
    log(st, "fields %.1fs" % (time.time() - t0))

    # ---------------------------------------------------------------- polymer, magazine polymer, rubber
    for f in ("polymer", "polymer_mag", "rubber"):
        k = fin == f
        if not k.any():
            continue
        F = SS.FIN[f]
        Pk, Nk = P[k], N[k]
        base = lin(F["srgb"])
        m_mold = PT.chunked(PT.fbm3, Pk, 0.35, 2, 90)                     # EDM-spark grain (sub-mm)
        flow = PT.chunked(PT.aniso, Pk, (1.0, 0.0, 0.0), 18.0, 3.0, 3, 91)   # faint moulding flow mottle
        var = 1.0 + 0.045 * (v_lo[k] - 0.5) + 0.025 * (flow - 0.5) + 0.02 * (v_far[k] - 0.5)
        col = base[None, :] * var[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.3 + 0.5 * v_lo[k] + 0.4 * (m_mold - 0.5))
        hh = 0.0025 * (m_mold - 0.5) * 2.0                                   # +-2.5 um moulded grain
        # ---- stipple panels (lower receiver's grip sides, the recessed panel floor at |Y| = 15.45)
        stip = np.zeros(int(k.sum()), bool)
        if f == "polymer":
            ay = np.abs(Pk[:, 1])
            stip = (pk[k] == "lower_receiver") & (np.abs(ay - SS.STIPPLE_FLOOR_Y) < 0.22) & (np.abs(Nk[:, 1]) > 0.85) \
                & (Pk[:, 2] < -44.0) & (Pk[:, 0] > 250.0) & (Pk[:, 0] < 350.0)
            if stip.any():
                Q2 = Pk[stip][:, [0, 2]]
                pitch = 0.5 * (SS.STIPPLE_PITCH[0] + SS.STIPPLE_PITCH[1])
                dome = worley_domes(Q2, pitch, 501)
                ht = SS.STIPPLE_HEIGHT[0] + (SS.STIPPLE_HEIGHT[1] - SS.STIPPLE_HEIGHT[0]) * \
                    PT.chunked(PT.fbm3, Pk[stip], 3.0, 2, 502)
                hh_s = ht * dome
                hh = np.where(stip, 0.0, hh)
                hh[stip] = hh_s
                rs0, rs1 = SS.FIN["stipple"]["rough"]
                crown = PT.smoothstep(0.55, 0.95, dome)
                r_st = rs0 + (rs1 - rs0) * (0.4 + 0.6 * PT.chunked(PT.fbm3, Pk[stip], 2.0, 2, 503))
                # crowns polished by the hand over the WHOLE panel (the palm covers it: a zone falloff drew a smooth
                # blotch), a touch more in the hand zone's core; the pebble field's micro-facets read a lighter grey
                # than the smooth moulding (L5: the sheet's grip panel reads as light as the receiver, 64 vs 64)
                r_st -= (0.10 + 0.04 * hz[k][stip]) * crown
                r[stip] = r_st
                col[stip] *= (1.10 + 0.22 * dome)[:, None]
        # ---- mould parting lines (mid-plane Y = 0 on surfaces crossing it edge-on: grip straps, guard, magwell
        # front / back, stock struts, magazine spine and back): a 0.15 mm flash line, raised 0.02, a hair lighter
        part_ok = np.isin(pk[k], ["lower_receiver", "stock_frame", "magazine", "grip_cover"])
        pl = part_ok & (np.abs(Nk[:, 1]) < 0.35) & ~stip
        plw = PT.smoothstep(0.16, 0.04, np.abs(Pk[:, 1])) * pl * (0.6 + 0.4 * PT.chunked(PT.fbm3, Pk, 4.0, 2, 92))
        hh = hh + 0.02 * plw
        col *= (1.0 + 0.12 * plw)[:, None]
        r = r - 0.04 * plw
        # ---- polish (handling, G): roughness -0.10..-0.18, base -2 levels (x 0.916)
        hk = hz[k]
        pol = np.clip(hk, 0, 1)
        pol = np.where(stip, 0.0, pol)          # the stipple has its own crown polish (no smooth blotch on the panel)
        r = r - (0.10 + 0.08 * PT.chunked(PT.fbm3, Pk, 3.0, 2, 93)) * pol
        col *= (1.0 - 0.084 * pol)[:, None]
        if f == "polymer":
            r = np.where(pol > 0.5, np.minimum(r, F.get("rough_hand", 0.52) + 0.06 * (1 - pol)), r)
        # ---- whitening (R): sharp convex edges in the zones, 0.3-1.0 mm bands, broken by flakes
        wk = SS.WHITEN_BASE + (1.0 - SS.WHITEN_BASE) * wz[k]
        band = 0.3 + 0.7 * PT.chunked(PT.fbm3, Pk, 5.0, 2, 94)
        near = PT.smoothstep(band, band * 0.35, dist_e[k])
        brk = PT.smoothstep(0.38, 0.62, flake[k]) * PT.smoothstep(0.30, 0.55, PT.chunked(PT.fbm3, Pk, 9.0, 3, 95))
        white = np.clip(near * edge_fine[k] * 1.6, 0, 1) * wk * brk
        white = np.where(wz[k] > 0.25, white, white * 0.45)                  # outside the zones: faint
        if f == "rubber":
            white *= 0.6
        lv = 15.0 + 20.0 * PT.chunked(PT.fbm3, Pk, 2.0, 2, 96)              # +15..+35 sRGB levels
        tgt = PT.srgb_to_lin(np.clip(F["srgb"][1] + lv, 0, 255)).astype(np.float32)
        gain = tgt / base[1]
        col *= (1.0 + (gain - 1.0) * white)[:, None]
        r = r + 0.05 * white
        # the sheet's white specks (spec wear_level: 'moderate, as the sheet (white specks and edge scuffs)'): sparse
        # 0.1-0.3 mm abrasion / dust specks in patches, more on the exposed outer faces (high AO), never in cavities
        spk = (PT.chunked(PT.vnoise3, Pk / 0.22, 120) > 0.935) &             (PT.chunked(PT.fbm3, Pk, 20.0, 2, 121) > 0.50) & (ao[k] > 0.8)
        sg = np.where(spk, 0.35 + 0.5 * PT.chunked(PT.fbm3, Pk, 0.5, 1, 122), 0.0).astype(np.float32)
        if f == "rubber":
            sg *= 0.5
        col *= (1.0 + (gain - 1.0) * 0.8 * sg)[:, None]
        r = r + 0.04 * sg
        white = np.maximum(white, sg * 0.0)
        # broad sheen mottle (handled, wiped, dusty areas: roughness +-0.03 over ~30 mm)
        r = r + 0.06 * (PT.chunked(PT.fbm3, Pk, 30.0, 2, 123) - 0.5)
        white_all[k] = white
        # ---- insertion scratches: into the magwell mouth (lower) and on the magazine's upper body
        ins = np.zeros(int(k.sum()), np.float32)
        ax = np.array([math.sin(math.radians(8.27)), 0.0, math.cos(math.radians(8.27))], np.float32)
        if f == "polymer":
            mouth = (pk[k] == "lower_receiver") & (Pk[:, 0] > 405.0) & (Pk[:, 0] < 485.0) & (Pk[:, 2] > -70.0) & \
                (Pk[:, 2] < -40.0)
            if mouth.any():
                sc = PT.chunked(PT.aniso, Pk[mouth], ax, 9.0, 0.06, 2, 97)
                ins[mouth] = PT.smoothstep(0.70, 0.82, sc) * PT.smoothstep(-40.0, -60.0, Pk[mouth][:, 2])
        if f == "polymer_mag":
            up = (pk[k] == "magazine") & (Pk[:, 2] > -110.0)
            if up.any():
                sc = PT.chunked(PT.aniso, Pk[up], ax, 14.0, 0.07, 2, 98)
                ins[up] = PT.smoothstep(0.70, 0.83, sc) * PT.smoothstep(-110.0, -60.0, Pk[up][:, 2]) * \
                    (np.abs(Nk[up][:, 1]) > 0.5)
        col *= (1.0 + 0.35 * ins)[:, None]
        r = r - 0.05 * ins
        # ---- cavities: dust in the deep ones (lighter, dry), grime in the tight ones
        ck = cav[k]
        deep = PT.smoothstep(0.55, 0.9, ck) * PT.smoothstep(0.45, 0.70, PT.chunked(PT.fbm3, Pk, 4.0, 2, 99))
        dust_w = 0.9 if f in ("rubber", "polymer_mag") else 0.45
        col = col * (1.0 - 0.10 * ck)[:, None]
        col = col * (1.0 + dust_w * 0.55 * deep)[:, None]
        r = r + 0.10 * ck * (1.0 - 0.5 * deep) + 0.08 * deep
        # ---- soot (port rear edge on the receiver)
        s_ = soot[k]
        col = col * (1 - 0.6 * s_)[:, None] + 0.022 * (0.6 * s_)[:, None]
        r = r * (1 - s_) + 0.9 * s_
        bc[k] = col
        rough[k] = r
        metal[k] = 0.0
        h[k] = hh
        m_edge[k] = np.clip(np.maximum(white, edge_fine[k] * wk * 0.6), 0, 1)
        m_hand[k] = np.clip(hk, 0, 1)
        refin[k] = 1.0

    # ---------------------------------------------------------------- phosphate steel
    k = fin == "phosphate"
    if k.any():
        F = SS.FIN["phosphate"]
        Pk, Nk, pkk = P[k], N[k], pk[k]
        base = lin(F["srgb"]) * np.array([0.985, 1.0, 1.02], np.float32)     # neutral, B - R +2 (spec samples)
        cry = PT.chunked(PT.vnoise3, Pk / 0.12, 60)                            # crystalline grain at the texel
        var = 1.0 + 0.12 * (v_mid[k] - 0.5) + 0.08 * (v_lo[k] - 0.5) + 0.05 * (cry - 0.5)
        col = base[None, :] * var[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.3 + 0.5 * v_lo[k]) + 0.05 * (cry - 0.5) * 2.0
        oily = np.isin(pkk, ["bolt", "bolt_rails", "charging_slide", "barrel"])
        oil = PT.smoothstep(0.45, 0.75, PT.chunked(PT.fbm3, Pk, 12.0, 3, 61)) * (0.4 + 0.6 * oily)
        o0, o1 = F["oiled"]
        r = r * (1 - oil) + (o0 + (o1 - o0) * v_mid[k]) * oil
        col *= (1.0 - 0.08 * oil)[:, None]
        wear = SS.STEEL_BASE + (1.0 - SS.STEEL_BASE) * sz[k]
        # rubbed phosphate short of a chip: thinned, a touch lighter and smoother along the worn edges
        rub = PT.smoothstep(0.35, 0.80, edge_broad[k]) * wear * (0.25 + 0.9 * flake[k])
        col *= (1.0 + 0.55 * rub)[:, None]
        r = r - 0.08 * rub
        # bare steel: hard flecks ON a sharp convex edge in the bright-edge zones (never a band, never a flat)
        near = (dist_e[k] < 0.6) | ((sz[k] > 0.5) & (dist_e[k] < 1.0))
        clus = PT.smoothstep(0.40, 0.70, PT.chunked(PT.fbm3, Pk, 8.0, 3, 45)) * (0.3 + 0.7 * sz[k])
        amt = edge_fine[k] * (0.35 + 1.2 * wear) * (0.4 + 0.9 * flake[k])
        chip = (amt > 0.86 - 0.10 * sz[k]) & (flk[k] > 0.55) & near & (clus > 0.40)
        # the trigger face and the paddle face: worn bright on their high middle (the finger), not only the edges
        face = np.zeros(int(k.sum()), bool)
        trg = pkk == "trigger"
        if trg.any():
            face[trg] = (Nk[trg][:, 0] > 0.6) & (Pk[trg][:, 2] < -45.0) & (Pk[trg][:, 2] > -70.0) & \
                (PT.chunked(PT.fbm3, Pk[trg], 1.2, 2, 62) > 0.52)
        pad = pkk == "mag_release"
        if pad.any():
            face[pad] = (Nk[pad][:, 0] < -0.6) & (PT.chunked(PT.fbm3, Pk[pad], 1.2, 2, 63) > 0.55)
        knob = (pkk == "charging_handle") & (Pk[:, 1] > 43.0)
        face |= knob & (Nk[:, 1] > 0.85)
        # (dev review: whole white blotches on the trigger face and the knob crown) the finger / palm rubs the
        # phosphate thin and smooth there (lighter, satin) and wears through only in small flecks at the high point
        fr = PT.chunked(PT.fbm3, Pk, 0.8, 3, 66)
        col *= (1.0 + 0.9 * face * PT.smoothstep(0.35, 0.65, fr))[:, None]
        r = r - 0.18 * face
        face = face & (fr > 0.70) & (flk[k] > 0.55)
        chip |= face
        # sliding polish: the bolt's flanks where they ride the rails (inside the receiver)
        slide = (pkk == "bolt") & (np.abs(Nk[:, 1]) > SS.BOLT_SLIDE["normal_y_min"]) & (Pk[:, 2] < -1.5) &             (Pk[:, 2] > -9.5)
        sp = PT.chunked(PT.aniso, Pk, (1.0, 0.0, 0.0), 14.0, 0.25, 2, 65)
        slide &= sp > 0.42
        chip &= ~slide
        bare_all[k] = chip | slide
        col[chip] = bare[None, :] * (0.93 + 0.10 * v_mid[k][chip])[:, None]
        if slide.any():
            col[slide] = bare[None, :] * (0.95 + 0.06 * v_mid[k][slide])[:, None]
        b0, b1 = SS.FIN["bare"]["rough"]
        s0, s1 = SS.FIN["bare"]["sliding"]
        r = np.where(chip, b0 + (b1 - b0) * v_mid[k], r)
        r = np.where(slide, s0 + (s1 - s0) * sp, r)
        met = np.where(chip | slide, 1.0, 0.0).astype(np.float32)
        hh = np.where(chip & ~face, -0.008, 0.0).astype(np.float32)          # the coat's step at a chip
        # cavity grime (slot roots, pin surrounds) and soot (device slots and crown, bore mouth): dielectric dirt
        g = np.clip(cav[k] * 0.6, 0, 1)
        # rail slot roots (spec wear: 'grime in the slot roots'): the slot floors and the tooth walls' lowest mm,
        # oily dirt packed in (the sheet's slots read black; the albedo stops at the PBR floor)
        tr = SS.RAIL_TOP_Z - SS.RAIL_SLOT_D
        lr = SS.RAIL_LOW_Z + SS.RAIL_SLOT_D
        root = ((pkk == "top_rail") & (Pk[:, 2] < tr + 1.0) & (Pk[:, 2] > tr - 0.4) & (np.abs(Pk[:, 1]) < 10.7)) |             ((pkk == "lower_rail") & (Pk[:, 2] > lr - 1.0) & (Pk[:, 2] < lr + 0.4) & (np.abs(Pk[:, 1]) < 10.7))
        g = np.maximum(g, root * (0.55 + 0.35 * v_mid[k]))
        s_ = soot[k]
        dirt = (met > 0.5) & ((g * (0.6 + 0.8 * v_mid[k]) > 0.45) | (s_ > 0.45))
        met = np.where(dirt, 0.0, met)
        col = np.where(dirt[:, None], grime[None, :] * (0.85 + 0.3 * v_mid[k][:, None]), col)
        isd = met < 0.5
        col = np.where(isd[:, None], col * (1 - g)[:, None] + grime[None, :] * g[:, None], col)
        col = np.where(isd[:, None], col * (1 - 0.85 * s_)[:, None] + 0.022 * (0.85 * s_)[:, None], col)
        r = r + 0.20 * g
        r = np.where(isd, r * (1 - s_) + 0.90 * s_, r)
        # the bore: soot deepening inward
        brl = pkk == "barrel"
        if brl.any():
            rad = np.hypot(Pk[brl][:, 1], Pk[brl][:, 2] - SS.BORE_Z_B - SS.GRIP_M[2])
            inner = rad < 6.5
            cb = col[brl]
            cb[inner] *= 0.45
            col[brl] = cb
        bc[k] = col
        rough[k] = r
        metal[k] = met
        h[k] = hh
        m_edge[k] = np.clip(edge_fine[k] * wear, 0, 1)
        refin[k] = np.where(met > 0.5, 0.0, 1.0)
        sight = np.isin(pkk, list(SS.SIGHT_PARTS))
        refin[np.nonzero(k)[0][sight]] = 0.0

    # ---------------------------------------------------------------- limits (gate B9 / G7)
    is_m = metal > 0.5
    metal = np.where(is_m, 1.0, 0.0).astype(np.float32)
    lo_d = PT.srgb_to_lin(np.array([30.0]))[0]
    lum_ = bc @ LW
    bc_d = bc * np.maximum(1.0, lo_d / np.maximum(lum_, 1e-6))[:, None]
    bc = np.where(is_m[:, None], np.maximum(bc, PT.srgb_to_lin(np.array([186.0]))[0]), bc_d)
    bc = np.clip(bc, 0.0, PT.srgb_to_lin(np.array([243.0]))[0])
    rough = np.clip(rough, 0.12, 0.95)

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
    log(st, "paint %.1fs" % (time.time() - t0))
    pos_mm = d["pos"].astype(np.float32) * 1000.0
    du, dv = PT.mm_per_px(pos_mm, valid, isl)
    nrm = PT.height_to_normal(Hm, np.where(valid, isl, -1), du, dv)
    nrm[~valid] = (0.0, 0.0, 1.0)
    audit = wear_audit(S, idx, du, dv, fin, pk, tp, part, bare_all, white_all, dist_e, sz, wz, bc, metal, P, N)
    log(st, "wear audit", json.dumps(audit)[:700])
    del pos_mm
    tex.mkdir(parents=True, exist_ok=True)
    stem = f"T_SMG01_{st}"
    PT.write_png(tex / f"{stem}_BC.png", PT.lin_to_srgb(BC))
    PT.write_png(tex / f"{stem}_ORM.png", np.stack([AO, R, M], -1))
    PT.write_png16(tex / f"{stem}_N.png", PT.normal_to_dx(nrm))
    MK = np.stack([full(m_edge, 1, 0), full(m_hand, 1, 0), full(cav, 1, 0), full(refin, 1, 0)], -1)
    MK = MK.reshape(S // 2, 2, S // 2, 2, 4).mean((1, 3))
    PT.write_png(tex / f"{stem}_Masks.png", MK, "RGBA")
    rep = {"size": S, "texels_painted": int(n), "seconds": round(time.time() - t0, 1), "finishes": {}}
    for f in np.unique(fin):
        s = fin == f
        b8 = (PT.lin_to_srgb(bc[s]) * 255).round()
        rep["finishes"][str(f)] = {
            "texels": int(s.sum()), "metal_fraction": round(float(metal[s].mean()), 5),
            "bc_srgb_dielectric_p1_p50_p99": [float(np.percentile(b8[metal[s] < 0.5].mean(1), q)) for q in (1, 50, 99)]
            if (metal[s] < 0.5).any() else None,
            "bc_srgb_metal_p1_p50_p99": [float(np.percentile(b8[metal[s] > 0.5].mean(1), q)) for q in (1, 50, 99)]
            if (metal[s] > 0.5).any() else None,
            "rough_p5_p50_p95": [round(float(np.percentile(rough[s], q)), 3) for q in (5, 50, 95)]}
    stip_t = (pk == "lower_receiver") & (np.abs(np.abs(P[:, 1]) - SS.STIPPLE_FLOOR_Y) < 0.22) & \
        (np.abs(N[:, 1]) > 0.85) & (P[:, 2] < -44.0) & (P[:, 0] > 250.0) & (P[:, 0] < 350.0)
    if stip_t.any():
        rep["stipple"] = {"texels": int(stip_t.sum()), "area_cm2": round(float((du * dv).reshape(-1)[idx][stip_t].sum())
                                                                        / 100.0, 2),
                          "rough_p5_p50_p95": [round(float(np.percentile(rough[stip_t], q)), 3) for q in (5, 50, 95)],
                          "height_mm_p50_p99": [round(float(np.percentile(h[stip_t], q)), 3) for q in (50, 99)]}
    rep["metallic_values"] = sorted(set(np.unique(M).tolist()))
    rep["wear_audit"] = audit
    log(st, "DONE %.1fs" % (time.time() - t0))
    return rep


def wear_audit(S, idx, du, dv, fin, pk, tp, part, bare_all, white_all, dist_e, sz, wz, bc, metal, P, N):
    """Measured in texture space on the final masks (the AR-01's stage-7 audits, SMG finishes):
      steel: bare texels on phosphate panel interiors (> 2 mm from any same-side sharp convex edge, outside the
        bright-edge zones; gate 0 clusters), the largest connected bare blob (mm2; gate <= 8, the bolt's slide faces
        and the trigger / paddle / knob faces are by design and listed apart);
      polymer: metallic texels (gate 0: polymer never shows metal), whitened texels off an edge (> 1.2 mm from a
        sharp convex edge; gate 0 clusters), the largest whitened blob (mm2, info) and the whitened fraction;
      the charging knob's bare fraction (review: <= 25 %)."""
    out = {}
    area = (du * dv).astype(np.float32)

    def img(m):
        a = np.zeros(S * S, bool)
        a[idx] = m
        return a.reshape(S, S)

    def blobs(m2):
        lab, nl = ndi.label(m2, structure=np.ones((3, 3), int))
        if not nl:
            return 0, 0.0, None
        ar = ndi.sum(area, lab, index=np.arange(1, nl + 1))
        kk = int(np.argmax(ar))
        return int(nl), float(ar[kk]), lab == kk + 1
    ph = fin == "phosphate"
    by_design = np.isin(pk, ["bolt", "trigger", "mag_release", "charging_handle"])
    if ph.any():
        interior = bare_all & ph & (dist_e > 2.0) & (sz < 0.5) & ~by_design
        ni, _a, _ = blobs(img(interior))
        nb, big, bm = blobs(img(bare_all & ph & ~by_design))
        wp = None
        if bm is not None:
            pidimg = np.zeros(S * S, np.int32)
            pidimg[idx] = tp
            wp = str(part[int(np.bincount(pidimg.reshape(S, S)[bm]).argmax())])
        out["steel_bare_texels"] = int((bare_all & ph).sum())
        out["steel_bare_fraction"] = round(float((bare_all & ph).sum() / max(ph.sum(), 1)), 5)
        out["interior_bare_clusters"] = ni
        out["largest_bare_blob_mm2"] = round(big, 2)
        out["largest_bare_blob_part"] = wp
        out["bare_blobs"] = nb
        _n2, big2, _ = blobs(img(bare_all & ph & by_design))
        out["by_design_bare_largest_mm2"] = round(big2, 2)
        knob = (pk == "charging_handle") & (P[:, 1] > 40.0)
        if knob.any():
            out["charging_knob_bare_fraction"] = round(float(bare_all[knob].mean()), 4)
    po = np.isin(fin, list(SS.POLYMER_FIN))
    if po.any():
        out["polymer_metallic_texels"] = int((metal[po] > 0.5).sum())
        wm = white_all > 0.35
        off = wm & po & (dist_e > 1.2)
        no, _a, _ = blobs(img(off))
        nw, bigw, _ = blobs(img(wm & po))
        out["whitened_fraction"] = round(float((wm & po).sum() / max(po.sum(), 1)), 5)
        out["whitened_off_edge_clusters"] = no
        out["whitened_largest_blob_mm2"] = round(bigw, 2)
        lum = bc @ LW
        out["polymer_lum_p50_srgb"] = round(float(PT.lin_to_srgb(np.array([np.median(lum[po])]))[0] * 255), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="Metal,Furniture,Mag")
    ap.add_argument("--bake", default=str(SCRATCH / "bake"))
    ap.add_argument("--uv", default=str(SCRATCH / "uv"))
    ap.add_argument("--tex", default=str(ROOT / "Exports" / "Guns" / "SMG01" / "Textures"))
    ap.add_argument("--rep", default=str(SCRATCH / "paint"))
    a = ap.parse_args()
    bake, uvd, tex, rep_dir = Path(a.bake), Path(a.uv), Path(a.tex), Path(a.rep)
    meta = json.loads((bake / "bake_meta.json").read_text())
    rep_dir.mkdir(parents=True, exist_ok=True)
    rp = rep_dir / "paint_report.json"
    report = json.loads(rp.read_text()) if rp.exists() else {}
    for st in a.sets.split(","):
        report[st] = paint(st, meta, bake, uvd, tex, rep_dir)
        rp.write_text(json.dumps(report, indent=1))
    print("[SMG01-paint] PAINT_DONE")


if __name__ == "__main__":
    main()
