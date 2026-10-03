"""DojoLab side of the ARMORY HALL two-way sync (WorkFiles/shared/armory_hall/SYNC.md): rebuild the armory interior and
the shell's window-backer lights in L_Dojo from the shared jsons. Hall + armory round (2026-10-01), revision 1.

Two halves, one file:

1. FILE STAGE (plain Python, no Unreal running on DojoLab):  py -3 -B dj_armory_sync.py files
   - The armory's material instances / masters / textures and the pack items (NinjaPack shuriken) are FILE COPIES of
     ArmoryLab's own .uasset packages into DojoLab/Content at the SAME package paths (/Game/ArmoryKit/...,
     /Game/NinjaPack/...): never an edit of theirs, and the copied bytes equal ArmoryLab's (sha256 recorded and compared
     with manifest.json). The copy set is the dependency closure (a string scan of each package's /Game/ imports)
     of: every material slot the interior pieces use + the item meshes of interior_layout.json.
   - A package is copied only when missing or when its sha256 differs (idempotent). Drift of ArmoryLab's file against
     manifest.json is reported (the armory chat then owes a manifest bump), not hidden.
   - Guard: STOP (exit 3) if any Unreal process has DojoLab open.

2. UNREAL STAGE (pythonscript commandlet on DojoLab, run by run_armory_sync.sh):
   - SM_AK_* meshes are IMPORTED from Exports/ArmoryKit/<piece>.fbx (the FBX is the shared source of truth) only when
     the FBX sha256 differs from this project's sync import manifest (or the asset is missing); a changed mesh is
     deleted and imported fresh (the armory chat's ak_import recipe: legacy FBX, no auto collision, one convex hull per
     UCX, imported normals, Import Mesh LODs ON, no lightmap UVs). Slots get the instance whose name equals the slot
     name. Nanite ON unless a slot's material derives from M_AK_Glass_Master (translucent), fallback at full detail.
   - DojoLab-only look (dj_armory_look.py, per level, never synced): the design lights' level scale, the emissive
     scale, shadows. Emissive armory instances get DojoLab child instances /Game/ArmoryHall/Materials/MI_DJA_<slot>
     (parent = the copied armory instance, Emissive Intensity x EMISSIVE_SCALE) set as per-actor overrides, so the
     copied armory assets stay byte-identical.
   - L_Dojo: the interior is planned from the jsons as pure data first: every Nanite piece is ONE actor ISM_<piece> with
     one InstancedStaticMeshComponent holding its instances in interior_layout.json order (finish stage 2026-10-01:
     461 actors -> 55 ISM + 9 glass actors; the glass pieces stay single actors because the copied armory masters carry
     no instanced-mesh usage flag), the items, the 114 design lights, the 10 shell backer lights, the level-only lights
     and the interior PPV. The plan's sha256 is tagged on every actor (DJA_spec_<hash>): when the level already holds
     exactly that plan and the transform / bounds / light gates pass, NOTHING is touched; otherwise every actor tagged
     DJ_ArmoryHall is destroyed and re-placed. Collision per interface.json gameplay classes (incl. 'glass': blocks the
     pawn, camera and visibility pass); decision D6: display cases, lanterns and vases are unwalkable
     (CanCharacterStepUpOn No + an unwalkable slope override).
   - CHANGE-ONLY WRITES (finish stage): MI_DJA_* are created / edited / saved only when their parent or value differs,
     meshes only when imported or their settings changed, the shell actors' channels / paper only when they differ,
     and L_Dojo is saved only when something in it changed: a second run with nothing new writes nothing.
   - Gates: FBX / material / texture sha256 vs manifest; every piece exists; transform (0.01 cm / 0.001 deg); world
     bounds vs interior_layout bbox_m within 1 cm (Nanite: the full-detail fallback geometry, dj_sc_nanite); every
     interior instance and light inside interface.json envelope.with_walls (0.012 m); the shell ids of
     hall_shell_layout.json all placed in L_Dojo (layout_showcase.json shell_id); shadowed local lights <= budget.
   Result: WorkFiles/dojo/build/unreal/armory_sync/sync.json; DJ_STEP_DONE armory_sync passed=...
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
SHARED = ROOT / "WorkFiles" / "shared" / "armory_hall"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "armory_sync"
DOJOLAB = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab")
ARMORYLAB = Path(r"C:\Users\Cody\Documents\Unreal Projects\ArmoryLab")    # READ ONLY (never opened in Unreal)
AK_EXPORTS = ROOT / "Exports" / "ArmoryKit"
HL_TO_WORLD = (22.0, 24.0, 0.5)
TAG = "DJ_ArmoryHall"
MESH_DEST = "/Game/ArmoryKit/Meshes"
MAT_DIR = "/Game/ArmoryKit/Materials"
DJA_DIR = "/Game/ArmoryHall/Materials"
GLASS_MASTER = "M_AK_Glass_Master"
EMISSIVE_PARAM = "Emissive Intensity"
UNWALKABLE_CLASSES = {"propblock", "glass"}
TOL_CM = 1.0


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jwrite(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, indent=1), encoding="utf-8")


def hl_to_world(v):
    return (v[0] + HL_TO_WORLD[0], v[1] + HL_TO_WORLD[1], v[2] + HL_TO_WORLD[2])


def loc_cm(v):
    return (v[0] * 100.0, -v[1] * 100.0, v[2] * 100.0)


def kelvin_rgb(k):
    """Tanner Helland's blackbody fit, exactly as the armory chat's ak_common uses it (linear RGB)."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def shared():
    return {k: jload(SHARED / f"{k}.json") for k in ("manifest", "interior_layout", "lights_design", "hall_shell_layout",
                                                    "interface")}


# ================================================================================================ FILE STAGE
def pkg_file(content_root, pkg):
    rel = pkg[len("/Game/"):]
    return content_root / (rel + ".uasset")


def deps_of(path):
    data = path.read_bytes()
    return sorted({m.decode("ascii") for m in re.findall(rb"/Game/[A-Za-z0-9_/]+", data)})


def closure(roots):
    src = ARMORYLAB / "Content"
    seen, todo, missing = set(), list(roots), []
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        f = pkg_file(src, p)
        if not f.exists():
            if not (src / p[len("/Game/"):]).is_dir():   # a folder path string in a package is not a dependency
                missing.append(p)
            seen.add(p)
            continue
        seen.add(p)
        for d in deps_of(f):
            if d not in seen and d != p:
                todo.append(d)
    return sorted(p for p in seen if pkg_file(src, p).exists()), sorted(set(missing))


def dojolab_busy():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match "
          "'DojoLab' } | ForEach-Object { $_.ProcessId }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return r.stdout.split()


def file_stage():
    t0 = time.time()
    busy = dojolab_busy()
    if busy:
        print(f"STOP: an Unreal process has DojoLab open (pid {busy}); nothing copied")
        sys.exit(3)
    S = shared()
    I, M = S["interior_layout"], S["manifest"]
    slots = sorted({s for p in I["pieces"].values() for s in p["slots"]})
    roots = [f"{MAT_DIR}/{s}" for s in slots] + sorted({it["ue_asset"] for it in I["items"]})
    pkgs, missing = closure(roots)
    rep = {"date": time.strftime("%Y-%m-%d %H:%M"), "manifest_revision": M["revision"], "slots": len(slots),
           "roots": len(roots), "packages": len(pkgs), "missing_in_armorylab": missing, "copied": [], "unchanged": 0,
           "sha": {}, "drift_vs_manifest": []}
    man_sha = {}
    for k, v in M["materials"]["assets"].items():
        man_sha[f"{MAT_DIR}/{k}"] = v["sha256"]
    for k, v in M["textures"].items():
        man_sha[f"/Game/ArmoryKit/Textures/{k}"] = v["armorylab_uasset_sha256"]
    for p in pkgs:
        src, dst = pkg_file(ARMORYLAB / "Content", p), pkg_file(DOJOLAB / "Content", p)
        h = sha256(src)
        rep["sha"][p] = h
        if p in man_sha and man_sha[p] != h:
            rep["drift_vs_manifest"].append({"package": p, "manifest": man_sha[p], "armorylab_now": h})
        if dst.exists() and sha256(dst) == h:
            rep["unchanged"] += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha256(dst) != h:
            raise RuntimeError(f"copy of {p} does not match its source")
        rep["copied"].append(p)
    rep["manifest_packages_not_in_closure"] = sorted(set(man_sha) - set(pkgs))
    rep["passed"] = not missing
    rep["sec"] = round(time.time() - t0, 1)
    jwrite(OUT / "files.json", rep)
    print(f"ARMORY_SYNC_FILES passed={rep['passed']} packages={len(pkgs)} copied={len(rep['copied'])} "
          f"unchanged={rep['unchanged']} missing={len(missing)} drift={len(rep['drift_vs_manifest'])}")
    return rep


# ================================================================================================ UNREAL STAGE
def unreal_stage():
    import unreal  # noqa: PLC0415
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import dj_sc_nanite as N  # noqa: PLC0415
    import dj_armory_look as LOOK  # noqa: PLC0415

    EAL = unreal.EditorAssetLibrary
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    AT = unreal.AssetToolsHelpers.get_asset_tools()
    MEL = unreal.MaterialEditingLibrary
    try:
        SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        SMS = None
    SMS = SMS or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": [], "setp_failed": [], "errors": []}
    S = shared()
    I, D, H, F, M = (S[k] for k in ("interior_layout", "lights_design", "hall_shell_layout", "interface", "manifest"))
    REP["revision"] = {"manifest": M["revision"], "interior_layout": I["revision"], "lights_design": D["revision"],
                       "hall_shell_layout": H["revision"], "interface": F["revision"]}
    CH = unreal.CollisionChannel
    RESP = {"block": unreal.CollisionResponseType.ECR_BLOCK, "ignore": unreal.CollisionResponseType.ECR_IGNORE}

    def setp(obj, k, v):
        try:
            obj.set_editor_property(k, v)
            return True
        except Exception as exc:  # noqa: BLE001
            REP["setp_failed"].append(f"{type(obj).__name__}.{k}: {str(exc)[:160]}")
            return False

    def V(t):
        return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))

    def rot(pitch=0.0, yaw=0.0, roll=0.0):
        r = unreal.Rotator()
        r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
        return r

    # ---------------------------------------------------------------- 1. hashes
    fbx_rows, drift = {}, []
    for piece in sorted(I["pieces"]):
        f = AK_EXPORTS / f"{piece}.fbx"
        h = sha256(f) if f.exists() else None
        want = M["fbx"].get(piece, {}).get("sha256")
        fbx_rows[piece] = {"sha256": h, "manifest": want, "match": h == want}
        if h != want:
            drift.append(piece)
    REP["fbx_sha_drift"] = drift
    files = jload(OUT / "files.json") if (OUT / "files.json").exists() else {}
    copied_ok = []
    for p, h in files.get("sha", {}).items():
        f = pkg_file(DOJOLAB / "Content", p)
        copied_ok.append(f.exists() and sha256(f) == h)
    REP["copied_packages"] = {"n": len(copied_ok), "byte_identical": sum(copied_ok),
                              "drift_vs_manifest": files.get("drift_vs_manifest", [])}

    # ---------------------------------------------------------------- 2. meshes
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    man_path = OUT / "import_manifest.json"
    man = jload(man_path) if man_path.exists() else {}
    man0 = json.dumps(man, sort_keys=True)
    force = os.environ.get("DJ_ARMORY_FORCE_IMPORT", "0") == "1"

    def mesh_options():
        ui = unreal.FbxImportUI()
        for k, v in (("automated_import_should_detect_type", False),
                     ("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH), ("import_as_skeletal", False),
                     ("import_mesh", True), ("import_materials", False), ("import_textures", False),
                     ("import_animations", False)):
            ui.set_editor_property(k, v)
        sm = ui.get_editor_property("static_mesh_import_data")
        for k, v in (("import_mesh_lods", True), ("auto_generate_collision", False), ("one_convex_hull_per_ucx", True),
                     ("combine_meshes", False), ("generate_lightmap_u_vs", False),
                     ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                     ("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE),
                     ("convert_scene", True), ("convert_scene_unit", True), ("force_front_x_axis", False),
                     ("import_uniform_scale", 1.0), ("build_nanite", False)):
            sm.set_editor_property(k, v)
        return ui

    def master_of(mi):
        m, chain = mi, []
        while isinstance(m, unreal.MaterialInstance):
            chain.append(m.get_name())
            m = m.get_editor_property("parent")
        return (m.get_name() if m else None), chain

    mats = {}

    def mat(slot):
        if slot not in mats:
            mats[slot] = unreal.load_asset(f"{MAT_DIR}/{slot}")
        return mats[slot]

    meshes = {}
    REP["meshes"] = {}
    for piece, prow in sorted(I["pieces"].items()):
        path = f"{MESH_DEST}/{piece}"
        e = {"sha256": fbx_rows[piece]["sha256"]}
        try:
            h = fbx_rows[piece]["sha256"]
            if not force and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = True
            else:
                if EAL.does_asset_exist(path):
                    e["deleted_before_import"] = bool(EAL.delete_asset(path))
                task = unreal.AssetImportTask()
                for k, v in (("filename", str(AK_EXPORTS / f"{piece}.fbx")), ("destination_path", MESH_DEST),
                             ("destination_name", piece), ("automated", True), ("replace_existing", True),
                             ("replace_existing_settings", True), ("save", False), ("factory", unreal.FbxFactory()),
                             ("options", mesh_options())):
                    task.set_editor_property(k, v)
                AT.import_asset_tasks([task])
                e["imported"] = True
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"{path} is not a StaticMesh")
            dirty = "imported" in e
            slots_now, glass, unmatched = [], False, []
            for i, sm in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(sm.get_editor_property("material_slot_name"))
                slots_now.append(slot)
                mi = mat(slot)
                if mi is None:
                    unmatched.append(slot)
                    continue
                if master_of(mi)[0] == GLASS_MASTER:
                    glass = True
                cur = sm.get_editor_property("material_interface")
                if cur is None or cur.get_path_name() != mi.get_path_name():
                    mesh.set_material(i, mi)
                    dirty = True
            e["slots"], e["unmatched"] = slots_now, unmatched
            want_nanite = not glass and not unmatched
            ns = mesh.get_editor_property("nanite_settings")
            want_t = unreal.NaniteFallbackTarget.RELATIVE_ERROR
            if (bool(ns.get_editor_property("enabled")) != want_nanite
                    or (want_nanite and (ns.get_editor_property("fallback_target") != want_t
                                         or float(ns.get_editor_property("fallback_relative_error")) != 0.0))):
                ns.set_editor_property("enabled", want_nanite)
                ns.set_editor_property("fallback_target", want_t)
                ns.set_editor_property("fallback_relative_error", 0.0)
                ns.set_editor_property("fallback_percent_triangles", 1.0)
                SMS.set_nanite_settings(mesh, ns, True)
                dirty = True
            e["nanite"] = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
            if prow["collision_class"] in UNWALKABLE_CLASSES:   # decision D6: an unwalkable slope override
                bs = mesh.get_editor_property("body_setup")
                wso = bs.get_editor_property("walkable_slope_override")
                if wso.get_editor_property("walkable_slope_behavior") != unreal.WalkableSlopeBehavior.WALKABLE_SLOPE_UNWALKABLE:
                    wso.set_editor_property("walkable_slope_behavior", unreal.WalkableSlopeBehavior.WALKABLE_SLOPE_UNWALKABLE)
                    wso.set_editor_property("walkable_slope_angle", 0.0)
                    bs.set_editor_property("walkable_slope_override", wso)
                    dirty = True
                e["unwalkable"] = True
            agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
            e["convex"] = len(agg.get_editor_property("convex_elems"))
            e["ucx_expected"] = prow.get("ucx")
            if dirty:
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
                if e["saved"]:
                    man[path] = h
            meshes[piece] = mesh
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
            REP["errors"].append(f"mesh {piece}")
        REP["meshes"][piece] = e
    if json.dumps(man, sort_keys=True) != man0:    # finish stage: written only when an import changed it
        jwrite(man_path, man)
    REP["meshes_saved"] = sorted(p for p, e in REP["meshes"].items() if e.get("saved"))

    # ---------------------------------------------------------------- 3. DojoLab-only emissive children (change only)
    REP["emissive_overrides"] = {}
    REP["assets_saved"] = []
    dja = {}

    def child_mi(path, parent, scalars, vectors=None):
        """A DojoLab child MI with these scalars (and vectors: {name: (r, g, b)}, voices_paper stage); created / edited /
        saved ONLY when it differs (finish stage)."""
        child = unreal.load_asset(path)
        changed = False
        if child is None:
            d, n = path.rsplit("/", 1)
            child = AT.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            changed = True
        par = child.get_editor_property("parent")
        if par is None or par.get_path_name() != parent.get_path_name():
            MEL.set_material_instance_parent(child, parent)
            changed = True
        for k, v in scalars.items():
            try:
                cur = float(MEL.get_material_instance_scalar_parameter_value(child, k))
            except Exception:  # noqa: BLE001
                cur = None
            if cur is None or abs(cur - float(v)) > 1e-6 * max(1.0, abs(float(v))):
                MEL.set_material_instance_scalar_parameter_value(child, k, float(v))
                changed = True
        for k, v in (vectors or {}).items():
            want_c = [float(c) for c in (list(v) + [1.0])[:4]]
            try:
                c = MEL.get_material_instance_vector_parameter_value(child, k)
                cur = [c.r, c.g, c.b, c.a]
            except Exception:  # noqa: BLE001
                cur = None
            if cur is None or max(abs(a - b) for a, b in zip(cur, want_c)) > 1e-5:
                MEL.set_material_instance_vector_parameter_value(child, k, unreal.LinearColor(*want_c))
                changed = True
        if changed:
            MEL.update_material_instance(child)
            EAL.save_asset(path, only_if_is_dirty=False)
            REP["assets_saved"].append(path)
        return child

    for slot in sorted({s for p in I["pieces"].values() for s in p["slots"]}):
        mi = mat(slot)
        if mi is None:
            continue
        try:
            names = [str(n) for n in MEL.get_scalar_parameter_names(mi)]
        except Exception:  # noqa: BLE001
            names = []
        if EMISSIVE_PARAM not in names:
            continue
        base = float(MEL.get_material_instance_scalar_parameter_value(mi, EMISSIVE_PARAM))
        want = base * LOOK.EMISSIVE_SCALE * LOOK.EMISSIVE_ROLE.get(slot, 1.0)
        path = f"{DJA_DIR}/MI_DJA_{slot[2:] if slot.startswith('M_') else slot}"
        tint = getattr(LOOK, "EMISSIVE_TINT", {}).get(slot)   # voices_paper stage: per-level tint (dj_armory_look)
        dja[slot] = child_mi(path, mi, {EMISSIVE_PARAM: want}, {"Emissive Tint": tint} if tint else None)
        REP["emissive_overrides"][slot] = {"mi": path, "armory": round(base, 4), "dojolab": round(want, 6)}
        if tint:
            REP["emissive_overrides"][slot]["tint"] = list(tint)

    # ---------------------------------------------------------------- 4. level: the PLAN (pure data), then place or keep
    # the ISM test reads the usage flags from disk BEFORE the level loads (an editor may set a missing usage flag in
    # memory when it meets an existing ISM, which -game cannot)
    ism_ok, ism_blocked = {}, set()
    for piece, mesh in meshes.items():
        ok = bool(getattr(LOOK, "INTERIOR_ISM", True))
        for sm in mesh.get_editor_property("static_materials"):
            b = mat(str(sm.get_editor_property("material_slot_name")))
            while isinstance(b, unreal.MaterialInstance):
                b = b.get_editor_property("parent")
            if b is None or not bool(b.get_editor_property("used_with_instanced_static_meshes")):
                ok = False
                ism_blocked.add(b.get_name() if b is not None else "None")
        ism_ok[piece] = ok
    LEVEL = "/Game/Dojo/Maps/L_Dojo"
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["open_ok"] = bool(les.load_level(LEVEL))
    classes = F["gameplay"]["collision_classes"]
    env = F["envelope"]["with_walls"]
    tol = 0.012

    def inside(p):
        return (env["x"][0] - tol <= p[0] <= env["x"][1] + tol and env["y"][0] - tol <= p[1] <= env["y"][1] + tol
                and env["z"][0] - tol <= p[2] <= env["z"][1] + tol)

    # finish stage (2026-10-01): every Nanite interior piece is ONE actor with one InstancedStaticMeshComponent (its
    # instances in interior_layout.json order, world space; label ISM_<piece>), so placement stays driven by the json
    # and the level holds 55 + 9 interior mesh actors instead of 461. The glass pieces (M_AK_Glass_Master, translucent,
    # not Nanite: the copied armory masters carry no instanced-static-mesh usage flag and must stay byte-identical) and
    # the six items stay single actors.
    # FINISH stage measurement (finish/caps/ism_trial): with ISM the copied armory masters render the DEFAULT material in
    # -game ('missing usage flag InstancedStaticMeshes', 92 materials): the usage flag lives on the masters, which are
    # byte copies of ArmoryLab's packages and are never edited here. So a piece goes into an ISM only when every slot's
    # base material already carries used_with_instanced_static_meshes (the armory chat sets it on its masters); until
    # then every piece stays a single actor. Measured (finish/perf_probe run 1): hiding all 461 interior mesh actors
    # changed the frame time by +0.65 / -0.05 ms, so single actors cost no render-thread time worth the switch.
    plan = {"version": 3, "meshes": [], "lights": [], "level_lights": [], "ppv": None}
    by_piece = {}
    for it in I["instances"]:
        by_piece.setdefault(it["piece"], []).append(it)
    for piece in sorted(by_piece):
        mesh = meshes.get(piece)
        if mesh is None:
            REP["errors"].append(f"no mesh for {piece}")
            continue
        nan = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
        mats = {}
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            if slot in dja:
                mats[i] = dja[slot].get_path_name()
        rows = [{"id": it["id"], "loc_cm": [round(v, 3) for v in loc_cm(hl_to_world(it["loc_m"]))],
                 "yaw": round(-float(it["rot_z_deg"]), 4), "bbox_m": it["bbox_m"], "group": it["group"],
                 "cls": it["collision_class"]} for it in by_piece[piece]]
        common = {"piece": piece, "mesh": mesh.get_path_name(), "materials": mats, "nanite": nan,
                  "cls": by_piece[piece][0]["collision_class"], "group": by_piece[piece][0]["group"],
                  "cast_shadow": piece not in LOOK.NO_SHADOW_PIECES}
        if nan and ism_ok[piece] and len({r["cls"] for r in rows}) == 1:
            plan["meshes"].append(dict(common, kind="ism", label=f"ISM_{piece}", rows=rows))
        else:
            for r in rows:
                plan["meshes"].append(dict(common, kind="sma", label=f"{piece}__{r['id']}", rows=[r], cls=r["cls"],
                                           group=r["group"]))
    for it in I["items"]:
        im = unreal.load_asset(it["ue_asset"])
        if im is None:
            REP["errors"].append(f"item mesh missing {it['ue_asset']}")
            continue
        plan["meshes"].append({"kind": "item", "label": f"Item_{it['name']}", "mesh": im.get_path_name(), "materials": {},
                               "cls": it["collision_class"], "group": "Items", "cast_shadow": True, "piece": it["name"],
                               "rows": [{"id": it["name"], "loc_cm": [round(v, 3) for v in loc_cm(hl_to_world(it["loc_m"]))],
                                         "yaw": round(-float(it["rot_z_deg"]), 4), "bbox_m": None}]})

    def light_spec(Lr, ue, world, kelvin, cd, shadows, folder, spec_off, visible=True):
        t = Lr["type"]
        dz = Lr["design"]
        sp = {"name": Lr["name"], "type": t, "role": Lr["role"], "loc_cm": [round(v, 3) for v in loc_cm(world)],
              "pitch": float(ue.get("pitch", 0.0)), "yaw": float(ue.get("yaw", 0.0)), "cd": round(float(cd), 6),
              "kelvin": float(kelvin), "atten_cm": float(LOOK.ATTEN_ROLE_CM.get(Lr["role"], LOOK.ATTENUATION_CM)),
              "shadows": bool(shadows), "spec_off": bool(spec_off), "folder": folder, "visible": bool(visible)}
        if t == "rect":
            w, h = Lr.get("size_m") or dz["size"]
            if "aim_m" in Lr or Lr.get("faces"):
                sp["source_w_cm"], sp["source_h_cm"] = w * 100.0, h * 100.0
            else:
                sp["source_w_cm"], sp["source_h_cm"] = h * 100.0, w * 100.0
            sp["barn_door_cm"] = float(ue.get("barn_door_cm") or 0.0)
        elif t == "spot":
            half = float(dz["angle_deg"]) / 2.0
            sp["outer"], sp["inner"] = half, half * (1.0 - float(dz.get("blend", 0.5)))
        else:
            sp["radius_cm"] = float(dz.get("radius", 0.1)) * 100.0
        return sp

    n_shadow, outside = 0, []
    for Lr in D["lights"]:
        ue = Lr["ue_armorylab_night"]
        role = Lr["role"]
        cd = (float(ue["candela"]) * LOOK.LIGHT_SCALE * LOOK.ROLE_SCALE.get(role, 1.0)
              * getattr(LOOK, "LIGHT_TRIM", {}).get(Lr["name"], 1.0))
        shadows = bool(ue["shadows"]) and role not in LOOK.SHADOW_OFF_ROLES
        n_shadow += int(shadows)
        if not inside(Lr["loc_m"]):
            outside.append(Lr["name"])
        plan["lights"].append(light_spec(Lr, ue, hl_to_world(Lr["loc_m"]), float(ue["kelvin"]), cd, shadows,
                                         "Lights/" + role, role in ("glow", "panel", "rack", "case", "lantern")))
    for Lr in H["lights"]:   # the shell's window backers (shell-owned, per-level intensity; rev 2: DojoLab off)
        ue = {"pitch": 0.0, "yaw": 0.0 if Lr["faces"] == "+x" else 180.0, "barn_door_cm": 0.0}
        plan["lights"].append(light_spec(dict(Lr, design={"size": Lr["size_m"]}), ue, hl_to_world(Lr["loc_m"]),
                                         float(Lr["kelvin"]), LOOK.BACKER_CD, False, "Lights/backer", True,
                                         visible=LOOK.BACKER_CD > 0.0))
    for Lr in getattr(LOOK, "LEVEL_LIGHTS", []):   # DojoLab-only level lights (rev 2: DJ_ThresholdFill)
        ue = {"pitch": Lr["pitch_deg"], "yaw": Lr["yaw_ue_deg"], "barn_door_cm": Lr.get("barn_door_cm", 0.0)}
        if not inside(Lr["loc_m"]):
            outside.append(Lr["name"])
        plan["level_lights"].append(light_spec(dict(Lr, design={"size": Lr["size_m"]}, aim_m=True), ue,
                                               hl_to_world(Lr["loc_m"]), float(Lr["kelvin"]), float(Lr["cd"]), False,
                                               "Lights/level", True))
    if LOOK.PPV:
        plan["ppv"] = {"label": "PostProcess_ArmoryHall", "loc_cm": [round(v, 3) for v in loc_cm(hl_to_world(LOOK.PPV["centre_hl"]))],
                       "scale": [s / 2.0 for s in LOOK.PPV["size_m"]], "priority": float(LOOK.PPV["priority"]),
                       "blend_radius_cm": float(LOOK.PPV["blend_radius_cm"]),
                       "settings": {k: (list(v) if isinstance(v, tuple) else v) for k, v in LOOK.PPV["settings"].items()}}
    spec_hash = hashlib.sha256(json.dumps(plan, sort_keys=True, default=str).encode()).hexdigest()[:16]
    SPEC_TAG = unreal.Name("DJA_spec_" + spec_hash)
    REP["spec_hash"] = spec_hash
    want_labels = ({m["label"] for m in plan["meshes"]} | {L["name"] for L in plan["lights"] + plan["level_lights"]}
                   | ({plan["ppv"]["label"]} if plan["ppv"] else set()))

    def channels(c0, c1):
        lc = unreal.LightingChannels()
        lc.set_editor_property("channel0", bool(c0))
        lc.set_editor_property("channel1", bool(c1))
        return lc

    INTERIOR_CH = channels(True, True)

    def collision(comp, cls):
        c = classes[cls]
        if c.get("no_collision"):
            comp.set_collision_profile_name("NoCollision")
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_collision_response_to_all_channels(RESP["ignore"])
            return
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_collision_response_to_channel(CH.ECC_PAWN, RESP[c["pawn"]])
        comp.set_collision_response_to_channel(CH.ECC_CAMERA, RESP[c["camera"]])
        comp.set_collision_response_to_channel(CH.ECC_VISIBILITY, RESP[c["visibility"]])
        if cls in UNWALKABLE_CLASSES:   # decision D6: no standing on display cases, lanterns, vases
            setp(comp, "can_character_step_up_on", unreal.CanBeCharacterBase.ECB_NO)

    def tag(a, label, folder, *extra):
        a.set_actor_label(label)
        a.set_folder_path("ArmoryHall/" + folder)
        a.tags = [unreal.Name(TAG), SPEC_TAG] + [unreal.Name(t) for t in extra]

    def place_mesh(m):
        mesh = unreal.load_asset(m["mesh"])
        if m["kind"] == "ism":
            a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V((0, 0, 0)), rot())
            a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
            sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            root = sds.k2_gather_subobject_data_for_instance(a)[0]
            handle, _fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=root, new_class=unreal.InstancedStaticMeshComponent, blueprint_context=None))
            comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(
                unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
            comp.set_static_mesh(mesh)
            comp.set_mobility(unreal.ComponentMobility.STATIC)
            comp.add_instances([unreal.Transform(V(r["loc_cm"]), rot(yaw=r["yaw"]), V((1, 1, 1))) for r in m["rows"]],
                               False, True)
            extra = ("DJA_ism", "DJA_" + m["cls"])
        else:
            r = m["rows"][0]
            a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(r["loc_cm"]), rot(yaw=r["yaw"]))
            comp = a.static_mesh_component
            comp.set_static_mesh(mesh)
            comp.set_mobility(unreal.ComponentMobility.STATIC)
            if m["kind"] == "item":
                a.set_actor_scale3d(V((1.0, 1.0, 1.0)))   # never mirrored (the HookedCross must never be)
                extra = ("DJA_item",)
            else:
                extra = ("DJA_" + m["cls"], "DJA_" + r["id"])
        for i, path in m["materials"].items():
            comp.set_material(int(i), unreal.load_asset(path))
        collision(comp, m["cls"])
        setp(comp, "lighting_channels", INTERIOR_CH)
        if not m["cast_shadow"]:
            setp(comp, "cast_shadow", False)
        tag(a, m["label"], m["group"], *extra)
        return a

    def place_light(sp):
        cls = {"rect": unreal.RectLight, "point": unreal.PointLight, "spot": unreal.SpotLight}[sp["type"]]
        a = EAS.spawn_actor_from_class(cls, V(sp["loc_cm"]), rot(sp["pitch"], sp["yaw"]))
        comp = a.get_editor_property({"rect": "rect_light_component", "point": "point_light_component",
                                      "spot": "spot_light_component"}[sp["type"]])
        setp(comp, "mobility", unreal.ComponentMobility.MOVABLE)
        setp(comp, "intensity_units", unreal.LightUnits.CANDELAS)
        setp(comp, "intensity", sp["cd"])
        r, g, b = kelvin_rgb(sp["kelvin"])
        comp.set_light_color(unreal.LinearColor(r, g, b, 1.0), True)
        setp(comp, "attenuation_radius", sp["atten_cm"])
        setp(comp, "cast_shadows", sp["shadows"])
        setp(comp, "volumetric_scattering_intensity", 0.0)
        if sp["spec_off"]:
            setp(comp, "specular_scale", 0.0)
        setp(comp, "lighting_channels", channels(False, True))
        if sp["type"] == "rect":
            setp(comp, "source_width", sp["source_w_cm"])
            setp(comp, "source_height", sp["source_h_cm"])
            if sp["barn_door_cm"] > 0.0:
                setp(comp, "barn_door_angle", 0.0)
            setp(comp, "barn_door_length", sp["barn_door_cm"])
        elif sp["type"] == "spot":
            setp(comp, "outer_cone_angle", sp["outer"])
            setp(comp, "inner_cone_angle", sp["inner"])
            setp(comp, "source_radius", 4.0)
        else:
            setp(comp, "source_radius", sp["radius_cm"])
        extra = ["DJA_light", "DJA_role_" + str(sp["role"])]
        if not sp["visible"]:
            setp(comp, "visible", False)
            extra.append("DJA_off")
        tag(a, sp["name"], sp["folder"], *extra)
        return a

    def place_ppv(p):
        a = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V(p["loc_cm"]), rot())
        setp(a, "unbound", False)
        setp(a, "priority", p["priority"])
        setp(a, "blend_radius", p["blend_radius_cm"])
        a.set_actor_scale3d(V(p["scale"]))   # the brush is 200 cm: scale = size_m / 2
        pp = a.get_editor_property("settings")
        for k, v in p["settings"].items():
            if isinstance(v, (tuple, list)) and len(v) == 4:   # grade vectors (e.g. color_saturation_shadows)
                v = unreal.Vector4(*[float(t) for t in v])
            setp(pp, "override_" + k, True)
            setp(pp, k, v)
        setp(a, "settings", pp)
        tag(a, p["label"], "PostProcess", "DJA_ppv")
        return a

    def live_actors():
        return {a.get_actor_label(): a for a in EAS.get_all_level_actors() if unreal.Name(TAG) in list(a.tags)}

    def inst_transform(comp, i):
        t = comp.get_instance_transform(i, True)
        return t[-1] if isinstance(t, tuple) else t

    fbox = {}

    def gate_meshes(live):
        """transform (0.01 cm / 0.001 deg) + world bounds (1 cm, Nanite: the full-detail fallback box) per instance"""
        g = {"failures": [], "max_bounds_err_cm": 0.0, "max_t_err_cm": 0.0, "n_placed": 0}
        for m in plan["meshes"]:
            a = live.get(m["label"])
            if a is None:
                g["failures"].append({"label": m["label"], "missing": True})
                continue
            if m["kind"] == "ism":
                comp = a.get_component_by_class(unreal.InstancedStaticMeshComponent)
                n = int(comp.get_instance_count()) if comp else -1
                if n != len(m["rows"]) or comp.get_editor_property("static_mesh").get_path_name() != m["mesh"]:
                    g["failures"].append({"label": m["label"], "instances": n, "want": len(m["rows"])})
                    continue
                trs = [inst_transform(comp, i) for i in range(n)]
                mesh = comp.get_editor_property("static_mesh")
            else:
                comp = a.static_mesh_component
                trs = [a.get_actor_transform()]
                mesh = comp.get_editor_property("static_mesh")
                if mesh is None or mesh.get_path_name() != m["mesh"]:
                    g["failures"].append({"label": m["label"], "mesh": str(mesh)})
                    continue
            for r, t in zip(m["rows"], trs):
                g["n_placed"] += 1 if m["kind"] != "item" else 0
                tl, tr = t.translation, t.rotation.rotator()
                terr = max(abs(tl.x - r["loc_cm"][0]), abs(tl.y - r["loc_cm"][1]), abs(tl.z - r["loc_cm"][2]))
                dy = abs(((tr.yaw - r["yaw"]) + 180.0) % 360.0 - 180.0)
                g["max_t_err_cm"] = max(g["max_t_err_cm"], terr)
                err = 0.0
                if r.get("bbox_m"):
                    b = r["bbox_m"]
                    wmin, wmax = hl_to_world(b[:3]), hl_to_world(b[3:])
                    want = [wmin[0] * 100, -wmax[1] * 100, wmin[2] * 100, wmax[0] * 100, -wmin[1] * 100, wmax[2] * 100]
                    if m["piece"] not in fbox:
                        fbox[m["piece"]] = N.fallback_box(mesh)
                    lo, hi = fbox[m["piece"]]
                    pts = [t.transform_location(unreal.Vector(x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                           for z in (lo[2], hi[2])]
                    got = [min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
                           max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)]
                    err = max(abs(p - q) for p, q in zip(got, want))
                    g["max_bounds_err_cm"] = max(g["max_bounds_err_cm"], err)
                if err > TOL_CM or terr > 0.01 or dy > 0.001:
                    g["failures"].append({"id": r["id"], "piece": m["piece"], "bounds_err_cm": round(err, 3),
                                          "t_err_cm": round(terr, 4), "yaw_err": round(dy, 4)})
        g["passed"] = g["n_placed"] == len(I["instances"]) and not g["failures"]
        return g

    def gate_lights(live):
        bad = []
        for sp in plan["lights"] + plan["level_lights"]:
            a = live.get(sp["name"])
            comp = a.get_component_by_class(unreal.LocalLightComponent) if a else None
            if comp is None:
                bad.append(sp["name"])
                continue
            l = a.get_actor_location()
            if (max(abs(l.x - sp["loc_cm"][0]), abs(l.y - sp["loc_cm"][1]), abs(l.z - sp["loc_cm"][2])) > 0.01
                    or abs(float(comp.get_editor_property("intensity")) - sp["cd"]) > 1e-3 * max(1.0, sp["cd"])
                    or bool(comp.get_editor_property("cast_shadows")) != sp["shadows"]
                    or abs(float(comp.get_editor_property("attenuation_radius")) - sp["atten_cm"]) > 0.01):
                bad.append(sp["name"])
        return bad

    live = live_actors()
    force = os.environ.get("DJ_ARMORY_FORCE_LEVEL", "0") == "1"
    keep = (not force and set(live) == want_labels
            and all(SPEC_TAG in list(a.tags) for a in live.values()))
    REP["level_kept"] = False
    if keep:
        g0 = gate_meshes(live)
        lb = gate_lights(live)
        keep = g0["passed"] and not lb
        REP["keep_check"] = {"mesh_gate": g0["passed"], "lights_bad": lb[:10]}
    dirty = False
    if keep:
        REP["level_kept"] = True
        REP["actors_removed"] = 0
    else:
        removed = 0
        for a in live.values():
            EAS.destroy_actor(a)
            removed += 1
        REP["actors_removed"] = removed
        for m in plan["meshes"]:
            try:
                place_mesh(m)
            except Exception:  # noqa: BLE001
                REP["errors"].append(f"place {m['label']}: {traceback.format_exc()[-600:]}")
        for sp in plan["lights"] + plan["level_lights"]:
            place_light(sp)
        if plan["ppv"]:
            place_ppv(plan["ppv"])
        dirty = True
        live = live_actors()
    gate = gate_meshes(live)
    REP["bounds_gate"] = gate
    REP["lights_gate_bad"] = gate_lights(live)
    REP["actors"] = {"total": len(live), "ism": sum(1 for m in plan["meshes"] if m["kind"] == "ism"),
                     "ism_instances": sum(len(m["rows"]) for m in plan["meshes"] if m["kind"] == "ism"),
                     "single_mesh_actors": sum(1 for m in plan["meshes"] if m["kind"] == "sma"),
                     "items": sum(1 for m in plan["meshes"] if m["kind"] == "item"),
                     "lights": len(plan["lights"]) + len(plan["level_lights"]), "ppv": int(bool(plan["ppv"]))}
    REP["ism_ids"] = {m["piece"]: [r["id"] for r in m["rows"]] for m in plan["meshes"] if m["kind"] == "ism"}
    REP["ism_blocked_by_masters_without_usage_flag"] = sorted(ism_blocked)
    REP["items"] = [m["piece"] for m in plan["meshes"] if m["kind"] == "item"]
    REP["lights"] = [{"name": sp["name"], "role": sp["role"], "cd": sp["cd"], "shadows": sp["shadows"],
                      "off": not sp["visible"]} for sp in plan["lights"]]
    REP["level_lights"] = [{"name": sp["name"], "cd": sp["cd"]} for sp in plan["level_lights"]]
    REP["ppv"] = LOOK.PPV
    REP["shadowed_local_lights"] = n_shadow
    REP["shadow_budget"] = LOOK.SHADOW_BUDGET
    REP["lights_outside_envelope"] = outside

    # the shell faces that face the interior join lighting channel 1 (DJ_Managed actors placed by dj_sc_level: run this
    # sync after every sc_level step); each setting is read first and written only when it differs
    L = jload(ROOT / "WorkFiles" / "dojo" / "build" / "showcase" / "layout_showcase.json")
    all_by_label = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}

    def same_channels(a, b):
        return all(bool(a.get_editor_property(k)) == bool(b.get_editor_property(k)) for k in ("channel0", "channel1"))

    def ensure_channels(smc, want):
        nonlocal dirty
        cur = smc.get_editor_property("lighting_channels")
        if same_channels(cur, want):
            return True
        ok = setp(smc, "lighting_channels", want)
        dirty = dirty or ok
        return ok

    def ensure_material(smc, slot_name, mi):
        nonlocal dirty
        for k, sm in enumerate(smc.static_mesh.get_editor_property("static_materials")):
            if str(sm.get_editor_property("material_slot_name")) == slot_name:
                cur = smc.get_material(k)
                if cur is None or cur.get_path_name() != mi.get_path_name():
                    smc.set_material(k, mi)
                    dirty = True

    want_lbl = set()
    for n, i in enumerate(L["instances"]):
        x, y, _z = i["loc"]
        if i.get("removed") or not i["piece"].startswith("SM_DKH_"):
            continue
        if i["piece"] == "SM_DKH_DoorLeaf_Parked" and not getattr(LOOK, "PARKED_LEAF_CHANNEL1", True):
            continue   # fix round: the parked leaves stay on channel 0 only (sun / sky through the doors)
        if (23.9 <= y <= 24.3 and 15.0 <= x <= 27.5) or i["piece"] in ("SM_DKH_Frame_Open", "SM_DKH_DoorLeaf_Parked"):
            want_lbl.add(f"{i['piece']}__{n:04d}")
    got = 0
    for lbl in want_lbl:
        a = all_by_label.get(lbl)
        smc = a.get_component_by_class(unreal.StaticMeshComponent) if a else None
        if smc is not None and ensure_channels(smc, INTERIOR_CH):
            got += 1
    REP["shell_faces_on_channel1"] = {"want": len(want_lbl), "set": got}
    leaf_lbl = {f"SM_DKH_DoorLeaf_Parked__{n:04d}" for n, i in enumerate(L["instances"])
                if i["piece"] == "SM_DKH_DoorLeaf_Parked" and not i.get("removed")}
    if not getattr(LOOK, "PARKED_LEAF_CHANNEL1", True):
        n0 = 0
        for lbl in leaf_lbl:
            a = all_by_label.get(lbl)
            smc = a.get_component_by_class(unreal.StaticMeshComponent) if a else None
            if smc is not None and ensure_channels(smc, channels(True, False)):
                n0 += 1
        REP["parked_leaves_channel0_only"] = {"want": len(leaf_lbl), "set": n0}
    # fix round (rev 2, judge delta 5): the parked leaves' shoji paper: a DojoLab child MI on those six actors only
    REP["parked_leaf_paper"] = None
    src_path = f"{L['materials']['M_DJ_ShojiPaper']['ue_dir']}/M_DJ_ShojiPaper"
    if getattr(LOOK, "PARKED_LEAF_PAPER", None):
        lp_path = f"{DJA_DIR}/MI_DJA_ParkedLeafPaper"
        lp = child_mi(lp_path, unreal.load_asset(src_path), LOOK.PARKED_LEAF_PAPER)
        nl = 0
        for lbl in leaf_lbl:
            a = all_by_label.get(lbl)
            if a is not None:
                ensure_material(a.get_component_by_class(unreal.StaticMeshComponent), "M_DJ_ShojiPaper", lp)
                nl += 1
        REP["parked_leaf_paper"] = {"mi": lp_path, "parent": src_path, "values": LOOK.PARKED_LEAF_PAPER,
                                    "actors": nl, "want": len(leaf_lbl)}
    # the window backers' shoji paper (a DojoLab child MI per actor, Emissive x BACKER_EMISSIVE)
    REP["backer_paper"] = None
    if LOOK.BACKER_EMISSIVE != 1.0:
        src = unreal.load_asset(src_path)
        base = float(MEL.get_material_instance_scalar_parameter_value(src, "EmissiveIntensity"))
        bp_path = f"{DJA_DIR}/MI_DJA_BackerPaper"
        bp = child_mi(bp_path, src, {"EmissiveIntensity": base * LOOK.BACKER_EMISSIVE})
        backers = {f"SM_DKH_Rear_WindowBacker__{n:04d}" for n, i in enumerate(L["instances"])
                   if i["piece"] == "SM_DKH_Rear_WindowBacker" and not i.get("removed")}
        nb = 0
        for lbl in backers:
            a = all_by_label.get(lbl)
            if a is not None:
                ensure_material(a.get_component_by_class(unreal.StaticMeshComponent), "M_DJ_ShojiPaper", bp)
                nb += 1
        REP["backer_paper"] = {"mi": bp_path, "parent": src_path, "emissive": round(base * LOOK.BACKER_EMISSIVE, 4),
                               "actors": nb, "want": len(backers)}

    # ---------------------------------------------------------------- 6. checks
    env_bad = []
    for it in I["instances"]:
        b = it["bbox_m"]
        if not (inside(b[:3]) and inside(b[3:])):
            env_bad.append(it["id"])
    REP["envelope_violations"] = env_bad
    have = {i.get("shell_id") for i in L["instances"] if i.get("shell_id") and not i.get("removed")}
    want_ids = {i["id"] for i in H["instances_new"] if not str(i.get("status", "")).startswith("removed")}
    REP["shell_ids"] = {"want": len(want_ids), "in_layout": len(have & want_ids), "missing": sorted(want_ids - have)}
    labels = set(all_by_label)
    REP["shell_actors_in_level"] = sum(1 for n, i in enumerate(L["instances"])
                                       if i.get("shell_id") in want_ids and f"{i['piece']}__{n:04d}" in labels)
    retired = {r if isinstance(r, str) else r.get("name") for r in M.get("retired", [])}
    REP["pieces_missing"] = sorted(p for p in I["pieces"] if p not in meshes and p not in retired)
    REP["level_dirty"] = dirty
    REP["saved"] = bool(les.save_current_level()) if dirty else "skipped (no change)"
    REP["passed"] = (REP["open_ok"] and REP["saved"] is not False and gate["passed"] and not REP["errors"]
                     and not drift and not REP["lights_gate_bad"]
                     and not env_bad and not outside and not REP["pieces_missing"]
                     and REP["shell_ids"]["in_layout"] == len(want_ids)
                     and REP["shell_actors_in_level"] == len(want_ids)
                     and n_shadow <= LOOK.SHADOW_BUDGET and len(REP["items"]) == len(I["items"])
                     and REP["copied_packages"]["byte_identical"] == REP["copied_packages"]["n"]
                     and REP["shell_faces_on_channel1"]["set"] == REP["shell_faces_on_channel1"]["want"]
                     and (REP["parked_leaf_paper"] is None
                          or REP["parked_leaf_paper"]["actors"] == REP["parked_leaf_paper"]["want"]))
    REP["synced_revision"] = M["revision"] if REP["passed"] else None
    jwrite(OUT / "sync.json", REP)
    if REP["passed"]:
        jwrite(OUT / "synced_revision.json", {"DojoLab": M["revision"], "date": time.strftime("%Y-%m-%d %H:%M")})
    unreal.log(f"DJ_STEP_DONE armory_sync passed={REP['passed']} placed={gate['n_placed']} items={len(REP['items'])} "
               f"lights={len(REP['lights'])} shadowed={n_shadow} bounds_max_cm={round(gate['max_bounds_err_cm'], 4)} "
               f"gate_fails={len(gate['failures'])} errors={len(REP['errors'])} rev={M['revision']} "
               f"level_kept={REP['level_kept']} dirty={dirty} assets_saved={len(REP['assets_saved'])}")


try:
    import unreal  # noqa: F401
    _IN_UE = True
except ImportError:
    _IN_UE = False

if _IN_UE:
    try:
        unreal_stage()
    except Exception:  # noqa: BLE001
        jwrite(OUT / "sync.json", {"passed": False, "error": traceback.format_exc()[-3000:]})
        import unreal as _u  # noqa: PLC0415
        _u.log("DJ_STEP_DONE armory_sync passed=False (exception, see sync.json)")
elif __name__ == "__main__":
    if (sys.argv[1:] or ["files"])[0] == "files":
        file_stage()
