"""Outline-plate spec: pure data, no bpy (library 3.9, the hooked cross, SM_Shuriken_HookedCross).

The pack's fourth generator family.  A radial star is arms off a round hub, the senban a square with
concave sides, the spike a bar; the hooked cross is a C4 plate whose outline is a chain of straight
edges and circular arcs with concave fillets and sharp convex corners, NO centre hole, and a knife
grind on some edges only.  This module turns the build-to numbers into that analytic contour (metres),
samples it into COLUMNS for a LOD, and derives everything the generator (``outline_plate``) needs:
the knife / chamfer profile at every column, the ridge where the two knife grinds of a point meet,
the grind run-outs, the plate-edge polygon and the exact plan area.  Pure Python: the verification
scripts import it without Blender.

Frame (study 4 pivot rule + study 2.6 handedness): Blender top view, +Z toward the viewer, X right,
Y up.  Arm 0 lies along +X (u = x); v = y is the side its hook turns to.  The presented face is +Z and
reads as the LEFT-FACING hooked cross: the arm along +X hooks toward +Y, the arm along +Y hooks toward
-X (every arm's hook tip lies ``tip_offset_deg`` COUNTER-clockwise of its arm axis).  The outline is
C4 by construction (one wedge, -45..+45 deg, authored per exact quarter turn) and has NO mirror
symmetry; nothing here can produce the mirrored form: ``HookedCrossSpec.validate`` refuses a
non-positive tip offset, and the generator never mirrors a coordinate.

The contour of one wedge (the photo-matched swept-blade outline, WorkFiles/shuriken/photo_study/
PHOTO_MEASUREMENT.md section 2.5), CCW around the material, from the -45 deg seam to the +45 deg seam:

    jin     lower half-junction fillet, concave, r_f, symmetric about the -45 deg diagonal (the seam point is
            its midpoint): arm 3's leading edge meets arm 0's trailing edge at J = (q_J, -q_J), q_J = hw0/(1+T)
    trail   arm 0's trailing edge  v = -(hw0 - T u), T = tan(taper per edge), out to the ELBOW
    arc     the back arc: ONE convex circle of radius R through (u_axis, 0) and the tip, centre on the far side;
            from the elbow (where it meets the trailing edge; a sharp convex corner) across the arm end
            (the axis crossing at u_axis) and up the hook's back to the TIP
    inner   the hook's inner edge, a straight line from the tip back to the hook corner HK = (u_hook, hw0 - T u_hook)
    hk      the hook-corner fillet, concave, r_f
    lead    arm 0's leading edge v = +(hw0 - T u), back in to the junction with arm 1
    jout    upper half-junction fillet, the quarter turn of jin's other half: ends ON the +45 deg diagonal

Edges.  The hook BLADE cuts: the back arc from the tip down to the blade root and the inner edge from the
tip down to the hook-corner fillet carry the pack's knife grind (spec.ChamferProfile.knife: 35 deg per side
to a 0.15 mm land; past the apex the two grinds meet in a RIDGE and the tip ends in a vertical edge the
height of the land).  Each knife runs out over ``runout_mm`` into the small chamfer: on the back arc it has
faded out exactly at the SHOULDER (where the arm's leading-edge line meets the arc, i.e. where the blade meets
the arm), on the inner edge exactly at the hook-corner fillet (a wheel cannot grind into a concave corner - the
stars' root run-out).  Every other edge (the arm edges, the arm end on the arc, the fillets) is not a cutting
edge and keeps the small chamfer plus wall at the grind angle, like the stars' hub scallops.  The width varies
linearly with contour length through a run-out and the depth follows at the grind angle, so a run-out facet on
a straight edge is exactly planar (3.9.1: ``OutlineLodSpec.runout_ease`` makes the width a smoothstep of the contour
length over several intervals; each interval's facet is still planar, since every column keeps d = w tan(angle)).

Columns.  A column is one cross-section of the edge band: the outline point P, the inward normal n, the facet's
plan width w and depth d (wall top at z = +-(t/2 - d)), and the plate-edge point E = P + w n (z = +-t/2).  At
the elbow two columns share P and E (E = the MITRE of the two insets).  Between the apex and the tip the plate
has run out: those ROOF columns carry the ridge point X(s) instead of E - the point at plan distance s from both
the inner edge and the arc, z = t/2 - d + s tan(angle) - and each ridge point is the plate edge of one column on
each edge (its feet), so the two grinds share the ridge by index.

Exactness.  Seam points are built from ONE float q as (q, -q) / (q, q), so the generator's quarter-turn keys
weld them; J, the fillets' centres and the tangent points are closed-form.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

from .spec import (EDGE_LAND_MM, GRIND_ANGLE_DEG, GRIND_RUNOUT_MM, LOD_SCREEN_SIZES, MAX_EDGE_LAND_MM, MM,
                   SCALLOP_CHAMFER_MM, ChamferProfile)

SQRT_HALF = math.sqrt(0.5)
OUTLINE_LOD_CEILING = 2500           # study 4's LOD0 ceiling; LOD1 900, LOD2 250 (ceilings only: nothing padded)
PIECES = ("jin", "trail", "arc", "inner", "hk", "lead", "jout")


# =========================================================================== LOD counts


@dataclass(frozen=True)
class OutlineLodSpec:
    """Column counts for one hooked-cross LOD (per wedge = one arm).

    ``arm_intervals``       stations along the two straight arm edges from the junction fillets' tangent
                            points to the hook-corner fillet's tangent point on the leading edge (the SAME u
                            stations on both edges, so the arm plate is a strip of facing columns)
    ``end_intervals``       the trailing edge beyond that station, out to the elbow
    ``arm_end_intervals``   the back arc from the elbow to the grind's run-out (the non-cutting arm end)
    ``runout_intervals``    each knife run-out (back arc, inner edge)
    ``runout_ease``         3.9.1: the run-out's width follows a smoothstep of the contour length instead of a straight
                            line (with more than one interval the facet then leaves the knife and meets the chamfer
                            tangentially instead of as one tilted plunge facet); every interval's quad stays planar on
                            a straight edge because each column keeps d = w tan(angle)
    ``hook_intervals``      the blade: run-out -> apex foot, on the back arc and on the inner edge (matched, so
                            the hook plate is a strip of facing columns too)
    ``roof_intervals``      ridge intervals from the apex to the tip (0: the LOD has no roof stations - a
                            single facet from the apex straight to the tip)
    ``junction_fillet_segments``  chords per HALF junction fillet; 0 = a sharp concave corner (LOD2)
    ``hook_fillet_segments``      chords of the hook-corner fillet; 0 = sharp
    ``chamfer``             the non-cutting edges carry the small chamfer (False: square edges, full wall; LOD2)
    ``knife_land``          False: the knife facets meet in an edge line (land 0; no wall on the blade; LOD2)
    ``grind``               False: no knife grind at all (the un-ground plate the outline mass gate measures)
    ``axis_points``         plate Steiner points on the arm axis at the arm stations (+ ``end_axis_points``)
    ``end_axis_points``     further axis points past the last arm station, toward the arm end
    ``hook_points``         plate Steiner points midway across the hook strip at its inner columns
    ``seam_points``         plate Steiner points on each seam between the centre and the plate edge
    ``band``                (min, max) triangles; study 4's bands are for stars: ceilings only here
    """

    arm_intervals: int = 8
    end_intervals: int = 2
    arm_end_intervals: int = 2
    runout_intervals: int = 1
    runout_ease: bool = False
    hook_intervals: int = 4
    roof_intervals: int = 3
    junction_fillet_segments: int = 2
    hook_fillet_segments: int = 3
    chamfer: bool = True
    knife_land: bool = True
    grind: bool = True
    axis_points: bool = True
    end_axis_points: int = 1
    hook_points: bool = True
    seam_points: int = 1
    band: Tuple[int, int] = (0, OUTLINE_LOD_CEILING)
    note: str = ""

    def validate(self) -> None:
        for name in ("arm_intervals", "end_intervals", "arm_end_intervals", "runout_intervals", "hook_intervals"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1: {self}")
        for name in ("roof_intervals", "junction_fillet_segments", "hook_fillet_segments", "end_axis_points",
                     "seam_points"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative: {self}")
        if self.band[0] >= self.band[1]:
            raise ValueError(f"band must be (min, max): {self.band}")
        if self.chamfer and self.junction_fillet_segments == 0:
            raise ValueError("a sharp junction corner is only authored with square non-cutting edges (chamfer False)")


# =========================================================================== the spec


@dataclass(frozen=True)
class HookedCrossSpec:
    """Build-to numbers for the hooked cross (study 2.6 + the photo-matched outline).  Millimetres."""

    form: str
    mesh_name: str
    thickness_mm: float
    arm_half_width_mm: float            # at u = 0 on the arm axis
    taper_per_edge_deg: float           # each arm edge leans in by this toward the tip
    hook_corner_u_mm: float             # the hook's inner corner, on the leading edge
    tip_radius_mm: float                # tip distance from the centre (half the tip-to-tip)
    tip_offset_deg: float               # tip direction, COUNTER-clockwise of its arm axis (> 0: the handedness)
    back_arc_radius_mm: float
    back_arc_axis_mm: float             # where the back arc crosses the arm axis
    fillet_mm: float                    # concave corners (junctions, hook corner)
    mass_target_g: float
    lods: Tuple[OutlineLodSpec, ...]
    grind_angle_deg: float = GRIND_ANGLE_DEG
    edge_land_mm: float = EDGE_LAND_MM
    chamfer_mm: float = SCALLOP_CHAMFER_MM      # non-cutting edges: plan width of the small chamfer (grind angle)
    runout_mm: float = GRIND_RUNOUT_MM
    # where each blade grind has run out (the chamfer resumes), measured from the tip along the edge (mm):
    # None = where the blade meets the arm - the shoulder on the back arc, the hook-corner fillet on the inner edge
    back_grind_end_mm: Optional[float] = None
    inner_grind_end_mm: Optional[float] = None
    mass_tolerance_g: float = 2.0
    density_g_cm3: float = 7.85
    study_mass_range_g: Optional[Tuple[float, float]] = None
    study_mass_typical_g: Optional[Tuple[float, float]] = None
    title: str = ""
    study_section: str = ""
    revision: int = 1
    physics_mass_kg: Optional[float] = None
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES
    tip_wear_mm: float = 2.5
    island_margin: Optional[float] = None
    # the gallery hero turns the plate about Z by this (the camera, lights and floor stay): see build_hooked_cross.py
    hero_yaw_deg: float = 0.0

    @property
    def points(self) -> int:
        return 4

    def outline(self) -> "HookedOutline":
        return HookedOutline.from_spec(self)

    def knife(self) -> ChamferProfile:
        return ChamferProfile.knife(self.thickness_mm * MM, self.grind_angle_deg, self.edge_land_mm * MM)

    def small_chamfer(self) -> ChamferProfile:
        return ChamferProfile.at_angle(self.chamfer_mm * MM, self.grind_angle_deg)

    def validate(self) -> None:
        if not self.mesh_name.startswith("SM_Shuriken_"):
            raise ValueError(f"mesh_name must be SM_Shuriken_<Form>: {self.mesh_name}")
        lowered = (self.form + self.mesh_name + self.title).lower()
        for banned in ("manji", "swastika"):
            if banned in lowered:
                raise ValueError(f"names must not contain {banned!r} (study 5): use HookedCross")
        if not 0.0 < self.tip_offset_deg < 45.0:
            # the handedness rule: a hook tip CLOCKWISE of its arm (offset < 0) is the mirrored form, never built
            raise ValueError(f"tip_offset_deg must be in (0, 45) - counter-clockwise of the arm axis, the "
                             f"left-facing form; {self.tip_offset_deg} would build the mirrored outline")
        if not 0.0 < self.edge_land_mm <= MAX_EDGE_LAND_MM:
            raise ValueError(f"edge_land_mm must be in (0, {MAX_EDGE_LAND_MM}]: {self.edge_land_mm}")
        if not 0.0 < self.chamfer_mm < self.knife().width / MM:
            raise ValueError(f"chamfer_mm must be positive and narrower than the knife grind: {self.chamfer_mm}")
        if not self.lods:
            raise ValueError("at least LOD0 is required")
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        for lod in self.lods:
            lod.validate()
        self.outline().validate(self.lods)


# =========================================================================== columns


@dataclass
class Column:
    """One cross-section of the edge band (metres).  See the module docstring."""

    x: float
    y: float
    nx: float
    ny: float
    w: float                     # facet plan width (0: square edge)
    d: float                     # wall-top drop below the face (0: square edge; t/2: land 0)
    piece: str
    zone: str                    # "chamfer" | "runout" | "knife" (roof columns are "knife")
    ex: float = 0.0              # plate-edge point (or ridge point on a roof column)
    ey: float = 0.0
    ez_drop: float = 0.0         # plate-edge / ridge point's drop below the face (0 on the plate)
    roof: bool = False           # E is a ridge point, not on the plate
    seam: int = 0                # -1 lower seam (-45 deg), +1 upper seam (+45 deg), 0 inside the wedge
    seam_q: float = 0.0          # outline point = (q, -+q) on a seam column
    seam_qe: float = 0.0         # plate-edge point = (qe, -+qe)
    s: float = 0.0               # contour length from the lower seam (m)


@dataclass
class Run:
    """Consecutive columns of one piece; faces between neighbours take the run's piece (and zone)."""

    piece: str
    columns: List[Column]


# =========================================================================== geometry


def _unit(x: float, y: float) -> Tuple[float, float]:
    length = math.hypot(x, y)
    return x / length, y / length


def _line_circle(px: float, py: float, dx: float, dy: float, cx: float, cy: float, r: float) -> Tuple[float, float]:
    """Parameters t of p + t d on the circle (d unit), ascending."""
    fx, fy = px - cx, py - cy
    b = fx * dx + fy * dy
    c = fx * fx + fy * fy - r * r
    disc = b * b - c
    if disc < 0.0:
        raise ValueError("line misses the circle")
    root = math.sqrt(disc)
    return -b - root, -b + root


@dataclass
class HookedOutline:
    """The analytic contour of one wedge in metres (see the module docstring)."""

    spec: HookedCrossSpec
    t: float
    half_t: float
    hw0: float
    T: float
    u_hook: float
    r_tip: float
    tip: Tuple[float, float]
    hk: Tuple[float, float]
    R: float
    C: Tuple[float, float]
    elbow: Tuple[float, float]
    shoulder: Tuple[float, float]
    q_j: float
    r_f: float
    knife: ChamferProfile
    small: ChamferProfile
    runout: float
    alpha: float

    @classmethod
    def from_spec(cls, spec: HookedCrossSpec) -> "HookedOutline":
        t = spec.thickness_mm * MM
        hw0 = spec.arm_half_width_mm * MM
        T = math.tan(math.radians(spec.taper_per_edge_deg))
        u_hook = spec.hook_corner_u_mm * MM
        r_tip = spec.tip_radius_mm * MM
        off = math.radians(spec.tip_offset_deg)
        tip = (r_tip * math.cos(off), r_tip * math.sin(off))
        hk = (u_hook, hw0 - T * u_hook)
        R = spec.back_arc_radius_mm * MM
        p1 = (spec.back_arc_axis_mm * MM, 0.0)
        mx, my = 0.5 * (p1[0] + tip[0]), 0.5 * (p1[1] + tip[1])
        dx, dy = tip[0] - p1[0], tip[1] - p1[1]
        half = 0.5 * math.hypot(dx, dy)
        h = math.sqrt(R * R - half * half)
        nx, ny = -dy / (2.0 * half), dx / (2.0 * half)
        c1, c2 = (mx + h * nx, my + h * ny), (mx - h * nx, my - h * ny)
        C = c1 if c1[0] < c2[0] else c2                      # the far side: the arc bulges outward (+u)
        # elbow: the trailing edge (0, -hw0) + s (1, T)/|.| meets the circle (the larger root: the arm end)
        du, dv = _unit(1.0, T)
        s_e = _line_circle(0.0, -hw0, du, dv, C[0], C[1], R)[1]
        elbow = (s_e * du, -hw0 + s_e * dv)
        # shoulder: the leading-edge line (0, hw0) + s (1, -T)/|.| meets the circle: where the blade meets the arm
        s_s = _line_circle(0.0, hw0, du, -dv, C[0], C[1], R)[1]
        shoulder = (s_s * du, hw0 - s_s * dv)
        return cls(spec=spec, t=t, half_t=0.5 * t, hw0=hw0, T=T, u_hook=u_hook, r_tip=r_tip, tip=tip, hk=hk, R=R,
                   C=C, elbow=elbow, shoulder=shoulder, q_j=hw0 / (1.0 + T), r_f=spec.fillet_mm * MM,
                   knife=spec.knife(), small=spec.small_chamfer(), runout=spec.runout_mm * MM,
                   alpha=math.radians(spec.grind_angle_deg))

    # ------------------------------------------------------------------ edge directions and normals
    @property
    def n_trail(self) -> Tuple[float, float]:
        return _unit(-self.T, 1.0)          # left of the travel direction (1, T)

    @property
    def n_lead(self) -> Tuple[float, float]:
        return _unit(-self.T, -1.0)         # left of the travel direction (-1, T)

    @property
    def d_inner(self) -> Tuple[float, float]:
        return _unit(self.hk[0] - self.tip[0], self.hk[1] - self.tip[1])     # tip -> hook corner

    @property
    def n_inner(self) -> Tuple[float, float]:
        dx, dy = self.d_inner
        return -dy, dx

    def lead_v(self, u: float) -> float:
        return self.hw0 - self.T * u

    def arc_angle(self, p) -> float:
        return math.atan2(p[1] - self.C[1], p[0] - self.C[0])

    def arc_point(self, phi: float, inset: float = 0.0) -> Tuple[float, float]:
        r = self.R - inset
        return self.C[0] + r * math.cos(phi), self.C[1] + r * math.sin(phi)

    def arc_normal(self, phi: float) -> Tuple[float, float]:
        return -math.cos(phi), -math.sin(phi)

    # ------------------------------------------------------------------ fillets
    def junction(self, upper: bool, r_f: Optional[float] = None) -> dict:
        """The junction fillet at (q_J, -+q_J): centre, tangent point on arm 0's edge, seam midpoint, angles."""
        r_f = self.r_f if r_f is None else r_f
        q = self.q_j
        sign = 1.0 if upper else -1.0
        e_arm = _unit(1.0, -sign * self.T)                   # along arm 0's edge, away from J
        e_diag = (SQRT_HALF, sign * SQRT_HALF)               # the diagonal, away from the centre
        cos_half = e_arm[0] * e_diag[0] + e_arm[1] * e_diag[1]
        half = math.acos(max(-1.0, min(1.0, cos_half)))      # half the empty angle between the two arms
        if r_f <= 0.0:
            return {"sharp": True, "q_mid": q, "corner": (q, sign * q)}
        dist = r_f / math.sin(half)
        centre = (q + dist * e_diag[0], sign * q + dist * e_diag[1])
        n_arm = self.n_lead if upper else self.n_trail       # inward normal of arm 0's edge
        tangent = (centre[0] + r_f * n_arm[0], centre[1] + r_f * n_arm[1])
        q_mid = q + (dist - r_f) * SQRT_HALF                 # the fillet's midpoint ON the diagonal: (q_mid, -+q_mid)
        return {"sharp": False, "centre": centre, "tangent": tangent, "q_mid": q_mid, "r": r_f,
                "a_mid": math.atan2(-e_diag[1], -e_diag[0]), "a_tan": math.atan2(n_arm[1], n_arm[0]),
                "empty_angle_deg": math.degrees(2.0 * half)}

    def hook_fillet(self, r_f: Optional[float] = None) -> dict:
        r_f = self.r_f if r_f is None else r_f
        e_in = _unit(self.tip[0] - self.hk[0], self.tip[1] - self.hk[1])
        e_ld = _unit(-1.0, self.T)
        cos_full = e_in[0] * e_ld[0] + e_in[1] * e_ld[1]
        full = math.acos(max(-1.0, min(1.0, cos_full)))      # the empty angle at the hook corner
        if r_f <= 0.0:
            return {"sharp": True, "corner": self.hk, "empty_angle_deg": math.degrees(full)}
        bis = _unit(e_in[0] + e_ld[0], e_in[1] + e_ld[1])
        dist = r_f / math.sin(0.5 * full)
        tan_len = r_f / math.tan(0.5 * full)
        centre = (self.hk[0] + dist * bis[0], self.hk[1] + dist * bis[1])
        h2 = (self.hk[0] + tan_len * e_in[0], self.hk[1] + tan_len * e_in[1])      # on the inner edge
        h1 = (self.hk[0] + tan_len * e_ld[0], self.hk[1] + tan_len * e_ld[1])      # on the leading edge
        return {"sharp": False, "centre": centre, "h1": h1, "h2": h2, "r": r_f, "tangent_length": tan_len,
                "a2": math.atan2(h2[1] - centre[1], h2[0] - centre[0]),
                "a1": math.atan2(h1[1] - centre[1], h1[0] - centre[0]),
                "empty_angle_deg": math.degrees(full)}

    # ------------------------------------------------------------------ profiles
    def knife_of(self, lod: OutlineLodSpec) -> Tuple[float, float]:
        """(width, drop) of the knife grind on this LOD: the spec's land, or land 0 (facets meet in an edge line);
        (0, 0) on the un-ground plate."""
        if not lod.grind:
            return 0.0, 0.0
        if lod.knife_land:
            return self.knife.width, self.knife.depth
        return self.half_t / math.tan(self.alpha), self.half_t

    def chamfer_of(self, lod: OutlineLodSpec) -> Tuple[float, float]:
        if lod.chamfer:
            return self.small.width, self.small.depth
        return 0.0, 0.0

    def ridge(self, s: float) -> Tuple[float, float, float]:
        """The point at plan distance s from both the inner edge and the arc (inside the hook), and its foot
        parameter along the inner edge from the tip: (x, y, t_inner)."""
        dx, dy = self.d_inner
        nx, ny = self.n_inner
        px, py = self.tip[0] + s * nx, self.tip[1] + s * ny
        fx, fy = px - self.C[0], py - self.C[1]
        b = fx * dx + fy * dy
        c = fx * fx + fy * fy - (self.R - s) ** 2
        disc = max(0.0, b * b - c)
        roots = sorted((-b - math.sqrt(disc), -b + math.sqrt(disc)))
        tpar = next(r for r in roots if r >= -1e-12)
        tpar = max(tpar, 0.0)
        return px + tpar * dx, py + tpar * dy, tpar

    def apex(self, lod: OutlineLodSpec) -> Tuple[float, float, float]:
        return self.ridge(self.knife_of(lod)[0])

    # ------------------------------------------------------------------ the analytic contour (exact, for area /
    # verification): pieces as ("line", a, b) or ("arc", centre, r, a0, a1) with signed sweep a1 - a0
    def pieces(self, fillets: bool = True) -> List[tuple]:
        r_f = self.r_f if fillets else 0.0
        jl, ju, hf = self.junction(False, r_f), self.junction(True, r_f), self.hook_fillet(r_f)
        out = []
        if jl["sharp"]:
            start = (self.q_j, -self.q_j)
        else:
            out.append(("arc", jl["centre"], r_f, jl["a_mid"], jl["a_tan"]))
            start = jl["tangent"]
        out.append(("line", start, self.elbow))
        out.append(("arc", self.C, self.R, self.arc_angle(self.elbow), self.arc_angle(self.tip)))
        if hf["sharp"]:
            out.append(("line", self.tip, self.hk))
            out.append(("line", self.hk, ju["corner"] if ju["sharp"] else ju["tangent"]))
        else:
            out.append(("line", self.tip, hf["h2"]))
            a2, a1 = hf["a2"], hf["a1"]
            while a1 > a2:                       # clockwise about the fillet centre (concave)
                a1 -= 2.0 * math.pi
            out.append(("arc", hf["centre"], r_f, a2, a1))
            out.append(("line", hf["h1"], ju["corner"] if ju["sharp"] else ju["tangent"]))
        if not ju["sharp"]:
            a_t, a_m = ju["a_tan"], ju["a_mid"]
            while a_m > a_t:
                a_m -= 2.0 * math.pi
            out.append(("arc", ju["centre"], r_f, a_t, a_m))
        return out

    def wedge_area(self, fillets: bool = True) -> float:
        """Exact plan area of one wedge (m2): 1/2 closed-contour integral of x dy - y dx; the seams are rays
        through the centre and contribute nothing."""
        total = 0.0
        for piece in self.pieces(fillets):
            if piece[0] == "line":
                (ax, ay), (bx, by) = piece[1], piece[2]
                total += ax * by - bx * ay
            else:
                (cx, cy), r, a0, a1 = piece[1], piece[2], piece[3], piece[4]
                total += (r * cx * (math.sin(a1) - math.sin(a0)) - r * cy * (math.cos(a1) - math.cos(a0))
                          + r * r * (a1 - a0))
        return 0.5 * total

    def dense_contour(self, step: float = 0.02 * MM, fillets: bool = True) -> List[Tuple[float, float]]:
        """The exact outline of the whole plate (all four quarter turns), sampled every ``step`` (m), CCW."""
        wedge = []
        for piece in self.pieces(fillets):
            if piece[0] == "line":
                (ax, ay), (bx, by) = piece[1], piece[2]
                n = max(1, int(math.ceil(math.hypot(bx - ax, by - ay) / step)))
                wedge += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
            else:
                (cx, cy), r, a0, a1 = piece[1], piece[2], piece[3], piece[4]
                n = max(1, int(math.ceil(abs(a1 - a0) * r / step)))
                wedge += [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n))
                          for k in range(n)]
        out = []
        for k in range(4):
            for x, y in wedge:
                out.append({0: (x, y), 1: (-y, x), 2: (-x, -y), 3: (y, -x)}[k])
        return out

    # ------------------------------------------------------------------ columns for a LOD
    def runout_bounds(self) -> dict:
        """Contour positions of the two run-outs.  Back arc: angles about the arc centre, the run-out ends (the
        chamfer resumes) at phi_b0 - the shoulder by default - and the full knife starts runout_mm up the arc
        (phi_b1).  Inner edge: distance from the tip along the edge; the run-out ends at inner_r1 - the hook-corner
        fillet's tangent point by default - and the full knife ends runout_mm before it (inner_r0).
        ``inner_fillet`` is the fillet's tangent point (where the inner edge ends)."""
        spec = self.spec
        phi_t = self.arc_angle(self.tip)
        phi_b0 = (self.arc_angle(self.shoulder) if spec.back_grind_end_mm is None
                  else phi_t - spec.back_grind_end_mm * MM / self.R)
        hf = self.hook_fillet()
        fillet = math.hypot(hf["h2"][0] - self.tip[0], hf["h2"][1] - self.tip[1])
        end = fillet if spec.inner_grind_end_mm is None else spec.inner_grind_end_mm * MM
        return {"phi_b0": phi_b0, "phi_b1": phi_b0 + self.runout / self.R, "inner_r1": end,
                "inner_r0": end - self.runout, "inner_fillet": fillet}

    def columns(self, lod: OutlineLodSpec) -> List[Run]:
        """The runs of columns of one wedge, CCW from the lower seam to the upper seam.

        ``lod.grind`` False (the un-ground plate of the outline mass gate and the plan-silhouette reference): the SAME
        columns as the ground LOD - the ridge feet and the blade stations depend on the knife width - with every
        profile flattened to a square edge, so the un-ground plate is exactly the ground mesh's outline polygon."""
        if not lod.grind:
            runs = self.columns(replace(lod, grind=True))
            for run in runs:
                for c in run.columns:
                    c.w = c.d = c.ez_drop = 0.0
                    c.roof = False
                    c.ex, c.ey = c.x, c.y
                    c.seam_qe = c.seam_q
            return runs
        wk, dk = self.knife_of(lod)
        wc, dc = self.chamfer_of(lod)
        tan_a = math.tan(self.alpha)
        rf_j = self.r_f if lod.junction_fillet_segments > 0 else 0.0
        rf_h = self.r_f if lod.hook_fillet_segments > 0 else 0.0
        jl, ju = self.junction(False, rf_j), self.junction(True, rf_j)
        hf = self.hook_fillet(rf_h)
        rb = self.runout_bounds()
        # with a sharp hook corner the inner run-out still ends where the fillet's tangent point is on LOD0
        inner_end = rb["inner_fillet"] if not hf["sharp"] else math.hypot(self.hk[0] - self.tip[0], self.hk[1] - self.tip[1])
        inner_r0, inner_r1 = rb["inner_r0"], rb["inner_r1"]
        if hf["sharp"] and self.spec.inner_grind_end_mm is None:
            # a sharp hook corner (LOD2): the run-out ends in the corner itself
            inner_r0, inner_r1 = inner_end - self.runout, inner_end

        def col(x, y, n, w, d, piece, zone, **kw) -> Column:
            c = Column(x=x, y=y, nx=n[0], ny=n[1], w=w, d=d, piece=piece, zone=zone, **kw)
            if not c.roof and c.seam == 0:
                c.ex, c.ey = x + w * n[0], y + w * n[1]
            return c

        def chamfer_col(x, y, n, piece, **kw):
            return col(x, y, n, wc, dc, piece, "chamfer", **kw)

        def mix(f):
            if lod.runout_ease:
                f = f * f * (3.0 - 2.0 * f)          # smoothstep: tangent to the knife and to the chamfer
            return wc + (wk - wc) * f, dc + (dk - dc) * f

        runs: List[Run] = []
        # --- jin: lower half-junction fillet, seam midpoint -> tangent point on the trailing edge
        cols = []
        if jl["sharp"]:
            q = self.q_j
            cols.append(chamfer_col(q, -q, (-SQRT_HALF, SQRT_HALF), "jin", seam=-1, seam_q=q,
                                    seam_qe=q - wc * SQRT_HALF))
        else:
            m = lod.junction_fillet_segments
            q = jl["q_mid"]
            cols.append(chamfer_col(q, -q, (-SQRT_HALF, SQRT_HALF), "jin", seam=-1, seam_q=q,
                                    seam_qe=q - wc * SQRT_HALF))
            (cx, cy), r = jl["centre"], jl["r"]
            for k in range(1, m + 1):
                if k == m:
                    tx, ty = jl["tangent"]
                    cols.append(chamfer_col(tx, ty, self.n_trail, "jin"))
                    break
                a = jl["a_mid"] + (jl["a_tan"] - jl["a_mid"]) * k / m
                n = (math.cos(a), math.sin(a))
                cols.append(chamfer_col(cx + r * n[0], cy + r * n[1], n, "jin"))
        runs.append(Run("jin", cols))
        # --- trail: tangent point -> arm stations -> elbow (stations in u; the leading edge uses the same u)
        u0 = cols[-1].x
        hook_station = hf["h1"][0] if not hf["sharp"] else self.hk[0]
        # the arm stations use LOD0's (filleted) end points so every LOD's arm columns share their u where they can
        hf0 = self.hook_fillet()
        u_hk = hf0["h1"][0]
        u_root = self.junction(False)["tangent"][0]
        stations = [u_root + (u_hk - u_root) * i / lod.arm_intervals for i in range(lod.arm_intervals + 1)]
        stations[0] = u0
        if hf["sharp"]:
            stations[-1] = hook_station
        us = stations + [stations[-1] + (self.elbow[0] - stations[-1]) * k / lod.end_intervals
                         for k in range(1, lod.end_intervals + 1)]
        cols = [cols[-1]]
        for u in us[1:]:
            if u == us[-1]:
                x, y = self.elbow
            else:
                x, y = u, -self.lead_v(u)
            cols.append(chamfer_col(x, y, self.n_trail, "trail"))
        runs.append(Run("trail", cols))
        # mitre at the elbow: the trailing inset line meets the arc's inset circle
        tn = self.n_trail
        du, dv = _unit(1.0, self.T)
        px, py = cols[0].x + wc * tn[0], cols[0].y + wc * tn[1]
        s_m = _line_circle(px, py, du, dv, self.C[0], self.C[1], self.R - wc)[1]
        mitre = (px + s_m * du, py + s_m * dv)
        cols[-1].ex, cols[-1].ey = mitre
        # --- arc: elbow -> arm end (chamfer) -> run-out -> blade (knife) -> apex foot -> roof -> tip
        phi_e = self.arc_angle(self.elbow)
        ax, ay, t_apex = self.ridge(wk)
        phi_a = self.arc_angle((ax, ay))
        phis = [phi_e + (rb["phi_b0"] - phi_e) * k / lod.arm_end_intervals for k in range(lod.arm_end_intervals)]
        phis += [rb["phi_b0"] + (rb["phi_b1"] - rb["phi_b0"]) * k / lod.runout_intervals
                 for k in range(lod.runout_intervals)]
        phis += [rb["phi_b1"] + (phi_a - rb["phi_b1"]) * k / lod.hook_intervals for k in range(lod.hook_intervals)]
        phis.append(phi_a)
        cols = []
        for i, phi in enumerate(phis):
            x, y = self.arc_point(phi)
            n = self.arc_normal(phi)
            if phi <= rb["phi_b0"] + 1e-15 or i == 0:       # the run-out's first column is still the chamfer
                c = chamfer_col(x, y, n, "arc")
            elif phi < rb["phi_b1"] - 1e-15:
                f = (phi - rb["phi_b0"]) / (rb["phi_b1"] - rb["phi_b0"])
                w, d = mix(f)
                c = col(x, y, n, w, d, "arc", "runout")
            else:
                c = col(x, y, n, wk, dk, "arc", "knife")
            cols.append(c)
        cols[0].ex, cols[0].ey = mitre
        cols[-1].ex, cols[-1].ey = ax, ay                  # the apex (exact, shared with the inner edge)
        roof = []
        K = lod.roof_intervals
        for k in range(K - 1, 0, -1):
            s = wk * k / K
            rx, ry, tpar = self.ridge(s)
            phi = self.arc_angle((rx, ry))
            x, y = self.arc_point(phi)
            roof.append((s, rx, ry, tpar))
            cols.append(col(x, y, self.arc_normal(phi), wk, dk, "arc", "knife", ex=rx, ey=ry,
                            ez_drop=dk - s * tan_a, roof=True))
        tip_col = col(self.tip[0], self.tip[1], self.arc_normal(self.arc_angle(self.tip)), wk, dk, "arc", "knife",
                      ex=self.tip[0], ey=self.tip[1], ez_drop=dk, roof=True)
        cols.append(tip_col)
        runs.append(Run("arc", cols))
        # --- inner: tip -> roof feet -> apex foot -> blade -> run-out -> fillet tangent point (or the corner)
        dxi, dyi = self.d_inner
        ni = self.n_inner
        cols = [Column(**{**tip_col.__dict__, "nx": ni[0], "ny": ni[1], "piece": "inner"})]
        for s, rx, ry, tpar in reversed(roof):
            cols.append(col(self.tip[0] + tpar * dxi, self.tip[1] + tpar * dyi, ni, wk, dk, "inner", "knife",
                            ex=rx, ey=ry, ez_drop=dk - s * tan_a, roof=True))
        ts = [t_apex + (inner_r0 - t_apex) * k / lod.hook_intervals for k in range(lod.hook_intervals)]
        ts += [inner_r0 + (inner_r1 - inner_r0) * k / lod.runout_intervals for k in range(lod.runout_intervals)]
        if inner_end > inner_r1 + 1e-9:                    # a chamfered stretch before the hook-corner fillet
            n_ch = max(1, int(round((inner_end - inner_r1) / (4.0 * MM))))
            ts += [inner_r1 + (inner_end - inner_r1) * k / n_ch for k in range(n_ch)]
        ts.append(inner_end)
        for i, tpar in enumerate(ts):
            x, y = self.tip[0] + tpar * dxi, self.tip[1] + tpar * dyi
            if i == len(ts) - 1 and hf["sharp"]:
                x, y = self.hk
            if tpar <= inner_r0 + 1e-15:
                c = col(x, y, ni, wk, dk, "inner", "knife")
            else:
                f = min(1.0, (tpar - inner_r0) / (inner_r1 - inner_r0))
                w, d = mix(1.0 - f)
                c = col(x, y, ni, w, d, "inner", "runout" if f < 1.0 else "chamfer")
            cols.append(c)
        cols[1 + len(roof)].ex, cols[1 + len(roof)].ey = ax, ay
        runs.append(Run("inner", cols))
        # --- hk: the hook-corner fillet (clockwise about its centre), or the sharp corner (mitred insets)
        if hf["sharp"]:
            ld = self.n_lead
            # the square / chamfered inner edge meets the leading edge: mitre of the two insets
            last = cols[-1]
            p_in = (last.x + wc * ni[0], last.y + wc * ni[1])
            p_ld = (self.hk[0] + wc * ld[0], self.hk[1] + wc * ld[1])
            ex, ey = _intersect(p_in, (dxi, dyi), p_ld, _unit(-1.0, self.T))
            last.ex, last.ey = ex, ey
            corner_lead = chamfer_col(self.hk[0], self.hk[1], ld, "lead")
            corner_lead.ex, corner_lead.ey = ex, ey
            runs.append(Run("hk", [last, corner_lead]))
            lead_start = corner_lead
        else:
            m = lod.hook_fillet_segments
            (cx, cy), r = hf["centre"], hf["r"]
            a2, a1 = hf["a2"], hf["a1"]
            while a1 > a2:
                a1 -= 2.0 * math.pi
            fcols = [cols[-1]]
            for k in range(1, m + 1):
                if k == m:
                    fcols.append(chamfer_col(hf["h1"][0], hf["h1"][1], self.n_lead, "hk"))
                    break
                a = a2 + (a1 - a2) * k / m
                n = (math.cos(a), math.sin(a))
                fcols.append(chamfer_col(cx + r * n[0], cy + r * n[1], n, "hk"))
            runs.append(Run("hk", fcols))
            lead_start = fcols[-1]
        # --- lead: back along the arm stations (the same u as the trailing edge), to the junction tangent point
        cols = [lead_start]
        for u in reversed(stations[:-1]):
            if u == stations[0]:
                if ju["sharp"]:
                    x, y = self.q_j, self.q_j
                else:
                    x, y = ju["tangent"]
            else:
                x, y = u, self.lead_v(u)
            cols.append(chamfer_col(x, y, self.n_lead, "lead"))
        runs.append(Run("lead", cols))
        # --- jout: upper half-junction fillet, tangent point -> seam midpoint (clockwise about its centre)
        cols = [cols[-1]]
        if ju["sharp"]:
            q = self.q_j
            last = cols[-1]                                  # square edges only (validated): E = P
            last.seam, last.seam_q, last.seam_qe, last.nx, last.ny = 1, q, q, -SQRT_HALF, -SQRT_HALF
            runs.append(Run("jout", cols))
        else:
            m = lod.junction_fillet_segments
            (cx, cy), r = ju["centre"], ju["r"]
            a_t, a_m = ju["a_tan"], ju["a_mid"]
            while a_m > a_t:
                a_m -= 2.0 * math.pi
            for k in range(1, m + 1):
                if k == m:
                    q = ju["q_mid"]
                    cols.append(chamfer_col(q, q, (-SQRT_HALF, -SQRT_HALF), "jout", seam=1, seam_q=q,
                                            seam_qe=q - wc * SQRT_HALF))
                    break
                a = a_t + (a_m - a_t) * k / m
                n = (math.cos(a), math.sin(a))
                cols.append(chamfer_col(cx + r * n[0], cy + r * n[1], n, "jout"))
            runs.append(Run("jout", cols))
        for run in runs:
            for c in run.columns:
                if c.seam:
                    sign = 1.0 if c.seam > 0 else -1.0
                    c.x, c.y = c.seam_q, sign * c.seam_q
                    c.ex, c.ey = c.seam_qe, sign * c.seam_qe
        # contour length (for reporting / attributes)
        s = 0.0
        prev = None
        for run in runs:
            for c in run.columns:
                if prev is not None:
                    s += math.hypot(c.x - prev.x, c.y - prev.y)
                c.s = s
                prev = c
        return runs

    def plate_edge(self, lod: OutlineLodSpec) -> List[Tuple[float, float]]:
        """The plate-edge polygon of one wedge (open: lower seam -> upper seam), consecutive duplicates removed."""
        out = []
        for run in self.columns(lod):
            for c in run.columns:
                if c.roof:
                    continue
                p = (c.ex, c.ey)
                if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-12:
                    out.append(p)
        return out

    # ------------------------------------------------------------------ checks
    def validate(self, lods) -> None:
        mm = lambda v: f"{v / MM:.4f} mm"  # noqa: E731
        self.knife.validate(self.half_t)
        self.small.validate(self.half_t)
        if not self.elbow[0] > self.u_hook:
            raise ValueError(f"elbow at u = {mm(self.elbow[0])} lies inside the hook corner")
        rb = self.runout_bounds()
        ax, ay, t_apex = self.ridge(self.knife.width)
        if not t_apex < rb["inner_r0"]:
            raise ValueError("the inner edge's run-out starts inside the tip roof")
        if not self.arc_angle((ax, ay)) > rb["phi_b1"]:
            raise ValueError("the back arc's run-out reaches into the tip roof")
        for level, lod in enumerate(lods):
            poly = self.plate_edge(lod)
            if len(poly) < 3:
                raise ValueError(f"LOD{level}: plate edge has {len(poly)} points")
            for (x, y) in poly:
                if y < -x - 1e-12 or y > x + 1e-12:
                    raise ValueError(f"LOD{level}: plate-edge point ({mm(x)}, {mm(y)}) leaves the wedge")

    def summary(self) -> dict:
        """Derived figures in mm / deg for the report's build_to block."""
        mm = lambda v: round(v / MM, 4)  # noqa: E731
        hf, jl = self.hook_fillet(), self.junction(False)
        tip_in = _unit(self.hk[0] - self.tip[0], self.hk[1] - self.tip[1])
        phi_t = self.arc_angle(self.tip)
        t_arc = (math.sin(phi_t), -math.cos(phi_t))                    # back along the arc from the tip
        included = math.degrees(math.acos(tip_in[0] * t_arc[0] + tip_in[1] * t_arc[1]))
        e_t = _unit(1.0, self.T)
        phi_e = self.arc_angle(self.elbow)
        a_e = (-math.sin(phi_e), math.cos(phi_e))
        elbow_angle = 180.0 - math.degrees(math.acos(e_t[0] * a_e[0] + e_t[1] * a_e[1]))
        rb = self.runout_bounds()
        ax, ay, t_apex = self.ridge(self.knife.width)
        inner = math.hypot(self.hk[0] - self.tip[0], self.hk[1] - self.tip[1])
        return {
            "tip_to_tip_mm": mm(2.0 * self.r_tip),
            "across_the_arms_mm": mm(2.0 * (self.C[0] + math.sqrt(self.R ** 2 - self.C[1] ** 2))),
            "arm_width_at_centre_mm": mm(2.0 * self.hw0),
            "arm_width_at_hook_corner_mm": mm(2.0 * self.lead_v(self.u_hook)),
            "arm_taper_included_deg": round(2.0 * math.degrees(math.atan(self.T)), 4),
            "central_square_mm": mm(2.0 * self.q_j),
            "hook_corner_mm": [mm(self.hk[0]), mm(self.hk[1])],
            "tip_mm": [mm(self.tip[0]), mm(self.tip[1])],
            "inner_edge_deg_to_arm": round(math.degrees(math.atan2(self.tip[1] - self.hk[1], self.tip[0] - self.hk[0])), 4),
            "inner_edge_length_mm": mm(inner),
            "tip_included_deg": round(included, 4),
            "elbow_included_deg": round(elbow_angle, 4),
            "back_arc_radius_mm": mm(self.R), "back_arc_centre_mm": [mm(self.C[0]), mm(self.C[1])],
            "back_arc_axis_crossing_mm": mm(self.C[0] + math.sqrt(self.R ** 2 - self.C[1] ** 2)),
            "elbow_mm": [mm(self.elbow[0]), mm(self.elbow[1])],
            "shoulder_mm": [mm(self.shoulder[0]), mm(self.shoulder[1])],
            "back_arc_length_mm": {"elbow_to_shoulder": mm(self.R * (self.arc_angle(self.shoulder) - phi_e)),
                                   "shoulder_to_tip": mm(self.R * (phi_t - self.arc_angle(self.shoulder)))},
            "fillet_mm": mm(self.r_f),
            "junction_empty_angle_deg": round(jl["empty_angle_deg"], 4),
            "hook_corner_empty_angle_deg": round(hf["empty_angle_deg"], 4),
            "knife": {"angle_deg": round(math.degrees(self.alpha), 4), "land_mm": mm(self.t - 2.0 * self.knife.depth),
                      "width_mm": mm(self.knife.width), "depth_mm": mm(self.knife.depth)},
            "small_chamfer": {"width_mm": mm(self.small.width), "depth_mm": mm(self.small.depth),
                              "wall_mm": mm(self.t - 2.0 * self.small.depth)},
            "apex_mm": [mm(ax), mm(ay)], "apex_from_tip_mm": mm(math.hypot(ax - self.tip[0], ay - self.tip[1])),
            "grind_extent": {
                "back_arc": {"knife_from_tip_mm": mm(self.R * (phi_t - rb["phi_b1"])),
                             "runout_mm": mm(self.runout),
                             "chamfer_resumes_from_tip_mm": mm(self.R * (phi_t - rb["phi_b0"])),
                             "chamfer_resumes_at": ("the shoulder (the arm's leading-edge line meets the arc)"
                                                    if self.spec.back_grind_end_mm is None else "a set distance"),
                             "shoulder_from_tip_mm": mm(self.R * (phi_t - self.arc_angle(self.shoulder)))},
                "inner_edge": {"knife_from_tip_mm": mm(rb["inner_r0"]), "runout_mm": mm(self.runout),
                               "chamfer_resumes_from_tip_mm": mm(rb["inner_r1"]),
                               "chamfer_resumes_at": ("the hook-corner fillet's tangent point"
                                                      if self.spec.inner_grind_end_mm is None else "a set distance"),
                               "fillet_from_tip_mm": mm(rb["inner_fillet"])},
            },
            "wedge_area_mm2": round(self.wedge_area() / MM ** 2, 6),
            "area_mm2": round(4.0 * self.wedge_area() / MM ** 2, 6),
        }


def _intersect(p, d, q, e) -> Tuple[float, float]:
    """Intersection of the lines p + s d and q + t e."""
    den = d[0] * e[1] - d[1] * e[0]
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return p[0] + s * d[0], p[1] + s * d[1]


def outline_mass_g(spec: HookedCrossSpec) -> float:
    o = spec.outline()
    return 4.0 * o.wedge_area() / MM ** 2 * spec.thickness_mm / 1000.0 * spec.density_g_cm3


__all__ = ["Column", "HookedCrossSpec", "HookedOutline", "OUTLINE_LOD_CEILING", "OutlineLodSpec", "PIECES", "Run",
           "SQRT_HALF", "outline_mass_g"]
