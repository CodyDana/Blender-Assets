"""Assemble WorkFiles/guns/rifle/gates/pack_materials.json (stage 9, the AR-01 in the pack's materials) from the
records this stage wrote: the constants (recolour_constants.json), the pack build (materials/build/), the dump
comparison, the Unreal captures and their analysis (gates/pack_materials_captures*.json).

    py -3 -B WorkFiles/guns/rifle/materials/pack_gates.py
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G = ROOT / "WorkFiles/guns/rifle/gates"
B = HERE / "build"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


const = load(ROOT / "Exports/Guns/AR01/Textures/Recolour/recolour_constants.json")
part = const["parts"]["AR01/Furniture"]
verify = load(B / "verify_ar01_1009b.json")
render = load(B / "render_ar01_1009b.json")
dump = load(HERE / "materials_dump_compare_katana_1003_vs_ar01_1009b.json")
cap = load(G / "pack_materials_captures.json")
cap1 = load(G / "pack_materials_captures_bc1.json")
log = (B / "run_build_ar01_1009b.log").read_text(encoding="utf-8")
c = cap["captures"]
stress = {n: r for n, r in c.items() if "hex" in r}
worst_stress = max(r["vs_twin"]["max"] for r in stress.values())
drift = max(abs(v["luminance_ratio_mip4"] - 1.0) for v in cap["mip_drift"].values())
ar01_inst = {k: v for k, v in verify["instances"].items() if "AR01" in k}
tm = {k.split("/")[-1]: v["memory_bytes"] for k, v in render["texture_memory"].items() if "AR01" in k}

gates = [
    {"name": "S1 constants (maps/derive_constants_ar01.py = derive_constants.fabric_part): default equals the v1 "
             "contract at mip 0 and every mip, guards inactive, mip drift of the fit within 2 %",
     "value": {k: v["pass"] for k, v in part["gates"].items()}, "threshold": "all", "pass": bool(part["pass"])},
    {"name": "S2 spec additions only: the spec without the AR01 keys equals material_spec_before_ar01.json "
             "(add_ar01_to_spec.py projection check); np_spec resolves, every export PNG imported or listed",
     "value": "projection OK; maps_check OK; accounting OK", "threshold": "equal", "pass": True},
    {"name": "S3 pack build run_build.sh ar01_1009b (preflight, maps_check, import_meshes, import_textures, clean, build, "
             "assign, verify): every step passed=True, 0 compile failures",
     "value": {"steps_passed": log.count("passed=True"), "compile_failures_lines": log.count("compile failures: 0")},
     "threshold": "6 Unreal steps passed, 6 x 0 compile failures (+ preflight, maps_check ok)",
     "pass": log.count("passed=True") == 6 and log.count("compile failures: 0") == 6 and "STOP" not in log},
    {"name": "S4 pack verify gates (fresh process): functions, masters, instances, meshes, textures, dependencies, "
             "accounting", "value": verify["gates"], "threshold": "all true", "pass": bool(verify["passed"])},
    {"name": "S5 AR01 instances read back (parent + every effective value), permutations compile",
     "value": {k: {"pass": v["pass"], "ps_instructions": v["statistics"].get("num_pixel_shader_instructions"),
                   "samplers": v["statistics"].get("num_samplers"), "overridden": v["overridden"]}
               for k, v in ar01_inst.items()},
     "threshold": "6 pass", "pass": len(ar01_inst) == 6 and all(v["pass"] for v in ar01_inst.values())},
    {"name": "S6 every other pack entry unchanged: dump katana_1003 (the last pack build) vs ar01_1009b",
     "value": {s: {k: (len(v) if isinstance(v, list) else v) for k, v in dump[s].items()}
               for s in ("functions", "masters", "instances", "meshes", "textures")}
              | {"node_layout_identical": dump["node_layout_identical"]},
     "threshold": "only AR01 entries added; nothing removed or changed; layout identical", "pass": bool(dump["pass"])},
    {"name": "P1 default capture = shipped BC: the shipped MI_AR01_Furniture (baked colours ON) vs "
             "T_AR01_Furniture_BC.png at the measured sample positions",
     "value": {"BC7 (shipped)": c["fur_default"]["vs_BC_png"] | {"dE00": c["fur_default"]["dE00_vs_BC_covered"]},
               "BC1 (measured first)": cap1["captures"]["fur_default"]["vs_BC_png"]
               | {"dE00": cap1["captures"]["fur_default"]["dE00_vs_BC_covered"]}},
     "threshold": "p99.9 <= 2 levels", "pass": bool(c["fur_default"]["gate_p999_le_2"]),
     "note": "FAIL as worded. The shipped default samples the BC itself (no material math: the graph's baked branch is "
             "BaseColourMap.rgb), so this is the block-compression floor of the map, the error the pack reports (not "
             "gates) for every steel BC. BC1 gave p99.9 12 levels (dE00 mean 0.71, p99 2.26); BC7 cut it to 4 "
             "(dE00 mean 0.23, p99 0.92), so the furniture BC ships BC7 (new kind BC_BC7). Only an uncompressed map "
             "(+18.6 MiB) would reach <= 2. The recolour path (P2) meets the pack's default gate."},
    {"name": "P2 the recolour path (switch OFF) at the default Colour vs the pack's float twin",
     "value": c["fur_tint_default"]["vs_twin"], "threshold": "p99.9 <= 1, mean <= 0.3 (pack default gate)",
     "pass": bool(c["fur_tint_default"]["gate_vs_twin"]),
     "note": f"its distance from the BC: p99.9 {c['fur_tint_default']['vs_BC_png_covered']['p99_9']} levels on "
             "covered texels (the four pieces' hue offsets; recolour_precheck.json predicted 33)"},
    {"name": "P3 10-colour stress on the wood (mip 0) vs the twin + the pack's v3 gate",
     "value": {r["hex"]: {"p99_9": r["vs_twin"]["p99_9"], "max": r["vs_twin"]["max"], "v3": r["gate_v3"],
                          "spearman": r["v3"]["spearman_vs_default_capture"], "std_ratio": r["v3"]["std_ratio_logL"],
                          "clip": r["v3"]["clip_frac"]} for r in stress.values()},
     "threshold": "10 colours; p99.9 <= 2; v3 (clip <= 0.1 %, banding, std ratio >= 0.25, Spearman >= 0.98)",
     "pass": bool(cap["gates"]["P3_stress_10_vs_twin"] and cap["gates"]["P3_stress_10_v3"]),
     "worst_level": worst_stress},
    {"name": "P4 mip drift: mip-4 capture mean vs the box-filtered mip-0 capture (11 colours incl. the default)",
     "value": {"worst_abs_ratio_minus_1": round(drift, 5)}, "threshold": "<= 0.02",
     "pass": bool(cap["gates"]["P4_mip_drift_le_2pct"])},
    {"name": "R1 steel sets vs their BC PNGs (BC1; reported, the pack does not gate steel)",
     "value": {"Metal 4096": c["metal_default"]["vs_BC_png"], "Mag 1024": c["mag_default"]["vs_BC_png"]},
     "threshold": "report", "pass": True},
    {"name": "R2 texture memory in Unreal (with mips); Detail16 builds G16 (2 bytes/texel)", "value": tm,
     "threshold": "report; Detail16 ~2.67 B/texel with mips",
     "pass": abs(render["texture_memory"]["/Game/NinjaPack/Textures/Guns/T_AR01_Furniture_Detail16"]
                 ["bytes_per_texel_with_mips"] - 2.6875) < 0.01},
    {"name": "R3 lit Unreal frames of SM_AR01 and SM_AR01_Mag with the pack instances (render ar01_1009b, beauty; "
             "looked at: wood, lacquer and magazine read correctly on all three UV tiles of the twin)",
     "value": {k: list(v.get("frames", {})) for k, v in render["beauty"]["frames"].items() if "AR01" in k},
     "threshold": "rendered, no error", "pass": bool(render["passed"])},
]
doc = {"stage": "9 pack materials (AR01 + AR01_Mag in the NinjaPack masters)", "date": "2026-10-09",
       "engine": verify.get("engine"), "validation_project": "WorkFiles/shuriken/UnrealShuriken (/Game/NinjaPack)",
       "lock": "PackMaterials held by ar01-gun-chat for the whole stage; released at the end",
       "how": "run_build.sh ran from a mirror root (temp folder: copies of main's Scripts/unreal/materials + "
              "Scripts/pipeline with this branch's spec and new script, junctions to main's Exports of the other "
              "pack items and to this worktree's Exports/Guns) so the other items were imported from exactly the "
              "bytes of the last pack build (katana_1003) and nothing in the main checkout's tracked files changed",
       "exports_sha256": {p: sha(ROOT / p) for p in (
           "Exports/Guns/AR01/SK_AR01.fbx", "Exports/Guns/AR01/SM_AR01.fbx", "Exports/Guns/AR01/SM_AR01_Mag.fbx",
           "Exports/Guns/AR01/SK_AR01.skeletal.json", "Exports/Guns/AR01/Textures/T_AR01_Furniture_BC.png",
           "Exports/Guns/AR01/Textures/Recolour/T_AR01_Furniture_Detail16.png",
           "Exports/Guns/AR01/Textures/Recolour/recolour_maps.json",
           "Exports/Guns/AR01/Textures/Recolour/recolour_constants.json")},
       "shipped_colour": {"Colour_linear": part["params"]["Colour"],
                          "Lightest Colour": part["params"]["Lightest Colour"]},
       "gates": gates, "failed": [g["name"] for g in gates if not g["pass"]]}
doc["status"] = "pass" if not doc["failed"] else "fail (see failed + notes)"
(G / "pack_materials.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(doc["status"], [g["name"][:40] for g in gates if not g["pass"]])
