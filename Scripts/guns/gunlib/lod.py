"""LOD level for the part generators (GUN_BUILDING_STUDY 5.7: "LOD1 halves segments; LOD2 drops bevels under ~2 px
at its switch distance and replaces fastener groups ...; LOD3 is the silhouette hull per part group").

The LODs come from the SAME generators as LOD0 (no Decimate): a build sets ``set_level(k)`` before calling the part
builders, and the primitives read it:

  mesh.revolve / cylinder / tube / capsule / ellipsoid / dome   ring segment counts      x 1, 1/2, 1/4
  geo2d.arc / rounded_rect / fillet / superellipse                arc segment counts       x 1, 1/2, 1/4
  bl.bevel / bl.bevel_weighted                                    bevel segments           table SEGMENTS below

Level 0 is the identity: every function returns its input unchanged, so LOD0 builds byte-identical meshes (checked by
the rifle's lods stage against the form stage's form_tris.npz). Level 3 is not a generator setting: the gun's LOD3 is
its blockout generator (the traced silhouette volumes) at a coarser tolerance.
"""
from __future__ import annotations

import math

LEVEL = 0
PHASE_JITTER_DEG = 0.0        # retry knob: a booleans' coincidence at a coarse level often clears with a tiny turn
RING_FACTOR = {0: 1.0, 1: 0.5, 2: 0.2, 3: 0.125}
RING_MIN = {0: 3, 1: 6, 2: 5, 3: 6}
# bevel segments per level: LOD0 n -> LOD1 / LOD2 (study 3.1 table: chamfer 1/1/0, rounds 3/2/1, S-cut 1/0/0)
SEGMENTS = {1: {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4},
            2: {1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2}}
MIN_BEVEL_MM = {1: 0.8, 2: 2.5}      # narrower bevels vanish at that level (LOD1 from ~2.7 m: 0.48 px/mm, a 0.8 mm
                                     # chamfer is under half a pixel; LOD2 from ~6.7 m: 0.19 px/mm)


def set_level(k: int) -> None:
    global LEVEL
    LEVEL = int(k)


def ring(n: int, minimum: int = None) -> int:
    """Segments around a revolve / circle at the current level (even counts stay even, so a half ring keeps every
    other LOD0 vertex: the coarse polygon is inscribed in the fine one with the same phase)."""
    n = int(n)
    if LEVEL == 0:
        return n
    lo = RING_MIN[LEVEL] if minimum is None else minimum
    m = max(lo, int(round(n * RING_FACTOR[LEVEL])))
    if n % 2 == 0 and m % 2:
        m += 1
    return min(n, m)


def count(n: int, minimum: int = 1) -> int:
    """A subdivision count along a profile (dome rings, capsule end segments, fillet segments)."""
    n = int(n)
    if LEVEL == 0:
        return n
    return min(n, max(minimum, int(math.ceil(n * RING_FACTOR[LEVEL]))))


def arc_points(n: int) -> int:
    """Points on an arc INCLUDING both ends (geo2d.arc)."""
    n = int(n)
    if LEVEL == 0 or n <= 2:
        return n
    return count(n - 1, 1) + 1


def bevel(width_mm: float, segments: int):
    """(width, segments) at the current level, or None to skip the bevel."""
    if LEVEL == 0:
        return width_mm, segments
    if LEVEL >= 3:
        return None
    s = SEGMENTS[LEVEL].get(int(segments), max(1, int(segments) // (2 * LEVEL)))
    if s <= 0 or width_mm < MIN_BEVEL_MM[LEVEL]:
        return None
    return width_mm, s


TOL_FACTOR = {0: 1.0, 1: 4.0, 2: 48.0, 3: 64.0}
STEP_FACTOR = {0: 1.0, 1: 2.0, 2: 6.0, 3: 8.0}


def tol(t: float) -> float:
    """A chordal tolerance (mm) at the current level: halving the segments of a round quadruples its chord error."""
    return t * TOL_FACTOR[LEVEL]


def step(s: float) -> float:
    """A maximum spacing (mm) between stations at the current level."""
    return s * STEP_FACTOR[LEVEL]


class hold:
    """``with lod.hold(1): ...`` builds at LOD0 resolution while the level is <= 1 (joints whose clearance row must
    hold at LOD1 too: a hinge pin in its seat keeps its LOD0 segment count, GUN_BUILDING_STUDY 7.2 B3)."""

    def __init__(self, upto: int = 1):
        self.upto = upto
        self.saved = None

    def __enter__(self):
        global LEVEL
        self.saved = LEVEL
        if LEVEL <= self.upto:
            LEVEL = 0
        return self

    def __exit__(self, *exc):
        global LEVEL
        LEVEL = self.saved
        return False
