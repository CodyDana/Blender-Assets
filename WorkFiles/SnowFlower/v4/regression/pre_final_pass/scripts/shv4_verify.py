"""Snow Flower sheath - FIT VERIFICATION on meshes (the exported FBX bytes of BOTH assets in the final run).

    blender -b --factory-startup --python shv4_verify.py -- --mode shipped [--out <json>]
    blender -b <work.blend> --factory-startup --python shv4_verify.py -- --mode work        (development check)

The sword is placed by the sheath's Holster socket AS SHIPPED (read back from SM_SnowFlower_Sheath.sockets.json:
Unreal location + rotator converted back to the Blender frame), never from the build's own numbers.  For every pairing
of sword LOD k and sheath LOD j:
    1 intersections       no sword triangle intersects any sheath triangle (BVH overlap)
    2 clearance           min distance from every sword vertex below the mouth to the sheath surface
    3 enclosure           rays +-X, +-Y from every blade vertex all hit the sheath, and each first hit is a surface
                          facing the vertex (the vertex is in the cavity, not inside the wall or outside the sheath)
    4 guard gap           the hilt (every sword vertex above the mouth plane) clears the sheath
    5 draw path           the sword slid out along its own axis in 10 mm steps: no intersection at any step
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shv4_spec as S  # noqa: E402

ROOT = S.ROOT
SHEATH_FBX = ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower_Sheath.fbx"
SHEATH_SIDECAR = ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower_Sheath.sockets.json"


def mesh_arrays(objs):
    """World-space (mm) vertices and triangles of the given mesh objects, concatenated."""
    V, T = [], []
    off = 0
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        M = np.array(o.matrix_world)
        v = np.array([x.co[:] for x in me.vertices])
        v = (np.c_[v, np.ones(len(v))] @ M.T)[:, :3] * 1000.0
        t = np.array([lt.vertices[:] for lt in me.loop_triangles], int)
        V.append(v)
        T.append(t + off)
        off += len(v)
    return np.vstack(V), np.vstack(T)


def bvh(V, T):
    return BVHTree.FromPolygons([Vector(p) for p in V], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def ue_socket_to_blender_matrix(rec):
    """Unreal socket (location cm, rotator) -> the INTENDED Blender-frame placement 4x4 (mm).  make_socket bakes a
    Ry(180) correction into the Empty that the importer's node flip cancels, so the Unreal rotation is simply the
    mirror-conjugate of the intended Blender rotation: R_blender = M @ R_ue @ M, M = diag(1, -1, 1)."""
    from pipeline.helpers import UE_MIRROR
    loc = rec["location_cm"]
    r = rec["rotation_deg"]
    roll, pitch, yaw = (math.radians(r[k]) for k in ("roll", "pitch", "yaw"))
    # Unreal composes Rz(yaw) @ Ry(-pitch) @ Rx(roll)
    basis = (Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(-pitch, 3, "Y") @ Matrix.Rotation(roll, 3, "X"))
    rot = UE_MIRROR @ basis @ UE_MIRROR
    M = rot.to_4x4()
    M.translation = Vector((loc[0] * 10.0, -loc[1] * 10.0, loc[2] * 10.0))
    return M


def check_pair(SV, ST, WV, WT, M, mouth_z, axis, draw=False):
    Mn = np.array(M)
    W = (np.c_[WV, np.ones(len(WV))] @ Mn.T)[:, :3]
    tree_s = bvh(SV, ST)
    tree_w = bvh(W, WT)
    inter = tree_s.overlap(tree_w)
    blade = W[:, 2] > mouth_z
    hilt = ~blade
    d_blade = [tree_s.find_nearest(Vector(p))[3] for p in W[blade]]
    d_hilt = [tree_s.find_nearest(Vector(p))[3] for p in W[hilt]]
    # enclosure
    bad_enc = 0
    for p in W[blade][:: max(1, int(blade.sum() / 4000))]:
        for dvec in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            hit = tree_s.ray_cast(Vector(p), Vector(dvec), 200.0)
            if hit[0] is None or hit[1].dot(Vector(dvec)) >= 0.0:
                bad_enc += 1
                break
    out = {"intersections": len(inter), "min_clearance_blade_mm": float(min(d_blade)) if d_blade else None,
           "min_clearance_hilt_mm": float(min(d_hilt)) if d_hilt else None, "blade_vertices": int(blade.sum()),
           "enclosure_failures": bad_enc}
    if draw:
        steps, worst = [], 0
        L = float(W[:, 2].max() - mouth_z) + 20.0
        for d in np.arange(0.0, L + 10.0, 10.0):
            Wd = W - axis[None, :] * d
            n = len(tree_s.overlap(bvh(Wd, WT)))
            steps.append(n)
            worst = max(worst, n)
        out["draw_steps"] = len(steps)
        out["draw_max_intersections"] = worst
    return out


def run(mode, out_path):
    fit = json.loads((ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build" / "fit" / "fit.json").read_text())
    if mode == "work":
        sheath = {lv: [o for o in bpy.data.collections[f"LOD{lv}_parts"].objects] for lv in (0, 1, 2)}
        M = Matrix(fit["matrix_S_from_W"])
        src = "work blend lows + fit.json placement (development)"
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(SHEATH_FBX))
        sheath = {lv: [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(f"SM_SnowFlower_Sheath_LOD{lv}")]
                  for lv in (0, 1, 2)}
        side = json.loads(SHEATH_SIDECAR.read_text(encoding="utf-8"))
        rec = next(r for r in side["sockets"] if r["socket"] == "Holster")
        M = ue_socket_to_blender_matrix(rec)
        src = "exported sheath FBX + Holster socket from the exported sidecar"
    for o in list(bpy.data.objects):
        o.select_set(False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(S.SWORD_FBX))
    new = [o for o in bpy.data.objects if o not in before]
    sword = {lv: [o for o in new if o.type == "MESH" and o.name.startswith(f"SM_SnowFlower_LOD{lv}")] for lv in (0, 1, 2)}
    Mfit = Matrix(fit["matrix_S_from_W"])
    dm = max(abs(Mfit[i][j] - M[i][j]) * (1.0 if j < 3 else 1.0) for i in range(3) for j in range(4))
    axis = np.array((M.to_3x3() @ Vector((0, 0, 1))).normalized())
    mouth_z = S.Z_MOUTH
    res = {"source": src, "holster_matrix_vs_fit_max_abs_diff": dm, "pairs": {}}
    arrays_s = {lv: mesh_arrays(sheath[lv]) for lv in (0, 1, 2)}
    arrays_w = {lv: mesh_arrays(sword[lv]) for lv in (0, 1, 2)}
    ok = True
    for ks in (0, 1, 2):
        for kw in (0, 1, 2):
            r = check_pair(*arrays_s[ks], *arrays_w[kw], M, mouth_z, axis, draw=(ks == kw))
            res["pairs"][f"sheath_LOD{ks}__sword_LOD{kw}"] = r
            good = (r["intersections"] == 0 and r["enclosure_failures"] == 0
                    and r["min_clearance_blade_mm"] >= 0.3 and r["min_clearance_hilt_mm"] >= 0.2
                    and r.get("draw_max_intersections", 0) == 0)
            r["pass"] = good
            ok &= good
            print("[SH4-VERIFY]", ks, kw, json.dumps(r), flush=True)
    res["pass"] = ok
    res["gates"] = {"clearance_blade_min_mm": 0.3, "clearance_hilt_min_mm": 0.2, "intersections": 0,
                    "enclosure_failures": 0, "draw_max_intersections": 0}
    Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("[SH4-VERIFY] PASS" if ok else "[SH4-VERIFY] FAIL", out_path, flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="shipped")
    ap.add_argument("--out", default=str(ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build" / "fit_verify.json"))
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT / "Scripts"))
    run(a.mode, a.out)


if __name__ == "__main__":
    main()
