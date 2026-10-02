"""Fix round probe (read-only): the Fishermans fir meshes' bounds and the bark section's radial extent per height slice
(where the root flare ends), to set the forest burial. Out: fix/json/probe_fir.json"""
import json
import math
from pathlib import Path
import unreal
OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fix\json\probe_fir.json")
rep = {}
for p in [f"/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SM_Fir_Tree_0{i}" for i in range(1, 9)] + [
        "/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SMF_Fir_Tree_Billboard"]:
    m = unreal.load_asset(p)
    if isinstance(m, unreal.FoliageType_InstancedStaticMesh):
        m = m.get_editor_property("mesh")
    b = m.get_bounding_box()
    r = {"min": [b.min.x, b.min.y, b.min.z], "max": [b.max.x, b.max.y, b.max.z], "sections": []}
    try:
        n = m.get_num_sections(0)
        for s in range(n):
            mat = m.get_material(m.get_material_index(f"{s}") if False else s)
            res = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, s)
            verts = res[0]
            zs = [v.z for v in verts]
            if not zs:
                continue
            z0 = min(zs)
            sl = {}
            for v in verts:
                k = int((v.z - z0) // 25)
                rr = math.hypot(v.x, v.y)
                sl[k] = max(sl.get(k, 0.0), rr)
            r["sections"].append({"s": s, "material": mat.get_name() if mat else None, "n": len(verts), "zmin": z0,
                                  "radial_by_25cm": [round(sl.get(k, 0), 1) for k in range(0, 24)]})
    except Exception as exc:  # noqa: BLE001
        r["err"] = str(exc)[:300]
    rep[p] = r
OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
unreal.log("DJ_STEP_DONE probe_fir passed=True")
