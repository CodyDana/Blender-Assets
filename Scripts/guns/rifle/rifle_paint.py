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
import math
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
from gunlib import edgemask as EM  # noqa: E402

WORK = ROOT / "WorkFiles" / "guns" / "rifle"
BAKE = WORK / "scratch" / "bake"
REP = WORK / "scratch" / "paint"
TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
GRIP = np.array(RS.GRIP_M)
sys.path.insert(0, str(ROOT / "Scripts" / "guns" / "rifle"))
from parts import receiver_right_cover as RC  # noqa: E402  (the cover's skirt bottom line)
from rifle_parts import WO  # noqa: E402
# Walnut shellac roughness base (look-polish round, 2026-10-05): 0.55 -> 0.43, the low end of the spec walnut range
# (0.42-0.60; texel P5..P95 ~0.40-0.55 with the figure / pores / dents / handling terms). Under physical light a 0.55
# shellac spreads its 4 % specular so wide that every side flat mirrors the studio and the dark stain washes out to
# R/B ~1.9 (the sheet: 2.0-2.6); a semi-gloss shellac (real rifle furniture) keeps the reflection in a narrower lobe.
WOOD_R0 = 0.43
# wood wear zones per part: (fraction along X of the part's bounds, fraction along Z, radius mm, weight)
WOOD_WEAR = {"upper_handguard": [(1.0, 0.6, 22.0, 0.9)], "lower_handguard": [(1.0, 0.5, 28.0, 1.0)],
             "buttstock": [(0.0, 0.0, 34.0, 1.0), (0.0, 1.0, 30.0, 0.85)], "pistol_grip": [(0.0, 0.0, 24.0, 0.7)]}
# Per-part tone ratio relative to the ONE stain (linear RGB multipliers; orchestrator ruling L5, 2026-10-05): the sheet
# draws the grip, the two handguards and the stock as four pieces of walnut (R/B 2.04 / 2.12 / 2.47 / 2.57), as
# mismatched furniture on real rifles of this pattern is. Calibrated per part on the physical L5 rig by
# rifle_wood_tone.py (WorkFiles/guns/rifle/wood_tone.json); without the file, the r4 per-part values (grey ratios).
_WT = ROOT / "WorkFiles" / "guns" / "rifle" / "wood_tone.json"
WOOD_TONE = ({k: tuple(v) for k, v in json.loads(_WT.read_text())["tone_linear"].items()} if _WT.exists() else
             {k: (v, v, v) for k, v in RS.WOOD_VALUE.items()})


# form-following grain per piece (realism-tex round): the piece's long axis and its "height" direction for
# gunlib.paint.flow_coords (frame M unit vectors), the pith of the virtual blank (distance from the piece's mid height
# and the angle of the pith direction from straight down, toward +w; oblique: the side faces cut the rings at a slant,
# so the lines run with the form and open into long arches), the mean ring spacing (mm) and a noise seed
_ga = math.radians(RS.GRIP_RAKE_DEG)
WOOD_FLOW = {
    "buttstock": {"ax": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "pith_mm": 150.0, "pith_deg": 38.0, "spacing": 2.9,
                  "seed": 410},
    "pistol_grip": {"ax": (math.sin(_ga), 0.0, math.cos(_ga)), "up": (-math.cos(_ga), 0.0, math.sin(_ga)),
                    "pith_mm": 95.0, "pith_deg": 52.0, "spacing": 2.4, "seed": 430},
    "upper_handguard": {"ax": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "pith_mm": 120.0, "pith_deg": 30.0,
                        "spacing": 2.5, "seed": 450, "rigid": True},
    "lower_handguard": {"ax": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "pith_mm": 135.0, "pith_deg": 44.0,
                        "spacing": 2.7, "seed": 470, "rigid": True},
}


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


def geo_edges(st, P, tp):
    """Geometric edge masks at the texels (gunlib.edgemask: convex dihedral edges of each texel's own part on the true
    LOD0 triangles; realism-fix round 2026-10-07): E at sigma 0.3 mm (fine) and 1.0 mm (broad), and the distance to
    the nearest sharp (> 25 deg) convex edge. Cached next to the bakes (recomputed when the triangles or the position
    bake are newer)."""
    cache = BAKE / f"{st}_geoedge.npz"
    src = [BAKE / f"{st}_tris.npz", BAKE / f"{st}_pos.npy", BAKE / f"{st}_ids.npy"]
    if cache.exists() and all(cache.stat().st_mtime > f.stat().st_mtime for f in src):
        c = np.load(cache)
        if len(c["ef"]) == len(P):
            return c["ef"], c["eb"], c["dist"]
    t = np.load(BAKE / f"{st}_tris.npz")
    E, dist = EM.part_fields(t["V"], t["pid"], P, tp, (0.3, 1.0))
    np.savez(cache, ef=E[0.3], eb=E[1.0], dist=dist)
    return E[0.3], E[1.0], dist


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
    ao = np.clip(d["ao"].reshape(-1)[idx].astype(np.float32), 0, 1)
    tp = pid.ravel()[idx]
    ef, eb, dist_e = geo_edges(st, P, tp)
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
    # REALISM-FIX ROUND (2026-10-07, review: white triangular shards on flat panels, a lit wedge on the receiver's
    # right wall at the magazine well, dashed seam lines): the edge masks are the GEOMETRIC convex-edge fields of
    # gunlib.edgemask (true dihedral edges of each part; an edge inside a planar face reads 0), no longer the
    # bevel-node bake (which followed the interpolated normals across long sliver triangles). Edges in an occluded
    # corner (low AO: a slot's inner lip, under a neighbour) see less handling
    open_ = 0.6 + 0.4 * PT.smoothstep(0.60, 0.90, ao)
    v_far = PT.chunked(PT.fbm3, P, 25.0, 2, 4)        # some edges see more handling than others
    edge_fine = PT.smoothstep(0.30, 0.80, ef) * open_
    edge_broad = PT.smoothstep(0.30, 0.90, eb) * open_
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
    # look-polish round (orchestrator item 3: wear read faint at hero / third-person distance): in the handling zones
    # the worn band spreads wider (x up to 2.0) and the zone term adds to the propensity, so the wear there forms
    # readable 1-4 mm bands and patches, not sub-mm flecks; elsewhere unchanged
    # (realism-tex round: x (2.4 + 2.4 wearz) put a uniform light halo round the cover's button hole; narrower now)
    e_band = np.maximum(e_core, np.clip(spread * (1.9 + 1.3 * wearz), 0.0, 1.0))
    flake = PT.chunked(PT.fbm3, P, 1.1, 3, 41)
    flake_big = PT.chunked(PT.fbm3, P, 5.0, 2, 42)
    edge = e_band * (0.45 + 1.1 * wear + 0.55 * wearz) * (0.75 + 0.5 * v_far) * (0.35 + 0.85 * flake + 0.35 * flake_big) / 0.95
    # realism-tex round (judges 2026-10-06: a flat white patch on the gas block collar, a hard white ring at the brake's
    # base): the chips to bare steel came from the SPREAD band (up to ~2 mm off any edge in the wear zones, x 4.8), so a
    # narrow section between two edges went bare all round. Bare steel now needs the true edge (the 0.6 / 2 mm bevel
    # masks, e_core) and is broken by a fine flake field (real chips are irregular flecks along an edge, never a solid
    # band); the spread band only thins / rubs the coat (lighter, glossier dielectric), as worn paint does first
    edge_chip = e_core * (0.45 + 1.1 * wear + 0.55 * wearz) * (0.75 + 0.5 * v_far) *         (0.35 + 0.85 * flake + 0.35 * flake_big) / 0.95
    flk = PT.chunked(PT.fbm3, P, 0.7, 3, 44)
    # bare steel only ON a sharp edge (the 0.6 mm bevel mask): the 2 mm mask lights whole rounded collars (the gas
    # block's rear collar went bare across its crown); the magazine's rib crests keep the broad mask (lacquer_mag)
    # (flake gate 0.48: at 0.40 a straight 0.6 mm bevel broke into regular bright dashes, "stitching" at FP distance)
    # bare steel only within 0.6 mm of a real sharp convex edge (1.2 mm inside a handling / wear zone), and never on
    # a panel interior (gate: bare clusters > 2 mm from any convex edge outside the wear zones = 0)
    near = (dist_e < 0.6) | ((wearz > 0.5) & (dist_e < 1.2))
    # chips CLUSTER where something rubs (review: 'even white streaks along every rib and edge, the look of an
    # automatic edge-wear generator'): a 9 mm cluster field gates them, loosely inside the wear zones and only at its
    # rare peaks elsewhere, so most of an edge's length keeps its coat
    clus = PT.smoothstep(0.42, 0.72, PT.chunked(PT.fbm3, P, 9.0, 3, 45)) * (0.35 + 0.65 * wearz)
    on_edge = (edge_fine > 0.35) & (flk > 0.48) & near & (clus > 0.30)
    on_edge_mag = (edge_fine > 0.30) & (flk > 0.46) & near & (clus > 0.34)
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
        col = base[None, :] * var[:, None] * tint * (1.0 - 0.10 * hot)[:, None]
        r0, r1 = F["rough"] if isinstance(F["rough"], tuple) else (F["rough"], F["rough"])
        r = r0 + (r1 - r0) * (0.25 + 0.6 * v_lo[k] + 0.4 * (v_mid[k] - 0.5))
        met = np.full(k.sum(), float(F["metal"]), np.float32)
        # wear: chips on convex edges (lacquer: hard flakes to bare steel; bluing: worn to bare on the high edges)
        if f in ("lacquer", "lacquer_cover", "lacquer_mag"):
            eb = edge_broad[k] * (0.55 + 0.9 * v_far[k]) if f == "lacquer_mag" else 0.0   # mag: bright rib crests
            amt = np.maximum(edge[k], eb) * (0.45 + chip_n[k])
            amt_c = edge_chip[k] * (0.45 + chip_n[k])     # (the mag's rib crests rub lighter; chips only at true edges)
            chip = (amt_c > (0.62 if f == "lacquer_mag" else 0.70) - 0.10 * wearz[k]) &                 (on_edge_mag[k] if f == "lacquer_mag" else on_edge[k])
            # rubbed lacquer short of a chip: the coat thinned lighter and glossier along the worn edges (a mid-dark
            # grey, not a light one: x <= 1.8 on the 0.035 lacquer)
            # (mottled by the flake field: a uniform rubbed band round a hole or along an edge read as a halo)
            rub = PT.smoothstep(0.36, 0.70, amt) * (~chip) * np.clip(0.15 + 1.0 * flake[k], 0, 1)
            col *= (1.0 + (0.45 + 0.35 * wearz[k]) * rub)[:, None]
            r = r - 0.06 * rub
            # scuffs (the sheet's long light rubs on the cover, receiver, barrel and magazine): thin streaks along the
            # part's scuff axis in patches, plus short random scratches; light (thinned lacquer), the deepest to bare
            pk_ = part[tp[k]]
            sw = np.array([RS.SCUFF_W.get(x, 0.7) for x in pk_], np.float32)
            # the dust cover: no long bore-aligned streaks, oil blotches or thinned-coat patches on its crown (the
            # judges' "brushed aluminium / plaster"); short random-direction scratches only
            cov = (pk_ == "dust_cover").astype(np.float32)
            Pk = P[k]
            # REALISM-FIX ROUND (review: uniform horizontal hairlines over the whole receiver side and the front
            # sight tower read as brushed aluminium): scuffs only in the handling / sling / wear zones, short (6 mm)
            # and in a direction that changes from patch to patch, at about half the old contrast; the open flats
            # keep the fine lacquer mottle only. Deep scratches to bare steel only inside a wear zone
            zone = PT.smoothstep(0.30, 0.65, wearz[k])
            scl = PT.scratch_patches(Pk, 9.0, 6.0, 0.07, 81)
            patch = PT.smoothstep(0.45, 0.72, PT.chunked(PT.fbm3, Pk, 14.0, 3, 83)) * sw * zone
            scr1 = PT.scratch_patches(Pk, 5.0, 3.0, 0.05, 85)
            scuff = np.clip(PT.smoothstep(0.68, 0.80, scl) * patch * (1.0 - cov)
                            + 0.7 * PT.smoothstep(0.74, 0.84, scr1) * np.clip(patch + 0.15 * zone, 0, 1), 0, 1)
            col *= (1.0 + 0.55 * scuff)[:, None]
            r = r - 0.04 * scuff
            deep = (scuff > 0.85) & (PT.smoothstep(0.80, 0.90, scl) * patch * (0.6 + 0.8 * wear[k]) > 0.55)
            chip |= deep & (flk[k] > 0.45) & (wearz[k] > 0.5) & (dist_e[k] < 2.0)
            # worn-finish mottling (lighter, glossier patches where the coat has thinned) and darker oily patches
            wp = PT.smoothstep(0.58, 0.82, PT.chunked(PT.fbm3, Pk, 22.0, 3, 87)) * np.clip(sw, 0, 1.2) * (1 - cov)
            col *= (1.0 + 0.35 * wp)[:, None]
            r = r - 0.06 * wp
            oil = PT.smoothstep(0.62, 0.86, PT.chunked(PT.fbm3, Pk, 34.0, 2, 88)) * (1.0 - 0.8 * cov)
            col *= (1.0 - 0.22 * oil)[:, None]
            r = r - 0.05 * oil
            # dust cover (look-polish item 4): the top is not one uniform light slab at ADS: broad dust (lighter,
            # rougher) and oil / hand-wipe (darker, glossier) patches, streaked along the bore where it is wiped, on
            # the up-facing texels; zero-mean in value so the part's median (L5, BC gate) holds. Its thin skirt edge
            # over the receiver wall is rubbed bright (the cover slides on and off along it)
            is_c = pk_ == "dust_cover"
            if is_c.any():
                # realism-tex round (judges 2026-10-06: the top read as plaster / brushed aluminium - large whitish
                # dust slabs and glossy wipe streaks stretched along the bore): the cover is a dark pressed sheet in
                # one coat; only a fine low-contrast mottle (+-4 %) and a satin sheen wander (+-0.04) on it; its wear is
                # on the edges, the rear lip and round the button (METAL_WEAR, the edge masks), not on the flat crown
                cm = PT.chunked(PT.fbm3, Pk, 6.0, 3, 101)
                cs = PT.chunked(PT.fbm3, Pk, 20.0, 2, 102)
                col *= (1.0 + 0.08 * (cm - 0.5) * is_c)[:, None]
                r = r + 0.08 * (cs - 0.5) * is_c
                sb = np.array([RC.skirt_bottom(float(x)) for x in Pk[:, 0]], np.float32)
                skirt = is_c & (Pk[:, 2] < sb + 1.3) & (np.abs(N[k][:, 1]) > 0.35) & (Pk[:, 2] < RC.Z_BASE + 12.0)
                sk = skirt.astype(np.float32) * PT.smoothstep(1.3, 0.2, Pk[:, 2] - sb) * (0.55 + 0.6 * flake[k])
                col *= (1.0 + 1.1 * sk)[:, None]
                r = r - 0.10 * sk
                chip |= sk > 0.95
            # the receiver wall just under the cover's skirt edge: a dark oily contact line (dirt collects in the 1 mm
            # step), so the pressed-sheet edge reads as a separate sheet lying over the receiver
            is_r = pk_ == "receiver"
            if is_r.any():
                sb = np.array([RC.skirt_bottom(float(x)) for x in Pk[:, 0]], np.float32)
                band = is_r & (Pk[:, 0] > 241.0) & (Pk[:, 0] < 452.0) & (np.abs(Pk[:, 1]) > WO - 0.2) &                     (Pk[:, 2] < sb) & (Pk[:, 2] > sb - 2.2)
                cl = band.astype(np.float32) * PT.smoothstep(2.2, 0.3, sb - Pk[:, 2])
                col *= (1.0 - 0.45 * cl)[:, None]
                r = r + 0.12 * cl
            # pitting in the worn patches: dark specks
            pit = (PT.chunked(PT.vnoise3, Pk / 0.35, 89) > 0.93) & (PT.chunked(PT.fbm3, Pk, 9.0, 2, 90) > 0.6)
            col[pit] *= 0.55
            r = np.where(pit, r + 0.15, r)
            # rare surface nicks on flats: a dull rubbed fleck in the coat (no bare steel off the edges: the review's
            # 'isolated white chip in the middle of the magazine body')
            nick = (PT.chunked(PT.fbm3, Pk, 0.45, 2, 9) > 0.88) & (v_lo[k] > 0.64) & (cov < 0.5)
            col[nick] *= 1.25
            # micro scratches and handling sheen in roughness only (no colour change), in the zones, mixed directions
            scr = PT.smoothstep(0.68, 0.80, PT.scratch_patches(Pk, 7.0, 4.0, 0.15, 12)) * (1.0 - cov) * zone
            r = r - 0.05 * scr
            hscuff = -0.006 * scuff - 0.02 * pit
            m_edge[k] = np.clip(edge[k], 0, 1)
            refin[k] = 1.0
        elif f == "lacquer_worn":
            # butt plate: densely scratched to bare steel (two scratch directions)
            sc1 = PT.aniso(P[k], (0.0, 0.0, 1.0), 12.0, 0.30, 2, 21)
            sc2 = PT.aniso(P[k], (0.0, 0.7, 0.7), 10.0, 0.30, 2, 22)
            chip = (np.maximum(sc1, sc2) > 0.79) | ((edge_chip[k] * (0.5 + chip_n[k]) > 0.55) & on_edge[k])
            m_edge[k] = np.clip(edge[k] + 0.4, 0, 1)
            refin[k] = 1.0
        elif f == "bluing":
            amt = edge[k] * (0.4 + chip_n[k])
            chip = (edge_chip[k] * (0.4 + chip_n[k]) > 0.70 - 0.14 * wearz[k]) & on_edge[k]
            # bluing thins to a lighter grey before it reaches bare steel (metal stays metal: >= sRGB 110)
            thin = PT.smoothstep(0.35, 0.70, amt) * (~chip)
            # (realism-fix round: the stamped small parts flashed white / chrome; bluing thins only a little before bare)
            col *= (1.0 + 0.25 * thin)[:, None]
            r = r - 0.04 * thin
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
            # REALISM-FIX ROUND (review: the carrier flank in the port read as cloudy polished chrome, the charging
            # knob 79 % bare): polish only on the rail-contact strip (the carrier's lower flank inside the receiver,
            # Z <= 1, |Y| < 20; the knob is outside the wall at |Y| > 20): the bluing worn lighter (BC ~ 150-165,
            # still blued, not bare) at roughness 0.30-0.40
            Pc = P[k][cs]
            slide[cs] = (np.abs(N[k][cs, 1]) > 0.75) & (Pc[:, 2] <= 1.0) & (np.abs(Pc[:, 1]) < 20.0)
        chip &= ~slide
        col[chip] = bare[None, :] * (0.92 + 0.12 * v_mid[k][chip])[:, None]
        if slide.any():
            col[slide] = lin((156, 156, 154))[None, :] * (0.94 + 0.10 * v_mid[k][slide])[:, None]
        # worn steel: micro-scratched, rough enough (0.50-0.62) to read mid grey under a soft light, not a white mirror flash
        r = np.where(chip, 0.50 + 0.12 * v_mid[k], r)
        r = np.where(slide, 0.30 + 0.10 * st_, r)
        met = np.where(chip | slide, 1.0, met)
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
        # REALISM-FIX ROUND (review G11: the slant brake's inside was the same even grey as its outside): the
        # chamber, bore and port walls (texels facing into the bore axis or along it, inside r 9.6) carry soot that
        # deepens toward the chamber's rear, heaviest carbon on the slant lip's inner face; dielectric, rough
        if (pk == "muzzle_brake").any():
            msel = pk == "muzzle_brake"
            Pm, Nm = P[k][msel], N[k][msel]
            rad = np.maximum(np.hypot(Pm[:, 1], Pm[:, 2]), 1e-3)
            nr = (Nm[:, 1] * Pm[:, 1] + Nm[:, 2] * Pm[:, 2]) / rad
            inside = (nr < 0.4) & (rad < 9.6) & (Pm[:, 0] > 849.5)
            dep = PT.smoothstep(879.0, 858.0, Pm[:, 0])
            sootm = np.clip(0.55 + 0.40 * dep + 0.15 * (v_mid[k][msel] - 0.5), 0, 1) * inside
            cm, rm, mm_ = col[msel], r[msel], met[msel]
            cm = np.where(inside[:, None], cm * (1 - 0.88 * sootm)[:, None] + 0.018 * sootm[:, None], cm)
            rm = np.where(inside, 0.82 + 0.08 * sootm, rm)
            mm_ = np.where(inside, 0.0, mm_)
            # carbon on the slant lip's front (the outer rim within 3 mm of the cut, in front of X 873)
            lip = (~inside) & (Pm[:, 0] > 873.0) & (edge_broad[k][msel] > 0.2)
            cm = np.where(lip[:, None], cm * 0.55, cm)
            mm_ = np.where(lip & (mm_ > 0.5) & (v_mid[k][msel] > 0.45), 0.0, mm_)
            col[msel], r[msel], met[msel] = cm, rm, mm_
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
        satm = np.ones(wsel.sum(), np.float32)        # chroma multiplier (1 = the part's tone; < 1 browner / greyer)
        gold = np.zeros(wsel.sum(), np.float32)       # -1 redder .. +1 more golden (light figure)
        endg = np.zeros(wsel.sum(), np.float32)       # end grain (surface across the grain)
        Pw, Nw, pk = P[wsel], N[wsel], part[tp[wsel]]
        for name in np.unique(pk):
            s = pk == name
            # realism-tex round (judges 2026-10-06: "straight horizontal wallpaper stripes that ignore the form"): the
            # grain is laid out in FORM-FOLLOWING coordinates of each piece (gunlib.paint.flow_coords: u along the
            # piece, s between its lower and upper outline at that u), so the lines run with the stock's drop and
            # converge through the wrist, lean with the grip, and the butt / grip toe / guard ends cut across them
            # (end grain: ring arcs, open pores, darker and drier)
            fl = WOOD_FLOW.get(str(name), WOOD_FLOW["upper_handguard"])
            u, sv, w, span, Hn, T = PT.flow_coords(Pw[s], fl["ax"], fl["up"], rigid=bool(fl.get("rigid")))
            v = np.clip(sv, -0.3, 1.3) * np.sqrt(np.maximum(span, 5.0) * Hn)   # straightened height (mm)
            sd = fl["seed"]
            th = math.radians(fl["pith_deg"])
            pith = (0.5 * Hn - fl["pith_mm"] * math.cos(th), fl["pith_mm"] * math.sin(th))
            ph, ring = PT.ring_phase(v, w, u, pith, fl["spacing"], sd)
            # walnut is semi-ring-porous: a soft darker latewood band closing each ring, open pores in the earlywood
            late = PT.smoothstep(0.55, 0.88, ph) * (1.0 - PT.smoothstep(0.92, 1.0, ph))
            rv = PT._hash(ring, np.full_like(ring, sd), np.zeros_like(ring), 5)          # per-ring strength
            late *= 0.3 + 1.2 * rv
            # straightened sample points: noise stretched ALONG the grain lines
            def gq(along, across, off=0.0):
                return np.stack([u / along + off, v / across, w / across], 1).astype(np.float32)
            # dark colour streaks (heartwood / mineral streaks), long and narrow, in patches
            strk = PT.smoothstep(0.56, 0.80, PT.chunked(PT.fbm3, gq(95.0, 3.2), 1.0, 3, sd + 1))
            strk *= PT.smoothstep(0.35, 0.65, PT.chunked(PT.fbm3, gq(160.0, 22.0, 3.3), 1.0, 2, sd + 2))
            # broad figure (lighter golden / darker red-brown zones), elongated along the grain
            fig = PT.chunked(PT.fbm3, gq(75.0, 16.0, 7.1), 1.0, 3, sd + 3)
            # fine fibre texture between the rings, and the pores: short dark dashes along the grain
            fib = PT.chunked(PT.fbm3, gq(9.0, 0.45, 1.7), 1.0, 2, sd + 4)
            # (the furniture texel is 0.14-0.29 mm: the pores are a fine, dense, low-contrast fleck along the grain)
            pores = PT.smoothstep(0.58, 0.76, PT.chunked(PT.fbm3, gq(1.2, 0.20, 5.5), 1.0, 2, sd + 6))
            pores *= 0.55 + 0.45 * (1.0 - late)
            # end grain: |N . T| high where the surface cuts across the grain lines
            eg = PT.smoothstep(0.55, 0.88, np.abs(np.sum(Nw[s] * T, axis=1)))
            # broad heartwood-dark zones (walnut's chocolate patches): the figure's large-scale value contrast
            heart = PT.smoothstep(0.42, 0.72, PT.chunked(PT.fbm3, gq(150.0, 30.0, 4.4), 1.0, 3, sd + 9))
            l_ = 1.0 + (k_dark - 1.0) * 0.42 * late
            l_ *= 1.0 + 0.65 * (fig - 0.5)
            l_ *= 1.0 - 0.34 * heart
            l_ *= 1.0 - 0.46 * strk                    # (realism-fix: darker mineral streaks)
            l_ *= 1.0 + 0.10 * (fib - 0.5)
            l_ *= 1.0 - 0.26 * pores
            l_ *= 1.0 - 0.34 * eg                      # end grain: drier and grimier
            dirt = PT.smoothstep(0.55, 0.75, PT.chunked(PT.fbm3, Pw[s], 14.0, 3, 65 + len(name)))
            l_ *= 1.0 - 0.10 * dirt
            # (the part's value AND hue relative to the stain: WOOD_TONE below, applied to the colour)
            # handling damage (the sheet's furniture is dinged and scratched all over, the grip most): small dark
            # dents (crushed fibres, darker, rougher, a shallow dip) and fine scratches through the shellac (lighter)
            dw = RS.DENT_W.get(name, 1.0)
            dpatch = PT.smoothstep(0.35, 0.70, PT.chunked(PT.fbm3, Pw[s], 18.0, 2, 91 + len(name)))
            # REALISM-FIX ROUND (review: evenly spread round pock dents gave a hammered look): sparse dings
            # stretched ALONG the grain (crushed fibres run with it), in patches
            dents = PT.smoothstep(0.83 - 0.03 * (dw - 1.0), 0.90 - 0.03 * (dw - 1.0),
                                  PT.chunked(PT.fbm3, gq(5.0, 0.9, 2.9), 1.0, 2, 93 + len(name))) * \
                np.clip(dpatch * dw, 0, 1)
            sc_a = PT.aniso(Pw[s], (0.35, 0.85, 0.40), 9.0, 0.07, 2, 95 + len(name))
            sc_b = PT.aniso(Pw[s], (0.80, -0.30, 0.52), 12.0, 0.07, 2, 97 + len(name))
            scr = PT.smoothstep(0.76, 0.84, np.maximum(sc_a, sc_b)) * np.clip(dpatch * dw + 0.2, 0, 1)
            l_ *= 1.0 - 0.16 * dents
            l_ *= 1.0 + 0.12 * scr
            L[s] = l_
            # chroma: streaks, pores and end grain browner / greyer, latewood richer, a broad saturation wander
            sn = PT.chunked(PT.fbm3, gq(120.0, 30.0, 9.9), 1.0, 2, sd + 7)
            satm[s] = (1.0 + 0.40 * (sn - 0.5) - 0.30 * strk - 0.16 * pores - 0.20 * eg + 0.06 * late
                       - 0.08 * dents - 0.22 * heart)
            # light figure turns golden (hue toward yellow), dark figure red-brown: desaturating an orange toward its
            # luminance grey reads salmon / pink, so the light zones shift hue instead of losing chroma
            gold[s] = np.clip((fig - 0.5) * 3.0 - 0.5 * heart, -1.0, 1.0)
            endg[s] = eg
            # finish sheen: an oil / shellac wander along the grain, open pores and end grain drier
            sh = PT.chunked(PT.fbm3, gq(60.0, 14.0, 2.2), 1.0, 2, sd + 8)
            rr[s] = (WOOD_R0 + 0.10 * (sh - 0.5) + 0.08 * pores + 0.03 * late + 0.12 * eg + 0.06 * dents
                     + 0.08 * scr)
            hh[s] = -0.014 * pores + 0.005 * late - 0.05 * dents - 0.01 * scr - 0.006 * eg * (1.0 - ph)
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
        # wood edge wear (look-polish item 3): where real handling wears the shellac through to lighter, drier wood -
        # the handguards' front ends (slid into the band, gripped), the stock's toe and heel (grounded, racked), the
        # grip's lower rear edge - zones from each part's own bounds (frame M)
        wz = np.zeros(wsel.sum(), np.float32)
        for name, corners in WOOD_WEAR.items():
            s = pk == name
            if not s.any():
                continue
            lo_, hi_ = Pw[s].min(0), Pw[s].max(0)
            for (fx, fz, rad, w) in corners:
                c = np.array([lo_[0] + fx * (hi_[0] - lo_[0]), 0.0, lo_[2] + fz * (hi_[2] - lo_[2])], np.float32)
                # the bounds corner can lie off the rounded / raked part: centre on the part's nearest surface point
                c = Pw[s][np.argmin(np.linalg.norm((Pw[s] - c) * np.array([1.0, 0.25, 1.0], np.float32), axis=1))]
                dd = np.linalg.norm((Pw[s] - c) * np.array([1.0, 0.25, 1.0], np.float32), axis=1)
                wz[s] = np.maximum(wz[s], w * PT.smoothstep(rad, rad * 0.3, dd))
        wedge = edge_broad[wsel] * (0.6 + 0.6 * chip_n[wsel]) * (1.0 + 1.6 * wz)
        wband = np.clip(edge_fine[wsel] * 1.5 + edge_broad[wsel], 0, 1) * wz * (0.4 + 0.9 * PT.chunked(
            PT.fbm3, Pw, 1.6, 2, 103))
        L *= 1.0 + (k_hand - 1.0) * np.clip(hz * 1.1 + 0.6 * wedge, 0, 1)
        L *= 1.0 + 0.55 * np.clip(wband, 0, 1)                      # worn through: lighter raw walnut
        L *= 1.0 - 0.10 * ring
        # worn high points: lighter, paler (the stain thinned), drier; the hands' own zones polished a little
        satm -= 0.12 * np.clip(wband, 0, 1) + 0.06 * np.clip(hz, 0, 1)
        gold += 0.6 * np.clip(wband, 0, 1) + 0.3 * np.clip(hz, 0, 1)            # bare / thinned wood: tan
        rr += 0.02 * hz + 0.06 * wedge + 0.12 * np.clip(wband, 0, 1)
        # checkering (grip): darker grooves from the baked normal's tilt
        if "ckm" in d:
            infield = np.zeros(len(idx), bool)
            gsel = part[tp] == "pistol_grip"
            infield[gsel] = checker_field_mask(P[gsel])
            km = (d["ckm"].reshape(-1)[idx][wsel] > 0.5) & infield[wsel]
            ckn = d["ckn"].reshape(-1, 3)[idx][wsel] * 2.0 - 1.0
            groove = PT.smoothstep(0.98, 0.80, ckn[:, 2])
            # (realism-fix round, review + blind tells: 'a dark rectangular inset panel / decal on flat wood'): the
            # grooves darken, the diamond tops keep the wood's own tone (worked into the wood, not a dark patch)
            L = np.where(km, L * (1.0 + (k_chk - 1.0) * (0.08 + 0.72 * groove)), L)
            rr = np.where(km, rr + 0.06 * groove, rr)
        g = np.clip(cav[wsel] * 0.45, 0, 1)
        L *= 1.0 - 0.35 * g
        rr += 0.15 * g
        # one stain x a per-part tone ratio x the luminance field: the sheet's four wood parts are four slightly
        # different pieces of walnut (mismatched furniture, as on real rifles of this pattern); see WOOD_TONE
        tone = np.ones((wsel.sum(), 3), np.float32)
        for name in np.unique(pk):
            tone[pk == name] = WOOD_TONE.get(str(name), (1.0, 1.0, 1.0))
        # each part's luminance field and chroma multiplier normalised to median 1 (the tone ratios carry the part's
        # median value and hue: wood_tone.json, calibrated on the L5 rig), then the colour: one stain x tone x L, the
        # golden / red-brown hue wander of the figure (luminance kept), and the chroma wander (luminance kept)
        for name in np.unique(pk):
            s = pk == name
            L[s] /= max(float(np.median(L[s])), 1e-3)
            satm[s] /= max(float(np.median(satm[s])), 1e-3)
        col = stain[None, :] * tone * L[:, None]
        lw = np.array([0.2126, 0.7152, 0.0722], np.float32)
        l_before = col @ lw
        col = col * np.stack([1.0 - 0.02 * gold, 1.0 + 0.11 * gold, 1.0 - 0.06 * gold], 1)
        col *= (l_before / np.maximum(col @ lw, 1e-6))[:, None]
        lum_w = (col @ lw)[:, None]
        col = lum_w + (col - lum_w) * np.clip(satm, 0.45, 1.5)[:, None]
        bc[wsel] = np.maximum(col, 0.0)
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
    # dielectric floor on the LUMINANCE (scale the colour up, hue kept): a per-channel clamp at sRGB 30 flattened the
    # blue channel of the stained walnut (the stock's tone) and capped its saturation; grey finishes are unchanged
    lum_ = bc @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bc_d = bc * np.maximum(1.0, lo_d / np.maximum(lum_, 1e-6))[:, None]
    bc_d = np.maximum(bc_d, PT.srgb_to_lin(np.array([4.0]))[0])
    bc = np.where(is_m[:, None], np.maximum(bc, PT.srgb_to_lin(np.array([110.0]))[0]), bc_d)
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
