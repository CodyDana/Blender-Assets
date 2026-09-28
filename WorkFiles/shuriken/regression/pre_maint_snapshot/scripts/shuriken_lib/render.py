"""Gallery render rig shared by every form: hero, top (spec), wireframe, LOD strip.

Exposure is the whole ball game on a 0.9 metallic: rev 1 lit a blackened star with
four soft lamps against a near-white world and got a flat mid-grey card in the hero
and a near-black plate in the top view - a 3.2x difference in the same product across
two gallery images.  These constants were tuned against measurements taken from the
finished PNGs (see ``image_stats``), targeting a plate mid-tone of 0.10 to 0.20 in
*both* beauty shots with the brightness carried by specular hits.  Do not retune them
per form: one rig is what makes the pack's gallery read as one product line.

Gallery frames are 16:9 so they survive Fab's 1920x1080 thumbnail crop (study 7).

Form-dependent inputs, and only these: the ground sits at -thickness/2, the top and
LOD cameras frame the form's tip extents, and the top view's lamp ring has the
smallest multiple of n lamps that is >= 8 (8 for C4 and C8, exactly rev 2's ring;
12 for C6, 9 for C3) at constant total power, so every arm of any C_n form is lit
identically.

The rig is built after the .blend is saved and torn down after each form, so it never
reaches Assets/Shuriken.blend and every form renders from an identical starting state.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List

import bpy
import numpy as np
from mathutils import Matrix, Vector

from .spec import Outline

GROUND_COLOUR = (0.150, 0.149, 0.144)
GROUND_ROUGHNESS = 0.22 # glossy enough to bounce the rake strips back up into the rim walls
HERO_KEY_W = 1.28       # broad source in the camera's mirror direction: sets plate value
HERO_RAKE_A_W = 0.88    # grazing strip: makes the 0.9 mm ground facet read
HERO_RAKE_B_W = 0.68
HERO_FILL_W = 2.20      # lifts the 3 mm rim wall off black
HERO_BOUNCE_W = 1.60    # low card on the camera side: the near rim wall, not an ink outline
TOP_DOME_W = 5.40       # axial soft box: the only thing a flat plate mirrors straight up
TOP_RING_W = 0.22       # per lamp of the 8-lamp ring (scaled to keep total power for other counts)
TOP_RING_BASE = 8
LOD_STRIP_GAP = 0.021   # m between neighbours in the LOD strip (rev 2: 0.118 m pitch for 97 mm)
SHOT_SUFFIXES = ("persp", "top", "wire", "lods")


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
    """Ground, world-facing strip lights and the three cameras."""
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

    cam_top_data = bpy.data.cameras.new("PREVIEW_CamTop")
    cam_top_data.type = "ORTHO"
    cam_top = bpy.data.objects.new("PREVIEW_CamTop", cam_top_data)
    coll.objects.link(cam_top)
    cam_top.location = (0.0, 0.0, 0.30)
    cam_top.rotation_euler = (0.0, 0.0, 0.0)
    fit_ortho(cam_top, span_x, span_y, 0.84, 0.84, res_x, res_y)

    cam_lod_data = bpy.data.cameras.new("PREVIEW_CamLod")
    cam_lod_data.type = "ORTHO"
    cam_lod = bpy.data.objects.new("PREVIEW_CamLod", cam_lod_data)
    coll.objects.link(cam_lod)
    cam_lod.location = (0.0, 0.0, 0.30)
    cam_lod.rotation_euler = (0.0, 0.0, 0.0)

    cam_persp_data = bpy.data.cameras.new("PREVIEW_CamPersp")
    cam_persp_data.lens = 72.0
    cam_persp_data.dof.use_dof = True
    cam_persp_data.dof.aperture_fstop = 16.0   # a hint of falloff, not a macro shot
    cam_persp = bpy.data.objects.new("PREVIEW_CamPersp", cam_persp_data)
    coll.objects.link(cam_persp)
    cam_persp.location = _polar(0.30, 29.0, -22.0)
    _aim(cam_persp)
    return {"collection": coll, "ground": ground, "hero_lights": hero, "top_lights": top,
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
    """(height, width, 4) raw stored values of a PNG.

    ``image.pixels`` returns raw stored values in Blender 5.2, and the colour space is
    forced to Non-Color so nothing is converted: these numbers are directly comparable
    to sampling the PNG with any other tool.
    """
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    width, height = img.size
    buf = np.empty(width * height * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(height, width, 4)


def image_stats(beauty: Path, mask: Path, n: int = 4) -> dict:
    """Read a render back and report what a buyer will actually see."""
    pixels = load_pixels(beauty)
    alpha = load_pixels(mask)[..., 3]
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
            "bbox_width_fraction": round(float((cols.max() - cols.min() + 1) / width), 4),
            "bbox_height_fraction": round(float((rows.max() - rows.min() + 1) / height), 4),
        })
        # The silhouette band is the rim wall plus the ground bevel seen edge-on.
        # Rev 1 rendered it as a solid black outline; the target is 0.15 to 0.25.
        eroded = selection.copy()
        for _ in range(4):
            step = eroded.copy()
            for axis in (0, 1):
                step &= np.roll(eroded, 1, axis=axis)
                step &= np.roll(eroded, -1, axis=axis)
            eroded = step
        rim = selection & ~eroded
        if rim.any():
            stats["rim_band_luminance"] = {
                "mean": round(float(lum[rim].mean()), 4),
                "p50": round(float(np.percentile(lum[rim], 50)), 4),
                "note": "outer 4 px of the silhouette: the plate edge, target 0.15 to 0.25",
            }
        # n-fold evenness: on a C_n object an unevenly lit spec shot shows n different
        # arms.  Sectors are taken about the subject centre, one centred on each arm in
        # the top view (arm 0 points right).
        yy, xx = np.nonzero(selection)
        cy, cx = 0.5 * (rows.min() + rows.max()), 0.5 * (cols.min() + cols.max())
        pitch = 360.0 / n
        angle = (np.degrees(np.arctan2(-(yy - cy), xx - cx)) + 360.0 + 0.5 * pitch) % 360.0
        labels = ("right", "up", "left", "down") if n == 4 else tuple(f"arm{i}" for i in range(n))
        sectors = {}
        for i, label in enumerate(labels):
            pick = (angle >= i * pitch) & (angle < (i + 1) * pitch)
            if pick.any():
                sectors[label] = round(float(lum[yy[pick], xx[pick]].mean()), 4)
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
    return stats


_DATA_KINDS = ("objects", "meshes", "materials", "lights", "cameras", "worlds", "collections", "images")


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
                    hide=()) -> tuple:
    """Render ``<form>_persp/_top/_wire/_lods.png`` and measure them; leave no trace.

    ``hide`` are objects of other forms in the same scene: hidden from render for these
    shots and restored afterwards, as are every hide_render flag this touches and the
    scene world.
    """
    scene = bpy.context.scene
    before = _snapshot()
    previous_world = scene.world
    touched = list(helpers) + list(lods) + [lod0] + list(hide)
    saved_hide = {obj.name: obj.hide_render for obj in touched}
    try:
        setup_render(samples, res_x, res_y)
        rig = build_preview_rig(o, res_x, res_y, light_scale)
        coll = rig["collection"]
        for obj in list(helpers) + list(lods) + list(hide):
            obj.hide_render = True
        lod0.hide_render = False

        diag_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, str] = {}
        stats: Dict[str, dict] = {}

        def shoot(name: str, camera, lights, hide_now=(), show=()):
            for light in rig["hero_lights"] + rig["top_lights"]:
                light.hide_render = light not in lights
            for obj in hide_now:
                obj.hide_render = True
            for obj in show:
                obj.hide_render = False
            scene.render.film_transparent = False
            scene.cycles.samples = samples
            beauty = Path(render_to(render_dir / f"{name}.png", camera))
            # Matching alpha mask, so the stats below describe the subject and not a
            # luminance guess: the ground goes away and the film goes transparent.
            rig["ground"].hide_render = True
            scene.render.film_transparent = True
            scene.cycles.samples = max(8, samples // 12)
            mask = Path(render_to(diag_dir / f"{name}_mask.png", camera))
            scene.render.film_transparent = False
            rig["ground"].hide_render = False
            written[name] = str(beauty)
            try:
                stats[name] = image_stats(beauty, mask, o.n)
            except Exception as exc:                                # pragma: no cover
                stats[name] = {"error": f"{type(exc).__name__}: {exc}"}

        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        shoot(f"{form}_persp", rig["cam_persp"], rig["hero_lights"])
        shoot(f"{form}_top", rig["cam_top"], rig["top_lights"])

        # --- wireframe and LOD strip: flat-lit emissive copies, no lights, dark field.
        solid, wires = wire_pair(lod0, coll, "Wire")
        strip_objects: List = []
        spacing = rig["span_x"] + LOD_STRIP_GAP
        for i, obj in enumerate([lod0] + list(lods)):
            offset = ((i - 0.5 * len(lods)) * spacing, 0.0, 0.0)
            strip_objects += list(wire_pair(obj, coll, f"Lod{i}", offset=offset, thickness=0.00013))
        for obj in [solid, wires] + strip_objects:
            obj.hide_render = True
        fit_ortho(rig["cam_lod"], len(lods) * spacing + rig["span_x"], rig["span_y"], 0.90, 0.80,
                  res_x, res_y)

        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.02, 0.026, 1.0)
        for node in list(scene.world.node_tree.nodes):
            if node.type in {"VALTORGB", "MAP_RANGE", "SEPXYZ", "TEX_COORD"}:
                scene.world.node_tree.nodes.remove(node)
        shoot(f"{form}_wire", rig["cam_top"], [],
              hide_now=[lod0, rig["ground"]] + strip_objects, show=[solid, wires])
        shoot(f"{form}_lods", rig["cam_lod"], [],
              hide_now=[solid, wires], show=strip_objects)
        rig_info = {"ring_lamps": rig["ring_lamps"], "top_span_mm": [round(rig["span_x"] * 1000, 6),
                                                                      round(rig["span_y"] * 1000, 6)],
                    "lod_strip_pitch_mm": round(spacing * 1000, 6)}
        return written, stats, rig_info
    finally:
        scene.world = previous_world
        _teardown(before)
        for name, value in saved_hide.items():
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.hide_render = value


__all__ = ["SHOT_SUFFIXES", "build_preview_rig", "fit_ortho", "fit_perspective", "image_stats",
           "load_pixels", "projected_bbox", "render_previews", "render_to", "ring_lamp_count",
           "setup_render", "wire_pair"]
