"""INDEPENDENT pass C (fresh commandlet, real RHI): textures fully built (sizes, formats where exposed), tassel
constraints, per-LOD geometry exported back out of the engine to FBX (triangles counted offline), and base-colour
captures of the tint materials vs the BC materials (does the recolour law's default reproduce the baked colour?).
Nothing is saved."""
import json, os, time, traceback
from pathlib import Path
import unreal

OUT = Path(os.environ["IV_OUT"])
DEST = os.environ["IV_DEST"]
res = {"t0": time.time()}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def dump():
    (OUT / "ivC.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


try:
    res["compile_api"] = [x for x in dir(unreal) if "ompil" in x][:40]
    for cmd in ("Editor.AsyncTextureCompilation 0", "r.Streaming.PoolSize 3000", "r.TextureStreaming 0"):
        unreal.SystemLibrary.execute_console_command(None, cmd)
    texs = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p))
        texs[t.get_name()] = t
    for fn in ("finish_all_compilation",):
        for cls in ("AssetCompilingManager", "TextureCompilingManager"):
            c = getattr(unreal, cls, None)
            if c is not None and hasattr(c, fn):
                res.setdefault("finish", []).append(safe(lambda: getattr(c, fn)()))
    time.sleep(0.1)
    res["texture_api"] = sorted({x for t in list(texs.values())[:1] for x in dir(t)
                                 if any(k in x.lower() for k in ("format", "mip", "resource", "size", "platform", "alpha"))})
    info = {}
    for n, t in sorted(texs.items()):
        d = {"size": [t.blueprint_get_size_x(), t.blueprint_get_size_y()]}
        for k in ("get_num_mips", "get_pixel_format", "get_surface_width", "get_resource_size_bytes", "has_alpha_channel"):
            if hasattr(t, k):
                d[k] = str(safe(lambda: getattr(t, k)()))
        info[n] = d
    res["textures_built"] = info
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    rt = {}
    for n in texs:
        ad = ar.get_asset_by_object_path(f"{DEST}/Textures/{n}.{n}")
        rt[n] = {k: str(safe(lambda: ad.get_tag_value(k))) for k in ("Dimensions", "Format", "HasAlphaChannel", "SRGB", "CompressionSettings", "MipGenSettings", "LODGroup", "NumMips", "ResourceSize", "AlphaCoverage")}
    res["texture_registry_tags"] = rt
    dump()
    # ---------------------------------------------------------------- constraints
    pa = unreal.load_asset(f"{DEST}/PHYS_Fan_Tassel_IV")
    cons = []
    CL = getattr(unreal, "ConstraintInstanceBlueprintLibrary", None)
    res["constraint_lib_api"] = [x for x in dir(CL) if not x.startswith("_")][:80] if CL else None
    for acc in (pa.get_constraints(True) if pa else []):
        r = {}
        if CL:
            r["bodies"] = str(safe(lambda: CL.get_attached_body_names(acc)))
            for fn in ("get_angular_limits", "get_linear_limits", "get_angular_swing1_limit", "get_angular_swing2_limit",
                       "get_angular_twist_limit", "get_projection_params", "get_disable_collsion", "get_disable_collision"):
                if hasattr(CL, fn):
                    r[fn] = str(safe(lambda: getattr(CL, fn)(acc)))
        cons.append(r)
    res["tassel_constraints"] = cons
    dump()
    # ---------------------------------------------------------------- export the engine's meshes back to FBX (all LODs)
    ex = OUT / "export"
    ex.mkdir(parents=True, exist_ok=True)
    for n in ("SK_Fan", "SK_Fan_Tassel"):
        task = unreal.AssetExportTask()
        task.set_editor_property("object", unreal.load_asset(f"{DEST}/{n}"))
        task.set_editor_property("filename", str(ex / f"{n}_from_ue.fbx"))
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        opt = unreal.FbxExportOption()
        safe(lambda: opt.set_editor_property("level_of_detail", True))
        safe(lambda: opt.set_editor_property("ascii", False))
        task.set_editor_property("options", opt)
        res.setdefault("export", {})[n] = bool(unreal.Exporter.run_asset_export_task(task))
    dump()
    # ---------------------------------------------------------------- base colour: tint law vs baked BC (front view, open)
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    RL = unreal.RenderingLibrary
    ML = unreal.MathLibrary
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    mesh = unreal.load_asset(f"{DEST}/SK_Fan")
    tmesh = unreal.load_asset(f"{DEST}/SK_Fan_Tassel")
    pose = unreal.load_asset(f"{DEST}/A_Fan_OpenPose")
    MEL = unreal.MaterialEditingLibrary
    mats = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Materials", recursive=False, include_folder=False):
        m = unreal.load_asset(str(p))
        MEL.recompile_material(m)
        mats[m.get_name()] = m
    for t in texs.values():
        safe(lambda: t.set_editor_property("never_stream", True))
        safe(lambda: t.update_resource())
    rdir = OUT / "renders_c"
    rdir.mkdir(parents=True, exist_ok=True)
    spawned = []
    try:
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), ML.make_rot_from_x(unreal.Vector(0.3, 0.5, -1.0)))
        la.get_editor_property("directional_light_component").set_editor_property("intensity", 5.0)
        spawned.append(la)
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.35, -8.5, 80.0),
                                         ML.make_rot_from_xz(unreal.Vector(0, 0, -1), unreal.Vector(0, -1, 0)))
        spawned.append(cam)
        cc = cam.get_editor_property("capture_component2d")
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", 42.0)
        safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        rt16 = RL.create_render_target2d(w, 768, 768, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        rt8 = RL.create_render_target2d(w, 768, 768, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        shots = []
        for label, ml, tm_ in (("tint", ["M_IV_Tint_Leaf", "M_IV_Tint_Sticks", "M_IV_BC_Rivet"], "M_IV_Tint_Tassel"),
                               ("bc", ["M_IV_BC_Leaf", "M_IV_BC_Sticks", "M_IV_BC_Rivet"], "M_IV_BC_Tassel"),
                               ("dbg", ["M_IV_Dbg_Leaf", "M_IV_Dbg_Sticks", "M_IV_Dbg_Rivet"], "M_IV_Dbg_Tassel")):
            a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
            c = a.get_editor_property("skeletal_mesh_component")
            c.set_skinned_asset_and_update(mesh)
            c.override_animation_data(pose, False, False, 0.0, 0.0)
            for i, m in enumerate(ml):
                c.set_material(i, mats[m])
            ta = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
            tc = ta.get_editor_property("skeletal_mesh_component")
            tc.set_skinned_asset_and_update(tmesh)
            tc.set_material(0, mats[tm_])
            tc.attach_to_component(c, "Tassel", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                   unreal.AttachmentRule.KEEP_WORLD, False)
            for src, rt, ext in ((unreal.SceneCaptureSource.SCS_BASE_COLOR, rt16, "exr"),
                                 (unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR, rt8, "png")):
                cc.set_editor_property("capture_source", src)
                cc.set_editor_property("texture_target", rt)
                for _ in range(4):
                    cc.capture_scene()
                nm = f"{label}_{str(src).split('.')[-1].split(':')[0]}.{ext}"
                RL.export_render_target(w, rt, str(rdir), nm)
                shots.append(nm)
            EAS.destroy_actor(ta)
            EAS.destroy_actor(a)
        res["shots"] = shots
        res["textures_after_render"] = {n: [t.blueprint_get_size_x(), t.blueprint_get_size_y()] for n, t in texs.items()}
    finally:
        for a in spawned:
            safe(lambda: EAS.destroy_actor(a))
    res["status"] = "ok"
except Exception:  # noqa
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("IV_PASS_C_DONE status=" + res["status"])
