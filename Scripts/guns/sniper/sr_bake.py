"""SR01 W2b: Cycles bakes of the LOD0 parts into the three sets (headless Blender; GPU when present; the AR-01's
rifle_bake.py with the SMG rules):

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_bake.py -- \
        [--uv DIR] [--out DIR] [--ao-samples 256] [--only Metal,Furniture,Mag] [--passes pos,nrm,ids,edge,ao,tris]

Per set (sizes from the UV step, <uv>/sets.json): pos, nrm, ids, edge, ao (gunlib.bake) + the triangles for the
geometric edge masks. Bake rules (SMG_BUILD_PLAN 9.3, spec textures.bake_rules; AR-01 lessons):
  - every pass with margin 0 (the painter fills the gutters per island; a per-object margin overwrote neighbours);
  - the magazine's AO and edge passes see the magazine ALONE (it is its own asset: seated, the receiver's shadow
    printed into its top);
  - the gun's AO at rest, stock extended, magazine OUT (the well interior is class-E visible with the mag out; a
    seated-mag contact shadow is added on the gun side only if a review asks).
Output: <out>/<Set>_<pass>.npy (+ bake_meta.json). The .blend is not saved (bake materials are temporary).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_surface import SCRATCH, GRIP, COLL as PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sr_surface as SS  # noqa: E402
from gunlib import bake as BK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


AO_SAMPLES = int(arg("--ao-samples", "256"))
EDGE_SAMPLES = int(arg("--edge-samples", "64"))
ONLY = arg("--only", "").split(",") if "--only" in argv else None
PASSES = arg("--passes", "").split(",") if "--passes" in argv else None
UVD = Path(arg("--uv", str(SCRATCH / "uv")))
OUT = Path(arg("--out", str(SCRATCH / "bake")))
OUT.mkdir(parents=True, exist_ok=True)
AO_DISTANCE_M = 0.025
MARGIN = 0


def log(*a):
    print("[SR01-bake]", *a, flush=True)


def part_rec(ob):
    return json.loads(ob.get("gun_part", "{}"))


def main():
    t0 = time.time()
    dev = BK.setup_cycles(1)
    log("device", dev)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = AO_DISTANCE_M
    parts = sorted((o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"), key=lambda o: o.name)
    pidx = {o.name: i for i, o in enumerate(parts)}
    isl = np.load(UVD / "islands.npz")
    sets = json.loads((UVD / "sets.json").read_text())
    for o in parts:
        BK.set_face_attr(o, "pid", np.full(len(o.data.polygons), pidx[o.name] + 1.0))
        BK.set_face_attr(o, "cls", isl[f"{o.name}__cls"].astype(np.float32))
        BK.set_face_attr(o, "isl", isl[f"{o.name}__isl"].astype(np.float32) + 1.0)
        o.hide_render = False
        for att, val in (("shadow_terminator_geometry_offset", 1.0), ("shadow_terminator_normal_offset", 0.0)):
            if hasattr(o, att):
                setattr(o, att, val)
    meta = {"parts": {o.name: pidx[o.name] + 1 for o in parts}, "ao_samples": AO_SAMPLES, "ao_distance_m": AO_DISTANCE_M,
            "edge_samples": EDGE_SAMPLES, "device": dev, "margin": MARGIN, "sets": {},
            "rules": {"Mag": "AO + edge with the magazine alone", "Metal/Furniture": "AO with the magazine out (rest, "
                      "stock extended)"},
            "encoding": {"pos": "metres frame B + 1.0", "nrm": "n * 0.5 + 0.5 (world)", "ids": "R part index + 1 (0 = "
                         "empty), G class code (sr_surface.CLASS_CODE), B island id + 1", "edge": "R 1 - "
                         "Nbevel(0.6 mm).N, G 1 - Nbevel(2.0 mm).N, B pointiness", "ao": "Cycles AO",
                         "rows": "bottom-up (Blender pixel order)"}}
    mag_objs = [o for o in parts if o.name in SS.MAG_PARTS]
    for st, info in sets.items():
        if ONLY and st not in ONLY:
            continue
        S = int(info["size"])
        objs = [o for o in parts if SS.SLOT_SET[part_rec(o)["slot"]] == st]
        img = BK.new_image(f"BAKE_{st}", S)
        mat = BK.bake_material(f"BAKE_{st}", img)
        saved = {o.name: [s.material for s in o.material_slots] for o in objs}
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(mat)
        times = {}
        if not PASSES or "tris" in PASSES:
            BK.dump_tris(objs, {o.name: pidx[o.name] + 1 for o in objs}, OUT / f"{st}_tris.npz", [float(v) for v in GRIP])
            log(st, "tris dumped")
        for name, kind, src, spp in (("pos", "EMIT", "pos", 1), ("nrm", "EMIT", "nrm", 1), ("ids", "EMIT", "ids", 1),
                                     ("edge", "EMIT", "edge", EDGE_SAMPLES), ("ao", "AO", None, AO_SAMPLES)):
            if PASSES and name not in PASSES:
                continue
            hidden = []
            if name in ("ao", "edge"):
                if st == "Mag":
                    hidden = [o for o in parts if o not in objs and not o.hide_render]
                elif name == "ao":
                    hidden = [o for o in mag_objs if not o.hide_render]
            for o in hidden:
                o.hide_render = True
            times[name] = round(BK.bake_pass(objs, [mat], img, kind, src, samples=spp, margin=MARGIN), 1)
            for o in hidden:
                o.hide_render = False
            px = BK.read_image(img)
            if name == "pos":
                np.save(OUT / f"{st}_pos.npy", px[..., :3] - 1.0)
            elif name == "ids":
                np.save(OUT / f"{st}_ids.npy", np.rint(px[..., :3]).astype(np.int16))
            elif name == "ao":
                np.save(OUT / f"{st}_ao.npy", px[..., 0].astype(np.float16))
            else:
                np.save(OUT / f"{st}_{name}.npy", px[..., :3].astype(np.float16))
            log(st, name, "%.1fs" % times[name])
        for o in objs:
            o.data.materials.clear()
            for m in saved[o.name]:
                o.data.materials.append(m)
        bpy.data.images.remove(img)
        meta["sets"][st] = {"size": S, "objects": [o.name for o in objs], "seconds": times}
    mp = OUT / "bake_meta.json"
    if (PASSES or ONLY) and mp.exists():
        old = json.loads(mp.read_text())
        for st_, v in meta["sets"].items():
            old["sets"].setdefault(st_, v)["seconds"].update(v["seconds"])
        meta = dict(old, parts=meta["parts"])
    mp.write_text(json.dumps(meta, indent=1))
    log("BAKE_DONE %.1fs" % (time.time() - t0))


main()
