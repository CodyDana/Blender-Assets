"""Assemble WorkFiles/guns/sniper/gates/pack_materials.json (the SR-01 in the pack's materials) from the records the
build wrote: the constants, the pack build (WorkFiles/guns/sniper/pack/build/, copied out of the mirror by
run_pack_build.sh), the dump comparison against the last build's dump, the Unreal captures' analysis
(gates/pack_materials_captures.json) and the 8-bit floor check of the near-black stress colours (the pack's own twin).
WorkFiles/guns/smg/materials/pack_gates.py + dump_compare_smg01.py adapted.

    py -3 -B WorkFiles/guns/sniper/pack/sr01_pack_gates.py <tag> <reference dump.json> [--pack-dir <mirror pack dir>]

Exit 0 when every blocking gate passes (P3b may fail only if the 8-bit floor explains it, as on the SMG), else 1.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ARGS = sys.argv[1:]
TAG = ARGS[0]
REF_DUMP = Path(ARGS[1])
PACK = Path(ARGS[ARGS.index("--pack-dir") + 1]) if "--pack-dir" in ARGS else ROOT / "Scripts/unreal/materials"
G = ROOT / "WorkFiles/guns/sniper/gates"
B = HERE / "build"
E = ROOT / "Exports/Guns/SR01"
ALLOWED = ("SR01", "Att_Scope_LongRange")
sys.path.insert(0, str(PACK / "maps"))
sys.path.insert(0, str(PACK))
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rank(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def floor_check(const):
    """Spearman of log luminance, colour vs default, of the pack's float twin, unquantised and after the 8-bit sRGB
    store: if the 8-bit twin misses 0.98 too, a capture's miss is the output's quantisation at the black floor."""
    out = {}
    p = const["parts"]["SR01/Chassis"]["params"]
    d16, _, _ = rc.png_read(E / "Textures/Recolour/T_SR01_Chassis_Detail16.png")
    v, n = np.unique(d16, return_counts=True)
    d = (d16 / 65535.0)[d16 != v[np.argmax(n)]]
    a0, _ = tw.fabric_albedo(p, d, np.asarray(p["Colour"][:3]), lod=0.0)
    for hx in ("000000", "1A1A1A", "808080"):
        col = [float(rc.s2l(int(hx[i:i + 2], 16) / 255.0)) for i in (0, 2, 4)]
        a, _ = tw.fabric_albedo(p, d, np.asarray(col), lod=0.0)
        r = {}
        for q in (False, True):
            A = rc.s2l(rc.q8_srgb(a) / 255.0) if q else a
            B0 = rc.s2l(rc.q8_srgb(a0) / 255.0) if q else a0
            la = np.log(np.maximum(A @ rc.LUM, 1e-7))[::7]
            lb = np.log(np.maximum(B0 @ rc.LUM, 1e-7))[::7]
            r["8bit" if q else "float"] = round(float(np.corrcoef(rank(la), rank(lb))[0, 1]), 4)
        r["mean_srgb_level"] = round(float(rc.q8_srgb(a).mean()), 1)
        out[f"chassis_{hx}"] = r
    return out


def dump_compare(a_path, b_path):
    A, Bd = load(a_path), load(b_path)
    secs = ("functions", "masters", "instances", "meshes", "textures")
    res = {"before": str(a_path), "after": str(b_path), "allowed_additions": ALLOWED}
    for sec in secs:
        a, b = A[sec], Bd[sec]
        res[sec] = {"before": len(a), "after": len(b), "added": sorted(set(b) - set(a)),
                    "removed": sorted(set(a) - set(b)),
                    "changed": sorted(k for k in set(a) & set(b)
                                      if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True))}
    la = load(Path(a_path).with_name(Path(a_path).name.replace("dump_", "dump_layout_")))
    lb = load(Path(b_path).with_name(Path(b_path).name.replace("dump_", "dump_layout_")))
    res["node_layout_identical"] = la == lb
    added = [k for s in secs for k in res[s]["added"]]
    res["added_sr01"] = {s: len(res[s]["added"]) for s in secs}
    res["added_all_allowed"] = all(any(t in k for t in ALLOWED) for k in added)
    res["nothing_removed_or_changed"] = not any(res[s]["removed"] or res[s]["changed"] for s in secs)
    res["pass"] = bool(res["added_all_allowed"] and res["nothing_removed_or_changed"] and res["node_layout_identical"])
    return res


const = load(E / "Textures/Recolour/recolour_constants.json")
verify = load(B / f"verify_{TAG}.json")
render = load(B / f"render_{TAG}.json")
imp = load(B / f"import_meshes_{TAG}.json")
imt = load(B / f"import_textures_{TAG}.json")
cap = load(G / "pack_materials_captures.json")
log = (B / f"run_build_{TAG}.log").read_text(encoding="utf-8")
w5 = load(ROOT / "WorkFiles/guns/sniper/UnrealCheck/verification_summary.json")["sha256"]
spec = load(ROOT / "Scripts/unreal/materials/material_spec.json")
dump = dump_compare(REF_DUMP, B / f"dump_{TAG}.json")
(HERE / f"materials_dump_compare_{REF_DUMP.stem.replace('dump_', '')}_vs_{TAG}.json").write_text(
    json.dumps(dump, indent=1), encoding="utf-8")
c = cap["captures"]
cg = cap["gates"]
inst = {k: v for k, v in verify["instances"].items() if any(t in k for t in ALLOWED)}
sr_tex = {k: v for k, v in imt["textures"].items() if any(t in k for t in ALLOWED)}
tm = {k.split("/")[-1]: v["memory_bytes"] for k, v in render["texture_memory"].items() if any(t in k for t in ALLOWED)}
floor = floor_check(const)
v3_fail = cap["sets"]["chassis"]["gates"]["P3b_v3_failures"]
floor_explains = all(floor.get(f"chassis_{hx}", {}).get("8bit", 1.0) < 0.98 and
                     floor.get(f"chassis_{hx}", {}).get("float", 0.0) >= 0.999 for hx in v3_fail)
sk = imp["meshes"]["SK_SR01"]
MESHES = ("SK_SR01", "SM_SR01", "SM_SR01_Mag", "SM_Att_Scope_LongRange")
fbx_w5 = {m: imp["meshes"][m]["fbx_sha256"] == w5.get(f"{m}.fbx") for m in MESHES if m in imp["meshes"]}
side = load(E / "SK_SR01.skeletal.json")
n_sock = len(side.get("sockets", [])) if isinstance(side.get("sockets"), list) else None
n_tex_expected = len(sr_tex)
steps = "preflight maps_check import_meshes import_textures clean build assign verify render".split()
ue_steps = steps[2:]

gates = [
    {"name": "S1 constants (maps/derive_constants_sr01.py = derive_constants.fabric_part, run from the mirror on main's "
             "LF bytes of the pack code): default equals the v1 contract at mip 0 and every mip, guards inactive, mip "
             "drift of the fit within 2 %", "blocking": True,
     "value": {k: {g: x["pass"] for g, x in v["gates"].items()} for k, v in const["parts"].items()},
     "twin_sha256": const["generator"]["twin_sha256"], "threshold": "all", "pass": bool(const["pass"])},
    {"name": "S2 spec additions only: the spec without the SR01 keys equals material_spec_before_sr01.json "
             "(add_sr01_to_spec.py projection check, re-run by run_pack_build.sh); preflight + maps_check OK",
     "blocking": True, "value": "checked by run_pack_build.sh before the build (stops otherwise)",
     "threshold": "equal", "pass": True},
    {"name": f"S3 pack build run_build.sh {TAG} ({', '.join(steps)}) from the short-path mirror: every Unreal step "
             "passed=True, 0 compile failures", "blocking": True,
     "value": {"steps_passed": log.count("passed=True"), "compile_failures_0_lines": log.count("compile failures: 0"),
               "STOP_in_log": "STOP" in log},
     "threshold": f"{len(ue_steps)} Unreal steps passed, {len(ue_steps)} x 0 compile failures",
     "pass": log.count("passed=True") == len(ue_steps) and log.count("compile failures: 0") == len(ue_steps)
     and "STOP" not in log},
    {"name": "S4 pack verify gates (fresh process): functions, masters, instances, meshes, textures, dependencies, "
             "accounting", "blocking": True, "value": verify["gates"], "threshold": "all true",
     "pass": bool(verify["passed"])},
    {"name": "S5 SR01 + scope instances read back (parent + every effective value), permutations compile",
     "blocking": True,
     "value": {k: {"pass": v["pass"], "ps_instructions": v["statistics"].get("num_pixel_shader_instructions"),
                   "samplers": v["statistics"].get("num_samplers"), "overridden": v["overridden"]}
               for k, v in inst.items()},
     "threshold": "10 pass", "pass": len(inst) == 10 and all(v["pass"] for v in inst.values())},
    {"name": f"S6 every other pack entry unchanged: dump {REF_DUMP.name} (the last pack build) vs dump_{TAG}",
     "blocking": True,
     "value": {s: {k: (len(v) if isinstance(v, list) else v) for k, v in dump[s].items()}
               for s in ("functions", "masters", "instances", "meshes", "textures")}
     | {"node_layout_identical": dump["node_layout_identical"], "added": dump["added_sr01"]},
     "threshold": f"only SR01 / scope entries added (10 instances, 4 meshes, {n_tex_expected} textures); nothing "
                  "removed or changed; node layout identical",
     "pass": bool(dump["pass"]) and dump["added_sr01"]["instances"] == 10 and dump["added_sr01"]["meshes"] == 4
     and dump["added_sr01"]["textures"] == n_tex_expected
     and dump["added_sr01"]["functions"] == 0 and dump["added_sr01"]["masters"] == 0},
    {"name": "S7 SK_SR01 imported by the pack's skeletal path from the W5-verified bytes: 4 LODs, sockets as the "
             "sidecar (20), 8 clips, PHYS_SR01, bounds extension; every SR01 FBX = the W5 bytes", "blocking": True,
     "value": {"lods": sk["lod_count"], "sockets": len(sk["sockets"]), "sidecar_sockets": n_sock,
               "clips": len(sk["animations"]), "physics": sk["physics"].get("applied"),
               "bounds_extension_cm": sk["bounds_extension_cm"], "lod_sizes": sk["lod_settings"].get("sizes"),
               "fbx_sha_equals_W5": fbx_w5},
     "threshold": "as the sidecar; bytes = W5",
     "pass": sk["lod_count"] == 4 and len(sk["sockets"]) == 20 and len(sk["animations"]) == 8
     and len(fbx_w5) == 4 and all(fbx_w5.values())},
    {"name": "P1 default capture = shipped BC: MI_SR01_Chassis (baked colours ON) and MI_SR01_Mag vs the BC PNG at the "
             "measured sample positions (the other compression measured beside it)", "blocking": True,
     "value": {s: {"shipped": c[f"{s}_default"]["compression"],
                   "shipped_vs_BC": c[f"{s}_default"]["vs_BC_png"] | {"dE00": c[f"{s}_default"]["dE00_vs_BC"]},
                   "alt": c.get(f"{s}_default_alt", {}).get("compression"),
                   "alt_vs_BC": c.get(f"{s}_default_alt", {}).get("vs_BC_png")} for s in ("chassis", "mag")},
     "threshold": "p99.9 <= 2 levels (shipped)", "pass": bool(cg["P1_pass"]),
     "note": "if the shipped kind is BC7 and the BC1 alt also meets p99.9 <= 2, the BC1 kind may be chosen (saves "
             "memory): re-run add_sr01_to_spec.py --bc-kind BC / --mag-bc-kind BC and rebuild. If the shipped kind is "
             "BC1 and misses, use BC7 (the plan's fallback)"},
    {"name": "P2 the chassis recolour path (switch OFF) at the default Colour vs the pack's float twin, OD texels",
     "blocking": True, "value": c["chassis_tint_default"]["vs_twin"],
     "threshold": "p99.9 <= 1, mean <= 0.3", "pass": bool(cg["P2_recolour_default_equals_twin"]),
     "note": "its distance from the BC on the OD (detail size): p99.9 "
             f"{c['chassis_tint_default']['vs_BC_png_covered_at_detail_size']['p99_9']} levels (why the default ships "
             "the baked BC, D1-a)"},
    {"name": "P3a 13-colour stress (10 + tan C2B280 / OD 4B5320 / FDE B08D57) on the chassis OD texels (mip 0) vs the "
             "twin", "blocking": True,
     "value": {r["hex"]: r["vs_twin"]["p99_9"] for n, r in c.items() if n.startswith("chassis_") and "hex" in r},
     "threshold": "p99.9 <= 1 level per colour, 13 captures", "pass": bool(cg["P3a_stress_vs_twin_le_1"]),
     "worst_level": cg["worst_stress_twin_level_p999"]},
    {"name": "P3b the pack's v3 gate on the same 13 captures (clip <= 0.1 %, banding, std ratio >= 0.25, Spearman vs "
             "the default capture >= 0.98): reported; a near-black Spearman miss the 8-bit twin also shows is the "
             "pack's known floor", "blocking": False,
     "value": {"failures": v3_fail, "floor_check_twin_spearman": floor},
     "threshold": "13 pass", "pass": bool(cg["P3b_stress_v3"]), "explained_by_8bit_floor": floor_explains},
    {"name": "P4 mip drift: mip-4 capture mean vs the box-filtered mip-0 capture (14 colours incl. the default)",
     "blocking": True, "value": {"worst_abs_ratio_minus_1": cg["worst_mip_drift"]}, "threshold": "<= 0.02",
     "pass": bool(cg["P4_mip_drift_le_2pct"])},
    {"name": "R1 steel sets vs their BC PNG (BC1; reported, the pack does not gate steel)", "blocking": False,
     "value": {k: c[f"{k}_default"]["vs_BC_png"] for k in ("metal", "scope_body", "scope_lens")},
     "threshold": "report", "pass": True},
    {"name": "R2 texture memory in Unreal (with mips)", "blocking": False, "value": tm,
     "total_MiB": round(sum(tm.values()) / 2 ** 20, 2), "threshold": "report", "pass": True},
    {"name": f"R3 lit Unreal frames (render {TAG}): LOOK AT THEM before merging (the twin's three UV tiles resolve; "
             "scope on the rail)", "blocking": False,
     "value": {k: list(v.get("frames", {})) for k, v in render["beauty"]["frames"].items()
               if any(t in k for t in ALLOWED)},
     "threshold": "rendered, no error; looked at by the main chat", "pass": bool(render["passed"])},
]
blocking_failed = [g["name"] for g in gates if g["blocking"] and not g["pass"]]
p3b = next(g for g in gates if g["name"].startswith("P3b"))
doc = {"stage": "SR-01 pack colours (SR01 + SR01_Static + SR01_Mag + Att_Scope_LongRange in the NinjaPack masters; "
                "option D1-a)", "tag": TAG, "engine": verify.get("engine"),
       "validation_project": "WorkFiles/shuriken/UnrealShuriken (/Game/NinjaPack)",
       "lock": "PackMaterials, owner sr01-pack (run_build.sh ran with NP_OWNER=sr01-pack)",
       "how": "run_pack_build.sh: make_mirror.py (copies of main's Scripts/unreal/materials + Scripts/pipeline with this "
              "branch's spec and derive_constants_sr01.py; junctions to main's Exports of the other items, checked "
              "against the last import records, and to this worktree's Exports/Guns/SR01), run_build.sh from the "
              "mirror, the captures and this file",
       "reference_dump": str(REF_DUMP),
       "exports_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(
           [*E.glob("*.fbx"), E / "SK_SR01.skeletal.json", *E.glob("Textures/*_BC.png"),
            *E.glob("Textures/Recolour/*")])},
       "shipped_colour": {k: {"Colour_linear": v["params"]["Colour"]} for k, v in const["parts"].items()},
       "gates": gates, "blocking_failed": blocking_failed,
       "reported_failed": [g["name"] for g in gates if not g["blocking"] and not g["pass"]]}
doc["status"] = "fail (see blocking_failed)" if blocking_failed else (
    "pass" if p3b["pass"] else
    "pass (P3b Spearman at near black = the pack's known 8-bit floor, proven on the twin)" if floor_explains else
    "pass on the blocking gates; P3b v3 failure NOT explained by the 8-bit floor: look before merging")
G.mkdir(parents=True, exist_ok=True)
(G / "pack_materials.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(doc["status"], blocking_failed)
sys.exit(1 if blocking_failed else 0)
