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

Second style pass (visual review): the camera-facing chamfer facets rendered as ink bands
(a 26.6 deg facet mirrors ~8 deg past the zenith, where only the dark world was), so the
hero gained an overhead soft panel and the top view a rotationally symmetric cone band,
both glossy-rays-only so the plate, the ground and the backdrop are untouched; the mask
pass now also flags the facets (green) and ``facet_gate`` checks them; ``plate_gate`` and
``pack_consistency`` gate the mean as well as the p50, with the bands re-centred on the
reference asset rendered through this very rig.

3.7.1 (six-point review): ``pack_consistency`` is centred on a FIXED anchor (``PACK_ANCHOR``,
the mean of the forms frozen at restyle pass 2) instead of the mean of whichever forms are in
the build, so adding a form can no longer push an unchanged frozen form out of tolerance; the
all-forms statistics and every form's headroom are still reported.

3.8 (the throwing spike, the pack's first BAR).  The rig is unchanged; four form-dependent inputs
were added, each read with a default that is the old behaviour, so the plate forms render as before:

* ``hero_yaw_deg`` (render outline): the hero turns the object about Z for the shot (the camera,
  the lights and the ground stay where they are).  A 150 mm bar on +X seen from the rig's -22 deg
  camera is end-on; turned it lies across the frame.  The top (spec) view is never turned.
* ``lod_strip_axis`` "y": the LOD strip stacks a long form's LODs top to bottom instead of end to end.
* ``grind_target_back_m``: how far back from the point the LOD close-up aims.
* The top frame's size check compares the plan span with the frame's WIDTH along X and its height
  along Y (it compared the larger span with the height); the frame itself (TOP_FRAME_HEIGHT, the
  pack's common px/mm) is unchanged.

The mask pass also writes BLUE = the generator's FACE attribute ``shuriken_ground`` (a bar's
polished, ground surfaces; absent, i.e. 0, on the plate forms), and ``image_stats`` reports
``coat_luminance``: pixels of flat, up-facing, non-ground faces (red, green and blue all below
0.5) - the plate of a star, the up-facing faces of a bar: the same coat under the same light.
``pack_consistency`` compares like with like: plate forms as before (whole object against
PACK_ANCHOR); a bar's whole-object figures are information (half its silhouette is side face and
a polished point, which no plate has), and its COAT pixels are gated against PACK_COAT_ANCHOR,
the anchor forms' own coat pixels.

3.8.1 (spike maintenance, visual review), again read with defaults that are the old behaviour:

* ``hero_rig_match`` (a bar): the dolly fit puts the camera ~0.30 m from a 150 mm bar against ~0.22 m
  for the stars, and the larger frame showed more floor - the key's floor reflection ended at 0.88 of
  the frame width (a dark wedge down the right edge) and rake A's reflection glowed in the top-right
  corner.  The hero lamps are scaled about the origin by the fitted camera distance over
  HERO_RIG_REFERENCE_M (the anchor forms' mean), sizes x s and power x s^2: every lamp keeps its
  direction, solid angle and radiance, so the lighting reads the same from the camera and the plate
  forms (scale 1, nothing touched) render exactly as before.  The lamps are restored after the hero.
  Before that the object is slid on the floor (with its hero yaw, for the hero only) until the lens
  shift the framing needs equals the anchor forms' mean (HERO_SHIFT_TARGET): the yawed bar's near end
  projects larger, so centring it needed shift_x +0.067 against the stars' -0.036..+0.012, which moved
  the frame 0.1 of its width right, past the end of the key's floor reflection.
* ``image_stats`` reports ``backdrop_points`` on every shot: backdrop luminance (11 x 11 px median, the
  object and 3 px around it excluded) at BACKDROP_POINTS, fixed frame fractions at the corners and down
  the right third; ``pack_consistency`` gates every form's hero backdrop against PACK_BACKDROP_ANCHOR (the
  anchor forms' range at each point) +- BACKDROP_TOLERANCE.
* A bar's side faces (``bar_wall_gate``; mask red = |N.z| < 0.5, not blue = not ground): their
  luminance (``bar_wall_luminance``) and an isolated dark-dot count (``dark_dots``: blobs of <= 16 px and
  <= 5 px across in the face interior, eroded 4 px, at least 30 % darker than the 7 x 7 median of the
  face around them) - the pits on the hero side face read as black pepper at 8.3 dots / 10k px (stars'
  plates 0.03-0.08, reference 0.74).  render gate ``hero_bar_walls``: dots <= BAR_WALL_DOT_GATE; and
  ``pack_consistency`` gates the side face's p50 against PACK_WALL_ANCHOR (the anchor forms' hero wall p50).
* ``lod_section_inset`` (a bar): the plan-view LOD strip cannot show the 0.3 mm arris round (4 chords /
  2 / square), so each LOD gets an end-on section of its butt end beside it at that scale.

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

from .material import GROUND_ATTR
from .spec import Outline

GROUND_COLOUR = (0.150, 0.149, 0.144)
GROUND_ROUGHNESS = 0.22 # glossy enough to bounce the rake strips back up into the rim walls
HERO_KEY_W = 1.15       # broad source in the camera's mirror direction: sets plate value (1.28 until the
                        # maintenance pass: the baked scratches and the wall card lifted the hero p50 past 0.20)
HERO_RAKE_A_W = 0.88    # grazing strip: makes the 0.9 mm ground facet read
HERO_RAKE_B_W = 0.68
HERO_FILL_W = 2.20      # lifts the 3 mm rim wall off black
HERO_BOUNCE_W = 1.60    # low card on the camera side: the near rim wall, not an ink outline
HERO_TOP_W = 1.30       # overhead soft panel, glossy rays only: what the camera-facing chamfer facets mirror
TOP_DOME_W = 5.40       # axial soft box: the only thing a flat plate mirrors straight up
TOP_RING_W = 0.22       # per lamp of the 8-lamp ring (scaled to keep total power for other counts)
TOP_RING_BASE = 8
# Top-view facet band: an emissive cone band (glossy rays only) at the elevation the 26.6 deg
# chamfer facets mirror when seen straight down (2 x 26.6 deg off the axis = 37 deg elevation).
# Rotationally symmetric, so every facet at every azimuth of any C_n form sees the same thing.
TOP_BAND_ELEVATION = (29.0, 45.0)   # deg
TOP_BAND_RADIUS = 0.36              # m
TOP_BAND_STRENGTH = 0.70
TOP_BAND_COLOUR = (0.92, 0.94, 0.98)
LOD_STRIP_GAP = 0.021   # m between neighbours in the LOD strip (rev 2: 0.118 m pitch for 97 mm)
LOD_STRIP_Y_GAP = 0.016  # m between a long form's LODs stacked top to bottom (room for the label under each)
SHOT_SUFFIXES = ("persp", "top", "wire", "lods", "lodgrind")
# LOD grind close-up (visual review, decision D): the plan-view LOD strip cannot show that LOD1 and
# LOD2 keep a single-facet knife grind, so every LOD is also shot as an oblique, shaded close-up of
# the point on +X (arm 0 / the senban's corner 0) with the baked maps and the hero lights, and the
# panels are laid side by side in <form>_lodgrind.png, labelled LOD0 / LOD1 / LOD2.
GRIND_VIEW = {"elevation_deg": 21.0, "azimuth_deg": -34.0, "distance_m": 0.075, "lens_mm": 105.0,
              "target_back_m": 0.011}

# Reflection card for the rim walls (hero only): radiance of its top face, and its reach.
WALL_CARD_STRENGTH = 0.9
WALL_CARD_COLOUR = (0.88, 0.90, 0.94)
WALL_CARD_MARGIN = 0.040          # m beyond the tip circle
WALL_CARD_LIFT = 0.00005          # m above the ground plane
# Wall gate (hero): stored-sRGB Rec.709 luma of pixels on faces with |N.z| < 0.5.
WALL_GATE = {"p50_min": 0.06, "dark_below": 0.03, "dark_fraction_max": 0.05}
# Facet gate (hero and top): the chamfer facets (0.5 <= |N.z| < 0.95, the mask pass's green
# channel) must read as a ground edge that catches light, not an ink band.  The first style
# pass shipped the camera-facing facets as solid black (hero p05 0.06, 2-3 % of the object below
# 0.05) because a 26.6 deg facet mirrors ~8 deg past the zenith, where the rig had only the dark
# world; the reference through the same rig has 0.07 % below 0.05.  ``near`` is the camera-facing
# half of the facets (image rows below the object's bbox centre in the hero).
FACET_GATE = {"p50_min": 0.16, "dark_below": 0.05, "dark_fraction_max": 0.06}
# Object luminance of both beauty shots, p50 AND mean, bracketing the reference asset rendered
# through THIS rig (WorkFiles/shuriken/style_reference/ref_on_rig.py, the study-only LP scaled
# to 100 mm and at its native 197 mm): hero mean 0.47-0.48 / p50 0.50-0.52, top mean 0.47 / p50
# 0.44.  STYLE_TARGET.md's projected 0.30 / 0.28 came from a different scratch rig (AgX, flat
# world) and is not comparable.  The upper edge allows for shape: with ONE flat 0.10 / 0.32
# material on every mesh the reference's six long points read hero mean 0.47 / p50 0.53 while
# the compact senban reads 0.56 / 0.61 (four-point 0.47 / 0.58, eight-point 0.50 / 0.60) - a
# solid plate sits inside the key's highlight where a long point does not.  The
# pack-consistency gate compares the forms against each other.
PLATE_BAND = (0.36, 0.64)           # p50
PLATE_MEAN_BAND = (0.38, 0.60)      # mean
# Pack consistency: every form's hero and top p50 and mean within this of PACK_ANCHOR.
PACK_P50_TOLERANCE = 0.05
# The centre the pack gate measures against (3.7.1, six-point review).  Up to 3.7.0 it was the
# mean of every form in the build, so each new form moved the centre: adding the six-point cut the
# frozen four-point's hero-mean headroom from 0.0086 to 0.0059 without the four-point changing, and a
# brighter spike could have failed the gate on a frozen form.  The anchor is now FIXED: the mean of
# the three forms frozen at restyle pass 2 (WorkFiles/shuriken/regression/post_restyle2/
# pack_report.json, library 3.7.0; four-point, eight-point, senban), so a frozen form's offset is a
# constant of its own renders and only a new form is judged against it.  Re-derive the anchor only
# with a deliberate rig or material change that moves every form's renders; pack_consistency fails
# with ``anchor_stale`` when the anchor forms in the build have drifted more than
# PACK_ANCHOR_DRIFT_MAX from it.
PACK_ANCHOR = {
    "forms": ("four_point", "eight_point", "square_plate"),
    "source": "WorkFiles/shuriken/regression/post_restyle2/pack_report.json (restyle pass 2, library 3.7.0)",
    "hero": {"p50": 0.5448, "mean": 0.4844},
    "top": {"p50": 0.4319, "mean": 0.4658},
}
PACK_ANCHOR_DRIFT_MAX = 0.01
# Like-with-like centre for a BAR (3.8, the spike): the COAT pixels (flat up-facing faces that are not
# ground steel: a star's plate, a bar's top faces) of the same three anchor forms, measured on the 3.7.1
# maintenance build's renders and masks (WorkFiles/shuriken/diag/*_mask.png; the whole-object figures
# of the same files reproduce PACK_ANCHOR's sources exactly; the frozen six-point's coat lands within
# 0.002).  A bar's coat must sit within PACK_P50_TOLERANCE of it.
PACK_COAT_ANCHOR = {
    "forms": ("four_point", "eight_point", "square_plate"),
    "source": ("coat pixels (mask R, G, B < 0.5) of the anchor forms' persp / top renders, library 3.7.1 maintenance "
               "build (the 3.8 spike build re-measures them: anchor_drift.coat)"),
    "hero": {"p50": 0.5599, "mean": 0.5503},
    "top": {"p50": 0.4296, "mean": 0.4236},
}
# 3.8.1: the hero lamps of a ``hero_rig_match`` form are scaled by its fitted camera distance over this, the mean
# fitted distance of the anchor forms (four-point 201.161, eight-point 222.455, senban 223.475 mm; render_rig.
# hero_depth_of_field.focus_mm of the 3.8.0 build).
HERO_RIG_REFERENCE_M = 0.215697
# ... and slides the object on the floor until its framing needs this lens shift: the anchor forms' mean
# (render_rig.hero_composition.shift of the 3.8.0 build: four-point (-0.0356, -0.0273), eight-point
# (-0.0009, -0.0213), senban (-0.0356, -0.0273)).
HERO_SHIFT_TARGET = (-0.0240, -0.0253)
# Backdrop points (3.8.1): (x, y) frame fractions, x from the left, y from the top; 11 x 11 px medians.
BACKDROP_POINTS = {"tl": (0.0125, 0.0222), "tr": (0.9875, 0.0222), "bl": (0.0125, 0.9778), "br": (0.9875, 0.9778),
                   "r28": (0.9875, 0.28), "r50": (0.9875, 0.50), "r78": (0.9875, 0.78),
                   "q11": (0.90, 0.11), "q50": (0.90, 0.50), "q78": (0.90, 0.78), "t03": (0.80, 0.03), "t97": (0.80, 0.97)}
BACKDROP_PATCH_HALF = 5
BACKDROP_TOLERANCE = 0.05
# The anchor forms' hero backdrop at each point, [min, max] (3.8.0 build renders; WorkFiles/shuriken/spike_maint/
# backdrop_probe.py).  A form's point must lie within [min - tol, max + tol]; a point covered by the object is skipped.
PACK_BACKDROP_ANCHOR = {
    "forms": ("four_point", "eight_point", "square_plate"),
    "source": "hero backdrop of the anchor forms, 3.8.0 build (spike_maint/backdrop_probe.py)",
    "hero": {"tl": (0.4070, 0.4555), "tr": (0.3535, 0.3653), "bl": (0.3725, 0.4000), "br": (0.3958, 0.4280),
             "r28": (0.4826, 0.5297), "r50": (0.6403, 0.7187), "r78": (0.5336, 0.6050), "q11": (0.4003, 0.4123),
             "q50": (0.7381, 0.7498), "q78": (0.6314, 0.6431), "t03": (0.3683, 0.3770), "t97": (0.4518, 0.4661)},
}
# A bar's side faces, like with like (3.8.1): their hero p50 against the anchor forms' hero WALL p50 (0.2272 /
# 0.2373 / 0.3390 in the 3.8.0 reports) within PACK_P50_TOLERANCE.
PACK_WALL_ANCHOR = {"forms": ("four_point", "eight_point", "square_plate"),
                    "source": "render_stats.<form>_persp.wall_luminance.p50, 3.8.0 build", "hero": {"p50": 0.2678}}
# Isolated dark dots on a bar's hero side faces (pits read as pepper): per 10k face-interior px, at 30 % darker.
BAR_WALL_DOT_GATE = {"threshold": 0.70, "max_per_10k": 1.0, "erode_px": 4, "window_px": 7, "max_blob_px": 16,
                     "max_blob_extent_px": 5}
LOD_STRIP_INSET_GAP = 0.012       # m between a bar and its end-on section inset
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
    """Mask pass: red = 1 on faces with |N.z| < 0.5 (walls, steep facet segments), green = 1 on
    the chamfer facets (0.5 <= |N.z| < 0.95), blue = a bar's ground surfaces (the FACE attribute
    ``shuriken_ground``; 0 on every plate form), black on the flat coat."""
    mat = bpy.data.materials.new("M_Preview_WallMask")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    geom = tree.nodes.new("ShaderNodeNewGeometry")
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    absz = tree.nodes.new("ShaderNodeMath")
    absz.operation = "ABSOLUTE"
    wall = tree.nodes.new("ShaderNodeMath")
    wall.operation = "LESS_THAN"
    wall.inputs[1].default_value = 0.5
    steep = tree.nodes.new("ShaderNodeMath")
    steep.operation = "LESS_THAN"
    steep.inputs[1].default_value = 0.95
    facet = tree.nodes.new("ShaderNodeMath")
    facet.operation = "SUBTRACT"
    combine = tree.nodes.new("ShaderNodeCombineColor")
    emit = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(geom.outputs["True Normal"], sep.inputs["Vector"])
    tree.links.new(sep.outputs["Z"], absz.inputs[0])
    tree.links.new(absz.outputs["Value"], wall.inputs[0])
    tree.links.new(absz.outputs["Value"], steep.inputs[0])
    tree.links.new(steep.outputs["Value"], facet.inputs[0])
    tree.links.new(wall.outputs["Value"], facet.inputs[1])
    tree.links.new(wall.outputs["Value"], combine.inputs["Red"])
    tree.links.new(facet.outputs["Value"], combine.inputs["Green"])
    ground = tree.nodes.new("ShaderNodeAttribute")
    ground.attribute_type = "GEOMETRY"
    ground.attribute_name = GROUND_ATTR
    tree.links.new(ground.outputs["Fac"], combine.inputs["Blue"])
    tree.links.new(combine.outputs["Color"], emit.inputs["Color"])
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def _band_material():
    """Emissive top-view facet band; found by glossy rays only, never light-sampled."""
    mat = _emission("M_Preview_TopBand", TOP_BAND_COLOUR, TOP_BAND_STRENGTH)
    try:
        mat.cycles.emission_sampling = "NONE"
    except (AttributeError, TypeError):         # pragma: no cover
        pass
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


def _top_band(coll):
    """Camera-invisible emissive cone band around the axis: what the chamfer facets mirror in the top view."""
    segments = 96
    verts, faces = [], []
    for elevation in TOP_BAND_ELEVATION:
        for k in range(segments):
            verts.append(_polar(TOP_BAND_RADIUS, elevation, 360.0 * k / segments))
    for k in range(segments):
        k1 = (k + 1) % segments
        faces.append((k, k1, segments + k1, segments + k))
    mesh = bpy.data.meshes.new("PREVIEW_TopBand")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    band = bpy.data.objects.new("PREVIEW_TopBand", mesh)
    coll.objects.link(band)
    band.data.materials.append(_band_material())
    band.visible_camera = False
    band.visible_diffuse = False
    band.visible_shadow = False
    band.visible_transmission = False
    band.visible_volume_scatter = False
    band.visible_glossy = True
    return band


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


def place_for_shift(camera, obj, res_x: int, res_y: int, target=HERO_SHIFT_TARGET, steps: int = 6) -> dict:
    """Slide ``obj`` on the floor until the dolly fit + centring need the lens shift ``target`` (3.8.1).

    A shift of d frame widths moves the image by d; the object moved by d x W along the camera's
    (horizontal) right vector does the same, W the frame width at the camera's distance; a move of
    d x W / sin(elevation) along the horizontal view direction moves it up the frame by d.
    """
    info = {}
    for step in range(steps):
        fit_perspective(camera, [obj], 0.90, 0.86)
        info = centre_perspective(camera, [obj], res_x, res_y)
        dx, dy = camera.data.shift_x - target[0], camera.data.shift_y - target[1]
        if max(abs(dx), abs(dy)) < 0.001:
            break
        rot = camera.matrix_world.to_3x3()
        view = rot @ Vector((0.0, 0.0, -1.0))
        right = rot @ Vector((1.0, 0.0, 0.0))
        right.z = 0.0
        right.normalize()
        forward = Vector((view.x, view.y, 0.0)).normalized()
        elevation = math.asin(max(1e-3, -view.z))
        width = camera.location.length * camera.data.sensor_width / camera.data.lens
        obj.location = obj.location - right * (dx * width) - forward * (dy * width / math.sin(elevation))
        bpy.context.view_layer.update()
    info.update({"object_offset_mm": [round(v * 1000.0, 3) for v in obj.location], "target_shift": list(target),
                 "steps": step + 1})
    return info


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
    # The camera-facing chamfer facets (26.6 deg) mirror the camera ray to ~8 deg past the
    # zenith on the key's side, where the world is at its darkest: a broad soft panel there,
    # seen by glossy rays only (the ground and the flat plate's diffuse are untouched; the plate
    # mirrors the key 50 deg away, outside the 0.32-roughness lobe), so the near edges read as
    # ground steel catching light instead of an ink band.
    top_panel = _strip(coll, "PREVIEW_HeroTop", _polar(0.70, 80.0, 158.0), 0.70, 0.70,
                       HERO_TOP_W, light_scale, colour=(0.95, 0.96, 1.0))
    top_panel.visible_diffuse = False
    top_panel.visible_shadow = False
    hero.append(top_panel)

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
    band = _top_band(coll)
    for light in hero + top:
        light.hide_render = True
    band.hide_render = True

    top_width = TOP_FRAME_HEIGHT * max(res_x, res_y) / min(res_x, res_y)
    if span_y > 0.92 * TOP_FRAME_HEIGHT or span_x > 0.92 * top_width:
        raise ValueError(f"form spans {span_x * 1000:.1f} x {span_y * 1000:.1f} mm; the pack-wide top frame is "
                         f"{top_width * 1000:.0f} x {TOP_FRAME_HEIGHT * 1000:.0f} mm - raise TOP_FRAME_HEIGHT for every form")
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
    return {"collection": coll, "ground": ground, "card": card, "band": band, "hero_lights": hero, "top_lights": top,
            "cam_top": cam_top, "cam_persp": cam_persp, "cam_lod": cam_lod,
            "span_x": span_x, "span_y": span_y, "ring_lamps": count}


def wire_pair(source, coll, name: str, offset=(0.0, 0.0, 0.0), thickness: float = 0.00016, basis=None):
    """Flat-lit copy plus a Wireframe-modifier copy floated just above it.

    ``basis`` (3.8.1): an optional 4x4 rotation / scale applied before the offset (the bar's end-on insets)."""
    solid = source.copy()
    solid.data = source.data.copy()
    solid.name = f"PREVIEW_{name}Solid"
    solid.parent = None
    solid.matrix_world = Matrix.Translation(offset) if basis is None else Matrix.Translation(offset) @ basis
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(_emission(f"M_Preview_{name}Solid", (0.150, 0.162, 0.185), 1.0))

    wires = source.copy()
    wires.data = source.data.copy()
    wires.name = f"PREVIEW_{name}Lines"
    wires.parent = None
    lifted = Matrix.Translation((offset[0], offset[1], offset[2] + 0.0006))
    wires.matrix_world = lifted if basis is None else lifted @ basis
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


def _write_pixels(pixels: np.ndarray, path: Path) -> None:
    """Write (height, width, 4) raw stored values (rows top-down) to a PNG, unconverted."""
    height, width = pixels.shape[:2]
    image = bpy.data.images.new(f"__{path.stem}", width=width, height=height, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(np.ascontiguousarray(pixels[::-1], dtype=np.float32).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def render_lod_grind(form: str, o: Outline, lod_objects, material, rig: dict, render_dir: Path,
                     diag_dir: Path, samples: int, res_x: int, res_y: int, labels: Sequence[str]) -> dict:
    """``<form>_lodgrind.png``: every LOD's point on +X as an oblique shaded close-up, side by side.

    One camera (GRIND_VIEW) looks at the point from above and to one side, so the facets of both
    faces' grinds, the land (LOD0 / LOD1) or the edge line (LOD2) and the tip read; the hero lights,
    the ground and the wall card light it; each LOD is rendered alone with ``material`` (the baked
    preview material, shared by every LOD through LOD0's UV0) and the panels are pasted into one PNG.
    """
    scene = bpy.context.scene
    count = len(lod_objects)
    panel_w = res_x // count
    target = Vector((o.r_tip - getattr(o, "grind_target_back_m", GRIND_VIEW["target_back_m"]), 0.0, 0.0))
    cam_data = bpy.data.cameras.new("PREVIEW_CamGrind")
    cam_data.lens = GRIND_VIEW["lens_mm"]
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.01
    cam = bpy.data.objects.new("PREVIEW_CamGrind", cam_data)
    rig["collection"].objects.link(cam)
    cam.location = target + Vector(_polar(GRIND_VIEW["distance_m"], GRIND_VIEW["elevation_deg"],
                                          GRIND_VIEW["azimuth_deg"]))
    _aim(cam, target)
    bpy.context.view_layer.update()
    # labels ride on the camera, 2 cm in front of it (above the ground), at the bottom of the frame
    depth = 0.02
    frame_w = depth * cam_data.sensor_width / cam_data.lens
    frame_h = frame_w * res_y / panel_w
    saved_res = (scene.render.resolution_x, scene.render.resolution_y)
    saved_materials = [obj.data.materials[0] if len(obj.data.materials) else None for obj in lod_objects]
    saved_hide = [obj.hide_render for obj in lod_objects]
    saved_cam_vis = {light.name: light.visible_camera for light in rig["hero_lights"]}
    for light in rig["hero_lights"]:
        light.visible_camera = False           # the close-up frames a lamp the hero camera never sees
    for light in rig["hero_lights"] + rig["top_lights"]:
        light.hide_render = light not in rig["hero_lights"]
    rig["ground"].hide_render = False
    rig["card"].hide_render = False
    rig["band"].hide_render = True
    scene.render.resolution_x, scene.render.resolution_y = panel_w, res_y
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    panels, made = [], []
    try:
        for i, obj in enumerate(lod_objects):
            for other in lod_objects:
                other.hide_render = other is not obj
            if material is not None:
                obj.data.materials[0] = material
            text = None
            if i < len(labels):
                size = min(0.045 * frame_h, 0.92 * frame_w / (0.62 * max(len(labels[i]), 1)))
                text = label(rig["collection"], f"PREVIEW_GrindLabel{i}", labels[i], (0.0, 0.0, 0.0), size)
                text.parent = cam
                text.matrix_parent_inverse = Matrix.Identity(4)
                text.location = (0.0, -0.38 * frame_h, -depth)
                text.rotation_euler = (0.0, 0.0, 0.0)
                made.append(text)
            path = diag_dir / f"{form}_lodgrind_lod{i}.png"
            render_to(path, cam)
            panels.append(load_pixels(path))
            if text is not None:
                text.hide_render = True
        sheet = np.concatenate(panels, axis=1)
        out = render_dir / f"{form}_lodgrind.png"
        _write_pixels(sheet, out)
    finally:
        for obj, mat, hidden in zip(lod_objects, saved_materials, saved_hide):
            if mat is not None and len(obj.data.materials):
                obj.data.materials[0] = mat
            obj.hide_render = hidden
        scene.render.resolution_x, scene.render.resolution_y = saved_res
        for light in rig["hero_lights"]:
            light.visible_camera = saved_cam_vis[light.name]
    return {"path": str(out), "panels": count, "panel_px": [panel_w, res_y], "view": dict(GRIND_VIEW),
            "target_mm": [round(v * 1000, 3) for v in target], "labels": list(labels),
            "material": material.name if material is not None else None}


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


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(radius):
        step = out.copy()
        for axis in (0, 1):
            step &= np.roll(out, 1, axis=axis)
            step &= np.roll(out, -1, axis=axis)
        out = step
    return out


def dark_dots(lum: np.ndarray, region: np.ndarray, gate: dict = BAR_WALL_DOT_GATE, thresholds=(0.80, 0.70)) -> Optional[dict]:
    """Isolated dark dots inside ``region`` (3.8.1; the visual review's pepper metric).

    The interior is ``region`` eroded by ``erode_px``; a pixel is dark when it is below ``threshold`` x the
    median of the ``region`` pixels in the ``window_px`` square around it; dark pixels are grouped 8-connected
    and a group of at most ``max_blob_px`` pixels and ``max_blob_extent_px`` across is a dot.  Per 10k interior px.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    core = _erode(region, gate["erode_px"])
    count = int(core.sum())
    if count < 500:
        return None
    r = gate["window_px"] // 2
    ys, xs = np.nonzero(core)
    y0, y1, x0, x1 = ys.min() - r, ys.max() + r + 1, xs.min() - r, xs.max() + r + 1
    padded = np.full((y1 - y0, x1 - x0), np.nan, dtype=np.float32)
    sy0, sy1, sx0, sx1 = max(y0, 0), min(y1, lum.shape[0]), max(x0, 0), min(x1, lum.shape[1])
    padded[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = np.where(region[sy0:sy1, sx0:sx1], lum[sy0:sy1, sx0:sx1], np.nan)
    windows = sliding_window_view(padded, (2 * r + 1, 2 * r + 1))
    median = np.nanmedian(windows[ys - y0 - r, xs - x0 - r].reshape(count, -1), axis=1)   # window k starts at row y0 + k
    values = lum[ys, xs]
    out = {"interior_px": count, "window_px": gate["window_px"], "erode_px": gate["erode_px"]}
    for threshold in thresholds:
        dark = values < median * threshold
        points = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(ys[dark], xs[dark]))}
        parent = list(range(len(points)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        keys = list(points)
        for i, (y, x) in enumerate(keys):
            for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                j = points.get((y + dy, x + dx))
                if j is not None:
                    a, b = find(i), find(j)
                    if a != b:
                        parent[a] = b
        groups: Dict[int, list] = {}
        for i in range(len(keys)):
            groups.setdefault(find(i), []).append(keys[i])
        dots = 0
        for members in groups.values():
            gy = [m[0] for m in members]
            gx = [m[1] for m in members]
            if len(members) <= gate["max_blob_px"] and max(max(gy) - min(gy), max(gx) - min(gx)) + 1 <= gate["max_blob_extent_px"]:
                dots += 1
        key = f"{int(round((1.0 - threshold) * 100))}pct"
        out[key] = {"dark_px_per_1000": round(float(dark.sum()) / count * 1000.0, 3),
                    "dots": dots, "dots_per_10k_px": round(dots / count * 1e4, 3)}
    return out


def backdrop_points(lum: np.ndarray, selection_any: np.ndarray) -> dict:
    """Backdrop luminance at BACKDROP_POINTS: 11 x 11 px medians, the object and 3 px around it excluded."""
    excluded = _dilate(selection_any, 3)
    height, width = lum.shape
    out = {}
    for key, (fx, fy) in BACKDROP_POINTS.items():
        cx, cy = int(round(fx * (width - 1))), int(round(fy * (height - 1)))
        y0, y1 = max(cy - BACKDROP_PATCH_HALF, 0), min(cy + BACKDROP_PATCH_HALF + 1, height)
        x0, x1 = max(cx - BACKDROP_PATCH_HALF, 0), min(cx + BACKDROP_PATCH_HALF + 1, width)
        valid = ~excluded[y0:y1, x0:x1]
        out[key] = round(float(np.median(lum[y0:y1, x0:x1][valid])), 4) if valid.mean() >= 0.5 else None
    return out


def image_stats(beauty: Path, mask: Path, n: int = 4, bar: bool = False) -> dict:
    """Read a render back and report what a buyer will actually see.

    ``mask`` is the wall-mask pass: alpha is the subject's coverage, red is 1 on faces with
    |N.z| < 0.5 (walls and steep facet segments), green the chamfer facets, blue a bar's ground
    surfaces.  ``bar`` (3.8.1) adds the side-face luminance and the dark-dot counts.
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
        facets = selection & (mask_px[..., 1] > 0.5)
        if facets.any():
            centre_row = 0.5 * (rows.min() + rows.max())
            row_index = np.arange(height)[:, None] * np.ones((1, width), dtype=int)
            facet_stats = {"pixels": int(facets.sum()),
                           "fraction_of_object": round(float(facets.sum() / selection.sum()), 5),
                           "note": "pixels of chamfer facets (0.5 <= |N.z| < 0.95); near = image rows below "
                                   "the object's bbox centre (the camera-facing half in the hero)"}
            for key, pick in (("all", facets), ("near", facets & (row_index > centre_row)),
                              ("far", facets & (row_index <= centre_row))):
                if pick.any():
                    values = lum[pick]
                    facet_stats[key] = {
                        "pixels": int(pick.sum()),
                        "mean": round(float(values.mean()), 4),
                        "p05": round(float(np.percentile(values, 5)), 4),
                        "p50": round(float(np.percentile(values, 50)), 4),
                        "p95": round(float(np.percentile(values, 95)), 4),
                        "fraction_below_0_05": round(float((values < FACET_GATE["dark_below"]).mean()), 5),
                    }
            stats["facet_luminance"] = facet_stats
        coat = selection & (mask_px[..., 0] <= 0.5) & (mask_px[..., 1] <= 0.5) & (mask_px[..., 2] <= 0.5)
        if coat.any():
            coat_lum = lum[coat]
            stats["coat_luminance"] = {
                "pixels": int(coat.sum()),
                "fraction_of_object": round(float(coat.sum() / selection.sum()), 5),
                "mean": round(float(coat_lum.mean()), 4),
                "p05": round(float(np.percentile(coat_lum, 5)), 4),
                "p50": round(float(np.percentile(coat_lum, 50)), 4),
                "p95": round(float(np.percentile(coat_lum, 95)), 4),
                "note": ("pixels of flat faces (|N.z| >= 0.95) that are not a bar's ground surfaces: a star's plate, a "
                         "bar's up-facing faces - the coat under the same light (pack_consistency, like with like)"),
            }
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
        stats["backdrop_points"] = backdrop_points(lum, alpha > 0.02)
        if bar:
            side = selection & (mask_px[..., 0] > 0.5) & (mask_px[..., 2] <= 0.5)
            if side.any():
                side_lum = lum[side]
                side_rgb = rgb[side].mean(axis=0)
                stats["bar_wall_luminance"] = {
                    "pixels": int(side.sum()),
                    "fraction_of_object": round(float(side.sum() / selection.sum()), 5),
                    "mean": round(float(side_lum.mean()), 4),
                    "p05": round(float(np.percentile(side_lum, 5)), 4),
                    "p50": round(float(np.percentile(side_lum, 50)), 4),
                    "p95": round(float(np.percentile(side_lum, 95)), 4),
                    "mean_rgb": [round(float(v), 4) for v in side_rgb],
                    "rgb_spread": round(float((side_rgb.max() - side_rgb.min()) / max(side_rgb.mean(), 1e-6)), 4),
                    "note": "a bar's side faces: |N.z| < 0.5 and not ground (mask red, not blue)",
                }
                stats["bar_wall_dots"] = dark_dots(lum, side)
            coat_region = selection & (mask_px[..., 0] <= 0.5) & (mask_px[..., 1] <= 0.5) & (mask_px[..., 2] <= 0.5)
            if coat_region.any():
                stats["coat_dots"] = dark_dots(lum, coat_region)
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


def facet_gate(stats: dict, side: str = "near") -> dict:
    """Chamfer-facet gate: the ground edges read as steel catching light, not an ink band."""
    facet = (stats.get("facet_luminance") or {}).get(side)
    if not facet:
        return {"passed": False, "detail": f"no {side} facet pixels measured"}
    passed = facet["p50"] >= FACET_GATE["p50_min"] and facet["fraction_below_0_05"] <= FACET_GATE["dark_fraction_max"]
    return {"passed": bool(passed), "side": side, "p50": facet["p50"], "p50_min": FACET_GATE["p50_min"],
            "fraction_below_0_05": facet["fraction_below_0_05"],
            "dark_fraction_max": FACET_GATE["dark_fraction_max"]}


def plate_gate(stats: dict, consistency_class: str = "plate") -> dict:
    """Object p50 and mean of a beauty shot inside the rig's PLATE_BAND / PLATE_MEAN_BAND.

    Like with like (3.8): for a BAR the gate reads its coat pixels (``coat_luminance``: the up-facing
    coat faces, what a star's plate is), because 55-65 % of a bar's hero pixels are the side face that
    mirrors the floor next to it (a vertical 6 mm coat face; a star's walls are a few per cent), which
    no composition removes (hero yaw 25 / 40 / 55 deg: whole-object p50 0.351 / 0.345 / 0.341).  The
    whole-object figures are reported beside it.
    """
    if consistency_class == "bar":
        coat = stats.get("coat_luminance") or {}
        lum = stats.get("object_luminance") or {}
        p50, mean = coat.get("p50"), coat.get("mean")
        passed = (p50 is not None and PLATE_BAND[0] <= p50 <= PLATE_BAND[1]
                  and mean is not None and PLATE_MEAN_BAND[0] <= mean <= PLATE_MEAN_BAND[1])
        return {"passed": bool(passed), "p50": p50, "band": list(PLATE_BAND), "mean": mean,
                "mean_band": list(PLATE_MEAN_BAND), "measured_on": "coat pixels (bar: like with like)",
                "whole_object": {"p50": lum.get("p50"), "mean": lum.get("mean"),
                                 "in_band": bool(lum.get("p50") is not None
                                                 and PLATE_BAND[0] <= lum["p50"] <= PLATE_BAND[1]
                                                 and PLATE_MEAN_BAND[0] <= lum["mean"] <= PLATE_MEAN_BAND[1]),
                                 "note": "information for a bar"}}
    lum = stats.get("object_luminance") or {}
    p50, mean = lum.get("p50"), lum.get("mean")
    passed = (p50 is not None and PLATE_BAND[0] <= p50 <= PLATE_BAND[1]
              and mean is not None and PLATE_MEAN_BAND[0] <= mean <= PLATE_MEAN_BAND[1])
    return {"passed": bool(passed), "p50": p50, "band": list(PLATE_BAND), "mean": mean,
            "mean_band": list(PLATE_MEAN_BAND)}


def bar_wall_gate(stats: dict) -> dict:
    """A bar's hero side faces carry no pepper: isolated dark dots per 10k interior px within BAR_WALL_DOT_GATE."""
    dots = stats.get("bar_wall_dots")
    if not dots:
        return {"passed": False, "detail": "no side-face interior measured"}
    key = f"{int(round((1.0 - BAR_WALL_DOT_GATE['threshold']) * 100))}pct"
    value = dots[key]["dots_per_10k_px"]
    return {"passed": bool(value <= BAR_WALL_DOT_GATE["max_per_10k"]), "dots_per_10k_px": value,
            "threshold": f"{key} darker than the 7 x 7 face median", "max_per_10k": BAR_WALL_DOT_GATE["max_per_10k"],
            "interior_px": dots["interior_px"],
            "reference": "visual review: stars' plates 0.03-0.08, the reference asset 0.74, the 3.8.0 spike 8.28"}


def pack_consistency(reports: dict) -> dict:
    """The forms against each other: hero and top p50 and mean per form, spread, and a gate.

    ``reports`` maps form name -> its report.  Passes when every form's hero and top p50 AND
    mean lie within PACK_P50_TOLERANCE of the FIXED ``PACK_ANCHOR`` (one rig, one product
    line) and, when every anchor form is in the build, their current mean has not drifted
    more than PACK_ANCHOR_DRIFT_MAX from the anchor (a stale anchor after a rig or material
    change).  The mean is gated as well as the p50 because a form's p50 can sit on the pack's
    while its mean drifts (the first style pass: hero p50 within 0.024, mean 14 % apart).

    Reported as well: every form's offset and headroom (tolerance - |offset|) against the
    anchor, the smallest headroom and where it is, and - information only, the pre-3.7.1
    rule - the same figures against the mean of the forms in this build (``all_forms``; the
    old top-level ``<shot>_<stat>_mean / _spread / _max_offset`` keys are kept).
    """
    tol = PACK_P50_TOLERANCE
    out = {"tolerance": tol,
           "rule": ("like with like (3.8): every PLATE form's hero and top p50 and mean within the tolerance of the "
                    "fixed anchor (the mean of the forms frozen at restyle pass 2); a BAR's coat pixels (its up-facing "
                    "faces) within the tolerance of the anchor forms' coat pixels (PACK_COAT_ANCHOR) and (3.8.1) its "
                    "hero side faces' p50 within the tolerance of the anchor forms' hero wall p50 (PACK_WALL_ANCHOR), "
                    "its whole-object figures reported as information; (3.8.1) every form's hero backdrop at fixed "
                    "frame points within the anchor forms' range (PACK_BACKDROP_ANCHOR); the all-forms mean is "
                    "information only"),
           "anchor": {"forms": list(PACK_ANCHOR["forms"]), "source": PACK_ANCHOR["source"],
                      "hero": dict(PACK_ANCHOR["hero"]), "top": dict(PACK_ANCHOR["top"])},
           "coat_anchor": {"forms": list(PACK_COAT_ANCHOR["forms"]), "source": PACK_COAT_ANCHOR["source"],
                           "hero": dict(PACK_COAT_ANCHOR["hero"]), "top": dict(PACK_COAT_ANCHOR["top"])},
           "classes": {}, "hero": {}, "top": {}, "coat": {"hero": {}, "top": {}}, "bar_whole_object": {"hero": {}, "top": {}}}
    for name, report in reports.items():
        stats = report.get("render_stats") or {}
        cls = "bar" if report.get("geometry") == "bar" else "plate"
        out["classes"][name] = cls
        for shot in ("hero", "top"):
            key = f"{name}_{'persp' if shot == 'hero' else 'top'}"
            lum = (stats.get(key) or {}).get("object_luminance") or {}
            coat = (stats.get(key) or {}).get("coat_luminance") or {}
            if coat:
                out["coat"][shot][name] = {"p50": coat.get("p50"), "mean": coat.get("mean"),
                                           "fraction_of_object": coat.get("fraction_of_object")}
            if lum and cls == "plate":
                out[shot][name] = {"p50": lum.get("p50"), "mean": lum.get("mean")}
            elif lum:
                out["bar_whole_object"][shot][name] = {
                    "p50": lum.get("p50"), "mean": lum.get("mean"),
                    "offset_vs_anchor": {st: round(lum.get(st) - PACK_ANCHOR[shot][st], 4) for st in ("p50", "mean")},
                    "note": ("information only: about half of a bar's hero pixels are its vertical side face, which "
                             "mirrors the floor beside it, not the key (gated like with like: bar_walls_vs_wall_anchor)"
                             if shot == "hero" else
                             "information only: a bar seen from above is its top face, the polished point and the "
                             "tail facets (no side face shows); its coat pixels are the gated figure")}
    passed = True
    # --- bars: the coat pixels against the anchor forms' coat pixels
    bar_offsets = {"hero": {}, "top": {}}
    for name, cls in out["classes"].items():
        if cls != "bar":
            continue
        for shot in ("hero", "top"):
            coat = out["coat"][shot].get(name)
            if not coat:
                passed = False
                bar_offsets[shot][name] = {"error": "no coat pixels measured"}
                continue
            for stat in ("p50", "mean"):
                off = coat[stat] - PACK_COAT_ANCHOR[shot][stat]
                bar_offsets[shot].setdefault(name, {})[stat] = {"offset": round(off, 4) + 0.0,
                                                                "headroom": round(tol - abs(off), 4)}
                passed = passed and abs(off) <= tol
    out["bar_coat_vs_coat_anchor"] = bar_offsets
    # --- bars (3.8.1): the side faces against the anchor forms' walls, like with like
    wall_offsets = {}
    for name, cls in out["classes"].items():
        if cls != "bar":
            continue
        side = ((reports[name].get("render_stats") or {}).get(f"{name}_persp") or {}).get("bar_wall_luminance") or {}
        if side.get("p50") is None:
            passed = False
            wall_offsets[name] = {"error": "no side-face pixels measured"}
            continue
        off = side["p50"] - PACK_WALL_ANCHOR["hero"]["p50"]
        wall_offsets[name] = {"p50": side["p50"], "offset": round(off, 4) + 0.0, "headroom": round(tol - abs(off), 4),
                              "rgb_spread": side.get("rgb_spread")}
        passed = passed and abs(off) <= tol
    out["wall_anchor"] = {"forms": list(PACK_WALL_ANCHOR["forms"]), "source": PACK_WALL_ANCHOR["source"],
                          "hero": dict(PACK_WALL_ANCHOR["hero"])}
    out["bar_walls_vs_wall_anchor"] = wall_offsets
    # --- every form (3.8.1): the hero backdrop at fixed frame points against the anchor forms' range
    btol = BACKDROP_TOLERANCE
    backdrop = {}
    for name in out["classes"]:
        points = ((reports[name].get("render_stats") or {}).get(f"{name}_persp") or {}).get("backdrop_points")
        if not points:
            continue
        misses, worst = {}, None
        for key, (lo, hi) in PACK_BACKDROP_ANCHOR["hero"].items():
            value = points.get(key)
            if value is None:
                continue
            off = 0.0 if lo <= value <= hi else (value - hi if value > hi else value - lo)
            room = round(btol - abs(off), 4)
            if worst is None or room < worst["headroom"]:
                worst = {"point": key, "value": value, "anchor_range": [lo, hi], "headroom": room}
            if abs(off) > btol:
                misses[key] = {"value": value, "anchor_range": [lo, hi], "off_by": round(off, 4)}
        backdrop[name] = {"passed": not misses, "misses": misses, "min_headroom": worst,
                          "points_measured": sum(1 for v in points.values() if v is not None)}
        passed = passed and not misses
    out["backdrop"] = {"points": {k: list(v) for k, v in BACKDROP_POINTS.items()}, "tolerance": btol,
                       "anchor": {k: list(v) for k, v in PACK_BACKDROP_ANCHOR["hero"].items()},
                       "anchor_source": PACK_BACKDROP_ANCHOR["source"], "per_form": backdrop,
                       "rule": ("hero backdrop luminance (11 x 11 px median, object excluded) at fixed frame points "
                                "within the anchor forms' range +- the tolerance; points under the object skipped")}
    offsets = {"hero": {}, "top": {}}
    headroom = {"hero": {}, "top": {}}
    all_forms = {"offsets": {"hero": {}, "top": {}}, "headroom": {"hero": {}, "top": {}}}
    worst = None
    worst_all = None
    all_forms_ok = True
    for shot in ("hero", "top"):
        for stat in ("p50", "mean"):
            values = {n: v[stat] for n, v in out[shot].items() if v.get(stat) is not None}
            if not values:
                continue
            centre = PACK_ANCHOR[shot][stat]
            for name, value in values.items():
                off = value - centre
                room = tol - abs(off)
                offsets[shot].setdefault(name, {})[stat] = round(off, 4) + 0.0
                headroom[shot].setdefault(name, {})[stat] = round(room, 4)
                passed = passed and abs(off) <= tol
                if worst is None or room < worst["headroom"]:
                    worst = {"headroom": round(room, 4), "form": name, "shot": shot, "stat": stat}
            # information only: the pre-3.7.1 rule, centred on the mean of the forms in this build
            mean = sum(values.values()) / len(values)
            out[f"{shot}_{stat}_mean"] = round(mean, 4)
            out[f"{shot}_{stat}_spread"] = round(max(values.values()) - min(values.values()), 4)
            out[f"{shot}_{stat}_max_offset"] = round(max(abs(v - mean) for v in values.values()), 4)
            for name, value in values.items():
                room = tol - abs(value - mean)
                all_forms["offsets"][shot].setdefault(name, {})[stat] = round(value - mean, 4)
                all_forms["headroom"][shot].setdefault(name, {})[stat] = round(room, 4)
                all_forms_ok = all_forms_ok and room >= 0.0
                if worst_all is None or room < worst_all["headroom"]:
                    worst_all = {"headroom": round(room, 4), "form": name, "shot": shot, "stat": stat}
    out["offsets_vs_anchor"] = offsets
    out["headroom_vs_anchor"] = headroom
    out["min_headroom_vs_anchor"] = worst
    all_forms.update({"min_headroom": worst_all, "would_pass": bool(all_forms_ok),
                      "note": "pre-3.7.1 rule (centre = mean of the forms in this build), information only"})
    out["all_forms"] = all_forms
    present = [f for f in PACK_ANCHOR["forms"] if f in out["hero"] and f in out["top"]]
    drift = None
    stale = False
    if len(present) == len(PACK_ANCHOR["forms"]):
        drift = {}
        for shot in ("hero", "top"):
            for stat in ("p50", "mean"):
                now = sum(out[shot][f][stat] for f in present) / len(present)
                drift[f"{shot}_{stat}"] = round(now - PACK_ANCHOR[shot][stat], 4) + 0.0   # no -0.0
        stale = any(abs(v) > PACK_ANCHOR_DRIFT_MAX for v in drift.values())
    coat_drift = None
    if all(f in out["coat"]["hero"] and f in out["coat"]["top"] for f in PACK_COAT_ANCHOR["forms"]):
        coat_drift = {}
        for shot in ("hero", "top"):
            for stat in ("p50", "mean"):
                now = sum(out["coat"][shot][f][stat] for f in PACK_COAT_ANCHOR["forms"]) / len(PACK_COAT_ANCHOR["forms"])
                coat_drift[f"{shot}_{stat}"] = round(now - PACK_COAT_ANCHOR[shot][stat], 4) + 0.0
        stale = stale or any(abs(v) > PACK_ANCHOR_DRIFT_MAX for v in coat_drift.values())
    out["anchor_drift"] = {"forms_present": present, "drift": drift, "coat": coat_drift, "max": PACK_ANCHOR_DRIFT_MAX,
                           "anchor_stale": bool(stale),
                           "note": ("the anchor forms' current mean minus PACK_ANCHOR (checked only when all of them "
                                    "are in the build); a stale anchor means the rig or material moved every form: "
                                    "re-derive PACK_ANCHOR with that change")}
    out["passed"] = bool(passed and not stale)
    return out


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
    saved_rotation = lod0.rotation_euler.copy()
    saved_location = lod0.location.copy()
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

        def shoot(name: str, camera, lights, hide_now=(), show=(), ground=True, card=False, band=False,
                  denoise=True):
            for light in rig["hero_lights"] + rig["top_lights"]:
                light.hide_render = light not in lights
            for obj in hide_now:
                obj.hide_render = True
            for obj in show:
                obj.hide_render = False
            rig["ground"].hide_render = not ground
            rig["card"].hide_render = not card
            rig["band"].hide_render = not band
            scene.render.film_transparent = False
            scene.cycles.samples = samples
            scene.cycles.use_denoising = denoise
            beauty = Path(render_to(render_dir / f"{name}.png", camera))
            # Matching mask pass: alpha = coverage (ground gone, film transparent), red =
            # walls, via a flat emission override and the Standard view transform.
            rig["ground"].hide_render = True
            rig["card"].hide_render = True
            rig["band"].hide_render = True
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
                stats[name] = image_stats(beauty, mask, o.n, bar=bool(getattr(o, "bar_wall_gate", False)))
            except Exception as exc:                                # pragma: no cover
                stats[name] = {"error": f"{type(exc).__name__}: {exc}"}

        if beauty_material is not None:
            lod0.data.materials[0] = beauty_material
        yaw = float(getattr(o, "hero_yaw_deg", 0.0) or 0.0)
        if yaw:
            lod0.rotation_euler = (0.0, 0.0, math.radians(yaw))     # the hero only: the object turns, the rig stays
            bpy.context.view_layer.update()
        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        placement = None
        if getattr(o, "hero_rig_match", False):
            placement = place_for_shift(rig["cam_persp"], lod0, res_x, res_y)   # 3.8.1: the anchor forms' lens shift
            composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y, steps=1)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        rig_scale, saved_lamps = 1.0, []
        if getattr(o, "hero_rig_match", False):
            # 3.8.1: the hero lamps follow the fitted camera distance (see the module docstring); restored below
            rig_scale = rig["cam_persp"].location.length / HERO_RIG_REFERENCE_M
            for light in rig["hero_lights"]:
                saved_lamps.append((light, light.location.copy(), light.data.size, light.data.size_y,
                                    light.data.energy))
                light.location = light.location * rig_scale
                light.data.size *= rig_scale
                light.data.size_y *= rig_scale
                light.data.energy *= rig_scale ** 2
            bpy.context.view_layer.update()
        shoot(f"{form}_persp", rig["cam_persp"], rig["hero_lights"], card=True)
        for light, location, size, size_y, energy in saved_lamps:
            light.location, light.data.size, light.data.size_y, light.data.energy = location, size, size_y, energy
        if saved_lamps:
            bpy.context.view_layer.update()
        if yaw or placement is not None:
            lod0.rotation_euler = saved_rotation
            lod0.location = saved_location
            bpy.context.view_layer.update()
        shoot(f"{form}_top", rig["cam_top"], rig["top_lights"], band=True)
        if beauty_material is not None:
            lod0.data.materials[0] = saved_material
        grind_labels = [text.replace(chr(10), "   ") for text in (lod_labels or [])]
        grind = render_lod_grind(form, o, [lod0] + list(lods), beauty_material, rig, render_dir, diag_dir,
                                 samples, res_x, res_y, grind_labels)
        written[f"{form}_lodgrind"] = grind["path"]

        # --- wireframe and LOD strip: flat-lit emissive copies, no lights, dark field.
        top_px_per_m = res_x / rig["cam_top"].data.ortho_scale
        solid, wires = wire_pair(lod0, coll, "Wire", thickness=WIRE_PX / top_px_per_m)
        stack_y = getattr(o, "lod_strip_axis", "x") == "y"    # a long form (the spike): LODs top to bottom
        inset_k = float(getattr(o, "lod_section_inset", 0.0) or 0.0) if stack_y else 0.0
        inset = 2.0 * o.a * inset_k if inset_k else 0.0      # 3.8.1: the end-on section's side at the inset scale
        bar_dx = 0.0
        if stack_y:
            row_h = max(rig["span_y"], inset)
            spacing = row_h + LOD_STRIP_Y_GAP
            total_w = rig["span_x"] + (LOD_STRIP_INSET_GAP + inset if inset_k else 0.0)
            if inset_k:
                bar_dx = -0.5 * (LOD_STRIP_INSET_GAP + inset)   # the bars move left, the insets sit on their right
            fit_ortho(rig["cam_lod"], total_w, len(lods) * spacing + row_h + LOD_STRIP_Y_GAP, 0.86, 0.90,
                      res_x, res_y)
            rig["cam_lod"].location.x = bar_dx + 0.5 * (getattr(o, "x_butt", -0.5 * rig["span_x"])
                                                        + getattr(o, "x_tip", 0.5 * rig["span_x"])) + (
                0.5 * (LOD_STRIP_INSET_GAP + inset) if inset_k else 0.0)
        else:
            spacing = rig["span_x"] + LOD_STRIP_GAP
            fit_ortho(rig["cam_lod"], len(lods) * spacing + rig["span_x"], rig["span_y"], 0.90, 0.80,
                      res_x, res_y)
        lod_px_per_m = res_x / rig["cam_lod"].data.ortho_scale
        strip_objects: List = []
        inset_info = None
        for i, obj in enumerate([lod0] + list(lods)):
            offset = ((bar_dx, (0.5 * len(lods) - i) * spacing, 0.0) if stack_y
                      else ((i - 0.5 * len(lods)) * spacing, 0.0, 0.0))
            strip_objects += list(wire_pair(obj, coll, f"Lod{i}", offset=offset,
                                            thickness=WIRE_PX / lod_px_per_m))
            if inset_k:
                # the butt end seen end-on: R_y(90 deg) turns -X up toward the ortho camera, x inset_k; placed right
                # of the bar and well below it in z (under the camera's clip start, off every other object)
                basis = Matrix.Scale(inset_k, 4) @ Matrix.Rotation(math.radians(90.0), 4, "Y")
                cx = bar_dx + o.x_tip + LOD_STRIP_INSET_GAP + 0.5 * inset
                cz = -0.05 - inset_k * (-o.x_butt)
                strip_objects += list(wire_pair(obj, coll, f"LodEnd{i}", offset=(cx, offset[1], cz),
                                                thickness=WIRE_PX / lod_px_per_m / inset_k, basis=basis))
                inset_info = {"scale": inset_k, "view": "the butt end, end-on (-X toward the camera)",
                              "side_mm": round(inset * 1000.0, 3)}
        labels = []
        if lod_labels:
            frame_h = rig["cam_lod"].data.ortho_scale * res_y / res_x
            size = 0.036 * frame_h
            for i, text in enumerate(lod_labels):
                if stack_y:
                    y = (0.5 * len(lods) - i) * spacing
                    bar_mid = bar_dx + 0.5 * (getattr(o, "x_butt", 0.0) + getattr(o, "x_tip", 0.0)) if inset_k else 0.0
                    labels.append(label(coll, f"PREVIEW_LodLabel{i}", text.replace(chr(10), "   "),
                                        (bar_mid, y - 0.5 * rig["span_y"] - 0.02 * frame_h, 0.001), size))
                    if inset_k:
                        cx = bar_dx + o.x_tip + LOD_STRIP_INSET_GAP + 0.5 * inset
                        labels.append(label(coll, f"PREVIEW_LodEndLabel{i}", f"butt end x{inset_k:g}",
                                            (cx, y - 0.5 * inset - 0.02 * frame_h, 0.001), 0.75 * size))
                else:
                    x = (i - 0.5 * len(lods)) * spacing
                    labels.append(label(coll, f"PREVIEW_LodLabel{i}", text,
                                        (x, -0.5 * rig["span_y"] - 0.05 * frame_h, 0.001), size))
            bpy.context.view_layer.update()
            if stack_y:
                label_bottom = min(obj.location.y - obj.dimensions.y for obj in labels)
                top = 0.5 * len(lods) * spacing + 0.5 * max(rig["span_y"], inset)
                rig["cam_lod"].location.y = 0.5 * (top + label_bottom)
            else:
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
            "hero_yaw_deg": yaw,
            "hero_rig_scale": round(rig_scale, 6),
            "hero_placement": placement,
            "hero_rig_reference_m": HERO_RIG_REFERENCE_M if rig_scale != 1.0 else None,
            "lod_strip_section_inset": inset_info,
            "lod_strip_axis": "y" if stack_y else "x",
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
            "hero_top_panel": {"power_w": HERO_TOP_W, "size_m": [0.70, 0.70], "elevation_deg": 80.0,
                               "azimuth_deg": 158.0, "distance_m": 0.70,
                               "visibility": "glossy rays only (visible_diffuse off): the camera-facing chamfer "
                                             "facets' mirror direction"},
            "top_facet_band": {"strength": TOP_BAND_STRENGTH, "colour": list(TOP_BAND_COLOUR),
                               "elevation_deg": list(TOP_BAND_ELEVATION), "radius_m": TOP_BAND_RADIUS,
                               "visibility": "glossy rays only; rotationally symmetric cone band the 26.6 deg "
                                             "facets mirror when seen straight down"},
            "beauty_material": beauty_material.name if beauty_material is not None else saved_material.name,
            "lod_grind_closeup": grind,
            "lod_labels": list(lod_labels or []),
        }
        return written, stats, rig_info
    finally:
        lod0.rotation_euler = saved_rotation
        lod0.location = saved_location
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


__all__ = ["BACKDROP_POINTS", "BAR_WALL_DOT_GATE", "HERO_RIG_REFERENCE_M", "PACK_BACKDROP_ANCHOR", "PACK_WALL_ANCHOR",
           "bar_wall_gate", "dark_dots", "backdrop_points",
           "FACET_GATE", "PACK_ANCHOR", "PACK_ANCHOR_DRIFT_MAX", "PACK_COAT_ANCHOR", "PACK_P50_TOLERANCE", "PLATE_BAND",
           "PLATE_MEAN_BAND", "SHOT_SUFFIXES", "TOP_FRAME_HEIGHT",
           "WALL_GATE", "build_preview_rig", "centre_perspective", "facet_gate", "fit_ortho", "fit_perspective",
           "image_stats", "label", "load_pixels", "pack_consistency", "plate_gate", "projected_bbox", "render_previews",
           "render_to", "ring_lamp_count", "setup_render", "solve_depth_of_field", "wall_gate", "wire_pair"]
