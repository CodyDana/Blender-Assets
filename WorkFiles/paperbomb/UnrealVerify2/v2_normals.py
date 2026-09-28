#!/usr/bin/env python
"""Did the split normals survive the import, or did Unreal round the rim over?

README section 1: 'the 170 sharp edges between the card's faces and its 0.15 mm rim exist
only as explicit split normals; the FBX smoothing layer says every face is smooth, so
Compute Normals rounds the rim over'.  The test: at each vertex POSITION, how far apart
are the face-corner normals that meet there?  A rounded rim collapses them to one.  Run
over the shipped FBX and over Unreal's re-export with one instrument.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
OUT = HERE / "normals.json"
CASES = [("shipped", PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx", 1000.0),
         ("unreal_roundtrip", HERE / "roundtrip.fbx", 10.0)]


def measure(path, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=True)
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.upper().startswith("UCX"):
            continue
        me = o.data
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) * scale
        nrm = np.empty(len(me.loops) * 3, np.float64)
        me.loops.foreach_get("normal", nrm)
        nrm = nrm.reshape(-1, 3)
        vidx = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", vidx)

        groups = {}
        for li in range(len(me.loops)):
            groups.setdefault(int(vidx[li]), []).append(nrm[li])
        spreads = []
        for vi, ns in groups.items():
            if len(ns) < 2:
                spreads.append(0.0)
                continue
            a = np.array(ns)
            a = a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)
            d = np.clip(a @ a.T, -1.0, 1.0)
            spreads.append(float(math.degrees(math.acos(d.min()))))
        s = np.array(spreads)
        # a "hard" position is one where two normals meet at more than 30 degrees
        out[o.name] = {
            "positions": int(len(groups)),
            "loops": int(len(me.loops)),
            "hard_positions_over_30deg": int((s > 30.0).sum()),
            "hard_positions_over_60deg": int((s > 60.0).sum()),
            "max_normal_spread_deg": round(float(s.max()), 3),
            "mean_normal_spread_deg": round(float(s.mean()), 3),
            "p99_normal_spread_deg": round(float(np.percentile(s, 99)), 3),
            "normals_are_all_smooth": bool(s.max() < 5.0),
            "unique_normal_directions": int(len(np.unique(
                np.round(nrm, 3), axis=0))),
        }
    return out


def main():
    rep = {}
    for tag, p, sc in CASES:
        rep[tag] = measure(p, sc) if Path(p).is_file() else {"error": "missing"}
    l0 = rep.get("shipped", {}).get("SM_PaperBomb_LOD0", {})
    r0 = rep.get("unreal_roundtrip", {}).get("SM_PaperBomb_LOD0", {})
    rep["verdict"] = {
        "shipped_hard_positions_over_60deg": l0.get("hard_positions_over_60deg"),
        "roundtrip_hard_positions_over_60deg": r0.get("hard_positions_over_60deg"),
        "shipped_max_spread_deg": l0.get("max_normal_spread_deg"),
        "roundtrip_max_spread_deg": r0.get("max_normal_spread_deg"),
        "rim_survived_import": bool(
            r0.get("hard_positions_over_60deg", 0) > 0
            and abs((r0.get("max_normal_spread_deg") or 0) -
                    (l0.get("max_normal_spread_deg") or 0)) < 5.0),
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[normals] ->", OUT)
    print(json.dumps(rep, indent=1))


main()
