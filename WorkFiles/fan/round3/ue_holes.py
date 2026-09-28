"""Round 3: see-through holes in Unreal's HDR coverage captures (pass 2's holes_f<frame>_<view>_hdr.exr), counted
exactly as the round-2 Unreal review did (indep_verify_r2/scripts/an_fold2.py): background pixels (alpha > 0.5) not
reachable from the image border through background = holes; 4-neighbour blobs.  Compared with that review's own
numbers for the same frames and cameras (indep_verify_r2/an_fold2.json).

    blender -b --factory-startup --python WorkFiles/fan/round3/ue_holes.py -- <renders_dir> <out_json> [<mask_dir>]
"""
import glob
import json
import os
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
D, OUT = args[0], args[1]
MASKS = args[2] if len(args) > 2 else None
R2 = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/UnrealCheck/indep_verify_r2/an_fold2.json"


def holes_of(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    bg = px[..., 3] > 0.5
    reach = np.zeros_like(bg)
    reach[0, :] = bg[0, :]
    reach[-1, :] = bg[-1, :]
    reach[:, 0] = bg[:, 0]
    reach[:, -1] = bg[:, -1]
    for _ in range(6000):
        n = reach.copy()
        n[1:, :] |= reach[:-1, :]
        n[:-1, :] |= reach[1:, :]
        n[:, 1:] |= reach[:, :-1]
        n[:, :-1] |= reach[:, 1:]
        n &= bg
        if (n == reach).all():
            break
        reach = n
    hole = bg & ~reach
    ys, xs = np.nonzero(hole)
    s = set(zip(ys.tolist(), xs.tolist()))
    seen, sizes = set(), []
    for p in s:
        if p in seen:
            continue
        stack, k = [p], 0
        seen.add(p)
        while stack:
            y, x = stack.pop()
            k += 1
            for q in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if q in s and q not in seen:
                    seen.add(q)
                    stack.append(q)
        sizes.append(k)
    if MASKS and hole.sum():
        os.makedirs(MASKS, exist_ok=True)
        m = np.zeros((h, w, 4), np.float32)
        m[..., 0] = hole
        m[..., 1] = (~bg) * 0.25
        m[..., 2] = (~bg) * 0.25
        m[..., 3] = 1
        o = bpy.data.images.new("m", w, h, alpha=True)
        o.pixels[:] = m.ravel()
        o.filepath_raw = os.path.join(MASKS, os.path.basename(path).replace("_hdr.exr", "_holes.png"))
        o.file_format = "PNG"
        o.save()
        bpy.data.images.remove(o)
    return {"geometry_px": int((~bg).sum()), "hole_px": int(hole.sum()), "hole_blobs": len(sizes),
            "largest_blob_px": max(sizes) if sizes else 0}


out = {"method": "indep_verify_r2/scripts/an_fold2.py (enclosed background pixels, 4-neighbour blobs)", "shots": {}}
for f in sorted(glob.glob(os.path.join(D, "holes_*_hdr.exr"))):
    out["shots"][os.path.basename(f)] = holes_of(f)
r2 = {}
try:
    r2 = json.loads(open(R2, encoding="utf-8").read()).get("see_through_holes", {})
except Exception:  # noqa: BLE001
    pass
cmp_ = {}
for name, v in out["shots"].items():
    key = "fold_" + name[len("holes_"):]
    old = r2.get(key)
    cmp_[key] = {"round3_blobs": v["hole_blobs"], "round3_px": v["hole_px"],
                 "round2_blobs": old.get("hole_blobs") if old else None, "round2_px": old.get("hole_px") if old else None}
out["vs_round2_review"] = cmp_
out["total_round3_px"] = int(sum(v["hole_px"] for v in out["shots"].values()))
out["total_round2_px_same_shots"] = int(sum(c["round2_px"] or 0 for c in cmp_.values()))
open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1))
print(json.dumps(cmp_, indent=0))
