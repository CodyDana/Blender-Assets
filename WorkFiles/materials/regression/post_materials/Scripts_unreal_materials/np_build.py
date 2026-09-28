"""Build the material functions, the three masters and every instance from nothing (inside Unreal).

Idempotent by construction: ``clean`` (its OWN process) deletes Materials/ and MaterialInstances/, then ``build``
creates every function, master and instance from nothing, and ``assign`` re-binds the mesh slots. The build REFUSES
to run over existing graphs. Measured on UE 5.8.3 (2026-09-26): rebuilding a material function IN PLACE
(delete_all_material_expressions_in_function + new inputs) saves cleanly and even compiles in the authoring process,
but a fresh process then fails to compile every material that calls it ("Missing function input 'Colour'",
"If input A must be a primitive type"): the calls lose some of the re-created inputs. So graphs are never rebuilt in
place. Running clean + build + assign twice gives the same graphs and parameters; ``np_dump`` proves it.

v2 (final pass): instances come in a chain, master -> MI_<Item>_<Part>_Base (every texture and value) ->
MI_<Item>_<Part> (the mesh's, overriding only its colour parameter(s)); presets hang off the Base. ``clean`` deletes
only the assets the spec authors and refuses when the folders hold anything else (a hand-made variant is never wiped).
"""
from __future__ import annotations

import time
import traceback

import unreal

import np_functions
import np_masters
import np_spec

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
ASSOC = unreal.MaterialParameterAssociation.GLOBAL_PARAMETER

FUNCTION_ORDER = ["MF_NormalStrength", "MF_AlbedoRollOff", "MF_TintDetail", "MF_LetteringBand", "MF_InkDerive"]


def get_or_create(path: str, cls, factory):
    if EAL.does_asset_exist(path):
        asset = unreal.load_asset(path)
        if not isinstance(asset, cls):
            raise TypeError(f"{path} exists but is a {type(asset).__name__}, not {cls.__name__}: refusing to touch it")
        return asset, False
    folder, name = path.rsplit("/", 1)
    asset = AT.create_asset(name, folder, cls, factory)
    if asset is None:
        raise RuntimeError(f"could not create {path}")
    return asset, True


def load_texture(asset: str):
    tex = unreal.load_asset(asset)
    if not isinstance(tex, unreal.Texture2D):
        raise RuntimeError(f"texture {asset} is missing: run the import_textures mode first")
    return tex


def stats(obj) -> dict:
    t0 = time.time()
    st = MEL.get_statistics(obj)       # blocks until this material / permutation's shaders exist (probe finding)
    out = {"sec": round(time.time() - t0, 2)}
    for p in ("num_pixel_shader_instructions", "num_vertex_shader_instructions", "num_samplers",
              "num_pixel_texture_samples", "num_vertex_texture_samples", "num_virtual_texture_samples",
              "num_uv_scalars", "num_interpolator_scalars"):
        try:
            out[p] = int(st.get_editor_property(p))
        except Exception:  # noqa: BLE001
            pass
    return out


def master_textures(plan: dict, master: str) -> dict:
    """The master's default textures (v2): the neutral 8x8 maps of build.master_defaults, never an item's maps."""
    return {k: load_texture(v) for k, v in plan["master_defaults"][master]["textures"].items()}


ROLE_ORDER = {"base": 0, "leaf": 1, "preset": 2}


def root_master(plan: dict, inst: dict) -> str:
    parent = inst["parent"]
    for _ in range(4):
        for mname, m in plan["spec"]["masters"].items():
            if m["path"] == parent:
                return mname
        parent = next(i["parent"] for i in plan["instances"].values() if i["path"] == parent)
    raise KeyError(inst["name"])


def _lc(v):
    return unreal.LinearColor(*[float(x) for x in (list(v) + [1.0] * 4)[:4]])


def set_instance(mi, plan, inst) -> dict:
    master = root_master(plan, inst)
    table = {p["name"]: p for p in plan["spec"]["masters"][master]["parameters"]}
    MEL.clear_all_material_instance_parameters(mi)
    parent = unreal.load_asset(inst["parent"])
    if parent is None:
        raise RuntimeError(f"parent {inst['parent']} missing")
    MEL.set_material_instance_parent(mi, parent)
    for name in sorted(inst["params"]):
        value = inst["params"][name]
        t = table[name]["type"]
        if t == "vector":
            MEL.set_material_instance_vector_parameter_value(mi, name, _lc(value), ASSOC)
        elif t == "scalar":
            MEL.set_material_instance_scalar_parameter_value(mi, name, float(value), ASSOC)
        elif t == "static_switch":
            MEL.set_material_instance_static_switch_parameter_value(mi, name, bool(value), ASSOC)
        else:
            raise TypeError(f"{inst['name']}: {name} has type {t}")
    for name in sorted(inst["textures"]):
        MEL.set_material_instance_texture_parameter_value(mi, name, load_texture(inst["textures"][name]), ASSOC)
    MEL.update_material_instance(mi)
    return readback(mi, plan, inst)


def overridden_names(mi, table: dict) -> list:
    out = []
    for name in sorted(table):
        try:
            if MEL.is_material_instance_parameter_overridden(mi, name):
                out.append(name)
        except Exception:  # noqa: BLE001
            pass
    return out


def readback(mi, plan, inst) -> dict:
    """Compare every EFFECTIVE value (own override or inherited through the chain) with the spec, and the set of
    overridden parameters with what this link of the chain must override (set_* returns False even on success)."""
    master = root_master(plan, inst)
    table = {p["name"]: p for p in plan["spec"]["masters"][master]["parameters"]}
    out = {"parent": None, "params": {}, "textures": {}, "mismatches": []}
    parent = mi.get_editor_property("parent")
    out["parent"] = parent.get_path_name().split(".")[0] if parent else None
    if out["parent"] != inst["parent"]:
        out["mismatches"].append(f"parent {out['parent']} != {inst['parent']}")
    out["overridden"] = overridden_names(mi, table)
    want_over = sorted(set(inst["params"]) | set(inst["textures"]))
    out["overridden_expected"] = want_over
    if out["overridden"] != want_over:
        out["mismatches"].append(f"overridden {out['overridden']} != {want_over}")
    for name, want in sorted(inst.get("effective_params", inst["params"]).items()):
        t = table[name]["type"]
        if t == "vector":
            c = MEL.get_material_instance_vector_parameter_value(mi, name, ASSOC)
            got = [c.r, c.g, c.b, c.a]
            ok = all(abs(a - b) <= 1e-6 * max(1.0, abs(b)) for a, b in zip(got, (list(want) + [1.0] * 4)[:4]))
        elif t == "scalar":
            got = float(MEL.get_material_instance_scalar_parameter_value(mi, name, ASSOC))
            ok = abs(got - float(want)) <= 1e-6 * max(1.0, abs(float(want)))
        else:
            got = bool(MEL.get_material_instance_static_switch_parameter_value(mi, name, ASSOC))
            ok = got == bool(want)
        out["params"][name] = got
        if not ok:
            out["mismatches"].append(f"{name}: {got} != {want}")
    for name, want in sorted(inst.get("effective_textures", inst["textures"]).items()):
        tex = MEL.get_material_instance_texture_parameter_value(mi, name, ASSOC)
        got = tex.get_path_name().split(".")[0] if tex else None
        out["textures"][name] = got
        if got != want:
            out["mismatches"].append(f"{name}: {got} != {want}")
    return out


def existing_authored(plan: dict) -> list:
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    return [p for p in authored_paths(plan) if EAL.does_asset_exist(p)]


def authored_paths(plan: dict) -> list:
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    paths = [f"{folders['functions']}/{n}" for n in FUNCTION_ORDER]
    paths += [m["path"] for m in spec["masters"].values()]
    paths += [i["path"] for i in plan["instances"].values()]
    return paths


def run_build(plan: dict) -> dict:
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    report = {"mode": "build", "functions": {}, "masters": {}, "instances": {}, "diffs": plan["diffs"]}
    left = existing_authored(plan)
    if left:
        raise RuntimeError(f"{len(left)} authored assets already exist (e.g. {left[0]}): run the 'clean' mode in its "
                           f"own process first - graphs are never rebuilt in place (see the module docstring)")
    mfs = {}
    for name in FUNCTION_ORDER:
        rep = {}
        try:
            mf, created = get_or_create(f"{folders['functions']}/{name}", unreal.MaterialFunction,
                                        unreal.MaterialFunctionFactoryNew())
            rep["created"] = created
            MEL.delete_all_material_expressions_in_function(mf)
            g = np_functions.BUILDERS[name](mf)
            mf.set_editor_property("description", np_functions.DESCRIPTIONS[name])
            mf.set_editor_property("expose_to_library", True)
            MEL.layout_material_function_expressions(mf)
            MEL.update_material_function(mf, None)
            rep["expressions"] = int(MEL.get_num_material_expressions_in_function(mf))
            rep["saved"] = bool(EAL.save_loaded_asset(mf, only_if_is_dirty=False))
            mfs[name] = mf
        except Exception:  # noqa: BLE001
            rep["error"] = traceback.format_exc()
        report["functions"][name] = rep
    for mname, builder in np_masters.BUILDERS.items():
        rep = {}
        try:
            mat, created = get_or_create(spec["masters"][mname]["path"], unreal.Material, unreal.MaterialFactoryNew())
            rep["created"] = created
            MEL.delete_all_material_expressions(mat)
            g, missing = builder(mat, spec["masters"][mname], plan["master_defaults"][mname]["params"],
                                 master_textures(plan, mname), mfs)
            rep["settings"] = {k: str(mat.get_editor_property(k))
                               for k in (spec["masters"][mname].get("settings") or {})}
            if missing:
                raise RuntimeError(f"{mname}: spec parameters not built: {missing}")
            MEL.layout_material_expressions(mat)
            rep["recompile_return"] = str(MEL.recompile_material(mat))
            rep["expressions"] = int(MEL.get_num_material_expressions(mat))
            rep["saved"] = bool(EAL.save_loaded_asset(mat, only_if_is_dirty=False))
            rep["statistics"] = stats(mat)
        except Exception:  # noqa: BLE001
            rep["error"] = traceback.format_exc()
        report["masters"][mname] = rep
    # parents before children: Base, then the buyer-facing leaf, then presets
    order = sorted(plan["instances"].values(), key=lambda i: (ROLE_ORDER[i["role"]], i["name"]))
    for inst in order:
        rep = {}
        try:
            mi, created = get_or_create(inst["path"], unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew())
            rep["created"] = created
            rep["readback"] = set_instance(mi, plan, inst)
            rep["saved"] = bool(EAL.save_loaded_asset(mi, only_if_is_dirty=False))
            rep["statistics"] = stats(mi)
        except Exception:  # noqa: BLE001
            rep["error"] = traceback.format_exc()
        report["instances"][inst["name"]] = rep
    report["passed"] = (all(not v.get("error") and v.get("saved") for v in report["functions"].values())
                        and all(not v.get("error") and v.get("saved") for v in report["masters"].values())
                        and all(not v.get("error") and v.get("saved") and not v["readback"]["mismatches"]
                                for v in report["instances"].values()))
    return report


def run_clean(plan: dict) -> dict:
    """Delete the authored materials and instances (own process; the next process rebuilds them). v2: ONLY the assets
    the spec authors are deleted, and nothing at all if Materials/ or MaterialInstances/ hold anything else (listed
    in the report). Meshes keep dangling slot references until ``assign`` runs; textures and meshes are not touched."""
    folders = plan["spec"]["unreal"]["folders"]
    out = {"mode": "clean"}
    expected = set(authored_paths(plan))
    present = []
    for key in ("materials", "instances"):
        path = folders[key]
        if EAL.does_directory_exist(path):
            present += [str(a).split(".")[0] for a in EAL.list_assets(path, recursive=True, include_folder=False)]
    present = sorted(set(present))
    out["present"] = present
    out["unexpected"] = [p for p in present if p not in expected]
    if out["unexpected"]:
        out["passed"] = False
        out["refused"] = ("assets that the spec does not author are in the pack's material folders; nothing was "
                          "deleted. Move them out, or add them to the spec as presets.")
        return out
    # children before parents: presets, leaves, bases, then masters, then functions
    rank = {i["path"]: ROLE_ORDER[i["role"]] for i in plan["instances"].values()}

    def order_key(path):
        if path in rank:
            return (0, -rank[path], path)
        return (1 if "/Functions/" not in path else 2, 0, path)
    out["deleted"] = {}
    for path in sorted(present, key=order_key):
        out["deleted"][path] = bool(EAL.delete_asset(path))
    content = np_spec.PROJECT / "WorkFiles/shuriken/UnrealShuriken/Content/NinjaPack"
    out["left_on_disk"] = sorted(str(p.relative_to(content)) for sub in ("Materials", "MaterialInstances")
                                 for p in (content / sub).rglob("*.uasset")) if content.is_dir() else []
    out["left_in_registry"] = existing_authored(plan)
    out["passed"] = not out["left_on_disk"] and not out["left_in_registry"] and all(out["deleted"].values())
    return out
