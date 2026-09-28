"""Independent verifier: compare vf_unreal.json (fresh commandlet dump) with vf_blender.json (headless Blender dump),
layout.json and the project configs. Plain Python (run with Blender's bundled python). Writes vf_report.json."""
import configparser
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
V = ROOT / "WorkFiles/armory/build/unreal/verify"
U = json.loads((V / "vf_unreal.json").read_text(encoding="utf-8"))
B = json.loads((V / "vf_blender.json").read_text(encoding="utf-8"))
LAY = json.loads((ROOT / "WorkFiles/armory/build/layout.json").read_text(encoding="utf-8"))
rep = {}

# ---------------------------------------------------------------- gate 1: meshes
M = U["meshes"]["meshes"]
g1 = {"n_fbx": len(U["meshes"]["fbx_stems"]), "rows": {}, "fail": []}
for s in U["meshes"]["fbx_stems"]:
    e = M[s]
    bp = B["pieces"].get(s)
    r = {"sm": e.get("static_mesh"), "convex": e.get("convex"), "ucx_blender": len(bp["ucx"]) if bp else None,
         "other_simple": sum(e.get(k, 0) or 0 for k in ("box", "sphere", "sphyl"))}
    slots = {sl["slot"]: sl["material"] for sl in e.get("slots", [])}
    want = bp["slots"] if bp else []
    r["slots_expected"] = want
    r["slots_got"] = {k: (v["path"] if v else None) for k, v in slots.items()}
    bad_slot = []
    for w in want:
        mi = slots.get(w)
        if mi is None:
            bad_slot.append((w, "missing slot or no material"))
            continue
        chain = [mi["path"], mi.get("base")] + [p for p in mi.get("parent_chain", []) if p]
        if any(p is None or p.startswith("/Engine/") or "DefaultMaterial" in p or "WorldGridMaterial" in p for p in chain):
            bad_slot.append((w, "engine default in chain", chain))
    extra = sorted(set(slots) - set(want))
    r["extra_slots"], r["bad_slots"] = extra, bad_slot
    r["ok"] = bool(e.get("static_mesh")) and (e.get("convex") or 0) >= 1 and r["convex"] == r["ucx_blender"] \
        and not bad_slot and not extra
    g1["rows"][s] = r
    if not r["ok"]:
        g1["fail"].append(s)
g1["n_static_meshes"] = sum(1 for r in g1["rows"].values() if r["sm"])
g1["convex_total"] = sum(r["convex"] or 0 for r in g1["rows"].values())
g1["ucx_total_blender"] = sum(r["ucx_blender"] or 0 for r in g1["rows"].values())
g1["materials_used"] = sorted({p for r in g1["rows"].values() for p in r["slots_got"].values() if p})
g1["passed"] = g1["n_fbx"] == 35 and g1["n_static_meshes"] == 35 and not g1["fail"]
rep["1_meshes"] = g1

# ---------------------------------------------------------------- gate 2: level
L = U["level"]
acts = L["actors"]
sma = [a for a in acts if a["class"] == "StaticMeshActor"]
all_smc = [(a["label"], c) for a in acts for c in a["smc"]]
missing_mesh = [lab for lab, c in all_smc if not c["mesh"]]
bad_mesh_ref = [lab for lab, c in all_smc if c["mesh"] and not c["mesh"].startswith("/Game/")]
null_mats = [lab for lab, c in all_smc if any(m is None or m.startswith("/Engine/") for m in c["mats"])]
overrides = [lab for lab, c in all_smc if any(c["overrides"])]
label_piece_mismatch = []
for a in sma:
    piece = a["label"].rsplit("__", 1)[0]
    mesh = a["smc"][0]["mesh"] if a["smc"] else None
    if not mesh or mesh.rsplit(".", 1)[-1] != piece:
        label_piece_mismatch.append((a["label"], mesh))
g2 = {"asset_exists": L["asset_exists"], "loaded": L["loaded"], "n_actors": L["n_actors"],
      "classes": dict(Counter(a["class"] for a in acts)), "n_static_mesh_actors": len(sma),
      "n_smc_all_actors": len(all_smc), "n_layout_instances": len(LAY["instances"]),
      "n_blender_assembly": len(B["instances"]), "missing_mesh": missing_mesh, "non_game_mesh": bad_mesh_ref,
      "null_or_engine_mats": null_mats, "overrides": overrides, "label_mesh_mismatch": label_piece_mismatch,
      "hidden": [a["label"] for a in acts if a["hidden"]],
      "invisible_smc": [lab for lab, c in all_smc if not c["visible"]]}
g2["passed"] = (L["asset_exists"] and L["loaded"] and len(sma) == len(LAY["instances"]) == len(B["instances"])
                and len(all_smc) == len(sma) and not missing_mesh and not bad_mesh_ref and not null_mats
                and not label_piece_mismatch)
rep["2_level"] = g2

# ---------------------------------------------------------------- gate 3: bounds
by_label = {a["label"]: a for a in sma}
rows, worst = [], 0.0
for n, inst in enumerate(LAY["instances"]):
    bname = f"{inst['piece']}__{n:03d}"
    bo = B["instances"].get(bname)
    a = by_label.get(bname)
    if bo is None or a is None:
        rows.append({"n": n, "name": bname, "missing": [bo is None, a is None]})
        continue
    bmin, bmax = bo["min"], bo["max"]
    conv = [bmin[0] * 100, -bmax[1] * 100, bmin[2] * 100, bmax[0] * 100, -bmin[1] * 100, bmax[2] * 100]
    err = max(abs(p - q) for p, q in zip(a["bounds"], conv))
    # layout.json placement cross-check (piece + rot) vs Blender object
    rows.append({"n": n, "name": bname, "piece": inst["piece"], "rot_z": float(inst["rot_z"]),
                 "blender_rot": bo["rot_deg"], "ue_yaw": a["rot"][2], "err_cm": err,
                 "ue": [round(x, 3) for x in a["bounds"]], "bl_conv": [round(x, 3) for x in conv],
                 "eval_vs_raw_cm": max(abs(p - q) * 100 for p, q in zip(bo["min"] + bo["max"], bo["raw_min"] + bo["raw_max"]))})
    worst = max(worst, err)
ok_rows = [r for r in rows if "err_cm" in r]
# sample: one per distinct (piece, rot_z), preferring variety; report >= 6 explicitly
seen, sample = set(), []
for r in sorted(ok_rows, key=lambda r: (r["rot_z"] == 0.0, r["piece"])):
    key_p, key_r = r["piece"], r["rot_z"]
    if key_p in {s["piece"] for s in sample}:
        continue
    if len(sample) < 4 and key_r in {s["rot_z"] for s in sample}:
        continue
    sample.append(r)
    if len(sample) >= 10:
        break
g3 = {"tolerance_cm": 1.0, "n_compared": len(ok_rows), "n_missing": len(rows) - len(ok_rows),
      "max_err_cm_all": round(worst, 5), "rot_values": dict(Counter(r["rot_z"] for r in ok_rows)),
      "n_distinct_pieces": len({r["piece"] for r in ok_rows}),
      "max_eval_vs_raw_cm": round(max(r["eval_vs_raw_cm"] for r in ok_rows), 5),
      "sample": [{k: r[k] for k in ("name", "rot_z", "ue_yaw", "err_cm", "ue", "bl_conv")} for r in sample],
      "failures": [r for r in rows if r.get("err_cm", 99) > 1.0]}
g3["n_sample"] = len(sample)
g3["passed"] = g3["n_compared"] == len(LAY["instances"]) and worst <= 1.0 and len(sample) >= 6 \
    and len({s["rot_z"] for s in sample}) >= 3
rep["3_bounds"] = g3

# ---------------------------------------------------------------- gate 4: lights / environment
lights = [(a["label"], a["class"], lc) for a in acts for lc in a["lights"]]
by_type = Counter(lc["class"] for _, _, lc in lights)
local = [(lab, lc) for lab, cls, lc in lights if lc["class"] in ("PointLightComponent", "SpotLightComponent", "RectLightComponent")]
shadow_local = [lab for lab, lc in local if lc["cast_shadows"]]
dirs = [(lab, lc) for lab, cls, lc in lights if lc["class"] == "DirectionalLightComponent"]
sky = [a for a in acts if "skylight" in a]
fog = [a for a in acts if "fog" in a]
ppv = [a for a in acts if "ppv" in a]
lay_types = Counter(l["type"] for l in LAY["lights"])
g4 = {"light_components_by_type": dict(by_type), "n_light_components": len(lights), "layout_light_types": dict(lay_types),
      "n_local": len(local), "shadow_casting_local": len(shadow_local), "shadow_casting_local_labels": shadow_local,
      "zero_intensity": [lab for lab, _, lc in lights if lc["intensity"] <= 0], "invisible": [lab for lab, _, lc in lights if not lc["visible"]],
      "directional": [{"label": lab, **lc} for lab, lc in dirs],
      "skylight": [a["skylight"] for a in sky], "fog": [a["fog"] for a in fog], "ppv": [a["ppv"] for a in ppv],
      "sky_atmosphere": sum(a["class"] == "SkyAtmosphere" for a in acts)}
g4["passed"] = (len(lights) == len(LAY["lights"]) and len(shadow_local) <= 12 and len(dirs) == 1 and len(sky) == 1
                and len(fog) == 1 and fog[0]["fog"]["volumetric"] and len(ppv) >= 1 and not g4["zero_intensity"])
rep["4_lights"] = g4

# ---------------------------------------------------------------- gate 5: project config
def ini(p):
    cp = configparser.RawConfigParser(strict=False, allow_no_value=True, delimiters=("=",))
    cp.optionxform = str
    txt = Path(p).read_text(encoding="utf-8-sig")
    # drop duplicate keys (+/- arrays) problems: keep last
    cp.read_string("\n".join(l for l in txt.splitlines() if not l.strip().startswith(";")))
    return cp


arm = ini(r"C:\Users\Cody\Documents\Unreal Projects\ArmoryLab\Config\DefaultEngine.ini")
dem = ini(r"C:\Users\Cody\Documents\Unreal Projects\DemoGame_1\Config\DefaultEngine.ini")
sec = "/Script/Engine.RendererSettings"
cmp = {}
for k in dem[sec]:
    cmp[k] = [dem[sec][k], arm[sec].get(k)]
rhi = "/Script/WindowsTargetPlatform.WindowsTargetSettings"
cmp["DefaultGraphicsRHI"] = [dem[rhi].get("DefaultGraphicsRHI"), arm[rhi].get("DefaultGraphicsRHI")]
raw_a = Path(r"C:\Users\Cody\Documents\Unreal Projects\ArmoryLab\Config\DefaultEngine.ini").read_text(encoding="utf-8-sig")
raw_d = Path(r"C:\Users\Cody\Documents\Unreal Projects\DemoGame_1\Config\DefaultEngine.ini").read_text(encoding="utf-8-sig")
sm6 = [l for l in raw_d.splitlines() if "D3D12TargetedShaderFormats" in l]
mismatch = {k: v for k, v in cmp.items() if v[0] != v[1]}
gmap = arm["/Script/EngineSettings.GameMapsSettings"].get("GameDefaultMap")
g5 = {"compared": cmp, "mismatch": mismatch, "sm6_lines_demogame": sm6,
      "sm6_lines_present_in_armory": all(l in raw_a.splitlines() for l in sm6), "GameDefaultMap": gmap,
      "runtime_cvars_fresh_process": U["settings"],
      "saved_config_overrides": [str(p) for p in Path(r"C:\Users\Cody\Documents\Unreal Projects\ArmoryLab\Saved\Config").rglob("*Engine.ini")
                                 if "r.Dynamic" in p.read_text(errors="ignore") or "Substrate" in p.read_text(errors="ignore")]}
cv = U["settings"]
g5["passed"] = (not mismatch and g5["sm6_lines_present_in_armory"] and gmap == "/Game/Armory/Maps/L_Armory.L_Armory"
                and cv.get("r.DynamicGlobalIlluminationMethod") == 1 and cv.get("r.ReflectionMethod") == 1
                and cv.get("r.Shadow.Virtual.Enable") == 1 and cv.get("r.Substrate") == 1)
rep["5_config"] = g5
rep["gates"] = {k: rep[k]["passed"] for k in ("1_meshes", "2_level", "3_bounds", "4_lights", "5_config")}
(V / "vf_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
print(json.dumps(rep["gates"]))
for k in ("1_meshes", "2_level", "3_bounds", "4_lights", "5_config"):
    r = {kk: vv for kk, vv in rep[k].items() if kk not in ("rows", "compared", "sample", "materials_used")}
    print(k, json.dumps(r, default=str)[:1500])
