"""Gallery render rig shared by every form: hero, top (spec), wireframe, LOD strip.

Exposure is the whole ball game on a 0.9 metallic: rev 1 lit a blackened star with
four soft lamps against a near-white world and got a flat mid-grey card in the hero
and a near-black plate in the top view - a 3.2x difference in the same product across
two gallery images.  These constants were tuned against measurements taken from the
finished PNGs (see ``image_stats``), targeting a plate mid-tone of 0.10 to 0.20 in
*both* beauty shots with the brightness carried by specular hits.  Do not retune them
per form: one rig is what makes the pack's gallery read as one product line.

Gallery frames are 16:9 so they survive Fab's 1920x1080 thumbnail crop (study 7).

Maintenance pass (visual review), pack-wide:

* The beauty shots render from the BAKED textures only (shuriken_lib.bake), passed in as
  ``beauty_material``: what the gallery shows is what the maps carry.
* Rim walls.  A vertical metallic wall seen from 29 deg up mirrors the ground right next
  to the star, so the camera-facing walls and the far wall of the hole rendered as a
  pure-black ink band (10.8 % / 17.2 % of hero object pixels below 0.05), and the old
  ``rim_band`` metric (outer 4 px of the whole silhouette) averaged it away.  The hero now
  has a reflection card: an emissive disc lying on the ground under and around the star,
  invisible to camera, diffuse and shadow rays and emitting from its top face only, so
  the walls' glossy rays see a light-grey floor while the camera and the ground do not.
  The gate is a wall-only measurement: a second mask pass renders faces with
  |N.z| < 0.5 white (``wall_mask``), and ``WALL_GATE`` checks the hero wall p50 and the
  fraction of wall pixels that are near-black.
* Depth of field is solved, not guessed: the f-stop is the smallest (>= f/16) that keeps
  every vertex's circle of confusion within ``HERO_MAX_COC_PX`` (f/16 at 0.3 m smeared 5
  of the eight-point's 8 points, which are the selling detail).
* Composition: after the dolly fit, lens shift puts the projected bounding-box centre on
  ``HERO_CENTRE`` (the four-point used to sit 15 px off the bottom-left corner).
* The top (spec) view uses one pack-wide ortho frame, ``TOP_FRAME_HEIGHT`` tall, so every
  form is drawn at the same px/mm and the gallery reads to a common scale.
* Wireframe and LOD strip: one backdrop (the ground is hidden in both - it used to stay
  visible in the LOD strip), wires sized in pixels, no denoiser on flat emission shots
  (the smeared orange halo), and each LOD panel is labelled with its triangle count and
  screen-size range.
* ``load_pixels`` returns rows top-down, so ``bbox_px`` and the sector labels match the
  PNG (they were upside down).

Form-dependent inputs, and only these: the ground sits at -thickness/2, the LOD camera
frames the form's tip extents, the reflection card's radius follows the tip radius, and
the top view's lamp ring has the smallest multiple of n lamps that is >= 8 at constant
total power, so every arm of any C_n form is lit identically.

The rig is built after the .blend is saved and torn down after each form, so it never
reaches Assets/Shuriken.blend and every form renders from an identical starting state.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import bpy
import numpy as np
from mathutils import Matrix, Vector

from .spec import Outline

GROUND_COLOUR = (0.150, 0.149, 0.144)
GROUND_ROUGHNESS = 0.22 # glossy enough to bounce the rake strips back up into the rim walls
HERO_KEY_W = 1.15       # broad source in the camera's mirror direction: sets plate value (1.28 until the
                        # maintenance pass: the baked scratches and the wall card lifted the hero p50 past 0.20)
HERO_RAKE_A_W = 0.88    # grazing strip: makes the 0.9 mm ground facet read
HERO_RAKE_B_W = 0.68
HERO_FILL_W = 2.20      # lifts the 3 mm rim wall off black
HERO_BOUNCE_W = 1.60    # low card on the camera side: the near rim wall, not an ink outline
TOP_DOME_W = 5.40       # axial soft box: the only thing a flat plate mirrors straight up
TOP_RING_W = 0.22       # per lamp of the 8-lamp ring (scaled to keep total power for other counts)
TOP_RING_BASE = 8
LOD_STRIP_GAP = 0.021   # m between neighbours in the LOD strip (rev 2: 0.118 m pitch for 97 mm)
SHOT_SUFFIXES = ("persp", "top", "wire", "lods")

# Reflection card for the rim walls (hero only): radiance of its top face, and its reach.
WALL_CARD_STRENGTH = 0.9
WALL_CARD_COLOUR = (0.88, 0.90, 0.94)
WALL_CARD_MARGIN = 0.040          # m beyond the tip circle
WALL_CARD_LIFT = 0.00005          # m above the ground plane
# Wall gate (hero): stored-sRGB Rec.709 luma of pixels on faces with |N.z| < 0.5.
WALL_GATE = {"p50_min": 0.06, "dark_below": 0.03, "dark_fraction_max": 0.05}
PLATE_BAND = (0.10, 0.20)         # object p50 target of both beauty shots
HERO_CENTRE = (0.5, 0.47)         # camera-view coordinates (y up): 0.53 of the height from the top
HERO_MAX_COC_PX = 1.5
HERO_MIN_FSTOP = 16.0
TOP_FRAME_HEIGHT = 0.130          # m: fits a 108 mm senban diagonal at 0.83 of the height
WIRE_PX = 1.1                     # wire width in output pixels
LABEL_COLOUR = (0.80, 0.80, 0.78)


def _aim(obj, target=(0.0, 0.0, 0.0)) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _polar(distance: float, elevation_deg: float, azimuth_deg: float):
    elevation = math.radians(elevation_deg)
    azimuth = math.radians(azimuth_deg)
    return (distance * math.cos(elevation) * math.cos(azimuth),
            distance * math.cos(elevation) * math.sin(azimuth),
            distance * math.sin(elevation))


def _emission(name: str, colour, strength: float):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*colour, 1.0)
    emit.inputs["Strength"].default_value = strength
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _ground_material():
    """Dark, faintly reflective sweep: the star has to sit on something."""
    mat = bpy.data.materials.new("M_Preview_Ground")
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*GROUND_COLOUR, 1.0)
    bsdf.inputs["Roughness"].default_value = GROUND_ROUGHNESS
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _wall_card_material():
    """Emits from the top face only (the walls look down at it); the underside is transparent."""
    mat = bpy.data.materials.new("M_Preview_WallCard")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    geom = tree.nodes.new("ShaderNodeNewGeometry")
    mix = tree.nodes.new("ShaderNodeMixShader")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*WALL_CARD_COLOUR, 1.0)
    emit.inputs["Strength"].default_value = WALL_CARD_STRENGTH
    clear = tree.nodes.new("ShaderNodeBsdfTransparent")
    tree.links.new(geom.outputs["Backfacing"], mix.inputs["Fac"])
    tree.links.new(emit.outputs["Emission"], mix.inputs[1])
    tree.links.new(clear.outputs["BSDF"], mix.inputs[2])
    tree.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.cycles.emission_sampling = "NONE"   # found by glossy rays only, never light-sampled
    except (AttributeError, TypeError):         # pragma: no cover
        pass
    return mat


def _wall_mask_material():
    """Mask pass: white on faces with |N.z| < 0.5 (walls, steep facet segments), black elsewhere."""
    mat = bpy.data.materials.new("M_Preview_WallMask")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    geom = tree.nodes.new("ShaderNodeNewGeometry")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    absz = tree.nodes.new("ShaderNodeMath")
    absz.operation = "ABSOLUTE"
    less = tree.nodes.new("ShaderNodeMath")
    less.operation = "LESS_THAN"
    less.inputs[1].default_value = 0.5
    emit = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(geom.outputs["True Normal"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], absz.inputs[0])
    tree.links.new(absz.outputs["Value"], less.inputs[0])
    tree.links.new(less.outputs["Value"], emit.inputs["Color"])
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def setup_render(samples: int, res_x: int, res_y: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = (device.type == "OPTIX")
        scene.cycles.device = "GPU"
    except Exception as exc:                                   # pragma: no cover
        print(f"[render] OPTIX unavailable, falling back to CPU: {exc}")
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    for transform in ("Khronos PBR Neutral", "Standard"):
        try:
            scene.view_settings.view_transform = transform
            break
        except Exception:
            continue

    # A metal shows only what it reflects, so the world carries a real value ramp
    # instead of one flat grey: dark below the horizon, a brighter band above it.
    world = bpy.data.worlds.new("W_Shuriken_Preview")
    scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputWorld")
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    coord = tree.nodes.new("ShaderNodeTexCoord")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    remap = tree.nodes.new("ShaderNodeMapRange")
    remap.inputs["From Min"].default_value = -1.0
    remap.inputs["From Max"].default_value = 1.0
    tree.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], remap.inputs["Value"])
    tree.links.new(remap.outputs["Result"], ramp.inputs["Fac"])
    elements = ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.006, 0.006, 0.007, 1.0)
    elements[1].position = 0.52
    elements[1].color = (0.020, 0.020, 0.022, 1.0)
    third = ramp.color_ramp.elements.new(0.70)
    third.color = (0.085, 0.086, 0.092, 1.0)
    fourth = ramp.color_ramp.elements.new(1.0)
    fourth.color = (0.045, 0.046, 0.050, 1.0)
    tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])


def _strip(coll, name: str, location, size_x: float, size_y: float, power: float, light_scale: float,
           colour=(1.0, 0.97, 0.93)):
    data = bpy.data.lights.new(name, type="AREA")
    data.shape = "RECTANGLE"
    data.size = size_x
    data.size_y = size_y
    data.energy = power * light_scale
    data.color = colour
    light = bpy.data.objects.new(name, data)
    coll.objects.link(light)
    light.location = location
    _aim(light)
    return light


def _wall_card(coll, o: Outline):
    """Camera-invisible emissive disc on the ground: what the rim walls mirror (hero only)."""
    radius = o.r_tip + WALL_CARD_MARGIN
    segments = 96
    verts = [(0.0, 0.0, 0.0)] + [(radius * math.cos(2 * math.pi * k / segments),
                                  radius * math.sin(2 * math.pi * k / segments), 0.0) for k in range(segments)]
    faces = [(0, 1 + k, 1 + (k + 1) % segments) for k in range(segments)]
    mesh = bpy.data.meshes.new("PREVIEW_WallCard")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    card = bpy.data.objects.new("PREVIEW_WallCard", mesh)
    coll.objects.link(card)
    card.location = (0.0, 0.0, -o.half_t + WALL_CARD_LIFT)
    card.data.materials.append(_wall_card_material())
    card.visible_camera = False
    card.visible_diffuse = False
    card.visible_shadow = False
    card.visible_transmission = False
    card.visible_volume_scatter = False
    card.visible_glossy = True
    return card


def projected_bbox(camera, objects):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    xs, ys = [], []
    for obj in objects:
        matrix = obj.matrix_world
        for vert in obj.data.vertices:
            point = world_to_camera_view(scene, camera, matrix @ vert.co)
            xs.append(point.x)
            ys.append(point.y)
    return min(xs), max(xs), min(ys), max(ys)


def fit_perspective(camera, objects, frac_x: float, frac_y: float, steps: int = 12) -> None:
    """Dolly the camera until the subject fills the frame - no more 91% empty grey.

    ``matrix_world`` is lazy, so the view layer has to be updated inside the loop;
    without it every pass reads the same stale matrix, applies the same correction and
    walks the camera into the middle of the mesh.
    """
    bpy.context.view_layer.update()
    for _ in range(steps):
        x0, x1, y0, y1 = projected_bbox(camera, objects)
        scale = max((x1 - x0) / frac_x, (y1 - y0) / frac_y)
        if abs(scale - 1.0) < 0.002:
            break
        camera.location = camera.location * scale
        _aim(camera)
        bpy.context.view_layer.update()
    camera.data.dof.focus_distance = camera.location.length
    bpy.context.view_layer.update()


def centre_perspective(camera, objects, res_x: int, res_y: int, target=HERO_CENTRE, steps: int = 4) -> dict:
    """Lens-shift the frame so the projected bounding-box centre lands on ``target``.

    Shift is measured in units of the larger frame dimension (the width here), so a
    horizontal error moves ``shift_x`` one-for-one and a vertical one by height / width.
    """
    data = camera.data
    for _ in range(steps):
        bpy.context.view_layer.update()
        x0, x1, y0, y1 = projected_bbox(camera, objects)
        cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        data.shift_x += cx - target[0]
        data.shift_y += (cy - target[1]) * res_y / res_x
    bpy.context.view_layer.update()
    x0, x1, y0, y1 = projected_bbox(camera, objects)
    return {"shift": [round(data.shift_x, 6), round(data.shift_y, 6)],
            "bbox_centre": [round(0.5 * (x0 + x1), 5), round(0.5 * (y0 + y1), 5)],
            "margins_lrbt": [round(x0, 4), round(1.0 - x1, 4), round(y0, 4), round(1.0 - y1, 4)]}


def solve_depth_of_field(camera, objects, res_x: int, max_coc_px: float = HERO_MAX_COC_PX,
                         min_fstop: float = HERO_MIN_FSTOP) -> dict:
    """Smallest f-stop (>= ``min_fstop``) whose circle of confusion stays within ``max_coc_px``.

    Thin lens: c = (f / N) f |d - s| / (d (s - f)) on the sensor, for every vertex depth d
    along the view axis, focus s at the subject centre.
    """
    data = camera.data
    f = data.lens
    sensor = data.sensor_width
    view = camera.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    s = data.dof.focus_distance * 1000.0
    depths = [((obj.matrix_world @ v.co) - camera.location).dot(view) * 1000.0
              for obj in objects for v in obj.data.vertices]
    c_max = max_coc_px * sensor / res_x
    needed = max(f * f * abs(d - s) / (c_max * d * (s - f)) for d in depths)
    fstop = max(min_fstop, needed)
    data.dof.use_dof = True
    data.dof.aperture_fstop = fstop
    worst = max((f / fstop) * f * abs(d - s) / (d * (s - f)) for d in depths) * res_x / sensor
    return {"fstop": round(fstop, 3), "focus_mm": round(s, 3), "depth_range_mm": [round(min(depths), 3),
                                                                                  round(max(depths), 3)],
            "max_coc_px": round(worst, 3), "target_max_coc_px": max_coc_px}


def fit_ortho(camera, span_x: float, span_y: float, frac_x: float, frac_y: float,
              res_x: int, res_y: int) -> None:
    aspect = res_x / res_y
    if res_x >= res_y:
        camera.data.ortho_scale = max(span_x / frac_x, span_y / frac_y * aspect)
    else:
        camera.data.ortho_scale = max(span_x / frac_x / aspect, span_y / frac_y)


def ring_lamp_count(n: int) -> int:
    """Smallest multiple of n that is >= 8: an n-fold symmetric top ring."""
    return n * math.ceil(TOP_RING_BASE / n)


def build_preview_rig(o: Outline, res_x: int, res_y: int, light_scale: float = 1.0):
    """Ground, world-facing strip lights, the reflection card and the three cameras."""
    coll = bpy.data.collections.new("PREVIEW_RIG")
    bpy.context.scene.collection.children.link(coll)
    span_x, span_y = o.tip_extents()

    bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0.0, 0.0, -o.half_t))
    ground = bpy.context.object
    ground.name = "PREVIEW_Ground"
    ground.data.materials.append(_ground_material())
    for parent in list(ground.users_collection):
        parent.objects.unlink(ground)
    coll.objects.link(ground)
    card = _wall_card(coll, o)

    # --- hero rig.  One broad source in the camera's mirror direction sets the plate
    # value; two narrow grazing strips at ~8 deg rake the ground facet and the rim
    # wall, which is the only way either of them reads on a 0.9 metallic.
    hero = []
    hero.append(_strip(coll, "PREVIEW_HeroKey", _polar(0.62, 32.0, 158.0), 0.42, 0.075,
                       HERO_KEY_W, light_scale))
    hero.append(_strip(coll, "PREVIEW_HeroRakeA", _polar(0.34, 7.0, 96.0), 0.50, 0.022,
                       HERO_RAKE_A_W, light_scale, colour=(1.0, 0.96, 0.90)))
    hero.append(_strip(coll, "PREVIEW_HeroRakeB", _polar(0.34, 9.0, -146.0), 0.44, 0.022,
                       HERO_RAKE_B_W, light_scale, colour=(0.92, 0.95, 1.0)))
    hero.append(_strip(coll, "PREVIEW_HeroFill", _polar(0.40, 16.0, -34.0), 0.55, 0.55,
                       HERO_FILL_W, light_scale, colour=(0.88, 0.92, 1.0)))
    hero.append(_strip(coll, "PREVIEW_HeroBounce", _polar(0.30, 2.0, -22.0), 0.90, 0.30,
                       HERO_BOUNCE_W, light_scale, colour=(0.90, 0.93, 1.0)))

    # --- top rig.  The spec shot's only job is the outline, so it is lit with n-fold
    # symmetry: one axial soft box plus a lamp ring, which makes all arms identical
    # instead of the 9.2% top-to-bottom bias rev 1 shipped.
    top = [_strip(coll, "PREVIEW_TopDome", (0.0, 0.0, 0.80), 0.85, 0.85, TOP_DOME_W, light_scale)]
    count = ring_lamp_count(o.n)
    pitch = 360.0 / count
    ring_power = TOP_RING_W * TOP_RING_BASE / count
    for i in range(count):
        azimuth = 0.5 * pitch + pitch * i
        top.append(_strip(coll, f"PREVIEW_TopRing{i}", _polar(0.24, 13.0, azimuth),
                          0.16, 0.020, ring_power, light_scale))
    for light in hero + top:
        light.hide_render = True

    if max(span_x, span_y) > 0.92 * TOP_FRAME_HEIGHT:
        raise ValueError(f"form spans {max(span_x, span_y) * 1000:.1f} mm; the pack-wide top frame is "
                         f"{TOP_FRAME_HEIGHT * 1000:.0f} mm tall - raise TOP_FRAME_HEIGHT for every form")
    cam_top_data = bpy.data.cameras.new("PREVIEW_CamTop")
    cam_top_data.type = "ORTHO"
    cam_top = bpy.data.objects.new("PREVIEW_CamTop", cam_top_data)
    coll.objects.link(cam_top)
    cam_top.location = (0.0, 0.0, 0.30)
    cam_top.rotation_euler = (0.0, 0.0, 0.0)
    cam_top_data.ortho_scale = TOP_FRAME_HEIGHT * max(res_x, res_y) / min(res_x, res_y)

    cam_lod_data = bpy.data.cameras.new("PREVIEW_CamLod")
    cam_lod_data.type = "ORTHO"
    cam_lod = bpy.data.objects.new("PREVIEW_CamLod", cam_lod_data)
    coll.objects.link(cam_lod)
    cam_lod.location = (0.0, 0.0, 0.30)
    cam_lod.rotation_euler = (0.0, 0.0, 0.0)

    cam_persp_data = bpy.data.cameras.new("PREVIEW_CamPersp")
    cam_persp_data.lens = 72.0
    cam_persp_data.dof.use_dof = True
    cam_persp_data.dof.aperture_fstop = HERO_MIN_FSTOP
    cam_persp = bpy.data.objects.new("PREVIEW_CamPersp", cam_persp_data)
    coll.objects.link(cam_persp)
    cam_persp.location = _polar(0.30, 29.0, -22.0)
    _aim(cam_persp)
    return {"collection": coll, "ground": ground, "card": card, "hero_lights": hero, "top_lights": top,
            "cam_top": cam_top, "cam_persp": cam_persp, "cam_lod": cam_lod,
            "span_x": span_x, "span_y": span_y, "ring_lamps": count}


def wire_pair(source, coll, name: str, offset=(0.0, 0.0, 0.0), thickness: float = 0.00016):
    """Flat-lit copy plus a Wireframe-modifier copy floated just above it."""
    solid = source.copy()
    solid.data = source.data.copy()
    solid.name = f"PREVIEW_{name}Solid"
    solid.parent = None
    solid.matrix_world = Matrix.Translation(offset)
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(_emission(f"M_Preview_{name}Solid", (0.150, 0.162, 0.185), 1.0))

    wires = source.copy()
    wires.data = source.data.copy()
    wires.name = f"PREVIEW_{name}Lines"
    wires.parent = None
    wires.matrix_world = Matrix.Translation((offset[0], offset[1], offset[2] + 0.0006))
    coll.objects.link(wires)
    wires.data.materials.clear()
    wires.data.materials.append(_emission(f"M_Preview_{name}Lines", (1.0, 0.48, 0.14), 2.0))
    modifier = wires.modifiers.new("Wireframe", "WIREFRAME")
    modifier.thickness = thickness
    modifier.use_boundary = True
    modifier.use_even_offset = False   # even thickness spikes right off the tips
    modifier.use_replace = True
    return solid, wires


def label(coll, name: str, text: str, location, size: float):
    """Flat emissive text (Blender's built-in font), centred on ``location``."""
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "TOP"
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    obj.location = location
    obj.data.materials.append(_emission(f"M_{name}", LABEL_COLOUR, 1.0))
    return obj


def render_to(path: Path, camera) -> str:
    scene = bpy.context.scene
    scene.camera = camera
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path)


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Square-kernel binary dilation, done as two separable running maxima."""
    out = mask.copy()
    for axis in (0, 1):
        acc = out.copy()
        for shift in range(1, radius + 1):
            acc |= np.roll(out, shift, axis=axis)
            acc |= np.roll(out, -shift, axis=axis)
        out = acc
    return out


def load_pixels(path) -> np.ndarray:
    """(height, width, 4) raw stored values of a PNG, rows top-down as in the file.

    ``image.pixels`` returns raw stored values in Blender 5.2, bottom row first; the rows
    are flipped here so pixel coordinates (bbox_px, sector angles) match any image viewer.
    The colour space is forced to Non-Color so nothing is converted: these numbers are
    directly comparable to sampling the PNG with any other tool.
    """
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    width, height = img.size
    buf = np.empty(width * height * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(height, width, 4)[::-1]


def image_stats(beauty: Path, mask: Path, n: int = 4) -> dict:
    """Read a render back and report what a buyer will actually see.

    ``mask`` is the wall-mask pass: alpha is the subject's coverage, red is 1 on faces with
    |N.z| < 0.5 (walls and steep facet segments).
    """
    pixels = load_pixels(beauty)
    mask_px = load_pixels(mask)
    alpha = mask_px[..., 3]
    rgb = pixels[..., :3].astype(np.float64)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    selection = alpha > 0.85
    height, width = lum.shape
    stats = {
        "resolution": [int(width), int(height)],
        "object_pixel_fraction": round(float(selection.mean()), 5),
    }
    if selection.any():
        obj_lum = lum[selection]
        obj_rgb = rgb[selection]
        rows = np.any(selection, axis=1).nonzero()[0]
        cols = np.any(selection, axis=0).nonzero()[0]
        stats.update({
            "object_mean_rgb": [round(float(v), 4) for v in obj_rgb.mean(axis=0)],
            "object_luminance": {
                "mean": round(float(obj_lum.mean()), 4),
                "std": round(float(obj_lum.std()), 4),
                "p05": round(float(np.percentile(obj_lum, 5)), 4),
                "p50": round(float(np.percentile(obj_lum, 50)), 4),
                "p95": round(float(np.percentile(obj_lum, 95)), 4),
                "max": round(float(obj_lum.max()), 4),
            },
            "object_fraction_above_0_50": round(float((obj_lum > 0.50).mean()), 5),
            "object_fraction_below_0_05": round(float((obj_lum < 0.05).mean()), 5),
            "bbox_px": [int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())],
            "bbox_px_note": "left, top, right, bottom in image pixels, rows top-down",
            "bbox_margins_px_lrtb": [int(cols.min()), int(width - 1 - cols.max()), int(rows.min()),
                                     int(height - 1 - rows.max())],
            "bbox_width_fraction": round(float((cols.max() - cols.min() + 1) / width), 4),
            "bbox_height_fraction": round(float((rows.max() - rows.min() + 1) / height), 4),
        })
        walls = selection & (mask_px[..., 0] > 0.5)
        if walls.any():
            wall_lum = lum[walls]
            stats["wall_luminance"] = {
                "pixels": int(walls.sum()),
                "fraction_of_object": round(float(walls.sum() / selection.sum()), 5),
                "mean": round(float(wall_lum.mean()), 4),
                "p05": round(float(np.percentile(wall_lum, 5)), 4),
                "p50": round(float(np.percentile(wall_lum, 50)), 4),
                "p95": round(float(np.percentile(wall_lum, 95)), 4),
                "fraction_below_0_03": round(float((wall_lum < WALL_GATE["dark_below"]).mean()), 5),
                "fraction_below_0_05": round(float((wall_lum < 0.05).mean()), 5),
                "note": "pixels of faces with |N.z| < 0.5 (rim, notch and hole walls, steep facet segments)",
            }
        # Legacy silhouette band (outer 4 px of the whole silhouette).  Informational only:
        # it averages bright tips with black walls, which is how it passed an ink outline.
        eroded = selection.copy()
        for _ in range(4):
            step = eroded.copy()
            for axis in (0, 1):
                step &= np.roll(eroded, 1, axis=axis)
                step &= np.roll(eroded, -1, axis=axis)
            eroded = step
        rim = selection & ~eroded
        if rim.any():
            stats["silhouette_band_luminance"] = {
                "mean": round(float(lum[rim].mean()), 4),
                "p50": round(float(np.percentile(lum[rim], 50)), 4),
                "note": "outer 4 px of the silhouette; informational - the gate is wall_luminance",
            }
        # n-fold evenness: on a C_n object an unevenly lit spec shot shows n different
        # arms.  Sectors are taken about the subject centre, one centred on each arm in
        # the top view (arm 0 points right; rows are top-down, so image up is -row).
        yy, xx = np.nonzero(selection)
        cy, cx = 0.5 * (rows.min() + rows.max()), 0.5 * (cols.min() + cols.max())
        pitch = 360.0 / n
        angle = (np.degrees(np.arctan2(-(yy - cy), xx - cx)) + 360.0 + 0.5 * pitch) % 360.0
        labels = ("right", "up", "left", "down") if n == 4 else tuple(f"arm{i}" for i in range(n))
        sectors = {}
        for i, name in enumerate(labels):
            pick = (angle >= i * pitch) & (angle < (i + 1) * pitch)
            if pick.any():
                sectors[name] = round(float(lum[yy[pick], xx[pick]].mean()), 4)
        if len(sectors) == n:
            values = list(sectors.values())
            stats["object_sector_luminance"] = sectors
            stats["object_sector_spread"] = round((max(values) - min(values))
                                                  / max(np.mean(values), 1e-6), 4)
        background = lum[~selection]
        stats["backdrop_luminance_mean"] = round(float(background.mean()), 4)
        # Contact shadow: a ring of backdrop hugging the silhouette against the backdrop
        # far away from it.  Sampling a rectangle under the bbox (what rev 1's audit did)
        # mostly samples open floor and reports "no shadow" on a shot that has one.
        near = _dilate(selection, max(3, width // 120)) & ~selection
        far = _dilate(selection, max(24, width // 12)) & ~_dilate(selection, max(12, width // 24))
        if near.any() and far.any():
            stats["contact_shadow_ratio"] = round(float(lum[near].mean() / max(lum[far].mean(), 1e-6)), 4)
            stats["contact_shadow_note"] = "backdrop luminance hugging the silhouette / well away from it"
        halo = _dilate(selection, 4) & ~selection
        if halo.any():
            stats["halo_luminance_4px"] = round(float(lum[halo].mean()), 4)
    return stats


def wall_gate(stats: dict) -> dict:
    """Hero rim-wall gate: walls read as steel, not an ink outline."""
    wall = stats.get("wall_luminance")
    if not wall:
        return {"passed": False, "detail": "no wall pixels measured"}
    passed = wall["p50"] >= WALL_GATE["p50_min"] and wall["fraction_below_0_03"] <= WALL_GATE["dark_fraction_max"]
    return {"passed": bool(passed), "p50": wall["p50"], "p50_min": WALL_GATE["p50_min"],
            "fraction_below_0_03": wall["fraction_below_0_03"],
            "dark_fraction_max": WALL_GATE["dark_fraction_max"]}


def plate_gate(stats: dict) -> dict:
    """Object p50 of a beauty shot inside the rig's 0.10 to 0.20 target."""
    p50 = (stats.get("object_luminance") or {}).get("p50")
    passed = p50 is not None and PLATE_BAND[0] <= p50 <= PLATE_BAND[1]
    return {"passed": bool(passed), "p50": p50, "band": list(PLATE_BAND)}


_DATA_KINDS = ("objects", "meshes", "materials", "lights", "cameras", "worlds", "collections", "images",
               "curves", "fonts")


def _snapshot() -> Dict[str, set]:
    return {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in _DATA_KINDS}


def _teardown(before: Dict[str, set]) -> None:
    """Remove every datablock created since ``before`` (objects first, then their data)."""
    for kind in _DATA_KINDS:
        store = getattr(bpy.data, kind)
        for item in [item for item in store if item.as_pointer() not in before[kind]]:
            store.remove(item)


def render_previews(form: str, o: Outline, lod0, lods, helpers, render_dir: Path, diag_dir: Path,
                    samples: int, res_x: int, res_y: int, light_scale: float = 1.0,
                    hide=(), beauty_material=None, lod_labels: Optional[Sequence[str]] = None) -> tuple:
    """Render ``<form>_persp/_top/_wire/_lods.png`` and measure them; leave no trace.

    ``hide`` are objects of other forms in the same scene: hidden from render for these
    shots and restored afterwards, as are every hide_render flag this touches, the scene
    world and LOD0's material slot (``beauty_material`` replaces it for the two beauty
    shots only).
    """
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    before = _snapshot()
    previous_world = scene.world
    previous_override = view_layer.material_override
    previous_transform = scene.view_settings.view_transform
    touched = list(helpers) + list(lods) + [lod0] + list(hide)
    saved_hide = {obj.name: obj.hide_render for obj in touched}
    saved_material = lod0.data.materials[0] if len(lod0.data.materials) else None
    try:
        setup_render(samples, res_x, res_y)
        rig = build_preview_rig(o, res_x, res_y, light_scale)
        coll = rig["collection"]
        for obj in list(helpers) + list(lods) + list(hide):
            obj.hide_render = True
        lod0.hide_render = False
        wall_mask = _wall_mask_material()

        diag_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        stats: Dict[str, dict] = {}

        def shoot(name: str, camera, lights, hide_now=(), show=(), ground=True, card=False, denoise=True):
            for light in rig["hero_lights"] + rig["top_lights"]:
                light.hide_render = light not in lights
            for obj in hide_now:
                obj.hide_render = True
            for obj in show:
                obj.hide_render = False
            rig["ground"].hide_render = not ground
            rig["card"].hide_render = not card
            scene.render.film_transparent = False
            scene.cycles.samples = samples
            scene.cycles.use_denoising = denoise
            beauty = Path(render_to(render_dir / f"{name}.png", camera))
            # Matching mask pass: alpha = coverage (ground gone, film transparent), red =
            # walls, via a flat emission override and the Standard view transform.
            rig["ground"].hide_render = True
            rig["card"].hide_render = True
            scene.render.film_transparent = True
            scene.cycles.samples = max(8, samples // 12)
            beauty_transform = scene.view_settings.view_transform
            view_layer.material_override = wall_mask
            scene.view_settings.view_transform = "Standard"
            try:
                mask = Path(render_to(diag_dir / f"{name}_mask.png", camera))
            finally:
                view_layer.material_override = previous_override
                scene.view_settings.view_transform = beauty_transform
                scene.render.film_transparent = False
                scene.cycles.use_denoising = True
            written[name] = str(beauty)
            try:
                stats[name] = image_stats(beauty, mask, o.n)
            except Exception as exc:                                # pragma: no cover
                stats[name] = {"error": f"{type(exc).__name__}: {exc}"}

        if beauty_material is not None:
            lod0.data.materials[0] = beauty_material
        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        shoot(f"{form}_persp", rig["cam_persp"], rig["hero_lights"], card=True)
        shoot(f"{form}_top", rig["cam_top"], rig["top_lights"])
        if beauty_material is not None:
            lod0.data.materials[0] = saved_material

        # --- wireframe and LOD strip: flat-lit emissive copies, no lights, dark field.
        top_px_per_m = res_x / rig["cam_top"].data.ortho_scale
        solid, wires = wire_pair(lod0, coll, "Wire", thickness=WIRE_PX / top_px_per_m)
        spacing = rig["span_x"] + LOD_STRIP_GAP
        fit_ortho(rig["cam_lod"], len(lods) * spacing + rig["span_x"], rig["span_y"], 0.90, 0.80,
                  res_x, res_y)
        lod_px_per_m = res_x / rig["cam_lod"].data.ortho_scale
        strip_objects: List = []
        for i, obj in enumerate([lod0] + list(lods)):
            offset = ((i - 0.5 * len(lods)) * spacing, 0.0, 0.0)
            strip_objects += list(wire_pair(obj, coll, f"Lod{i}", offset=offset,
                                            thickness=WIRE_PX / lod_px_per_m))
        labels = []
        if lod_labels:
            frame_h = rig["cam_lod"].data.ortho_scale * res_y / res_x
            size = 0.036 * frame_h
            for i, text in enumerate(lod_labels):
                x = (i - 0.5 * len(lods)) * spacing
                labels.append(label(coll, f"PREVIEW_LodLabel{i}", text,
                                    (x, -0.5 * rig["span_y"] - 0.05 * frame_h, 0.001), size))
            bpy.context.view_layer.update()
            label_bottom = min(obj.location.y - obj.dimensions.y for obj in labels)
            rig["cam_lod"].location.y = 0.5 * (0.5 * rig["span_y"] + label_bottom)
        for obj in [solid, wires] + strip_objects + labels:
            obj.hide_render = True

        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.02, 0.026, 1.0)
        for node in list(scene.world.node_tree.nodes):
            if node.type in {"VALTORGB", "MAP_RANGE", "SEPXYZ", "TEX_COORD"}:
                scene.world.node_tree.nodes.remove(node)
        shoot(f"{form}_wire", rig["cam_top"], [], hide_now=[lod0] + strip_objects + labels,
              show=[solid, wires], ground=False, denoise=False)
        shoot(f"{form}_lods", rig["cam_lod"], [], hide_now=[solid, wires], show=strip_objects + labels,
              ground=False, denoise=False)
        rig_info = {
            "ring_lamps": rig["ring_lamps"],
            "top_span_mm": [round(rig["span_x"] * 1000, 6), round(rig["span_y"] * 1000, 6)],
            "top_frame_mm": [round(rig["cam_top"].data.ortho_scale * 1000, 3), round(TOP_FRAME_HEIGHT * 1000, 3)],
            "top_px_per_mm": round(top_px_per_m / 1000.0, 4),
            "lod_strip_pitch_mm": round(spacing * 1000, 6),
            "lod_strip_px_per_mm": round(lod_px_per_m / 1000.0, 4),
            "wire_px": WIRE_PX,
            "hero_composition": composition,
            "hero_depth_of_field": dof,
            "hero_wall_card": {"strength": WALL_CARD_STRENGTH, "colour": list(WALL_CARD_COLOUR),
                               "radius_mm": round((o.r_tip + WALL_CARD_MARGIN) * 1000, 3),
                               "visibility": "glossy rays only; top face emits, underside transparent"},
            "beauty_material": beauty_material.name if beauty_material is not None else saved_material.name,
            "lod_labels": list(lod_labels or []),
        }
        return written, stats, rig_info
    finally:
        if saved_material is not None and len(lod0.data.materials):
            lod0.data.materials[0] = saved_material
        view_layer.material_override = previous_override
        scene.view_settings.view_transform = previous_transform
        scene.world = previous_world
        _teardown(before)
        for name, value in saved_hide.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = value


__all__ = ["PLATE_BAND", "SHOT_SUFFIXES", "TOP_FRAME_HEIGHT", "WALL_GATE", "build_preview_rig", "centre_perspective",
           "fit_ortho", "fit_perspective", "image_stats", "label", "load_pixels", "plate_gate", "projected_bbox",
           "render_previews", "render_to", "ring_lamp_count", "setup_render", "solve_depth_of_field", "wall_gate",
           "wire_pair"]
