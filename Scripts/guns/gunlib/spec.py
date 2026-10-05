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
