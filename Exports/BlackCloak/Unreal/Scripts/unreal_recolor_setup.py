"""Create the recolorable cloak materials in an isolated Unreal 5.8 project.

Run with UnrealEditor-Cmd PROJECT -run=pythonscript -script=THIS_FILE.
BLACKCLOAK_SOURCE may point at a portable BlackCloak export folder. Otherwise
the export folder is discovered relative to this script or the project.
Only /Game/BlackCloak assets are created/updated. The Blender/FBX source is read.
"""
from pathlib import Path
import hashlib
import json
import os
import traceback
import unreal

DEST = "/Game/BlackCloak"
PROJECT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
REPORT = PROJECT / "Validation" / "recolor_setup_report.json"
GRAIN_REFERENCE_LINEAR = 0.013702083
PRESETS = {
    "Black": [0.013702083, 0.01355, 0.0134],
    "Crimson": [0.32, 0.012, 0.018],
    "Navy": [0.016, 0.035, 0.12],
    "Ivory": [0.80, 0.73, 0.57],
}
MEL = unreal.MaterialEditingLibrary


def source_folder():
    here = Path(__file__).resolve()
    candidates = []
    if os.environ.get("BLACKCLOAK_SOURCE"):
        candidates.append(Path(os.environ["BLACKCLOAK_SOURCE"]))
    candidates += [here.parents[2] / "Exports" / "BlackCloak", here.parent.parent,
                   PROJECT.parent, PROJECT.parent.parent]
    for path in candidates:
        if (path / "BlackCloak.fbx").is_file() and (path / "Textures").is_dir():
            return path.resolve()
    raise FileNotFoundError("Set BLACKCLOAK_SOURCE to the exported BlackCloak folder.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Failed to save " + asset.get_path_name())


def asset(name, kind, factory):
    path = DEST + "/Materials/" + name
    found = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if found is None:
        found = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST + "/Materials", kind, factory)
    if not isinstance(found, kind):
        raise TypeError("Unexpected asset type at " + path)
    return found


def import_texture(path, role):
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=DEST + "/Textures",
                           destination_name=path.stem, automated=True, replace_existing=True,
                           replace_existing_settings=True, save=True).items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = unreal.load_asset(DEST + "/Textures/" + path.stem)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError("Texture import failed: " + str(path))
    texture.set_editor_property("srgb", role == "base")
    if role == "normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif role == "roughness":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    save(texture)
    return texture


def material_graph(textures):
    material = asset("M_Cloak_Recolor", unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(material)
    material.set_editor_property("two_sided", True)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("used_with_skeletal_mesh", True)
    nodes, connections = {}, []

    def node(key, cls, x, y, **props):
        expr = MEL.create_material_expression(material, cls, x, y)
        expr.set_editor_property("desc", key)
        for prop, value in props.items():
            expr.set_editor_property(prop, value)
        nodes[key] = expr
        return expr

    def link(a, output, b, pin):
        if pin in ("Input", "VectorInput"):
            pin = ""  # Unreal's default first input; visible pin labels differ.
        if not MEL.connect_material_expressions(nodes[a], output, nodes[b], pin):
            raise RuntimeError("Could not connect %s.%s -> %s.%s" % (a, output, b, pin))
        connections.append([a, output, b, pin])

    def output(a, pin, prop):
        if not MEL.connect_material_property(nodes[a], pin, prop):
            raise RuntimeError("Could not connect material property: " + str(prop))
        connections.append([a, pin, str(prop)])

    node("Fabric base sample (sRGB decoded to linear)", unreal.MaterialExpressionTextureSample,
         -1200, -200, texture=textures["base"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    node("Normalize neutral grain", unreal.MaterialExpressionDivide, -920, -200,
         const_b=GRAIN_REFERENCE_LINEAR)
    link("Fabric base sample (sRGB decoded to linear)", "R", "Normalize neutral grain", "A")
    node("Bound grain", unreal.MaterialExpressionClamp, -760, -200, min_default=0.0, max_default=1.0)
    link("Normalize neutral grain", "", "Bound grain", "Input")
    node("FabricDetail", unreal.MaterialExpressionScalarParameter, -1150, 70,
         parameter_name="FabricDetail", default_value=1.0, slider_min=0.0, slider_max=1.0)
    node("Bound FabricDetail", unreal.MaterialExpressionClamp, -900, 90, min_default=0.0, max_default=1.0)
    link("FabricDetail", "", "Bound FabricDetail", "Input")
    node("Grain blend", unreal.MaterialExpressionLinearInterpolate, -650, -160, const_a=1.0)
    link("Bound grain", "", "Grain blend", "B")
    link("Bound FabricDetail", "", "Grain blend", "Alpha")
    node("CloakColor", unreal.MaterialExpressionVectorParameter, -650, -390,
         parameter_name="CloakColor", default_value=unreal.LinearColor(*PRESETS["Black"], 1.0))
    node("Tint by grain", unreal.MaterialExpressionMultiply, -350, -220)
    link("CloakColor", "RGB", "Tint by grain", "A")
    link("Grain blend", "", "Tint by grain", "B")
    node("Clamp base color", unreal.MaterialExpressionClamp, -90, -220, min_default=0.0, max_default=1.0)
    link("Tint by grain", "", "Clamp base color", "Input")
    output("Clamp base color", "", unreal.MaterialProperty.MP_BASE_COLOR)

    node("Roughness sample", unreal.MaterialExpressionTextureSample, -1150, 380,
         texture=textures["roughness"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    node("RoughnessMultiplier", unreal.MaterialExpressionScalarParameter, -1150, 600,
         parameter_name="RoughnessMultiplier", default_value=1.0, slider_min=0.0, slider_max=2.0)
    node("Roughness product", unreal.MaterialExpressionMultiply, -820, 380)
    link("Roughness sample", "R", "Roughness product", "A")
    link("RoughnessMultiplier", "", "Roughness product", "B")
    node("Clamp roughness", unreal.MaterialExpressionClamp, -530, 380, min_default=0.0, max_default=1.0)
    link("Roughness product", "", "Clamp roughness", "Input")
    output("Clamp roughness", "", unreal.MaterialProperty.MP_ROUGHNESS)
    node("Metallic zero", unreal.MaterialExpressionConstant, -300, 540, r=0.0)
    node("Low fabric specular", unreal.MaterialExpressionConstant, -300, 650, r=0.08)
    output("Metallic zero", "", unreal.MaterialProperty.MP_METALLIC)
    output("Low fabric specular", "", unreal.MaterialProperty.MP_SPECULAR)

    node("DirectX normal sample", unreal.MaterialExpressionTextureSample, -1150, 860,
         texture=textures["normal"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    node("Flat normal", unreal.MaterialExpressionConstant3Vector, -1150, 1100,
         constant=unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
    node("NormalStrength", unreal.MaterialExpressionScalarParameter, -1150, 1290,
         parameter_name="NormalStrength", default_value=1.0, slider_min=0.0, slider_max=2.0)
    node("Normal blend", unreal.MaterialExpressionLinearInterpolate, -810, 930)
    link("Flat normal", "", "Normal blend", "A")
    link("DirectX normal sample", "RGB", "Normal blend", "B")
    link("NormalStrength", "", "Normal blend", "Alpha")
    node("Normalize tangent normal", unreal.MaterialExpressionNormalize, -500, 930)
    link("Normal blend", "", "Normalize tangent normal", "VectorInput")
    output("Normalize tangent normal", "", unreal.MaterialProperty.MP_NORMAL)
    MEL.layout_material_expressions(material)
    MEL.recompile_material(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, "CloakFormula",
        "Clamp(CloakColor * Lerp(1, Saturate(BaseColorTexture.R_linear / 0.013702083), Saturate(FabricDetail)), 0, 1)")
    save(material)
    return material, connections


def simple_material(name, color, roughness, metallic):
    material = asset(name, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("used_with_skeletal_mesh", True)
    MEL.delete_all_material_expressions(material)
    color_node = MEL.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -300, 0)
    color_node.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    MEL.connect_material_property(color_node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for y, value, prop in [(180, roughness, unreal.MaterialProperty.MP_ROUGHNESS),
                           (360, metallic, unreal.MaterialProperty.MP_METALLIC)]:
        expr = MEL.create_material_expression(material, unreal.MaterialExpressionConstant, -300, y)
        expr.set_editor_property("r", value)
        MEL.connect_material_property(expr, "", prop)
    MEL.recompile_material(material)
    save(material)
    return material


def instances(master):
    result = {}
    for name, color in PRESETS.items():
        inst = asset("MI_Cloak_" + name, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(inst, master)
        # UE 5.8.2's setters leave their local bResult false even after writing.
        # Verify the value itself, and later repeat in a fresh process.
        MEL.set_material_instance_vector_parameter_value(inst, "CloakColor", unreal.LinearColor(*color, 1))
        actual=MEL.get_material_instance_vector_parameter_value(inst,"CloakColor")
        assert max(abs(a-b) for a,b in zip((actual.r,actual.g,actual.b),color))<1e-6
        for parameter in ("FabricDetail", "NormalStrength", "RoughnessMultiplier"):
            MEL.set_material_instance_scalar_parameter_value(inst, parameter, 1.0)
            assert abs(MEL.get_material_instance_scalar_parameter_value(inst,parameter)-1)<1e-6
        MEL.update_material_instance(inst)
        save(inst)
        result[name] = inst
    return result


def ensure_skeleton(mesh):
    """Persist the mesh's skeleton, including after a legacy FBX reimport."""
    skeleton = mesh.get_editor_property("skeleton")
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError("Cloak skeleton creation failed")
    assert mesh.get_editor_property("skeleton") == skeleton
    save(skeleton)
    save(mesh)
    return skeleton.get_path_name()


def import_mesh(path, skeletal, materials):
    ui = unreal.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False, import_as_skeletal=skeletal,
                           import_mesh=True, import_materials=False, import_textures=False,
                           import_animations=False, create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal
                           else unreal.FBXImportType.FBXIT_STATIC_MESH)
    skeleton_asset = DEST + "/Meshes/SK_BlackCloak_Skeleton"
    if skeletal and unreal.EditorAssetLibrary.does_asset_exist(skeleton_asset):
        ui.set_editor_property("skeleton", unreal.load_asset(skeleton_asset))
    imp = ui.get_editor_property("skeletal_mesh_import_data" if skeletal else "static_mesh_import_data")
    for key, value in dict(import_mesh_lods=False, normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                           normal_generation_method=unreal.FBXNormalGenerationMethod.MIKK_T_SPACE,
                           convert_scene=True, convert_scene_unit=True, force_front_x_axis=False,
                           import_uniform_scale=1.0).items():
        imp.set_editor_property(key, value)
    if skeletal:
        imp.set_editor_property("import_content_type", unreal.FBXImportContentType.FBXICT_ALL)
        imp.set_editor_property("update_skeleton_reference_pose", False)
        imp.set_editor_property("use_t0_as_ref_pose", False)
    else:
        imp.set_editor_property("combine_meshes", True)
        imp.set_editor_property("auto_generate_collision", False)
        imp.set_editor_property("generate_lightmap_u_vs", True)
    name = "SK_BlackCloak" if skeletal else "SM_BlackCloak"
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=DEST + "/Meshes", destination_name=name,
                           automated=True, replace_existing=True, replace_existing_settings=True,
                           save=True, factory=unreal.FbxFactory(), options=ui).items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(DEST + "/Meshes/" + name)
    cls = unreal.SkeletalMesh if skeletal else unreal.StaticMesh
    if not isinstance(mesh, cls):
        raise RuntimeError("Cloak mesh import failed: " + name)
    prop = "materials" if skeletal else "static_materials"
    slots = list(mesh.get_editor_property(prop))
    result = []
    for index, slot in enumerate(slots):
        source_name = str(slot.get_editor_property("imported_material_slot_name"))
        slot_name = str(slot.get_editor_property("material_slot_name"))
        token = (source_name + " " + slot_name).lower()
        if "wovenwool" in token:
            assigned = materials["cloth"]
        elif "steel" in token:
            assigned = materials["steel"]
        elif "leather" in token:
            assigned = materials["leather"]
        else:
            raise ValueError("Unknown cloak material slot: " + token)
        slot.set_editor_property("material_interface", assigned)
        result.append({"index": index, "slot": slot_name, "source_slot": source_name,
                       "material": assigned.get_path_name()})
    mesh.set_editor_property(prop, slots)
    save(mesh)
    skeleton_path = ensure_skeleton(mesh) if skeletal else None
    return {"path": mesh.get_path_name(), "skeletal": skeletal, "source": str(path),
            "skeleton": skeleton_path,
            "source_sha256": sha(path), "material_slots": result,
            "imported_object_paths": [str(p) for p in task.get_editor_property("imported_object_paths")]}


def main():
    report = {"status": "running", "engine": unreal.SystemLibrary.get_engine_version(),
              "project": str(PROJECT), "presets_linear": PRESETS,
              "grain_reference_linear": GRAIN_REFERENCE_LINEAR,
              "color_parameter_semantics": "Linear RGB of the brightest yarn/dye swatch; grain and lighting darken the rendered average.",
              "limits": ["No cloth physics, cloth simulation or collision setup is created.",
                         "Skeletal mesh has existing rigid attachment weights; no playable animation test.",
                         "This workflow validates saved recoloring controls, not a photorealistic reference match.",
                         "Mesh import includes LOD0 only. Existing exported LOD1/LOD2 remain separately available."]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        source = source_folder()
        report["source_folder"] = str(source)
        report["source_files_sha256"] = {p.name: sha(p) for p in [source / "BlackCloak.fbx", source / "BlackCloak_Skeletal.fbx"]}
        tex_paths = {"base": source / "Textures/T_BlackCloak_BaseColor.png",
                     "roughness": source / "Textures/T_BlackCloak_Roughness.png",
                     "normal": source / "Textures/T_BlackCloak_Normal_DirectX.png"}
        textures = {role: import_texture(path, role) for role, path in tex_paths.items()}
        report["textures"] = {role: {"path": tex.get_path_name(), "source_sha256": sha(tex_paths[role]),
            "srgb": bool(tex.get_editor_property("srgb")), "compression": str(tex.get_editor_property("compression_settings")),
            "flip_green_channel": bool(tex.get_editor_property("flip_green_channel"))} for role, tex in textures.items()}
        master, connections = material_graph(textures)
        variants = instances(master)
        report["master_material"] = master.get_path_name()
        report["graph_connections"] = connections
        report["instances"] = {name: inst.get_path_name() for name, inst in variants.items()}
        materials = {"cloth": variants["Black"],
                     "steel": simple_material("M_Cloak_BlackenedSteel", [0.012, 0.013, 0.012], 0.73, 1.0),
                     "leather": simple_material("M_Cloak_CharcoalLeather", [0.014, 0.011, 0.008], 0.66, 0.0)}
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
        report["meshes"] = [import_mesh(source / "BlackCloak.fbx", False, materials),
                            import_mesh(source / "BlackCloak_Skeletal.fbx", True, materials)]
        report["status"] = "saved_pending_fresh_process_verification"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("BLACKCLOAK_RECOLOR_SETUP " + report["status"] + " " + str(REPORT))
    if report["status"] == "failed":
        raise RuntimeError(report["error"])


if __name__ == "__main__":
    main()
