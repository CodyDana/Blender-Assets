"""SMG01 (Compact SMG SM-01) build, staged (SMG_BUILD_PLAN section 15, W1b). Headless Blender only:

    blender -b --factory-startup --python Scripts/guns/smg/build_smg.py -- --stage blockout|form
            [--only name,name] [--groups receiver,rails,...] [--tag x] [--no-save]

blockout  primary volumes from the traces (+ the flip-sight generators for B4)
          -> WorkFiles/guns/smg/scratch/SMG01_blockout.blend + scratch/blockout_tris.npz
form      every part as real geometry -> Assets/Guns/SMG01.blend + scratch/form_tris.npz + scratch/form_build_report.json
lod       (W3) --level 1|2 the SAME part generators at a coarser gunlib.lod level, --level 3 the blockout generator
          (the traced silhouette volumes + the sights' traced outlines) -> scratch/SMG01_LOD<k>.blend (objects
          '<part>_LOD<k>' in collection SMG01_LOD<k>, each with its gun_part record: bone, slot) + scratch/lod<k>_tris.npz

The asset lock SMG01 is asserted at the top (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, CODE, GRIP, SCRATCH, BLEND, BLOCKOUT_BLEND, PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from gunlib import bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def assert_lock():
    from pipeline import lock as L
    info = L.assert_owner(CODE, "claude")
    print(f"[{CODE}] lock ok:", info.get("agent"), info.get("since"))


def stage_blockout():
    import smg_blockout as SB
    import smg_parts as SP
    from parts import sights
    bl.reset_scene()
    col = bl.collection(f"{CODE}_Blockout")
    objs = []
    for pid, m in SB.parts().items():
        objs.append(m.to_object(pid, col, GRIP))
    for it in sights.rear_sight() + sights.front_sight():
        objs.append(SP.build_one(it, col, GRIP))
    if "--no-save" not in argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_BLEND))
    bl.export_npz(objs, SCRATCH / "blockout_tris.npz", GRIP, [o.name for o in objs])
    print(f"[{CODE}] blockout parts", len(objs), "tris", sum(len(o.data.polygons) for o in objs))


def stage_form():
    import smg_parts as SP
    bl.reset_scene()
    t0 = time.time()
    only = [v for v in arg("--only", "").split(",") if v]
    groups = [v for v in arg("--groups", "").split(",") if v]
    tag = arg("--tag", None)
    res = SP.build_all(only or None, tag=tag, groups=groups or None)
    if "--no-save" not in argv:
        partial = bool(only or groups)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND if not partial else SCRATCH / f"{CODE}_form_partial.blend"))
    print(f"[{CODE}] form built in %.1fs" % (time.time() - t0))
    return res


# ------------------------------------------------------------------------------------------------ W3 LODs
# LOD2 drops the fastener groups and the hidden internals (GUN_BUILDING_STUDY 5.7; plan 7.1: pins and screws 0 at LOD2;
# under ~1 px at the LOD2 switch distance): the rail screws, the drawn fastener heads, the axle / pin heads, the bolt's
# guide rails (inside the receiver) and the magazine follower (inside the magazine)
LOD2_DROP = ("pins_fasteners", "rail_screws", "sight_rear_pin", "sight_front_pin", "trigger_axle", "mag_release_pin",
             "bolt_rails", "magazine_follower")
LOD3_TOL = 1.2
# LOD3 (the blockout generator): bone and slot of each silhouette volume (the build's part records name them at LOD0-2)
LOD3_BONE = {"trigger": "trigger", "mag_release": "mag_release", "magazine": "magazine",
             "charging_handle": "charging_handle", "selector": "selector", "muzzle_device": "muzzle_device",
             "sight_rear": "sight_rear", "sight_front": "sight_front", "stock_hinge": "stock", "stock_neck": "stock",
             "stock_top_strut": "stock", "stock_lower_strut": "stock", "stock_web": "stock",
             "stock_rear_upright": "stock", "butt_pad": "stock"}
LOD3_METAL = ("barrel", "muzzle_device", "top_rail", "lower_rail", "trigger", "mag_release", "charging_handle",
              "selector", "sight_rear", "sight_front")


# The SMG's outline generators (smg_geom's traced rings, the lofts' sections) clean their rings with fixed Douglas-Peucker
# tolerances and resample steps tuned for LOD0 (sub-pixel at 0.3 m). At a coarse level the SAME generators run with
# those two numbers scaled to the level's viewing distance (gunlib.lod's rule: halving a round's segments quadruples its
# chord error): every ring of >= 8 points is simplified at max(tol, min(OUTLINE_TOL[k], 2 % of its extent)) and every
# resample step grows by OUTLINE_STEP[k] while the ring keeps >= 24 points (small rings, holes and slots unchanged).
# LOD1 switches in at ~2.4 m (0.53 px/mm at 1440p): 0.2 mm = 0.11 px (resample steps kept: a coarser grip loft broke
# the lower receiver's booleans into more triangles); LOD2 at ~6 m (0.21 px/mm): 0.6 mm = 0.13 px, steps x 3.
OUTLINE_TOL = {1: 0.1, 2: 0.2}
OUTLINE_STEP = {1: 2.0, 2: 3.0}
# fastener groups (plan 7.1: pins and screws 800 / 250 / 0) are built one level coarser at LOD1: their heads are
# 4-6 mm (2-3 px at the LOD1 switch), the LOD2 ring count keeps their round silhouette there
# ... and the paddle is HELD at LOD0 resolution at LOD1 (the AR-01's HOLD_AT; GUN_BUILDING_STUDY 7.2: 0 intersections
# at LOD1): with its LOD1 outline its nose met the magazine's notch (10 triangle pairs at -3 deg) sweeping out of it.
# (Held sight pins were tried: a LOD0 pin intersects its base's LOD1 hole; they stay at the base's level.)
LEVEL_OVERRIDE = {1: {"pins_fasteners": 2, "rail_screws": 2, "trigger_axle": 2, "mag_release_pin": 2, "hinge_axle": 2,
                      "bolt_rails": 2, "mag_release": 0}}
# per-part outline tolerances at a level (tol, step) where the level's default makes a part heavier: the butt pad's
# serration at LOD1 (0.1 / 2.0: 1,238 triangles; 0.3 / 1.0: ~1,020)
OUTLINE_PART = {1: {"butt_pad": (0.3, 1.0)}}
# shape check (W3): a coarse part must keep LOD0's solid: volume within SHAPE_VOL of LOD0's and its bounding box within
# SHAPE_BOX mm (scratch/form_tris.npz, the gated form build); one that does not (a boolean chain the coarse outline broke:
# measured on the lower receiver, 29 % of its volume left) is rebuilt without the outline coarsening, then one level finer
SHAPE_VOL = (0.85, 1.30)
SHAPE_BOX = {1: 2.0, 2: 4.0}
SHAPE_EXEMPT = {2: ("barrel",)}      # LOD2: the barrel's hidden length inside the receiver is removed by design


def coarse_outlines(level, params=None):
    """Install the level's outline tolerances on gunlib.geo2d for THIS process (the LOD stage runs in its own Blender
    process; LOD0 builds never call this). params = (tol, step) overrides the level's (OUTLINE_PART)."""
    from gunlib import geo2d as G2
    key = (level, params)
    if level not in OUTLINE_TOL or getattr(G2, "_smg_coarse", None) == key:
        return
    dp0, rs0 = getattr(G2, "_dp0", G2.dp_simplify), getattr(G2, "_rs0", G2.resample)
    G2._dp0, G2._rs0 = dp0, rs0
    import os
    tmin = float(os.environ.get("SMG_LOD_TOL", OUTLINE_TOL[level]))          # (experiments only)
    k = float(os.environ.get("SMG_LOD_STEP", OUTLINE_STEP[level]))
    if params is not None:
        tmin, k = params

    def dp(P, tol):
        P = np.asarray(P, float)
        if len(P) >= 8:
            ext = float(np.ptp(P, axis=0).max())
            tol = max(float(tol), min(tmin, 0.02 * ext))
        return dp0(P, tol)

    def rs(P, step, closed=True):
        P = np.asarray(P, float)
        Q = np.vstack([P, P[:1]]) if closed else P
        L = float(np.linalg.norm(np.diff(Q, axis=0), axis=1).sum())
        st = float(step)
        if L / st > 24:
            st = min(st * k, L / 24.0)
        return rs0(P, st, closed)
    G2.dp_simplify, G2.resample = dp, rs
    G2._smg_coarse = key


def plain_outlines():
    """Undo coarse_outlines (the LOD0 tolerances back) for the rest of this process."""
    from gunlib import geo2d as G2
    if getattr(G2, "_smg_coarse", None):
        G2.dp_simplify, G2.resample = G2._dp0, G2._rs0
        G2._smg_coarse = None


_LOD0_SHAPES = {}


def lod0_shape(name):
    """(volume mm3, bbox lo, bbox hi) of a LOD0 part from scratch/form_tris.npz."""
    if not _LOD0_SHAPES:
        z = np.load(SCRATCH / "form_tris.npz")
        V, T, lab = z["V"], z["T"], z["lab"]
        for i, n in enumerate(z["names"]):
            t = T[lab == i]
            a, b, c = V[t[:, 0]], V[t[:, 1]], V[t[:, 2]]
            P = V[np.unique(t)]
            _LOD0_SHAPES[str(n)] = (float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0), P.min(0), P.max(0))
    return _LOD0_SHAPES.get(name)


def shape_ok(ob, lv):
    """(ok, record): the coarse part's volume / bbox against its LOD0 part."""
    from gunlib import bl as _bl
    ref = lod0_shape(ob.name)
    if ref is None or ob.name in SHAPE_EXEMPT.get(lv, ()):
        return True, None
    V, T = _bl.tris_np(ob, GRIP)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    vol = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    P = V[np.unique(T)]
    dev = float(max(np.abs(P.min(0) - ref[1]).max(), np.abs(P.max(0) - ref[2]).max()))
    r = vol / ref[0] if ref[0] else 1.0
    ok = SHAPE_VOL[0] <= r <= SHAPE_VOL[1] and dev <= SHAPE_BOX.get(lv, 4.0)
    return ok, {"volume_ratio": round(r, 4), "bbox_dev_mm": round(dev, 3)}


def planar_dissolve(ob, log=None, angle_deg=0.5):
    """LOD2 (lossless): the booleans' coplanar triangle fans merged (limited dissolve at 0.5 deg) and re-triangulated
    (beauty); kept only when the part stays closed and manifold and passes UD1 / UD2 (gunlib.ud), else reverted."""
    import bmesh
    import math as _m
    from gunlib import ud as UD
    keep = ob.data.copy()
    n0 = sum(len(p.vertices) - 2 for p in keep.polygons)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm, angle_limit=_m.radians(angle_deg), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    r = UD.check_object(ob)
    m = bl.manifold_report(ob)
    n1 = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    ok = r["pass_ud1"] and r["pass_ud2"] and not _bad(m) and n1 < n0
    if not ok:
        bad = ob.data
        ob.data = keep
        bpy.data.meshes.remove(bad)
    else:
        bpy.data.meshes.remove(keep)
        ob["gun_part_ud"] = json.dumps({k: r.get(k) for k in ("unreal_drops", "min_area_mm2", "pass_ud1", "pass_ud2")})
    if log is not None and ok:
        log[ob.name] = {"step": "LOD2 planar dissolve (lossless, UD-checked)", "triangles": [n0, n1]}
    return ok


def _bad(rep):
    return rep["multi_face_edges"] or rep["boundary_edges"] or rep["wire_edges"] or rep["zero_area_faces"]


def _lod3_parts():
    """The blockout generator at gunlib.lod level 3 (rings / ellipsoids at 1/8 of their segments, traced outlines at
    LOD3_TOL) plus the two flip sights as their traced LEFT outlines across the spec widths (the blockout proved B4 with
    the form generators; at LOD3 the silhouette is enough)."""
    import smg_blockout as SB
    from gunlib import geo2d as G2
    from gunlib import mesh as MS
    from smg_common import trace, box
    import smg_geom as SG
    from smg_common import dims
    parts = SB.parts(tol=LOD3_TOL)
    # the selector: the blockout's through-cylinder buried 17 mm deep in the receiver (G5 at LOD3: 1.1 px at the
    # switch) becomes its two visible hubs, each entering the receiver's side face by 1 mm
    sd = dims("selector")
    sx, sz = sd["pivot_XZ"]
    r = sd["hub_dia"] / 2
    parts["selector"] = MS.cylinder((sx, SG.Y_R - 2.5, sz), (sx, SG.Y_R + 1.0, sz), r, 32).extend(
        MS.cylinder((sx, SG.Y_L - 1.0, sz), (sx, SG.Y_L + 2.5, sz), r, 32))
    j = trace("LEFT")
    for key in ("sight_rear", "sight_front"):
        y0, y1 = box(key)["Y"]
        m = MS.Mesh()
        for r in j["parts"][key]:
            if r["kind"] != "outer" or abs(r["area_px"]) <= 4:
                continue
            P = G2.ccw(G2.dp_simplify(np.array(r["mm"], float), LOD3_TOL))
            if len(P) >= 3:
                m.extend(MS.prism(P, y0, y1, "XZ"))
        parts[key] = m
    return parts


def stage_lod():
    """LOD1 / LOD2 from the SAME part generators at gunlib.lod level 1 / 2; LOD3 from the blockout generator. A part
    whose coarse booleans come out non-manifold is rebuilt (retry ladder, recorded in scratch/lod<k>_report.json): a
    0.37 deg turn of every round, then each finer level down to LOD0 (the AR-01's ladder)."""
    from gunlib import lod as L
    import smg_parts as SP
    lv = int(arg("--level", "1"))
    bl.reset_scene()
    t0 = time.time()
    ladder = {}
    cname = f"{CODE}_LOD{lv}"
    if lv <= 2:
        coarse_outlines(lv)
        objs = []
        over = LEVEL_OVERRIDE.get(lv, {})
        if arg("--only", ""):
            over = {}
        for klv in sorted(set(over.values())):           # the overridden keys first, in this fresh process
            keys = [k for k, v in over.items() if v == klv]
            L.set_level(klv)
            if klv == 0:
                plain_outlines()
            o2, _r = SP.build_all(keys, tag=f"lod{lv}_over", coll_name=cname)
            coarse_outlines(lv)
            objs += o2
            for o in o2:
                ladder[o.name] = {"step": "built at level %d (LEVEL_OVERRIDE)" % klv, "level_used": klv,
                                  "manifold": bl.manifold_report(o)}
        L.set_level(lv)
        for k_, prm in OUTLINE_PART.get(lv, {}).items():
            if k_ in over or (arg("--only", "") and k_ not in arg("--only", "").split(",")):
                continue
            plain_outlines()
            coarse_outlines(lv, prm)
            o3, _r = SP.build_all([k_], tag=f"lod{lv}_part", coll_name=cname)
            objs += o3
            for o in o3:
                ladder[o.name] = {"step": "outline (tol, step) = %s (OUTLINE_PART)" % (prm,), "level_used": lv}
            plain_outlines()
            coarse_outlines(lv)
        only = [v for v in arg("--only", "").split(",") if v]
        rest = [k for k in SP.ORDER if k not in over and k not in OUTLINE_PART.get(lv, {}) and (not only or k in only)]
        o1, _rep = SP.build_all(rest, tag=f"lod{lv}_build", coll_name=cname)
        objs += o1
        if lv == 2:
            for o in list(objs):
                if o.name in LOD2_DROP:
                    objs.remove(o)
                    bpy.data.objects.remove(o, do_unlink=True)
        if lv == 2:
            for o in objs:
                planar_dissolve(o, ladder)
        # shape check: a broken coarse boolean chain -> the part rebuilt without the outline coarsening (then the
        # manifold ladder below, which also goes finer if the rebuilt part still fails the shape check)
        bad_shape = []
        for o in list(objs):
            ok, srec = shape_ok(o, lv)
            if not ok:
                bad_shape.append((o.name, srec))
        if bad_shape:
            plain_outlines()
            keys = [n for n, _ in bad_shape]
            for o in [o for o in objs if o.name in keys]:
                objs.remove(o)
                bpy.data.objects.remove(o, do_unlink=True)
            L.set_level(lv)
            new, _r3 = SP.build_all(keys, tag=f"lod{lv}_plain", coll_name=cname)
            if lv == 2:
                for o in new:
                    planar_dissolve(o, ladder)
            objs += new
            for (n, srec), o in zip(bad_shape, new):
                ok2, s2 = shape_ok(o, lv)
                ladder[o.name] = {"step": "shape check failed with the coarse outlines: rebuilt with LOD0's outline "
                                          "tolerances", "coarse": srec, "plain": s2, "shape_ok": ok2,
                                  "manifold": bl.manifold_report(o)}
            coarse_outlines(lv)
        base_factor = L.RING_FACTOR[lv]
        steps = [(0.37, lv)] + [(0.0, k) for k in range(lv - 1, -1, -1)]
        for step, (jit, lvl) in enumerate(steps):
            bad = [o for o in objs if _bad(bl.manifold_report(o)) or not shape_ok(o, lv)[0]]
            if not bad:
                break
            keys = sorted(o.name for o in bad)
            for o in bad:
                objs.remove(o)
                bpy.data.objects.remove(o, do_unlink=True)
            L.PHASE_JITTER_DEG = jit
            L.set_level(lvl)
            plain_outlines()
            new, _r2 = SP.build_all(keys, tag=f"lod{lv}_retry", coll_name=cname)
            coarse_outlines(lv)
            objs += new
            for o in new:
                ladder[o.name] = {"step": step + 1, "phase_jitter_deg": jit, "level_used": lvl,
                                  "manifold": bl.manifold_report(o)}
            L.PHASE_JITTER_DEG = 0.0
            L.RING_FACTOR[lv] = base_factor
            L.set_level(lv)
    else:
        L.set_level(3)
        col = bl.collection(cname)
        objs = []
        for i, (pid, m) in enumerate(_lod3_parts().items()):
            # the silhouette prisms share traced outline points: each part shrinks 0.02-0.06 % about its own centre,
            # so no two parts keep a vertex pair closer than qa_check's 1 micron (the AR-01's LOD3 rule)
            V = m.verts()
            c = V.mean(0)
            m2 = type(m)()
            m2.add_verts(c + (V - c) * (1.0 - 2e-4 * (1 + i % 3)))
            m2.F = m.F
            ob = m2.to_object(pid, col, GRIP, smooth_deg=40.0)
            bl.finish(ob)
            ob["gun_part"] = json.dumps({"bone": LOD3_BONE.get(pid, "body"),
                                         "slot": "M_SMG01_Mag" if pid == "magazine" else
                                         ("M_SMG01_Metal" if pid in LOD3_METAL else "M_SMG01_Furniture"),
                                         "class": "LOD3 silhouette", "spec_id": pid,
                                         "joint": {"type": "lod3"}, "recipe": "blockout generator, tol %.2f" % LOD3_TOL})
            objs.append(ob)
        L.set_level(0)
    for o in objs:
        o.name = f"{o.name}_LOD{lv}"
        o.data.name = o.name
    bl.export_npz(objs, SCRATCH / f"lod{lv}_tris.npz", GRIP, [o.name for o in objs])
    final = {o.name: bl.manifold_report(o) for o in objs}
    (SCRATCH / f"lod{lv}_report.json").write_text(json.dumps({"retries": ladder, "parts": final}, indent=1))
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    nbad = sum(1 for r in final.values() if _bad(r))
    print(f"[{CODE}] LOD%d parts %d tris %d non-manifold parts %d retried %d built in %.1fs" % (
        lv, len(objs), tris, nbad, len(ladder), time.time() - t0))
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH / f"{CODE}_LOD{lv}.blend"))


if __name__ == "__main__":
    assert_lock()
    st = arg("--stage", "blockout")
    {"blockout": stage_blockout, "form": stage_form, "lod": stage_lod}[st]()
    print(f"[{CODE}] STAGE_DONE", st)
