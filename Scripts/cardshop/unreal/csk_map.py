"""CardShopKit G1 step: maps (pythonscript commandlet, -nullrhi). Builds two levels from the imported assets only.

L_CSK_G1 (gate G1 tests 1 and 2, looked at in the editor):
  * ART ROW (a table on the customer side, Unreal +Y): row "Plain" uses the plain-texture instances, row "Atlas" the
    csk_pack_cards atlas cells. Cards and packs appear face up AND flipped (back up); slabs with a card in the Card
    socket; the filled slab; a top-loader with a card; an open booster box with 36 packs in its Pack_NN sockets.
    Every face carries the test pattern: TL red, TR green, BL blue, BR yellow, "TOP" at the top edge.
  * SHOWCASE at the origin with glass and doors on their sockets; S2 top-loaders with cards, S1 empty slabs with
    cards (front row) and filled slabs (back row), Deck two open boxes with packs + loose packs. Grid slots come from
    .csk.json ``slots_ue``; CONTAIN children use the imported mesh sockets (from the pipeline sidecars).
L_CSK_G1_Stress (gate G1 test 3): four showcases in a row. Cases A and B hold 200 EMPTY slabs, each with a card
  actor ATTACHED to its Card socket (SnapToTarget): the socket-attached path, 600 draws expected. Cases C and D hold
  200 FILLED slabs as plain actors in the folder "Stress/Filled_ToBatch": merge them into one instanced actor in the
  editor (G1_HANDOFF.md step), then compare stat scenerendering between the two halves.

Every actor is tagged CSK_G1; a re-run destroys exactly those. The expected transform of each actor is written to
WorkFiles/cardshop/g1/unreal/map.json for csk_verify.py.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import csk_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": [], "levels": {}}
EXPECTED = {}


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def R(roll=0.0, pitch=0.0, yaw=0.0):
    r = unreal.Rotator()
    r.roll, r.pitch, r.yaw = float(roll), float(pitch), float(yaw)
    return r


def T(loc=(0, 0, 0), rot=(0, 0, 0)):
    """rot is [roll, pitch, yaw] (the order .csk.json slots_ue uses)."""
    return unreal.Transform(location=V(loc), rotation=R(*rot), scale=V((1, 1, 1)))


def compose(child, parent):
    """World transform of ``child`` (relative) under ``parent`` (world): apply child, then parent."""
    return unreal.MathLibrary.compose_transforms(child, parent)


MESH = {}


def mesh(name):
    if name not in MESH:
        m = unreal.load_asset(f"{C.MESH_DEST}/{name}")
        if not isinstance(m, unreal.StaticMesh):
            raise RuntimeError(f"{name} is not imported (run the import step)")
        MESH[name] = m
    return MESH[name]


def socket_T(mesh_name, socket):
    s = mesh(mesh_name).find_socket(socket)
    if s is None:
        raise RuntimeError(f"{mesh_name} has no socket {socket!r} (was the sidecar applied?)")
    return unreal.Transform(location=s.get_editor_property("relative_location"),
                            rotation=s.get_editor_property("relative_rotation"), scale=V((1, 1, 1)))


def mi(name):
    m = unreal.load_asset(f"{C.MAT_DEST}/{name}")
    if m is None:
        raise RuntimeError(f"material {name} missing (run the materials step)")
    return m


def spawn(mesh_name, t, label, folder, overrides=None):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, t.translation, R())
    a.static_mesh_component.set_static_mesh(mesh(mesh_name))
    a.set_actor_transform(t, False, True)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    a.tags = [unreal.Name(C.MANAGED_TAG)]
    for slot, name in (overrides or {}).items():
        idx = [str(s.get_editor_property("material_slot_name")) for s in
               mesh(mesh_name).get_editor_property("static_materials")].index(slot)
        a.static_mesh_component.set_material(idx, mi(name))
    loc = a.get_actor_location()
    EXPECTED[label] = {"mesh": mesh_name, "loc_cm": [t.translation.x, t.translation.y, t.translation.z],
                       "got_cm": [loc.x, loc.y, loc.z]}
    return a


def open_level(path):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL.does_asset_exist(path):
        ok = les.load_level(path)
    else:
        try:
            ok = les.new_level(path, False)
        except TypeError:
            ok = les.new_level(path)
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(C.MANAGED_TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    return {"open": bool(ok), "managed_removed": removed}


def save_level(path):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les.save_current_level():
            return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"save_current_level: {exc}")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return bool(unreal.EditorLoadingAndSavingUtils.save_map(world, path))


def lighting(folder="Lighting"):
    out = []
    for cls, loc, rot in ((unreal.DirectionalLight, (0, 0, 500), R(0, -45, -135)), (unreal.SkyLight, (0, 0, 400), R()),
                          (unreal.SkyAtmosphere, (0, 0, 0), R())):
        a = EAS.spawn_actor_from_class(cls, V(loc), rot)
        a.set_folder_path(folder)
        a.tags = [unreal.Name(C.MANAGED_TAG)]
        out.append(a.get_class().get_name())
    try:
        sl = next(a for a in EAS.get_all_level_actors() if isinstance(a, unreal.SkyLight))
        sl.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"skylight realtime: {exc}")
    return out


def top_z(name):
    return C.csk(name)["render_aabb_mm"][1][2] / 10.0


def flipped(t_world, name):
    """The item turned over (180 deg about its X), resting on the same surface: lifted by its height."""
    return compose(T((0, 0, 0), (180, 0, 0)), compose(T((0, 0, top_z(name))), t_world))


def showcase(origin, folder, doors_open=0.0):
    base = T(origin)
    spawn(C.SHOWCASE, base, f"{folder}_Showcase", folder)
    spawn("SM_CSK_Showcase_Full_Glass_1778", base, f"{folder}_Glass", folder)
    for side, off in (("Door_L", 0.0), ("Door_R", doors_open)):
        t = compose(compose(T((off, 0, 0)), socket_T(C.SHOWCASE, side)), base)
        spawn("SM_CSK_Showcase_Full_Door_1778", t, f"{folder}_{side}", folder)
    return base


def slots(level, cls):
    d = C.csk(C.SHOWCASE)
    lv = next(l for l in d["levels"] if l["socket"] == level)
    g = next(x for x in lv["grids"] if x["class"] == cls)
    return [T(s["loc_cm"], s["rot"]) for s in g["slots_ue"]], g["cols"]


def box_with_packs(t, label, folder, pack_mi=None):
    spawn("SM_CSK_Box_Booster_S", t, label, folder)
    part = C.csk("SM_CSK_Box_Booster_S")["parts"]["Lid"]["open_ue"]
    spawn("SM_CSK_Box_Booster_S_Lid", compose(T(part["loc_cm"], part["rot"]), t), f"{label}_Lid", folder)
    n = 0
    for s in C.csk("SM_CSK_Box_Booster_S")["sockets"]:
        if s["name"].startswith("Pack_"):
            n += 1
            spawn("SM_CSK_Pack_Std_Sealed", compose(socket_T("SM_CSK_Box_Booster_S", s["name"]), t),
                  f"{label}_{s['name']}", folder, {"M_CSK_Pack": pack_mi} if pack_mi else None)
    return n


def build_main():
    rep = open_level(C.LEVEL)
    rep["lights"] = lighting()
    # ---------------- showcase seating (test 2 look)
    base = showcase((0, 0, 0), "Showcase", doors_open=42.0)
    s2, _ = slots("Level_S2", "CardProt")
    for i, t in enumerate(s2[:12]):
        w = compose(t, base)
        spawn("SM_CSK_TopLoader_35pt", w, f"S2_TopLoader_{i:02d}", "Showcase/S2")
        spawn("SM_CSK_Card_Std", compose(socket_T("SM_CSK_TopLoader_35pt", "Card"), w), f"S2_Card_{i:02d}", "Showcase/S2",
              {"M_CSK_Card": f"MI_CSK_G1_Card_Atlas_{i % 6}"})
    s1, cols = slots("Level_S1", "Slab")
    for i, t in enumerate(s1):
        w = compose(t, base)
        if i < cols:
            spawn("SM_CSK_Slab_Std", w, f"S1_Slab_{i:02d}", "Showcase/S1", {"M_CSK_SlabBody": f"MI_CSK_G1_SlabBody_Atlas_{i % 2}"})
            spawn("SM_CSK_Card_Std", compose(socket_T("SM_CSK_Slab_Std", "Card"), w), f"S1_Card_{i:02d}", "Showcase/S1",
                  {"M_CSK_Card": f"MI_CSK_G1_Card_Atlas_{i % 6}"})
        else:
            spawn("SM_CSK_Slab_Std_Filled", w, f"S1_Filled_{i:02d}", "Showcase/S1")
    boxes, _ = slots("Level_Deck", "BoxS")
    for i, t in enumerate(boxes[:2]):
        box_with_packs(compose(t, base), f"Deck_Box_{i}", "Showcase/Deck", f"MI_CSK_G1_Pack_Atlas_{i}")
    packs, _ = slots("Level_Deck", "Pack")
    for i, t in enumerate(packs[14:22]):
        spawn("SM_CSK_Pack_Std_Sealed", compose(t, base), f"Deck_Pack_{i:02d}", "Showcase/Deck",
              {"M_CSK_Pack": f"MI_CSK_G1_Pack_Atlas_{i % 3}"})
    # ---------------- art rows (test 1): a table on the customer side (Unreal +Y)
    table = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V((0, 95, 88)), R())
    table.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    table.set_actor_scale3d(V((2.6, 0.7, 0.04)))
    table.set_actor_label("ArtTable")
    table.set_folder_path("ArtRows")
    table.tags = [unreal.Name(C.MANAGED_TAG)]
    z = 90.0
    x0 = -120.0
    plain = [("SM_CSK_Card_Std", False, None), ("SM_CSK_Card_Std", True, None), ("SM_CSK_Pack_Std_Sealed", False, None),
             ("SM_CSK_Pack_Std_Sealed", True, None), ("SM_CSK_Slab_Std", False, None),
             ("SM_CSK_Slab_Std_Filled", False, None), ("SM_CSK_Slab_Std_Filled", True, None),
             ("SM_CSK_TopLoader_35pt", False, None)]
    atlas = [("SM_CSK_Card_Std", False, {"M_CSK_Card": f"MI_CSK_G1_Card_Atlas_{i}"}) for i in range(6)]
    atlas += [("SM_CSK_Card_Std", True, {"M_CSK_Card": "MI_CSK_G1_Card_Atlas_0"})]
    atlas += [("SM_CSK_Pack_Std_Sealed", False, {"M_CSK_Pack": f"MI_CSK_G1_Pack_Atlas_{k}"}) for k in range(3)]
    atlas += [("SM_CSK_Pack_Std_Sealed", True, {"M_CSK_Pack": "MI_CSK_G1_Pack_Atlas_0"})]
    atlas += [("SM_CSK_Slab_Std", False, {"M_CSK_SlabBody": f"MI_CSK_G1_SlabBody_Atlas_{k}"}) for k in range(2)]
    atlas += [("SM_CSK_Slab_Std_Filled", False, {"M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Atlas"})]
    atlas += [("SM_CSK_Slab_Std_Filled", True, {"M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Atlas"})]
    for row, (tag, items, y) in enumerate((("Plain", plain, 80.0), ("Atlas", atlas, 100.0))):
        x = x0
        for i, (name, flip, ov) in enumerate(items):
            w = T((x, y, z))
            if flip:
                w = flipped(w, name)
            label = f"Art{tag}_{i:02d}_{name.replace('SM_CSK_', '')}{'_Back' if flip else ''}"
            spawn(name, w, label, f"ArtRows/{tag}", ov)
            if name in ("SM_CSK_Slab_Std", "SM_CSK_TopLoader_35pt") and not flip:
                card_ov = {"M_CSK_Card": "MI_CSK_G1_Card_Atlas_0"} if tag == "Atlas" else None
                spawn("SM_CSK_Card_Std", compose(socket_T(name, "Card"), T((x, y, z))), label + "_Card",
                      f"ArtRows/{tag}", card_ov)
            x += 12.0 if "Card" in name or "Pack" in name else 14.0
    box_with_packs(T((x0 + 225.0, 90.0, z)), "ArtBox", "ArtRows/Box")       # clear of both rows
    rep["actors"] = sum(1 for a in EAS.get_all_level_actors() if unreal.Name(C.MANAGED_TAG) in list(a.tags))
    rep["saved"] = save_level(C.LEVEL)
    return rep


def build_stress():
    rep = open_level(C.STRESS_LEVEL)
    rep["lights"] = lighting()
    per_case = 100
    all_slots = []
    for level, cls in (("Level_Deck", "Slab"), ("Level_S1", "Slab"), ("Level_S2", "Slab")):
        all_slots += slots(level, cls)[0]
    if len(all_slots) < per_case:
        raise RuntimeError(f"only {len(all_slots)} slab slots per case, need {per_case}")
    attached = filled = 0
    for ci, (cx, mode) in enumerate(((-600.0, "attached"), (-400.0, "attached"), (-200.0, "filled"), (0.0, "filled"))):
        folder = f"Stress/{'Attached' if mode == 'attached' else 'Filled_ToBatch'}"
        base = showcase((cx, 0, 0), f"StressCase{ci}")
        for k, t in enumerate(all_slots[:per_case]):
            w = compose(t, base)
            if mode == "attached":
                slab = spawn("SM_CSK_Slab_Std", w, f"Stress{ci}_Slab_{k:03d}", folder)
                card = spawn("SM_CSK_Card_Std", compose(socket_T("SM_CSK_Slab_Std", "Card"), w),
                             f"Stress{ci}_Card_{k:03d}", folder, {"M_CSK_Card": f"MI_CSK_G1_Card_Atlas_{k % 6}"})
                snap = unreal.AttachmentRule.SNAP_TO_TARGET
                card.attach_to_actor(slab, "Card", snap, snap, snap, False)
                attached += 1
            else:
                spawn("SM_CSK_Slab_Std_Filled", w, f"Stress{ci}_Filled_{k:03d}", folder,
                      {"M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Atlas"})
                filled += 1
    rep["attached_slabs"], rep["filled_slabs"] = attached, filled
    rep["saved"] = save_level(C.STRESS_LEVEL)
    return rep


def main():
    t0 = time.time()
    try:
        REP["levels"]["main"] = build_main()
        REP["levels"]["stress"] = build_stress()
        errs = [lbl for lbl, e in EXPECTED.items()
                if max(abs(a - b) for a, b in zip(e["loc_cm"], e["got_cm"])) > C.SEAT_TOL_CM]
        REP["spawn_readback_errors"] = errs[:20]
        REP["passed"] = all(v.get("saved") for v in REP["levels"].values()) and not errs
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        REP["passed"] = False
    REP["expected"] = EXPECTED
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "map.json", REP)
    unreal.log(f"CSK_STEP_DONE map passed={REP['passed']} actors={len(EXPECTED)}")


main()
