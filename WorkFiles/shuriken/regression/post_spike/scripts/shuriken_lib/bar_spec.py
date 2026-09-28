"""Throwing-spike (bo-shuriken) spec: pure data, no bpy.

SHURIKEN_STUDY.md 2.5 (Katori / Meifu Shinkage pattern): a straight SQUARE bar, square in
section through the point, sharpened at one end with a shorter taper at the other, no hole.
Study 4: C4 about the long axis (not an array shape), pivot at the centre of mass by volume.

Frame (every LOD): long axis X, +X toward the point, the bar lying with a flat face down
(faces normal to +-Y and +-Z; the ground is at z = -a).  Authoring is in a bar-local x that
runs from 0 at the butt to L at the tip; the stored mesh is that shifted by ``shift`` (the
x of the finished LOD0's centre of mass by volume), so the object origin IS the centre of
mass and the point sits at +(L - shift).

Section and ends (metres in ``BarOutline``):

    a        half the section (3 mm)
    tail     x in [0, Lt]: the square tapers linearly from half-width e (the butt, 1.5 mm)
             to a (the study's ESTIMATE: the last 20 mm to 3 mm); flat faces, sharp ridges
    body     x in [Lt, L - Lp]: the full 6 mm square
    point    x in [L - Lp, L]: four flat facets, one per face, from the full section to a
             square tip flat of half-width tau (the pack's tip radius, 0.075 mm, like the
             stars' land) at x = L exactly, so the length stays the sourced 150 mm
    arrises  the four long arrises carry a round of radius rho (0.3 mm, the study's "bevel
             the four long arrises about 0.3 mm", in Blender's Offset sense: 0.3 mm from the
             old edge along each face) authored as K chords inscribed in the arc (K = 1 is a
             flat 45 deg chamfer, K = 0 square arrises).  The point and tail facets are planes
             that cut through the round: each arc point P_j is cut where the facet of its
             dominant face reaches it, so the round RUNS OUT into the facets over
             (a - d) / slope (d = the arc's diagonal point) and the pyramid ridges beyond are
             sharp - exactly what grinding a point into a bar with rounded arrises leaves.

C4 is exact: one quadrant (the top face, the corner at +y +z, the top point / tail facet) is
authored and turned by trig-free quarter turns about X; the profile is mirrored about the
diagonal explicitly (P_{K-j} = swap(P_j)), so every LOD is also mirror-symmetric (D4).

The mass gate (the pack's rule since the knife-grind pass) is evaluated on the UN-GROUND
bar: the same outline with square arrises and a sharp point (no round, no tip flat), i.e.
5400 - 600 - 300 = 4500 mm3 = 35.325 g at 7.85 g/cm3 against the sourced 37 g (+-2 g).
The finished (rounded, tip-flat) mass is reported and drives the physics override.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

from .spec import LOD_SCREEN_SIZES, MM

# Ceilings only - nothing is padded (study 2.5: "the silhouette is nearly all straight line, so the
# triangles belong at the point").  150 ~ the study's typical 144-triangle single star; a bar's LOD1
# stays under 100 and its LOD2 under 48, the study's floor for a whole star.
BAR_LOD_BANDS = ((0, 150), (0, 100), (0, 48))
BAR_CLASSES = ("face", "round", "point", "tail", "tip", "butt")
BAR_CLASS_CODE = {name: code for code, name in enumerate(BAR_CLASSES)}
GROUND_CLASSES = ("round", "point", "tip")     # the polished, ground surfaces (material: bar mode)


@dataclass(frozen=True)
class BarLodSpec:
    """One spike LOD.  ``arris_segments`` K: chords of the arris round (0 = square arrises,
    1 = a flat 45 deg chamfer, >= 2 = an inscribed round, smooth-shaded within itself)."""

    arris_segments: int = 4
    band: Tuple[int, int] = BAR_LOD_BANDS[0]
    note: str = ""

    @property
    def has_round(self) -> bool:
        return self.arris_segments > 0

    def validate(self) -> None:
        if self.arris_segments < 0:
            raise ValueError(f"arris_segments cannot be negative: {self}")
        if self.band[0] >= self.band[1]:
            raise ValueError(f"band must be (min, max): {self.band}")


def bar_triangles(lod: BarLodSpec) -> int:
    """Exact triangle count as the generator authors it.

    4 face quads (8) + tip and butt quads (4); per arris K strips (quads; for odd K the middle
    strip crosses the diagonal and ends in a triangle at each run-out: 4 triangles); per
    facet (4 point + 4 tail) a quad strip zipped between its two mirrored chains: K + 2
    triangles for even K, K + 3 for odd K.  Even K: 16 K + 28; odd K: 16 K + 44.
    """
    k = lod.arris_segments
    if k % 2 == 0:
        return 16 * k + 28
    return 16 * k + 44


@dataclass(frozen=True)
class BarSpec:
    """Build-to numbers for the throwing spike (study 2.5).  Millimetres, like RadialStarSpec."""

    form: str
    mesh_name: str
    length_mm: float                # butt to tip (SOURCED 150)
    section_mm: float               # square section side (SOURCED 6; never the reseller's 8)
    point_mm: float                 # point taper length (SOURCED 25)
    tail_taper_mm: float            # tail taper length (ESTIMATE 20)
    tail_end_mm: float              # butt square side (ESTIMATE 3)
    mass_target_g: float
    lods: Tuple[BarLodSpec, ...]
    tip_flat_mm: float = 0.15       # the point ends in a square flat this wide: tip radius 0.075 mm (the stars')
    arris_mm: float = 0.30          # arris round radius = Blender Bevel "Offset" (study: about 0.3 mm)
    study_mass_range_g: Optional[Tuple[float, float]] = None
    study_mass_typical_g: Optional[Tuple[float, float]] = None
    mass_tolerance_g: float = 2.0
    density_g_cm3: float = 7.85
    title: str = ""
    study_section: str = ""
    revision: int = 1
    physics_mass_kg: Optional[float] = None
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES
    grip_from_butt_mm: float = 40.0     # SOCKET_Grip on the axis this far from the butt (ESTIMATE, see build_spike)
    axial_wear_mm: float = 50.0         # the coat's wear ramps up over this length toward the point
    hero_yaw_deg: float = 0.0           # gallery only: the hero shot turns the bar about Z by this much
    hull: str = "bar_prism"
    island_margin: Optional[float] = None

    @property
    def points(self) -> int:
        return 4

    def outline(self, shift_mm: float = 0.0, sharp: bool = False) -> "BarOutline":
        """Metre values; ``shift_mm`` moves the origin to that bar-local x (the centre of mass);
        ``sharp`` = the un-ground outline (square arrises are the LOD's business; no tip flat)."""
        return BarOutline.from_spec(self, shift_mm * MM, sharp=sharp)

    def validate(self) -> None:
        if not self.mesh_name.startswith("SM_Shuriken_"):
            raise ValueError(f"mesh_name must be SM_Shuriken_<Form> (study 4 naming): {self.mesh_name}")
        if not self.lods:
            raise ValueError("at least LOD0 is required")
        if self.hull != "bar_prism":
            raise ValueError("the spike's hull is the un-rounded bar itself (it is convex): hull='bar_prism'")
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        counts = []
        for level, lod in enumerate(self.lods):
            lod.validate()
            predicted = bar_triangles(lod)
            if predicted > lod.band[1]:
                raise ValueError(f"{self.mesh_name} LOD{level}: {predicted} triangles predicted, over {lod.band}")
            counts.append(predicted)
        if any(b >= a for a, b in zip(counts, counts[1:])):
            raise ValueError(f"LOD triangle counts must strictly descend: {counts}")
        self.outline().validate()


@dataclass(frozen=True)
class BarOutline:
    """Derived spike outline in metres (see the module docstring for the frame)."""

    n: int
    length: float
    a: float                # half section
    e: float                # half the butt square
    lp: float               # point length
    lt: float               # tail taper length
    tau: float              # half the tip flat (the tip radius); 0 = a sharp apex
    rho: float              # arris round radius
    shift: float            # bar-local x of the object origin (the centre of mass)
    hero_yaw_deg: float = 0.0
    lod_strip_axis: str = "y"
    grind_target_back_m: float = 0.013
    axial_wear: float = 0.050

    @classmethod
    def from_spec(cls, spec: BarSpec, shift: float = 0.0, sharp: bool = False) -> "BarOutline":
        return cls(n=4, length=spec.length_mm * MM, a=0.5 * spec.section_mm * MM, e=0.5 * spec.tail_end_mm * MM,
                   lp=spec.point_mm * MM, lt=spec.tail_taper_mm * MM,
                   tau=0.0 if sharp else 0.5 * spec.tip_flat_mm * MM, rho=spec.arris_mm * MM, shift=shift,
                   hero_yaw_deg=spec.hero_yaw_deg, axial_wear=spec.axial_wear_mm * MM)

    # ------------------------------------------------------------------ the rig's view of a bar
    @property
    def half_t(self) -> float:
        """Half the section: the bar lies flat, so the ground is at z = -a (render rig)."""
        return self.a

    @property
    def r_tip(self) -> float:
        """Object-space x of the tip (the rig's 'tip radius': the point on +X)."""
        return self.length - self.shift

    @property
    def x_butt(self) -> float:
        return -self.shift

    @property
    def x_tail_base(self) -> float:
        return self.lt - self.shift

    @property
    def x_point_base(self) -> float:
        return self.length - self.lp - self.shift

    @property
    def x_tip(self) -> float:
        return self.length - self.shift

    @property
    def point_slope(self) -> float:
        """Half-width lost per metre along the point (tan of the facet's angle to the axis)."""
        return (self.a - self.tau) / self.lp

    @property
    def tail_slope(self) -> float:
        return (self.a - self.e) / self.lt

    def tip_extents(self):
        """(span_x, span_y) in plan: the length along X, the section along Y."""
        return self.length, 2.0 * self.a

    # ------------------------------------------------------------------ profile and cuts (bar-local x)
    def profile(self, k: int) -> List[Tuple[float, float]]:
        """(y, z) of the arris round's chord points P_0..P_K for the corner at +y +z.

        P_0 = (a - rho, a) on the top face, P_K = (a, a - rho) on the +y face, the rest on the
        arc of radius rho about (a - rho, a - rho); mirrored about the diagonal exactly
        (P_{K-j} = swap(P_j)), the diagonal point (even K) with y == z.  K = 0: the corner.
        """
        a, rho = self.a, self.rho
        if k == 0:
            return [(a, a)]
        pts: List[Tuple[float, float]] = []
        for j in range(k + 1):
            if j == 0:
                pts.append((a - rho, a))
            elif j == k:
                pts.append((a, a - rho))
            elif 2 * j == k:
                d = a - rho + rho * math.cos(0.25 * math.pi)
                pts.append((d, d))
            elif 2 * j < k:
                theta = 0.5 * math.pi * (1.0 - j / k)
                pts.append((a - rho + rho * math.cos(theta), a - rho + rho * math.sin(theta)))
            else:
                y, z = pts[k - j]
                pts.append((z, y))
        return pts

    def diagonal(self, k: int) -> float:
        """Where the round (or chamfer, K odd: its middle chord) crosses the diagonal y = z."""
        if k == 0:
            return self.a
        if k % 2 == 0:
            return self.a - self.rho + self.rho * math.cos(0.25 * math.pi)
        pts = self.profile(k)
        y, z = pts[(k - 1) // 2]
        return 0.5 * (y + z)

    def x_tail_cut(self, m: float) -> float:
        """Bar-local x where the tail facet of the dominant face reaches a point of max(|y|, |z|) = m."""
        return self.lt * (m - self.e) / (self.a - self.e)

    def x_point_cut(self, m: float) -> float:
        return (self.length - self.lp) + (self.a - m) / self.point_slope

    def runout_mm(self, k: int) -> dict:
        d = self.diagonal(k)
        return {"diagonal_mm": d / MM, "point_runout_mm": (self.x_point_cut(d) - (self.length - self.lp)) / MM,
                "tail_runout_mm": (self.lt - self.x_tail_cut(d)) / MM}

    def validate(self) -> None:
        mm = lambda v: f"{v / MM:.4f} mm"  # noqa: E731
        if not 0.0 < self.e < self.a:
            raise ValueError(f"butt half-width {mm(self.e)} must be inside (0, {mm(self.a)})")
        if not 0.0 <= self.tau < self.e:
            raise ValueError(f"tip flat half-width {mm(self.tau)} must be under the butt's {mm(self.e)}")
        if not 0.0 < self.rho < self.a - self.e:
            raise ValueError(f"arris round {mm(self.rho)} must be under a - e = {mm(self.a - self.e)} (it has to run out "
                             "inside the tail taper)")
        if not self.lt + self.lp < self.length:
            raise ValueError("the tail taper and the point overlap")
        for k in (1, 2, 4):
            d = self.diagonal(k)
            if not self.x_tail_cut(d) > 0.0 or not self.x_point_cut(d) < self.length:
                raise ValueError(f"K={k}: the arris run-out leaves its taper")


# =========================================================================== analytic volume / mass / COM


def _frustum(l: float, h0: float, h1: float, x0: float) -> Tuple[float, float]:
    """(volume, x-moment) of a square frustum of half-widths h0 at x0 and h1 at x0 + l (mm)."""
    # A(x) = 4 (h0 + s t)^2, t in [0, l], s = (h1 - h0) / l
    s = (h1 - h0) / l
    vol = 4.0 * (h0 * h0 * l + h0 * s * l * l + s * s * l ** 3 / 3.0)
    mom_t = 4.0 * (h0 * h0 * l * l / 2.0 + 2.0 * h0 * s * l ** 3 / 3.0 + s * s * l ** 4 / 4.0)
    return vol, x0 * vol + mom_t


def bar_analytic(spec: BarSpec) -> dict:
    """Exact volume, mass and centre of mass of the spike, term by term (mm, pure Python).

    The UN-GROUND outline (the mass gate): the 150 x 6 x 6 prism, minus what the 25 mm point
    removes (the prism section 900 mm3 minus the pyramid 36 x 25 / 3 = 300) and what the 20 mm
    tail taper removes (720 minus the frustum 20 / 3 (36 + 9 + 18) = 420).  The finished bar
    adds the tip flat (the facets end on a 0.15 mm square at x = 150 instead of a point) and
    takes the arris round off; the round's section loss per corner is rho^2 (1 - pi / 4) for the
    true arc (the K-chord polygon loses a little more) - reported for the body run only, the
    run-outs are measured on the mesh.
    """
    L, s, lp, lt = spec.length_mm, spec.section_mm, spec.point_mm, spec.tail_taper_mm
    a, e, tau, rho = 0.5 * s, 0.5 * spec.tail_end_mm, 0.5 * spec.tip_flat_mm, spec.arris_mm
    prism = L * s * s
    point_prism, pyramid = lp * s * s, s * s * lp / 3.0
    tail_prism = lt * s * s
    tail_frustum, tail_mom = _frustum(lt, e, a, 0.0)
    body_len = L - lp - lt
    body, body_mom = s * s * body_len, s * s * body_len * (lt + 0.5 * body_len)
    pyr, pyr_mom = _frustum(lp, a, 0.0, L - lp)
    outline = tail_frustum + body + pyr
    com_outline = (tail_mom + body_mom + pyr_mom) / outline
    tipped, tipped_mom = _frustum(lp, a, tau, L - lp)
    finished_unrounded = tail_frustum + body + tipped
    com_unrounded = (tail_mom + body_mom + tipped_mom) / finished_unrounded
    round_loss = 4.0 * rho * rho * (1.0 - math.pi / 4.0)
    to_g = lambda v: v / 1000.0 * spec.density_g_cm3  # noqa: E731
    return {
        "units": "mm3 / mm / g",
        "prism_150x6x6": prism,
        "point_prism": point_prism, "point_pyramid": pyramid, "point_removes": point_prism - pyramid,
        "tail_prism": tail_prism, "tail_frustum": tail_frustum, "tail_removes": tail_prism - tail_frustum,
        "outline_volume": outline, "outline_mass_g": to_g(outline),
        "hand_check": "5400 - 600 (point pyramid) - 300 (tail frustum) = 4500 mm3 = 35.3 g",
        "outline_com_from_butt_mm": com_outline,
        "outline_com_from_middle_mm": com_outline - 0.5 * L,
        "tip_flat_adds": tipped - pyr,
        "finished_unrounded_volume": finished_unrounded,
        "finished_unrounded_com_from_butt_mm": com_unrounded,
        "arris_round_section_loss_mm2": round_loss,
        "arris_round_body_loss_mm3": round_loss * body_len,
        "point_facet_angle_to_axis_deg": math.degrees(math.atan((a - tau) / lp)),
        "point_included_deg": 2.0 * math.degrees(math.atan((a - tau) / lp)),
        "point_included_sharp_deg": 2.0 * math.degrees(math.atan(a / lp)),
        "tail_facet_angle_to_axis_deg": math.degrees(math.atan((a - e) / lt)),
        "mass_target_g": spec.mass_target_g,
        "outline_minus_target_g": to_g(outline) - spec.mass_target_g,
    }


def tail_end_for_mass(spec: BarSpec, target_g: Optional[float] = None) -> float:
    """The butt side (mm) that would make the un-ground outline weigh ``target_g`` with the tail
    taper length kept: the only ESTIMATE the brief allows to move."""
    target = spec.mass_target_g if target_g is None else target_g
    volume = target * 1000.0 / spec.density_g_cm3
    s, lt = spec.section_mm, spec.tail_taper_mm
    fixed = spec.length_mm * s * s - (spec.point_mm * s * s - s * s * spec.point_mm / 3.0) - lt * s * s
    frustum = volume - fixed                      # = lt / 3 (s^2 + x^2 + s x)
    c = s * s - 3.0 * frustum / lt
    return (-s + math.sqrt(s * s - 4.0 * c)) / 2.0


__all__ = ["BAR_CLASSES", "BAR_CLASS_CODE", "BAR_LOD_BANDS", "BarLodSpec", "BarOutline", "BarSpec", "GROUND_CLASSES",
           "bar_analytic", "bar_triangles", "tail_end_for_mass"]
