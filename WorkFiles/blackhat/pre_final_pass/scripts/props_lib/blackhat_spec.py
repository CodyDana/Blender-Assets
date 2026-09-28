#!/usr/bin/env python
"""props_lib.blackhat_spec - SM_BlackHat's build-to numbers, in one place.

Pure Python (no bpy, no numpy).  Every number comes from References/BlackHat/REFERENCE_SPEC.md
(the metrology of blackhat_guide.png; it takes precedence over BLACKHAT_STUDY.md where the two
differ) and carries its status the way the spec labels it: MEASURED / INFERRED / DESIGNED.
The build script reads this object, the report restates it, and nothing is typed twice.

UNITS: millimetres.  R is the outer radius of the rolled rim (DESIGNED D = 600 mm, R = 300 mm).

FRAME (DESIGNED, REFERENCE_SPEC 1 and 10):
    +Z up out of the crown; the hat axis is the Z axis; z = 0 is the BOTTOM of the rim tube
    (the hat's floor-contact plane) and the pivot is on the axis there.
    +X forward (the HEAD socket's forward); the knot is on the wearer's LEFT (+Y).
    theta is the spec's azimuth: 0 is the rim point nearest the reference camera, + toward
    image right.  World azimuth (from +X toward +Y) is phi = theta + PSI_DEG, so the knot
    (theta +61) sits at phi 90 (+Y) and the reference camera at phi +29.
    Export Forward -Y / Up Z (the pack's; Scripts/pipeline/export_fbx).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .spec import (PACK_LOD_REFERENCE_RADIUS_MM, PACK_LOD_SCREEN_SIZES, assert_clean, deny_hits,  # noqa: F401
                   scaled_lod_screen_sizes, screen_size_distance_m)

R_MM = 300.0                   # DESIGNED (REFERENCE_SPEC 10: D = 600 mm)
PSI_DEG = 29.0                 # DESIGNED: world azimuth of theta = 0 (knot on +Y)
SLOPE_DEG = 26.0               # MEASURED (INFERRED from H/R 0.488)
TAN_SLOPE = 0.4877             # H/R, MEASURED 0.488 +- 0.015 (camera model 2.6 R: 0.48768)


@dataclass(frozen=True)
class SocketDef:
    name: str
    position_mm: Tuple[float, float, float]
    rotation_deg: Tuple[float, float, float]
    use: str


@dataclass(frozen=True)
class RibSpec:
    #: 13 primary ribs (INFERRED count); the visible seven MEASURED, the far six DESIGNED
    visible_deg: Tuple[float, ...] = (-82.0, -54.5, -23.5, 7.6, 30.0, 58.0, 85.0)
    far_deg: Tuple[float, ...] = (112.7, 140.3, 167.9, 195.4, 223.0, 250.6)
    diameter_R: float = 0.011          # MEASURED 0.011 +- 0.003 R (3.3 mm)
    #: relief 0.6 - 1.0 x diameter (INFERRED): the rod's centre sits this many diameters above the skin
    centre_lift_d: float = 0.25
    twist_pitch_d: float = 1.6         # MEASURED (visual) rope twist pitch, x diameter
    rho_top: float = 0.080             # starts under the crown cap lip (cap radius 0.1055 R)

    @property
    def all_deg(self) -> Tuple[float, ...]:
        return tuple(sorted(self.visible_deg + self.far_deg))


@dataclass(frozen=True)
class RimSpec:
    tube_diameter_R: float = 0.044     # MEASURED +- 0.006 R (13.2 mm)
    cord_diameter_R: float = 0.005     # MEASURED +- 0.002 R binding cord on the inner top of the tube
    #: the skin's plane meets the tube this far above its centre, in tube radii (DESIGNED, tuned on the
    #: silhouette + rim-face measurement: the skin comes down onto the top of the roll)
    skin_entry_rt: float = -0.40
    #: binding-cord centre angle on the tube section, degrees from outward (+r) toward +z
    cord_angle_deg: float = 112.0
    lashing_width_R: float = 0.038     # MEASURED +- 0.005 R
    lashing_wraps: int = 3             # MEASURED exactly
    wrap_cord_R: float = 0.012         # INFERRED +- 0.003 R
    lashing_skin_reach_R: float = 0.015  # MEASURED: reaches ~0.015 R onto the skin
    #: MEASURED lashing azimuths (REFERENCE_SPEC 6); the rest follow the rule "one at every rib end
    #: plus one inside every bay" (DESIGNED on the far side: rib ends and bay midpoints)
    at_ribs_measured: Tuple[Tuple[float, float], ...] = ((-54.5, -53.7), (-23.5, -22.1), (7.6, 7.65),
                                                         (30.0, 30.0), (58.0, 58.35))
    in_bays_measured: Tuple[float, ...] = (-67.0, -32.5, -9.0, 17.1, 42.75)


@dataclass(frozen=True)
class CapSpec:
    radius_R: float = 0.1055           # MEASURED +- 0.008 R
    lid_slope_deg: float = 20.0        # INFERRED +- 5
    top_below_apex_R: float = 0.0      # INFERRED 0.005 (fitted to the crown-top row: 0.0)
    lip_R: float = 0.008               # INFERRED lip thickness / overhang (0.004 - 0.012 R)


@dataclass(frozen=True)
class BandSpec:
    ring_rho: float = 0.365            # MEASURED +- 0.015
    cloth_width_R: float = 0.10        # INFERRED flat cloth width
    thickness_R: float = 0.004         # DESIGNED cloth thickness
    roll_width_R: float = 0.011        # MEASURED 0.010 +- 0.003 (twisted, cord-like) for theta < -20
    width_at_0_R: float = 0.04         # MEASURED
    width_at_30_R: float = 0.11        # MEASURED (fanned)
    lower_edge_rho_at_knot: float = 0.51  # MEASURED: dips to rho 0.51 just before the knot
    knot_theta: float = 61.0           # MEASURED +- 5
    knot_rho: float = 0.43             # MEASURED +- 0.04
    knot_size_R: Tuple[float, float] = (0.08, 0.09)   # MEASURED +- 0.02


@dataclass(frozen=True)
class TailSpec:
    name: str
    leave_theta: float                 # MEASURED 64
    leave_rho: float                   # MEASURED 0.51
    rim_theta: float                   # MEASURED A 31 / B 40
    width_R: Tuple[float, float]       # MEASURED (near the knot, below the rim; below-rim set to the face-on
    #                                    reading of the measured 28-34 / 36-39 px at the hang's 1.3-1.4 px/mm)
    length_R: float                    # INFERRED knot to tip
    hang_R: float                      # MEASURED hang below the rim
    tip_px: Tuple[float, float]        # MEASURED image position of the tip (reference camera)
    tear_R: float                      # MEASURED length of the diagonal tear
    twist_deg: float                   # MEASURED A turned 60-90 deg for 0.15 R after the knot
    twist_len_R: float
    stand_off_R: float                 # B stands slightly off the cone near the rim
    notch: bool                        # B: one deep notch splitting off a sliver


TAILS = (
    TailSpec("A", 64.0, 0.51, 31.0, (0.072, 0.080), 0.99, 0.30, (592.0, 533.0), 0.18, 75.0, 0.15, 0.0, False),
    TailSpec("B", 64.0, 0.51, 38.5, (0.094, 0.097), 0.96, 0.32, (643.0, 520.0), 0.25, 0.0, 0.0, 0.012, True),
)


@dataclass(frozen=True)
class CameraSpec:
    """REFERENCE_SPEC 1, the joint fit at d = 2.6 R (bh_s07_joint.json '2.6'), in the metrology
    frame: rim outline circle radius 1 at z = 0, camera on -Y, image right = +X."""
    distance_R: float = 2.6
    elevation_deg: float = 17.029856059141743
    f_px: float = 796.6851011045686
    u0: float = 332.96565486121455
    v0: float = 291.94479499342003
    roll_deg: float = -0.5050076663300229    # the fit at 2.6 R (spec: content 0.51 deg clockwise)
    res: Tuple[int, int] = (670, 599)
    #: the metrology frame's z = 0 (its fitted rim-outline circle) above OUR z = 0 (the tube
    #: bottom), in R.  DESIGNED/TUNED by measuring the render's silhouette against REFERENCE_SPEC 1
    z_offset_R: float = 0.008


@dataclass(frozen=True)
class BlackHatSpec:
    name: str = "BlackHat"
    mesh_name: str = "SM_BlackHat"
    straw_material: str = "M_BlackHat_Straw"
    cloth_material: str = "M_BlackHat_Cloth"
    straw_stem: str = "T_BlackHat_Straw"
    cloth_stem: str = "T_BlackHat_Cloth"
    R: float = R_MM
    #: the skin (outer woven surface) is a straight cone of slope 26 deg; its virtual apex is
    #: placed from the rim tube (RimSpec.skin_entry_rt)
    slope_deg: float = SLOPE_DEG
    tan_slope: float = TAN_SLOPE
    skin_thickness_R: float = 0.006    # DESIGNED (REFERENCE_SPEC 10)
    ribs: RibSpec = RibSpec()
    rim: RimSpec = RimSpec()
    cap: CapSpec = CapSpec()
    band: BandSpec = BandSpec()
    tails: Tuple[TailSpec, ...] = TAILS
    camera: CameraSpec = CameraSpec()
    #: textures: two sets (straw / cloth), 2048 each (the house prop size; see the report)
    texture_size: int = 2048
    padding_px: int = 8
    seed: int = 7
    #: mass (DESIGNED, the study: 0.21 - 0.30 kg for a 50 cm kasa; ours is 60 cm)
    mass_g: float = 300.0
    #: triangle bands per LOD (the report justifies LOD0 above 10k: 26 lashings x 3 wraps as geometry)
    lod_bands: Tuple[Tuple[int, int], ...] = ((12000, 20000), (4000, 9000), (1200, 3200))
    head_circumference_mm: float = 570.0

    # ------------------------------------------------------------------ derived
    @property
    def rt(self) -> float:
        return 0.5 * self.rim.tube_diameter_R * self.R

    @property
    def rim_centre_radius(self) -> float:
        return self.R - self.rt

    @property
    def tube_centre_z(self) -> float:
        return self.rt

    @property
    def apex_z(self) -> float:
        """The skin cone's virtual apex height above z = 0."""
        z_entry = self.tube_centre_z + self.rim.skin_entry_rt * self.rt
        return z_entry + self.rim_centre_radius * self.tan_slope

    def skin_z(self, r_mm: float) -> float:
        return self.apex_z - r_mm * self.tan_slope

    @property
    def head_sphere_radius_mm(self) -> float:
        return self.head_circumference_mm / (2.0 * math.pi)

    def head_seat_z(self) -> float:
        """HEAD socket (DESIGNED, REFERENCE_SPEC 10): a 57 cm head (sphere r = C / 2 pi) inscribed
        in the INNER cone (half-angle 90 - slope) touches it with its top 0.113 r below the inner
        apex (r / sin(half) - r)."""
        half = math.radians(90.0 - self.slope_deg)
        r = self.head_sphere_radius_mm
        inner_apex = self.apex_z - self.skin_thickness_R * self.R / math.cos(math.radians(self.slope_deg))
        return inner_apex - (r / math.sin(half) - r)

    def sockets(self) -> Tuple[SocketDef, ...]:
        return (SocketDef("HEAD", (0.0, 0.0, round(self.head_seat_z(), 3)), (0.0, 0.0, 0.0),
                          "the crown seat: where the top of a 57 cm head touches the inner cone. +Z up out "
                          "of the crown, +X forward (the knot on the wearer's left, +Y). Attach to the head "
                          "bone with SnapToTarget; tune the offset per character"),)

    def lod_screen_sizes(self, radius_mm: float) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm)

    def switch_distances_m(self, radius_mm: float) -> List[float]:
        return [round(screen_size_distance_m(s, radius_mm * 0.001), 4) for s in self.lod_screen_sizes(radius_mm)[1:]]

    def world_phi_deg(self, theta_deg: float) -> float:
        return theta_deg + PSI_DEG


BLACK_HAT = BlackHatSpec()


def lashing_azimuths(s: BlackHatSpec = BLACK_HAT) -> List[Tuple[float, str]]:
    """26 lashings: every rib end plus one per bay.  MEASURED where REFERENCE_SPEC 6 gives one,
    else at the rib (rib ends) or the bay midpoint (DESIGNED far side and the side bays)."""
    ribs = list(s.ribs.all_deg)
    at = dict(s.rim.at_ribs_measured)
    out = []
    for i, rb in enumerate(ribs):
        out.append((at.get(rb, rb), "rib"))
        nxt = ribs[(i + 1) % len(ribs)] + (360.0 if i == len(ribs) - 1 else 0.0)
        inb = [b for b in s.rim.in_bays_measured if rb < b < nxt]
        out.append((inb[0] if inb else 0.5 * (rb + nxt), "bay"))
    return [((a + 180.0) % 360.0 - 180.0, k) for a, k in out]


def build_to(s: BlackHatSpec = BLACK_HAT) -> Dict[str, object]:
    return {
        "name": s.name, "mesh": s.mesh_name, "materials": [s.straw_material, s.cloth_material],
        "textures": [f"{st}_{k}" for st in (s.straw_stem, s.cloth_stem) for k in ("BC", "ORM", "N", "Detail")],
        "texture_size": s.texture_size, "R_mm": s.R, "D_mm": 2 * s.R,
        "cone": {"slope_deg": s.slope_deg, "H_over_R": s.tan_slope, "apex_z_mm": round(s.apex_z, 3),
                 "skin_thickness_mm": s.skin_thickness_R * s.R},
        "rim": {"tube_diameter_mm": s.rim.tube_diameter_R * s.R, "cord_mm": s.rim.cord_diameter_R * s.R,
                "lashings": len(lashing_azimuths(s)), "wraps": s.rim.lashing_wraps,
                "wrap_cord_mm": s.rim.wrap_cord_R * s.R},
        "ribs": {"count": len(s.ribs.all_deg), "azimuths_deg": list(s.ribs.all_deg),
                 "diameter_mm": s.ribs.diameter_R * s.R},
        "cap": {"radius_mm": s.cap.radius_R * s.R, "lid_slope_deg": s.cap.lid_slope_deg},
        "band": {"ring_rho": s.band.ring_rho, "knot_theta": s.band.knot_theta, "knot_rho": s.band.knot_rho,
                 "cloth_width_mm": s.band.cloth_width_R * s.R, "thickness_mm": s.band.thickness_R * s.R},
        "tails": [{"name": t.name, "rim_theta": t.rim_theta, "length_mm": t.length_R * s.R,
                   "tear_mm": t.tear_R * s.R} for t in s.tails],
        "mass_g": s.mass_g, "lod_bands": [list(b) for b in s.lod_bands],
        "pack_lod_rule": {"sizes": list(PACK_LOD_SCREEN_SIZES), "reference_radius_mm": PACK_LOD_REFERENCE_RADIUS_MM},
        "sockets": [{"name": k.name, "position_mm": list(k.position_mm), "rotation_deg": list(k.rotation_deg),
                     "use": k.use} for k in s.sockets()],
        "frame": "+Z up, +X forward, knot on +Y (wearer's left), z = 0 at the rim-tube bottom, pivot on the axis",
    }


__all__ = ["BlackHatSpec", "BLACK_HAT", "SocketDef", "RibSpec", "RimSpec", "CapSpec", "BandSpec", "TailSpec",
           "CameraSpec", "TAILS", "R_MM", "PSI_DEG", "lashing_azimuths", "build_to", "assert_clean", "deny_hits"]
