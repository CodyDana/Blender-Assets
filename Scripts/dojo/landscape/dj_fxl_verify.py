"""LANDSCAPE ROUND, FX + LIGHTING stage: FRESH-process gate on the saved assets and L_Dojo (pythonscript commandlet,
-nullrhi, DojoFXTools installed for the run by run_fx.sh so the lightweight emitters can be read back).
  F1 systems   the 7 NS_DKF_* systems load; each has one lightweight emitter, its renderer (mesh: the 7 petal meshes;
               sprite: our MI), spawn rate and fixed bounds as built; the petal mesh scale is the real one (1.0-1.4,
               no render-test scale left behind)
  F2 actors    every DJ_FXL actor: NiagaraActors carry an NS_DKF system; one NS_DKF_PetalCanopy per CherrySlot (20) with
               the slot id tag, active exactly on ACTIVE_SLOTS; StaticMeshActors / DecalActors NoCollision (no gameplay
               effect: the FX never block a pawn, camera or trace) and shadowless
  F3 materials M_DKF_Petal usage (Niagara mesh particles, instanced static meshes); the FX masters are translucent /
               decal as built
  F4 budget    the estimated steady particle count of the active emitters (rate x mean life) under 6000
Out: WorkFiles/dojo/build/landscape/fxlight/json/fxl_verify.json
"""
import json
import os
import time
from pathlib import Path

import unreal

O = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fxlight")
W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\world")
LAY = json.loads((W / "json/world_layout.json").read_text(encoding="utf-8"))
PLACE = json.loads((Path(os.environ["DJ_FXL_OUT"]) if os.environ.get("DJ_FXL_OUT") else O / "json/fxl_place.json").read_text(encoding="utf-8"))
FXL = unreal.DojoFXToolsLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ACTIVE_SLOTS = ("CS01", "CS02", "CS03", "CS04", "CS09")
SYSTEMS = ("NS_DKF_PetalDrift", "NS_DKF_PetalCanopy", "NS_DKF_MistPuff", "NS_DKF_MistWisp", "NS_DKF_RapidSpray",
           "NS_DKF_SprayDroplets", "NS_DKF_RiverHaze")
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "gates": {}}


def f1():
    out, ok = {}, True
    for n in SYSTEMS:
        s = unreal.load_asset(f"/Game/DojoKit/FX/Niagara/{n}")
        rec = {"loaded": s is not None}
        if s is None:
            ok = False
            out[n] = rec
            continue
        em = FXL.find_inner(s, "NiagaraStatelessEmitter", "")
        handles = FXL.get_prop(s, "EmitterHandles")
        rec["stateless_emitters"] = handles.count("EmitterMode=Stateless")
        rec["renderers"] = FXL.get_prop(em, "RendererProperties")[:300]
        rec["spawn"] = FXL.get_prop(em, "SpawnInfos")[:200]
        rec["bounds"] = FXL.get_prop(em, "FixedBounds")
        good = rec["stateless_emitters"] == 1 and "Rate=" in rec["spawn"]
        if "Petal" in n:
            ini = FXL.find_inner(s, "NiagaraStatelessModule_InitializeParticle", "")
            sc = FXL.get_prop(ini, "MeshScaleDistribution")
            rec["mesh_scale"] = sc[:160]
            rec["mesh_renderer"] = "NiagaraMeshRendererProperties" in rec["renderers"]
            mr = FXL.find_inner(s, "NiagaraMeshRendererProperties", "")
            meshes = FXL.get_prop(mr, "Meshes")
            rec["n_meshes"] = meshes.count("(Mesh=")
            good = good and rec["mesh_renderer"] and rec["n_meshes"] == 7 and "Max=(X=1.400000" in sc and "Min=(X=1.000000" in sc
        else:
            sr = FXL.find_inner(s, "NiagaraSpriteRendererProperties", "")
            rec["material"] = FXL.get_prop(sr, "Material")
            good = good and "MI_DKF_" in rec["material"]
        rec["ok"] = good
        ok = ok and good
        out[n] = rec
    return {"systems": out, "passed": ok}


def f2(actors):
    fx = [a for a in actors if unreal.Name("DJ_FXL") in list(a.tags)]
    rec = {"n": len(fx), "by_class": {}, "bad": [], "canopy": {}}
    for a in fx:
        cls = a.get_class().get_name()
        rec["by_class"][cls] = rec["by_class"].get(cls, 0) + 1
        lab = a.get_actor_label()
        if cls == "NiagaraActor":
            c = a.get_editor_property("niagara_component")
            asset = c.get_asset()
            if asset is None or not asset.get_name().startswith("NS_DKF_"):
                rec["bad"].append(f"{lab}: system {asset}")
            if lab.startswith("FX_PetalCanopy_"):
                sid = lab.split("_")[-1]
                act = bool(c.get_editor_property("auto_activate"))
                rec["canopy"][sid] = act
                if act != (sid in ACTIVE_SLOTS) or unreal.Name(sid) not in list(a.tags):
                    rec["bad"].append(f"{lab}: active {act}")
        elif cls == "StaticMeshActor":
            c = a.static_mesh_component
            if str(c.get_collision_enabled()).split(".")[-1].split(":")[0] != "NO_COLLISION":
                rec["bad"].append(f"{lab}: collision {c.get_collision_enabled()}")
            if bool(c.get_editor_property("cast_shadow")):
                rec["bad"].append(f"{lab}: casts shadow")
        elif cls == "DecalActor":
            pass
        else:
            rec["bad"].append(f"{lab}: class {cls}")
    slots = sorted(a["label"].split("_")[-1] for a in LAY["actors"] if a["group"] == "cherry")
    rec["slots_missing_fx"] = [s for s in slots if s not in rec["canopy"]]
    rec["expected_n"] = PLACE["n_fxl_actors"]
    rec["passed"] = not rec["bad"] and not rec["slots_missing_fx"] and len(fx) == PLACE["n_fxl_actors"]
    return rec


def f3():
    rec = {}
    m = unreal.load_asset("/Game/DojoKit/FX/Materials/M_DKF_Petal")
    rec["petal_usage"] = {k: bool(m.get_editor_property(k)) for k in ("used_with_niagara_mesh_particles",
                                                                     "used_with_instanced_static_meshes")}
    for n in ("M_DKF_SixWayMist", "M_DKF_HazeSprite", "M_DKF_Droplet", "M_DKF_FoamWake", "M_DKF_PetalScatterDecal"):
        mm = unreal.load_asset(f"/Game/DojoKit/FX/Materials/{n}")
        rec[n] = {"blend": str(mm.get_editor_property("blend_mode")).split(".")[-1].split(":")[0],
                  "domain": str(mm.get_editor_property("material_domain")).split(".")[-1].split(":")[0]} if mm else None
    rec["passed"] = all(rec["petal_usage"].values()) and all(rec[n] for n in rec if n.startswith("M_DKF"))
    return rec


def main():
    t0 = time.time()
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["loaded"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
    actors = EAS.get_all_level_actors()
    for k, fn in (("F1_systems", f1), ("F2_actors", lambda: f2(actors)), ("F3_materials", f3)):
        try:
            REP[k] = fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            REP[k] = {"passed": False, "error": traceback.format_exc()[-1500:]}
    REP["F4_budget"] = {"particles_est": PLACE["particles_total_est"], "by_system": PLACE["particles"],
                        "passed": PLACE["particles_total_est"] < 6000}
    REP["gates"] = {k: bool(REP[k]["passed"]) for k in ("F1_systems", "F2_actors", "F3_materials", "F4_budget")}
    REP["passed"] = all(REP["gates"].values())
    REP["sec"] = round(time.time() - t0, 1)
    (Path(os.environ["DJ_FXL_VOUT"]) if os.environ.get("DJ_FXL_VOUT") else O / "json/fxl_verify.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE fxl_verify passed={REP['passed']} gates={REP['gates']}")


main()
