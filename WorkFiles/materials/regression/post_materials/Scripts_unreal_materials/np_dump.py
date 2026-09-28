"""Canonical dump of everything the build authors (inside Unreal): graphs, parameters, instances, texture flags, slots.

Graphs are walked from their roots (a material's property inputs / its Material Attributes input; a function's
outputs), and every node gets the index of its first visit in that walk, so the dump does not depend on object
names (asset bytes carry GUIDs and auto-numbered names; two builds are compared through this dump instead).
Node positions come from MEL.layout_* and are kept in a separate ``layout`` section.
"""
from __future__ import annotations

import unreal

import np_spec

MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty

PROPS = ("parameter_name", "group", "sort_priority", "desc", "default_value", "slider_min", "slider_max", "texture",
         "sampler_type", "sampler_source", "r", "g", "b", "a", "constant", "const_a", "const_b", "const_exponent",
         "input_name", "input_type", "output_name", "description", "material_function", "shading_model",
         "coordinate_index", "equals_threshold")
MATERIAL_PROPS = ("shading_model", "blend_mode", "two_sided", "use_material_attributes", "float_precision_mode",
                  "used_with_instanced_static_meshes")
PROPERTY_ROOTS = ("MP_BASE_COLOR", "MP_METALLIC", "MP_SPECULAR", "MP_ROUGHNESS", "MP_ANISOTROPY", "MP_EMISSIVE_COLOR",
                  "MP_OPACITY", "MP_OPACITY_MASK", "MP_NORMAL", "MP_TANGENT", "MP_WORLD_POSITION_OFFSET",
                  "MP_SUBSURFACE_COLOR", "MP_AMBIENT_OCCLUSION", "MP_REFRACTION", "MP_MATERIAL_ATTRIBUTES")


def ser(v):
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return round(v, 9)
    if isinstance(v, unreal.LinearColor):
        return [round(v.r, 9), round(v.g, 9), round(v.b, 9), round(v.a, 9)]
    if isinstance(v, unreal.Object):
        return v.get_path_name().split(".")[0]
    if hasattr(v, "name") and hasattr(v, "value"):          # unreal enums
        return str(v)
    return str(v)


def expr_props(e) -> dict:
    d = {"class": e.get_class().get_name()}
    for p in PROPS:
        try:
            v = e.get_editor_property(p)
        except Exception:  # noqa: BLE001
            continue
        d[p] = ser(v)
    return d


def walk(owner, is_function: bool, roots: list) -> dict:
    ids, nodes, layout = {}, [], []

    def visit(e):
        key = e.get_path_name()
        if key in ids:
            return ids[key]
        idx = len(nodes)
        ids[key] = idx
        nodes.append(None)
        layout.append(None)
        d = expr_props(e)
        names = [str(n) for n in MEL.get_material_expression_input_names(e)]
        inputs = (MEL.get_inputs_for_material_function_expression(owner, e) if is_function
                  else MEL.get_inputs_for_material_expression(owner, e))
        ins = []
        for nm, src in zip(names, inputs):
            if src is None:
                ins.append([nm, None])
                continue
            out_name = MEL.get_input_node_output_name_for_material_expression(e, src)
            ins.append([nm, visit(src), str(out_name)])
        d["inputs"] = ins
        nodes[idx] = d
        x, y = MEL.get_material_expression_node_position(e)
        layout[idx] = [int(x), int(y)]
        return idx

    root_ids = {}
    for name, e, out in roots:
        if e is not None:
            root_ids[name] = [visit(e), out]
    return {"roots": root_ids, "nodes": nodes, "layout": layout}


def dump_material(mat) -> dict:
    roots = []
    for rname in PROPERTY_ROOTS:
        prop = getattr(MP, rname)
        e = MEL.get_material_property_input_node(mat, prop)
        if e is not None:
            roots.append((rname, e, str(MEL.get_material_property_input_node_output_name(mat, prop))))
    g = walk(mat, False, roots)
    d = {"asset": mat.get_path_name().split(".")[0],
         "settings": {p: ser(mat.get_editor_property(p)) for p in MATERIAL_PROPS},
         "graph": {"roots": g["roots"], "nodes": g["nodes"]}, "layout": g["layout"],
         "expressions_total": int(MEL.get_num_material_expressions(mat))}
    d["unreachable_expressions"] = d["expressions_total"] - len(g["nodes"])
    d["parameters"] = {
        "vector": sorted(str(n) for n in MEL.get_vector_parameter_names(mat)),
        "scalar": sorted(str(n) for n in MEL.get_scalar_parameter_names(mat)),
        "texture": sorted(str(n) for n in MEL.get_texture_parameter_names(mat)),
        "static_switch": sorted(str(n) for n in MEL.get_static_switch_parameter_names(mat))}
    return d


def dump_function(mf) -> dict:
    exprs = list(MEL.get_material_function_expressions(mf))
    outs = [e for e in exprs if isinstance(e, unreal.MaterialExpressionFunctionOutput)]
    ins = [e for e in exprs if isinstance(e, unreal.MaterialExpressionFunctionInput)]
    roots = [(f"out:{e.get_editor_property('output_name')}", e, "") for e in
             sorted(outs, key=lambda x: int(x.get_editor_property("sort_priority")))]
    roots += [(f"in:{e.get_editor_property('input_name')}", e, "") for e in
              sorted(ins, key=lambda x: int(x.get_editor_property("sort_priority")))]
    g = walk(mf, True, roots)
    return {"asset": mf.get_path_name().split(".")[0], "description": ser(mf.get_editor_property("description")),
            "graph": {"roots": g["roots"], "nodes": g["nodes"]}, "layout": g["layout"],
            "expressions_total": len(exprs), "unreachable_expressions": len(exprs) - len(g["nodes"])}


def dump_instance(mi, plan: dict) -> dict:
    parent = mi.get_editor_property("parent")
    d = {"asset": mi.get_path_name().split(".")[0], "parent": ser(parent), "vector": {}, "scalar": {},
         "texture": {}, "static_switch": {}, "overridden": []}
    for n in sorted(str(x) for x in MEL.get_vector_parameter_names(mi)):
        d["vector"][n] = ser(MEL.get_material_instance_vector_parameter_value(mi, n))
    for n in sorted(str(x) for x in MEL.get_scalar_parameter_names(mi)):
        d["scalar"][n] = ser(float(MEL.get_material_instance_scalar_parameter_value(mi, n)))
    for n in sorted(str(x) for x in MEL.get_texture_parameter_names(mi)):
        d["texture"][n] = ser(MEL.get_material_instance_texture_parameter_value(mi, n))
    for n in sorted(str(x) for x in MEL.get_static_switch_parameter_names(mi)):
        d["static_switch"][n] = bool(MEL.get_material_instance_static_switch_parameter_value(mi, n))
    for kind in ("vector", "scalar", "texture", "static_switch"):
        for n in d[kind]:
            try:
                if MEL.is_material_instance_parameter_overridden(mi, n):
                    d["overridden"].append(n)
            except Exception:  # noqa: BLE001
                pass
    d["overridden"] = sorted(set(d["overridden"]))
    return d


def dump_all(plan: dict) -> dict:
    import np_meshes
    import np_textures
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    out = {"functions": {}, "masters": {}, "instances": {}, "textures": {}, "meshes": {}}
    for name in ("MF_NormalStrength", "MF_AlbedoRollOff", "MF_TintDetail", "MF_LetteringBand", "MF_InkDerive"):
        mf = unreal.load_asset(f"{folders['functions']}/{name}")
        out["functions"][name] = dump_function(mf) if mf else None
    for mname, m in spec["masters"].items():
        mat = unreal.load_asset(m["path"])
        out["masters"][mname] = dump_material(mat) if mat else None
    for iname, inst in sorted(plan["instances"].items()):
        mi = unreal.load_asset(inst["path"])
        out["instances"][iname] = dump_instance(mi, plan) if mi else None
    for asset in sorted(plan["textures"]):
        tex = unreal.load_asset(asset)
        out["textures"][asset] = np_textures.inspect(tex) if tex else None
    for name, m in sorted(plan["meshes"].items()):
        mesh = unreal.load_asset(m["asset"])
        out["meshes"][name] = {"slots": np_meshes.slot_table(mesh), "lod_sections": np_meshes.lod_sections(mesh)} if mesh else None
    return out


def strip_layout(d: dict) -> dict:
    """The dump without node positions (compared separately)."""
    import copy
    c = copy.deepcopy(d)
    for sect in ("functions", "masters"):
        for v in c.get(sect, {}).values():
            if v:
                v.pop("layout", None)
    return c
