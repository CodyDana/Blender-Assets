"""Heels Unreal check, step 1 (commandlet, -AllowCommandletRendering): import the SHIPPED heels onto her skeleton.

Everything lands under /Game/HeelsCheck/<RUN>/ (RUN from WorkFiles/SnowFlowerHeels/ue/run.json):
  SK_SnowFlowerHeels            LOD0 FBX onto metahuman_base_skel (never a new skeleton), LOD1/LOD2 added from their FBX,
                                screen sizes from the sidecar (1.0 / 0.5 / 0.25)
  Textures/T_SnowFlowerHeels_*  BC sRGB (Default), ORM linear (Masks), N (Normalmap, DirectX so no green flip)
  Materials/M_HeelsCheck_Preview + MI_* per slot (a TEST material; the pack masters belong to the Finalise agent)
  Anims/AS_Her_*                the MetaHumanCharacter plugin's female Stand_Idle / Walk_Loop_F / Run_Loop_F, exported to FBX
                                from the plugin's own metahuman_base_skel and re-imported onto HER skeleton (same bone names)
Her assets are only read. Writes WorkFiles/SnowFlowerHeels/ue/import_<RUN>.json.
"""
import hashlib
import json
import os
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/" + RUN
EXP = ROOT + "/Exports/SnowFlowerHeels"
SKELETON = "/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"
CLIPS = {
    "Idle": "/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Stand_Idle_Loop",
    "Walk": "/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Walk_Loop_F",
    "Run": "/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Run_Loop_F",
}
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SMS = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
rep = {"run": RUN, "dest": DEST, "status": "failed", "errors": [], "steps": []}


def note(msg):
    rep["steps"].append(msg)
    unreal.log("[hc_import] " + msg)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return "ERR " + str(exc)[:300]


def fbx_ui(skeleton, animation=False):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    if animation:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
        ui.set_editor_property("import_mesh", False)
        ui.set_editor_property("import_as_skeletal", True)
        ui.set_editor_property("import_animations", True)
        ad = ui.get_editor_property("anim_sequence_import_data")
        ad.set_editor_property("convert_scene", True)
        ad.set_editor_property("force_front_x_axis", False)
        ad.set_editor_property("convert_scene_unit", True)
        ad.set_editor_property("import_bone_tracks", True)
        ad.set_editor_property("remove_redundant_keys", False)
        ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        ui.set_editor_property("import_mesh", True)
        ui.set_editor_property("import_as_skeletal", True)
        ui.set_editor_property("import_animations", False)
        data = ui.get_editor_property("skeletal_mesh_import_data")
        data.set_editor_property("import_morph_targets", False)
        data.set_editor_property("convert_scene", True)
        data.set_editor_property("force_front_x_axis", False)
        data.set_editor_property("convert_scene_unit", True)
        data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    return ui


def run_task(filename, dest, name, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    if options is not None:
        task.set_editor_property("options", options)
    TOOLS.import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


try:
    skeleton = unreal.load_asset(SKELETON)
    sidecar = json.load(open(EXP + "/SK_SnowFlowerHeels.garment.json", encoding="utf-8"))
    rep["sidecar"] = sidecar
    rep["fbx_sha256"] = {f: sha(EXP + "/" + f) for f in sidecar["lods"]}
    rep["fbx_sha_matches_sidecar"] = rep["fbx_sha256"][sidecar["fbx"]] == sidecar["fbx_sha256"]
    # ---------------------------------------------------------------- mesh + LODs
    paths = run_task(EXP + "/" + sidecar["lods"][0], DEST, "SK_SnowFlowerHeels", fbx_ui(skeleton))
    note("LOD0 imported: %s" % paths)
    mesh = [unreal.load_asset(p) for p in paths]
    mesh = [m for m in mesh if isinstance(m, unreal.SkeletalMesh)][0]
    rep["mesh"] = mesh.get_path_name()
    rep["mesh_skeleton"] = mesh.get_editor_property("skeleton").get_path_name()
    for i, f in enumerate(sidecar["lods"][1:], start=1):
        r = SMS.import_lod(mesh, i, EXP + "/" + f)
        note("import_lod %d %s -> %s" % (i, f, r))
    rep["lod_count"] = SMS.get_lod_count(mesh)
    rep["mesh_lod_methods"] = [m for m in dir(mesh) if "lod" in m.lower()]
    # screen sizes
    sizes = sidecar["lod_screen_sizes"]
    done = False
    try:
        infos = mesh.get_editor_property("lod_info")
        for i, li in enumerate(infos):
            if i < len(sizes):
                li.set_editor_property("screen_size", unreal.PerPlatformFloat(default=sizes[i]))
        mesh.set_editor_property("lod_info", infos)
        done = True
        note("screen sizes via lod_info")
    except Exception as exc:  # noqa: BLE001
        note("lod_info not settable: %s" % exc)
    if not done:
        for i, s in enumerate(sizes):
            try:
                li = mesh.get_lod_info(i) if hasattr(mesh, "get_lod_info") else None
                note("lod %d info %s" % (i, li))
            except Exception as exc:  # noqa: BLE001
                note("get_lod_info %d: %s" % (i, exc))
        try:
            opts = unreal.SkeletalMeshBuildSettings()  # noqa: F841
        except Exception:  # noqa: BLE001
            pass
    rep["verts_per_lod"] = [SMS.get_num_verts(mesh, i) for i in range(rep["lod_count"])]
    rep["materials"] = [str(m.get_editor_property("material_slot_name")) for m in mesh.get_editor_property("materials")]
    # ---------------------------------------------------------------- textures
    tex = {}
    for slot in ("Leather", "Metal", "Insole"):
        for kind in ("BC", "ORM", "N"):
            name = "T_SnowFlowerHeels_%s_%s" % (slot, kind)
            p = run_task(EXP + "/Textures/" + name + ".png", DEST + "/Textures", name)
            t = unreal.load_asset(p[0])
            if kind == "BC":
                t.set_editor_property("srgb", True)
                t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
                t.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
            elif kind == "ORM":
                t.set_editor_property("srgb", False)
                t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                t.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
            else:
                t.set_editor_property("srgb", False)
                t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                t.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP)
                t.set_editor_property("flip_green_channel", False)
            t.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
            tex[name] = t
    rep["textures"] = sorted(tex)
    # ---------------------------------------------------------------- preview material (test only)
    MEL = unreal.MaterialEditingLibrary
    mat_path = DEST + "/Materials/M_HeelsCheck_Preview"
    mat = TOOLS.create_asset("M_HeelsCheck_Preview", DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    specs = [("BaseColor", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -600, -300),
             ("ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -600, 0),
             ("Normal", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -600, 300)]
    nodes = {}
    for pname, stype, x, y in specs:
        n = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        n.set_editor_property("parameter_name", pname)
        n.set_editor_property("sampler_type", stype)
        nodes[pname] = n
    nodes["BaseColor"].set_editor_property("texture", tex["T_SnowFlowerHeels_Leather_BC"])
    nodes["ORM"].set_editor_property("texture", tex["T_SnowFlowerHeels_Leather_ORM"])
    nodes["Normal"].set_editor_property("texture", tex["T_SnowFlowerHeels_Leather_N"])
    MEL.connect_material_property(nodes["BaseColor"], "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nodes["ORM"], "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(nodes["ORM"], "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(nodes["ORM"], "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(nodes["Normal"], "RGB", unreal.MaterialProperty.MP_NORMAL)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    MEL.recompile_material(mat)
    mis = {}
    for slot in ("Leather", "Insole", "Metal"):
        mi = TOOLS.create_asset("MI_HeelsCheck_" + slot, DEST + "/Materials", unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, mat)
        MEL.set_material_instance_texture_parameter_value(mi, "BaseColor", tex["T_SnowFlowerHeels_%s_BC" % slot])
        MEL.set_material_instance_texture_parameter_value(mi, "ORM", tex["T_SnowFlowerHeels_%s_ORM" % slot])
        MEL.set_material_instance_texture_parameter_value(mi, "Normal", tex["T_SnowFlowerHeels_%s_N" % slot])
        mis[slot] = mi
    mats = mesh.get_editor_property("materials")
    for i, m in enumerate(mats):
        slot = str(m.get_editor_property("material_slot_name")).replace("M_SnowFlowerHeels_", "")
        if slot in mis:
            m.set_editor_property("material_interface", mis[slot])
            mats[i] = m
    mesh.set_editor_property("materials", mats)
    note("materials assigned %s" % [str(m.get_editor_property("material_slot_name")) for m in mats])
    # ---------------------------------------------------------------- clips: plugin skeleton -> FBX -> her skeleton
    anim_dir = UE + "/anim_fbx"
    os.makedirs(anim_dir, exist_ok=True)
    rep["clips"] = {}
    for label, src in CLIPS.items():
        entry = {"source": src}
        try:
            anim = unreal.load_asset(src)
            entry["source_skeleton"] = anim.get_editor_property("skeleton").get_path_name()
            entry["source_length"] = anim.get_play_length()
            fbx = "%s/AS_Plugin_%s.fbx" % (anim_dir, label)
            et = unreal.AssetExportTask()
            et.set_editor_property("object", anim)
            et.set_editor_property("filename", fbx)
            et.set_editor_property("automated", True)
            et.set_editor_property("prompt", False)
            et.set_editor_property("replace_identical", True)
            et.set_editor_property("exporter", unreal.AnimSequenceExporterFBX())
            opt = unreal.FbxExportOption()
            opt.set_editor_property("export_preview_mesh", False)
            opt.set_editor_property("export_morph_targets", False)
            opt.set_editor_property("force_front_x_axis", False)
            et.set_editor_property("options", opt)
            entry["exported"] = unreal.Exporter.run_asset_export_task(et)
            entry["fbx_bytes"] = os.path.getsize(fbx) if os.path.exists(fbx) else 0
            p = run_task(fbx, DEST + "/Anims", "AS_Her_" + label, fbx_ui(skeleton, animation=True))
            entry["imported"] = p
            seqs = [unreal.load_asset(x) for x in p]
            seqs = [s for s in seqs if isinstance(s, unreal.AnimSequence)]
            if seqs:
                s = seqs[0]
                entry["skeleton"] = s.get_editor_property("skeleton").get_path_name()
                entry["length"] = s.get_play_length()
                entry["path"] = s.get_path_name()
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        rep["clips"][label] = entry
        note("clip %s: %s" % (label, entry.get("path", entry.get("error", "?"))[:200]))
    saved = EAL.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    note("saved %s -> %s" % (DEST, saved))
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/import_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
    unreal.log("[hc_import] status " + rep["status"])
