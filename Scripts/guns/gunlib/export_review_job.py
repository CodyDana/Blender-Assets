"""Review renders of a gun from its EXPORTED bytes (headless Blender, Cycles): the shipped skeletal FBX (+ its LOD
files), the shipped magazine static mesh carried on the magazine bone (or placed at a socket), the shipped weapon clips,
and game-material previews built from the shipped textures only (gunlib.game.game_material: BC sRGB, ORM linear,
N DirectX flipped back). Nothing from the build blend is used. Review only: nothing here is exported.

    blender -b --factory-startup --python Scripts/guns/gunlib/export_review_job.py -- --job <job.json>

job.json:
  {"exports_dir": "<Exports/Guns/X>", "tex_dir": "<Exports/Guns/X/Textures>",
   "offset_M": [x, y, z],                 frame B = (M - offset) / 1000 (the exported files are in frame B)
   "gun_lods": ["SK_X.fbx", "SK_X_LOD1.fbx", ...],  "mag_fbx": "SM_X_Mag.fbx", "mag_lod_prefix": "SM_X_Mag_LOD",
   "mag_bone": "magazine", "clips": ["A_X_Charge", ...],
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
                        {"rig": "l5", "bg_rgb", "env", "k", "key_elev_deg", "side": "right" | "left" | "top"}}]}
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

ACTS = {}
for c in JOB.get("clips", []):
    objs = import_fbx(EXP / f"{c}.fbx")
    a2 = next(o for o in objs if o.type == "ARMATURE")
    act = a2.animation_data.action
    act.name = c
    act.use_fake_user = True
    ACTS[c] = act
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
print("[export_review] clips", {k: tuple(v.frame_range) for k, v in ACTS.items()})

# game materials from the shipped textures, one per material base name
GMATS = {}
for ob in [m for _a, m in GUN] + list(MAG.values()):
    for i, slot in enumerate(ob.material_slots):
        base = slot.material.name.split(".")[0] if slot.material else None
        if base not in JOB["materials"]:
            raise SystemExit(f"unmapped material {base} on {ob.name}")
        if base not in GMATS:
            GMATS[base] = GM.game_material("GM_" + base, JOB["materials"][base], TEX)
        ob.material_slots[i].material = GMATS[base]
TEXMATS = {ob.name: [s.material for s in ob.material_slots] for ob in [m for _a, m in GUN] + list(MAG.values())}


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
    for ob in [m for _a, m in GUN] + list(MAG.values()):
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
    c = np.array((0.2, 0.0, 0.0))
    e = math.radians(float(L.get("key_elev_deg", 70.0)))
    RD.area_light("Key", tuple(c + 1.4 * (0.05 * rgt + math.cos(e) * back + math.sin(e) * up)), tuple(c), 2.4, 60 * k)
    RD.area_light("Rim", tuple(c - back + 0.6 * up), tuple(c), 1.5, 10 * k)


# ------------------------------------------------------------------------------------------------ shots
def main():
    RD.engine(sc, "CYCLES", int(JOB.get("samples", 128)))
    sc.render.resolution_percentage = 100
    cam = RD.camera_object("ER_Cam")
    results = []
    for shot in JOB["shots"]:
        sc.cycles.samples = int(shot.get("samples", JOB.get("samples", 128)))
        lod = int(shot.get("lod", 0))
        show = shot.get("show", ["gun", "mag"])
        for _a, m in GUN:
            m.hide_render = True
        for m in MAG.values():
            m.hide_render = True
        for a, _m in GUN:
            rest(a)
        arm, gmesh = GUN[lod]
        mag = MAG[int(shot.get("mag_lod", lod))]
        gmesh.hide_render = "gun" not in show
        mag.hide_render = "mag" not in show
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
        transparent = bool(shot.get("transparent", False))
        Path(shot["out"]).parent.mkdir(parents=True, exist_ok=True)
        RD.still(sc, shot["out"], transparent)
        rec = {"name": shot["name"], "out": shot["out"], "res": [sc.render.resolution_x, sc.render.resolution_y],
               "lod": lod, "mesh": gmesh.name if "gun" in show else None, "mag": mag.name if "mag" in show else None,
               "bones_M_mm": {}}
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
