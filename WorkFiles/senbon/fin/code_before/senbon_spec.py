"""Senbon needles: the build-to numbers (pure Python, no bpy / numpy).

Read from the Study's WorkFiles/senbon/senbon_spec.json (the design: every dimension, the point and tail forms, the
wrap, the finish) and SENBON_BUILD_PLAN.md (the frame, sockets, collision, LOD sides, screen sizes, maps).  Nothing here
is invented: where a number below is not in the spec it is a build choice and says so (BUILD).

Frames
------
Needle: x from the centre, mm, +X = the front point; mirror-symmetric, pivot = the centre.
Heavy:  s from the butt face (s = 0) to the tip (s = 170), mm; the mesh is authored in s and shifted by the centre of
        mass afterwards (pivot = the steel + wrap centre of mass of the as-built round profile).
Azimuth theta in the YZ plane from +Y toward +Z (90 = +Z, up), the spec's convention.  UV seam on -Z (theta 270).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

PROJECT = Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT / "WorkFiles" / "senbon" / "senbon_spec.json"
SHEET_PATH = PROJECT / "WorkFiles" / "senbon" / "SENBON_DESIGN_SHEET.png"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

STEEL_DENSITY_G_MM3 = SPEC["derived"]["steel_density_g_cm3"] * 1e-3
COTTON_DENSITY_G_MM3 = SPEC["derived"]["cotton_wrap_density_g_cm3"] * 1e-3
SEAM_DEG = 270.0                     # plan 2: the UV seam on -Z

# --------------------------------------------------------------------------------------------------- needle
_N = SPEC["items"]["SM_Senbon_Needle"]
_NP = _N["profile"]
NEEDLE_L = float(_N["overall_length_mm"])            # 130
NEEDLE_HALF = NEEDLE_L / 2.0                          # 65 (tips at +-65)
NEEDLE_SH_X = float(_NP["shoulder_abs_x_mm"])         # 50
NEEDLE_D_BELLY = float(_NP["belly_diameter_mm"])      # 2.8
NEEDLE_D_SH = float(_NP["shoulder_diameter_mm"])      # 2.3
NEEDLE_TIP_R = float(_NP["tip_radius_mm"])            # 0.05


def needle_r(x: float) -> float:
    """The spec's body law and straight cones (sharp apex at +-65); the tip radius is applied by the mesh."""
    ax = abs(x)
    if ax <= NEEDLE_SH_X:
        return 0.5 * (NEEDLE_D_SH + (NEEDLE_D_BELLY - NEEDLE_D_SH) * (1.0 - (ax / NEEDLE_SH_X) ** 2))
    return 0.5 * NEEDLE_D_SH * max(0.0, (NEEDLE_HALF - ax) / (NEEDLE_HALF - NEEDLE_SH_X))


def needle_drdx(x: float) -> float:
    ax = abs(x)
    sg = 1.0 if x >= 0 else -1.0
    if ax <= NEEDLE_SH_X:
        return sg * (-(NEEDLE_D_BELLY - NEEDLE_D_SH) * ax / NEEDLE_SH_X ** 2)
    return sg * (-0.5 * NEEDLE_D_SH / (NEEDLE_HALF - NEEDLE_SH_X))


# --------------------------------------------------------------------------------------------------- heavy
_H = SPEC["items"]["SM_Senbon_Heavy"]
_HP = _H["profile"]
HEAVY_L = float(_H["overall_length_mm"])                       # 170
H_R_TAIL = _HP["tail_steel"]["diameter_mm"] / 2.0              # 1.4
H_CH = float(_HP["butt"]["chamfer_mm"])                         # 0.3
H_TAIL_END = float(_HP["tail_steel"]["s_mm"][1])               # 54
H_RB = tuple(_HP["rear_binding"]["s_mm"])                       # 6 .. 7.5
H_FB = tuple(_HP["front_binding"]["s_mm"])                      # 52.5 .. 54
H_R_BIND = _HP["rear_binding"]["outer_diameter_mm"] / 2.0      # 2.3
H_R_WRAP = _HP["wrap"]["outer_diameter_mm"] / 2.0              # 2.1
H_WRAP = tuple(_HP["wrap"]["s_mm"])                             # 7.5 .. 52.5
H_BIND_ROUND = 0.15                                              # spec: "crisp 0.15 mm round on both outer corners"
H_BODY = tuple(_HP["body"]["s_mm"])                             # 54 .. 148
H_R_FRONT = _HP["body"]["diameter_mm"][1] / 2.0                # 2.25
H_PT0 = float(_HP["point"]["s_mm"][0])                          # 148
H_PT_L = float(_HP["point"]["length_mm"])                       # 22
H_FACET_PHI = tuple(float(a) for a in _HP["point"]["facet_normal_azimuths_deg"])   # 90, 210, 330
H_RIDGE_PSI = (30.0, 150.0, 270.0)                              # spec: ridges at azimuths 30, 150, 270
H_FACET_H0 = 2.25                                                # facet plane 2.25 mm off axis at s = 148
H_RIDGE_S0 = HEAVY_L - H_PT_L / 2.0                              # 159


def heavy_facet_h(s: float) -> float:
    """Distance of each facet plane from the axis at station s (spec facet_rule)."""
    return (HEAVY_L - s) * H_FACET_H0 / H_PT_L


def heavy_round_r(s: float) -> float:
    """Radius of the ROUND steel (no facets, no wrap) at s: chamfer, tail, taper, then the 4.5 mm stock."""
    if s < H_CH:
        return (H_R_TAIL - H_CH) + s
    if s <= H_TAIL_END:
        return H_R_TAIL
    if s <= H_PT0:
        return H_R_TAIL + (H_R_FRONT - H_R_TAIL) * (s - H_TAIL_END) / (H_PT0 - H_TAIL_END)
    return H_R_FRONT


def heavy_steel_area(s: float) -> float:
    """Exact area of the round steel section with the three facets cut (the sheet script's formula)."""
    r = heavy_round_r(s)
    if s <= H_PT0:
        return math.pi * r * r
    h = heavy_facet_h(s)
    if h >= r:
        return math.pi * r * r
    if h >= r / 2:
        seg = r * r * math.acos(h / r) - h * math.sqrt(r * r - h * h)
        return math.pi * r * r - 3 * seg
    return 3 * math.sqrt(3) * h * h


def heavy_wrap_outer_r(s: float) -> float:
    """Outer radius of the thread wrap + bindings at s (the as-designed sharp-cornered layer)."""
    if H_RB[0] <= s <= H_RB[1] or H_FB[0] <= s <= H_FB[1]:
        return H_R_BIND
    if H_WRAP[0] <= s <= H_WRAP[1]:
        return H_R_WRAP
    return 0.0


# --------------------------------------------------------------------------------------------------- LODs
@dataclass(frozen=True)
class LodDef:
    sides: int
    phase_deg: float
    note: str


# Needle: the plan's 12 / 8 / 6.  Vertices at k * 360/n from +Y so the side (-Y) and top (+Z) views see vertices
# (full radius) on LOD0 and LOD1.  LOD2: phase 0 too (vertices at 0, 60, ...).
NEEDLE_LODS = (LodDef(12, 0.0, "full profile: tip flats r 0.05, 12 swell stations, hard shoulder rings"),
               LodDef(8, 0.0, "swell at x = 0, +-25, +-50; sharp apex cones"),
               LodDef(6, 0.0, "belly ring + shoulder rings + apex cones"))
NEEDLE_LOD0_SWELL_STEPS = 6          # stations per half on LOD0 (spec budget note: about 6)
NEEDLE_LOD1_SWELL_STEPS = 2          # x = 0, 25, 50 (spec: 3 rings per half)
NEEDLE_LOD2_SWELL_STEPS = 1          # x = 0, 50

# Heavy: 12 / 9 / 6.  BUILD: LOD1 has 9 sides, not the plan's 8: the point's three facets and ridges are three-fold, an
# 8-gon cannot carry three equal facets without extra columns (and LOD1 keeps the facets per the spec's lod_notes).
# Phases put the ridge azimuths 30 / 150 / 270 on vertices at every LOD.
HEAVY_LODS = (LodDef(12, 0.0, "full profile: chamfered butt, rounded bindings, 48-column round point lands + "
                               "three planar facets (12-gon body morphing to a 48-gon ring at s = 148)"),
              LodDef(9, 30.0, "plain butt, square-cornered bindings, facets as three planes on the 9-gon"),
              LodDef(6, 30.0, "wrap + bindings merged into one cylinder, three facets on the 6-gon"))
HEAVY_POINT_COLUMNS_LOD0 = 48          # BUILD: the round lands carry the elliptical grind lines (0.05 mm chord error)

# --------------------------------------------------------------------------------------------------- textures
@dataclass(frozen=True)
class TexDef:
    stem: str
    size: Tuple[int, int]          # (width, height) px
    ppmm: float                     # texel density on every island, px / mm
    border: int = 8
    gap: int = 16


NEEDLE_TEX = TexDef("T_Senbon_Needle", (2048, 256), float(_N["texture"]["texel_px_per_mm_target"]))   # 14
HEAVY_TEX = TexDef("T_Senbon_Heavy", (2048, 256), float(_H["texture"]["steel"]["texel_px_per_mm_target"]))  # 12
# BUILD: the spec's 18 px/mm does not fit 256 px over the Ø 4.6 binding's 14.45 mm circumference (260 px + borders);
# 16 px/mm fits (231 + 16 px) and still gives 9.6 px per 0.6 mm thread turn (the spec asks for about 3).
WRAP_TEX = TexDef("T_Senbon_Heavy_Wrap", tuple(_H["texture"]["wrap"]["size"]), 16.0)

# --------------------------------------------------------------------------------------------------- names
NEEDLE_MESH = "SM_Senbon_Needle"
HEAVY_MESH = "SM_Senbon_Heavy"
MAT_NEEDLE_STEEL = "M_Senbon_Needle_Steel"
MAT_HEAVY_STEEL = "M_Senbon_Heavy_Steel"
MAT_HEAVY_WRAP = "M_Senbon_Heavy_Wrap"
MI = {MAT_NEEDLE_STEEL: "MI_Senbon_Needle_Steel", MAT_HEAVY_STEEL: "MI_Senbon_Heavy_Steel",
      MAT_HEAVY_WRAP: "MI_Senbon_Heavy_Wrap"}

# --------------------------------------------------------------------------------------------------- finish
FIN = SPEC["finish"]
COAT = tuple(FIN["steel_coat"]["base_colour_linear"])
COAT_ROUGH = float(FIN["steel_coat"]["roughness"])
GROUND = tuple(FIN["ground_point"]["base_colour_linear"])
GROUND_ROUGH = float(FIN["ground_point"]["roughness"])
FADE_MM = tuple(FIN["ground_point"]["fade_back_mm"])
WRAP_HEX = FIN["wrap"]["shipped_colour_srgb_hex"]
WRAP_ROUGH = float(FIN["wrap"]["roughness"])
THREAD_PITCH = float(FIN["wrap"]["thread_pitch_mm"])


def hex_to_linear(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


WRAP_LINEAR = hex_to_linear(WRAP_HEX)

# --------------------------------------------------------------------------------------------------- sockets
EMBED_DEFAULT_MM = 15.0      # plan 3 / 9.4
EMBED_BY_SURFACE_MM = {"wood": [10, 20], "straw_tatami": [25, 40], "cloth_flesh": [20, 35], "paper": "passes",
                       "stone_metal": 0}
SOCKET_NAMES = ("Grip", "Tip", "Trail", "Throw", "Embed")


def needle_sockets_x() -> Dict[str, float]:
    s = _N["sockets"]
    return {"Grip": float(s["Grip"]["x_mm"]), "Tip": float(s["Tip"]["x_mm"]), "Trail": float(s["Trail"]["x_mm"]),
            "Throw": 0.0, "Embed": float(s["Tip"]["x_mm"]) - EMBED_DEFAULT_MM}


def heavy_sockets_s() -> Dict[str, float]:
    s = _H["sockets"]
    return {"Grip": float(s["Grip"]["s_mm"]), "Tip": float(s["Tip"]["s_mm"]), "Trail": float(s["Trail"]["s_mm"]),
            "Embed": float(s["Tip"]["s_mm"]) - EMBED_DEFAULT_MM}


SOCKET_USE = {"Grip": "hand attach (inverse of the socket)", "Tip": "impact FX, embed, projectile root",
              "Trail": "trail / ribbon VFX", "Throw": "launch point (= pivot)",
              "Embed": "put on the surface hit point: Tip - 15 mm"}

# --------------------------------------------------------------------------------------------------- budgets
BUDGETS = {NEEDLE_MESH: {"lod0_max": int(_N["budgets_tris"]["LOD0_target_max"]), "cap": 1000},
           HEAVY_MESH: {"lod0_max": int(_H["budgets_tris"]["LOD0_cap"]), "cap": 1000}}

DENY = ("naruto", "haku", "konoha", "kamish", "jinmuwon", "jin mu-won")


def deny_hits(*values) -> List[str]:
    return [f"{d!r} in {v!r}" for v in values if v for d in DENY if d in str(v).lower()]


def build_to() -> Dict[str, object]:
    return {"spec": str(SPEC_PATH.relative_to(PROJECT)), "sheet": str(SHEET_PATH.relative_to(PROJECT)),
            "needle": {"length_mm": NEEDLE_L, "belly_d_mm": NEEDLE_D_BELLY, "shoulder_d_mm": NEEDLE_D_SH,
                       "shoulder_abs_x_mm": NEEDLE_SH_X, "tip_radius_mm": NEEDLE_TIP_R,
                       "derived_mass_g": SPEC["derived"]["SM_Senbon_Needle"]["mass_g"]},
            "heavy": {"length_mm": HEAVY_L, "tail_d_mm": 2 * H_R_TAIL, "front_d_mm": 2 * H_R_FRONT,
                      "binding_d_mm": 2 * H_R_BIND, "wrap_d_mm": 2 * H_R_WRAP, "point_mm": H_PT_L,
                      "ridges_start_s_mm": H_RIDGE_S0,
                      "derived_mass_g": SPEC["derived"]["SM_Senbon_Heavy"]["mass_g"],
                      "derived_com_from_butt_mm": SPEC["derived"]["SM_Senbon_Heavy"]["com_from_butt_mm"]},
            "lods": {"needle": [l.sides for l in NEEDLE_LODS], "heavy": [l.sides for l in HEAVY_LODS]},
            "textures": {t.stem: {"size": list(t.size), "px_per_mm": t.ppmm} for t in (NEEDLE_TEX, HEAVY_TEX, WRAP_TEX)}}
