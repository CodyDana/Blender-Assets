"""ArmoryLab: build the EXTENDED HALL SHELL around the armory interior (SYNC.md section 11). Runs INSIDE Unreal as a
pythonscript commandlet on ArmoryLab, after the armory chat's own level step (ak_level.py), every sync:

  UnrealEditor-Cmd.exe "<ArmoryLab>.uproject" -run=pythonscript -script="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shared/armory_hall/tools/ue_armorylab_shell.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput

Options (environment variables; all optional):
  AH_LEVEL            the level to edit                      (default /Game/Armory/Maps/L_Armory)
  AH_OFFSET_M         ArmoryLab world = hall-local + this    (default "6,0,0": SYNC.md section 2)
  AH_EMISSIVE         'parity' (x ArmoryLab parity scale from shell_materials.json level_values) or a number (default parity)
  AH_BACKER_CD        window-backer rect candela, 0 = off   (default 0: the windows read dark, as the armory's night stills)
  AH_INTERIOR_PAPER   1 = the parked leaves' and backers' shoji paper unlit (DojoLab's per-actor overrides; default 1)
  AH_GROUND           1 = a flat courtyard stand-in at hall-local z -0.50 (the armory's own garden ground is hidden; default 1)
  AH_REPORT           report json (default WorkFiles/armory/build/unreal/armory_hall_sync/shell.json)
  AH_TEST             1 = TEST MODE (used by the dojo chat on DojoLab to prove this script): every asset goes under
                      /Game/_AHShellTest, nothing is saved, the level is only loaded

What it does (idempotent; it touches only what it tags):
  1 textures (PNG) and SM_DKH_* meshes imported by sha256 with the recipe of shell_materials.json import_recipe
    (re-imported only when the source sha differs from its own import manifest); sockets sidecars applied
  2 the two masters rebuilt from the dojo's graph code (Scripts/dojo/unreal/dj_sc_materials.py build_lib_opaque /
    build_lib_emissive, executed without its main()); one MaterialInstanceConstant per slot with shell_materials.json's
    parameters; slots assigned by slot name
  3 the level: every actor tagged AH_Shell is destroyed and re-placed from hall_shell_layout.json (instances_existing
    'kept*' + instances_new not 'removed*'), labels '<piece>__<shell id>', folder ArmoryHall/Shell, collision per
    interface.json gameplay classes; the 10 window-backer rects (BackerLight_*); the optional ground stand-in
  4 the armory's own exterior is HIDDEN, KEPT for reference: every actor of an interior_layout.json
    not_used_in_the_hall instance (label '<piece>__<armory layout index, 3 digits>', as ak_level.py names them, or the
    same piece within 1 cm of its armory location) gets its mesh component invisible, no collision, hidden in game, the
    tag AH_ExteriorHidden and the folder ArmoryHall_Reference/... (ak_level.py re-creates them visible on its next run:
    run this script after it, every time). Sky, sun, moon, fog, exposure stay ArmoryLab's own.
  4b the HALL VARIANT of the interior: the 8 substitution floor tiles AKI_9001..9008 placed (tag AH_Shell), the entry
    lanterns / mat and their lights lifted +0.12 off the (hidden) genkan, exactly as interior_layout.json
  5 gates: every shell instance placed; actor bounds = hall_shell_layout bbox_world_m converted (1 cm) where recorded;
    every hidden exterior instance found. Report + log line 'AH_SHELL_DONE passed=...'.
"""
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[4]
SH = ROOT / "WorkFiles" / "shared" / "armory_hall"
TEST = os.environ.get("AH_TEST", "0") == "1"
LEVEL = os.environ.get("AH_LEVEL", "/Game/Armory/Maps/L_Armory")
OFF = [float(v) for v in os.environ.get("AH_OFFSET_M", "6,0,0").split(",")]
HALL_TO_DOJO = (22.0, 24.0, 0.5)
REPORT = Path(os.environ.get("AH_REPORT", str(ROOT / "WorkFiles/armory/build/unreal/armory_hall_sync/shell.json")))
IMPORT_MAN = REPORT.parent / "shell_import_manifest.json"
TAG, HIDE_TAG = "AH_Shell", "AH_ExteriorHidden"
EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AT = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
REP = {"test": TEST, "level": LEVEL, "offset_m": OFF, "errors": [], "notes": []}


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def remap(path):
    return path.replace("/Game/", "/Game/_AHShellTest/", 1) if TEST else path


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def rot(yaw=0.0, pitch=0.0):
    r = unreal.Rotator()
    r.yaw, r.pitch = float(yaw), float(pitch)
    return r


def setp(o, k, v):
    try:
        o.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"setp {type(o).__name__}.{k}: {str(exc)[:120]}")
        return False


def world_cm(hl):
    x, y, z = hl[0] + OFF[0], hl[1] + OFF[1], hl[2] + OFF[2]
    return (x * 100.0, -y * 100.0, z * 100.0)


def import_task(filename, dest, name, factory=None, options=None):
    t = unreal.AssetImportTask()
    for k, v in (("filename", str(filename)), ("destination_path", dest), ("destination_name", name),
                 ("automated", True), ("replace_existing", True), ("replace_existing_settings", True), ("save", False)):
        t.set_editor_property(k, v)
    if factory is not None:
        t.set_editor_property("factory", factory)
    if options is not None:
        t.set_editor_property("options", options)
    AT.import_asset_tasks([t])


def mesh_options(nanite):
    ui = unreal.FbxImportUI()
    for k, v in (("automated_import_should_detect_type", False), ("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH),
                 ("import_as_skeletal", False), ("import_mesh", True), ("import_materials", False),
                 ("import_textures", False), ("import_animations", False)):
        ui.set_editor_property(k, v)
    sm = ui.get_editor_property("static_mesh_import_data")
    for k, v in (("import_mesh_lods", True), ("auto_generate_collision", False), ("one_convex_hull_per_ucx", True),
                 ("combine_meshes", False), ("generate_lightmap_u_vs", False),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                 ("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE),
                 ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE),
                 ("convert_scene", True), ("convert_scene_unit", True), ("force_front_x_axis", False),
                 ("import_uniform_scale", 1.0), ("build_nanite", bool(nanite))):
        sm.set_editor_property(k, v)
    return ui


def save(asset_path):
    if TEST:
        return False
    return bool(EAL.save_asset(asset_path, only_if_is_dirty=False))


def main():
    t0 = time.time()
    SM, H, I, F = (J(SH / f) for f in ("shell_materials.json", "hall_shell_layout.json", "interior_layout.json",
                                       "interface.json"))
    M = J(SH / "manifest.json")
    REP["manifest_revision"] = M["revision"]
    man = J(IMPORT_MAN) if (IMPORT_MAN.exists() and not TEST) else {}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    # ---- 1 textures
    TS = unreal.TextureCompressionSettings
    REP["textures"] = {}
    for t, r in sorted(SM["textures"].items()):
        path = remap(r["ue_path"])
        h = sha(ROOT / r["png"])
        try:
            if man.get(path) == h and EAL.does_asset_exist(path):
                REP["textures"][t] = "skipped"
                continue
            import_task(ROOT / r["png"], path.rsplit("/", 1)[0], t)
            tex = unreal.load_asset(path)
            tex.set_editor_property("srgb", bool(r["srgb"]))
            tex.set_editor_property("compression_settings", getattr(TS, r["compression"]))
            if "flip_green_channel" in r:
                tex.set_editor_property("flip_green_channel", bool(r["flip_green_channel"]))
            ok = save(path)
            if ok:
                man[path] = h
            REP["textures"][t] = "imported" + ("+saved" if ok else "")
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"texture {t}: {traceback.format_exc()[-600:]}")
    # ---- 2 masters (the dojo's graph code) + instances
    src = (ROOT / "Scripts/dojo/unreal/dj_sc_materials.py").read_text(encoding="utf-8")
    assert src.rstrip().endswith("main()"), "dj_sc_materials.py layout changed: update this tool"
    sys.path.insert(0, str(ROOT / "Scripts/dojo/unreal"))
    NS = {"__name__": "ah_dj_sc_materials", "__file__": str(ROOT / "Scripts/dojo/unreal/dj_sc_materials.py")}
    exec(compile(src.rstrip()[:-len("main()")], NS["__file__"], "exec"), NS)
    if TEST:   # the masters' default texture samplers resolve through the layout's paths: point them at the test copies
        S = NS["S"]
        _tp = S.tex_path
        NS["S"].tex_path = lambda layout, name: remap(_tp(layout, name))
    masters = {}
    REP["masters"] = {}
    for m, r in SM["masters"].items():
        path = remap(r["ue_path"])
        try:
            mat, created = NS["get_or_create"](path, unreal.Material, unreal.MaterialFactoryNew())
            NS["MASTERS"][m](mat)
            MEL.layout_material_expressions(mat)
            MEL.recompile_material(mat)
            masters[r["ue_path"]] = mat
            REP["masters"][m] = {"created": created, "expressions": int(MEL.get_num_material_expressions(mat)),
                                 "saved": save(path)}
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"master {m}: {traceback.format_exc()[-800:]}")
    emis = os.environ.get("AH_EMISSIVE", "parity")
    lv = SM["level_values"]["EmissiveIntensity"]
    k_em = (float(lv["ArmoryLab_parity_scale"]) if emis == "parity" else float(emis)) if not TEST else 1.0
    REP["emissive_scale_vs_dojolab"] = k_em
    mis, REP["instances"] = {}, {}
    for name, r in sorted(SM["materials"].items()):
        path = remap(r["ue_path"])
        try:
            mi, created = NS["get_or_create"](path, unreal.MaterialInstanceConstant,
                                              unreal.MaterialInstanceConstantFactoryNew())
            MEL.clear_all_material_instance_parameters(mi)
            MEL.set_material_instance_parent(mi, masters[r["parent"]])
            for k, v in r["scalars"].items():
                v = float(v) * (k_em if k in ("EmissiveIntensity", "Emissive Intensity") else 1.0)
                MEL.set_material_instance_scalar_parameter_value(mi, k, v)
            for k, v in r["static_switches"].items():
                MEL.set_material_instance_static_switch_parameter_value(mi, k, bool(v))
            for k, v in r["vectors_linear_rgba"].items():
                MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
            for k, v in r["textures"].items():
                MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset(remap(SM["textures"][v]["ue_path"])))
            MEL.update_material_instance(mi)
            mis[name] = mi
            REP["instances"][name] = {"created": created, "readback": {
                k: round(float(MEL.get_material_instance_scalar_parameter_value(mi, k)), 4) for k in r["scalars"]},
                "saved": save(path)}
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"instance {name}: {traceback.format_exc()[-800:]}")
    # ---- 1b meshes
    try:
        SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        SMS = None
    SMS = SMS or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline.ue_import_sockets import apply_sidecar  # noqa: PLC0415
    meshes, REP["meshes"] = {}, {}
    for p, r in sorted(SM["pieces"].items()):
        path = remap(r["ue_mesh"])
        e = {}
        try:
            h = sha(ROOT / r["fbx"]) + f"|nanite={int(r['nanite'])}"
            if not (man.get(path) == h and EAL.does_asset_exist(path)):
                if EAL.does_asset_exist(path):
                    EAL.delete_asset(path)
                import_task(ROOT / r["fbx"], path.rsplit("/", 1)[0], p, unreal.FbxFactory(), mesh_options(r["nanite"]))
                e["imported"] = True
                if r.get("sidecar"):
                    apply_sidecar(str(ROOT / r["sidecar"]), path, save=False)
            mesh = unreal.load_asset(path)
            for i, sm in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(sm.get_editor_property("material_slot_name"))
                if slot in mis:
                    mesh.set_material(i, mis[slot])
                else:
                    REP["errors"].append(f"mesh {p}: slot {slot} has no instance")
            if r["nanite"]:
                ns = mesh.get_editor_property("nanite_settings")
                ns.set_editor_property("enabled", True)
                ns.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.RELATIVE_ERROR)
                ns.set_editor_property("fallback_relative_error", 0.0)
                ns.set_editor_property("fallback_percent_triangles", 1.0)
                SMS.set_nanite_settings(mesh, ns, True)
            e["convex"] = len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
                              .get_editor_property("convex_elems"))
            e["ucx_expected"] = r.get("ucx")
            e["saved"] = save(path)
            if e["saved"]:
                man[path] = h
            meshes[p] = mesh
        except Exception:  # noqa: BLE001
            REP["errors"].append(f"mesh {p}: {traceback.format_exc()[-800:]}")
        REP["meshes"][p] = e
    if not TEST:
        IMPORT_MAN.parent.mkdir(parents=True, exist_ok=True)
        IMPORT_MAN.write_text(json.dumps(man, indent=1), encoding="utf-8")
    # ---- 3 level
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["open_ok"] = bool(les.load_level(LEVEL))
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    REP["removed"] = removed
    classes = F["gameplay"]["collision_classes"]
    RESP = {"block": unreal.CollisionResponseType.ECR_BLOCK, "ignore": unreal.CollisionResponseType.ECR_IGNORE}
    CH = unreal.CollisionChannel

    def collide(comp, cls):
        c = classes.get(cls, classes.get("building"))
        if c.get("no_collision"):
            comp.set_collision_profile_name("NoCollision")
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            return
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_collision_response_to_channel(CH.ECC_PAWN, RESP[c["pawn"]])
        comp.set_collision_response_to_channel(CH.ECC_CAMERA, RESP[c["camera"]])
        comp.set_collision_response_to_channel(CH.ECC_VISIBILITY, RESP[c["visibility"]])

    paper = None
    if os.environ.get("AH_INTERIOR_PAPER", "1") == "1" and "M_DJ_ShojiPaper" in mis:
        pp = remap("/Game/ArmoryHall/Materials/MI_AH_InteriorPaper")
        paper, _c = NS["get_or_create"](pp, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(paper, mis["M_DJ_ShojiPaper"])
        MEL.set_material_instance_scalar_parameter_value(paper, "EmissiveIntensity", 0.0)
        MEL.set_material_instance_scalar_parameter_value(paper, "BaseMult", 1.0)
        MEL.update_material_instance(paper)
        save(pp)
    placed, gate = 0, {"max_bounds_err_cm": 0.0, "fails": []}
    for i in [x for x in H["instances_existing"] if str(x["status"]).startswith("kept")] + \
             [x for x in H["instances_new"] if not str(x.get("status", "")).startswith("removed")]:
        mesh = meshes.get(i["piece"])
        if mesh is None:
            REP["errors"].append(f"no mesh for {i['id']}")
            continue
        hl = [i["loc_world_m"][k] - HALL_TO_DOJO[k] for k in range(3)]
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(world_cm(hl)), rot(yaw=-float(i["rot_z_deg"])))
        smc = a.static_mesh_component
        smc.set_static_mesh(mesh)
        smc.set_mobility(unreal.ComponentMobility.STATIC)
        collide(smc, i.get("collision_class", "building"))
        if paper is not None and i["piece"] in ("SM_DKH_DoorLeaf_Parked", "SM_DKH_Rear_WindowBacker"):
            for k, sm in enumerate(mesh.get_editor_property("static_materials")):
                if str(sm.get_editor_property("material_slot_name")) == "M_DJ_ShojiPaper":
                    smc.set_material(k, paper)
        a.set_actor_label(f"{i['piece']}__{i['id']}")
        a.set_folder_path("ArmoryHall/Shell")
        a.tags = [unreal.Name(TAG), unreal.Name("AH_" + i["id"])]
        placed += 1
        if i.get("bbox_world_m"):
            b = i["bbox_world_m"]
            lo = world_cm([b[0] - HALL_TO_DOJO[0], b[4] - HALL_TO_DOJO[1], b[2] - HALL_TO_DOJO[2]])
            hi = world_cm([b[3] - HALL_TO_DOJO[0], b[1] - HALL_TO_DOJO[1], b[5] - HALL_TO_DOJO[2]])
            o, ex = a.get_actor_bounds(False)
            got = [o.x - ex.x, o.y - ex.y, o.z - ex.z, o.x + ex.x, o.y + ex.y, o.z + ex.z]
            err = max(abs(p - q) for p, q in zip(got, list(lo) + list(hi)))
            gate["max_bounds_err_cm"] = max(gate["max_bounds_err_cm"], err)
            if err > 1.0:
                gate["fails"].append({"id": i["id"], "piece": i["piece"], "err_cm": round(err, 3)})
    REP["shell_placed"] = placed
    REP["bounds_gate"] = gate
    # backer rects (shell lights, per-level intensity)
    cd = float(os.environ.get("AH_BACKER_CD", "0"))
    for L in H["lights"]:
        yaw = 0.0 if L["faces"] == "+x" else 180.0
        a = EAS.spawn_actor_from_class(unreal.RectLight, V(world_cm(L["loc_m"])), rot(yaw=yaw))
        c = a.get_editor_property("rect_light_component")
        setp(c, "mobility", unreal.ComponentMobility.MOVABLE)
        setp(c, "intensity_units", unreal.LightUnits.CANDELAS)
        setp(c, "intensity", cd)
        setp(c, "source_height", L["size_m"][0] * 100.0)
        setp(c, "source_width", L["size_m"][1] * 100.0)
        setp(c, "cast_shadows", False)
        if cd <= 0:
            setp(c, "visible", False)
        a.set_actor_label(L["name"])
        a.set_folder_path("ArmoryHall/Shell/Lights")
        a.tags = [unreal.Name(TAG)]
    if os.environ.get("AH_GROUND", "1") == "1":
        plane = unreal.load_asset("/Engine/BasicShapes/Plane")
        g = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(world_cm([0.0, -6.0, -0.5])), rot())
        g.static_mesh_component.set_static_mesh(plane)
        g.set_actor_scale3d(V((60.0, 40.0, 1.0)))     # the 1 m engine plane: 60 x 40 m round the hall front
        if "M_DJ_Granite" in mis:
            g.static_mesh_component.set_material(0, mis["M_DJ_Granite"])
        g.set_actor_label("AH_CourtyardGround_StandIn")
        g.set_folder_path("ArmoryHall/Shell")
        g.tags = [unreal.Name(TAG)]
    # ---- 4 hide the armory's own exterior (kept for reference)
    want = I["not_used_in_the_hall"]["instances"]
    by_label, by_mesh = {}, {}
    for b in EAS.get_all_level_actors():
        by_label[b.get_actor_label()] = b
        if isinstance(b, unreal.StaticMeshActor):
            m = b.static_mesh_component.static_mesh
            if m is not None and m.get_name().startswith("SM_AK"):
                l = b.get_actor_location()
                by_mesh.setdefault(m.get_name(), []).append((b, (l.x, l.y, l.z)))
    found, missing = 0, []
    for r in want:
        a = by_label.get(f"{r['piece']}__{r['armory_layout_index']:03d}")
        if a is None:
            loc = world_cm([r["armory_loc"][0] - 6.0, r["armory_loc"][1], r["armory_loc"][2]])
            for b, l in by_mesh.get(r["piece"], []):
                if max(abs(l[0] - loc[0]), abs(l[1] - loc[1]), abs(l[2] - loc[2])) < 1.0:
                    a = b
                    break
        if a is None:
            missing.append(f"{r['piece']}#{r['armory_layout_index']}")
            continue
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            c.set_visibility(False, True)
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        a.set_actor_hidden_in_game(True)
        a.set_folder_path("ArmoryHall_Reference/ArmoryExterior")
        if unreal.Name(HIDE_TAG) not in list(a.tags):
            a.tags = list(a.tags) + [unreal.Name(HIDE_TAG)]
        found += 1
    REP["exterior_hidden"] = {"want": len(want), "found": found, "missing": missing[:50]}
    # ---- 4b the HALL VARIANT of the interior (interior_layout.json): the eight floor tiles that fill the genkan + entry
    # band (AKI_9001..9008, no armory layout index) are placed; the pieces and lights lifted off the genkan (z_shift_m)
    # are raised on ArmoryLab's own actors (ak_level.py resets them: this runs after it, every time)
    subs, lifted, lifted_missing = 0, 0, []
    for it in I["instances"]:
        src = it.get("src_armory", {})
        if src.get("layout_index") is None:
            mesh = unreal.load_asset(I["pieces"][it["piece"]]["ue_mesh"])   # the armory's own mesh (ArmoryLab / DojoLab)
            if mesh is None:
                REP["errors"].append(f"substitution {it['id']}: no mesh {it['piece']}")
                continue
            a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(world_cm(it["loc_m"])), rot(yaw=-float(it["rot_z_deg"])))
            a.static_mesh_component.set_static_mesh(mesh)
            a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
            collide(a.static_mesh_component, it["collision_class"])
            a.set_actor_label(f"{it['piece']}__{it['id']}")
            a.set_folder_path("ArmoryHall/InteriorHallVariant")
            a.tags = [unreal.Name(TAG), unreal.Name("AH_" + it["id"])]
            subs += 1
        elif it.get("z_shift_m"):
            a = by_label.get(f"{it['piece']}__{src['layout_index']:03d}")
            if a is None:
                lifted_missing.append(it["id"])
                continue
            want_z = world_cm(it["loc_m"])[2]
            l = a.get_actor_location()
            if abs(l.z - want_z) > 0.01:
                a.set_actor_location(V((l.x, l.y, want_z)), False, False)
            lifted += 1
    D = J(SH / "lights_design.json")
    for L in D["lights"]:
        if not L.get("z_shift_m"):
            continue
        a = by_label.get(L["name"])
        if a is None:
            lifted_missing.append(L["name"])
            continue
        want_z = world_cm(L["loc_m"])[2]
        l = a.get_actor_location()
        if abs(l.z - want_z) > 0.01:
            a.set_actor_location(V((l.x, l.y, want_z)), False, False)
        lifted += 1
    REP["hall_variant"] = {"substitution_tiles": subs, "lifted": lifted, "lifted_missing": lifted_missing}
    want_n = len([x for x in H["instances_existing"] if str(x["status"]).startswith("kept")]) + \
        len([x for x in H["instances_new"] if not str(x.get("status", "")).startswith("removed")])
    n_subs = sum(1 for it in I["instances"] if it.get("src_armory", {}).get("layout_index") is None)
    REP["passed"] = (REP["open_ok"] and placed == want_n and not gate["fails"] and not REP["errors"]
                     and subs == n_subs and (TEST or (found == len(want) and not lifted_missing)))
    if not TEST and REP["passed"]:
        REP["level_saved"] = bool(les.save_current_level())
        REP["passed"] = REP["level_saved"]
        if REP["passed"]:   # the last step of the ArmoryLab sync: record the synced revision (check_sync reads it)
            (REPORT.parent / "synced_revision.json").write_text(json.dumps(
                {"ArmoryLab": M["revision"], "date": time.strftime("%Y-%m-%d %H:%M"),
                 "by": "tools/ue_armorylab_shell.py"}, indent=1), encoding="utf-8")
    REP["sec"] = round(time.time() - t0, 1)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"AH_SHELL_DONE passed={REP['passed']} test={TEST} placed={placed}/{want_n} "
               f"bounds_max_cm={round(gate['max_bounds_err_cm'], 4)} hidden={found}/{len(want)} errors={len(REP['errors'])}")


try:
    main()
except Exception:  # noqa: BLE001
    REP["errors"].append(traceback.format_exc()[-3000:])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log("AH_SHELL_DONE passed=False (exception)")
