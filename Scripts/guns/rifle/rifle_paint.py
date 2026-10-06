"""AR-01 stage 3c: per-texel painted maps from the bakes (plain Python: numpy + PIL):

    py -3 -B Scripts/guns/rifle/rifle_paint.py [--sets Metal,Furniture,Mag]

Inputs: WorkFiles/guns/rifle/scratch/bake/<Set>_{pos,nrm,ids,edge,ao}.npy (+ Furniture_ckn / _ckm, the checkering).
Every texel knows its 3D point (frame M, mm), normal, part, texel class and island, so it is painted from the part's
finish (rifle_surface.PART_FINISH; rifle_spec materials.finishes; GUN_BUILDING_STUDY 3.3 / 3.4):

  black lacquer over steel (metallic 0, #353535, rough 0.40-0.55) chipped in hard-edged flakes to bare steel (metallic
    1, #C3C3C1, rough 0.25-0.40) on convex edges only (the bevel-normal edge mask x pointiness x AO keeps concave
    corners and flats clean), subtle lacquer value / sheen variation, cavity grime, soot at the brake, gas vents and
    port; the butt plate densely scratched to bare steel; the magazine (#313131) bright on its rib crests and edges
  bluing (metallic 1, #787878, rough 0.30-0.55) on the small parts, worn to bare steel on edges; the carrier's flanks
    polished along their sliding axis
  walnut shellac on the furniture: ONE stain hue x a luminance field (the pack's recolour reproduces it by
    construction), 3D growth rings in a virtual blank along each part's axis, figure, pores along the grain, handling
    wear (finish worn lighter and rougher at the hands, oil-darkened round it), rubbed edges; the grip's checkering from
    the baked normal of the modelled pyramids, its grooves darker
  normal map: painted height (chip steps, scratches, pores) -> tangent space in each texel's own UV frame, blended
    (whiteout) with the checkering bake; DirectX (green flipped)

Outputs (shipped): Exports/Guns/AR01/Textures/T_AR01_<Set>_{BC,ORM,N}.png (BC sRGB, ORM linear: R AO / G roughness /
B metallic, N DirectX 16-bit: an exact flat, so no island-border seams from the 8-bit 128 bias), T_AR01_<Set>_Masks.png (half size; R edge-wear propensity, G handling, B cavity, A
refinishable, GUN_BUILDING_STUDY 5.10). Report: scratch/paint/paint_report.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(HERE))

import rifle_surface as RS  # noqa: E402
from gunlib import paint as PT  # noqa: E402

WORK = ROOT / "WorkFiles" / "guns" / "rifle"
BAKE = WORK / "scratch" / "bake"
REP = WORK / "scratch" / "paint"
TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
GRIP = np.array(RS.GRIP_M)


def lin(rgb):
    return PT.srgb_to_lin(np.array(rgb, float))


def log(*a):
    print("[AR01-paint]", *a, flush=True)


def inside_poly(Q, poly):
    """Even-odd point-in-polygon for many points Q (n, 2) against one closed polygon (m, 2)."""
    x, y = Q[:, 0], Q[:, 1]
    ins = np.zeros(len(Q), bool)
    px, py = poly[:, 0], poly[:, 1]
    j = len(poly) - 1
    for i in range(len(poly)):
        c = ((py[i] > y) != (py[j] > y)) & (x < (px[j] - px[i]) * (y - py[i]) / (py[j] - py[i] + 1e-30) + px[i])
        ins ^= c
        j = i
    return ins


def checker_field_mask(P):
    """Texels whose frame-M point lies inside the modelled checker field's outline (grip_checker.field_outline_xz, side
    plane XZ, both sides): the selected-to-active mask also caught rays from the panel's border band hitting the bake
    source's clip walls (dark blotches along the border); the field outline is the authority."""
    sys.path.insert(0, str(ROOT / "Scripts" / "guns" / "rifle"))
    from parts import grip_checker as GC
    return inside_poly(P[:, [0, 2]], np.asarray(GC.field_outline_xz(0.0), float))


def load(st):
    d = {}
    for k in ("pos", "nrm", "ids", "edge", "ao"):
        d[k] = np.load(BAKE / f"{st}_{k}.npy")
    if st == "Furniture":
        d["ckn"] = np.load(BAKE / "Furniture_ckn.npy").astype(np.float32)
        d["ckm"] = np.load(BAKE / "Furniture_ckm.npy").astype(np.float32)
    return d


def paint(st, meta):
    t0 = time.time()
    d = load(st)
    S = d["pos"].shape[0]
    pid = d["ids"][..., 0].astype(np.int32)
    cls = d["ids"][..., 1].astype(np.int32)
    isl = d["ids"][..., 2].astype(np.int32)
    valid = pid > 0
    names = {v: k for k, v in meta["parts"].items()}
    idx = np.nonzero(valid.ravel())[0]
    P = d["pos"].reshape(-1, 3)[idx].astype(np.float32) * 1000.0 + GRIP.astype(np.float32)     # frame M, mm
    N = d["nrm"].reshape(-1, 3)[idx].astype(np.float32) * 2.0 - 1.0
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-6)
    e1 = d["edge"].reshape(-1, 3)[idx, 0].astype(np.float32)
    e2 = d["edge"].reshape(-1, 3)[idx, 1].astype(np.float32)
    pt = d["edge"].reshape(-1, 3)[idx, 2].astype(np.float32)
    ao = np.clip(d["ao"].reshape(-1)[idx].astype(np.float32), 0, 1)
    tp = pid.ravel()[idx]
    n = len(idx)
    part = np.array([names.get(int(k), "") for k in range(0, max(names) + 1)], object)
    fin_of_part = np.array([RS.PART_FINISH.get(part[k], "lacquer") if part[k] else "lacquer"
                            for k in range(len(part))], object)
    fin = fin_of_part[tp]
    log(st, S, "texels", n, "load %.1fs" % (time.time() - t0))

    bc = np.zeros((n, 3), np.float32)
    rough = np.zeros(n, np.float32)
    metal = np.zeros(n, np.float32)
    h = np.zeros(n, np.float32)                     # painted height (mm) for the normal map
    m_edge = np.zeros(n, np.float32)
    m_hand = np.zeros(n, np.float32)
    cav = PT.smoothstep(0.85, 0.35, ao)             # cavity (low AO)
    m_cav = cav.astype(np.float32)
    refin = np.zeros(n, np.float32)

    # ---------------------------------------------------------------- shared masks
    # convex edges only: a concave corner is occluded by its own neighbour face (low AO), a convex one is open; the
    # vertex pointiness reads > 0.5 on most flats here (fine bevels everywhere), so it only nudges
    convex = PT.smoothstep(0.78, 0.95, ao) * (0.75 + 0.25 * PT.smoothstep(0.50, 0.56, pt))
    v_far = PT.chunked(PT.fbm3, P, 25.0, 2, 4)        # some edges see more handling than others
    edge_fine = PT.smoothstep(0.012, 0.07, e1) * convex
    edge_broad = PT.smoothstep(0.035, 0.16, e2) * convex
    # wear placement (rifle_surface.METAL_WEAR): edges wear where hands, sling, ground and reloads put it, and where
    # the sheet draws its bright edges; elsewhere only the strongest edges chip
    wearz = np.zeros(n, np.float32)
    for z in RS.METAL_WEAR:
        dd = np.linalg.norm(P - np.array(z["center_M"], np.float32), axis=1)
        wearz = np.maximum(wearz, z["w"] * PT.smoothstep(z["radius"], z["radius"] * 0.3, dd))
    wear = RS.WEAR_BASE + (1.0 - RS.WEAR_BASE) * wearz
    # the baked bevel masks light whole bevel strips (sub-mm faces) evenly: real wear is an irregular 0.5-3 mm band
    # (GUN_BUILDING_STUDY 3.4) that bleeds onto the flats. The edge mask is spread ~0.8 mm (sigma, in texels from the
    # set's density) inside the islands (normalised blur), then broken by flake noise at two scales
    e_core = np.maximum(edge_fine, 0.8 * edge_broad)
    E_full = np.zeros(S * S, np.float32)
    E_full[idx] = e_core
    E_full = E_full.reshape(S, S)
    vmask = valid.astype(np.float32)
    # texels per mm at the set's packing scale (uv_report: px per chart unit; class B / C charts at k ~0.8-1)
    px_mm = 0.85 * json.loads((WORK / "scratch" / "uv" / "uv_report.json").read_text())["sets"][st]["pack"][
        "scale_px_per_unit"]
    sig = max(1.0, 0.8 * px_mm)
    num = ndi.gaussian_filter(E_full * vmask, sig)
    den = ndi.gaussian_filter(vmask, sig)
    spread = (num / np.maximum(den, 1e-4)).reshape(-1)[idx]
    del num, den, E_full
    e_band = np.maximum(e_core, np.clip(spread * 2.4, 0.0, 1.0))
    flake = PT.chunked(PT.fbm3, P, 1.1, 3, 41)
    flake_big = PT.chunked(PT.fbm3, P, 5.0, 2, 42)
    edge = e_band * (0.45 + 1.1 * wear) * (0.75 + 0.5 * v_far) * (0.35 + 0.85 * flake + 0.35 * flake_big) / 0.95
    v_lo = PT.chunked(PT.fbm3, P, 9.0, 3, 1)          # broad value / sheen variation
    v_mid = PT.chunked(PT.fbm3, P, 2.6, 3, 2)
    chip_n = PT.chunked(PT.fbm3, P, 0.9, 3, 3)
    soot = np.zeros(n, np.float32)
    for so in RS.SOOT:
        dd = np.linalg.norm(P - np.array(so["center_M"], np.float32), axis=1)
        soot = np.maximum(soot, so["w"] * PT.smoothstep(so["radius"], so["radius"] * 0.25, dd))
    soot *= 0.55 + 0.45 * v_mid
    log(st, "masks %.1fs" % (time.time() - t0))

    bare = lin(RS.FIN["bare"]["srgb"]).astype(np.float32)
    grime = lin(RS.FIN["grime"]["srgb"]).astype(np.float32)

    # ---------------------------------------------------------------- metal finishes
    for f in ("lacquer", "lacquer_cover", "lacquer_mag", "lacquer_worn", "bluing", "bare"):
        sel = fin == f
        if not sel.any():
            continue
        F = RS.FIN[f]
        base = lin(F["srgb"]).astype(np.float32)
        k = sel
        # mottled, used finish (the sheet's receiver and magazine are not one flat value): broad value patches, a
        # faint warm patina in the dirtier ones, finer sheen variation
        var = 1.0 + 0.20 * (v_lo[k] - 0.5) + 0.12 * (v_far[k] - 0.5) + 0.06 * (v_mid[k] - 0.5)
        warm = np.clip((0.55 - v_lo[k]) * 2.0, 0.0, 1.0) * (0.0 if F["metal"] else 1.0)
        # the gas system and barrel run hot and oily: a warm brown cast on their lacquer (the sheet's gas block and
        # barrel read R/B ~1.08 where the receiver reads neutral)
        hot = np.isin(part[tp[k]], RS.HOT_PARTS).astype(np.float32) * (0.0 if F["metal"] else 1.0)
        tint = np.stack([1.0 + 0.035 * warm + 0.08 * hot, np.ones_like(warm), 1.0 - 0.04 * warm - 0.08 * hot], 1)
        col = base[None, :] * var[:, None] * tint
        r0, r1 = F["rough"] if isinstance(F["rough"], tuple) else (F["rough"], F["rough"])
        r = r0 + (r1 - r0) * (0.25 + 0.6 * v_lo[k] + 0.4 * (v_mid[k] - 0.5))
        met = np.full(k.sum(), float(F["metal"]), np.float32)
        # wear: chips on convex edges (lacquer: hard flakes to bare steel; bluing: worn to bare on the high edges)
        if f in ("lacquer", "lacquer_cover", "lacquer_mag"):
            eb = edge_broad[k] * (0.55 + 0.9 * v_far[k]) if f == "lacquer_mag" else 0.0   # mag: bright rib crests
            amt = np.maximum(edge[k], eb) * (0.45 + chip_n[k])
            chip = amt > 0.62
            # rubbed lacquer short of a chip: the coat thinned lighter and glossier along the worn edges
            rub = PT.smoothstep(0.30, 0.62, amt) * (~chip)
            col *= (1.0 + 0.9 * rub)[:, None]
            r = r - 0.06 * rub
            # scuffs (the sheet's long light rubs on the cover, receiver, barrel and magazine): thin streaks along the
            # part's scuff axis in patches, plus short random scratches; light (thinned lacquer), the deepest to bare
            pk_ = part[tp[k]]
            sw = np.array([RS.SCUFF_W.get(x, 0.7) for x in pk_], np.float32)
            Pk = P[k]
            scl = np.zeros(k.sum(), np.float32)
            for axn in set(RS.SCUFF_AXIS.get(x, (1.0, 0.0, 0.0)) for x in np.unique(pk_)):
                gsel = np.array([RS.SCUFF_AXIS.get(x, (1.0, 0.0, 0.0)) == axn for x in pk_])
                scl[gsel] = PT.aniso(Pk[gsel], axn, 16.0, 0.09, 2, 81)
            patch = PT.smoothstep(0.42, 0.72, PT.chunked(PT.fbm3, Pk, 14.0, 3, 83)) * sw
            scr1 = PT.aniso(Pk, (0.62, 0.70, 0.35), 5.0, 0.05, 2, 85)
            scr2 = PT.aniso(Pk, (0.55, -0.60, -0.58), 4.0, 0.05, 2, 86)
            scuff = np.clip(PT.smoothstep(0.66, 0.78, scl) * patch
                            + 0.8 * PT.smoothstep(0.72, 0.82, np.maximum(scr1, scr2)) * np.clip(patch + 0.25, 0, 1),
                            0, 1)
            col *= (1.0 + 1.6 * scuff)[:, None]
            r = r - 0.10 * scuff
            deep = (scuff > 0.85) & (PT.smoothstep(0.80, 0.90, scl) * patch * (0.6 + 0.8 * wear[k]) > 0.55)
            chip |= deep
            # worn-finish mottling (lighter, glossier patches where the coat has thinned) and darker oily patches
            wp = PT.smoothstep(0.58, 0.82, PT.chunked(PT.fbm3, Pk, 22.0, 3, 87)) * np.clip(sw, 0, 1.2)
            col *= (1.0 + 0.55 * wp)[:, None]
            r = r - 0.06 * wp
            oil = PT.smoothstep(0.62, 0.86, PT.chunked(PT.fbm3, Pk, 34.0, 2, 88))
            col *= (1.0 - 0.22 * oil)[:, None]
            r = r - 0.05 * oil
            # pitting in the worn patches: dark specks
            pit = (PT.chunked(PT.vnoise3, Pk / 0.35, 89) > 0.93) & (PT.chunked(PT.fbm3, Pk, 9.0, 2, 90) > 0.6)
            col[pit] *= 0.55
            r = np.where(pit, r + 0.15, r)
            # rare surface nicks on flats (subtle surface wear)
            nick = (PT.chunked(PT.fbm3, Pk, 0.45, 2, 9) > 0.88) & (v_lo[k] > 0.64)
            chip |= nick
            # micro scratches and handling sheen in roughness only (no colour change)
            scr = PT.smoothstep(0.68, 0.80, PT.aniso(Pk, (1.0, 0.0, 0.25), 6.0, 0.18, 2, 12))
            r = r - 0.07 * scr
            hscuff = -0.006 * scuff - 0.02 * pit
            m_edge[k] = np.clip(edge[k], 0, 1)
            refin[k] = 1.0
        elif f == "lacquer_worn":
            # butt plate: densely scratched to bare steel (two scratch directions)
            sc1 = PT.aniso(P[k], (0.0, 0.0, 1.0), 12.0, 0.30, 2, 21)
            sc2 = PT.aniso(P[k], (0.0, 0.7, 0.7), 10.0, 0.30, 2, 22)
            chip = (np.maximum(sc1, sc2) > 0.79) | (edge[k] * (0.5 + chip_n[k]) > 0.55)
            m_edge[k] = np.clip(edge[k] + 0.4, 0, 1)
            refin[k] = 1.0
        elif f == "bluing":
            amt = edge[k] * (0.4 + chip_n[k])
            chip = amt > 0.70
            # bluing thins to a lighter grey before it reaches bare steel (metal stays metal: >= sRGB 110)
            thin = PT.smoothstep(0.35, 0.70, amt) * (~chip)
            col *= (1.0 + 0.45 * thin)[:, None]
            r = r - 0.08 * thin
            m_edge[k] = np.clip(edge[k], 0, 1)
        else:
            chip = np.zeros(k.sum(), bool)
        # sliding faces: the carrier's flanks and the charging handle's face polished along X (forced bare)
        pk = part[tp[k]]
        slide = np.zeros(k.sum(), bool)
        cs = pk == "bolt_carrier"
        st_ = np.zeros(k.sum(), np.float32)
        if cs.any():
            st_[cs] = PT.aniso(P[k][cs], (1.0, 0.0, 0.0), 14.0, 0.25, 2, 31)
            slide[cs] = np.abs(N[k][cs, 1]) > 0.75                      # the flanks: polished bare
        chip |= slide
        col[chip] = bare[None, :] * (0.92 + 0.12 * v_mid[k][chip])[:, None]
        r = np.where(chip, np.where(slide, 0.16 + 0.10 * st_, 0.30 + 0.08 * v_mid[k]), r)
        met = np.where(chip, 1.0, met)
        # chip relief: the lacquer flake edge (0.03 mm) for the normal map
        if f.startswith("lacquer"):
            h[k] = np.where(chip, -0.03, hscuff if f in ("lacquer", "lacquer_cover", "lacquer_mag") else 0.0)
        # cavity grime and soot. On a dielectric (lacquer) they darken the colour; on bare / blued metal they are a
        # dirt layer: a texel is either clean metal (its BC stays a metal's, >= sRGB 110 / 186: B9) or covered
        # (dielectric, grime / soot colour) - never a darkened metal
        g = np.clip(cav[k] * 0.55, 0, 1)
        s_ = soot[k]
        isd = met < 0.5
        col = np.where(isd[:, None], col * (1 - g)[:, None] + grime[None, :] * g[:, None], col)
        col = np.where(isd[:, None], col * (1 - 0.85 * s_)[:, None] + 0.022 * (0.85 * s_)[:, None], col)
        dirt = (~isd) & ((g * (0.6 + 0.8 * chip_n[k]) > 0.42) | (s_ > 0.45))
        dcol = np.where((s_ > g)[:, None], 0.022 + 0.01 * v_mid[k][:, None], grime[None, :] * (0.8 + 0.3 * v_mid[k][:, None]))
        col = np.where(dirt[:, None], dcol, col)
        met = np.where(dirt, 0.0, met)
        r = r + 0.25 * g
        r = r * (1 - s_) + 0.88 * s_
        # the bore: soot darkening with depth (inner barrel faces)
        if (pk == "barrel").any():
            bsel = pk == "barrel"
            rad = np.hypot(P[k][bsel, 1], P[k][bsel, 2])
            inner = rad < 6.0
            dep = PT.smoothstep(848.8, 820.0, P[k][bsel, 0])
            col_b = col[bsel]
            col_b[inner] *= (0.35 + 0.4 * (1 - dep[inner]))[:, None]
            col[bsel] = col_b
            met_b = met[bsel]
            met_b[inner] = 0.0
            met[bsel] = met_b
        bc[k] = col
        rough[k] = r
        metal[k] = met

    # ---------------------------------------------------------------- walnut
    wsel = fin == "walnut"
    if wsel.any():
        F = RS.FIN["walnut"]
        stain = lin(F["srgb"]).astype(np.float32)
        Lum = lambda c: float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])   # noqa: E731
        l0 = Lum(stain)
        k_dark = Lum(lin(F["grain_dark"])) / l0
        k_light = Lum(lin(F["figure_light"])) / l0
        k_hand = Lum(lin(F["handling"])) / l0
        k_chk = Lum(lin(F["checker"])) / l0
        L = np.ones(wsel.sum(), np.float32)
        rr = np.zeros(wsel.sum(), np.float32)
        hh = np.zeros(wsel.sum(), np.float32)
        Pw, Nw, pk = P[wsel], N[wsel], part[tp[wsel]]
        for name in np.unique(pk):
            s = pk == name
            ax = np.array(RS.GRAIN_AXIS.get(name, (1.0, 0.0, 0.0)), np.float32)
            c = Pw[s].mean(0)
            # pith of the virtual blank: off the part, below / to one side (flat-sawn: rings show as cathedral arches)
            perp = np.cross(ax, np.array([0.0, 1.0, 0.0], np.float32))
            perp /= max(np.linalg.norm(perp), 1e-6)
            pith = c - perp * 55.0 + np.array([0.0, 23.0, 0.0], np.float32)
            ph, rad = PT.wood_rings(Pw[s], ax, pith, spacing_mm=1.3, warp_mm=4.0, seed=40 + len(name))
            # soft latewood (no contour-map lines), long figure streaks, fine pores along the grain
            late = PT.smoothstep(0.35, 0.80, ph) * (1 - PT.smoothstep(0.80, 1.0, ph))
            fig = PT.aniso(Pw[s], ax, 60.0, 6.0, 3, 50 + len(name))
            streak = PT.aniso(Pw[s], ax, 18.0, 0.8, 2, 55 + len(name))
            pores = PT.smoothstep(0.62, 0.82, PT.aniso(Pw[s], ax, 4.0, 0.18, 2, 60 + len(name)))
            l_ = 1.0 + (k_dark - 1.0) * 0.30 * late
            l_ *= 1.0 + (k_light - 1.0) * 0.30 * PT.smoothstep(0.45, 0.75, fig) - 0.10 * PT.smoothstep(0.5, 0.2, fig)
            l_ *= 1.0 + 0.45 * (streak - 0.5)
            # long dark grain streaks (the sheet's walnut: dark lines running the part's length)
            dstreak = PT.smoothstep(0.62, 0.78, PT.aniso(Pw[s], ax, 40.0, 0.35, 3, 57 + len(name)))
            l_ *= 1.0 - 0.38 * dstreak
            # broad darker patches in the figure (heartwood / old oil), the sheet's uneven stock and guards
            l_ *= 1.0 - 0.16 * PT.smoothstep(0.50, 0.78, PT.chunked(PT.fbm3, Pw[s], 30.0, 3, 59 + len(name)))
            l_ *= 1.0 - 0.12 * pores
            dirt = PT.smoothstep(0.55, 0.75, PT.chunked(PT.fbm3, Pw[s], 14.0, 3, 65 + len(name)))
            l_ *= 1.0 - 0.14 * dirt
            l_ *= RS.WOOD_VALUE.get(name, 1.0)
            # handling damage (the sheet's furniture is dinged and scratched all over, the grip most): small dark
            # dents (crushed fibres, darker, rougher, a shallow dip) and fine scratches through the shellac (lighter)
            dw = RS.DENT_W.get(name, 1.0)
            dpatch = PT.smoothstep(0.35, 0.70, PT.chunked(PT.fbm3, Pw[s], 18.0, 2, 91 + len(name)))
            dents = PT.smoothstep(0.74 - 0.05 * (dw - 1.0), 0.84 - 0.05 * (dw - 1.0),
                                  PT.chunked(PT.fbm3, Pw[s], 1.5, 2, 93 + len(name))) * np.clip(dpatch * dw, 0, 1)
            sc_a = PT.aniso(Pw[s], (0.35, 0.85, 0.40), 9.0, 0.07, 2, 95 + len(name))
            sc_b = PT.aniso(Pw[s], (0.80, -0.30, 0.52), 12.0, 0.07, 2, 97 + len(name))
            scr = PT.smoothstep(0.76, 0.84, np.maximum(sc_a, sc_b)) * np.clip(dpatch * dw + 0.2, 0, 1)
            l_ *= 1.0 - 0.32 * dents
            l_ *= 1.0 + 0.16 * scr
            # stronger figure for the sheet's dark-grained walnut (r4 look: the grain hardly read at the side view),
            # as one extra luminance factor normalised to median 1, so the part's median value (gate L5) is kept
            extra = (1.0 - 0.30 * PT.smoothstep(0.55, 0.75, PT.aniso(Pw[s], ax, 55.0, 0.6, 3, 61 + len(name))))
            extra *= 1.0 + (k_dark - 1.0) * 0.25 * late
            extra *= 1.0 - 0.18 * PT.smoothstep(0.45, 0.80, PT.aniso(Pw[s], ax, 120.0, 4.0, 2, 63 + len(name)))
            l_ *= extra / max(float(np.median(extra)), 1e-3)
            L[s] = l_
            rr[s] = 0.55 + 0.06 * (fig - 0.5) + 0.07 * pores + 0.03 * late + 0.06 * dents + 0.08 * scr
            hh[s] = -0.012 * pores + 0.006 * late - 0.05 * dents - 0.01 * scr
        # handling wear: worn lighter and rougher at the hands, oil-darkened around
        hz = np.zeros(wsel.sum(), np.float32)
        ring = np.zeros(wsel.sum(), np.float32)
        nh = PT.chunked(PT.fbm3, Pw, 6.0, 3, 70)
        for z in RS.HANDLING:
            s = pk == z["part"]
            if not s.any():
                continue
            dd = np.linalg.norm(Pw[s] - np.array(z["center_M"], np.float32), axis=1)
            core = z["w"] * PT.smoothstep(z["radius"], z["radius"] * 0.35, dd) * (0.5 + 0.5 * nh[s])
            hz[s] = np.maximum(hz[s], core)
            ring[s] = np.maximum(ring[s], z["w"] * PT.smoothstep(z["radius"] * 1.5, z["radius"], dd)
                                 * (1 - PT.smoothstep(z["radius"], z["radius"] * 0.6, dd)))
        wedge = edge_broad[wsel] * (0.6 + 0.6 * chip_n[wsel])
        L *= 1.0 + (k_hand - 1.0) * np.clip(hz * 1.1 + 0.6 * wedge, 0, 1)
        L *= 1.0 - 0.10 * ring
        rr += 0.10 * hz + 0.06 * wedge
        # checkering (grip): darker grooves from the baked normal's tilt
        if "ckm" in d:
            infield = np.zeros(len(idx), bool)
            gsel = part[tp] == "pistol_grip"
            infield[gsel] = checker_field_mask(P[gsel])
            km = (d["ckm"].reshape(-1)[idx][wsel] > 0.5) & infield[wsel]
            ckn = d["ckn"].reshape(-1, 3)[idx][wsel] * 2.0 - 1.0
            groove = PT.smoothstep(0.98, 0.80, ckn[:, 2])
            L = np.where(km, L * (1.0 + (k_chk - 1.0) * (0.45 + 0.55 * groove)), L)
            rr = np.where(km, rr + 0.06 * groove, rr)
        g = np.clip(cav[wsel] * 0.45, 0, 1)
        L *= 1.0 - 0.35 * g
        rr += 0.15 * g
        bc[wsel] = stain[None, :] * L[:, None]
        rough[wsel] = np.clip(rr, F["rough"][0] - 0.02, 0.75)
        metal[wsel] = 0.0
        h[wsel] = hh
        m_edge[wsel] = np.clip(edge_broad[wsel], 0, 1)
        m_hand[wsel] = np.clip(hz, 0, 1)
        refin[wsel] = 1.0
    # handling on metal (thumb on the selector tab, support hand on the front band): G channel only
    for z in RS.HANDLING:
        pass
    # sights and bare / blued parts are not refinishable (A = 0); lacquered sight parts too (study 5.10: sights 0)
    sight = np.isin(part[tp], ["rear_sight_block", "rear_sight_leaf", "rear_sight_slider", "front_sight_block",
                               "front_sight_post"])
    refin[sight] = 0.0

    # ---------------------------------------------------------------- limits (gate B9 / G7)
    is_m = metal > 0.5
    metal = np.where(is_m, 1.0, 0.0).astype(np.float32)
    lo_d = PT.srgb_to_lin(np.array([30.0]))[0]
    bc = np.where(is_m[:, None], np.maximum(bc, PT.srgb_to_lin(np.array([110.0]))[0]), np.maximum(bc, lo_d))
    bc = np.clip(bc, 0.0, PT.srgb_to_lin(np.array([243.0]))[0])
    rough = np.clip(rough, 0.12, 0.95)

    # ---------------------------------------------------------------- full-size maps
    def full(vals, ch, fill):
        a = np.empty((S * S, ch) if ch > 1 else S * S, np.float32)
        a[:] = fill
        a[idx] = vals
        return a.reshape((S, S, ch) if ch > 1 else (S, S))
    BC = full(bc, 3, 0.0)
    R = full(rough, 1, 0.5)
    M = full(metal, 1, 0.0)
    AO = full(ao, 1, 1.0)
    Hm = full(h, 1, 0.0)
    # gutters beyond the bake margin: bleed the island colours outward (mips)
    BC = PT.dilate_fill(BC, valid, 32)
    R = PT.dilate_fill(R, valid, 32)
    M = np.where(PT.dilate_fill(M, valid, 32) > 0.5, 1.0, 0.0)
    AO = PT.dilate_fill(AO, valid, 32)
    left = ~PT.dilate_fill(valid.astype(np.float32), valid, 32).astype(bool)
    log(st, "paint %.1fs" % (time.time() - t0))
    # normal map: painted height in each texel's UV frame + the checkering bake
    pos_mm = d["pos"].astype(np.float32) * 1000.0
    du, dv = PT.mm_per_px(pos_mm, valid)
    nrm = PT.height_to_normal(Hm, np.where(valid, isl, -1), du, dv)
    if "ckm" in d:
        ck = d["ckn"] * 2.0 - 1.0
        ck /= np.maximum(np.linalg.norm(ck, axis=-1, keepdims=True), 1e-6)
        km_flat = np.zeros(S * S, bool)
        km_flat[idx] = (d["ckm"].reshape(-1)[idx] > 0.5) & infield
        km = km_flat.reshape(S, S) & valid
        nrm = np.where(km[..., None], PT.whiteout(ck, nrm), nrm)
    nrm[~valid] = (0.0, 0.0, 1.0)
    del pos_mm, du, dv
    # ---------------------------------------------------------------- write
    TEX.mkdir(parents=True, exist_ok=True)
    stem = f"T_AR01_{st}"
    PT.write_png(TEX / f"{stem}_BC.png", PT.lin_to_srgb(BC))
    PT.write_png(TEX / f"{stem}_ORM.png", np.stack([AO, R, M], -1))
    PT.write_png16(TEX / f"{stem}_N.png", PT.normal_to_dx(nrm))           # 16-bit: an exact flat (see paint.py)
    MK = np.stack([full(m_edge, 1, 0), full(m_hand, 1, 0), full(m_cav, 1, 0), full(refin, 1, 0)], -1)
    MK = MK.reshape(S // 2, 2, S // 2, 2, 4).mean((1, 3))
    PT.write_png(TEX / f"{stem}_Masks.png", MK, "RGBA")
    # ---------------------------------------------------------------- report
    rep = {"size": S, "texels_painted": int(n), "gutter_unfilled_fraction": round(float(left.mean()), 4),
           "seconds": round(time.time() - t0, 1), "finishes": {}}
    for f in np.unique(fin):
        s = fin == f
        b8 = (PT.lin_to_srgb(bc[s]) * 255).round()
        rep["finishes"][str(f)] = {
            "texels": int(s.sum()), "metal_fraction": round(float(metal[s].mean()), 4),
            "bc_srgb_dielectric_p1_p50_p99": [float(np.percentile(b8[metal[s] < 0.5].mean(1), q)) for q in (1, 50, 99)]
            if (metal[s] < 0.5).any() else None,
            "bc_srgb_metal_p1_p50_p99": [float(np.percentile(b8[metal[s] > 0.5].mean(1), q)) for q in (1, 50, 99)]
            if (metal[s] > 0.5).any() else None,
            "rough_p5_p50_p95": [round(float(np.percentile(rough[s], q)), 3) for q in (5, 50, 95)]}
    rep["metallic_values"] = sorted(set(np.unique(M).tolist()))
    log(st, "DONE %.1fs" % (time.time() - t0))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="Metal,Furniture,Mag")
    a = ap.parse_args()
    meta = json.loads((BAKE / "bake_meta.json").read_text())
    REP.mkdir(parents=True, exist_ok=True)
    rp = REP / "paint_report.json"
    report = json.loads(rp.read_text()) if rp.exists() else {}
    for st in a.sets.split(","):
        report[st] = paint(st, meta)
        rp.write_text(json.dumps(report, indent=1))
    print("[AR01-paint] PAINT_DONE")


if __name__ == "__main__":
    main()
