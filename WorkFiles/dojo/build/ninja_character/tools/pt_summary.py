"""Collect the ninja play-test reports (test/<suite>/report_*.json, test/perf/perf_*.json, the log scans, the DemoGame_1
comparison) into test/RESULTS.json + test/RESULTS.md.     py -3 -B pt_summary.py
"""
import json
from pathlib import Path

T = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/test")


def load(p):
    p = T / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def cloth(rep):
    out = {}
    for k, rows in rep["recordings"].items():
        c = [r["cloak"] for r in rows if r.get("cloak")]
        if not c:
            continue
        sim = [x.get("sim_ms") for x in c if x.get("sim_ms") is not None]
        out[k] = {"samples": len(c), "cloths": sorted({x.get("cloths") for x in c}), "dynamic_particles": sorted({x.get("dyn") for x in c}),
                  "suspended": sorted({x.get("suspended") for x in c}), "sim_ms_min_max": [min(sim), max(sim)] if sim else None,
                  "sim_ms_distinct_pct": round(100.0 * len(set(sim)) / len(sim), 1) if sim else None,
                  "half_extent_max_cm": [max(x["ext"][i] for x in c if x.get("ext")) for i in range(3)],
                  "pose_max_delta_cm": max([r["pose"]["max_delta"] for r in rows if r.get("pose")] or [None]),
                  "hand_span_max_cm": max([r["pose"]["span_mh"] for r in rows if r.get("pose")] or [None])}
    return out


def main():
    R = {}
    look = load("look/report_ninja.json")
    if look:
        R["look"] = {"cmc": look["results"]["cmc"], "visual": look.get("visual_at_start"), "cloth": cloth(look),
                     "camera_framing": look["results"].get("look_cam"), "compare_demogame": load("look/compare/compare.json")}
    mv = {"ninja": load("move/report_ninja.json"), "ninja_run2": load("move_run2/report_ninja.json"),
          "gasp": load("move_gasp/report_gasp.json"), "ninja_run3": load("move_run3/report_ninja.json")}
    R["move"] = {}
    for k, v in mv.items():
        if not v:
            continue
        r = v["results"]
        R["move"][k] = {"pawn": v["spawn"]["pawn_class"].split(".")[-1], "cmc": r.get("cmc"), "gaits": r.get("gaits"),
                        "jumps": r.get("jumps"), "cam_idle": r.get("cam_idle"),
                        "cam_run_lateral_abs_max_cm": r.get("cam_run_lateral_abs_max_cm"),
                        "traversal": {t: {x: tv.get(x) for x in ("marker", "marker_top_m", "end_feet_m", "on_top", "rise_cm",
                                                                  "gasp_montages", "pose_max_delta", "span_mh_max")}
                                      for t, tv in (r.get("traversal") or {}).items()}}
    js = {"run1": load("jutsu/report_ninja.json"), "run2": load("jutsu_run2/report_ninja.json")}
    R["jutsu"] = {}
    for k, v in js.items():
        if not v:
            continue
        R["jutsu"][k] = {}
        for name, j in v["results"]["jutsu"].items():
            if name.startswith("warm"):
                continue
            up = [m for m in j["montages"] if m.endswith("@UpperBody")]
            ds = [m for m in j["montages"] if m.endswith("@DefaultSlot")]
            R["jutsu"][k][name] = {
                "upperbody_montages": len(up), "defaultslot_montages": len(ds),
                "seal_events": j["n_seal_events"], "completed_event": j["completed"], "cancelled_event": j["cancelled"],
                "events": [(e["kind"], e["t"]) for e in j["events"]],
                "casting_s": j["casting_from_to"], "finishing_s": j["finishing_from_to"],
                "upper_slot_while_casting": f"{j['upperbody_while_casting']}/{j['cast_rows']}", "seal_weight_max": j["seal_weight_max"],
                "speed_while_casting": j["speed_while_casting_min_max"], "audio": j["audio"],
                "niagara_new": [n for n in j["niagara_new"] if not n.startswith("NS_DKF_")],
                "result_first_last_s": {n: [j["first_seen"][n], j["last_seen"][n]] for n in j["first_seen"] if j["first_seen"][n] is not None},
                "max_counts": j["max_counts"], "pose_max_delta_cm": j["pose_max_delta"], "hand_span_max_cm": j.get("span_mh_max"),
                "duration_game_s": j["duration_game_s"]}
    rts = {"ninja": load("routes/report_ninja.json"), "gasp": load("routes_gasp/report_gasp.json"),
           "ninja_run2": load("routes_run2/report_ninja.json"), "ninja_run3": load("routes_run3/report_ninja.json")}
    R["routes"] = {}
    for k, v in rts.items():
        if not v:
            continue
        r = v["results"]
        rt = r.get("routes", {})
        R["routes"][k] = {"pawn": v["spawn"]["pawn_class"].split(".")[-1], "cmc": {x: r["cmc"].get(x) for x in ("capsule_r", "capsule_hh", "jump_max_count", "max_walk_speed")},
                          "walk_speed": r.get("walk_speed"), "routes": len(rt),
                          "as_expected": sum(1 for x in rt.values() if x["as_expected"]),
                          "not_as_expected": r.get("routes_not_as_expected"),
                          "controls_blocked": f"{sum(1 for n, x in rt.items() if n.startswith('CONTROL') and x['as_expected'])}/{sum(1 for n in rt if n.startswith('CONTROL'))}",
                          "interior": f"{sum(1 for n, x in rt.items() if n.startswith(('ARM_', 'HALL_', 'CONTROL_ARM', 'CONTROL_interior')) and x['as_expected'])}/{sum(1 for n in rt if n.startswith(('ARM_', 'HALL_', 'CONTROL_ARM', 'CONTROL_interior')))}",
                          "br": f"{sum(1 for x in rt.values() if x['mode'] == 'br' and x['as_expected'])}/{sum(1 for x in rt.values() if x['mode'] == 'br')}",
                          "max_dev_clear_m": max([x["max_dev_m"] for x in rt.values() if x["status"] == "reached"] or [None]),
                          "attempt_leaks": r.get("attempt_leaks"),
                          "attempts": {a: {x: av.get(x) for x in ("leak", "end_bl", "max_feet_m", "max_speed", "gasp_montages")}
                                       for a, av in (r.get("attempts") or {}).items()},
                          "route_status": {n: x["status"] for n, x in rt.items()}}
    if "ninja" in R["routes"] and "gasp" in R["routes"]:
        a, b = R["routes"]["ninja"]["route_status"], R["routes"]["gasp"]["route_status"]
        R["routes"]["ninja_vs_gasp_status_differs"] = [n for n in a if n in b and (a[n] == "reached") != (b[n] == "reached")]
    def perf_set(folder):
        perf, agg = {}, {}
        for p in sorted(folder.glob("perf_*.json")):
            v = json.loads(p.read_text(encoding="utf-8"))
            perf[p.stem] = {"pawn": v.get("pawn", "").split(".")[-1], "placements": v.get("placements"),
                            "segments": [{"view": s["view"], "mean_ms": s["frames"]["mean_ms"], "p95_ms": s["frames"]["p95_ms"],
                                          "frames": s["frames"]["n"]} for s in v.get("segments", []) if s.get("frames")]}
            who = "ninja" if "ninja" in p.stem else "gasp"
            for s in perf[p.stem]["segments"]:
                agg.setdefault(s["view"], {}).setdefault(who, []).append((s["mean_ms"], s["p95_ms"]))
        by = {view: {who: {"segments": len(x), "mean_ms_avg": round(sum(m for m, _ in x) / len(x), 2),
                           "p95_ms_avg": round(sum(q for _, q in x) / len(x), 2), "p95_ms_max": max(q for _, q in x),
                           "p95_ms_min": min(q for _, q in x)} for who, x in d.items()} for view, d in agg.items()}
        load = None
        lf = folder / "background_load.csv"
        if lf.exists():
            rows = [ln.split(",") for ln in lf.read_text(encoding="utf-8").splitlines()[1:] if ln.count(",") >= 5]
            num = [r for r in rows if r[1].strip().isdigit() and r[2].strip().isdigit()]
            if num:
                load = {"samples": len(num), "cpu_pct_mean": round(sum(int(r[1]) for r in num) / len(num), 1),
                        "gpu_util_pct_mean": round(sum(int(r[2]) for r in num) / len(num), 1),
                        "gpu_util_pct_max": max(int(r[2]) for r in num),
                        "blender_procs_max": max(int(r[4]) for r in num)}
        return perf, by, load
    R["perf"], R["perf_by_view"], R["perf_background_load"] = perf_set(T / "perf")
    _, R["perf_contaminated_by_view"], R["perf_contaminated_load"] = perf_set(T / "perf" / "contaminated_run1")
    scans = {}
    for p in sorted((T / "logs").glob("scan_*.json")):
        v = json.loads(p.read_text(encoding="utf-8"))
        scans[p.stem] = {"totals": v["totals"], "windows_with_lines": {w: c for w, c in v["windows"].items() if c and w != "startup"},
                         "unique_ensure_error": (v["unique"].get("ensure", []) + v["unique"].get("error", []))[:6]}
    R["log_scans"] = scans
    (T / "RESULTS.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    # markdown
    L = ["# Ninja play tests: results (generated by tools/pt_summary.py)", ""]
    for key, title in (("perf_by_view", "idle machine"), ("perf_contaminated_by_view", "CONTAMINATED (other chat's renders)")):
        if R.get(key):
            L += [f"Perf, {title}; load {R.get('perf_background_load' if key == 'perf_by_view' else 'perf_contaminated_load')}", "",
                  "| view | pawn | segments | mean ms | p95 ms (avg) | p95 ms (min / max) |", "|---|---|---|---|---|---|"]
            for view, d in R[key].items():
                for who, x in d.items():
                    L.append(f"| {view} | {who} | {x['segments']} | {x['mean_ms_avg']} | {x['p95_ms_avg']} | {x['p95_ms_min']} / {x['p95_ms_max']} |")
            L.append("")
    for k, v in R["routes"].items():
        if isinstance(v, dict):
            L.append(f"- routes {k}: {v['as_expected']}/{v['routes']} as expected, CONTROLs {v['controls_blocked']}, interior "
                     f"{v['interior']}, BR {v['br']}, attempt leaks {v['attempt_leaks']}, not as expected {v['not_as_expected']}")
    (T / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
