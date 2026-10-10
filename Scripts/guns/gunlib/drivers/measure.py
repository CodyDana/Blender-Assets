"""Measure stage (gates L3 features and L4 dimensions) on the built geometry, frame M (mm), inside Blender. Promoted from
the AR-01's rifle_measure.py (gunlib 0.2.0): the ray-scan toolkit is here, each gun's feature list is its config hook.

    blender -b <gun>.blend --factory-startup --python <shim> -- [--out json]

Features are measured by ray scans of the built meshes (side rays along +Y from the right, top rays along -Z), never
from the build numbers; dimensions from part bounds and ray hits.

Config ``cfg.measure``: features(M) (the gun's hook: calls M.l3 / M.l4 with the toolkit below), px_per_mm (sheet px
per mm of the side views; L3 tolerance = 2 sheet px), out (default scratch/measure_result.json).
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np

from .. import bl
from .. import gateutil as GU


class Measurer:
    """Ray-scan toolkit on the gun's mesh objects (frame M, mm)."""

    def __init__(self, cfg, px_per_mm, collection=None):
        import bpy
        self.cfg = cfg
        self.spec = cfg.spec
        self.grip = cfg.grip
        self.tol_mm = 2.0 / px_per_mm
        src = bpy.data.collections[collection].objects if collection else bpy.data.objects
        self.objs = {o.name: o for o in src if o.type == "MESH" and not o.name.startswith("_")}
        self.GEO = {n: bl.tris_np(o, self.grip) for n, o in self.objs.items()}
        self.ALL = self.tree(list(self.GEO))
        self.res = {"L3": [], "L4": [], "tol_mm_side": round(self.tol_mm, 3)}

    # ------------------------------------------------------------------ geometry
    def tree(self, names):
        from mathutils.bvhtree import BVHTree
        V, T, n = [], [], 0
        for nm in names:
            v, t = self.GEO[nm]
            V.append(v)
            T.append(t + n)
            n += len(v)
        V, T = np.vstack(V), np.vstack(T)
        return BVHTree.FromPolygons([tuple(p) for p in V], [tuple(int(i) for i in t) for t in T], all_triangles=True)

    @staticmethod
    def ray(t, o, d, dist=1e4):
        from mathutils import Vector
        h = t.ray_cast(Vector(o), Vector(d), dist)
        return None if h[0] is None else np.array(h[0])

    def side_y(self, x, z, t=None):
        """First hit Y of a ray from the right (-Y) at (x, z); None = see-through."""
        h = self.ray(self.ALL if t is None else t, (x, -200.0, z), (0, 1, 0))
        return None if h is None else float(h[1])

    @staticmethod
    def edges_1d(vals, xs, pred):
        """Positions where pred(value) switches along xs (linear-midpoint)."""
        flags = np.array([pred(v) for v in vals])
        out = []
        for i in range(1, len(xs)):
            if flags[i] != flags[i - 1]:
                out.append(round(float(0.5 * (xs[i] + xs[i - 1])), 2))
        return out

    def see_through_bbox(self, x0, x1, z0, z1, step=0.1, seed=None):
        """bbox of the see-through region (rays from the right that hit nothing); with a seed, only the connected
        region containing it (4-neighbour flood fill on the scan grid)."""
        X = np.arange(x0, x1, step)
        Z = np.arange(z0, z1, step)
        M = np.array([[self.side_y(x, z) is None for z in Z] for x in X])
        if seed is not None:
            i0 = int(np.argmin(np.abs(X - seed[0])))
            j0 = int(np.argmin(np.abs(Z - seed[1])))
            if not M[i0, j0]:
                return None
            keep = np.zeros_like(M)
            q = deque([(i0, j0)])
            keep[i0, j0] = True
            while q:
                i, j = q.popleft()
                for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < len(X) and 0 <= b < len(Z) and M[a, b] and not keep[a, b]:
                        keep[a, b] = True
                        q.append((a, b))
            M = keep
        ii, jj = np.nonzero(M)
        if not len(ii):
            return None
        P = np.c_[X[ii], Z[jj]]
        return [round(float(P[:, 0].min()), 2), round(float(P[:, 0].max()), 2), round(float(P[:, 1].min()), 2),
                round(float(P[:, 1].max()), 2)]

    def bb(self, names):
        V = np.vstack([self.GEO[n][0] for n in names])
        return V.min(0), V.max(0)

    # ------------------------------------------------------------------ records
    def l3(self, name, measured, spec, err, note=""):
        self.res["L3"].append({"feature": name, "measured": measured, "spec": spec, "error_mm": None if err is None else
                               round(float(err), 3), "pass": err is not None and err <= self.tol_mm, "note": note})

    def l4(self, name, measured, spec, how, tol=0.05):
        err = abs(measured - spec)
        self.res["L4"].append({"dimension": name, "measured": round(float(measured), 3), "spec": spec,
                               "error_mm": round(float(err), 3), "pass": err <= tol, "how": how})


def main(cfg, argv=None):
    argv = GU.argv_after_dashes() if argv is None else argv
    C = cfg.measure
    M = Measurer(cfg, C["px_per_mm"], GU.opt(argv, "--collection"))
    C["features"](M)
    res = M.res
    res["L3_pass"] = all(f["pass"] for f in res["L3"])
    res["L4_pass"] = all(d["pass"] for d in res["L4"])
    out = Path(GU.opt(argv, "--out") or C.get("out") or cfg.scratch / "measure_result.json")
    out.write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    for f in res["L3"]:
        print("[L3]", f["pass"], f["feature"], f["measured"], "err", f["error_mm"])
    for d in res["L4"]:
        print("[L4]", d["pass"], d["dimension"], d["measured"], d["spec"], d["error_mm"])
    return res
