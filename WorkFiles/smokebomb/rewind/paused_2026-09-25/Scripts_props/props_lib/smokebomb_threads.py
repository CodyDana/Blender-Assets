#!/usr/bin/env python
"""props_lib.smokebomb_threads - REFERENCE_SPEC 6's loose threads, round 2.  numpy only.

Round 1's threads read as "straight, stiff, sometimes forked grey lines lying flat on the
surface" (the blind judge, pairs 16, 17, 19, 20) against the reference's "curly, warm-toned,
loop off the surface, with light and shadow".  What changed:

  * the path CURLS in three dimensions (a lateral wave plus a vertical one, a quarter turn
    apart, so it loops), and it LIFTS off the tape it falls onto (a hump up to ``lift_mm``
    between the root and the tip), so it casts its own shadow;
  * two or three plies, twisted near the root and splaying into separate curly strands
    toward the tip (T1 forks ~12 px from its tip, T2 slightly near the edge);
  * T4 is a small CURLED LOOP on the outline (6 px, dark: it is seen against the backdrop),
    not a straight spike; T5 is a short cluster of stubs on W's lower edge;
  * the threads' texture is the dye at a LIGHTER tone (warm tan, recolourable), T4 at the
    cloth's own tone (smokebomb_cloth.thread_texels ``ranges``).

Exactly T1-T5, no others (REFERENCE_SPEC 6: "Add no others").  Every tube keeps >= 0.008 mm2
per triangle (smokebomb_tape.tube_mesh; Unreal drops smaller ones).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_tape as T

hash01, vnoise1, VN_RMS, _smoothstep = T.hash01, T.vnoise1, T.VN_RMS, T._smoothstep


@dataclass(frozen=True)
class Thread2:
    plies: int = 2
    ply_r_mm: float = 0.065              # >= 0.065: the tip cone keeps >= 0.008 mm2 per triangle
    twist_pitch_mm: float = 0.55
    twist_r_mm: float = 0.045
    fork_from_tip_mm: float = 0.9
    fork_splay_mm: float = 0.30
    curl_amp_mm: float = 0.30          # lateral wave amplitude
    curl_len_mm: float = 1.1           # its wavelength
    curl_up_mm: float = 0.12           # the vertical wave (a quarter turn behind): loops
    lift_mm: float = 0.18              # the hump off the surface between root and tip
    strand_curl_mm: float = 0.22       # each forked strand's own extra wiggle
    sides: int = 3
    seg_mm: float = 0.16
    tone: str = "light"                # 'light' (warm tan) or 'cloth' (the tape's own tone)


def curly_core(root, tip, centre, r_low: float, ts: Thread2, seed: int = 0, drop_len_mm: float = 0.45,
               n: int = 96) -> np.ndarray:
    """Centre line from ``root`` (on the covering pass's cord) to ``tip`` (on the tape beneath),
    on a ball about ``centre``: it drops off the cord within ``drop_len_mm``, humps up to
    ``lift_mm`` off the surface and comes down to touch it at the tip, and curls in 3-D."""
    root = np.asarray(root, np.float64)
    tip = np.asarray(tip, np.float64)
    c0 = np.asarray(centre, np.float64)
    d0 = (root - c0) / np.linalg.norm(root - c0)
    d1 = (tip - c0) / np.linalg.norm(tip - c0)
    r_root = float(np.linalg.norm(root - c0))
    om = math.acos(float(np.clip(np.dot(d0, d1), -1, 1)))
    s = np.linspace(0.0, 1.0, n)
    if om < 1e-9:
        dirs = np.repeat(d0[None], n, 0)
    else:
        dirs = (np.sin((1 - s) * om)[:, None] * d0 + np.sin(s * om)[:, None] * d1) / math.sin(om)
    L = max(om * r_low, 1e-6)
    sl = s * L
    fall = _smoothstep(0.0, max(drop_len_mm, 1e-3), sl)
    hump = ts.lift_mm * np.sin(np.pi * np.clip(s, 0, 1)) ** 1.5 * (0.6 + 0.4 * fall)
    rad = r_root + (r_low - r_root) * fall + hump
    tang = np.gradient(dirs, axis=0)
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-12)
    side = np.cross(dirs, tang)
    ph1 = 2 * np.pi * hash01(seed, seed=seed + 1)
    wav = VN_RMS * 0.6 * (vnoise1(sl / (0.5 * ts.curl_len_mm) + 3.0 + 7.0 * hash01(seed, seed=seed + 9), seed + 2)
                          + 0.45 * vnoise1(sl / (0.22 * ts.curl_len_mm) + 1.0, seed + 3))
    env = _smoothstep(0.0, 0.35 * L, sl)
    lat = ts.curl_amp_mm * wav * env
    up = ts.curl_up_mm * VN_RMS * 0.6 * vnoise1(sl / (0.5 * ts.curl_len_mm) + 11.0, seed + 4) * env
    up = up * (1.0 - _smoothstep(0.85 * L, L, sl))
    return c0 + dirs * (rad + np.maximum(up, -0.5 * hump))[:, None] + side * lat[:, None]


def strands(core: np.ndarray, centre, ts: Thread2, seed: int = 0) -> List[np.ndarray]:
    """The plies about ``core``: twisted together near the root, splaying into separate curly
    strands over the last ``fork_from_tip_mm``."""
    c0 = np.asarray(centre, np.float64)
    seg = np.linalg.norm(np.diff(core, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    n = max(6, int(math.ceil(L / (0.4 * ts.seg_mm))) + 1)
    sl = np.linspace(0, L, n)
    P = np.stack([np.interp(sl, s, core[:, k]) for k in range(3)], 1)
    Tg = np.gradient(P, axis=0)
    Tg /= np.linalg.norm(Tg, axis=1, keepdims=True)
    up = (P - c0) / np.linalg.norm(P - c0, axis=1, keepdims=True)
    up = up - np.sum(up * Tg, 1, keepdims=True) * Tg
    up /= np.linalg.norm(up, axis=1, keepdims=True)
    sd = np.cross(Tg, up)
    fork0 = max(0.0, L - ts.fork_from_tip_mm)
    split = _smoothstep(fork0, L, sl) if L - fork0 > 1e-6 else np.zeros_like(sl)
    out = []
    for k in range(ts.plies):
        ph = 2 * np.pi * (sl / ts.twist_pitch_mm + k / max(ts.plies, 1))
        rr = ts.twist_r_mm * (1.0 - 0.8 * split)
        ang = 2 * np.pi * k / max(ts.plies, 1) + 0.6 * (hash01(k, seed=seed + 3) - 0.5)
        spl = ts.fork_splay_mm * split ** 0.8 * (0.7 + 0.6 * hash01(k, seed=seed + 4))
        wig = ts.strand_curl_mm * split * VN_RMS * 0.6 * vnoise1(sl / 0.35 + 5.0 * k, seed + 5)
        off = ((np.cos(ph) * rr + np.cos(ang) * spl + wig)[:, None] * sd
               + (np.sin(ph) * rr * (1 - split) + 0.35 * np.sin(ang) * spl)[:, None] * up)
        lift = np.where(np.sin(ph) < 0, -np.sin(ph) * rr * (1 - split), 0.0)
        out.append(P + off + up * lift[:, None])
    return out


def tubes(lines: Sequence[np.ndarray], ts: Thread2, centre, min_tri_mm2: float = 0.008):
    out = []
    for pl in lines:
        for k in range(10):
            part = T.tube_mesh(pl, ts.ply_r_mm, ts.sides, ts.seg_mm * (1.15 ** k), centre)
            if T.min_tri_area_mm2(part[0], part[1]) >= min_tri_mm2:
                break
        out.append(part)
    return out


def make_hanging(root, tip, ts: Thread2, seed: int, centre, r_low: float, drop_len_mm: float = 0.45):
    core = curly_core(root, tip, centre, r_low, ts, seed=seed, drop_len_mm=drop_len_mm)
    return tubes(strands(core, centre, ts, seed=seed), ts, centre)


def make_hook(root, out_dir, ts: Thread2, seed: int, centre, reach_mm: float = 0.45, loop_r_mm: float = 0.16):
    """T4: a small curled loop standing off the outline: out ``reach_mm`` along ``out_dir``
    (in the image plane, away from the ball) and curling back round a ``loop_r_mm`` circle."""
    root = np.asarray(root, np.float64)
    c0 = np.asarray(centre, np.float64)
    o = np.asarray(out_dir, np.float64)
    o = o / np.linalg.norm(o)
    rad = (root - c0) / np.linalg.norm(root - c0)
    # the loop's plane holds the outward direction and a direction along the outline
    along = np.cross(rad, np.array([0.0, 1.0, 0.0]))
    if np.linalg.norm(along) < 1e-6:
        along = np.array([1.0, 0.0, 0.0])
    along /= np.linalg.norm(along)
    n = 60
    t = np.linspace(0.0, 1.0, n)
    stem = np.clip(t / 0.45, 0, 1)
    P = root[None] + (reach_mm - loop_r_mm) * stem[:, None] * o[None]
    th = np.clip((t - 0.45) / 0.55, 0, 1) * 1.55 * np.pi
    loop = (loop_r_mm * np.sin(th))[:, None] * o[None] + (loop_r_mm * (1 - np.cos(th)))[:, None] * along[None]
    P = P + loop * (t[:, None] > 0.45)
    P = P + (0.05 * np.sin(np.pi * t))[:, None] * rad[None]
    return tubes([P], ts, centre)


def make_stubs(root, tip, ts: Thread2, seed: int, centre, r_low: float, count: int = 3, spread_mm: float = 0.35):
    """T5: a short cluster of stubs leaving the edge side by side."""
    root = np.asarray(root, np.float64)
    tip = np.asarray(tip, np.float64)
    c0 = np.asarray(centre, np.float64)
    along = np.cross((root - c0) / np.linalg.norm(root - c0), tip - root)
    along /= max(np.linalg.norm(along), 1e-9)
    out = []
    for k in range(count):
        f = (k - 0.5 * (count - 1)) / max(count - 1, 1)
        L = 0.6 + 0.5 * hash01(k, seed=seed + 7)
        r0 = root + along * f * spread_mm
        t0 = r0 + (tip - root) * L + along * 0.1 * (hash01(k, seed=seed + 8) - 0.5)
        core = curly_core(r0, t0, c0, r_low, ts, seed=seed + 11 * k, drop_len_mm=0.25)
        out += tubes([core], ts, c0)
    return out


#: REFERENCE_SPEC 6 - exactly these five.  root / tip in reference image px (the build finds the
#: 3-D root on the named edge and the tip on the surface it falls onto: smokebomb_ball.thread_parts)
THREAD_PRESETS2: Dict[str, Dict[str, object]] = {
    "T1": dict(root_px=(801, 703), tip_px=(797, 741), hangs_from="W lower edge", onto="A", seed=21, kind="hang",
               spec=Thread2(plies=3, ply_r_mm=0.065, fork_from_tip_mm=2.2, fork_splay_mm=0.80, curl_amp_mm=0.26,
                            curl_len_mm=1.2, curl_up_mm=0.14, lift_mm=0.20)),
    "T2": dict(root_px=(936, 783), tip_px=(932, 812), hangs_from="W lower edge", onto="A", seed=22, kind="hang",
               spec=Thread2(plies=2, ply_r_mm=0.065, fork_from_tip_mm=1.6, fork_splay_mm=0.45, curl_amp_mm=0.25,
                            curl_len_mm=0.9, curl_up_mm=0.12, lift_mm=0.16)),
    "T3": dict(root_px=(369, 603), tip_px=(381, 611), hangs_from=None, onto="A", seed=23, kind="lie",
               spec=Thread2(plies=2, ply_r_mm=0.065, fork_from_tip_mm=0.5, fork_splay_mm=0.22, curl_amp_mm=0.22,
                            curl_len_mm=0.6, curl_up_mm=0.08, lift_mm=0.08)),
    "T4": dict(root_px=(194, 434), tip_px=(186, 428), hangs_from="outline", onto=None, seed=24, kind="hook",
               spec=Thread2(plies=1, ply_r_mm=0.09, seg_mm=0.14, tone="cloth")),
    "T5": dict(root_px=(989, 820), tip_px=(991, 829), hangs_from="W lower edge", onto="A", seed=25, kind="stubs",
               spec=Thread2(plies=1, ply_r_mm=0.065, curl_amp_mm=0.06, curl_len_mm=0.5, curl_up_mm=0.05,
                            lift_mm=0.10)),
}

__all__ = ["Thread2", "curly_core", "strands", "tubes", "make_hanging", "make_hook", "make_stubs", "THREAD_PRESETS2"]
