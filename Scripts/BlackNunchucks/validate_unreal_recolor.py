"""Fresh-process reload and GPU evaluation of the saved recolor graph."""
from pathlib import Path
import json
import sys
import traceback

import unreal

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "WorkFiles/BlackNunchucks/RecolorUnreal"
sys.path.insert(0, str(ROOT / "Scripts/BlackNunchucks"))
import unreal_recolor_setup as setup

M = unreal.MaterialEditingLibrary
E = unreal.EditorAssetLibrary
R = unreal.RenderingLibrary


def gpu_check():
    # Only the verification clone changes to unlit. Its emissive output is the
    # exact persisted master BaseColor subgraph, with all connections preserved.
    source = setup.DEST + "/Materials/" + setup.MASTER_NAME
    path = "/Game/RecolorVerification/M_BaseColor_TestOnly"
    if E.does_asset_exist(path):
        E.delete_asset(path)
    clone = E.duplicate_asset(source, path)
    color_node = M.get_material_property_input_node(clone, unreal.MaterialProperty.MP_BASE_COLOR)
    pin = M.get_material_property_input_node_output_name(clone, unreal.MaterialProperty.MP_BASE_COLOR)
    assert color_node is not None
    clone.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    assert M.connect_material_property(color_node, pin, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_NORMAL,
                 unreal.MaterialProperty.MP_ROUGHNESS, unreal.MaterialProperty.MP_METALLIC,
                 unreal.MaterialProperty.MP_AMBIENT_OCCLUSION):
        M.disconnect_material_property(clone, prop)
    assert not list(M.recompile_material(clone))
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    assert world is not None
    # Use the same runtime component API already verified on the real mesh.
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_material(0, clone)
    mid = component.create_dynamic_material_instance(0, clone, 'GPU_Recolor_Verification')
    assert isinstance(mid, unreal.MaterialInstanceDynamic)
    target = R.create_render_target2d(world, 4096, 4096, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    manifest = json.loads((ROOT / "Exports/BlackNunchucks/recolor_parameters.json").read_text())
    samples = {p["parameter_suffix"]: p["texture_sample_uv_top_left"] for p in manifest["parts"]}

    def draw():
        R.draw_material_to_render_target(world, target, mid)
        return {name: setup.values(R.read_render_target_raw_uv(world, target, uv[0], uv[1], False))[:3]
                for name, uv in samples.items()}

    original = draw()
    for p in setup.PARTS:
        mid.set_scalar_parameter_value("Amount_" + p, 1.0)
    neutral = draw()
    for p in setup.PARTS:
        assert max(neutral[p]) > 0.1, ("No rendered neutral detail", p, neutral[p])
        mid.set_scalar_parameter_value("Amount_" + p, 0.0)
    tests = []
    for idx, p in enumerate(setup.PARTS):
        color = (0.8, 0.02, 0.06, 1) if idx % 2 == 0 else (0.01, 0.75, 0.04, 1)
        mid.set_vector_parameter_value("Color_" + p, unreal.LinearColor(*color))
        mid.set_scalar_parameter_value("Amount_" + p, 1.0)
        rendered = draw()
        expected = [neutral[p][k] * color[k] for k in range(3)]
        error = max(abs(rendered[p][k] - expected[k]) for k in range(3))
        others = max(abs(rendered[q][k] - original[q][k]) for q in setup.PARTS if q != p for k in range(3))
        assert error < 0.012, ("Tint output mismatch", p, rendered[p], expected, error)
        assert others < 0.002, ("Mask leaked into another part", p, others)
        tests.append({"part": p, "uv_top_left": samples[p], "rendered_linear_rgb": rendered[p],
                      "expected_linear_rgb": expected, "max_tint_error": error,
                      "max_other_part_change": others})
        mid.set_scalar_parameter_value("Amount_" + p, 0.0)
        mid.set_vector_parameter_value("Color_" + p, unreal.LinearColor(1, 1, 1, 1))
    final = draw()
    reset_error = max(abs(final[p][k] - original[p][k]) for p in setup.PARTS for k in range(3))
    assert reset_error < 0.002
    R.release_render_target2d(target)
    return {"rhi": "D3D12", "render_target": "4096x4096 RGBA16F",
            "method": "Persisted master BaseColor graph cloned to unlit emissive; GPU-rendered UV atlas; 16 chart center samples per state",
            "tests": tests, "max_reset_error": reset_error,
            "default_linear_rgb": original, "neutral_detail_linear_rgb": neutral}


report = {"status": "failed", "fresh_process": True}
try:
    source = json.loads((HERE / "setup_report.json").read_text())
    assert source["status"] == "passed"
    report.update(setup.verify(source_records=source))
    report["gpu_mask_isolation"] = gpu_check()
    report["status"] = "passed"
except Exception:
    report["status"] = "failed"
    report["error"] = traceback.format_exc()
    raise
finally:
    (HERE / "reload_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("BLACK_NUNCHUCKS_RELOAD_REPORT " + str(HERE / "reload_report.json"))
