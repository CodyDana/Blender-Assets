"""t3 (2026-10-02): fix round 3 review renders (same views as t2) (--photo: the same views under a photo-studio light, dark
surround and small softboxes like the user's photo, written as *_photo.png) of the taiko (Assets/Dojo/Taiko.blend, never saved).

  drum_front_standing.png : the drum standing on a head like the user's reference photo, camera ~9 deg above the
                            body centre, ring handle to the camera
  closeup_tack_band.png   : the head-side tack band, same orientation
  set_34.png              : the assembled set (stand, drum, both sticks) 3/4
  closeup_saddle.png      : (the user's stand question) the cradle saddle under the drum, from the outer end

Run: blender -b -t 4 --factory-startup Assets/Dojo/Taiko.blend --python render_t1.py -- [--samples 128] [--only a,b]
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t3"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PHOTO = "--photo" in ARGS   # t2: a photo-studio variant (dark surround, small softboxes) for the side-by-side
SAMPLES = int(ARGS[ARGS.index("--samples") + 1]) if "--samples" in ARGS else 128
ONLY = (ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS
        else ["front", "band", "set", "saddle", "standend", "saddlefelt"])

sc = bpy.context.scene
for c in list(sc.collection.children):
    c.hide_render = True
    c.hide_viewport = True


def setup_cycles():
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        print("GPU setup failed, CPU render:", exc)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.sample_clamp_indirect = 5.0
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.3
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True


def flat_mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def studio(coll):
    w = bpy.data.worlds.new("Studio")
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (0.75, 0.75, 0.76, 1)
    bgn.inputs["Strength"].default_value = 0.15 if PHOTO else 0.7
    sc.world = w
    me = bpy.data.meshes.new("Floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat_mat("MAT_Floor", (0.8, 0.8, 0.8)))
    fl = bpy.data.objects.new("Floor", me)
    coll.objects.link(fl)
    fl.is_shadow_catcher = True
    for name, loc, power, size in (("Key", (-3.0, -5.0, 5.0), 700.0, 4.0), ("Fill", (4.0, -4.0, 2.5), 300.0, 4.0),
                                   ("Top", (0.5, 1.5, 6.0), 250.0, 5.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power * (1.6 if PHOTO else 1.0)
        ld.size = 0.8 if PHOTO else size
        ld.color = (1.0, 0.98, 0.95)
        o = bpy.data.objects.new(name, ld)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(o)


def camera(name, loc, target, lens):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.clip_start = 0.01
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(o)
    return o


def render(cam, name, res):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(OUT / (name.replace(".png", "_photo.png") if PHOTO else name))
    bpy.ops.render.render(write_still=True)
    print("rendered", OUT / name)


setup_cycles()
st = bpy.data.collections.new("T1Studio")
sc.collection.children.link(st)
studio(st)
drum_me = bpy.data.objects["SM_DKP_Taiko_Drum"].data

# ---- the drum standing on its -X head (axis vertical, +X up), ring handle on -Y facing the camera
standing = bpy.data.collections.new("T1Standing")
sc.collection.children.link(standing)
od = bpy.data.objects.new("DrumStanding", drum_me)
od.matrix_world = Matrix.Translation((0, 0, 0.777)) @ Matrix.Rotation(math.radians(-90), 4, "Y")
standing.objects.link(od)

# ---- the assembled set re-based to the origin (stand base centre at 0), from the Taiko_Layout instances
setc = bpy.data.collections.new("T1Set")
sc.collection.children.link(setc)
lay = bpy.data.collections["Taiko_Layout"]
stand_inst = next(o for o in lay.objects if o.data.name.startswith("SM_DKP_Taiko_Stand"))
inv = stand_inst.matrix_world.inverted()
for o in lay.objects:
    c = bpy.data.objects.new("T1_" + o.name, o.data)
    c.matrix_world = inv @ o.matrix_world
    setc.objects.link(c)

ang = math.radians(9.0)
if "front" in ONLY:
    setc.hide_render = True
    standing.hide_render = False
    D = 3.0
    a2 = math.radians(15.0)     # the reference shows the top head as a clear ellipse: a closer, higher camera
    tgt = (0, 0, 0.76)
    cam = camera("CAM_Front", (0, -D * math.cos(a2), 0.76 + D * math.sin(a2)), tgt, 50)
    render(cam, "drum_front_standing.png", (1024, 1024))
if "band" in ONLY:
    setc.hide_render = True
    standing.hide_render = False
    zb = 0.777 + 0.678
    tgt = (0.0, -0.53, zb - 0.01)
    D = 0.95
    cam = camera("CAM_Band", (0.0, -0.53 - D * math.cos(ang), zb - 0.01 + D * math.sin(ang)), tgt, 60)
    render(cam, "closeup_tack_band.png", (1200, 800))
    if "--nohl" in ARGS:
        # t3: the same view with the lights hidden from glossy rays: the difference to the beauty is the lights'
        # specular highlights (excluded from the judge's darkness test)
        for o in st.objects:
            if o.type == "LIGHT":
                o.visible_glossy = False
        sc.render.filepath = str(OUT / ("closeup_tack_band_nohl%s.png" % ("_photo" if PHOTO else "")))
        bpy.ops.render.render(write_still=True)
        for o in st.objects:
            if o.type == "LIGHT":
                o.visible_glossy = True
        print("rendered nohl")
    if "--mask" in ARGS:
        # t3: a tack mask for the darkness test (white = tack faces: hide-atlas faces below the lip, |x| < 0.745)
        mme = drum_me.copy()
        mme.materials.clear()
        mw = bpy.data.materials.new("MASK_W")
        mw.use_nodes = True
        nt = mw.node_tree
        for n_ in list(nt.nodes):
            nt.nodes.remove(n_)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        mo = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(em.outputs[0], mo.inputs[0])
        mk = mw.copy()
        mk.node_tree.nodes["Emission"].inputs["Color"].default_value = (0, 0, 0, 1)
        mme.materials.append(mk)
        mme.materials.append(mw)
        hide_i = [i for i, m in enumerate(drum_me.materials) if m.name == "M_DKP_Taiko_Hide"][0]
        for pl in mme.polygons:
            is_tack = (drum_me.polygons[pl.index].material_index == hide_i
                       and max(abs(mme.vertices[v].co.x) for v in pl.vertices) < 0.745)
            pl.material_index = 1 if is_tack else 0
        od.data = mme
        for o in st.objects:
            o.hide_render = True
        sc.world = None
        sc.cycles.samples = 16
        sc.cycles.use_denoising = False
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = 0.0
        sc.render.film_transparent = False
        sc.camera = cam
        sc.render.filepath = str(OUT / "closeup_tack_band_mask.png")
        bpy.ops.render.render(write_still=True)
        print("rendered mask")
if "set" in ONLY:
    standing.hide_render = True
    setc.hide_render = False
    az, el, D = math.radians(-38), math.radians(18), 5.2
    tgt = Vector((0, 0, 0.95))
    loc = tgt + Vector((D * math.cos(el) * math.sin(az), -D * math.cos(el) * math.cos(az), D * math.sin(el)))
    cam = camera("CAM_Set34", loc, tgt, 50)
    render(cam, "set_34.png", (1400, 1050))
if "saddle" in ONLY:
    standing.hide_render = True
    setc.hide_render = False
    # stand-local frame: the drum axis is X, the cradle beam spans x 0.46..0.58; look along -Y at the saddle's
    # outer half from just outside the post, low, so the drum-to-saddle gap shows against the background
    for o in setc.objects:      # the sticks lean at the +X/-Y corner; hide them for this view
        if o.data.name.startswith("SM_DKP_Taiko_Stick"):
            o.hide_render = True
    tgt = Vector((0.52, 0.10, 0.70))
    cam = camera("CAM_Saddle", (0.95, 0.95, 0.66), tgt, 50)
    render(cam, "closeup_saddle.png", (1200, 800))
if "standend" in ONLY:
    # the stand alone, orthographic from +X (end elevation): the cradle beams' concave saddle cut reads in silhouette
    standing.hide_render = True
    setc.hide_render = False
    for o in setc.objects:
        o.hide_render = not o.data.name.startswith("SM_DKP_Taiko_Stand")
    cd = bpy.data.cameras.new("CAM_StandEnd")
    cd.type = "ORTHO"
    cd.ortho_scale = 1.9
    cam = bpy.data.objects.new("CAM_StandEnd", cd)
    cam.location = (4.0, 0.0, 0.45)
    cam.rotation_euler = (Vector((0, 0, 0.45)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    render(cam, "stand_end_elevation.png", (1200, 800))

if "saddlefelt" in ONLY:
    # t2: the felt-lined, tapered seat of the +X cradle beam, stand only, from above the drum's place
    standing.hide_render = True
    setc.hide_render = False
    for o in setc.objects:
        o.hide_render = not o.data.name.startswith("SM_DKP_Taiko_Stand")
    cam = camera("CAM_SaddleFelt", (1.05, -0.95, 1.45), (0.52, 0.0, 0.72), 45)
    render(cam, "saddle_felt.png", (1200, 800))
