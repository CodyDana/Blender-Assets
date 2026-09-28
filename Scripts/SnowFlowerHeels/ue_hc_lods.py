"""Heels Unreal check, step 4 (commandlet): set the heels' LOD screen sizes from the sidecar (1.0 / 0.5 / 0.25).

USkeletalMesh::LODInfo is not reachable from Python in 5.8, so a SkeletalMeshLODSettings asset carries the screen sizes
(/Game/HeelsCheck/<RUN>/LODS_SnowFlowerHeels, reduction left at 100 %) and is assigned to the mesh, which copies them onto
its LODs (USkeletalMeshLODSettings::SetLODSettingsToMesh). The imported LOD geometry must not change: vertex counts per LOD
are compared before/after. Saves only the mesh and the settings asset. Writes WorkFiles/SnowFlowerHeels/ue/lods_<RUN>.json.
"""
import json
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/" + RUN
MESH = DEST + "/SK_SnowFlowerHeels"
SIDECAR = json.load(open(ROOT + "/Exports/SnowFlowerHeels/SK_SnowFlowerHeels.garment.json", encoding="utf-8"))
SMS = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
rep = {"status": "failed", "errors": []}
try:
    mesh = unreal.load_asset(MESH)
    rep["verts_before"] = [SMS.get_num_verts(mesh, i) for i in range(SMS.get_lod_count(mesh))]
    name = "LODS_SnowFlowerHeels"
    path = DEST + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        lods = unreal.load_asset(path)
    else:
        fac = unreal.DataAssetFactory()
        fac.set_editor_property("data_asset_class", unreal.SkeletalMeshLODSettings)
        lods = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, unreal.SkeletalMeshLODSettings, fac)
    groups = []
    for size in SIDECAR["lod_screen_sizes"]:
        g = unreal.SkeletalMeshLODGroupSettings()
        g.set_editor_property("screen_size", unreal.PerPlatformFloat(default=size))
        try:
            rs = g.get_editor_property("reduction_settings")
            rs.set_editor_property("num_of_triangles_percentage", 1.0)
            rs.set_editor_property("num_of_vert_percentage", 1.0)
            g.set_editor_property("reduction_settings", rs)
        except Exception as exc:  # noqa: BLE001
            rep.setdefault("notes", []).append("reduction settings: %s" % exc)
        groups.append(g)
    lods.set_editor_property("lod_groups", groups)
    rep["group_props"] = [m for m in dir(groups[0]) if not m.startswith("_")][:60]
    mesh.set_editor_property("lod_settings", lods)
    rep["verts_after"] = [SMS.get_num_verts(mesh, i) for i in range(SMS.get_lod_count(mesh))]
    rep["geometry_unchanged"] = rep["verts_before"] == rep["verts_after"]
    rep["lod_settings_screen_sizes"] = [str(g.get_editor_property("screen_size")) for g in lods.get_editor_property("lod_groups")]
    rep["saved"] = [unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False),
                    unreal.EditorAssetLibrary.save_asset(MESH, only_if_is_dirty=False)]
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/lods_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
