"""Independent measurer (round 1): render the SHIPPED SM_Flashbang.fbx with its shipped baked maps.

usage: blender -b --factory-startup --python mr_render.py -- <mode> <cfg.json> <out> [samples]
  mode sweep : workbench texture renders of the top row over a yaw list -> npz of paint masks + alpha
  mode row   : Cycles top row (four copies, one camera like the reference)       -> png (+ alpha npy)
  mode close : Cycles close-up for cfg["key"]                                      -> png
Only the exported bytes are used: Exports/Flashbang/SM_Flashbang.fbx + Exports/Flashbang/Textures/*.png.
"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
FBX = ROOT + "Exports/Flashbang/SM_Flashbang.fbx"
TEX = ROOT + "Exports/Flashbang/Textures/"
argv = sys.argv[sys.argv.index("--") + 1:]
MODE, CFG, OUT = argv[0], json.load(open(argv[1])), argv[2]
SPP = int(argv[3]) if len(argv) > 3 else 128

REF = 1254
FOCAL_PX = 2600.0
LENS = FOCAL_PX / REF * 36.0
CAM_Y = -652.5e-3
VIEW_CX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
VIEW_BOT = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def img(name, noncolor):
    im = bpy.data.images.load(TEX + name)
    im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return im


def build_material():
    m = bpy.data.materials.new("MR_Shipped")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    bc = nt.nodes.new("ShaderNodeTexImage"); bc.image = img("T_Flashbang_BC.png", False)
    orm = nt.nodes.new("ShaderNodeTexImage"); orm.image = img("T_Flashbang_ORM.png", True)
    nrm = nt.nodes.new("ShaderNodeTexImage"); nrm.image = img("T_Flashbang_N.png", True)
    for t in (bc, orm, nrm):
        t.interpolation = "Cubic" if MODE != "sweep" else "Linear"
        nt.links.new(uv.outputs[0], t.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs[0], sep.inputs[0])
    # AO (R) multiplied into base colour lightly, roughness G, metallic B
    ao_mix = nt.nodes.new("ShaderNodeMix"); ao_mix.data_type = "RGBA"; ao_mix.blend_type = "MULTIPLY"
    ao_mix.inputs[0].default_value = 1.0
    nt.links.new(bc.outputs[0], ao_mix.inputs[6]); nt.links.new(sep.outputs[0], ao_mix.inputs[7])
    nt.links.new(ao_mix.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    # DirectX normal -> flip green for Blender (OpenGL)
    sn = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(nrm.outputs[0], sn.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cn = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cn.inputs[0]); nt.links.new(inv.outputs[0], cn.inputs[1]); nt.links.new(sn.outputs[2], cn.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "UVMap"
    nt.links.new(cn.outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    nt.nodes.active = bc
    return m


def load_lod0():
    bpy.ops.import_scene.fbx(filepath=FBX)
    lod0 = bpy.data.objects["SM_Flashbang_LOD0"]
    lod0.parent = None
    for o in list(bpy.data.objects):
        if o is not lod0:
            bpy.data.objects.remove(o, do_unlink=True)
    lod0.matrix_world = Matrix.Identity(4)
    mat = build_material()
    for i in range(len(lod0.data.materials)):
        lod0.data.materials[i] = mat
    for p in lod0.data.polygons:
        p.use_smooth = p.use_smooth  # keep shipped normals
    return lod0


def local_to_world_rot(phi_deg):
    """rotation about Z so that the object's LOCAL azimuth phi faces the camera (camera sits toward world -Y)."""
    return Matrix.Rotation(math.radians(-90.0 - phi_deg), 4, "Z")


def diffuse(name, rgb, rough=0.8, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (1, 1, 0.985, 1); b.inputs["Emission Strength"].default_value = emit
    return m


def studio(cfg, floor_z=0.0):
    # sweep: floor + curved wall far behind; lights are soft area lights, key from upper right front
    import bmesh
    me = bpy.data.meshes.new("MR_Sweep"); bm = bmesh.new()
    W = 6.0; prof = []
    for i in range(0, 25):
        t = i / 24.0
        if t < 0.5:
            prof.append((-3.0 + t * 2 * 4.0, floor_z))  # y from -3 to 1, z floor
        else:
            a = (t - 0.5) * 2 * math.pi / 2
            prof.append((1.0 + 1.0 * math.sin(a), floor_z + 1.0 - 1.0 * math.cos(a)))
    prof.append((2.0, floor_z + 4.0))
    rows = []
    for (y, z) in prof:
        rows.append([bm.verts.new((x, y, z)) for x in (-W, W)])
    for a, b in zip(rows[:-1], rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("MR_Sweep", me); sc.collection.objects.link(ob)
    g = cfg.get("bg_albedo", 0.05)
    ob.data.materials.append(diffuse("MR_Bg", (g, g, g * 0.97), 0.9, cfg.get("bg_emit", 0.0)))
    gf = cfg.get("floor_albedo", g)
    ob.data.materials.append(diffuse("MR_Floor", (gf, gf, gf * 0.97), 0.9, cfg.get("bg_emit", 0.0)))
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 1 if p.center.z < floor_z + 0.05 else 0
    ob.visible_camera = cfg.get("bg_visible", True)
    world = bpy.data.worlds.new("MR_World"); sc.world = world; world.use_nodes = True
    bgn = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (cfg.get("world", 0.01),) * 3 + (1,)
    bgn.inputs[1].default_value = 1.0
    tgt = Vector(cfg.get("light_target", (0, 0, 0.08)))

    def area(name, loc, size, power, col=(1, 1, 1)):
        L = bpy.data.lights.new(name, "AREA"); L.shape = "DISK"; L.size = size; L.energy = power; L.color = col
        o = bpy.data.objects.new(name, L); sc.collection.objects.link(o)
        o.location = Vector(loc)
        o.rotation_euler = (tgt - o.location).to_track_quat("-Z", "Y").to_euler()
        return o
    k = cfg.get("light_scale", 1.0)
    area("MR_Key", cfg.get("key_loc", (0.9, -0.9, 1.0)), cfg.get("key_size", 1.2), 220 * k * cfg.get("key_mul", 1.0), (1.0, 0.98, 0.95))
    area("MR_Fill", cfg.get("fill_loc", (-1.2, -0.8, 0.4)), 1.5, 45 * k * cfg.get("fill_mul", 1.0), (0.95, 0.97, 1.0))
    area("MR_Rim", cfg.get("rim_loc", (-0.6, 1.0, 0.9)), 0.8, 90 * k * cfg.get("rim_mul", 1.0))
    area("MR_Top", (0.0, -0.2, 1.6), 1.0, 40 * k * cfg.get("top_mul", 1.0))


def cycles(res, spp, transparent=False):
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"; prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.view_settings.exposure = CFG.get("exposure", 0.0)
    sc.render.use_stamp = False
    sc.render.metadata_input = "SCENE"
    for a in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_camera",
              "use_stamp_lens", "use_stamp_scene", "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
        try:
            setattr(sc.render, a, False)
        except Exception:
            pass


def row_camera():
    cd = bpy.data.cameras.new("MR_RowCam"); cd.lens = LENS; cd.sensor_width = 36.0; cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.01
    co = bpy.data.objects.new("MR_RowCam", cd); sc.collection.objects.link(co)
    co.rotation_euler = (math.radians(90), 0, 0)  # looks +Y, level
    cd.shift_y = -(REF / 2 - 460.0) / REF
    sc.camera = co
    return co


def project(co, p):
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(sc, co, Vector(p))
    return v.x * REF, (1 - v.y) * REF


def place_row(lod0, yaws):
    """four copies; each copy's axis projects to the reference body centre, its front foot to the contact row."""
    co = row_camera()
    sc.render.resolution_x = sc.render.resolution_y = REF
    # camera height: solve so the front foot (r 20.7 mm) of a copy at depth 0 lands on the mean contact row
    rows = []
    mean_bot = np.mean(list(VIEW_BOT.values()))
    hc = 0.062
    for _ in range(30):
        co.location = (0, CAM_Y, hc)
        bpy.context.view_layer.update()
        _, y = project(co, (0, -0.0207, 0.0))
        hc -= (y - mean_bot) / FOCAL_PX * 0.63
    co.location = (0, CAM_Y, hc)
    bpy.context.view_layer.update()
    copies = []
    for i, v in enumerate(("v1", "v2", "v3", "v4")):
        c = lod0 if i == 0 else lod0.copy()
        if i:
            sc.collection.objects.link(c)
        x = (VIEW_CX[v] - REF / 2) / FOCAL_PX * (-CAM_Y)
        for _ in range(20):
            px, _ = project(co, (x, 0.0, 0.07))
            x -= (px - VIEW_CX[v]) / FOCAL_PX * (-CAM_Y)
        c.matrix_world = Matrix.Translation((x, 0.0, 0.0)) @ local_to_world_rot(yaws[v])
        copies.append(c)
    bpy.context.view_layer.update()
    return co, copies, hc


def save_alpha_npy(path_png, out_npy):
    im = bpy.data.images.load(path_png)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
    np.save(out_npy, a)


def sweep():
    lod0 = load_lod0()
    yaws_list = CFG["yaws"]
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"; sh.color_type = "TEXTURE"
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_percentage = 50
    res = {}
    co = None
    copies = None
    for yaw in yaws_list:
        ys = {v: yaw for v in ("v1", "v2", "v3", "v4")}
        if copies is None:
            co, copies, hc = place_row(lod0, ys)
        else:
            for c, v in zip(copies, ("v1", "v2", "v3", "v4")):
                t = c.matrix_world.translation.copy()
                c.matrix_world = Matrix.Translation(t) @ local_to_world_rot(yaw)
        sc.render.filepath = OUT + f"_tmp.png"
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(OUT + "_tmp.png", check_existing=False)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
        bpy.data.images.remove(im)
        res[str(yaw)] = (a * 255).astype(np.uint8)
    np.savez_compressed(OUT, **res)


def row():
    lod0 = load_lod0()
    co, copies, hc = place_row(lod0, CFG["yaws"])
    studio(CFG)
    cycles((REF, REF), SPP, transparent=CFG.get("transparent", False))
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print("MR_ROW hc_mm", round(hc * 1000, 2), "copies", [tuple(round(x * 1000, 1) for x in c.matrix_world.translation) for c in copies])


def close():
    lod0 = load_lod0()
    c = CFG
    # object transform: yaw so local azimuth phi faces the camera, then tilt about world X (top away from camera
    # positive), then image roll about world Y; pivot at the local point c["pivot"] (mm)
    piv = Vector(c.get("pivot", (0, 0, 80))) * 1e-3
    R = (Matrix.Rotation(math.radians(c.get("roll", 0.0)), 4, "Y") @ Matrix.Rotation(math.radians(c.get("wz", 0.0)), 4, "Z")
         @ Matrix.Rotation(math.radians(c.get("tilt", 0.0)), 4, "X") @ local_to_world_rot(c["phi"]))
    lod0.matrix_world = R @ Matrix.Translation(-piv)
    bpy.context.view_layer.update()
    # floor under the object's lowest point
    zs = [(lod0.matrix_world @ v.co).z for v in lod0.data.vertices]
    fz = min(zs)
    studio(c, floor_z=fz)
    cd = bpy.data.cameras.new("MR_Cam"); cd.lens = c["lens"]; cd.sensor_width = 36.0; cd.sensor_fit = "AUTO"
    cd.clip_start = 0.002
    if c.get("dof"):
        cd.dof.use_dof = True; cd.dof.focus_distance = c.get("focus", c["dist"]) * 1e-3; cd.dof.aperture_fstop = c["dof"]
    co = bpy.data.objects.new("MR_Cam", cd); sc.collection.objects.link(co)
    el = math.radians(c.get("el", 0.0))
    tgt = Vector(c.get("target", (0, 0, 0))) * 1e-3
    co.location = tgt + Vector((0, -math.cos(el), math.sin(el))) * c["dist"] * 1e-3
    q = (tgt - co.location).to_track_quat("-Z", "Y")
    co.rotation_euler = (q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(c.get("cam_roll", 0.0)), 4, "Z")).to_euler()
    cd.shift_x = c.get("shift_x", 0.0); cd.shift_y = c.get("shift_y", 0.0)
    sc.camera = co
    cycles(tuple(c["res"]), SPP)
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print("MR_CLOSE done", OUT)


{"sweep": sweep, "row": row, "close": close}[MODE]()
