from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials")


def patch(fname, pairs):
    p = ROOT / fname
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in s:
            raise SystemExit(f"{fname}: NOT FOUND {old[:90]!r}")
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    print("patched", fname)


patch("np_dump.py", [
    ('MATERIAL_PROPS = ("shading_model", "blend_mode", "two_sided", "use_material_attributes")',
     'MATERIAL_PROPS = ("shading_model", "blend_mode", "two_sided", "use_material_attributes", "float_precision_mode",\n'
     '                  "used_with_instanced_static_meshes")'),
])

patch("np_verify.py", [
    ('''    instances   parent and every value the spec sets read back equal; their permutation compiles (statistics)''',
     '''    instances   parent and every EFFECTIVE value the spec sets read back equal (v2 chain: master -> _Base -> the
                buyer MI, which overrides only its colour(s)); the overridden set is exactly what that link must
                override; their permutation compiles (statistics)
    masters     (v2) also: the spec's material settings (float precision, instanced-mesh usage), every parameter has
                a tooltip, and the master references only the neutral textures in Textures/Default
    dependencies (v2) every mesh's transitive package dependencies hold no other item's textures (migrating or
                cooking one item never drags another item's maps along)'''),
    ('''        rep["settings"] = d["settings"]
        rep["unreachable"] = d["unreachable_expressions"]''', '''        rep["settings"] = d["settings"]
        want_settings = m.get("settings") or {}
        rep["settings_ok"] = {k: (str(d["settings"].get(k)).split(".")[-1].split(":")[0].strip("<>") == str(v)
                                  if isinstance(v, str) else d["settings"].get(k) == v)
                              for k, v in want_settings.items()}
        params = [n for n in d["graph"]["nodes"] if n.get("parameter_name")]
        rep["tooltips_missing"] = sorted({n["parameter_name"] for n in params if not (n.get("desc") or "").strip()})
        default_folder = spec["unreal"]["folders"]["default_textures"] + "/"
        rep["textures_referenced"] = sorted({n["texture"] for n in params if n.get("texture")})
        rep["non_default_textures"] = [t for t in rep["textures_referenced"] if not t.startswith(default_folder)]
        rep["unreachable"] = d["unreachable_expressions"]'''),
    ('''        rep["pass"] = (not rep["parameters_missing"] and not rep["parameters_extra"] and rep["unreachable"] == 0
                       and rep["shading_ok"] and rep["statistics"].get("num_pixel_shader_instructions", 0) > 0
                       and rep["statistics"].get("num_samplers", 99) <= 16)''',
     '''        rep["pass"] = (not rep["parameters_missing"] and not rep["parameters_extra"] and rep["unreachable"] == 0
                       and rep["shading_ok"] and rep["statistics"].get("num_pixel_shader_instructions", 0) > 0
                       and rep["statistics"].get("num_samplers", 99) <= 16 and all(rep["settings_ok"].values())
                       and not rep["tooltips_missing"] and not rep["non_default_textures"])'''),
    ('''        out[iname] = {"parent": rb["parent"], "mismatches": rb["mismatches"], "statistics": st,
                      "overridden": d["overridden"],''', '''        out[iname] = {"role": inst["role"], "parent": rb["parent"], "mismatches": rb["mismatches"],
                      "statistics": st, "overridden": d["overridden"],'''),
    ('''def run_verify(plan: dict) -> dict:''', '''def verify_dependencies(plan) -> dict:
    """Transitive package dependencies of every mesh: only its own item's textures (and Textures/Default)."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=True,
                                                 include_searchable_names=False, include_soft_management_references=False,
                                                 include_hard_management_references=False)
    tex_root = np_spec.ROOT + "/Textures/"
    default_folder = plan["spec"]["unreal"]["folders"]["default_textures"] + "/"
    out = {}
    for name, m in sorted(plan["meshes"].items()):
        allowed = set()
        for s in plan["slots"]:
            if s["mesh"] == name:
                allowed |= set(s["textures"].values())
                for i in plan["instances"].values():
                    if i.get("preset_of") == s["base_instance"] or i.get("preset_of") == s["instance"]:
                        allowed |= set(i["textures"].values())
        seen, todo = set(), [m["asset"]]
        while todo:
            pkg = todo.pop()
            if pkg in seen:
                continue
            seen.add(pkg)
            deps = ar.get_dependencies(pkg, opts) or []
            for dep in deps:
                dep = str(dep)
                if dep.startswith("/Game/") and dep not in seen:
                    todo.append(dep)
        textures = sorted(p for p in seen if p.startswith(tex_root))
        foreign = [t for t in textures if t not in allowed and not t.startswith(default_folder)]
        out[name] = {"packages": len(seen), "textures": textures, "foreign_textures": foreign,
                     "pass": not foreign and bool(textures)}
    return out


def run_verify(plan: dict) -> dict:'''),
    ('''    report["textures"] = _safe(lambda: np_textures.verify(plan))''',
     '''    report["textures"] = _safe(lambda: np_textures.verify(plan))
    report["dependencies"] = _safe(lambda: verify_dependencies(plan))'''),
    ('''    report["gates"] = {s: sect_pass(s) for s in ("functions", "masters", "instances", "meshes", "textures")}''',
     '''    report["gates"] = {s: sect_pass(s) for s in ("functions", "masters", "instances", "meshes", "textures",
                                                   "dependencies")}'''),
])
