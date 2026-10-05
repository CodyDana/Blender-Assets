"""AR-01 detail-part modules (detail pass, 2026-10-04).

Each detailed part lives in its own module ``parts/<module>.py`` with

    OBJECTS   the registry keys it builds (rifle_parts.ORDER; one key can make several objects, e.g. rear_sight_leaf
              makes the leaf and the slider)
    CLOSEUPS  the sheet panels that are the part's 3D-shape authority (camera / crop / trace config: rifle_detail.py)
    build(spec, ctx) -> {key: [objects]}   builds into ctx (gunlib.parts.BuildCtx: collection, frame offset, only)

Shape, proportions within the part and details come from the part's own close-up; scale and position from the spec
and the side views (the close-ups are not to scale). Modules import shared constants / helpers from rifle_parts and
rifle_parts2 and never from each other, so the part builders can work in parallel; the interfaces each module must
keep are listed in its docstring. Non-detailed parts stay in rifle_parts.py / rifle_parts2.py.
"""
from __future__ import annotations

import importlib

MODULES = ("receiver_right", "rear_sight", "front_sight", "muzzle_brake", "trigger_guard", "grip", "selector",
           "magazine", "butt_plate")


def load(name):
    return importlib.import_module(f"parts.{name}")


def owner_of(key):
    """Detail module that builds the registry key (KeyError if none)."""
    for m in MODULES:
        if key in load(m).OBJECTS:
            return m
    raise KeyError(key)


def objects_of(name):
    """Object names a module produces (keys plus the extra objects a key makes)."""
    extra = {"rear_sight_leaf": ("rear_sight_slider",)}
    out = []
    for k in load(name).OBJECTS:
        out.append(k)
        out += list(extra.get(k, ()))
    return out
