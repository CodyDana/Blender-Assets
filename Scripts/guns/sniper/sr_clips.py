"""SR01 weapon clips as data (plain Python; imported by sr_rig.py in Blender, by the rig_verify driver and the fit /
render steps). SR01_BUILD_PLAN 3 / 4, spec clips (the SMG's smg_clips.py pattern).

Values per frame: rot (bolt rotation about the bore, deg, open = -60), bolt (mm back, only at rot -60), trigger /
selector / release (deg about Y: trigger + = blade rearward, selector FIRE 0 / SAFE -12, release - = pad forward),
insert (mm down the magazine's straight path Mag -> MagInsertStart, -Z), drop (mm further down, below MagInsertStart),
riser (mm, Z), cant (deg about X at Z -46), leg_l / leg_r (deg about each leg's SPLAYED pin: 0 folded forward, +90
deployed; the pin is rolled 12 deg about the leg axis, so the deployed leg leans 12 deg out), ext_l / ext_r (mm along
the leg's own rest X). basis_from() turns them into bone bases (mm; every rest rotation is identity, so a basis is the
bone's motion about its own head in weapon axes; children compose through the parents: leg under bipod, ext under
leg).

Rules (plan 1 / 4, the AR-01 and SMG lessons): Fire, BoltCycle and ReloadEmpty hold the safety at FIRE (the bind value
0) on every frame; ReloadEmpty starts with the bolt open and BipodStow starts deployed (starts_at_rest false);
BipodDeploy ends deployed (ends_at_rest false); the bolt slides only at the full -60 rotation.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gunlib import rig as RG  # noqa: E402

CODE = "SR01"
FPS = 30
FPS_FIRE = 60
ROT = -60.0
TRAVEL = 88.0
INSERT = 67.8               # Mag -> MagInsertStart along -Z (spec sockets)
DROP_MM = 160.0
TRIG = 6.0
SEL = {"FIRE": 0.0, "SAFE": -12.0}
SEL_HELD = 0.0              # FIRE
REL = -4.5
DEPLOY = 90.0
EXT_DEPLOY = 38.0
EXT_MAX = 76.0
CANT = 15.0
RISER = (-12.9, 12.0)
SPLAY = 12.0


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def accel(u):
    u = min(1.0, max(0.0, u))
    return u * u


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


def rot_x(deg):
    a = math.radians(deg)
    M = np.eye(4)
    M[1, 1], M[1, 2], M[2, 1], M[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return M


def leg_basis(side, deg):
    """rotation by deg about the leg's splayed pin (Y rolled SPLAY about X, outboard down), about the leg head."""
    Rr = rot_x(SPLAY if side == "l" else -SPLAY)
    return Rr @ RG.rot_y(deg) @ np.linalg.inv(Rr)


def basis_from(v):
    out = {}
    if v.get("rot") or v.get("bolt"):
        out["bolt"] = RG.trans(-v.get("bolt", 0.0)) @ rot_x(v.get("rot", 0.0))
    if v.get("trigger"):
        out["trigger"] = RG.rot_y(v["trigger"])
    if v.get("selector"):
        out["selector"] = RG.rot_y(v["selector"])
    if v.get("release"):
        out["mag_release"] = RG.rot_y(v["release"])
    s, d = v.get("insert", 0.0), v.get("drop", 0.0)
    if s or d:
        out["magazine"] = RG.trans(0.0, 0.0, -(s + d))
    if v.get("riser"):
        out["cheek_riser"] = RG.trans(0.0, 0.0, v["riser"])
    if v.get("cant"):
        out["bipod"] = rot_x(v["cant"])
    for sd in ("l", "r"):
        if v.get(f"leg_{sd}"):
            out[f"bipod_leg_{sd}"] = leg_basis(sd, v[f"leg_{sd}"])
        if v.get(f"ext_{sd}"):
            out[f"bipod_leg_{sd}_ext"] = RG.trans(v[f"ext_{sd}"])
    return out


def bolt_values(f, f_rot0, f_rot1, f_sl0, f_sl1, opening=True):
    """the sequenced path: rotation only at slide 0, slide only at rot -60."""
    if opening:
        return {"rot": seg(f, f_rot0, f_rot1, 0.0, ROT), "bolt": seg(f, f_sl0, f_sl1, 0.0, TRAVEL)}
    return {"bolt": seg(f, f_sl0, f_sl1, TRAVEL, 0.0), "rot": seg(f, f_rot0, f_rot1, ROT, 0.0)}


def clip_fire():
    """60 fps: the trigger breaks (f2), held, resets (f8); a bolt action: nothing else moves."""
    ks = [(0, 0.0), (2, TRIG), (4, TRIG), (8, 0.0)]
    return [(f, {"trigger": keys(f, ks)}) for f in range(9)], [("Fire", 2), ("TriggerReset", 8)], FPS_FIRE


def cycle_values(f):
    if f <= 14:
        return bolt_values(f, 0, 6, 6, 14, True)
    if f <= 16:
        return {"rot": ROT, "bolt": TRAVEL}
    return bolt_values(f, 24, 30, 16, 24, False)


def clip_bolt_cycle():
    frames = [(f, cycle_values(f)) for f in range(31)]
    return frames, [("BoltUnlock", 1), ("ShellEject", 13), ("BoltForward", 16), ("BoltLock", 30)], FPS


RELOAD_LEN = 60


def reload_values(i):
    """Paddle pressed (f0-3), the magazine straight down its path to MagInsertStart (f3-10) and dropped (f10-18); the
    new magazine back to MagInsertStart (f28-38) and up the path (f38-50); the paddle is FULLY pressed (f40-43) before
    the magazine's top reaches the hook (insert ~32 mm, f44: the square hook does not cam; M4b is the insert rule), held,
    and released as the magazine seats (f50): the hook snaps into the notch."""
    v = {}
    v["release"] = keys(i, [(0, 0.0), (3, REL), (10, REL), (12, 0.0), (40, 0.0), (43, REL), (49, REL), (50, 0.0)])
    v["insert"] = keys(i, [(3, 0.0), (10, INSERT), (38, INSERT), (50, 0.0)])
    v["drop"] = keys(i, [(10, 0.0), (18, DROP_MM), (28, DROP_MM), (38, 0.0)])
    if 10 <= i <= 18:
        v["drop"] = seg(i, 10, 18, 0.0, DROP_MM, accel)
    return v


def clip_reload(empty=False):
    frames = [(i, reload_values(i)) for i in range(RELOAD_LEN + 1)]
    notes = [("MagRelease", 2), ("MagOut", None), ("MagDrop", 18), ("MagIn", 50)]
    if not empty:
        return frames, notes, FPS
    # ReloadEmpty: the bolt open (rotated and back) through the swap, then forward (f62-70) and down (f70-76)
    out = [(i, dict(v, rot=ROT, bolt=TRAVEL)) for i, v in frames]
    for f in range(RELOAD_LEN + 1, 91):
        out.append((f, bolt_values(f, 70, 76, 62, 70, False)))
    notes += [("BoltForward", 62), ("BoltLock", 76)]
    return out, notes, FPS


def clip_selector():
    """FIRE (bind) -> SAFE -> FIRE, detents held."""
    ks = [(0, 0.0), (2, 0.0), (7, SEL["SAFE"]), (13, SEL["SAFE"]), (18, 0.0), (20, 0.0)]
    return [(f, {"selector": keys(f, ks)}) for f in range(21)], [], FPS


def deploy_values(f):
    return {"leg_l": keys(f, [(0, 0.0), (10, DEPLOY)]), "leg_r": keys(f, [(2, 0.0), (12, DEPLOY)]),
            "ext_l": keys(f, [(16, 0.0), (30, EXT_DEPLOY)]), "ext_r": keys(f, [(16, 0.0), (30, EXT_DEPLOY)])}


def clip_bipod_deploy():
    """Legs 0 -> +90 (the left leads by 2 frames: independent legs), detent click; then both extensions 0 -> 38 with
    the collar buttons pressed. Ends deployed."""
    frames = [(f, deploy_values(f)) for f in range(37)]
    return frames, [("BipodLegOut_L", 10), ("BipodLegOut_R", 12), ("BipodLocked", 30)], FPS


def clip_bipod_stow():
    """Starts deployed at ext 38: extensions 38 -> 0 (f0-14), then the legs +90 -> 0 (f18-32, the right leads),
    detent click; ends at the bind pose."""
    frames = [(f, {"ext_l": keys(f, [(0, EXT_DEPLOY), (14, 0.0)]), "ext_r": keys(f, [(0, EXT_DEPLOY), (14, 0.0)]),
                   "leg_l": keys(f, [(20, DEPLOY), (32, 0.0)]), "leg_r": keys(f, [(18, DEPLOY), (30, 0.0)])})
              for f in range(37)]
    return frames, [("BipodRetracted", 14), ("BipodStowed", 32)], FPS


def clip_cheek_riser():
    """Optional: rest -> +12 -> -12.9 -> rest (the lever opened first; the lever has no bone)."""
    ks = [(0, 0.0), (2, 0.0), (8, RISER[1]), (10, RISER[1]), (18, RISER[0]), (20, RISER[0]), (24, 0.0)]
    return [(f, {"riser": keys(f, ks)}) for f in range(25)], [], FPS


def hold_selector(frames, deg=SEL_HELD):
    return [(f, dict(v, selector=deg)) for f, v in frames]


def at_rest(v, allow_selector=True):
    vv = {k: x for k, x in v.items() if not (allow_selector and k == "selector")}
    return basis_from(vv) == {}


STARTS_AT_REST = {f"A_{CODE}_ReloadEmpty": False, f"A_{CODE}_BipodStow": False}
ENDS_AT_REST = {f"A_{CODE}_BipodDeploy": False}


def ends_rest(name, frames):
    sel = {round(float(v.get("selector", 0.0)), 6) for _f, v in frames}
    held = len(sel) == 1
    return at_rest(frames[0][1], held), at_rest(frames[-1][1], held)


def rest_as_declared(frames, name=None):
    """first / last frame = rest unless the clip declares otherwise; a declared non-rest end must NOT be rest."""
    s, e = ends_rest(name, frames)
    return s == STARTS_AT_REST.get(name, True) and e == ENDS_AT_REST.get(name, True)


# the ranges B3 / F swept with 0 intersections (gates/form.json): every clip value must stay inside
RANGES = {"rot": (ROT, 0.0), "bolt": (0.0, TRAVEL), "trigger": (0.0, TRIG), "selector": (SEL["SAFE"], 0.0),
          "release": (REL, 0.0), "riser": RISER, "cant": (-CANT, CANT), "leg_l": (0.0, DEPLOY), "leg_r": (0.0, DEPLOY),
          "ext_l": (0.0, EXT_MAX), "ext_r": (0.0, EXT_MAX)}
SAFETY_HELD = (f"A_{CODE}_Fire", f"A_{CODE}_BoltCycle", f"A_{CODE}_ReloadEmpty")


def all_clips(optional=True):
    def held(c):
        return (hold_selector(c[0]),) + tuple(c[1:])
    out = {f"A_{CODE}_Fire": held(clip_fire()), f"A_{CODE}_BoltCycle": held(clip_bolt_cycle()),
           f"A_{CODE}_Reload": clip_reload(False), f"A_{CODE}_ReloadEmpty": held(clip_reload(True)),
           f"A_{CODE}_Selector": clip_selector(), f"A_{CODE}_BipodDeploy": clip_bipod_deploy(),
           f"A_{CODE}_BipodStow": clip_bipod_stow()}
    if optional:
        out[f"A_{CODE}_CheekRiser"] = clip_cheek_riser()
    return out


def extreme_poses():
    """The B11 / physics-route envelope poses beyond the clips: bipod folded / deployed x ext 0 / 76 x cant -15 / 0 /
    +15, riser low / high, bolt open / back (name -> value dict)."""
    out = {}
    for legs in (0.0, DEPLOY):
        for ext in (0.0, EXT_MAX):
            for c in (-CANT, 0.0, CANT):
                out[f"legs{legs:g}_ext{ext:g}_cant{c:g}"] = {"leg_l": legs, "leg_r": legs, "ext_l": ext, "ext_r": ext,
                                                             "cant": c}
    for r in RISER:
        out[f"riser{r:g}"] = {"riser": r}
    out["bolt_open"] = {"rot": ROT}
    out["bolt_back"] = {"rot": ROT, "bolt": TRAVEL}
    return out
