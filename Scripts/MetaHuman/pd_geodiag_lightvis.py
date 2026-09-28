"""pd_geodiag_lightvis.py -- which UE-capture pixels get NO direct light from the capture rig, and how dark they are in UE.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P Scripts/MetaHuman/pd_geodiag_lightvis.py

For the exact UE capture camera it renders, from the FaceC dump geometry, the direct irradiance of each of the three
directional lights of pb_conform.py's LIGHT_RIG separately (white diffuse, black world, shadows on for all three
so 'no light' is the strict geometric bound), plus a head/body id pass. Then it bins the UE capture pixels by
'direct light received' and by surface (jaw underside vs everything else on the head) and reports UE brightness.
If every no-direct-light head pixel is near-black in UE -> the sky light contributes ~nothing on the head skin.
If only the jaw-underside ones are black -> something surface-specific (AO/cavity texture) kills the ambient there.
Writes geodiag/lightvis_report.json and geodiag/lightvis/*.png
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, load_obj  # noqa: E402

NH = 24049
CAP = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/faces/captures")
LDIR = OUT / "lightvis"
LDIR.mkdir(parents=True, exist_ok=True)
SUBJECT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "FaceC"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    scene.cycles.device = "GPU"
except Exception as exc:  # noqa: BLE001
    print("GPU setup failed:", exc)
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0            # direct light only
scene.render.filter_size = 0.01
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "OPEN_EXR"
scene.render.image_settings.color_depth = "32"
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bgn = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bgn.inputs["Strength"].default_value = 0.0


def diffuse_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    return m


WHITE = diffuse_mat("white", (1, 1, 1))


def emission(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(em.outputs["Emission"], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    return m


def downfacing_id_mat():
    """R = 1 on head, G = 1 on body, B = 1 where the smooth normal points down (n.z < -0.5)."""
    m = bpy.data.materials.new("id")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    lt = nt.nodes.new("ShaderNodeMath")
    lt.operation = "LESS_THAN"
    lt.inputs[1].default_value = -0.5
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "OBJECT"
    attr.attribute_name = "pass_index"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], lt.inputs[0])
    # object color carries head/body id in R/G
    oc = nt.nodes.new("ShaderNodeObjectInfo")
    sepc = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(oc.outputs["Color"], sepc.inputs[0])
    nt.links.new(sepc.outputs[0], comb.inputs[0])
    nt.links.new(sepc.outputs[1], comb.inputs[1])
    nt.links.new(lt.outputs[0], comb.inputs[2])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(comb.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    return m


IDM = downfacing_id_mat()


def make_mesh(name, V, F, color):
    V = np.asarray(V, dtype=np.float64).copy()
    V[:, 1] *= -1.0
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3)
    me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.validate()
    me.shade_smooth()
    me.materials.append(WHITE)
    ob = bpy.data.objects.new(name, me)
    ob.color = (*color, 1)
    scene.collection.objects.link(ob)
    return ob


Vf, Ff = load_obj(DUMPS[f"{SUBJECT}_Face"])
Vb, Fb = load_obj(DUMPS[f"{SUBJECT}_Body"])
FH = Ff[np.all(Ff < NH, axis=1)]
objs = [make_mesh("head", Vf[:NH], FH, (1, 0, 0)), make_mesh("body", Vb, Fb, (0, 1, 0)),
        make_mesh("others", Vf, Ff[~np.all(Ff < NH, axis=1)], (0, 0, 0))]

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 1.0


def ue2bl(p):
    return Vector((p[0], -p[1], p[2]))


def ue_dir(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))


LIGHTS = {"key": ue_dir(-27, -117), "fill": ue_dir(-12, -58), "rim": ue_dir(-37, 90)}
suns = {}
for name, travel in LIGHTS.items():
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = 1.0
    ld.angle = math.radians(0.5)
    ob = bpy.data.objects.new(name, ld)
    ob.rotation_euler = ue2bl(travel).normalized().to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)
    suns[name] = ob


def render(path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1][..., :3]
    bpy.data.images.remove(img)
    return a


def load_png(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1][..., :3]
    bpy.data.images.remove(img)
    return a


def save_png(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


FC = (0.0, 5.959721088409424, 173.6)
a35 = math.radians(35.0)
VIEWS = {"ThreeQuarter": (FC[0] + 70 * math.sin(a35), FC[1] + 70 * math.cos(a35), FC[2]),
         "Front": (FC[0], FC[1] + 70, FC[2])}
report = {"subject": SUBJECT, "views": {}}
for view, loc in VIEWS.items():
    l, t = ue2bl(loc), ue2bl(FC)
    cam.location = l
    cam.rotation_euler = (t - l).to_track_quat("-Z", "Y").to_euler()
    cam_data.angle = math.radians(30.0)
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1200
    # id / down-facing pass
    for o in objs:
        o.data.materials[0] = IDM
    for s in suns.values():
        s.hide_render = True
    idp = render(LDIR / f"{SUBJECT}_id_{view}.exr")
    for o in objs:
        o.data.materials[0] = WHITE
    direct = {}
    for name in suns:
        for n2, s in suns.items():
            s.hide_render = n2 != name
        direct[name] = render(LDIR / f"{SUBJECT}_{name}_{view}.exr")[..., 0]
    for s in suns.values():
        s.hide_render = False
    total = direct["key"] * 4 + direct["fill"] * 2 + direct["rim"] * 2      # rig intensities
    head = idp[..., 0] > 0.5
    down = idp[..., 2] > 0.5
    if not (CAP / f"{SUBJECT}_Face_{view}.png").is_file():
        continue
    ue = load_png(CAP / f"{SUBJECT}_Face_{view}.png")
    lum = ue.max(2) * 255.0
    nodirect = head & (total < 0.02)
    some = head & (total >= 0.02)
    jaw = nodirect & down & (np.arange(1200)[:, None] > 700)
    other_nd = nodirect & ~jaw
    out = {"head_pixels": int(head.sum()), "no_direct_light_head_pixels": int(nodirect.sum()),
           "no_direct_jaw_underside_pixels": int(jaw.sum()), "no_direct_other_pixels": int(other_nd.sum())}
    for label, m in (("UE_maxRGB_on_jaw_underside_no_direct", jaw), ("UE_maxRGB_on_other_no_direct", other_nd),
                     ("UE_maxRGB_on_directly_lit_head", some)):
        v = lum[m]
        out[label] = {"n": int(m.sum()), "p5_p50_p95": np.round(np.percentile(v, [5, 50, 95]), 1).tolist() if len(v) else None,
                      "fraction_below_12": round(float((v < 12).mean()), 3) if len(v) else None}
    # where are the other no-direct pixels and how bright are they (per connected blob, coarse 20 px grid)
    ys, xs = np.nonzero(other_nd)
    cells = {}
    for y, x in zip(ys, xs):
        cells.setdefault((y // 25, x // 25), []).append(lum[y, x])
    out["other_no_direct_cells_25px"] = sorted(
        [{"xy": [int(k[1] * 25), int(k[0] * 25)], "n": len(v), "median_UE": round(float(np.median(v)), 1)}
         for k, v in cells.items() if len(v) >= 20], key=lambda d: d["median_UE"])[:40]
    report["views"][view] = out
    # visualization: UE capture; no-direct-light head pixels tinted cyan, jaw ones magenta
    vis = ue.copy()
    vis[other_nd] = vis[other_nd] * 0.4 + np.array([0, 0.6, 0.6])
    vis[jaw] = vis[jaw] * 0.4 + np.array([0.6, 0, 0.6])
    save_png(vis, LDIR / f"{SUBJECT}_nodirect_{view}.png")
    save_png(np.stack([total / 4.0] * 3, -1) ** (1 / 2.2), LDIR / f"{SUBJECT}_directsum_{view}.png")
(OUT / f"lightvis_report_{SUBJECT}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))
