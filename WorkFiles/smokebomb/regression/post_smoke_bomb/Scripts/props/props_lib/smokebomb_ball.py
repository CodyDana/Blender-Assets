#!/usr/bin/env python
"""props_lib.smokebomb_ball - SM_SmokeBomb built the way the real ball is made.

numpy only.  This module joins the two halves of the rebuild:

    props_lib.smokebomb_wind   WHERE the one tape runs (the fitted winding: a buried core and
                               20 near-great-circle passes, crossing-local weaves)
    props_lib.smokebomb_tape   WHAT the tape is (the padded section with rolled cords, the
                               sweep, the cloth in tape space, the maps)

and turns them into a game mesh:

    stretches  the tape is 9.6 m long and most of it is buried.  Every sample of the winding
               is tested for EXPOSURE (no other stretch of the tape lies above it there, weaves
               applied: smokebomb_wind's own stack); the exposed runs, run on by ``run_margin``
               under whatever covers their ends, are the STRETCHES that get geometry.  Each is
               swept with the tape's section, with ONE continuous u along the whole tape.
    lift       a pass lies on the passes beneath it: its base is lifted ``layer_mm`` per
               stretch below it (the winder's layers_below), BRIDGED over buried edges (the
               tape spans a step instead of folding into it, never below the raw stack), and
               DRAPED: the low-pass of the top surface's own layer count is taken off, so the
               ball stays round (a raw stack moves the outline ~10 px rms) while every visible
               edge keeps its full one-layer step.
    culling    per stretch, a (u, a) grid of the exposure, dilated by ``keep_mm``: a face is
               built only where it can be seen or lies within the margin under a covering
               edge (the lower tape runs on under its cover; no slit, no void).
    LODs       the same stretches, the same lift and the same (u, t) texture coordinates at
               every LOD: LOD1 / LOD2 keep fewer section points and longer rings, and LOD2
               takes the layers further apart so its longer chords never let what lies
               beneath show through.
    atlas      the tape in CHUNKS: each stretch is cut every ``chunk_mm`` along u and each
               chunk gets one block holding exactly the t-range its kept faces use at any
               LOD.  u along +x, t down the rows, one texel = 1/ppmm mm of cloth everywhere.

ROUND 2 (rewind builder): the height guard no longer ratchets (stretches within GUARD_KEY_EPS of
the same key are one layer; a raise is capped at GUARD_CAP_MM), which had inflated the outline
into squared tabs and a stacked bottom; a shallower, later sink (no black pocket under a covering
edge at the limb); layer 0.50 mm with a 2 mm bridge (REFERENCE_SPEC 1's 8-16 outline steps);
a 0.7 mm crown (padded bands); LOD2's edge vertices carry the body's normal (no dark edge lines
at the LOD1 -> LOD2 switch); the threads come from props_lib.smokebomb_threads (thread_parts2).

ROUND 3 (rewind builder 3): LOD0 at the prop budget (~9,600 triangles with the loose threads, was
30,991): the rolled edge is a rounded shoulder, not a separate tube (LODS); finish_maps stores the
Detail gamma-2 when the shading says so (full range; BaseColor = Detail^2 x Tint) and reports its
percentiles; T4 is an open hook.

ROUND 4 (rewind builder, workflow round 3; the round-3 judge picked the copy 20 of 20): LOD0 keeps a
round outline and a real rolled edge - rings <= 3.5 mm, body points <= 3 mm apart across a band
(BallLod.body_chord_mm), the cord at -40 / 45 deg plus the groove (16.7k triangles with the threads;
round 3's 9.6k read as "a faceted polygon with piping edges"); a smooth LUMP field (BallSpec.lump_mm,
a function of position so the stack order is untouched) gives the outline the reference's
mid-frequency bumpiness.

Units mm (build frame: X right, Y back, Z up; the reference view looks along +Y).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_tape as T
from . import smokebomb_wind as W


# =========================================================================== numbers
#: the height guard's default clearance (mm); BallSpec.guard_clear_mm
GUARD_CLEAR_MM = 0.08


@dataclass(frozen=True)
class BallSpec:
    #: radius of the sphere the tape's base centre line lies on before any lift (mm); the
    #: build solves it so the reference-view outline's mean radius is ``outline_mm``
    core_mm: float = 33.6
    outline_mm: float = 35.0
    #: radial lift per stretch beneath (mm).  REFERENCE_SPEC 5: the outline step is 5.7 px
    #: (4 - 8.5) = 0.43 mm at 70 mm; the section's cord stands 0.56 mm, so a 0.42 mm lift
    #: gives a 0.44 - 0.66 mm step where an edge crosses the limb
    #: round 2: 0.50 (was 0.42).  With the height guard's ratchet fixed (GUARD_KEY_EPS /
    #: GUARD_CAP_MM) the guard no longer inflated the outline, and the genuine edge steps at
    #: 0.42 mm with a 4 mm bridge left only 4-5 of REFERENCE_SPEC 1's 8-16 outline steps >= 4 px;
    #: 0.50 with a 2 mm bridge gives 10-12 (median ~5.5 px, spec 5.7 px)
    layer_mm: float = 0.50
    #: the tape spans a buried step over this length instead of folding into it (4 mm: at 2 mm
    #: every edge beneath telegraphed through a wide band as a crease)
    bridge_mm: float = 2.0
    #: the drape: this much of the top surface's layer count is taken off as a low-pass
    #: (Gaussian sigma on the sphere, mm) so the ball stays round
    drape_sigma_mm: float = 3.0
    drape_share: float = 1.0
    #: buried-face cull margins (mm): LOD0 keeps faces within keep_mm of an exposed point;
    #: the coarse LODs keep any face whose (u, a) rectangle meets the exposure grown by
    #: keep_coarse_mm
    keep_mm: float = 1.2
    keep_coarse_mm: float = 0.5
    #: an exposed run is extended this far along the tape under its cover
    run_margin_mm: float = 3.0
    #: stretches cut into atlas chunks of at most this length (mm)
    chunk_mm: float = 30.0
    #: the per-stretch analysis grid (mm)
    grid_du_mm: float = 0.25
    grid_da_mm: float = 0.10
    grid_margin_mm: float = 0.8
    #: per LOD: the layer lift is scaled by this about the top surface's mean (so a coarse
    #: LOD's longer chords never let a lower layer poke through; the outline mean is kept)
    lod_layer_scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    #: exposure test across the tape
    exposure_v: int = 21
    #: harmonics of the reference outline the lift carries (OutlineShape)
    outline_harmonics: int = 12
    #: the height guard (Ball.guard_heights): a covering stretch is raised until its top is
    #: GUARD_CLEAR_MM above everything beneath it
    guard: bool = True
    #: the sink: a buried run dives this far (mm) below its stacked height, from SINK_D0_MM to
    #: SINK_D1_MM in under its cover (hidden: the cover's underside is 0.42 mm above it and
    #: its top 0.74 - 1.04 mm; the cover's body chords sag up to ~0.13 mm)
    #: round 2: 0.30 from 0.30 mm in (was 0.55 from 0.15): the deeper, earlier dive left a
    #: wedge-shaped pocket under a covering edge that the grazing limb saw as a black notch
    #: (C's lower edge at the lower-left limb) and a squared tab (B at the right limb); the ID
    #: render's poke-through count fell too (1,267 -> 928 px)
    sink_mm: float = 0.30
    #: the tape section's crown (smokebomb_tape.TapeSpec.crown_mm) for the whole ball; None =
    #: the tape module's own
    #: 0.5 mm on bands 14 mm and wider (REFERENCE_SPEC's "padded" bands, shaded across their
    #: whole width: the tape module's 0.30 mm crown gave a wide band a ~4 deg edge slope and it
    #: read as a flat ribbon), a proportional share on narrower ones so a slope stays ~7-9 deg.
    #: Measured: 0.7 read more padded still, but the covering tapes then stood on their lower
    #: neighbours' crowns (the height guard raised 51 % of the grid, up to 3.6 mm) and the
    #: render's dominant texture period left the warp band (5.7 px against 3.4-5.5)
    #: round 2: 0.7 (was 0.5): the blind judge still read "flat" bands against the reference's
    #: "padded bands shaded across their width"; round 1 dropped 0.7 only because the height
    #: guard then raised 51 % of the grid by up to 3.6 mm - its ratchet, now fixed.  Measured
    #: (ID render, front): 0.7 -> 1,614 px of poke-through and 10 outline steps (max 8.8 px);
    #: 0.9 -> 2,059 px, 7 steps; 1.1 -> 2,056 px, max step 12 px (over REFERENCE_SPEC's 10)
    crown_mm: Optional[float] = 0.7
    #: the width (mm) at and above which a band carries the whole crown; narrower bands carry
    #: a proportional share (smokebomb_tape.Profile.crown_ref_w); None = a fixed crown
    crown_ref_w_mm: Optional[float] = 14.0
    #: round 4: a smooth random LUMP field over the ball (mm rms, a sum of plane waves with
    #: wavelengths in ``lump_wl_mm``), added to every stretch's lift as a function of POSITION -
    #: so every layer at a point moves together and the stack order is untouched.  The
    #: reference's outline carries 1.24 / 0.82 px rms in harmonics 31-60 / 61-120 (3.7-7 mm /
    #: 1.8-3.6 mm wavelengths); a smooth wound ball carried 0.95 / 0.59 and 14 % of its 40-px
    #: outline windows were straighter than a circle (the reference: 0 %).  The padded bands
    #: shade over the lumps as the reference's do.
    lump_mm: float = 0.06
    lump_wl_mm: Tuple[float, float] = (3.5, 9.0)
    lump_waves: int = 48
    lump_seed: int = 4242
    #: final pass (maintainer, 2026-09-25): the SPAN - the bridged layer count low-passed inside
    #: each stretch (box passes, this half-width in mm; 0 = off), so buried crossings would not
    #: telegraph through a covering band.  Measured and left OFF: at 1.0-3.0 mm it flattened the
    #: outline (straight 40-px outline windows 19 % -> 22-27 %, outline steps 8 -> 5-7 against
    #: REFERENCE_SPEC's 8-16); the shingled fan (smokebomb_wind_fit) took the ropes away instead.
    span_mm: float = 0.0
    span_passes: int = 3
    #: the height guard's clearance (mm): a covering stretch's top is kept this far above the top
    #: beneath it wherever it can be seen (final pass 0.3: an overlap is a true step; GUARD_CLEAR_MM 0.08 before)
    guard_clear_mm: float = 0.3


BALL = BallSpec()


def lump_field(P_unit: np.ndarray, R_mm: float, rms_mm: float, wl_mm: Tuple[float, float], waves: int,
               seed: int) -> np.ndarray:
    """A smooth random field on the ball (mm): ``waves`` plane waves with random directions,
    wavelengths spread over ``wl_mm`` and phases, normalised to ``rms_mm`` rms (numpy only,
    deterministic)."""
    if rms_mm <= 0.0:
        return np.zeros(len(P_unit))
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(waves, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    lam = np.exp(rng.uniform(math.log(wl_mm[0]), math.log(wl_mm[1]), waves))
    k = d * (2.0 * math.pi / lam)[:, None]
    ph = rng.uniform(0.0, 2.0 * math.pi, waves)
    amp = lam / lam.mean()                        # longer waves a little stronger (a red spectrum)
    X = np.asarray(P_unit, np.float64) * R_mm
    out = np.zeros(len(X))
    for i in range(waves):
        out += amp[i] * np.sin(X @ k[i] + ph[i])
    return out * (rms_mm / math.sqrt(0.5 * float(np.sum(amp ** 2))))

#: the height guard's cube map (cells per face edge: ~0.2 mm cells on the 34 mm core) and
#: the least a covering stretch's top stands above the highest top beneath it (0.08 mm =
#: 1.1 px at the reference framing)
GUARD_NF = 256
#: the guard enforces the order only where a stretch can be SEEN: exposed, or within this of
#: an exposed point (under a covering edge); deeper in, the sink hides it
GUARD_VIS_MM = 0.45
#: effective keys (arc length, unit radii) closer than this are the same layer for the guard
GUARD_KEY_EPS = 0.1
#: the most the guard may raise a stretch (mm): two stretches that cross each other both ways
#: (woven) would otherwise ratchet each other up every iteration (round 2: B and D_a at the
#: right limb, 2 mm, which stood out of the outline as a squared tab)
GUARD_CAP_MM = 0.8
#: the sink's ramp (mm in under the cover) and the distance steps it is measured in
SINK_D0_MM = 0.30
SINK_D1_MM = 0.9
SINK_RADII_MM = (0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.2, 1.6)
#: exposed specks smaller than this (mm across) are dropped before the sink is measured
SPECK_MM = 0.3


def open_mask(mask: np.ndarray, du: float, da: float, r_mm: float) -> np.ndarray:
    """Morphological opening (erode then grow) of a boolean (u, a) grid by ``r_mm``."""
    ru, ra = max(r_mm / du, 0.5), max(r_mm / da, 0.5)
    er = ~_dilate_disc(~mask, ru, ra)
    return _dilate_disc(er, ru, ra) & mask


def _smoothstep(e0: float, e1: float, x) -> np.ndarray:
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def distance_from(mask: np.ndarray, du: float, da: float, radii: Sequence[float]) -> np.ndarray:
    """(nu, na) distance (mm, quantised to ``radii``; beyond the last: 2 x the last) from
    the nearest True cell of a boolean (u, a) grid, by growing it one radius at a time
    (elliptic discs, so the u and a cell sizes are honoured)."""
    out = np.full(mask.shape, 2.0 * radii[-1])
    out[mask] = 0.0
    done = mask.copy()
    prev = 0.0
    for r in radii:
        m = _dilate_disc(mask, r / du, r / da)
        new = m & ~done
        out[new] = 0.5 * (prev + r)
        done |= m
        prev = r
    return out


def section_top(prof: T.Profile, sw: T.Sweep, u, a) -> np.ndarray:
    """The tape's top surface height above its base at (u, a), mm: the section's envelope
    at the local width, narrowed by the gather, plus the gather's bump (smokebomb_tape
    Sweep.shaped) - 0 beyond the footprint."""
    u = np.asarray(u, np.float64)
    a = np.asarray(a, np.float64)
    w = sw.width_at(u)
    g = sw.gather_at(u)
    rope = prof.spec.rope_w_mm
    weff = w * (1.0 - g) + rope * g
    sg = np.maximum(weff / np.maximum(w, 1e-6), 1e-6)
    h = prof.top_h(a / sg, w)
    hw = 0.5 * weff
    x = np.clip(a / np.maximum(hw, 1e-6), -1.0, 1.0)
    return h + g * 0.5 * hw * np.sqrt(np.maximum(1.0 - x * x, 0.0)) * (np.abs(a) <= hw)

@dataclass(frozen=True)
class BallLod(T.LodSpec):
    """smokebomb_tape.LodSpec plus whether the groove (cord / body junction) is a section
    point; a coarse LOD drops it and runs straight from the cord's outer point to the body.
    ``body_chord_mm`` (round 4): the body carries evenly spaced points at least this close
    ACROSS the stretch's widest width (the fractions scale with the width, so an 18 mm band's
    0.45 / 0 chords were 4 mm long and drew a straight segment where it crossed the limb)."""
    groove: bool = True
    body_chord_mm: Optional[float] = None


#: the section and ring spacing per LOD.  LOD0: the rolled cord at -90 / -30 / 30 / 90 / 135
#: deg and the groove, the padded body at 0.96 / 0.6 / 0, the hidden skirt, rings <= 3 mm
#: (closer on tight bends, RING_TOL_MM): 18 intervals across.  LOD1 is the tape's own (groove,
#: 0.55, centre; 7 mm rings) with its edge point on the cord's LOWER shoulder (-45 deg, 0.08 mm
#: above the base: with no skirt, the outer point at 0 deg left a slit under each covering edge
#: that the limb's grazing view saw through - 219 px of background inside LOD1's disc at 1254 px,
#: 68 with the lower shoulder).  LOD2 (the ball ~27 px on a 1080p screen): the cord's lower
#: shoulder and the centre only, 8 mm rings - sagitta 64 / 280 = 0.23 mm along and
#: ~0.3 mm across a wide band, under one layer step, so no layer scaling is needed (the sink
#: takes buried runs out of the way) and the outline stays round (round 1's 16 mm rings with
#: a 2.6 x layer scale gave a polygonal outline with slabs standing proud of it)
#: round 3 (rewind builder 3): LOD0 came down from 30,991 to ~8,500 triangles (the prop budget the
#: user asked for) by carrying the rolled edge as a ROUNDED SHOULDER instead of a separate tube:
#: the cord at -60 / 30 deg (no groove point: the body runs straight into the roll), the body at
#: 0.45 / 0, the hidden skirt kept (without it the grazing limb saw white slits under covering
#: edges), rings <= 5 mm with a 0.10 mm chord tolerance on bends (1.3 px at the reference framing).
#: Measured on the clay render: round 2's five-point cord stood 0.24 mm proud of a groove as a
#: perfect tube - the judge's "smooth grey piping"; the rounded shoulder reads as padded tape.
#: LOD1: the cord's lower shoulder and the centre, 10 mm rings (~3,000); LOD2 as round 2 with 14 mm
#: rings (~1,400).
#: round 4 (rewind builder, workflow round 3): the round-3 judge read LOD0's outline as "faceted, straight
#: polygon segments" (27 % of 40-px outline windows straighter than a circle; 5 mm rings are 66 px
#: chords at the reference framing, and a wide band's 0.45 / 0 body chords were 4 mm) and its edges as
#: "piping" (the rounded shoulder carried no cord).  Now: rings <= 3.5 mm (0.045 mm chord
#: tolerance), body points no more than 3 mm apart across the band (``body_chord_mm``), the cord
#: at -40 / 45 deg PLUS the groove (the cord / body junction), the hidden skirt kept (without it:
#: 1,400-2,300 back-facing px per view and see-through slits at the limb, measured).  16.7k
#: triangles with the threads (tape 15.8k): 14 % of outline windows straight (round 3: 27 %).
#: The normal map carries the rest of the rolled cord (smokebomb_cloth.section_relief).
LODS: Dict[int, T.LodSpec] = {
    0: BallLod(cord_deg=(-40.0, 45.0), body_fracs=(0.45, 0.0), ds_mm=3.5, skirt=True, groove=True,
               body_chord_mm=3.0),
    1: BallLod(cord_deg=(-45.0,), body_fracs=(0.0,), ds_mm=10.0, skirt=False),
    2: BallLod(cord_deg=(-45.0,), body_fracs=(0.0,), ds_mm=14.0, skirt=False, groove=False),
}

#: coarse LODs whose edge vertex takes the body's normal at this share of the groove's |tc|
#: (build_part; round 2)
LOD_EDGE_NORMAL_INSET: Dict[int, float] = {2: 0.85}

#: Unreal 5.8.2 drops triangles under 0.005 mm2 at build time (measured, round 1); with a
#: margin nothing that small is built
MIN_TRI_MM2 = 0.008


def section_points(prof: T.Profile, L: T.LodSpec, w_max: Optional[float] = None) -> np.ndarray:
    """smokebomb_tape.section_points for an explicit LodSpec (and, with ``body_chord_mm`` and
    ``w_max``, enough evenly spaced body points that no body chord is longer than that)."""
    ts: List[float] = []
    for sd in (-1, 1):
        m = (prof.region == T.CORD) & (prof.side == sd)
        ph, tt = prof.phi[m], prof.tc[m]
        order = np.argsort(ph)
        for deg in L.cord_deg:
            r = math.radians(deg)
            if r < prof.phi_j - 1e-6:
                ts.append(float(np.interp(r, ph[order], tt[order])))
        if getattr(L, "groove", True):
            ts.append(float(np.interp(prof.phi_j, ph[order], tt[order])))
    mb = prof.region == T.BODY
    ab, tb = prof.a[mb], prof.tc[mb]
    amax = ab.max()
    fracs = list(L.body_fracs)
    bc = getattr(L, "body_chord_mm", None)
    if bc and w_max is not None:
        Aw = amax + float(prof.dW(w_max))                 # the body's actual half-extent (mm)
        n = int(math.ceil(max(Aw, 1e-6) / bc - 1e-9))
        if n >= 2:
            fracs = [k / n for k in range(n)]
    for fr in fracs:
        for sgn in ((-1, 1) if fr > 0 else (1,)):
            ts.append(float(np.interp(sgn * fr * amax, ab, tb)))
    if L.skirt:
        ts += [float(prof.tc[0]), float(prof.tc[-1])]
    return np.unique(np.round(np.asarray(ts), 9))


# =========================================================================== the drape field
class DrapeField:
    """The low-pass (Gaussian, sigma mm on the ball) of the TOP surface's layer count
    (stretches beneath the top one, smokebomb_wind's stack), on a 2 deg lat-long grid in the
    camera frame, bilinear after that."""

    def __init__(self, wd: W.Winding, grid: W.StackGrid, sigma_mm: float, radius_mm: float, step_deg: float = 2.0):
        nf = grid.n_face
        cen = W._cube_centres(nf)
        ntop = np.maximum(grid.count - 1, 0).astype(np.float64)
        self.step = step_deg
        nlat = int(round(180.0 / step_deg))
        nlon = int(round(360.0 / step_deg))
        lat = np.degrees(np.arcsin(np.clip(cen[:, 1], -1, 1)))
        lon = np.degrees(np.arctan2(cen[:, 0], cen[:, 2])) % 360.0
        il = np.clip(((lat + 90.0) / step_deg).astype(int), 0, nlat - 1)
        io = np.clip((lon / step_deg).astype(int), 0, nlon - 1)
        flat = il * nlon + io
        s = np.bincount(flat, weights=ntop, minlength=nlat * nlon)
        c = np.bincount(flat, minlength=nlat * nlon)
        raw = np.where(c > 0, s / np.maximum(c, 1), np.nan).reshape(nlat, nlon)
        if np.isnan(raw).any():                 # (the poles' rows are never empty at nf=256)
            raw = np.where(np.isnan(raw), np.nanmean(raw), raw)
        self.raw = raw
        glat = -90.0 + (np.arange(nlat) + 0.5) * step_deg
        glon = (np.arange(nlon) + 0.5) * step_deg
        LA, LO = np.meshgrid(np.radians(glat), np.radians(glon), indexing="ij")
        P = np.stack([np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)], -1).reshape(-1, 3)
        wgt = np.cos(LA).ravel()
        v = raw.ravel()
        sig = sigma_mm / radius_mm
        out = np.empty(len(P))
        for i in range(0, len(P), 1500):
            d = np.clip(P[i:i + 1500] @ P.T, -1.0, 1.0)
            ang = np.arccos(d)
            k = np.exp(-0.5 * (ang / sig) ** 2) * wgt[None, :]
            out[i:i + 1500] = (k @ v) / k.sum(1)
        self.lp = out.reshape(nlat, nlon)
        self.glat, self.glon = glat, glon

    def __call__(self, p_cam: np.ndarray) -> np.ndarray:
        p = W.normalize(np.asarray(p_cam, np.float64))
        lat = np.degrees(np.arcsin(np.clip(p[..., 1], -1, 1)))
        lon = np.degrees(np.arctan2(p[..., 0], p[..., 2])) % 360.0
        nlat, nlon = self.lp.shape
        y = np.clip((lat + 90.0) / self.step - 0.5, 0, nlat - 1.000001)
        x = (lon / self.step - 0.5) % nlon
        i, j = np.floor(y).astype(int), np.floor(x).astype(int)
        fy, fx = y - i, x - j
        j1 = (j + 1) % nlon
        i1 = np.minimum(i + 1, nlat - 1)
        L = self.lp
        return ((L[i, j] * (1 - fx) + L[i, j1] * fx) * (1 - fy) + (L[i1, j] * (1 - fx) + L[i1, j1] * fx) * fy)


# =========================================================================== the outline's shape
#: MEASURED, typed in (round 3's props_lib.smokebomb_outline, measured with the round-2
#: adversary's own outline instrument on the reference: half-maximum edge, 1440 rays, circle
#: fit centre (627.33, 628.85), R 464.07 px): the reference outline's Fourier coefficients
#: (cos, sin) in px, n = 0..24.  The build never reads the reference image.
REF_OUTLINE_PX: Tuple[Tuple[float, float], ...] = (
    (-0.036, 0.0), (0.034, -0.081), (-1.501, -4.322), (3.077, 0.639), (-0.606, -1.378),
    (1.142, 2.154), (-1.354, 1.564), (-1.204, -1.556), (0.43, -0.516), (-0.465, 0.215),
    (-0.725, -0.279), (-1.992, -0.27), (0.325, -1.014), (-0.468, 0.167), (-0.68, 0.313),
    (-0.29, -0.113), (0.624, -0.943), (0.039, 0.939), (-0.842, 0.146), (-1.123, -0.11),
    (0.28, -0.398), (0.713, -0.023), (-0.275, 0.272), (-0.138, -0.756), (-0.084, 0.156),
)
REF_OUTLINE_R_PX = 464.07


class OutlineShape:
    """The low-order shape of the reference's outline (REFERENCE_SPEC 1: ellipse 1.020 at
    125 deg, flat at 30-60 and 180-210, full at 120-150), added to every layer's lift so the
    silhouette carries it:

        delta r (P) = sum_{n=2..N} (A_n cos n theta + B_n sin n theta) x (1 - z^2)

    theta = P's image angle, z = P's component along the view axis, so the term is full on
    the limb (which is what the silhouette shows) and nothing at the front and back poles.
    ``measured`` is the correction the build adds after measuring its own outline."""

    def __init__(self, radius_mm: float, n_max: int = 12, measured: Optional[np.ndarray] = None):
        k = radius_mm / REF_OUTLINE_R_PX
        self.n_max = int(n_max)
        self.coef = np.zeros((self.n_max + 1, 2))
        for n in range(2, min(self.n_max, len(REF_OUTLINE_PX) - 1) + 1):
            self.coef[n] = (REF_OUTLINE_PX[n][0] * k, REF_OUTLINE_PX[n][1] * k)
        self.target = self.coef.copy()
        self.measured = np.zeros_like(self.coef) if measured is None else np.asarray(measured, np.float64)

    def with_correction(self, corr: np.ndarray) -> "OutlineShape":
        out = OutlineShape.__new__(OutlineShape)
        out.n_max, out.target = self.n_max, self.target
        out.measured = self.measured + np.asarray(corr, np.float64)
        out.coef = out.target + out.measured
        return out

    def __call__(self, P_cam: np.ndarray) -> np.ndarray:
        P = np.asarray(P_cam, np.float64)
        th = np.arctan2(P[..., 1], P[..., 0])
        w = np.clip(1.0 - P[..., 2] ** 2, 0.0, 1.0)
        out = np.zeros(th.shape)
        for n in range(2, self.n_max + 1):
            a, b = self.coef[n]
            if a or b:
                out = out + a * np.cos(n * th) + b * np.sin(n * th)
        return out * w


def fourier(r: np.ndarray, n_max: int) -> np.ndarray:
    """(n_max + 1, 2) cos / sin coefficients of r sampled uniformly on [0, 2 pi)."""
    F = np.fft.rfft(r) / len(r)
    out = np.zeros((n_max + 1, 2))
    out[0, 0] = F[0].real
    for n in range(1, min(n_max, len(F) - 1) + 1):
        out[n, 0] = 2 * F[n].real
        out[n, 1] = -2 * F[n].imag
    return out


# =========================================================================== stack queries
def stack_counts(wd: W.Winding, g: W.StackGrid, P_cam: np.ndarray, sid: np.ndarray):
    """(below, above) stretch counts at camera-frame unit points P lying on samples sid,
    weaves applied (smokebomb_wind.layers_below and its mirror)."""
    P_cam = np.asarray(P_cam, np.float64)
    sid = np.asarray(sid)
    ek = wd.effective_key(P_cam, sid)
    ci = W._cube_index(P_cam, g.n_face)
    K, S = g.keys[ci], g.samples[ci]
    other = (S >= 0) & (np.abs(S - sid[:, None]) > 3 * g.run_len)
    return (np.sum(other & (K < ek[:, None]), axis=1), np.sum(other & (K > ek[:, None]), axis=1))


def exposure_along(wd: W.Winding, g: W.StackGrid, nv: int = 21, chunk: int = 4000) -> np.ndarray:
    """Per winding sample: the share of its cross-section (nv points) that nothing covers."""
    N = wd.s.size
    v = np.linspace(-1.0, 1.0, nv)
    out = np.zeros(N)
    for i0 in range(0, N, chunk):
        ii = np.arange(i0, min(N, i0 + chunk))
        P = wd.points(v, idx=ii).reshape(-1, 3)
        sid = np.repeat(ii, nv)
        _b, ab = stack_counts(wd, g, P, sid)
        out[ii] = (ab == 0).reshape(len(ii), nv).mean(1)
    return out


def exposed_runs(expfrac: np.ndarray, ds_mm: float, margin_mm: float) -> List[Tuple[int, int]]:
    on = expfrac > 0
    k = int(math.ceil(margin_mm / ds_mm))
    ond = on.copy()
    for s in range(1, k + 1):
        ond[s:] |= on[:-s]
        ond[:-s] |= on[s:]
    runs = []
    i, n = 0, len(ond)
    while i < n:
        if ond[i]:
            j = i
            while j + 1 < n and ond[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


# =========================================================================== grid helpers
def _shift_max(a: np.ndarray, k: int, axis: int) -> np.ndarray:
    out = a.copy()
    for s in range(1, k + 1):
        if axis == 0:
            out[s:] = np.maximum(out[s:], a[:-s])
            out[:-s] = np.maximum(out[:-s], a[s:])
        else:
            out[:, s:] = np.maximum(out[:, s:], a[:, :-s])
            out[:, :-s] = np.maximum(out[:, :-s], a[:, s:])
    return out


def _dilate_disc(m: np.ndarray, ru: float, ra: float) -> np.ndarray:
    """Grow a boolean (u, a) mask by an ellipse of radii ru, ra cells."""
    out = m.copy()
    iu, ia = int(math.ceil(ru)), int(math.ceil(ra))
    for du in range(-iu, iu + 1):
        half = ra * math.sqrt(max(0.0, 1.0 - (du / max(ru, 1e-9)) ** 2)) if ru > 0 else ra
        k = int(math.floor(half))
        if du > 0:
            src = m[:-du]
            row = _shift_max(src.astype(np.uint8), k, 1).astype(bool)
            out[du:] |= row
        elif du < 0:
            src = m[-du:]
            row = _shift_max(src.astype(np.uint8), k, 1).astype(bool)
            out[:du] |= row
        else:
            out |= _shift_max(m.astype(np.uint8), k, 1).astype(bool)
    return out


def _bridge(raw: np.ndarray, du: float, da: float, bridge_mm: float) -> np.ndarray:
    """smokebomb_tape.stack_lift's bridging on a raw stack height grid: max over half the
    bridge each way, three box passes, never below the raw envelope."""
    k = max(1, int(round(0.5 * bridge_mm / da)))
    ku = max(1, int(round(0.5 * bridge_mm / du)))
    env = _shift_max(_shift_max(raw, k, 1), ku, 0)
    sm = env.copy()
    for _ in range(3):
        sm = T._box(sm, ku, k)
    return np.maximum(sm, raw)


class SAT:
    """Summed-area table of a boolean (u, a) grid: rectangle-any queries in O(1)."""

    def __init__(self, m: np.ndarray, u0: float, du: float, a0: float, da: float):
        self.S = np.zeros((m.shape[0] + 1, m.shape[1] + 1), np.int64)
        self.S[1:, 1:] = np.cumsum(np.cumsum(m.astype(np.int64), 0), 1)
        self.u0, self.du, self.a0, self.da = u0, du, a0, da
        self.nu, self.na = m.shape

    def any(self, u_lo, u_hi, a_lo, a_hi) -> np.ndarray:
        i0 = np.clip(np.floor((np.asarray(u_lo) - self.u0) / self.du + 0.5).astype(int), 0, self.nu)
        i1 = np.clip(np.floor((np.asarray(u_hi) - self.u0) / self.du + 0.5).astype(int) + 1, 0, self.nu)
        j0 = np.clip(np.floor((np.asarray(a_lo) - self.a0) / self.da + 0.5).astype(int), 0, self.na)
        j1 = np.clip(np.floor((np.asarray(a_hi) - self.a0) / self.da + 0.5).astype(int) + 1, 0, self.na)
        i1 = np.maximum(i1, i0)
        j1 = np.maximum(j1, j0)
        S = self.S
        tot = S[i1, j1] - S[i0, j1] - S[i1, j0] + S[i0, j0]
        return tot > 0


# =========================================================================== the fold guard
class FoldSafeSweep(T.Sweep):
    """smokebomb_tape.Sweep that never folds its INNER edge.

    Where a pass bends hard in the plane (REFERENCE_SPEC's A, R_in, C and D_a bend a lot: the
    winder's edge strain reaches 112 - 155 %), the geodesic curvature kappa_g times the
    across offset a passes 1 on the inner side and a straight sweep folds back through
    itself.  A real tape gathers there.  So on the inner side the across offset is
    compressed smoothly once kappa_g a passes 0.70, saturating at 0.97 (C1, identity
    below): the geometry gathers, the texture keeps its (u, t) coordinates."""
    X0 = 0.70
    XMAX = 0.97

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        dT = np.gradient(self.T, self.s, axis=0)
        kg = np.sum(dT * np.cross(self.N, self.T), 1)
        step = max(float(np.median(np.diff(self.s))), 1e-6)
        k = max(1, int(round(0.75 / step)))
        ker = np.exp(-0.5 * (np.arange(-2 * k, 2 * k + 1) / k) ** 2)
        ker /= ker.sum()
        self.kg = np.convolve(np.pad(kg, 2 * k, mode="edge"), ker, "valid")

    def _compress(self, u, a):
        kg = np.interp(np.asarray(u, np.float64), self.s, self.kg)
        a = np.asarray(a, np.float64)
        x = kg * a
        x0, xm = self.X0, self.XMAX
        z = np.maximum(x - x0, 0.0) / (xm - x0)
        over = x > x0
        y = np.where(over, x0 + (xm - x0) * np.tanh(z), x)
        d = np.where(over, 1.0 / np.cosh(z) ** 2, 1.0)
        safe = np.abs(kg) > 1e-9
        a_eff = np.where(over & safe, y / np.where(safe, kg, 1.0), a)
        return a_eff, d

    def folded_share(self) -> float:
        """share of samples where the open half-width would pass the guard's onset"""
        hw = 0.5 * (self.w * (1.0 - self.g) + self.profile.spec.rope_w_mm * self.g)
        return float(np.mean(np.abs(self.kg) * hw > self.X0))

    def eval(self, u, tc, normals: bool = True):
        u = np.asarray(u, np.float64)
        tc = np.asarray(tc, np.float64)
        u, tc = np.broadcast_arrays(u, tc)
        C, Tt, N, B, Ra, w, g, tw = self.frame(u)
        a, h, ta, th, _ = self.shaped(tc, w, g, tw)
        a, d = self._compress(u, a)
        ta = ta * d
        nn = np.maximum(np.hypot(ta, th), 1e-12)
        ta, th = ta / nn, th / nn
        P, dirv, ca, sa, rr = self._place(u, a, h, C, N, B, Ra)
        if not normals:
            return P
        eps = 0.01
        dPdu = (self.eval(u + eps, tc, normals=False) - self.eval(u - eps, tc, normals=False)) / (2 * eps)
        Ba = -N * sa + B * ca
        if self.lift is not None:
            dLda = ((self.lift(u, a + eps) - self.lift(u, a - eps)) / (2 * eps))[..., None]
        else:
            dLda = 0.0
        dPda = (rr / Ra[..., None]) * Ba + dLda * dirv
        dPdt = ta[..., None] * dPda + th[..., None] * dirv
        n = np.cross(dPdu, dPdt)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
        return P, n

    def eval_ah(self, u, a, h):
        u = np.asarray(u, np.float64)
        C, Tt, N, B, Ra, w, g, tw = self.frame(u)
        a_eff, _ = self._compress(u, np.asarray(a, np.float64))
        P, *_ = self._place(u, a_eff, np.asarray(h, np.float64), C, N, B, Ra)
        return P


def fold_safe_sweep(d: Dict[str, np.ndarray], idx, profile: T.Profile, name: str) -> FoldSafeSweep:
    idx = np.asarray(idx)
    return FoldSafeSweep(d["points_mm"][idx], profile, normals=d["normals"][idx], width_mm=d["width_mm"][idx],
                         gather=d["gather"][idx], u0_mm=float(d["s_mm"][idx[0]]), tape_id=0, name=name)


# =========================================================================== stretches
@dataclass
class Stretch:
    index: int
    key: str                  # atlas / object key, e.g. "k07_W"
    pass_name: str
    i0: int
    i1: int
    sweep: T.Sweep            # LOD0 lift
    u0: float
    du: float
    a0: float
    da: float
    exposed: np.ndarray       # (nu, na) bool
    below: np.ndarray         # (nu, na) raw stretch count beneath
    lift0: np.ndarray         # (nu, na) mm, LOD0 lift (bridged, draped)
    sat_keep0: SAT = None
    sat_keep1: SAT = None
    chunks: List[float] = field(default_factory=list)      # chunk boundaries in u (incl. ends)
    exposed_area_mm2: float = 0.0
    #: the height guard's per-grid-point data (flattened (nu * na)): cube cell, effective
    #: key, inside the footprint, the section's top height above the base (mm)
    g_cell: np.ndarray = None
    g_ek: np.ndarray = None
    g_in: np.ndarray = None
    g_h: np.ndarray = None
    guard_mm: np.ndarray = None
    dexp: np.ndarray = None   # (nu, na) mm from the nearest exposed grid point (SINK_RADII_MM steps)
    g_sag: np.ndarray = None  # LOD0 body chord sag allowance at each grid point (mm)

    @property
    def u_range(self):
        return self.sweep.u_range

    def breaks(self) -> List[float]:
        return list(self.chunks[1:-1])

    def chunk_of(self, u) -> np.ndarray:
        c = np.asarray(self.chunks)
        return np.clip(np.searchsorted(c, np.asarray(u), side="right") - 1, 0, len(c) - 2)


class Ball:
    """The wound ball: winding, stack, drape, stretches."""

    def __init__(self, spec: BallSpec = BALL, tape: T.TapeSpec = T.TapeSpec(), log: Callable = print,
                 winding: Optional[W.Winding] = None, drape: Optional[DrapeField] = None,
                 shape: Optional[OutlineShape] = None, expfrac: Optional[np.ndarray] = None):
        self.spec = spec
        self.log = log
        self.wd = W.reference_winding() if winding is None else winding
        self.grid = self.wd.stack_grid(256)
        if spec.crown_mm is not None:
            tape = replace(tape, crown_mm=float(spec.crown_mm))
        self.prof = T.build_profile(tape)
        self.prof.crown_ref_w = spec.crown_ref_w_mm
        self.R = spec.core_mm
        self.d = self.wd.to_mm(self.R)
        self.ds_mm = self.wd.ds * self.R
        self.drape = drape if drape is not None else DrapeField(self.wd, self.grid, spec.drape_sigma_mm,
                                                                spec.outline_mm)
        self.shape = shape if shape is not None else OutlineShape(spec.outline_mm, spec.outline_harmonics)
        self.expfrac = expfrac
        self.stretches: List[Stretch] = []
        self.lift_mean_top = 0.0

    # ---------------------------------------------------------------- exposure
    def find_stretches(self):
        sp = self.spec
        wd = self.wd
        if self.expfrac is None:
            self.expfrac = exposure_along(wd, self.grid, sp.exposure_v)
        runs = exposed_runs(self.expfrac, self.ds_mm, sp.run_margin_mm)
        self.runs = runs
        self.log(f"  exposure: {len(runs)} exposed runs, "
                 f"{sum(b - a + 1 for a, b in runs) * self.ds_mm:.0f} mm of {wd.s[-1] * self.R:.0f} mm of tape")
        return runs

    def build_stretch(self, k: int, i0: int, i1: int) -> Stretch:
        sp = self.spec
        wd, d = self.wd, self.d
        idx = np.arange(i0, i1 + 1)
        pname = wd.names[int(np.bincount(wd.pass_idx[idx]).argmax())]
        key = f"k{k:02d}_{pname}"
        sw = fold_safe_sweep(d, idx, self.prof, key)
        u0, u1 = sw.u_range
        wmax = float(np.max(d["width_mm"][idx]))
        du, da = sp.grid_du_mm, sp.grid_da_mm
        us = np.arange(u0, u1 + 0.5 * du, du)
        a_half = 0.5 * wmax + sp.grid_margin_mm
        as_ = np.arange(-a_half, a_half + 0.5 * da, da)
        UU, AA = np.meshgrid(us, as_, indexing="ij")
        C, Tt, N, B, Ra, *_ = sw.frame(UU.ravel())
        ang = (AA.ravel() / Ra)[:, None]
        Pb = W.normalize(N * np.cos(ang) + B * np.sin(ang))           # build frame unit
        Pc = W.build_to_cam(Pb)
        sid = np.clip(i0 + np.searchsorted(sw.s, UU.ravel()), i0, i1)
        below = np.zeros(UU.size, np.int64)
        above = np.zeros(UU.size, np.int64)
        for c0 in range(0, UU.size, 200000):
            sl = slice(c0, c0 + 200000)
            below[sl], above[sl] = stack_counts(wd, self.grid, Pc[sl], sid[sl])
        weff = np.interp(UU.ravel(), sw.s, d["width_eff_mm"][idx])
        inside = np.abs(AA.ravel()) <= 0.5 * weff
        exposed = (inside & (above == 0)).reshape(UU.shape)
        below = below.reshape(UU.shape)
        raw = sp.layer_mm * below.astype(np.float64)
        bridged = _bridge(raw, du, da, sp.bridge_mm)
        if sp.span_mm > 0.0:
            ku = max(1, int(round(sp.span_mm / du)))
            ka = max(1, int(round(sp.span_mm / da)))
            sm = bridged
            for _ in range(max(1, sp.span_passes)):
                sm = T._box(sm, ku, ka)
            bridged = sm
        drape = sp.layer_mm * sp.drape_share * self.drape(Pc).reshape(UU.shape)
        # the SINK: where this stretch runs on under whatever covers it, it dives (hidden)
        # below the covering tape's underside, so neither its vertices nor its cords can
        # stand through the cover's chords; the dive starts SINK_D0_MM in under the covering
        # edge, so the visible lower tape still meets the edge's crevice at full height
        # (measured from the exposure OPENED by SPECK_MM: a lone grid cell the stack calls
        # exposed inside a cover is the stack grid's discretisation, not a window)
        dexp = distance_from(open_mask(exposed, du, da, SPECK_MM), du, da, SINK_RADII_MM)
        sink = sp.sink_mm * _smoothstep(SINK_D0_MM, SINK_D1_MM, dexp)
        lift0 = bridged - drape + self.shape(Pc).reshape(UU.shape) - sink
        if sp.lump_mm > 0.0:
            lift0 = lift0 + lump_field(Pb, self.R, sp.lump_mm, sp.lump_wl_mm, sp.lump_waves,
                                       sp.lump_seed).reshape(UU.shape)
        st = Stretch(index=k, key=key, pass_name=pname, i0=i0, i1=i1, sweep=sw, u0=float(us[0]), du=du,
                     a0=float(as_[0]), da=da, exposed=exposed, below=below, lift0=lift0)
        st.dexp = dexp
        st.exposed_area_mm2 = float(exposed.sum() * du * da)
        # the height guard's data: where each grid point lies (cube cell), its effective key
        # (weaves applied), whether it is inside the footprint, the section's top there
        st.g_cell = W._cube_index(Pc, GUARD_NF)
        ekk = np.empty(UU.size)
        for c0 in range(0, UU.size, 200000):
            sl = slice(c0, c0 + 200000)
            ekk[sl] = wd.effective_key(Pc[sl], sid[sl])
        st.g_ek = ekk
        st.g_in = np.abs(AA.ravel()) <= 0.5 * weff + 0.05
        st.g_h = section_top(self.prof, sw, UU.ravel(), AA.ravel())
        # LOD0's body chords sag below the true top (a wide band's 0.6 -> 0 chord on the
        # ball's curvature, plus the crown): the guard wants the cover's MESH above
        wv = np.interp(UU.ravel(), sw.s, sw.w)
        body = np.abs(AA.ravel()) < 0.42 * wv
        st.g_sag = np.where(body, (0.3 * wv) ** 2 / (8.0 * self.R) + 0.3 * 0.3 ** 2, 0.0)
        st.guard_mm = np.zeros(UU.shape)
        keep0 = _dilate_disc(exposed, sp.keep_mm / du, sp.keep_mm / da)
        keep1 = _dilate_disc(exposed, sp.keep_coarse_mm / du, sp.keep_coarse_mm / da)
        st.sat_keep0 = SAT(keep0, st.u0, du, st.a0, da)
        st.sat_keep1 = SAT(keep1, st.u0, du, st.a0, da)
        L = u1 - u0
        n = max(1, int(math.ceil(L / sp.chunk_mm - 1e-9)))
        st.chunks = list(np.linspace(u0, u1, n + 1))
        sw.lift = T.LiftGrid(st.u0, du, st.a0, da, lift0)
        return st

    def guard_heights(self, iterations: int = 12, clear_mm: float = GUARD_CLEAR_MM, grow_mm: float = 1.5):
        """The HEIGHT GUARD: a stretch that lies above another (by the stack, weaves applied)
        must also lie above it in 3-D.  The per-stretch lift (raw layer count, bridged,
        draped) is a stack of COUNTS; a rope (gather 1) or a cord stands taller than one layer
        step, and bridging lifts a lower stretch toward a step it runs beside - so a buried
        stretch's mesh could stand through the one covering it (measured on the first
        build: 5,100 px of the reference view showed a buried stretch through its cover -
        D_a through X at the right limb, R_in's rope through C at the left limb).

        Here, per cube cell (GUARD_NF), every stretch's top radius (base + lift + the
        section's top incl. the gather's bump) is compared with every stretch above it in
        that cell; where a covering stretch's top is not ``clear_mm`` above the highest top
        beneath it, its lift is raised by the shortfall, grown over ``grow_mm`` and
        smoothed (the tape spans the bump instead of creasing round it).  Raising a stretch
        can push the one above it: a few Gauss-Seidel sweeps settle it.  Returns stats."""
        sts = [st for st in self.stretches if st.g_cell is not None]
        if not sts:
            return {}
        NS = len(self.stretches)
        stats = []
        keep_lim = self.spec.keep_mm + 0.3
        cand = {st.index: st.g_in & (st.dexp.ravel() <= keep_lim) for st in sts}
        query = {st.index: (st.dexp.ravel() <= GUARD_VIS_MM)[cand[st.index]] for st in sts}
        for it in range(iterations):
            cells, sids, eks, trs, owners = [], [], [], [], []
            for st in sts:
                m = cand[st.index]
                cells.append(st.g_cell[m])
                sids.append(np.full(int(m.sum()), st.index, np.int64))
                eks.append(st.g_ek[m])
                trs.append(self.R + (st.lift0 + st.guard_mm).ravel()[m] + st.g_h[m])
            cell = np.concatenate(cells)
            sid = np.concatenate(sids)
            ek = np.concatenate(eks)
            tr = np.concatenate(trs)
            gkey = cell.astype(np.int64) * NS + sid
            ug, inv = np.unique(gkey, return_inverse=True)
            gmax = np.full(len(ug), -np.inf)
            np.maximum.at(gmax, inv, tr)
            gek = np.bincount(inv, weights=ek, minlength=len(ug)) / np.bincount(inv, minlength=len(ug))
            gcell = ug // NS
            order = np.lexsort((gek, gcell))            # by cell, then key (bottom first)
            c_o, v_o = gcell[order], gmax[order]
            # exclusive prefix max within each cell: shift by the cell's rank so maxima reset
            span = float(np.nanmax(np.abs(v_o))) * 4.0 + 10.0
            first = np.r_[True, c_o[1:] != c_o[:-1]]
            rank = np.cumsum(first) - 1
            acc = np.maximum.accumulate(v_o + rank * span) - rank * span
            # only a stretch whose key is at least GUARD_KEY_EPS lower lies BENEATH: two pieces of
            # the tape within a hair of the same arc length are the same layer (a connector's run-on
            # next to the pass it joins), and guarding them against each other ratchets both up
            # (round 2: X and D_a at the right limb, 0.01 apart, were raised 2.2 mm; the covering B
            # then stood 2 mm proud of the limb as a squared tab)
            k_o = gek[order]
            comb = rank.astype(np.float64) * 4096.0 + k_o
            j = np.searchsorted(comb, comb - GUARD_KEY_EPS, side="left")
            start = np.maximum.accumulate(np.where(first, np.arange(len(first)), 0))
            below = np.where(j > start, acc[np.maximum(j - 1, 0)], -np.inf)
            req = np.empty(len(ug))
            req[order] = below
            sag = np.concatenate([st.g_sag[cand[st.index]] for st in sts])
            need_all = req[inv] + clear_mm + sag - tr    # > 0: this point's top is too low
            qall = np.concatenate([query[st.index] for st in sts])
            need_all = np.where(qall & np.isfinite(need_all), need_all, -np.inf)
            worst = float(need_all.max()) if need_all.size else 0.0
            n_bad = int(np.sum(need_all > 1e-4))
            stats.append({"iteration": it, "points_short": n_bad, "worst_mm": round(max(worst, 0.0), 4)})
            if n_bad == 0:
                break
            off = 0
            for st in sts:
                m = cand[st.index]
                k = int(m.sum())
                need = np.zeros(st.lift0.size)
                nd = need_all[off:off + k]
                need[m] = np.maximum(nd, 0.0)
                off += k
                need = need.reshape(st.lift0.shape)
                if not (need > 1e-4).any():
                    continue
                ku = max(1, int(round(grow_mm / st.du)))
                ka = max(1, int(round(grow_mm / st.da)))
                env = _shift_max(_shift_max(need, ka, 1), ku, 0)
                sm = env
                for _ in range(2):
                    sm = T._box(sm, ku, ka)
                st.guard_mm = np.minimum(st.guard_mm + np.maximum(sm, need), GUARD_CAP_MM)
        for st in sts:
            st.lift0 = st.lift0 + st.guard_mm
            st.sweep.lift = T.LiftGrid(st.u0, st.du, st.a0, st.da, st.lift0)
        raised = np.concatenate([st.guard_mm.ravel() for st in sts])
        out = {"iterations": stats, "cells_per_face": GUARD_NF, "clear_mm": clear_mm, "grow_mm": grow_mm,
               "raised_share": round(float(np.mean(raised > 1e-4)), 4),
               "raised_p99_mm": round(float(np.percentile(raised, 99)), 4), "raised_max_mm": round(float(raised.max()), 4)}
        self.guard = out
        return out

    def build(self):
        runs = self.find_stretches()
        self.stretches = []
        for k, (i0, i1) in enumerate(runs):
            st = self.build_stretch(k, i0, i1)
            self.stretches.append(st)
        if self.spec.guard:
            g = self.guard_heights(clear_mm=self.spec.guard_clear_mm)
            self.log(f"  height guard: {g.get('iterations')}, raised share {g.get('raised_share')}, "
                     f"p99 {g.get('raised_p99_mm')} mm, max {g.get('raised_max_mm')} mm")
        tops = np.concatenate([st.lift0[st.exposed] for st in self.stretches if st.exposed.any()])
        self.lift_mean_top = float(np.mean(tops))
        self.log(f"  {len(self.stretches)} stretches; exposed {sum(s.exposed_area_mm2 for s in self.stretches):.0f} mm2; "
                 f"top lift mean {self.lift_mean_top:.3f} mm, p5/p95 {np.percentile(tops, 5):.3f}/{np.percentile(tops, 95):.3f}")
        return self

    # ---------------------------------------------------------------- LOD lift
    def lift_for_lod(self, st: Stretch, lod: int) -> T.LiftGrid:
        s = self.spec.lod_layer_scale[lod]
        v = st.lift0 if s == 1.0 else (s * (st.lift0 - self.lift_mean_top) + self.lift_mean_top)
        return T.LiftGrid(st.u0, st.du, st.a0, st.da, v)

    def outline_profile(self, n: int = 1440) -> np.ndarray:
        """r(theta) of the reference view's outline (mm): the largest projected radius of the
        exposed top surface in each of ``n`` image-angle bins (the same quantity the render's
        silhouette instrument measures, before the cloth's fray)."""
        r = np.full(n, -np.inf)
        for st in self.stretches:
            if not st.exposed.any():
                continue
            Q, _u, _a = _exposed_top_points(self, st, 1)
            th = np.arctan2(Q[:, 2], Q[:, 0]) % (2 * np.pi)
            rr = np.hypot(Q[:, 0], Q[:, 2])
            b = np.clip((th / (2 * np.pi) * n).astype(int), 0, n - 1)
            np.fmax.at(r, b, rr)
        bad = ~np.isfinite(r)
        if bad.any():
            idx = np.arange(n)
            r[bad] = np.interp(idx[bad], idx[~bad], r[~bad], period=n)
        return r

    def outline_report(self, n_max: int = 12) -> Dict[str, object]:
        r = self.outline_profile()
        F = fourier(r, n_max)
        tgt = self.shape.target.copy()
        tgt[0, 0] = self.spec.outline_mm
        err = F - tgt
        err[1] = 0.0
        return {"mean_mm": round(float(F[0, 0]), 4), "rms_dev_pct": round(float(np.std(r) / np.mean(r) * 100), 3),
                "min_mm": round(float(r.min()), 3), "max_mm": round(float(r.max()), 3),
                "harmonic_amp_px": [round(float(np.hypot(*F[k]) / self.spec.outline_mm * REF_OUTLINE_R_PX), 2)
                                    for k in range(2, n_max + 1)],
                "target_amp_px": [round(float(np.hypot(*tgt[k]) / self.spec.outline_mm * REF_OUTLINE_R_PX), 2)
                                  for k in range(2, n_max + 1)],
                "harmonic_err_rms_px": round(float(np.sqrt((err[2:] ** 2).sum() / 2) / self.spec.outline_mm
                                                   * REF_OUTLINE_R_PX), 3),
                "_err": err, "_r": r}

    def limb_radius_estimate(self, band: float = 0.012) -> Dict[str, float]:
        """The reference view's outline radius, predicted from the stretch grids: every
        exposed grid point within ``band`` of the limb (camera z ~ 0), at its base radius +
        lift + the section's top height there."""
        vals = []
        for st in self.stretches:
            if not st.exposed.any():
                continue
            ii, jj = np.nonzero(st.exposed)
            u = st.u0 + ii * st.du
            a = st.a0 + jj * st.da
            C, Tt, N, B, Ra, w, g, tw = st.sweep.frame(u)
            ang = (a / Ra)[:, None]
            Pb = W.normalize(N * np.cos(ang) + B * np.sin(ang))
            lim = np.abs(Pb[:, 1]) < band
            if not lim.any():
                continue
            h = self.prof.top_h(a[lim] / np.maximum(1.0 - g[lim] * (1 - self.prof.spec.rope_w_mm / np.maximum(w[lim], 1e-6)), 1e-6),
                                w[lim])
            vals.append(self.R + st.lift0[ii[lim], jj[lim]] + h)
        v = np.concatenate(vals) if vals else np.array([self.R])
        return {"mean": float(v.mean()), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
                "n": int(v.size)}


# =========================================================================== faces per LOD
@dataclass
class FaceSet:
    """A stretch's kept faces at one LOD, before evaluation."""
    us: np.ndarray            # ring u
    tc: np.ndarray            # (nr, npf) centred tc of each ring's section points
    faces: np.ndarray         # (F, 4) indices into the (nr * npf) grid
    chunk: np.ndarray         # (F,) chunk index


#: chord tolerance per LOD (mm): a ring interval never sags more than this against the
#: tape's EDGE, which curves with the ball (1 / R) and in the plane (the pass's geodesic
#: curvature, tighter on the inner edge).  LOD0 0.03 mm = 0.4 px at the reference framing.
RING_TOL_MM = {0: 0.045, 1: 0.30, 2: 0.50}


def adaptive_rings(sw: T.Sweep, ds_max: float, tol_mm: float, breaks: Sequence[float] = ()) -> np.ndarray:
    """Ring positions along the sweep: at most ``ds_max`` apart and closer where an edge
    curves, so no chord sags more than ``tol_mm``; plus every break."""
    s = sw.s
    dT = np.gradient(sw.T, s, axis=0)
    kn = np.abs(np.sum(dT * sw.N, 1))
    kg = np.abs(np.sum(dT * np.cross(sw.N, sw.T), 1))
    # the FOOTPRINT half-width (a gathered stretch is a rope: its edges are the rope's)
    hw = 0.5 * (sw.w * (1.0 - sw.g) + sw.profile.spec.rope_w_mm * sw.g)
    ke = kg / np.maximum(1.0 - np.minimum(kg * hw, 0.9), 0.1)
    kap = np.sqrt(kn ** 2 + ke ** 2)
    # smooth over a couple of mm (the curvature from sampled points is noisy)
    k = max(1, int(round(1.0 / max(np.median(np.diff(s)), 1e-6))))
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    kap = np.convolve(np.pad(kap, k, mode="edge"), ker, "valid")
    ds = np.clip(np.sqrt(8.0 * tol_mm / np.maximum(kap, 1e-6)), min(0.8, ds_max), ds_max)
    dens = np.concatenate([[0.0], np.cumsum(0.5 * (1 / ds[1:] + 1 / ds[:-1]) * np.diff(s))])
    br = sorted(b for b in breaks if s[0] + 1e-6 < b < s[-1] - 1e-6)
    edges = [s[0]] + br + [s[-1]]
    out = [np.array([edges[0]])]
    for a, b in zip(edges[:-1], edges[1:]):
        da_, db_ = np.interp(a, s, dens), np.interp(b, s, dens)
        n = max(1, int(math.ceil(db_ - da_ - 1e-9)))
        seg = np.interp(np.linspace(da_, db_, n + 1), dens, s)
        seg[0], seg[-1] = a, b
        out.append(seg[1:])
    return np.concatenate(out)


def lod_faces(ball: Ball, st: Stretch, lod: int) -> FaceSet:
    L = LODS[lod]
    sw = st.sweep
    u0, u1 = sw.u_range
    us = adaptive_rings(sw, L.ds_mm, RING_TOL_MM[lod], st.breaks())
    lo_, hi_ = np.searchsorted(sw.s, [u0, u1])
    w_max = float(np.max(sw.w[max(lo_ - 1, 0):hi_ + 1])) if len(sw.w) else None
    tc0 = section_points(ball.prof, L, w_max)
    UU, T0 = np.meshgrid(us, tc0, indexing="ij")
    TC = ball.prof.from_nominal(T0, sw.width_at(UU))
    C, Tt, N, B, Ra, w, g, tw = sw.frame(UU.ravel())
    a, h, *_ = sw.shaped(TC.ravel(), w, g, tw)
    A = a.reshape(UU.shape)
    nr, npf = UU.shape
    k = np.arange(nr - 1)[:, None]
    j = np.arange(npf - 1)[None, :]
    i00 = (k * npf + j).ravel()
    faces = np.stack([i00, i00 + npf, i00 + npf + 1, i00 + 1], 1)
    Af = A.ravel()[faces]
    Uf = UU.ravel()[faces]
    u_lo, u_hi = Uf.min(1), Uf.max(1)
    a_lo, a_hi = Af.min(1), Af.max(1)
    sat = st.sat_keep0 if lod == 0 else st.sat_keep1
    keep = sat.any(u_lo, u_hi, a_lo, a_hi)
    faces = faces[keep]
    chunk = st.chunk_of(0.5 * (u_lo[keep] + u_hi[keep]))
    return FaceSet(us=us, tc=TC, faces=faces, chunk=chunk)


def plan_chunks(ball: Ball, st: Stretch, pad_mm: float, max_len_mm: float = 80.0) -> List[float]:
    """Cut a stretch into atlas chunks where its kept t-range changes: a 1-D dynamic
    program over LOD0's ring intervals minimising the padded block area
    sum (L + 2 pad)(H + 2 pad).  Sets and returns ``st.chunks``."""
    st.chunks = [st.u_range[0], st.u_range[1]]
    fs = lod_faces(ball, st, 0)
    us = fs.us
    n = len(us) - 1
    if n <= 0 or len(fs.faces) == 0:
        return st.chunks
    npf = fs.tc.shape[1]
    ring = fs.faces[:, 0] // npf
    tcf = fs.tc.ravel()[fs.faces]
    lo = np.full(n, np.inf)
    hi = np.full(n, -np.inf)
    np.minimum.at(lo, ring, tcf.min(1))
    np.maximum.at(hi, ring, tcf.max(1))
    best = np.full(n + 1, np.inf)
    arg = np.zeros(n + 1, np.int64)
    best[0] = 0.0
    for j in range(1, n + 1):
        mn, mx = np.inf, -np.inf
        for i in range(j - 1, -1, -1):
            mn = min(mn, lo[i])
            mx = max(mx, hi[i])
            L = us[j] - us[i]
            if L > max_len_mm:
                break
            H = (mx - mn) if np.isfinite(mn) else 0.0
            cost = best[i] + ((L + 2 * pad_mm) * (H + 2 * pad_mm) if np.isfinite(mn) else 0.0)
            if cost < best[j]:
                best[j] = cost
                arg[j] = i
    cuts = [n]
    while cuts[-1] > 0:
        cuts.append(int(arg[cuts[-1]]))
    cuts = cuts[::-1]
    st.chunks = [float(us[c]) for c in cuts]
    return st.chunks


def chunk_t_ranges(ball: Ball, st: Stretch, facesets: Sequence[FaceSet], pad_mm: float = 0.12):
    """Per chunk: [t_lo, t_hi] over every kept face corner at every LOD (None = unused)."""
    n = len(st.chunks) - 1
    lo = np.full(n, np.inf)
    hi = np.full(n, -np.inf)
    for fs in facesets:
        if len(fs.faces) == 0:
            continue
        tcf = fs.tc.ravel()[fs.faces]
        np.minimum.at(lo, fs.chunk, tcf.min(1))
        np.maximum.at(hi, fs.chunk, tcf.max(1))
    out = []
    for c in range(n):
        if not np.isfinite(lo[c]):
            out.append(None)
        else:
            out.append((float(lo[c] - pad_mm), float(hi[c] + pad_mm)))
    return out


@dataclass
class MeshPart:
    verts: np.ndarray       # (V, 3) mm
    faces: np.ndarray       # (F, 4)
    loop_ut: np.ndarray     # (F, 4, 2)
    normals: np.ndarray     # (V, 3)
    key: str
    dropped: int = 0

    @property
    def tris(self) -> int:
        f = self.faces
        return int(np.sum(np.where(f[:, 3] == f[:, 2], 1, 2)))


def collapse_short_edges(verts: np.ndarray, faces: np.ndarray, normals: np.ndarray, min_along_mm: float,
                         min_across_mm: float = 0.03):
    """Edge-collapse every ALONG-the-tape edge shorter than ``min_along_mm`` and every
    across edge shorter than ``min_across_mm`` (union-find clusters to their mean).  Only where
    the fold guard gathers an inner edge do consecutive rings' vertices come this close;
    collapsing them keeps the surface closed where dropping the sliver faces would leave
    pinholes.  Faces are (ring k, j), (k+1, j), (k+1, j+1), (k, j+1): edges 0-1 and 2-3 run
    along u.  Returns (verts, faces, normals, collapsed_vertex_count)."""
    ea = np.concatenate([faces[:, [0, 1]], faces[:, [2, 3]]], 0)
    ec = np.concatenate([faces[:, [1, 2]], faces[:, [3, 0]]], 0)
    La = np.linalg.norm(verts[ea[:, 0]] - verts[ea[:, 1]], axis=1)
    Lc = np.linalg.norm(verts[ec[:, 0]] - verts[ec[:, 1]], axis=1)
    short = np.concatenate([ea[(La < min_along_mm) & (ea[:, 0] != ea[:, 1])],
                            ec[(Lc < min_across_mm) & (ec[:, 0] != ec[:, 1])]], 0)
    if len(short) == 0:
        return verts, faces, normals, 0
    parent = np.arange(len(verts))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in short:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    root = np.array([find(i) for i in range(len(verts))])
    cnt = np.bincount(root, minlength=len(verts)).astype(np.float64)
    V = np.zeros_like(verts)
    Nn = np.zeros_like(normals)
    np.add.at(V, root, verts)
    np.add.at(Nn, root, normals)
    V = V / np.maximum(cnt, 1)[:, None]
    Nn = Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
    return V[root], root[faces], Nn[root], int((root != np.arange(len(verts))).sum())


def build_part(ball: Ball, st: Stretch, fs: FaceSet, lod: int) -> Optional[MeshPart]:
    if len(fs.faces) == 0:
        return None
    sw = st.sweep
    saved = sw.lift
    sw.lift = ball.lift_for_lod(st, lod)
    try:
        nr, npf = fs.tc.shape
        UU = np.repeat(fs.us[:, None], npf, 1)
        used = np.unique(fs.faces.ravel())
        P = np.zeros((nr * npf, 3))
        Nn = np.zeros((nr * npf, 3))
        Pu, Nu = sw.eval(UU.ravel()[used], fs.tc.ravel()[used])
        if lod in LOD_EDGE_NORMAL_INSET:
            # a coarse LOD's edge vertex (the cord's lower shoulder) carries the BODY's normal just
            # inside the groove: its own (tilted 45 deg outward and down) spread over half the
            # band in one triangle and drew a dark line along every edge - the visible pop at the
            # LOD1 -> LOD2 switch (round 1 measurer: mean |d| 0.019, local max 0.39)
            tcu = fs.tc.ravel()[used]
            wu = sw.width_at(UU.ravel()[used])
            grv = ball.prof.from_nominal(np.full_like(tcu, ball.prof.tb0), wu)
            edge = np.abs(tcu) > grv - 1e-6
            if np.any(edge):
                tcn = np.sign(tcu[edge]) * (grv[edge] * LOD_EDGE_NORMAL_INSET[lod])
                _p, Ne = sw.eval(UU.ravel()[used][edge], tcn)
                Nu = Nu.copy()
                Nu[edge] = Ne
        P[used], Nn[used] = Pu, Nu
    finally:
        sw.lift = saved
    faces = fs.faces
    ut = np.stack([UU.ravel(), fs.tc.ravel()], 1)
    loop_ut = ut[faces]
    first, remap, welds = T.weld_1nm(P[used])
    vmap = -np.ones(nr * npf, np.int64)
    vmap[used] = remap
    verts = P[used][first]
    normals = Nn[used][first]
    faces = vmap[faces]
    verts, faces, normals, collapsed = collapse_short_edges(verts, faces, normals, 0.12)
    # a quad whose corners weld: drop the repeat (becomes a triangle) or the face
    out_f, out_ut = [], []
    for f, lu in zip(faces, loop_ut):
        q = [int(f[0])]
        l2 = [lu[0]]
        for i in range(1, 4):
            if int(f[i]) != q[-1] and not (i == 3 and int(f[i]) == q[0]):
                q.append(int(f[i]))
                l2.append(lu[i])
        if len(q) == 4:
            out_f.append(q)
            out_ut.append(l2)
        elif len(q) == 3:
            out_f.append(q + [q[2]])
            out_ut.append(l2 + [l2[2]])
    if not out_f:
        return None
    faces = np.array(out_f, np.int64)
    loop_ut = np.array(out_ut, np.float64)
    a, b, c, dd = (verts[faces[:, i]] for i in range(4))
    ar1 = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    ar2 = np.where(faces[:, 3] == faces[:, 2], np.inf, 0.5 * np.linalg.norm(np.cross(c - a, dd - a), axis=1))
    ok = np.minimum(ar1, ar2) >= MIN_TRI_MM2
    dropped = int((~ok).sum())
    faces, loop_ut = faces[ok], loop_ut[ok]
    usedv = np.unique(faces.ravel())
    m2 = -np.ones(len(verts), np.int64)
    m2[usedv] = np.arange(len(usedv))
    mp = MeshPart(verts=verts[usedv], faces=m2[faces], loop_ut=loop_ut, normals=normals[usedv], key=st.key,
                  dropped=dropped)
    mp.collapsed = collapsed
    return mp


# =========================================================================== atlas
@dataclass
class ChunkBlock:
    key: str
    chunk: int
    u0: float
    u1: float
    t_lo: float
    t_hi: float
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    pad: int = 16

    @property
    def t_half(self) -> float:
        return max(abs(self.t_lo), abs(self.t_hi))


class ChunkAtlas(T.TapeAtlas):
    """smokebomb_tape.TapeAtlas with one block per CHUNK and an asymmetric t-range per block
    (the block holds rows t_lo .. t_hi, not -t_half .. t_half)."""

    def __init__(self, size: int, ppmm: float, pad: int, blocks: List[ChunkBlock]):
        super().__init__(size, ppmm, pad, blocks)

    @staticmethod
    def _shelf(reqs: Sequence[ChunkBlock], size: int, pad: int, ppmm: float):
        items = []
        for r in reqs:
            w = int(math.ceil((r.u1 - r.u0) * ppmm)) + 1
            h = int(math.ceil((r.t_hi - r.t_lo) * ppmm)) + 1
            items.append((h, w, r))
        items.sort(key=lambda z: (-z[0], -z[1]))
        out = []
        x = y = 0
        row_h = 0
        for h, w, r in items:
            W_ = w + 2 * pad
            H_ = h + 2 * pad
            if W_ > size or H_ > size:
                return None
            if x + W_ > size:
                y += row_h
                x = 0
                row_h = 0
            if y + H_ > size:
                return None
            b = ChunkBlock(r.key, r.chunk, r.u0, r.u1, r.t_lo, r.t_hi, x + pad, y + pad, w, h, pad)
            out.append(b)
            x += W_
            row_h = max(row_h, H_)
        return out

    @classmethod
    def pack_chunks(cls, reqs: Sequence[ChunkBlock], size: int, pad: int, max_ppmm: float = 60.0) -> "ChunkAtlas":
        lo, hi, best = 1.0, max_ppmm, None
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            b = cls._shelf(reqs, size, pad, mid)
            if b is None:
                hi = mid
            else:
                lo, best = mid, b
        if best is None:
            raise ValueError("chunk atlas: nothing fits")
        # the final density rounded down to 1e-4 px/mm (a stated, reproducible number)
        pp = math.floor(lo * 1e4) / 1e4
        best = cls._shelf(reqs, size, pad, pp)
        return cls(size, pp, pad, best)

    def block_of(self, key: str, u) -> np.ndarray:
        bl = self._by_key[key]
        starts = np.array([b.u0 for b in bl])
        return np.clip(np.searchsorted(starts, np.asarray(u), side="right") - 1, 0, len(bl) - 1)

    def px(self, key: str, u, tc, block_index=None):
        u = np.asarray(u, np.float64)
        tc = np.asarray(tc, np.float64)
        bi = self.block_of(key, u) if block_index is None else np.asarray(block_index)
        bl = self._by_key[key]
        x0 = np.array([b.x for b in bl], np.float64)[bi]
        y0 = np.array([b.y for b in bl], np.float64)[bi]
        u0 = np.array([b.u0 for b in bl])[bi]
        t0 = np.array([b.t_lo for b in bl])[bi]
        return x0 + (u - u0) * self.ppmm, y0 + (tc - t0) * self.ppmm

    def uv(self, key: str, u, tc, block_index=None):
        """Blender UV with V = the atlas row / size: t runs UP the image (the stored maps are
        the painted atlas flipped vertically), so every island keeps the surface's handedness
        (nothing mirrored)."""
        x, y = self.px(key, u, tc, block_index)
        return x / self.size, y / self.size

    def texel_grid(self, b: ChunkBlock):
        xs = np.arange(b.x - b.pad, b.x + b.w + b.pad) + 0.5
        ys = np.arange(b.y - b.pad, b.y + b.h + b.pad) + 0.5
        u = b.u0 + (xs - b.x) / self.ppmm
        tc = b.t_lo + (ys - b.y) / self.ppmm
        return xs, ys, u, tc

    def mesh_uv_part(self, part: MeshPart) -> np.ndarray:
        um = part.loop_ut[..., 0].mean(1)
        bi = self.block_of(part.key, um)
        U, V = self.uv(part.key, part.loop_ut[..., 0], part.loop_ut[..., 1], np.repeat(bi[:, None], 4, 1))
        return np.stack([U, V], -1)

    def to_json(self) -> Dict[str, object]:
        return {"size": self.size, "ppmm": round(self.ppmm, 4), "pad_px": self.pad,
                "fill": round(self.fill_fraction(), 4), "blocks": len(self.blocks)}


def uv_bounds_check(atlas: ChunkAtlas, part: MeshPart, uv: np.ndarray) -> Dict[str, float]:
    """How far any corner's texel lies outside its block's content rect (px; <= pad is safe)."""
    um = part.loop_ut[..., 0].mean(1)
    bi = atlas.block_of(part.key, um)
    bl = atlas._by_key[part.key]
    x = uv[..., 0] * atlas.size
    y = uv[..., 1] * atlas.size
    bx0 = np.array([b.x for b in bl])[bi][:, None]
    by0 = np.array([b.y for b in bl])[bi][:, None]
    bx1 = bx0 + np.array([b.w for b in bl])[bi][:, None]
    by1 = by0 + np.array([b.h for b in bl])[bi][:, None]
    over = np.maximum.reduce([bx0 - x, x - bx1, by0 - y, y - by1, np.zeros_like(x)])
    return {"max_outside_px": float(over.max()) if over.size else 0.0}


# =========================================================================== reference image <-> build
def img_to_xz(x, y, outline_mm: float):
    """reference image px -> build (X, Z) mm under the reference's orthographic framing."""
    cx, cy = W.REF_CENTRE_PX
    return ((np.asarray(x, np.float64) - cx) / W.REF_RADIUS_PX * outline_mm,
            -(np.asarray(y, np.float64) - cy) / W.REF_RADIUS_PX * outline_mm)


def build_to_img(P, outline_mm: float):
    P = np.asarray(P, np.float64)
    cx, cy = W.REF_CENTRE_PX
    return np.stack([cx + P[..., 0] / outline_mm * W.REF_RADIUS_PX, cy - P[..., 2] / outline_mm * W.REF_RADIUS_PX], -1)


def _exposed_top_points(ball: "Ball", st: "Stretch", step: int = 1):
    ii, jj = np.nonzero(st.exposed[::step, ::step])
    ii, jj = ii * step, jj * step
    u = st.u0 + ii * st.du
    a = st.a0 + jj * st.da
    w = st.sweep.width_at(u)
    C, Tt, N, B, Ra, ww, g, tw = st.sweep.frame(u)
    sg = np.maximum(1.0 - g * (1.0 - ball.prof.spec.rope_w_mm / np.maximum(w, 1e-6)), 1e-6)
    h = ball.prof.top_h(a / sg, w)
    return st.sweep.eval_ah(u, a, h), u, a


class FrontSurface:
    """The exposed top surface seen from the reference camera (build -Y): a dense cloud of
    exposed surface points with their stretch, u and a, for picking what lies under an
    image pixel (the loose threads' roots and tips)."""

    def __init__(self, ball: "Ball", step: int = 2):
        P, K, U, A = [], [], [], []
        for st in ball.stretches:
            if not st.exposed.any():
                continue
            Q, u, a = _exposed_top_points(ball, st, step)
            front = Q[:, 1] < 0
            P.append(Q[front])
            K.append(np.full(int(front.sum()), st.index))
            U.append(u[front])
            A.append(a[front])
        self.P = np.concatenate(P)
        self.k = np.concatenate(K)
        self.u = np.concatenate(U)
        self.a = np.concatenate(A)
        self.ball = ball

    def hit(self, x, y, pass_name: Optional[str] = None):
        X, Z = img_to_xz(x, y, self.ball.spec.outline_mm)
        d2 = (self.P[:, 0] - X) ** 2 + (self.P[:, 2] - Z) ** 2
        if pass_name is not None:
            ok = np.array([self.ball.stretches[i].pass_name == pass_name for i in self.k])
            d2 = np.where(ok, d2, np.inf)
        best = float(d2.min())
        near = d2 <= best + 0.08 ** 2
        i = int(np.argmin(np.where(near, self.P[:, 1], np.inf)))
        return self.P[i], self.ball.stretches[int(self.k[i])], float(self.u[i]), float(self.a[i]), math.sqrt(best)

    def top_at(self, x, y):
        """the front-most exposed point under an image pixel, any stretch."""
        return self.hit(x, y, None)


def thread_parts(ball: "Ball", presets: Dict[str, Dict[str, object]] = None, log: Callable = print):
    """REFERENCE_SPEC 6's loose threads T1 - T5 (smokebomb_tape.THREAD_PRESETS), rooted on
    the fitted winding: a hanging thread's root on the named pass's EDGE cord nearest the
    root pixel, its tip on the surface under the tip pixel; T3 lies on A; T4 is a single-ply
    hook standing past the outline.  Returns (parts, report)."""
    presets = T.THREAD_PRESETS if presets is None else presets
    fs = FrontSurface(ball)
    parts, rep = [], {}
    R0 = ball.spec.outline_mm
    for name, pr in presets.items():
        ts = pr["spec"]
        seed = int(pr["seed"])
        rx, ry = pr["root_px"]
        tx, ty = pr["tip_px"]
        info = {"root_px": [rx, ry], "tip_px": [tx, ty]}
        if pr.get("hangs_from") == "W lower edge":
            best = None
            for st in ball.stretches:
                if st.pass_name != "W":
                    continue
                sw = st.sweep
                us = np.linspace(sw.u_range[0], sw.u_range[1], max(50, int((sw.u_range[1] - sw.u_range[0]) / 0.05)))
                for sd in (-1, 1):
                    tc = sd * (ball.prof.t_edge(sw.width_at(us)) - 0.12)
                    P = sw.eval(us, tc, normals=False)
                    ij = build_to_img(P, R0)
                    d2 = (ij[:, 0] - rx) ** 2 + (ij[:, 1] - ry) ** 2
                    d2 = np.where(P[:, 1] < 0, d2, np.inf)
                    i = int(np.argmin(d2))
                    if best is None or d2[i] < best[0]:
                        best = (float(d2[i]), P[i], st.key, float(us[i]), sd)
            root = best[1]
            tip, st_t, _u, _a, dt = fs.hit(tx, ty, pr.get("onto"))
            rl = float(np.linalg.norm(tip)) + ts.ply_r_mm + ts.twist_r_mm
            pl = T.make_thread(root, tip, ts, seed=seed, r_low=rl, drop_len_mm=0.5)
            info.update(root_on=best[2], root_side=int(best[4]), root_px_error=round(math.sqrt(best[0]), 2),
                        tip_on=st_t.key, tip_px_error=round(dt / R0 * W.REF_RADIUS_PX, 2))
        elif pr.get("lies_on"):
            root, st_r, *_ = fs.hit(rx, ry, pr.get("onto"))
            tip, st_t, *_ = fs.hit(tx, ty, pr.get("onto"))
            lift = ts.ply_r_mm + ts.twist_r_mm
            rootl = root * (1.0 + lift / np.linalg.norm(root))
            rl = float(np.linalg.norm(tip)) + lift
            pl = T.make_thread(rootl, tip, ts, seed=seed, r_low=rl, drop_len_mm=0.05)
            info.update(root_on=st_r.key, tip_on=st_t.key)
        else:
            # T4: a hook on the OUTLINE: its root is the outline point at the root pixel's image
            # angle (the top surface's largest projected radius there), its tip past it
            ang = math.atan2(-(ry - W.REF_CENTRE_PX[1]), rx - W.REF_CENTRE_PX[0])
            allP = []
            for st in ball.stretches:
                if not st.exposed.any():
                    continue
                Q, _u, _a = _exposed_top_points(ball, st, 1)
                thq = np.arctan2(Q[:, 2], Q[:, 0])
                m = np.abs((thq - ang + np.pi) % (2 * np.pi) - np.pi) < math.radians(0.3)
                allP.append(Q[m])
            Q = np.concatenate(allP)
            rr = np.hypot(Q[:, 0], Q[:, 2])
            q = Q[int(np.argmax(rr))]
            root = q * (1.0 - 0.05 / float(np.linalg.norm(q)))
            dx, dz = (tx - rx) / W.REF_RADIUS_PX * R0, -(ty - ry) / W.REF_RADIUS_PX * R0
            tip = root + np.array([dx, 0.0, dz])
            pl = T.make_thread(root, tip, ts, seed=seed, r_low=float(np.linalg.norm(tip)), drop_len_mm=0.2)
            info.update(root_outline_radius_mm=round(float(rr.max()), 4), reach_mm=round(math.hypot(dx, dz), 3))
        tris = 0
        for V, F, UT, NN in pl:
            parts.append((V, F, UT, NN))
            tris += int(np.sum(np.where(F[:, 3] == F[:, 2], 1, 2)))
        info.update(plies=len(pl), triangles=tris,
                    min_tri_mm2=round(min(T.min_tri_area_mm2(p[0], p[1]) for p in pl), 5),
                    root_mm=[round(float(v), 3) for v in root], tip_mm=[round(float(v), 3) for v in tip])
        rep[name] = info
        log(f"  thread {name}: {info}")
    return parts, rep


def _w_edge_root(ball: "Ball", rx: float, ry: float, inset_mm: float = 0.12):
    """The point on W's cord (either edge, front side) nearest image px (rx, ry)."""
    R0 = ball.spec.outline_mm
    best = None
    for st in ball.stretches:
        if st.pass_name != "W":
            continue
        sw = st.sweep
        us = np.linspace(sw.u_range[0], sw.u_range[1], max(50, int((sw.u_range[1] - sw.u_range[0]) / 0.05)))
        for sd in (-1, 1):
            tc = sd * (ball.prof.t_edge(sw.width_at(us)) - inset_mm)
            P = sw.eval(us, tc, normals=False)
            ij = build_to_img(P, R0)
            d2 = (ij[:, 0] - rx) ** 2 + (ij[:, 1] - ry) ** 2
            d2 = np.where(P[:, 1] < 0, d2, np.inf)
            i = int(np.argmin(d2))
            if best is None or d2[i] < best[0]:
                best = (float(d2[i]), P[i], st.key, float(us[i]), sd)
    return best


def thread_parts2(ball: "Ball", presets: Dict[str, Dict[str, object]] = None, log: Callable = print):
    """REFERENCE_SPEC 6's loose threads T1 - T5, round 2 (props_lib.smokebomb_threads): curly,
    lifted, forked plies hung from W's lower edge (T1, T2), a curl lying on A (T3), a small
    curled loop on the outline (T4) and a short cluster of stubs on W's edge (T5).  Returns
    (parts, report, tones): ``tones`` names each part's texture ('light' / 'cloth')."""
    from . import smokebomb_threads as TH
    presets = TH.THREAD_PRESETS2 if presets is None else presets
    fs = FrontSurface(ball)
    parts, rep, tones = [], {}, []
    R0 = ball.spec.outline_mm
    c0 = np.zeros(3)
    for name, pr in presets.items():
        ts = pr["spec"]
        seed = int(pr["seed"])
        rx, ry = pr["root_px"]
        tx, ty = pr["tip_px"]
        info = {"root_px": [rx, ry], "tip_px": [tx, ty], "kind": pr["kind"]}
        if pr["kind"] in ("hang", "stubs"):
            best = _w_edge_root(ball, rx, ry)
            root = best[1]
            tip, st_t, _u, _a, dt = fs.hit(tx, ty, pr.get("onto"))
            rl = float(np.linalg.norm(tip)) + ts.ply_r_mm + ts.twist_r_mm
            if pr["kind"] == "hang":
                pl = TH.make_hanging(root, tip, ts, seed, c0, rl)
            else:
                pl = TH.make_stubs(root, tip, ts, seed, c0, rl, count=int(pr.get("count", 3)),
                                   spread_mm=float(pr.get("spread_mm", 0.95)))
            info.update(root_on=best[2], root_side=int(best[4]), root_px_error=round(math.sqrt(best[0]), 2),
                        tip_on=st_t.key, tip_px_error=round(dt / R0 * W.REF_RADIUS_PX, 2))
        elif pr["kind"] == "lie":
            root, st_r, *_ = fs.hit(rx, ry, pr.get("onto"))
            tip, st_t, *_ = fs.hit(tx, ty, pr.get("onto"))
            lift = ts.ply_r_mm + ts.twist_r_mm
            rootl = root * (1.0 + lift / np.linalg.norm(root))
            rl = float(np.linalg.norm(tip)) + lift
            pl = TH.make_hanging(rootl, tip, ts, seed, c0, rl, drop_len_mm=0.05)
            info.update(root_on=st_r.key, tip_on=st_t.key)
        else:
            # T4: a curled loop on the OUTLINE at the root pixel's image angle
            ang = math.atan2(-(ry - W.REF_CENTRE_PX[1]), rx - W.REF_CENTRE_PX[0])
            allP = []
            for st in ball.stretches:
                if not st.exposed.any():
                    continue
                Q, _u, _a = _exposed_top_points(ball, st, 1)
                thq = np.arctan2(Q[:, 2], Q[:, 0])
                m = np.abs((thq - ang + np.pi) % (2 * np.pi) - np.pi) < math.radians(0.3)
                allP.append(Q[m])
            Q = np.concatenate(allP)
            rr = np.hypot(Q[:, 0], Q[:, 2])
            q = Q[int(np.argmax(rr))]
            root = q * (1.0 - 0.06 / float(np.linalg.norm(q)))
            out = np.array([math.cos(ang), 0.0, math.sin(ang)])
            reach = math.hypot(tx - rx, ty - ry) / W.REF_RADIUS_PX * R0
            pl = TH.make_hook(root, out, ts, seed, c0, reach_mm=0.62, loop_r_mm=0.30, turn=1.15 * math.pi)
            info.update(root_outline_radius_mm=round(float(rr.max()), 4), reach_mm=round(reach, 3))
        tris = 0
        for V, F, UT, NN in pl:
            parts.append((V, F, UT, NN))
            tones.append(ts.tone)
            tris += int(np.sum(np.where(F[:, 3] == F[:, 2], 1, 2)))
        info.update(plies=len(pl), triangles=tris,
                    min_tri_mm2=round(min(T.min_tri_area_mm2(p[0], p[1]) for p in pl), 5))
        rep[name] = info
        log(f"  thread {name}: {info}")
    return parts, rep, tones


# =========================================================================== crevices
def crevices(ball: "Ball", atlas: "ChunkAtlas", sit_tol_mm: float = 0.35, log: Callable = print):
    """Every stretch's edges, and where each rests on another stretch: the crevice fields
    (smokebomb_tape.crevice_seeds / crevice_fields) in the atlas."""
    edges = T.merge_edges([T.edge_samples(st.sweep, key=st.key) for st in ball.stretches])
    seeds = []
    for st in ball.stretches:
        if st.key not in atlas._by_key:
            continue
        sd = T.crevice_seeds(atlas, st.sweep, st.key, edges, sit_tol_mm=sit_tol_mm)
        if len(sd.x):
            seeds.append(sd)
    allseeds = T.merge_seeds(seeds)
    log(f"  crevice seeds: {len(allseeds.x)} from {len(edges.u)} edge samples")
    return T.crevice_fields(atlas, allseeds), {"edge_samples": int(len(edges.u)), "seeds": int(len(allseeds.x)),
                                                "sit_tol_mm": sit_tol_mm}


# =========================================================================== maps
def _box2(a):
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def finish_maps(ch: Dict[str, np.ndarray], cloth: T.ClothSpec, ppmm: float, shading: T.Shading = T.SHADING,
                small: int = 2048, geometric_ao_small: Optional[np.ndarray] = None,
                ref_percentile: float = 99.97) -> Dict[str, object]:
    """The shipped maps from the float atlases (smokebomb_tape.finish_maps, at two sizes):

    DETAIL  full size, greyscale LINEAR, FULL RANGE: albedo / L_ref from the float albedo,
            quantised once (L_ref = the albedo at ``ref_percentile`` of the written texels)
    BC      full size, sRGB 8-bit of (Detail8 / 255) x Tint: BaseColor = Detail x Tint is BC
    ORM     ``small``: R = the analytic crevice / groove AO x the Cycles AO bake, G roughness,
            B metallic 0 (box-filtered from the full-size float fields)
    N       ``small``: DirectX, from the box-filtered micro height at ppmm x small / size
    Texels outside every block (and its padding) take the median cloth so no mip ever pulls a
    foreign colour into a block."""
    alb = ch["alb"].copy()
    wr = ch["written"]
    med = float(np.median(alb[wr]))
    alb[~wr] = med
    if getattr(cloth, "detail_units", False):
        # round 3: the cloth is painted in DETAIL units (0..1, full range by design) times its
        # gain, so Detail stores exactly the designed value and the Tint's luminance is the gain
        L_ref = float(cloth.gain * cloth.alb_max)
    else:
        L_ref = float(np.percentile(ch["alb"][wr], ref_percentile))
    D = np.clip(alb / max(L_ref, 1e-9), 0.0, 1.0)
    # round 3: Detail may be stored gamma-p (shading.detail_power): Detail = D ^ (1/p), so a dark
    # weave with a bright tail still fills the 0..1 range; BaseColor = Detail ^ p x Tint
    dp = float(getattr(shading, "detail_power", 1.0))
    srgb_detail = getattr(shading, "detail_encoding", "power") == "srgb"
    if srgb_detail:
        # final pass: Detail = sRGB-encode(d), imported sRGB ON: Unreal decodes before filtering
        # and mips (the gamma-2 Detail's mips ran 8-29 % dark); BaseColor = Detail x Tint
        dp = 1.0
        D8 = np.rint(T.srgb_encode(D) * 255.0).astype(np.uint8)
    else:
        D8 = np.rint((D ** (1.0 / dp) if dp != 1.0 else D) * 255.0).astype(np.uint8)
    chroma = np.asarray(cloth.chroma, np.float64)
    tint = L_ref * chroma / float(chroma @ T.LUMA)
    dq = D8.astype(np.float64) / 255.0
    if srgb_detail:
        dq = T.srgb_decode(dq)
    bc_lin = (dq ** dp if dp != 1.0 else dq)[..., None] * tint[None, None, :]
    BC8 = np.rint(T.srgb_encode(bc_lin) * 255.0).astype(np.uint8)
    size = alb.shape[0]
    f = max(1, size // small)
    ao = ch["ao"].copy()
    ao[~wr] = 1.0
    rough = ch["rough"].copy()
    rough[~wr] = float(np.median(ch["rough"][wr]))
    hgt = ch["hgt"].copy()
    hgt[~wr] = 0.0
    smp = float(getattr(shading, "spec_mask_power", 0.0))
    # final pass: the specular MASK from the float detail (the final quantity, so the box filter
    # and every Unreal mip average what the material uses)
    spm = np.clip(D, 0.0, 1.0) ** smp if smp > 0 else None
    for _ in range(int(round(math.log2(f)))):
        ao, rough, hgt = _box2(ao), _box2(rough), _box2(hgt)
        if spm is not None:
            spm = _box2(spm)
    if geometric_ao_small is not None:
        ao = ao * geometric_ao_small
    chans = [ao, rough, np.full_like(ao, shading.metallic)] + ([spm] if spm is not None else [])
    orm = np.stack(chans, -1)
    ORM8 = np.rint(np.clip(orm, 0, 1) * 255.0).astype(np.uint8)
    n = T.height_to_normal_dx(hgt, ppmm / f, shading.normal_strength)
    N8 = np.rint((n * 0.5 + 0.5) * 255.0).astype(np.uint8)
    bc_dec = T.srgb_decode(BC8.astype(np.float64) / 255.0)
    err_lin = np.abs(bc_dec - bc_lin)[wr]
    q_err = np.abs((dq ** dp if dp != 1.0 else dq) * L_ref - np.minimum(ch["alb"], L_ref))[wr]
    spec_rep = None
    if spm is not None:
        a8 = ORM8[..., 3].astype(np.float64) / 255.0
        spec_rep = {"channel": "ORM.A", "mask": "saturate(d)^%.3g, box-filtered from the float detail" % smp,
                    "specular": "%.3g x ORM.A" % float(shading.specular),
                    "mean_float": float(spm.mean()), "mean_8bit": float(a8.mean()),
                    "levels_used": int(len(np.unique(ORM8[..., 3])))}
    return {"BC": BC8, "ORM": ORM8, "N": N8, "DETAIL": D8, "tint_linear": tint.tolist(),
            "tint_srgb": T.srgb_encode(tint).tolist(), "L_ref": L_ref,
            "sizes": {"BC": size, "DETAIL": size, "ORM": size // f, "N": size // f},
            "specular_mask": spec_rep,
            "recolour": {"bc_is_detail_x_tint": ("BC8 = sRGB8(sRGBdecode(Detail8 / 255) x Tint), built from the quantised "
                                                 "Detail (Detail stored sRGB-encoded, imported sRGB ON)" if srgb_detail else
                                                 "BC8 = sRGB8(Detail8 / 255 x Tint), built from the quantised Detail"
                                                 if dp == 1.0 else
                                                 "BC8 = sRGB8((Detail8 / 255) ^ %.3g x Tint), built from the quantised "
                                                 "Detail (Detail stored gamma-%.3g)" % (dp, dp)),
                         "detail_power": dp, "detail_encoding": "srgb" if srgb_detail else "power",
                         "max_abs_err_linear_after_srgb8": float(err_lin.max()) if err_lin.size else 0.0,
                         "detail_levels_used": int(len(np.unique(D8[wr]))),
                         "detail_clipped_share": float(np.mean(ch["alb"][wr] > L_ref)),
                         "detail_percentiles_of_255": {str(pq): float(np.percentile(D8[wr], pq))
                                                       for pq in (1, 10, 25, 50, 75, 90, 99, 99.9)},
                         "detail_quant_err_lin_p99": float(np.percentile(q_err, 99)) if q_err.size else 0.0},
            "albedo_stats": {"mean": float(ch["alb"][wr].mean()), "p10": float(np.percentile(ch["alb"][wr], 10)),
                             "p50": float(np.percentile(ch["alb"][wr], 50)),
                             "p90": float(np.percentile(ch["alb"][wr], 90)),
                             "max": float(ch["alb"][wr].max()), "median_fill_outside_blocks": med}}


def write_maps(maps: Dict[str, object], folder, prefix: str = "T_SmokeBomb") -> Dict[str, str]:
    from pathlib import Path
    folder = Path(folder)
    out = {}
    for k, suf in (("BC", "BC"), ("ORM", "ORM"), ("N", "N"), ("DETAIL", "Detail")):
        out[k] = T.write_png(folder / ("%s_%s.png" % (prefix, suf)), maps[k])
    return out



__all__ = ["BallSpec", "BALL", "LODS", "MIN_TRI_MM2", "section_points", "DrapeField", "stack_counts",
           "exposure_along", "exposed_runs", "SAT", "Stretch", "Ball", "FaceSet", "lod_faces", "chunk_t_ranges",
           "MeshPart", "build_part", "ChunkBlock", "ChunkAtlas", "uv_bounds_check", "plan_chunks",
           "adaptive_rings", "img_to_xz", "build_to_img", "FrontSurface", "thread_parts", "thread_parts2", "crevices",
           "finish_maps", "write_maps"]
