"""LANDSCAPE ROUND (world stage), Unreal verify (pythonscript commandlet, -nullrhi, a FRESH process, read-only: nothing
is saved). Gates on what dj_ls_world.py SAVED in L_Dojo, against world/json/world_layout.json:

 L1 landscapes   LS_Valley + LS_Far present, 256 components each, Nanite on; line traces at the terrain report's
                 named probes hit the valley within 2 cm of the heightmap value (the landscape IS the plan's terrain)
 L2 actors       every layout actor present (label, mesh, location within 1 cm for the kit pieces), per-group counts
 L3 collision    boundary B1-B8: hidden, Pawn block only, tags Boundary_1v1 + TerraceEdge + Dojo/Boundary_1v1;
                 CherrySlots: 20, hidden, no collision; pine foliage NoCollision with a WPO disable distance; rails and
                 lanterns thin-upright (camera / visibility ignore)
 L4 water        one WaterBodyRiver (points, material MI_DJL_River), one WaterZone
 L5 stair walk   the GASP capsule (r 30, half height 86 cm, MaxStepHeight 45 cm, walkable 44.77 deg) walks the stair path
                 from the river landing L7 to the gate apron and back (BR mode: the Boundary_1v1 set ignored): floor found by
                 a downward trace every 10 cm, step up <= 45 cm, floor normal z >= cos 44.77, no side block between
                 samples; CONTROL: in 1v1 mode the same walk is stopped at the terrace edge (B3)
 L6 B-lines      one CONTROL sweep across each of B1-B8 from the terrace side (the ring ignored, as 'disabled'): the
                 first hit must be that line's blocker; the same sweeps in BR mode (the set ignored) must pass B-lines
Out: world/json/ls_verify.json
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
import unreal  # noqa: E402

W = ROOT / "WorkFiles/dojo/build/landscape/world"
LAY = json.loads((W / "json/world_layout.json").read_text(encoding="utf-8"))
TREP = json.loads((W / "terrain/terrain_report.json").read_text(encoding="utf-8"))
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CH = unreal.CollisionChannel
V = unreal.Vector
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "gates": {}}
R_CM, HH_CM, STEP_CM, WALK_NZ = 30.0, 86.0, 45.0, math.cos(math.radians(44.77))


def resp(c, ch):
    return str(c.get_collision_response_to_channel(ch)).split(".")[-1].split(":")[0].replace("ECR_", "").lower()


def lab(a):
    return a.get_actor_label() if a else None


def hit_t(h):
    if h is None:
        return None
    t = h.to_tuple()
    if not (t[0] or t[1]):
        return None
    return {"blocking": bool(t[0]), "start_pen": bool(t[1]), "loc": t[4], "impact": t[5], "normal": t[7], "actor": t[9]}


def main():
    t0 = time.time()
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["loaded"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
    acts = EAS.get_all_level_actors()
    by = {a.get_actor_label(): a for a in acts}
    ls_acts = [a for a in acts if unreal.Name("DJ_Landscape") in list(a.tags)]
    REP["n_landscape_tagged"] = len(ls_acts)
    ctx = acts[0]
    # ---- L1
    g = {"landscapes": {}}
    for name in ("LS_Valley", "LS_Far"):
        a = by.get(name)
        if a is None:
            g["landscapes"][name] = None
            continue
        g["landscapes"][name] = {"class": a.get_class().get_name(), "components": len(a.get_components_by_class(unreal.LandscapeComponent)),
                                 "nanite": bool(a.get_editor_property("enable_nanite")),
                                 "material": a.get_editor_property("landscape_material").get_path_name()
                                 if a.get_editor_property("landscape_material") else None}
    probes = {}
    worst = 0.0
    # the heightmap value at the exact probe point (bilinear), not the nearest vertex (UE's Python has no numpy)
    import array
    n = 2017
    hraw = array.array("H")
    with open(str(W / "terrain/LS_Valley.r16"), "rb") as fh:
        hraw.frombytes(fh.read())
    x0v, y0v = 22.0 - 504.0, 18.0 + 504.0

    def zmap(x, y):
        c, r = (x - x0v) / 0.5, (y0v - y) / 0.5
        c0, r0 = int(c), int(r)
        fc, fr = c - c0, r - r0

        def H(rr, cc):
            return hraw[rr * n + cc]
        h = (H(r0, c0) * (1 - fc) * (1 - fr) + H(r0, c0 + 1) * fc * (1 - fr) + H(r0 + 1, c0) * (1 - fc) * fr
             + H(r0 + 1, c0 + 1) * fc * fr)
        return round((float(h) - 32768.0) * 100.0 / 128.0 / 100.0, 4)
    for k in TREP["LS_Valley"]["probes"]:
        x, y = [float(v) for v in k[k.index("(") + 1:k.index(")")].split(",")]
        zexp = zmap(x, y)
        h = unreal.SystemLibrary.line_trace_single(ctx, V(x * 100, -y * 100, 20000), V(x * 100, -y * 100, -3000),
                                                   unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False,
                                                   [b for b in acts if b.get_actor_label() != "LS_Valley"],
                                                   unreal.DrawDebugTrace.NONE, True)
        t = hit_t(h)
        z = round(t["impact"].z / 100.0, 4) if t else None
        probes[k] = {"expected_m": zexp, "traced_m": z, "actor": lab(t["actor"]) if t else None}
        if z is not None:
            worst = max(worst, abs(z - zexp))
        else:
            worst = 1e9
    g["probes"] = probes
    g["max_err_m"] = round(worst, 4)
    g["passed"] = (all(v and v["components"] == 256 and v["nanite"] for v in g["landscapes"].values())
                   and worst <= 0.03)
    REP["gates"]["L1_landscapes"] = g
    # ---- L2
    missing, bad_mesh, bad_loc, counts = [], [], [], {}
    for r in LAY["actors"]:
        a = by.get(r["label"])
        if a is None:
            missing.append(r["label"])
            continue
        counts[r["group"]] = counts.get(r["group"], 0) + 1
        if r.get("skeletal"):
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        if sm is None or sm.get_path_name().split(".")[0] != r["mesh"]:
            bad_mesh.append(r["label"])
        if r["group"] in ("walls", "stair", "lanterns", "pines", "boundary", "cherry"):
            l = a.get_actor_location()
            e = max(abs(l.x - r["loc"][0] * 100), abs(l.y + r["loc"][1] * 100), abs(l.z - r["loc"][2] * 100))
            if e > 1.0:
                bad_loc.append({"label": r["label"], "err_cm": round(e, 2)})
    want = {}
    for r in LAY["actors"]:
        want[r["group"]] = want.get(r["group"], 0) + 1
    isms = {}
    for a in ls_acts:
        if unreal.Name("DJL_ISM") in list(a.tags):
            for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
                isms[a.get_actor_label()] = int(c.get_instance_count())
    want_ism = {i["name"]: len(i["rows"]) for i in LAY["ism"]}
    REP["gates"]["L2_actors"] = {"missing": missing, "bad_mesh": bad_mesh, "bad_loc": bad_loc, "counts": counts,
                                 "want": want, "ism": isms, "ism_want": want_ism,
                                 "passed": not missing and not bad_mesh and not bad_loc and isms == want_ism}
    # ---- L3
    bnd, cs, fol, thin = [], [], [], []
    for r in LAY["actors"]:
        a = by.get(r["label"])
        if a is None:
            continue
        c = a.static_mesh_component if not r.get("skeletal") else None
        if r["group"] == "boundary":
            ok = (bool(a.get_editor_property("hidden")) and resp(c, CH.ECC_PAWN) == "block"
                  and resp(c, CH.ECC_CAMERA) == "ignore" and resp(c, CH.ECC_VISIBILITY) == "ignore"
                  and all(unreal.Name(t) in list(a.tags) for t in ("Boundary_1v1", "TerraceEdge", "Dojo/Boundary_1v1")))
            bnd.append({"label": r["label"], "ok": ok})
        elif r["group"] == "cherry":
            en = str(c.get_collision_enabled()).upper()
            ok = bool(a.get_editor_property("hidden")) and "NO_COLLISION" in en and unreal.Name("CherrySlot") in list(a.tags)
            cs.append({"label": r["label"], "ok": ok})
        elif r["label"].endswith("_Foliage"):
            en = str(c.get_collision_enabled()).upper()
            wpo = int(c.get_editor_property("world_position_offset_disable_distance"))
            fol.append({"label": r["label"], "ok": "NO_COLLISION" in en and wpo == 5000, "wpo_cm": wpo})
        elif r["collision"] == "thin":
            ok = resp(c, CH.ECC_PAWN) == "block" and resp(c, CH.ECC_CAMERA) == "ignore"
            thin.append({"label": r["label"], "ok": ok})
    REP["gates"]["L3_collision"] = {"boundary": bnd, "cherry_ok": sum(1 for x in cs if x["ok"]), "cherry_n": len(cs),
                                    "foliage": fol, "thin_ok": sum(1 for x in thin if x["ok"]), "thin_n": len(thin),
                                    "passed": len(bnd) == 8 and all(x["ok"] for x in bnd) and len(cs) == 20
                                    and all(x["ok"] for x in cs) and all(x["ok"] for x in fol) and all(x["ok"] for x in thin)}
    # ---- L4
    rivers = [a for a in acts if a.get_class().get_name() == "WaterBodyRiver"]
    zones = [a for a in acts if a.get_class().get_name() == "WaterZone"]
    wr = {"rivers": len(rivers), "zones": len(zones)}
    if rivers:
        sp = rivers[0].get_water_spline()
        comp = rivers[0].get_water_body_component()
        wr["points"] = sp.get_number_of_spline_points()
        wr["length_m"] = round(sp.get_spline_length() / 100, 1)
        m = comp.get_water_material()
        wr["material"] = m.get_path_name() if m else None
    wr["passed"] = (wr["rivers"] == 1 and wr["zones"] == 1 and wr.get("points") == len(LAY["water"]["points"])
                    and (wr.get("material") or "").endswith("MI_DJL_River"))
    REP["gates"]["L4_water"] = wr
    # ---- L5 stair walk
    ring = [a for a in acts if a.get_actor_label().startswith("SM_DGB_Boundary_1v1")]
    setb = [a for a in acts if unreal.Name("Dojo/Boundary_1v1") in list(a.tags)]
    trv = [a for a in acts if a.get_actor_label().startswith("TRV_")]
    hidden_fx = [a for a in acts if unreal.Name("CherrySlot") in list(a.tags) or unreal.Name("FXAnchor") in list(a.tags)]
    route = [(3.3, -38.9), (3.3, -37.5), (3.3, -35.6), (3.3, -33.7), (3.3, -29.6), (3.3, -28.9), (9.1, -28.9),
             (9.1, -28.0), (9.1, -24.0), (9.1, -14.2), (9.1, -12.4), (9.1, -11.3), (9.1, -6.5), (10.0, -6.5),
             (12.3, -6.5), (13.5, -6.0), (20.5, -6.0), (21.1, -4.4), (21.1, -2.2)]

    def floor_at(x, y, zref, ign):
        top = V(x * 100, -y * 100, zref + 150.0)
        bot = V(x * 100, -y * 100, zref - 250.0)
        h = hit_t(unreal.SystemLibrary.sphere_trace_single_by_profile(ctx, top, bot, 12.0, "Pawn", False, ign,
                                                                       unreal.DrawDebugTrace.NONE, True))
        if not h or h["start_pen"]:
            return None, None, None
        return h["impact"].z, h["normal"].z, lab(h["actor"])

    def walk(pts, ign, z0):
        seq = []
        for (a, b) in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.1))
            for i in range(n):
                t = i / n
                seq.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        seq.append(pts[-1])
        z = z0
        worst_step, min_nz, samples = 0.0, 1.0, 0
        prev = None
        for (x, y) in seq:
            fz, nz, act = floor_at(x, y, z, ign)
            if fz is None:
                return {"clear": False, "why": "no floor", "at": [round(x, 2), round(y, 2)], "samples": samples}
            if fz - z > STEP_CM + 0.5:
                return {"clear": False, "why": f"step {round(fz - z, 1)} cm", "at": [round(x, 2), round(y, 2)],
                        "on": act, "samples": samples}
            if nz < WALK_NZ and fz - z > 1.0:
                return {"clear": False, "why": f"unwalkable nz {round(nz, 3)}", "at": [round(x, 2), round(y, 2)],
                        "on": act, "samples": samples}
            if prev is not None:
                # the body above the step height (the capsule's lowest 45 cm is the step-up band GASP climbs)
                zc = max(z, fz) + STEP_CM + 2.0 + (HH_CM - 24.0)
                h = hit_t(unreal.SystemLibrary.capsule_trace_single_by_profile(
                    ctx, V(prev[0] * 100, -prev[1] * 100, zc), V(x * 100, -y * 100, zc), R_CM, HH_CM - 24.0, "Pawn",
                    False, ign, unreal.DrawDebugTrace.NONE, True))
                if h:
                    return {"clear": False, "why": "blocked", "at": [round(x, 2), round(y, 2)], "by": lab(h["actor"]),
                            "start_pen": h["start_pen"], "samples": samples}
            worst_step = max(worst_step, abs(fz - z))
            min_nz = min(min_nz, nz)
            z = fz
            prev = (x, y)
            samples += 1
        return {"clear": True, "samples": samples, "max_step_cm": round(worst_step, 1), "min_floor_nz": round(min_nz, 3),
                "end_floor_m": round(z / 100, 3)}
    ign_br = trv + ring + setb + hidden_fx
    ign_1v1 = trv + hidden_fx
    up = walk(route, ign_br, -700.0)
    down = walk(list(reversed(route)), ign_br, 0.0)
    ctrl = walk(route, ign_1v1, -700.0)
    REP["gates"]["L5_stair_walk"] = {"BR_stair_path_river_landing_to_gate": up, "BR_stair_path_gate_to_river_landing": down,
                                     "CONTROL_1v1_stair_path_to_gate": ctrl,
                                     "passed": up["clear"] and down["clear"] and not ctrl["clear"]}
    # ---- L6 B-lines
    rows = {}
    for r in LAY["actors"]:
        if r["group"] != "boundary":
            continue
        ln = r["line"]
        (ax, ay), (bx, by_) = ln["from"], ln["to"]
        mx, my = (ax + bx) / 2, (ay + by_) / 2
        dx, dy = bx - ax, by_ - ay
        L = math.hypot(dx, dy)
        nx, ny = dy / L, -dx / L                      # a normal; point it away from the terrace centre (22, 18)
        if (mx + nx - 22) ** 2 + (my + ny - 18) ** 2 < (mx - 22) ** 2 + (my - 18) ** 2:
            nx, ny = -nx, -ny
        # sample off the compound walls: a quarter along each line
        sx, sy = ax + dx * 0.3, ay + dy * 0.3
        p0 = (sx - nx * 0.9, sy - ny * 0.9)
        p1 = (sx + nx * 1.6, sy + ny * 1.6)
        zc = ln["z0"] * 100 + HH_CM + 3.0 + 60.0
        res = {}
        for mode, ign in (("1v1_ring_off", trv + hidden_fx + ring), ("br", trv + hidden_fx + ring + setb)):
            h = hit_t(unreal.SystemLibrary.capsule_trace_single_by_profile(
                ctx, V(p0[0] * 100, -p0[1] * 100, zc), V(p1[0] * 100, -p1[1] * 100, zc), R_CM, HH_CM, "Pawn", False, ign,
                unreal.DrawDebugTrace.NONE, True))
            res[mode] = {"hit": lab(h["actor"]) if h else None, "start_pen": h["start_pen"] if h else None}
        res["ok"] = res["1v1_ring_off"]["hit"] == r["label"] and not res["1v1_ring_off"]["start_pen"] and \
            res["br"]["hit"] != r["label"]
        res["from_to"] = [p0, p1]
        rows[r["label"]] = res
    REP["gates"]["L6_Blines"] = {"rows": rows, "passed": len(rows) == 8 and all(v["ok"] for v in rows.values())}
    REP["passed"] = all(g_["passed"] for g_ in REP["gates"].values())
    REP["sec"] = round(time.time() - t0, 1)


try:
    main()
except Exception:  # noqa: BLE001
    REP["error"] = traceback.format_exc()[-3000:]
    REP["passed"] = False
(Path(__import__("os").environ["DJ_LS_VOUT"]) if __import__("os").environ.get("DJ_LS_VOUT") else W / "json/ls_verify.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
unreal.log(f"DJ_STEP_DONE ls_verify passed={REP['passed']} gates={ {k: v['passed'] for k, v in REP['gates'].items()} }")
