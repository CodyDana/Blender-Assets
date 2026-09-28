"""PASS 1 (commandlet, -nullrhi): import SK_Fan (+ LOD1/LOD2 through import_lod), its three animations at their own
rates, SK_Fan_Tassel; apply the sidecar: LOD screen sizes, mesh sockets on bones, the physics asset (the build's
bodies, nothing auto-generated kept); make plain check materials from the exported BC/ORM maps (the pack masters
lack 'Used with Skeletal Mesh' and are frozen: see FAN_REPORT); save once.  Results -> pass1.json."""
import json
import math
import sys
import traceback

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck")
import unreal  # noqa: E402

from fan_ue_common import (DEST, EXPORTS, MESH, PHYS, REPORT, SIDECAR, TASSEL, TPHYS, TSIDECAR,  # noqa: E402
                           component_space_ref, find_bodies, safe, sha256, tf, write)

AT = unreal.AssetToolsHelpers.get_asset_tools()
ACS = SIDECAR["import"].get("bone_compression", "/Engine/Animation/DefaultRecorderBoneCompression")   # round 3: from the sidecar
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
res = {"dest": DEST, "steps": {}}


def fbx_task(path, name, ui):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("options", ui)
    AT.import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def mesh_ui(skeleton=None, physics=False):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", True)
    if skeleton is not None:
        ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("create_physics_asset", physics)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    d = ui.get_editor_property("skeletal_mesh_import_data")
    for k, v in (("import_morph_targets", False), ("convert_scene", True), ("force_front_x_axis", False),
                 ("convert_scene_unit", True), ("use_t0_as_ref_pose", False), ("update_skeleton_reference_pose", False),
                 ("import_mesh_lods", False),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)):
        safe(lambda: d.set_editor_property(k, v))
    return ui


def anim_ui(skeleton, fps):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", False)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    d = ui.get_editor_property("anim_sequence_import_data")
    for k, v in (("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME),
                 ("use_default_sample_rate", False), ("custom_sample_rate", int(fps)), ("convert_scene", True),
                 ("force_front_x_axis", False), ("convert_scene_unit", True), ("import_meshes_in_bone_hierarchy", False),
                 ("remove_redundant_keys", False)):
        safe(lambda: d.set_editor_property(k, v))
    return ui


def texture(path, name, srgb, compression=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", DEST + "/Textures")
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    AT.import_asset_tasks([task])
    t = unreal.load_asset(f"{DEST}/Textures/{name}")
    t.set_editor_property("srgb", srgb)
    if compression is not None:
        t.set_editor_property("compression_settings", compression)
    return t


def check_material(name, bc, orm, metal):
    """A plain lit material from the exported BC (and ORM roughness) - Used with Skeletal Mesh set on THIS material."""
    mel = unreal.MaterialEditingLibrary
    path = f"{DEST}/Materials/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    m = AT.create_asset(name, DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)
    tb = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -400, 0)
    tb.set_editor_property("texture", bc)
    mel.connect_material_property(tb, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    to = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -400, 300)
    to.set_editor_property("texture", orm)
    to.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mel.connect_material_property(to, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    if metal:
        mel.connect_material_property(to, "B", unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m)
    return m


def build_physics(mesh, skel, proxy_fbx, bodies, phys_path):
    """The physics asset from the build's proxy (one body per body bone, see build_fan.export_physics_proxy),
    each body rewritten from the sidecar's elements, renamed to phys_path and assigned to the real mesh."""
    out = {"proxy": proxy_fbx}
    pname = mesh.get_name() + "_PhysicsProxy"
    fbx_task(proxy_fbx, pname, mesh_ui(skeleton=skel, physics=True))
    pmesh = unreal.load_asset(f"{DEST}/{pname}")
    pa = pmesh.get_editor_property("physics_asset")
    out["built"] = pa.get_path_name()
    setups = find_bodies(pa)
    out["auto_bodies"] = sorted(setups)
    ref, parent, _ = component_space_ref(mesh)
    applied = {}
    for body in bodies:
        names = body.get("unreal_bone_any_of") or [body["bone"]]
        bone = next((n for n in names if n in setups), None)
        if bone is None:
            applied[body["bone"]] = {"error": "no body on " + "/".join(names)}
            continue
        bs = setups[bone]
        g = unreal.KAggregateGeom()
        boxes, sphyls, spheres, flags = [], [], [], []
        for e in body["elements"]:
            uc = e["unreal_component"]
            rel = unreal.MathLibrary.make_relative_transform(tf(uc["location_cm"], uc["quaternion_xyzw"]), ref[bone])
            if e["shape"] == "box":
                el = unreal.KBoxElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("rotation", rel.rotation.rotator())
                sx, sy, sz = e["size_cm"]
                el.set_editor_property("x", float(sx))
                el.set_editor_property("y", float(sy))
                el.set_editor_property("z", float(sz))
                boxes.append(el)
            elif e["shape"] == "capsule":
                el = unreal.KSphylElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("rotation", rel.rotation.rotator())
                el.set_editor_property("radius", float(e["radius_mm"]) * 0.1)
                el.set_editor_property("length", float(e["length_mm"]) * 0.1)
                sphyls.append(el)
            else:
                el = unreal.KSphereElem()
                el.set_editor_property("center", rel.translation)
                el.set_editor_property("radius", float(e["radius_mm"]) * 0.1)
                spheres.append(el)
            flags.append({
                "collision": safe(lambda: (el.set_editor_property(
                    "collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS if e["collision"]
                    else unreal.CollisionEnabled.NO_COLLISION), True)[1]),
                "mass": safe(lambda: (el.set_editor_property("contribute_to_mass", bool(e["contribute_to_mass"])), True)[1])})
        g.set_editor_property("box_elems", boxes)
        g.set_editor_property("sphyl_elems", sphyls)
        g.set_editor_property("sphere_elems", spheres)
        g.set_editor_property("convex_elems", [])
        bs.set_editor_property("agg_geom", g)
        bs.set_editor_property("physics_type", unreal.PhysicsType.PHYS_TYPE_KINEMATIC if body["physics_type"] == "Kinematic"
                               else unreal.PhysicsType.PHYS_TYPE_DEFAULT)
        bs.set_editor_property("consider_for_bounds", bool(body["consider_for_bounds"]))

        def inst():
            bi = bs.get_editor_property("default_instance")
            any_coll = any(e["collision"] for e in body["elements"])
            bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS if any_coll
                                   else unreal.CollisionEnabled.NO_COLLISION)
            bi.set_editor_property("override_mass", True)
            bi.set_editor_property("mass_in_kg_override", float(body["mass_kg"]))
            bs.set_editor_property("default_instance", bi)
            return True
        applied[body["bone"]] = {"unreal_bone": bone, "elements": flags, "instance": safe(inst)}
    out["applied"] = applied
    out["unused_auto_bodies"] = sorted(set(setups) - {a.get("unreal_bone") for a in applied.values()})
    safe(lambda: pa.set_editor_property("preview_skeletal_mesh", mesh))
    pmesh.set_editor_property("physics_asset", None)
    unreal.EditorAssetLibrary.delete_loaded_asset(pmesh)
    old = pa.get_path_name().split(".")[0]
    out["renamed"] = bool(unreal.EditorAssetLibrary.rename_asset(old, phys_path))
    pa = unreal.load_asset(phys_path)
    mesh.set_editor_property("physics_asset", pa)
    out["asset"] = pa.get_path_name()
    return out


try:
    # ------------------------------------------------------------------ SK_Fan
    paths = fbx_task(EXPORTS / "SK_Fan.fbx", "SK_Fan", mesh_ui())
    res["steps"]["mesh_import"] = paths
    mesh = unreal.load_asset(MESH)
    skel = mesh.get_editor_property("skeleton")
    res["skeleton"] = skel.get_path_name()
    # LODs
    lods = []
    for i, f in enumerate(SIDECAR["lod_files"][1:], 1):
        lods.append({"lod": i, "file": f, "result": safe(lambda: SUB.import_lod(mesh, i, str(EXPORTS / f)))})
    res["steps"]["lods"] = lods
    res["lod_count"] = SUB.get_lod_count(mesh)

    def set_sizes():
        """LODInfo is not exposed to Python: a SkeletalMeshLODSettings asset carrying the screen sizes (and no
        reduction), assigned to the mesh, which copies them onto its LODs."""
        verts_before = [SUB.get_num_verts(mesh, i) for i in range(SUB.get_lod_count(mesh))]
        ls = AT.create_asset("LODS_Fan", DEST, unreal.SkeletalMeshLODSettings, None)
        groups = []
        for i, v in enumerate(SIDECAR["lod_screen_sizes"]):
            gset = unreal.SkeletalMeshLODGroupSettings()
            pp = unreal.PerPlatformFloat()
            pp.set_editor_property("default", float(v))
            gset.set_editor_property("screen_size", pp)
            groups.append(gset)
        ls.set_editor_property("lod_groups", groups)
        mesh.set_editor_property("lod_settings", ls)
        verts_after = [SUB.get_num_verts(mesh, i) for i in range(SUB.get_lod_count(mesh))]
        return {"asset": ls.get_path_name(), "sizes": SIDECAR["lod_screen_sizes"], "verts_before": verts_before,
                "verts_after": verts_after}
    res["steps"]["screen_sizes"] = safe(set_sizes)

    def set_bounds_ext():
        be = SIDECAR["import"]["bounds_extension_cm"]
        mesh.set_editor_property("positive_bounds_extension", unreal.Vector(*[float(v) for v in be["positive_cm"]]))
        mesh.set_editor_property("negative_bounds_extension", unreal.Vector(*[float(v) for v in be["negative_cm"]]))
        return {"positive": be["positive_cm"], "negative": be["negative_cm"]}
    res["steps"]["bounds_extension"] = safe(set_bounds_ext)
    # animations, each at its own rate
    anims = {}
    for a in SIDECAR["animations"]:
        name = a["file"][:-4]
        p = fbx_task(EXPORTS / a["file"], name, anim_ui(skel, a["fps"]))
        seq = unreal.load_asset(f"{DEST}/{name}")
        # the project default (ACL, 0.01 cm at a 3 cm virtual vertex) moves the 19 cm leaf up to ~0.6 mm and
        # opens cracks between face bones: the fan's clips keep full precision (Bitwise, float keys)
        acs = unreal.load_asset(ACS)
        unreal.AnimationLibrary.set_bone_compression_settings(seq, acs)
        if "loop" in a:                                      # round 3: the sidecar's intended playback
            seq.set_editor_property("loop", bool(a["loop"]))
        anims[name] = {"paths": p, "fps": a["fps"], "frames": a["frames"], "loop": bool(seq.get_editor_property("loop")),
                       "bone_compression": unreal.AnimationLibrary.get_bone_compression_settings(seq).get_path_name()}
    res["steps"]["animations"] = anims
    # sockets: sidecar component transforms -> relative to the bone's reference pose
    ref, parent, _ = component_space_ref(mesh)
    socks = []
    for s in SIDECAR["sockets"]:
        uc = s["unreal_component"]
        comp_t = tf(uc["location_cm"], uc["quaternion_xyzw"])
        rel = unreal.MathLibrary.make_relative_transform(comp_t, ref[s["bone"]])
        # SocketName and BoneName are read-only to Python: parent it with set_socket_parent, add it (it arrives
        # named None) and rename it through the subsystem
        sock = unreal.new_object(unreal.SkeletalMeshSocket, outer=mesh)
        try:
            sock.set_socket_parent(mesh, s["bone"])
        except TypeError:
            sock.set_socket_parent(s["bone"], mesh)
        sock.set_editor_property("relative_location", rel.translation)
        sock.set_editor_property("relative_rotation", rel.rotation.rotator())
        sock.set_editor_property("relative_scale", unreal.Vector(1.0, 1.0, 1.0))
        mesh.add_socket(sock, False)
        SUB.rename_socket(mesh, sock.get_editor_property("socket_name"), s["name"])
        socks.append({"name": s["name"], "bone": s["bone"], "relative_location": [rel.translation.x, rel.translation.y,
                                                                                  rel.translation.z]})
    res["steps"]["sockets"] = socks
    res["steps"]["physics"] = build_physics(mesh, skel, REPORT["physics_proxy"]["fbx"], SIDECAR["physics_bodies"], PHYS)
    # check materials from the exported maps
    tex = EXPORTS / "Textures"
    mats = {}
    for part, slot_mat in (("Leaf", "M_Fan_Leaf"), ("Sticks", "M_Fan_Sticks"), ("Rivet", "M_Fan_Rivet")):   # check mats
        bc = texture(tex / f"T_Fan_{part}_BC.png", f"T_Fan_{part}_BC", True)
        orm = texture(tex / f"T_Fan_{part}_ORM.png", f"T_Fan_{part}_ORM", False, unreal.TextureCompressionSettings.TC_MASKS)
        mats[slot_mat] = check_material(f"M_FanCheck_{part}", bc, orm, part == "Rivet")
    sm = list(mesh.get_editor_property("materials"))
    slots = []
    for s in sm:
        nm = str(s.get_editor_property("material_slot_name"))
        key = next((k for k in mats if k in nm or nm in k), None)
        if key:
            s.set_editor_property("material_interface", mats[key])
        slots.append({"slot": nm, "material": mats[key].get_path_name() if key else None})
    mesh.set_editor_property("materials", sm)
    res["steps"]["materials"] = slots
    # ------------------------------------------------------------------ SK_Fan_Tassel (+ its chain physics asset)
    tpaths = fbx_task(EXPORTS / "SK_Fan_Tassel.fbx", "SK_Fan_Tassel", mesh_ui())
    res["steps"]["tassel_import"] = tpaths
    tmesh = unreal.load_asset(TASSEL)
    res["steps"]["tassel_physics"] = build_physics(tmesh, tmesh.get_editor_property("skeleton"),
                                                   REPORT["tassel_physics_proxy"]["fbx"], TSIDECAR["physics_bodies"], TPHYS)
    tl = []
    for i, f in enumerate(TSIDECAR["lod_files"][1:], 1):
        tl.append({"lod": i, "result": safe(lambda: SUB.import_lod(tmesh, i, str(EXPORTS / f)))})
    res["steps"]["tassel_lods"] = tl
    tbc = texture(tex / "T_Fan_Tassel_BC.png", "T_Fan_Tassel_BC", True)
    torm = texture(tex / "T_Fan_Tassel_ORM.png", "T_Fan_Tassel_ORM", False, unreal.TextureCompressionSettings.TC_MASKS)
    tm = check_material("M_FanCheck_Tassel", tbc, torm, False)
    ts = list(tmesh.get_editor_property("materials"))
    for s in ts:
        s.set_editor_property("material_interface", tm)
    tmesh.set_editor_property("materials", ts)
    res["sha256"] = {f: sha256(EXPORTS / f) for f in ["SK_Fan.fbx", *SIDECAR["lod_files"][1:],
                                                     *[a["file"] for a in SIDECAR["animations"]], "SK_Fan_Tassel.fbx"]}
    saved = unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    res["saved"] = bool(saved)
    res["status"] = "ok"
except Exception:                                               # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
write("pass1.json", res)
unreal.log("FAN_PASS1_DONE status=" + res["status"])
