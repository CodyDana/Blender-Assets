"""PASS C - a THIRD fresh process: the accessors 5.8.2 actually exposes, plus validation.

Everything here is read off the packages pass A saved; pass C never imports anything.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealVerify2")
sys.path.insert(0, str(HERE))

import unreal                                                    # noqa: E402
import v2_common as C                                            # noqa: E402

OUT = HERE / "passC.json"


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        mesh = unreal.load_asset(C.ASSET)
        sub = C.sme()

        rep["lod_screen_sizes"] = [round(float(v), 7) for v in sub.get_lod_screen_sizes(mesh)]
        rep["is_lod_screen_size_auto_computed"] = C.safe(
            lambda: bool(mesh.is_lod_screen_size_auto_computed()))
        rep["sidecar_screen_sizes"] = C.EXP_SCREEN
        rep["screen_sizes_match_sidecar"] = all(
            abs(a - b) < 1e-6 for a, b in zip(rep["lod_screen_sizes"], C.EXP_SCREEN))

        b = mesh.get_bounds()
        rep["bounds"] = {
            "origin_cm": C.vec(b.origin),
            "box_extent_cm": C.vec(b.box_extent),
            "sphere_radius_cm": round(float(b.sphere_radius), 6),
        }
        box = mesh.get_bounding_box()
        rep["bounding_box_cm"] = {"min": C.vec(box.min), "max": C.vec(box.max),
                                  "size": [round(box.max.x - box.min.x, 5),
                                           round(box.max.y - box.min.y, 5),
                                           round(box.max.z - box.min.z, 5)]}

        # material assignment per LOD section
        mats = []
        for i in range(mesh.get_num_lods()):
            for s in range(mesh.get_num_sections(i)):
                mats.append({"lod": i, "section": s,
                             "material_slot": C.safe(
                                 lambda i=i, s=s: str(sub.get_lod_material_slot(mesh, i, s)))})
        rep["lod_section_materials"] = mats
        rep["static_materials"] = [
            {"slot": C.safe(lambda m=m: str(m.material_slot_name)),
             "material": C.safe(lambda m=m: (m.material_interface.get_path_name()
                                             if m.material_interface else None)),
             "members": [a for a in dir(m) if not a.startswith("_")]}
            for m in mesh.get_editor_property("static_materials")]

        # physics, in full
        body = mesh.get_editor_property("body_setup")
        inst = body.get_editor_property("default_instance")
        rep["physics"] = {
            "collision_trace_flag": str(body.get_editor_property("collision_trace_flag")),
            "override_mass": C.safe(lambda: bool(inst.get_editor_property("override_mass"))),
            "mass_in_kg_override": C.safe(lambda: float(inst.get_editor_property("mass_in_kg_override"))),
            "simulate_physics": C.safe(lambda: bool(inst.get_editor_property("simulate_physics"))),
            "physics_material_override": C.safe(
                lambda: str(body.get_editor_property("phys_material"))),
            "readme_claims_mass_kg": 0.001,
        }

        # textures, with the built size (what actually reaches the GPU)
        tex = {}
        for suffix in C.TEX_INTENT:
            t = unreal.load_asset(f"{C.TEXDEST}/T_PaperBomb_{suffix}")
            if not isinstance(t, unreal.Texture2D):
                tex[suffix] = {"error": "missing"}
                continue
            built = C.safe(lambda t=t: t.blueprint_get_built_texture_size())
            tex[suffix] = {
                "srgb": t.get_editor_property("srgb"),
                "compression_settings": str(t.get_editor_property("compression_settings")),
                "mip_gen_settings": str(t.get_editor_property("mip_gen_settings")),
                "lod_group": str(t.get_editor_property("lod_group")),
                "never_stream": t.get_editor_property("never_stream"),
                "source_size": C.safe(lambda t=t: [int(t.blueprint_get_size_x()),
                                                   int(t.blueprint_get_size_y())]),
                "built_texture_size": C.safe(
                    lambda bu=built: [int(bu.x), int(bu.y)] if hasattr(bu, "x") else str(bu)),
                "memory_size_mb": C.safe(
                    lambda t=t: round(float(t.blueprint_get_memory_size(
                        unreal.TextureMemoryUsageMode.ACTUAL)) / (1024 * 1024), 4)),
                "num_mips_expected_full_chain": 12,
            }
        rep["textures"] = tex

        # the editor's own asset validation
        try:
            v = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
            settings = unreal.ValidateAssetsSettings()
            settings.set_editor_property("validation_usecase", unreal.DataValidationUsecase.MANUAL)
            settings.set_editor_property("show_if_no_failures", True)
            data = [unreal.EditorAssetLibrary.find_asset_data(p) for p in
                    [C.ASSET] + [f"{C.TEXDEST}/T_PaperBomb_{s}" for s in C.TEX_INTENT]]
            results = v.validate_assets_with_settings(data, settings)
            # 5.8.2 returns (int, ValidateAssetsResults) from this call in some
            # builds and the struct alone in others; take whichever carries the
            # counters rather than assuming.
            res = results
            if isinstance(results, tuple):
                res = next((r for r in results
                            if hasattr(r, "get_editor_property")), results[-1])
            def _n(name):
                try:
                    return int(res.get_editor_property(name))
                except Exception:
                    return -1
            rep["validation"] = {
                "num_checked": _n("num_checked"),
                "num_valid": _n("num_valid"),
                "num_invalid": _n("num_invalid"),
                "num_warnings": _n("num_warnings"),
                "num_unable_to_validate": _n("num_unable_to_validate"),
                "raw_type": type(results).__name__,
            }
        except Exception:
            rep["validation_error"] = traceback.format_exc()[-800:]
    except Exception:
        rep["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("PBV2_PASSC_DONE " + str(OUT))


main()
