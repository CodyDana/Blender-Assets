"""Pass 1 of 2: import SM_Shuriken_FourPoint.fbx into the copied validation project.

Modelled on WorkFiles/pipeline_test/UnrealCheck/verify_shipped.py (UE 5.8.2, legacy
FBX importer) and Scripts/pipeline/ue_import_sockets.py for the socket sidecar.

Imports, inspects, applies the sidecar sockets, saves. verify_shuriken_reload.py
re-reads the saved asset in a FRESH process, because an in-process socket query
cannot tell a persisted socket from a transient one (ASSET_GUIDELINES 6.5).
"""
import json
import sys
import traceback
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CHECK_DIR = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck"
REPORT = CHECK_DIR / "import_report.json"
FBX = PROJ / "Exports" / "Shuriken" / "SM_Shuriken_FourPoint.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / "SM_Shuriken_FourPoint.sockets.json"
DEST_PATH = "/Game/ShurikenCheck"
DEST_NAME = "SM_Shuriken_FourPoint"

SCRIPTS = PROJ / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

EXPECTED_LOD_TRIS = [1664, 700, 184]


def options():
    """The 6.5 legacy-importer settings, verbatim from verify_shipped.py."""
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def vec(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def prop(obj, name, default="<unreadable>"):
    try:
        return obj.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return f"{default}: {type(exc).__name__}: {exc}"[:160]


def inspect(mesh):
    info = {"asset": mesh.get_path_name(), "name": mesh.get_name()}
    try:
        n = mesh.get_num_lods()
        info["num_lods"] = n
        info["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
        info["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
        try:
            info["lod_uv_channels"] = [mesh.get_num_uv_channels(i) for i in range(n)]
        except Exception as exc:  # noqa: BLE001
            info["lod_uv_channels_error"] = f"{type(exc).__name__}: {exc}"[:160]
    except Exception as exc:  # noqa: BLE001
        info["lod_error"] = f"{type(exc).__name__}: {exc}"[:200]

    # Collision: read body_setup.agg_geom directly (6.5 -- the subsystems lie under -run=pythonscript)
    try:
        agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
        info["convex"] = len(agg.get_editor_property("convex_elems"))
        info["box"] = len(agg.get_editor_property("box_elems"))
        info["sphere"] = len(agg.get_editor_property("sphere_elems"))
        info["sphyl"] = len(agg.get_editor_property("sphyl_elems"))
        info["collision_complexity"] = str(prop(mesh.get_editor_property("body_setup"), "collision_trace_flag"))
    except Exception as exc:  # noqa: BLE001
        info["collision_error"] = f"{type(exc).__name__}: {exc}"[:200]

    # Sockets, read through a component so the transform is the one gameplay sees
    try:
        component = unreal.new_object(unreal.StaticMeshComponent)
        component.set_static_mesh(mesh)
        sockets = []
        for name in component.get_all_socket_names():
            t = component.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
            e = t.rotation.euler()
            sockets.append({"name": str(name), "location_cm": vec(t.translation),
                            "rotation_roll_pitch_yaw": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                            "scale": vec(t.scale3d)})
        info["sockets"] = sockets
        info["socket_objects"] = [
            {"socket_name": str(prop(s, "socket_name")),
             "relative_location_cm": vec(s.get_editor_property("relative_location")),
             "relative_scale": vec(s.get_editor_property("relative_scale"))}
            for s in (mesh.find_socket(n) for n in ("Grip", "Trail")) if s is not None
        ]
    except Exception as exc:  # noqa: BLE001
        info["socket_error"] = f"{type(exc).__name__}: {exc}"[:200]

    # Bounds -- the scale gate. Expect 9.7 x 9.7 x 0.3 cm.
    try:
        b = mesh.get_bounding_box()
        info["bounds_min_cm"] = vec(b.min)
        info["bounds_max_cm"] = vec(b.max)
        info["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4), round(b.max.z - b.min.z, 4)]
    except Exception as exc:  # noqa: BLE001
        info["bounds_error"] = f"{type(exc).__name__}: {exc}"[:200]

    info["lightmap_coord_index"] = prop(mesh, "light_map_coordinate_index")
    info["lightmap_resolution"] = prop(mesh, "light_map_resolution")
    try:
        info["nanite_enabled"] = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
    except Exception as exc:  # noqa: BLE001
        info["nanite_error"] = f"{type(exc).__name__}: {exc}"[:160]
    try:
        info["material_slots"] = [{"slot": str(s.material_slot_name),
                                   "material": s.material_interface.get_path_name() if s.material_interface else None}
                                  for s in mesh.get_editor_property("static_materials")]
    except Exception as exc:  # noqa: BLE001
        info["material_error"] = f"{type(exc).__name__}: {exc}"[:160]
    return info


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(),
              "fbx": str(FBX), "sidecar": str(SIDECAR),
              "expected_lod_triangles": EXPECTED_LOD_TRIS}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        if not FBX.is_file():
            raise FileNotFoundError(str(FBX))
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(FBX))
        task.set_editor_property("destination_path", DEST_PATH)
        task.set_editor_property("destination_name", DEST_NAME)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        report["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        report["static_mesh_count"] = len(meshes)
        report["after_import"] = [inspect(m) for m in meshes]
        if meshes:
            asset_path = meshes[0].get_path_name().split(".")[0]
            report["asset_path"] = asset_path
            report["sidecar_result"] = apply_sidecar(str(SIDECAR), asset_path)
            report["after_sockets"] = inspect(meshes[0])
            report["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(meshes[0]))
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_IMPORT " + json.dumps(report, default=str)[:4000])
    unreal.log("SHURIKEN_IMPORT_DONE " + str(REPORT))


if __name__ == "__main__":
    main()
