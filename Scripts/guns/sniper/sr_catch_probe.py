"""SR01 W4 Part A1 probe: the generic straight M-gates (gunlib magfit_check.straight_gates, spring-loaded catch) on the
FORM-stage blend, so a catch / notch change is proven in seconds before the full chain (the AR-01's R51 lesson).

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_catch_probe.py [-- --out json]

Same config as sr_magfit.py (the shipped-bytes run) plus the overtravel's limiting part, reported.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import GRIP, gun_socket_rows  # noqa: E402
from gunlib import bl, gateutil as GU  # noqa: E402
from gunlib.drivers import magfit_check as MC  # noqa: E402
import sniper_parts as SP  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None

OBJS = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
GEO, BONE = {}, {}
for o in OBJS:
    V, T = bl.tris_np(o)
    GEO[o.name] = (V + GRIP, T)
    BONE[o.name] = json.loads(o.get("gun_part", "{}")).get("bone", "body")


class Scene:
    def __init__(self):
        mag = [n for n in GEO if BONE[n] == "magazine"]
        self.rn = [n for n in GEO if n not in mag]
        self.ci = self.rn.index("mag_release")
        def stack(names):
            Vs, Ts, L, off = [], [], [], 0
            for i, n in enumerate(names):
                V, T = GEO[n]
                Vs.append(V)
                Ts.append(T + off)
                L += [i] * len(T)
                off += len(V)
            return np.vstack(Vs), np.vstack(Ts), np.array(L)
        self.MV, self.MT, _ = stack(mag)
        self.RV, self.RT, self.RL = stack(self.rn)
        self.rtree = GU.tree(self.RV, self.RT)
        self.cV = self.RV
        self.cT = self.RT[self.RL == self.ci]


rows = {r["socket"]: r for r in gun_socket_rows()}
mag_M = np.array(rows["Mag"]["M_mm"], float)
ins = float(np.linalg.norm(mag_M - np.array(rows["MagInsertStart"]["M_mm"], float)))
S = Scene()
C = {"path": "straight", "catch": "mag_release", "catch_pivot_M": [408.6, 0.0, -74.0], "catch_axis": [0.0, 1.0, 0.0],
     "release_deg": -4.5, "mag_origin_M": mag_M.tolist(), "mag_axes_M": {"x": [1, 0, 0], "z": [0, 0, 1]},
     "insert_mm": ins, "well_band": [0.0, 44.8], "lip_z": 0.0, "well_parts": ("chassis",), "catch_zone_mm": 6.0,
     "half_thickness": 13.25, "half_length": 44.6}
if getattr(SP, "CATCH_SPRING", None):
    C["catch_spring"] = SP.CATCH_SPRING
gates = [] if "--ot-only" in argv else MC.straight_gates(S, C)
for g in gates:
    print("[SR01-catch]", "PASS" if g["pass"] else "FAIL", g["name"][:70], json.dumps(g["value"])[:420])

# the overtravel's limiting part (rays up the insert axis from the magazine's top 3 mm)
from mathutils import Vector  # noqa: E402
from gunlib import game as GM  # noqa: E402
Sm = GM.dense_samples(S.MV, S.MT, 0.25)
top = Sm[Sm[:, 2] > Sm[:, 2].max() - 3.0]
best = {}
for n in S.rn:
    if n == "mag_release":
        continue
    t = GU.tree(*GEO[n])
    d = 1e9
    for p in top:
        h = t.ray_cast(Vector(p) + Vector((0, 0, 1e-4)), Vector((0, 0, 1)), 30.0)
        if h[0] is not None:
            d = min(d, h[3])
    if d < 1e8:
        best[n] = round(d, 3)
print("[SR01-catch] overtravel by part", json.dumps(dict(sorted(best.items(), key=lambda kv: kv[1])[:6])))
# every vertical stop: rays up from ALL magazine samples (the gate looks at the top 3 mm only), per gun part, with
# where on the magazine the stop is (M frame)
stops = {}
for n in S.rn:
    if n == "mag_release":
        continue
    V, T = GEO[n]
    lo, hi = V.min(0), V.max(0)
    sel = Sm[(Sm[:, 0] > lo[0] - 1) & (Sm[:, 0] < hi[0] + 1) & (Sm[:, 1] > lo[1] - 1) & (Sm[:, 1] < hi[1] + 1)]
    if not len(sel):
        continue
    t = GU.tree(V, T)
    d, at = 1e9, None
    for p in sel:
        h = t.ray_cast(Vector(p) + Vector((0, 0, 1e-4)), Vector((0, 0, 1)), 10.0)
        if h[0] is not None and h[3] < d:
            d, at = h[3], [round(float(c), 2) for c in p]
    if d < 1e8:
        stops[n] = {"mm": round(d, 3), "mag_point_M": at}
print("[SR01-catch] vertical stops", json.dumps(dict(sorted(stops.items(), key=lambda kv: kv[1]["mm"])[:8])))
if OUT:
    OUT.write_text(json.dumps({"gates": gates, "overtravel_by_part": best}, indent=1, default=str))
print("[SR01-catch] DONE")
