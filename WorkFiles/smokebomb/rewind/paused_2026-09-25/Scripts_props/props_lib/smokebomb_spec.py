#!/usr/bin/env python
"""props_lib.smokebomb_spec - SM_SmokeBomb's build-to numbers, in one place (rewind build).

Pure Python.  Every number is labelled the way References/SmokeBomb/SMOKEBOMB_STUDY.md
labels them (SOURCED / DERIVED / ESTIMATE / MEASURED) or says where it comes from.  The
build script reads this object; the report restates it; nothing is typed twice.

The ball is ONE continuous cotton tape wound on a core (props_lib.smokebomb_wind: where it
runs; props_lib.smokebomb_tape: what it is; props_lib.smokebomb_ball: the game mesh).

FRAME: ball centre at the origin; the reference view is Blender's Front view (camera on
-Y looking +Y, image-right +X, image-up +Z).  Export Forward -Y / Up Z (the pack's).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .spec import (PACK_LOD_REFERENCE_RADIUS_MM, PACK_LOD_SCREEN_SIZES, scaled_lod_screen_sizes,
                   screen_size_distance_m)


@dataclass(frozen=True)
class SocketDef:
    name: str
    position_mm: Tuple[float, float, float]
    rotation_deg: Tuple[float, float, float]
    use: str


@dataclass(frozen=True)
class SmokeBombSpec:
    name: str = "SmokeBomb"
    mesh_name: str = "SM_SmokeBomb"
    material_name: str = "M_SmokeBomb"
    texture_stem: str = "T_SmokeBomb"
    #: study 4: 70 mm mean outline diameter (ESTIMATE, reasoned); the build solves the core so
    #: the reference view's outline has this mean diameter
    diameter_mm: float = 70.0
    #: study 4 / 5: a 10 mm x 0.5 mm cotton tape (SOURCED); the fitted winding's widths vary per
    #: pass (0.04 - 0.26 frac D, REFERENCE_SPEC 4.2) and the section is width-parametric
    tape_width_nominal_mm: float = 10.0
    tape_thickness_mm: float = 0.5
    #: textures.  BC and Detail at 4096 (DERIVED, justified in the report: the whole ball's
    #: exposed tape needs ~31,000 mm2 of atlas; 2048 gives 9.5 texels/mm, under the reference
    #: framing's 13.26 px/mm, where the 0.31 mm warp is 3 texels); ORM and N at the house 2048
    #: (the tape test measured no loss from them at half size)
    texture_sizes: Tuple[Tuple[str, int], ...] = (("BC", 4096), ("Detail", 4096), ("ORM", 2048), ("N", 2048))
    padding_px: int = 16
    seed: int = 1
    #: study 8: mass 121 g design (98 - 139 g), physics override 0.12 kg (DERIVED)
    mass_g: float = 121.0
    physics_mass_kg: float = 0.12
    #: triangle bands per LOD (DERIVED in the report: the rolled cords are geometry, 5 section
    #: intervals per exposed edge; LOD0 is used within 0.9 m only; LOD2 holds ~97 visible stretches
    #: of tape at 2 intervals across and 8 mm rings, which is what keeps its outline round)
    lod_bands: Tuple[Tuple[int, int], ...] = ((18000, 32000), (3000, 6500), (1000, 2400))
    sockets: Tuple[SocketDef, ...] = (
        SocketDef("Grip", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  "hand socket: the ball's centre in the palm; build frame, reference face -Y, +Z up"),
        SocketDef("Burst", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  "smoke spawn point: spawn with ABSOLUTE rotation so smoke rises however the ball lands"),
    )

    def texture_size(self, kind: str) -> int:
        return dict(self.texture_sizes)[kind]

    def lod_screen_sizes(self, radius_mm: float) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm)

    def switch_distances_m(self, radius_mm: float) -> List[float]:
        return [round(screen_size_distance_m(s, radius_mm * 0.001), 4)
                for s in self.lod_screen_sizes(radius_mm)[1:]]


SMOKE_BOMB = SmokeBombSpec()

#: the franchise deny gate (props_lib.spec.DENY_SUBSTRINGS) plus nothing smoke-specific
from .spec import assert_clean, deny_hits  # noqa: E402,F401


def build_to(s: SmokeBombSpec = SMOKE_BOMB) -> Dict[str, object]:
    return {
        "name": s.name, "mesh": s.mesh_name, "material": s.material_name,
        "textures": [f"{s.texture_stem}_{k}" for k, _ in s.texture_sizes],
        "texture_sizes": {k: v for k, v in s.texture_sizes}, "padding_px": s.padding_px,
        "diameter_mm": s.diameter_mm, "tape_nominal": {"width_mm": s.tape_width_nominal_mm,
                                                       "thickness_mm": s.tape_thickness_mm},
        "mass_g": s.mass_g, "physics_mass_kg": s.physics_mass_kg,
        "lod_bands": [list(b) for b in s.lod_bands],
        "pack_lod_rule": {"sizes": list(PACK_LOD_SCREEN_SIZES),
                          "reference_radius_mm": PACK_LOD_REFERENCE_RADIUS_MM},
        "sockets": [{"name": k.name, "position_mm": list(k.position_mm),
                     "rotation_deg": list(k.rotation_deg), "use": k.use} for k in s.sockets],
    }


__all__ = ["SmokeBombSpec", "SMOKE_BOMB", "SocketDef", "build_to", "assert_clean", "deny_hits"]
