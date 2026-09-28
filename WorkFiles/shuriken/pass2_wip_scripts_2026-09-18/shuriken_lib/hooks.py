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

    def hole_projection(self):
        """``(n, radius)`` to re-project the hole wall as one planar island per wedge, or None.

        Faces with a horizontal normal and a centroid inside ``radius`` are grouped by the
        wedge their centroid falls in and projected along that wedge's arm direction (see
        pack.unwrap).  Smart UV Project otherwise scatters the hole-wall faces over whatever
        projection vectors the chamfer chords seeded, and a coarser LOD's hole face (one per
        wedge) then straddles two islands.
        """
        return None

    def wall_projection(self):
        """A classifier ``(centre, normal) -> (group, (tx, ty)) | None`` of LOD0 wall faces to put on
        one planar UV island per group (pack._project_walls), or None."""
        return None

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
        spec, o = self.spec, self.o
        return {
            "points": spec.points,
            "across_mm": spec.tip_circle_mm, "thickness_mm": spec.thickness_mm,
            "mass_g": spec.mass_target_g, "arm_width_mm": spec.arm_width_mm,
            "hub_radius_mm": spec.hub_radius_mm, "hole_mm": spec.hole_diameter_mm,
            "tip_included_deg": spec.tip_included_deg,
            "grind": "knife: both faces, every cutting edge (parallel arm edges and taper edges), to an edge land",
            "grind_angle_deg": spec.grind_angle_deg, "edge_land_mm": spec.edge_land_mm,
            "grind_width_mm": round(o.chamfer_w / MM, 4), "grind_depth_mm": round(o.chamfer.depth / MM, 4),
            "chamfer_width_mm": round(o.chamfer_w / MM, 4),
            "chamfer_wall_top_drop_mm": round(o.chamfer.wall_top_drop / MM, 4),
            "scallop_chamfer_mm": spec.scallop_chamfer_mm,
            "scallop_wall_mm": round((o.thickness - 2.0 * o.scallop.wall_top_drop) / MM, 4),
            "hole_chamfer_mm": spec.hole_chamfer_mm, "hole_chamfer_deg": spec.hole_chamfer_deg,
            "grind_runout_mm": spec.grind_runout_mm,
            "mass_gate": "outline (un-ground plate) mass within +-2 g of the target; ground mass reported",
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
            "X_ROOT_mm": o.x_root(0.0) / MM, "X_ROOT_PLATE_mm": o.x_root(o.scallop_of(lod0_spec)) / MM,
            "X_RUNOUT_mm": o.x_run / MM,
            "X_TAPER_mm": o.x_taper / MM, "X_APEX_mm": o.x_apex / MM,
            "taper_len_mm": o.taper_len / MM,
            "chamfer_width_mm": o.chamfer_w / MM, "chamfer_taper_y_inset_mm": o.chamfer_y / MM,
            "chamfer_depth_mm": o.chamfer.depth / MM, "chamfer_round_mm": o.chamfer.round / MM,
            "grind_angle_deg": o.grind_angle_deg, "edge_land_mm": o.edge_land / MM,
            "scallop_chamfer_mm": o.scallop.width / MM, "hole_chamfer_mm": o.hole_chamfer.width / MM,
            "chamfer_segments": lod0_spec.bevel_segments,
            "plate_rim_radius_mm": o.rim_radius(lod0_spec) / MM, "plate_half_width_mm": o.rim_half_w(lod0_spec) / MM,
            "hole_polygon_radius_mm": o.hole_polygon_radius(hole_total) / MM if hole_total else None,
        }

    def wear_range(self):
        return wear_range(self.o)

    def split_radius(self) -> float:
        return self.o.r_hub

    def hole_projection(self):
        o = self.o
        return o.n, 0.5 * (o.r_hole + o.r_hub)

    def wall_projection(self):
        """Hole wall per wedge, notch wall per notch, arm-edge wall per arm side (knife grind pass).

        Every face with a horizontal normal is a wall: inside the hub (centre radius below halfway
        between the hole and the hub) it is the hole wall, projected along its wedge's tangent;
        on the hub circle within a notch's angular range it is that notch's wall, projected along
        the notch's tangent; anything else belongs to an arm edge (the root run-out wall, the land
        of the parallel run and of the taper, the point's edge) and is projected along its arm.
        """
        o = self.o
        n, sector = o.n, 2.0 * math.pi / o.n
        split = 0.5 * (o.r_hole + o.r_hub)

        def classify(centre, normal):
            if abs(normal[2]) >= 0.01:
                return None
            x, y = float(centre[0]), float(centre[1])
            r = math.hypot(x, y)
            ang = math.atan2(y, x)
            if r < split:
                wedge = int(round(ang / sector)) % n
                a = wedge * sector
                return ("hole", wedge), (-math.sin(a), math.cos(a))
            arm = int(round(ang / sector)) % n
            local = ang - round(ang / sector) * sector
            if abs(local) > o.arm_half_angle - 1e-4 and r < o.r_hub + 1e-6:
                notch = int(math.floor(ang / sector)) % n          # the notch between arms k and k + 1
                a = (notch + 0.5) * sector
                return ("notch", notch), (-math.sin(a), math.cos(a))
            a = arm * sector
            side = 1 if local > 0.0 else -1
            return ("edge", arm, side), (math.cos(a), math.sin(a))

        return classify

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
