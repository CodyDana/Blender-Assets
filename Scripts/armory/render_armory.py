"""Cycles review renders of the assembled armory (Assets/Armory/ArmoryKit.blend) from WorkFiles/armory/build/layout.json.

Adds the light table and the cameras, then renders to WorkFiles/armory/build/renders/<camera>_<preset>.png.
Run: blender -b --factory-startup Assets/Armory/ArmoryKit.blend --python Scripts/armory/render_armory.py --
     [--cams C1_EntryReveal,...] [--samples 96] [--res 1600x900] [--out DIR] [--preset golden|gallery]
     [--exposure EV] [--look NAME] [--fog DENSITY] [--no-fog] [--no-bloom]
(--factory-startup keeps the user's add-ons, e.g. the BlenderMCP add-on, out of the headless process.)

Look pass (2026-09-27, WorkFiles/armory/build/BUILD_NOTES.md): powers retuned for the dark-timber room, practicals
hidden from camera, a haze volume confined to the sun's shafts (only the sun scatters), a warm evening sky behind the
lattice windows, AgX Medium High Contrast at +0.4 EV matched to the LOOK reference, and a mild bloom (the review
stand-in for Unreal's default bloom).
Fix round 1 (same notes file): shaft prisms read from layout.json "openings", sun 0.15 deg, haze 0.006 faded out
below +2.7 m, an exterior tree line for camera and glossy rays, OIDN high quality, exposure +0.8.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "armory" / "build"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


# Blender watts per role (review renders only; Unreal sets its own units). "glow" is watts per metre of plinth
# perimeter. PRESET_SCALE multiplies a role per preset (the plan: Golden Hour runs the gallery lights at about 60 %).
# f2: wash 35 -> 6 (judge delta 5: the painting was the brightest thing in the room; C1 measured its paper at 0.93
# display value against reference 2's 0.48-0.56); rack 20 kept, and the new
# alcove spots (judge delta 8: the rear alcoves glow in reference 2)
POWER = {"case": 40.0, "panel": 14.0, "rack": 9.0, "lantern": 8.0, "down": 80.0, "wash": 6.0, "glow": 8.0,
         "alcove": 12.0,   # f2: panel 40 -> 22 (the cream backs clipped to white at 7-10 cm from the lens)
         "banner": 60.0,   # f1: 30 -> 60 (the cloth read as black wall)   # building stage: a narrow spot grazing each banner
         "sill": 14.0}     # f1: a narrow spot on each sill vase
PRESET_SCALE = {
    "golden": {"down": 1.3, "case": 0.8, "panel": 0.85},   # building r4: case 0.85 -> 0.6 (decks read pink); f1: down 0.6 -> 0.9, case 0.6 -> 0.8 (black decks; C1 mid-tones)
    "gallery": {},
}
SUN = {"golden": 90.0, "gallery": 0.0}   # look3: 60 -> 90 (the salmon patches came from the pink floor, fixed)   # f2: 100 -> 60 (two suns, broader patches; C1 p90 0.83 against 0.71, and the hot patches tone-mapped salmon-white)         # W/m2: the floor albedo is about 0.05 (linear), so the lattice patch needs a strong key
SKY = {  # colour, strength of the world seen through the windows
    "golden": ((0.90, 0.86, 0.80), 2.2),   # building stage: less orange fill (was 1.0, 0.66, 0.38); f1: cooler still
    "gallery": ((0.55, 0.62, 0.75), 0.35),
}
FOG = {"golden": 0.0004, "gallery": 0.0}   # look3: 0.0008 -> 0.0004 (grey veil on the left wall)   # f2: 0.0015 -> 0.0008 (judge delta 2: less haze and veil)   # building stage: 0.003 -> 0.0015 (reference 2 is crisp)   # look2: crisper, as reference 2         # fix1: 0.014 -> 0.006 (the review read the shafts as a sepia haze)
SUN_ANGLE_DEG = 0.5    # f1: 0.15 -> 0.5 (judge: soften the patch edges slightly)   # fix1: 0.8 -> 0.15. At 0.8 deg the ~7 m throw blurred the 25 mm lattice bars into one soft patch
# f1: the niches are no longer emissive lightboxes and the decks are black: golden +0.8 -> +2.4 with AgX Very High
# Contrast (was Medium High): C1 1086 x 815 p10 0.065 / p90 0.710 against the reference's 0.060 / 0.711
EXPOSURE = {"golden": 2.4, "gallery": 2.4}
LOOK = "AgX - Very High Contrast"
_PREV_EXPOSURE = {"golden": 0.8, "gallery": 0.8}   # exterior stage: golden 0.6 -> 0.8 (the emissive garden backdrop that lit the entry is gone; C1 mean 0.273 -> 0.294, was 0.299)   # building stage: 0.2 / 0.5 -> 0.6 / 0.8 (C1 p50 0.16 vs reference 0.29)   # look2: darker, as reference 2   # fix1: +0.4 -> +0.8 with the dark decks and niches (C1 stats in BUILD_NOTES)
BLOOM = (2.0, 0.2)   # f1: threshold 1.2 -> 2.0, strength 0.35 -> 0.2 (judge: milky, heavy bloom)


def kelvin_rgb(k):
    """Tanner Helland's blackbody fit, returned linear-ish 0-1."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# clear openings; main() replaces them with layout.json "openings" (fix1: the south pair moved to Y 5.25-6.75)
WINDOWS_Y = ((5.25, 6.75), (8.25, 9.75))   # lattice window openings on both long walls, sill +3.50, head +4.40
WINDOW_Z = (3.50, 4.40)
DOOR_X, DOOR_Z = (3.25, 4.75), (0.0, 2.0)
ROOM = (8.0, 12.0, 4.8)   # building stage: main() replaces it with layout.json "room" (12 x 16 m)


def _in_range(nt, value, lo, hi):
    """1.0 where lo < value < hi, else 0.0 (shader math)."""
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "GREATER_THAN"
    a.inputs[1].default_value = lo
    nt.links.new(value, a.inputs[0])
    b = nt.nodes.new("ShaderNodeMath")
    b.operation = "LESS_THAN"
    b.inputs[1].default_value = hi
    nt.links.new(value, b.inputs[0])
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    nt.links.new(a.outputs[0], m.inputs[0])
    nt.links.new(b.outputs[0], m.inputs[1])
    return m.outputs[0]


def _math(nt, op, x, y):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((x, y)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def shaft_mask(nt, d, pad=0.12):
    """f2: d may be a list of sun directions (the union of their shafts)."""
    if isinstance(d, (list, tuple)):
        outs = [shaft_mask(nt, di, pad) for di in d]
        out = outs[0]
        for m in outs[1:]:
            out = _math(nt, "MAXIMUM", out, m)
        return out
    return _shaft_mask_one(nt, d, pad)


def _shaft_mask_one(nt, d, pad=0.12):
    """1.0 inside the prisms swept by the sun through the window openings (and the door), else 0.0.

    Haze outside those prisms gets no sunlight (the practicals do not scatter, see main), so dropping it changes
    nothing visible, but it lets Cycles place its scatter samples inside the shafts: a uniform thin volume leaves the
    shafts grainy at 96 samples on the close cameras."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])   # the fog object sits at the origin: object = world metres
    px, py, pz = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    masks = []
    if abs(d.x) > 1e-3:   # the long wall the sun enters by (west if it travels +X), wall mid-plane
        xw = -0.15 if d.x > 0 else ROOM[0] + 0.15
        t = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", px, xw), d.x)
        qy = _math(nt, "SUBTRACT", py, _math(nt, "MULTIPLY", t, d.y))
        qz = _math(nt, "SUBTRACT", pz, _math(nt, "MULTIPLY", t, d.z))
        inz = _in_range(nt, qz, WINDOW_Z[0] - pad, WINDOW_Z[1] + pad)
        for y0, y1 in WINDOWS_Y:
            masks.append(_math(nt, "MULTIPLY", inz, _in_range(nt, qy, y0 - pad, y1 + pad)))
    if d.y > 1e-3:        # the south door, if the sun travels toward the platform
        s = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", py, -0.15), d.y)
        qx = _math(nt, "SUBTRACT", px, _math(nt, "MULTIPLY", s, d.x))
        qz = _math(nt, "SUBTRACT", pz, _math(nt, "MULTIPLY", s, d.z))
        masks.append(_math(nt, "MULTIPLY", _in_range(nt, qx, DOOR_X[0] - pad, DOOR_X[1] + pad),
                           _in_range(nt, qz, DOOR_Z[0] - pad, DOOR_Z[1] + pad)))
    out = masks[0]
    for m in masks[1:]:
        out = _math(nt, "MAXIMUM", out, m)
    return out


def add_fog(sc, density, sun_dir=None):
    """A room-sized volume box inside the walls; with a sun, its density is confined to the sun's shafts."""
    me = bpy.data.meshes.new("Review_FogVolume")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = 0.02 + (v.co.x + 0.5) * (ROOM[0] - 0.04)
        v.co.y = 0.02 + (v.co.y + 0.5) * (ROOM[1] - 0.04)
        v.co.z = 0.005 + (v.co.z + 0.5) * (ROOM[2] - 0.08)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Review_FogVolume", me)
    sc.collection.objects.link(ob)
    mat = bpy.data.materials.new("Review_Fog")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (1.0, 0.93, 0.85, 1)
    vol.inputs["Anisotropy"].default_value = float(arg("--aniso", "0.35"))
    if sun_dir is not None and "--uniform-fog" not in ARGS:
        dens = _math(nt, "MULTIPLY", shaft_mask(nt, sun_dir), density)
        # fix1: the haze fades out below +2.7 m (none under +1.2): the shafts read in the air under the windows, and
        # the low haze that lit up in front of the case glass (C3 and C10 speckle on the dark decks) is gone
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sz = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sz.inputs[0])
        fade = nt.nodes.new("ShaderNodeMapRange")
        fade.inputs["From Min"].default_value = float(arg("--haze-floor", "1.2"))
        fade.inputs["From Max"].default_value = float(arg("--haze-floor", "1.2")) + 1.5
        nt.links.new(sz.outputs[2], fade.inputs["Value"])
        dens = _math(nt, "MULTIPLY", dens, fade.outputs["Result"])
        # seen by camera and through-glass rays only: a glossy reflection (the 4-8 % Fresnel off the case glass, the
        # satin floor) gets a handful of the 96 samples and turns the reflected shafts into speckle
        lp = nt.nodes.new("ShaderNodeLightPath")
        # fix1: camera rays only by default (a cleanup; the deck speckle itself was fixed by the height fade below)
        if "--haze-through-glass" in ARGS:
            seen = _math(nt, "MAXIMUM", lp.outputs["Is Camera Ray"], lp.outputs["Is Transmission Ray"])
        else:
            seen = lp.outputs["Is Camera Ray"]
        nt.links.new(_math(nt, "MULTIPLY", dens, seen), vol.inputs["Density"])
        mat.cycles.volume_step_rate = 0.5
    else:
        vol.inputs["Density"].default_value = density
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(mat)
    ob.visible_shadow = False


def exterior(world, bg, preset, sun_dir=None):
    """Exterior stage (2026-09-27): the sky a camera (and a glossy ray) sees. The garden, the tree lines, the hills and the
    mountains are real geometry now (build_armory_exterior.py), so the world is sky only: a golden-hour gradient (warm
    horizon, pale middle, soft blue zenith), a glow around the sun and faint horizontal cloud streaks. Diffuse rays keep
    the flat SKY colour, so the fill light in the room is unchanged. Review stand-in for Unreal's SkyAtmosphere.
    --legacy-exterior restores the fix1 procedural tree line."""
    if "--legacy-exterior" not in ARGS:
        return sky_only(world, bg, preset, sun_dir)
    nt = world.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])   # world direction
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Generated"], noise.inputs["Vector"])
    # tree line: foliage below an elevation of about 14-26 deg (sin 0.24-0.44), ragged by the noise
    line = _math(nt, "ADD", 0.24, _math(nt, "MULTIPLY", noise.outputs["Fac"], 0.34))
    foliage = _math(nt, "LESS_THAN", sep.outputs[2], line)
    ramp = nt.nodes.new("ShaderNodeValToRGB")   # leaf mottle: shadowed to sunlit greens
    ramp.color_ramp.elements[0].color = (0.010, 0.022, 0.008, 1)
    ramp.color_ramp.elements[1].color = (0.20, 0.30, 0.07, 1) if preset == "golden" else (0.06, 0.12, 0.05, 1)
    leaf = nt.nodes.new("ShaderNodeTexNoise")
    leaf.inputs["Scale"].default_value = 60.0
    leaf.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Generated"], leaf.inputs["Vector"])
    nt.links.new(leaf.outputs["Fac"], ramp.inputs["Fac"])
    skyg = nt.nodes.new("ShaderNodeValToRGB")   # sky: warm near the horizon, paler above
    skyg.color_ramp.elements[0].color = (1.0, 0.62, 0.32, 1) if preset == "golden" else (0.55, 0.62, 0.75, 1)
    skyg.color_ramp.elements[1].color = (0.75, 0.70, 0.62, 1) if preset == "golden" else (0.35, 0.45, 0.65, 1)
    nt.links.new(sep.outputs[2], skyg.inputs["Fac"])
    mixc = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(foliage, mixc.inputs["Fac"])
    nt.links.new(skyg.outputs["Color"], mixc.inputs["Color1"])
    nt.links.new(ramp.outputs["Color"], mixc.inputs["Color2"])
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(mixc.outputs["Color"], cam_bg.inputs["Color"])
    cam_bg.inputs["Strength"].default_value = 3.0 if preset == "golden" else 0.6
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    # camera and glossy rays see the exterior (the case glass reflected the flat sky through the door as a white panel)
    nt.links.new(_math(nt, "MAXIMUM", lp.outputs["Is Camera Ray"], lp.outputs["Is Glossy Ray"]), mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def sky_only(world, bg, preset, sun_dir):
    nt = world.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    gen = tc.outputs["Generated"]                       # world direction
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(gen, sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    golden = preset == "golden"
    # (sin elevation, colour): orange at the horizon, gold, pale cream, then blue high up (a straight orange-to-blue
    # blend reads as grey-mauve)
    stops = ((0.0, (1.0, 0.46, 0.15)), (0.12, (1.0, 0.56, 0.22)), (0.30, (1.0, 0.72, 0.40)), (0.55, (0.90, 0.82, 0.66)), (1.0, (0.36, 0.56, 0.92))) \
        if golden else ((0.0, (0.55, 0.60, 0.72)), (0.22, (0.40, 0.48, 0.66)), (1.0, (0.22, 0.30, 0.50)))
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], stops[0][1] + (1,)
    els[1].position, els[1].color = stops[-1][0], stops[-1][1] + (1,)
    for pos, c in stops[1:-1]:
        els.new(pos).color = c + (1,)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    # faint cloud streaks between about 3 and 25 degrees
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.5, 2.5, 18.0)
    nt.links.new(gen, mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    band = _math(nt, "MULTIPLY", _in_range(nt, sep.outputs[2], 0.05, 0.42),
                 _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", nz.outputs["Fac"], 0.55), 0.0))
    cl = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(_math(nt, "MULTIPLY", band, 2.2), cl.inputs["Fac"])
    nt.links.new(col, cl.inputs["Color1"])
    cl.inputs["Color2"].default_value = (1.0, 0.86, 0.72, 1) if golden else (0.6, 0.62, 0.7, 1)
    col = cl.outputs["Color"]
    if sun_dir is not None and golden:                  # glow around the sun (toward the sun = -travel direction)
        dp = nt.nodes.new("ShaderNodeVectorMath")
        dp.operation = "DOT_PRODUCT"
        nt.links.new(gen, dp.inputs[0])
        dp.inputs[1].default_value = tuple(-c for c in sun_dir)
        c = _math(nt, "MAXIMUM", dp.outputs["Value"], 0.0)
        glow = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "POWER", c, 60.0), 3.0),
                     _math(nt, "MULTIPLY", _math(nt, "POWER", c, 6.0), 0.45))
        ad = nt.nodes.new("ShaderNodeMixRGB")
        ad.blend_type = "ADD"
        nt.links.new(glow, ad.inputs["Fac"])
        nt.links.new(col, ad.inputs["Color1"])
        ad.inputs["Color2"].default_value = (1.0, 0.72, 0.42, 1)
        col = ad.outputs["Color"]
    cam_bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(col, cam_bg.inputs["Color"])
    cam_bg.inputs["Strength"].default_value = float(arg("--sky", "4.5" if golden else "0.6"))
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(_math(nt, "MAXIMUM", lp.outputs["Is Camera Ray"], lp.outputs["Is Glossy Ray"]), mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def add_bloom(sc):
    """Mild bloom in the compositor (Blender 5.2 API: node group + Glare inputs as sockets)."""
    try:
        ng = bpy.data.node_groups.new("Review_Comp", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Quality"].default_value = "High"
        gl.inputs["Threshold"].default_value = float(arg("--bloom-th", str(BLOOM[0])))
        gl.inputs["Strength"].default_value = float(arg("--bloom-str", str(BLOOM[1])))
        gl.inputs["Size"].default_value = 0.6
        out = ng.nodes.new("NodeGroupOutput")
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs[0], out.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
    except Exception as exc:  # noqa: BLE001
        print("bloom setup failed, rendering without:", exc)


def main():
    global WINDOWS_Y, WINDOW_Z, DOOR_X, DOOR_Z, ROOM
    data = json.loads(Path(arg("--layout", str(WORK / "layout.json"))).read_text(encoding="utf-8"))   # --layout: a test copy
    if "room" in data:
        ROOM = (data["room"]["width_x"], data["room"]["length_y"], data["room"]["ceiling_z"])
    op = data.get("openings")
    if op:
        WINDOWS_Y = tuple(tuple(w) for w in op["windows_y"])
        WINDOW_Z, DOOR_X, DOOR_Z = tuple(op["window_z"]), tuple(op["door_x"]), tuple(op["door_z"])
    preset = arg("--preset", "golden")
    scale = PRESET_SCALE[preset]
    sc = bpy.context.scene
    coll = bpy.data.collections.new("ReviewLights")
    sc.collection.children.link(coll)
    for L in data["lights"]:
        kind = {"sun": "SUN", "rect": "AREA", "point": "POINT", "spot": "SPOT"}[L["type"]]
        ld = bpy.data.lights.new(L["name"], kind)
        ld.color = kelvin_rgb(L["kelvin"])
        o = bpy.data.objects.new(L["name"], ld)
        coll.objects.link(o)
        if kind == "SUN":
            ld.energy = SUN[preset] * L.get("power_scale", 1.0)
            if L.get("link") == "interior":   # f2: the window fill sun lights, and is shadowed by, the room only
                room = bpy.data.collections.get("Assembly")
                o.light_linking.receiver_collection = room
                o.light_linking.blocker_collection = room
            ld.angle = math.radians(float(arg("--sun-angle", str(SUN_ANGLE_DEG))))
            o.rotation_euler = [math.radians(a) for a in L["rot_deg"]]
            o.hide_render = SUN[preset] <= 0
            # f2: only the real sun scatters in the haze (the window fill's shafts veiled the west aisle in grey)
            o.visible_volume_scatter = "--sun-no-scatter" not in ARGS and L.get("link") != "interior"
            continue
        role = L["role"]
        o.location = L["loc"]
        power = POWER[role] * (L["perimeter"] if role == "glow" else 1.0)
        ld.energy = power * scale.get(role, 1.0) * L.get("power_scale", 1.0)
        ld.use_shadow = bool(L.get("shadows", True))
        o.visible_camera = False
        # only the sun (and the lanterns' soft halo) scatter in the haze: ~70 small practicals scattering in a thin
        # volume add blotchy noise for no visible gain (Unreal: Volumetric Scattering Intensity 0 on those lights)
        o.visible_volume_scatter = "--lantern-haze" in ARGS and role == "lantern"
        if role in ("glow", "panel", "rack", "case"):
            o.visible_glossy = False   # hidden emitters: only the LED strips and panels they stand for show
            o.visible_transmission = False   # nor through the case glass
        if kind == "AREA":
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = L["size"]
            if "aim" in L:
                look_at(o, L["aim"])
            else:
                o.rotation_euler = (0, 0, math.radians(L.get("rot_z", 0)))  # points down (-Z)
            if role == "glow":
                ld.spread = math.radians(160)
            if "spread_deg" in L:   # f2: a narrowed area light (the hero table's)
                ld.spread = math.radians(L["spread_deg"])
        elif kind == "POINT":
            ld.shadow_soft_size = L.get("radius", 0.1)
        elif kind == "SPOT":
            ld.spot_size = math.radians(L["angle_deg"])
            if "aim" in L:   # building stage: aimed spots (banner grazers)
                look_at(o, L["aim"])
            ld.spot_blend = L.get("blend", 0.5)   # f1: the niche spots fall off softly
            ld.shadow_soft_size = 0.04
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    col, strength = SKY[preset]
    bg.inputs["Color"].default_value = col + (1,)
    bg.inputs["Strength"].default_value = float(arg("--fill", str(strength)))
    if "--no-exterior" not in ARGS:
        sun_l = next((L for L in data["lights"] if L["type"] == "sun"), None)
        exterior(world, bg, preset, sun_l.get("travel_dir") if sun_l else None)
    sc.world = world
    try:   # the sky reaches the haze only through small windows: sampled from every fog point it is pure noise
        world.cycles_visibility.scatter = False
    except AttributeError:
        world.visible_volume_scatter = False
    for mname in arg("--no-emis-sampling", "").split(","):
        if mname in bpy.data.materials:
            bpy.data.materials[mname].cycles.emission_sampling = "NONE"
    if FOG[preset] > 0 and "--no-fog" not in ARGS:
        suns = [L for L in data["lights"] if L["type"] == "sun" and "travel_dir" in L]   # f2: two suns
        sun_dir = [Vector(L["travel_dir"]).normalized() for L in suns] or None
        add_fog(sc, float(arg("--fog", str(FOG[preset]))), sun_dir)
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
    sc.cycles.samples = int(arg("--samples", "96"))
    sc.cycles.use_denoising = True
    sc.cycles.sample_clamp_indirect = float(arg("--clamp-indirect", "3"))   # fix1: 6 -> 3 (glass speckle)
    try:   # fix1: best OIDN quality with albedo + normal guides (the review saw grain in the glass)
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        sc.cycles.denoising_prefilter = "ACCURATE"
        sc.cycles.denoising_quality = "HIGH"
    except (AttributeError, TypeError) as exc:
        print("denoiser settings:", exc)
    sc.cycles.sample_clamp_direct = float(arg("--clamp-direct", "25"))
    sc.cycles.volume_bounces = 0
    # fix1: no caustic paths and a glossy blur: the dark felt decks behind the glass showed caustic speckle
    sc.cycles.caustics_refractive = False
    sc.cycles.caustics_reflective = False
    sc.cycles.blur_glossy = 1.0
    w, h = (int(v) for v in arg("--res", "1600x900").split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = arg("--look", LOOK)
    sc.view_settings.exposure = float(arg("--exposure", str(EXPOSURE[preset])))
    if "--no-bloom" not in ARGS:
        add_bloom(sc)
    out = Path(arg("--out", str(WORK / "renders")))
    out.mkdir(parents=True, exist_ok=True)
    want = arg("--cams", "")
    cams = [c for c in data["cameras"] if not want or c["name"] in want.split(",")]
    for c in cams:
        cd = bpy.data.cameras.new(c["name"])
        cd.lens = c["lens_mm"]
        cd.shift_y = c.get("shift_y", 0.0)   # f1: C1 is a level shift-lens camera (reference 2's verticals are vertical)
        cd.sensor_width = 36.0
        cd.clip_start = 0.05
        cd.clip_end = 3000.0   # exterior stage: the mountain ring stands 720 m out
        co = bpy.data.objects.new(c["name"], cd)
        sc.collection.objects.link(co)
        co.location = c["loc"]
        look_at(co, c["look_at"])
        # exterior stage: sunlit garden views carry their own exposure (the interior preset would blow them out)
        ev = c.get("exposure_ev", {}).get(preset) if "--exposure" not in ARGS else None
        sc.view_settings.exposure = float(ev) if ev is not None else float(arg("--exposure", str(EXPOSURE[preset])))
        sc.camera = co
        sc.render.filepath = str(out / f"{c['name']}_{preset}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath, flush=True)


main()
