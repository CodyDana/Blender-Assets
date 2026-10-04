"""Saya renders - always from the EXPORTED FBX bytes (SM_Katana_Saya.fbx and SM_Katana.fbx re-imported) with their
BAKED maps (the game materials appended read-only from Assets/Katana/Saya.blend and Katana.blend), Cycles.
The katana is placed by the saya's Holster socket read back from the exported sidecar.

    blender -b --factory-startup --python Scripts/Katana/saya_render.py -- --set all|gallery|sheet [--samples N]

gallery  saya_hero, saya_sheathed_hero, saya_sheathed_side, saya_sheathed_top, saya_mouth, saya_seat, saya_kurikata,
         saya_kojiri, saya_cutaway (+ _mouth, _tip), saya_lod0..2 (+ _mouth), saya_wire  -> Renders/Katana/
sheet    the design sheet's rows 2 (saya) and 3 (sheathed) re-created at the sheet's own scale and framing (5 px per mm,
         objects placed with the sheet's view matrices) -> Renders/Katana/saya_sheet_*.png (+ _mask)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts"))
import saya_spec as S  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "all")
SAMPLES = int(arg("--samples", "128"))
OUT = ROOT / "Renders" / "Katana"
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
PX_PER_MM = 5.0
# the design sheet's layout (WorkFiles/katana/study/make_design_sheet.py): sheet mm, 1400 x 1200, 7000 x 6000 px
OX, END_X = 70.0 + 215.0, 1180.0
ROW_B_TOP, ROW_B = 777.0, 735.0
ROW_C_TOP, ROW_C = 550.0, 465.0
SHEET_CROPS = {   # sheet pixels (x0, y0, x1, y1), top-left origin
    "B": (1695, 2000, 5400, 2990),       # row 2: saya top + side (1:1)
    "B_end": (5700, 2140, 6060, 2960),   # row 2: end view from the kojiri
    "C": (330, 3040, 5400, 4320),        # row 3: sheathed top + side
    "C_end": (5690, 3470, 6110, 4310),   # row 3: end view from the tip
}


def rotm(cols):
    return Matrix(((cols[0][0], cols[1][0], cols[2][0]), (cols[0][1], cols[1][1], cols[2][1]),
                   (cols[0][2], cols[1][2], cols[2][2])))


SIDE = rotm(((0, -1, 0), (0, 0, -1), (1, 0, 0)))
TOP = rotm(((0, 0, -1), (0, 1, 0), (1, 0, 0)))
END = rotm(((0, -1, 0), (1, 0, 0), (0, 0, 1)))


def gpu():
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"


def world_studio(bg=(1, 1, 1), env_strength=1.0):
    """Camera sees a flat background; reflections see a soft top-bright / bottom-dark studio (as katana_render)."""
    w = bpy.data.worlds.new("SAYA_Studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bgc = nt.nodes.new("ShaderNodeBackground")
    bgc.inputs["Color"].default_value = (*bg, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.01, 0.01, 0.012, 1)
    ramp.color_ramp.elements[1].position = 0.80
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mid = ramp.color_ramp.elements.new(0.55)
    mid.color = (0.35, 0.35, 0.37, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    env = nt.nodes.new("ShaderNodeBackground")
    env.inputs["Strength"].default_value = env_strength
    nt.links.new(ramp.outputs["Color"], env.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs["Background"], mix.inputs[1])
    nt.links.new(bgc.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


LIGHTS = []


def area(name, loc, target, size, energy, color=(1, 1, 1), shape=None, size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = color
    if shape:
        ld.shape = shape
        ld.size_y = size_y
    lo = bpy.data.objects.new(name, ld)
    lo.location = Vector(loc)
    d = (Vector(target) - Vector(loc)).normalized()
    lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
    LIGHTS.append(lo)
    return lo


def clear_lights():
    for lo in LIGHTS:
        bpy.data.objects.remove(lo, do_unlink=True)
    LIGHTS.clear()


def lights_studio():
    """Saya frame (metres): the saya runs z -0.08 .. 0.64, the katana's hilt z -0.35 .. -0.08."""
    area("key", (-0.9, -1.3, 0.75), (0, 0, 0.15), 1.2, 9.0)
    area("strip", (-0.55, -0.9, 0.3), (0.02, 0, 0.2), 0.4, 6.0, shape="RECTANGLE", size_y=0.35).data.size = 1.6
    area("fill", (0.9, -1.0, -0.4), (0, 0, 0.0), 2.0, 4.0, color=(0.92, 0.95, 1.0))
    area("rim", (0.4, 1.2, 0.5), (0, 0, 0.2), 1.0, 8.0)


def cam_axes(right, up):
    r = Vector(right).normalized()
    u = Vector(up)
    u = (u - r * u.dot(r)).normalized()
    z = r.cross(u)
    return Matrix((r, u, z)).transposed()


CAM = None


def shot(path, centre_mm, right, up, px_w, px_h, ortho_mm=None, persp=None, transparent=False):
    global CAM
    if CAM is None:
        CAM = bpy.data.objects.new("SAYA_cam", bpy.data.cameras.new("SAYA_cam"))
        sc.collection.objects.link(CAM)
    sc.camera = CAM
    cd = CAM.data
    rot = cam_axes(right, up)
    c = Vector(centre_mm) * 0.001
    back = rot.col[2]
    if persp:
        cd.type = "PERSP"
        cd.lens = persp[1]
        CAM.matrix_world = Matrix.Translation(c + back * persp[0] * 0.001) @ rot.to_4x4()
    else:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_mm * 0.001
        CAM.matrix_world = Matrix.Translation(c + back * 3.0) @ rot.to_4x4()
    cd.clip_start = 0.001
    cd.clip_end = 20.0
    sc.render.resolution_x = px_w
    sc.render.resolution_y = px_h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("WROTE", path, flush=True)


# ------------------------------------------------------------------------------------------------- scene from bytes
def ue_socket_to_blender_matrix(rec):
    from pipeline.helpers import UE_MIRROR
    loc = rec["location_cm"]
    r = rec["rotation_deg"]
    roll, pitch, yaw = (math.radians(r[k]) for k in ("roll", "pitch", "yaw"))
    basis = (Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(-pitch, 3, "Y") @ Matrix.Rotation(roll, 3, "X"))
    M = (UE_MIRROR @ basis @ UE_MIRROR).to_4x4()
    M.translation = Vector((loc[0] * 0.1, -loc[1] * 0.1, loc[2] * 0.1)) * 0.1   # cm -> m
    return M


def append_materials(blend, names):
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        dst.materials = [n for n in src.materials if n in names]
    return {m.name: m for m in dst.materials}


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def assign(objs, mats):
    for o in objs:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            base = slot.material.name.split(".")[0] if slot.material else None
            if base in mats:
                slot.material = mats[base]


def build_scene():
    global sc
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    mats = append_materials(ROOT / "Assets" / "Katana" / "Saya.blend", S.SLOT_NAMES)
    mats.update(append_materials(ROOT / "Assets" / "Katana" / "Katana.blend",
                                 ["M_Katana_Blade", "M_Katana_Fittings", "M_Katana_Grip"]))
    saya_objs = import_fbx(ROOT / "Exports" / "Katana" / f"{S.NAME}.fbx")
    kat_objs = import_fbx(S.KATANA_FBX)
    assign(saya_objs + kat_objs, mats)
    side = json.loads((ROOT / "Exports" / "Katana" / f"{S.NAME}.sockets.json").read_text(encoding="utf-8"))
    hol = ue_socket_to_blender_matrix(next(r for r in side["sockets"] if r["socket"] == "Holster"))
    for o in kat_objs:
        if o.parent is None:
            o.matrix_world = hol @ o.matrix_world
    bpy.context.view_layer.update()      # children's matrix_world must follow before the sheet copies read them
    for o in saya_objs + kat_objs:
        if o.name.startswith("UCX_") or o.type != "MESH":
            o.hide_render = True
    lod = lambda objs, base, i: next(o for o in objs if o.type == "MESH" and o.name.startswith(f"{base}_LOD{i}"))
    saya = [lod(saya_objs, S.NAME, i) for i in range(3)]
    kat = [lod(kat_objs, "SM_Katana", i) for i in range(3)]
    return saya, kat


def show(objs):
    keep = {o.name for o in objs}
    for o in sc.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep


# ------------------------------------------------------------------------------------------------- gallery
def cutaway_mesh(src):
    """A copy of the saya LOD0 with the omote half (y < 0) cut away and the cut faces filled (render-only)."""
    me = src.data.copy()
    ob = bpy.data.objects.new("SAYA_cutaway", me)
    sc.collection.objects.link(ob)
    ob.matrix_world = src.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    inv = ob.matrix_world.inverted()
    co = inv @ Vector((0, 0, 0))
    no = (inv.to_3x3() @ Vector((0, 1, 0))).normalized()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=True)
    nfaces = len(bm.faces)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    sec = bpy.data.materials.new("SAYA_section")
    sec.use_nodes = True
    bsdf = next(n for n in sec.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.43, 0.28, 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    me.materials.append(sec)
    for f in bm.faces[nfaces:]:
        f.material_index = len(me.materials) - 1
    bmesh.ops.triangulate(bm, faces=bm.faces[nfaces:])
    bm.to_mesh(me)
    bm.free()
    return ob


def gallery(saya, kat):
    lights_studio()
    show([saya[0]])
    shot(OUT / "saya_hero.png", (40, 0, 270), (0.36, -0.22, 0.91), (-0.92, -0.14, 0.33), 2400, 1350, persp=(1350, 50))
    shot(OUT / "saya_mouth.png", (-2, 0, -76), (0.55, -0.65, 0.35), (-0.75, -0.3, 0.55), 1600, 1600, persp=(170, 70))
    shot(OUT / "saya_kurikata.png", (-3, -16, 0), (0.2, -0.35, 1.0), (-0.6, -0.75, 0.1), 1600, 1200, persp=(150, 70))
    a = (S.S_EN - 15) / S.R
    tip = S.arc_to_xyz(S.S_EN - 15, 12, 0) - np.array([0, 0, S.Z_OFF])
    shot(OUT / "saya_kojiri.png", tuple(tip), (math.sin(a), -0.5, math.cos(a)), (-math.cos(a), -0.2, math.sin(a)),
         1600, 1100, persp=(170, 70))
    show([saya[0], kat[0]])
    shot(OUT / "saya_sheathed_hero.png", (30, 0, 120), (0.36, -0.22, 0.91), (-0.92, -0.14, 0.33), 2400, 1350,
         persp=(1650, 50))
    shot(OUT / "saya_sheathed_side.png", (25, 0, 140), (0, 0, 1), (-1, 0, 0), 2600, 640, ortho_mm=1040)
    shot(OUT / "saya_sheathed_top.png", (25, 0, 140), (0, 0, 1), (0, 1, 0), 2600, 420, ortho_mm=1040)
    shot(OUT / "saya_seat.png", (-6, -4, -80), (0.0, 0.77, 0.6), (-1, 0, 0), 1600, 1200, persp=(150, 60))
    # cutaway: the omote half of the saya removed, the katana seated by the exported Holster
    cut = cutaway_mesh(saya[0])
    show([cut, kat[0]])
    shot(OUT / "saya_cutaway.png", (25, 0, 140), (0, 0, 1), (-1, 0, 0), 2600, 640, ortho_mm=1040)
    shot(OUT / "saya_cutaway_mouth.png", (0, 0, -66), (0, 0, 1), (-1, 0, 0), 1600, 1000, ortho_mm=75)
    tip_s = S.arc_to_xyz(S.K.S_TIP - 8, 8, 0) - np.array([0, 0, S.Z_OFF])
    a = (S.K.S_TIP - 8) / S.R
    shot(OUT / "saya_cutaway_tip.png", tuple(tip_s), (math.sin(a), 0, math.cos(a)), (-math.cos(a), 0, math.sin(a)),
         1600, 1000, ortho_mm=70)
    bpy.data.objects.remove(cut, do_unlink=True)
    # LOD strip
    for i, o in enumerate(saya):
        show([o])
        shot(OUT / f"saya_lod{i}.png", (40, 0, 280), (0, 0, 1), (-1, 0, 0), 2000, 400, ortho_mm=760)
        shot(OUT / f"saya_lod{i}_mouth.png", (-2, 0, -60), (0.55, -0.65, 0.35), (-0.75, -0.3, 0.55), 1000, 1000,
             persp=(230, 60))
    show([saya[0]])
    # wireframe (Workbench)
    eng = sc.render.engine
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = (0.8, 0.8, 0.8)
    m = saya[0].modifiers.new("wf", "WIREFRAME")
    m.thickness = 0.00012
    m.use_replace = False
    shot(OUT / "saya_wire.png", (40, 0, 280), (0, 0, 1), (-1, 0, 0), 2400, 520, ortho_mm=760)
    shot(OUT / "saya_wire_mouth.png", (-2, 0, -60), (0.55, -0.65, 0.35), (-0.75, -0.3, 0.55), 1400, 1400, persp=(200, 60))
    saya[0].modifiers.remove(m)
    sc.render.engine = eng
    clear_lights()


# ------------------------------------------------------------------------------------------------- sheet framing
def sheet(saya, kat):
    """Objects placed with the sheet's view matrices (sheet mm -> metres), camera straight down at 5 px per mm."""
    sh_objs = []
    zoff = Matrix.Translation((0, 0, S.Z_OFF / 1000.0))   # saya frame -> sword frame

    def place(objs, rot, off, tag):
        M = Matrix.Translation(Vector(off) * 0.001) @ rot.to_4x4() @ zoff
        for o in objs:
            d = bpy.data.objects.new(f"{tag}_{o.name}", o.data)
            sc.collection.objects.link(d)
            d.matrix_world = M @ o.matrix_world
            sh_objs.append(d)
    place([saya[0]], SIDE, (OX, ROW_B, 0), "B_side")
    place([saya[0]], TOP, (OX, ROW_B_TOP, 0), "B_top")
    place([saya[0]], END, (END_X, ROW_B, 0), "B_end")
    place([saya[0], kat[0]], SIDE, (OX, ROW_C, 0), "C_side")
    place([saya[0], kat[0]], TOP, (OX, ROW_C_TOP, 0), "C_top")
    place([saya[0], kat[0]], END, (END_X, ROW_C, 0), "C_end")
    show(sh_objs)
    # lighting for a plane of objects seen from +Z: a large soft key from the camera side, top-left (as the sheet)
    # (a dim reflection environment: the camera-facing gloss lacquer would otherwise mirror the bright studio top)
    env = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND" and not n.inputs["Color"].is_linked
               and False) if False else None
    for n in sc.world.node_tree.nodes:
        if n.type == "BACKGROUND" and n.inputs["Color"].is_linked:
            n.inputs["Strength"].default_value = 0.25
    area("sheet_key", (0.2, 1.4, 2.0), (0.7, 0.6, 0.0), 2.5, 60.0)
    area("sheet_fill", (1.2, -0.2, 1.5), (0.7, 0.6, 0.0), 2.5, 15.0, color=(0.92, 0.95, 1.0))
    for name, (x0, y0, x1, y1) in SHEET_CROPS.items():
        w, h = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2 / PX_PER_MM, 1200.0 - (y0 + y1) / 2 / PX_PER_MM
        for suffix, transp in (("", False), ("_mask", True)):
            shot(OUT / f"saya_sheet_{name}{suffix}.png", (cx, cy, 0.0), (1, 0, 0), (0, 1, 0), w, h,
                 ortho_mm=max(w, h) / PX_PER_MM, transparent=transp)
    for o in sh_objs:
        bpy.data.objects.remove(o, do_unlink=True)
    clear_lights()


def main():
    saya, kat = build_scene()
    gpu()
    world_studio(env_strength=1.0)
    if SET in ("all", "gallery"):
        gallery(saya, kat)
    if SET in ("all", "sheet"):
        sheet(saya, kat)
    print("SAYA_RENDER_DONE", flush=True)


main()
