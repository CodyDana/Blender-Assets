"""Fresh-process verification (inside Unreal): everything the build wrote, read back from the saved packages.

Gates (all must pass):
    functions   the five MFs exist, with their spec'd outputs
    masters     exist, recompile, report statistics (samplers <= 16), expose exactly the spec's parameters,
                no unreachable expressions, the right shading model / material-attributes setting
    instances   parent and every value the spec sets read back equal; their permutation compiles (statistics)
    meshes      every slot of every mesh holds its spec'd instance; every section of every LOD resolves to one of the
                pack's instances (no WorldGridMaterial / DefaultMaterial anywhere); sockets = the sidecar's
    textures    every texture carries its kind's flags (np_textures.verify), incl. the hat ORM composite

Compile ERRORS are also checked outside Python: run_build.sh greps this process's log for "Failed to compile".
"""
from __future__ import annotations

import json
import traceback

import unreal

import np_build
import np_dump
import np_meshes
import np_spec
import np_textures

MEL = unreal.MaterialEditingLibrary
MSM = unreal.MaterialShadingModel

FUNCTION_OUTPUTS = {"MF_TintDetail": ["Albedo", "Headroom"], "MF_AlbedoRollOff": ["Albedo"],
                    "MF_NormalStrength": ["Normal"], "MF_LetteringBand": ["BaseColor", "Roughness", "Ink"],
                    "MF_InkDerive": ["BlackDry", "RedDry", "RedPool"]}


def _safe(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return {"error": traceback.format_exc()[-1500:]}


def verify_functions(plan, dump) -> dict:
    out = {}
    for name, outs in FUNCTION_OUTPUTS.items():
        d = dump["functions"].get(name)
        if not d:
            out[name] = {"pass": False, "error": "missing"}
            continue
        got = [k[4:] for k in d["graph"]["roots"] if k.startswith("out:")]
        out[name] = {"outputs": got, "expressions": d["expressions_total"],
                     "unreachable": d["unreachable_expressions"],
                     "pass": got == outs and d["unreachable_expressions"] == 0}
    return out


def verify_masters(plan, dump) -> dict:
    out = {}
    spec = plan["spec"]
    for mname, m in spec["masters"].items():
        rep = {}
        mat = unreal.load_asset(m["path"])
        d = dump["masters"].get(mname)
        if mat is None or d is None:
            out[mname] = {"pass": False, "error": "missing"}
            continue
        rep["recompile_return"] = str(MEL.recompile_material(mat))
        rep["statistics"] = np_build.stats(mat)
        want = {"vector": set(), "scalar": set(), "texture": set(), "static_switch": set()}
        for p in m["parameters"]:
            want[p["type"]].add(p["name"])
        got = {k: set(v) for k, v in d["parameters"].items()}
        rep["parameters_missing"] = {k: sorted(want[k] - got[k]) for k in want if want[k] - got[k]}
        rep["parameters_extra"] = {k: sorted(got[k] - want[k]) for k in want if got[k] - want[k]}
        rep["settings"] = d["settings"]
        rep["unreachable"] = d["unreachable_expressions"]
        attrs = bool(m.get("use_material_attributes", False))
        want_sm = MSM.MSM_FROM_MATERIAL_EXPRESSION if mname == "M_Fabric_Master" else MSM.MSM_DEFAULT_LIT
        rep["shading_ok"] = (d["settings"]["shading_model"] == str(want_sm)
                             and bool(d["settings"]["use_material_attributes"]) == attrs)
        rep["pass"] = (not rep["parameters_missing"] and not rep["parameters_extra"] and rep["unreachable"] == 0
                       and rep["shading_ok"] and rep["statistics"].get("num_pixel_shader_instructions", 0) > 0
                       and rep["statistics"].get("num_samplers", 99) <= 16)
        out[mname] = rep
    return out


def verify_instances(plan, dump) -> dict:
    out = {}
    for iname, inst in sorted(plan["instances"].items()):
        mi = unreal.load_asset(inst["path"])
        if mi is None:
            out[iname] = {"pass": False, "error": "missing"}
            continue
        rb = np_build.readback(mi, plan, inst)
        st = np_build.stats(mi)
        d = dump["instances"][iname]
        out[iname] = {"parent": rb["parent"], "mismatches": rb["mismatches"], "statistics": st,
                      "overridden": d["overridden"],
                      "pass": not rb["mismatches"] and st.get("num_pixel_shader_instructions", 0) > 0}
    return out


def verify_meshes(plan, dump) -> dict:
    out = {}
    pack_mi = plan["spec"]["unreal"]["folders"]["instances"] + "/"
    for name, m in sorted(plan["meshes"].items()):
        mesh = unreal.load_asset(m["asset"])
        if mesh is None:
            out[name] = {"pass": False, "error": "missing"}
            continue
        slots = np_meshes.slot_table(mesh)
        secs = np_meshes.lod_sections(mesh)
        want = {s["index"]: s for s in m["slots"]}
        bad = []
        for s in slots:
            w = want.get(s["index"])
            if w is None:
                bad.append(f"extra slot {s}")
            elif s["slot_name"] != w["slot_name"] or s["material"] != w["instance_path"]:
                bad.append(f"slot {s['index']}: {s} != {w['slot_name']} / {w['instance_path']}")
        for lod in secs:
            for sec in lod["sections"]:
                mat = sec["material"] or "None"
                if not mat.startswith(pack_mi):
                    bad.append(f"LOD{lod['lod']} section {sec['section']}: {mat}")
        sidecar = json.loads((np_spec.PROJECT / m["sidecar"]).read_text(encoding="utf-8"))
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        sockets = sorted(str(n) for n in comp.get_all_socket_names())
        want_sockets = sorted(r["socket"] for r in sidecar.get("sockets", []))
        if sockets != want_sockets:
            bad.append(f"sockets {sockets} != sidecar {want_sockets}")
        world_grid = any("WorldGridMaterial" in str(s["material"]) or "DefaultMaterial" in str(s["material"]) for s in slots)
        out[name] = {"slots": slots, "lod_sections": secs, "lods": len(secs), "sockets": sockets,
                     "problems": bad, "world_grid_anywhere": world_grid, "pass": not bad and not world_grid}
    return out


def run_verify(plan: dict) -> dict:
    dump = np_dump.dump_all(plan)
    report = {"mode": "verify"}
    report["functions"] = _safe(lambda: verify_functions(plan, dump))
    report["masters"] = _safe(lambda: verify_masters(plan, dump))
    report["instances"] = _safe(lambda: verify_instances(plan, dump))
    report["meshes"] = _safe(lambda: verify_meshes(plan, dump))
    report["textures"] = _safe(lambda: np_textures.verify(plan))
    report["accounting"] = np_spec.export_pngs_accounted(plan)

    def sect_pass(sect):
        v = report[sect]
        if "error" in v and isinstance(v["error"], str):
            return False
        if sect == "textures":
            return bool(v.get("passed"))
        return all(x.get("pass") for x in v.values())

    report["gates"] = {s: sect_pass(s) for s in ("functions", "masters", "instances", "meshes", "textures")}
    report["gates"]["accounting"] = report["accounting"]["passed"]
    report["passed"] = all(report["gates"].values())
    return report, dump
