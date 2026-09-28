#!/usr/bin/env python
"""props_lib.flashbang_spec - SM_Flashbang's build-to numbers, in one place (round 1 + finalise 2026-09-27).

Pure Python (no bpy, no numpy).  The Blender build, the calculators and the Unreal verifier read the SAME object.

SOURCES.  Every dimension comes from the Study's metrology of References/Flashbang/flashbang_reference.png
(WorkFiles/flashbang/FLASHBANG_REFERENCE_SPEC.md + flashbang_spec.json), in the unit D = the perforated body's outer
diameter, using the PERSPECTIVE-CORRECTED heights (spec section 2, "build to the corrected column").  The scale is the
plan's (WorkFiles/flashbang/FLASHBANG_BUILD_PLAN.md 1.2): D = 44.0 mm, one constant.  Where the reference is silent
or inconsistent (spec sections 10 and 11) the choice is written next to the number as CHOICE.

FRAME (plan section 2).  +Z is the canister axis toward the fuze, the origin is the centre of the base end face (the
floor contact, the lowest point of the raised rim lip), the lever lies on +X, the pull ring on -Y.  Azimuth theta is
measured from +X toward +Y.  Export Forward -Y / Up Z (the pack's); in Unreal the lever is on +X and the ring on +Y.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .spec import (PACK_LOD_REFERENCE_RADIUS_MM, PACK_LOD_SCREEN_SIZES, assert_clean, deny_hits,  # noqa: F401
                   scaled_lod_screen_sizes, screen_size_distance_m)

D_MM = 44.0                       #: the plan's scale constant: the perforated body's outer diameter (the grip)


def dmm(x_d: float) -> float:
    """D units -> mm."""
    return round(x_d * D_MM, 4)


@dataclass(frozen=True)
class SocketDef:
    name: str
    rule: str
    use: str


@dataclass(frozen=True)
class LodQuality:
    """One LOD's tessellation.  Every LOD is GENERATED from the same parametric parts (no Decimate)."""
    body_cell_u: int          # segments across one 60 deg hole cell (outer surface)
    body_web_u: int           # segments across one 30 deg plain web
    body_cell_v: int          # segments up one cell side
    hole_pts: int             # points round each oval hole
    inner_cell_u: int         # the tube's inner surface (seen only through the holes)
    inner_cell_v: int
    revolve_segs: int         # sleeve / neck (must equal 5*body_cell_u + 2*body_web_u)
    collar_segs: int
    plinth_segs: int
    cap_per_flat: int         # base cap: segments per 30 deg flat (12 flats)
    cap_notches: bool
    tube_segs: int            # FINALISE: segments of each brass can's visible arc
    ring_major: int
    ring_minor: int
    small_segs: int           # knuckle, pin boss, pins, bosses
    eye_major: int
    eye_minor: int
    lever_curl: int           # segments of the lever's curl round the knuckle
    box_chamfer: bool         # chamfered boxes (housing, top plate, hinge block)
    tri_band: Tuple[int, int]
    cap_end_detail: int = 2   # FINALISE: 2 the notched end face + foot cut-outs, 1 disc + groove + rim (no inner
                              # tabs) with the foot cut-outs, 0 a flat end face
    inner_shell: bool = True  # the tube's hole walls and inner surface (LOD2 drops them; the holes stay open)
    grooves: bool = False     # ROUND 2: the ring lines as real V-grooves (else normal / colour only)
    can_shoulder: bool = False  # ROUND 2: each brass can's seam step + rounded shoulder as geometry
    head_detail: int = 2      # ROUND 2: 2 every fuze part, 1 no coil / pads, 0 the silhouette parts only


@dataclass(frozen=True)
class FlashbangSpec:
    name: str = "Flashbang"
    mesh_name: str = "SM_Flashbang"
    body_mesh: str = "SM_Flashbang_Body"
    ring_mesh: str = "SM_Flashbang_PullRing"
    lever_mesh: str = "SM_Flashbang_Lever"
    material_paint: str = "M_Flashbang_Paint"
    material_steel: str = "M_Flashbang_Steel"
    texture_stem: str = "T_Flashbang"
    atlas_px: int = 2048
    padding_px: int = 16
    seed: int = 20260927

    # ------------------------------------------------------------------ body (spec 2-4)
    body_r: float = D_MM / 2.0                              # 22.0
    wall_mm: float = dmm(0.05)                              # ROUND 2: 2.2 (was 1.76) - the reference's thick cut
                                                            # wall (spec 3: 0.03-0.05 D, the top of the range)
    inner_tube_r: float = 18.8                              # ROUND 2b: the brass tube 1.0 mm behind the wall (was 16.72,
                                                            # 3 mm deeper: its floor / ceiling showed as an 'egg')
    body_z0: float = dmm(0.471)                             # 20.72 cap top = end of paint
    sleeve_z0: float = dmm(2.529)                           # 111.28 sleeve bottom step
    sleeve_r: float = dmm(1.066) / 2.0                      # 23.45
    sleeve_z1: float = dmm(2.857)                           # 125.71 sleeve full diameter top
    sleeve_top_z: float = dmm(2.936)                        # 129.18 top chamfer top
    sleeve_top_r: float = dmm(0.94) / 2.0                   # 20.68 chamfer top edge
    neck_r: float = dmm(0.74) / 2.0                         # 16.28
    collar_z0: float = dmm(2.966)                           # 130.50
    collar_z1: float = dmm(3.105)                           # 136.62
    collar_r: float = dmm(0.773) / 2.0                      # 17.01
    collar_chamfer: float = 0.9                             # CHOICE: the "chamfered top edge" (spec 3), size by eye (p1)
    collar_groove_z: float = 133.1                          # CHOICE: the collar's two-band line (v2/p1), groove 0.45 mm
    plinth_r: float = dmm(0.59) / 2.0                       # 12.98
    plinth_z1: float = dmm(3.158)                           # 138.95 = housing bottom
    # holes (spec 4)
    hole_rows_z: Tuple[float, ...] = (dmm(0.859), dmm(1.521), dmm(2.158))   # 37.80, 66.92, 94.95 (C, B, A)
    hole_ang_w_deg: float = 40.0                            # 0.349 D along the arc = 40 deg
    hole_h: float = dmm(0.41)                               # 18.04
    #: CHOICE (spec 4 recommendation): 5 holes per row at phase + (0, 60, 120, 180, 270), the only pattern that
    #: reproduces every view's local spacing.  The phase relative to the lever (theta 0) is fitted to the lever-side
    #: view v4 (holes at -67 / +20 / +87 deg from its camera, lever face 13.3 mm right of the axis => camera -28 deg).
    hole_pattern_deg: Tuple[float, ...] = (0.0, 60.0, 120.0, 180.0, 270.0)
    hole_phase_deg: float = -8.0
    ring_lines_z: Tuple[float, ...] = (dmm(1.19), dmm(1.84))   # 52.36, 80.96 engraved lines (maps: 0.66 mm, spec 4)
    ring_line_w: float = dmm(0.015)
    groove_w: float = 0.26                                  # ROUND 2: V-groove half width (0.52 mm wide) ...
    groove_d: float = 0.22                                  # ... and depth (craft: 0.6-0.8 wide, 0.4 deep; p2 reads finer)
    tube_seam_z: Tuple[float, ...] = (dmm(0.859) + 0.3, dmm(1.521) + 0.3, dmm(2.158) + 0.3)  # 0-3 px above centre
    #: FINALISE (craft + blind review: "a smooth brass egg"): through each hole the reference shows a vertical brass
    #: CYLINDER narrower than the hole with dark gaps both sides.  One brass can per hole column (radius can_r, axis
    #: at radius can_c), dark radial dividers between the columns (they also close the see-through at the limbs).
    can_r: float = 5.8                                      # ROUND 2b: 11.6 mm wide = 75 % of the hole (the reference's
                                                            # tube: 71 % in p4); its straight vertical edges must show
                                                            # inside the window or the tube reads as a capsule
    can_c: float = 14.8                                     # ROUND 2: front of the can at r 20.6, INSIDE the wall
                                                            # (19.8): the rim's shadow on the can is shallower (round
                                                            # 1's deeper can showed a lit oval = the "brass egg")
    can_arc_deg: float = 200.0
    can_step: float = 0.30                                  # ROUND 2b: the seam is a small raised LIP (the lower tube's
    can_flare: float = 0.25                                 # rolled top edge, can_flare proud) with the upper tube
                                                            # can_step NARROWER above it (p4: a bright line, a dark band
                                                            # above, then a straight tube).  Round 2's notch + 1.2 mm
                                                            # flare lit as the rounded end of a 'pill'
    # ------------------------------------------------------------------ base cap (spec 3)
    cap_apothem: float = 23.9                               # 12 flats; mean width 1.095 D = 48.2 (with the corners)
    cap_corner_r: float = 3.0                               # ROUND 2: 14 -> 3 - the reference's cap shows its 12 flats as
                                                            # light / dark vertical bands (v2 / v3; round 1 read as "a
                                                            # plain cylinder", blind pair 13)
    cap_side_z0: float = dmm(0.081)                         # 3.56 foot chamfer top
    cap_side_z1: float = dmm(0.413)                         # 18.17 side top
    foot_r: float = dmm(0.94) / 2.0                         # 20.68 bottom edge after the lower chamfer
    cap_top_inner_r: float = 22.25                          # top chamfer's inner edge (0.25 mm shoulder at the body)
    # end face (p3), CHOICE of the depths the reference cannot give (spec 11): lip 0.5 mm proud, groove 1.2 deep
    #: FINALISE (craft review): p3 reads as a WIDE flat contact rim (r 15.2 .. foot) around a recessed central disc,
    #: a narrow groove between them, and 5 blocky notches where the rim juts IN toward the centre (the disc outline
    #: steps in); the side views' foot cut-outs are the same 5 notches cut out through the outer bottom edge.
    #: Radial bands (r0, r1, z normal, z in a notch) from the centre out; z = height ABOVE the contact plane.
    end_bands: Tuple[Tuple[float, float, float, float], ...] = (
        (0.0, 12.6, 1.1, 1.1),        # central disc, 1.1 mm recessed
        (12.6, 13.8, 1.1, 1.9),       # notch: the groove steps in
        (13.8, 15.2, 1.1, 0.0),       # notch: the rim tab (the disc outline steps in at each notch)
        (15.2, 16.4, 1.9, 0.0),       # the groove (normal) / rim tab (notch)
        (16.4, 18.4, 0.0, 0.0),       # the flat contact rim
        (18.4, dmm(0.94) / 2.0, 0.0, 0.0),   # outer rim (ROUND 2b: no longer cut through the foot edge)
    )
    #: ROUND 2b: the side views' foot "cut-outs" are a STEP in the height of the dark lower chamfer band, not a gap
    #: under the silhouette (the reference's bottom edge is level in v1-v4; the band above it is ~2 mm taller over
    #: wide arcs, with a vertical step at each end - 4x crops WorkFiles/flashbang/r2/look2/ref_feet.png).  Round 2's
    #: 5 mm through-cuts were nearly invisible (blind pair 13).  Modelled as 5 wide recesses centred on the end-face
    #: notches: over each arc the chamfer starts foot_recess_h higher (a steeper, taller, shadowed band), closed by a
    #: wall triangle at each end.  The edges snap to existing ring angles (no extra triangles but the walls).
    #: The reference's four views disagree on where the recesses are (they are not one rigid object); this layout
    #: matches the steps in v1 and v3 and most of v2's front.
    foot_recess_w_deg: float = 32.0
    foot_recess_h: float = 2.2
    notch_foot_z: float = 2.0                               # the foot cut-out height (side views v1 / v3)
    notch_deg: Tuple[float, ...] = (-10.0, 62.0, 134.0, 206.0, 278.0)   # 5 notches, 72 deg pitch (p3: -10 ... )
    notch_w_mm: float = 5.0                                 # FINALISE: 4-5 mm blocky notches (was 2.2)
    # ------------------------------------------------------------------ fuze head (spec 5)
    housing_half: float = dmm(0.48) / 2.0                   # 10.56 square box
    housing_z0: float = dmm(3.158)                          # 138.95
    housing_z1: float = dmm(3.671)                          # 161.53
    housing_chamfer: float = 0.6
    plate_z1: float = 164.1                                 # top cover plate top (2.57 mm plate)
    #: ROUND 2 fuze head (the blind tells: "a plain box with a flat cap").  Every part below is real geometry,
    #: placed by projecting it through the reference row camera (WorkFiles/flashbang/r2/tools/r2proj.py) so each view's
    #: head silhouette extents land near the reference's (r2_extents.py), and by eye against the close-ups.
    plate_x: Tuple[float, float] = (-11.3, 12.9)            # small overhang on every side (0.7 / 1.0 mm)
    plate_y: float = 11.6
    housing_corner_c: Tuple[float, float, float, float] = (0.6, 0.6, 0.6, 2.6)   # vertical edges (-X-Y, +X-Y,
                                                            # +X+Y, -X+Y): the -X+Y corner cut back (v1's narrow left)
    # the striker on the -X face (v2: a raised plate topped by a hinge knuckle across the face)
    striker_proud: float = 1.6
    striker_y: float = 6.8                                  # half width
    striker_z: Tuple[float, float] = (142.0, 160.6)
    striker_knuckle_r: float = 2.9
    striker_knuckle_c: Tuple[float, float] = (-11.86, 163.0)   # (x, z): its top = 165.9 = 3.77 D (the overall height)
    # the side lug on the +Y face (v2's left flank with two pin ends; v1 / v3's top-left lug and roll): a flag-shaped
    # plate standing off the housing on a spacer, its top edge rolled, two cross pins with square washers
    lug_y: Tuple[float, float] = (12.6, 15.8)
    lug_standoff: Tuple[float, float, float, float] = (0.0, 4.8, 143.0, 161.0)   # x0, x1, z0, z1 (y 10.3 .. lug)
    lug_poly_xz: Tuple[Tuple[float, float], ...] = ((-1.0, 141.5), (5.5, 141.5), (5.5, 162.4), (-10.0, 162.4),
                                                    (-10.8, 161.6), (-10.8, 156.3), (-10.0, 155.5), (-1.0, 155.5))
    lug_roll_r: float = 1.6                                 # the rolled top edge (a tube along X)
    lug_pins: Tuple[Tuple[float, float], ...] = ((-10.8, 159.0), (-1.0, 149.0))   # (x of the face, z)
    #: ROUND 2b: the -Y side flag (the reference's top-right block in v2 at H 3.56-3.65 D reaching 20.5 mm right of the
    #: axis, and the top-left hook in v4 reaching 21-23 mm left at H 3.6-3.7 D; both views put it on the -Y side at the
    #: top): a 1.4 mm sheet plate in the YZ plane flush with the -X (striker) face, its outer end turned, with a cross
    #: pin.  Round 2's head was 7 % / 12 % narrower than the reference there (v2 / v4 at H 3.4-3.7 D)
    flag_x: Tuple[float, float] = (-11.2, -9.8)
    flag_poly_yz: Tuple[Tuple[float, float], ...] = ((-10.0, 155.0), (-19.3, 155.0), (-20.5, 156.2), (-20.5, 162.0),
                                                     (-19.5, 163.0), (-10.0, 163.0))
    flag_pin: Tuple[float, float, float] = (-18.2, 159.0, 0.95)   # (y, z, r) of its cross pin
    knuckle_r: float = dmm(0.137) / 2.0                     # 3.01
    knuckle_len: float = 15.2                               # FINALISE: fills the lever curl between its flanges (cheeks)
    knuckle_c: Tuple[float, float, float] = (18.0, -2.62, 161.5)   # ROUND 2: +0.86 so the curl top = 165.9 = 3.77 D
    block_x: Tuple[float, float] = (10.2, 17.6)             # CHOICE: the hinge bracket carrying knuckle and pin
    block_y: Tuple[float, float] = (-8.3, 6.3)
    block_z: Tuple[float, float] = (151.3, 160.0)
    pin_boss_r: float = 2.2
    pin_boss_y1: float = -14.5                              # ROUND 2: the boss's outer end (the pin shaft shows beyond)
    #: ROUND 2: the pin eye and the ring's top point, fitted with the ring's pose to the four views
    #: (r2_ring_search3.py): the ring-side silhouette extents (mean |ours - ref| over H 2.70-3.75 D, summed over the
    #: views: 16.5 mm in round 1 -> 11.8) with the ring near FACE-ON in v1 ("the pull ring toward the viewer") and v3 and
    #: nearly edge-on in v2 (projected aspect 0.90 / 1.06 / 0.38; round 1: 0.77 / 0.95 / 0.20)
    pin_c: Tuple[float, float] = (12.0, 156.5)              # (x, z) of the pin axis
    pin_eye_c_y: float = -19.5
    pin_r: float = 1.0
    pin_head_r: float = 2.4                                 # the ring passes through the pin's head
    pin_head_len: float = 2.6
    small_boss_r: float = 1.35                              # the screw head on the -Y face (v1 / v3 / p1)
    small_boss_c: Tuple[float, float] = (5.2, 158.2)
    coil_c: Tuple[float, float] = (-5.6, 158.0)             # ROUND 2: the small coil end on the -Y face (v3)
    post_c: Tuple[float, float] = (15.6, -9.0)              # ROUND 2: the spring post and its ball (v1 / v4)
    post_z: Tuple[float, float] = (151.5, 157.4)
    post_r: float = 0.9
    ball_r: float = 1.3
    ball_z: float = 158.2
    # ------------------------------------------------------------------ lever (spec 6)
    lever_t: float = 1.3                                    # FINALISE: sheet thickness of a CHANNEL section
    lever_flange: float = 3.3                               # flange depth (edge-on the lever reads ~0.08 D deep, v1)
    lever_w: float = dmm(0.26)                              # 11.44 lower segment
    lever_w_top: float = dmm(0.41)                          # 18.04 upper segment at the top
    lever_w_joggle: float = dmm(0.29)                       # 12.76 upper segment at the joggle
    lever_upper_x: float = 21.0                             # inner face of the upper segment (outboard of the knuckle)
    lever_lower_x: float = D_MM / 2.0 + dmm(0.11)           # 26.84 inner face: stands 0.11 D off the body
    lever_joggle_z: Tuple[float, float] = (146.0, 137.0)    # FINALISE: one smooth diagonal step (was an S-crank)
    lever_tip_z: float = dmm(0.91)                          # 40.04 (v4, the lever-side view)
    lever_tip_bend: float = dmm(0.10)                       # 4.4 mm bent inward (v1)
    lever_tip_in: float = 2.0
    lever_tip_corner_r: float = dmm(0.05)                   # 2.2
    # ------------------------------------------------------------------ pull ring (spec 5)
    ring_outer_d: float = dmm(1.05)                         # 46.2
    ring_wire_d: float = 2.4                                # FINALISE: thicker dark wire (craft 2.2-2.5 mm)
    ring_tilt_deg: float = 20.0                             # ROUND 2: fitted (r2_ring_search3.py), was 30
    ring_yaw_deg: float = -5.0                              # ROUND 2: the wire through the eye runs 5 deg off +X
    # ------------------------------------------------------------------ mass (plan 1.2 / 6.3)
    mass_g: float = 300.0
    physics_mass_kg: float = 0.30
    lever_mass_kg: float = 0.015
    ring_mass_kg: float = 0.008
    grip_below_step_mm: float = 41.6                        # plan 3: half of an 83 mm four-finger span
    # ------------------------------------------------------------------ LODs
    lods: Tuple[LodQuality, ...] = (
        #  ROUND 2: the revolve 72 -> 48 at LOD0 (7.5 deg: a 0.05 mm sagitta) and cap 3 -> 2 per flat pay for the
        #  V-grooves, the can shoulders and the fuze mechanism; LOD1 back near the plan's ~2,600-3,000
        #          cell_u web_u cell_v hole  in_u in_v rev coll pl  cap/flat notch tube ring  sm eye  curl chamf band
        LodQuality(8, 4, 1, 24, 1, 1, 48, 24, 20, 2, True, 6, 32, 8, 12, 8, 4, 8, True, (5200, 6000), 2, True,
                   True, True, 2),
        LodQuality(4, 2, 1, 14, 1, 1, 24, 16, 16, 1, True, 6, 24, 8, 8, 6, 3, 5, True, (2400, 4000), 1, True,
                   False, False, 1),                # ROUND 2b: no tube ledge (sub-pixel at the 0.89 m switch); the ring stays 24x8 (24x6 popped: 6.4 %)
        LodQuality(4, 2, 1, 16, 1, 1, 24, 12, 8, 1, False, 6, 24, 8, 6, 4, 3, 3, True, (800, 2000), 0, False,
                   False, False, 0),
    )
    sockets: Tuple[SocketDef, ...] = (
        SocketDef("Grip", "on the axis at the palm centre: Z = sleeve step - 41.6 mm (half of an 83 mm finger span)",
                  "hand attach: component relative transform = inverse(Grip)"),
        SocketDef("Throw", "the centre of mass of the assembled parts (analytic volumes x densities), 0.1 mm",
                  "launch point / spin centre; CCD on when thrown"),
        SocketDef("Pin", "on the pin axis at the pin's eye; +X = the pull direction (-Y), +Z = world up",
                  "pull-ring attach and the pull (translate along socket +X by pin_travel_mm)"),
        SocketDef("LeverHinge", "on the knuckle axis at the lever's mid-width (y 0); +X radially out through the "
                                "lever, +Y along the hinge, +Z up",
                  "lever attach; the lever opens with a POSITIVE pitch in Unreal"),
        SocketDef("Flash", "on the axis at the middle hole row's centre", "flash / light / smoke FX spawn"),
    )

    # ------------------------------------------------------------------ derived
    def hole_thetas(self) -> List[float]:
        return sorted(((self.hole_phase_deg + a) % 360.0) for a in self.hole_pattern_deg)

    @property
    def body_r_in(self) -> float:
        return self.body_r - self.wall_mm

    @property
    def ring_major_r(self) -> float:
        return self.ring_outer_d / 2.0 - self.ring_wire_d / 2.0

    def lod_screen_sizes(self, radius_mm: float) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm)

    def switch_distances_m(self, radius_mm: float) -> List[float]:
        return [round(screen_size_distance_m(s, radius_mm * 0.001), 4) for s in self.lod_screen_sizes(radius_mm)[1:]]

    def grip_z(self) -> float:
        return round(self.sleeve_z0 - self.grip_below_step_mm, 3)

    def pin_eye_y(self) -> float:
        """The pin head's centre (the ring passes through it) = the Pin socket."""
        return round(self.pin_eye_c_y, 3)


FLASHBANG = FlashbangSpec()

#: analytic mass model (plan 6.3): densities g/cm3
DENSITY = {"steel": 7.85, "brass": 8.5, "charge": 1.6}


def build_to(s: FlashbangSpec = FLASHBANG) -> Dict[str, object]:
    return {
        "name": s.name, "meshes": [s.mesh_name, s.body_mesh, s.ring_mesh, s.lever_mesh],
        "materials": [s.material_paint, s.material_steel],
        "textures": [f"{s.texture_stem}_{k}" for k in ("BC", "ORM", "N")] + [f"Recolour/{s.texture_stem}_Paint_Detail16"],
        "atlas_px": s.atlas_px, "padding_px": s.padding_px, "D_mm": D_MM,
        "hole_thetas_deg": s.hole_thetas(), "hole_rows_z_mm": list(s.hole_rows_z),
        "mass_g": s.mass_g, "physics_mass_kg": s.physics_mass_kg,
        "lod_bands": [list(l.tri_band) for l in s.lods],
        "pack_lod_rule": {"sizes": list(PACK_LOD_SCREEN_SIZES), "reference_radius_mm": PACK_LOD_REFERENCE_RADIUS_MM},
        "sockets": [{"name": k.name, "rule": k.rule, "use": k.use} for k in s.sockets],
    }


__all__ = ["FlashbangSpec", "FLASHBANG", "SocketDef", "LodQuality", "build_to", "assert_clean", "deny_hits",
           "D_MM", "DENSITY"]
