"""Stone kit f2: rebuild Assets/Dojo/DojoStoneKit.blend's two collections from the tracks' own build blends
(wall/DojoStoneKit_wall.blend -> StoneKit_Wall, stairs/StairKit_build.blend -> StoneKit_Stairs) with
sk_shared.fold_into_kit (the kit's own retuned recipes win), under the shared file lock. Prints every kit material's
tint check so the kit blend is proven to carry the f2 recipes.
Run: blender -b --factory-startup --python Scripts/dojo/stonekit/remerge_f2.py
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sk_shared as sk  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402

assert_owner("DojoStoneKit", "claude")
SRC = {"StoneKit_Wall": sk.WORK / "wall" / "DojoStoneKit_wall.blend",
       "StoneKit_Stairs": sk.WORK / "stairs" / "StairKit_build.blend"}
with sk.file_lock(sk.BLEND):
    bpy.ops.wm.open_mainfile(filepath=str(sk.BLEND))
    for cn in SRC:
        sk.drop_collection_for_append(cn)
    for cn, src in SRC.items():
        with bpy.data.libraries.load(str(src), link=False) as (a, b):
            b.collections = [cn]
        for c in b.collections:
            if c is not None:
                bpy.context.scene.collection.children.link(c)
        print("appended", cn, "folded", sk.fold_into_kit(), flush=True)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sk.BLEND))
    for m in sorted(set(sk.KIT_MATS) | set(sk.LIB_VARIANTS)):
        mat = bpy.data.materials.get(m)
        tint = None
        if mat is not None:
            for n in mat.node_tree.nodes:
                if n.type == "MIX" and n.blend_type == "MULTIPLY" and not n.inputs["B"].is_linked:
                    tint = tuple(round(x, 3) for x in n.inputs["B"].default_value[:3])
                    break
        print("KITMAT", m, "present" if mat else "MISSING", "tint", tint, flush=True)
    import json
    cat = json.loads(sk.CATALOG.read_text(encoding="utf-8"))["pieces"]
    mism = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("SM_DKT_") and o.parent is None and o.name in cat:
            t = sum(len(p.vertices) - 2 for p in o.data.polygons)
            want = cat[o.name].get("tris_lod0") or cat[o.name].get("tris")
            if want and t != want:
                mism.append((o.name, t, want))
    print("TRI MISMATCH vs catalog:", mism, flush=True)
    n_obj = len([o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_") and o.parent is None])
    bad = sorted({m.name for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_")
                  for m in o.data.materials if m and m.name[-4:-3] == "." and m.name[-3:].isdigit()})
    print("PIECES", n_obj, "suffixed slots:", bad, flush=True)
