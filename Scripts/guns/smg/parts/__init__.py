"""SMG01 part generators (plain Python + numpy; Blender only through gunlib.parts.build_part / build_composite).

Each module exposes functions that return a list of builds:
  PartDef                                   built by gunlib.parts.build_part
  Comp(name, pieces, cutters, bone, ...)    built by gunlib.parts.build_composite (pieces edge-broken, then united)
Everything is in frame M (mm); smg_parts.build_all converts to frame B (Grip) and registers the objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

METAL = "M_SMG01_Metal"
FURN = "M_SMG01_Furniture"
MAGS = "M_SMG01_Mag"
GAP = 0.02                 # butt-joint modelled gap (clearance row 0.01-0.05)


@dataclass
class Comp:
    name: str
    pieces: list
    cutters: list = field(default_factory=list)
    bone: str = "body"
    cls: str = "M-chamfer"
    slot: str = METAL
    joint: Optional[Dict[str, Any]] = None
    spec_id: Optional[str] = None
    smooth_deg: float = 30.0


def pcyl(p0, p1, r, n=48):
    """A cylinder whose end caps are fans round a centre pole (no sliver triangulation of a big n-gon cap: UD2)."""
    import numpy as np
    from gunlib.mesh import revolve
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    return revolve([(0.0, 0.0), (0.0, r), (L, r), (L, 0.0)], p0, p1 - p0, n)


def loft_capped(rings):
    """A loft of closed rings whose two end caps are fans round the ring centroids."""
    import numpy as np
    from gunlib.mesh import Mesh
    m = Mesh()
    idx = [m.add_verts(r) for r in rings]
    n = len(rings[0])
    for a, b in zip(idx[:-1], idx[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            m.face((a[k], a[k2], b[k2], b[k]))
    c0 = m.add_verts([np.asarray(rings[0]).mean(0)])[0]
    c1 = m.add_verts([np.asarray(rings[-1]).mean(0)])[0]
    for k in range(n):
        k2 = (k + 1) % n
        m.face((idx[0][k2], idx[0][k], c0))
        m.face((idx[-1][k], idx[-1][k2], c1))
    return m
