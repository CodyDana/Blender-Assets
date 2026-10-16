"""(SR01 W4 copy of gunlib/export_review_job.py, gunlib untouched) + the scope attachment: "scope_fbx",
"scope_lod_prefix", "scope_origin_M" place SM_Att_Scope_LongRange (static, on the body: its Mount at the rail) and a
shot shows it with "scope" in "show" ("scope_lod" optional, default min(lod, 2)).

Review renders of a gun from its EXPORTED bytes (headless Blender, Cycles): the shipped skeletal FBX (+ its LOD
files), the shipped magazine static mesh carried on the magazine bone (or placed at a socket), the shipped weapon clips,
and game-material previews built from the shipped textures only (gunlib.game.game_material: BC sRGB, ORM linear,
N DirectX flipped back). Nothing from the build blend is used. Review only: nothing here is exported.

    blender -b --factory-startup --python Scripts/guns/gunlib/export_review_job.py -- --job <job.json>

job.json:
  {"exports_dir": "<Exports/Guns/X>", "tex_dir": "<Exports/Guns/X/Textures>",
   "offset_M": [x, y, z],                 frame B = (M - offset) / 1000 (the exported files are in frame B)
   "gun_lods": ["SK_X.fbx", "SK_X_LOD1.fbx", ...],  "mag_fbx": "SM_X_Mag.fbx", "mag_lod_prefix": "SM_X_Mag_LOD",
   "mag_bone": "magazine", "clips": ["A_X_Charge", ...],
   "mag_socket_rel_rows": optional 3x3: the magazine socket's rotation relative to mag_bone (applied after the bone),
   "materials": {"M_X_Metal": "T_X_Metal", ...},     material base name -> texture stem
   "samples": 128, "result": "<json>",
   "shots": [{"name", "out", "ss": 1, "transparent": false, "samples": optional,
              "camera": ORTHO | PERSP (gunlib.closeup / camsolve JSON with panel_px) | {"type": "LOOK", "eye_M",
                        "target_M", "fov_deg" | "ortho_width_mm", "res": [w, h], "up_M": optional},
              "clip_end_m": optional,
              "show": ["gun", "mag"], "lod": 0, "mag_lod": optional,
              "pose": {"clip": name, "frame": clip frame (0-based)} and/or
                      {"hinges": [{"bone", "pivot_M", "axis_M", "deg"}]} and/or
                      {"mag_socket": {"location_B_mm": [...], "matrix_rows": 3x3}},
              "look": "tex" | "wire",
              "lights": {"rig": "rough", "bg_rgb", "env", "k", "dist_m", "target_M"} |
                        {"rig": "l5", "bg_rgb", "env", "k", "key_elev_deg", "side": "right" | "left" | "top",
                         "target_M": optional rig centre (default the gun's middle), "fill": optional weak fill W}}]}
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from gunlib import game as GM  # noqa: E402
from gunlib import look as LK  # noqa: E402
from gunlib import render as RD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
JOB = json.loads(Path(argv[argv.index("--job") + 1]).read_text())
sc = bpy.context.scene
OFF = np.array(JOB["offset_M"], float)
EXP = Path(JOB["exports_dir"])
TEX = Path(JOB["tex_dir"])


def B(p):
    return Vector(((np.asarray(p, float) - OFF) / 1000.0).tolist())


def import_fbx(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(p), use_custom_normals=True, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


# ------------------------------------------------------------------------------------------------ load
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

GUN = []                                  # [(armature, mesh)] per LOD file
for f in JOB["gun_lods"]:
    objs = import_fbx(EXP / f)
    arm = next(o for o in objs if o.type == "ARMATURE")
    mesh = next(o for o in objs if o.type == "MESH" and not o.name.startswith("UCX_"))
    for o in objs:
        if o.type == "MESH" and o is not mesh:
            o.hide_render = True
    GUN.append((arm, mesh))
    print("[export_review] gun", f, mesh.name, len(mesh.data.polygons), "faces")

MAG = {}
for o in import_fbx(EXP / JOB["mag_fbx"]):
    if o.type != "MESH":
        continue
    if o.name.startswith(JOB["mag_lod_prefix"]):
        k = int(o.name[len(JOB["mag_lod_prefix"]):].split(".")[0])
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        MAG[k] = o
    else:
        o.hide_render = True                   # UCX hulls
print("[export_review] mag LODs", sorted(MAG))

SCOPE = {}
if JOB.get("scope_fbx"):
    for o in import_fbx(EXP / JOB["scope_fbx"]):
        if o.type != "MESH":
            continue
        if o.name.startswith(JOB["scope_lod_prefix"]):
            k = int(o.name[len(JOB["scope_lod_prefix"]):].split(".")[0])
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = Matrix.Translation(B(JOB["scope_origin_M"])) @ mw
            SCOPE[k] = o
        else:
            o.hide_render = True
print("[export_review] scope LODs", sorted(SCOPE))

ACTS = {}
CLIPARM = {}
for c in JOB.get("clips", []):
    objs = import_fbx(EXP / f"{c}.fbx")
    a2 = next(o for o in objs if o.type == "ARMATURE")
    act = a2.animation_data.action
    act.name = c
    act.use_fake_user = True
    ACTS[c] = act
    # stage-7: the clip's own armature is kept (hidden). Blender's importer takes an animation FBX's node defaults
    # (the exporter writes the clip's first-frame pose there) as the bones' rest, so the action alone, put on the
    # mesh's skeleton, loses any pose the clip holds from its first frame (the selector held at AUTO read as SAFE).
    # The clip armature's ABSOLUTE bone matrices are what Unreal plays; set_clip copies them
    for o in objs:
        if o is a2:
            o.hide_render = True                  # (not hide_viewport: a viewport-hidden armature is not evaluated)
            CLIPARM[c] = o
        else:
            bpy.data.objects.remove(o, do_unlink=True)
print("[export_review] clips", {k: tuple(v.frame_range) for k, v in ACTS.items()})

# game materials from the shipped textures, one per material base name
GMATS = {}
for ob in [m for _a, m in GUN] + list(MAG.values()) + list(SCOPE.values()):
    for i, slot in enumerate(ob.material_slots):
        base = slot.material.name.split(".")[0] if slot.material else None
        if base not in JOB["materials"]:
            raise SystemExit(f"unmapped material {base} on {ob.name}")
        if base not in GMATS:
            GMATS[base] = GM.game_material("GM_" + base, JOB["materials"][base], TEX)
        ob.material_slots[i].material = GMATS[base]
TEXMATS = {ob.name: [s.material for s in ob.material_slots] for ob in [m for _a, m in GUN] + list(MAG.values()) +
           list(SCOPE.values())}


def wire_material():
    m = bpy.data.materials.new("GM_Wire")
    m.use_nodes = True
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.22, 0.22, 0.22, 1.0)
    bs.inputs["Roughness"].default_value = 0.65
    dark = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dark.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    wf = nt.nodes.new("ShaderNodeWireframe")
    wf.use_pixel_size = True
    wf.inputs["Size"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(wf.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(bs.outputs["BSDF"], mix.inputs[1])
    nt.links.new(dark.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


WIRE = wire_material()
DIAG = {}


def diag_material(base, look):
    """Diagnostic looks (review of the maps, never shipped): 'bc' = the BC map as emission (no shading), 'clay_n' =
    a mid-grey dielectric with the set's NORMAL map only, 'clay' = the same grey on the mesh normals alone."""
    key = (base, look)
    if key in DIAG:
        return DIAG[key]
    src = GMATS[base]
    m = src.copy()
    m.name = f"GD_{base}_{look}"
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    if look == "bc":
        tbc = next(n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image.name.endswith("_BC.png"))
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(tbc.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    else:
        for inp in ("Base Color", "Roughness", "Metallic"):
            for l in list(bs.inputs[inp].links):
                nt.links.remove(l)
        bs.inputs["Base Color"].default_value = (0.18, 0.18, 0.18, 1.0)
        bs.inputs["Roughness"].default_value = 0.35
        bs.inputs["Metallic"].default_value = 0.0
        if look == "clay":
            for l in list(bs.inputs["Normal"].links):
                nt.links.remove(l)
    DIAG[key] = m
    return m


def set_look(look):
    for ob in [m for _a, m in GUN] + list(MAG.values()) + list(SCOPE.values()):
        for i, s in enumerate(ob.material_slots):
            if look == "wire":
                s.material = WIRE
            elif look in ("bc", "clay", "clay_n"):
                s.material = diag_material(TEXMATS[ob.name][i].name[3:], look)
            else:
                s.material = TEXMATS[ob.name][i]


# ------------------------------------------------------------------------------------------------ poses
def rest(arm):
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)


def set_clip(arm, name, frame):
    if name in CLIPARM:
        ca = CLIPARM[name]
        off = int(round(ACTS[name].frame_range[0]))
        sc.frame_set(int(frame) + off)
        bpy.context.view_layer.update()
        rest(arm)
        for pb in arm.pose.bones:                 # parents first (Blender's bone order)
            cpb = ca.pose.bones.get(pb.name)
            if cpb is None:
                continue
            pb.matrix = arm.matrix_world.inverted() @ ca.matrix_world @ cpb.matrix
            bpy.context.view_layer.update()
        return
    act = ACTS[name]
    arm.animation_data.action = act
    try:
        if hasattr(arm.animation_data, "action_slot") and len(act.slots):
            arm.animation_data.action_slot = act.slots[0]
    except Exception:  # noqa: BLE001
        pass
    off = int(round(act.frame_range[0]))          # the importer starts each take at frame 1 (clip frame 0)
    sc.frame_set(int(frame) + off)


def hinge(arm, bone, pivot_M, axis_M, deg):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    W = arm.matrix_world @ pb.matrix
    p = B(pivot_M)
    R = Matrix.Translation(p) @ Matrix.Rotation(math.radians(float(deg)), 4, Vector(axis_M).normalized()) @ \
        Matrix.Translation(-p)
    pb.matrix = arm.matrix_world.inverted() @ (R @ W)
    bpy.context.view_layer.update()


def bone_world(arm, bone):
    M = arm.matrix_world @ arm.pose.bones[bone].matrix
    loc, rot, _s = M.decompose()
    return loc, rot


def place_mag(mag, arm, sock=None):
    if sock is None:
        loc, rot = bone_world(arm, JOB["mag_bone"])
        mag.matrix_world = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
        if "mag_socket_rel_rows" in JOB:
            # (SMG01 W4) the magazine attaches to a SOCKET on its bone whose rotation is not the bone's own (the
            # SMG01 Mag socket carries the 8.27 deg rake; its bone is unrotated): mag = bone @ socket-relative 3x3
            Rrel = Matrix([list(r) for r in JOB["mag_socket_rel_rows"]]).to_4x4()
            mag.matrix_world = mag.matrix_world @ Rrel
    else:
        R = Matrix([list(r) for r in sock["matrix_rows"]]).to_4x4()
        mag.matrix_world = Matrix.Translation(Vector([v / 1000.0 for v in sock["location_B_mm"]])) @ R


# ------------------------------------------------------------------------------------------------ cameras
def cam_ortho(cam, d, ss):
    Rm = np.array(d["R_rows_right_up_fwd_M"], float)
    c = np.array(d["image_centre_point_M"], float)
    W, H = d["panel_px"]
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = Rm[0], Rm[1], -Rm[2]
    M[:3, 3] = (c - Rm[2] * 1500.0 - OFF) / 1000.0
    cam.matrix_world = Matrix(M.tolist())
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = d["ortho_width_mm"] / 1000.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.05
    cam.data.clip_end = 6.0
    sc.render.resolution_x, sc.render.resolution_y = int(W * ss), int(H * ss)


def cam_look(cam, d):
    eye, tgt = B(d["eye_M"]), B(d["target_M"])
    cam.location = eye
    up = Vector(d.get("up_M", (0.0, 0.0, 1.0)))
    fwd = (tgt - eye).normalized()
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    if abs(fwd.dot(up)) > 0.999:
        cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "X").to_euler()
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.shift_x = cam.data.shift_y = 0.0
    if "ortho_width_mm" in d:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = d["ortho_width_mm"] / 1000.0
    else:
        cam.data.type = "PERSP"
        cam.data.angle = math.radians(float(d["fov_deg"]))
    cam.data.clip_start = 0.01
    cam.data.clip_end = 60.0
    sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in d["res"])


def set_camera(cam, d, ss):
    if d["type"] == "ORTHO":
        cam_ortho(cam, d, ss)
    elif d["type"] == "PERSP":
        W, H = d["panel_px"]
        RD.persp_from_solve(cam, sc, d, OFF, (H, W), ss)
    else:
        cam_look(cam, d)


# ------------------------------------------------------------------------------------------------ lights
def lights(cam, L):
    bg = tuple(L.get("bg_rgb", (126, 126, 126)))
    k = float(L.get("k", 1.0))
    if L["rig"] == "rough":
        LK.rough_world(sc, bg, float(L.get("env", 0.55)))
        LK.rough_lights(cam, tuple(B(L["target_M"])), float(L.get("dist_m", 1.1)), k)
        return
    if L["rig"] == "photo":
        photo_lights(cam, L)
        return
    if L["rig"] == "studio":
        # (gunlib 0.2.x, SMG01 W4 resume; optional, no AR-01 job uses it) a photographic studio for the realism views:
        # lighting and reflections from Blender's bundled studio HDRI (studiolights/world/<hdri>.exr, CC0) made
        # neutral (saturation 0) at `strength`, plus the rough rig's softboxes at k; the camera still sees the flat
        # bg_rgb backdrop. The flat grey world of the 'l5' / 'rough' rigs gives a dark, rough surface nothing to
        # reflect, so every finish reads as one matte clay (the W4 realism judges' tell); the L5 rig stays the colour
        # calibration rig
        w = bpy.data.worlds.new("ER_Studio")
        sc.world = w
        w.use_nodes = True
        nt = w.node_tree
        bgn = next(n for n in nt.nodes if n.type == "BACKGROUND")
        bgn.inputs["Color"].default_value = (*RD.srgb_to_lin(bg), 1.0)
        bgn.inputs["Strength"].default_value = 1.0
        d = Path(bpy.utils.system_resource("DATAFILES", path="studiolights/world"))
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(d / f"{L.get('hdri', 'studio')}.exr"), check_existing=True)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value[2] = math.radians(float(L.get("hdri_rot_deg", 0.0)))
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = float(L.get("saturation", 0.0))
        nt.links.new(env.outputs["Color"], hs.inputs["Color"])
        bg2 = nt.nodes.new("ShaderNodeBackground")
        bg2.inputs["Strength"].default_value = float(L.get("strength", 0.6))
        nt.links.new(hs.outputs["Color"], bg2.inputs["Color"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
        nt.links.new(bg2.outputs["Background"], mix.inputs[1])
        nt.links.new(bgn.outputs["Background"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        LK.clear_lights()
        if k > 0.0:
            LK.rough_lights(cam, tuple(B(L["target_M"])), float(L.get("dist_m", 1.1)), k)
        extra_lights(cam, L)
        return
    # 'l5': the physical L5 rig of rifle_texrender.sheet_lights_physical (overhead key tipped toward the camera side,
    # rim behind, the grey world as fill and reflection environment), mirrored for a view from the left
    RD.world_flat(sc, RD.srgb_to_lin(bg), 1.0, env=float(L.get("env", 0.2)) * k)
    LK.clear_lights()
    # Placed in the camera's own axes (back = toward the camera, up = image up): for the right-side camera this is
    # exactly the L5 rig (key c + 1.4 (0.05, -cos e, sin e), rim c + (0, 1, 0.6)); the left view mirrors it and the
    # top view gets the same relation to its camera (the key never sits in a flat's mirror direction)
    Mw = cam.matrix_world
    rgt = np.array(Mw.col[0][:3])
    up = np.array(Mw.col[1][:3])
    back = np.array(Mw.col[2][:3])
    rgt, up, back = (v / np.linalg.norm(v) for v in (rgt, up, back))
    # (stage-7 fix round, review item 7: the close-up set and the realism views use this rig too, centred on the
    # shot's own target instead of the gun's middle; the key / rim distances stay the L5 rig's own, so the light the
    # colour was calibrated under reaches every view unchanged)
    c = np.array(B(L["target_M"])) if "target_M" in L else np.array((0.2, 0.0, 0.0))
    e = math.radians(float(L.get("key_elev_deg", 70.0)))
    RD.area_light("Key", tuple(c + 1.4 * (0.05 * rgt + math.cos(e) * back + math.sin(e) * up)), tuple(c), 2.4, 60 * k)
    RD.area_light("Rim", tuple(c - back + 0.6 * up), tuple(c), 1.5, 10 * k)
    if float(L.get("fill", 0.0)) > 0.0:
        # optional weak fill from the camera side, low (opens a port's interior without lifting the flats much)
        RD.area_light("Fill", tuple(c + 1.2 * (0.35 * rgt + 0.9 * back - 0.25 * up)), tuple(c), 1.5,
                      float(L["fill"]) * k)


def photo_lights(cam, L):
    """(SR01 rig2, FINAL_JUDGES tells #1/#3/#7) a product-photo rig: NO environment map (the interior HDRI's window
    rectangles were the blocky floor patches) but a dim neutral world, the cyclorama of floor() as the visible backdrop
    and the bounce, and three large soft boxes placed in the camera's axes: a key high on the left front, a broad weak
    fill low on the right, a rim/kicker strip behind and above. Sizes are real softbox sizes (1.2 x 0.9 m key, 2 x 1.4 m
    fill) so no light pool has a hard edge. L["photo"] may override {"key", "fill", "rim", "top"} energies (W)."""
    LK.clear_lights()
    w = bpy.data.worlds.new("ER_Photo")
    sc.world = w
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (*RD.srgb_to_lin(tuple(L.get("bg_rgb", (128, 128, 128)))), 1.0)
    bgn.inputs["Strength"].default_value = float(L.get("env", 0.12))
    Mw = cam.matrix_world
    rgt = Vector(Mw.col[0][:3]).normalized()
    back = Vector(Mw.col[2][:3]).normalized()
    z = Vector((0.0, 0.0, 1.0))
    hb = Vector((back.x, back.y, 0.0))
    hb = hb.normalized() if hb.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    hr = Vector((rgt.x, rgt.y, 0.0)).normalized()
    t = Vector(B(L["target_M"]))
    E = dict({"key": 260.0, "fill": 35.0, "rim": 45.0, "top": 70.0}, **L.get("photo", {}))
    # (spread: a honeycomb grid on the rim only, so it lights the gun, not a pool on the sweep; a narrower spread
    # concentrates the same power, hence its lower energy)
    specs = [("Key", -0.75 * hr + 0.55 * hb + 1.0 * z, 1.7, (1.2, 0.9), E["key"], 180.0),
             ("Fill", 1.0 * hr + 0.7 * hb + 0.35 * z, 2.2, (2.0, 1.4), E["fill"], 180.0),
             ("Rim", 0.35 * hr - 1.0 * hb + 0.8 * z, 1.6, (0.35, 1.6), E["rim"], 45.0),
             ("Top", -0.15 * hb + 1.0 * z, 1.5, (1.6, 0.6), E["top"], 180.0)]
    for name, d, dist, size, energy, spread in specs:
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
        ld.energy = energy
        ld.spread = math.radians(spread)
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.location = t + d.normalized() * dist
        ob.rotation_euler = (t - ob.location).to_track_quat("-Z", "Y").to_euler()
        ob.visible_camera = False


def extra_lights(cam, L):
    """(gunlib 0.2.x, SMG01 W4b close-up r2; optional, no AR-01 job uses it) explicit rectangular softboxes / strip
    lights for the 'studio' rig, the way a black product is photographed: a broad overhead box whose mirror image lands
    on the top faces and strip lights whose reflections run along the edges. Each entry: name, a direction from the
    shot's target either in the camera's axes ("dir_cam": [right, up, back]) or in frame M ("dir_M"), "dist" (m),
    "size" [x, y] (m), "energy" (W), "spread_deg" (optional). Never seen directly by the camera (the backdrop stays
    the flat bg_rgb)."""
    if not L.get("extra_lights"):
        return
    Mw = cam.matrix_world
    rgt = Vector(Mw.col[0][:3]).normalized()
    up = Vector(Mw.col[1][:3]).normalized()
    back = Vector(Mw.col[2][:3]).normalized()
    t = Vector(B(L["target_M"]))
    for e in L["extra_lights"]:
        if "mirror_n_M" in e:
            # the mirror direction of the view about a face normal (frame M): the box's reflection lands on that face
            # (a black satin flat reads by the reflection it carries); "nudge_cam" moves it in the camera's axes so
            # the box's edge falls across the face as a gradient
            v = (Vector(cam.matrix_world.translation) - t).normalized()
            if e["mirror_n_M"] == "flank":          # the side face toward the camera (+Y seen from the left)
                n = Vector((0.0, 1.0 if v.y >= 0.0 else -1.0, 0.0))
            else:
                n = Vector(e["mirror_n_M"]).normalized()
            d = (2.0 * n.dot(v) * n - v).normalized()
            r_, u_, b_ = e.get("nudge_cam", (0.0, 0.0, 0.0))
            d = (d + rgt * r_ + up * u_ + back * b_).normalized()
        elif "dir_cam" in e:
            r_, u_, b_ = e["dir_cam"]
            d = (rgt * r_ + up * u_ + back * b_).normalized()
        else:
            d = Vector(e["dir_M"]).normalized()
        ld = bpy.data.lights.new(e["name"], "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = float(e["size"][0]), float(e["size"][1])
        ld.energy = float(e["energy"])
        if "spread_deg" in e:
            ld.spread = math.radians(float(e["spread_deg"]))
        ob = bpy.data.objects.new(e["name"], ld)
        sc.collection.objects.link(ob)
        ob.location = t + d * float(e.get("dist", 1.0))
        ob.rotation_euler = (t - ob.location).to_track_quat("-Z", "Y").to_euler()
        if "roll_deg" in e:
            ob.rotation_euler = (ob.rotation_euler.to_matrix() @ Matrix.Rotation(math.radians(float(e["roll_deg"])),
                                                                                 3, "Z")).to_euler()
        ob.visible_camera = False


# ------------------------------------------------------------------------------------------------ floor + lens (W4b)
FLOOR = {}
HOME = {}                                 # rig2: each armature's / scope's load-time matrix (rest_on_butt undo)


def cyc_material(F):
    """a matte paper/vinyl sweep: neutral grey with a faint large-scale tone drift and fine roughness/bump grain (a
    perfectly uniform surface is itself a CG tell)."""
    m = bpy.data.materials.new("ER_Cyc")
    m.use_nodes = True
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    base = RD.srgb_to_lin(tuple(F.get("rgb", (120, 120, 118))))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = 0.8
    big.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*(c * 0.95 for c in base), 1.0)
    ramp.color_ramp.elements[1].color = (*(c * 1.04 for c in base), 1.0)
    nt.links.new(big.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 900.0
    fine.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = float(F.get("rough", 0.62)) - 0.06
    mr.inputs["To Max"].default_value = float(F.get("rough", 0.62)) + 0.06
    nt.links.new(fine.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bs.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.04
    bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    for nm in ("Specular IOR Level", "Specular"):
        if nm in bs.inputs:
            bs.inputs[nm].default_value = 0.35
            break
    return m


def cyclorama(F, zmin, cam):
    """(SR01 rig2, FINAL_JUDGES tells #1/#5) a seamless studio sweep instead of the infinite plane + flat world: the
    floor runs from well behind the camera to `wall_m` behind the shot's target, bends up through a radius-`radius_m`
    quarter circle (48 smooth segments, no seam) into a 9 m wall; the sweep is turned about Z so the wall faces the
    camera. Its floor sits EXACTLY at the lowest posed vertex (drop 0: the lowest point touches, nothing intersects)."""
    if "cyc" in FLOOR:
        bpy.data.objects.remove(FLOOR["cyc"], do_unlink=True)
    R, Dw, H, W, Df = (float(F.get("radius_m", 1.0)), float(F.get("wall_m", 1.4)), 9.0, 20.0, 10.0)
    prof = [(Df, 0.0), (0.0, 0.0), (-(Dw - R), 0.0)]
    for i in range(1, 49):                                # y toward the camera, z up
        a = (math.pi / 2.0) * i / 48.0
        prof.append((-(Dw - R) - R * math.sin(a), R - R * math.cos(a)))
    prof.append((-Dw, H))
    verts, faces = [], []
    for y, zz in prof:
        verts += [(-W / 2, y, zz), (W / 2, y, zz)]
    for i in range(len(prof) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    me = bpy.data.meshes.new("ER_Cyc")
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("ER_Cyc", me)
    sc.collection.objects.link(ob)
    if "cycmat" not in FLOOR:
        FLOOR["cycmat"] = cyc_material(F)
    ob.data.materials.append(FLOOR["cycmat"])
    t = Vector(B(F["target_M"]))
    v = Vector(cam.matrix_world.translation) - t
    ang = math.atan2(v.y, v.x) - math.pi / 2.0          # local +y -> the camera's horizontal direction
    ob.rotation_euler = (0.0, 0.0, ang)
    ob.location = (t.x, t.y, zmin - float(F.get("drop_mm", 0.0)) / 1000.0)
    FLOOR["cyc"] = ob
    return round(float(zmin) * 1000.0 + float(OFF[2]), 2)


def world_verts(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.hide_render or o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        M = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        pts.append(co)
        ev.to_mesh_clear()
    return np.concatenate(pts)


def rest_on_butt(movers, objs):
    """(SR01 rig2, FINAL_JUDGES tell #5: "the butt doesn't press into the floor") a rifle grounded on its bipod rests
    its butt on the ground: one rigid pitch of the whole assembly (armature, scope; the magazine follows its bone)
    about a Y line through the lowest point (a bipod foot), by the smallest angle that brings a point behind it down to
    the same height. No bone is re-posed. Returns the angle in degrees."""
    bpy.context.view_layer.update()
    P = world_verts(objs)
    p = P[np.argmin(P[:, 2])]
    rear = P[P[:, 0] < p[0] - 0.3]
    dx, dz = rear[:, 0] - p[0], rear[:, 2] - p[2]
    th = float(np.min(np.arctan2(dz, -dx)))
    R = Matrix.Translation(Vector(p)) @ Matrix.Rotation(th, 4, "Y") @ Matrix.Translation(-Vector(p))
    if (R @ Vector(rear[0])).z > rear[0][2]:            # pick the sense that lowers the rear
        R = Matrix.Translation(Vector(p)) @ Matrix.Rotation(-th, 4, "Y") @ Matrix.Translation(-Vector(p))
    for o in movers:
        o.matrix_world = R @ o.matrix_world
    bpy.context.view_layer.update()
    return round(math.degrees(th), 2)


def floor(shot, objs, cam=None):
    """(SR01 W4b, both realism judges: "floats in a grey void, no contact shadow") an optional tabletop: a 40 m plane
    under the lowest point of the visible meshes (posed), a neutral satin grey, so the gun casts and receives real
    contact shadows. shot["floor"] = {"rgb": [r, g, b] sRGB, "rough": 0.55, "drop_mm": 0.3} or absent.
    (rig2) {"cyc": true, "target_M", "wall_m", "radius_m", "rgb", "rough", "drop_mm": 0} = the cyclorama sweep."""
    F = shot.get("floor")
    if "ob" in FLOOR:
        FLOOR["ob"].hide_render = True
    if "cyc" in FLOOR:
        FLOOR["cyc"].hide_render = True
    if not F:
        return None
    dg = bpy.context.evaluated_depsgraph_get()
    zmin = 1e9
    for o in objs:
        if o.hide_render or o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        M = o.matrix_world
        for v in me.vertices:
            zmin = min(zmin, (M @ v.co).z)
        ev.to_mesh_clear()
    if F.get("cyc"):
        return cyclorama(F, zmin, cam)
    if "ob" not in FLOOR:
        me = bpy.data.meshes.new("ER_Floor")
        h = 20.0
        me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new("ER_Floor", me)
        sc.collection.objects.link(ob)
        mat = bpy.data.materials.new("ER_Floor")
        mat.use_nodes = True
        ob.data.materials.append(mat)
        FLOOR["ob"], FLOOR["mat"] = ob, mat
    ob, mat = FLOOR["ob"], FLOOR["mat"]
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*RD.srgb_to_lin(tuple(F.get("rgb", (118, 118, 116)))), 1.0)
    bsdf.inputs["Roughness"].default_value = float(F.get("rough", 0.55))
    ob.location = (0.0, 0.0, zmin - float(F.get("drop_mm", 0.3)) / 1000.0)
    ob.hide_render = False
    return round(float(zmin) * 1000.0 + float(OFF[2]), 2)


def lens_dof(cam, shot):
    """(SR01 W4b, realism judge: "no depth of field despite the 35 cm close-up") shot["dof"] = {"fstop": 4.0} focuses
    on the shot's camera target (frame M) through a real aperture; absent = pinhole."""
    D = shot.get("dof")
    cam.data.dof.use_dof = bool(D)
    if not D:
        return
    c = shot["camera"]
    t = B(D.get("focus_M", c.get("target_M", (0, 0, 0))))
    cam.data.dof.focus_distance = float((Vector(cam.matrix_world.translation) - t).length)
    cam.data.dof.aperture_fstop = float(D.get("fstop", 4.0))
    # (rig2) a real lens's polygonal iris (7 blades) and the 36 mm full-frame sensor the fov is solved on
    cam.data.dof.aperture_blades = int(D.get("blades", 0))
    cam.data.dof.aperture_rotation = math.radians(15.0) if D.get("blades") else 0.0
    cam.data.sensor_width = 36.0


def photo_render(shot):
    """(SR01 rig2, FINAL_JUDGES tells #1/#7) shot["render"] = {"view": "AgX", "look": ..., "exposure": 0.0,
    "clamp_indirect": 10, "filter_glossy": 0.5}: a filmic view transform so the soft boxes roll off instead of
    clipping to blown pools, no caustics, light tree on, and (with "denoise": true) OIDN on albedo + normal passes.
    Absent = the calibration settings (Standard, no clamp)."""
    P = shot.get("render")
    vs = sc.view_settings
    c = sc.cycles
    if not P:
        vs.view_transform, vs.look, vs.exposure = "Standard", "None", 0.0
        c.sample_clamp_indirect, c.blur_glossy = 0.0, 0.0
        return
    vs.view_transform = P.get("view", "AgX")
    try:
        vs.look = P.get("look", "None")
    except TypeError:
        print("[export_review] look not found:", P.get("look"))
    vs.exposure = float(P.get("exposure", 0.0))
    c.sample_clamp_indirect = float(P.get("clamp_indirect", 10.0))
    c.blur_glossy = float(P.get("filter_glossy", 0.5))
    c.caustics_reflective = c.caustics_refractive = False
    c.use_light_tree = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    c.denoising_prefilter = "ACCURATE"


NO_FINISH = "--no-finish" in argv
FINISH = {"dispersion": 0.006, "lift": 0.002, "s_curve": ((0.05, 0.045), (0.18, 0.18), (0.6, 0.63)),
          "vignette_k": 0.07, "grain_scale": 1.3, "grain_strength": 0.22}
_FIN = {}


def photo_finish(shot):
    """(SR01 rig 2b, RIG_PROPOSAL judge tell "too clean, no grain or grading") a subtle photographic finish in the
    Blender 5.2 compositor (node group on scene.compositing_node_group; scene-linear, before AgX): lateral chromatic
    aberration (Lens Distortion dispersion only), a slight black lift + mild S-curve, a radial vignette, and
    multiplicative ~1 px luminance grain. On for rig2 shots (shot["render"]) unless render["finish"] is false or the
    job runs with --no-finish; every other shot renders with no compositor."""
    P = shot.get("render")
    if not P or NO_FINISH or not P.get("finish", True) or shot.get("transparent"):
        sc.compositing_node_group = None
        return
    if "ng" not in _FIN:
        F = dict(FINISH, **{k: v for k, v in P.items() if k in FINISH})
        ng = bpy.data.node_groups.new("SR_PhotoFinish", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        N, L = ng.nodes, ng.links

        def node(t, **kw):
            n = N.new(t)
            for k, v in kw.items():
                setattr(n, k, v)
            return n

        def math(op, a, b=None, c=None):
            n = node("ShaderNodeMath", operation=op)
            for i, v in enumerate((a, b, c)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[i].default_value = v
                else:
                    L.new(v, n.inputs[i])
            return n.outputs[0]

        rl = node("CompositorNodeRLayers")
        ld = node("CompositorNodeLensdist")                     # lateral CA only: no barrel/pincushion
        ld.inputs["Distortion"].default_value = 0.0
        ld.inputs["Dispersion"].default_value = F["dispersion"]
        L.new(rl.outputs["Image"], ld.inputs["Image"])
        cb = node("CompositorNodeColorBalance")                # black lift (offset), white balance left neutral
        try:
            cb.inputs["Type"].default_value = "Offset/Power/Slope (ASC-CDL)"
        except (TypeError, ValueError):
            print("[export_review] colour balance type menu:", [i.name for i in cb.inputs])
        cb.inputs[9].default_value = F["lift"]                   # Offset (value)
        L.new(ld.outputs["Image"], cb.inputs["Image"])
        cv = node("CompositorNodeCurveRGB")                     # mild S on the combined curve, pivot at mid grey
        cm = cv.mapping
        cm.extend = "EXTRAPOLATED"
        for x, y in F["s_curve"]:
            cm.curves[3].points.new(x, y)
        cm.update()
        L.new(cb.outputs["Image"], cv.inputs["Image"])
        ic = node("CompositorNodeImageCoordinates")             # vignette: 1 - k r^2 on zero-centred coordinates
        L.new(rl.outputs["Image"], ic.inputs["Image"])
        ln = node("ShaderNodeVectorMath", operation="LENGTH")
        L.new(ic.outputs["Uniform"], ln.inputs[0])
        vig = math("MULTIPLY_ADD", math("POWER", ln.outputs["Value"], 2.0), -F["vignette_k"], 1.0)
        nz = node("ShaderNodeTexNoise", noise_dimensions="4D")  # grain: ~1 px value noise on pixel coordinates
        nz.inputs["W"].default_value = 0.37
        nz.inputs["Scale"].default_value = F["grain_scale"]
        nz.inputs["Detail"].default_value = 0.0
        L.new(ic.outputs["Pixel"], nz.inputs["Vector"])
        gr = math("MULTIPLY_ADD", math("SUBTRACT", nz.outputs["Factor"], 0.5), F["grain_strength"], 1.0)
        gain = math("MULTIPLY", vig, gr)
        mx = node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
        mx.inputs["Factor"].default_value = 1.0
        L.new(cv.outputs["Image"], mx.inputs[6])
        L.new(gain, mx.inputs[7])
        go = node("NodeGroupOutput")
        L.new(mx.outputs[2], go.inputs[0])
        _FIN["ng"] = ng
        print("[export_review] photo finish", json.dumps(F))
    sc.compositing_node_group = _FIN["ng"]
    sc.render.use_compositing = True


# ------------------------------------------------------------------------------------------------ shots
def main():
    RD.engine(sc, "CYCLES", int(JOB.get("samples", 128)))
    sc.render.resolution_percentage = 100
    cam = RD.camera_object("ER_Cam")
    results = []
    HOME.update({o: o.matrix_world.copy() for o in [a for a, _m in GUN] + list(SCOPE.values())})
    for shot in JOB["shots"]:
        sc.cycles.samples = int(shot.get("samples", JOB.get("samples", 128)))
        # (SMG01 W4b r2, optional) the denoiser smooths sub-millimetre texture (moulded grain, stipple, wear flecks)
        # into a clean plastic look at the close views; a shot may switch it off and pay in samples instead
        sc.cycles.use_denoising = bool(shot.get("denoise", True))
        lod = int(shot.get("lod", 0))
        show = shot.get("show", ["gun", "mag"])
        for _a, m in GUN:
            m.hide_render = True
        for m in MAG.values():
            m.hide_render = True
        for a, _m in GUN:
            rest(a)
        for o, M0 in HOME.items():                       # undo a previous shot's rest_on_butt (rig2)
            o.matrix_world = M0
        arm, gmesh = GUN[lod]
        mag = MAG[int(shot.get("mag_lod", lod))]
        gmesh.hide_render = "gun" not in show
        mag.hide_render = "mag" not in show
        for m in SCOPE.values():
            m.hide_render = True
        if SCOPE and "scope" in show:
            SCOPE[int(shot.get("scope_lod", min(lod, max(SCOPE))))].hide_render = False
        pose = shot.get("pose") or {}
        if "clip" in pose:
            set_clip(arm, pose["clip"], pose["frame"])
        bpy.context.view_layer.update()
        for h in pose.get("hinges", []):
            hinge(arm, h["bone"], h["pivot_M"], h["axis_M"], h["deg"])
        bpy.context.view_layer.update()
        place_mag(mag, arm, pose.get("mag_socket"))
        set_look(shot.get("look", "tex"))
        ss = int(shot.get("ss", 1))
        set_camera(cam, shot["camera"], ss)
        if "clip_end_m" in shot:
            cam.data.clip_end = float(shot["clip_end_m"])
        bpy.context.view_layer.update()
        lights(cam, shot["lights"])
        vis = [m for _a, m in GUN] + list(MAG.values()) + list(SCOPE.values())
        tilt = rest_on_butt([arm, mag] + list(SCOPE.values()), vis) if shot.get("rest_on_butt") else 0.0
        fz = floor(shot, vis, cam)
        lens_dof(cam, shot)
        photo_render(shot)
        photo_finish(shot)
        transparent = bool(shot.get("transparent", False))
        Path(shot["out"]).parent.mkdir(parents=True, exist_ok=True)
        RD.still(sc, shot["out"], transparent)
        rec = {"name": shot["name"], "out": shot["out"], "res": [sc.render.resolution_x, sc.render.resolution_y],
               "lod": lod, "mesh": gmesh.name if "gun" in show else None, "mag": mag.name if "mag" in show else None,
               "bones_M_mm": {}, "floor_z_M_mm": fz, "rest_on_butt_deg": tilt}
        for bn in ("bolt", "selector", JOB["mag_bone"]):
            if bn in arm.pose.bones:
                loc, _r = bone_world(arm, bn)
                rec["bones_M_mm"][bn] = [round(float(v) * 1000.0 + float(o), 3) for v, o in zip(loc, OFF)]
        mw = mag.matrix_world
        rec["mag_M_mm"] = [round(float(v) * 1000.0 + float(o), 3) for v, o in zip(mw.translation, OFF)]
        rec["mag_pitch_deg"] = round(math.degrees(math.atan2(mw[0][2], mw[0][0])), 3)
        results.append(rec)
        print("[export_review] RENDERED", shot["name"], json.dumps(rec["bones_M_mm"]))
    rest_bolt = None
    if GUN:
        rest(GUN[0][0])
        bpy.context.view_layer.update()
        rest_bolt = [round(float(v) * 1000.0 + float(o), 3) for v, o in zip(bone_world(GUN[0][0], "bolt")[0], OFF)] \
            if "bolt" in GUN[0][0].pose.bones else None
    Path(JOB["result"]).write_text(json.dumps({"shots": results, "rest_bolt_M_mm": rest_bolt,
                                               "gun_faces": [len(m.data.polygons) for _a, m in GUN],
                                               "mag_faces": {k: len(v.data.polygons) for k, v in MAG.items()}},
                                              indent=1))
    print("[export_review] EXPORT_REVIEW_DONE", len(results))


main()
