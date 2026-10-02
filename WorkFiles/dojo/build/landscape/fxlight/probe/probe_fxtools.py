"""Probe (nothing saved): the DojoFXTools helper on an in-memory duplicate of the engine's FountainLightweight system."""
import json
import unreal
from pathlib import Path

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/landscape/fxlight/probe/probe_fxtools.json")
L = unreal.DojoFXToolsLibrary
R = {}
try:
    src = unreal.load_asset("/Niagara/DefaultAssets/Templates/Systems/FountainLightweight")
    dup = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset("NS_DKF_ProbeTmp", "/Game/DojoKit/FX/ProbeTmp", src)
    R["dup"] = str(dup)
    R["inner"] = list(L.list_inner(dup))
    em = L.find_inner(dup, "NiagaraStatelessEmitter", "")
    R["emitter_props"] = list(L.list_props(em))
    R["system_props"] = [p[:600] for p in L.list_props(dup) if p.split("|")[0] in ("EmitterHandles", "EffectType", "bFixedBounds", "FixedBounds", "WarmupTime")]
    for cls in ("NiagaraStatelessModule_InitializeParticle", "NiagaraStatelessModule_ShapeLocation",
                "NiagaraStatelessModule_SubUVAnimation", "NiagaraStatelessModule_MeshIndex",
                "NiagaraStatelessModule_ScaleColor", "NiagaraStatelessModule_CurlNoiseForce"):
        m = L.find_inner(dup, cls, "")
        R[cls] = list(L.list_props(m))
    m = L.find_inner(dup, "NiagaraStatelessModule_InitializeParticle", "")
    R["set_lifetime"] = L.set_prop(m, "LifetimeDistribution", "(Mode=UniformRange,ChannelConstantsAndRanges=(14.000000,20.000000))")
    R["get_lifetime"] = L.get_prop(m, "LifetimeDistribution")
    R["set_lifetime_mode"] = L.set_prop(m, "LifetimeDistribution.Mode", "UniformConstant")
    R["get_lifetime2"] = L.get_prop(m, "LifetimeDistribution")
    r = L.replace_array_with_new(em, "RendererProperties", unreal.load_class(None, "/Script/Niagara.NiagaraMeshRendererProperties"))
    R["mesh_renderer"] = str(r)
    R["mesh_renderer_props"] = list(L.list_props(r))
    R["sprite_props"] = list(L.list_props(L.find_inner(dup, "NiagaraSpriteRendererProperties", "")))
    R["finalize"] = L.finalize_system(dup)
except Exception as exc:  # noqa: BLE001
    import traceback
    R["error"] = traceback.format_exc()
OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
unreal.log("DJ_STEP_DONE probe_fxtools passed=%s" % ("error" not in R))
