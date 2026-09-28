"""API probe (read-only, creates nothing on disk except the JSON): expression classes, pin names, enums."""
import json
from pathlib import Path
import unreal

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build/probe_api.json")
MEL = unreal.MaterialEditingLibrary
R = {}
R["MEL"] = sorted(n for n in dir(MEL) if not n.startswith("_"))
want = ["Exponential", "Exponential2", "Logarithm", "Logarithm2", "Logarithm10", "Step", "If", "Custom", "AppendVector",
        "ComponentMask", "DotProduct", "Max", "Min", "Power", "Saturate", "Normalize", "LinearInterpolate",
        "TextureObjectParameter", "TextureSample", "TextureCoordinate", "Clamp", "Divide", "Subtract", "Add", "Multiply",
        "OneMinus", "Constant", "Constant3Vector", "Constant4Vector", "StaticSwitchParameter", "ShadingModel",
        "MakeMaterialAttributes", "FunctionInput", "FunctionOutput", "MaterialFunctionCall", "Reroute", "NamedRerouteDeclaration",
        "Comment", "Abs", "Floor", "Frac", "SmoothStep", "Sign", "Ceil"]
R["classes"] = {w: hasattr(unreal, "MaterialExpression" + w) for w in want}
R["FunctionInputType"] = [n for n in dir(unreal.FunctionInputType) if n.startswith("FUNCTION")]
R["TC"] = [n for n in dir(unreal.TextureCompressionSettings) if n.startswith("TC_")]
R["CTM"] = [n for n in dir(unreal.CompositeTextureMode) if n.startswith("CTM")]
R["SamplerType"] = [n for n in dir(unreal.MaterialSamplerType) if n.startswith("SAMPLERTYPE")]
R["SamplerSource"] = [n for n in dir(unreal.SamplerSourceMode) if n.startswith("SSM")] if hasattr(unreal, "SamplerSourceMode") else None
R["MP"] = [n for n in dir(unreal.MaterialProperty) if n.startswith("MP_")]
R["MSM"] = [n for n in dir(unreal.MaterialShadingModel) if n.startswith("MSM")]
tmp = unreal.new_object(unreal.Material, outer=unreal.get_transient_package()) if False else None
# pin names on a transient material
mat = unreal.Material()
def pins(cls):
    try:
        e = MEL.create_material_expression(mat, cls, 0, 0)
        return {"inputs": [str(n) for n in MEL.get_material_expression_input_names(e)],
                "props": sorted(p for p in dir(e) if not p.startswith("_"))[:0]}
    except Exception as exc:
        return repr(exc)
for w in ["If", "LinearInterpolate", "Power", "MakeMaterialAttributes", "TextureSample", "StaticSwitchParameter",
          "Custom", "DotProduct", "AppendVector", "Max", "Exponential", "Logarithm2", "Clamp", "Normalize"]:
    c = getattr(unreal, "MaterialExpression" + w, None)
    if c:
        R.setdefault("pins", {})[w] = pins(c)
for w in ["If", "ComponentMask", "TextureSample", "Custom", "Power", "Constant3Vector", "FunctionInput", "TextureSampleParameter2D",
          "TextureObjectParameter", "StaticSwitchParameter", "VectorParameter", "ScalarParameter"]:
    c = getattr(unreal, "MaterialExpression" + w, None)
    if c:
        try:
            e = MEL.create_material_expression(mat, c, 0, 0)
            props = {}
            for p in dir(e):
                if p.startswith("_"):
                    continue
                try:
                    v = e.get_editor_property(p)
                    props[p] = str(v)[:80]
                except Exception:
                    pass
            R.setdefault("props", {})[w] = props
        except Exception as exc:
            R.setdefault("props", {})[w] = repr(exc)
# can we list a material's expressions?
for p in ("expressions", "editor_only_data", "expression_collection"):
    try:
        R.setdefault("mat_list", {})[p] = str(mat.get_editor_property(p))[:200]
    except Exception as exc:
        R.setdefault("mat_list", {})[p] = repr(exc)[:200]
R["mat_dir"] = sorted(n for n in dir(mat) if not n.startswith("_"))
R["mf_dir"] = sorted(n for n in dir(unreal.MaterialFunction()) if not n.startswith("_"))
R["tex_dir"] = sorted(n for n in dir(unreal.Texture2D) if not n.startswith("_"))
R["sm_dir"] = [n for n in dir(unreal.StaticMesh) if "material" in n.lower()]
OUT.write_text(json.dumps(R, indent=1, default=str))
print("NP_PROBE_API_DONE")
