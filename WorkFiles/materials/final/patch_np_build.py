from pathlib import Path

p = Path("C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/np_build.py")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit(f"NOT FOUND: {old[:80]!r}")
    s = s.replace(old, new)


rep('''place. Running clean + build + assign twice gives the same graphs and parameters; ``np_dump`` proves it.
"""''', '''place. Running clean + build + assign twice gives the same graphs and parameters; ``np_dump`` proves it.

v2 (final pass): instances come in a chain, master -> MI_<Item>_<Part>_Base (every texture and value) ->
MI_<Item>_<Part> (the mesh's, overriding only its colour parameter(s)); presets hang off the Base. ``clean`` deletes
only the assets the spec authors and refuses when the folders hold anything else (a hand-made variant is never wiped).
"""''')
rep('''def master_textures(plan: dict, master: str) -> dict:
    """The master's default textures: the spec's default slot first, then any other slot of the master."""
    names = dict(plan["master_defaults"][master]["textures"])
    for s in plan["slots"]:
        if s["master"] == master:
            for k, v in s["textures"].items():
                names.setdefault(k, v)
    return {k: load_texture(v) for k, v in names.items()}
''', '''def master_textures(plan: dict, master: str) -> dict:
    """The master's default textures (v2): the neutral 8x8 maps of build.master_defaults, never an item's maps."""
    return {k: load_texture(v) for k, v in plan["master_defaults"][master]["textures"].items()}


ROLE_ORDER = {"base": 0, "leaf": 1, "preset": 2}
''')
rep('''def readback(mi, plan, inst) -> dict:
    """Compare every value the spec sets with what the instance reports (set_* returns False even on success)."""
    master = root_master(plan, inst)
    table = {p["name"]: p for p in plan["spec"]["masters"][master]["parameters"]}
    out = {"parent": None, "params": {}, "textures": {}, "mismatches": []}
    parent = mi.get_editor_property("parent")
    out["parent"] = parent.get_path_name().split(".")[0] if parent else None
    if out["parent"] != inst["parent"]:
        out["mismatches"].append(f"parent {out['parent']} != {inst['parent']}")
    for name, want in sorted(inst["params"].items()):''', '''def overridden_names(mi, table: dict) -> list:
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
    for name, want in sorted(inst.get("effective_params", inst["params"]).items()):''')
rep('''    for name, want in sorted(inst["textures"].items()):
        tex = MEL.get_material_instance_texture_parameter_value(mi, name, ASSOC)''', '''    for name, want in sorted(inst.get("effective_textures", inst["textures"]).items()):
        tex = MEL.get_material_instance_texture_parameter_value(mi, name, ASSOC)''')
rep('''    paths = [f"{folders['functions']}/{n}" for n in FUNCTION_ORDER]
    paths += [m["path"] for m in spec["masters"].values()]
    paths += [i["path"] for i in plan["instances"].values()]
    return [p for p in paths if EAL.does_asset_exist(p)]''', '''    return [p for p in authored_paths(plan) if EAL.does_asset_exist(p)]


def authored_paths(plan: dict) -> list:
    spec = plan["spec"]
    folders = spec["unreal"]["folders"]
    paths = [f"{folders['functions']}/{n}" for n in FUNCTION_ORDER]
    paths += [m["path"] for m in spec["masters"].values()]
    paths += [i["path"] for i in plan["instances"].values()]
    return paths''')
rep('''            g, missing = builder(mat, spec["masters"][mname], plan["master_defaults"][mname]["params"],
                                 master_textures(plan, mname), mfs)''', '''            g, missing = builder(mat, spec["masters"][mname], plan["master_defaults"][mname]["params"],
                                 master_textures(plan, mname), mfs)
            rep["settings"] = {k: str(mat.get_editor_property(k))
                               for k in (spec["masters"][mname].get("settings") or {})}''')
rep('''    # parents before children (the preset's parent is an instance)
    order = sorted(plan["instances"].values(), key=lambda i: (i.get("preset_of") is not None, i["name"]))''',
    '''    # parents before children: Base, then the buyer-facing leaf, then presets
    order = sorted(plan["instances"].values(), key=lambda i: (ROLE_ORDER[i["role"]], i["name"]))''')
old_clean = s[s.index("def run_clean(plan: dict) -> dict:"):]
s = s.replace(old_clean, '''def run_clean(plan: dict) -> dict:
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
''')
p.write_text(s, encoding="utf-8")
print("np_build patched")
