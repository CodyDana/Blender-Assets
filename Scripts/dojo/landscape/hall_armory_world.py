"""HALL + ARMORY round (2026-10-01), DojoLab stage: the landscape world layout for the extended hall, as a DELTA on the
landscape fix round's final world_layout.json (plain Python).

Why a delta: make_world_layout.py draws every random placement (rocks, firs, grass, bushes) from ONE seeded stream, so
re-running it on the moved terrace re-rolls the whole valley (every tree near the river and behind the hall moves),
which the brief forbids ("without changing the look elsewhere"). Here only what the extension touches changes:

- terrain: make_terrain.py with ls_geo.HALL_ARMORY (the terrace to y 56, the north hill's spot heights +12 m, the
  -0.30 pads under the extension and the moved alley gravel, WR5's face to y 57.2) must have run first;
- deterministic records rebuilt by make_world_layout's own functions (executed without its main()): the ishigaki runs
  (WR5 + 4 + 4 + 2 + 2 m, its EndR to y 56), the 1v1 terrace B-lines (B5 / B6 / B7 to y 56), the cherry slots (CS19 /
  CS20 + 11 m), the stair lanterns + their lights (carry-over: lanterns 3 / 4 / 6 off the tread to the cheek side) and
  the valley mask (FZ1 / FZ2 from y 59, WR5's moss band);
- the five cypresses + 12 m in y, z on the new ground - 0.2;
- every other record and ISM row keeps its x / y / yaw / scale; its z follows the terrain change at its (x, y)
  (z += new - old ground, only where the ground changed); firs inside the new keepout (x -10..52, y < 59) are dropped;
  grass / bushes / rocks inside the new structures (the extension, the moved wall and side walls, the alley gravel,
  the new WR5 modules) are dropped.
Inputs: hall_armory/ue/json/{world_layout_base.json, LS_Valley_m_base.npy} (the fix round's final, saved by this stage
before any write); world/terrain/LS_Valley_m.npy + .r16 (new). Out: world/json/world_layout.json, world/terrain/
T_DJL_ValleyMask.png, hall_armory/ue/json/hall_armory_world_report.json.
Run: py -3 -B hall_armory_world.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ls_geo as G  # noqa: E402

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
U = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "ue" / "json"
TER = G.WORLD / "terrain"
assert G.HALL_ARMORY, "ls_geo.HALL_ARMORY must be on"

# make_world_layout's functions, without running its main()
_src = (HERE / "make_world_layout.py").read_text(encoding="utf-8")
assert _src.rstrip().endswith("main()")
NS = {"__name__": "mwl_hall_armory", "__file__": str(HERE / "make_world_layout.py")}
exec(compile(_src.rstrip()[:-len("main()")], str(HERE / "make_world_layout.py"), "exec"), NS)

A = np.load(U / "LS_Valley_m_base.npy")
B = np.load(TER / "LS_Valley_m.npy")
LS = G.LS_VALLEY
XS, YS = G.grid_axes(LS)


def bil(Z, x, y):
    s = LS["spacing"]
    c = (np.asarray(x, float) - XS[0]) / s
    r = (YS[0] - np.asarray(y, float)) / s
    c0 = np.clip(np.floor(c).astype(int), 0, LS["n"] - 2)
    r0 = np.clip(np.floor(r).astype(int), 0, LS["n"] - 2)
    fc, fr = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
    return (Z[r0, c0] * (1 - fc) * (1 - fr) + Z[r0, c0 + 1] * fc * (1 - fr) + Z[r0 + 1, c0] * (1 - fc) * fr
            + Z[r0 + 1, c0 + 1] * fc * fr)


HALF = (LS["n"] - 1) * LS["spacing"] / 2.0


def delta(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    inside = (np.abs(x - LS["centre"][0]) < HALF - 2.0) & (np.abs(y - LS["centre"][1]) < HALF - 2.0)
    d = np.where(inside, bil(B, x, y) - bil(A, x, y), 0.0)
    return np.where(np.abs(d) > 0.005, d, 0.0)


# structures the extension adds / moves (level frame, x0 x1 y0 y1), for dropping cover / rocks
STRUCT = {"extension": (14.6, 29.4, 33.8, 45.4), "north_wall": (-1.2, 45.2, 46.7, 48.3),
          "west_wall_ext": (-1.2, 0.2, 35.5, 48.3), "east_wall_ext": (43.8, 45.2, 35.5, 48.3),
          "alley_gravel": (10.5, 35.5, 44.9, 47.1), "wr5_ext": (48.3, 50.6, 43.8, 56.6)}


def in_struct(x, y, pad=0.0):
    x, y = np.asarray(x, float), np.asarray(y, float)
    hit = np.zeros(np.shape(x), bool)
    for x0, x1, y0, y1 in STRUCT.values():
        hit |= (x > x0 - pad) & (x < x1 + pad) & (y > y0 - pad) & (y < y1 + pad)
    return hit


# hall + armory FINISH (2026-10-01, the verify's carry-over): CAM_Ref2Match's backdrop above the hall roof. The hill
# returns to the landscape round's terrain north of y 72 (ls_geo.HILL_RESTORE), so the trees there keep their base
# records exactly. A tree that stands where the ground is still lower (the shoulder band y 56-72), or that the new keepout
# dropped, or one of the five cypresses, is RE-SEATED ALONG ITS CAMERA RAY when CAM_Ref2Match sees it: scaling the tree
# about the camera centre by k (position C + k (P - C), scale k s, same yaw) projects to exactly the same image, and k
# is solved so its base meets the new ground (with the record's own offset to the ground, x k). Other views see the same
# tree k x larger and k x farther from that camera (k is reported).
REF2 = {"loc": (22.0, -0.3, 7.3), "look_at": (22.0, 26.0, 0.0), "hfov_deg": 84.0, "fov_margin_deg": 3.0}
RESEAT_MIN_DROP = 0.05
RESEAT_K_MAX = 2.5


def in_ref2_fov(x, y):
    cx, cy, _cz = REF2["loc"]
    fx, fy = REF2["look_at"][0] - cx, REF2["look_at"][1] - cy
    ang = math.degrees(math.atan2(x - cx, y - cy) - math.atan2(fx, fy))
    return (y - cy) > 1.0 and abs(ang) <= REF2["hfov_deg"] / 2.0 + REF2["fov_margin_deg"]


def reseat(x, y, z):
    """-> (x', y', z', k) on the new ground along the CAM_Ref2Match ray, or None (no root for k in (1, K_MAX])."""
    cx, cy, cz = REF2["loc"]
    off = z - float(bil(A, x, y))

    def f(k):
        xn, yn = cx + k * (x - cx), cy + k * (y - cy)
        return cz + k * (z - cz) - (float(bil(B, xn, yn)) + off * k)

    lo, hi = 1.0, RESEAT_K_MAX
    if f(lo) <= 0.0 or f(hi) > 0.0:
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    k = 0.5 * (lo + hi)
    xn, yn = cx + k * (x - cx), cy + k * (y - cy)
    if yn < G.TERRACE[3] + 1.5 or bool(in_struct(xn, yn, 0.5)):
        return None
    return xn, yn, cz + k * (z - cz), k


def keepout_fir(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return (x > -10) & (x < 52) & (y > -6) & (y < G.TERRACE[3] + 3.0)


def main():
    W = json.loads((U / "world_layout_base.json").read_text(encoding="utf-8"))
    rep = {"date": "2026-10-01", "base": str(U / "world_layout_base.json"), "replaced": {}, "moved": [], "dropped": {},
           "resnapped": {}, "lanterns": {}}
    acts = W["actors"]
    # ---- deterministic groups rebuilt
    new_walls = NS["walls"]()
    la, lights = NS["lanterns"]()
    # L7's lantern: z = the kerb top or the ground under the lantern, whichever is higher
    for r in la:
        if r["label"].startswith("Lantern_6_"):
            x, y = r["loc"][:2]
            gz = float(max(bil(B, x + dx, y + dy) for dx in (-0.2, 0.0, 0.2) for dy in (-0.2, 0.0, 0.2)))
            kerb_top = -7.0 + 0.093
            r["loc"][2] = round(max(kerb_top, gz), 4)
            rep["lanterns"]["Lantern_6_ground_max_m"] = round(gz, 3)
    for li in lights:
        for r in la:
            if li["name"] == "Light_PathLantern_" + r["label"].split("_")[1]:
                lz = 1.02 if "Timber" in r["mesh"] else 0.6
                li["loc"] = [r["loc"][0], r["loc"][1], round(r["loc"][2] + lz, 4)]
    old_l = {r["label"]: r["loc"] for r in acts if r["group"] == "lanterns"}
    rep["lanterns"]["moved"] = {r["label"]: {"from": old_l.get(r["label"]), "to": r["loc"]} for r in la
                                if old_l.get(r["label"]) != r["loc"]}
    groups = {"walls": new_walls, "lanterns": la, "cherry": NS["cherry"](), "boundary": NS["boundary"]()}
    out = []
    seen = set()
    for r in acts:
        g = r["group"]
        if g in groups:
            if g not in seen:
                out.extend(groups[g])
                seen.add(g)
                old = {x["label"]: x for x in acts if x["group"] == g}
                new = {x["label"]: x for x in groups[g]}
                rep["replaced"][g] = {"n_old": len(old), "n_new": len(new),
                                      "added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
                                      "changed": sorted(k for k in set(new) & set(old)
                                                        if json.dumps(new[k], sort_keys=True)
                                                        != json.dumps(old[k], sort_keys=True))}
            continue
        out.append(r)
    W["lights"] = lights
    # ---- cypress (+12 m) and the generic re-snap / drops on the other actor groups
    final, dropped = [], []
    for r in out:
        if r["group"] in groups:
            final.append(r)
            continue
        x, y, z = r["loc"]
        if r["label"].startswith("Cypress_"):
            r = dict(r)
            rs = reseat(x, y, z) if in_ref2_fov(x, y) else None
            if rs is not None:
                xn, yn, zn, k = rs
                r["loc"] = [round(xn, 4), round(yn, 4), round(zn, 4)]
                r["scale"] = [round(v * k, 4) for v in r["scale"]]
                rep.setdefault("reseated", []).append({"label": r["label"], "from": [x, y, z], "to": r["loc"],
                                                       "k": round(k, 4)})
            else:   # not seen from CAM_Ref2Match: the stage-3 move (+12 m in y, z on the new ground - 0.2)
                ny = y + 12.0
                r["loc"] = [x, ny, round(float(bil(B, x, ny)) - 0.2, 4)]
            rep["moved"].append({"label": r["label"], "from": [x, y, z], "to": r["loc"]})
            final.append(r)
            continue
        if r["group"] in ("rocks", "fx") and bool(in_struct(x, y, 0.6 * max(r.get("scale", [1])[0], 1.0))):
            dropped.append(r["label"])
            continue
        d = float(delta(x, y))
        if d != 0.0:
            r = dict(r)
            r["loc"] = [x, y, round(z + d, 4)]
            rep["resnapped"].setdefault("actors", []).append({"label": r["label"], "dz": round(d, 3)})
        final.append(r)
    W["actors"] = final
    rep["dropped"]["actors"] = dropped
    # ---- ISM rows
    for ism in W["ism"]:
        rows = np.array([[float(v) for v in row[:5]] for row in ism["rows"]]) if ism["rows"] else np.zeros((0, 5))
        tags = [row[5] if len(row) > 5 else "" for row in ism["rows"]]
        if not len(rows):
            continue
        x, y = rows[:, 0], rows[:, 1]
        drop = np.zeros(len(rows), bool)
        if ism["group"] == "forest":
            drop |= keepout_fir(x, y) & np.array([t.startswith("FZ") for t in tags])
        else:
            drop |= in_struct(x, y, 0.3)
        d = delta(x, y)
        keep = []
        n_res = 0
        for k, row in enumerate(ism["rows"]):
            if ism["group"] == "forest" and (drop[k] or d[k] < -RESEAT_MIN_DROP) and in_ref2_fov(x[k], y[k]):
                rs = reseat(float(row[0]), float(row[1]), float(row[2]))
                if rs is not None:
                    xn, yn, zn, kk = rs
                    keep.append([xn, yn, zn, row[3], float(row[4]) * kk] + list(row[5:]))
                    rep.setdefault("reseated_rows", {}).setdefault(ism["name"], []).append(
                        {"from": [round(float(v), 3) for v in row[:3]], "to": [round(xn, 3), round(yn, 3), round(zn, 3)],
                         "k": round(kk, 4), "was_dropped": bool(drop[k])})
                    continue
            if drop[k]:
                continue
            if d[k] != 0.0:
                row = list(row)
                row[2] = float(row[2]) + float(d[k])
                n_res += 1
            keep.append(row)
        n_rd = sum(1 for e in rep.get("reseated_rows", {}).get(ism["name"], []) if e["was_dropped"])
        if drop.any() and int(drop.sum()) - n_rd:
            rep["dropped"][ism["name"]] = int(drop.sum()) - n_rd
        if n_res:
            rep["resnapped"][ism["name"]] = n_res
        ism["rows"] = keep
    # ---- shadow pass (carry-over): every shadow-casting ISM with wind WPO (the near firs, the bushes) keeps its virtual
    # shadow map pages cached (Rigid invalidation: WPO does not redraw the shadow); the look keeps every shadow
    rep["shadow_rigid"] = []
    for ism in W["ism"]:
        if ism.get("shadow", True) and ism.get("wpo_disable_cm") and ism["group"] in ("forest", "cover"):
            ism["shadow_invalidation"] = "Rigid"
            rep["shadow_rigid"].append(ism["name"])
    # ---- the mask
    W["mask"] = NS["valley_mask"](TER / "T_DJL_ValleyMask.png")
    counts = {}
    for a in W["actors"]:
        counts[a["group"]] = counts.get(a["group"], 0) + 1
    W["counts"]["actors_by_group"] = counts
    W["counts"]["ism_instances"] = {i["name"]: len(i["rows"]) for i in W["ism"]}
    W["counts"]["lights"] = len(W["lights"])
    W["hall_armory_round"] = {"date": "2026-10-01", "script": "Scripts/dojo/landscape/hall_armory_world.py",
                              "terrace_north_y": G.TERRACE[3], "hill_spots": G.HILL_SPOTS,
                              "summary": {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in rep.items()}}
    W["date"] = "2026-10-01"
    (G.WORLD / "json" / "world_layout.json").write_text(json.dumps(W, indent=0), encoding="utf-8")
    rep["counts"] = W["counts"]
    (U / "hall_armory_world_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("HALL_ARMORY_WORLD", json.dumps({"replaced": {k: {kk: (len(vv) if isinstance(vv, list) else vv)
                                                            for kk, vv in v.items()} for k, v in rep["replaced"].items()},
                                           "moved": len(rep["moved"]), "dropped": {k: (len(v) if isinstance(v, list)
                                                                                       else v)
                                                                                   for k, v in rep["dropped"].items()},
                                           "resnapped": {k: (len(v) if isinstance(v, list) else v)
                                                         for k, v in rep["resnapped"].items()},
                                           "lanterns": rep["lanterns"]}))


main()
