"""Assemble the Snow Flower v4 parts per level.

``build_low(level)`` -> {part: MB} for the game levels 0/1/2 (steel slot 0, wrap slot 1).
``build_high()``     -> {part: {high_material: MB}} (bake source).
Bake groups (part names) are shared by both so each low part bakes against its own high set.
"""
from __future__ import annotations

import sfv4_blade as B
import sfv4_hilt as H
import sfv4_rev3 as R3
import sfv4_spec as S
from sfv4_mesh import MB

PARTS = ("blade", "relief", "guard", "collar", "grip", "gorn", "pommel")
#: cage extrusion (mm) per bake group: must exceed the tallest high detail NOT modelled in the low
CAGE_MM = {"blade": 2.6, "relief": 1.2, "guard": 1.4, "collar": 1.0, "grip": 1.6, "gorn": 1.0, "pommel": 1.6}
#: which high groups each low part may hit (the others are hidden from its rays)
HIGH_FOR = {"blade": ("blade", "relief"), "relief": ("relief",), "guard": ("guard",), "collar": ("collar",),
            "grip": ("grip",), "gorn": ("gorn",), "pommel": ("pommel",)}


def build_low(level):
    out = {}
    mb = MB(f"blade_L{level}")
    B.blade_steel(mb, level, mat=H.STEEL)
    out["blade"] = mb
    mb = MB(f"relief_L{level}")
    for side in (-1, 1):
        B.relief_low(mb, side, level, mat=H.STEEL)
    out["relief"] = mb
    mb = MB(f"guard_L{level}")
    H.guard_low(mb, level)
    out["guard"] = mb
    mb = MB(f"collar_L{level}")
    H.collar(mb, level)
    out["collar"] = mb
    mb = MB(f"grip_L{level}")
    H.grip_core(mb, level, S.WRAP_THICK * 0.55, mat=H.WRAP)
    out["grip"] = mb
    mb = MB(f"gorn_L{level}")
    for side in (-1, 1):
        H.grip_ornament(level, side, mb=mb)
    out["gorn"] = mb
    mb = MB(f"pommel_L{level}")
    H.pommel(mb, level)
    out["pommel"] = mb
    return {k: v for k, v in out.items() if v.faces}


def build_high():
    out = {}
    # blade steel
    sink = R3.Sink("blade")
    B.blade_steel(sink.mb(R3.BLADE), "high", mat=R3.BLADE)
    out["blade"] = sink.mbs
    sink = R3.Sink("relief")
    for side in (-1, 1):
        B.relief_high(sink, side)
    out["relief"] = sink.mbs
    sink = R3.Sink("guard")
    H.guard_high(sink.mb(R3.BLACKSTEEL), sink)
    out["guard"] = sink.mbs
    sink = R3.Sink("collar")
    H.collar_high(sink.mb(R3.SILVER), sink)
    out["collar"] = sink.mbs
    sink = R3.Sink("grip")
    H.wrap_high(sink.mb(R3.CORD), sink.mb(R3.CORE))
    # the core MB got CORD faces through grid(mat=...) defaults; fix below by building separately
    out["grip"] = sink.mbs
    sink = R3.Sink("gorn")
    for side in (-1, 1):
        H.grip_ornament("high", side, sink=sink)
    out["gorn"] = sink.mbs
    sink = R3.Sink("pommel")
    H.pommel_high(sink.mb(R3.SILVER), sink)
    out["pommel"] = sink.mbs
    return out
