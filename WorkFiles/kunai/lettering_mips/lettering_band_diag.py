"""Diagnose the lettering band in /Game/NinjaPack (UE 5.8, real RHI). Nothing is saved; the scratch folder is deleted.

Top-down orthographic BASE-COLOUR captures of SM_Kunai_Plain's grip (+X to the right, the +Z face toward the camera)
with scratch children of MI_Kunai_Plain_Wrap:
  off          Use Lettering off
  test_inh     on, mask = TEST pattern, band rectangle inherited
  test_set     on, mask = TEST pattern, band rectangle set explicitly on the child to the spec value
  black_inh    on, mask = engine black, rectangle inherited
  test_whole   on, mask = TEST pattern, rectangle = (1, 0, 2, 1) (the whole wrap tile)
plus a transient UV readout material (BaseColor = (u - 1, v, 0)) to read the mesh's real UV0 at the band.
"""
import json
import traceback
from pathlib import Path

import unreal

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/kunai/lettering_mips/diag2"
TEST_PNG = ROOT / "WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png"
SCRATCH = "/Game/Scratch_LetteringBandDiag2"
SHIPPED = "/Game/NinjaPack/Textures/Shuriken/T_Kunai_Lettering"
WRAP_MI = "/Game/NinjaPack/MaterialInstances/MI_Kunai_Plain_Wrap"
MESH = "/Game/NinjaPack/Meshes/SM_Kunai_Plain"
RECT = (1.1328125, 0.618985116, 1.8359375, 0.736172616)

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
res = {"captures": {}, "params": {}}


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def lc(v):
    return unreal.LinearColor(*v)


def make_mi(name, use, mask=None, rect=None):
    mi = AT.create_asset(name, SCRATCH, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", EAL.load_asset(WRAP_MI))
    if use:
        MEL.set_material_instance_static_switch_parameter_value(mi, "Use Lettering", True)
        MEL.set_material_instance_texture_parameter_value(mi, "Lettering Mask", mask)
        MEL.set_material_instance_vector_parameter_value(mi, "Lettering Colour", lc((1.0, 0.0, 0.0, 1.0)))
        if rect is not None:
            MEL.set_material_instance_vector_parameter_value(mi, "Lettering Band UV", lc(rect))
    MEL.update_material_instance(mi)
    st = MEL.get_statistics(mi)        # blocks until this permutation's shaders exist (np_build probe finding)
    v = MEL.get_material_instance_vector_parameter_value(mi, "Lettering Band UV")
    res["params"][name] = {"band_uv_read": [v.r, v.g, v.b, v.a],
                           "use_lettering": bool(MEL.get_material_instance_static_switch_parameter_value(mi, "Use Lettering")),
                           "ps_instructions": int(st.num_pixel_shader_instructions)}
    return mi


def uv_material():
    mat = unreal.new_object(unreal.Material, name="NP_UVReadout")
    tc = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -800, 0)
    off = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant2Vector, -800, 200)
    off.set_editor_property("r", 1.0)
    off.set_editor_property("g", 0.0)
    sub = MEL.create_material_expression(mat, unreal.MaterialExpressionSubtract, -600, 0)
    MEL.connect_material_expressions(tc, "", sub, "A")
    MEL.connect_material_expressions(off, "", sub, "B")
    z = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -600, 300)
    ap = MEL.create_material_expression(mat, unreal.MaterialExpressionAppendVector, -400, 0)
    MEL.connect_material_expressions(sub, "", ap, "A")
    MEL.connect_material_expressions(z, "", ap, "B")
    MEL.connect_material_property(ap, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.recompile_material(mat)
    MEL.get_statistics(mat)
    return mat


def capture(w, name, fmt=unreal.TextureRenderTargetFormat.RTF_RGBA8, ext=".png"):
    loc = unreal.Vector(-3.44, 0.0, 60.0)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot(pitch=-90.0, yaw=-90.0))
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(w, 2048, 1024, fmt)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    cc.set_editor_property("ortho_width", 12.0)
    for _ in range(3):
        cc.capture_scene()
    OUT.mkdir(parents=True, exist_ok=True)
    RL.export_render_target(w, rt, str(OUT), name + ext)
    EAS.destroy_actor(cap)
    return str(OUT / (name + ext))


def main():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if EAL.does_directory_exist(SCRATCH):
        raise RuntimeError(f"{SCRATCH} already exists")
    v = MEL.get_material_instance_vector_parameter_value(EAL.load_asset(WRAP_MI), "Lettering Band UV")
    res["params"]["MI_Kunai_Plain_Wrap"] = [v.r, v.g, v.b, v.a]
    EAL.duplicate_asset(SHIPPED, f"{SCRATCH}/T_Test")
    task = unreal.AssetImportTask()
    for k, val in (("filename", str(TEST_PNG)), ("destination_path", SCRATCH), ("destination_name", "T_Test"),
                   ("automated", True), ("replace_existing", True), ("save", False)):
        task.set_editor_property(k, val)
    AT.import_asset_tasks([task])
    test = EAL.load_asset(f"{SCRATCH}/T_Test")
    black = EAL.load_asset("/Engine/EngineResources/Black")
    mis = {"off": make_mi("MI_off", False),
           "test_inh": make_mi("MI_test_inh", True, test),
           "test_set": make_mi("MI_test_set", True, test, RECT),
           "black_inh": make_mi("MI_black_inh", True, black),
           "test_whole": make_mi("MI_test_whole", True, test, (1.0, 0.0, 2.0, 1.0))}
    mesh = EAL.load_asset(MESH)
    slot = next(i for i in range(4) if mesh.get_material(i) and "Wrap" in mesh.get_material(i).get_name())
    res["wrap_slot"] = slot
    actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), rot())
    smc = actor.get_editor_property("static_mesh_component")
    smc.set_static_mesh(mesh)
    try:
        for k, mi in mis.items():
            smc.set_material(slot, mi)
            res["captures"][k] = capture(w, f"diag_{k}")
        smc.set_material(slot, uv_material())
        res["captures"]["uv"] = capture(w, "diag_uv", unreal.TextureRenderTargetFormat.RTF_RGBA32F, ".exr")
    finally:
        EAS.destroy_actor(actor)


try:
    main()
except Exception:  # noqa: BLE001
    res["error"] = traceback.format_exc()
finally:
    try:
        if EAL.does_directory_exist(SCRATCH):
            res["scratch_deleted"] = bool(EAL.delete_directory(SCRATCH))
        res["scratch_exists_after"] = bool(EAL.does_directory_exist(SCRATCH))
    except Exception:  # noqa: BLE001
        res["cleanup_error"] = traceback.format_exc()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lettering_band_diag.json").write_text(json.dumps(res, indent=1))
    print("LETTERING_BAND_DIAG_DONE")
