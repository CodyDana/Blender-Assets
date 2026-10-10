"""SMG01 (Compact SMG SM-01): paths, the spec and the trace access shared by every SMG script (plain Python; safe
inside Blender). Every path derives from this file's location (a worktree build never writes into the main checkout).

Frames: M = the spec's measurement frame (mm; X from the butt-pad rear toward the muzzle, Z up, +Y = the gun's left);
B = M - Grip (Blender, metres at export). The trace JSONs are in M at the ruled scale (625 mm, spec R26).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                                 # Scripts/guns/smg -> repo root
for _p in (ROOT / "Scripts" / "guns", ROOT / "Scripts", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from gunlib.spec import GunSpec  # noqa: E402

CODE = "SMG01"
WORK = ROOT / "WorkFiles" / "guns" / "smg"
SPEC_PATH = WORK / "smg_spec.json"
TRACE = WORK / "trace"
GATES = WORK / "gates"
SCRATCH = WORK / "scratch"
REVIEW = WORK / "review"
LOGS = SCRATCH / "logs"
SHEET = ROOT / "References" / "Guns" / "SMG" / "smg_sheetA.webp"
REALREF = SCRATCH / "realref" / "craft"
BLEND = ROOT / "Assets" / "Guns" / "SMG01.blend"
BLOCKOUT_BLEND = SCRATCH / "SMG01_blockout.blend"
FORM_STAGE_BLEND = SCRATCH / "SMG01_form_stage.blend"
RENDERS = ROOT / "Renders" / "Guns" / "SMG01"
FIT_BODY = ROOT / "References" / "Characters" / "MH_PlayerDefault" / "MH_PlayerDefault_FitBody.blend"
for _d in (GATES, SCRATCH, REVIEW, LOGS, RENDERS, BLEND.parent):
    _d.mkdir(parents=True, exist_ok=True)

SPEC = GunSpec(SPEC_PATH)
D = SPEC.d
GRIP = SPEC.grip_M                                     # frame B origin in M (mm)
P = SPEC.parts                                         # part id -> record
OVERALL = float(D["scale"]["overall_length"])
BORE_Z = float(D["key_dimensions"]["bore_Z_M"])
PARTS_COLL = f"{CODE}_Parts"


def dims(pid):
    return P[pid].get("dims", {})


def box(pid):
    return P[pid].get("box_M")


def feature(pid, name):
    for f in P[pid].get("features", []):
        if f.get("name") == name:
            return f
    raise KeyError(f"{pid}.{name}")


def socket(name):
    return SPEC.socket(name)


def bone_head(name):
    return np.array(SPEC.bones[name]["head_M"], float)


# ------------------------------------------------------------------------------------------------ traces
_TR = {}


def trace(view):
    if view not in _TR:
        _TR[view] = json.loads((TRACE / f"{view}_outline.json").read_text(encoding="utf-8"))
    return _TR[view]


def trace_rings(view, key, part=None, kind="outer"):
    """Rings (mm, M) of a trace key (silhouette / gun_without_magazine / magazine) or a LEFT part."""
    j = trace(view)
    rr = j["parts"][part] if part else j[key]
    return [np.array(r["mm"], float) for r in rr if kind is None or r["kind"] == kind]


def main_ring(view, key, part=None):
    j = trace(view)
    rr = j["parts"][part] if part else j[key]
    r = max((r for r in rr if r["kind"] == "outer"), key=lambda r: abs(r["area_px"]))
    return np.array(r["mm"], float)


class PanelMap:
    """Panel px <-> M mm for a side / top trace (the trace's own mapping)."""

    def __init__(self, view):
        j = trace(view)
        self.view = view
        self.s = float(j["px_per_mm"])
        u = np.array(j["bore_dir_px"], float)
        self.u = u / np.hypot(*u)
        n = np.array(j["up_dir_px"], float)
        self.n = n / np.hypot(*n)
        self.p0 = np.array(j["origin_px"], float)
        self.mirrored = bool(j.get("mirrored"))
        self.width = j["panel_box_sheet_px"][2] - j["panel_box_sheet_px"][0] + 1

    def mm(self, P_px, raw=False):
        """Panel px (mirrored panel coords; raw=True takes un-mirrored RIGHT coords) -> (X, Z) mm."""
        P_px = np.asarray(P_px, float).reshape(-1, 2).copy()
        if raw and self.mirrored:
            P_px[:, 0] = self.width - 1 - P_px[:, 0]
        d = P_px - self.p0
        return np.c_[d @ self.u, d @ self.n] / self.s

    def px(self, Q):
        Q = np.asarray(Q, float).reshape(-1, 2)
        return self.p0 + self.s * (Q[:, :1] * self.u + Q[:, 1:2] * self.n)


def sheet_px_per_mm(view="LEFT"):
    return float(trace(view)["px_per_mm"])
