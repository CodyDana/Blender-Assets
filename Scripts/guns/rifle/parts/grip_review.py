"""Grip detail review build (headless Blender): the current form blend with ONLY the pistol grip rebuilt from
parts/grip.py, plus the review-only checker field (grip.REVIEW_EXTRAS), saved to a private scratch blend so parallel
part builders never overwrite each other's Assets/Guns/AR01.blend or scratch/form_tris.npz.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/parts/grip_review.py --
        --out <blend> --npz <tris.npz> --report <json> [--no-extras]

Writes: the blend (pistol_grip + pistol_grip_checker in place), the .npz (every LOD0 mesh, no review extras), and a
report: grip triangles, manifold report, checker-field triangles, the old / new grip triangles (grip_old_new.npz,
for grip_loop.py's XZ silhouette IoU), the H1 section (perimeter / width / depth at the Grip origin, the
rifle_h1.py method).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent                       # Scripts/guns/rifle/parts
sys.path.insert(0, str(HERE.parent))
from rifle_common import ROOT, SPEC, GRIP  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from gunlib import bl  # noqa: E402
from gunlib.parts import BuildCtx  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d


sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline import lock as L  # noqa: E402
L.assert_owner("AR01", "claude")

from parts import grip as GR  # noqa: E402


def section(ob):
    ang = math.radians(SPEC.dims("pistol_grip")["axis_rake_deg_from_vertical"])
    axis = np.array([-math.sin(ang), 0.0, -math.cos(ang)])
    origin = np.array(SPEC.d["frames"]["B"]["Grip_in_M"])
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7,
                                 plane_co=Vector((origin - GRIP) / 1000.0), plane_no=Vector(axis),
                                 clear_inner=False, clear_outer=False)
    perim = sum(e.calc_length() for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)) * 1000.0
    pts = np.array([v.co for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]) * 1000.0
    bm.free()
    pdir = np.array([math.cos(ang), 0.0, -math.sin(ang)])
    return {"perimeter_mm": round(perim, 2), "width_Y_mm": round(float(np.ptp(pts[:, 1])), 2),
            "depth_mm": round(float(np.ptp(pts @ pdir)), 2)}


def main():
    old = bpy.data.objects.get("pistol_grip")
    rep = {}
    oldV = oldT = None
    if old is not None:
        oldV, oldT = bl.tris_np(old, GRIP)
        rep["old"] = {"triangles": int(len(oldT)), "section": section(old)}
        coll = old.users_collection[0]
        bpy.data.objects.remove(old, do_unlink=True)
    else:
        coll = bl.collection("AR01_Parts")
    for n in [n for n, _ in GR.REVIEW_EXTRAS]:
        if bpy.data.objects.get(n):
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    ctx = BuildCtx(coll, GRIP, SPEC, None)
    built = GR.build(SPEC, ctx)
    ob = built["pistol_grip"][0]
    rep["grip"] = {"triangles": bl.manifold_report(ob)["triangles"], "manifold": bl.manifold_report(ob),
                   "section": section(ob)}
    V, T = bl.tris_np(ob, GRIP)
    if oldV is not None:                          # the XZ silhouette comparison runs in grip_loop.py (no PIL here)
        np.savez_compressed(str(Path(arg("--npz")).with_name("grip_old_new.npz")), oldV=oldV, oldT=oldT, V=V, T=T)
    # contact with the neighbours: intersecting triangle pairs (BVH overlap) and the minimum gap (vertex samples)
    tg = bl.bvh_of(ob)
    rep["contacts"] = {}
    for nb in ("receiver", "trigger_guard", "rear_trunnion", "buttstock", "trigger", "mag_catch", "selector"):
        o2 = bpy.data.objects.get(nb)
        if o2 is None:
            continue
        t2 = bl.bvh_of(o2)
        V2, _ = bl.tris_np(o2, GRIP)
        Vs = (bl.surface_samples(V, T, 1.0) - GRIP) / 1000.0
        gap = bl.min_distance(Vs, t2, cap_m=0.01) * 1000.0
        rep["contacts"][nb] = {"overlap_tri_pairs": len(tg.overlap(t2)), "min_gap_mm_samples": round(gap, 4)}
    if "--no-extras" not in argv:
        bc = bl.collection("AR01_ReviewBakeSource")
        for n, f in GR.REVIEW_EXTRAS:
            e = f(bc, GRIP, n)
            rep[n] = {"triangles": bl.manifold_report(e)["triangles"], "manifold": bl.manifold_report(e)}
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(arg("--out")).resolve()))
    lod0 = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")
            and o.name not in [n for n, _ in GR.REVIEW_EXTRAS]]
    bl.export_npz(lod0, arg("--npz"), GRIP, [o.name for o in lod0])
    rep["lod0_objects"] = len(lod0)
    rep["lod0_triangles_total"] = int(sum(bl.manifold_report(o)["triangles"] for o in lod0))
    Path(arg("--report")).write_text(json.dumps(rep, indent=1))
    print("[grip_review]", json.dumps(rep))
    print("[grip_review] DONE")


main()
