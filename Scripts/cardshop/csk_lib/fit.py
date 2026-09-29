"""Pure-Python seating and fit maths for the kit (CARDSHOP_KIT_SPEC.md 4.2-4.3). No bpy: runs under any Python.

Seating (HOUSE, armory 8): item world = slot transform x inverse(item Seat). Every G1 item's Seat is its origin with
identity rotation, so item world = slot transform. The fit test is zero-tolerance on render bounds: the item's
render AABB, carried into the container / level frame, must lie inside the clear volume and must not overlap a
neighbour or a collision hull (touching is allowed).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Box = Tuple[Vec3, Vec3]
EPS = 1e-4          # mm (0.1 micron): float32 vertex noise only (~4e-6 mm at 44 mm), not a fit tolerance


def rot_xyz(deg: Sequence[float]) -> List[List[float]]:
    """3x3 rotation of a Blender XYZ Euler in degrees (R = Rz @ Ry @ Rx)."""
    ax, ay, az = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return _mul(rz, _mul(ry, rx))


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def transform_box(box: Box, loc: Vec3, rot_deg: Vec3) -> Box:
    """AABB of ``box`` after rotating by ``rot_deg`` and moving to ``loc`` (the item's AABB in the slot's parent)."""
    r = rot_xyz(rot_deg)
    (x0, y0, z0), (x1, y1, z1) = box
    pts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    out = [tuple(loc[i] + sum(r[i][k] * p[k] for k in range(3)) for i in range(3)) for p in pts]
    mn = tuple(min(p[i] for p in out) for i in range(3))
    mx = tuple(max(p[i] for p in out) for i in range(3))
    return mn, mx  # type: ignore[return-value]


def inside(inner: Box, outer: Box) -> bool:
    return all(inner[0][i] >= outer[0][i] - EPS and inner[1][i] <= outer[1][i] + EPS for i in range(3))


def overlap(a: Box, b: Box) -> float:
    """Interior overlap volume (mm^3); 0 when the boxes only touch or are apart."""
    v = 1.0
    for i in range(3):
        d = min(a[1][i], b[1][i]) - max(a[0][i], b[0][i])
        if d <= EPS:
            return 0.0
        v *= d
    return v


def grid_slots(level_loc: Vec3, grid: Dict) -> List[Vec3]:
    """Slot floor centres of one class grid, in the fixture frame (levels are unrotated in G1)."""
    cols, rows = grid["cols"], grid["rows"]
    (px, py), (fx, fy) = grid["pitch_mm"], grid["first_mm"]
    return [(level_loc[0] + fx + c * px, level_loc[1] + fy + r * py, level_loc[2])
            for r in range(rows) for c in range(cols)]


def check_contain(container: str, cavity: Box, slots: Iterable[Tuple[str, Vec3, Vec3]], item: str,
                  item_box: Box) -> List[Dict]:
    """Every slot (name, loc, rot) seats ``item`` inside ``cavity`` with no neighbour overlap."""
    res = []
    placed = []
    for name, loc, rot in slots:
        b = transform_box(item_box, loc, rot)
        ok = inside(b, cavity)
        res.append({"test": "contain_fit", "container": container, "slot": name, "item": item, "passed": ok,
                    "item_aabb": [list(map(_r, b[0])), list(map(_r, b[1]))]})
        placed.append((name, b))
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            v = overlap(placed[i][1], placed[j][1])
            if v > 0:
                res.append({"test": "contain_neighbours", "container": container, "slot": placed[i][0],
                            "other": placed[j][0], "item": item, "passed": False, "overlap_mm3": _r(v)})
    return res


def check_level(fixture: str, level: Dict, level_loc: Vec3, grid: Dict, item: str, item_box: Box,
                hulls: Sequence[Box]) -> List[Dict]:
    """A class grid on one level: each item in its level's clear volume, inside its own pitch cell, clear of every
    collision hull (touching allowed; the shelf it stands on touches)."""
    w, d = level["interior_mm"]
    clear = level["clear_h_mm"]
    vol = ((level_loc[0] - w / 2, level_loc[1] - d / 2, level_loc[2]),
           (level_loc[0] + w / 2, level_loc[1] + d / 2, level_loc[2] + clear))
    px, py = grid["pitch_mm"]
    res = []
    bad_vol, bad_cell, bad_hull = [], [], []
    for k, s in enumerate(grid_slots(level_loc, grid)):
        b = transform_box(item_box, s, (0, 0, 0))
        cell = ((s[0] - px / 2, s[1] - py / 2, s[2]), (s[0] + px / 2, s[1] + py / 2, s[2] + clear))
        if not inside(b, vol):
            bad_vol.append(k)
        if not inside(b, cell):
            bad_cell.append(k)
        for hi, h in enumerate(hulls):
            if overlap(b, h) > 0:
                bad_hull.append((k, hi))
    n = grid["cols"] * grid["rows"]
    tag = {"fixture": fixture, "level": level["socket"], "class": grid["class"], "item": item, "slots": n}
    res.append(dict(tag, test="level_volume", passed=not bad_vol, failures=bad_vol[:10]))
    res.append(dict(tag, test="level_cell", passed=not bad_cell, failures=bad_cell[:10]))
    res.append(dict(tag, test="level_hulls", passed=not bad_hull, failures=bad_hull[:10]))
    return res


def check_stack(item: str, item_box: Box, stack: Dict, clear_h: float) -> Dict:
    """Spec 4.3: the stack pitch covers the render height, and the per-slot maximum is whatever fits the level's
    clear height, capped at the item's ``max``. Passes when at least one item fits; reports the effective max."""
    h = item_box[1][2] - item_box[0][2]
    pitch, mx = stack["pitch_mm"], stack["max"]
    fits = int(math.floor((clear_h - h + EPS) / pitch)) + 1 if clear_h >= h - EPS else 0
    effective = max(0, min(mx, fits))
    ok = pitch >= h - EPS and effective >= 1
    return {"test": "stack", "item": item, "passed": ok, "render_h_mm": _r(h), "pitch_mm": pitch,
            "max": mx, "effective_max": effective, "top_mm": _r((effective - 1) * pitch + h) if effective else None,
            "clear_h_mm": clear_h}


def _r(v: float) -> float:
    return round(v, 4) + 0.0
