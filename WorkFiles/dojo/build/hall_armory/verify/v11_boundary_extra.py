# ------------------------------------------------------------------------------------------------ VERIFIER v11 additions
SKIN = 2.0
UNWALK_KEYS = ("_Glass__", "_Plinth__", "SM_AK_Lantern", "SM_AK_H_LanternStand", "SM_AK_Vase")


def unwalkable(actor_label):
    return bool(actor_label) and actor_label.startswith("SM_AK_") and any(k in actor_label for k in UNWALK_KEYS)


def _floor_below(cx, cy, cz, depth, r, ign):
    """capsule centre (cm) swept straight down by depth cm: (hit, floor_z_m) with the v10 edge-contact rule."""
    h = cap_sweep(V(cx, cy, cz), V(cx, cy, cz - depth), r, ign)
    if not h or h["start_pen"]:
        return h, None
    zf = (h["loc"].z - HH - 1.0) / 100
    if nz(h) < 0.71:
        lh = line_down(cx / 100, -cy / 100, zf + 0.10, 0.25, ign)
        if lh and not lh["start_pen"] and nz(lh) >= 0.71 and abs(lh["imp"].z / 100 - zf) <= 0.06:
            h = dict(h, n=lh["n"], actor=lh["actor"])
    lo = h["loc"]
    h = dict(h, loc=V(lo.x, lo.y, lo.z + SKIN))   # keep a 2 cm skin over the floor (no contact at the next sweep start)
    return h, zf


def step(c, tx, ty, r, ign, max_drop=0.5):
    """one CMC-like move of the standing capsule centre c (cm vector) to plan point (tx, ty) m.
    Returns (new centre, floor m, actor, None) or (None, None, actor, why)."""
    t = V(tx * 100, -ty * 100, c.z)
    h = cap_sweep(c, t, r, ign)
    lift = 0.0
    if h is not None:
        if h["start_pen"]:
            return None, None, h["actor"], "start penetrating"
        up = cap_sweep(c, V(c.x, c.y, c.z + 45.0), r, ign)       # step-up, clamped by any ceiling (door head)
        full = 45.0 if up is None else max(0.0, up["loc"].z - c.z - 1.0)   # CMC pulls back off a ceiling contact
        h2, ok = None, False
        for lift in sorted({full, max(0.0, full - 3.0), max(0.0, full - 6.0), max(0.0, full - 9.0), max(0.0, full - 12.0),
                            max(0.0, full - 18.0)}, reverse=True):
            top = V(c.x, c.y, c.z + lift)
            if lift > 0 and cap_sweep(c, top, r, ign) is not None:
                continue
            t2 = V(t.x, t.y, top.z)
            h2 = cap_sweep(top, t2, r, ign)
            if h2 is None:
                ok = True
                break
        if not ok:
            return None, None, h2["actor"] if h2 else None, f"blocked (lift up to {full:.1f} cm)"
        t = t2
    fh, zf = _floor_below(t.x, t.y, t.z, lift + max_drop * 100 + 1.0, r, ign)
    if fh is None or zf is None:
        return None, None, fh["actor"] if fh else None, "no floor (drop)" if fh is None else "floor start penetrating"
    if nz(fh) < 0.71:
        return None, None, fh["actor"], f"floor nz {nz(fh):.3f}"
    if unwalkable(fh["actor"]):
        return None, None, fh["actor"], "unwalkable prop (D6)"
    c2 = fh["loc"]
    return c2, zf, fh["actor"], None


def walk2(pts, r, ign, z_start):
    """the layout route with step(): 5 cm samples; rise <= 45 cm, drop <= 50 cm."""
    x0, y0 = pts[0]
    fh, zf = _floor_below(x0 * 100, -y0 * 100, (z_start + 0.30) * 100 + HH + 1.0, 80.0, r, ign)
    if fh is None or zf is None:
        return {"clear": False, "why": "no start floor", "at_bl_m": [x0, y0, z_start], "actor": fh["actor"] if fh else None}
    c, floor = fh["loc"], zf
    rows = {"samples": 0, "max_rise_cm": 0.0, "max_drop_cm": 0.0}
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 0.05))
        for k in range(1, n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            c2, z2, act, why = step(c, x, y, r, ign)
            if why:
                return {**rows, "clear": False, "why": why, "at_bl_m": [round(x, 2), round(y, 2), round(floor, 3)], "actor": act}
            d = z2 - floor
            rows["max_rise_cm"] = max(rows["max_rise_cm"], round(d * 100, 2))
            rows["max_drop_cm"] = max(rows["max_drop_cm"], round(-d * 100, 2))
            c, floor = c2, z2
            rows["samples"] += 1
    return {**rows, "clear": True, "end_bl_m": [round(pts[-1][0], 2), round(pts[-1][1], 2), round(floor, 3)]}


def run_interior():
    """walking flood (2.5D, one floor per cell, 8-neighbour, step() moves) on a 0.2 m grid from the courtyard at
    (22, 16) over X 12.1..31.9, Y 14.1..46.9, mode 1v1, r 30 (and the reached set at r 35 counted separately).
    Reports: interior floor cells reached (inside the armory walls X 16..28, Y 24.12..44), free interior floor cells
    NOT reached (free = a downward trace from +3.6 m finds a floor below the ceiling and the capsule fits), every reached
    cell inside the hall but outside the armory walls (side strips / cavities: a leak), the dais deck reached, the
    floor actors stood on (props?)."""
    t0 = time.time()
    out = {}
    for r in (30.0, 35.0):
        ign = IGN["1v1"]
        g, X0, Y0, NX, NY = 0.2, 12.1, 14.1, 100, 165
        fh, zf = _floor_below(22.0 * 100, -16.0 * 100, 1.0 * 100 + HH + 1.0, 150.0, r, ign)
        seen = {(50, 9): (fh["loc"], zf)}
        q = deque([(50, 9)])
        floor_actors = {}
        while q:
            i, j = q.popleft()
            c, z = seen[(i, j)]
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                a, b = i + di, j + dj
                if not (0 <= a < NX and 0 <= b < NY) or (a, b) in seen:
                    continue
                c2, z2, act, why = step(c, X0 + a * g, Y0 + b * g, r, ign)
                if why or z2 - z > 0.45:
                    continue
                if not cap_free_at(X0 + a * g, Y0 + b * g, z2 + 0.01, r, ign):
                    continue
                seen[(a, b)] = (c2, z2)
                floor_actors[act] = floor_actors.get(act, 0) + 1
                q.append((a, b))
        inside = lambda x, y: 16.0 < x < 28.0 and 24.12 < y < 44.0
        hall_not_armory = lambda x, y: (13.12 < x < 15.7 or 28.3 < x < 30.88) and 24.12 < y < 44.88
        reached = {(i, j): v for (i, j), v in seen.items()}
        rin = [(X0 + i * g, Y0 + j * g, v[1]) for (i, j), v in reached.items() if inside(X0 + i * g, Y0 + j * g)]
        leaks = [[round(X0 + i * g, 2), round(Y0 + j * g, 2), round(v[1], 3)] for (i, j), v in reached.items()
                 if hall_not_armory(X0 + i * g, Y0 + j * g) or (Y0 + j * g > 44.3) or (Y0 + j * g > 34.12 and not 14.88 < X0 + i * g < 29.12)]
        # free interior floor cells (independent of connectivity)
        free_cells, unreached = 0, []
        for i in range(NX):
            for j in range(NY):
                x, y = X0 + i * g, Y0 + j * g
                if not inside(x, y):
                    continue
                lh = line_down(x, y, 3.6, 3.4, ign)
                if not lh or lh["start_pen"] or nz(lh) < 0.71 or unwalkable(lh["actor"]):
                    continue
                zf2 = lh["imp"].z / 100
                if not cap_free_at(x, y, zf2 + 0.02, r, ign):
                    continue
                free_cells += 1
                if (i, j) not in reached:
                    unreached.append([round(x, 2), round(y, 2), round(zf2, 3), lh["actor"]])
        dais = [p for p in rin if p[2] > 1.0]
        out[f"r{int(r)}"] = {"reached_cells": len(reached), "interior_reached_cells": len(rin), "interior_free_cells": free_cells,
                             "interior_free_unreached": len(unreached), "unreached_examples": unreached[:80],
                             "leaks_into_hidden_strips_or_cavities": leaks[:40], "n_leaks": len(leaks),
                             "dais_cells_reached": len(dais), "max_floor_reached_m": round(max((p[2] for p in rin), default=0), 3),
                             "max_y_reached": round(max((Y0 + j * g for (i, j) in reached), default=0), 2),
                             "floor_actors_top": sorted(floor_actors.items(), key=lambda kv: -kv[1])[:40],
                             "props_stood_on": sorted(k for k in floor_actors if k and ("SM_AK_" in k and unwalkable(k)))}
        unreal.log(f"VHA_INTERIOR r{int(r)} reached {len(reached)} interior {len(rin)}/{free_cells} leaks {len(leaks)}")
    out["reached_cells"] = out["r30"]["reached_cells"]
    out["leaks_into_targets"] = out["r30"]["n_leaks"] + out["r35"]["n_leaks"]
    out["sec"] = round(time.time() - t0, 1)
    return out


def run_rearroof():
    """BR (the whole 1v1 group ignored): walk the main roof's back slope over the valley, up the rear roof to its ridge
    and down to the north eave on x 17 / 22 / 27, and back; 1v1 controls: the same lines and a walk from the front half
    over the main ridge must be BLOCKED; plus BR ground -> rear eave is NOT a walk (climb only: Blender climb check)."""
    out = {}

    def start_on(x, y, ign):
        lh = line_down(x, y, 14.0, 10.0, ign)
        return None if not lh or lh["start_pen"] else lh["imp"].z / 100

    for x in (17.0, 22.0, 27.0):
        for mode in ("br", "1v1"):
            ign = IGN[mode]
            z0 = start_on(x, 31.0, IGN["br"])
            line = [(x, 31.0), (x, 34.42), (x, 40.16), (x, 45.6)]
            out[f"{mode}_x{x:g}_back_slope_over_valley_ridge_to_north_eave"] = walk2(line, 30.0, ign, z0) if z0 else {"clear": False, "why": "no start"}
            z1 = start_on(x, 45.4, IGN["br"])
            out[f"{mode}_x{x:g}_north_eave_up_over_rear_ridge_to_valley"] = walk2(list(reversed(line))[:3], 30.0, ign, z1) if z1 else {"clear": False, "why": "no start"}
    # 1v1 from the legal front half over the main ridge into the rear half
    for x in (17.0, 22.0, 27.0):
        z0 = start_on(x, 26.5, IGN["1v1"])
        out[f"CONTROL_1v1_x{x:g}_front_half_over_main_ridge"] = walk2([(x, 26.5), (x, 29.15), (x, 31.5)], 30.0, IGN["1v1"], z0) if z0 else {"clear": False, "why": "no start"}
    # the rear roof's gable verges (BR): walk along the ridge from west verge to east verge
    z = start_on(15.0, 40.16, IGN["br"])
    out["br_along_rear_ridge_W_to_E"] = walk2([(15.0, 40.16), (29.0, 40.16)], 30.0, IGN["br"], z) if z else {"clear": False, "why": "no start"}
    br_ok = all(v["clear"] for k, v in out.items() if k.startswith("br_"))
    ctl_ok = all(not v["clear"] for k, v in out.items() if k.startswith("CONTROL"))
    out["info_1v1_lines_from_closed_back_slope_clear"] = [k for k, v in out.items() if k.startswith("1v1_") and isinstance(v, dict) and v.get("clear")]
    out["summary"] = {"br_all_clear": br_ok, "1v1_all_blocked": ctl_ok}
    out["passed"] = br_ok and ctl_ok
    return out
