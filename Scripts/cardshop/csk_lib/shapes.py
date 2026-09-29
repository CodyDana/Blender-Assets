"""Pure-Python shape building for the Card Shop Kit (no bpy): outlines in mm and the face-list ``Builder`` that
``mesh.to_object`` turns into a Blender mesh. Kept free of bpy so the geometry definitions (geom.py) and their
numbers are importable and testable under any Python."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]


# --------------------------------------------------------------------------- outlines (mm, CCW seen from +Z)

def rect(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> List[Tuple[float, float]]:
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def rounded_rect(w: float, h: float, r: float, segs: int) -> List[Tuple[float, float]]:
    """Rounded rectangle centred on the origin, ``segs`` segments per corner (segs + 1 points per corner)."""
    pts = []
    corners = ((w / 2 - r, -h / 2 + r, -90.0), (w / 2 - r, h / 2 - r, 0.0),
               (-w / 2 + r, h / 2 - r, 90.0), (-w / 2 + r, -h / 2 + r, 180.0))
    for cx, cy, a0 in corners:
        for i in range(segs + 1):
            a = math.radians(a0 + 90.0 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def chamfer_rect(w: float, h: float, c: float, cx: float = 0.0, cy: float = 0.0) -> List[Tuple[float, float]]:
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c),
            (x0, y0 + c)]


# --------------------------------------------------------------------------- builder

@dataclass
class Face:
    verts: Tuple[int, ...]
    mat: int
    region: int


@dataclass
class Fill:
    loops: List[List[int]]      # first loop outer, the rest holes
    mat: int
    region: int
    normal: Vec3                # the side the filled faces must face


@dataclass
class Builder:
    verts: List[Vec3] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    fills: List[Fill] = field(default_factory=list)

    def v(self, x: float, y: float, z: float) -> int:
        self.verts.append((float(x), float(y), float(z)))
        return len(self.verts) - 1

    def face(self, idx: Sequence[int], mat: int = 0, region: int = 0) -> None:
        self.faces.append(Face(tuple(idx), mat, region))

    def loop(self, outline: Sequence[Tuple[float, float]], z: float) -> List[int]:
        return [self.v(x, y, z) for x, y in outline]

    def fill(self, loops: List[List[int]], mat: int, region: int, normal: Vec3) -> None:
        self.fills.append(Fill(loops, mat, region, normal))

    # ---- solids
    def box(self, mn: Vec3, mx: Vec3, mat: int = 0, region: int = 0, inward: bool = False,
            regions: Optional[Dict[str, int]] = None, mats: Optional[Dict[str, int]] = None,
            skip: Sequence[str] = ()) -> None:
        """An axis-aligned box. ``regions`` / ``mats`` override per side: px nx py ny pz nz. ``inward`` flips the
        winding (a cavity). ``skip`` leaves sides open."""
        (x0, y0, z0), (x1, y1, z1) = mn, mx
        c = [self.v(x0, y0, z0), self.v(x1, y0, z0), self.v(x1, y1, z0), self.v(x0, y1, z0),
             self.v(x0, y0, z1), self.v(x1, y0, z1), self.v(x1, y1, z1), self.v(x0, y1, z1)]
        sides = {"nz": (c[0], c[3], c[2], c[1]), "pz": (c[4], c[5], c[6], c[7]),
                 "ny": (c[0], c[1], c[5], c[4]), "py": (c[2], c[3], c[7], c[6]),
                 "nx": (c[3], c[0], c[4], c[7]), "px": (c[1], c[2], c[6], c[5])}
        for key, quad in sides.items():
            if key in skip:
                continue
            q = tuple(reversed(quad)) if inward else quad
            self.face(q, (mats or {}).get(key, mat), (regions or {}).get(key, region))

    def prism(self, outline: Sequence[Tuple[float, float]], z0: float, z1: float, mat: int = 0,
              top: Optional[int] = 0, bottom: Optional[int] = 0, side: int = 0,
              top_mat: Optional[int] = None, bottom_mat: Optional[int] = None) -> Tuple[List[int], List[int]]:
        """Extrude a CCW outline from z0 to z1. ``top`` / ``bottom`` region None leaves that cap open (the caller
        fills it, e.g. with holes). Returns (bottom loop, top loop)."""
        lb, lt = self.loop(outline, z0), self.loop(outline, z1)
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            self.face((lb[i], lb[j], lt[j], lt[i]), mat, side)
        if top is not None:
            self.fill([lt], mat if top_mat is None else top_mat, top, (0, 0, 1))
        if bottom is not None:
            self.fill([lb], mat if bottom_mat is None else bottom_mat, bottom, (0, 0, -1))
        return lb, lt
