"""Gun spec loader (one JSON per gun, GUN_BUILDING_STUDY 4.3). Plain Python.

The spec's frame M is the measurement frame (mm); the Blender build frame B = M - Grip_in_M (pure translation).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


class GunSpec:
    def __init__(self, path):
        self.path = Path(path)
        self.d: Dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        self.code = self.d["meta"]["code"]
        self.grip_M = np.array(self.d["frames"]["B"]["Grip_in_M"], float)
        self.parts = {p["id"]: p for p in self.d["parts"]}
        self.bones = {b["bone"]: b for b in self.d["bones"]["table"]}

    def part(self, pid) -> Dict[str, Any]:
        return self.parts[pid]

    def profile(self, pid) -> np.ndarray:
        """Traced side profile in M (X, Z), or None."""
        p = self.parts[pid].get("side_profile_M")
        return None if p is None else np.array(p, float)

    def box(self, pid):
        return self.parts[pid].get("box_M")

    def dims(self, pid):
        return self.parts[pid].get("dims", {})

    def feature(self, pid, name):
        for f in self.parts[pid].get("features", []):
            if f.get("name") == name:
                return f
        return None

    def M_to_B(self, p):
        return np.asarray(p, float) - self.grip_M

    def B_to_M(self, p):
        return np.asarray(p, float) + self.grip_M

    @property
    def key(self):
        return self.d["key_dimensions"]

    @property
    def stations(self):
        return self.d["stations_X"]

    @property
    def sockets(self):
        return self.d["sockets"]

    @property
    def gates(self):
        return self.d["gates_look"]

    # ------------------------------------------------------------------ gun-agnostic socket access (gunlib 0.2.0)
    @property
    def gun_socket_key(self) -> str:
        """The spec's key for the gun's socket list: 'rifle' on the AR-01 spec, 'gun' from the SMG on."""
        s = self.d["sockets"]
        for k in ("gun", "rifle"):
            if isinstance(s.get(k), list):
                return k
        raise KeyError("no gun socket list in the spec (sockets.gun / sockets.rifle)")

    def gun_sockets(self) -> List[Dict[str, Any]]:
        """The gun's socket records, each with ``unreal_rotation_deg`` filled in (the SMG spec nests it under
        ``rotation.unreal``; the AR-01 spec has it at the top level)."""
        out = []
        for r in self.d["sockets"][self.gun_socket_key]:
            if "unreal_rotation_deg" not in r and isinstance(r.get("rotation"), dict) and "unreal" in r["rotation"]:
                r = dict(r, unreal_rotation_deg=r["rotation"]["unreal"])
            out.append(r)
        return out

    def socket(self, name) -> Dict[str, Any]:
        return {r["socket"]: r for r in self.gun_sockets()}[name]

    def mag_sockets(self) -> List[Dict[str, Any]]:
        out = []
        for r in self.d["sockets"].get("mag", []):
            if "unreal_rotation_deg" not in r and isinstance(r.get("rotation"), dict) and "unreal" in r["rotation"]:
                r = dict(r, unreal_rotation_deg=r["rotation"]["unreal"])
            out.append(r)
        return out
