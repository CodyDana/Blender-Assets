"""Compare the AR-01 regression outputs (ar01_regression.sh, gunlib 0.2.0 drivers) with the committed AR-01 gate values
and write WorkFiles/guns/smg/gates/gunlib_regression.json (plain Python).

Equality is EXACT (every number to the bit, every string) except the keys listed in IGNORE: wall-clock seconds, image
and blend paths (the regression writes its images into its own folder and opens copies of the blends), and text the
promoted driver words generically where the AR-01 wording named a script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
from gunlib import LIB_VERSION  # noqa: E402

W = ROOT / "WorkFiles" / "guns" / "rifle"
R = ROOT / "WorkFiles" / "guns" / "smg" / "scratch" / "regression"
OUT = ROOT / "WorkFiles" / "guns" / "smg" / "gates" / "gunlib_regression.json"
IGNORE = {"seconds", "image", "blend"}


def j(p):
    return json.loads(Path(p).read_text())


def diff(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE:
                continue
            if k not in a or k not in b:
                out.append({"path": f"{path}/{k}", "new": a.get(k, "<missing>"), "committed": b.get(k, "<missing>")})
            else:
                diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append({"path": path, "new": f"list[{len(a)}]", "committed": f"list[{len(b)}]"})
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append({"path": path, "new": a, "committed": b})
    return out


checks = []


def check(stage, name, new, committed, new_src, committed_src, note=None):
    d = diff(new, committed)
    c = {"stage": stage, "name": name, "new": new_src, "committed": committed_src, "equal": not d,
         "mismatches": len(d), "first_mismatches": d[:12]}
    if note:
        c["note"] = note
    checks.append(c)
    print(("EQUAL   " if not d else "DIFFER  ") + f"[{stage}] {name}" + ("" if not d else f" ({len(d)})"))
    return c


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def main():
    form = j(W / "gates" / "form.json")
    det = form["details"]
    # ------------------------------------------------------------------ stage 2 (form)
    if (R / "b3_result.json").exists():
        check(2, "B3 motion sweeps + G5 static + contact gaps (LOD0)", j(R / "b3_result.json"), det["B3"],
              rel(R / "b3_result.json"), "WorkFiles/guns/rifle/gates/form.json details.B3")
        check(2, "B6a joined twin + B10 deny list", j(R / "b6a_result.json"), det["B6a"], rel(R / "b6a_result.json"),
              "form.json details.B6a")
        check(2, "L3 features + L4 dimensions (measure)", j(R / "measure_result.json"), det["measure"],
              rel(R / "measure_result.json"), "form.json details.measure")
        check(2, "B4 sight picture (notch, occlusion-aware)", j(R / "b4_result.json"), det["B4"],
              rel(R / "b4_result.json"), "form.json details.B4")
        check(2, "form_magfit F1-F8 (rock path)", j(R / "form_magfit.json"), j(W / "gates" / "form_magfit.json"),
              rel(R / "form_magfit.json"), "WorkFiles/guns/rifle/gates/form_magfit.json")
        # the form.json gate records these feed
        fg = {g["name"]: g for g in form["gates"]}
        b3 = j(R / "b3_result.json")
        rows = []
        for grp, d in b3["groups"].items():
            sm = d["summary"]
            nm = "B3 %s sweep %s..%s (step %.4f, %d steps)" % (grp, sm["range"][0], sm["range"][1], sm["step"], sm["steps"])
            v = {"intersecting_steps": sm["intersecting_steps"], "min_clearance_mm": sm["min_clearance_mm"],
                 "min_with": sm["min_with"], "rest_mm": sm["rest_clearance_mm"], "end_mm": sm["end_clearance_mm"]}
            rows.append((nm, v, sm["pass"]))
        b4 = j(R / "b4_result.json")
        rows.append(("B4 sight picture (ADS 55 deg, eye 0.25 m behind Sight on its line, occlusion-aware raster)",
                     {"lateral_mm": b4["lateral_offset_mm"], "vertical_mm": b4["vertical_offset_mm"],
                      "post_visible_in_notch_mm": b4["post"]["visible_height_in_notch_mm_at_notch"],
                      "occluders": b4["occluders_in_notch_px"]}, b4["pass"]))
        b6 = j(R / "b6a_result.json")
        rows.append(("B6a joined twin: qa_check topology + degenerate checks", b6["passed"], b6["passed"]))
        for x in j(R / "form_magfit.json")["gates"]:
            rows.append(("MAGFIT " + x["name"], x["value"], x["pass"]))
        new = {n: {"value": v, "pass": p} for n, v, p in rows}
        com = {n: {"value": fg[n]["value"], "pass": fg[n]["pass"]} if n in fg else "<missing>" for n, _, _ in rows}
        check(2, "form.json gate records (B3 x5, B4, B6a, MAGFIT F1-F8)", new, com, "rebuilt from the outputs above",
              "form.json gates")
    # ------------------------------------------------------------------ stage 4 (game)
    if (R / "game" / "viewgates.json").exists():
        check(4, "LOD-pop + S2 at LOD0-3 (viewgates)", j(R / "game" / "viewgates.json"),
              j(W / "scratch" / "game" / "viewgates.json"), rel(R / "game" / "viewgates.json"),
              "WorkFiles/guns/rifle/scratch/game/viewgates.json (fed gates/game.json)")
        check(4, "LOD screen sizes", j(R / "game_lod_sizes.json"), j(W / "gates" / "game_lod_sizes.json"),
              rel(R / "game_lod_sizes.json"), "WorkFiles/guns/rifle/gates/game_lod_sizes.json")
        g5n, g5c = j(R / "game" / "g5_lods.json"), j(W / "scratch" / "game" / "g5_lods.json")
        check(4, "G5 at LOD2-3 (penetration px)", {k: g5n[k] for k in ("rule", "lods", "pass")},
              {k: g5c[k] for k in ("rule", "lods", "pass")}, rel(R / "game" / "g5_lods.json"),
              "WorkFiles/guns/rifle/scratch/game/g5_lods.json (rule, lods, pass; its 'visible' block is "
              "rifle_g5_visible.py's, not a promoted driver)")
        check(4, "B3 + G5 at LOD1", j(R / "b3_lod1.json"), j(W / "scratch" / "b3_lod1.json"), rel(R / "b3_lod1.json"),
              "WorkFiles/guns/rifle/scratch/b3_lod1.json")
        check(4, "G5 at LOD0 on the shipped (triangulated) parts", j(R / "b3_lod0_tri.json"),
              j(W / "scratch" / "b3_lod0_tri.json"), rel(R / "b3_lod0_tri.json"),
              "WorkFiles/guns/rifle/scratch/b3_lod0_tri.json")
        # the game.json gate values (rifle_stage34_gates.stage4's formulas on the new outputs)
        game = j(W / "gates" / "game.json")
        gg = {g["name"]: g for g in game["gates"]}
        vg, b3 = j(R / "game" / "viewgates.json"), j(R / "b3_lod1.json")
        b30 = j(R / "b3_lod0_tri.json")
        rows = [("G5 at LOD0 on the shipped (triangulated) parts", f"{len(b30['static_intersections'])} intersecting "
                 f"pairs; min butt gap {min(x['min_gap_mm'] for x in b30['contact_gaps'])} mm"),
                ("B3 at LOD1 (moving parts, sweep)", {g: {"intersecting_steps": v["summary"]["intersecting_steps"],
                                                         "min_clearance_mm": v["summary"]["min_clearance_mm"]}
                                                     for g, v in b3["groups"].items()}),
                ("G5 at LOD1 (static intersecting pairs)", len(b3["static_intersections"])),
                ("G5 at LOD1 butt-joint gaps", min(x["min_gap_mm"] for x in b3["contact_gaps"]))]
        for k, v in g5n["lods"].items():
            rows.append((f"G5 at {k} (study B3/G5 R5: penetration depth projected at the switch-in distance)",
                         f"{v['intersecting_pairs']} intersecting pairs; deepest penetration {v['worst_depth_px']} px "
                         f"at {v['distance_m']} m ({v['pairs'][0]['a']}/{v['pairs'][0]['b']} "
                         f"{v['pairs'][0]['depth_mm']} mm)" if v["pairs"] else "0 intersecting pairs"))
        s2 = vg["s2"]
        rows.append(("S2 sight picture at LOD0 (B4 method: post tip level with the notch top, R48)",
                     f"lateral {s2.get('lateral_offset_px')} px, vertical {s2.get('vertical_offset_px')} px"))
        for k, v in vg["s2_lods"].items():
            rows.append((f"S2 sight picture at {k}", "n/a" if v.get("pass") is None else
                         f"lateral {v.get('lateral_offset_px')} px, vertical {v.get('vertical_offset_px')} px"))
        for sw in vg["lod_pop"]["switches"]:
            t = sw["tries"][-1]
            rows.append((f"LOD-pop LOD{sw['from']} -> LOD{sw['to']}", f"size {sw['chosen_screen_size']} "
                         f"({t['distance_m']} m): mean {t['worst_mean_px']} px, max {t['worst_max_px']} px "
                         "(worst of 4 headings)"))
        new = {n: v for n, v in rows}
        com = {n: gg[n]["value"] if n in gg else "<missing>" for n, _ in rows}
        check(4, "game.json gate values (G5 LOD0-3, B3 LOD1, S2 LOD0-3, LOD-pop)", new, com,
              "rebuilt from the outputs above with rifle_stage34_gates.stage4's formulas", "WorkFiles/guns/rifle/gates/game.json")
    # ------------------------------------------------------------------ stage 5 (rig + export)
    if (R / "rig_export.json").exists():
        check(5, "rig_export (B1-B5, clips, S1, sha256, B10) on the shipped bytes", j(R / "rig_export.json"),
              j(W / "gates" / "rig_export.json"), rel(R / "rig_export.json"), "WorkFiles/guns/rifle/gates/rig_export.json")
    # ------------------------------------------------------------------ stage 6 (mag fit)
    if (R / "mag.json").exists():
        check(6, "mag fit M1-M8 + the mag build gates on the shipped bytes", j(R / "mag.json"), j(W / "gates" / "mag.json"),
              rel(R / "mag.json"), "WorkFiles/guns/rifle/gates/mag.json",
              "stage 6 is beyond the W1a scope (2/4/5); run because mag_fit is a promoted driver too")
    # ------------------------------------------------------------------ bytes
    def shas(p):
        out = {}
        for line in Path(p).read_text().splitlines():
            h, f = line.split(None, 1)
            out[f.lstrip("*").strip()] = h
        return out
    eb, ea = shas(R / "exports_sha256_before.txt"), shas(R / "exports_sha256_after.txt")
    e0 = shas(ROOT / "WorkFiles" / "guns" / "smg" / "scratch" / "regression" / "ar01_exports_sha256_before.txt") \
        if (R / "ar01_exports_sha256_before.txt").exists() else eb
    rig = j(W / "gates" / "rig_export.json")
    magj = j(W / "gates" / "mag.json")
    recorded = {**{k: v["sha256"] for k, v in rig["files"].items()},
                **{k: v["sha256"] for k, v in magj["files"].items() if not k.endswith("(input)")}}
    rec_ok = all(ea.get(k) == v for k, v in recorded.items())
    # (SMG01 W4 resume) the AR-01's own blends only: 'Assets/Guns' as a whole also matched the SMG01 build's own
    # Assets/Guns/SMG01.blend (modified by every SMG01 run) and failed the AR-01 bytes row falsely
    git = subprocess.run(["git", "status", "--porcelain", "--", "Exports/Guns/AR01", "Assets/Guns/AR01.blend",
                          "Assets/Guns/AR01_Mag.blend", "WorkFiles/guns/rifle"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
    tracked_changes = [x for x in git if not x.startswith("??")]
    ib, ia = shas(R / "inputs_sha256_before.txt"), shas(R / "inputs_sha256_after.txt")
    bytes_ = {"exports_files": len(ea), "exports_unchanged_during_run": eb == ea,
              "exports_unchanged_since_session_start": e0 == ea,
              "exports_equal_recorded_build_sha256 (rig_export.json + mag.json files)": rec_ok,
              "recorded_files_checked": len(recorded),
              "input_blends_unchanged": ib == ia,
              "git_tracked_changes_under_Exports_AR01_Assets_Guns_WorkFiles_guns_rifle": tracked_changes}
    ok_bytes = eb == ea and e0 == ea and rec_ok and ib == ia and not tracked_changes
    # ------------------------------------------------------------------ the new modules (gunlib 0.2.0)
    new_mod = {}
    pt = R / "parts_test.json"
    if pt.exists():
        d = j(pt)
        # (SMG01 W4 resume) a test process that ended before its final write leaves no status: report it, do not crash
        new_mod["test_parts"] = {"status": d.get("status", "incomplete: no final record (the test process ended early)"),
                                 "failed": d.get("failed", ["incomplete"]),
                                 "checks": [{"name": c["name"], "pass": c["pass"], "threshold": c["threshold"]}
                                            for c in d["checks"]],
                                 "rail_measured": d.get("rail", {}).get("measured", {}),
                                 "magfit_straight": {n: v["value"] for n, v in d.get("magfit_straight", {}).items()},
                                 "triangles_per_level": {k: {n: p["triangles"] for n, p in v["parts"].items()}
                                                         for k, v in d.get("levels", {}).items()},
                                 "file": rel(pt)}
    from gunlib import standard as STD
    new_mod["standard_vs_rig_bone_table"] = STD.check_against_rig()
    ua = R / "ud_ar01_form.json"
    if ua.exists():
        d = j(ua)
        new_mod["ud_on_ar01_form_parts (info)"] = {"gates": d["gates"], "file": rel(ua),
                                                   "note": "information: the AR-01 predates UD1-UD2 (its stage-8 Unreal "
                                                           "import dropped 4,584 triangles, U5; U10 zero tangents); "
                                                           "the SMG gates it from the form stage"}
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    stages = sorted({c["stage"] for c in checks})
    failed = [f"[{c['stage']}] {c['name']}" for c in checks if not c["equal"]]
    if new_mod.get("test_parts", {}).get("status") != "pass":
        failed.append("gunlib 0.2.0 new-module tests (test_parts.py)")
    if not new_mod["standard_vs_rig_bone_table"]["equal"]:
        failed.append("gun_standard.json bone table != gunlib.rig.STANDARD_BONES")
    if not ok_bytes:
        failed.append("AR-01 export / input bytes")
    need = {2, 4, 5}
    missing = sorted(need - set(stages))
    if missing:
        failed.append(f"stages not run: {missing}")
    res = {"gate": "gunlib_regression (SMG_BUILD_PLAN 15 W1a; spec gunlib_additions_W1a.regression)",
           "date": datetime.now().isoformat(timespec="seconds"), "lib_version": LIB_VERSION, "start_commit": "c70cc918",
           "head": head, "status": "pass" if not failed else "fail", "failed": failed,
           "rule": "the AR-01's stage-2/4/5 gate drivers re-run through the promoted gunlib.drivers (rifle_* shims + "
                   "rifle_gun.CFG) reproduce the committed values EXACTLY (every number to the bit; ignored keys: "
                   "%s); the AR-01 export bytes stay unchanged (sha256 before = after = the build's recorded "
                   "sha256; nothing re-exported)" % ", ".join(sorted(IGNORE)),
           "method": "Scripts/guns/gunlib/tests/ar01_regression.sh: the stage-2 drivers on a COPY of "
                     "WorkFiles/guns/rifle/scratch/AR01_form_stage.blend (the gated form-stage blend form.json was "
                     "measured on), b4 / viewgates on the committed triangle dumps (scratch/form_tris.npz, "
                     "scratch/game/lod<k>_tris.npz), G5 / B3 LOD1 / LOD0-tri on a COPY of Assets/Guns/AR01.blend, "
                     "rig_verify and mag_fit on the shipped Exports/Guns/AR01 bytes in fresh processes; every output "
                     "in WorkFiles/guns/smg/scratch/regression/ (gitignored)",
           "stages_run": stages, "checks": checks, "bytes": bytes_, "new_modules": new_mod,
           "drivers": ["gunlib.drivers.b3", "gunlib.drivers.b4", "gunlib.drivers.b6a", "gunlib.drivers.measure",
                       "gunlib.drivers.magfit_check", "gunlib.drivers.viewgates", "gunlib.drivers.g5_lods",
                       "gunlib.drivers.rig_verify", "gunlib.drivers.mag_fit"],
           "config": "Scripts/guns/rifle/rifle_gun.py (+ rifle_gun_measure.py, rifle_gun_magfit.py)"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print("[regression]", res["status"], failed)


if __name__ == "__main__":
    main()
