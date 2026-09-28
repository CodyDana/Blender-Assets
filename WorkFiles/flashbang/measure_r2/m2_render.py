"""Round-2 independent measurer: render the SHIPPED SM_Flashbang.fbx (LOD0) with the SHIPPED textures only.
usage: blender -b --factory-startup --python m2_render.py -- <mode> <cfg.json> <out.png> [spp]
modes: sweep (workbench silhouettes of the row over a yaw list -> npz), row (Cycles top row), close (Cycles close-up)"""
import bpy, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
FBX = ROOT + "Exports/Flashbang/SM_Flashbang.fbx"
TEX = ROOT + "Exports/Flashbang/Textures/"
argv = sys.argv[sys.argv.index("--") + 1:]
MODE, CFG, OUT = argv[0], json.load(open(argv[1])), argv[2]
SPP = int(argv[3]) if len(argv) > 3 else 96
REF = 1254
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def teximg(name, noncolor):
    im = bpy.data.images.load(TEX + name)
    im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return im


def shipped_material():
    m = bpy.data.materials.new("M2_Shipped"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    bc = nt.nodes.new("ShaderNodeTexImage"); bc.image = teximg("T_Flashbang_BC.png", False)
    orm = nt.nodes.new("ShaderNodeTexImage"); orm.image = teximg("T_Flashbang_ORM.png", True)
    nr = nt.nodes.new("ShaderNodeTexImage"); nr.image = teximg("T_Flashbang_N.png", True)
    for t in (bc, orm, nr):
        t.interpolation = "Linear" if MODE == "sweep" else "Cubic"
        nt.links.new(uv.outputs[0], t.inputs[0])
    so = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(orm.outputs[0], so.inputs[0])
    nt.links.new(bc.outputs[0], b.inputs["Base Color"])
    nt.links.new(so.outputs[1], b.inputs["Roughness"]); nt.links.new(so.outputs[2], b.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(nr.outputs[0], sn.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cc = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cc.inputs[0]); nt.links.new(inv.outputs[0], cc.inputs[1]); nt.links.new(sn.outputs[2], cc.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "UVMap"
    nt.links.new(cc.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs[0]); nt.nodes.active = bc
    return m


def load_lod0():
    bpy.ops.import_scene.fbx(filepath=FBX)
    o = bpy.data.objects["SM_Flashbang_LOD0"]; o.parent = None
    for x in list(bpy.data.objects):
        if x is not o:
            bpy.data.objects.remove(x, do_unlink=True)
    o.matrix_world = Matrix.Identity(4)
    m = shipped_material()
    for i in range(len(o.data.materials)):
        o.data.materials[i] = m
    return o


def dmat(name, g, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (g, g, g * 0.98, 1); b.inputs["Roughness"].default_value = 0.9
    if emit:
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1); b.inputs["Emission Strength"].default_value = emit
    return m


def area(name, loc, tgt, size, power, col):
    L = bpy.data.lights.new(name, "AREA"); L.shape = "DISK"; L.size = size; L.energy = power; L.color = col
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = Vector(loc)
    o.rotation_euler = (Vector(tgt) - o.location).to_track_quat("-Z", "Y").to_euler()
    return o


def world(g):
    w = bpy.data.worlds.new("M2_W"); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (g, g, g, 1)


def cam_rig_lights(cam, tgt, k):
    """soft studio lights placed in the camera frame: key upper-left front, fill right, rim behind."""
    r = cam.matrix_world.to_3x3(); t = Vector(tgt)
    right, up, back = r @ Vector((1, 0, 0)), r @ Vector((0, 1, 0)), r @ Vector((0, 0, 1))
    D = CFG.get("light_dist", 0.9)
    kl = CFG.get("key_dir", (-0.75, 0.75, 0.9)); fl = CFG.get("fill_dir", (1.0, 0.1, 0.7)); rl = CFG.get("rim_dir", (0.6, 0.6, -1.0))

    def P(dv):
        v = right * dv[0] + up * dv[1] + back * dv[2]; v.normalize(); return t + v * D
    area("M2_Key", P(kl), t, CFG.get("key_size", 0.9), 110 * k * CFG.get("key_mul", 1.0), (1.0, 0.97, 0.92))
    area("M2_Fill", P(fl), t, 1.2, 28 * k * CFG.get("fill_mul", 1.0), (0.93, 0.96, 1.0))
    area("M2_Rim", P(rl), t, 0.6, 60 * k * CFG.get("rim_mul", 1.0), (1.0, 0.98, 0.95))


def cycles(res, transparent=False):
    sc.render.engine = "CYCLES"
    ok = False
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        for dt in ("OPTIX", "CUDA"):
            try:
                pr.compute_device_type = dt; pr.get_devices()
                for d in pr.devices:
                    d.use = d.type == dt
                if any(d.use for d in pr.devices):
                    ok = True; break
            except Exception:
                pass
    except Exception:
        pass
    sc.cycles.device = "GPU" if ok else "CPU"
    print("M2R device", sc.cycles.device)
    sc.cycles.samples = SPP; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    s = sc.render.image_settings; s.file_format = "PNG"; s.color_mode = "RGBA" if transparent else "RGB"; s.color_depth = "8"
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.view_settings.exposure = CFG.get("exposure", 0.0)
    sc.render.use_stamp = False


def newcam(lens):
    cd = bpy.data.cameras.new("M2_Cam"); cd.lens = lens; cd.sensor_width = 36.0; cd.sensor_fit = "HORIZONTAL"; cd.clip_start = 0.002
    co = bpy.data.objects.new("M2_Cam", cd); sc.collection.objects.link(co); sc.camera = co
    return co


def rotz_face(phi):  # local azimuth phi faces the camera (camera toward world -Y)
    return Matrix.Rotation(math.radians(-90.0 - phi), 4, "Z")


def backdrop(floor_z, g_wall, g_floor, emit):
    import bmesh
    me = bpy.data.meshes.new("M2_Sweep"); bm = bmesh.new(); prof = []
    for i in range(25):
        t = i / 24.0
        y0s, rr = CFG.get("sweep_y0", 0.12), CFG.get("sweep_r", 0.5)
        if t < 0.5:
            prof.append((-3.0 + t * 2 * (3.0 + y0s), floor_z))
        else:
            a = (t - 0.5) * math.pi; prof.append((y0s + rr * math.sin(a), floor_z + rr - rr * math.cos(a)))
    prof.append((y0s + rr, floor_z + 4.0))
    rows = [[bm.verts.new((x, y, z)) for x in (-6, 6)] for (y, z) in prof]
    for a, b in zip(rows[:-1], rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("M2_Sweep", me); sc.collection.objects.link(ob)
    ob.data.materials.append(dmat("M2_Wall", g_wall, emit)); ob.data.materials.append(dmat("M2_Floor", g_floor, emit))
    for p in me.polygons:
        p.use_smooth = True; p.material_index = 1 if p.center.z < floor_z + 0.005 else 0
    return ob


def proj(co, p):
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(sc, co, Vector(p))
    return v.x * REF, (1 - v.y) * REF


def row_setup(o, yaws):
    c = CFG
    sc.render.resolution_x = sc.render.resolution_y = REF
    co = newcam(c["focal_px"] / REF * 36.0)
    el = math.radians(c.get("el", 0.0)); tz = c.get("tz", 80.0) * 1e-3
    d = c.get("dist0", 650.0) * 1e-3
    co.data.shift_y = 0.0
    for _ in range(3):
        for _ in range(25):
            co.location = (0, -d * math.cos(el), tz + d * math.sin(el)); co.rotation_euler = (math.pi / 2 - el, 0, 0)
            bpy.context.view_layer.update()
            xa, _ = proj(co, (-0.022, 0, 0.060)); xb, _ = proj(co, (0.022, 0, 0.060))
            w = abs(xb - xa) * (1 + 0.5 * (0.022 / d) ** 2)
            d *= w / c.get("body_px", 176.0)
        _, yb = proj(co, (0, -0.0239, 0.0))
        co.data.shift_y -= (yb - c.get("bot_row", 714.0)) / REF
        bpy.context.view_layer.update()
    copies = []
    for i, v in enumerate(("v1", "v2", "v3", "v4")):
        x = o if i == 0 else o.copy()
        if i:
            sc.collection.objects.link(x)
        px = 0.0
        for _ in range(20):
            X, _ = proj(co, (px, 0, 0.01))
            px -= (X - c["cx"][v]) / c["focal_px"] * d
        x.matrix_world = Matrix.Translation((px, 0, 0)) @ rotz_face(yaws[v])
        copies.append(x)
    bpy.context.view_layer.update()
    print("M2R cam dist_mm", round(d * 1000, 1), "loc", tuple(round(a * 1000, 1) for a in co.location), "shift_y", round(co.data.shift_y, 4))
    return co, copies


def sweep():
    o = load_lod0()
    sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "FLAT"; sh.color_type = CFG.get("wb_color", "SINGLE")
    sh.single_color = (1, 1, 1)
    sc.view_settings.view_transform = "Standard"; sc.render.film_transparent = True
    s = sc.render.image_settings; s.file_format = "PNG"; s.color_mode = "RGBA"
    res = {}; copies = None
    for yaw in CFG["yaw_list"]:
        ys = {v: yaw for v in ("v1", "v2", "v3", "v4")}
        if copies is None:
            co, copies = row_setup(o, ys)
            sc.render.resolution_percentage = CFG.get("pct", 50)
        else:
            for x, v in zip(copies, ("v1", "v2", "v3", "v4")):
                x.matrix_world = Matrix.Translation(x.matrix_world.translation.copy()) @ rotz_face(yaw)
        sc.render.filepath = OUT + "_tmp.png"; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(OUT + "_tmp.png", check_existing=False)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
        bpy.data.images.remove(im); res[str(yaw)] = (a[..., 3] > 0.5) if CFG.get("wb_color", "SINGLE") == "SINGLE" else (a * 255).astype(np.uint8)
    np.savez_compressed(OUT, **res)


def row():
    o = load_lod0()
    co, copies = row_setup(o, CFG["yaws"])
    tgt = (0, 0, 0.08)
    if not CFG.get("transparent"):
        backdrop(0.0, CFG.get("wall", 0.03), CFG.get("floor", 0.02), CFG.get("bg_emit", 0.0))
    world(CFG.get("world", 0.005))
    k = CFG.get("light_scale", 1.0); D = CFG.get("light_dist", 1.2)
    kd = CFG.get("key_loc", (-0.7, -0.9, 0.9))
    area("M2_Key", tuple(x * D for x in kd), tgt, CFG.get("key_size", 1.0), 220 * k * CFG.get("key_mul", 1.0), (1.0, 0.97, 0.92))
    area("M2_Fill", (1.0 * D, -0.7 * D, 0.35 * D), tgt, 1.4, 45 * k * CFG.get("fill_mul", 1.0), (0.93, 0.96, 1.0))
    area("M2_Rim", (0.5 * D, 1.0 * D, 0.9 * D), tgt, 0.8, 90 * k * CFG.get("rim_mul", 1.0), (1, 0.98, 0.95))
    area("M2_Top", (0.0, -0.2 * D, 1.5 * D), tgt, 1.0, 40 * k * CFG.get("top_mul", 1.0), (1, 1, 1))
    cycles((REF, REF), CFG.get("transparent", False))
    sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)


def close():
    o = load_lod0(); c = CFG
    tgt = Vector(c["target"]) * 1e-3
    az, el = math.radians(c["az"]), math.radians(c["el"])
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    co = newcam(c["lens"]); loc = tgt + d * c["dist"] * 1e-3
    up = Vector(c.get("up", (0, 0, 1)))
    fwd = (tgt - loc).normalized(); rt = fwd.cross(up).normalized(); upv = rt.cross(fwd)
    M = Matrix((rt, upv, -fwd)).transposed().to_4x4()
    M = M @ Matrix.Rotation(math.radians(c.get("roll", 0.0)), 4, "Z")
    M.translation = loc; co.matrix_world = M
    co.data.shift_x = c.get("shift_x", 0.0); co.data.shift_y = c.get("shift_y", 0.0)
    if c.get("fstop"):
        co.data.dof.use_dof = True; co.data.dof.focus_distance = c.get("focus", c["dist"]) * 1e-3; co.data.dof.aperture_fstop = c["fstop"]
    bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_plane_add(size=3.0); card = bpy.context.active_object
    card.matrix_world = Matrix.Translation(tgt - d * 0.35) @ M.to_3x3().to_4x4()
    card.data.materials.append(dmat("M2_Card", c.get("card", 0.03), c.get("card_emit", 0.0)))
    world(c.get("world", 0.003))
    cam_rig_lights(co, tgt, c.get("light_scale", 1.0))
    cycles(tuple(c["res"]), False)
    sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)


{"sweep": sweep, "row": row, "close": close}[MODE]()
print("M2R done", MODE, OUT)
