"""Transient probe (nothing saved): node classes, pin names and material properties the final pass needs."""
import json
import unreal
MEL = unreal.MaterialEditingLibrary
out = {}
mat = unreal.new_object(unreal.Material, name="NP_FinalProbe")
for cls in ("MaterialExpressionDDX", "MaterialExpressionDDY", "MaterialExpressionSquareRoot", "MaterialExpressionTextureProperty",
            "MaterialExpressionLength", "MaterialExpressionDotProduct", "MaterialExpressionExponential", "MaterialExpressionPower",
            "MaterialExpressionTextureObjectParameter", "MaterialExpressionSaturate", "MaterialExpressionClamp"):
    c = getattr(unreal, cls, None)
    rec = {"exists": c is not None}
    if c is not None:
        try:
            e = MEL.create_material_expression(mat, c, 0, 0)
            rec["inputs"] = [str(n) for n in MEL.get_material_expression_input_names(e)]
            try:
                rec["outputs"] = [str(n) for n in MEL.get_material_expression_output_names(e)]
            except Exception as ex:
                rec["outputs"] = repr(ex)
            if cls == "MaterialExpressionTextureProperty":
                rec["props"] = [p for p in dir(e) if "prop" in p.lower() or "coord" in p.lower()]
        except Exception as ex:
            rec["error"] = repr(ex)
    out[cls] = rec
for p in ("float_precision_mode", "used_with_instanced_static_meshes", "used_with_nanite", "used_with_static_lighting", "used_with_skeletal_mesh"):
    try:
        out["mat." + p] = str(mat.get_editor_property(p))
    except Exception as ex:
        out["mat." + p] = "ERR " + repr(ex)
out["MaterialFloatPrecisionMode"] = [n for n in dir(unreal.MaterialFloatPrecisionMode) if n.startswith("MFPM")] if hasattr(unreal, "MaterialFloatPrecisionMode") else None
out["TMTM"] = [n for n in dir(getattr(unreal, "MaterialExposedTextureProperty", object)) if n.startswith("TMTM")]
path = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/final/probe/np_final_probe.json"
open(path, "w").write(json.dumps(out, indent=1))
unreal.log("NP_FINAL_PROBE_DONE")
