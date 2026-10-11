"""SMG01 weapon clips as data (plain Python; imported by smg_rig.py in Blender, by the rig_verify driver and the fit /
H1 / render steps). SMG_BUILD_PLAN 13, spec clips.

Values per frame: bolt (mm back), handle (charging handle mm back), trigger / selector / release / stock / rear /
front (deg, the B3 sweep axes and signs: trigger + = lower end rearward, selector SAFE -63.4 / SEMI 0 / AUTO +45,
release - = nose rearward, stock + = folding to the right, rear sight + = folds forward, front sight - = folds
rearward), insert (mm along the magazine's own -Z, the straight reload path Mag -> MagInsertStart), drop (mm along the
weapon's -Z, below MagInsertStart). basis_from() turns them into bone bases (mm; every rest rotation is identity, so a
basis is the bone's motion about its own head in weapon axes). configure() sets the travels and the insert path from
the spec.

Rules (plan 13, the AR-01 lessons): every clip that moves the bolt holds the selector at AUTO from its first frame to
its last; ReloadEmpty starts with the bolt held open and the charging handle forward (starts_at_rest false); StockFold
ends folded and StockUnfold starts folded (their sidecar flags say so). The charging handle's 15 deg lock is in no clip
(the spec's clip list does not use it; the slide shares the 'charging_handle' bone and must not rotate) and the stock
latch button has no bone (plan 2.2: 11 bones): StockFold / StockUnfold rotate the stock with the latch at rest; the
latch bolt's path through the end-block lug is measured and reported by the rig (a rigid rig cannot press the button).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gunlib import rig as RG  # noqa: E402

FPS = 30
FPS_FIRE = 60
TRAVEL = 67.9              # bolt travel (spec clips.values.bolt_travel)
HANDLE = 67.9              # charging handle travel
INSERT = 68.2              # Mag -> MagInsertStart along the magazine's -Z
MAG_Z = np.array([-0.1438, 0.0, 0.9896])        # the magazine's +Z (out of the well) in weapon axes
DROP_MM = 160.0
SEL = {"SAFE": -63.4, "SEMI": 0.0, "AUTO": 45.0}
SEL_HELD = 45.0            # AUTO
TRIG = 13.0
REL = -11.0
FOLD = 180.0
REAR_FOLD, FRONT_FOLD = 90.0, -90.0


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def accel(u):
    u = min(1.0, max(0.0, u))
    return u * u


def lin(u):
    return min(1.0, max(0.0, u))


def seg(f, f0, f1, a, b, shape=ease):
    if f <= f0:
        return a
    if f >= f1:
        return b
    return a + (b - a) * shape((f - f0) / float(f1 - f0))


def keys(f, ks, shape=ease):
    """Piecewise value from [(frame, value), ...] (held outside)."""
    if f <= ks[0][0]:
        return ks[0][1]
    for (fa, a), (fb, b) in zip(ks[:-1], ks[1:]):
        if fa <= f <= fb:
            return seg(f, fa, fb, a, b, shape)
    return ks[-1][1]


def rot_z(deg):
    a = math.radians(deg)
    M = np.eye(4)
    M[0, 0], M[0, 1], M[1, 0], M[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return M


def basis_from(v):
    out = {}
    if v.get("bolt"):
        out["bolt"] = RG.trans(-v["bolt"])
    if v.get("handle"):
        out["charging_handle"] = RG.trans(-v["handle"])
    if v.get("trigger"):
        out["trigger"] = RG.rot_y(v["trigger"])
    if v.get("selector"):
        out["selector"] = RG.rot_y(v["selector"])
    if v.get("release"):
        out["mag_release"] = RG.rot_y(v["release"])
    if v.get("stock"):
        out["stock"] = rot_z(v["stock"])
    if v.get("rear"):
        out["sight_rear"] = RG.rot_y(v["rear"])
    if v.get("front"):
        out["sight_front"] = RG.rot_y(v["front"])
    s, d = v.get("insert", 0.0), v.get("drop", 0.0)
    if s or d:
        out["magazine"] = RG.trans(*(-s * MAG_Z + np.array([0.0, 0.0, -d])))
    return out


def clip_fire():
    """60 fps (~600 rpm blowback: back in 2 frames, forward in 3): the trigger breaks (f1), the bolt runs to the rear
    stop (f3) and back to battery (f6) while the charging handle stays forward (non-reciprocating), the trigger resets
    on the last frame."""
    bolt = {0: 0.0, 1: 0.0, 2: 0.62 * TRAVEL, 3: TRAVEL, 4: 0.6 * TRAVEL, 5: 0.2 * TRAVEL, 6: 0.0}
    trig = {0: 0.0, 1: TRIG, 2: TRIG, 3: TRIG, 4: TRIG, 5: 0.5 * TRIG, 6: 0.0}
    frames = [(f, {"bolt": bolt[f], "trigger": trig[f]}) for f in range(7)]
    return frames, [("Fire", 1), ("ShellEject", 3), ("TriggerReset", 6)], FPS_FIRE


def charge_values(i, bolt_open=False):
    """Frame i of the charge: the hand pulls the handle back (its slide's hook carries the bolt) to the rear stop
    (0.33 s), holds (0.13 s) and lets go: both run forward (2 frames)."""
    pull, hold, rel = 10, 4, 2
    if i <= pull:
        h = seg(i, 0, pull, 0.0, HANDLE)
    elif i <= pull + hold:
        h = HANDLE
    else:
        h = seg(i, pull + hold, pull + hold + rel, HANDLE, 0.0, accel)
    b = h if not bolt_open else (TRAVEL if i <= pull + hold else h)
    return {"handle": h, "bolt": b}


def clip_charge():
    frames = [(i, charge_values(i)) for i in range(23)]
    return frames, [("ChargeRear", 10), ("BoltRelease", 14)], FPS


RELOAD_LEN = 55


def reload_values(i):
    """The paddle pressed (nose out of the notch), the magazine straight down its own axis out of the well
    (-> MagInsertStart), dropped, held while the hand swaps magazines, the full magazine brought back to
    MagInsertStart and pushed up the axis; over its last mm its rear face cams the spring-loaded catch back (the paddle
    swings to the release angle) and the nose snaps into the notch as it seats."""
    v = {"release": 0.0, "insert": 0.0, "drop": 0.0}
    # the new magazine's rear face cams the nose from 26 mm before the seat (M4 on the shipped bytes): the paddle is
    # swung to the release angle before the magazine reaches it (f44: 34 mm to go) and snaps back as it seats
    v["release"] = keys(i, [(0, 0.0), (3, REL), (10, REL), (12, 0.0), (42, 0.0), (44, REL), (48, REL), (49, 0.0)])
    v["insert"] = keys(i, [(3, 0.0), (9, INSERT), (40, INSERT), (48, 0.0)])
    v["drop"] = keys(i, [(9, 0.0), (17, DROP_MM), (30, DROP_MM), (40, 0.0)])
    if 9 <= i <= 17:
        v["drop"] = seg(i, 9, 17, 0.0, DROP_MM, accel)
    return v


def clip_reload(empty=False):
    frames = [(i, reload_values(i)) for i in range(RELOAD_LEN + 1)]
    notes = [("MagRelease", 2), ("MagOut", None), ("MagDrop", 17), ("MagIn", 48)]
    if not empty:
        return frames, notes, FPS
    # ReloadEmpty: the bolt held open throughout the swap (the internal hold-open, not modelled), the handle forward;
    # then the handle pulled fully back to the open bolt and released: both run forward
    out = [(i, dict(v, bolt=TRAVEL)) for i, v in frames]
    base = RELOAD_LEN + 2
    out.append((RELOAD_LEN + 1, {"bolt": TRAVEL}))
    for i in range(23):
        cv = charge_values(i, bolt_open=True)
        out.append((base + i, cv))
    last = out[-1][0]
    for f in range(last + 1, 81):
        out.append((f, {}))
    notes += [("ChargeRear", base + 10), ("BoltRelease", base + 14)]
    return out, notes, FPS


def clip_selector():
    """SEMI (bind) -> SAFE -> SEMI -> AUTO -> SEMI, detents held (the design call, Q16)."""
    ks = [(0, 0.0), (5, SEL["SAFE"]), (9, SEL["SAFE"]), (14, 0.0), (16, 0.0), (21, SEL["AUTO"]), (25, SEL["AUTO"]),
          (30, 0.0)]
    return [(f, {"selector": keys(f, ks)}) for f in range(31)], [], FPS


def clip_stock_fold(unfold=False):
    """The stock about the hinge axle (Z) to the right, 0 -> 180 (fold) or 180 -> 0 (unfold): unlocked at f1-2, the
    swing over f2-21 (eased), locked (the lug's barb under the port catch's lip / the latch bolt in its bore) at the
    end."""
    ks = [(0, 0.0), (2, 0.0), (21, FOLD), (24, FOLD)]
    frames = [(f, {"stock": keys(f, ks)}) for f in range(25)]
    if unfold:
        frames = [(f, {"stock": FOLD - v["stock"]}) for f, v in frames]
    return frames, [("StockUnlock", 1), ("StockLocked", 24)], FPS


def clip_sight_flip():
    """Both flip sights up -> folded -> up (Q12: shipped)."""
    ks_r = [(0, 0.0), (2, 0.0), (8, REAR_FOLD), (12, REAR_FOLD), (18, 0.0), (20, 0.0)]
    ks_f = [(0, 0.0), (2, 0.0), (8, FRONT_FOLD), (12, FRONT_FOLD), (18, 0.0), (20, 0.0)]
    return [(f, {"rear": keys(f, ks_r), "front": keys(f, ks_f)}) for f in range(21)], [], FPS


def hold_selector(frames, deg=SEL_HELD):
    return [(f, dict(v, selector=deg)) for f, v in frames]


def at_rest(v, allow_selector=True):
    vv = {k: x for k, x in v.items() if not (allow_selector and k == "selector")}
    return basis_from(vv) == {}


def loop_rest(frames):
    """First and last frame at rest, apart from a selector held at one detent through the whole clip."""
    a, b = frames[0][1], frames[-1][1]
    sel = {round(float(v.get("selector", 0.0)), 6) for _f, v in frames}
    held = len(sel) == 1
    return at_rest(a, held) and at_rest(b, held) and abs(a.get("selector", 0.0) - b.get("selector", 0.0)) < 1e-9


STARTS_AT_REST = {"A_SMG01_ReloadEmpty": False, "A_SMG01_StockUnfold": False}
ENDS_AT_REST = {"A_SMG01_StockFold": False}


def ends_rest(name, frames):
    """(starts at rest, ends at rest) by the clip's own declaration, checked against its first / last frame."""
    sel = {round(float(v.get("selector", 0.0)), 6) for _f, v in frames}
    held = len(sel) == 1
    return at_rest(frames[0][1], held), at_rest(frames[-1][1], held)


def rest_as_declared(frames, name=None):
    """The rig_verify rule: first / last frame = rest unless the clip declares otherwise (StockFold ends folded,
    StockUnfold starts folded, ReloadEmpty starts with the bolt open); a declared non-rest end must NOT be rest."""
    s, e = ends_rest(name, frames)
    return s == STARTS_AT_REST.get(name, True) and e == ENDS_AT_REST.get(name, True)


def configure(travel, handle, insert):
    global TRAVEL, HANDLE, INSERT
    TRAVEL, HANDLE, INSERT = float(travel), float(handle), float(insert)


def all_clips():
    def held(c):
        return (hold_selector(c[0]),) + tuple(c[1:])
    return {"A_SMG01_Fire": held(clip_fire()), "A_SMG01_Charge": held(clip_charge()),
            "A_SMG01_Reload": clip_reload(False), "A_SMG01_ReloadEmpty": held(clip_reload(True)),
            "A_SMG01_Selector": clip_selector(), "A_SMG01_StockFold": clip_stock_fold(False),
            "A_SMG01_StockUnfold": clip_stock_fold(True), "A_SMG01_SightFlip": clip_sight_flip()}
