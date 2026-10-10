"""SM_Casing_762x39: the spent 7.62x39 steel case, as numbers (plain Python, no bpy).

Source of every case dimension: C.I.P. TAB. I "7,62 x 39" (1989-01-04, revision 2002-05-15), CARTRIDGE MAXI column
(the copy read on 2026-10-09: tiropratico.com/CIP/Commission Internationale Permanente/762x39.pdf). Values in mm.

    L1 30.50 base to P2      L2 33.00 base to H1      L3 38.70 case length
    R  1.50  base to the groove floor (rim thickness at the groove)
    R1 11.35 rim diameter    E  3.20 base to P1       E1 9.56 extractor groove diameter
    e  1.00  groove floor width (min)                f  0.25 base edge chamfer (45 deg)
    beta 45 deg rim front cone                       delta 51deg58'12" groove front flank (to the axis)
    P1 11.35 body at E       P2 10.07 body at L1 (shoulder start)
    H1 8.60  neck at L2      H2 8.60 mouth at L3     alpha 32deg46' shoulder (included angle)
    r1 min 4.00 / r2 3.00 body-shoulder / shoulder-neck fillets (shaded, not modelled: section "Normals")

The groove numbers close exactly: rim front 45 deg over the groove depth (11.35 - 9.56) / 2 = 0.895 starts at
1.50 - 0.895 = 0.605; the floor runs 1.50 -> 2.50 (e = 1.00); the front flank rises 0.895 over 3.20 - 2.50 = 0.70,
atan(0.895 / 0.70) = 51.97 deg = delta. The shoulder: atan(0.735 / 2.50) x 2 = 32.77 deg = alpha.

Not on the C.I.P. sheet (sources: common 7.62x39 practice, stated as such in the README):
    neck inner = projectile G1 7.92 (wall 0.34 at the mouth); Berdan primer 5.50 mm; struck dimple 1.6 mm wide, 0.30 deep.

Spent case: kept at the C.I.P. cartridge numbers (a fired steel case springs back to within ~0.05-0.1 mm of them;
the chamber minimums are P1 11.36 / P2 10.12 / H1 8.74). No headstamp, no markings (gun study 6.2).

Frame: the case axis is Blender +X (= Unreal +X), base at -X, mouth at +X; the origin is the centre of mass of the
real hollow case (mass_properties), so a Niagara mesh particle tumbles about the right point. Sockets: Base (head
centre) and Mouth (mouth centre), both with X along the case axis toward the mouth.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

CIP = {
    "L1": 30.50, "L2": 33.00, "L3": 38.70, "R": 1.50, "R1": 11.35, "E": 3.20, "E1": 9.56, "e": 1.00,
    "f": 0.25, "beta_deg": 45.0, "delta_deg": 51.0 + 58.0 / 60.0 + 12.0 / 3600.0, "P1": 11.35, "P2": 10.07,
    "H1": 8.60, "H2": 8.60, "alpha_deg": 32.0 + 46.0 / 60.0, "r1_min": 4.00, "r2": 3.00,
}
EXTRA = {"neck_inner_d": 7.92, "primer_d": 5.50, "dimple_d": 1.60, "dimple_depth": 0.30, "seam_w": 0.10,
         "sealant_w": 0.30}
STEEL_DENSITY_G_CM3 = 7.85
PRIMER_POCKET_DEPTH = 2.9

_rr = CIP["R1"] / 2.0                     # 5.675 rim / P1 radius
_rg = CIP["E1"] / 2.0                     # 4.78 groove floor radius
_depth = _rr - _rg                        # 0.895
_rim_band_top = CIP["R"] - _depth / math.tan(math.radians(CIP["beta_deg"]))   # 0.605: the 45 deg rim front cone
_r_p2 = CIP["P2"] / 2.0
_r_h = CIP["H1"] / 2.0
_r_in = EXTRA["neck_inner_d"] / 2.0

# Normal modes per profile vertex: (mode for the band BEFORE it, mode for the band AFTER it); "own" = that band's own
# face normal (a hard edge), "avg" = the average of both bands (soft). ("own", "avg") on the body-shoulder vertex keeps
# the long body band flat-shaded and lets the shoulder band shade as the r1 / r2 fillets do.
SHARP = ("own", "own")
SMOOTH = ("avg", "avg")


def _p(r, z, v_weight_next, mode=SHARP, tag=""):
    return {"r": float(r), "z": float(z), "w": float(v_weight_next), "mode": mode, "tag": tag}


def profile_lod0() -> List[Dict]:
    """Outer profile base -> mouth, then the inner bore as a cone (the inside is soot-black; looking into a 7.9 mm
    mouth shows a dark hole either way). ``w`` = UV weight of the segment that STARTS at this vertex."""
    return [
        _p(0.0, EXTRA["dimple_depth"], 2.0, SMOOTH, "dimple_centre"),     # pole (inside the base: +z)
        _p(EXTRA["dimple_d"] / 2.0, 0.0, 2.0, SHARP, "dimple_rim"),
        _p(_rr - CIP["f"], 0.0, 3.0, SHARP, "base_chamfer_in"),
        _p(_rr, CIP["f"], 3.0, SHARP, "rim_low"),
        _p(_rr, _rim_band_top, 3.0, SHARP, "rim_high"),
        _p(_rg, CIP["R"], 2.0, SHARP, "groove_floor_start"),
        _p(_rg, CIP["R"] + CIP["e"], 2.0, SHARP, "groove_floor_end"),
        _p(_rr, CIP["E"], 1.0, SHARP, "P1"),
        _p(_r_p2, CIP["L1"], 1.5, ("own", "avg"), "P2"),
        _p(_r_h, CIP["L2"], 1.5, ("avg", "own"), "H1"),
        _p(_r_h, CIP["L3"], 3.0, SHARP, "H2_outer"),
        _p(_r_in, CIP["L3"], 0.2, SHARP, "mouth_inner"),
        _p(0.0, 9.0, 0.0, SMOOTH, "bore_apex"),                            # pole
    ]


def profile_lod1() -> List[Dict]:
    """8 segments: no base chamfer, no dimple, the groove as a V (rim front cone + front flank), mouth capped by a
    shallow dark cone."""
    return [
        _p(0.0, 0.0, 0.0, SMOOTH, "base_centre"),
        _p(_rr, 0.0, 0.0, SHARP, "rim_low"),
        _p(_rr, _rim_band_top, 0.0, SHARP, "rim_high"),
        _p(_rg, CIP["R"] + CIP["e"] / 2.0, 0.0, SHARP, "groove"),
        _p(_rr, CIP["E"], 0.0, SHARP, "P1"),
        _p(_r_p2, CIP["L1"], 0.0, ("own", "avg"), "P2"),
        _p(_r_h, CIP["L2"], 0.0, ("avg", "own"), "H1"),
        _p(_r_h, CIP["L3"], 0.0, SHARP, "H2_outer"),
        _p(0.0, CIP["L3"] - 1.5, 0.0, SMOOTH, "mouth_cap"),
    ]


def profile_lod2() -> List[Dict]:
    """6 segments: base, one tapered body, shoulder, neck, dark mouth cone."""
    return [
        _p(0.0, 0.0, 0.0, SMOOTH, "base_centre"),
        _p(_rr, 0.0, 0.0, SHARP, "rim_low"),
        _p(_r_p2, CIP["L1"], 0.0, ("own", "avg"), "P2"),
        _p(_r_h, CIP["L2"], 0.0, ("avg", "own"), "H1"),
        _p(_r_h, CIP["L3"], 0.0, SHARP, "H2_outer"),
        _p(0.0, CIP["L3"] - 1.5, 0.0, SMOOTH, "mouth_cap"),
    ]


LODS = [("LOD0", profile_lod0, 24), ("LOD1", profile_lod1, 8), ("LOD2", profile_lod2, 6)]
TRI_BUDGET = {"LOD0": 540, "LOD1": 130, "LOD2": 50}   # plan 4.2: ~400 / ~120 / ~40 at 24 segments (see README)


def seg_len(a, b) -> float:
    return math.hypot(b["r"] - a["r"], b["z"] - a["z"])


def lod0_v() -> List[float]:
    """V coordinate of each LOD0 profile vertex (weighted arc length, padded 0.004 .. 0.996)."""
    prof = profile_lod0()
    acc = [0.0]
    for a, b in zip(prof, prof[1:]):
        acc.append(acc[-1] + seg_len(a, b) * a["w"])
    tot = acc[-1]
    return [0.004 + 0.992 * x / tot for x in acc]


def v_of_point(r: float, z: float, tag: str = "") -> float:
    """V for a point of any LOD: the LOD0 V of the nearest point on the LOD0 profile (outer part only for outer
    points); the dark mouth caps map into the bore."""
    prof = profile_lod0()
    vs = lod0_v()
    if tag == "mouth_cap":
        return vs[11] + 0.3 * (vs[12] - vs[11])
    if tag == "base_centre":
        return vs[0]
    best = (1e9, 0.0)
    for i in range(0, 10):          # outer segments only (0..10)
        a, b = prof[i], prof[i + 1]
        dx, dz = b["r"] - a["r"], b["z"] - a["z"]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((r - a["r"]) * dx + (z - a["z"]) * dz) / L2))
        pr, pz = a["r"] + t * dx, a["z"] + t * dz
        d = math.hypot(r - pr, z - pz)
        if d < best[0]:
            best = (d, vs[i] + t * (vs[i + 1] - vs[i]))
    return best[1]


def row_lookup(v: float) -> Tuple[int, float, float, float]:
    """For a V in the LOD0 layout: (segment index, t, r, z)."""
    prof = profile_lod0()
    vs = lod0_v()
    for i in range(len(prof) - 1):
        if v <= vs[i + 1] or i == len(prof) - 2:
            t = 0.0 if vs[i + 1] == vs[i] else (v - vs[i]) / (vs[i + 1] - vs[i])
            t = max(0.0, min(1.0, t))
            a, b = prof[i], prof[i + 1]
            return i, t, a["r"] + t * (b["r"] - a["r"]), a["z"] + t * (b["z"] - a["z"])
    raise ValueError(v)


def outer_r(z: float) -> float:
    """Outer radius of the real case at height z (outer LOD0 profile, z >= 0, ignoring the dimple)."""
    prof = profile_lod0()[2:11]
    if z <= prof[0]["z"]:
        return prof[0]["r"]
    for a, b in zip(prof, prof[1:]):
        if a["z"] <= z <= b["z"] and b["z"] > a["z"]:
            return a["r"] + (z - a["z"]) / (b["z"] - a["z"]) * (b["r"] - a["r"])
    return prof[-1]["r"]


def real_inner_r(z: float) -> float:
    """Inner radius of the REAL hollow case (mass properties only; the mesh bore is a dark cone). Solid head to
    z = 4.6 (web); body wall 0.70 -> 0.40 over the body, 0.37 in the shoulder, 0.34 in the neck (typical sectioned
    steel 7.62x39 cases). The Berdan primer pocket is handled in mass_properties."""
    if z < 4.6:
        return 0.0
    if z <= CIP["L1"]:
        wall = 0.70 + (0.40 - 0.70) * (z - 4.6) / (CIP["L1"] - 4.6)
    elif z <= CIP["L2"]:
        wall = 0.37
    else:
        wall = 0.34
    return max(0.0, outer_r(z) - wall)


def mass_properties(steps: int = 4000) -> Dict[str, float]:
    """Volume (mm^3), mass (g, steel 7.85) and the centre of mass on the axis (mm from the base) of the real case."""
    L = CIP["L3"]
    vol = 0.0
    mom = 0.0
    for k in range(steps):
        z0 = L * k / steps
        z1 = L * (k + 1) / steps
        zm = 0.5 * (z0 + z1)
        a = math.pi * (outer_r(zm) ** 2 - real_inner_r(zm) ** 2)
        if zm < PRIMER_POCKET_DEPTH:    # Berdan pocket 5.50 x 2.9 deep; the cup + anvil fill about a quarter of it
            a -= math.pi * (EXTRA["primer_d"] / 2.0) ** 2 * 0.75
        dv = a * (z1 - z0)
        vol += dv
        mom += dv * zm
    return {"volume_mm3": vol, "mass_g": vol * 1e-3 * STEEL_DENSITY_G_CM3, "com_z_mm": mom / vol}
