"""Per-gun configuration for the gun-agnostic gate drivers (gunlib 0.2.0).

A gun's config is a small Python module next to its build code (``Scripts/guns/rifle/rifle_gun.py``,
``Scripts/guns/smg/smg_gun.py``) that builds one ``GunConfig`` named ``CFG``. The drivers in ``gunlib.drivers`` read
only the config: paths, names, the spec, and the gun's own data and hooks per driver (``cfg.b3``, ``cfg.b4``, ...).
Data that is the same for every gun lives in ``WorkFiles/guns/gunlib/gun_standard.json`` (``gunlib.standard``).

Every path derives from the repo root that gunlib computes from its own location, so a worktree run never writes into
the main checkout.

Load a config by path (the generic runner does this)::

    cfg = gunconf.load("Scripts/guns/rifle/rifle_gun.py")
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from . import ROOT
from .spec import GunSpec


class GunConfig:
    """Paths + names + spec of one gun, and one dict per driver (``b3``, ``b4``, ``b6a``, ``measure``, ``magfit``,
    ``viewgates``, ``g5_lods``, ``rig_verify``, ``mag_fit``). Unknown keyword arguments become attributes."""

    def __init__(self, code: str, work, spec_path, *, socket_key: Optional[str] = None, **kw):
        self.code = code
        self.root = ROOT
        self.work = Path(work)
        self.spec_path = Path(spec_path)
        self.spec = GunSpec(self.spec_path)
        self.grip = self.spec.grip_M                              # frame B origin in M (mm)
        self.gates = self.work / "gates"
        self.scratch = self.work / "scratch"
        self.review = self.work / "review"
        self.trace = self.work / "trace"
        self.exports = ROOT / "Exports" / "Guns" / code
        self.blend = ROOT / "Assets" / "Guns" / f"{code}.blend"
        self.renders = ROOT / "Renders" / "Guns" / code
        self.parts_collection = f"{code}_Parts"
        self.lod_collection = f"{code}_LOD{{k}}"                  # .format(k=...)
        self.twin = f"SM_{code}"
        self.skeletal = f"SK_{code}"
        self.mag = f"SM_{code}_Mag"
        self.mag_slot = f"M_{code}_Mag"
        self.log_tag = code
        self.socket_key = socket_key or self.spec.gun_socket_key
        for name in ("b3", "b4", "b6a", "measure", "magfit", "viewgates", "g5_lods", "rig_verify", "mag_fit"):
            setattr(self, name, {})
        for k, v in kw.items():
            setattr(self, k, v)

    # ------------------------------------------------------------------ helpers
    def M_to_B(self, p) -> np.ndarray:
        return np.asarray(p, float) - self.grip

    def B_to_M(self, p) -> np.ndarray:
        return np.asarray(p, float) + self.grip

    def gun_sockets(self):
        return self.spec.gun_sockets()

    def socket(self, name) -> Dict[str, Any]:
        return self.spec.socket(name)

    def rel(self, p) -> str:
        return str(Path(p).resolve().relative_to(ROOT.resolve())).replace("\\", "/")

    def lod_coll(self, k: int) -> str:
        return self.lod_collection.format(k=k)

    def get(self, section: str, key: str, default=None):
        return getattr(self, section, {}).get(key, default)


def load(path) -> GunConfig:
    """Import a gun config module by file path and return its ``CFG``. The module's folder goes on sys.path first
    (gun configs import their sibling modules: spec helpers, clip tables, part modules)."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    if str(p.parent) not in sys.path:
        sys.path.insert(0, str(p.parent))
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[p.stem] = mod
    spec.loader.exec_module(mod)
    return mod.CFG
