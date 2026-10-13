"""SR01 (Sniper Rifle SR-01): paths, the spec and the trace access shared by every sniper script (plain Python; safe
inside Blender). Every path derives from this file's location (a worktree build never writes into the main checkout).

Frames: M = the spec's measurement frame (mm; X 0 = butt-pad rear, +X muzzle, Z 0 = bore, +Y = the gun's left);
B = M - Grip (Blender, metres). The trace JSONs are in M at the ruled scale (1100 mm, Q1 accepted 2026-10-13).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                                 # Scripts/guns/sniper -> repo root
for _p in (ROOT / "Scripts" / "guns", ROOT / "Scripts", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

CODE = "SR01"
WORK = ROOT / "WorkFiles" / "guns" / "sniper"
SPEC_PATH = WORK / "sr01_spec.json"
TRACE = WORK / "trace"
GATES = WORK / "gates"
SCRATCH = WORK / "scratch" / "w1"
REVIEW = WORK / "review"
LOGS = SCRATCH / "logs"
BLEND = ROOT / "Assets" / "Guns" / "SR01.blend"
BLOCKOUT_BLEND = SCRATCH / "SR01_blockout.blend"
RENDERS = ROOT / "Renders" / "Guns" / "SR01"
CROPS = WORK / "scratch" / "crops"
FIT_BODY = ROOT / "References" / "Characters" / "MH_PlayerDefault" / "MH_PlayerDefault_FitBody.blend"
for _d in (GATES, SCRATCH, REVIEW, LOGS, RENDERS, BLEND.parent):
    _d.mkdir(parents=True, exist_ok=True)

D = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
P = {p["id"]: p for p in D["parts"]}
GRIP = np.array(D["frames"]["B"]["Grip_in_M"], float)  # frame B origin in M (mm)
OVERALL = float(D["scale"]["overall_length"])
PARTS_COLL = f"{CODE}_Parts"
SLOT_METAL, SLOT_CHASSIS, SLOT_MAG = "M_SR01_Metal", "M_SR01_Chassis", "M_SR01_Mag"


def dims(pid):
    return P[pid].get("dims", {})


def box(pid):
    return P[pid].get("box_M")


def socket(name):
    for s in D["sockets"]["gun"]:
        if s["socket"] == name:
            return s
    raise KeyError(name)


def bone(name):
    for b in D["bones"]["table"]:
        if b.get("bone", b.get("name")) == name:
            return b
    raise KeyError(name)


# ------------------------------------------------------------------------------------------------ traces
_TR = {}


def trace(view):
    if view not in _TR:
        _TR[view] = json.loads((TRACE / f"{view}_outline.json").read_text(encoding="utf-8"))
    return _TR[view]


def signed_area(P2):
    P2 = np.asarray(P2, float)
    x, y = P2[:, 0], P2[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def part_rings(key, view="GR", min_area=4.0):
    """(outers, holes) of a traced GR part (frame M X, Z mm)."""
    rings = trace(view)["parts"][key]["mm"]
    outs, holes = [], []
    for r in rings:
        a = signed_area(r)
        if abs(a) < min_area:
            continue
        (outs if a > 0 else holes).append(np.array(r, float))
    return outs, holes


# ------------------------------------------------------------------------------------------------ plan widths
# half-width (Y) of the chassis / butt by X: the TOP left half-width (the right edge carries the floor-shadow bias, I2;
# spec chassis.width_note), read at 10 mm steps (scratch/w1/topp.py) and the spec's part widths
CHASSIS_HALF = [(244.8, 21.6), (290.0, 23.5), (318.0, 27.0), (404.0, 27.0), (414.0, 32.7), (505.0, 32.7),
                (522.0, 36.9), (836.8, 36.9)]
BUTT_HALF = [(68.9, 29.6), (190.0, 29.6), (212.0, 21.6), (245.0, 21.6)]


def half_at(table, x):
    xs = np.array([a for a, _ in table])
    ys = np.array([b for _, b in table])
    return float(np.interp(x, xs, ys))


def plan_ring(table, y_scale=1.0, extra=0.0):
    """Closed plan outline (X, Y) symmetric about Y 0 from a half-width table."""
    up = [(x, half_at(table, x) * y_scale + extra) for x, _ in table]
    lo = [(x, -y) for x, y in reversed(up)]
    return np.array(up + lo, float)


# ------------------------------------------------------------------------------------------------ W3 sockets / rig
def x_axis_rot(xa):
    """Unreal rotator (roll 0) whose +X is a socket's x axis given in frame M (= Blender axes; Unreal Y = -Blender Y)."""
    import math
    xa = np.asarray(xa, float)
    xa = xa / np.linalg.norm(xa)
    yaw = math.degrees(math.atan2(-xa[1], xa[0]))
    pitch = math.degrees(math.atan2(xa[2], math.hypot(xa[0], xa[1])))
    return {"roll": 0.0, "pitch": round(pitch, 4), "yaw": round(yaw, 4)}


def gun_socket_rows():
    """The spec's 20 gun sockets in the gunlib record shape (blender_mm = frame B mm, unreal_rotation_deg)."""
    return [dict(r, blender_mm=list(r["B_mm"]), unreal_rotation_deg=x_axis_rot(r["x_axis_M"])) for r in D["sockets"]["gun"]]


# gunlib proposal P1 applied SNIPER-SIDE (gunlib untouched): gun_standard / rig.STANDARD_BONES allow cheek_riser only
# under 'stock'; SR01 has a fixed butt and no stock bone ("never dummies"), so its riser hangs from 'body'
def standard_bones_p1():
    from gunlib import rig as RG
    t = dict(RG.STANDARD_BONES)
    t["cheek_riser"] = tuple(t.get("cheek_riser", ())) + ("body",)
    return t
