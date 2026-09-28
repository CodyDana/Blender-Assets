"""UnrealCheck5 pass 4 (diagnostic): the mass Unreal derives for the saved asset with no override.

UPrimitiveComponent.CalculateMass on an unregistered StaticMeshComponent uses the mesh's
BodySetup (hull volume x default physical material density, RaiseMassToPower). Compares it
with the report's physics block. Read-only: nothing is saved. Runs once for both forms.
"""
import json
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck5"
out = {"engine": unreal.SystemLibrary.get_engine_version()}
for form, mesh_name in (("eight_point", "SM_Shuriken_EightPoint"), ("four_point", "SM_Shuriken_FourPoint")):
    rec = {}
    try:
        mesh = unreal.load_asset(f"/Game/ShurikenCheck5/Verify/{mesh_name}")
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        rec["component_mass_api"] = sorted(n for n in dir(comp) if "mass" in n.lower())
        rec["bodysetup_mass_api"] = sorted(n for n in dir(mesh.get_editor_property("body_setup")) if "mass" in n.lower())
        for api in ("calculate_mass", "get_mass"):
            if hasattr(comp, api):
                try:
                    rec[api + "_kg"] = round(float(getattr(comp, api)()), 6)
                except Exception as exc:  # noqa: BLE001
                    rec[api + "_kg"] = f"{type(exc).__name__}: {exc}"[:120]
        body = mesh.get_editor_property("body_setup")
        for key in ("mass_scale", "phys_material"):
            try:
                val = body.get_editor_property(key)
                rec[key] = val.get_path_name() if hasattr(val, "get_path_name") else val
            except Exception as exc:  # noqa: BLE001
                rec[key] = f"{type(exc).__name__}: {exc}"[:120]
        report = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{form}_report.json").read_text(encoding="utf-8"))
        rec["report_physics"] = report.get("physics")
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"
    out[form] = rec
(HERE / "mass_diag.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
unreal.log("PASS4_DONE")
