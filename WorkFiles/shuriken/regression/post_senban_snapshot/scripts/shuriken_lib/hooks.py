"""The generic Form hook: everything ``pack.build_form`` needs from a form's generator.

Library 3.3 (senban build).  Until 3.2 ``build_form`` called the radial-star generator,
``measure`` and the render rig directly, so only a ``RadialStarSpec`` could be built.  A
form now carries a ``FormGeometry`` (``Form.geometry``); ``build_form``, ``render_form``,
the bake and the export talk to the form ONLY through it:

    validate()                        spec sanity, raises ValueError
    build_to()                        the report's build_to block
    author(level, name, collection)   -> (obj, stats, lod_used); lod_used is a dataclass with
                                         a ``band`` (min, max) triangle tuple
    tag(obj)                          material custom properties (shuriken_wear_from / _to ...)
    make_hull(lod0, options)          -> (UCX object, method text)
    make_sockets(lod0)                Grip and Trail Empties through pipeline.make_socket
    density(lod_used)                 the report's density block (LOD0 segment counts)
    wear_range()                      (from, to) radius in metres of the tip wear ramp
    split_radius()                    radius splitting lod_deviation's inner / outer regions
    order                             rotational order n (symmetry, per-point sampling, render)
    measure(obj, lod_used)            build-to figures measured on the mesh (must carry mass_g,
                                         mass_target_g, mass_within_tolerance, plate_area_mm2)
    topology_quality(obj)             face-shape figures for the wireframe review
    symmetry_extra(lod_objects)       optional extra symmetry figures (mirror lines ...)
    lod_note() / lod_strategy()       report text
    lod_switching_extra(report)       optional additions to the lod_switching block
    render_outline()                  what the shared rig reads: n, half_t, r_tip, tip_extents()
    island_margin(default)            LOD0 Smart UV island margin (default: the pack's --island-margin)

``RadialGeometry`` is the radial-star path moved here VERBATIM from 3.2's ``build_form``
(same calls, same order), so the four-point and eight-point rebuild bit-for-bit - the
regression gate in WorkFiles/shuriken/regression proves it.  A form that sets no
``geometry`` gets a ``RadialGeometry`` of its spec.  Non-radial forms (the senban's
``shuriken_lib.plate.SquarePlateGeometry``; the spike next) subclass ``FormGeometry``.
"""
from __future__ import annotations

import math
from typing import Optional

import pipeline

from .geometry import author_lod, author_tip_prism_hull
from .material import tag_object, wear_range
from .measure import measure, topology_quality
from .spec import MM, RadialStarSpec


class FormGeometry:
    """Base class (and documentation) of the hook; every method a form must provide raises."""

    kind = "abstract"

    def __init__(self, spec) -> None:
        self.spec = spec

    # ------------------------------------------------------------------ required
    @property
    def order(self) -> int:
        raise NotImplementedError

    def validate(self) -> None:
        raise NotImplementedError

    def build_to(self) -> dict:
        raise NotImplementedError

    def author(self, level: int, name: str, collection):
        raise NotImplementedError

    def tag(self, obj) -> None:
        raise NotImplementedError

    def make_hull(self, lod0, options):
        raise NotImplementedError

    def make_sockets(self, lod0) -> None:
        raise NotImplementedError

    def density(self, lod_used) -> dict:
        raise NotImplementedError

    def wear_range(self):
        raise NotImplementedError

    def split_radius(self) -> float:
        raise NotImplementedError

    def measure(self, obj, lod_used) -> dict:
        raise NotImplementedError

    def topology_quality(self, obj) -> dict:
        raise NotImplementedError

    def render_outline(self):
        raise NotImplementedError

    # ------------------------------------------------------------------ optional
    def island_margin(self, default: float) -> float:
        return default

    def symmetry_method(self) -> str:
        return (f"max nearest-neighbour distance after a 360/{self.order} deg rotation of the stored "
                "(float32) vertices")

    def symmetry_extra(self, lod_objects) -> Optional[dict]:
        return None

    def lod_note(self) -> str:
        return ""

    def lod_strategy(self) -> dict:
        return {}

    def lod_switching_extra(self, report: dict) -> Optional[dict]:
        return None


class RadialGeometry(FormGeometry):
    """The C_n radial-star path of library 3.2, unchanged (four-point, eight-point, ...)."""

    kind = "radial_star"

    def __init__(self, spec: RadialStarSpec) -> None:
        super().__init__(spec)
        self.o = spec.outline()

    @property
    def order(self) -> int:
        return self.o.n

    def validate(self) -> None:
        self.spec.validate()

    def build_to(self) -> dict:
        spec = self.spec
        return {
            "points": spec.points,
            "across_mm": spec.tip_circle_mm, "thickness_mm": spec.thickness_mm,
            "mass_g": spec.mass_target_g, "arm_width_mm": spec.arm_width_mm,
            "hub_radius_mm": spec.hub_radius_mm, "hole_mm": spec.hole_diameter_mm,
            "tip_included_deg": spec.tip_included_deg,
            "bevel_offset_mm": spec.bevel_offset_mm, "bevel_runout_mm": spec.bevel_runout_mm,
            "source": f"References/Shuriken/SHURIKEN_STUDY.md section {spec.study_section}",
        }

    def author(self, level: int, name: str, collection):
        return author_lod(self.o, self.spec.lods[level], name, collection)

    def tag(self, obj) -> None:
        tag_object(obj, self.o)

    def make_hull(self, lod0, options):
        o = self.o
        if self.spec.hull == "tip_prism":
            hull = author_tip_prism_hull(lod0, o, index=0)
            method = (f"tip_prism: shuriken_lib.geometry.author_tip_prism_hull, the {o.n}-gon prism "
                      "through the tips at full plate thickness (exactly C_n, encloses LOD0)")
        else:
            hull = pipeline.make_ucx_hull(lod0, index=0, max_verts=options.hull_verts)
            method = (f"pipeline: pipeline.make_ucx_hull, convex hull of LOD0 collapse-decimated "
                      f"to <= {options.hull_verts} vertices")
        return hull, method

    def make_sockets(self, lod0) -> None:
        o, spec = self.o, self.spec
        grip = (math.radians(spec.grip_angle_deg) if spec.grip_angle_deg is not None
                else math.pi / o.n)                      # the rim notch between arms 0 and 1
        pipeline.make_socket(lod0, "Grip", (o.r_hub * math.cos(grip), o.r_hub * math.sin(grip), 0.0),
                             rotation_euler=(0.0, 0.0, grip))
        pipeline.make_socket(lod0, "Trail", (0.0, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    def density(self, lod_used) -> dict:
        o = self.o
        lod0_spec = lod_used[0]
        hole_total = lod0_spec.hole_segments * o.n
        return {
            "points": o.n,
            "N_COL": lod0_spec.columns, "N_NOTCH": lod0_spec.notch_segments,
            "N_STRAIGHT": lod0_spec.straight_intervals,
            "N_TAPER_B1": lod0_spec.taper_intervals, "N_TAPER_B2": lod0_spec.tip_intervals,
            "HOLE_SEG_PER_WEDGE": lod0_spec.hole_segments, "hole_segments_total": hole_total,
            "hub_segments_total": lod0_spec.hub_segments * o.n,
            "hub_topology": ("rings: " + " -> ".join(
                [f"hole {lod0_spec.hole_segments * o.n}"]
                + [f"{kind} {lod0_spec.ring_segments(kind) * o.n} at r={o.hub_ring_radius(lod0_spec, t) / MM:.2f} mm"
                   for kind, t in lod0_spec.hub_rings]
                + [f"rim {lod0_spec.hub_segments * o.n}"])) if lod0_spec.hub_rings else
            f"bridge: hole ring {hole_total} -> hub rim {lod0_spec.hub_segments * o.n} at "
            f"{(lod0_spec.hub_segments // lod0_spec.hole_segments) if lod0_spec.has_hole else 0}:1",
            "hub_to_hole_ratio": (lod0_spec.hub_segments // lod0_spec.hole_segments
                                  if lod0_spec.has_hole and not lod0_spec.hub_rings else None),
            "X_TAPER_mm": o.x_taper / MM, "X_RUNOUT_mm": o.x_runout / MM, "X_APEX_mm": o.x_apex / MM,
            "taper_len_mm": o.taper_len / MM,
            "bevel_offset_mm": o.bevel_offset / MM, "bevel_y_inset_mm": o.bevel_y / MM,
            "bevel_segments": lod0_spec.bevel_segments, "bevel_runout_mm": o.bevel_runout / MM,
            "hole_polygon_radius_mm": o.hole_polygon_radius(hole_total) / MM if hole_total else None,
        }

    def wear_range(self):
        return wear_range(self.o)

    def split_radius(self) -> float:
        return self.o.r_hub

    def measure(self, obj, lod_used) -> dict:
        return measure(obj, self.spec, lod_used)

    def topology_quality(self, obj) -> dict:
        return topology_quality(obj, self.o)

    def render_outline(self):
        return self.spec.outline()

    def symmetry_method(self) -> str:
        return (f"max nearest-neighbour distance after a 360/{self.o.n} deg rotation of the stored "
                "(float32) vertices. Quarter-turn forms are exact (0.0); any other n is exact in "
                "topology and float64 authoring, and lands within float32 storage precision "
                "(a few nm) on the stored mesh")

    def lod_note(self) -> str:
        return ("LODs are authored by the radial-star generator at reduced segment counts "
                "(study 4's table), not decimated, so LOD1 is a genuinely different mesh: "
                "its hole ring and bevel segments are halved. max_surface_deviation_mm is "
                "two-sided (vertices, edge midpoints and triangle centroids of each mesh "
                "against the other's surface); the rev2 metric (LOD0 vertices only) is kept "
                "for comparison with rev 2's 1e-6 mm.")

    def lod_strategy(self) -> dict:
        return {
            "method": "parametric: every LOD authored by shuriken_lib.geometry at its own segment counts",
            "table": "study 4: LOD0 full outline, bevels, hole ring; LOD1 halve the hole ring and bevel "
                     "segments; LOD2 drop the bevel and the hole entirely",
            "replaces": "rev 2 pipeline.decimate_lods (Collapse Decimate of LOD0)",
            "naming": "LODn objects are created as <mesh>_LODn, and pipeline.make_lod_group renames LOD0 "
                      "with its UCX_/SOCKET_ children, so the hull stays UCX_<mesh>_LOD0_00",
        }


def geometry_of(form) -> FormGeometry:
    """The form's hook, or the radial-star path for a form that sets none."""
    geometry = getattr(form, "geometry", None)
    return geometry if geometry is not None else RadialGeometry(form.spec)


__all__ = ["FormGeometry", "RadialGeometry", "geometry_of"]
