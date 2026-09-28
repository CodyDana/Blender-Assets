"""INDEPENDENT pass A (fresh commandlet, -nullrhi): import the exact shipped FBX files and every map into a NEW
content path, apply the sidecar (LOD screen sizes, sockets, physics bodies), build check materials, save."""
import hashlib, json, os, sys, time, traceback
from pathlib import Path
import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
EXP = PROJ / "Exports" / "Fan"
OUT = Path(os.environ["IV_OUT"])
DEST = os.environ["IV_DEST"]
SC = json.loads((EXP / "SK_Fan.skeletal.json").read_text(encoding="utf-8"))
TSC = json.loads((EXP / "SK_Fan_Tassel.skeletal.json").read_text(encoding="utf-8"))
PROXY = PROJ / "WorkFiles/fan/build/physics_proxy/SK_Fan_PhysicsProxy.fbx"
TPROXY = PROJ / "WorkFiles/fan/build/physics_proxy/SK_Fan_Tassel_PhysicsProxy.fbx"
AT = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TC = unreal.TextureCompressionSettings
TMGS = unreal.TextureMipGenSettings
res = {"dest": DEST, "t0": time.time(), "steps": {}}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa
        return {"error": f"{type(e).__name__}: {e}"[:400]}


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


def mesh_ui(skeleton=None, physics=False):
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
    # exactly the sidecar's "import" block
    d.set_editor_property("import_morph_targets", False)
    d.set_editor_property("convert_scene", True)
    d.set_editor_property("force_front_x_axis", False)
    d.set_editor_property("use_t0_as_ref_pose", False)
    d.set_editor_property("update_skeleton_reference_pose", False)
    d.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    return ui


def anim_ui(skeleton):
    """What a buyer gets: skeleton set, animation import, everything else the importer's default."""
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
    res.setdefault("anim_import_defaults", {k: str(safe(lambda: d.get_editor_property(k))) for k in (
        "animation_length", "use_default_sample_rate", "custom_sample_rate", "remove_redundant_keys",
        "import_bone_tracks", "convert_scene", "snap_to_closest_frame_boundary")})
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


def build_phys(mesh, skel, proxy, spec, name):
    rec = {"proxy": str(proxy), "proxy_sha256": sha(proxy)}
    pname = name + "_Proxy"
    rec["import"] = imp(proxy, DEST, pname, mesh_ui(skeleton=skel, physics=True))
    pm = unreal.load_asset(f"{DEST}/{pname}")
    pa = pm.get_editor_property("physics_asset")
    got = bodies_of(pa)
    rec["auto_bodies"] = sorted(got)
    ref = comp_ref(mesh)
    for b in spec:
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
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS
                               if any(e["collision"] for e in b["elements"]) else unreal.CollisionEnabled.NO_COLLISION)
        bi.set_editor_property("override_mass", True)
        bi.set_editor_property("mass_in_kg_override", float(b["mass_kg"]))
        bs.set_editor_property("default_instance", bi)
    safe(lambda: pa.set_editor_property("preview_skeletal_mesh", mesh))
    pm.set_editor_property("physics_asset", None)
    EAL.delete_loaded_asset(pm)
    rec["renamed"] = bool(EAL.rename_asset(pa.get_path_name().split(".")[0], f"{DEST}/{name}"))
    pa = unreal.load_asset(f"{DEST}/{name}")
    mesh.set_editor_property("physics_asset", pa)
    rec["asset"] = pa.get_path_name()
    return rec


def add_sockets(mesh, spec):
    ref = comp_ref(mesh)
    out = []
    for s in spec:
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


def tex_info(t):
    d = {}
    for k in ("srgb", "compression_settings", "mip_gen_settings", "lod_group", "flip_green_channel",
              "compression_no_alpha", "address_x", "address_y", "never_stream", "compression_quality", "power_of_two_mode"):
        d[k] = str(safe(lambda: t.get_editor_property(k)))
    d["size"] = [safe(lambda: t.blueprint_get_size_x()), safe(lambda: t.blueprint_get_size_y())]
    return d


# pack conventions: Scripts/props/props_lib/ue_import_textures.py INTENT + material_spec texture_import (Detail16)
INTENT = {
    "BC": {"srgb": True, "compression_settings": TC.TC_DEFAULT, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP},
    "ORM": {"srgb": False, "compression_settings": TC.TC_MASKS, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP},
    "N": {"srgb": False, "compression_settings": TC.TC_NORMALMAP, "flip_green_channel": False,
          "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP},
    "Detail": {"srgb": True, "compression_settings": TC.TC_GRAYSCALE, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP},
    "Detail16": {"srgb": False, "compression_settings": TC.TC_GRAYSCALE, "mip_gen_settings": TMGS.TMGS_FROM_TEXTURE_GROUP},
}


def tsample(m, tex, x, y, stype=None):
    e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
    e.set_editor_property("texture", tex)
    if stype is not None:
        e.set_editor_property("sampler_type", stype)
    return e


def scalar(m, name, v, x, y):
    e = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", float(v))
    return e


def new_mat(name):
    m = AT.create_asset(name, DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)
    return m


def tint_material(name, T, part, tint, bias, scale):
    """BaseColor = saturate(Colour x (Bias + Scale x Detail16)) - the pack's recolour law with the sidecar defaults;
    roughness ORM.G, AO ORM.R, normal N."""
    m = new_mat(name)
    det = tsample(m, T[f"T_Fan_{part}_Detail16"], -900, -200, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -900, -450)
    col.set_editor_property("parameter_name", "Colour")
    col.set_editor_property("default_value", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
    b = scalar(m, "Detail Bias", bias, -900, 0)
    s = scalar(m, "Detail Scale", scale, -900, 100)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -600, -150)
    MEL.connect_material_expressions(s, "", mul, "A")
    MEL.connect_material_expressions(det, "R", mul, "B")
    add = MEL.create_material_expression(m, unreal.MaterialExpressionAdd, -450, -100)
    MEL.connect_material_expressions(b, "", add, "A")
    MEL.connect_material_expressions(mul, "", add, "B")
    mul2 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, -250)
    MEL.connect_material_expressions(col, "", mul2, "A")
    MEL.connect_material_expressions(add, "", mul2, "B")
    sat = MEL.create_material_expression(m, unreal.MaterialExpressionSaturate, -150, -250)
    MEL.connect_material_expressions(mul2, "", sat, "")
    MEL.connect_material_property(sat, "", unreal.MaterialProperty.MP_BASE_COLOR)
    orm = tsample(m, T[f"T_Fan_{part}_ORM"], -600, 250, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    n = tsample(m, T[f"T_Fan_{part}_N"], -600, 550, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m)
    return m


def bc_material(name, T, part, metal):
    m = new_mat(name)
    bc = tsample(m, T[f"T_Fan_{part}_BC"], -600, -200)
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    orm = tsample(m, T[f"T_Fan_{part}_ORM"], -600, 150, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if metal:
        MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    n = tsample(m, T[f"T_Fan_{part}_N"], -600, 450, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m)
    return m


def flat_material(name, rgb, rough=0.6):
    m = new_mat(name)
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    c.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 200)
    r.set_editor_property("r", rough)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    return m


try:
    files = ["SK_Fan.fbx", "SK_Fan_LOD1.fbx", "SK_Fan_LOD2.fbx", "A_Fan_OpenClose.fbx", "A_Fan_Openness.fbx",
             "A_Fan_OpenPose.fbx", "SK_Fan_Tassel.fbx", "SK_Fan_Tassel_LOD1.fbx", "SK_Fan_Tassel_LOD2.fbx",
             "SK_Fan.skeletal.json", "SK_Fan_Tassel.skeletal.json"]
    res["sha256_before"] = {f: sha(EXP / f) for f in files}
    pngs = sorted(list((EXP / "Textures").glob("*.png")) + list((EXP / "Textures" / "Recolour").glob("*.png")))
    res["png_sha256_before"] = {p.name: sha(p) for p in pngs}
    # ---------------- SK_Fan + LODs
    res["steps"]["mesh"] = imp(EXP / "SK_Fan.fbx", DEST, "SK_Fan", mesh_ui())
    mesh = unreal.load_asset(f"{DEST}/SK_Fan")
    skel = mesh.get_editor_property("skeleton")
    res["skeleton"] = skel.get_path_name()
    res["steps"]["lods"] = [safe(lambda: SUB.import_lod(mesh, i, str(EXP / f"SK_Fan_LOD{i}.fbx"))) for i in (1, 2)]
    res["lod_count_after_import"] = SUB.get_lod_count(mesh)

    def sizes():
        try:
            infos = list(mesh.get_editor_property("lod_info"))
            for i, v in enumerate(SC["lod_screen_sizes"]):
                pp = unreal.PerPlatformFloat()
                pp.set_editor_property("default", float(v))
                infos[i].set_editor_property("screen_size", pp)
            mesh.set_editor_property("lod_info", infos)
            return {"route": "lod_info"}
        except Exception as e:  # noqa
            ls = AT.create_asset("LODS_Fan_IV", DEST, unreal.SkeletalMeshLODSettings, None)
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
            return {"route": "lod_settings", "lod_info_error": str(e)[:200], "verts_before": v0, "verts_after": v1}
    res["steps"]["screen_sizes"] = safe(sizes)
    # ---------------- animations: buyer-default import, then a second copy with the builder's compression
    anims = {}
    for a in SC["animations"]:
        nm = a["file"][:-4]
        p1 = imp(EXP / a["file"], DEST, nm + "_Default", anim_ui(skel))
        p2 = imp(EXP / a["file"], DEST, nm, anim_ui(skel))
        seq = unreal.load_asset(f"{DEST}/{nm}")
        dseq = unreal.load_asset(f"{DEST}/{nm}_Default")
        default_comp = safe(lambda: unreal.AnimationLibrary.get_bone_compression_settings(dseq).get_path_name())
        unreal.AnimationLibrary.set_bone_compression_settings(seq, unreal.load_asset("/Engine/Animation/DefaultRecorderBoneCompression"))
        anims[nm] = {"default_paths": p1, "paths": p2, "default_compression": default_comp,
                     "set_compression": unreal.AnimationLibrary.get_bone_compression_settings(seq).get_path_name()}
    res["steps"]["animations"] = anims
    # ---------------- sockets
    res["steps"]["sockets"] = add_sockets(mesh, SC["sockets"])
    # ---------------- tassel
    res["steps"]["tassel"] = imp(EXP / "SK_Fan_Tassel.fbx", DEST, "SK_Fan_Tassel", mesh_ui())
    tmesh = unreal.load_asset(f"{DEST}/SK_Fan_Tassel")
    res["steps"]["tassel_lods"] = [safe(lambda: SUB.import_lod(tmesh, i, str(EXP / f"SK_Fan_Tassel_LOD{i}.fbx"))) for i in (1, 2)]
    # ---------------- physics (sidecar bodies through the build's proxy: the body list is not scriptable)
    res["steps"]["physics_fan"] = safe(lambda: build_phys(mesh, skel, PROXY, SC["physics_bodies"], "PHYS_Fan_IV"))
    res["steps"]["physics_tassel"] = safe(lambda: build_phys(tmesh, tmesh.get_editor_property("skeleton"), TPROXY,
                                                             TSC["physics_bodies"], "PHYS_Fan_Tassel_IV"))
    # ---------------- every map
    T, tex = {}, {}
    for p in pngs:
        name = p.stem
        kind = "Detail16" if name.endswith("Detail16") else name.rsplit("_", 1)[-1]
        paths = imp(p, DEST + "/Textures", name)
        t = unreal.load_asset(f"{DEST}/Textures/{name}")
        rec = {"kind": kind, "paths": paths, "as_imported": tex_info(t) if t else None}
        if t:
            for k, v in INTENT[kind].items():
                t.set_editor_property(k, v)
            rec["applied"] = tex_info(t)
            T[name] = t
        tex[name] = rec
    res["textures"] = tex
    # ---------------- check materials
    mats = {}
    for part, key in (("Leaf", "M_Fan_Leaf"), ("Sticks", "M_Fan_Sticks")):
        m = SC["materials"][key]
        mats["tint_" + key] = tint_material(f"M_IV_Tint_{part}", T, part, m["tint_default_linear"], m["detail_bias_default"], m["detail_scale_default"])
        mats["bc_" + key] = bc_material(f"M_IV_BC_{part}", T, part, False)
    tm = TSC["materials"]["M_Fan_Tassel"]
    mats["tint_M_Fan_Tassel"] = tint_material("M_IV_Tint_Tassel", T, "Tassel", tm["tint_default_linear"], tm["detail_bias_default"], tm["detail_scale_default"])
    mats["bc_M_Fan_Tassel"] = bc_material("M_IV_BC_Tassel", T, "Tassel", False)
    mats["bc_M_Fan_Rivet"] = bc_material("M_IV_BC_Rivet", T, "Rivet", True)
    for nm, rgb in (("Leaf", (0.55, 0.62, 0.75)), ("Sticks", (0.75, 0.35, 0.08)), ("Rivet", (0.9, 0.9, 0.9)), ("Tassel", (0.1, 0.6, 0.2))):
        mats["dbg_" + nm] = flat_material(f"M_IV_Dbg_{nm}", rgb)
    res["materials_created"] = {k: v.get_path_name() for k, v in mats.items()}
    slots = []
    sm = list(mesh.get_editor_property("materials"))
    for s in sm:
        nm = str(s.get_editor_property("material_slot_name"))
        mi = s.get_editor_property("material_interface")
        slots.append({"slot": nm, "imported_material": mi.get_path_name() if mi else None})
        m = mats.get("tint_" + nm) or mats.get("bc_" + nm)
        if m:
            s.set_editor_property("material_interface", m)
    mesh.set_editor_property("materials", sm)
    ts = list(tmesh.get_editor_property("materials"))
    for s in ts:
        slots.append({"tassel_slot": str(s.get_editor_property("material_slot_name"))})
        s.set_editor_property("material_interface", mats["tint_M_Fan_Tassel"])
    tmesh.set_editor_property("materials", ts)
    res["slots"] = slots
    res["saved"] = bool(EAL.save_directory(DEST, only_if_is_dirty=False, recursive=True))
    res["listing"] = sorted(str(x) for x in EAL.list_assets(DEST, recursive=True, include_folder=False))
    res["sha256_after"] = {f: sha(EXP / f) for f in files}
    res["status"] = "ok"
except Exception:  # noqa
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ivA.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
unreal.log("IV_PASS_A_DONE status=" + res["status"])
