#!/usr/bin/env python
"""Corner chamfer of the shipped card, measured two independent ways.

(a) PAPER SPACE.  The front UV island is a 1:1 map of the flat card (2048 px atlas at
    the spec's own px/mm), so the card outline - and therefore the corner clip - can be measured
    from the UV boundary without any assumption about how the sheet is curled.

(b) PLAN SPACE for the collision hull.  A true 2D convex hull of the UCX projected to XY,
    then the length and angle of each ~45 deg edge.

Run headless on the shipped FBX only.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
OUT = HERE / "chamfer.json"

ATLAS = 2048.0
# READ FROM THE SPEC, NOT TYPED.  This was hard-coded at 12.923, which was the texel
# density of the 156 mm card.  The reference of record's aspect puts the card at
# 162.29 mm, and the long side's 2048 px ceiling takes ppmm to 12.4222 with it - so a
# hard-coded 12.923 measured the new card's UV island as a 156 mm one and reported a
# chamfer 4 % small, with two corners at 37 degrees.  The verification is supposed to be
# independent of the build's REPORT, not of the build's own dimensions.
import sys
sys.path.insert(0, str(PROJ / "Scripts" / "props"))
from props_lib.spec import PAPER_BOMB as _SPEC                     # noqa: E402
PPMM = float(_SPEC.ppmm)
CARD_W_MM = float(_SPEC.width_mm)
CARD_H_MM = float(_SPEC.height_mm)
MM_PER_UV = ATLAS / PPMM          # 164.8590 mm across the full 0-1 UV range


def convex_hull_2d(pts):
    """Monotone chain; returns CCW hull points."""
    p = sorted({(round(float(x), 7), round(float(y), 7)) for x, y in pts})
    if len(p) < 3:
        return p

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx - ax) * (q[1] - ay) - (by - ay) * (q[0] - ax) <= 1e-9:
                    out.pop()
                else:
                    break
            out.append(q)
        return out

    return half(p)[:-1] + half(p[::-1])[:-1]


def clip_from_outline(hull, tag):
    """Given a CCW hull of a rectangle-with-45deg-corners, report each clip edge."""
    xs = [q[0] for q in hull]
    ys = [q[1] for q in hull]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    res = {"bbox": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
           "size": [round(x1 - x0, 4), round(y1 - y0, 4)], "corners": {}}
    n = len(hull)
    for i in range(n):
        a = np.array(hull[i])
        b = np.array(hull[(i + 1) % n])
        v = b - a
        L = float(np.hypot(*v))
        if L < 0.30:                       # ignore tessellation crumbs
            continue
        ang = math.degrees(math.atan2(abs(v[1]), abs(v[0])))
        if not (20.0 < ang < 70.0):        # only the diagonal (clip) edges
            continue
        mid = (a + b) * 0.5
        key = ("x+" if mid[0] > (x0 + x1) * 0.5 else "x-") + \
              ("y+" if mid[1] > (y0 + y1) * 0.5 else "y-")
        leg_x = abs(float(v[0]))
        leg_y = abs(float(v[1]))
        res["corners"][key] = {
            "chord_mm": round(L, 4),
            "leg_x_mm": round(leg_x, 4),
            "leg_y_mm": round(leg_y, 4),
            "leg_mean_mm": round((leg_x + leg_y) * 0.5, 4),
            "angle_deg": round(ang, 4),
            "a": [round(float(a[0]), 4), round(float(a[1]), 4)],
            "b": [round(float(b[0]), 4), round(float(b[1]), 4)],
        }
    res["tag"] = tag
    return res


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX), automatic_bone_orientation=True)
    report = {"mm_per_uv": round(MM_PER_UV, 6), "atlas_px": ATLAS, "ppmm": PPMM,
              "card_mm": [CARD_W_MM, CARD_H_MM],
              "ppmm_source": "props_lib.spec.PAPER_BOMB.ppmm"}

    # ---- (a) paper space, per LOD, from the FRONT UV island ---------------------------
    for lod in range(3):
        name = f"SM_PaperBomb_LOD{lod}"
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        mesh = obj.data
        uv = np.empty(len(mesh.loops) * 2, np.float64)
        mesh.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2) * MM_PER_UV
        umid = (uv[:, 0].min() + uv[:, 0].max()) * 0.5
        front = uv[uv[:, 0] < umid]
        back = uv[uv[:, 0] >= umid]
        entry = {}
        for tag, isl in (("front", front), ("back", back)):
            if len(isl) < 8:
                continue
            # normalise the island to its own origin so both read as a 70 x 156 card
            isl = isl - isl.min(axis=0)
            hull = convex_hull_2d(isl)
            entry[tag] = clip_from_outline(hull, tag)
            entry[tag]["island_points"] = int(len(isl))
            entry[tag]["hull_points"] = int(len(hull))
        report[name] = entry

    # ---- (b) plan space, the collision hull ------------------------------------------
    ucx = bpy.data.objects.get("UCX_SM_PaperBomb_LOD0_00")
    if ucx is not None:
        co = np.empty(len(ucx.data.vertices) * 3, np.float64)
        ucx.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) * 1000.0
        hull = convex_hull_2d(co[:, :2])
        report["UCX_plan"] = clip_from_outline(hull, "ucx_plan")
        report["UCX_plan"]["hull_points"] = int(len(hull))
        report["UCX_plan"]["z_range_mm"] = [round(float(co[:, 2].min()), 4),
                                            round(float(co[:, 2].max()), 4)]

    # LOD0 plan silhouette for comparison (curled, so the clip reads short in plan)
    l0 = bpy.data.objects.get("SM_PaperBomb_LOD0")
    if l0 is not None:
        co = np.empty(len(l0.data.vertices) * 3, np.float64)
        l0.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) * 1000.0
        hull = convex_hull_2d(co[:, :2])
        report["LOD0_plan"] = clip_from_outline(hull, "lod0_plan")
        report["LOD0_plan"]["hull_points"] = int(len(hull))
        # clearance: how far the UCX plan hull sits outside the LOD0 plan hull on the
        # diagonal supports (0 = the hull is tight on the chamfer)
        ph = convex_hull_2d(
            np.array([[v[0], v[1]] for v in
                      (np.array(bpy.data.objects["UCX_SM_PaperBomb_LOD0_00"].data.vertices[i].co)
                       * 1000.0 for i in range(len(
                           bpy.data.objects["UCX_SM_PaperBomb_LOD0_00"].data.vertices)))]))
        gaps = {}
        n = len(ph)
        for i in range(n):
            a = np.array(ph[i]); b = np.array(ph[(i + 1) % n])
            v = b - a
            L = float(np.hypot(*v))
            if L < 0.3:
                continue
            ang = math.degrees(math.atan2(abs(v[1]), abs(v[0])))
            if not (20.0 < ang < 70.0):
                continue
            nrm = np.array([v[1], -v[0]]) / L
            d = float(np.dot(nrm, a))
            support = float((co[:, :2] @ nrm).max())
            mid = (a + b) * 0.5
            key = ("x+" if mid[0] > 0 else "x-") + ("y+" if mid[1] > 0 else "y-")
            gaps[key] = round(d - support, 6)
        report["ucx_diagonal_clearance_over_lod0_mm"] = gaps

    HERE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[chamfer] ->", OUT)
    print(json.dumps(report, indent=1)[:4000])


main()
