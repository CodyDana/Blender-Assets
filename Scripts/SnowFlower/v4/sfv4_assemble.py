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

PARTS = ("blade", "relief", "guard", "collar", "grip", "gorn", "pommel", "fbloom", "pbloom")
#: cage extrusion (mm) per bake group: must exceed the tallest high detail NOT modelled in the low.
#: Final pass: a blossom proxy's rim sinks below its flower centre while the high petals stand ~0.1 r ABOVE it, so near
#: the rim the high petal was up to (0.1 r + sink) above the proxy - more than the part's cage (guard 1.4 vs 3.05 mm,
#: relief 1.2 vs ~1.6, grip sprigs 1.0 vs 1.4).  Those rays started UNDER the petals and baked their undersides: the
#: black crescents on every blossom rim.  The fittings' blossom proxies (guard, pommel, grip sprigs) are now their own
#: bake group 'fbloom' with a 3.8 mm cage, and the relief proxies get 2.6 mm.
CAGE_MM = {"blade": 3.8, "relief": 3.2, "guard": 2.2, "collar": 1.6, "grip": 1.6, "gorn": 1.0, "pommel": 1.6,
           "fbloom": 3.8, "pbloom": 2.2}
#: final pass 2026-09-27: the POMMEL end-face blossom lies nearly flat (height 0.2 r) on a field ringed by the medallion
#: rims, so the 3.8 mm 'fbloom' cage started its rim rays far outside the petals and smeared the petal walls and rims
#: into ghost outlines around every petal; it bakes as its own group 'pbloom' with a 2.2 mm cage
#: which high groups each low part may hit (the others are hidden from its rays)
HIGH_FOR = {"blade": ("blade", "relief"), "relief": ("relief", "blade"), "guard": ("guard",), "collar": ("collar",),
            "grip": ("grip",), "gorn": ("gorn", "grip"), "pommel": ("pommel",),
            "fbloom": ("guard", "gorn", "grip"), "pbloom": ("pommel",)}


def _is_fitting_bloom(island):
    return island.startswith("guard_bloss") or (island.startswith("gorn_") and "_bl" in island)


def _is_pommel_bloom(island):
    return island.startswith("pommel_bloss")


def _split(mb, pred):
    """(faces NOT matching pred, faces matching pred) as two MBs with their own vertices (islands and slots kept)."""
    rest, sel = MB(mb.name), MB(mb.name + "_sel")
    maps = ({}, {})
    for f, uv, isl, m in zip(mb.faces, mb.fuv, mb.fisl, mb.fmat):
        tgt, mp = (sel, maps[1]) if pred(isl) else (rest, maps[0])
        idx = []
        for i in f:
            if i not in mp:
                mp[i] = tgt.v(mb.verts[i])
            idx.append(mp[i])
        tgt.f(idx, uv, isl, m)
    return rest, sel
#: final pass: the blossom/sprig proxies' rays must be able to land on the surface they sit on.  With only their own
#: high group visible, rays in the gaps between petals missed or grazed the petal walls and baked the black
#: crescents / halos the craft review found on every blossom rim (relief on the blade, grip sprigs on the cord).


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
    # final pass: three material slots (blade / fittings / grip), one index per part (sfv4_spec.SLOT_OF_PART)
    for k, m in out.items():
        m.fmat = [S.SLOT_OF_PART[k] for _ in m.fmat]
    # final pass: the fittings' blossom proxies bake as their own group (bigger cage); islands and slot unchanged
    fb = MB(f"fbloom_L{level}")
    for k in ("guard", "pommel", "gorn"):
        if k in out:
            out[k], sel = _split(out[k], _is_fitting_bloom)
            fb.extend(sel)
    out["fbloom"] = fb
    pb = MB(f"pbloom_L{level}")
    if "pommel" in out:
        out["pommel"], sel = _split(out["pommel"], _is_pommel_bloom)
        pb.extend(sel)
    out["pbloom"] = pb
    return {k: v for k, v in out.items() if v.faces}


def build_high(parts=None):
    """``parts`` (look-match preview): build only these bake groups; None = all."""
    want = (lambda k: True) if not parts else (lambda k: k in parts)
    out = {}
    if want("blade"):
        sink = R3.Sink("blade")
        B.blade_steel(sink.mb(R3.BLADE), "high", mat=R3.BLADE)
        out["blade"] = sink.mbs
    if want("relief"):
        sink = R3.Sink("relief")
        for side in (-1, 1):
            B.relief_high(sink, side)
        out["relief"] = sink.mbs
    if want("guard"):
        sink = R3.Sink("guard")
        H.guard_high(sink.mb(R3.BLACKSTEEL), sink)
        out["guard"] = sink.mbs
    if want("collar"):
        sink = R3.Sink("collar")
        H.collar_high(sink.mb(R3.SILVER), sink)
        out["collar"] = sink.mbs
    if want("grip"):
        sink = R3.Sink("grip")
        H.wrap_high(sink.mb(R3.CORD), sink.mb(R3.CORE))
        out["grip"] = sink.mbs
    if want("gorn"):
        sink = R3.Sink("gorn")
        for side in (-1, 1):
            H.grip_ornament("high", side, sink=sink)
        out["gorn"] = sink.mbs
    if want("pommel"):
        sink = R3.Sink("pommel")
        H.pommel_high(sink.mb(R3.SILVER), sink)
        out["pommel"] = sink.mbs
    return out
