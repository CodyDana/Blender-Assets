"""Render set for the pines (TREE_BUILDING_STUDY.md 6.3), Cycles headless (GPU if present), denoised.

    blender -b <DojoPines.blend> --factory-startup --python Scripts/dojo/pines/render_pines.py -- --out DIR
            [--variants PineA1,...] [--views front,side,3q] [--passes final,sil] [--closeups] [--context]
            [--samples 160] [--res 900]

Views: front = camera on -Y looking +Y (the sheet's front panel); side = camera on +X looking -X (image right = +Y,
the convention make_spec.py uses for the side panel); 3q = camera at 45 deg between them. All tree views are
orthographic (study 6.3: silhouette pairs orthographic) with one scale per tree, so front / side / 3/4 share px/m.
Passes: final (materials, soft studio light on the sheet's light grey), sil (flat foliage green / wood brown /
rock grey on the sheet's grey, Standard view: exact colours for measure_tree.py).
Writes <out>/<variant>_<view>_<pass>.png and <out>/render_meta.json (camera scale, base pixel per image).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = json.loads((HERE / "pines_spec.json").read_text(encoding="utf-8"))
BG_SRGB = 182.0 / 255.0
VIEWS = {"front": 0.0, "side": 90.0, "3q": 45.0}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="")
    ap.add_argument("--views", default="front,side,3q")
    ap.add_argument("--passes", default="final,sil")
    ap.add_argument("--closeups", action="store_true")
    ap.add_argument("--context", action="store_true")
    ap.add_argument("--samples", type=int, default=160)
    ap.add_argument("--res", type=int, default=900)
    ap.add_argument("--figure", action="store_true", help="add the 1.8 m figure to final views")
    return ap.parse_args(argv)


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def setup_cycles(samples):
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
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 8
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.resolution_percentage = 100


def tree_objects(v, mound=True):
    """The variant's meshes plus (v2) its family's optional base mound, shown the way the sheet shows the trees."""
    fam = f"SM_DKN_BaseMound_{v[4]}"
    return [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith(f"SM_DKN_{v}_")
                                                                   or (mound and o.name == fam))]


def show_only(v):
    for o in bpy.data.objects:
        if o.type == "MESH":
            keep = (o.name.startswith(f"SM_DKN_{v}_") or o.name.startswith("__")
                    or o.name == f"SM_DKN_BaseMound_{v[4]}")
            if o.name.startswith("UCX_"):
                keep = False
            o.hide_render = not keep
            o.hide_viewport = not keep


def bbox(objs):
    pts = []
    for o in objs:
        pts.append(np.array([o.matrix_world @ Vector(c) for c in o.bound_box]))
    P = np.vstack(pts)
    return P.min(0), P.max(0)


def make_world(strength, colour):
    w = bpy.data.worlds.new("W") if "W" not in bpy.data.worlds else bpy.data.worlds["W"]
    bpy.context.scene.world = w
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (*colour, 1.0)
    bgn.inputs["Strength"].default_value = strength
    return w


def studio_rig():
    for n in ("__key", "__fill", "__rim"):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n])
    key = bpy.data.lights.new("__key", "SUN")
    key.energy = 3.2
    key.angle = math.radians(12)
    key.color = (1.0, 0.97, 0.92)
    ko = bpy.data.objects.new("__key", key)
    ko.rotation_euler = (math.radians(50), 0, math.radians(-35))
    bpy.context.scene.collection.objects.link(ko)
    fill = bpy.data.lights.new("__fill", "SUN")
    fill.energy = 0.9
    fill.angle = math.radians(40)
    fill.color = (0.92, 0.95, 1.0)
    fo = bpy.data.objects.new("__fill", fill)
    fo.rotation_euler = (math.radians(70), 0, math.radians(140))
    bpy.context.scene.collection.objects.link(fo)
    make_world(0.8, (0.8, 0.8, 0.8))


def shadow_floor():
    if "__floor" in bpy.data.objects:
        return bpy.data.objects["__floor"]
    me = bpy.data.meshes.new("__floor")
    s = 40.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("__floor", me)
    ob.is_shadow_catcher = True
    bpy.context.scene.collection.objects.link(ob)
    return ob


def figure(x, y, height=1.8):
    """A plain grey 1.8 m human silhouette (capsules), like the sheet's scale figure."""
    if "__figure" in bpy.data.objects:
        ob = bpy.data.objects["__figure"]
        ob.location = (x, y, 0)
        return ob
    import bmesh
    bm = bmesh.new()
    s = height / 1.8

    def cyl(p0, p1, r, seg=12):
        p0, p1 = Vector(p0) * s, Vector(p1) * s
        d = p1 - p0
        mat = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * s, radius2=r * s, depth=d.length)
        for v in res["verts"]:
            v.co = mat @ v.co + (p0 + p1) / 2

    def sph(c, r):
        res = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r * s)
        for v in res["verts"]:
            v.co += Vector(c) * s
    sph((0, 0, 1.68), 0.11)
    cyl((0, 0, 1.52), (0, 0, 1.60), 0.05)
    cyl((0, 0, 0.98), (0, 0, 1.50), 0.17)
    cyl((-0.1, 0, 0.05), (-0.1, 0, 0.98), 0.075)
    cyl((0.1, 0, 0.05), (0.1, 0, 0.98), 0.075)
    cyl((-0.23, 0, 0.82), (-0.21, 0, 1.46), 0.05)
    cyl((0.23, 0, 0.82), (0.21, 0, 1.46), 0.05)
    me = bpy.data.meshes.new("__figure")
    bm.to_mesh(me)
    ob = bpy.data.objects.new("__figure", me)
    mat = bpy.data.materials.new("__figure_mat")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.2, 0.2, 0.2, 1)
    b.inputs["Roughness"].default_value = 0.9
    me.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, 0)
    return ob


def flat_mat(name, srgb):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*[srgb_to_lin(c / 255.0) for c in srgb], 1)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(e.outputs["Emission"], out.inputs["Surface"])
    return m


def ortho_camera(target, az_deg, scale, dist=60.0, elev_deg=0.0):
    cam = bpy.data.objects.get("__cam")
    if cam is None:
        cd = bpy.data.cameras.new("__cam")
        cam = bpy.data.objects.new("__cam", cd)
        bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_start = 0.1
    cam.data.clip_end = 400
    az = math.radians(az_deg)
    el = math.radians(elev_deg)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def persp_camera(loc, look, lens=50.0):
    cam = bpy.data.objects.get("__pcam")
    if cam is None:
        cd = bpy.data.cameras.new("__pcam")
        cam = bpy.data.objects.new("__pcam", cd)
        bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.data.clip_start = 0.01
    cam.data.clip_end = 2000
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def project_px(cam, p, res):
    """Pixel (x, y from the top) of world point p in an ORTHO camera render."""
    M = cam.matrix_world.inverted()
    q = M @ Vector(p)
    s = cam.data.ortho_scale
    return (res / 2 + q.x / s * res, res / 2 - q.y / s * res)


def view_extent(v, az_deg):
    """Projected horizontal extent (min, max along the view's right axis) of the tree's vertices."""
    a = math.radians(az_deg)
    rv = np.array([math.cos(a), math.sin(a), 0.0])
    lo, hi = 1e9, -1e9
    for o in tree_objects(v):
        me = o.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        u = co.reshape(-1, 3) @ rv
        lo, hi = min(lo, float(u.min())), max(hi, float(u.max()))
    return lo, hi


def tree_frame(v):
    objs = tree_objects(v)
    lo, hi = bbox([o for o in objs])
    # horizontal extent over all azimuths: the radius of the xy bounding circle about the trunk base
    R = 0.0
    for o in objs:
        me = o.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        R = max(R, float(np.sqrt((co[:, 0] ** 2 + co[:, 1] ** 2).max())))
    top = float(hi[2])
    bottom = min(0.0, float(lo[2]))
    return {"R": R, "top": top, "bottom": bottom}


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def set_view(mode):
    sc = bpy.context.scene
    if mode == "sil":
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    else:
        sc.view_settings.view_transform = "AgX"
        try:
            sc.view_settings.look = "AgX - Base Contrast"
        except TypeError:
            sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0


def with_sil_materials(objs):
    saved = []
    fol_m = flat_mat("__sil_fol", (40, 130, 40))
    wood_m = flat_mat("__sil_wood", (130, 80, 40))
    rock_m = flat_mat("__sil_rock", (110, 110, 110))
    for o in objs:
        saved.append((o, [s.material for s in o.material_slots]))
        m = fol_m if o.name.endswith("_Foliage") else (rock_m if (o.name.endswith("_Rock") or "BaseMound" in o.name) else wood_m)
        for s in o.material_slots:
            s.material = m
    return saved


def restore(saved):
    for o, mats in saved:
        for s, m in zip(o.material_slots, mats):
            s.material = m


def main():
    a = args()
    out = Path(a.out)
    if not out.is_absolute():
        out = (ROOT / out).resolve()   # blender's cwd is not the repo: never write outside it
    out.mkdir(parents=True, exist_ok=True)
    setup_cycles(a.samples)
    sc = bpy.context.scene
    variants = [v for v in SPEC if (not a.variants or v in a.variants.split(","))]
    meta = {}
    mp = out / "render_meta.json"
    if mp.exists():
        meta = json.loads(mp.read_text())
    studio_rig()
    floor = shadow_floor()
    for v in variants:
        show_only(v)
        objs = tree_objects(v)
        fr = tree_frame(v)
        H = fr["top"] - fr["bottom"]
        # one scale per tree (front / side / 3/4 share px per m): the widest projected view or the height
        ext = {view: view_extent(v, VIEWS[view]) for view in a.views.split(",")}
        scale = max(max(e[1] - e[0] for e in ext.values()), H) * 1.10
        centre_z = fr["bottom"] + scale / 2 - 0.05 * scale
        sc.render.resolution_x = a.res
        sc.render.resolution_y = a.res
        for view in a.views.split(","):
            az = VIEWS[view]
            uc = 0.5 * (ext[view][0] + ext[view][1])
            ar = math.radians(az)
            cam = ortho_camera((uc * math.cos(ar), uc * math.sin(ar), centre_z), az, scale)
            bpy.context.view_layer.update()
            base_px = project_px(cam, (0, 0, 0), a.res)
            top_px = project_px(cam, (0, 0, fr["top"]), a.res)
            meta[f"{v}_{view}"] = {"scale": scale, "res": a.res, "base_px": base_px, "px_per_m": a.res / scale,
                                   "top_z": fr["top"], "az": az}
            fig = None
            for p in a.passes.split(","):
                if p == "sil":
                    set_view("sil")
                    make_world(1.0, (srgb_to_lin(BG_SRGB),) * 3)
                    floor.hide_render = True
                    saved = with_sil_materials(objs)
                    sc.cycles.samples = 16
                    sc.cycles.use_denoising = False
                    for n in ("__key", "__fill"):
                        bpy.data.objects[n].hide_render = True
                    sc.render.film_transparent = True
                    sc.render.image_settings.color_mode = "RGBA"
                    render(out / f"{v}_{view}_sil.png")
                    sc.render.film_transparent = False
                    restore(saved)
                    for n in ("__key", "__fill"):
                        bpy.data.objects[n].hide_render = False
                    sc.cycles.use_denoising = True
                    sc.cycles.samples = a.samples
                    floor.hide_render = False
                else:
                    set_view("final")
                    make_world(0.8, (0.8, 0.8, 0.8))
                    sc.render.film_transparent = True
                    sc.render.image_settings.color_mode = "RGBA"
                    render(out / f"{v}_{view}_final.png")
                    sc.render.film_transparent = False
    mp.write_text(json.dumps(meta, indent=1))
    if a.closeups:
        closeups(out, a)
    if a.context:
        context_shot(out, a)


def closeups(out, a):
    """Four close-ups matching the sheet's bottom row: bark, pad from the side, pad from above, branch fork."""
    sc = bpy.context.scene
    set_view("final")
    make_world(0.8, (0.8, 0.8, 0.8))
    sc.render.film_transparent = True
    bpy.data.objects["__floor"].hide_render = True
    shots = {}
    # bark: the big leaning trunk (pine C1), about 0.6 m of it, low, slightly from the side
    sC = SPEC["PineC1"]
    t = np.array(sC["trunk"]["pts"])
    z0 = 1.2
    i = int(np.argmin(np.abs(t[:, 2] - z0)))
    p = t[i]
    r = sC["trunk"]["min_r"][i]
    shots["bark"] = ("PineC1", p + np.array([0.12, -(r + 0.62), 0.05]), p + np.array([0.0, 0.0, 0.0]), 60, (1100, 980))
    # pad side: a mid pad of pine B1 seen level from outside
    sB = SPEC["PineB1"]
    sA = SPEC["PineA1"]
    pad = sA["pads"][4]
    c = np.array(pad.get("profile", {}).get("centre", pad["centre"]))
    w = 2 * pad.get("profile", {}).get("hx", pad["rx"])
    dist = 1.0 * w / (36.0 / 50.0)
    shots["pad_side"] = ("PineA1", c + np.array([0.0, -dist, 0.02]), c + np.array([0, 0, 0.06]), 50, (1260, 1000))
    # pad from above: the apex pad of A1 (open sky above it)
    pad = sA["pads"][0]
    c = np.array(pad.get("profile", {}).get("centre", pad["centre"]))
    w = 2 * pad.get("profile", {}).get("hx", pad["rx"])
    shots["pad_top"] = ("PineA1", c + np.array([0.0, -0.02, 1.0 * w / (36.0 / 50.0) + 0.3]), c, 50, (880, 1000))
    # branch fork (judge r0: 'sbs_closeup_fork shows no fork at all'): a real primary fork, pine C1's trunk top
    # where two scaffold limbs leave it together and the leader goes on up (the sheet's fork close-up)
    sC1 = SPEC["PineC1"]
    L1, L2 = np.array(sC1["limbs"][0]["pts"][0]), np.array(sC1["limbs"][1]["pts"][0])
    f = 0.5 * (L1 + L2)
    shots["fork"] = ("PineC1", f + np.array([0.35, -2.3, -0.35]), f + np.array([0.0, 0.0, 0.05]), 50, (1120, 1000))
    key, fill = bpy.data.objects["__key"], bpy.data.objects["__fill"]
    k_rot, k_e, k_a, f_e = tuple(key.rotation_euler), key.data.energy, key.data.angle, fill.data.energy
    for name, (v, loc, look, lens, res) in shots.items():
        show_only(v)
        for o in bpy.data.objects:
            if "BaseMound" in o.name:
                o.hide_render = True          # close-ups frame the tree only (the sheet's close-ups are isolated)
        sc.render.resolution_x, sc.render.resolution_y = res
        persp_camera(loc, look, lens)
        if name == "bark":
            # v2: the sheet's bark close-up is lit by a hard raking key from the upper left (G13 is measured on a
            # matched close-up): a small-angle sun grazing the trunk, weak fill and sky
            key.rotation_euler = (math.radians(58), 0, math.radians(-75))
            key.data.energy, key.data.angle, fill.data.energy = 4.2, math.radians(2.5), 0.25
            make_world(0.35, (0.8, 0.8, 0.8))
        render(out / f"closeup_{name}.png")
        key.rotation_euler, key.data.energy, key.data.angle, fill.data.energy = k_rot, k_e, k_a, f_e
        make_world(0.8, (0.8, 0.8, 0.8))
    sc.render.film_transparent = False
    bpy.data.objects["__floor"].hide_render = False


def context_shot(out, a):
    """Sunset context: the pines on a granite terrace edge over water, back-lit by a low sun (study 6.3)."""
    sc = bpy.context.scene
    set_view("final")
    for o in bpy.data.objects:
        if o.name.startswith("__") and o.type == "LIGHT":
            o.hide_render = True
    bpy.data.objects["__floor"].hide_render = True
    import bmesh
    # terrace: a granite slab 30 x 14 m, top at z 0, edge at y = +4, 3 m tall wall down to the water
    me = bpy.data.meshes.new("__terrace")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 30
        v.co.y = v.co.y * 14 - 3.0
        v.co.z = v.co.z * 3.2 - 1.6
    bm.to_mesh(me)
    ter = bpy.data.objects.new("__terrace", me)
    sc.collection.objects.link(ter)
    gm = bpy.data.materials.get("M_DJ_Granite") or bpy.data.materials.get("MI_DKN_PineRock")
    if gm is None:
        gm = bpy.data.materials.new("__stone")
    me.materials.append(gm)
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            nz = abs(poly.normal.z) > 0.5
            uvl.data[li].uv = ((co.x / 4.0, co.y / 4.0) if nz else ((co.x + co.y) / 4.0, co.z / 4.0))
    # water
    wm = bpy.data.meshes.new("__water")
    s = 400
    wm.from_pydata([(-s, -s, -2.6), (s, -s, -2.6), (s, s, -2.6), (-s, s, -2.6)], [], [(0, 1, 2, 3)])
    water = bpy.data.objects.new("__water", wm)
    sc.collection.objects.link(water)
    wmat = bpy.data.materials.new("__water_mat")
    wmat.use_nodes = True
    nt = wmat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.02, 0.05, 0.05, 1)
    b.inputs["Roughness"].default_value = 0.06
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.06
    nt.links.new(nz.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    wm.materials.append(wmat)
    # far ridges: dark layered silhouettes
    for k, (dist, h, col) in enumerate([(160, 38, (0.09, 0.07, 0.10)), (260, 70, (0.16, 0.12, 0.16))]):
        rm = bpy.data.meshes.new(f"__ridge{k}")
        xs = np.linspace(-600, 600, 80)
        rng = np.random.default_rng(10 + k)
        ys = h * (0.55 + 0.45 * np.abs(np.sin(xs / (90 + 40 * k) + k)) ) + rng.normal(0, h * 0.04, len(xs))
        verts = [(x, dist, -3.0) for x in xs] + [(x, dist, float(yv)) for x, yv in zip(xs, ys)]
        n = len(xs)
        faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
        rm.from_pydata(verts, [], faces)
        ro = bpy.data.objects.new(f"__ridge{k}", rm)
        sc.collection.objects.link(ro)
        mm = bpy.data.materials.new(f"__ridge_mat{k}")
        mm.use_nodes = True
        bb = next(nn for nn in mm.node_tree.nodes if nn.type == "BSDF_PRINCIPLED")
        bb.inputs["Base Color"].default_value = (*col, 1)
        bb.inputs["Roughness"].default_value = 1.0
        rm.materials.append(mm)
    # sky: gradient + a low warm sun straight ahead (back-light through the pads)
    w = bpy.data.worlds.new("__sunset")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bgn = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (1.0, 0.42, 0.16, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.20, 0.22, 0.42, 1)
    e = ramp.color_ramp.elements.new(0.56)
    e.color = (0.95, 0.62, 0.35, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bgn.inputs["Color"])
    bgn.inputs["Strength"].default_value = 1.6
    sun = bpy.data.lights.new("__sun", "SUN")
    sun.energy = 5.0
    sun.angle = math.radians(1.5)
    sun.color = (1.0, 0.62, 0.32)
    so = bpy.data.objects.new("__sun", sun)
    so.rotation_euler = (math.radians(84), 0, math.radians(145))    # low sun, back-right: rim + translucency
    sc.collection.objects.link(so)
    # the low sun itself, straight behind the trees (the lamp shines along its -Z)
    bpy.context.view_layer.update()
    ldir = so.matrix_world.to_3x3() @ Vector((0, 0, -1))
    sun_pos = -ldir * 420.0
    sm = bpy.data.meshes.new("__sundisc")
    import bmesh as _bm
    b_ = _bm.new()
    _bm.ops.create_uvsphere(b_, u_segments=24, v_segments=12, radius=9.0)
    b_.to_mesh(sm)
    sd = bpy.data.objects.new("__sundisc", sm)
    sd.location = sun_pos
    sc.collection.objects.link(sd)
    em = bpy.data.materials.new("__sun_em")
    em.use_nodes = True
    ent = em.node_tree
    for n in list(ent.nodes):
        if n.type != "OUTPUT_MATERIAL":
            ent.nodes.remove(n)
    e_ = ent.nodes.new("ShaderNodeEmission")
    e_.inputs["Color"].default_value = (1.0, 0.72, 0.42, 1)
    e_.inputs["Strength"].default_value = 60.0
    ent.links.new(e_.outputs["Emission"], next(n for n in ent.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    sm.materials.append(em)
    sd.visible_shadow = False
    # trees: C1 leaning out over the edge, B1 and A1 on the terrace, D1 on the rocks by the water
    place = {"PineC1": ((-2.0, 3.0, 0.0), 0.0), "PineB1": ((5.0, 2.4, 0.0), 20.0),
             "PineA1": ((9.0, 3.1, 0.0), -30.0), "PineD1": ((-9.5, 7.5, -2.6), 150.0),
             "PineA2": ((-8.5, 1.5, 0.0), 60.0)}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("SM_DKN_"):
            o.hide_render = True
    for v, (loc, rot) in place.items():
        for o in tree_objects(v, mound=v.endswith("1")):
            o.hide_render = False
            o.location = loc
            o.rotation_euler = (0, 0, math.radians(rot))
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.cycles.samples = max(a.samples, 192)
    sc.view_settings.exposure = -0.3
    persp_camera((2.0, -16.0, 6.0), (-1.0, 10.0, 1.2), 28)
    render(out / "context_sunset_terrace.png")
    persp_camera((0.5, -4.0, 1.9), (-4.0, 8.0, 4.4), 24)
    render(out / "context_sunset_close.png")


if __name__ == "__main__":
    main()
