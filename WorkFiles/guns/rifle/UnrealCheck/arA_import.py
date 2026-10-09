"""AR-01 stage 8, pass A (a FRESH UnrealEditor-Cmd, -nullrhi): import the exact shipped bytes of Exports/Guns/AR01 into
a NEW content path (/Game/GunCheck/AR01_<run>) with the README / sidecar settings, and save. Nothing here is a gate:
pass B (a second fresh process) reads everything back.

- SK_AR01.fbx (legacy FBX importer, skeletal, Import Normals, Convert Scene ON, Force Front X OFF, T0-as-ref OFF, no
  physics asset), LOD1-3 through SkeletalMeshEditorSubsystem.import_lod, LOD screen sizes from the sidecar (through a
  SkeletalMeshLODSettings asset: SkeletalMesh.lod_info is not exposed to Python, measured on the fan);
- the five A_AR01_* clips on SK_AR01_Skeleton at the file's rate, bone compression
  /Engine/Animation/DefaultRecorderBoneCompression (sidecar import.bone_compression);
- the sidecar notifies: one Blueprint AnimNotify class per notify name (Notifies/<Name>; UAnimNotify::GetNotifyName
  returns the Blueprint's name), one track 'AR01' per clip, each event at frame / fps;
- PHYS_AR01 from Physics/SK_AR01_PhysicsProxy.fbx (Create Physics Asset ON -> one body on 'body'), the body rewritten
  from the sidecar's physics_bodies (the fan's np_skeletal method), renamed, assigned to SK_AR01, proxy deleted;
- the 17 sidecar sockets on their bones (SkeletalMeshSocket outered to the mesh);
- SM_AR01.fbx and SM_AR01_Mag.fbx (static: Import Mesh LODs ON, Convert Scene ON, Convert Scene Unit ON, Force Front X
  OFF, uniform scale 1, Import Normals + MikkTSpace, Auto Collision OFF, One Convex Hull per UCX ON, Generate Lightmap
  UVs 0 -> 1 on every LOD, Nanite OFF), each sidecar through Scripts/pipeline/ue_import_sockets.apply_sidecar;
- every shipped map with the README flags (BC sRGB TC_Default group Weapon; ORM linear TC_Masks group Weapon; N
  TC_Normalmap flip-green OFF group WeaponNormalMap; Masks linear TC_Masks group Weapon; Detail16 linear TC_Grayscale);
- plain check materials (BC/ORM/N) assigned to the CHECK copies' slots so the renders use the shipped maps.
"""
import json, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[3] / "Scripts"))
import unreal  # noqa: E402
import ar_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

DEST = C.dest()
OUT = C.HERE / "arA_import.json"
AT = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AL = unreal.AnimationLibrary
TC = unreal.TextureCompressionSettings
TMGS = unreal.TextureMipGenSettings
TG = unreal.TextureGroup
SC = C.sidecar_sk()
safe = C.safe
res = {"dest": DEST, "t0": time.time(), "engine": unreal.SystemLibrary.get_engine_version(),
       "hashes_before": C.all_hashes(), "steps": {}}


def dump():
    res["seconds"] = round(time.time() - res["t0"], 1)
    C.write(OUT, res)


def imp(path, folder, name, options=None):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(path))
    t.set_editor_property("destination_path", folder)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("save", False)
    t.set_editor_property("replace_existing", True)
    if options is not None:
        t.set_editor_property("options", options)
    AT.import_asset_tasks([t])
    return [str(p) for p in t.get_editor_property("imported_object_paths")]


def sk_ui(skeleton=None, physics=False):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", physics)
    if skeleton is not None:
        ui.set_editor_property("skeleton", skeleton)
    d = ui.get_editor_property("skeletal_mesh_import_data")
    imp_ = SC["import"]
    d.set_editor_property("import_morph_targets", bool(imp_["import_morph_targets"]))
    d.set_editor_property("convert_scene", bool(imp_["convert_scene"]))
    d.set_editor_property("force_front_x_axis", bool(imp_["force_front_x_axis"]))
    d.set_editor_property("use_t0_as_ref_pose", bool(imp_["use_t0_as_ref_pose"]))
    d.set_editor_property("update_skeleton_reference_pose", bool(imp_["update_skeleton_reference_pose"]))
    d.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    safe(lambda: d.set_editor_property("convert_scene_unit", True))
    return ui


def anim_ui(skeleton):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", False)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("skeleton", skeleton)
    d = ui.get_editor_property("anim_sequence_import_data")
    d.set_editor_property("convert_scene", True)
    d.set_editor_property("force_front_x_axis", False)
    safe(lambda: d.set_editor_property("use_default_sample_rate", False))
    safe(lambda: d.set_editor_property("custom_sample_rate", 0))  # 0 = the file's own rate
    res.setdefault("anim_import_options", {k: str(safe(lambda k=k: d.get_editor_property(k))) for k in (
        "animation_length", "use_default_sample_rate", "custom_sample_rate", "remove_redundant_keys",
        "import_bone_tracks", "convert_scene", "snap_to_closest_frame_boundary", "import_meshes_in_bone_hierarchy")})
    return ui


def static_ui():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    safe(lambda: sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE))
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    safe(lambda: sm.set_editor_property("build_nanite", False))
    return ui


def comp_ref(mesh):
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skinned_asset_and_update(mesh)
    local, par = {}, {}
    for i in range(c.get_num_bones()):
        n = str(c.get_bone_name(i))
        local[n] = c.get_ref_pose_transform(i)
        p = str(c.get_parent_bone(n))
        par[n] = None if p in ("None", "") else p
    w = {}

    def r(n):
        if n not in w:
            w[n] = local[n] if par[n] is None else unreal.MathLibrary.compose_transforms(local[n], r(par[n]))
        return w[n]
    for n in local:
        r(n)
    return w


def tf(loc, q):
    t = unreal.Transform()
    t.translation = unreal.Vector(*[float(x) for x in loc])
    t.rotation = unreal.Quat(*[float(x) for x in q])
    t.scale3d = unreal.Vector(1, 1, 1)
    return t


def bodies_of(pa):
    out = {}
    for i in range(96):
        o = unreal.find_object(pa, f"SkeletalBodySetup_{i}")
        if o is not None:
            out[str(o.get_editor_property("bone_name"))] = o
    return out


def build_phys(mesh, skel):
    proxy = C.EXP / SC["physics_proxies"]["SK_AR01"]
    rec = {"proxy": str(proxy), "proxy_sha256": C.sha(proxy)}
    pname = "SK_AR01_PhysicsProxy"
    rec["import"] = imp(proxy, DEST, pname, sk_ui(skeleton=skel, physics=True))
    pm = unreal.load_asset(f"{DEST}/{pname}")
    pa = pm.get_editor_property("physics_asset")
    got = bodies_of(pa)
    rec["auto_bodies"] = sorted(got)
    ref = comp_ref(mesh)
    for b in SC["physics_bodies"]:
        bone = next((n for n in (b.get("unreal_bone_any_of") or [b["bone"]]) if n in got), None)
        if bone is None:
            rec.setdefault("missing", []).append(b["bone"])
            continue
        bs = got[bone]
        g = unreal.KAggregateGeom()
        boxes, caps, sph = [], [], []
        for e in b["elements"]:
            uc = e["unreal_component"]
            rel = unreal.MathLibrary.make_relative_transform(tf(uc["location_cm"], uc["quaternion_xyzw"]), ref[bone])
            if e["shape"] == "box":
                el = unreal.KBoxElem()
                el.set_editor_property("rotation", rel.rotation.rotator())
                for k, v in zip("xyz", e["size_cm"]):
                    el.set_editor_property(k, float(v))
                boxes.append(el)
            elif e["shape"] == "capsule":
                el = unreal.KSphylElem()
                el.set_editor_property("rotation", rel.rotation.rotator())
                el.set_editor_property("radius", e["radius_mm"] * 0.1)
                el.set_editor_property("length", e["length_mm"] * 0.1)
                caps.append(el)
            else:
                el = unreal.KSphereElem()
                el.set_editor_property("radius", e["radius_mm"] * 0.1)
                sph.append(el)
            el.set_editor_property("center", rel.translation)
            safe(lambda: el.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS
                                                if e["collision"] else unreal.CollisionEnabled.NO_COLLISION))
            safe(lambda: el.set_editor_property("contribute_to_mass", bool(e["contribute_to_mass"])))
        g.set_editor_property("box_elems", boxes)
        g.set_editor_property("sphyl_elems", caps)
        g.set_editor_property("sphere_elems", sph)
        g.set_editor_property("convex_elems", [])
        bs.set_editor_property("agg_geom", g)
        bs.set_editor_property("physics_type", unreal.PhysicsType.PHYS_TYPE_KINEMATIC if b["physics_type"] == "Kinematic"
                               else unreal.PhysicsType.PHYS_TYPE_DEFAULT)
        bs.set_editor_property("consider_for_bounds", bool(b["consider_for_bounds"]))
        bi = bs.get_editor_property("default_instance")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        bi.set_editor_property("override_mass", True)
        bi.set_editor_property("mass_in_kg_override", float(b["mass_kg"]))
        bs.set_editor_property("default_instance", bi)
        rec["elements_written"] = {"box": len(boxes), "capsule": len(caps), "sphere": len(sph)}
    safe(lambda: pa.set_editor_property("preview_skeletal_mesh", mesh))
    pm.set_editor_property("physics_asset", None)
    EAL.delete_loaded_asset(pm)
    rec["renamed"] = bool(EAL.rename_asset(pa.get_path_name().split(".")[0], f"{DEST}/{SC['physics_asset']}"))
    pa = unreal.load_asset(f"{DEST}/{SC['physics_asset']}")
    mesh.set_editor_property("physics_asset", pa)
    rec["asset"] = pa.get_path_name()
    return rec


def add_sockets(mesh):
    ref = comp_ref(mesh)
    out = []
    for s in SC["sockets"]:
        uc = s["unreal_component"]
        rel = unreal.MathLibrary.make_relative_transform(tf(uc["location_cm"], uc["quaternion_xyzw"]), ref[s["bone"]])
        so = unreal.new_object(unreal.SkeletalMeshSocket, outer=mesh)
        try:
            so.set_socket_parent(mesh, s["bone"])
        except TypeError:
            so.set_socket_parent(s["bone"], mesh)
        so.set_editor_property("relative_location", rel.translation)
        so.set_editor_property("relative_rotation", rel.rotation.rotator())
        so.set_editor_property("relative_scale", unreal.Vector(1, 1, 1))
        mesh.add_socket(so, False)
        SUB.rename_socket(mesh, so.get_editor_property("socket_name"), s["name"])
        out.append(s["name"])
    return out


def lod_sizes(mesh):
    ls = AT.create_asset("LODS_AR01_GC", DEST, unreal.SkeletalMeshLODSettings, None)
    gs = []
    for v in SC["lod_screen_sizes"]:
        g = unreal.SkeletalMeshLODGroupSettings()
        pp = unreal.PerPlatformFloat()
        pp.set_editor_property("default", float(v))
        g.set_editor_property("screen_size", pp)
        gs.append(g)
    ls.set_editor_property("lod_groups", gs)
    v0 = [SUB.get_num_verts(mesh, i) for i in range(SUB.get_lod_count(mesh))]
    mesh.set_editor_property("lod_settings", ls)
    v1 = [SUB.get_num_verts(mesh, i) for i in range(SUB.get_lod_count(mesh))]
    return {"route": "lod_settings", "asset": ls.get_path_name(), "verts_before": v0, "verts_after": v1}


def notify_classes():
    names = sorted({n["name"] for n in SC["notifies"]})
    out = {}
    for n in names:
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.AnimNotify)
        bp = AT.create_asset(n, DEST + "/Notifies", unreal.Blueprint, f)
        safe(lambda: unreal.BlueprintEditorLibrary.compile_blueprint(bp))
        out[n] = EAL.load_blueprint_class(f"{DEST}/Notifies/{n}")
    return out


def smsub():
    s = None
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        s = None
    return s if s is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


def import_static(name):
    fbx = C.EXP / f"{name}.fbx"
    r = {"fbx": str(fbx), "sha256_before": C.sha(fbx)}
    r["imported"] = imp(fbx, DEST, name, static_ui())
    mesh = unreal.load_asset(f"{DEST}/{name}")
    r["is_static_mesh"] = isinstance(mesh, unreal.StaticMesh)
    s = smsub()
    r["in_process_lods"] = mesh.get_num_lods()
    for i in range(mesh.get_num_lods()):
        bs = s.get_lod_build_settings(mesh, i)
        bs.set_editor_property("generate_lightmap_u_vs", True)
        bs.set_editor_property("src_lightmap_index", 0)
        bs.set_editor_property("dst_lightmap_index", 1)
        s.set_lod_build_settings(mesh, i, bs)
    mesh.set_editor_property("light_map_coordinate_index", 1)
    r["sidecar"] = safe(lambda: apply_sidecar(str(C.EXP / f"{name}.sockets.json"), f"{DEST}/{name}"))
    r["sha256_after"] = C.sha(fbx)
    return r


INTENT = {
    "BC": {"srgb": True, "compression_settings": TC.TC_DEFAULT, "lod_group": TG.TEXTUREGROUP_WEAPON},
    "ORM": {"srgb": False, "compression_settings": TC.TC_MASKS, "lod_group": TG.TEXTUREGROUP_WEAPON},
    "N": {"srgb": False, "compression_settings": TC.TC_NORMALMAP, "flip_green_channel": False,
          "lod_group": TG.TEXTUREGROUP_WEAPON_NORMAL_MAP},
    "Masks": {"srgb": False, "compression_settings": TC.TC_MASKS, "lod_group": TG.TEXTUREGROUP_WEAPON},
    "Detail16": {"srgb": False, "compression_settings": TC.TC_GRAYSCALE, "lod_group": TG.TEXTUREGROUP_WEAPON},
}


def kind_of(stem):
    return "Detail16" if stem.endswith("Detail16") else stem.rsplit("_", 1)[-1]


def import_textures():
    out, T = {}, {}
    pngs = sorted(list((C.EXP / "Textures").glob("*.png")) + list((C.EXP / "Textures" / "Recolour").glob("*.png")))
    for p in pngs:
        k = kind_of(p.stem)
        rec = {"kind": k, "sha256": C.sha(p), "paths": imp(p, DEST + "/Textures", p.stem)}
        t = unreal.load_asset(f"{DEST}/Textures/{p.stem}")
        if t is not None:
            for prop, v in INTENT[k].items():
                t.set_editor_property(prop, v)
            t.set_editor_property("mip_gen_settings", TMGS.TMGS_FROM_TEXTURE_GROUP)
            rec["size"] = [t.blueprint_get_size_x(), t.blueprint_get_size_y()]
            T[p.stem] = t
        out[p.stem] = rec
    return out, T


def make_material(name, T, s):
    m = AT.create_asset(name, DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)

    def sample(tex, stype, y):
        e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, -400, y)
        e.set_editor_property("texture", tex)
        e.set_editor_property("sampler_type", stype)
        return e
    bc = sample(T[f"T_AR01_{s}_BC"], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -200)
    orm = sample(T[f"T_AR01_{s}_ORM"], unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 100)
    n = sample(T[f"T_AR01_{s}_N"], unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 400)
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m)
    return m


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    res["existed_before"] = bool(EAL.does_directory_exist(DEST))
    if res["existed_before"]:
        raise RuntimeError(f"{DEST} already exists: pick a new run name in content_path.txt")
    # ------------------------------------------------------------------ skeletal mesh + LODs
    res["steps"]["sk"] = imp(C.EXP / "SK_AR01.fbx", DEST, "SK_AR01", sk_ui())
    mesh = unreal.load_asset(f"{DEST}/SK_AR01")
    skel = mesh.get_editor_property("skeleton")
    res["skeleton_asset"] = skel.get_path_name()
    res["steps"]["lods"] = [safe(lambda i=i: SUB.import_lod(mesh, i, str(C.EXP / f"SK_AR01_LOD{i}.fbx"))) for i in (1, 2, 3)]
    res["lod_count_after_import"] = SUB.get_lod_count(mesh)
    res["steps"]["screen_sizes"] = safe(lambda: lod_sizes(mesh))
    pe, ne = SC["import"]["bounds_extension_cm"]["positive_cm"], SC["import"]["bounds_extension_cm"]["negative_cm"]
    mesh.set_editor_property("positive_bounds_extension", unreal.Vector(*pe))
    mesh.set_editor_property("negative_bounds_extension", unreal.Vector(*ne))
    dump()
    # ------------------------------------------------------------------ clips + notifies
    ncls = notify_classes()
    res["notify_classes"] = {k: (v.get_path_name() if v else None) for k, v in ncls.items()}
    comp = unreal.load_asset("/Engine/Animation/DefaultRecorderBoneCompression")
    anims = {}
    for a in SC["animations"]:
        nm = a["file"][:-4]
        rec = {"paths": imp(C.EXP / a["file"], DEST, nm, anim_ui(skel)), "sha256": C.sha(C.EXP / a["file"])}
        seq = unreal.load_asset(f"{DEST}/{nm}")
        rec["default_compression"] = safe(lambda: AL.get_bone_compression_settings(seq).get_path_name())
        AL.set_bone_compression_settings(seq, comp)
        rec["set_compression"] = AL.get_bone_compression_settings(seq).get_path_name()
        safe(lambda: AL.add_animation_notify_track(seq, "AR01"))
        added = []
        for n in SC["notifies"]:
            if n["clip"] != nm:
                continue
            t = n["frame"] / float(a["fps"])
            ev = safe(lambda: AL.add_animation_notify_event(seq, "AR01", t, ncls[n["name"]]))
            added.append({"name": n["name"], "frame": n["frame"], "time": t, "ok": not isinstance(ev, dict),
                          "err": ev if isinstance(ev, dict) else None})
        rec["notifies_added"] = added
        rec["in_process_events"] = safe(lambda: [str(x) for x in AL.get_animation_notify_event_names(seq)])
        anims[nm] = rec
    res["steps"]["animations"] = anims
    dump()
    # ------------------------------------------------------------------ sockets + physics
    res["steps"]["sockets"] = safe(lambda: add_sockets(mesh))
    res["steps"]["physics"] = safe(lambda: build_phys(mesh, skel))
    dump()
    # ------------------------------------------------------------------ static twin + magazine
    res["steps"]["SM_AR01"] = import_static("SM_AR01")
    res["steps"]["SM_AR01_Mag"] = import_static("SM_AR01_Mag")
    dump()
    # ------------------------------------------------------------------ textures + check materials
    res["textures"], T = import_textures()
    mats = {s: make_material(f"M_GC_AR01_{s}", T, s) for s in ("Metal", "Furniture", "Mag")}
    res["materials"] = {k: v.get_path_name() for k, v in mats.items()}

    def assign_sk():
        sm = list(mesh.get_editor_property("materials"))
        out = []
        for s in sm:
            nm = str(s.get_editor_property("material_slot_name"))
            out.append(nm)
            key = "Metal" if "Metal" in nm else ("Furniture" if "Furniture" in nm else ("Mag" if "Mag" in nm else None))
            if key:
                s.set_editor_property("material_interface", mats[key])
        mesh.set_editor_property("materials", sm)
        return out

    def assign_static(name):
        m = unreal.load_asset(f"{DEST}/{name}")
        sm = list(m.get_editor_property("static_materials"))
        out = []
        for s in sm:
            nm = str(s.get_editor_property("material_slot_name"))
            out.append(nm)
            key = "Metal" if "Metal" in nm else ("Furniture" if "Furniture" in nm else ("Mag" if "Mag" in nm else None))
            if key:
                s.set_editor_property("material_interface", mats[key])
        m.set_editor_property("static_materials", sm)
        return out
    res["slots"] = {"SK_AR01": safe(assign_sk), "SM_AR01": safe(lambda: assign_static("SM_AR01")),
                    "SM_AR01_Mag": safe(lambda: assign_static("SM_AR01_Mag"))}
    dump()
    res["saved"] = bool(EAL.save_directory(DEST, only_if_is_dirty=False, recursive=True))
    res["listing"] = sorted(str(x) for x in EAL.list_assets(DEST, recursive=True, include_folder=False))
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
dump()
unreal.log("AR_PASS_A_DONE status=" + res["status"])
