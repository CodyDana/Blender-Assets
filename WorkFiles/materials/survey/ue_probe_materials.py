"""Throwaway capability probe for the pack-materials job (UE 5.8.3, validation project only).

MODE (env NP_PROBE_MODE):
  author  - write two tiny PNGs, import them, build MF + materials + MICs in /Game/_Probe_NPMat_0926,
            compile, save, and (if the RHI is real) render BaseColor / lit captures of a plane
  reload  - fresh process: reload the MICs, read their parameters back, then DELETE the probe folder
Writes WorkFiles/materials/survey/probe/ue_probe_<mode>.json
"""
import json
import os
import struct
import time
import traceback
import zlib
from pathlib import Path

import unreal

MODE = os.environ.get("NP_PROBE_MODE", "author")
HERE = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/survey/probe")
HERE.mkdir(parents=True, exist_ok=True)
DEST = "/Game/_Probe_NPMat_0926"
OUT = HERE / f"ue_probe_{MODE}.json"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
R = {"mode": MODE, "steps": [], "errors": []}


def step(name, fn):
    t0 = time.time()
    try:
        val = fn()
        R["steps"].append({"step": name, "ok": True, "sec": round(time.time() - t0, 2), "result": val})
        return val
    except Exception as exc:  # noqa
        R["steps"].append({"step": name, "ok": False, "sec": round(time.time() - t0, 2),
                           "error": repr(exc), "trace": traceback.format_exc()[-1500:]})
        return None


def save():
    OUT.write_text(json.dumps(R, indent=1, default=str))


def png(path, w, h, rows, colour_type):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + r for r in rows)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, colour_type, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)


def s2l(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def import_png(src, name, srgb, comp):
    task = unreal.AssetImportTask()
    for k, v in {"filename": str(src), "destination_path": DEST + "/Textures", "destination_name": name,
                 "automated": True, "replace_existing": True, "save": False}.items():
        task.set_editor_property(k, v)
    AT.import_asset_tasks([task])
    tex = unreal.load_asset(DEST + "/Textures/" + name)
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("compression_settings", comp)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    EAL.save_loaded_asset(tex, only_if_is_dirty=False)
    info = {"asset": tex.get_path_name(), "srgb": tex.get_editor_property("srgb"),
            "compression": str(tex.get_editor_property("compression_settings"))}
    for fn in ("blueprint_get_memory_size",):
        try:
            info[fn] = getattr(tex, fn)()
        except Exception as exc:  # noqa
            info[fn] = repr(exc)
    for prop in ("source_colour_settings",):
        try:
            info[prop] = str(tex.get_editor_property(prop))
        except Exception:  # noqa
            pass
    return tex, info


def new_asset(name, folder, cls, factory):
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    return AT.create_asset(name, folder, cls, factory)


def node(mat, cls, x, y, fn=False, **props):
    n = (MEL.create_material_expression_in_function if fn else MEL.create_material_expression)(mat, cls, x, y)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def link(a, ao, b, bi):
    ok = MEL.connect_material_expressions(a, ao, b, bi)
    if not ok:
        raise RuntimeError(f"connect failed {a.get_name()}.{ao} -> {b.get_name()}.{bi}")


def author():
    tex_dir = HERE
    g8 = tex_dir / "T_Probe_G8_128.png"
    rgb = tex_dir / "T_Probe_RGB.png"
    png(g8, 64, 64, [bytes([128] * 64)] * 64, 0)
    png(rgb, 64, 64, [bytes([200, 100, 50] * 64)] * 64, 2)
    tg8, ig8 = import_png(g8, "T_Probe_G8_sRGB", True, unreal.TextureCompressionSettings.TC_GRAYSCALE)
    tg8l, ig8l = import_png(g8, "T_Probe_G8_Linear", False, unreal.TextureCompressionSettings.TC_GRAYSCALE)
    trgb, irgb = import_png(rgb, "T_Probe_RGB_BC7", True, unreal.TextureCompressionSettings.TC_BC7)
    tui, iui = import_png(rgb, "T_Probe_RGB_UI", True, unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    R["textures"] = {"g8_srgb": ig8, "g8_linear": ig8l, "rgb_bc7": irgb, "rgb_editoricon": iui}
    save()

    # ---- material function: out = In x Gain
    mf = new_asset("MF_Probe_Gain", DEST + "/Materials", unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew())
    fin = node(mf, unreal.MaterialExpressionFunctionInput, -400, 0, fn=True, input_name="In",
               input_type=unreal.FunctionInputType.FUNCTION_INPUT_VECTOR3, sort_priority=0)
    fg = node(mf, unreal.MaterialExpressionFunctionInput, -400, 200, fn=True, input_name="Gain",
              input_type=unreal.FunctionInputType.FUNCTION_INPUT_SCALAR, sort_priority=1)
    mul = node(mf, unreal.MaterialExpressionMultiply, -150, 0, fn=True)
    link(fin, "", mul, "A")
    link(fg, "", mul, "B")
    fout = node(mf, unreal.MaterialExpressionFunctionOutput, 100, 0, fn=True, output_name="Out")
    link(mul, "", fout, "")
    mf.set_editor_property("description", "probe")
    MEL.update_material_function(mf, None)
    EAL.save_loaded_asset(mf, only_if_is_dirty=False)

    # ---- master: BaseColor = switch(UseRGB, RGB, MF(Colour x G8, Gain))
    mat = new_asset("M_Probe_Master", DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    col = node(mat, unreal.MaterialExpressionVectorParameter, -1200, 0, parameter_name="Cloth Colour",
               default_value=unreal.LinearColor(1, 1, 1, 1), group="01 Colour", sort_priority=0,
               desc="probe colour")
    gain = node(mat, unreal.MaterialExpressionScalarParameter, -1200, 250, parameter_name="Detail Strength",
                default_value=1.0, slider_min=0.0, slider_max=1.5, group="02 Detail", sort_priority=0)
    tg = node(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1500, 0, parameter_name="Detail Map",
              texture=tg8, sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE, group="09 Textures")
    tc = node(mat, unreal.MaterialExpressionTextureSampleParameter2D, -1500, 400, parameter_name="Base Colour Map",
              texture=trgb, sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, group="09 Textures")
    m1 = node(mat, unreal.MaterialExpressionMultiply, -900, 0)
    link(col, "", m1, "A")
    link(tg, "R", m1, "B")
    call = node(mat, unreal.MaterialExpressionMaterialFunctionCall, -650, 0)
    call.set_material_function(mf) if hasattr(call, "set_material_function") else call.set_editor_property("material_function", mf)
    link(m1, "", call, "In")
    link(gain, "", call, "Gain")
    sw = node(mat, unreal.MaterialExpressionStaticSwitchParameter, -350, 0, parameter_name="Use Baked Colour Map",
              default_value=False, group="09 Textures")
    link(tc, "RGB", sw, "True")
    link(call, "Out", sw, "False")
    assert MEL.connect_material_property(sw, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = node(mat, unreal.MaterialExpressionConstant, -350, 300, r=0.8)
    assert MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    comp = MEL.recompile_material(mat)
    R["master_recompile_return"] = str(comp)
    EAL.save_loaded_asset(mat, only_if_is_dirty=False)
    try:
        st = MEL.get_statistics(mat)
        R["master_statistics"] = {p: str(st.get_editor_property(p)) for p in
                                  ("num_pixel_shader_instructions", "num_vertex_shader_instructions",
                                   "num_samplers", "num_pixel_texture_samples")}
    except Exception as exc:  # noqa
        R["master_statistics"] = repr(exc)
    R["master_params"] = {"vector": [str(n) for n in MEL.get_vector_parameter_names(mat)],
                          "scalar": [str(n) for n in MEL.get_scalar_parameter_names(mat)],
                          "texture": [str(n) for n in MEL.get_texture_parameter_names(mat)],
                          "static_switch": [str(n) for n in MEL.get_static_switch_parameter_names(mat)]}

    # ---- cloth shading model + shading-model switch, both through MakeMaterialAttributes (the Python
    #      MaterialProperty enum has no CustomData0 / ShadingModel member)
    def sub(label, fn):
        try:
            R[label] = fn()
        except Exception as exc:  # noqa
            R[label] = {"error": repr(exc), "trace": traceback.format_exc()[-800:]}
        save()

    R["material_property_names"] = [n for n in dir(unreal.MaterialProperty) if n.startswith("MP_")]

    def cloth():
        cm = new_asset("M_Probe_Cloth", DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
        cm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLOTH)
        cm.set_editor_property("use_material_attributes", True)
        mma = node(cm, unreal.MaterialExpressionMakeMaterialAttributes, -200, 0)
        names = [str(n) for n in MEL.get_material_expression_input_names(mma)]
        bc = node(cm, unreal.MaterialExpressionVectorParameter, -600, -200, parameter_name="Colour",
                  default_value=unreal.LinearColor(0.04, 0.035, 0.03, 1))
        fz = node(cm, unreal.MaterialExpressionVectorParameter, -600, 0, parameter_name="Sheen Colour",
                  default_value=unreal.LinearColor(0.2, 0.2, 0.2, 1))
        ca = node(cm, unreal.MaterialExpressionScalarParameter, -600, 200, parameter_name="Sheen Amount", default_value=1.0)
        res = {"mma_inputs": names}
        res["bc"] = MEL.connect_material_expressions(bc, "", mma, "BaseColor")
        sub_in = next((n for n in names if n.replace(" ", "").lower() == "subsurfacecolor"), None)
        cd_in = next((n for n in names if n.replace(" ", "").lower() == "customdata0"), None)
        res["fuzz"] = MEL.connect_material_expressions(fz, "", mma, sub_in) if sub_in else "no input"
        res["cloth"] = MEL.connect_material_expressions(ca, "", mma, cd_in) if cd_in else "no input"
        res["to_attributes"] = MEL.connect_material_property(mma, "", unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        res["recompile"] = str(MEL.recompile_material(cm))
        st = MEL.get_statistics(cm)
        res["ps_instructions"] = str(st.get_editor_property("num_pixel_shader_instructions"))
        EAL.save_loaded_asset(cm, only_if_is_dirty=False)
        return res

    def sm_switch():
        sm = new_asset("M_Probe_SMSwitch", DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
        sm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_FROM_MATERIAL_EXPRESSION)
        sm.set_editor_property("use_material_attributes", True)
        mma = node(sm, unreal.MaterialExpressionMakeMaterialAttributes, -200, 0)
        names = [str(n) for n in MEL.get_material_expression_input_names(mma)]
        s_def = node(sm, unreal.MaterialExpressionShadingModel, -800, 0,
                     shading_model=unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        s_cloth = node(sm, unreal.MaterialExpressionShadingModel, -800, 150,
                       shading_model=unreal.MaterialShadingModel.MSM_CLOTH)
        ssw = node(sm, unreal.MaterialExpressionStaticSwitchParameter, -500, 0, parameter_name="Cloth Sheen",
                   default_value=False)
        link(s_cloth, "", ssw, "True")
        link(s_def, "", ssw, "False")
        sm_in = next((n for n in names if n.replace(" ", "").lower() == "shadingmodel"), None)
        res = {"sm_input": sm_in, "connect": MEL.connect_material_expressions(ssw, "", mma, sm_in) if sm_in else None}
        res["to_attributes"] = MEL.connect_material_property(mma, "", unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        res["recompile"] = str(MEL.recompile_material(sm))
        st = MEL.get_statistics(sm)
        res["ps_instructions"] = str(st.get_editor_property("num_pixel_shader_instructions"))
        EAL.save_loaded_asset(sm, only_if_is_dirty=False)
        mi = new_asset("MI_Probe_SMCloth", DEST + "/MaterialInstances", unreal.MaterialInstanceConstant,
                       unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, sm)
        MEL.set_material_instance_static_switch_parameter_value(mi, "Cloth Sheen", True)
        MEL.update_material_instance(mi)
        st2 = MEL.get_statistics(mi)
        res["mi_ps_instructions"] = str(st2.get_editor_property("num_pixel_shader_instructions"))
        res["mi_switch_readback"] = MEL.get_material_instance_static_switch_parameter_value(mi, "Cloth Sheen")
        EAL.save_loaded_asset(mi, only_if_is_dirty=False)
        return res

    sub("cloth_material", cloth)
    sub("shading_model_switch_material", sm_switch)

    # ---- instances
    def mic(name, parent, colour=None, switch=None):
        mi = new_asset(name, DEST + "/MaterialInstances", unreal.MaterialInstanceConstant,
                       unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        if colour is not None:
            r1 = MEL.set_material_instance_vector_parameter_value(mi, "Cloth Colour", unreal.LinearColor(*colour, 1.0))
            R.setdefault("set_vector_return", []).append(r1)
        if switch is not None:
            r2 = MEL.set_material_instance_static_switch_parameter_value(mi, "Use Baked Colour Map", switch)
            R.setdefault("set_switch_return", []).append(r2)
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi, only_if_is_dirty=False)
        back = MEL.get_material_instance_vector_parameter_value(mi, "Cloth Colour")
        return mi, [back.r, back.g, back.b]

    mi_a, back_a = mic("MI_Probe_Tint", mat, colour=(1.0, 0.5, 0.25))
    mi_b, back_b = mic("MI_Probe_Baked", mat, switch=True)
    R["mic_readback"] = {"MI_Probe_Tint": back_a, "MI_Probe_Baked_switch": MEL.get_material_instance_static_switch_parameter_value(mi_b, "Use Baked Colour Map")}
    R["expected_basecolor"] = {"MI_Probe_Tint": [s2l(128) * c for c in (1.0, 0.5, 0.25)],
                               "MI_Probe_Baked": [s2l(200), s2l(100), s2l(50)],
                               "note": "G8 128 sRGB-decoded = 0.21586; linear would read 0.50196"}
    save()
    return mi_a, mi_b


def render(mi_a, mi_b):
    out = {"can_ever_render": None}
    try:
        out["rhi_note"] = unreal.SystemLibrary.get_rendering_detail_mode() if hasattr(unreal.SystemLibrary, "get_rendering_detail_mode") else "n/a"
    except Exception:  # noqa
        pass
    world = None
    for getter in (lambda: unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
                   lambda: unreal.EditorLevelLibrary.get_editor_world()):
        try:
            world = getter()
            if world:
                break
        except Exception as exc:  # noqa
            out.setdefault("world_errors", []).append(repr(exc))
    out["world"] = str(world.get_path_name()) if world else None
    if not world:
        return out
    # get_statistics() calls FMaterialResource::FinishCompilation() for GMaxRHIShaderPlatform: the only
    # Python-reachable way found to block until a material's (or a MIC permutation's) shaders exist
    t0 = time.time()
    stats = {}
    for label, m in (("tint", mi_a), ("baked", mi_b)):
        try:
            st = MEL.get_statistics(m)
            stats[label] = str(st.get_editor_property("num_pixel_shader_instructions"))
        except Exception as exc:  # noqa
            stats[label] = repr(exc)
    out["finish_compilation_sec"] = round(time.time() - t0, 2)
    out["mic_statistics"] = stats
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    results = {}
    actors = []
    try:
        for i, (label, mi) in enumerate((("tint", mi_a), ("baked", mi_b))):
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(i * 1000.0, 0, 0))
            actors.append(a)
            smc = a.get_editor_property("static_mesh_component")
            smc.set_static_mesh(plane)
            smc.set_material(0, mi)
            cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(i * 1000.0, 0, 300.0),
                                             unreal.Rotator(0, -90, 0))
            actors.append(cap)
            cc = cap.get_editor_property("capture_component2d")
            rt = unreal.RenderingLibrary.create_render_target2d(world, 64, 64, unreal.TextureRenderTargetFormat.RTF_RGBA32F)
            cc.set_editor_property("texture_target", rt)
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            cc.set_editor_property("ortho_width", 80.0)
            cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
            cc.set_editor_property("capture_every_frame", False)
            cc.set_editor_property("capture_on_movement", False)
            for attempt in range(3):
                cc.capture_scene()
                px = unreal.RenderingLibrary.read_render_target_raw_pixel(world, rt, 32, 32, False)
                results[f"{label}_attempt{attempt}"] = [px.r, px.g, px.b, px.a]
            area = unreal.RenderingLibrary.read_render_target_raw_pixel_area(world, rt, 16, 16, 47, 47, False)
            rs = [c.r for c in area]
            results[f"{label}_centre_area_r_min_max"] = [min(rs), max(rs), len(rs)]
            try:
                unreal.RenderingLibrary.export_render_target(world, rt, str(HERE), f"probe_{label}_basecolor")
                results[f"{label}_export"] = sorted(p.name for p in HERE.glob(f"probe_{label}_basecolor*"))
            except Exception as exc:  # noqa
                results[f"{label}_export"] = repr(exc)
        # a lit capture: directional light + final colour
        light = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(0, -60, 30))
        actors.append(light)
        cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -200, 200), unreal.Rotator(0, -45, 90))
        actors.append(cap)
        cc = cap.get_editor_property("capture_component2d")
        rt = unreal.RenderingLibrary.create_render_target2d(world, 128, 128, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_HDR)
        cc.capture_scene()
        px = unreal.RenderingLibrary.read_render_target_raw_pixel(world, rt, 64, 64, False)
        results["lit_hdr_centre"] = [px.r, px.g, px.b]
        try:
            unreal.RenderingLibrary.export_render_target(world, rt, str(HERE), "probe_lit_hdr")
            results["lit_export"] = sorted(p.name for p in HERE.glob("probe_lit_hdr*"))
        except Exception as exc:  # noqa
            results["lit_export"] = repr(exc)
    finally:
        for a in actors:
            try:
                eas.destroy_actor(a)
            except Exception:  # noqa
                pass
    out["captures"] = results
    return out


def reload_and_delete():
    out = {}
    for name in ("MI_Probe_Tint", "MI_Probe_Baked"):
        mi = unreal.load_asset(f"{DEST}/MaterialInstances/{name}")
        if mi is None:
            out[name] = "missing"
            continue
        v = MEL.get_material_instance_vector_parameter_value(mi, "Cloth Colour")
        out[name] = {"parent": mi.get_editor_property("parent").get_path_name(), "colour": [v.r, v.g, v.b],
                     "switch": MEL.get_material_instance_static_switch_parameter_value(mi, "Use Baked Colour Map")}
    for t in ("T_Probe_G8_sRGB", "T_Probe_G8_Linear", "T_Probe_RGB_BC7", "T_Probe_RGB_UI"):
        tex = unreal.load_asset(f"{DEST}/Textures/{t}")
        if tex:
            info = {"srgb": tex.get_editor_property("srgb"), "compression": str(tex.get_editor_property("compression_settings"))}
            try:
                info["memory_size"] = tex.blueprint_get_memory_size()
            except Exception as exc:  # noqa
                info["memory_size"] = repr(exc)
            out[t] = info
    out["deleted_directory"] = EAL.delete_directory(DEST)
    out["exists_after_delete"] = EAL.does_directory_exist(DEST)
    return out


if MODE == "author":
    R["argv_has_nullrhi"] = "-nullrhi" in unreal.SystemLibrary.get_command_line().lower() if hasattr(unreal.SystemLibrary, "get_command_line") else None
    mis = step("author", author)
    save()
    if mis and not R.get("argv_has_nullrhi"):
        step("render", lambda: render(*mis))
else:
    step("reload_and_delete", reload_and_delete)
save()
print("NP_PROBE_DONE", OUT)
