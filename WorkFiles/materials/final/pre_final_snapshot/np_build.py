"""Build the material functions, the three masters and every instance from nothing (inside Unreal).

Idempotent by construction: ``clean`` (its OWN process) deletes Materials/ and MaterialInstances/, then ``build``
creates every function, master and instance from nothing, and ``assign`` re-binds the mesh slots. The build REFUSES
to run over existing graphs. Measured on UE 5.8.3 (2026-09-26): rebuilding a material function IN PLACE
(delete_all_material_expressions_in_function + new inputs) saves cleanly and even compiles in the authoring process,
but a fresh process then fails to compile every material that calls it ("Missing function input 'Colour'",
"If input A must be a primitive type"): the calls lose some of the re-created inputs. So graphs are never rebuilt in
place. Running clean + build + assign twice gives the same graphs and parameters; ``np_dump`` proves it.
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
    """The master's default textures: the spec's default slot first, then any other slot of the master."""
    names = dict(plan["master_defaults"][master]["textures"])
    for s in plan["slots"]:
        if s["master"] == master:
            for k, v in s["textures"].items():
                names.setdefault(k, v)
    return {k: load_texture(v) for k, v in names.items()}


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


def readback(mi, plan, inst) -> dict:
    """Compare every value the spec sets with what the instance reports (set_* returns False even on success)."""
    master = root_master(plan, inst)
    table = {p["name"]: p for p in plan["spec"]["masters"][master]["parameters"]}
    out = {"parent": None, "params": {}, "textures": {}, "mismatches": []}
    parent = mi.get_editor_property("parent")
    out["parent"] = parent.get_path_name().split(".")[0] if parent else None
    if out["parent"] != inst["parent"]:
        out["mismatches"].append(f"parent {out['parent']} != {inst['parent']}")
    for name, want in sorted(inst["params"].items()):
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
    for name, want in sorted(inst["textures"].items()):
        tex = MEL.get_material_instance_texture_parameter_value(mi, name, ASSOC)
        got = tex.get_path_name().split(".")[0] if tex else None
        out["textures"][name] = got
        if got != want:
            out["mismatches"].append(f"{name}: {got} != {want}")
    return out


def existing_authored(plan: dict) -> list:
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    paths = [f"{folders['functions']}/{n}" for n in FUNCTION_ORDER]
    paths += [m["path"] for m in spec["masters"].values()]
    paths += [i["path"] for i in plan["instances"].values()]
    return [p for p in paths if EAL.does_asset_exist(p)]


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
    # parents before children (the preset's parent is an instance)
    order = sorted(plan["instances"].values(), key=lambda i: (i.get("preset_of") is not None, i["name"]))
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
    """Delete the materials and instances (own process; the next process rebuilds them). Meshes keep their slots'
    references as dangling until ``assign`` runs again; textures and meshes are not touched."""
    folders = plan["spec"]["unreal"]["folders"]
    out = {"mode": "clean"}
    for key in ("instances", "materials"):
        path = folders[key]
        out[key] = {"existed": bool(EAL.does_directory_exist(path)),
                    "deleted": bool(EAL.delete_directory(path)) if EAL.does_directory_exist(path) else None}
    content = np_spec.PROJECT / "WorkFiles/shuriken/UnrealShuriken/Content/NinjaPack"
    out["left_on_disk"] = sorted(str(p.relative_to(content)) for sub in ("Materials", "MaterialInstances")
                                 for p in (content / sub).rglob("*.uasset")) if content.is_dir() else []
    out["left_in_registry"] = existing_authored(plan)
    out["passed"] = not out["left_on_disk"] and not out["left_in_registry"]
    return out
