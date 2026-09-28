#!/usr/bin/env python
"""props_lib.spec - the build-to numbers for a flat printed prop, and the paper bomb's own.

Pure Python: no bpy, no numpy.  A Blender build script, a pure-Python calculator and the
Unreal verifier all read the SAME object, so nothing is typed twice.

FRAME (study 3, "build_to.frame").  The card lies in the XY plane.

    +X  is the TOP of the tag          +Y  is the LEFT of the printed face seen from +Z
    +Z  comes out of the printed FRONT face

which matches the pack (shuriken plates in XY with +Z presented, the kunai's long axis on
+X).  Export is Forward -Y / Up Z like every other file in the pack.

PAPER COORDINATES.  Everything about the artwork is authored in *card millimetres*
``(u, v)``: ``u`` from the left edge of the printed face seen from +Z, ``v`` from the top.
``props_lib.paperbomb_art`` draws in exactly those coordinates.  The study's conversion,
which ``paper_to_world`` implements for the undeformed sheet, is::

    X_mm = (0.5 - v/H) * H = H/2 - v          Y_mm = (0.5 - u/W) * W = W/2 - u

The pivot is the card MID-SURFACE at the plan centre (the pack's centre-of-mass
convention; study open question 4).  The front plane is +0.075 mm from it and the back
plane -0.075 mm.

LOD SCREEN SIZES.  The pack rule is ``shuriken_lib.spec.LOD_SCREEN_SIZES`` (1.0 / 0.10 /
0.035) scaled by the bounds radius over 50 mm.  That library is frozen and read-only, so
the constants are restated here and ``scaled_lod_screen_sizes`` reproduces it exactly;
``props_lib.measure.check_pack_lod_rule`` imports shuriken_lib and asserts the two agree.

THE DENY GATE.  ``Scripts/pipeline/qa_check.py`` is used as it is and its DENY_SUBSTRINGS
holds only four words, so this line adds its own, wider list over every name the build
emits.  See ``props_lib.paperbomb_art.DENY_SUBSTRINGS`` - the same tuple, kept in one
place there because the art module is the one that must never emit a franchise word into
a texture name either.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- pack rules

#: shuriken_lib.spec.LOD_SCREEN_SIZES, restated (that module is frozen).
PACK_LOD_SCREEN_SIZES: Tuple[float, float, float] = (1.0, 0.10, 0.035)
#: shuriken_lib.spec.LOD_REFERENCE_RADIUS_MM.
PACK_LOD_REFERENCE_RADIUS_MM = 50.0
#: shuriken_lib.spec.REFERENCE_HFOV_DEG / REFERENCE_ASPECT, for the switch distances.
REFERENCE_HFOV_DEG = 90.0
REFERENCE_ASPECT = 16.0 / 9.0

#: ASSET_GUIDELINES: props author at 2K; 4K is reserved for hero and skin.
PROP_TEXTURE_SIZE = 2048
#: ASSET_GUIDELINES 4 / study 3.4: 16 px of padding at 2K, EXTEND margin.
BAKE_MARGIN_PX = 16
#: ASSET_GUIDELINES: a prop sits in 1,000 - 5,000 triangles.
PROP_TRIANGLE_BUDGET = (1000, 5000)


def scaled_lod_screen_sizes(radius_mm: float,
                            sizes: Sequence[float] = PACK_LOD_SCREEN_SIZES,
                            reference_mm: float = PACK_LOD_REFERENCE_RADIUS_MM) -> List[float]:
    """The pack rule: LOD0 always 1.0, the rest scaled by ``radius_mm / reference_mm``."""
    factor = float(radius_mm) / float(reference_mm)
    return [1.0] + [round(float(s) * factor, 4) for s in sizes[1:]]


def screen_size_distance_m(screen_size: float, radius_m: float,
                           hfov_deg: float = REFERENCE_HFOV_DEG,
                           aspect: float = REFERENCE_ASPECT) -> float:
    """Distance at which a sphere of ``radius_m`` projects to ``screen_size`` of the frame.

    Unreal's screen size is the projected DIAMETER as a fraction of the smaller frame
    dimension; the pack's figure is taken at 90 deg horizontal FOV on 16:9.
    """
    if screen_size <= 0.0:
        return float("inf")
    half_v = math.atan(math.tan(math.radians(hfov_deg) * 0.5) / aspect)
    return radius_m / (screen_size * math.tan(half_v))


# --------------------------------------------------------------------------- the sheet


@dataclass(frozen=True)
class FoldSpec:
    """One soft crease running across the sheet at ``v_mm`` from the top."""

    v_mm: float
    #: Total turn at the crease, degrees.
    #:
    #: The first build shipped 3 deg over a 3.5 mm half width, reconciling the study's
    #: dihedral 175 with its own 2.6 mm Z bound, and the result was measurable and
    #: invisible: 0.43 deg of turn per millimetre throws no shadow, 62 mm of the card
    #: came out Z-identical to three decimals, and the AO bake found nothing to
    #: occlude.  A buyer pays for a paper prop instead of a decal plane precisely for
    #: the deformation, so the creases are now 7 deg over a 2.2 mm half width - 1.6 deg
    #: per millimetre, which does throw a shading line - and the study's 2.6 mm Z
    #: figure is corrected in the study text rather than defended.  The bounds radius
    #: is unmoved to three decimals (Z contributes ~30 mm2 against 7,300), so the LOD
    #: screen sizes are still exactly the pack's.
    turn_deg: float
    #: half-width of the smoothed crease in mm.  The study's 0.5 mm fold radius is a
    #: KNIFE edge at this scale: the whole turn lands in a 1 mm band and a point 35 mm
    #: out on the curl slides along the sheet inside it.  2.2 mm is the tightest crease
    #: that keeps the measured skin UV stretch inside +-8 % once the curl is deep
    #: enough to read - see ``CurlSpec.crease_relief``, which is what pays for it.
    half_width_mm: float = 2.2
    #: the crease is not straight: it wanders this far across the width (study 6).
    wander_mm: float = 1.5


@dataclass(frozen=True)
class CurlSpec:
    """A cylindrical curl about the LONG axis: the sheet cups across its width.

    Sagitta is measured at the card's side edge.  The study's mechanism is sourced (a
    printed sheet curls toward the side that dries last, i.e. toward its printed face),
    so the printed face is CONCAVE and the side edges rise toward +Z.
    """

    #: The study's estimate was 2.0 mm, and at 2.0 mm over a 70 mm width the card read
    #: as flat in every gallery shot.  4.2 mm (R ~146 mm) is a cup you can see from the
    #: end of the tag and still a sheet rather than a tube.  ESTIMATE, like the study's,
    #: decided by looking at the hero render.
    sagitta_mm: float = 4.2
    #: the curl tightens over the last ``deepen_run_mm`` at the bottom end
    deepen_sagitta_mm: float = 6.0
    deepen_run_mm: float = 40.0
    #: How much of the curl RELAXES at each crease, 0 - 1.
    #:
    #: This is physics, not a fudge.  A cupped sheet cannot be folded across its cup
    #: without straining: the surface metric picks up a factor ``(1 - lift * dtheta/dv)``
    #: along the sheet, so at 4.2 mm of lift and a 7 deg crease the card edge would
    #: compress by a quarter.  Real paper pops the curl out where it creases, and so
    #: does this: the curvature is scaled down toward the crease over a long, smooth
    #: ramp (a short one would trade the stretch for a ``d(lift)/dv`` term just as big).
    crease_relief: float = 0.62
    crease_relief_sigma_mm: float = 13.0
    #: A gentle whole-length bow on top of the creases, so the panels between them are
    #: not rigid planes.  The first build measured Z bit-identical across five
    #: consecutive 8 mm bins; a sheet of paper is never that flat.
    bow_deg: float = 1.15
    bow_cycles: float = 1.0

    def radius_for_sagitta(self, half_width_mm: float, sagitta_mm: float) -> float:
        """Solve R from ``s = R (1 - cos(h/R))`` by Newton; h is the half width."""
        h = float(half_width_mm)
        s = float(sagitta_mm)
        if s <= 1e-9:
            return 1e9
        r = h * h / (2.0 * s)                       # parabolic first guess
        for _ in range(60):
            f = r * (1.0 - math.cos(h / r)) - s
            # d/dr [ r - r cos(h/r) ] = 1 - cos(h/r) - (h/r) sin(h/r)
            d = 1.0 - math.cos(h / r) - (h / r) * math.sin(h / r)
            if abs(d) < 1e-15:
                break
            step = f / d
            r -= step
            if abs(step) < 1e-12:
                break
        return r


# THE DOG-EAR, THE NICK AND THE TORN EDGE ARE GONE, AND THIS IS WHY.
#
# ``DogEarSpec`` used to live here, beside a ``nick_v_mm`` on the card and a
# ``tear_lobes`` on every LOD.  All three were the STUDY's invention, never the
# reference's.  Re-measuring the reference of record
# (``References/PaperBomb/paperbomb_guide_v2_real_glyphs.png``, the file the user
# named) fitted its four straight edges sub-pixel and its four bevels independently
# and compared 1 820 boundary samples against the resulting octagon: worst deviation
# +0.78 / -0.72 px (+-0.2 mm), and ZERO samples on any side more than 1.5 px inboard.
# A 12 mm dog-ear, a 5 mm nick or a 16 mm torn edge would each show as tens of samples
# 20-60 px inboard.  None exists.  The user's own report - "the bottom right edge of
# the tag looks not correct, its like burned off or cut short" - was the dog-ear.
#
# The sheet is still a PHYSICAL sheet: the curl and the two creases stay, because they
# are shading and they do not move the outline.  ``measure.silhouette_octagon`` is the
# gate that keeps it that way.


@dataclass(frozen=True)
class SocketSpec:
    name: str
    #: position in WORLD millimetres (study 3, "build_to.sockets")
    position_mm: Tuple[float, float, float]
    #: rotation the socket should report in Unreal, as a Blender XYZ euler in degrees
    rotation_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    use: str = ""
    #: when set, the build snaps the socket onto the real deformed surface at this paper
    #: coordinate and records how far it moved
    snap_paper_uv: Optional[Tuple[float, float]] = None
    snap_side: str = "front"


@dataclass(frozen=True)
class LodSpec:
    """One LOD's tessellation.  No Decimate anywhere: every LOD is generated."""

    level: int
    columns: int
    rows: int
    #: keep the two creases
    folds: bool
    band: Tuple[int, int]
    target: int


@dataclass(frozen=True)
class CardSpec:
    """Everything the geometry, the UVs, the bake and the report need."""

    name: str = "PaperBomb"
    mesh_name: str = "SM_PaperBomb"
    material_name: str = "M_PaperBomb"
    texture_stem: str = "T_PaperBomb"

    width_mm: float = 70.0
    #: REFERENCE_SPEC row S1.  The reference of record's tag measures 274.189 x 635.673
    #: px, aspect W/H **0.43134** (stable to 0.36 % over a 0.25 - 0.80 threshold sweep).
    #: The older, higher-resolution guide is 0.4468 - the real-glyph file is a
    #: non-uniform VERTICAL stretch of it, corroborated by its two bottom bevels fitting
    #: at 46.2 and 46.6 deg where a true 45 deg cut stretched 3.6 % would read 46.1.
    #: The user named the real-glyph file, so the proportion comes from it.  Width stays
    #: the product decision at 70.0 mm and the height moves: 70.0 / 0.43134 = 162.29 mm,
    #: +4.03 % on the 156.0 this shipped at.  ONE LINE, and every vertical fraction in
    #: ``paperbomb_art.Layout`` follows it without being touched, because they are all
    #: fractions of H.  ``card_h_mm`` below is a read-only alias, so there is exactly one
    #: place to change and no second field that can silently disagree with this one.
    height_mm: float = 162.29
    thickness_mm: float = 0.15
    #: REFERENCE_SPEC rows S3/S4.  On the reference of record the four bevels were fitted
    #: independently and intersected with the four straight edges: horizontal legs
    #: 7.71 / 7.82 / 8.18 / 8.21 mm (mean 7.98), vertical legs 7.71 / 7.80 / 8.53 / 8.66
    #: (mean 8.18) - the two BOTTOM corners really are cut a little larger, which is the
    #: same 3.6 % vertical stretch that moved the aspect.  A single 45 deg clip that sits
    #: inside both means is 8.05 mm, which is 0.07 under the horizontal mean and 0.13
    #: under the vertical one, both well inside the +-0.35 mm the rows allow.
    #: ``paperbomb_art.CORNER_CLIP_MM`` carries the same number and
    #: ``measure.corner_clip_agrees`` is the gate that they have not drifted apart.
    corner_clip_mm: float = 8.05

    grammage_g_per_m2: float = 80.0

    curl: CurlSpec = field(default_factory=CurlSpec)
    #: at H/3 and 2H/3, which is where ``paperbomb_art.Layout.crease_y`` puts them
    #: (0.333, 0.667).  They moved with the card: 52.0 / 104.0 on the 156 mm sheet.
    folds: Tuple[FoldSpec, ...] = (FoldSpec(54.04, 7.0), FoldSpec(108.25, -7.0))

    texture_size: int = PROP_TEXTURE_SIZE
    #: The hard 2048 ceiling for the LONG side, once 16 px of bake padding is taken off
    #: each end: ``(2048 - 32) / height_mm``.  It was 12.923 on the 156 mm card; the
    #: card is now 162.29 mm (REFERENCE_SPEC row S1), so 2016 / 162.29 = 12.4222 and the
    #: island still lands on exactly 2016 px with exactly 16 px of padding either side.
    #: This is a 3.9 % drop in texel density - 124.2 px/cm against 129.2 - which is a
    #: consequence of matching the reference's proportion, not a choice, and it is still
    #: far above the pack's own props figure.  Raising it would push the art raster past
    #: 2048 and ``atlas.compose`` would refuse the blit.
    ppmm: float = 12.4222

    #: ORM AO is a real Cycles bake; this is its sample count
    ao_samples: int = 192

    # With the three damage features gone there is nothing left on the boundary that
    # needs refining: the outline is eight straight runs, so the only thing the grid has
    # to carry is the corner clip and the crease shoulders.  The LOD ladder is now pure
    # tessellation of the curl, and the counts are set from the grid rather than from a
    # refinement budget.  The bands are the study's, unchanged.
    lods: Tuple[LodSpec, ...] = (
        LodSpec(0, columns=11, rows=23, folds=True, band=(1000, 1600), target=1150),
        LodSpec(1, columns=5, rows=9, folds=True, band=(350, 650), target=420),
        LodSpec(2, columns=3, rows=5, folds=False, band=(100, 240), target=200),
    )

    sockets: Tuple[SocketSpec, ...] = (
        # NOT "lay flat on a surface": the shipped card curls and creases through
        # several millimetres of Z, so a tag resting on a floor rests on its curl, not
        # on its plan centre.  Face is the decal/glow anchor on the printed side; the
        # study's open question 4 was written for a nearly flat card and is answered in
        # the study text.  Every paper coordinate below moved with the card's new
        # height: the plan centre is 81.145 mm from the top, not 78.0.
        SocketSpec("Face", (0.0, 0.0, 0.075), (0.0, 0.0, 0.0),
                   "decal, glow and VFX anchor on the printed face (the tag rests on "
                   "its curl, not on this point)", (35.0, 81.145), "front"),
        SocketSpec("Attach", (0.0, 0.0, -0.075), (180.0, 0.0, 0.0),
                   "stick to a wall, glue to a crate, parent to a kunai",
                   (35.0, 81.145), "back"),
        # the emblem, at Layout.fuse_point = (0.500, 0.196) of the card
        SocketSpec("Fuse", (49.33, 0.0, 0.075), (0.0, 0.0, 0.0),
                   "spark and burn VFX start; the _M green scorch gradient radiates from here",
                   (35.0, 31.81), "front"),
        # Cord's forward axis is +X, OUT OF THE TOP, exactly as the study's socket
        # table says and exactly like Fuse and like all four of the kunai's sockets.
        # It shipped as a Blender Y-euler of +90, which Unreal read as pitch -90 and a
        # forward vector of (0, 0, -1) - out of the BACK of the card - so anything
        # parented at Cord arrived rotated ninety degrees from what the study promised.
        # The dry-fit against the kunai's Ring socket, which the first build deferred,
        # is the test that catches this and it now runs in the build.
        SocketSpec("Cord", (81.145, 0.0, 0.0), (0.0, 0.0, 0.0),
                   "ties to the kunai's Ring socket at (-103.5, 0, 0) mm; also a fuse cord",
                   (35.0, 0.0), "mid"),
    )

    #: study 3, "build_to.collision"
    hull_inflate_mm: float = 1.5
    hull_sides: int = 12

    # ---- derived ---------------------------------------------------------

    @property
    def card_h_mm(self) -> float:
        """Read-only alias for ``height_mm`` - the one-line aspect knob, by its spec name."""
        return self.height_mm

    @property
    def card_aspect(self) -> float:
        """W / H.  REFERENCE_SPEC row S1 measures the reference at 0.43134 +-0.0016."""
        return self.width_mm / self.height_mm

    @property
    def half_thickness_mm(self) -> float:
        return self.thickness_mm * 0.5

    @property
    def plan_area_mm2(self) -> float:
        """Card box less the four 45 deg corner triangles."""
        c = self.corner_clip_mm
        return self.width_mm * self.height_mm - 4 * 0.5 * c * c

    @property
    def mass_g(self) -> float:
        return self.plan_area_mm2 * 1e-6 * self.grammage_g_per_m2

    def curl_radius_mm(self, sagitta_mm: Optional[float] = None) -> float:
        s = self.curl.sagitta_mm if sagitta_mm is None else sagitta_mm
        return self.curl.radius_for_sagitta(self.width_mm * 0.5, s)

    @property
    def bounds_radius_mm(self) -> float:
        """Unreal's bounds sphere radius: the far corner of the box the mesh occupies.

        The study quotes 85.5 mm from a (70, 156, 2.6) box.  The build re-measures the
        real box and ``props_lib.measure`` reports both.  The Z half-extent was 5.6 mm
        when the dog-ear stood 105 deg out of plane; with the flap gone the card's own
        curl and creases reach about 4 mm, and 4.5 is kept as the conservative figure -
        it contributes 0.11 mm to a 88.5 mm radius, so the LOD screen sizes do not care.
        """
        half = (self.width_mm * 0.5, self.height_mm * 0.5, 4.5)
        return math.sqrt(sum(h * h for h in half))

    def lod_screen_sizes(self, radius_mm: Optional[float] = None) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm if radius_mm is not None else self.bounds_radius_mm)

    def switch_distances_m(self, radius_mm: Optional[float] = None) -> List[float]:
        r = (radius_mm if radius_mm is not None else self.bounds_radius_mm) / 1000.0
        return [round(screen_size_distance_m(s, r), 4) for s in self.lod_screen_sizes()[1:]]

    def texel_density_px_per_cm(self) -> float:
        return self.ppmm * 10.0

    def hull_name(self, lod0_node: str) -> str:
        """``UCX_<render mesh NODE name>_00``.

        The node is ``SM_PaperBomb_LOD0`` once ``make_lod_group`` has renamed it, so the
        hull must be ``UCX_SM_PaperBomb_LOD0_00``.  ``UCX_SM_PaperBomb_00`` on that node
        imports with convex count 0 and NO collision at all, silently (study 3).
        """
        return f"UCX_{lod0_node}_00"


PAPER_BOMB = CardSpec()


# --------------------------------------------------------------------------- deny gate

#: Wider than Scripts/pipeline/qa_check.py's DENY_SUBSTRINGS, which is used as it is.
DENY_SUBSTRINGS: Tuple[str, ...] = (
    "naruto", "kibaku", "kibakufuda", "uzumaki", "konoha", "shippuden", "boruto",
    "akatsuki", "hidden leaf", "explosive tag", "exploding tag",
)


def deny_hits(*values: Optional[str]) -> List[str]:
    """Every forbidden substring found in ``values`` (case-insensitive)."""
    hits: List[str] = []
    for value in values:
        if not value:
            continue
        low = str(value).lower()
        hits.extend(f"{word!r} in {value!r}" for word in DENY_SUBSTRINGS if word in low)
    return hits


def assert_clean(*values: Optional[str]) -> None:
    hits = deny_hits(*values)
    if hits:
        raise ValueError("franchise vocabulary in a shipped name: " + "; ".join(hits))


def build_to() -> Dict[str, object]:
    """The spec as plain data, for the report and the Unreal verifier."""
    s = PAPER_BOMB
    radius = s.bounds_radius_mm
    return {
        "name": s.name,
        "mesh": s.mesh_name,
        "material": s.material_name,
        "textures": [f"{s.texture_stem}_{k}" for k in ("BC", "ORM", "N", "M")],
        "card_mm": [s.width_mm, s.height_mm, s.thickness_mm],
        "card_aspect_w_over_h": round(s.card_aspect, 5),
        "corner_clip_mm": s.corner_clip_mm,
        "silhouette": "clean octagon - four straight sides, four straight 45 deg "
                      "chamfers; no tear, no nick, no dog-ear (REFERENCE_SPEC section 1)",
        "plan_area_mm2": round(s.plan_area_mm2, 3),
        "mass_g": round(s.mass_g, 4),
        "curl": {"sagitta_mm": s.curl.sagitta_mm, "radius_mm": round(s.curl_radius_mm(), 2),
                 "deepen_sagitta_mm": s.curl.deepen_sagitta_mm,
                 "deepen_radius_mm": round(s.curl_radius_mm(s.curl.deepen_sagitta_mm), 2),
                 "deepen_run_mm": s.curl.deepen_run_mm},
        "folds": [{"v_mm": f.v_mm, "turn_deg": f.turn_deg, "half_width_mm": f.half_width_mm,
                   "wander_mm": f.wander_mm} for f in s.folds],
        "bounds_radius_mm": round(radius, 3),
        "lod_screen_sizes": s.lod_screen_sizes(),
        "switch_distances_m": s.switch_distances_m(),
        "lod_bands": [list(l.band) for l in s.lods],
        "lod_targets": [l.target for l in s.lods],
        "texture_size": s.texture_size,
        "texel_density_px_per_cm": round(s.texel_density_px_per_cm(), 3),
        "sockets": [{"name": k.name, "position_mm": list(k.position_mm),
                     "rotation_deg": list(k.rotation_deg), "use": k.use} for k in s.sockets],
    }


__all__ = ["CardSpec", "CurlSpec", "FoldSpec", "LodSpec", "SocketSpec",
           "PAPER_BOMB", "DENY_SUBSTRINGS", "assert_clean", "build_to", "deny_hits",
           "scaled_lod_screen_sizes", "screen_size_distance_m", "BAKE_MARGIN_PX",
           "PROP_TEXTURE_SIZE", "PROP_TRIANGLE_BUDGET"]


if __name__ == "__main__":                                   # pragma: no cover
    import json
    print(json.dumps(build_to(), indent=2))
