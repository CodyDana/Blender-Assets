"""LANDSCAPE ROUND, FX + LIGHTING stage, Unreal step 2 (pythonscript commandlet, -nullrhi): place the FX in L_Dojo.

Re-run safe: destroys exactly the actors tagged DJ_FXL (never DJ_Managed: the showcase level step; never DJ_Landscape:
the world step), then places, from world/json/world_layout.json (CherrySlots, rocks, river points, FX anchors):
  petals    NS_DKF_PetalDrift over the courtyard / terrace and over the cliff stair (active); NS_DKF_PetalCanopy on EVERY
            CherrySlot at 0.6 x the slot height (tags CherrySlotFX + the slot id): active only where the look needs
            petals now (ACTIVE_SLOTS), the others auto-activate off, ready for the cherries
  fallen    on the ground under each slot canopy (line traces; sand, water, roofs and steep faces skipped): petal
            scatter decals (MI_DKF_PetalScatter_0..3, 35 cm, 10 cm deep, random yaw) and SM_DKF_PetalDrift_A..C hero
            clusters, all NoCollision and shadowless (decor only, no gameplay effect)
  river     NS_DKF_RapidSpray + NS_DKF_SprayDroplets on the upstream face of every boulder in the fast reach, foam wakes
            (MI_DKF_FoamWake planes) behind them, NS_DKF_MistPuff at the FX anchors and the bigger boulders,
            NS_DKF_MistWisp along the rapids, NS_DKF_RiverHaze low over the water (actor +X = down-stream)
Particle budget: every Niagara actor's estimated steady count (rate x mean life) is summed in the report.
Result: WorkFiles/dojo/build/landscape/fxlight/json/fxl_place.json
"""
import json
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
import unreal  # noqa: E402

W = ROOT / "WorkFiles/dojo/build/landscape/world"
O = ROOT / "WorkFiles/dojo/build/landscape/fxlight"
LAY = json.loads((W / "json/world_layout.json").read_text(encoding="utf-8"))
ASSETS = json.loads((O / "json/fxl_assets.json").read_text(encoding="utf-8"))
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
TAG = "DJ_FXL"
FNS = "/Game/DojoKit/FX/Niagara"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "errors": [], "notes": [], "counts": {}, "particles": {}}
RNG = random.Random(20260930)
# CherrySlot canopy emitters that run now (the courtyard pair, the west strip by the hall, the cliff-top slot over the
# stair): the other slots are placed inactive and fire when their cherry is imported
ACTIVE_SLOTS = ("CS01", "CS02", "CS03", "CS04", "CS09")
EST = {k.rsplit("/", 1)[1]: v.get("est_particles") or 0 for k, v in ASSETS["systems"].items()}


def V(x, y, z):
    return unreal.Vector(float(x), float(y), float(z))


def cm(p):
    return V(p[0] * 100.0, -p[1] * 100.0, p[2] * 100.0)


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def tag(a, label, folder, extra=()):
    a.set_actor_label(label)
    a.set_folder_path("Dojo/FX/" + folder)
    a.tags = [unreal.Name(TAG)] + [unreal.Name(t) for t in extra]
    return a


def clear():
    n = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(TAG) in list(a.tags):
            EAS.destroy_actor(a)
            n += 1
    REP["removed_previous"] = n


_SYS = {}


def niagara(sysname, loc_cm, yaw, label, folder, active=True, extra=()):
    if sysname not in _SYS:
        _SYS[sysname] = unreal.load_asset(f"{FNS}/{sysname}")
        if _SYS[sysname] is None:
            raise RuntimeError(f"missing {sysname}")
    a = EAS.spawn_actor_from_class(unreal.NiagaraActor, loc_cm, rot(yaw))
    tag(a, label, folder)
    c = a.get_editor_property("niagara_component")
    c.set_asset(_SYS[sysname])
    c.set_editor_property("auto_activate", bool(active))
    # hall + armory FINISH (2026-10-01, measured: finish/perf_probe run 2): with Lumen hardware ray tracing every Niagara
    # emitter fed the ray tracing scene, and gathering it cost 7.3-7.9 ms of render thread per frame at
    # CAM_PlayerEyeSand / CAM_AK_CW_WestAisle (RayTracing_FinishGatherInstances; frame time 16.0 / 15.7 ms, p95 17.6).
    # With the Niagara RT geometry off: frame time 11.4 / 11.7 ms, p95 12.3 / 12.9, GPU unchanged. The petals, mist and
    # dust are not needed in ray-traced reflections / GI: each FX component is invisible to ray tracing (the main view
    # and the shadows are unchanged).
    for k, v in (("cast_shadow", False), ("visible_in_ray_tracing", False)):
        try:
            c.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            REP.setdefault("setp_failed", []).append(f"Niagara.{k}: {str(exc)[:100]}")
    tag(a, label, folder, ("DJF_" + sysname,) + tuple(extra) + (("FX_Active",) if active else ("FX_Ready",)))
    REP["counts"][sysname] = REP["counts"].get(sysname, 0) + 1
    if active:
        REP["particles"][sysname] = round(REP["particles"].get(sysname, 0) + EST.get(sysname, 0), 1)
    return a


# ---------------------------------------------------------------------------------------------------- river geometry
PTS = LAY["water"]["points"]


def river_at(x, y):
    """Nearest river point: (index, water_z m, width m, velocity cm/s, flow dir (Blender xy, unit))."""
    best, bi = 1e18, 0
    for i, p in enumerate(PTS):
        d = (p["xy"][0] - x) ** 2 + (p["xy"][1] - y) ** 2
        if d < best:
            best, bi = d, i
    i0, i1 = max(bi - 1, 0), min(bi + 1, len(PTS) - 1)
    dx, dy = PTS[i1]["xy"][0] - PTS[i0]["xy"][0], PTS[i1]["xy"][1] - PTS[i0]["xy"][1]
    n = math.hypot(dx, dy) or 1.0
    p = PTS[bi]
    return bi, p["water_z"], p["width_m"], p["velocity_cm_s"], (dx / n, dy / n), math.sqrt(best)


def yaw_of(d):
    """Blender xy direction -> UE yaw (deg) of an actor whose local +X points along it."""
    return math.degrees(math.atan2(-d[1], d[0]))


def river():
    """Only boulders that break the surface get spray and a wake (probe pa: submerged rocks put foam rectangles and
    splashes on open water): the rock actor's bounds must reach the water level (top no more than 35 cm under it)."""
    rocks = [a for a in LAY["actors"] if a["group"] == "rocks"]
    by_label = {a.get_actor_label(): a for a in EAS.get_all_level_actors() if unreal.Name("DJ_Landscape") in list(a.tags)}
    sprays, out = [], []
    REP["rocks_rejected"] = {}
    for r in rocks:
        x, y = r["loc"][0], r["loc"][1]
        i, wz, wid, vel, fd, dist = river_at(x, y)
        act = by_label.get(r["label"])
        if act is None:
            continue
        o, e = act.get_actor_bounds(False)
        top, bot = (o.z + e.z) / 100.0, (o.z - e.z) / 100.0
        size = max(e.x, e.y) * 2.0 / 100.0
        if vel < 300 or dist > wid / 2.0 + size * 0.3:
            continue
        # emergent boulders, and stones just under the surface (top within 35 cm): the water piles over them into a
        # standing wave of white water (pour-over), which is where the reference's foam sits
        if not (top > wz - 0.35 and bot < wz):
            REP["rocks_rejected"][r["label"]] = {"top": round(top, 2), "bottom": round(bot, 2), "water": round(wz, 2)}
            continue
        sprays.append((r, i, wz, wid, vel, fd, size, top))
    REP["spray_rocks"] = []
    for r, i, wz, wid, vel, fd, size, top in sprays:
        x, y = r["loc"][0], r["loc"][1]
        face = (x - fd[0] * size * 0.45, y - fd[1] * size * 0.45, wz + 0.05)
        emergent = top > wz + 0.15
        # caps/it3: a SprayBurst sheet on a stone under the surface read from above as a white bird on open water: the
        # splashes and drops only where a boulder stands out of the water; the pour-over stones get the softer wake
        if emergent:
            niagara("NS_DKF_RapidSpray", cm(face), yaw_of(fd), f"FX_Spray_{r['label']}", "River/Spray")
            niagara("NS_DKF_SprayDroplets", cm(face), yaw_of(fd), f"FX_Drops_{r['label']}", "River/Spray")
        # the foam wake: a plane from the rock's downstream face, length 2.5 x size, width 0.9 x size (+3 cm over the water)
        L, Wd = size * 2.5, size * 0.9
        c = (x + fd[0] * (size * 0.4 + L / 2.0), y + fd[1] * (size * 0.4 + L / 2.0), wz + 0.03)
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, cm(c), rot(yaw_of(fd) - 90.0))
        a.set_actor_scale3d(V(Wd, L, 1.0))
        sm = a.static_mesh_component
        sm.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
        sm.set_material(0, unreal.load_asset("/Game/DojoKit/FX/Materials/" + ("MI_DKF_FoamWake" if emergent
                                                                           else "MI_DKF_FoamWakeSoft")))
        sm.set_collision_profile_name("NoCollision")
        sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        sm.set_editor_property("cast_shadow", False)
        sm.set_mobility(unreal.ComponentMobility.STATIC)
        tag(a, f"FX_FoamWake_{r['label']}", "River/Foam", ("DJF_FoamWake",))
        REP["counts"]["FoamWake"] = REP["counts"].get("FoamWake", 0) + 1
        REP["spray_rocks"].append({"rock": r["label"], "size_m": round(size, 2), "emergent": emergent,
                                   "top_z": round(top, 2), "river_index": i, "water_z": round(wz, 2),
                                   "velocity": vel, "face": [round(v, 2) for v in face]})
    # mist puffs: the three anchors + the boulders of 1.4 m and up
    puffs = [(an["loc"][0], an["loc"][1], an["loc"][2], an["label"]) for an in LAY["fx_anchors"]]
    # LANDSCAPE FIX ROUND (blocker 5 / delta 6): the mist read as a steam plume at the bend; with the fix round's 30+
    # emergent boulders the per-boulder puffs are capped: the 4 biggest emergent boulders of the stepped reach (key
    # 5.0-7.4) only
    big = sorted([sp for sp in sprays if sp[7] > sp[2] + 0.15 and sp[6] >= 1.4 and 5.0 <= PTS[sp[1]].get("key", 0) <= 7.4],
                 key=lambda sp: -sp[6])[:4]          # it5: 6 -> 4 (CAM_RiverRapids still read a veil)
    for r, i, wz, wid, vel, fd, size, top in big:
        puffs.append((r["loc"][0] + fd[0] * size, r["loc"][1] + fd[1] * size, wz + 0.4, r["label"]))
    for x, y, z, lab in puffs:
        i, wz, wid, vel, fd, dist = river_at(x, y)
        niagara("NS_DKF_MistPuff", cm((x, y, max(z, wz + 0.3))), yaw_of(fd), f"FX_MistPuff_{lab}", "River/Mist")
    # wisps along the fast reach every ~14 m; haze every ~32 m over a longer reach (index 100-185)
    acc, last = 0.0, None
    for i, p in enumerate(PTS):
        if last is not None:
            acc += math.hypot(p["xy"][0] - last[0], p["xy"][1] - last[1])
        last = p["xy"]
        if p["velocity_cm_s"] >= 300 and acc >= 22.0:      # fix round it5: every 22 m (was 14 m)
            acc = 0.0
            _, wz, wid, vel, fd, _ = river_at(*p["xy"])
            niagara("NS_DKF_MistWisp", cm((p["xy"][0], p["xy"][1], wz + 0.6)), yaw_of(fd), f"FX_MistWisp_{i:03d}",
                    "River/Mist")
    acc, last = 0.0, None
    for i, p in enumerate(PTS):
        if last is not None:
            acc += math.hypot(p["xy"][0] - last[0], p["xy"][1] - last[1])
        last = p["xy"]
        # fix round: the haze sheets stay over the rapids and the run below them (key 4.8-8.5; they reached 2.3 km
        # upstream and stacked into the plume the judge saw at the bend)
        if 4.8 <= p.get("key", 0) <= 8.5 and acc >= 32.0:
            acc = 0.0
            _, wz, wid, vel, fd, _ = river_at(*p["xy"])
            niagara("NS_DKF_RiverHaze", cm((p["xy"][0], p["xy"][1], wz + 1.2)), yaw_of(fd), f"FX_Haze_{i:03d}",
                    "River/Haze")


# ---------------------------------------------------------------------------------------------------- petals
def hit(ctx, x, y, ztop, ignore):
    h = unreal.SystemLibrary.line_trace_single(ctx, V(x * 100, -y * 100, ztop * 100), V(x * 100, -y * 100, -3000),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple()
    if not t[0]:
        return None
    vecs = [v for v in t if isinstance(v, unreal.Vector)]
    act = next((v for v in t if isinstance(v, unreal.Actor)), None)
    comp = next((v for v in t if isinstance(v, unreal.PrimitiveComponent)), None)
    return {"loc": vecs[0], "normal": vecs[2] if len(vecs) > 2 else V(0, 0, 1), "actor": act, "comp": comp}


SKIP_WORDS = ("Sand", "Water", "River", "Roof", "Ridge", "Kawara", "Eave", "Boundary", "Wall_", "Fence", "SM_DGB_Tree")


def surface_ok(h):
    if h is None or h["normal"].z < 0.7:
        return False, "steep/none"
    lab = h["actor"].get_actor_label() if h["actor"] else ""
    mat = ""
    try:
        m = h["comp"].get_material(0) if h["comp"] else None
        mat = m.get_name() if m else ""
    except Exception:  # noqa: BLE001
        pass
    s = lab + " " + mat
    if any(w in s for w in SKIP_WORDS):
        return False, s
    return True, s


def petals():
    ctx = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # the drift layer: the courtyard / terrace (box centred on the compound) and the cliff stair
    niagara("NS_DKF_PetalDrift", cm((22.0, 18.0, 0.0)), yaw_of((1, 0)), "FX_PetalDrift_Courtyard", "Petals")
    niagara("NS_DKF_PetalDrift", cm((4.0, -28.0, -3.0)), yaw_of((1, 0)), "FX_PetalDrift_Stair", "Petals")
    ignore = [a for a in EAS.get_all_level_actors() if unreal.Name("CherrySlot") in list(a.tags)
              or a.get_actor_label().startswith("SM_DGB_Tree") or a.get_class().get_name() in ("NiagaraActor",)]
    decal_mis = [unreal.load_asset(f"/Game/DojoKit/FX/Materials/MI_DKF_PetalScatter_{i}") for i in range(4)]
    drifts = [unreal.load_asset(f"/Game/DojoKit/FX/Meshes/SM_DKF_PetalDrift_{c}") for c in "ABC"]
    REP["fallen"] = {}
    for s in [a for a in LAY["actors"] if a["group"] == "cherry"]:
        sid = s["label"].split("_")[-1]
        x, y, z = s["loc"]
        h, canopy = float(s["height_m"]), float(s["canopy_m"])
        niagara("NS_DKF_PetalCanopy", cm((x, y, z + 0.6 * h)), yaw_of((1, 0)), f"FX_PetalCanopy_{sid}", "Petals/Slots",
                active=sid in ACTIVE_SLOTS, extra=("CherrySlotFX", sid))
        nd = nm = 0
        skipped = {}
        for k in range(16):
            ang, rr = RNG.uniform(0, 2 * math.pi), canopy * 0.5 * math.sqrt(RNG.uniform(0.05, 1.0))
            px, py = x + rr * math.cos(ang), y + rr * math.sin(ang)
            hh = hit(ctx, px, py, z + h + 3.0, ignore)
            ok, why = surface_ok(hh)
            if not ok:
                skipped[why[:40]] = skipped.get(why[:40], 0) + 1
                continue
            nrm = hh["normal"]
            base = unreal.MathLibrary.make_rot_from_z(nrm)
            if nd < 7:
                # decal: +X projects into the surface (= -normal), random spin about the normal
                r = unreal.MathLibrary.make_rot_from_x(V(-nrm.x, -nrm.y, -nrm.z))
                r = unreal.MathLibrary.compose_rotators(rot(roll=RNG.uniform(0, 360)), r)
                a = EAS.spawn_actor_from_class(unreal.DecalActor, hh["loc"], r)
                dc = a.get_editor_property("decal")
                cell = RNG.choice((0, 0, 1, 1, 2, 3))
                dc.set_decal_material(decal_mis[cell])
                dc.set_editor_property("decal_size", V(10.0, 17.5, 17.5))
                tag(a, f"FX_PetalDecal_{sid}_{nd:02d}", "Petals/Fallen", ("DJF_PetalDecal", sid))
                nd += 1
            elif nm < 3:
                r = unreal.MathLibrary.compose_rotators(rot(yaw=RNG.uniform(0, 360)), base)
                a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, hh["loc"], r)
                sm = a.static_mesh_component
                sm.set_static_mesh(RNG.choice(drifts))
                sm.set_collision_profile_name("NoCollision")
                sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                sm.set_editor_property("cast_shadow", False)
                sm.set_mobility(unreal.ComponentMobility.STATIC)
                tag(a, f"FX_PetalDrift_{sid}_{nm:02d}", "Petals/Fallen", ("DJF_PetalDriftMesh", sid))
                nm += 1
        REP["fallen"][sid] = {"decals": nd, "drift_meshes": nm, "skipped": skipped}
        REP["counts"]["PetalDecal"] = REP["counts"].get("PetalDecal", 0) + nd
        REP["counts"]["PetalDriftMesh"] = REP["counts"].get("PetalDriftMesh", 0) + nm
    stair_petals(ctx, ignore, decal_mis)


# fix round (delta 9): the reference's pink petals lie on the stair steps and landings (ref x0-300, y1280-1536): petal
# scatter decals on every path piece of ls_geo.path_footprints (about 0.8 per m2), traced onto the kit steps
def stair_petals(ctx, ignore, decal_mis):
    n = 0
    for fp in LAY["path_footprints"]:
        k = max(3, int(fp["hl"] * fp["hw"] * 4 * 0.8))
        for _ in range(k):
            u, v = RNG.uniform(-fp["hw"], fp["hw"]), RNG.uniform(-fp["hl"], fp["hl"])
            c, s_ = math.cos(math.radians(fp["rot"])), math.sin(math.radians(fp["rot"]))
            x, y = fp["cx"] + u * c - v * s_, fp["cy"] + u * s_ + v * c
            hh = hit(ctx, x, y, max(fp["z0"], fp["z1"]) + 2.0, ignore)
            if hh is None or hh["normal"].z < 0.7:
                continue
            nrm = hh["normal"]
            r = unreal.MathLibrary.make_rot_from_x(V(-nrm.x, -nrm.y, -nrm.z))
            r = unreal.MathLibrary.compose_rotators(rot(roll=RNG.uniform(0, 360)), r)
            a = EAS.spawn_actor_from_class(unreal.DecalActor, hh["loc"], r)
            dc = a.get_editor_property("decal")
            dc.set_decal_material(decal_mis[RNG.choice((0, 1, 2, 3))])
            dc.set_editor_property("decal_size", V(10.0, 17.5, 17.5))
            tag(a, f"FX_PetalDecal_Stair_{fp['id']}_{n:03d}", "Petals/Stair", ("DJF_PetalDecal", "Stair"))
            n += 1
    REP["counts"]["PetalDecalStair"] = n


def petal_material_check():
    m = unreal.load_asset("/Game/DojoKit/FX/Materials/M_DKF_Petal")
    rec = {}
    for k in ("used_with_niagara_mesh_particles", "used_with_instanced_static_meshes"):
        try:
            v = bool(m.get_editor_property(k))
            if not v:
                m.set_editor_property(k, True)
                unreal.MaterialEditingLibrary.recompile_material(m)
                EAL.save_loaded_asset(m, False)
            rec[k] = [v, bool(m.get_editor_property(k))]
        except Exception as exc:  # noqa: BLE001
            rec[k] = f"ERR {exc}"
    REP["petal_material_usage_before_after"] = rec


def main():
    t0 = time.time()
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["loaded"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
    clear()
    for name, fn in (("petal_material_check", petal_material_check), ("river", river), ("petals", petals)):
        t1 = time.time()
        try:
            fn()
        except Exception:  # noqa: BLE001
            REP["errors"].append(name)
            REP.setdefault("tracebacks", {})[name] = traceback.format_exc()[-2500:]
        REP.setdefault("sec_by_step", {})[name] = round(time.time() - t1, 1)
    REP["particles_total_est"] = round(sum(REP["particles"].values()), 1)
    REP["n_fxl_actors"] = sum(1 for a in EAS.get_all_level_actors() if unreal.Name(TAG) in list(a.tags))
    REP["saved"] = bool(les.save_current_level()) if not REP["errors"] else False
    REP["passed"] = not REP["errors"] and REP["saved"]
    REP["sec"] = round(time.time() - t0, 1)
    (Path(os.environ["DJ_FXL_OUT"]) if os.environ.get("DJ_FXL_OUT") else O / "json/fxl_place.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE fxl_place passed={REP['passed']} errors={REP['errors']} actors={REP['n_fxl_actors']} "
               f"particles_est={REP['particles_total_est']}")


main()
