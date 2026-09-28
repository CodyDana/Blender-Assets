"""Build the Black Nunchucks per-part material in Unreal Engine 5.8.

Enable Python Editor Script Plugin and Editor Scripting Utilities, then execute
this file in Unreal. In an extracted package the workspace-relative layout is
preserved. Optionally set BLACK_NUNCHUCKS_ROOT to that extracted package root.

The generated /Game/BlackNunchucks folder is reserved for this importer. Re-running
rebuilds its master and demo instances; keep your own presets in another folder.
This editor-only setup is not required at runtime: ordinary dynamic material
instance parameters control the saved material in a packaged game.
"""
from pathlib import Path
import hashlib
import json
import os
import traceback

import unreal

PARTS = ["Grip_L", "Grip_R", "Cap_L", "Cap_R", "Eye_L", "Eye_R"] + [
    f"Chain_{i:02d}" for i in range(1, 8)
] + ["Weld_03", "Weld_04", "Weld_05"]
DEST = "/Game/BlackNunchucks"
MASTER_NAME = "M_BlackNunchucks_Customizable"
DEFAULT_NAME = "MI_BlackNunchucks_Default"
DEMO_NAME = "MI_BlackNunchucks_Demo"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
DEMO_COLORS = {
    "Grip_L": (0.65, 0.012, 0.018, 1.0), "Grip_R": (0.8, 0.82, 0.75, 1.0),
    "Cap_L": (0.78, 0.39, 0.07, 1.0), "Cap_R": (0.055, 0.14, 0.7, 1.0),
    "Eye_L": (0.8, 0.7, 0.45, 1.0), "Eye_R": (0.35, 0.6, 0.8, 1.0),
    "Chain_01": (0.7, 0.09, 0.02, 1.0), "Chain_02": (0.02, 0.5, 0.65, 1.0),
    "Chain_03": (0.65, 0.4, 0.04, 1.0), "Chain_04": (0.35, 0.02, 0.55, 1.0),
    "Chain_05": (0.03, 0.55, 0.15, 1.0), "Chain_06": (0.65, 0.03, 0.23, 1.0),
    "Chain_07": (0.035, 0.2, 0.65, 1.0), "Weld_03": (0.65, 0.4, 0.04, 1.0),
    "Weld_04": (0.35, 0.02, 0.55, 1.0), "Weld_05": (0.03, 0.55, 0.15, 1.0),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def root_folder():
    return Path(os.environ.get("BLACK_NUNCHUCKS_ROOT", str(Path(__file__).resolve().parents[2])))


def asset(path):
    result = unreal.load_asset(path)
    if result is None:
        raise RuntimeError("Missing asset: " + path)
    return result


def create_or_load(name, folder, cls, factory):
    path = folder + "/" + name
    existing = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    result = existing or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, cls, factory)
    assert isinstance(result, cls), path
    return result


def import_file(source, folder, name, options=None):
    assert source.is_file(), str(source)
    task = unreal.AssetImportTask()
    for key, value in {
        "filename": str(source), "destination_path": folder,
        "destination_name": name, "automated": True, "replace_existing": True,
        "replace_existing_settings": True, "save": False,
    }.items():
        task.set_editor_property(key, value)
    if options is not None:
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = [asset(str(p)) for p in task.get_editor_property("imported_object_paths")]
    assert imported, "Nothing imported from " + str(source)
    return imported


def import_textures(root, dest):
    files = {
        "BaseColor": ("basecolor", True, unreal.TextureCompressionSettings.TC_DEFAULT),
        "Normal": ("normal", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
        "ORM": ("orm", False, unreal.TextureCompressionSettings.TC_MASKS),
        "TintDetail": ("tintdetail", False, unreal.TextureCompressionSettings.TC_DEFAULT),
        **{f"PartMask{i}": (f"partmask{i}", False, unreal.TextureCompressionSettings.TC_MASKS) for i in range(4)},
    }
    textures, records = {}, {}
    for key, (suffix, srgb, compression) in files.items():
        source = root / "Textures/BlackNunchucks" / f"blacknunchucks_{suffix}.png"
        name = "T_BlackNunchucks_" + key
        candidates = import_file(source, dest + "/Textures", name)
        tex = next(t for t in candidates if isinstance(t, unreal.Texture2D))
        tex.set_editor_property("srgb", srgb)
        tex.set_editor_property("compression_settings", compression)
        tex.set_editor_property("flip_green_channel", False)
        tex.set_editor_property("compression_no_alpha", False)
        tex.set_editor_property("virtual_texture_streaming", False)
        tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
        assert EAL.save_loaded_asset(tex, only_if_is_dirty=False)
        textures[key] = tex
        records[key] = {"source": str(source), "sha256": sha256(source), "asset": tex.get_path_name(),
                        "srgb": srgb, "compression": str(compression), "alpha_preserved": True}
    return textures, records


def make_master(textures, dest=DEST):
    mat = create_or_load(MASTER_NAME, dest + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(mat)
    MEL.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    mat.set_editor_property("two_sided", False)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)

    def node(cls, x, y, **props):
        n = MEL.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def connect(a, output, b, input_name):
        assert MEL.connect_material_expressions(a, output, b, input_name), (str(a), output, str(b), input_name)

    samplers = {}
    for idx, (key, tex) in enumerate(textures.items()):
        sampler_type = (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if key == "Normal" else
                        unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if key == "BaseColor" else
                        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS if key.startswith("PartMask") or key == "ORM" else
                        unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        samplers[key] = node(unreal.MaterialExpressionTextureSampleParameter2D, -2300, idx * 290,
                             parameter_name="Texture_" + key, texture=tex, sampler_type=sampler_type,
                             group="00 Textures", desc="UV0 atlas; replace for a compatible full skin")
    previous, previous_pin = samplers["BaseColor"], "RGB"
    for index, part in enumerate(PARTS):
        y = index * 360
        color = node(unreal.MaterialExpressionVectorParameter, -1900, y,
                     parameter_name="Color_" + part, default_value=unreal.LinearColor(1, 1, 1, 1),
                     group=f"{index+1:02d} {part}", desc="Linear tint; set Amount to 1 to use this color")
        amount = node(unreal.MaterialExpressionScalarParameter, -1900, y + 150,
                      parameter_name="Amount_" + part, default_value=0.0,
                      slider_min=0.0, slider_max=1.0, group=f"{index+1:02d} {part}",
                      desc="0 = original skin, 1 = selected tint; values are clamped")
        clamp = node(unreal.MaterialExpressionSaturate, -1610, y + 180)
        connect(amount, "", clamp, "")
        alpha = node(unreal.MaterialExpressionMultiply, -1400, y + 170)
        connect(clamp, "", alpha, "A")
        connect(samplers[f"PartMask{index//4}"], "RGBA"[index % 4], alpha, "B")
        tint = node(unreal.MaterialExpressionMultiply, -1400, y)
        connect(color, "RGB", tint, "A")
        connect(samplers["TintDetail"], "RGB", tint, "B")
        blend = node(unreal.MaterialExpressionLinearInterpolate, -950 + index * 90, y)
        connect(previous, previous_pin, blend, "A")
        connect(tint, "", blend, "B")
        connect(alpha, "", blend, "Alpha")
        previous, previous_pin = blend, ""
    assert MEL.connect_material_property(previous, previous_pin, unreal.MaterialProperty.MP_BASE_COLOR)
    for output, prop in [("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                         ("G", unreal.MaterialProperty.MP_ROUGHNESS),
                         ("B", unreal.MaterialProperty.MP_METALLIC)]:
        assert MEL.connect_material_property(samplers["ORM"], output, prop)
    assert MEL.connect_material_property(samplers["Normal"], "RGB", unreal.MaterialProperty.MP_NORMAL)
    errors = list(MEL.recompile_material(mat))
    assert not errors, errors
    assert EAL.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat, errors


def make_instance(name, mat, dest, demo=False):
    mi = create_or_load(name, dest + "/Materials", unreal.MaterialInstanceConstant,
                        unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, mat)
    MEL.clear_all_material_instance_parameters(mi)
    if demo:
        for part, value in DEMO_COLORS.items():
            # UE 5.8's implementation returns false unconditionally; read back instead.
            color = unreal.LinearColor(*value)
            MEL.set_material_instance_vector_parameter_value(mi, "Color_" + part, color)
            MEL.set_material_instance_scalar_parameter_value(mi, "Amount_" + part, 1.0)
            assert values(MEL.get_material_instance_vector_parameter_value(mi, "Color_" + part)) == values(color)
            assert MEL.get_material_instance_scalar_parameter_value(mi, "Amount_" + part) == 1.0
    MEL.update_material_instance(mi)
    assert EAL.save_loaded_asset(mi, only_if_is_dirty=False)
    return mi


def import_mesh(root, dest, material):
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = unreal.FbxImportUI()
    for key, val in {"automated_import_should_detect_type": False,
                     "mesh_type_to_import": unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                     "import_as_skeletal": True, "import_mesh": True,
                     "import_materials": False, "import_textures": False,
                     "import_animations": False, "create_physics_asset": False}.items():
        ui.set_editor_property(key, val)
    data = ui.get_editor_property("skeletal_mesh_import_data")
    for key, val in {"import_mesh_lods": False, "normal_import_method": unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                     "normal_generation_method": unreal.FBXNormalGenerationMethod.MIKK_T_SPACE,
                     "convert_scene": True, "convert_scene_unit": True,
                     "force_front_x_axis": False, "import_uniform_scale": 1.0,
                     "import_morph_targets": False}.items():
        data.set_editor_property(key, val)
    source = root / "Exports/BlackNunchucks/SK_BlackNunchucks_LOD0.fbx"
    objects = import_file(source, dest + "/Meshes", "SK_BlackNunchucks", ui)
    mesh = next(o for o in objects if isinstance(o, unreal.SkeletalMesh))
    # Preserve FBX imported slot names so the additional LODs reuse slot zero.
    slots = mesh.get_editor_property("materials")
    assert len(slots) == 1
    slot = slots[0]
    slot.set_editor_property("material_interface", material)
    slots[0] = slot
    mesh.set_editor_property("materials", slots)
    lods = [{"lod": 0, "source": str(source), "sha256": sha256(source)}]
    for index in (1, 2):
        fbx = source.with_name(f"SK_BlackNunchucks_LOD{index}.fbx")
        assert unreal.SkeletalMeshEditorSubsystem.import_lod(mesh, index, str(fbx)) == index
        lods.append({"lod": index, "source": str(fbx), "sha256": sha256(fbx)})
    slots = mesh.get_editor_property("materials")
    assert len(slots) == 1
    slot = slots[0]
    slot.set_editor_property("material_interface", material)
    slots[0] = slot
    mesh.set_editor_property("materials", slots)
    assert EAL.save_loaded_asset(mesh, only_if_is_dirty=False)
    for obj in objects:
        assert EAL.save_loaded_asset(obj, only_if_is_dirty=False)
    return mesh, lods


def values(color):
    return [float(color.r), float(color.g), float(color.b), float(color.a)]


def verify(dest=DEST, source_records=None):
    mat = asset(dest + "/Materials/" + MASTER_NAME)
    default = asset(dest + "/Materials/" + DEFAULT_NAME)
    demo = asset(dest + "/Materials/" + DEMO_NAME)
    mesh = asset(dest + "/Meshes/SK_BlackNunchucks")
    assert isinstance(mesh, unreal.SkeletalMesh)
    assert default.get_editor_property("parent") == mat
    assert demo.get_editor_property("parent") == mat
    assert len(mesh.get_editor_property("materials")) == 1
    assert mesh.get_editor_property("materials")[0].material_interface == default
    vector_names = sorted(str(n) for n in MEL.get_vector_parameter_names(mat))
    scalar_names = sorted(str(n) for n in MEL.get_scalar_parameter_names(mat))
    texture_names = sorted(str(n) for n in MEL.get_texture_parameter_names(mat))
    assert vector_names == sorted("Color_" + p for p in PARTS)
    assert scalar_names == sorted("Amount_" + p for p in PARTS)
    expected_textures = ["BaseColor", "Normal", "ORM", "TintDetail"] + [f"PartMask{i}" for i in range(4)]
    assert texture_names == sorted("Texture_" + p for p in expected_textures)
    defaults = {}
    for part in PARTS:
        amount = MEL.get_material_instance_scalar_parameter_value(default, "Amount_" + part)
        tint = values(MEL.get_material_instance_vector_parameter_value(default, "Color_" + part))
        assert amount == 0.0 and tint == [1.0, 1.0, 1.0, 1.0]
        defaults[part] = {"amount": amount, "color": tint}
    texture_flags = {}
    for key in expected_textures:
        tex = MEL.get_material_instance_texture_parameter_value(default, "Texture_" + key)
        assert isinstance(tex, unreal.Texture2D)
        want_srgb = key == "BaseColor"
        assert tex.get_editor_property("srgb") == want_srgb
        assert not tex.get_editor_property("flip_green_channel")
        assert not tex.get_editor_property("compression_no_alpha")
        comp = tex.get_editor_property("compression_settings")
        if key == "Normal": assert comp == unreal.TextureCompressionSettings.TC_NORMALMAP
        if key == "ORM" or key.startswith("PartMask"): assert comp == unreal.TextureCompressionSettings.TC_MASKS
        texture_flags[key] = {"asset": tex.get_path_name(), "srgb": want_srgb,
                              "compression": str(comp), "alpha_preserved": True,
                              "size": [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()]}
    # Exercise the actual runtime component API, then independently read back the MID.
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    mid = component.create_dynamic_material_instance(0, default, "BlackNunchucks_RuntimeTest")
    assert isinstance(mid, unreal.MaterialInstanceDynamic)
    runtime = []
    for index, part in enumerate(PARTS):
        test_color = unreal.LinearColor(0.15, 0.80, 0.05, 1.0) if index % 2 else unreal.LinearColor(0.85, 0.03, 0.08, 1.0)
        mid.set_vector_parameter_value("Color_" + part, test_color)
        mid.set_scalar_parameter_value("Amount_" + part, 1.0)
        for other in PARTS:
            amount = mid.get_scalar_parameter_value("Amount_" + other)
            assert amount == (1.0 if other == part else 0.0), (part, other, amount)
            expected = values(test_color) if other == part else [1.0, 1.0, 1.0, 1.0]
            assert values(mid.get_vector_parameter_value("Color_" + other)) == expected
        runtime.append({"part": part, "set_and_read_color": values(test_color), "other_parts_unchanged": True})
        mid.set_scalar_parameter_value("Amount_" + part, 0.0)
        mid.set_vector_parameter_value("Color_" + part, unreal.LinearColor(1, 1, 1, 1))
    base = MEL.get_material_instance_texture_parameter_value(default, "Texture_BaseColor")
    test_skin = MEL.get_material_instance_texture_parameter_value(default, "Texture_TintDetail")
    mid.set_texture_parameter_value("Texture_BaseColor", test_skin)
    assert mid.get_texture_parameter_value("Texture_BaseColor") == test_skin
    mid.set_texture_parameter_value("Texture_BaseColor", base)
    assert mid.get_texture_parameter_value("Texture_BaseColor") == base
    lod_count = unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh)
    assert lod_count == 3
    inspector = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    if inspector is None:
        # These read-only getters only inspect the supplied asset (no subsystem state).
        inspector = unreal.new_object(unreal.SkeletalMeshEditorSubsystem)
    lod_info = []
    for lod in range(lod_count):
        sections = inspector.get_num_sections(mesh, lod)
        slots = [inspector.get_lod_material_slot(mesh, lod, section) for section in range(sections)]
        assert sections == 1 and slots == [0], (lod, sections, slots)
        lod_info.append({"lod": lod, "sections": sections, "material_slots": slots,
                         "vertices": inspector.get_num_verts(mesh, lod)})
    assert lod_info[0]["vertices"] > lod_info[1]["vertices"] > lod_info[2]["vertices"] > 0
    source_hashes = {}
    if source_records:
        for rec in list(source_records["textures"].values()) + source_records["mesh_lods"]:
            assert sha256(rec["source"]) == rec["sha256"], rec["source"]
            source_hashes[rec["source"]] = rec["sha256"]
    errors = list(MEL.recompile_material(mat))
    assert not errors, errors
    return {"status": "passed", "engine": unreal.SystemLibrary.get_engine_version(),
            "material": mat.get_path_name(), "mesh": mesh.get_path_name(),
            "material_slots": 1, "lod_count": lod_count, "lod_sections": lod_info,
            "vector_parameters": vector_names, "scalar_parameters": scalar_names,
            "texture_parameters": texture_names, "defaults": defaults,
            "textures": texture_flags, "runtime_mid_tests": runtime,
            "runtime_texture_swap": True, "compile_errors": errors,
            "matching_source_sha256": source_hashes}


def setup(root=None, dest=DEST, report_path=None):
    root = Path(root) if root is not None else root_folder()
    report_path = Path(report_path) if report_path else root / "WorkFiles/BlackNunchucks/RecolorUnreal/setup_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "engine": unreal.SystemLibrary.get_engine_version(), "dest": dest}
    try:
        textures, report["textures"] = import_textures(root, dest)
        mat, report["compile_errors"] = make_master(textures, dest)
        default = make_instance(DEFAULT_NAME, mat, dest)
        make_instance(DEMO_NAME, mat, dest, demo=True)
        mesh, report["mesh_lods"] = import_mesh(root, dest, default)
        assert EAL.save_directory(dest, only_if_is_dirty=False, recursive=True)
        report["in_process_checks"] = verify(dest, report)
        report["status"] = "passed"
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        unreal.log("BLACK_NUNCHUCKS_SETUP_REPORT " + str(report_path))
    return report


if __name__ == "__main__":
    setup()
