"""VERIFIER (hall + armory round), Unreal side, a FRESH read-only pythonscript commandlet on DojoLab (-nullrhi).
NOTHING IS SAVED: every save / delete / import / create entry point the sync script uses is replaced by a recorder.

1. STATE: load L_Dojo as saved; dump every actor (label, class, transform, mesh, material overrides, collision,
   lighting channels, shadows, light values, PPV values, tags, folder).
2. PLACEMENT: every interior_layout.json instance, item and lights_design.json light vs its actor (hall-local ->
   world; world cm = (x*100, -y*100, z*100), yaw = -rot_z): translation error in mm, yaw error; mesh = the piece's
   ue_mesh; collision vs interface.json collision classes; glass / props collision (simple hulls present, Pawn block).
   Shell: hall_shell_layout.json instances_new vs layout_showcase.json + the level actors.
3. IDEMPOTENCY: run dj_armory_sync.py's Unreal stage a second time IN MEMORY (its source, with only these swaps:
   OUT -> verify/sync2, EAL / AT / level save -> recorders), then dump again and diff against the state of step 1.
   Zero differences + zero imports / saves-with-change = idempotent.
Out: WorkFiles/dojo/build/hall_armory/verify/json/ue_state.json
"""
import json
import math
import shutil
import time
import traceback
from pathlib import Path

import unreal

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VD = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "verify"
OUTJ = VD / "json"
OUTJ.mkdir(parents=True, exist_ok=True)
SH = ROOT / "WorkFiles" / "shared" / "armory_hall"
SYNC_SRC = ROOT / "Scripts" / "dojo" / "unreal" / "dj_armory_sync.py"
SYNC_OUT_ORIG = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "armory_sync"
SYNC_OUT_V = VD / "sync2"
LEVEL = "/Game/Dojo/Maps/L_Dojo"
HL = (22.0, 24.0, 0.5)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
CH = unreal.CollisionChannel
R = {"errors": []}


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def en(e):
    return str(e).split(".")[-1].split(":")[0].strip("<> ")


def rnd(v, k=3):
    return round(float(v), k)


def comp_sig(c):
    s = {"cls": c.get_class().get_name()}
    try:
        s["mobility"] = en(c.get_editor_property("mobility"))
    except Exception:  # noqa: BLE001
        pass
    if isinstance(c, unreal.PrimitiveComponent):
        try:
            s["coll_enabled"] = en(c.get_collision_enabled())
            s["profile"] = str(c.get_collision_profile_name())
            s["resp"] = [en(c.get_collision_response_to_channel(ch)) for ch in (CH.ECC_PAWN, CH.ECC_CAMERA, CH.ECC_VISIBILITY)]
            lc = c.get_editor_property("lighting_channels")
            s["lc"] = [bool(lc.get_editor_property(k)) for k in ("channel0", "channel1", "channel2")]
            s["cast_shadow"] = bool(c.get_editor_property("cast_shadow"))
            s["visible"] = bool(c.get_editor_property("visible"))
            s["step_up"] = en(c.get_editor_property("can_character_step_up_on"))
        except Exception as e:  # noqa: BLE001
            s["err"] = repr(e)[:120]
    if isinstance(c, unreal.StaticMeshComponent):
        m = c.static_mesh
        s["mesh"] = m.get_path_name().split(".")[0] if m else None
        try:
            s["mats"] = [(mm.get_path_name().split(".")[0] if mm else None) for mm in c.get_materials()]
        except Exception:  # noqa: BLE001
            pass
    if isinstance(c, unreal.LocalLightComponent):
        for k in ("intensity", "attenuation_radius", "cast_shadows", "specular_scale", "visible", "volumetric_scattering_intensity"):
            try:
                v = c.get_editor_property(k)
                s[k] = rnd(v, 4) if isinstance(v, float) else v
            except Exception:  # noqa: BLE001
                pass
        try:
            col = c.get_editor_property("light_color")
            s["color"] = [col.r, col.g, col.b]
        except Exception:  # noqa: BLE001
            pass
        for k in ("source_width", "source_height", "barn_door_angle", "barn_door_length", "outer_cone_angle",
                  "inner_cone_angle", "source_radius"):
            try:
                s[k] = rnd(c.get_editor_property(k), 3)
            except Exception:  # noqa: BLE001
                pass
        try:
            s["units"] = en(c.get_editor_property("intensity_units"))
        except Exception:  # noqa: BLE001
            pass
    return s


def actor_sig(a):
    l, r, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
    s = {"class": a.get_class().get_name(), "loc": [rnd(l.x), rnd(l.y), rnd(l.z)], "rot": [rnd(r.pitch, 4), rnd(r.yaw, 4), rnd(r.roll, 4)],
         "scale": [rnd(sc.x, 5), rnd(sc.y, 5), rnd(sc.z, 5)], "tags": sorted(str(t) for t in a.tags),
         "folder": str(a.get_folder_path()), "hidden_game": bool(a.get_editor_property("hidden"))}
    comps = a.get_components_by_class(unreal.ActorComponent)
    s["comps"] = sorted([comp_sig(c) for c in comps if isinstance(c, (unreal.PrimitiveComponent, unreal.LightComponentBase))],
                        key=lambda d: json.dumps(d, sort_keys=True))
    if isinstance(a, unreal.PostProcessVolume):
        pp = a.get_editor_property("settings")
        ps = {}
        for k in ("auto_exposure_bias", "lumen_skylight_leaking", "bloom_intensity", "local_exposure_highlight_contrast_scale",
                  "local_exposure_shadow_contrast_scale"):
            try:
                ps[k] = [bool(pp.get_editor_property("override_" + k)), rnd(pp.get_editor_property(k), 4)]
            except Exception:  # noqa: BLE001
                pass
        s["pp"] = ps
        s["ppv"] = {k: str(a.get_editor_property(k)) for k in ("unbound", "priority", "blend_radius")}
    return s


def dump():
    out, dup = {}, []
    for a in EAS.get_all_level_actors():
        lb = a.get_actor_label()
        if lb in out:
            dup.append(lb)
            lb = f"{lb}#{len(dup)}"
        out[lb] = actor_sig(a)
    return out, dup


def world_cm(v):
    return (( v[0] + HL[0]) * 100.0, -(v[1] + HL[1]) * 100.0, (v[2] + HL[2]) * 100.0)


def yaw_err(ue_yaw, rot_z):
    return abs(((ue_yaw + rot_z) + 180.0) % 360.0 - 180.0)


def placement(state):
    I, D, F = jl(SH / "interior_layout.json"), jl(SH / "lights_design.json"), jl(SH / "interface.json")
    classes = F["gameplay"]["collision_classes"]
    by_id = {}
    for lb, s in state.items():
        for t in s["tags"]:
            if t.startswith("DJA_AKI_"):
                by_id[t[4:]] = (lb, s)
    rows, worst, worst_id, missing, mesh_bad, coll_bad, pitch_roll_bad = [], 0.0, None, [], [], [], []
    yaw_worst = 0.0
    for it in I["instances"]:
        e = by_id.get(it["id"])
        if not e:
            missing.append(it["id"])
            continue
        lb, s = e
        w = world_cm(it["loc_m"])
        d = math.sqrt(sum((s["loc"][k] - w[k]) ** 2 for k in range(3))) * 10.0   # mm
        ye = yaw_err(s["rot"][1], float(it["rot_z_deg"]))
        yaw_worst = max(yaw_worst, ye)
        if abs(s["rot"][0]) > 1e-3 or abs(s["rot"][2]) > 1e-3 or any(abs(v - 1.0) > 1e-5 for v in s["scale"]):
            pitch_roll_bad.append(it["id"])
        if d > worst:
            worst, worst_id = d, it["id"]
        smc = [c for c in s["comps"] if c["cls"] == "StaticMeshComponent"]
        want_mesh = I["pieces"][it["piece"]]["ue_mesh"]
        if not smc or smc[0].get("mesh") != want_mesh:
            mesh_bad.append([it["id"], smc[0].get("mesh") if smc else None, want_mesh])
        cls = it["collision_class"]
        c = classes[cls]
        if smc:
            got = smc[0]
            if c.get("no_collision"):
                ok = got.get("coll_enabled") == "NO_COLLISION"
            else:
                want = [c["pawn"], c["camera"], c["visibility"]]
                gotr = [x.replace("ECR_", "").lower() for x in got.get("resp", [])]
                ok = got.get("coll_enabled") == "QUERY_AND_PHYSICS" and gotr == want
                if cls in ("glass", "propblock"):
                    ok = ok and got.get("step_up") == "ECB_NO"
            if not ok:
                coll_bad.append([it["id"], cls, got.get("coll_enabled"), got.get("resp"), got.get("step_up")])
        if d > 1.0 or ye > 0.01:
            rows.append({"id": it["id"], "piece": it["piece"], "err_mm": round(d, 3), "yaw_err": round(ye, 4)})
    # items
    items = []
    for it in I["items"]:
        lb = f"Item_{it['name']}"
        s = state.get(lb)
        if not s:
            items.append({"name": it["name"], "missing": True})
            continue
        w = world_cm(it["loc_m"])
        d = math.sqrt(sum((s["loc"][k] - w[k]) ** 2 for k in range(3))) * 10.0
        items.append({"name": it["name"], "err_mm": round(d, 3), "yaw_err": round(yaw_err(s["rot"][1], float(it["rot_z_deg"])), 4),
                      "scale": s["scale"]})
    # lights (lights_design + level lights)
    lights, lmiss = [], []
    for Lr in D["lights"]:
        s = state.get(Lr["name"])
        if not s:
            lmiss.append(Lr["name"])
            continue
        w = world_cm(Lr["loc_m"])
        d = math.sqrt(sum((s["loc"][k] - w[k]) ** 2 for k in range(3))) * 10.0
        lights.append(round(d, 3))
    return {"instances": len(I["instances"]), "found": len(I["instances"]) - len(missing), "missing": missing,
            "max_err_mm": round(worst, 4), "max_err_id": worst_id, "max_yaw_err_deg": round(yaw_worst, 5),
            "over_1mm_or_0.01deg": rows[:50], "n_over": len(rows), "pitch_roll_scale_off": pitch_roll_bad,
            "mesh_mismatch": mesh_bad, "collision_mismatch": coll_bad, "items": items,
            "lights": {"design": len(D["lights"]), "found": len(lights), "missing": lmiss,
                       "max_err_mm": max(lights) if lights else None}}


def collision_assets():
    """every SM_AK mesh used: simple-collision hull count (vs the piece's UCX count), walkable-slope override on glass /
    propblock pieces; the item meshes."""
    I = jl(SH / "interior_layout.json")
    out, bad = {}, []
    for piece, p in sorted(I["pieces"].items()):
        m = unreal.load_asset(p["ue_mesh"])
        if m is None:
            bad.append([piece, "missing"])
            continue
        bs = m.get_editor_property("body_setup")
        ag = bs.get_editor_property("agg_geom")
        n = {k: len(ag.get_editor_property(k)) for k in ("convex_elems", "box_elems", "sphere_elems", "sphyl_elems")}
        wso = bs.get_editor_property("walkable_slope_override")
        beh = en(wso.get_editor_property("walkable_slope_behavior"))
        ctf = en(bs.get_editor_property("collision_trace_flag"))
        nan = bool(m.get_editor_property("nanite_settings").get_editor_property("enabled"))
        try:
            src = m.get_editor_property("asset_import_data").extract_filenames()
        except Exception:  # noqa: BLE001
            src = None
        r = {"class": p["collision_class"], "ucx": p.get("ucx"), "hulls": n, "slope": beh, "trace_flag": ctf, "nanite": nan,
             "src": [Path(s).name for s in src] if src else None}
        out[piece] = r
        if p["collision_class"] != "nocollision" and (p.get("ucx") or 0) > 0 and n["convex_elems"] != p.get("ucx"):
            bad.append([piece, "hulls", n["convex_elems"], p.get("ucx")])
        if p["collision_class"] in ("glass", "propblock") and beh != "WALKABLE_SLOPE_UNWALKABLE":
            bad.append([piece, "slope", beh])
        if p["collision_class"] != "nocollision" and sum(n.values()) == 0 and ctf != "CTF_USE_COMPLEX_AS_SIMPLE":
            bad.append([piece, "no simple collision"])
        if src and Path(src[0]).name != f"{piece}.fbx":
            bad.append([piece, "import source", src])
    return {"pieces": out, "problems": bad}


def shell(state):
    H = jl(SH / "hall_shell_layout.json")
    L = jl(ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json")
    by_sid = {}
    for n, i in enumerate(L["instances"]):
        if i.get("shell_id"):
            by_sid.setdefault(i["shell_id"], []).append((n, i))
    rows, worst = [], 0.0
    removed_present = []
    for s in H["instances_new"]:
        st = str(s.get("status", ""))
        hits = by_sid.get(s["id"], [])
        live = [(n, i) for n, i in hits if not i.get("removed")]
        if st.startswith("removed"):
            for n, i in hits:
                if f"{i['piece']}__{n:04d}" in state:
                    removed_present.append(s["id"])
            continue
        if len(live) != 1:
            rows.append({"id": s["id"], "layout_hits": len(live)})
            continue
        n, i = live[0]
        lb = f"{i['piece']}__{n:04d}"
        a = state.get(lb)
        if a is None:
            rows.append({"id": s["id"], "actor_missing": lb})
            continue
        w = s["loc_world_m"]
        want = (w[0] * 100, -w[1] * 100, w[2] * 100)
        d = math.sqrt(sum((a["loc"][k] - want[k]) ** 2 for k in range(3))) * 10.0
        ye = yaw_err(a["rot"][1], float(s["rot_z_deg"]))
        worst = max(worst, d)
        if d > 1.0 or ye > 0.01 or i["piece"] != s["piece"]:
            rows.append({"id": s["id"], "label": lb, "err_mm": round(d, 3), "yaw_err": round(ye, 4), "piece": [i["piece"], s["piece"]]})
    return {"instances_new": len(H["instances_new"]), "problems": rows, "max_err_mm": round(worst, 4),
            "removed_but_present": removed_present}


class _Rec:
    log = []


class _VEAL:
    """EditorAssetLibrary stand-in: reads pass through; writes are recorded, never executed."""

    @staticmethod
    def does_asset_exist(p):
        return unreal.EditorAssetLibrary.does_asset_exist(p)

    @staticmethod
    def delete_asset(p):
        _Rec.log.append(["delete_asset", p])
        return False

    @staticmethod
    def save_loaded_asset(a, *k):
        _Rec.log.append(["save_loaded_asset(dirty)", a.get_path_name()])
        return True

    @staticmethod
    def save_asset(p, only_if_is_dirty=True):
        pkg = unreal.load_asset(p)
        dirty = None
        try:
            dirty = bool(pkg.get_outermost().is_dirty())
        except Exception:  # noqa: BLE001
            pass
        _Rec.log.append(["save_asset", p, "dirty" if dirty else ("clean" if dirty is False else "unknown")])
        return True


class _VAT:
    def __init__(self, at):
        self.at = at

    def import_asset_tasks(self, tasks):
        _Rec.log.append(["import_asset_tasks", [str(t.get_editor_property("filename")) for t in tasks]])

    def create_asset(self, *a, **k):
        _Rec.log.append(["create_asset", [str(x) for x in a[:2]]])
        return self.at.create_asset(*a, **k)   # in memory only (never saved)


def second_run():
    SYNC_OUT_V.mkdir(parents=True, exist_ok=True)
    for f in ("files.json", "import_manifest.json"):
        if (SYNC_OUT_ORIG / f).exists():
            shutil.copy2(SYNC_OUT_ORIG / f, SYNC_OUT_V / f)
    src = SYNC_SRC.read_text(encoding="utf-8")
    swaps = [
        ('OUT = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "armory_sync"', f'OUT = Path(r"{SYNC_OUT_V}")'),
        ("EAL = unreal.EditorAssetLibrary", "EAL = _VEAL"),
        ("AT = unreal.AssetToolsHelpers.get_asset_tools()", "AT = _VAT(unreal.AssetToolsHelpers.get_asset_tools())"),
        ('REP["saved"] = bool(les.save_current_level())', 'REP["saved"] = _vsave_level()'),
    ]
    for a, b in swaps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    cut = src.index("try:\n    import unreal  # noqa: F401\n    _IN_UE = True")
    src = src[:cut]

    def _vsave_level():
        w = unreal.EditorLevelLibrary.get_editor_world()
        try:
            d = bool(w.get_outermost().is_dirty())
        except Exception:  # noqa: BLE001
            d = None
        _Rec.log.append(["save_current_level", "dirty" if d else ("clean" if d is False else "unknown")])
        return True

    g = {"__name__": "dj_armory_sync_verify", "__file__": str(SYNC_SRC), "_VEAL": _VEAL, "_VAT": _VAT,
         "_vsave_level": _vsave_level}
    exec(compile(src, str(SYNC_SRC), "exec"), g)
    g["unreal_stage"]()
    rep = jl(SYNC_OUT_V / "sync.json")
    return {"passed": rep.get("passed"), "bounds_gate": {k: rep.get("bounds_gate", {}).get(k) for k in ("max_bounds_err_cm", "max_t_err_cm", "n_placed", "passed")},
            "imports": [m for m, e in rep.get("meshes", {}).items() if e.get("imported")],
            "mesh_saves": [m for m, e in rep.get("meshes", {}).items() if e.get("saved")],
            "fbx_sha_drift": rep.get("fbx_sha_drift"), "copied_packages": rep.get("copied_packages"),
            "envelope_violations": rep.get("envelope_violations"), "shell_ids": rep.get("shell_ids"),
            "shadowed": rep.get("shadowed_local_lights"), "errors": rep.get("errors"), "write_calls": _Rec.log}


def diff(a, b):
    ka, kb = set(a), set(b)
    # actor labels of re-spawned actors are equal by construction (the sync labels them); compare signatures
    changed = [k for k in sorted(ka & kb) if a[k] != b[k]]
    det = {}
    for k in changed[:30]:
        det[k] = {f: [a[k].get(f), b[k].get(f)] for f in set(a[k]) | set(b[k]) if a[k].get(f) != b[k].get(f)}
    return {"only_before": sorted(ka - kb)[:50], "n_only_before": len(ka - kb), "only_after": sorted(kb - ka)[:50],
            "n_only_after": len(kb - ka), "n_changed": len(changed), "changed_examples": det}


def main():
    t0 = time.time()
    R["open_ok"] = bool(LES.load_level(LEVEL))
    s1, dup1 = dump()
    R["actors"] = len(s1)
    R["duplicate_labels"] = dup1[:40]
    R["n_dja"] = sum(1 for s in s1.values() if "DJ_ArmoryHall" in s["tags"])
    R["placement"] = placement(s1)
    R["collision_assets"] = collision_assets()
    R["shell"] = shell(s1)
    (OUTJ / "ue_state_before.json").write_text(json.dumps(s1, indent=0), encoding="utf-8")
    unreal.log(f"VHA_STATE dumped {len(s1)} actors; placement max {R['placement']['max_err_mm']} mm")
    try:
        R["second_run"] = second_run()
        s2, dup2 = dump()
        R["idempotency_diff"] = diff(s1, s2)
        R["duplicate_labels_after"] = dup2[:40]
    except Exception:  # noqa: BLE001
        R["errors"].append(traceback.format_exc()[-3000:])
    R["sec"] = round(time.time() - t0, 1)
    (OUTJ / "ue_state.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    d = R.get("idempotency_diff", {})
    unreal.log(f"VHA_STATE_DONE placement_max_mm={R['placement']['max_err_mm']} missing={len(R['placement']['missing'])} "
               f"diff_changed={d.get('n_changed')} only_before={d.get('n_only_before')} only_after={d.get('n_only_after')} "
               f"errors={len(R['errors'])}")


try:
    main()
except Exception:  # noqa: BLE001
    R["errors"].append(traceback.format_exc()[-3000:])
    (OUTJ / "ue_state.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    unreal.log("VHA_STATE_DONE exception")
