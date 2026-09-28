"""PASS D - what the buyer's physics body actually weighs, and the editor's own validation.

README section 5 tells the buyer 'the asset ships with Mass in KG overridden to 0.001'.
Passes B and C both read override_mass = False off the saved package.  This pass settles
what that means in kilogrammes by asking the engine for the body's mass directly, and
falls back to the convex hull's volume if no world is available in a commandlet.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealVerify2")
sys.path.insert(0, str(HERE))

import unreal                                                    # noqa: E402
import v2_common as C                                            # noqa: E402

OUT = HERE / "passD.json"


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        mesh = unreal.load_asset(C.ASSET)
        body = mesh.get_editor_property("body_setup")
        inst = body.get_editor_property("default_instance")
        rep["body_setup"] = {
            "override_mass": C.safe(lambda: bool(inst.get_editor_property("override_mass"))),
            "mass_in_kg_override": C.safe(lambda: float(inst.get_editor_property("mass_in_kg_override"))),
            "mass_scale": C.safe(lambda: float(inst.get_editor_property("mass_scale"))),
            "phys_material": C.safe(lambda: str(body.get_editor_property("phys_material"))),
            "readme_claim_kg": 0.001,
        }

        # a component is enough - no world needed for the mass Chaos would compute
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        for meth in ("get_mass", "calculate_mass"):
            rep[f"component_{meth}"] = C.safe(lambda m=meth: float(getattr(comp, m)()))
        rep["component_members_mass"] = [m for m in dir(comp)
                                         if "mass" in m.lower() and not m.startswith("_")]
        rep["bodysetup_members_mass"] = [m for m in dir(body)
                                         if "mass" in m.lower() or "volume" in m.lower()]

        # try a real world, if the commandlet has one
        try:
            sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = sub.spawn_actor_from_object(mesh, unreal.Vector(0, 0, 0))
            smc = actor.static_mesh_component
            smc.set_simulate_physics(True)
            rep["spawned_actor_mass_kg"] = C.safe(lambda: float(smc.get_mass()))
            rep["spawned"] = True
            sub.destroy_actor(actor)
        except Exception as exc:                                 # noqa: BLE001
            rep["spawn_error"] = f"{type(exc).__name__}: {exc}"[:300]

        # validation, with the 5.8 tuple return unpacked
        try:
            v = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
            s = unreal.ValidateAssetsSettings()
            s.set_editor_property("validation_usecase", unreal.DataValidationUsecase.MANUAL)
            data = [unreal.EditorAssetLibrary.find_asset_data(p) for p in
                    [C.ASSET] + [f"{C.TEXDEST}/T_PaperBomb_{x}" for x in C.TEX_INTENT]]
            out = v.validate_assets_with_settings(data, s)
            if isinstance(out, tuple):
                results = next((o for o in out if hasattr(o, "get_editor_property")), None)
                rep["validation_tuple_len"] = len(out)
                rep["validation_scalar"] = [o for o in out if not hasattr(o, "get_editor_property")]
            else:
                results = out
            if results is not None:
                rep["validation"] = {k: C.safe(lambda k=k: int(results.get_editor_property(k)))
                                     for k in ("num_checked", "num_valid", "num_invalid",
                                               "num_warnings", "num_unable_to_validate")}
        except Exception:
            rep["validation_error"] = traceback.format_exc()[-700:]
    except Exception:
        rep["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("PBV2_PASSD_DONE " + str(OUT))


main()
