"""AR-01 weapon clips as data (plain Python; imported by rifle_rig.py in Blender and by the verify / fit scripts).

Values per frame: bolt (mm back), trigger / selector / catch / leaf (deg, the B3 sweep axes and signs), magazine rock
(deg about the front-lug hook, MagRockStart sense), insert (mm along the tilted mag's -Z, MagInsertStart sense), drop
(mm along the weapon's -Z). basis_from() turns them into bone bases (mm; rest rotations are identity, so a basis is the
bone's motion about its own head in weapon axes). configure() sets the bolt travel and the reload path from the spec.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gunlib import rig as RG  # noqa: E402

FPS = 30
FPS_FIRE = 60

def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def seg(f, f0, f1, a, b, shape=ease):
    """Value at frame f of a move a -> b over frames f0..f1 (held outside)."""
    if f <= f0:
        return a
    if f >= f1:
        return b
    return a + (b - a) * shape((f - f0) / float(f1 - f0))


def lin(u):
    return min(1.0, max(0.0, u))


def accel(u):
    u = min(1.0, max(0.0, u))
    return u * u


TRAVEL = None              # bolt travel (mm) from the carrier's part record
ROCK = None                # MagRockStart pitch (deg) and insert distance (mm) from the spec sockets
INSERT = None
DROP_MM = 160.0


def basis_from(v):
    """Bone bases (mm) from clip values: bolt mm back; trigger / selector / catch / leaf degrees; magazine rock
    (deg), insert (mm along the tilted -Z) and drop (mm along the weapon's -Z)."""
    out = {}
    if v.get("bolt"):
        out["bolt"] = RG.trans(-v["bolt"])
    if v.get("trigger"):
        out["trigger"] = RG.rot_y(v["trigger"])
    if v.get("selector"):
        out["selector"] = RG.rot_y(v["selector"])
    if v.get("catch"):
        out["mag_release"] = RG.rot_y(-v["catch"])          # B3 axis -Y: + = top rearward (release)
    if v.get("leaf"):
        out["sight_rear"] = RG.rot_y(v["leaf"])
    th, s, d = v.get("rock", 0.0), v.get("insert", 0.0), v.get("drop", 0.0)
    if th or s or d:
        R = RG.rot_y(-th)                                   # MagRockStart: Blender rotation_euler.y = -theta
        t = R[:3, :3] @ np.array([0.0, 0.0, -s]) + np.array([0.0, 0.0, -d])
        M = R.copy()
        M[:3, 3] = t
        out["magazine"] = M
    return out


def clip_fire():
    """60 fps: trigger breaks (f1), the carrier runs to the rear stop and back to battery (~600 rpm cycle: back in
    2 frames, forward in 3), the finger releases and the trigger resets."""
    bolt = {0: 0.0, 1: 0.0, 2: 0.68 * TRAVEL, 3: TRAVEL, 4: 0.7 * TRAVEL, 5: 0.3 * TRAVEL, 6: 0.0, 7: 0.0, 8: 0.0}
    trig = {0: 0.0, 1: 12.0, 2: 12.0, 3: 12.0, 4: 12.0, 5: 12.0, 6: 12.0, 7: 6.0, 8: 0.0}
    frames = [(f, {"bolt": bolt[f], "trigger": trig[f]}) for f in range(9)]
    # stage-7 fix round (tech review): the case leaves the port once the carrier has pulled it back past the port,
    # i.e. at the rear stop (frame 3, full travel), not at frame 2 (the carrier only starting back)
    notes = [("Fire", 1), ("ShellEject", 3), ("TriggerReset", 8)]
    return frames, notes, FPS_FIRE


def clip_charge(f0=0):
    """Hand pulls the charging handle to the rear stop (0.4 s), holds (0.2 s) and lets go: the spring slams the
    carrier forward (2 frames)."""
    pull, hold, rel = 12, 6, 2
    frames = []
    for i in range(pull + hold + rel + 3):
        f = f0 + i
        if i <= pull:
            b = seg(i, 0, pull, 0.0, TRAVEL)
        elif i <= pull + hold:
            b = TRAVEL
        else:
            b = seg(i, pull + hold, pull + hold + rel, TRAVEL, 0.0, accel)
        frames.append((f, {"bolt": b}))
    notes = [("ChargeRear", f0 + pull), ("BoltRelease", f0 + pull + hold)]
    return frames, notes


def clip_selector():
    """safe (0) -> auto (16) -> semi (32), then back to safe; detents held."""
    keys = [(0, 0.0), (4, 16.0), (8, 16.0), (12, 32.0), (18, 32.0), (22, 16.0), (24, 16.0), (28, 0.0), (30, 0.0)]
    frames = []
    for f in range(31):
        for (fa, a), (fb, b) in zip(keys[:-1], keys[1:]):
            if fa <= f <= fb:
                frames.append((f, {"selector": seg(f, fa, fb, a, b)}))
                break
    notes = [("SelectorAuto", 4), ("SelectorSemi", 12), ("SelectorAuto", 22), ("SelectorSafe", 28)]
    return frames, notes, FPS


def reload_values(i):
    """Frame i of the reload: catch pressed, mag rocked out about the front-lug hook (Mag -> MagRockStart), lifted
    off the hook along its tilted -Z (-> MagInsertStart), pulled away down (off screen), held while the hand swaps
    mags, the full mag brought back to MagInsertStart, pushed onto the hook (-> MagRockStart), rocked in (-> Mag); the
    catch rides over the rear lug and snaps."""
    v = {"catch": 0.0, "rock": 0.0, "insert": 0.0, "drop": 0.0}
    v["catch"] = seg(i, 0, 3, 0.0, 10.0) if i <= 9 else seg(i, 9, 12, 10.0, 0.0)
    if i >= 50:
        v["catch"] = seg(i, 50, 52, 0.0, 6.0) if i <= 52 else seg(i, 52, 53, 6.0, 0.0, lin)
    if i <= 20:
        v["rock"] = seg(i, 3, 9, 0.0, ROCK)
        v["insert"] = seg(i, 9, 12, 0.0, INSERT)
        v["drop"] = seg(i, 12, 20, 0.0, DROP_MM, accel)
    elif i <= 34:
        v.update(rock=ROCK, insert=INSERT, drop=DROP_MM)
    else:
        v["drop"] = seg(i, 34, 44, DROP_MM, 0.0)
        v["insert"] = seg(i, 44, 47, INSERT, 0.0)
        v["rock"] = seg(i, 47, 53, ROCK, 0.0)
        if i <= 44:
            v.update(rock=ROCK, insert=INSERT)
        elif i <= 47:
            v["rock"] = ROCK
    return v


RELOAD_LEN = 60


def clip_reload(empty=False):
    frames = [(i, reload_values(i)) for i in range(RELOAD_LEN + 1)]
    notes = [("MagRelease", 2), ("MagOut", None), ("MagDrop", 20), ("MagIn", 53)]
    if empty:
        cf, cn = clip_charge(RELOAD_LEN + 2)
        frames += [(RELOAD_LEN + 1, {})] + [(f, v) for f, v in cf]
        notes += cn
    return frames, notes, FPS


# stage-7 fix round (craft review item 4): the clips that move the carrier (Fire, Charge, ReloadEmpty) ran with the
# selector at SAFE (lever up), which on the real pattern blocks the trigger and the carrier's rearward travel. Every clip
# except A_AR01_Selector now HOLDS the selector at the AUTO detent for its whole length (first frame = last frame, so
# looping and blending are unaffected); the game keeps the player's real fire mode with a per-bone layered blend of the
# 'selector' bone from the A_AR01_Selector poses (README, AnimBP notes). The static SM_AR01 and the bind pose stay on
# SAFE as the sheet draws them.
SELECTOR_HELD_DEG = 16.0


def hold_selector(frames, deg=SELECTOR_HELD_DEG):
    return [(f, dict(v, selector=deg)) for f, v in frames]


def loop_rest(frames):
    """True when the clip starts and ends in the same pose and that pose is the rest pose apart from a selector held
    at one detent through the whole clip (the clip's own selector track, or the held AUTO)."""
    a, b = frames[0][1], frames[-1][1]
    sel = {round(float(v.get("selector", 0.0)), 6) for _f, v in frames}
    no_sel = (lambda v: {k: x for k, x in v.items() if k != "selector"})
    held = len(sel) == 1 or (abs(a.get("selector", 0.0)) < 1e-9 and abs(b.get("selector", 0.0)) < 1e-9)
    return basis_from(no_sel(a)) == {} and basis_from(no_sel(b)) == {} and held and \
        abs(a.get("selector", 0.0) - b.get("selector", 0.0)) < 1e-9


def configure(travel, rock, insert):
    global TRAVEL, ROCK, INSERT
    TRAVEL, ROCK, INSERT = float(travel), float(rock), float(insert)


def all_clips():
    def held(c):
        return (hold_selector(c[0]),) + tuple(c[1:])
    return {"A_AR01_Fire": held(clip_fire()), "A_AR01_Charge": held(clip_charge() + (FPS,)),
            "A_AR01_Reload": held(clip_reload(False)), "A_AR01_ReloadEmpty": held(clip_reload(True)),
            "A_AR01_Selector": clip_selector()}
