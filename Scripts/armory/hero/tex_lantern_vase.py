"""The floor lantern's own washi picture (hero_lantern_vase, reference sheet WorkFiles/armory/reference/lantern.png):

  T_AK_HWashi_BC / _ORM / _N   one lantern pane, UV 0-1 over the pane (U across, V up), for M_AK_HWashi (emit_image,
                               unlit: the colour IS the glow). The sheet's orthographic panes: a flat pale cream washi
                               (sRGB ~221, 205, 189, luminance std ~4) with faint, kinked, branching tan veins (drawn
                               ~4 px wide so they survive the pane's ~5x minification on the sheet) and a fine mottled
                               formation; only a whisper of a warm centre. 1024 px, unique per pane (not tiled).
  T_AK_HWashiRoom_BC / _ORM / _N  calibration pass 2 (the room): the same paper with reference 2's glow painted in, a hot
                               pale-gold core fading to amber toward the frame (M_AK_HWashi wears it in the room).
  T_AK_HLacquer_BC / _ORM / _N the lantern frame's near-black satin lacquer (M_AK_HLacquer, 0.5 m tile), finely brushed
                               along V (hero_lantern_vase maps V along every member).

Judge deltas (2026-09-28): lantern 8 "aged and stained"; lantern 7.5 "faint crackle lines" (r6: strong fibres and an
amber hotspot); r7 (lantern 7.5): "peach / salmon with a strong central hotspot in every orthographic view, long curly
orange hair-lines like crackle; the sheet's orthographic panes are flat pale cream with mottled cloud fibres and faint
veins" -> the flat cream above (_veins: straight-ish kinked polylines, some branching off earlier ones). NEW sets only:
M_AK_LanternPaper (used by other pieces) is untouched.
Original and procedural (periodic FFT noise, no photo, scan or third-party source). Uses make_armory_textures'
writers (same PNG / DirectX-normal conventions). Never overwrites another set.

Run (Git Bash, from the project root):
  "/c/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/armory/hero/tex_lantern_vase.py [--room]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_armory_textures as MT  # noqa: E402

NAME = "HWashi"
# r7 (lantern 7.5, "peach / salmon with a strong central hotspot in every orthographic view, long curly uniform orange
# hair-lines that read like crackle; the sheet's orthographic panes are a flat pale cream with mottled cloud fibres and
# faint veins"): measured off lantern.png's front and top panes: mean sRGB 221, 205, 189, lum std only ~4: a flat cream
# (BASE_C), only a whisper of a warm centre (HOT_A), sparse faint branching tan veins (FIB_N, VEIN_K) and a fine mottled
# formation (CLOUD_K, MOTTLE_K)
HOT_K, HOT_A = 1.4, 0.035       # hotspot falloff and amplitude (was a full amber-to-white ramp)
BASE_C = "#E1BC8D"
FIB_N, VEIN_C, VEIN_K = 80, "#C4975E", 0.45
CLOUD_K, MOTTLE_K = 0.03, 0.045 # cloudy formation, fine mottle
# calibration pass 2 (2026-09-28, the room judge: the floor lanterns read as unlit grey-white paper in the room; reference
# 2's burn a hot pale-gold core fading to amber at the frame): the room variant T_AK_HWashiRoom (same paper, glow painted)
NAME_ROOM = "HWashiRoom"
ROOM_CORE, ROOM_EDGE, ROOM_HOT_K = "#FFD98C", "#C8701E", 1.3
LACQ = "HLacquer"               # the frame's near-black brushed lacquer (M_AK_HLacquer, 0.5 m tile)
LACQ_C = "#131211"


def _fibres(n, rng, count, length, width, bend, strength):
    """Kozo fibres: `count` thin, gently curved strands (quadratic curves `length` px long, random direction, a random
    sideways bow of up to `bend` x their length), each with its own strength, fading in and out along its length
    (they dive into and out of the sheet), splatted bilinearly and softened to about `width` px. -> 0..~1 map."""
    acc = np.zeros((n, n))
    for _ in range(count):
        L = rng.uniform(*length)
        th = rng.uniform(0, np.pi)
        c = rng.uniform(0, n, 2)
        d = np.array([np.cos(th), np.sin(th)])
        nrm = np.array([-d[1], d[0]])
        t = np.linspace(-0.5, 0.5, int(L * 2.2) + 2)
        bow = rng.uniform(-bend, bend) * L
        wig = rng.uniform(-0.02, 0.02, 3) * L
        side = bow * (1 - 4 * t * t) + wig[0] * np.sin(2 * np.pi * (t * 2 + wig[1]))
        pts = c[None, :] + t[:, None] * L * d[None, :] + side[:, None] * nrm[None, :]
        k = rng.uniform(*strength) * np.clip(np.sin(np.pi * (t + 0.5)) * rng.uniform(1.2, 2.0), 0, 1) ** 0.7
        x, y = pts[:, 0] % n, pts[:, 1] % n
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, ((y0 + dy) % n, (x0 + dx) % n), w * k / 2.2)
    acc = MT.blur(acc, max(1, int(round(width / 2))), 2) * width * 1.6
    return np.clip(acc, 0, 1)


def _veins(n, rng, count, length, width, strength, segs=(3, 5), turn=40):
    """The sheet's veins: straight-ish polylines (segs segments, each turning up to `turn` deg: kinked like the sheet's
    branching net, not curly hairs), some starting on an earlier vein (branching). -> 0..~1 map."""
    acc = np.zeros((n, n))
    starts = []
    for _ in range(count):
        L = rng.uniform(*length)
        if starts and rng.random() < 0.3:
            c = starts[rng.integers(len(starts))].copy()
        else:
            c = rng.uniform(0, n, 2)
        th = rng.uniform(0, 2 * np.pi)
        k0 = rng.uniform(*strength)
        ns = int(rng.integers(segs[0], segs[1] + 1))
        for j in range(ns):
            seg = L / ns * rng.uniform(0.6, 1.4)
            th += np.radians(rng.uniform(-turn, turn))
            d = np.array([np.cos(th), np.sin(th)])
            t = np.linspace(0, 1, int(seg * 2.2) + 2)
            pts = c[None, :] + t[:, None] * seg * d[None, :]
            f = (j + t) / ns
            k = k0 * np.clip(np.sin(np.pi * f) * 1.6, 0, 1) ** 0.6
            x, y = pts[:, 0] % n, pts[:, 1] % n
            x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
            fx, fy = x - x0, y - y0
            for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy),
                              (1, 1, fx * fy)):
                np.add.at(acc, ((y0 + dy) % n, (x0 + dx) % n), w * k / 2.2)
            c = pts[-1]
            starts.append(c.copy())
    acc = MT.blur(acc, max(1, int(round(width / 2))), 2) * width * 1.6
    return np.clip(acc, 0, 1)


def washi(n=1024, seed=701, room=False):
    """room (calibration pass 2): the SAME paper (seed, fibres, veins, relief) with the room's glow painted in: a hot
    pale-gold core fading to amber at the frame (ROOM_CORE / ROOM_EDGE), written as T_AK_HWashiRoom_*."""
    rng = np.random.default_rng(seed)
    v, u = (np.mgrid[0:n, 0:n] + 0.5) / n
    v = 1 - v                                                   # rows run down; V up
    # the glow: a flat cream field, only a whisper of warmth a little above the middle (the sheet's orthographic panes
    # are flat: the lamp shows only as the even glow)
    d2 = ((u - 0.5) / 0.46) ** 2 + ((v - 0.54) / 0.52) ** 2
    hot = np.exp(-HOT_K * d2)
    col = MT.srgb(BASE_C)[None, None, :] * (1 + HOT_A * (hot[..., None] - 0.5) * np.array([1.0, 0.97, 0.9]))
    if room:   # reference 2's floor lanterns: a hot pale-gold core over most of the pane, amber toward the frame
        t = np.exp(-ROOM_HOT_K * d2)[..., None]
        col = MT.srgb(ROOM_EDGE)[None, None, :] * (1 - t) + MT.srgb(ROOM_CORE)[None, None, :] * t
    # the sheet's fibres: sparse, faint, short branching tan veins (a loose net, not long hair-lines) and a few longer
    # pale strands; a fine mottled formation over a soft cloud
    # (the pane shows ~200 px wide on the sheet: the veins are drawn ~4 px wide and 80-260 px long so they survive the
    # 5x minification as the sheet's ~1 px, 20-50 px veins)
    tan = np.clip(_veins(n, rng, FIB_N, (90, 280), 3.2, (0.35, 1.0))
                  + 0.6 * _veins(n, rng, 90, (30, 90), 2.6, (0.3, 0.9), (1, 2), 30), 0, 1)
    pale = _fibres(n, rng, 120, (30, 120), 1.4, 0.15, (0.2, 0.5))
    cloud = MT.pnoise(n, n, 1.6, seed + 5)
    mottle = MT.pnoise(n, n, 0.7, seed + 7)
    grain = MT.pnoise(n, n, 0.3, seed + 6)
    vein_c = MT.srgb(VEIN_C)
    k = (VEIN_K * tan)[..., None]
    col = col * (1 - k) + (col * vein_c / MT.srgb("#EDE3D3")) * k
    col = col * (1 + 0.035 * pale[..., None] + CLOUD_K * cloud[..., None] + MOTTLE_K * mottle[..., None]
                 + 0.01 * grain[..., None])
    col = np.clip(col, 0, 1)
    height = 0.5 * tan + 0.3 * pale + 0.1 * cloud
    rough = np.full((n, n), 0.9)
    stats = MT.save_set(NAME_ROOM if room else NAME, col, height * 0.01, 1.0, rough)
    c = col.reshape(-1, 3)
    stats["centre_srgb"] = [round(float(x), 3) for x in col[int(n * 0.46), n // 2]]
    stats["corner_srgb"] = [round(float(x), 3) for x in col[8, 8]]
    stats["p05_srgb"] = [round(float(x), 3) for x in np.percentile(c, 5, axis=0)]
    return stats


def lacquer(n=1024, seed=733):
    """T_AK_HLacquer: lantern.png's frame, a near-black satin lacquer (sRGB ~27, neutral-warm) finely brushed along V
    (the members' length: hero_lantern_vase maps V along every member), 0.5 m tile (20 px / cm): fine long brush streaks,
    a few faint longer lighter strokes, satin roughness varying with the brushing."""
    fine = MT.pnoise(n, n, 0.5, seed, stretch_v=60.0)           # V variation suppressed: streaks long along V
    mid = MT.pnoise(n, n, 1.0, seed + 1, stretch_v=25.0)
    blot = MT.pnoise(n, n, 1.8, seed + 2)
    lum = 1 + 0.06 * fine + 0.04 * mid + 0.03 * blot
    col = MT.srgb(LACQ_C)[None, None, :] * lum[..., None]
    rough = np.clip(0.48 + 0.05 * fine + 0.04 * mid, 0.3, 0.65)
    height = 0.6 * fine + 0.4 * mid
    return MT.save_set(LACQ, np.clip(col, 0, 1), height * 0.004, 1.0, rough)


if __name__ == "__main__":
    for suf in ("BC", "ORM", "N"):
        assert (MT.OUT / f"T_AK_{NAME}_{suf}.png").name.startswith("T_AK_HWashi")
        assert (MT.OUT / f"T_AK_{LACQ}_{suf}.png").name.startswith("T_AK_HLacquer")
    if "--room" in sys.argv:   # calibration pass 2: only the room variant (the studio washi and lacquer are unchanged)
        print(json.dumps(washi(room=True), indent=1))
        sys.exit(0)
    print(json.dumps(washi(), indent=1))
    print(json.dumps(lacquer(), indent=1))
