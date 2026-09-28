#!/usr/bin/env python
"""props_lib.fan_spec - SK_Fan's build-to numbers (the folding fan, sensu), pure Python.

Every number comes from ``References/Fan/REFERENCE_SPEC.md`` (RS) or ``References/Fan/FAN_STUDY.md``
(FS) and carries its status: MEASURED / INFERRED / DESIGNED (RS) or SOURCED / DERIVED / ESTIMATE (FS).
Where the build moved a number, the reason is on the constant.

FRAME (FS 3).  Origin at the rivet centre on the stick stack's mid-plane.  Z is the rivet axis, +Z comes
out of the FRONT (the side fan2 shows).  The front guard ``stick_00`` is the HELD guard: it lies along +X
in every pose, and the fan opens counter-clockwise seen from +Z (fan2: front guard at image right,
everything else at larger image angles).  Millimetres.  Export is Forward -Y / Up Z like the pack.

THE MECHANISM (why the numbers below are what they are; the full argument is in FAN_REPORT.md 3)

* Sticks are stacked on the rivet: front guard on top (+Z), inner ribs 1..24 below it, rear guard at
  the bottom.  A rib's thickness is its Z pitch.
* The leaf is 25 identical pleats (50 faces).  It is hinged to each stick along one LEAF LINE, a radial
  line fixed in that stick.  ROUND 2 (measured on fan2 against the round-1 render, FAN_REPORT 1 D2): the
  leaf lines are the MOUNTAINS seen from the front (the silk draped over each rib: fan2's soft rounded
  ridges) and the mid-gap folds are the VALLEYS (-Z: fan2's sharp dark creases, where its edge notches
  are).  Round 1 had them the other way round, which put every lit face where fan2 has an unlit one.
* Every face is a rigid panel (its own bone), so it never stretches and its normals are exact.
* The front guard lies OVER the leaf and every face falls away from it (-Z), so leaf line 0 may lie
  under the guard (``leaf_off_front_deg``, measured: 1.27 deg inside its axis, by the guard's inner edge).
  Leaf line 0 lies one leaf pitch above rib 1's leaf line, so the stack has a gap of that size under the
  front guard (the leaf's first panel is glued there, as on a real fan); a spacer on the guard's bone fills
  it in the bare zone.  The rear guard lies behind everything and the last face falls toward it, so its
  leaf line is at the guard's INNER edge (``leaf_off_rear_deg`` inboard of its axis; in the leaf zone the
  guard's inner edge is brought to that line) and the leaf reaches over the guard as a glued flap to
  fan2's leaf corner.
* The 26 stick AXES keep fan2's uniform pitch (RS 3); the 25 leaf gaps are equal (so every pleat folds
  the same way at the same moment).  Each stick carries its leaf line at a fixed offset from its axis,
  linear from ``leaf_off_front_deg`` (front guard) to ``leaf_off_rear_deg`` (rear guard).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .spec import (PACK_LOD_SCREEN_SIZES, PROP_TRIANGLE_BUDGET, deny_hits, assert_clean,  # noqa: F401
                   scaled_lod_screen_sizes, screen_size_distance_m)

D2R = math.pi / 180.0
STACK_CLEARANCE_MM = 0.005


@dataclass(frozen=True)
class TasselSpec:
    """RS 8 (fan2 only; a separate optional piece).  Lengths in L."""
    cord_d_L: float = 0.010            # MEASURED, diameter
    rivet_to_knot_L: float = 0.19      # MEASURED, rivet to the knot's top
    knot_len_L: float = 0.047          # MEASURED
    knot_w_L: float = 0.046            # MEASURED
    neck_len_L: float = 0.017          # MEASURED, binding under the knot
    neck_w_L: float = 0.025            # MEASURED
    skirt_len_L: float = 0.373         # MEASURED
    #: skirt width profile (distance below the skirt top in L, width in L): MEASURED
    skirt_width_L: Tuple[Tuple[float, float], ...] = ((0.0, 0.029), (0.06, 0.050), (0.1865, 0.063),
                                                      (0.358, 0.083), (0.373, 0.083))
    ragged_L: float = 0.015            # MEASURED, thread tips at the end
    fullness_L: float = 0.070          # DESIGNED, bundle thickness at mid length
    emerge_L: float = 0.110            # MEASURED, where the cord emerges from behind the lobe
    photo_heading_deg: float = -160.0  # MEASURED (-159.7), the flat-lay direction in fan2
    colour_linear: Tuple[float, float, float] = (0.0072, 0.0091, 0.0136)   # RS 9, #14181F


@dataclass(frozen=True)
class FanSpec:
    name: str = "Fan"
    mesh_name: str = "SK_Fan"
    tassel_name: str = "SK_Fan_Tassel"
    skeleton_name: str = "SK_Fan_Skeleton"
    L: float = 190.0                   # DESIGNED (RS 0): pivot to guard tip = leaf outer radius

    # ------------------------------------------------------------------ sticks (RS 2 - 5)
    n_sticks: int = 26                 # MEASURED: 2 guards + 24 inner ribs, 25 gaps
    opening_deg: float = 163.2         # MEASURED, guard axis to guard axis (the bind pose)
    #: leaf line 0 relative to the front guard's axis (+ = toward the leaf) and leaf line 25 relative to the rear
    #: guard's axis (+ = away from the leaf).  MEASURED (round 2) on fan2's silhouette: its 24 visible edge notches
    #: (the valleys) lie at 14.35 + 6.49 k deg in the photo, 2.2 deg past a first round-2 trial's; a least-squares
    #: fit of the two offsets to them gives +1.27 / -0.30 (rms 0.55 deg, within the notches' own scatter).  fan2's
    #: first mountain then shows just inside the front guard's inner edge, as in the photo.  The rear offset is
    #: held at -0.30 (fan2 alone would put it 0.75 deg OUTSIDE the axis): the last face falls toward the rear
    #: guard, so leaf line 25 must lie on the guard's inner edge, which the build narrows to it in the leaf zone
    #: (hidden under the glued flap from the front)
    leaf_off_front_deg: float = 1.27
    leaf_off_rear_deg: float = -0.30
    hinge_margin_mm: float = 0.03   # a guard's inner edge stops this far short of the leaf line
    butt_L: float = 0.106              # MEASURED, butt below the pivot (lobe radius)
    rib_w_pivot_L: float = 0.030       # DESIGNED (RS 4), straight taper
    #: RS 4 measures 0.041 L of VISIBLE (lit) rib at the leaf edge with a 2 - 3 px dark boundary and
    #: says the ribs almost touch: the physical rib spans the pitch arc (0.049 L) with rounded edges
    #: round 2: 0.056 L, so neighbouring ribs overlap ~1 mm under each other at the leaf edge (stacked plates): at
    #: 0.0495 L the tips only just met and the chamfered corners let daylight through at every rib (blind test)
    rib_w_leaf_L: float = 0.056
    #: RS 4 DESIGNED 0.85 mm (a 24.2 mm stack); FS 3 SOURCED a comparable closed fan at 12.7 mm (0.5 in),
    #: which with two 1.9 mm guards is 0.37 mm per rib (FS open question 2).  The build takes the SOURCED
    #: figure: the stacked leaf cannot fold exactly (FAN_REPORT 3), and the crack left between its rigid
    #: faces grows in proportion to this pitch (0.85 mm: ~0.2 mm; 0.37 mm: under 0.1 mm)
    rib_thick_mm: float = 0.37
    #: the bare rib stops this far inside the leaf's inner edge.  Round 1 kept 0.18 mm (and hid it with slips under
    #: the leaf); round 2's valleys fall behind the leaf lines, where no slip fits, and the 0.18 mm ring showed
    #: daylight between the rib tips and the leaf.  0.10 mm: the closing pleats' valley corners come in over the
    #: rib tips near 5 - 10 deg open (0.05 mm touched them there); the fold proof finds no contact at 0.10
    rib_end_gap_mm: float = 0.10
    rib_shoulder_r_mm: float = 0.12   # round 2: near-square shoulders, so neighbouring rib tips meet (0.6 let daylight through)
    #: ROUND 3 (maintainer): the LEAF-ZONE PRONG.  Every stick but the rear guard carries a thin plate on its own bone that
    #: runs on past its rib tip into the leaf zone, glued over the leaf's inner margin (as a real fan's ribs run on
    #: under/over the silk there): the prongs shingle like the ribs, so from the front the leaf's inner edge sits under
    #: one continuous dark band (fan2's) and the valley notches under it no longer let daylight through.  DESIGNED from
    #: the fold (WorkFiles/fan/FAN_REPORT.md, round 3): a face falls away (-Z) from its leaf line on the + side and
    #: swings through the vertical UNDER that line as the fan closes, so nothing may sit under a leaf line; on the + side
    #: of a leaf line, beyond ``prong_clear_mm``, the face is always deeper than the prong (open: 0.37 mm below the leaf
    #: line at 0.9 mm; closing: steeper), and every other face hangs below its own, lower, leaf line.  So a prong on the
    #: + side, reaching over the gap and over the next leaf line (0.375 mm lower, 0.095 mm under the prong), clears the
    #: leaf at every opening.  Nothing can go on the - side (the closed pages lie there)
    #: past the silk's inner edge r_in, to the visible leaf edge.  MEASURED (see-through samples round the inner edge,
    #: LOD0, WorkFiles/fan/round3/st_*.json): 2.3 mm left rim-oblique 45 deg holes at every opening 36 - 123 deg; 4 mm
    #: cleared 45 deg but the round-2 Unreal review's rim camera (~20 - 27 deg) still saw a dotted row (208 px at
    #: 122.8 deg); 5.9 mm clears 30 deg at 122.8 deg and cuts 20 - 25 deg by 3 - 10x
    prong_reach_mm: float = 5.9
    prong_thick_mm: float = 0.20       # down from the stick's top face (a rib is 0.37 mm)
    prong_clear_mm: float = 0.90       # its + side starts this far from its own leaf line
    prong_overlap_mm: float = 0.30     # it ends this far past the next prong's start (shingled, no gap from the front)
    guard_thick_mm: float = 1.9        # DESIGNED (RS 5, 0.010 L)
    #: guard visible width (x in L, width in L): MEASURED (RS 5), the 1.0 L value extrapolated
    guard_width_L: Tuple[Tuple[float, float], ...] = ((-0.106, 0.036), (0.0, 0.037), (0.17, 0.039),
                                                      (0.29, 0.039), (0.47, 0.034), (0.58, 0.034),
                                                      (0.76, 0.041), (0.93, 0.047), (1.0, 0.048))
    guard_tip_round_mm: float = 1.0    # square tip, softened corners (RS 5)
    guard_edge_round_mm: float = 0.45  # rounded long edges, the inner-edge highlight (RS 5)
    rib_edge_round_mm: float = 0.28

    # ------------------------------------------------------------------ leaf (RS 7)
    #: ROUND 3: the leaf's VISIBLE inner edge is the outer edge of the prong band (``prong_reach_mm``, below), which is
    #: glued over the silk's inner margin; the silk itself runs on under the band (DESIGNED, as a real leaf is glued
    #: over the rib tips).  The visible edge sits at 0.437 L, inside RS 7's 0.431 L +- 0.012 L (1.1 mm, 2 px in fan2's
    #: frame, outward), so that the band can be 5.9 mm wide while the rib tips (the band's inner step) stay inside RS 4's
    #: rounded-shoulder row (0.415 - 0.431 L +- 0.01 L): they sit at 0.4054 L.  The band's width is what blocks daylight
    #: through the valley notches from low oblique views (WorkFiles/fan/round3/st_vis437_*.json)
    leaf_visible_in_L: float = 0.437   # DESIGNED within RS 7's MEASURED 0.431 L +- 0.012 L
    leaf_in_L: float = 0.437 - 5.9 / 190.0   # DESIGNED: the silk's own inner edge, under the prong band
    leaf_out_L: float = 1.000          # MEASURED
    face_tilt_deg: float = 20.0        # INFERRED (13 - 30): the faces' tilt out of the fan plane, open
    #: RS 7 MEASURED 0.0066 L peak to trough in fan2's view; the pleats' own depth adds to what the camera
    #: sees, so the leaf's in-plane scallop is smaller (tuned on the reference render: round 1's 0.0066 L
    #: read 1.5x fan2's ripple; round 2's valleys falling 3.9 mm behind the leaf lines alone give ~2.8 px of fan2's
    #: 3.0 px in its view, so the in-plane scallop left is 0.19 mm).  Bumps at the mountains (ribs), notches at the valleys (mid-gap), a
    #: sinusoid along the edge (fan2's gentle ripple, not a zigzag)
    scallop_L: float = 0.0010
    #: the leaf corner over the rear guard (RS 2: 173.8 vs its axis at 172.6): the glued flap reaches this far
    #: past the rear guard's axis at 0.99 L
    #: the rear guard's OUTER silhouette is a straight line in fan2 (image line through (60, 508.1) and
    #: (330, 547.8) px, WorkFiles/fan/measure/fan_edge_lines.py), mapped onto the rear guard's plane through RS 1's
    #: camera: (x along the guard mm, lateral mm) - it is wider toward the pivot than the front guard (MEASURED;
    #: RS 5 designed the rear guard as the front one mirrored).  Its visible width stays RS 5's.
    rear_guard_outer_mm: Tuple[Tuple[float, float], ...] = ((37.5, 5.58), (191.2, 3.22))
    rear_flap_past_axis_deg: float = 0.95        # the leaf's corner ends on that silhouette (RS 2: 173.8 deg)
    leaf_on_rib_mm: float = 0.03       # > the leaf back layer (0.02 mm behind the front)
    #: the leaf lines' own pitch beyond the rib ends: a rib's top also carries a short slip (its -y half, to
    #: 0.8 mm past the leaf's inner edge) that hides the daylight under the raised inner corners of the pleats
    rib_slip_past_leaf_mm: float = 0.8

    # ------------------------------------------------------------------ rivet (RS 6)
    rivet_head_d_L: float = 0.035      # MEASURED, eyelet ring
    rivet_hole_d_L: float = 0.017      # MEASURED, the dark hollow centre
    rivet_proud_L: float = 0.006       # DESIGNED, each head
    rivet_shaft_d_mm: float = 3.9      # DESIGNED, the eyelet's barrel through the stack
    #: round 3: brighter, mirror-polished (fan2's ring reads bright with a white glint; round 2's read dull grey)
    rivet_colour_linear: Tuple[float, float, float] = (0.80, 0.78, 0.74)  # polished nickel / silver-plate F0

    # ------------------------------------------------------------------ colour (RS 9)
    leaf_colour_linear: Tuple[float, float, float] = (0.0199, 0.0245, 0.0299)   # #272B30
    sticks_colour_linear: Tuple[float, float, float] = (0.0151, 0.0191, 0.0213)  # #212628

    tassel: TasselSpec = field(default_factory=TasselSpec)

    # ------------------------------------------------------------------ assets
    texture_size: int = 2048
    tassel_texture_size: int = 1024
    rivet_texture_size: int = 256
    mass_g: float = 22.0               # FS 2.8 SOURCED 20 - 24 g
    tassel_mass_g: float = 3.0         # FS 2.8 ESTIMATE 2 - 4 g
    #: round 2: the leaf is cut into strips (the sinusoidal edge, the convex shading, the tapered back layer)
    lod_bands: Tuple[Tuple[int, int], ...] = ((3000, 6000), (1500, 3000), (500, 1500))
    tassel_lod_bands: Tuple[Tuple[int, int], ...] = ((500, 1500), (150, 500), (50, 200))

    # ------------------------------------------------------------------ derived
    @property
    def stick_pitch_deg(self) -> float:
        return self.opening_deg / (self.n_sticks - 1)

    @property
    def leaf_pitch_deg(self) -> float:
        a, b = self.leaf_off_front_deg, self.leaf_off_rear_deg
        return (self.opening_deg + b - a) / (self.n_sticks - 1)

    @property
    def front_gap_mm(self) -> float:
        """the gap under the front guard (leaf line 0 is one pitch above rib 1's and 0.03 mm under the guard)"""
        return self.leaf_z_pitch + 2 * self.leaf_on_rib_mm

    @property
    def face_angle_deg(self) -> float:
        """beta: the angle each of the 50 faces spans in the flat leaf (RS 7's construction)."""
        h = 0.5 * self.leaf_pitch_deg * D2R
        return math.atan(math.tan(h) / math.cos(self.face_tilt_deg * D2R)) / D2R

    @property
    def unfolded_leaf_deg(self) -> float:
        return 2 * (self.n_sticks - 1) * self.face_angle_deg

    @property
    def gamma_deg(self) -> float:
        """elevation of a mid-gap fold above the fan plane in the open pose (unstacked model)."""
        b = self.face_angle_deg * D2R
        h = 0.5 * self.leaf_pitch_deg * D2R
        return math.acos(min(1.0, math.cos(b) / math.cos(h))) / D2R

    @property
    def r_in(self) -> float:
        return self.leaf_in_L * self.L

    @property
    def r_out(self) -> float:
        return self.leaf_out_L * self.L

    @property
    def butt_mm(self) -> float:
        return self.butt_L * self.L

    @property
    def stack_mm(self) -> float:
        return 2 * self.guard_thick_mm + self.front_gap_mm + (self.n_sticks - 2) * self.stack_pitch_mm

    @property
    def stack_pitch_mm(self) -> float:
        """a rib's Z pitch: its thickness plus a 5 um clearance, so stacked plates touch but never overlap
        after a float32 round trip (FBX)"""
        return self.rib_thick_mm + STACK_CLEARANCE_MM

    def stick_z(self, i: int) -> Tuple[float, float]:
        """(bottom, top) of stick i in Z: front guard on top."""
        top = 0.5 * self.stack_mm
        g = self.guard_thick_mm
        if i == 0:
            return top - g, top
        if i == self.n_sticks - 1:
            return -0.5 * self.stack_mm, -0.5 * self.stack_mm + g
        t0 = top - g - self.front_gap_mm - (i - 1) * self.stack_pitch_mm
        return t0 - self.rib_thick_mm, t0

    @property
    def leaf_z_pitch(self) -> float:
        """the leaf lines step down one rib pitch per stick"""
        return self.stack_pitch_mm

    @property
    def leaf_z0(self) -> float:
        """The leaf lies ON its ribs: leaf line i (1..24) is ``leaf_on_rib_mm`` above rib i's top face (the ribs are
        glued behind the silk, RS 7), and the 25 steps are all one pitch.  So the front guard's leaf line is one
        pitch above rib 1's, 0.03 mm under the front guard (``front_gap_mm``), and the rear guard's is just
        above the rear guard's top face, where the glued flap lies."""
        return self.stick_z(1)[1] + self.leaf_on_rib_mm + self.leaf_z_pitch

    @property
    def leaf_z25(self) -> float:
        return self.leaf_z0 - (self.n_sticks - 1) * self.leaf_z_pitch

    def leaf_line_z(self, i: int) -> float:
        return self.leaf_z0 - i * self.leaf_z_pitch

    def leaf_line_offset_deg(self, i: int) -> float:
        """leaf line angle minus stick axis angle (fixed in the stick)."""
        a, b = self.leaf_off_front_deg, self.leaf_off_rear_deg
        return a + (b - a) * i / (self.n_sticks - 1)

    def stick_axis_deg(self, i: int, s: float) -> float:
        """axis angle of stick i at openness s (0 closed .. 1 = the bind/open pose); stick_00 at 0."""
        return self.leaf_line_deg(i, s) - self.leaf_line_offset_deg(i)

    def leaf_line_deg(self, i: int, s: float) -> float:
        return self.leaf_off_front_deg + i * s * self.leaf_pitch_deg

    def opening_at(self, s: float) -> float:
        """guard axis to guard axis at openness s."""
        return self.stick_axis_deg(self.n_sticks - 1, s)

    def s_for_opening(self, opening_deg: float) -> float:
        n = self.n_sticks - 1
        a, b = self.leaf_off_front_deg, self.leaf_off_rear_deg
        return max(0.0, (opening_deg - a + b) / (n * self.leaf_pitch_deg))

    @property
    def rivet_head_r(self) -> float:
        return 0.5 * self.rivet_head_d_L * self.L

    @property
    def rivet_hole_r(self) -> float:
        return 0.5 * self.rivet_hole_d_L * self.L

    @property
    def rivet_proud(self) -> float:
        return self.rivet_proud_L * self.L

    def guard_width_mm(self, x_mm: float) -> float:
        xs = [p[0] * self.L for p in self.guard_width_L]
        ws = [p[1] * self.L for p in self.guard_width_L]
        if x_mm <= xs[0]:
            return ws[0]
        for (x0, w0), (x1, w1) in zip(zip(xs, ws), zip(xs[1:], ws[1:])):
            if x_mm <= x1:
                u = (x_mm - x0) / (x1 - x0)
                u = u * u * (3 - 2 * u)
                return w0 + (w1 - w0) * u
        return ws[-1]

    def rib_width_mm(self, x_mm: float) -> float:
        a, b = self.rib_w_pivot_L * self.L, self.rib_w_leaf_L * self.L
        if x_mm <= 0.0:
            return a
        return a + (b - a) * min(1.0, x_mm / self.r_in)

    def lod_screen_sizes(self, radius_mm: float) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm)

    def switch_distances_m(self, radius_mm: float) -> List[float]:
        return [round(screen_size_distance_m(s, radius_mm / 1000.0), 4)
                for s in self.lod_screen_sizes(radius_mm)[1:]]

    # names
    @property
    def bone_names(self) -> List[str]:
        return (["pivot"] + [f"stick_{i:02d}" for i in range(self.n_sticks)]
                + [f"leaf_{j:02d}" for j in range(2 * (self.n_sticks - 1))])

    @property
    def materials(self) -> Dict[str, str]:
        return {"leaf": "M_Fan_Leaf", "sticks": "M_Fan_Sticks", "rivet": "M_Fan_Rivet", "tassel": "M_Fan_Tassel"}

    @property
    def texture_stems(self) -> Dict[str, str]:
        return {"leaf": "T_Fan_Leaf", "sticks": "T_Fan_Sticks", "rivet": "T_Fan_Rivet", "tassel": "T_Fan_Tassel"}


FAN = FanSpec()


def build_to(spec: FanSpec = FAN) -> Dict[str, object]:
    return {
        "asset": spec.mesh_name, "tassel": spec.tassel_name, "skeleton": spec.skeleton_name,
        "L_mm": spec.L, "closed_length_mm": round(spec.L + spec.butt_mm, 2),
        "sticks": spec.n_sticks, "opening_deg": spec.opening_deg,
        "stick_pitch_deg": round(spec.stick_pitch_deg, 4), "leaf_pitch_deg": round(spec.leaf_pitch_deg, 4),
        "leaf_line_offsets_deg": [spec.leaf_off_front_deg, spec.leaf_off_rear_deg],
        "folds": "leaf lines (ribs) = mountains from the front, mid-gap folds = valleys",
        "face_angle_deg": round(spec.face_angle_deg, 4), "unfolded_leaf_deg": round(spec.unfolded_leaf_deg, 3),
        "gamma_open_deg": round(spec.gamma_deg, 4),
        "pleat_depth_open_mm": {"leaf_edge": round(spec.r_out * math.sin(spec.gamma_deg * D2R), 3),
                                "leaf_base": round(spec.r_in * math.sin(spec.gamma_deg * D2R), 3)},
        "front_gap_mm": round(spec.front_gap_mm, 4),
        "leaf_radii_mm": [round(spec.r_in, 3), round(spec.r_out, 3)],
        "scallop_mm": round(spec.scallop_L * spec.L, 3),
        "butt_mm": round(spec.butt_mm, 3),
        "rib_width_mm": [round(spec.rib_width_mm(0.0), 3), round(spec.rib_width_mm(spec.r_in), 3)],
        "rib_thick_mm": spec.rib_thick_mm, "guard_thick_mm": spec.guard_thick_mm,
        "stack_mm": round(spec.stack_mm, 3), "leaf_z_pitch_mm": round(spec.leaf_z_pitch, 5),
        "rivet": {"head_d_mm": round(2 * spec.rivet_head_r, 3), "hole_d_mm": round(2 * spec.rivet_hole_r, 3),
                  "proud_mm": round(spec.rivet_proud, 3), "shaft_d_mm": spec.rivet_shaft_d_mm},
        "bones": len(spec.bone_names) + 1,
        "materials": list(spec.materials.values()),
        "textures": [f"{v}_{k}" for v in spec.texture_stems.values() for k in ("BC", "ORM", "N", "Detail")],
        "mass_g": spec.mass_g,
        "colours_linear": {"leaf": spec.leaf_colour_linear, "sticks": spec.sticks_colour_linear,
                           "tassel": spec.tassel.colour_linear, "rivet": spec.rivet_colour_linear},
    }


__all__ = ["FanSpec", "TasselSpec", "FAN", "build_to", "deny_hits", "assert_clean", "D2R"]
