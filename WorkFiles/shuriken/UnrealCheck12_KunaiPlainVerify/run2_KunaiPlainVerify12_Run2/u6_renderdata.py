"""UnrealCheck12 process 6 (fresh): the SAVED SM_Kunai_Plain's RENDER data, every LOD, every section.

ProceduralMeshLibrary.get_section_from_static_mesh reads RenderData->LODResources[LOD] (positions, tangent-Z normals,
UV0, index buffer).  It warns when Allow CPU Access is off, so the flag is set IN MEMORY ONLY with notify_mode NEVER
(no PostEditChange, no rebuild, nothing saved; the saved value and the dirty-package list are recorded before and
after).  Each section's material slot comes from StaticMeshEditorSubsystem.get_lod_material_slot.  Raw arrays are
written for b2_roundtrip.py, which compares them with the Blender truth (b1_truth.json): positions under the legacy
importer's conversion, (position, UV0) pairs with Unreal's V flip, per-slot triangle counts, the lettering band on +Z.
Writes u6_renderdata.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck12_KunaiPlainVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc12_common as C  # noqa: E402


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
           "dirty_packages_before": C.dirty_packages(), "lods": {}}
    try:
        mesh = unreal.load_asset(C.ASSET)
        sub = C.subsystem()
        rep["allow_cpu_access_saved"] = bool(mesh.get_editor_property("allow_cpu_access"))
        mesh.set_editor_property("allow_cpu_access", True, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        rep["static_materials"] = [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")]
        for lod in range(int(mesh.get_num_lods())):
            secs = []
            for s in range(int(mesh.get_num_sections(lod))):
                v, t, n, uv, _tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, s)
                secs.append({"section": s,
                             "material_slot": C.safe(lambda s=s: int(sub.get_lod_material_slot(mesh, lod, s))),
                             "verts_cm": [[p.x, p.y, p.z] for p in v],
                             "normals": [[p.x, p.y, p.z] for p in n],
                             "uv0": [[p.x, p.y] for p in uv],
                             "tris": [[t[i], t[i + 1], t[i + 2]] for i in range(0, len(t), 3)]})
            rep["lods"][f"LOD{lod}"] = secs
        rep["allow_cpu_access_in_memory_after"] = bool(mesh.get_editor_property("allow_cpu_access"))
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["dirty_packages_after"] = C.dirty_packages()
    C.write(C.HERE / "u6_renderdata.json", rep)
    unreal.log("UC12_U6_DONE")


main()
