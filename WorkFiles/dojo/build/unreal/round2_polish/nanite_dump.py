"""Round-2 diagnostic (pythonscript commandlet, -nullrhi, READ-ONLY: saves nothing): every NaniteSettings property, the
asset bounds, LOD0 triangles and the source (mesh description) box of a few Nanite meshes, to find what inflates the
Nanite bounds after a rebuild. Out: round2_polish/nanite_dump.json"""
import json
import unreal

OUT = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round2_polish\nanite_dump.json"
PATHS = ["/Game/DojoKit/Stone/Meshes/SM_DKP_Stone_Cistern", "/Game/DojoKit/Kit1/Meshes/SM_DK_Gate_Frame",
         "/Game/DojoKit/Modern/Meshes/SM_DKP_Modern_VendingMachine"]
R = {}
for path in PATHS:
    m = unreal.load_asset(path)
    if m is None:
        R[path] = "missing"
        continue
    e = {}
    ns = m.get_editor_property("nanite_settings")
    props = {}
    for k in dir(ns):
        if k.startswith("_") or callable(getattr(ns, k, None)):
            continue
        try:
            props[k] = str(ns.get_editor_property(k))
        except Exception as exc:  # noqa: BLE001
            props[k] = f"ERR {str(exc)[:80]}"
    e["nanite_settings"] = props
    bb = m.get_bounding_box()
    e["asset_bbox"] = [[bb.min.x, bb.min.y, bb.min.z], [bb.max.x, bb.max.y, bb.max.z]]
    try:
        eb = m.get_editor_property("extended_bounds")
        e["extended_bounds"] = str(eb)
    except Exception as exc:  # noqa: BLE001
        e["extended_bounds"] = f"ERR {exc}"
    for k in ("positive_bounds_extension", "negative_bounds_extension"):
        try:
            e[k] = str(m.get_editor_property(k))
        except Exception as exc:  # noqa: BLE001
            e[k] = f"ERR {exc}"
    e["lod0_tris"] = m.get_num_triangles(0)
    d = m.get_static_mesh_description(0)
    xs, ys, zs = [], [], []
    for i in range(d.get_vertex_count()):
        p = d.get_vertex_position(unreal.VertexID(i))
        xs.append(p.x)
        ys.append(p.y)
        zs.append(p.z)
    e["source_bbox"] = [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]]
    e["source_tris"] = d.get_triangle_count()
    try:
        e["num_source_models"] = m.get_num_source_models()
    except Exception:  # noqa: BLE001
        pass
    try:
        hr = m.get_editor_property("hi_res_source_model")
        e["hi_res_source"] = str(hr)[:300]
    except Exception as exc:  # noqa: BLE001
        e["hi_res_source"] = f"ERR {exc}"
    R[path] = e
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(R, fh, indent=1, default=str)
unreal.log("NANITE_DUMP_DONE")
