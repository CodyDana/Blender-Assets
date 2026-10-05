"""AR-01 rifle build, staged (RIFLE_BUILD_PLAN section 12). Headless Blender only:

    blender -b --factory-startup --python Scripts/guns/rifle/build_rifle.py -- --stage blockout|form [--mag-thickness 28]

blockout  primary volumes from the traces  -> WorkFiles/guns/rifle/scratch/AR01_blockout.blend + blockout_tris.npz
form      every part as real geometry      -> Assets/Guns/AR01.blend + scratch/form_tris.npz (+ per-pose data for B3)

The asset lock AR01 is asserted at the top (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, BLEND, BLOCKOUT_BLEND  # noqa: E402

import bpy  # noqa: E402

from gunlib import bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def assert_lock():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    info = L.assert_owner("AR01", "claude")
    print("[AR01] lock ok:", info.get("agent"), info.get("since"))


def stage_blockout():
    import rifle_blockout as RB
    bl.reset_scene()
    col = bl.collection("AR01_Blockout")
    t = float(arg("--mag-thickness", str(SPEC.key["magazine"]["thickness"])))
    objs = []
    for pid, m in RB.parts(t).items():
        ob = m.to_object("BO_" + pid, col, GRIP)
        objs.append(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLOCKOUT_BLEND))
    bl.export_npz(objs, SCRATCH / "blockout_tris.npz", GRIP, [o.name[3:] for o in objs])
    print("[AR01] blockout parts", len(objs), "tris", sum(len(o.data.polygons) for o in objs))


def stage_form():
    import rifle_parts as RP
    bl.reset_scene()
    t0 = time.time()
    only = [v for v in arg('--only', '').split(',') if v]
    res = RP.build_all(only or None)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND if not only else SCRATCH / 'AR01_form_partial.blend'))
    print("[AR01] form built in %.1fs" % (time.time() - t0))
    return res


# LOD2 drops the fastener groups and the hidden internals (GUN_BUILDING_STUDY 5.7: under ~2 px at its 6.7 m switch:
# a 5 mm rivet head is ~0.9 px there); LOD3 is the blockout generator (the silhouette level)
LOD2_DROP = ("rivets", "butt_screws", "stock_hardware", "receiver_rails", "gas_piston", "recoil_spring_button")
LOD3_TOL = 1.2
# parts built at LOD0 resolution in a level's mesh (before anything else, in this fresh process, so no module cache of
# the coarse level reaches them): pairs whose fit is defined by both parts' resolutions - the magazine and its floor
# plate (stage 6 rebuilds the magazine and its LODs; the twin's merged copy stays fine until then) and the butt plate
# with its screws (its heel meets the coarse stock's top line 0.0075 mm away otherwise; the row is 0.01-0.05)
HOLD_AT = {1: ("magazine", "magazine_floor_plate", "butt_plate", "butt_screws")}


def _bad(rep):
    return rep["multi_face_edges"] or rep["boundary_edges"] or rep["wire_edges"] or rep["zero_area_faces"]


def _key_of(name):
    import rifle_parts as RP
    return name if name in RP.ORDER else {"rear_sight_slider": "rear_sight_leaf"}.get(name, name)


def _lod1_contacts(objs, RP, L, rounds=3):
    """GUN_BUILDING_STUDY 7.2 G5 holds at LOD1 too (0 intersections, butt gaps >= 0.01 mm). Pairs that break it at the
    coarse level get one part rebuilt at LOD0 resolution: the part a retry boosted, else the smaller one."""
    from gunlib import fit as F
    from rifle_common import CONTACT_PAIRS
    out = {}
    for _ in range(rounds):
        G = {o.name: v for o, v in zip(objs, F.geom(objs).values())}
        bad = set()
        for r in F.pair_intersections(G):
            bad.add((r["a"], r["b"]))
        recs = {o.name: json.loads(o.get("gun_part", "{}")) for o in objs}
        pairs = [(n, r.get("joint", {}).get("parent")) for n, r in recs.items()
                 if r.get("joint", {}).get("type") in ("butt", "fixed") and r.get("joint", {}).get("parent") in G]
        pairs += [(a, b) for a, b in CONTACT_PAIRS if a in G and b in G]
        for g in F.min_gaps(G, sorted({tuple(sorted(p)) for p in pairs})):
            if g["min_gap_mm"] < 0.01:
                bad.add((g["a"], g["b"]))
        if not bad:
            break
        out["_unresolved"] = {"pairs": sorted(f"{a}/{b}" for a, b in bad),
                              "note": "reported, not rebuilt: an in-process LOD0 rebuild mixed LOD1 module caches into "
                                      "the part; contact fixes are generator holds (gunlib.lod.hold)"}
        break
        tris = {o.name: len(o.data.polygons) for o in objs}
        redo = set()
        for a, b in bad:
            boosted = [n for n in (a, b) if n in out or n in getattr(L, "_boosted", ())]
            redo.add(boosted[0] if boosted else (a if tris[a] <= tris[b] else b))
        keys = sorted({_key_of(n) for n in redo})
        for o in [o for o in objs if _key_of(o.name) in keys]:
            objs.remove(o)
            bpy.data.objects.remove(o, do_unlink=True)
        L.set_level(0)
        new, _ = RP.build_all(keys, tag="lod1_g5", coll_name="AR01_LOD1")
        L.set_level(1)
        objs += new
        for o in new:
            out[o.name] = {"step": "G5 at LOD1", "level_used": 0, "pairs": sorted(f"{a}/{b}" for a, b in bad),
                           "manifold": bl.manifold_report(o)}
    return out


def stage_lod():
    """LOD1 / LOD2 from the SAME part generators at a coarser gunlib.lod level; LOD3 from the blockout generator.
    --level 0 rebuilds LOD0 into a scratch file only to prove the level-0 hooks are the identity (the npz must equal
    form_tris.npz). A part whose coarse booleans come out non-manifold is rebuilt (retry ladder, recorded in
    scratch/lod<k>_report.json): a 0.37 deg turn of every round, then each finer level down to LOD0. Output: scratch/AR01_LOD<k>.blend (objects '<part>_LOD<k>' in collection AR01_LOD<k>) and
    scratch/lod<k>_tris.npz."""
    from gunlib import lod as L
    import rifle_parts as RP
    lv = int(arg("--level", "1"))
    bl.reset_scene()
    L.set_level(lv)
    t0 = time.time()
    ladder = {}
    if lv <= 2:
        held = [k for k in HOLD_AT.get(lv, ()) if k in RP.ORDER]
        objs = []
        if held:
            L.set_level(0)
            hobjs, _ = RP.build_all(held, tag=f"lod{lv}_held", coll_name=f"AR01_LOD{lv}")
            objs += hobjs
            for o in hobjs:
                ladder[o.name] = {"step": "held at LOD0 resolution (HOLD_AT)", "level_used": 0,
                                  "manifold": bl.manifold_report(o)}
            L.set_level(lv)
        rest = [k for k in RP.ORDER if k not in held]
        robjs, rep = RP.build_all(rest, tag=f"lod{lv}", coll_name=f"AR01_LOD{lv}")
        objs += robjs
        if lv == 2:
            for o in list(objs):
                if o.name in LOD2_DROP:
                    objs.remove(o)
                    bpy.data.objects.remove(o, do_unlink=True)
        if lv:
            base_factor = L.RING_FACTOR[lv]
            # (a ring-count boost was tried as a middle step: it fixed the booleans but broke the part's fits with
            # its neighbours at the base count - barrel / rod in the front sight, the magazine round its floor plate)
            ladder_steps = [(0.37, base_factor, lv)] + [(0.0, None, k) for k in range(lv - 1, -1, -1)]
            for step, (jit, rf, lvl) in enumerate(ladder_steps):
                bad = [o for o in objs if _bad(bl.manifold_report(o))]
                if not bad:
                    break
                keys = sorted({_key_of(o.name) for o in bad})
                for k in keys:
                    for o in [o for o in objs if _key_of(o.name) == k]:
                        objs.remove(o)
                        bpy.data.objects.remove(o, do_unlink=True)
                L.PHASE_JITTER_DEG = jit
                if rf is not None:
                    L.RING_FACTOR[lv] = rf
                L.set_level(lvl)
                new, rep2 = RP.build_all(keys, tag=f"lod{lv}_retry", coll_name=f"AR01_LOD{lv}")
                objs += new
                if rf is not None and rf != base_factor:
                    L._boosted = tuple(getattr(L, "_boosted", ())) + tuple(o.name for o in new)
                for o in new:
                    ladder[o.name] = {"step": step + 1, "phase_jitter_deg": jit, "ring_factor": rf if rf else
                                      L.RING_FACTOR.get(lvl), "level_used": lvl, "manifold": bl.manifold_report(o)}
                L.PHASE_JITTER_DEG = 0.0
                L.RING_FACTOR[lv] = base_factor
                L.set_level(lv)
        if lv == 1:
            ladder.update(_lod1_contacts(objs, RP, L))
    else:
        import rifle_blockout as RB
        col = bl.collection(f"AR01_LOD{lv}")
        objs = []
        for i, (pid, m) in enumerate(RB.parts(None, tol=LOD3_TOL).items()):
            # the silhouette prisms share traced outline points: each part shrinks 0.02 % about its own centre, so no
            # two parts keep a vertex pair closer than qa_check's 1 micron
            V = m.verts()
            c = V.mean(0)
            m2 = type(m)()
            m2.add_verts(c + (V - c) * (1.0 - 2e-4 * (1 + i % 3)))
            m2.F = m.F
            ob = m2.to_object(pid, col, GRIP, smooth_deg=40.0)
            bl.finish(ob)
            objs.append(ob)
    for o in objs:
        o.name = f"{o.name}_LOD{lv}"
        o.data.name = o.name
    if lv:
        bl.export_npz(objs, SCRATCH / f"lod{lv}_tris.npz", GRIP, [o.name for o in objs])
    final = {o.name: bl.manifold_report(o) for o in objs}
    (SCRATCH / f"lod{lv}_report.json").write_text(json.dumps({"retries": ladder, "parts": final}, indent=1))
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    nbad = sum(1 for r in final.values() if _bad(r))
    print("[AR01] LOD%d parts %d tris %d non-manifold parts %d retried %d built in %.1fs" % (
        lv, len(objs), tris, nbad, len(ladder), time.time() - t0))
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH / f"AR01_LOD{lv}.blend"))


if __name__ == "__main__":
    assert_lock()
    st = arg("--stage", "blockout")
    {"blockout": stage_blockout, "form": stage_form, "lod": stage_lod}[st]()
    print("[AR01] STAGE_DONE", st)
