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
    wall_mm: float = dmm(0.04)                              # 1.76 outer tube wall (spec 3: 0.03-0.05 D)
    inner_tube_r: float = dmm(0.76) / 2.0                   # 16.72 brass tube (spec 3)
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
    tube_seam_z: Tuple[float, ...] = (dmm(0.859) + 0.3, dmm(1.521) + 0.3, dmm(2.158) + 0.3)  # 0-3 px above centre
    #: FINALISE (craft + blind review: "a smooth brass egg"): through each hole the reference shows a vertical brass
    #: CYLINDER narrower than the hole with dark gaps both sides.  One brass can per hole column (radius can_r, axis
    #: at radius can_c), dark radial dividers between the columns (they also close the see-through at the limbs).
    can_r: float = 5.7
    can_c: float = 11.3
    can_arc_deg: float = 220.0
    # ------------------------------------------------------------------ base cap (spec 3)
    cap_apothem: float = 23.9                               # 12 flats; mean width 1.095 D = 48.2 (with the corners)
    cap_corner_r: float = 14.0                              # CHOICE: "corners are soft" - faint facet lines (p3 reads round)
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
        (18.4, dmm(0.94) / 2.0, 0.0, 2.0),   # outer rim; in a notch cut out 2.0 mm up through the foot edge
    )
    notch_foot_z: float = 2.0                               # the foot cut-out height (side views v1 / v3)
    notch_deg: Tuple[float, ...] = (-10.0, 62.0, 134.0, 206.0, 278.0)   # 5 notches, 72 deg pitch (p3: -10 ... )
    notch_w_mm: float = 5.0                                 # FINALISE: 4-5 mm blocky notches (was 2.2)
    # ------------------------------------------------------------------ fuze head (spec 5)
    housing_half: float = dmm(0.48) / 2.0                   # 10.56 square box
    housing_z0: float = dmm(3.158)                          # 138.95
    housing_z1: float = dmm(3.671)                          # 161.53
    housing_chamfer: float = 0.6
    plate_z1: float = dmm(3.732)                            # 164.21 top cover plate top
    plate_x: Tuple[float, float] = (-14.6, 12.8)            # FINALISE: overhang 4.0 mm = 0.09 D (craft: <= 0.07-0.1 D)
    plate_y: float = dmm(0.48) / 2.0 + 0.25                 # FINALISE: covers the housing top (no hidden +Z face)
    panel_proud: float = 1.0                                # FINALISE: the raised front panel on the -X face (v2)
    panel_y: float = 6.2                                    # its half width
    panel_slot: float = 0.7                                 # half width of its vertical slot
    panel_z: Tuple[float, float] = (141.5, 161.53)
    arm_curl_r: float = 2.1
    arm_curl_len: float = 11.0
    arm_pin_r: float = 0.85
    arm_pin_len: float = 13.6
    knuckle_r: float = dmm(0.137) / 2.0                     # 3.01
    knuckle_len: float = 15.2                               # FINALISE: fills the lever curl between its flanges (cheeks)
    knuckle_c: Tuple[float, float, float] = (18.0, -2.62, 160.64)  # top of the lever curl = overall top 165.9
    block_x: Tuple[float, float] = (10.2, 17.6)             # CHOICE: the hinge bracket carrying knuckle and pin
    block_y: Tuple[float, float] = (-8.3, 6.3)
    block_z: Tuple[float, float] = (151.3, 160.0)
    pin_boss_r: float = dmm(0.095) / 2.0                    # 2.09
    pin_boss_len: float = dmm(0.17)                         # 7.48
    pin_c: Tuple[float, float] = (15.4, dmm(3.514))         # (x, z) of the pin axis; z 154.6 (spec 2)
    pin_r: float = 1.0
    pin_head_r: float = 2.3                                 # FINALISE: the ring passes through the pin's head
    pin_head_len: float = 4.2                               # (the separate split-ring eyelet is gone)
    small_boss_r: float = dmm(0.057) / 2.0                  # 1.25 (v1 x185 y63 -> X +6.9, Z ~158.4)
    small_boss_c: Tuple[float, float] = (6.9, 158.4)
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
    ring_tilt_deg: float = 30.0                             # FINALISE: hangs 30 deg off the sleeve (v2 / v4 overhang)
    ring_yaw_deg: float = -10.0                             # CHOICE: v4 sees the ring ~72 deg from face-on
    # ------------------------------------------------------------------ mass (plan 1.2 / 6.3)
    mass_g: float = 300.0
    physics_mass_kg: float = 0.30
    lever_mass_kg: float = 0.015
    ring_mass_kg: float = 0.008
    grip_below_step_mm: float = 41.6                        # plan 3: half of an 83 mm four-finger span
    # ------------------------------------------------------------------ LODs
    lods: Tuple[LodQuality, ...] = (
        #  FINALISE: cell_v 2 (the cylinder needs no vertical splits), hole 24/16/12, inner 1x1, cap 3/2/1 per flat,
        #  tube = segments per brass can, ring 32x8 / 20x6 / 12x4 on one centreline, lever curl 10/5/3
        #          cell_u web_u cell_v hole  in_u in_v rev coll pl  cap/flat notch tube ring  sm eye  curl chamf band
        LodQuality(12, 6, 2, 24, 1, 1, 72, 32, 28, 3, True, 8, 32, 8, 12, 8, 4, 10, True, (5200, 6000), 2, True),
        LodQuality(8, 4, 1, 18, 1, 1, 48, 20, 16, 2, True, 8, 24, 8, 8, 6, 3, 5, True, (2500, 4000), 1, True),
        LodQuality(4, 2, 1, 16, 1, 1, 24, 16, 10, 1, False, 6, 24, 8, 6, 4, 3, 3, False, (800, 1700), 0, False),
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
        return round(self.block_y[0] - self.pin_boss_len - self.pin_head_len / 2.0, 3)


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
