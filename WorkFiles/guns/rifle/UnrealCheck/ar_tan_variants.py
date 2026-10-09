"""Diagnostic: per-LOD single-mesh FBX of the shipped SM_AR01 / SM_AR01_Mag, as shipped (V0) and after
gunlib.tspace.make_tangent_safe (V1), for an Unreal import test of the tangent warnings. Not shipped."""
import bpy, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "Scripts")); sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
import ar_common as C
from pipeline.export_fbx import base_settings
from gunlib import tspace as TS
import numpy as np
OUT = HERE / "tanexp"
rep = {}


def tex_twin(uv):
    u = uv[:, 0]
    return np.where(u < 0, 1 / 1024, np.where(u < 1, 1 / 4096, 1 / 2048))


def export(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    st = base_settings("static")
    bpy.ops.export_scene.fbx(filepath=str(path), **st)


for fn, texf in (("SM_AR01.fbx", tex_twin), ("SM_AR01_Mag.fbx", 1 / 1024)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX_")]:
        mw = ob.matrix_world.copy()
        ob.parent = None
        ob.matrix_world = mw
        base = ob.name
        ob.name = "TV0_" + base
        ob.data.name = ob.name
        export(ob, OUT / f"TV0_{base}.fbx")
        keep = ob.data.copy()
        for tag, th in (("TVE", 0.03),):
            ob.data = keep.copy()
            t0 = time.time()
            r = TS.unreal_safe(ob, texel_uv=texf); r["tris_after"] = sum(len(pp.vertices) - 2 for pp in ob.data.polygons); import bmesh as _b; _bm = _b.new(); _bm.from_mesh(ob.data); r["edges_3plus_faces"] = sum(1 for _e in _bm.edges if len(_e.link_faces) > 2); _bm.free()
            r["seconds"] = round(time.time() - t0, 1)
            r.pop("left", None)
            ob.name = f"{tag}_" + base
            ob.data.name = ob.name
            export(ob, OUT / f"{tag}_{base}.fbx")
            rep[f"{tag}_{base}"] = r
            print("TSPACE", tag, base, r)
(HERE / "ar_tan_variants.json").write_text(json.dumps(rep, indent=1))
