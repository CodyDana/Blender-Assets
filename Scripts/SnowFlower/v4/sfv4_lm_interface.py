"""Look-match round 1 (sword): the sword -> sheath interface, written whenever the guard changes.

    blender -b --factory-startup --python sfv4_lm_interface.py [-- --from-game]

Writes WorkFiles/SnowFlower/v4/lookmatch/sword_interface.json (model frame mm: origin = Grip socket, +Z to the tip,
+X spine, -Y front).  Measured on the generated LOD0/1/2 meshes (default: straight from the build code; --from-game:
from the shipped game blend's LOD objects) and on the guard high-poly:
  * guard_lower_envelope: per 1 mm slice from z 80 to the pendant tips, the x/y extents and the 2D convex hull of every
    hilt vertex (guard + pendant + blade section) - what the throat must clear / seat against;
  * seat: the lowest point of the guard's LEAF BODY (everything but the plug), per LOD - the sheath's seat rule;
  * pendant_plug: the part allowed INTO the mouth (front/back pendant leaves, hub bottom ring, blade section) and its
    extents per 1 mm slice;
  * blade: width / thickness envelope summary (unchanged by this pass: the blade profile is the v4 one).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_assemble as A  # noqa: E402
import sfv4_spec as S  # noqa: E402

ROOT = HERE.parents[2]
OUT = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "lookmatch" / "sword_interface.json"
PLUG_HALF_X = 15.5
PLUG_Z = 104.0
PLUG_BLADE_HALF_Y = 6.3
HILT_PARTS = ("guard", "collar", "fbloom", "grip", "gorn", "pommel", "pbloom")


def hull2d(P):
    P = np.unique(np.round(P, 3), axis=0)
    if len(P) < 3:
        return P.tolist()
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(tuple(p))
    for p in P[::-1]:
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(tuple(p))
    return [list(map(float, q)) for q in lo[:-1] + hi[:-1]]


def is_plug(V):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    return ((np.abs(x) < PLUG_HALF_X) & (z > PLUG_Z)) | ((np.abs(y) < PLUG_BLADE_HALF_Y) & (z > 96.0))


def lod_verts(level):
    d = A.build_low(level)
    hilt = np.vstack([np.array(d[k].verts) for k in HILT_PARTS if k in d])
    blade = np.vstack([np.array(d[k].verts) for k in ("blade", "relief") if k in d])
    return hilt, blade


def slices(V, z0, z1, step=1.0):
    out = []
    for z in np.arange(z0, z1, step):
        sel = (V[:, 2] >= z) & (V[:, 2] < z + step)
        if not sel.any():
            continue
        P = V[sel]
        out.append({"z": round(float(z + 0.5 * step), 2),
                    "x": [round(float(P[:, 0].min()), 3), round(float(P[:, 0].max()), 3)],
                    "y": [round(float(P[:, 1].min()), 3), round(float(P[:, 1].max()), 3)],
                    "hull_xy": [[round(a, 3), round(b, 3)] for a, b in hull2d(P[:, :2])]})
    return out


def main():
    t0 = time.time()
    env = {"written": time.strftime("%Y-%m-%d %H:%M:%S"),
           "writer": "Scripts/SnowFlower/v4/sfv4_lm_interface.py (look-match round 1, sword builder)",
           "frame": "mm; origin = Grip socket; +Z toward the tip; +X spine; -Y front",
           "plug_rule": {"PLUG_HALF_X": PLUG_HALF_X, "PLUG_Z": PLUG_Z, "PLUG_BLADE_HALF_Y": PLUG_BLADE_HALF_Y,
                         "text": "plug = (|x| < 15.5 and z > 104) or (|y| < 6.3 and z > 96): the pendant leaves, the hub's "
                                 "bottom ring and the blade section may enter the mouth; every other hilt vertex is leaf "
                                 "body and must stay above it (unchanged rule from the final pass)"},
           "lods": {}}
    for lv in (0, 1, 2):
        H, B = lod_verts(lv)
        allv = np.vstack([H, B])
        body = H[~is_plug(H)]
        plug = allv[is_plug(allv) & (allv[:, 2] < 140.0)]
        env["lods"][lv] = {
            "seat_leaf_body_lowest_z": round(float(body[:, 2].max()), 3),
            "seat_leaf_body_lowest_point": [round(float(v), 3) for v in body[np.argmax(body[:, 2])]],
            "hilt_lowest_z": round(float(H[:, 2].max()), 3),
            "hilt_bbox": [H.min(axis=0).round(3).tolist(), H.max(axis=0).round(3).tolist()],
            "plug_bbox": [plug.min(axis=0).round(3).tolist(), plug.max(axis=0).round(3).tolist()],
        }
        if lv == 0:
            env["guard_lower_envelope_lod0"] = slices(H[H[:, 2] > 80.0], 80.0, float(H[:, 2].max()) + 1.0)
            env["pendant_plug_lod0"] = slices(plug, PLUG_Z - 8.0, float(plug[:, 2].max()) + 1.0)
    hi = A.build_high(["guard"])
    HV = np.vstack([np.array(mb.verts) for mb in hi["guard"].values() if mb.verts])
    body = HV[~is_plug(HV)]
    env["high_guard"] = {"seat_leaf_body_lowest_z": round(float(body[:, 2].max()), 3),
                         "bbox": [HV.min(axis=0).round(3).tolist(), HV.max(axis=0).round(3).tolist()]}
    env["guard_lower_envelope_high"] = slices(HV[HV[:, 2] > 80.0], 80.0, float(HV[:, 2].max()) + 1.0)
    env["blade"] = {"z_seat_socket_BladeBase": S.Z_PENDANT_TIP, "z_tip": S.Z_TIP,
                    "note": "blade steel profile unchanged by look-match R1 (sfv4_spec WIDTH_TABLE / SECTION / SWEEP); "
                            "the relief now ends at z ~880 and a 0.25 mm ribbon strip exists only in the high-poly (baked)"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(env, open(OUT, "w"), indent=1)
    print("SF4_INTERFACE", json.dumps({lv: {k: v for k, v in d.items() if k.startswith("seat") or k == "hilt_lowest_z"}
                                       for lv, d in env["lods"].items()}), f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
