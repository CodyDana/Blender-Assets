"""Shared scene helpers for the BlackCloak_MH_v2 measurement tools (Blender 5.2, headless).

Conventions (all tools):
* World = the fitting body's frame: metres, Z up, the character faces -Y, his RIGHT is -X (viewer-left in a front view).
* The locked fitting body is APPENDED read-only through Scripts/pipeline/garment_helpers.append_fitbody (hash checked);
  nothing here ever saves a .blend.
* The garment measured is always the SHIPPED FBX (Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx) with its
  exported textures, re-bound to the fitting body's armature (same bone names, same rest pose).
* Renders: Cycles, view transform Standard, look None, exposure 0; a white Lambertian card (albedo 1, roughness 1, no
  specular) at the garment's chest, facing the camera, is calibrated to read 0.90 linear by scaling all lights + world.
"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
SCRIPTS = ROOT + "/Scripts"
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
REF_PHOTO = ROOT + "/References/BlackCloak/blackcloak.png"
REF_W, REF_H = 417, 674
EXPORT_DIR = ROOT + "/Exports/Garments/BlackCloak_MH_v2"
DEFAULT_FBX = EXPORT_DIR + "/SK_BlackCloak_MH_v2.fbx"
SPEC_OUT = ROOT + "/WorkFiles/BlackCloak_MH_v2/spec/out"

# The drape / look pose (arms hanging at the sides). Same aims as the male review's Blender capture
# (WorkFiles/BlackCloak_Review/male/blender/scripts/common.py pose_arms_down), written as garment_qa pose ops so
# garment_qa.apply_pose sets it: upper arm ~9 deg off vertical, forearm ~14 deg forward, hands beside the thighs.
ARMS_DOWN_V2 = [
    ("aim", "upperarm_l", "lowerarm_l", (0.16, 0.02, -1.0)), ("aim", "upperarm_r", "lowerarm_r", (-0.16, 0.02, -1.0)),
    ("aim", "lowerarm_l", "hand_l", (0.10, -0.22, -1.0)), ("aim", "lowerarm_r", "hand_r", (-0.10, -0.22, -1.0)),
]

# Camera definitions (see TARGET_SPEC.md section 6). fidelity-style camera: sensor_fit VERTICAL, sensor 24 mm,
# position = target + dist * (sin yaw cos pitch, -cos yaw cos pitch, sin pitch); yaw > 0 moves the camera to HIS LEFT (+X).
VIEWS = {
    # photo camera (camfit_lod0.json refit for the male): straight-on product view, frame = garment bbox * 1.08
    "photo": {"focal": 100.0, "yaw": 0.0, "pitch": 0.0, "frame": "garment", "res": (REF_W, REF_H)},
    # Jin-like framing: slightly to his left, a touch above, head top .. mid-thigh (z 1.908 .. 0.808), 2:3 portrait
    "jin": {"focal": 85.0, "yaw": 12.0, "pitch": 3.0, "target": (0.0, 0.0, 1.358), "span_m": 1.10, "res": (605, 908)},
    "front": {"focal": 85.0, "yaw": 0.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "q34": {"focal": 85.0, "yaw": -40.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "q34_other": {"focal": 85.0, "yaw": 40.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "side_r": {"focal": 85.0, "yaw": -90.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "side_l": {"focal": 85.0, "yaw": 90.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "back": {"focal": 85.0, "yaw": 180.0, "pitch": 0.0, "target": (0.0, 0.0, 0.95), "span_m": 2.02, "res": (600, 900)},
    "face": {"focal": 85.0, "yaw": 12.0, "pitch": 3.0, "target": (0.0, -0.05, 1.66), "span_m": 0.42, "res": (600, 600)},
    "hem": {"focal": 85.0, "yaw": 0.0, "pitch": 8.0, "target": (0.0, -0.1, 0.12), "span_m": 0.45, "res": (900, 600)},
}


def log(*a):
    print("V2M", *a, flush=True)


def fitbody(verify=True):
    """Append the locked fitting body (read-only, hash-checked) into the current empty scene."""
    from pipeline import garment_helpers as gh
    for n in ("Cube", "Light", "Camera"):      # factory-startup defaults
        if bpy.data.objects.get(n) is not None:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    fit = gh.append_fitbody(verify_file=verify)
    return fit


def drop_haircards():
    for o in list(bpy.data.objects):
        if o.name.endswith("HairCards"):
            bpy.data.objects.remove(o, do_unlink=True)


def import_garment(fbx, arm):
    """Import the shipped FBX, delete its armature and re-bind its meshes to the fitting body's ``root``."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx, use_custom_normals=True, automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    mws = {o.name: o.matrix_world.copy() for o in meshes}
    drop = [o.name for o in new if o.type in ("ARMATURE", "EMPTY")]
    for n in drop:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    for o in meshes:
        mw = mws[o.name]
        o.parent = arm; o.matrix_world = mw
        mods = [m for m in o.modifiers if m.type == "ARMATURE"]
        if not mods:
            mods = [o.modifiers.new("Armature", "ARMATURE")]
        for m in mods:
            m.object = arm
    bpy.context.view_layer.update()
    return meshes


def apply_pose(arm, ops):
    from pipeline import garment_qa as gq
    if ops:
        gq.apply_pose(arm, ops)
    else:
        gq.clear_pose(arm)
    bpy.context.view_layer.update()


def evaluated_coords(obj):
    dg = bpy.context.evaluated_depsgraph_get(); e = obj.evaluated_get(dg); me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
    M = np.array(obj.matrix_world); a = a @ M[:3, :3].T + M[:3, 3]
    polys = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return a, polys


def bake_static(obj, name=None):
    """Evaluated (posed) copy of a mesh as a static object (for collision / BVH / renders)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    me.transform(obj.matrix_world)
    ob = bpy.data.objects.new(name or (obj.name + "_STATIC"), me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bbox_of(objs):
    pts = np.concatenate([evaluated_coords(o)[0] for o in objs])
    return pts.min(0), pts.max(0)


def make_camera(view, garment_objs=None, overrides=None):
    v = dict(VIEWS[view]); v.update(overrides or {})
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.name.startswith("V2M_Cam"):
            bpy.data.objects.remove(o, do_unlink=True)
    cam = bpy.data.cameras.new("V2M_Cam"); cam.lens = v["focal"]; cam.sensor_fit = "VERTICAL"; cam.sensor_height = 24
    cam.clip_start = 0.05; cam.clip_end = 200
    co = bpy.data.objects.new("V2M_Cam", cam); sc.collection.objects.link(co)
    if v.get("frame") == "garment":
        lo, hi = bbox_of(garment_objs)
        tgt = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)); Hh = hi[2] - lo[2]
        dist = (Hh / 2 * 1.08) / (12.0 / v["focal"])
    else:
        tgt = Vector(v["target"]); dist = v["span_m"] / (24.0 / v["focal"])
    y, p = math.radians(v["yaw"]), math.radians(v["pitch"])
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    co.location = tgt + d
    co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = v["res"]; sc.render.resolution_percentage = 100
    v.update({"target_used": list(tgt), "dist_m": dist, "cam_loc": list(co.location)})
    return co, v


def lights(yaw_deg, centre=(0.0, 0.0, 1.0)):
    """Product-studio rig of the male review (key / fill ride with the camera yaw, top light, white world)."""
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.name.startswith("V2M_L_"):
            bpy.data.objects.remove(o, do_unlink=True)
    w = bpy.data.worlds.new("V2M_World"); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 4.0
    c = Vector(centre); yr = math.radians(yaw_deg)
    def rot(v): return Vector((v.x * math.cos(yr) - v.y * math.sin(yr), v.x * math.sin(yr) + v.y * math.cos(yr), v.z))
    out = []
    def area(name, loc, size, power, aim):
        l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size = size; l.size_y = size; l.energy = power
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); out.append(o)
    area("V2M_L_Key", c + rot(Vector((-1.6, -3.0, 1.4))), 3.0, 1000, c)
    area("V2M_L_Fill", c + rot(Vector((1.9, -2.8, 0.5))), 3.0, 350, c)
    area("V2M_L_Top", c + Vector((0, 0, 3.0)), 2.5, 400, Vector((0, 0, 0)))
    return out


def cycles_setup(samples=256):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    dev = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"; prefs.get_devices()
        for d in prefs.devices: d.use = (d.type == "OPTIX")
        sc.cycles.device = "GPU"; dev = "OPTIX"
    except Exception as e:
        dev = "CPU (%s)" % e
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 8
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "16"
    return dev


def calibrate_white(cam, card_at, tmpdir, target=0.90):
    """Scale lights + world so an albedo-1 Lambertian card at ``card_at`` facing the camera reads ``target`` (linear)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    hidden = {}
    for o in sc.objects:
        if o.type in ("MESH", "CURVE"):
            hidden[o.name] = o.hide_render; o.hide_render = True
    me = bpy.data.meshes.new("V2M_Card"); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.15); bm.to_mesh(me); bm.free()
    card = bpy.data.objects.new("V2M_Card", me); sc.collection.objects.link(card)
    m = bpy.data.materials.new("V2M_White"); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1); b.inputs["Roughness"].default_value = 1.0; b.inputs["Specular IOR Level"].default_value = 0.0
    me.materials.append(m)
    card.location = Vector(card_at); card.rotation_euler = (cam.location - card.location).to_track_quat("Z", "Y").to_euler()
    rx, ry, spp, ff, cd, ex = sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples, sc.render.image_settings.file_format, sc.render.image_settings.color_depth, sc.view_settings.exposure
    sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
    sc.render.resolution_x, sc.render.resolution_y = 96, 144; sc.cycles.samples = 64
    p = os.path.join(tmpdir, "_v2m_cal.exr"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(p); a = np.array(im.pixels[:]).reshape(144, 96, 4)[::-1]; bpy.data.images.remove(im); os.remove(p)
    pc = world_to_camera_view(sc, cam, card.location); cx, cy = int(pc.x * 96), int((1 - pc.y) * 144)
    val = float(a[cy - 2:cy + 3, cx - 2:cx + 3, :3].mean())
    k = target / max(val, 1e-9)
    for o in sc.objects:
        if o.type == "LIGHT": o.data.energy *= k
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs[1].default_value *= k
    bpy.data.objects.remove(card, do_unlink=True)
    for n, h in hidden.items():
        if n in sc.objects: sc.objects[n].hide_render = h
    sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples = rx, ry, spp
    sc.render.image_settings.file_format = ff; sc.render.image_settings.color_depth = cd
    return {"card_linear_before": val, "light_scale": k, "target": target, "view_transform": "Standard"}


# ------------------------------------------------------------------ shipped-material replica
def _find_tex(tex_dir, keys):
    if not tex_dir or not os.path.isdir(tex_dir): return None
    files = sorted(os.listdir(tex_dir))
    for k in keys:
        for f in files:
            if k.lower() in f.lower() and f.lower().endswith((".png", ".tga", ".exr", ".jpg")):
                return os.path.join(tex_dir, f)
    return None


def shipped_material(slot_name, tex_dir, params):
    """Blender replica of one exported slot, driven by <export>.material_params.json when present.
    params (per slot, all optional): base_color_tex, orm_tex, normal_tex (DirectX on disk), opacity_tex, uv_scale,
    base_tint_linear [r,g,b], roughness_mult, sheen_weight, sheen_tint, sheen_roughness, specular, metallic, normal_strength,
    detail_normal_tex, detail_uv_scale, opacity_clip. Missing params -> name-pattern textures + plain dielectric."""
    p = dict(params.get(slot_name, params.get(slot_name.replace("_Sim", ""), {}))) if params else {}
    m = bpy.data.materials.new("V2M_" + slot_name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    def tex(path, cs):
        if not path: return None
        if not os.path.isabs(path): path = os.path.join(tex_dir, path)
        if not os.path.exists(path): return None
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.image.colorspace_settings.name = cs
        return t
    hard = "clasp" in slot_name.lower() or "button" in slot_name.lower()
    base_keys = ["Clasp_BC", "Clasp_Base"] if hard else ["Cloth_BC", "_BC", "BaseColor"]
    bc = tex(p.get("base_color_tex") or _find_tex(tex_dir, base_keys), "sRGB")
    orm = tex(p.get("orm_tex") or _find_tex(tex_dir, ["Clasp_ORM"] if hard else ["Cloth_ORM", "_ORM"]), "Non-Color")
    nrm = tex(p.get("normal_tex") or _find_tex(tex_dir, ["Clasp_N"] if hard else ["Cloth_N", "Normal_DirectX", "_N."]), "Non-Color")
    opa = tex(p.get("opacity_tex"), "Non-Color")
    uv = N.new("ShaderNodeUVMap"); uv.uv_map = p.get("uv_map", "")
    sc_ = N.new("ShaderNodeVectorMath"); sc_.operation = "SCALE"; sc_.inputs["Scale"].default_value = float(p.get("uv_scale", 1.0))
    L.new(uv.outputs[0], sc_.inputs[0])
    for t in (bc, orm, nrm, opa):
        if t: L.new(sc_.outputs[0], t.inputs[0])
    tint = p.get("base_tint_linear")
    if bc:
        if tint:
            mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 1.0
            L.new(bc.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = tuple(tint) + (1,)
            L.new(mix.outputs[2], bs.inputs["Base Color"])
        else:
            L.new(bc.outputs[0], bs.inputs["Base Color"])
    elif tint:
        bs.inputs["Base Color"].default_value = tuple(tint) + (1,)
    else:
        bs.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1) if hard else (0.017, 0.0165, 0.016, 1)
    if orm:
        sep = N.new("ShaderNodeSeparateColor"); L.new(orm.outputs[0], sep.inputs[0])
        rm = N.new("ShaderNodeMath"); rm.operation = "MULTIPLY"; rm.use_clamp = True; rm.inputs[1].default_value = float(p.get("roughness_mult", 1.0))
        L.new(sep.outputs[1], rm.inputs[0]); L.new(rm.outputs[0], bs.inputs["Roughness"])
        L.new(sep.outputs[2], bs.inputs["Metallic"])
    else:
        bs.inputs["Roughness"].default_value = float(p.get("roughness", 0.3 if hard else 0.9))
        bs.inputs["Metallic"].default_value = float(p.get("metallic", 0.0))
    if nrm:
        # DirectX on disk -> flip green for Blender (OpenGL)
        sep = N.new("ShaderNodeSeparateColor"); L.new(nrm.outputs[0], sep.inputs[0])
        inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; L.new(sep.outputs[1], inv.inputs[1])
        com = N.new("ShaderNodeCombineColor"); L.new(sep.outputs[0], com.inputs[0]); L.new(inv.outputs[0], com.inputs[1]); L.new(sep.outputs[2], com.inputs[2])
        nm = N.new("ShaderNodeNormalMap"); nm.uv_map = p.get("uv_map", ""); nm.inputs["Strength"].default_value = float(p.get("normal_strength", 1.0))
        L.new(com.outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], bs.inputs["Normal"])
    bs.inputs["Specular IOR Level"].default_value = float(p.get("specular", 0.5 if hard else 0.35))
    if p.get("sheen_weight") is not None or not hard:
        bs.inputs["Sheen Weight"].default_value = float(p.get("sheen_weight", 0.0))
        bs.inputs["Sheen Tint"].default_value = tuple(p.get("sheen_tint", (1, 1, 1))) + (1,)
        bs.inputs["Sheen Roughness"].default_value = float(p.get("sheen_roughness", 0.5))
    if opa:
        sep = N.new("ShaderNodeSeparateColor"); L.new(opa.outputs[0], sep.inputs[0])
        L.new(sep.outputs[0], bs.inputs["Alpha"])
        try:
            m.surface_render_method = "DITHERED"
        except Exception:
            pass
    return m, {"slot": slot_name, "params_used": p, "base_color": bc.image.filepath if bc else None, "orm": orm.image.filepath if orm else None,
               "normal": nrm.image.filepath if nrm else None, "opacity": opa.image.filepath if opa else None}


def assign_shipped_materials(meshes, tex_dir, params_path=None):
    params = json.load(open(params_path)) if params_path and os.path.exists(params_path) else {}
    params = params.get("slots", params)
    rec = []; cache = {}
    for o in meshes:
        for s in o.material_slots:
            n = s.material.name if s.material else "unnamed"
            if n not in cache:
                cache[n], r = shipped_material(n, tex_dir, params); rec.append(r)
            s.material = cache[n]
    return rec


def region_colour_body(fit):
    """Copies of the (posed) body / head with a flat per-region colour for Workbench ID renders.
    torso = red, leg = yellow, arm = green, neck = magenta, head = blue."""
    from pipeline import garment_qa as gq
    col = {"torso": (1, 0, 0, 1), "leg": (1, 1, 0, 1), "arm": (0, 1, 0, 1), "neck": (1, 0, 1, 1), "head": (0, 0, 1, 1)}
    out = []
    for key in ("body", "head"):
        o = fit[key]; reg = gq.dominant_regions(o)
        st = bake_static(o, "V2M_ID_" + key)
        ca = st.data.color_attributes.new("V2M_ID", "FLOAT_COLOR", "POINT")
        for i, r in enumerate(reg):
            ca.data[i].color = col.get(r, (1, 0, 0, 1))
        st.data.color_attributes.active_color = ca
        out.append(st)
    return out


def workbench_id_render(path, garment_meshes, body_ids, garment_colour=(0, 0, 0, 1)):
    """Flat unlit ID render: garment black, body regions coloured (region_colour_body), background transparent."""
    sc = bpy.context.scene
    eng = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading; sh.light = "FLAT"; sh.color_type = "VERTEX"
    sh.show_cavity = False; sh.show_shadows = False; sh.show_specular_highlight = False; sh.show_object_outline = False
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    for o in garment_meshes:
        me = o.data
        ca = me.color_attributes.get("V2M_ID") or me.color_attributes.new("V2M_ID", "FLOAT_COLOR", "POINT")
        for i in range(len(ca.data)): ca.data[i].color = garment_colour
        me.color_attributes.active_color = ca
    for o in body_ids: o.hide_render = False
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
    sc.render.engine = eng


def project(cam, pts):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; W, H = sc.render.resolution_x, sc.render.resolution_y
    out = []
    for p in pts:
        c = world_to_camera_view(sc, cam, Vector(p)); out.append([c.x * W, (1 - c.y) * H, c.z])
    return out
