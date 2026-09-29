"""CardShopKit G1 step: verify (pythonscript commandlet, -nullrhi, a FRESH process: HOUSE rule, never trust a check made
in the process that wrote the assets). Reloads the saved assets and levels and grades every automatic part of G1.

Per mesh: imported; LOD count and LOD0 triangles as .csk.json; every authored socket present, at the authored place
(<= 1 mm) and rotation (quaternion match); the convex hull count; the LOD screen sizes from the sidecar; every slot
has a G1 instance. Per texture: sRGB, power of two.
G1 test 2 (sockets): the showcase has <= 40 sockets, and every grid slot computed IN UNREAL from the imported Level
socket plus the .csk.json grid (pitch, first offset; Blender +Y = Unreal -Y) lands on the Blender-computed
``slots_ue`` within 1 mm, for every class grid (at least Card, Slab and Pack are required).
Maps: both levels load; every recorded actor is where map.json says (<= 1 mm); the stress map holds 200 attached
empty slabs (each card attached to its slab's Card socket) and 200 filled slabs.
G1 test 1 (art) and test 3 (draws, sorting) need eyes and a real RHI: they are listed as MANUAL with what to look for.

Results: WorkFiles/cardshop/g1/unreal/verify.json; the log line CSK_STEP_DONE verify passed=... .
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

import unreal  # noqa: E402  (first: Scripts/unreal/ must never shadow the engine module)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import csk_common as C  # noqa: E402
from pipeline.ue_import_sockets import _static_mesh_editor_subsystem  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def R(roll=0.0, pitch=0.0, yaw=0.0):
    r = unreal.Rotator()
    r.roll, r.pitch, r.yaw = float(roll), float(pitch), float(yaw)
    return r


def dist(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def quat_match(r1, r2):
    q1, q2 = r1.quaternion(), r2.quaternion()
    return abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w) >= 1.0 - 1e-6


def check_mesh(name, sms):
    d = C.csk(name)
    e = {"passed": False}
    m = unreal.load_asset(f"{C.MESH_DEST}/{name}")
    if not isinstance(m, unreal.StaticMesh):
        e["error"] = "not imported"
        return e
    e["lods"] = int(m.get_num_lods())
    e["lods_expected"] = d["lods"]["count"]
    e["tris_lod0"] = int(m.get_num_triangles(0))
    e["tris_lod0_expected"] = d["lods"]["triangles"][0]
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(m)
    names = sorted(str(n) for n in comp.get_all_socket_names())
    want = [s["name"] for s in d["sockets"]]
    e["sockets"] = len(names)
    e["sockets_missing"] = sorted(set(want) - set(names))
    side = C.sidecar(name)
    side_rot = {}
    if side is not None:
        for rec in json.loads(side.read_text(encoding="utf-8"))["sockets"]:
            r = rec["rotation_deg"]
            side_rot[rec["socket"]] = R(r["roll"], r["pitch"], r["yaw"])
    bad_loc, bad_rot, worst = [], [], 0.0
    for s in d["sockets"]:
        sock = m.find_socket(s["name"])
        if sock is None:
            continue
        loc = sock.get_editor_property("relative_location")
        err = dist([loc.x, loc.y, loc.z], C.blender_mm_to_ue_cm(s["loc_mm"]))
        worst = max(worst, err)
        if err > C.SEAT_TOL_CM:
            bad_loc.append([s["name"], round(err, 4)])
        if s["name"] in side_rot and not quat_match(sock.get_editor_property("relative_rotation"), side_rot[s["name"]]):
            bad_rot.append(s["name"])
        sc = sock.get_editor_property("relative_scale")
        if max(abs(sc.x - 1), abs(sc.y - 1), abs(sc.z - 1)) > 1e-4:
            bad_rot.append(f"{s['name']} scale {sc.x:.3f}")
    e["socket_max_err_cm"] = round(worst, 5)
    e["socket_loc_errors"], e["socket_rot_errors"] = bad_loc, bad_rot
    try:
        agg = m.get_editor_property("body_setup").get_editor_property("agg_geom")
        e["convex"] = len(agg.get_editor_property("convex_elems"))
    except Exception as exc:  # noqa: BLE001
        e["convex_err"] = str(exc)[:200]
    e["convex_expected"] = d.get("hulls")
    if side is not None and d["lods"]["count"] > 1 and sms is not None:
        want_ss = json.loads(side.read_text(encoding="utf-8")).get("lod_screen_sizes") or []
        got_ss = [float(v) for v in sms.get_lod_screen_sizes(m)]
        e["screen_sizes"], e["screen_sizes_expected"] = [round(v, 5) for v in got_ss], want_ss
        e["screen_sizes_ok"] = len(got_ss) == len(want_ss) and all(abs(a - b) < 1e-4 for a, b in zip(got_ss, want_ss))
    else:
        e["screen_sizes_ok"] = True
    slots = []
    for i, s in enumerate(m.get_editor_property("static_materials")):
        mat = s.get_editor_property("material_interface")
        slots.append([str(s.get_editor_property("material_slot_name")), mat.get_name() if mat else None])
    e["slots"] = slots
    e["slots_ok"] = all(n and n.startswith("MI_CSK_G1_") for _, n in slots)
    e["passed"] = (e["lods"] == e["lods_expected"] and e["tris_lod0"] == e["tris_lod0_expected"]
                   and not e["sockets_missing"] and not bad_loc and not bad_rot
                   and e.get("convex") == e["convex_expected"] and e["screen_sizes_ok"] and e["slots_ok"])
    return e


def check_slots():
    """G1 test 2 core: grid slots from the IMPORTED Level socket + grid numbers vs the Blender-computed slots_ue."""
    d = C.csk(C.SHOWCASE)
    m = unreal.load_asset(f"{C.MESH_DEST}/{C.SHOWCASE}")
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(m)
    out = {"socket_count": len(list(comp.get_all_socket_names())), "limit": C.SOCKET_LIMIT, "grids": []}
    per_class = {}
    for lv in d["levels"]:
        s = m.find_socket(lv["socket"])
        lt = unreal.Transform(location=s.get_editor_property("relative_location"),
                              rotation=s.get_editor_property("relative_rotation"), scale=V((1, 1, 1)))
        for g in lv["grids"]:
            (px, py), (fx, fy) = g["pitch_mm"], g["first_mm"]
            worst, k = 0.0, 0
            for r in range(g["rows"]):
                for c in range(g["cols"]):
                    local = C.blender_mm_to_ue_cm((fx + c * px, fy + r * py, 0.0))
                    p = lt.transform_location(V(local))
                    worst = max(worst, dist([p.x, p.y, p.z], g["slots_ue"][k]["loc_cm"]))
                    k += 1
            out["grids"].append({"level": lv["socket"], "class": g["class"], "slots": k, "max_err_cm": round(worst, 5)})
            per_class[g["class"]] = max(per_class.get(g["class"], 0.0), worst)
    out["max_err_cm_by_class"] = {k: round(v, 5) for k, v in per_class.items()}
    need = {"Card", "Slab", "Pack"}
    out["passed"] = (out["socket_count"] <= C.SOCKET_LIMIT and need <= set(per_class)
                     and all(v <= C.SEAT_TOL_CM for v in per_class.values()))
    return out


def check_level(path, expected, prefix=None):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok = les.load_level(path)
    actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()
              if unreal.Name(C.MANAGED_TAG) in list(a.tags)}
    missing, off = [], []
    n = 0
    for label, e in expected.items():
        if prefix is not None and not label.startswith(prefix):
            continue
        if prefix is None and label.startswith("Stress"):
            continue
        n += 1
        a = actors.get(label)
        if a is None:
            missing.append(label)
            continue
        loc = a.get_actor_location()
        err = dist([loc.x, loc.y, loc.z], e["loc_cm"])
        if err > C.SEAT_TOL_CM:
            off.append([label, round(err, 4)])
    rep = {"loaded": bool(ok), "actors": len(actors), "expected_checked": n, "missing": missing[:20],
           "off": off[:20]}
    if prefix == "Stress":
        attached = sum(1 for lbl, a in actors.items() if "_Card_" in lbl and a.get_attach_parent_actor() is not None)
        filled = sum(1 for lbl in actors if "_Filled_" in lbl)
        rep["attached_cards"], rep["filled_slabs"] = attached, filled
        rep["passed"] = bool(ok) and not missing and not off and attached >= 200 and filled >= 200
    else:
        rep["passed"] = bool(ok) and not missing and not off
    return rep


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "meshes": {}, "textures": {}}
    try:
        sms = _static_mesh_editor_subsystem()
        for name in C.MESHES:
            try:
                rep["meshes"][name] = check_mesh(name, sms)
            except Exception:  # noqa: BLE001
                rep["meshes"][name] = {"passed": False, "error": traceback.format_exc()[-1200:]}
        for name in C.TEXTURES:
            t = unreal.load_asset(f"{C.TEX_DEST}/{name}")
            if t is None:
                rep["textures"][name] = {"passed": False, "error": "missing"}
                continue
            w, h = int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())
            pot = w > 0 and h > 0 and (w & (w - 1)) == 0 and (h & (h - 1)) == 0
            rep["textures"][name] = {"size": [w, h], "srgb": bool(t.get_editor_property("srgb")),
                                     "passed": pot and bool(t.get_editor_property("srgb"))}
        rep["g1_test2_slots"] = check_slots()
        expected = json.loads((C.OUT / "map.json").read_text(encoding="utf-8")).get("expected", {})
        rep["level_main"] = check_level(C.LEVEL, expected)
        rep["level_stress"] = check_level(C.STRESS_LEVEL, expected, prefix="Stress")
        rep["manual"] = {
            "g1_test1_art": "Open L_CSK_G1, ArtRows: every face shows TL red / TR green / BL blue / BR yellow with TOP at "
                            "the top, on BOTH rows (Plain and Atlas), on cards, card backs, packs, pack backs, slab "
                            "labels and filled slabs; the atlas row shows the right line and cell number on each item.",
            "g1_test3_draws": "Open L_CSK_G1_Stress, merge Stress/Filled_ToBatch into one instanced actor, then compare "
                              "'stat scenerendering' (mesh draw calls) looking at the attached cases vs the batched ones, "
                              "and look through the case glass from the customer side: no slab window drawn in front "
                              "of the glass or over its neighbour.",
        }
        auto = [v["passed"] for v in rep["meshes"].values()] + [v["passed"] for v in rep["textures"].values()]
        auto += [rep["g1_test2_slots"]["passed"], rep["level_main"]["passed"], rep["level_stress"]["passed"]]
        rep["passed"] = all(auto)
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-3000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "verify.json", rep)
    unreal.log(f"CSK_STEP_DONE verify passed={rep['passed']} "
               f"slots_max_err_cm={rep.get('g1_test2_slots', {}).get('max_err_cm_by_class')}")


main()
