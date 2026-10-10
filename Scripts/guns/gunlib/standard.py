"""Gun line standard loader (GUN_BUILDING_STUDY 4.7; gunlib 0.2.0): WorkFiles/guns/gunlib/gun_standard.json.

Plain Python. ``STD`` is the parsed file; the helpers return the pieces the part generators and drivers use, so a
change to the standard reaches every gun through one file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from . import ROOT

PATH = ROOT / "WorkFiles" / "guns" / "gunlib" / "gun_standard.json"


@lru_cache(maxsize=1)
def load() -> Dict[str, Any]:
    return json.loads(PATH.read_text(encoding="utf-8"))


def rail() -> Dict[str, float]:
    """MIL-STD-1913 numbers in mm (+ the derived profile depths)."""
    d = load()["rail_1913"]
    out = dict(d["mm"])
    out.update({k: v for k, v in d["derived_mm"].items() if k != "note"})
    return out


def clearance(row: str):
    return load()["clearance_mm"][row]


def clearance_rows() -> Dict[str, Tuple[float, float]]:
    c = load()["clearance_mm"]
    return {k: tuple(c[k]) for k in ("butt", "sliding", "hinge")}


def bone_parents() -> Dict[str, Tuple[Optional[str], ...]]:
    return {k: tuple(v) for k, v in load()["bones"]["parents"].items()}


def socket_names() -> Tuple[str, ...]:
    return tuple(load()["sockets"]["gun"])


def texel_class(c: str) -> Tuple[float, float]:
    return tuple(load()["texel_classes_px_per_cm"][c]["range"])


def camera() -> Dict[str, Any]:
    return load()["camera"]


def ud_thresholds() -> Dict[str, Any]:
    return load()["unreal_degenerate_rule"]


def hardware() -> Dict[str, Any]:
    return load()["hardware"]


def check_against_rig() -> Dict[str, Any]:
    """The JSON bone table must equal gunlib.rig.STANDARD_BONES (the rig module's copy, used by its checks)."""
    from .rig import STANDARD_BONES
    a = bone_parents()
    return {"equal": a == STANDARD_BONES, "only_json": sorted(set(a) - set(STANDARD_BONES)),
            "only_rig": sorted(set(STANDARD_BONES) - set(a)),
            "different": sorted(k for k in set(a) & set(STANDARD_BONES) if a[k] != STANDARD_BONES[k])}
