"""pd_geodiag_seethrough.py -- locate the see-through shoulder slivers of the UE captures on the body mesh.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P Scripts/MetaHuman/pd_geodiag_seethrough.py

Renders a world-position pass of the FaceC dump (head + body + face parts) through the exact UE capture cameras, and
flags pixels where the dump has skin but the UE capture shows the grey backdrop (a 2-px silhouette band is ignored).
Those pixels are mapped to body vertices. The body dump is closed (only the neck ring is open), so if such pixels
exist the skin is being removed at RENDER time (outfit hidden-face mask in the preview material), not in the mesh.
Writes geodiag/seethrough_report.json and geodiag/seethrough/*.png
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, load_obj  # noqa: E402

NH = 24049
CAP = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/faces/captures")
SDIR = OUT / "seethrough"
SDIR.mkdir(parents=True, exist_ok=True)
POS_OFFSET = (100.0, 100.0, 0.0)

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
scene.cycles.samples = 1
scene.cycles.use_denoising = False
scene.render.filter_size = 0.01
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "OPEN_EXR"
scene.render.image_settings.color_depth = "32"
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.0

m = bpy.data.materials.new("pos")
m.use_nodes = True
nt = m.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(n)
geo = nt.nodes.new("ShaderNodeNewGeometry")
add = nt.nodes.new("ShaderNodeVectorMath")
add.operation = "ADD"
add.inputs[1].default_value = POS_OFFSET
em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(geo.outputs["Position"], add.inputs[0])
nt.links.new(add.outputs["Vector"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])


def make_mesh(name, V, F):
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
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


Vf, Ff = load_obj(DUMPS["FaceC_Face"])
Vb, Fb = load_obj(DUMPS["FaceC_Body"])
make_mesh("face", Vf, Ff)
make_mesh("body", Vb, Fb)
kd = KDTree(len(Vb))
for i, p in enumerate(Vb):
    kd.insert(Vector(p), i)
kd.balance()

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 1.0
cam_data.clip_end = 5000.0


def ue2bl(p):
    return Vector((p[0], -p[1], p[2]))


def load(path):
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


def erode(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out &= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


FC = (0.0, 5.959721088409424, 173.6)
a35 = math.radians(35.0)
PBC = CAP.parent.parent / "captures"
# (camera loc, look-at, capture file). mh_* = the conform session (pb_conform attempt 4), same face camera centre.
VIEWS = {"Face_Front": ((FC[0], FC[1] + 70, FC[2]), FC, CAP / "FaceC_Face_Front.png"),
         "Face_ThreeQuarter": ((FC[0] + 70 * math.sin(a35), FC[1] + 70 * math.cos(a35), FC[2]), FC, CAP / "FaceC_Face_ThreeQuarter.png"),
         "Body_Front": ((0.0, 380.0, 93.0), (0.0, 0.0, 93.0), CAP / "FaceC_Body_Front.png"),
         "mh_Face_Front": ((FC[0], FC[1] + 70, FC[2]), FC, PBC / "mh_Face_Front.png"),
         "mh_Face_ThreeQuarter": ((FC[0] + 70 * math.sin(a35), FC[1] + 70 * math.cos(a35), FC[2]), FC, PBC / "mh_Face_ThreeQuarter.png")}
report = {"body_dump_closed": "see geodiag_report.json body.*: one boundary loop (neck, 92 edges), 0 non-manifold edges",
          "views": {}}
for view, (loc, look, capfile) in VIEWS.items():
    l, t = ue2bl(loc), ue2bl(look)
    cam.location = l
    cam.rotation_euler = (t - l).to_track_quat("-Z", "Y").to_euler()
    cam_data.angle = math.radians(30.0)
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1200
    scene.render.filepath = str(SDIR / f"pos_{view}.exr")
    bpy.ops.render.render(write_still=True)
    pos = load(SDIR / f"pos_{view}.exr")
    fg = pos.max(2) > 1.0
    pos = pos - np.array(POS_OFFSET, np.float32)
    ue = load(capfile)
    bgc = np.median(ue[:30, :30].reshape(-1, 3), axis=0)
    ue_bg = np.abs(ue - bgc).max(2) < 0.025
    see = erode(fg, 2) & ue_bg
    ys, xs = np.nonzero(see)
    P = pos[ys, xs].copy()
    P[:, 1] *= -1
    hits = [kd.find(Vector(p)) for p in P]
    on_body = [h for h in hits if h[2] < 0.6]
    vids = sorted(set(h[1] for h in on_body))
    r = {"see_through_pixels": int(len(ys)), "on_body_surface": len(on_body), "body_vertices": len(vids)}
    if len(vids):
        Q = Vb[vids]
        side = {"+X (character left)": Q[Q[:, 0] > 0], "-X (character right)": Q[Q[:, 0] < 0]}
        r["clusters"] = {k: {"n": int(len(v)), "min": np.round(v.min(0), 2).tolist(), "max": np.round(v.max(0), 2).tolist()}
                         for k, v in side.items() if len(v)}
        np.save(SDIR / f"verts_{view}.npy", np.array(vids))
    report["views"][view] = r
    ov = ue.copy()
    ov[see] = (1, 0, 1)
    save_png(ov, SDIR / f"overlay_{view}.png")
(OUT / "seethrough_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))
