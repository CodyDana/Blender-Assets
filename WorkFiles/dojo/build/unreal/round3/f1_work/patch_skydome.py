from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
p = ROOT / "Scripts/dojo/showcase/make_sky_clouds.py"
s = p.read_text()
s = s.replace("np.clip((base - thr) * 1.35 + 0.18 * detail, 0, 1)", "np.clip((base - thr) * 1.1 + 0.08 * detail, 0, 1)")
p.write_text(s)

p = ROOT / "Scripts/dojo/unreal/dj_sc_level.py"
s = p.read_text()
NEW = r'''SKY_TEX_SRC = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\DojoKit\Showcase\Textures\T_DJS_SunsetClouds.png")
SKY_DIR = "/Game/DojoKit/Showcase"
SKY_MAT = SKY_DIR + "/Materials/M_DJS_SkyClouds"


def sky_dome(cfg):
    """Round 3 fix f1: the painted sunset cloud layer (showcase/make_sky_clouds.py) on the engine's SM_SkySphere
    (radius 40.96 m, scaled), an unlit translucent two-sided material that maps the texture by the view direction from
    the dome centre (u = atan2(y, x) / 2 pi + 0.5, v = 1 - asin(z) / (pi / 2)), so the mesh UVs do not matter. The
    SkyAtmosphere shows through the gaps. Showcase dressing only: NoCollision, no shadows."""
    MEL = unreal.MaterialEditingLibrary
    task = unreal.AssetImportTask()
    for k, v in (("filename", str(SKY_TEX_SRC)), ("destination_path", SKY_DIR + "/Textures"),
                 ("destination_name", "T_DJS_SunsetClouds"), ("automated", True), ("replace_existing", True),
                 ("save", True)):
        task.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.load_asset(SKY_DIR + "/Textures/T_DJS_SunsetClouds")
    setp(tex, "srgb", True)
    setp(tex, "address_y", unreal.TextureAddress.TA_CLAMP)
    setp(tex, "lod_group", unreal.TextureGroup.TEXTUREGROUP_SKYBOX)
    setp(tex, "never_stream", True)
    EAL.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    mat = unreal.load_asset(SKY_MAT)
    if mat is None:
        d, n = SKY_MAT.rsplit("/", 1)
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(mat)
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    setp(mat, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    setp(mat, "two_sided", True)
    fog_off = []
    for k in ("use_translucency_vertex_fog", "apply_fogging"):
        try:
            mat.set_editor_property(k, False)
            fog_off.append(k)
        except Exception:  # noqa: BLE001
            pass

    def node(cls, x, y, **kw):
        n = MEL.create_material_expression(mat, cls, x, y)
        for k, v in kw.items():
            n.set_editor_property(k, v)
        return n

    wp = node(unreal.MaterialExpressionWorldPosition, -1600, 0)
    op = node(unreal.MaterialExpressionObjectPositionWS, -1600, 200)
    sub = node(unreal.MaterialExpressionSubtract, -1400, 100)
    MEL.connect_material_expressions(wp, "", sub, "A")
    MEL.connect_material_expressions(op, "", sub, "B")
    nrm = node(unreal.MaterialExpressionNormalize, -1250, 100)
    MEL.connect_material_expressions(sub, "", nrm, "")
    mx = node(unreal.MaterialExpressionComponentMask, -1100, 0, r=True, g=False, b=False, a=False)
    my = node(unreal.MaterialExpressionComponentMask, -1100, 100, r=False, g=True, b=False, a=False)
    mz = node(unreal.MaterialExpressionComponentMask, -1100, 200, r=False, g=False, b=True, a=False)
    for m_ in (mx, my, mz):
        MEL.connect_material_expressions(nrm, "", m_, "")
    at = node(unreal.MaterialExpressionArctangent2, -950, 50)
    MEL.connect_material_expressions(my, "", at, "Y")
    MEL.connect_material_expressions(mx, "", at, "X")
    u1 = node(unreal.MaterialExpressionMultiply, -800, 50, const_b=1.0 / (2.0 * math.pi))
    MEL.connect_material_expressions(at, "", u1, "A")
    u2 = node(unreal.MaterialExpressionAdd, -650, 50, const_b=0.5)
    MEL.connect_material_expressions(u1, "", u2, "A")
    zs = node(unreal.MaterialExpressionSaturate, -950, 200)
    MEL.connect_material_expressions(mz, "", zs, "")
    asn = node(unreal.MaterialExpressionArcsine, -800, 200)
    MEL.connect_material_expressions(zs, "", asn, "")
    v1 = node(unreal.MaterialExpressionMultiply, -650, 200, const_b=-2.0 / math.pi)
    MEL.connect_material_expressions(asn, "", v1, "A")
    v2 = node(unreal.MaterialExpressionAdd, -500, 200, const_b=1.0)
    MEL.connect_material_expressions(v1, "", v2, "A")
    uv = node(unreal.MaterialExpressionAppendVector, -400, 100)
    MEL.connect_material_expressions(u2, "", uv, "A")
    MEL.connect_material_expressions(v2, "", uv, "B")
    ts = node(unreal.MaterialExpressionTextureSample, -250, 100, texture=tex,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
              mip_value_mode=unreal.TextureMipValueMode.TMVM_MIP_LEVEL, const_mip_value=0)
    MEL.connect_material_expressions(uv, "", ts, "UVs")
    inten = node(unreal.MaterialExpressionScalarParameter, -250, 350, parameter_name="Intensity",
                 default_value=float(cfg.get("intensity", 1.0)))
    em = node(unreal.MaterialExpressionMultiply, 0, 100)
    MEL.connect_material_expressions(ts, "RGB", em, "A")
    MEL.connect_material_expressions(inten, "", em, "B")
    opm = node(unreal.MaterialExpressionScalarParameter, -250, 450, parameter_name="OpacityMult",
               default_value=float(cfg.get("opacity", 1.0)))
    op2 = node(unreal.MaterialExpressionMultiply, 0, 300)
    MEL.connect_material_expressions(ts, "A", op2, "A")
    MEL.connect_material_expressions(opm, "", op2, "B")
    MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(op2, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    EAL.save_asset(SKY_MAT, only_if_is_dirty=False)
    c = cfg.get("centre", (22.0, 18.0, 0.0))
    sc = float(cfg.get("radius_m", 2400.0)) / 40.96
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(c)), rot())
    a.set_actor_scale3d(V((sc, sc, sc)))
    smc = a.static_mesh_component
    smc.set_static_mesh(unreal.load_asset("/Engine/EngineSky/SM_SkySphere"))
    smc.set_material(0, mat)
    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    smc.set_collision_profile_name("NoCollision")
    setp(smc, "cast_shadow", False)
    setp(smc, "affect_distance_field_lighting", False)
    return {"material": SKY_MAT, "texture": tex.get_path_name(), "centre_m": list(c), "radius_m": round(sc * 40.96, 2),
            "intensity": cfg.get("intensity", 1.0), "opacity": cfg.get("opacity", 1.0), "fog_off": fog_off,
            "actor": tag(a, "SkyClouds_Dome", "Dojo/Lighting", "DJ_SkyDome").get_actor_label()}


def environment():'''
assert "def environment():" in s and "SKY_TEX_SRC" not in s
s = s.replace("def environment():", NEW, 1)
old = "    a = EAS.spawn_actor_from_class(unreal.SkyLight,"
assert old in s
s = s.replace(old, "    if S.SKY_DOME:\n        env[\"sky_dome\"] = sky_dome(S.SKY_DOME)\n" + old, 1)
p.write_text(s)

p = ROOT / "Scripts/dojo/unreal/dj_sc_common.py"
s = p.read_text()
if "SKY_DOME" not in s:
    s = s.replace("CAPTURE_CVARS = tuple(", 'SKY_DOME = _LOOK.ENV.get("sky_dome")\nCAPTURE_CVARS = tuple(', 1)
p.write_text(s)

p = ROOT / "Scripts/dojo/showcase/look_r3.py"
s = p.read_text()
s += '''# L4: UE 5.8's VolumetricCloud does not show in the SceneCapture2D stills (L3 / L3b: coverage 0.9, the Cloud show flag,
# r.VolumetricRenderTarget 0: no cloud), so the cloud layer is our own painted dome (make_sky_clouds.py + sky_dome())
ENV["clouds"] = None
ENV["capture_cvars"] = ()
ENV["capture_show_flags"] = ()
ENV["sky_dome"] = {"centre": (22.0, 18.0, 0.0), "radius_m": 2400.0, "intensity": 1.0, "opacity": 1.0,
                   "coverage": 0.46, "seed": 7}
'''
p.write_text(s)
print("patched")
