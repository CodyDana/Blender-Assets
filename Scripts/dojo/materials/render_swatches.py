"""Swatch renders for the shared dojo material library (headless Blender, Cycles).

For every library material: shape A (sphere / bevelled cube / framed pane) and shape B (bevelled plank / block /
strap / coil / barrel), each rendered twice with a transparent film:
  studio  = the model sheets' soft grey studio light (the same rig render_training.py calibrated against the sheets:
            grey world 0.78 x 0.55, key / fill / top disc lights, AgX Medium High Contrast, exposure -0.8)
  sunset  = dojo1_reference2's time of day: 3000 K sun 11 degrees up, warm-to-blue sky ramp, exposure -0.4
Shapes use the library's own UV helpers (grain_uv / box_uv / round_uv / rope_uv / unit_uv) and bake_wear, i.e. what
a kit build script would call.

  blender -b --factory-startup --python Scripts/dojo/materials/render_swatches.py -- --round r1 [--only TimberDark,Iron]
    [--samples 96] [--res 420]
Writes WorkFiles/dojo/build/materials/renders/<round>/<Material>_<A|B>_<studio|sunset>.png + shapes.json
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dojo_materials as djm  # noqa: E402

ROOT = HERE.parents[2]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


ROUND = arg("--round", "r1")
ONLY = set(arg("--only", "").split(",")) - {""}
SAMPLES = int(arg("--samples", "96"))
RES = int(arg("--res", "420"))
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "materials" / "renders" / ROUND


# ------------------------------------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(exposure):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == dev_type
                sc.cycles.device = "GPU"
                break
        except TypeError:
            continue
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = exposure


def new_obj(name, data):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return o


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def kelvin_rgb(k):
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def area(name, loc, target, size, power):
    L = bpy.data.lights.new(name, "AREA")
    L.shape = "DISK"
    L.size = size
    L.energy = power
    o = new_obj(name, L)
    o.location = loc
    look_at(o, target)
    return o


def catcher():
    me = bpy.data.meshes.new("Catcher")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=20.0)
    bm.to_mesh(me)
    bm.free()
    o = new_obj("Catcher", me)
    o.is_shadow_catcher = True
    return o


def studio_rig(c):
    w = bpy.data.worlds.new("W_Studio")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.78, 0.78, 0.78, 1)
    bg.inputs["Strength"].default_value = 0.55
    bpy.context.scene.world = w
    c = Vector(c)
    objs = [area("L_Key", c + Vector((-3.5, -5.0, 4.5)), c, 5.0, 750.0),
            area("L_Fill", c + Vector((4.5, -3.5, 2.5)), c, 5.0, 300.0),
            area("L_Top", c + Vector((0.5, 1.5, 6.0)), c, 6.0, 380.0)]
    return objs


def sunset_rig():
    w = bpy.data.worlds.new("W_Sunset")
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (1.0, 0.52, 0.22, 1)
    els[1].position, els[1].color = 0.35, (0.42, 0.42, 0.52, 1)
    e = els.new(0.10)
    e.color = (0.95, 0.62, 0.45, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    bpy.context.scene.world = w
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 4.5
    sun.color = kelvin_rgb(3000)
    sun.angle = math.radians(0.6)
    so = new_obj("Sun", sun)
    el, az = math.radians(11.0), math.radians(60.0)     # travels toward +X+Y: lights the faces the camera sees
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)))
    so.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    return [so]


def camera_for(obj, elev=24.0, azim=-58.0, margin=1.18):
    """Orthographic 3/4 camera from the front-left (-Y), framing the object's world bounds."""
    bpy.context.view_layer.update()
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (lo + hi) / 2
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    co = new_obj("Cam", cam)
    e, a = math.radians(elev), math.radians(azim)
    d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
    co.location = ctr + d * 10.0
    look_at(co, ctr)
    bpy.context.view_layer.update()
    inv = co.matrix_world.inverted()
    cp = [inv @ p for p in pts]
    ext = max(max(p.x for p in cp) - min(p.x for p in cp), max(p.y for p in cp) - min(p.y for p in cp))
    cam.ortho_scale = ext * margin
    bpy.context.scene.camera = co
    return co, ctr


# ------------------------------------------------------------------------------------------------ shapes
def mesh_obj(name, build):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(me)
    bm.free()
    o = new_obj(name, me)
    for p in me.polygons:
        p.use_smooth = False
    return o


def box(name, sx, sy, sz, bevel=0.0, segs=2, z0=0.0):
    def b(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz + sz / 2 + z0))
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, profile=0.5, affect="EDGES")
    o = mesh_obj(name, b)
    if bevel > 0 and segs > 1:
        for p in o.data.polygons:
            p.use_smooth = True
        o.data.shade_smooth()
        try:
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
        except Exception:
            pass
    return o


def sphere(name, r, z0=None):
    def b(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=r)
        for v in bm.verts:
            v.co.z += r if z0 is None else z0
    o = mesh_obj(name, b)
    o.data.shade_smooth()
    return o


def cylinder(name, r, length, axis="X", segs=48, z0=None, cap_bevel=0.0):
    def b(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=length)
        if cap_bevel > 0:
            caps = [e for e in bm.edges if all(abs(abs(v.co.z) - length / 2) < 1e-6 for v in e.verts)]
            bmesh.ops.bevel(bm, geom=caps, offset=cap_bevel, segments=2, profile=0.5, affect="EDGES")
        for v in bm.verts:
            x, y, z = v.co
            if axis == "X":      # a rotation (z, y, -x), not a reflection: normals stay outward
                v.co = Vector((z, y, -x + (r if z0 is None else z0)))
            else:
                v.co = Vector((x, y, z + length / 2))
    o = mesh_obj(name, b)
    o.data.shade_smooth()
    try:
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    except Exception:
        pass
    return o


def torus(name, R, r):
    def b(bm):
        seg_u, seg_v = 96, 24
        vs = []
        for i in range(seg_u):
            ph = 2 * math.pi * i / seg_u
            row = []
            for j in range(seg_v):
                th = 2 * math.pi * j / seg_v
                x = (R + r * math.cos(th)) * math.cos(ph)
                y = (R + r * math.cos(th)) * math.sin(ph)
                z = r * math.sin(th) + r
                row.append(bm.verts.new((x, y, z)))
            vs.append(row)
        for i in range(seg_u):
            for j in range(seg_v):
                a, b_, c, d = vs[i][j], vs[(i + 1) % seg_u][j], vs[(i + 1) % seg_u][(j + 1) % seg_v], vs[i][(j + 1) % seg_v]
                bm.faces.new((a, b_, c, d))
    o = mesh_obj(name, b)
    o.data.shade_smooth()
    return o


def flat_mat(name, srgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = tuple(djm._lin(c) for c in srgb) + (1,)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def assign(o, *mats):
    o.data.materials.clear()
    for m in mats:
        o.data.materials.append(m)


def framed_pane(name, w, h, muntins=True, glass_mat=None, frame_mat=None, frame=0.025):
    """A window: 2 x 2 glass panes (unit UV each, so each pane has its own hotspot) in a timber frame with a
    muntin cross (the stone lantern / gate lamp look)."""
    objs = []
    nx, ny = (2, 2) if muntins else (1, 1)
    pw, ph = (w - frame * (nx + 1)) / nx, (h - frame * (ny + 1)) / ny

    def panes(bm):
        for i in range(nx):
            for j in range(ny):
                x0 = -w / 2 + frame + i * (pw + frame)
                z0 = frame + j * (ph + frame)
                vs = [bm.verts.new((x0, 0, z0)), bm.verts.new((x0 + pw, 0, z0)),
                      bm.verts.new((x0 + pw, 0, z0 + ph)), bm.verts.new((x0, 0, z0 + ph))]
                bm.faces.new(vs)
    g = mesh_obj(name + "_Glass", panes)
    djm.unit_uv(g)
    assign(g, glass_mat)
    objs.append(g)
    bars = []
    for i in range(nx + 1):
        x = -w / 2 + frame / 2 + i * (pw + frame)
        bars.append(box(f"{name}_V{i}", frame, frame * 1.6, h, bevel=0.003, segs=1))
        bars[-1].location = (x, -frame * 0.3, 0)
    for j in range(ny + 1):
        z = j * (ph + frame)
        bars.append(box(f"{name}_H{j}", w, frame * 1.6, frame, bevel=0.003, segs=1, z0=z))
        bars[-1].location = (0, -frame * 0.3, 0)
    for b_ in bars:
        bpy.context.view_layer.update()
        assign(b_, frame_mat[0], frame_mat[1])
        djm.grain_uv(b_, "TimberDark", end_set="TimberDarkEnd", end_material_index=1)
    return objs + bars


# material name -> (shape A builder, shape B builder)
def timber_shapes(mname, set_face, set_end):
    face = djm.make_material(mname)
    end = djm.make_material(mname + "End")

    def A():
        o = box("A", 0.46, 0.22, 0.22, bevel=0.012, segs=2)     # a short beam: grain along X, end grain at +-X
        assign(o, face, end)            # slots first: materials.clear() resets face material indices
        djm.grain_uv(o, set_face, end_set=set_end, end_material_index=1)
        djm.bake_wear(o)
        return [o]

    def B():
        o = box("B", 1.00, 0.16, 0.08, bevel=0.008, segs=2)
        o.rotation_euler = (0, 0, math.radians(20))
        post = box("B_post", 0.14, 0.14, 0.62, bevel=0.010, segs=2)
        post.location = (0.42, 0.18, 0.0)
        bpy.context.view_layer.update()
        o.location = (0.0, -0.05, 0.0)
        bpy.context.view_layer.update()
        for x in (o, post):
            assign(x, face, end)
            djm.grain_uv(x, set_face, end_set=set_end, end_material_index=1)
            djm.bake_wear(x, ground_z=0.0)
        return [o, post]
    return A, B


def stone_shapes(mname, set_name, rubble=False):
    m = djm.make_material(mname)

    def A():
        if rubble:
            o = box("A", 0.50, 0.50, 0.50, bevel=0.01, segs=1)
            djm.box_uv(o, set_name)
            djm.bake_wear(o, ground_z=0.0)
            assign(o, m)
        else:
            o = sphere("A", 0.25)
            djm.bake_wear(o, ground_z=0.0)
            assign(o, djm.make_material(mname, rebuild=True, projection="BOX", box_blend=0.3))
        return [o]

    def B():
        if rubble:
            o = box("B", 1.20, 0.35, 0.50, bevel=0.012, segs=2)
        else:
            o = box("B", 0.90, 0.35, 0.30, bevel=0.015, segs=2)
        djm.box_uv(o, set_name)
        djm.bake_wear(o, ground_z=0.0)
        assign(o, m)
        return [o]
    return A, B


def sphere_block(mname, set_name, B_kind="block", uv="box", tri=True):
    m = djm.make_material(mname)

    def A():
        o = sphere("A", 0.25)
        djm.box_uv(o, set_name)
        # round parts: the triplanar path (Blender BOX projection = Unreal WorldAlignedTexture), no UV seams
        assign(o, djm.make_material(mname, rebuild=True, projection="BOX", box_blend=0.3) if tri else m)
        return [o]

    def B():
        if B_kind == "strap":
            o = box("B", 0.70, 0.10, 0.018, bevel=0.003, segs=2)
            o.rotation_euler = (math.radians(70), 0, 0)
            o.location = (0, 0, 0.05)
            bpy.context.view_layer.update()
            ring = torus("B_ring", 0.07, 0.009)
            ring.rotation_euler = (math.radians(90), 0, 0)
            ring.location = (0.0, -0.04, 0.10)
            bpy.context.view_layer.update()
            djm.grain_uv(o, set_name)
            djm.box_uv(ring, set_name)
            assign(o, m)
            assign(ring, m)
            return [o, ring]
        if B_kind == "barrel":
            o = cylinder("B", 0.25, 0.50, axis="X", cap_bevel=0.01)
            djm.round_uv(o, set_name)
            djm.bake_wear(o, ground_z=0.0)
            assign(o, m)
            return [o]
        if B_kind == "wall":
            o = box("B", 1.20, 0.20, 0.90, bevel=0.01, segs=2)
            djm.box_uv(o, set_name)
            djm.bake_wear(o, ground_z=0.0)
            assign(o, m)
            return [o]
        o = box("B", 0.90, 0.35, 0.30, bevel=0.015, segs=2)
        djm.box_uv(o, set_name)
        assign(o, m)
        return [o]
    return A, B


def rope_shapes():
    m = djm.make_material("M_DJ_Rope")

    def A():
        o = cylinder("A", 0.03, 0.60, axis="X", segs=32)
        djm.rope_uv(o, 0.06)
        assign(o, m)
        return [o]

    def B():
        o = torus("B", 0.16, 0.02)
        djm.rope_uv(o, 0.04, mode="ring")
        assign(o, m)
        return [o]
    return A, B


def glass_shapes(mname):
    g = djm.make_material(mname)
    fm = (djm.make_material("M_DJ_TimberDark"), djm.make_material("M_DJ_TimberDarkEnd"))

    def A():
        return framed_pane("A", 0.34, 0.34, True, g, fm)

    def B():
        # a lamp box: one tall pane each side under an iron cap (the gate bracket lamp look)
        objs = []
        iron = djm.make_material("M_DJ_Iron")
        for k, (x, y, rz) in enumerate(((0, -0.09, 0), (0.09, 0, 90), (0, 0.09, 180), (-0.09, 0, 270))):
            parts = framed_pane(f"B{k}", 0.18, 0.26, False, g, fm, frame=0.016)
            for p in parts:
                p.rotation_euler = (0, 0, math.radians(rz))
                p.location = (x, y, 0.02)
            objs += parts
        for z, nm in ((0.0, "Bot"), (0.30, "Top")):
            c = box("B_" + nm, 0.24, 0.24, 0.02, bevel=0.004, segs=1, z0=z)
            djm.box_uv(c, "Iron")
            assign(c, iron)
            objs.append(c)
        return objs
    return A, B


def vending_shapes():
    g = djm.make_material("M_DJ_VendingPanel")
    teal = flat_mat("M_Review_Teal", (0.306, 0.486, 0.478), 0.45)
    white = flat_mat("M_Review_White", (0.80, 0.80, 0.78), 0.4)

    def A():
        def b(bm):
            vs = [bm.verts.new(p) for p in ((-0.25, 0, 0.1), (0.25, 0, 0.1), (0.25, 0, 1.1), (-0.25, 0, 1.1))]
            bm.faces.new(vs)
        pane = mesh_obj("A", b)
        djm.unit_uv(pane)
        assign(pane, g)
        fr = box("A_frame", 0.62, 0.06, 1.22, bevel=0.01, segs=1)
        fr.location = (0, 0.035, 0.0)
        assign(fr, white)
        body = box("A_body", 0.70, 0.40, 1.30, bevel=0.01, segs=1)
        body.location = (0, 0.265, -0.04)
        assign(body, teal)
        return [pane, fr, body]

    def B():
        def b(bm):
            vs = [bm.verts.new(p) for p in ((-0.25, 0, 0.0), (0.25, 0, 0.0), (0.25, 0, 1.0), (-0.25, 0, 1.0))]
            bm.faces.new(vs)
        pane = mesh_obj("B", b)
        djm.unit_uv(pane)
        assign(pane, g)
        return [pane]
    return A, B


def registry():
    return {
        "TimberDark": lambda: timber_shapes("M_DJ_TimberDark", "TimberDark", "TimberDarkEnd"),
        "TimberAged": lambda: timber_shapes("M_DJ_TimberAged", "TimberAged", "TimberAgedEnd"),
        "Granite": lambda: stone_shapes("M_DJ_Granite", "Granite"),
        "GraniteRubble": lambda: stone_shapes("M_DJ_GraniteRubble", "GraniteRubble", rubble=True),
        "Iron": lambda: sphere_block("M_DJ_Iron", "Iron", "strap", tri=False),
        "Rope": rope_shapes,
        "PlasterCream": lambda: sphere_block("M_DJ_PlasterCream", "PlasterCream", "wall"),
        "PlasterEarth": lambda: sphere_block("M_DJ_PlasterEarth", "PlasterEarth", "wall"),
        "RoofTile": lambda: sphere_block("M_DJ_RoofTile", "RoofTile", "block"),
        "Lacquer": lambda: sphere_block("M_DJ_Lacquer", "Lacquer", "barrel", tri=False),
        "GlassAmber": lambda: glass_shapes("M_DJ_GlassAmber"),
        "VendingPanel": vending_shapes,
    }


def render_shape(mat_key, which, build, info):
    for light in ("studio", "sunset"):
        reset()
        setup_render(-0.8 if light == "studio" else -0.4)
        objs = build()
        bpy.context.view_layer.update()
        # a proxy bounds object for framing = the union of objs
        pts = []
        for o in objs:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        me = bpy.data.meshes.new("Bounds")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((lo.x + (v.co.x + 0.5) * (hi.x - lo.x), lo.y + (v.co.y + 0.5) * (hi.y - lo.y),
                           lo.z + (v.co.z + 0.5) * (hi.z - lo.z)))
        bm.to_mesh(me)
        bm.free()
        bo = new_obj("Bounds", me)
        bo.hide_render = True
        elev = 18.0 if mat_key in ("GlassAmber", "VendingPanel") else 24.0
        azim = -75.0 if mat_key in ("GlassAmber", "VendingPanel") else -58.0
        _, ctr = camera_for(bo, elev=elev, azim=azim)
        if light == "studio":
            studio_rig(ctr)
        else:
            sunset_rig()
        catcher()
        path = OUT / f"{mat_key}_{which}_{light}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        info.setdefault(mat_key, {})[f"{which}_{light}"] = {"file": path.name, "objects": [o.name for o in objs]}
        if which in ("A", "B") and light == "studio":
            for o in objs:
                if o.type == "MESH" and o.data.uv_layers and o.data.materials and o.data.materials[0] \
                        and o.data.materials[0].get("dj_set") and djm.tg.SETS[o.data.materials[0]["dj_set"]]["tile_m"]:
                    try:
                        info[mat_key].setdefault("texel", {})[o.name] = djm.texel_density(o)
                    except Exception as ex:  # noqa: BLE001
                        info[mat_key].setdefault("texel", {})[o.name] = str(ex)
                if o.type == "MESH" and "Wear" in o.data.color_attributes:
                    ca = o.data.color_attributes["Wear"].data
                    S = o.matrix_world.to_3x3()
                    tot = g = 0.0
                    for poly in o.data.polygons:
                        a = poly.area * abs(S.determinant()) ** (2 / 3)
                        tot += a
                        if ca[poly.loop_indices[0]].color[1] > 0.5:
                            g += a
                    info[mat_key].setdefault("wear_G_area_share", {})[o.name] = round(g / max(tot, 1e-9), 3)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"round": ROUND, "samples": SAMPLES, "res": RES, "library": djm.VERSION}
    for key, mk in registry().items():
        if ONLY and key not in ONLY:
            continue
        for which in ("A", "B"):
            def build(mk=mk, which=which):
                A, B = mk()
                return A() if which == "A" else B()
            render_shape(key, which, build, info)
            print("DONE", key, which, flush=True)
    p = OUT / "shapes.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(info)
    p.write_text(json.dumps(old, indent=1), encoding="utf-8")


main()
