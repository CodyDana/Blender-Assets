#!/usr/bin/env python
"""props_lib.smokebomb_spec - SM_SmokeBomb's build-to numbers, in one place.

Pure Python.  Every number is labelled the way References/SmokeBomb/SMOKEBOMB_STUDY.md
labels them (SOURCED / DERIVED / ESTIMATE / MEASURED) or says where the reference
measurement is (REFERENCE_SPEC section).  The build script reads this object; the report
restates it; nothing is typed twice.

FRAME: ball centre at the origin; the reference view is Blender's Front view (camera on
-Y looking +Y, image-right +X, image-up +Z).  Export Forward -Y / Up Z (the pack's).
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    #: study 4: 70 mm mean outline diameter (ESTIMATE, reasoned); the tape stack and the
    #: base below are tuned so the RENDER's fitted outline is 70 mm (REFERENCE_SPEC 1)
    diameter_mm: float = 70.0
    #: the core the tape is wound on (mm); round 3 re-solves it (with the outline correction)
    #: so the LOD0 mesh's own outline has the reference's mean radius
    base_radius_mm: float = 34.51
    #: round 3 height model (props_lib.smokebomb_shell.HeightModel).  t = 0.60 mm per layer
    #: with the tape rolled down 0.08 mm at its own edge (roll_mm, over 0.6 mm): the visible
    #: step where an edge crosses the limb square-on is ~0.52 mm = 6.9 px (REFERENCE_SPEC 5:
    #: 4 - 8.5 px, median 5.7).  Round 2's bead is replaced by the roll (a rolled selvedge,
    #: not a cut sheet).  0.60 is also the thickest tape LOD1 (2,000 triangles) can follow
    #: within its 1.5 mm two-sided deviation budget (0.62 measured 1.51 mm).
    height_params: Tuple[Tuple[str, float], ...] = (
        ("t_mm", 0.60), ("crown_mm", 0.28), ("crown_per_hw", 0.10), ("bead_mm", 0.0),
        ("bead_w_mm", 0.30), ("dip_mm", 1.6), ("groove_mm", 0.06), ("groove_w_mm", 1.0),
        ("drape_mm", 2.0), ("roll_mm", 0.08), ("roll_w_mm", 0.6))
    #: round 3: the 12-sector core profile is retired; the outline's shape is matched by
    #: props_lib.smokebomb_outline (REFERENCE_SPEC 1's outline, Fourier harmonics 2..24,
    #: measured with the adversary's instrument), fitted on the height model and then twice
    #: on the LOD0 mesh's own outline
    core_profile_pct: Tuple[float, ...] = (0.0,) * 12
    outline_radius_mm: float = 35.0
    outline_harmonics: int = 24
    outline_mesh_rounds: int = 2
    #: study 4 / 5: 10 mm cotton plain tape, 0.5 mm (SOURCED); round 3 models 0.60 mm per layer
    #: (REFERENCE_SPEC 5: 5.7 px = 0.43 mm at 70 mm, tolerance up to 8.5 px = 0.64 mm)
    tape_thickness_mm: float = 0.60
    #: textures: 4096 (study question 3's option).  At 2048 the islands pack at ~7.5 px/mm,
    #: under the 13.26 px/mm the reference framing needs, and the 0.31 mm ribs alias.
    texture_size: int = 4096
    padding_px: int = 32
    seed: int = 20260921
    #: study 8: mass 121 g design (98 - 139 g), physics override 0.12 kg (DERIVED)
    mass_g: float = 121.0
    physics_mass_kg: float = 0.12
    #: triangle bands per LOD (study 6.3; LOD0 at the study's 4,000-6,500 ceiling)
    lod_bands: Tuple[Tuple[int, int], ...] = ((4000, 6500), (1200, 2000), (400, 800))
    sockets: Tuple[SocketDef, ...] = (
        SocketDef("Grip", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  "hand socket: the ball's centre in the palm; build frame, reference face -Y, +Z up"),
        SocketDef("Burst", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  "smoke spawn point: spawn with ABSOLUTE rotation so smoke rises however the ball lands"),
    )

    def lod_screen_sizes(self, radius_mm: float) -> List[float]:
        return scaled_lod_screen_sizes(radius_mm)

    def switch_distances_m(self, radius_mm: float) -> List[float]:
        return [round(screen_size_distance_m(s, radius_mm * 0.001), 4)
                for s in self.lod_screen_sizes(radius_mm)[1:]]

    def core_profile(self) -> Tuple[float, ...]:
        return tuple(v * 0.01 for v in self.core_profile_pct)

    def height_model(self) -> Dict[str, object]:
        out = dict(self.height_params)
        out["core_mm"] = self.base_radius_mm
        out["profile"] = self.core_profile()
        return out


SMOKE_BOMB = SmokeBombSpec()

#: the franchise deny gate (props_lib.spec.DENY_SUBSTRINGS) plus nothing smoke-specific
from .spec import assert_clean, deny_hits  # noqa: E402,F401


def build_to(s: SmokeBombSpec = SMOKE_BOMB) -> Dict[str, object]:
    return {
        "name": s.name, "mesh": s.mesh_name, "material": s.material_name,
        "textures": [f"{s.texture_stem}_{k}" for k in ("BC", "ORM", "N")],
        "diameter_mm": s.diameter_mm, "base_radius_mm": s.base_radius_mm,
        "height_model": {k: v for k, v in s.height_params},
        "core_profile_pct": list(s.core_profile_pct),
        "tape_thickness_mm": s.tape_thickness_mm,
        "texture_size": s.texture_size, "padding_px": s.padding_px,
        "mass_g": s.mass_g, "physics_mass_kg": s.physics_mass_kg,
        "lod_bands": [list(b) for b in s.lod_bands],
        "pack_lod_rule": {"sizes": list(PACK_LOD_SCREEN_SIZES),
                          "reference_radius_mm": PACK_LOD_REFERENCE_RADIUS_MM},
        "sockets": [{"name": k.name, "position_mm": list(k.position_mm),
                     "rotation_deg": list(k.rotation_deg), "use": k.use} for k in s.sockets],
    }


__all__ = ["SmokeBombSpec", "SMOKE_BOMB", "SocketDef", "build_to", "assert_clean", "deny_hits"]
