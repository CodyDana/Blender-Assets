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


@dataclass(frozen=True)
class DogEarSpec:
    """A turned-back corner.

    ``fold_back_deg`` is the angle the flap is turned OUT OF THE PLANE, not a dihedral.
    A flat 180 deg fold would lie on the back face (z-fighting at 0.15 mm), hide 70 mm2
    of print and read as a doubled edge; the first build read the study's 25 deg
    literally and got a corner that is invisible in all six gallery shots.  105 deg is
    a corner that has been folded over and sprung part way back: it breaks the
    silhouette, throws a real shadow, gives the AO bake something to find, and never
    comes within 4 mm of the back face.  OURS, and the study's 25 deg is corrected.
    """

    #: "bottom right" of the PRINTED FACE seen from +Z, i.e. u -> W, v -> H.
    #: The study says 12 mm.  15.2 mm is TWICE THE CORNER CLIP, which is what makes the
    #: crease an exact cell diagonal at every LOD: the grid always carries lines at the
    #: clip, and the cells between the clip line and the 2c line are square, so the
    #: 45 deg crease falls on two cell diagonals with no extra grid lines anywhere.  At
    #: 12 mm it would need a 3.8 mm sub-grid through the whole card - about 270 extra
    #: triangles - to say the same thing.  OURS, with the reason.
    leg_mm: float = 15.2
    fold_back_deg: float = 105.0
    #: The crease is softened over this distance so the flap is bent, not kinked.
    soften_mm: float = 2.2


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
    #: extra boundary points per millimetre inside the torn stretch and the nick
    tear_refine_per_mm: float
    #: keep the two creases, the dog-ear, the nick
    folds: bool
    dog_ear: bool
    nick: bool
    #: how many lobes of the tear survive (LOD2 ships a straight edge)
    tear_lobes: Optional[int]
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
    height_mm: float = 156.0
    thickness_mm: float = 0.15
    #: REFERENCE_SPEC row 23 / worklist 21, and correction 4 in its section 5: fitting a
    #: line to the bevel itself and intersecting it with the two straight edges gives
    #: 8.10 mm on V1 and 7.97 on V2, matching the ink pass's 8.09 / 7.96 independently.
    #: The 7.6 this shipped at came from a departure-threshold method that under-measures
    #: with a coarse tolerance.  ``paperbomb_art.CORNER_CLIP_MM`` carries the same number
    #: and ``measure.corner_clip_agrees`` is the gate that they have not drifted apart.
    corner_clip_mm: float = 8.05

    grammage_g_per_m2: float = 80.0

    curl: CurlSpec = field(default_factory=CurlSpec)
    folds: Tuple[FoldSpec, ...] = (FoldSpec(52.0, 7.0), FoldSpec(104.0, -7.0))
    dog_ear: DogEarSpec = field(default_factory=DogEarSpec)
    #: study 6: a 5 mm nick bitten out of the right edge at y 0.62 of the card
    nick_v_mm: float = 0.62 * 156.0

    texture_size: int = PROP_TEXTURE_SIZE
    ppmm: float = 12.923                     # study 7: the hard 2048 ceiling for a 156 mm side

    #: ORM AO is a real Cycles bake; this is its sample count
    ao_samples: int = 192

    lods: Tuple[LodSpec, ...] = (
        # tear_refine_per_mm 0.95 -> 2.6: at 0.95 the 16 mm torn stretch carried 14
        # boundary points, so at most 7 of the study's 6 - 12 lobes were representable
        # and only 3 - 4 resolved - the edge read as a die-cut sawtooth.  2.6/mm is
        # ~40 points, three per lobe, for about 50 triangles inside a 1000 - 1600 band.
        LodSpec(0, columns=11, rows=22, tear_refine_per_mm=2.60, folds=True, dog_ear=True,
                nick=True, tear_lobes=None, band=(1000, 1600), target=1150),
        LodSpec(1, columns=5, rows=8, tear_refine_per_mm=0.55, folds=True, dog_ear=True,
                nick=True, tear_lobes=4, band=(350, 650), target=420),
        # The study's LOD2 content says "no dog-ear".  That was written when the
        # fold was 25 deg out of plane and invisible; at 105 deg the flap is a real
        # 15 mm feature and dropping it costs 6.2 mm of Hausdorff and a visible
        # silhouette pop at the switch.  KEPT, as a deliberate departure - the extra
        # cost is a handful of triangles inside a 100 - 200 band.
        LodSpec(2, columns=3, rows=4, tear_refine_per_mm=0.0, folds=False, dog_ear=True,
                nick=False, tear_lobes=0, band=(100, 240), target=200),
    )

    sockets: Tuple[SocketSpec, ...] = (
        # NOT "lay flat on a surface": the shipped card curls and creases through
        # about 11 mm of Z, so a tag resting on a floor rests on its curl and its
        # dog-ear, not on its plan centre.  Face is the decal/glow anchor on the
        # printed side; the study's open question 4 was written for a nearly flat card
        # and is answered in the study text.
        SocketSpec("Face", (0.0, 0.0, 0.075), (0.0, 0.0, 0.0),
                   "decal, glow and VFX anchor on the printed face (the tag rests on "
                   "its curl, not on this point)", (35.0, 78.0), "front"),
        SocketSpec("Attach", (0.0, 0.0, -0.075), (180.0, 0.0, 0.0),
                   "stick to a wall, glue to a crate, parent to a kunai", (35.0, 78.0), "back"),
        SocketSpec("Fuse", (47.4, 0.0, 0.075), (0.0, 0.0, 0.0),
                   "spark and burn VFX start; the _M green scorch gradient radiates from here",
                   (35.0, 30.6), "front"),
        # Cord's forward axis is +X, OUT OF THE TOP, exactly as the study's socket
        # table says and exactly like Fuse and like all four of the kunai's sockets.
        # It shipped as a Blender Y-euler of +90, which Unreal read as pitch -90 and a
        # forward vector of (0, 0, -1) - out of the BACK of the card - so anything
        # parented at Cord arrived rotated ninety degrees from what the study promised.
        # The dry-fit against the kunai's Ring socket, which the first build deferred,
        # is the test that catches this and it now runs in the build.
        SocketSpec("Cord", (78.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                   "ties to the kunai's Ring socket at (-103.5, 0, 0) mm; also a fuse cord",
                   (35.0, 0.0), "mid"),
    )

    #: study 3, "build_to.collision"
    hull_inflate_mm: float = 1.5
    hull_sides: int = 12

    # ---- derived ---------------------------------------------------------

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
        real box and ``props_lib.measure`` reports both.
        """
        half = (self.width_mm * 0.5, self.height_mm * 0.5, 5.6)
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
        "corner_clip_mm": s.corner_clip_mm,
        "plan_area_mm2": round(s.plan_area_mm2, 3),
        "mass_g": round(s.mass_g, 4),
        "curl": {"sagitta_mm": s.curl.sagitta_mm, "radius_mm": round(s.curl_radius_mm(), 2),
                 "deepen_sagitta_mm": s.curl.deepen_sagitta_mm,
                 "deepen_radius_mm": round(s.curl_radius_mm(s.curl.deepen_sagitta_mm), 2),
                 "deepen_run_mm": s.curl.deepen_run_mm},
        "folds": [{"v_mm": f.v_mm, "turn_deg": f.turn_deg, "half_width_mm": f.half_width_mm,
                   "wander_mm": f.wander_mm} for f in s.folds],
        "dog_ear": {"leg_mm": s.dog_ear.leg_mm, "fold_back_deg": s.dog_ear.fold_back_deg},
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


__all__ = ["CardSpec", "CurlSpec", "DogEarSpec", "FoldSpec", "LodSpec", "SocketSpec",
           "PAPER_BOMB", "DENY_SUBSTRINGS", "assert_clean", "build_to", "deny_hits",
           "scaled_lod_screen_sizes", "screen_size_distance_m", "BAKE_MARGIN_PX",
           "PROP_TEXTURE_SIZE", "PROP_TRIANGLE_BUDGET"]


if __name__ == "__main__":                                   # pragma: no cover
    import json
    print(json.dumps(build_to(), indent=2))
