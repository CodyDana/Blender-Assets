"""Moss as volume (pilot 2 fix 1 of the dojo rocks; STONE_BUILDING_STUDY.md 3.8). numpy only.

The judge on pilot 2: "moss is a flat green texture patch with a blurred mask edge and no volume or strands"; the
sheet's moss panel (bottom row, 3rd; looked at) shows tufted cushions of short upright shoots with yellow-green
tips and dark interiors, plus a few thin sporophyte stalks; on the boulders (row 2) the moss sits in ridge lines
along the crown and in the joints.

moss_cushions() scatters cushion sites over the moss field (Poisson-spaced, weighted by the field) and grows each
site as a dense tuft of short tapered shoots (opaque two-triangle-per-segment strips, no alpha: study 4.14), the
outer shoots leaning out so a cushion reads domed; ~4 % of the shoots are longer thin sporophyte stalks.
Vertex colour: R = height along the shoot (0 base -> 1 tip), G = per-shoot random, B = 1 for a sporophyte.
The cushion shell (stone_bake.cushion_shell) stays underneath as the dark, dense interior.
"""
from __future__ import annotations

import math

import numpy as np

import stone_sdf as sd


def pick_sites(V, N, w, spacing, rng, max_sites=600, nz_min=0.15):
    """Poisson-ish sites on vertices weighted by ``w`` (0-1), at least ``spacing`` apart."""
    idx = np.nonzero((w > 0.35) & (N[:, 2] > nz_min))[0]
    if not len(idx):
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0)
    p = w[idx] ** 1.5
    order = rng.choice(idx, min(len(idx), max_sites * 12), replace=False, p=p / p.sum())
    cell = spacing
    grid = {}
    out = []
    for i in order:
        q = V[i]
        key = tuple((q // cell).astype(int))
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if np.linalg.norm(V[j] - q) < spacing:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            out.append(i)
            grid.setdefault(key, []).append(i)
            if len(out) >= max_sites:
                break
    out = np.array(out, np.int64)
    return V[out], N[out], w[out]


def moss_cushions(sites, normals, strength, seed, shoots=(14, 26), height=(0.010, 0.028), radius=(0.014, 0.03),
                  sporophyte=0.04):
    rng = np.random.default_rng(seed)
    Vs, Fs, Cs = [], [], []
    off = 0
    for p, n0, s in zip(sites, normals, strength):
        n = sd.unit(np.asarray(n0) * 0.6 + np.array([0, 0, 0.4]))
        t = sd.unit(np.cross(n, [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]))
        b = np.cross(n, t)
        R = rng.uniform(*radius) * (0.7 + 0.3 * s)
        H = rng.uniform(*height) * (0.75 + 0.35 * s)
        for _ in range(int(rng.integers(*shoots) * (0.7 + 0.5 * s))):
            a = rng.uniform(0, 2 * math.pi)
            rr = R * math.sqrt(rng.uniform())
            rel = rr / R
            base = p + (t * math.cos(a) + b * math.sin(a)) * rr - n * 0.003
            out = sd.unit(t * math.cos(a) + b * math.sin(a))
            spo = rng.uniform() < sporophyte
            hgt = H * (1.0 - 0.55 * rel * rel) * rng.uniform(0.7, 1.15)     # domed cushion
            w = rng.uniform(0.0016, 0.0026)
            lean = 0.15 + 0.6 * rel
            if spo:
                hgt = H * rng.uniform(1.6, 2.4)
                w = 0.0005
                lean = rng.uniform(0.05, 0.25)
            side = sd.unit(np.cross(out, n) + rng.normal(0, 0.4, 3))
            pts = []
            for s_ in (0.0, 0.5, 1.0):
                bend = lean * s_ * s_
                c = base + n * hgt * s_ * (1 - 0.3 * bend) + out * hgt * bend
                ww = (w * (1.0 - 0.6 * s_) + 0.0002) if not spo else (0.0009 if s_ == 1.0 else w)
                pts += [c - side * ww, c + side * ww]
            Vs.append(np.array(pts))
            Fs.append(np.array([(0, 1, 3), (0, 3, 2), (2, 3, 5), (2, 5, 4)]) + off)
            g = rng.uniform()
            Cs.append(np.column_stack([np.repeat([0.0, 0.5, 1.0], 2), np.full(6, g), np.full(6, 1.0 if spo else 0.0)]))
            off += 6
    if not Vs:
        return None
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs)
