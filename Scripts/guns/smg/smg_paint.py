"""SMG01 W2c: per-texel painted maps from the bakes (plain Python: numpy + scipy + PIL; the AR-01's rifle_paint.py
method with the SMG's finishes):

    py -3 -B Scripts/guns/smg/smg_paint.py [--sets Metal,Furniture,Mag] [--bake DIR] [--uv DIR] [--tex DIR]

Every texel knows its 3D point (frame M, mm), normal, part, texel class and island (bake), so it is painted from the
part's finish (smg_surface.PART_FINISH; spec materials.finishes / wear_logic; GUN_BUILDING_STUDY 3.3 / 3.4):

  black glass-filled polymer (receiver shells, grip frame, stock, latch button; metallic 0, sRGB 46/47/50, rough
    0.50-0.58 satin, spec R46): a moulded matte surface (EDM-spark class texture at real scale: roughness grain + a faint normal
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
  manganese-phosphate steel (a DIELECTRIC coat, metallic 0, sRGB 40-42, rough 0.70-0.82 dry / 0.58-0.68 oiled, R46):
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
# (W4) moulded micro-texture height amplitudes (mm): (fine 0.6 mm grain, 1.8 mm orange peel) per finish
# (W4b r1) polymer (0.012, 0.020): at 35 cm the grazing tops mirrored the environment as one smooth plane ("a flat
# slab", "untextured clay"); the moulded skin's grain now breaks the reflection up (R45: 0.009 / 0.012)
MICRO = {"polymer": (0.012, 0.020), "polymer_mag": (0.012, 0.018), "rubber": (0.013, 0.008)}
# (W4 resume, the "flat clay" finding) visible real-scale variation: polymer sheen (roughness) at ~30 mm and ~8 mm,
# dust in the deep recesses (polymer), a settled dust film on up-facing faces, the phosphate's mottle gain
# (W4b close-up r1, spec R46) the realism judges (8 / 8 close views fake) read the R45 fields as "large, soft, cloudy
# grey / white blotches ... procedural noise or concrete": low-frequency roughness clouds (30 / 8 mm, +-0.12) and
# albedo clouds (9 / 25 mm, +-22 % / +-25 %) over every flat. Real moulded black polymer is EVEN (reference photos:
# commons_HKUMP45_left, commons_HK_HV_080810_046): its flats change with the light, not in blotches; the variation sits
# at the edges (rub, whitening), the contact points (polish) and the recesses (dust). The clouds come down to a trace,
# the per-texel speckle (0.6 mm, 2 px at 35 cm: "concrete") to a hair; the moulded grain stays in the normal map
SHEEN_BROAD = 0.05           # R45 0.25 (clouds); 0.45 tried earlier (camouflage)
SHEEN_MID = 0.05             # R45 0.22
ALB_LO, ALB_FAR, ALB_FINE = 0.10, 0.06, 0.14     # R45 0.45 / 0.50 / 0.70 (x (fbm - 0.5))
DUST_POLY = 0.8
DUST_FILM = 1.0
PHOS_MOTTLE = 1.2            # R45 1.8
EDGE_RUB_GAIN = 0.35         # (W4b r1) polymer edge rub: up to +35 % linear (~ +6 sRGB levels), rough -0.10
DUST_MIX = 0.30              # (W4b r1) deep-recess dust mixed toward DUST_SRGB
DUST_SRGB = (96, 92, 86)
PHOS_SHEEN = 0.08            # R45 SHEEN_MID 0.22 on the steel too
# (W4b r1) phosphate's crystalline coat in the normal map (parkerizing reads as a dead-flat, finely sparkling charcoal
# against the polymer's smooth satin: the judges' "no steel vs polymer contrast"), +-4 um at a 0.12 mm cell
PHOS_CRYST_H = 0.004


def lin(rgb):
    return PT.srgb_to_lin(np.array(rgb, float)).astype(np.float32)


DUST_LIN = lin(DUST_SRGB)


def log(*a):
    print("[SMG01-paint]", *a, flush=True)


# (W4 review fixes) bare steel: never further than BARE_MAX_DIST from a sharp convex edge; clusters under MIN_BARE_PX
# texels dropped (the review's minimum cluster: ~14 texels at class density)
BARE_MAX_DIST = 1.2
MIN_BARE_PX = 14
PAINT_INFO = {}


def _drop_small(mask_k, kk, idx, S, min_px):
    """mask_k over the set's texels kk (indices into the valid-texel list idx): drop 8-connected texture-space
    clusters smaller than min_px texels."""
    im = np.zeros(S * S, bool)
    im[idx[kk[mask_k]]] = True
    lab, nl = ndi.label(im.reshape(S, S), structure=np.ones((3, 3), int))
    if not nl:
        return mask_k
    sizes = np.bincount(lab.ravel())
    keep = sizes >= min_px
    keep[0] = False
    return mask_k & keep[lab.ravel()[idx[kk]]]


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
        # (W4 review fixes, G15) the moulded-in matte texture at the texel scale the maps can carry (class B/C: 0.1-0.2
        # mm per texel; the study's 0.05-0.15 mm EDM spark sits under it and only shows as roughness): a fine sand
        # grain (0.6 mm, +-9 um) over a soft orange-peel (1.8 mm, +-12 um) in the normal map, the same grain as a
        # +-0.03 roughness and a +-1.5 level albedo speckle; the low-frequency mottle +-3 levels (craft 3: +-4). W1-W3
        # carried +-2.5 um at 0.35 mm (1.7 texels): the normal map was flat but for the stipple (2.3 % of texels tilted
        # vs the AR-01's 24 %) and the polymer read as clay
        fine = PT.chunked(PT.fbm3, Pk, 0.6, 2, 130)
        peel = PT.chunked(PT.fbm3, Pk, 1.8, 2, 131)
        amp_t = MICRO.get(f, MICRO["polymer"])
        var = 1.0 + ALB_LO * (v_lo[k] - 0.5) + 0.04 * (flow - 0.5) + ALB_FAR * (v_far[k] - 0.5) +             ALB_FINE * (fine - 0.5)
        col = base[None, :] * var[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.3 + 0.5 * v_lo[k] + 0.4 * (m_mold - 0.5)) + 0.06 * (fine - 0.5)
        hh = 0.0025 * (m_mold - 0.5) * 2.0 + amp_t[0] * (fine - 0.5) * 2.0 + amp_t[1] * (peel - 0.5) * 2.0
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
                col[stip] *= (1.24 + 0.22 * dome)[:, None]      # (R46: 1.10; L5 grip luma -0.059 with the satin, -0.051 at 1.14)
        # ---- mould parting lines (mid-plane Y = 0 on surfaces crossing it edge-on: grip straps, guard, magwell
        # front / back, stock struts, magazine spine and back): a 0.15 mm flash line, raised 0.02, a hair lighter
        # (W4b r1) only on the straps and narrow faces where a two-half tool parts: the grip / guard / magwell (lower
        # receiver under Z -40), the grip cover, the magazine, the stock's struts (not its hinge head, X >= 218). On
        # the receiver's rear face and the head's top the judges read the 0.15 mm line as a UV seam (both ADS views)
        part_ok = (np.isin(pk[k], ["magazine", "grip_cover"]) | ((pk[k] == "lower_receiver") & (Pk[:, 2] < -40.0)) |
                   ((pk[k] == "stock_frame") & (Pk[:, 0] < 218.0)))
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
            # (W4b r1) blended in, not switched at pol 0.5: the switch drew a hard-edged lighter disc on the fore-end's
            # left side in the 24 cm close-up (a sheen step at the zone's half-weight circle)
            cl = PT.smoothstep(0.25, 0.85, pol)
            r = r * (1.0 - cl) + np.minimum(r, F.get("rough_hand", 0.52) + 0.06 * (1 - pol)) * cl
        # ---- whitening (R): sharp convex edges in the zones, 0.3-1.0 mm bands, broken by flakes
        wk = SS.WHITEN_BASE + (1.0 - SS.WHITEN_BASE) * wz[k]
        band = 0.3 + 0.7 * PT.chunked(PT.fbm3, Pk, 5.0, 2, 94)
        near = PT.smoothstep(band, band * 0.35, dist_e[k])
        # (W4 review fixes, G15) bands broken less (0.14 % of the polymer whitened in W2: the study's corner / lip /
        # well-lip bands were essentially absent): long runs with gaps, the flake field only thinning them
        brk = (0.35 + 0.65 * PT.smoothstep(0.30, 0.55, flake[k])) *             PT.smoothstep(0.22, 0.45, PT.chunked(PT.fbm3, Pk, 9.0, 3, 95))
        white = np.clip(near * edge_fine[k] * 1.8, 0, 1) * wk * brk
        white = np.where(wz[k] > 0.25, white, white * 0.6)                   # outside the zones: fainter
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
        # broad sheen mottle (handled, wiped, dusty areas over ~30 mm) and a wiped / handled field at ~8 mm. (W4 resume:
        # the review renders measured the painted maps only 1.8-3.5 sRGB levels (mean) off a constant per-set clay
        # material under the review light: the moulded surface's sheen is what breaks a real gun's flats up, so the
        # roughness carries visible, real-scale variation (SHEEN_BROAD / SHEEN_MID; 0.45 / 0.25 read as camouflage clouds at
        # hero distance, 0.25 / 0.22 kept); was 0.06 x (fbm - 0.5),
        # +-0.01 in effect)
        r = r + SHEEN_BROAD * (PT.chunked(PT.fbm3, Pk, 30.0, 2, 123) - 0.5) +             SHEEN_MID * (PT.chunked(PT.fbm3, Pk, 8.0, 2, 124) - 0.5)
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
        # (W4 review fixes, craft 3) small light-grey scratches, under 0.2 mm, mostly fore-aft on the receiver sides
        # (and the stock's flats): sparse, in patches, never in cavities
        if f == "polymer":
            sides = np.isin(pk[k], ["upper_receiver", "lower_receiver", "stock_frame"]) & (np.abs(Nk[:, 1]) > 0.8)
            if sides.any():
                Ps = Pk[sides]
                sc = PT.chunked(PT.aniso, Ps, (1.0, 0.0, 0.10), 7.0, 0.14, 2, 132)
                patch = PT.smoothstep(0.52, 0.66, PT.chunked(PT.fbm3, Ps, 16.0, 2, 133))
                scr = np.zeros(int(k.sum()), np.float32)
                scr[sides] = PT.smoothstep(0.79, 0.86, sc) * patch * (ao[k][sides] > 0.8)
                col *= (1.0 + 0.45 * scr)[:, None]
                r = r + 0.03 * scr
                white = np.maximum(white, 0.0 * scr)
        if f == "polymer_mag":
            # the follower: a slightly lighter, glossier polymer than the housing, so it reads in the cavity (review)
            fol = pk[k] == "magazine_follower"
            col[fol] *= 1.35
            r[fol] = r[fol] - 0.12
        # ---- (W4b r1) handling rub on the exposed convex edges (hands, sling, holster, the bench): the moulded skin
        # rubbed to a slightly lighter, smoother band 0.2-0.7 mm wide, varied along the edge and stronger in the
        # handling / whitening zones; this is what draws a real polymer gun's edges at arm's length (the judges: "no
        # edge rub", "the blotches are spread evenly instead of sitting at contact points")
        expo_p = PT.smoothstep(0.60, 0.92, ao[k])
        rb_w = 0.2 + 0.5 * PT.chunked(PT.fbm3, Pk, 6.0, 2, 134)
        rubp = PT.smoothstep(rb_w, rb_w * 0.3, dist_e[k]) * edge_fine[k] * expo_p *             (0.45 + 0.55 * np.maximum(hk, wz[k])) * (0.4 + 0.6 * PT.smoothstep(0.30, 0.70, PT.chunked(PT.fbm3, Pk, 10.0, 2, 135)))
        rubp = np.where(stip, 0.0, np.clip(rubp, 0.0, 1.0)).astype(np.float32)
        col *= (1.0 + EDGE_RUB_GAIN * rubp)[:, None]
        r = r - 0.10 * rubp
        # ---- cavities: dust in the deep ones (lighter, dry), grime in the tight ones
        ck = cav[k]
        deep = PT.smoothstep(0.55, 0.9, ck) * PT.smoothstep(0.45, 0.70, PT.chunked(PT.fbm3, Pk, 4.0, 2, 99))
        dust_w = 0.9 if f in ("rubber", "polymer_mag") else DUST_POLY
        col = col * (1.0 - 0.10 * ck)[:, None]
        # (W4b r1) dust as a dry grey-beige deposit mixed in (was x (1 + 0.44): a darker-than-dust grey)
        a_d = (dust_w * DUST_MIX * deep)[:, None]
        col = col * (1.0 - a_d) + DUST_LIN[None, :] * a_d
        r = r + 0.10 * ck * (1.0 - 0.5 * deep) + 0.08 * deep
        # (W4 resume) a settled dust film on the up-facing faces (the gun is stored and carried): faint, lighter and
        # drier, broken in patches, thinner where hands wipe it (the handling zones) and on the sharp edges
        upf = PT.smoothstep(0.55, 0.95, Nk[:, 2]) * PT.smoothstep(0.55, 0.80, ao[k]) * (1.0 - pol)
        # (W4b r1) the film settles against the inside corners (AO 0.97 -> 0.80), not in 6 mm fbm patches (blotches)
        film = upf * PT.smoothstep(0.97, 0.80, ao[k]) * (0.6 + 0.4 * PT.chunked(PT.fbm3, Pk, 2.0, 2, 125)) * DUST_FILM
        col = col * (1.0 - 0.08 * film)[:, None] + DUST_LIN[None, :] * (0.08 * film)[:, None]
        r = r + 0.10 * film
        # ---- soot (port rear edge on the receiver)
        s_ = soot[k]
        col = col * (1 - 0.6 * s_)[:, None] + float(SS.FIN["soot"]["lin"]) * (0.6 * s_)[:, None]
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
        kk = np.nonzero(k)[0]
        Pk, Nk, pkk = P[k], N[k], pk[k]
        nk = len(kk)
        base = lin(F["srgb"]) * np.array([0.985, 1.0, 1.02], np.float32)     # neutral, B - R +2 (spec samples)
        cry = PT.chunked(PT.vnoise3, Pk / 0.12, 60)                            # crystalline grain at the texel
        knob = (pkk == "charging_handle") & (Pk[:, 1] > SS.KNOB_Y_MIN)
        # (W4 review fixes) the knob's coat even (the 2.6 mm mottle read as camouflage on its ball)
        mott = np.where(knob, 0.25, 1.0).astype(np.float32)
        # (W4 resume) the phosphate's uneven take (parkerizing reads blotchy grey at arm's length): the mottle x 1.8
        var = 1.0 + mott * PHOS_MOTTLE * (0.12 * (v_mid[k] - 0.5) + 0.08 * (v_lo[k] - 0.5)) + 0.05 * (cry - 0.5)
        col = base[None, :] * var[:, None]
        r0, r1 = F["rough"]
        r = r0 + (r1 - r0) * (0.3 + 0.5 * v_lo[k]) + 0.05 * (cry - 0.5) * 2.0
        r = r + PHOS_SHEEN * (PT.chunked(PT.fbm3, Pk, 8.0, 2, 126) - 0.5)       # (W4 resume) handled / oiled sheen
        oily = np.isin(pkk, ["bolt", "bolt_rails", "charging_slide", "barrel"])
        oil = PT.smoothstep(0.45, 0.75, PT.chunked(PT.fbm3, Pk, 12.0, 3, 61)) * (0.4 + 0.6 * oily)
        o0, o1 = F["oiled"]
        r = r * (1 - oil) + (o0 + (o1 - o0) * v_mid[k]) * oil
        col *= (1.0 - 0.08 * oil)[:, None]
        wear = SS.STEEL_BASE + (1.0 - SS.STEEL_BASE) * sz[k]
        expo = PT.smoothstep(0.55, 0.92, ao[k])                 # open faces wear; recesses and slot roots do not
        # rubbed phosphate short of bare steel: thinned, lighter, smoother along the worn edges. (W4) varied along the
        # part (a 12 mm field) so identical rail teeth do not repeat one light frame each (review: a bake pattern)
        along = PT.chunked(PT.fbm3, Pk, 12.0, 2, 67)
        rub = PT.smoothstep(0.35, 0.80, edge_broad[k]) * wear * (0.15 + 0.9 * flake[k]) * (0.25 + 1.1 * along) * expo
        col *= (1.0 + 0.55 * rub)[:, None]
        r = r - 0.08 * rub
        # (W4 review fixes, G7 / G9 / G15) bare steel as CONTINUOUS bright lines on the sharp convex crests (the study's
        # rail slot edges and flank crests, sight ear tops, device rim and slot edges, selector tips, trigger face
        # edges): curvature (the same-side distance to a sharp convex edge) x exposure (AO) x handling (the bright-edge
        # zones), 0.25-0.8 mm wide, in long dashes (a 4 mm field: runs of several mm), never further than 1.2 mm from the
        # edge; clusters under MIN_BARE_PX texels dropped below. W2's hard flecks (196 clusters, median 12 texels, 0.07 %)
        # sparkled as fireflies in the middles of the tooth faces
        dash = PT.chunked(PT.fbm3, Pk, 4.0, 2, 68)
        wfield = PT.chunked(PT.fbm3, Pk, 2.0, 2, 69)
        width = np.clip((0.18 + 0.32 * wear * (0.5 + 0.8 * wfield)) * (0.4 + 0.6 * expo), 0.0, BARE_MAX_DIST)
        chip = (dist_e[k] < width) & (dash > 0.80 - 0.34 * sz[k]) & (edge_fine[k] > 0.25) & (expo > 0.3)
        # where hands and gear actually rub: the rails' tooth crests and dovetail flanks, not the base flange's edges
        # along the receiver (a dashed white line there in the dev renders); the device's front rim, not its slot
        # edges (carbon-black, the soot gradient below)
        top_r = pkk == "top_rail"
        chip &= ~(top_r & (Pk[:, 2] < SS.RAIL_TOP_Z - 3.6))
        # (W4b r1) the top rail is the player's view (FP / ADS): bare only on the most-worn crests (the judges: white
        # specks / fireflies on the rail teeth at 35 cm); the rest of its edges rubbed phosphate (below)
        chip &= ~(top_r & (dash < 0.88 - 0.20 * sz[k]))
        low_r = pkk == "lower_rail"
        chip &= ~(low_r & (Pk[:, 2] > SS.RAIL_LOW_Z + 3.6))
        chip &= ~((pkk == "muzzle_device") & (Pk[:, 0] < SS.X_MUZ - 1.2))
        # the trigger face and the paddle face: rubbed satin where the finger rests (no white flecks)
        face = np.zeros(nk, bool)
        trg = pkk == "trigger"
        if trg.any():
            face[trg] = (Nk[trg][:, 0] > 0.6) & (Pk[trg][:, 2] < -45.0) & (Pk[trg][:, 2] > -70.0)
        pad = pkk == "mag_release"
        if pad.any():
            face[pad] = Nk[pad][:, 0] < -0.6
        fr = PT.chunked(PT.fbm3, Pk, 0.8, 3, 66)
        col *= (1.0 + 0.7 * face * PT.smoothstep(0.30, 0.70, fr))[:, None]
        r = r - 0.16 * face
        # the knob (CRAFT 2.3: a satin dark knob with a polished crown and a bright rim): the flat crown (dia 7.0) worn
        # to a smooth satin (rough 0.45-0.55, the coat thinned), a thin continuous bright ring just outside its edge
        # (normals 18-26 deg off the knob axis: the crown edge is 20.7 deg, under the 25 deg sharp-edge rule)
        crown = knob & (Nk[:, 1] > 0.955)
        rim = knob & (Nk[:, 1] > 0.895) & (Nk[:, 1] <= 0.955)
        col[crown] *= 1.32
        r[crown] = 0.45 + 0.10 * v_mid[k][crown]
        chip &= ~knob
        chip |= rim
        # the selector's thumb arcs (both levers; the right-hand thumb on the left, the index finger on the right):
        # the levers' outer faces polished in the handling zones
        selp = (pkk == "selector") & (np.abs(Nk[:, 1]) > 0.7)
        sp_ = np.where(selp, hz[k], 0.0).astype(np.float32)
        col *= (1.0 + 0.30 * sp_)[:, None]
        r = r - 0.12 * sp_
        # sliding polish: the bolt's flanks where they ride the rails (inside the receiver)
        slide = (pkk == "bolt") & (np.abs(Nk[:, 1]) > SS.BOLT_SLIDE["normal_y_min"]) & (Pk[:, 2] < -1.5) & \
            (Pk[:, 2] > -9.5)
        sp = PT.chunked(PT.aniso, Pk, (1.0, 0.0, 0.0), 14.0, 0.25, 2, 65)
        slide &= sp > 0.42
        chip &= ~slide
        # the chamber mouth (W4): the breech's 45 deg chamfer rubbed bright satin by the rounds, its outer rim bare
        brl = pkk == "barrel"
        rad_b = np.hypot(Pk[:, 1], Pk[:, 2] - SS.BORE_Z_B - SS.GRIP_M[2])
        cham = brl & (Pk[:, 0] < SS.BREECH_X + 0.75) & (rad_b > SS.R_BORE - 0.1) & (rad_b < SS.R_BORE + 0.7)
        col[cham] *= 1.55
        r[cham] = 0.42 + 0.08 * v_mid[k][cham]
        chip |= brl & (Pk[:, 0] < SS.BREECH_X + 0.15) & (rad_b > SS.R_BORE + 0.5) & (rad_b < SS.R_BORE + 0.95)
        # the rear sight's windage drum: straight knurl on its rim (CRAFT 2.13: fine knurl in the normal map), 0.55 mm
        # pitch, 0.05 deep, the crests rubbed lighter
        hh = (PHOS_CRYST_H * 2.0 * (cry - 0.5)).astype(np.float32)          # (W4b r1) the crystalline coat
        drum = (pkk == "sight_rear_leaf") & (Pk[:, 1] > SS.DRUM_Y[0]) & (Pk[:, 1] < SS.DRUM_Y[1]) & \
            (np.abs(Nk[:, 1]) < 0.35)
        n_drum = 0
        if drum.any():
            Pd, Nd = Pk[drum], Nk[drum]
            c = np.median((Pd - Nd * SS.DRUM_R)[:, [0, 2]], axis=0)
            rr = np.hypot(Pd[:, 0] - c[0], Pd[:, 2] - c[1])
            ok = np.abs(rr - SS.DRUM_R) < 0.2
            ang = np.arctan2(Pd[:, 2] - c[1], Pd[:, 0] - c[0])
            nt = int(round(2.0 * math.pi * SS.DRUM_R / SS.KNURL_PITCH))
            ph = (ang / (2.0 * math.pi) * nt) % 1.0
            tri = (1.0 - 2.0 * np.abs(ph - 0.5)).astype(np.float32)          # 1 at the crest, 0 in the groove
            dsel = np.nonzero(drum)[0][ok]
            hh[dsel] = SS.KNURL_DEPTH * tri[ok]          # (the knurl replaces the coat's grain on the rim)
            crest = PT.smoothstep(0.65, 0.95, tri[ok])
            col[dsel] *= (1.0 + 0.35 * crest)[:, None]
            r[dsel] = r[dsel] - 0.10 * crest
            n_drum = int(ok.sum())
        # drop bare clusters smaller than MIN_BARE_PX texels (no isolated sparkle); by-design faces kept
        chip = _drop_small(chip, kk, idx, S, MIN_BARE_PX)
        bare_all[k] = chip | slide
        col[chip] = bare[None, :] * (0.93 + 0.10 * v_mid[k][chip])[:, None]
        if slide.any():
            col[slide] = bare[None, :] * (0.95 + 0.06 * v_mid[k][slide])[:, None]
        b0, b1 = SS.FIN["bare"]["rough"]
        s0, s1 = SS.FIN["bare"]["sliding"]
        r = np.where(chip, b0 + (b1 - b0) * v_mid[k], r)
        r = np.where(slide, s0 + (s1 - s0) * sp, r)
        met = np.where(chip | slide, 1.0, 0.0).astype(np.float32)
        hh = np.where(chip | slide, 0.0, hh)                                     # bare steel: no coat grain
        hh = hh + np.where(chip & ~face, -0.008, 0.0).astype(np.float32)          # the coat's step at a chip
        # cavity grime (slot roots, pin surrounds) and soot (device slots and crown, bore mouth): dielectric dirt
        g = np.clip(cav[k] * 0.6, 0, 1)
        tr = SS.RAIL_TOP_Z - SS.RAIL_SLOT_D
        lr = SS.RAIL_LOW_Z + SS.RAIL_SLOT_D
        root = ((pkk == "top_rail") & (Pk[:, 2] < tr + 1.0) & (Pk[:, 2] > tr - 0.4) & (np.abs(Pk[:, 1]) < 10.7)) | \
            ((pkk == "lower_rail") & (Pk[:, 2] > lr - 1.0) & (Pk[:, 2] < lr + 0.4) & (np.abs(Pk[:, 1]) < 10.7))
        g = np.maximum(g, root * (0.55 + 0.35 * v_mid[k]))
        s_ = soot[k].copy()
        # (W4 review fixes, G11) the muzzle device's carbon: the inner cage faces and the bore, the slot walls, a ring
        # on the crown / front face round the bore, a gradient out from each slot's edge on the outside
        dev = pkk == "muzzle_device"
        if dev.any():
            Pd, Nd = Pk[dev], Nk[dev]
            ry, rz = Pd[:, 1], Pd[:, 2] - SS.BORE_Z_B - SS.GRIP_M[2]
            rr = np.maximum(np.hypot(ry, rz), 1e-6)
            ndot = (Nd[:, 1] * ry + Nd[:, 2] * rz) / rr
            inslot = (Pd[:, 0] > SS.DEV_SLOT_X[0] - 0.5) & (Pd[:, 0] < SS.DEV_SLOT_X[1] + 0.5)
            inner = ndot < -0.4
            wall = (np.abs(ndot) < 0.55) & inslot & (np.abs(Nd[:, 0]) < 0.7)
            front = (Nd[:, 0] > 0.8) & (Pd[:, 0] > SS.X_MUZ - 1.5)
            ring = front * PT.smoothstep(10.5, 7.0, rr)
            grad = inslot * (ndot > 0.5) * PT.smoothstep(2.6, 0.2, dist_e[k][dev])
            vv = 0.75 + 0.25 * v_mid[k][dev]
            sd = np.maximum.reduce([inner * 0.95 * vv, wall * 0.9 * vv, ring * 0.85 * vv, grad * 0.7 * vv])
            s_[dev] = np.maximum(s_[dev], sd)
        soot_lin = float(SS.FIN["soot"]["lin"])
        dirt = (met > 0.5) & ((g * (0.6 + 0.8 * v_mid[k]) > 0.45) | (s_ > 0.45))
        met = np.where(dirt, 0.0, met)
        col = np.where(dirt[:, None], grime[None, :] * (0.85 + 0.3 * v_mid[k][:, None]), col)
        isd = met < 0.5
        col = np.where(isd[:, None], col * (1 - g)[:, None] + grime[None, :] * g[:, None], col)
        col = np.where(isd[:, None], col * (1 - 0.92 * s_)[:, None] + soot_lin * (0.92 * s_)[:, None], col)
        r = r + 0.20 * g
        r = np.where(isd, r * (1 - s_) + 0.90 * s_, r)
        # the bore: soot deepening inward (the chamber mouth's chamfer excluded: it is rubbed bright)
        if brl.any():
            inner_b = brl & (rad_b < 6.5) & ~cham
            col[inner_b] *= 0.45
        bc[k] = col
        rough[k] = r
        metal[k] = met
        h[k] = hh
        m_edge[k] = np.clip(edge_fine[k] * wear, 0, 1)
        # (W4 review fixes) the handling mask on the metal too (Masks G): trigger / paddle faces, knob crown, selector
        # thumb arcs, the handling zones (W2 wrote it for the polymer only: G = 0 on every Metal texel)
        m_hand[k] = np.clip(np.maximum.reduce([hz[k], face * 1.0, crown * 1.0, sp_]), 0, 1)
        refin[k] = np.where(met > 0.5, 0.0, 1.0)
        sight = np.isin(pkk, list(SS.SIGHT_PARTS))
        refin[kk[sight]] = 0.0
        PAINT_INFO[st] = {"drum_knurl_texels": n_drum, "knob_crown_texels": int(crown.sum()),
                          "knob_rim_bare_texels": int((rim & chip).sum()), "chamber_mouth_texels": int(cham.sum())}

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
    # (W4 review fixes) the polymer's surface statistics the review measured: BC standard deviation (sRGB levels, per
    # finish, dielectric texels), the share of texels whose normal tilts > 1 deg from flat (the moulded texture)
    b8 = PT.lin_to_srgb(bc) @ LW * 255.0
    rep["bc_std_srgb_levels"] = {str(f): round(float(np.std(b8[(fin == f) & (metal < 0.5)])), 2)
                                 for f in np.unique(fin) if ((fin == f) & (metal < 0.5)).any()}
    tilt = nrm.reshape(-1, 3)[idx][:, 2]
    rep["normal_tilt_gt_1deg_fraction"] = {str(f): round(float((tilt[fin == f] < math.cos(math.radians(1.0))).mean()), 4)
                                           for f in np.unique(fin)}
    rep["normal_tilt_gt_1deg_fraction_set"] = round(float((tilt < math.cos(math.radians(1.0))).mean()), 4)
    rep["info"] = PAINT_INFO.get(st, {})
    rep["masks_g_handling_fraction"] = {str(f): round(float((m_hand[fin == f] > 0.05).mean()), 4) for f in np.unique(fin)}
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
        # (W4 review fixes) bare steel as LINES: the widest point of any bare cluster (2 x the distance transform's
        # maximum, mm; a line, not a patch: <= 1.6), the smallest cluster (texels; >= MIN_BARE_PX), bare texels further
        # than BARE_MAX_DIST from a same-side sharp convex edge (outside the by-design faces and the knob's rim)
        bimg = img(bare_all & ph & ~np.isin(pk, ["bolt"]))
        lab, nl = ndi.label(bimg, structure=np.ones((3, 3), int))
        if nl:
            mmpx = np.sqrt(np.maximum(area, 1e-12))
            edt = ndi.distance_transform_edt(bimg)
            wmax = ndi.maximum(edt * mmpx, lab, index=np.arange(1, nl + 1))
            sizes = np.bincount(lab.ravel())[1:]
            out["bare_line_width_max_mm"] = round(float(2.0 * np.max(wmax)), 3)
            out["bare_clusters"] = int(nl)
            out["bare_cluster_min_texels"] = int(sizes.min())
            out["bare_cluster_median_texels"] = int(np.median(sizes))
        knob_rim = (pk == "charging_handle") & (P[:, 1] > SS.KNOB_Y_MIN)
        far = bare_all & ph & (dist_e > BARE_MAX_DIST + 0.05) & ~np.isin(pk, ["bolt"]) & ~knob_rim
        out["bare_texels_far_from_edge"] = int(far.sum())
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
