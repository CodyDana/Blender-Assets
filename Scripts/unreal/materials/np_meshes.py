"""Static-mesh import (legacy FBX, the line's measured settings) and material-slot assignment (inside Unreal).

Import settings are the ones every item's Unreal check used (e.g. WorkFiles/blackhat/UnrealCheck/bhu_pass1_import.py):
legacy FbxFactory with Interchange FBX off, Import Mesh LODs ON, normals imported (MikkTSpace tangents), one convex
hull per UCX, no auto collision, lightmap UVs generated, no materials and no textures. The sidecar goes through
``Scripts/pipeline/ue_import_sockets.apply_sidecar`` UNCHANGED, which restores the sockets and LOD screen sizes and
performs the only save of the new package (the kunai's triple-save race: several saves of one new package in
milliseconds raced the changelist scan).

Slot assignment runs in a LATER process (``assign`` mode), after the instances exist: each slot index gets its
instance, the slot name must equal the spec's, and every LOD section must resolve to one of the pack's instances.
"""
from __future__ import annotations

import sys
import traceback

import unreal

import np_spec

sys.path.insert(0, str(np_spec.PROJECT / "Scripts"))
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

EAL = unreal.EditorAssetLibrary


def mesh_options():
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


def sm_subsystem():
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    return sub or unreal.new_object(unreal.StaticMeshEditorSubsystem)


def slot_table(mesh) -> list:
    if isinstance(mesh, unreal.SkeletalMesh):            # the fan (np_skeletal); static meshes: unchanged below
        import np_skeletal
        return np_skeletal.slot_table(mesh)
    out = []
    for i, sm in enumerate(mesh.get_editor_property("static_materials")):
        mi = sm.get_editor_property("material_interface")
        out.append({"index": i, "slot_name": str(sm.get_editor_property("material_slot_name")),
                    "material": mi.get_path_name().split(".")[0] if mi else None})
    return out


def lod_sections(mesh) -> list:
    if isinstance(mesh, unreal.SkeletalMesh):
        import np_skeletal
        return np_skeletal.lod_sections(mesh)
    sub = sm_subsystem()
    out = []
    for lod in range(int(mesh.get_num_lods())):
        secs = []
        for s in range(int(mesh.get_num_sections(lod))):
            slot = int(sub.get_lod_material_slot(mesh, lod, s))
            mi = mesh.get_material(slot)
            secs.append({"section": s, "slot": slot, "material": mi.get_path_name().split(".")[0] if mi else None})
        out.append({"lod": lod, "sections": secs})
    return out


def import_one(m: dict) -> dict:
    if m.get("kind") == "skeletal":
        import np_skeletal
        rep = np_skeletal.import_one(m)
        rep["saved_by_build"] = rep.get("saved")
        return rep
    fbx = np_spec.PROJECT / m["fbx"]
    sidecar = np_spec.PROJECT / m["sidecar"]
    folder, name = m["asset"].rsplit("/", 1)
    rep = {"asset": m["asset"], "fbx": m["fbx"], "fbx_sha256": np_spec.sha256(fbx),
           "sidecar_sha256": np_spec.sha256(sidecar), "existed_before": bool(EAL.does_asset_exist(m["asset"]))}
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(fbx))
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", mesh_options())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    rep["imported_object_paths"] = paths
    meshes = [x for x in (unreal.load_asset(p) for p in paths) if isinstance(x, unreal.StaticMesh)]
    if not meshes:
        rep["error"] = "no StaticMesh imported"
        return rep
    mesh = meshes[0]
    asset_path = mesh.get_path_name().split(".")[0]
    rep["sidecar"] = apply_sidecar(str(sidecar), asset_path)
    if not rep["sidecar"].get("saved"):
        rep["saved_by_build"] = bool(EAL.save_loaded_asset(mesh, only_if_is_dirty=False))
    rep["slots"] = slot_table(mesh)
    rep["lods"] = int(mesh.get_num_lods())
    return rep


def run_import(plan: dict) -> dict:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    out = {"mode": "import_meshes", "meshes": {}}
    for name, m in sorted(plan["meshes"].items()):
        try:
            out["meshes"][name] = import_one(m)
        except Exception:  # noqa: BLE001
            out["meshes"][name] = {"error": traceback.format_exc()}
    out["passed"] = all(not v.get("error") and (v.get("sidecar", {}).get("saved") or v.get("saved_by_build"))
                        for v in out["meshes"].values())
    return out


def run_assign(plan: dict) -> dict:
    out = {"mode": "assign", "meshes": {}}
    for name, m in sorted(plan["meshes"].items()):
        rep = {"asset": m["asset"]}
        try:
            mesh = unreal.load_asset(m["asset"])
            if m.get("kind") == "skeletal":
                import np_skeletal
                if not isinstance(mesh, unreal.SkeletalMesh):
                    raise RuntimeError(f"{m['asset']} is not a SkeletalMesh")
                rep.update(np_skeletal.assign(mesh, m))
                rep["saved"] = bool(EAL.save_loaded_asset(mesh, only_if_is_dirty=False))
                rep["after"] = slot_table(mesh)
                rep["lod_sections"] = lod_sections(mesh)
                out["meshes"][name] = rep
                continue
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"{m['asset']} is not a StaticMesh")
            before = slot_table(mesh)
            rep["before"] = before
            if len(before) != len(m["slots"]):
                raise RuntimeError(f"{name}: {len(before)} slots in Unreal, {len(m['slots'])} in the spec")
            for s in m["slots"]:
                got = before[s["index"]]["slot_name"]
                if got != s["slot_name"]:
                    raise RuntimeError(f"{name} slot {s['index']} is {got!r}, spec says {s['slot_name']!r}")
                mi = unreal.load_asset(s["instance_path"])
                if mi is None:
                    raise RuntimeError(f"{s['instance_path']} missing")
                mesh.set_material(s["index"], mi)
            rep["saved"] = bool(EAL.save_loaded_asset(mesh, only_if_is_dirty=False))
            rep["after"] = slot_table(mesh)
            rep["lod_sections"] = lod_sections(mesh)
        except Exception:  # noqa: BLE001
            rep["error"] = traceback.format_exc()
        out["meshes"][name] = rep
    out["passed"] = all(v.get("saved") and not v.get("error") for v in out["meshes"].values())
    return out
