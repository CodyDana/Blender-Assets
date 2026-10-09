"""Diagnostic (Blender headless, shipped bytes): where would MikkTSpace give a zero / degenerate tangent frame?
Per mesh node of SM_AR01.fbx, SM_AR01_Mag.fbx and SK_AR01*.fbx: triangles with ~zero 3D area, ~zero UV0 area,
and loops whose Blender MikkTSpace tangent or bitangent is ~zero or parallel."""
import bpy, json, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ar_common as C
res = {}
for fn in ("SM_AR01.fbx", "SM_AR01_Mag.fbx", "SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.name.startswith("UCX_"):
            continue
        me = ob.data
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        V = np.array([v.co for v in me.vertices]) * 1000.0 * ob.matrix_world.to_scale()[0]
        uv = me.uv_layers[0].data
        UV = np.array([d.uv for d in uv])
        LT = np.array([t.loops[:] for t in me.loop_triangles])
        VT = np.array([t.vertices[:] for t in me.loop_triangles])
        A3 = 0.5 * np.linalg.norm(np.cross(V[VT[:, 1]] - V[VT[:, 0]], V[VT[:, 2]] - V[VT[:, 0]]), axis=1)
        u0, u1, u2 = UV[LT[:, 0]], UV[LT[:, 1]], UV[LT[:, 2]]
        AU = 0.5 * np.abs((u1[:, 0] - u0[:, 0]) * (u2[:, 1] - u0[:, 1]) - (u2[:, 0] - u0[:, 0]) * (u1[:, 1] - u0[:, 1]))
        rec = {"tris": n, "area3d_lt_1e-6mm2": int((A3 < 1e-6).sum()), "uvarea_lt_1e-12": int((AU < 1e-12).sum()),
               "uvarea_lt_1e-10": int((AU < 1e-10).sum()), "uvarea_lt_1e-9": int((AU < 1e-9).sum()),
               "uv_names": [u.name for u in me.uv_layers]}
        try:
            me.calc_tangents(uvmap=me.uv_layers[0].name)
            T = np.array([l.tangent for l in me.loops]); B = np.array([l.bitangent for l in me.loops]); N = np.array([l.normal for l in me.loops])
            tl = np.linalg.norm(T, axis=1); bl = np.linalg.norm(B, axis=1)
            cr = np.linalg.norm(np.cross(T, B), axis=1)
            bad = (tl < 1e-4) | (bl < 1e-4) | (cr < 1e-4)
            rec["mikk_bad_loops"] = int(bad.sum())
            rec["mikk_tangent_lt_1e-4"] = int((tl < 1e-4).sum())
            rec["mikk_TxB_lt_1e-4"] = int((cr < 1e-4).sum())
            # where: the loops' vertex positions (cm, Blender frame) of the first bad ones
            idx = np.where(bad)[0][:12]
            rec["bad_loop_positions_mm"] = [np.round(V[me.loops[i].vertex_index], 3).tolist() for i in idx]
            rec["bad_loop_material"] = sorted({me.materials[me.polygons[p].material_index].name if me.materials else "-"
                                              for p in range(len(me.polygons)) for li in range(me.polygons[p].loop_start, me.polygons[p].loop_start + me.polygons[p].loop_total) if bad[li]})[:10] if bad.any() else []
        except Exception as e:  # noqa
            rec["mikk_error"] = str(e)[:200]
        res[f"{fn}:{ob.name}"] = rec
(HERE / "ar_diag_tangent.json").write_text(json.dumps(res, indent=1))
print("DIAG_DONE")
