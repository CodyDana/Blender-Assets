"""How far does UV0 move through Unreal? (Use Full Precision UVs is OFF on every LOD.)

Matches each shipped LOD vertex to Unreal's re-exported vertex by POSITION (they
agree to 1e-6 cm) and reports the largest UV0 difference, in UV and in texels at
2048.  This is the print's registration error: the tag's whole value is the
artwork, so it is worth a number rather than a shrug.
"""
import json
import math
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
SHIPPED = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
FROM_UE = HERE / "roundtrip" / "SM_PaperBomb_from_unreal.fbx"
OUT = HERE / "pbr_uvquant.json"
MESH = "SM_PaperBomb"


def read(path):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for i in range(3):
        ob = bpy.data.objects.get(f"{MESH}_LOD{i}")
        if ob is None:
            continue
        me = ob.data
        mw = ob.matrix_world
        uv = me.uv_layers[0].data
        pairs = []
        for loop in me.loops:
            co = (mw @ me.vertices[loop.vertex_index].co) * 100.0    # cm
            pairs.append(((round(co.x, 4), round(co.y, 4), round(co.z, 4)),
                          (uv[loop.index].uv[0], uv[loop.index].uv[1])))
        out[i] = pairs
    return out


def main():
    a = read(SHIPPED)
    b = read(FROM_UE)
    rep = {"texture_size": 2048, "lods": {}}
    for i in sorted(a):
        # bucket Unreal's loops by quantised position; a position may carry several UVs (seams)
        buckets = {}
        for pos, t in b.get(i, []):
            buckets.setdefault(pos, []).append(t)
        worst_uv = 0.0
        matched = 0
        missing = 0
        for pos, t in a[i]:
            cands = buckets.get(pos)
            if not cands:
                missing += 1
                continue
            matched += 1
            worst_uv = max(worst_uv, min(max(abs(t[0] - c[0]), abs(t[1] - c[1])) for c in cands))
        rep["lods"][f"LOD{i}"] = {
            "loops_compared": matched, "loops_unmatched_by_position": missing,
            "max_uv0_delta": round(worst_uv, 9),
            "max_uv0_delta_texels_2048": round(worst_uv * 2048.0, 4),
            "max_uv0_delta_mm_on_print": round(worst_uv * 2048.0 / 12.923, 5),
        }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


main()
