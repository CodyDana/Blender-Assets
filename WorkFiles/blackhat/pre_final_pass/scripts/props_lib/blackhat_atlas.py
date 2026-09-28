#!/usr/bin/env python
"""props_lib.blackhat_atlas - pack SM_BlackHat's UV members into the two 2048 atlases.

numpy only.  Every member keeps its OWN local coordinates (mm, strand / tape space, built by
blackhat_geom); the atlas only places it: UV px = A @ local + o with A a rotation x a uniform
scale (the atlas px/mm x the member's density), never a mirror or a stretch.  So one texel is
the same number of millimetres everywhere in a member, and the painter inverts the same map.

    straw   the skin (outer bays in interleaved PAIRS - two wedges head to tail fill a rectangle
            at ~98 %; the inner bays the same at half density), ribs, rim tube and binding cord
            chunks, 26 lashing sleeves, the crown lid (its cone development) and lip
    cloth   the band chunks, the knot, both tails' faces and their edge walls; UV0 U is offset
            by +1 (the second tile) so the two slots never overlap in UV0, which qa_check grades
            as one layout; the textures repeat, so U + 1 samples the same texel

The same analytic UVs serve every LOD (a LOD's members are the same parts with fewer vertices),
so the atlas is packed from LOD0 and reused.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from .blackhat_geom import COS_A, D2R, MeshBuilder, Member


@dataclass
class Placement:
    A: np.ndarray            # 2x2: local mm -> atlas px
    o: np.ndarray            # atlas px offset (U right, V up, px)
    island: str

    def uv_px(self, L):
        return np.asarray(L, np.float64) @ self.A.T + self.o

    def local(self, uvpx):
        return (np.asarray(uvpx, np.float64) - self.o) @ np.linalg.inv(self.A).T


@dataclass
class Atlas:
    name: str
    size: int
    ppmm: float
    pad: int
    place: Dict[str, Placement] = field(default_factory=dict)
    u_offset: float = 0.0
    fill: float = 0.0

    def uv(self, member: str, L):
        p = self.place[member].uv_px(L) / self.size
        p[..., 0] += self.u_offset
        return p

    def to_json(self):
        return {"name": self.name, "size": self.size, "px_per_mm": round(self.ppmm, 5),
                "texel_density_px_per_cm": round(self.ppmm * 10, 3), "padding_px": self.pad,
                "members": len(self.place), "islands": len({p.island for p in self.place.values()}),
                "fill_fraction": round(self.fill, 4), "u_offset": self.u_offset}


def fix_handedness(mb: MeshBuilder) -> Dict[str, int]:
    """Flip a member's local y when its faces would map mirrored (UV winding against the 3D
    winding), so no island is ever mirrored.  Returns the per-member count of faces still
    disagreeing after the fix (must be 0)."""
    P = np.asarray(mb.P)
    area = {}
    for fi, (f, L, key) in enumerate(zip(mb.F, mb.FL, mb.FM)):
        a = 0.5 * np.sum(L[:, 0] * np.roll(L[:, 1], -1) - np.roll(L[:, 0], -1) * L[:, 1])
        area.setdefault(key, []).append(a)
    bad = {}
    for key, al in area.items():
        al = np.array(al)
        m = mb.members[key]
        if np.sum(al) < 0:
            m.flip = -1.0
        bad[key] = int(np.sum(al * m.flip < 0))
    for fi, key in enumerate(mb.FM):
        if mb.members[key].flip < 0:
            mb.FL[fi] = mb.FL[fi] * np.array([1.0, -1.0])
    for m in mb.members.values():
        m.lo, m.hi = None, None
    for fi, key in enumerate(mb.FM):
        mb.members[key].extend(mb.FL[fi])
    return bad


def _wedge_half(m: Member) -> float:
    return 0.5 * (m.info["theta_b"] - m.info["theta_a"]) * D2R * COS_A


def _islands(mb: MeshBuilder, atlas: str, gap_mm: float):
    """-> list of (name, [(member, R2, t)], w, h) in density-scaled mm, R2 a 2x2 rotation."""
    out = []
    mem = [m for m in mb.members.values() if m.atlas == atlas]
    wedges = {}
    for m in mem:
        if m.kind == "wedge":
            wedges.setdefault(m.info["surface"], []).append(m)
    used = set()
    for surf, ws in wedges.items():
        ws = sorted(ws, key=lambda m: m.info["bay"])
        for i in range(0, len(ws), 2):
            grp = ws[i:i + 2]
            k = grp[0].density
            if len(grp) == 1:
                m = grp[0]
                out.append((f"wedgesolo_{m.key}", [(m, np.eye(2) * k, np.zeros(2))], None, None))
                used.add(m.key)
                continue
            a, b = grp
            si = k * min(a.info["s0"], b.info["s0"])
            so = k * max(a.info["s1"], b.info["s1"])
            ta, tb = math.tan(_wedge_half(a)), math.tan(_wedge_half(b))
            x0 = si + so
            y0 = max(si * ta + (x0 - si) * tb, so * ta + (x0 - so) * tb) + gap_mm
            Rb = -np.eye(2) * k
            out.append((f"wedgepair_{a.key}_{b.key}", [(a, np.eye(2) * k, np.zeros(2)), (b, Rb, np.array([x0, y0]))],
                        None, None))
            used.update([a.key, b.key])
    for m in mem:
        if m.key in used:
            continue
        out.append((f"isl_{m.key}", [(m, np.eye(2) * m.density, np.zeros(2))], None, None))
    # bboxes (from the members' face-corner extents, transformed)
    res = []
    for name, parts, _, _ in out:
        pts = []
        for m, R2, t in parts:
            c = np.array([[m.lo[0], m.lo[1]], [m.hi[0], m.lo[1]], [m.hi[0], m.hi[1]], [m.lo[0], m.hi[1]]])
            if m.kind == "wedge" or m.kind == "disc":
                # the true outline (arcs bulge past the corner box)
                c = _wedge_outline(m)
            pts.append(c @ R2.T + t)
        pts = np.concatenate(pts)
        lo, hi = pts.min(0), pts.max(0)
        parts = [(m, R2, t - lo) for m, R2, t in parts]
        res.append((name, parts, float(hi[0] - lo[0]), float(hi[1] - lo[1])))
    return res


def _wedge_outline(m: Member, n: int = 24):
    if m.kind == "disc":
        r = float(max(np.abs(m.lo).max(), np.abs(m.hi).max()))
        a = np.linspace(0, 2 * math.pi, 4 * n)
        return np.stack([r * np.cos(a), r * np.sin(a)], -1)
    h = _wedge_half(m)
    a = np.linspace(-h, h, n)
    s0, s1 = m.info["s0"], m.info["s1"]
    arc1 = np.stack([s1 * np.cos(a), s1 * np.sin(a)], -1)
    arc0 = np.stack([s0 * np.cos(a[::-1]), s0 * np.sin(a[::-1])], -1)
    return np.concatenate([arc1, arc0])


def _skyline(sizes, W, H):
    """Skyline bottom-left packing of rectangles (w, h) px, each tried in both orientations;
    -> [(x, y, rotated)] or None."""
    order = sorted(range(len(sizes)), key=lambda i: -max(sizes[i]) * min(sizes[i]) ** 0.5)
    sky = [(0.0, W, 0.0)]                       # (x0, x1, y)
    pos = [None] * len(sizes)
    for i in order:
        best = None
        for rot in (False, True):
            w, h = sizes[i] if not rot else sizes[i][::-1]
            if w > W:
                continue
            for k in range(len(sky)):
                x0 = sky[k][0]
                if x0 + w > W + 1e-9:
                    break
                # the highest skyline under [x0, x0 + w]
                y = 0.0
                for (a, b, yy) in sky[k:]:
                    if a >= x0 + w - 1e-9:
                        break
                    y = max(y, yy)
                if y + h > H + 1e-9:
                    continue
                key = (y + h, x0)
                if best is None or key < best[0]:
                    best = (key, x0, y, w, h, rot)
        if best is None:
            return None
        _, x0, y, w, h, rot = best
        pos[i] = (x0, y, rot)
        # update the skyline
        new = []
        for (a, b, yy) in sky:
            if b <= x0 or a >= x0 + w:
                new.append((a, b, yy))
                continue
            if a < x0:
                new.append((a, x0, yy))
            if b > x0 + w:
                new.append((x0 + w, b, yy))
        new.append((x0, x0 + w, y + h))
        new.sort()
        merged = []
        for seg in new:
            if merged and abs(merged[-1][2] - seg[2]) < 1e-9 and abs(merged[-1][1] - seg[0]) < 1e-9:
                merged[-1] = (merged[-1][0], seg[1], seg[2])
            else:
                merged.append(seg)
        sky = merged
    return pos


def pack(mb: MeshBuilder, atlas: str, size: int = 2048, pad: int = 8, u_offset: float = 0.0) -> Atlas:
    isl0 = _islands(mb, atlas, gap_mm=0.0)
    lo, hi = 0.05, 50.0
    best = None
    for _ in range(40):
        ppmm = 0.5 * (lo + hi)
        gap_mm = 2.0 * pad / ppmm
        isl = _islands(mb, atlas, gap_mm)
        sizes = [(w * ppmm + 2 * pad, h * ppmm + 2 * pad) for name, parts, w, h in isl]
        pos = _skyline(sizes, size, size)
        if pos is None:
            hi = ppmm
        else:
            lo = ppmm
            best = (ppmm, isl, sizes, pos)
    ppmm, isl, sizes, pos = best
    at = Atlas(atlas, size, ppmm, pad, u_offset=u_offset)
    area = 0.0
    for (name, parts, w, h), (px, py, rot) in zip(isl, pos):
        for m, R2, t in parts:
            A = ppmm * R2
            o = ppmm * t
            if rot:
                Rq = np.array([[0.0, -1.0], [1.0, 0.0]])
                A = Rq @ A
                o = Rq @ o + np.array([h * ppmm, 0.0])
            at.place[m.key] = Placement(A, o + np.array([px + pad, py + pad]), name)
        area += w * h * ppmm * ppmm
    at.fill = area / (size * size)
    return at


def apply_uvs(mb: MeshBuilder, atlases: Dict[str, Atlas]) -> List[np.ndarray]:
    """Per face, the corner UVs."""
    out = []
    for L, key in zip(mb.FL, mb.FM):
        m = mb.members[key]
        out.append(atlases[m.atlas].uv(key, L))
    return out


def uv_report(mb: MeshBuilder, uvs: List[np.ndarray]) -> Dict[str, object]:
    """Mirrored / collapsed UV faces against the 3D winding, and the UV range."""
    P = np.asarray(mb.P)
    mirrored = collapsed = 0
    allv = np.concatenate(uvs)
    for f, uv in zip(mb.F, uvs):
        a = 0.5 * np.sum(uv[:, 0] * np.roll(uv[:, 1], -1) - np.roll(uv[:, 0], -1) * uv[:, 1])
        if abs(a) < 1e-12:
            collapsed += 1
        elif a < 0:
            mirrored += 1
    return {"mirrored_faces": mirrored, "collapsed_faces": collapsed,
            "u_range": [float(allv[:, 0].min()), float(allv[:, 0].max())],
            "v_range": [float(allv[:, 1].min()), float(allv[:, 1].max())]}


__all__ = ["Atlas", "Placement", "pack", "apply_uvs", "uv_report", "fix_handedness"]
