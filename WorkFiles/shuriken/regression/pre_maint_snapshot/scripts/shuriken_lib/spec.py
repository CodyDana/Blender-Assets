"""Form specs for the radial-star shuriken: pure data, no bpy.

A form is one ``RadialStarSpec`` (build-to numbers in millimetres, straight from
References/Shuriken/SHURIKEN_STUDY.md section 2) plus a chain of ``LodSpec`` segment
counts.  ``Outline`` turns the millimetres into the metre values the generator uses,
with exactly the arithmetic the rev-2 four-point script used, so the four-point
rebuilds bit-for-bit.

LOD strategy (study 4's table, replacing rev 2's Decimate):

    LOD0  1.0   1,200-2,500   full outline, bevels, hole ring
    LOD1  0.5     500-900     halve the hole ring and the bevel segments
    LOD2  0.25    120-250     drop the bevel and the hole entirely

Every LOD is authored by the same parametric generator at its own segment counts,
so each is a clean, exactly C_n mesh that genuinely differs from LOD0.
``study_lod_chain`` derives LOD1/LOD2 from a LOD0 by those rules; a form may also
spell its LODs out by hand.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional, Tuple

MM = 0.001                  # 1 Blender unit = 1 m (study 4)
SNAP = 1e-9                 # every vertex is snapped to 1 nm; duplicates become impossible


def rotate(k: int, n: int, x: float, y: float):
    """Rotate (x, y) by k n-th turns.

    Multiples of a quarter turn are done without trig (sign flips and swaps), so a C4
    form's four arms land on bit-identical floats - the property rev 2 relied on for an
    exactly C4 LOD0.  Any other turn uses cos/sin of the exact fraction 2*pi*k/n.
    """
    k %= n
    if (4 * k) % n == 0:
        q = (4 * k // n) % 4
        if q == 0:
            return x, y
        if q == 1:
            return -y, x
        if q == 2:
            return -x, -y
        return y, -x
    angle = 2.0 * math.pi * k / n
    c, s = math.cos(angle), math.sin(angle)
    return c * x - s * y, s * x + c * y


LOD0_BAND = (1200, 2500)
LOD1_BAND = (500, 900)
LOD2_BAND = (120, 250)
LOD_SCREEN_SIZES = (1.0, 0.5, 0.25)
HULL_METHODS = ("pipeline", "tip_prism")


@dataclass(frozen=True)
class LodSpec:
    """Segment counts for one LOD.  Counts are per wedge (one 360/n sector) unless noted.

    ``columns``            quads across the arm (``columns + 1`` plate columns)
    ``notch_segments``     hub segments per HALF notch (the notch arc is silhouette)
    ``hole_segments``      hole-ring segments per wedge; 0 drops the hole and the hub
                           becomes a disc fanned from the centre
    ``bevel_segments``     segments of the rounded ground facet; 0 drops the bevel
    ``straight_intervals`` intervals from the hub arc to the shoulder
    ``taper_intervals``    bevelled: run-out ring to bevel apex; plain: shoulder to tip.
                           This is the knob the builder raises when a LOD lands under
                           its band floor (it adds no shape, so it is the honest pad)
    ``tip_intervals``      bevelled only: bevel apex to the point (the roof there is
                           curved along its length, so these carry real shape)
    ``band``               (min, max) triangles, study 4
    """

    columns: int = 4
    notch_segments: int = 2
    hole_segments: int = 4
    bevel_segments: int = 3
    straight_intervals: int = 3
    taper_intervals: int = 4
    tip_intervals: int = 2
    band: Tuple[int, int] = LOD0_BAND
    note: str = ""

    @property
    def hub_segments(self) -> int:
        """Hub-ring segments per wedge: both half notches plus the arm root arc."""
        return 2 * self.notch_segments + self.columns

    @property
    def has_hole(self) -> bool:
        return self.hole_segments > 0

    @property
    def has_bevel(self) -> bool:
        return self.bevel_segments > 0

    def validate(self) -> None:
        if self.columns < 1 or self.notch_segments < 1 or self.straight_intervals < 1:
            raise ValueError(f"columns, notch_segments and straight_intervals must be >= 1: {self}")
        if self.taper_intervals < 1:
            raise ValueError(f"taper_intervals must be >= 1: {self}")
        if self.hole_segments < 0 or self.bevel_segments < 0 or self.tip_intervals < 0:
            raise ValueError(f"segment counts cannot be negative: {self}")
        if self.has_bevel and self.tip_intervals < 1:
            raise ValueError("a bevelled LOD needs tip_intervals >= 1 (apex to point)")
        if self.has_hole and self.hub_segments % self.hole_segments:
            raise ValueError(
                f"hub segments per wedge ({self.hub_segments} = 2 x {self.notch_segments} notch + "
                f"{self.columns} columns) must be a multiple of hole_segments ({self.hole_segments}) "
                f"so the hole ring bridges to the hub ring k:1 without T-junctions")
        if self.band[0] >= self.band[1]:
            raise ValueError(f"band must be (min, max): {self.band}")


def wedge_triangles(lod: LodSpec) -> int:
    """Exact triangle count of one wedge as the generator authors it (tested against it).

    Lets a spec pick LOD counts that land in band before any geometry exists.  Terms:
    hub region (annulus bridged to the hole ring, or a disc fan without a hole), notch
    walls, hole wall, parallel run, and the taper - shoulder->run-out fan, bevelled
    bridges to the apex, the roof past the apex and the tip cap; or, without a bevel,
    plain taper bridges closing on a point.
    """
    cols, notch, hub = lod.columns, lod.notch_segments, lod.hub_segments
    tris = 4 * notch + lod.straight_intervals * (4 * cols + 4)
    if lod.has_hole:
        tris += 2 * (hub + lod.hole_segments) + 2 * lod.hole_segments
    else:
        tris += 2 * hub
    if lod.has_bevel:
        b = lod.bevel_segments
        tris += 4 * cols + 4 * b + 4                                   # shoulder -> run-out
        tris += (lod.taper_intervals - 1) * (4 * cols + 8 * b + 4)      # run-out -> apex
        tris += 2 * cols + 8 * b + 4                                    # last bridge onto the apex
        tris += (lod.tip_intervals - 1) * (8 * b + 4) + 4 * b + 4       # roof and tip cap
    else:
        tris += (lod.taper_intervals - 1) * (4 * cols + 4) + 2 * cols + 4
    return tris


def lod_triangles(lod: LodSpec, points: int) -> int:
    return points * wedge_triangles(lod)


def _first_fitting(candidates, points: int, band) -> LodSpec:
    """First valid candidate whose triangle count is not over the band ceiling."""
    tried = []
    for lod in candidates:
        try:
            lod.validate()
        except ValueError:
            continue
        count = lod_triangles(lod, points)
        tried.append((count, lod))
        if count <= band[1]:
            return lod
    detail = ", ".join(f"{count}" for count, _lod in tried)
    raise ValueError(f"no study-4 LOD candidate fits under {band[1]} triangles for C{points} "
                     f"(candidates gave {detail}); spell this LOD out by hand")


def study_lod_chain(lod0: LodSpec, points: int) -> Tuple[LodSpec, LodSpec, LodSpec]:
    """LOD0 plus LOD1/LOD2 derived by study 4's table, sized for a C_points star.

    LOD1 halves the hole ring and the bevel segments (3 -> 2: rounded up, so the facet
    stays a curve rather than a flat chamfer); it also drops what never carried shape -
    extra plate columns and extra intervals on the flat parallel run - and halves the
    ruled taper intervals, but keeps the notch arc (silhouette) and the intervals past
    the bevel apex (a curved roof).  LOD2 drops the bevel and the hole entirely.

    Triangles scale with n, so when the preferred counts would overshoot the band ceiling
    (a C8 LOD2 at 2 columns and 2 notch segments is 320 triangles) coarser candidates are
    tried in order: fewer roof intervals, then a coarser notch arc, then one column.  A
    LOD under its band floor is padded later by author_lod (taper intervals only).
    """
    lod0.validate()
    if lod_triangles(lod0, points) > lod0.band[1]:
        raise ValueError(f"LOD0 is {lod_triangles(lod0, points)} triangles, over {lod0.band}")
    hole1 = math.ceil(lod0.hole_segments / 2) if lod0.has_hole else 0
    bevel1 = math.ceil(lod0.bevel_segments / 2) if lod0.has_bevel else 0
    tip1 = lod0.tip_intervals if lod0.has_bevel else 0
    note1 = "study 4 LOD1: hole ring and bevel segments halved"
    lod1_candidates = []
    for notch in (lod0.notch_segments, max(1, lod0.notch_segments // 2), 1):
        for cols in (max(2, lod0.columns // 2), 1):
            for tip in (tip1, min(tip1, 1)):
                for hole in (hole1, 1 if hole1 else 0):
                    lod1_candidates.append(LodSpec(
                        columns=cols, notch_segments=notch, hole_segments=hole, bevel_segments=bevel1,
                        straight_intervals=1, taper_intervals=max(1, lod0.taper_intervals // 2),
                        tip_intervals=tip, band=LOD1_BAND, note=note1))
    lod1 = _first_fitting(lod1_candidates, points, LOD1_BAND)
    note2 = "study 4 LOD2: bevel and hole dropped"
    lod2_candidates = [
        LodSpec(columns=cols, notch_segments=notch, hole_segments=0, bevel_segments=0,
                straight_intervals=1, taper_intervals=1, tip_intervals=0, band=LOD2_BAND, note=note2)
        for notch, cols in ((lod0.notch_segments, 2), (max(1, lod0.notch_segments // 2), 2), (1, 2), (1, 1))
    ]
    lod2 = _first_fitting(lod2_candidates, points, LOD2_BAND)
    lod0 = replace(lod0, note=lod0.note or "study 4 LOD0: full outline, bevel, hole ring")
    return lod0, lod1, lod2


@dataclass(frozen=True)
class RadialStarSpec:
    """Build-to numbers for a C_n hira-shuriken: parallel-sided arms off a round hub.

    Outline rule (study 2.1, shared by 2.2 / 2.4 / 2.7): parallel-sided arms off a ROUND
    hub, tapering only near the tip, no edge concavity; the notch between arms is the
    hub circle itself, not a vee.  +X points at arm 0 on every form (study 4 pivot rule).
    """

    form: str                       # CLI key, e.g. "four_point"
    mesh_name: str                  # "SM_Shuriken_FourPoint"
    points: int                     # n; the mesh is exactly C_n
    tip_circle_mm: float            # tip-circle diameter (= tip-to-tip across for even n)
    thickness_mm: float
    arm_width_mm: float
    hub_radius_mm: float
    hole_diameter_mm: float         # minimum opening: the hole polygon is circumscribed
    tip_included_deg: float
    bevel_offset_mm: float          # ground facet, perpendicular to the ground edge
    bevel_runout_mm: float          # length over which the facet opens from the shoulder
    mass_target_g: float
    lods: Tuple[LodSpec, ...]
    mass_tolerance_g: float = 2.0
    density_g_cm3: float = 7.85
    grip_angle_deg: Optional[float] = None   # default 180/n: the rim notch between arms 0 and 1
    title: str = ""
    study_section: str = ""
    revision: int = 1
    # UCX hull: "pipeline" = pipeline.make_ucx_hull (convex hull of LOD0, collapse-decimated to
    # <= hull_verts; the four-point's shipped hull), "tip_prism" = the n-gon prism through the
    # tips at full plate thickness (2n vertices, exactly C_n, encloses the mesh by construction
    # - the build refuses it if any LOD0 vertex falls outside).
    hull: str = "pipeline"

    def outline(self) -> "Outline":
        return Outline.from_spec(self)

    def validate(self) -> None:
        if self.points < 2:
            raise ValueError("a radial star needs at least 2 points")
        if not self.mesh_name.startswith("SM_Shuriken_"):
            raise ValueError(f"mesh_name must be SM_Shuriken_<Form> (study 4 naming): {self.mesh_name}")
        if not self.lods:
            raise ValueError("at least LOD0 is required")
        if self.hull not in HULL_METHODS:
            raise ValueError(f"hull must be one of {HULL_METHODS}: {self.hull!r}")
        for level, lod in enumerate(self.lods):
            lod.validate()
            predicted = lod_triangles(lod, self.points)
            if predicted > lod.band[1]:
                raise ValueError(f"{self.mesh_name} LOD{level}: {predicted} triangles predicted, over "
                                 f"its band {lod.band}; reduce its LodSpec counts")
        self.outline().validate(self.lods)


@dataclass(frozen=True)
class Outline:
    """Derived outline in metres.  Arithmetic order matches rev 2 exactly."""

    n: int
    r_tip: float
    thickness: float
    half_t: float
    arm_width: float
    half_w: float
    r_hub: float
    hole_diameter: float
    r_hole: float
    tip_included_deg: float
    half_tip_rad: float
    taper_len: float
    x_taper: float
    arm_half_angle: float
    bevel_offset: float
    bevel_y: float
    bevel_z: float
    bevel_runout: float
    x_runout: float
    x_apex: float
    half_sector: float

    @classmethod
    def from_spec(cls, spec: RadialStarSpec) -> "Outline":
        r_tip = 0.5 * spec.tip_circle_mm * MM
        thickness = spec.thickness_mm * MM
        arm_width = spec.arm_width_mm * MM
        half_w = 0.5 * arm_width
        r_hub = spec.hub_radius_mm * MM
        hole_diameter = spec.hole_diameter_mm * MM
        half_tip_rad = math.radians(0.5 * spec.tip_included_deg)
        taper_len = half_w / math.tan(half_tip_rad)
        x_taper = r_tip - taper_len
        bevel_offset = spec.bevel_offset_mm * MM
        # The offset is perpendicular to the ground edge, which leans half the tip angle
        # off x, so its y component is offset / cos(half tip angle).
        bevel_y = bevel_offset / math.cos(half_tip_rad)
        bevel_runout = spec.bevel_runout_mm * MM
        return cls(
            n=spec.points,
            r_tip=r_tip,
            thickness=thickness,
            half_t=0.5 * thickness,
            arm_width=arm_width,
            half_w=half_w,
            r_hub=r_hub,
            hole_diameter=hole_diameter,
            r_hole=0.5 * hole_diameter,
            tip_included_deg=spec.tip_included_deg,
            half_tip_rad=half_tip_rad,
            taper_len=taper_len,
            x_taper=x_taper,
            arm_half_angle=math.asin(half_w / r_hub) if half_w < r_hub else float("nan"),
            bevel_offset=bevel_offset,
            bevel_y=bevel_y,
            bevel_z=bevel_offset,
            bevel_runout=bevel_runout,
            x_runout=x_taper + bevel_runout,
            # Past x_apex the arm is narrower than the facet, so the two facets meet in a ridge.
            x_apex=r_tip - bevel_y / math.tan(half_tip_rad),
            half_sector=math.pi / spec.points,
        )

    @property
    def sector(self) -> float:
        return 2.0 * self.half_sector

    def hole_polygon_radius(self, hole_total: int) -> float:
        """Circumscribed hole polygon, so the *minimum* opening is the stated diameter."""
        return self.r_hole / math.cos(math.pi / hole_total)

    def half_width(self, x: float) -> float:
        """Half width of the arm at ``x``: parallel-sided, tapering only near the tip."""
        if x <= self.x_taper:
            return self.half_w
        return max(0.0, (self.r_tip - x) * math.tan(self.half_tip_rad))

    def validate(self, lods) -> None:
        mm = lambda v: f"{v / MM:.3f} mm"  # noqa: E731
        if not self.half_w < self.r_hub:
            raise ValueError(f"arm half width {mm(self.half_w)} must be below the hub radius {mm(self.r_hub)}")
        if not self.arm_half_angle < self.half_sector:
            raise ValueError(
                f"arms overlap at the hub: each arm needs {math.degrees(2 * self.arm_half_angle):.2f} deg "
                f"of a {math.degrees(self.sector):.2f} deg sector; raise the hub radius above "
                f"{mm(self.half_w / math.sin(self.half_sector))} or narrow the arm")
        if not self.r_hub < self.x_taper:
            raise ValueError(f"no parallel run: the taper starts at {mm(self.x_taper)}, inside the hub")
        if not 0.0 < self.r_hole < self.r_hub:
            raise ValueError("hole must be smaller than the hub")
        if not self.bevel_z < self.half_t:
            raise ValueError(f"bevel offset {mm(self.bevel_z)} must be below half the thickness {mm(self.half_t)}")
        if not self.x_taper < self.x_runout < self.x_apex < self.r_tip:
            raise ValueError(
                f"bevel stations out of order: shoulder {mm(self.x_taper)}, run-out {mm(self.x_runout)}, "
                f"apex {mm(self.x_apex)}, tip {mm(self.r_tip)}")
        for level, lod in enumerate(lods):
            if lod.has_hole:
                total = lod.hole_segments * self.n
                if self.hole_polygon_radius(total) >= self.r_hub:
                    raise ValueError(f"LOD{level}: hole polygon reaches the hub")

    def tip_extents(self):
        """(span_x, span_y) of the tip circle points, exact for quarter-turn forms."""
        xs, ys = [], []
        for k in range(self.n):
            x, y = rotate(k, self.n, self.r_tip, 0.0)
            xs.append(x)
            ys.append(y)
        return max(xs) - min(xs), max(ys) - min(ys)


# =========================================================================== analytic area


def analytic_area(spec: RadialStarSpec, lod: Optional[LodSpec] = None) -> dict:
    """Exact plan area of the UN-bevelled outline, term by term, in mm2 (pure Python).

    This is the number a study cross-check should quote.  Hub disc minus the round hole,
    plus n arms; each arm is

    * the parallel run OUTSIDE the hub circle: the strip |y| <= w/2 from the hub arc out
      to the shoulder, i.e. ``w * x_taper`` minus the circular cap
      ``integral_{-w/2}^{w/2} sqrt(r^2 - y^2) dy = (w/2) sqrt(r^2 - w^2/4) + r^2 asin(w/2r)``;
    * plus the taper triangle ``(w/2) * L``, ``L = (w/2) / tan(tip/2)``.

    ``arms_from_hub_radius_mm2`` is what the sum gives when each run is counted from the
    line x = r (a plain rectangle ``w * (x_taper - r)``) instead of from the hub arc: that
    drops n circular slivers of ``w r - cap`` each.  It is the slip behind study 2.1's
    first 1647 mm2 (corrected to 1668) and behind study 2.2's 3055 mm2.

    With ``lod`` the polygonised figure the generator authors is added: each notch arc
    becomes chords (a chord of angle phi loses ``r^2 (phi - sin phi) / 2``) and the hole
    becomes the circumscribed m-gon (``m r_h^2 tan(pi/m)``).  The arm-root arc is interior
    (hub fan and arm row share its chords), so it costs nothing.  What the ground bevel
    removes is not in any of these figures: that is a volume, measured on the mesh.
    """
    n = spec.points
    r_tip = 0.5 * spec.tip_circle_mm
    w = spec.arm_width_mm
    h = 0.5 * w
    r = spec.hub_radius_mm
    r_h = 0.5 * spec.hole_diameter_mm
    half_tip = math.radians(0.5 * spec.tip_included_deg)
    taper_len = h / math.tan(half_tip)
    x_taper = r_tip - taper_len
    cap = h * math.sqrt(r * r - h * h) + r * r * math.asin(h / r)
    run = w * x_taper - cap
    triangle = h * taper_len
    hub = math.pi * r * r
    hole = math.pi * r_h * r_h
    exact = hub - hole + n * (run + triangle)
    sliver = w * r - cap
    out = {
        "units": "mm2",
        "points": n,
        "hub_disc": hub,
        "hole_disc": hole,
        "hub_minus_hole": hub - hole,
        "arm_parallel_run_outside_hub": run,
        "arm_rectangle_to_shoulder": w * x_taper,
        "arm_circular_cap_inside_hub": cap,
        "arm_taper_triangle": triangle,
        "arm_total": run + triangle,
        "arms_total": n * (run + triangle),
        "taper_len_mm": taper_len,
        "x_taper_mm": x_taper,
        "exact": exact,
        "root_sliver_per_arm": sliver,
        "arms_from_hub_radius_mm2": exact - n * sliver,
        "arm_angle_at_hub_deg": 2.0 * math.degrees(math.asin(h / r)),
        "clear_hub_per_sector_deg": 360.0 / n - 2.0 * math.degrees(math.asin(h / r)),
    }
    if lod is not None:
        phi = (math.pi / n - math.asin(h / r)) / lod.notch_segments
        chords = 2 * lod.notch_segments * n
        notch_loss = chords * 0.5 * r * r * (phi - math.sin(phi))
        m = lod.hole_segments * n
        hole_poly = m * r_h * r_h * math.tan(math.pi / m) if m else 0.0
        hole_excess = hole_poly - hole if m else -hole
        out.update({
            "polygon_notch_chords": chords,
            "polygon_notch_chord_loss": notch_loss,
            "polygon_hole_segments": m,
            "polygon_hole_area": hole_poly,
            "polygon_hole_excess": hole_excess,
            "polygonised": exact - notch_loss - hole_excess,
        })
    return out


def numeric_outline_area(spec: RadialStarSpec, samples: int = 4096) -> float:
    """Shoelace area (mm2) of a finely sampled outline minus a finely sampled hole.

    An independent check on ``analytic_area``'s formula: no integral, no cap term, just the
    boundary walked point by point (``samples`` points per edge piece, per wedge).
    """
    n = spec.points
    r_tip = 0.5 * spec.tip_circle_mm
    h = 0.5 * spec.arm_width_mm
    r = spec.hub_radius_mm
    half_tip = math.radians(0.5 * spec.tip_included_deg)
    x_taper = r_tip - h / math.tan(half_tip)
    x_root = math.sqrt(r * r - h * h)
    arm_half = math.asin(h / r)
    half_sector = math.pi / n
    m = samples
    wedge = []
    for i in range(m):                    # lower half notch, up to the arm edge
        a = -half_sector + (half_sector - arm_half) * i / m
        wedge.append((r * math.cos(a), r * math.sin(a)))
    for i in range(m):                    # lower arm edge, root to shoulder
        wedge.append((x_root + (x_taper - x_root) * i / m, -h))
    for i in range(m):                    # lower taper edge to the point
        wedge.append((x_taper + (r_tip - x_taper) * i / m, -h * (1.0 - i / m)))
    for i in range(m):                    # upper taper edge back to the shoulder
        wedge.append((r_tip - (r_tip - x_taper) * i / m, h * i / m))
    for i in range(m):                    # upper arm edge back to the root
        wedge.append((x_taper - (x_taper - x_root) * i / m, h))
    for i in range(m):                    # upper half notch
        a = arm_half + (half_sector - arm_half) * i / m
        wedge.append((r * math.cos(a), r * math.sin(a)))
    points = []
    for k in range(n):
        c, s = math.cos(2.0 * math.pi * k / n), math.sin(2.0 * math.pi * k / n)
        points += [(c * x - s * y, s * x + c * y) for x, y in wedge]
    twice = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        twice += x1 * y2 - x2 * y1
    hole_m = 6 * m * n
    r_h = 0.5 * spec.hole_diameter_mm
    hole = 0.5 * hole_m * r_h * r_h * math.sin(2.0 * math.pi / hole_m)
    return abs(twice) * 0.5 - hole
