"""pd_geodiag_pixmap.py -- map the dark jaw-line pixels of the UE captures back onto the mesh (headless Blender).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P Scripts/MetaHuman/pd_geodiag_pixmap.py

For the exact UE capture cameras (pb_face_design.face_shots) it renders a per-pixel world-position pass and a
normal pass of the FaceC dump geometry (1 sample, tiny pixel filter), aligns them with the UE capture PNGs,
picks the near-black line pixels (max RGB < 24/255) under the jaw, and reports for each:
nearest head vertex, N.V (grazing test), whether the key light is shadowed (ray cast), and whether the pixel sits
on the jaw or the neck side of the jaw/neck occluding contour. The vertex sets from the front and 3/4 views are
compared: a surface-attached cause (texture / normals) hits the same vertices in both views; a view-dependent one
(occlusion contour / screen-space) does not.
Writes WorkFiles/MetaHuman/player_default/geodiag/pixmap_report.json and overlay PNGs.
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
from pd_geodiag_lib import DUMPS, OUT, load_obj, vertex_normals  # noqa: E402

NH = 24049
CAP = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/faces/captures")
PDIR = OUT / "pixmap"
PDIR.mkdir(parents=True, exist_ok=True)
SUBJECT = "FaceC"

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
bgn = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bgn.inputs["Color"].default_value = (0, 0, 0, 1)
bgn.inputs["Strength"].default_value = 0.0


POS_OFFSET = (100.0, 100.0, 0.0)


def emission_mat(name, what):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    if what == "position":   # offset so every channel is positive (Blender world, cm); undone after reading
        add = nt.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        add.inputs[1].default_value = POS_OFFSET
        nt.links.new(geo.outputs["Position"], add.inputs[0])
        nt.links.new(add.outputs["Vector"], em.inputs["Color"])
    else:   # true (geometric, flat) normal and interpolated normal packed: use smooth normal, mapped 0..1
        mp = nt.nodes.new("ShaderNodeVectorMath")
        mp.operation = "MULTIPLY_ADD"
        mp.inputs[1].default_value = (0.5, 0.5, 0.5)
        mp.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs["Normal"], mp.inputs[0])
        nt.links.new(mp.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


POS = emission_mat("pos", "position")
NRM = emission_mat("nrm", "normal")


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
    me.shade_smooth()
    me.materials.append(POS)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


Vf, Ff = load_obj(DUMPS[f"{SUBJECT}_Face"])
Vb, Fb = load_obj(DUMPS[f"{SUBJECT}_Body"])
FH = Ff[np.all(Ff < NH, axis=1)]
head = make_mesh("head", Vf[:NH], FH)
body = make_mesh("body", Vb, Fb)
# the other face components (eyes, teeth, lashes...) too, so occlusion matches the UE render
rest = Ff[~np.all(Ff < NH, axis=1)]
others = make_mesh("others", Vf, rest)
hv = Vf[:NH]
hn = -vertex_normals(hv, FH)    # outward (UE coords)
kd = KDTree(NH)
for i, p in enumerate(hv):
    kd.insert(Vector(p), i)
kd.balance()

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
cam_data.clip_start = 1.0


def ue2bl(p):
    return Vector((p[0], -p[1], p[2]))


def aim(loc_ue, look_ue, fov, w, h):
    loc, look = ue2bl(loc_ue), ue2bl(look_ue)
    cam.location = loc
    cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler()
    cam_data.angle = math.radians(fov)
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100


def render_pass(mat, path):
    for ob in (head, body, others):
        ob.data.materials[0] = mat
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return a


def load_png(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return a[..., :3]


def save_png(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = arr
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def ue_dir(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return np.array((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)))


KEY_TRAVEL = ue_dir(-27, -117)          # direction the key light travels (UE coords)
FILL_TRAVEL = ue_dir(-12, -58)
RIM_TRAVEL = ue_dir(-37, 90)
FC = (0.0, 5.959721088409424, 173.6)
a35 = math.radians(35.0)
VIEWS = {"ThreeQuarter": ((FC[0] + 70 * math.sin(a35), FC[1] + 70 * math.cos(a35), FC[2]), (400, 720, 790, 980)),
         "Front": ((FC[0], FC[1] + 70, FC[2]), (380, 880, 620, 990))}
depsgraph = bpy.context.evaluated_depsgraph_get()
report = {"subject": SUBJECT, "views": {}}
vert_sets = {}
for view, (loc, roi) in VIEWS.items():
    aim(loc, FC, 30.0, 1000, 1200)
    pos = render_pass(POS, PDIR / f"pos_{view}.exr")[..., :3]
    fg = pos.max(2) > 1.0
    pos = pos - np.array(POS_OFFSET, np.float32)
    nrm = render_pass(NRM, PDIR / f"nrm_{view}.exr")[..., :3] * 2 - 1
    ue = load_png(CAP / f"{SUBJECT}_Face_{view}.png")
    # silhouette alignment check vs the UE capture (background = uniform grey)
    bgc = np.median(ue[:40, :40].reshape(-1, 3), axis=0)
    ue_fg = np.abs(ue - bgc).max(2) > 0.03
    rows = slice(0, 900)   # head+neck only (UE has the tank top below)
    inter = (fg[rows] & ue_fg[rows]).sum()
    union = (fg[rows] | ue_fg[rows]).sum()
    x0, y0, x1, y1 = roi
    sub = ue[y0:y1, x0:x1]
    dark = (sub.max(2) < 24 / 255.0) & fg[y0:y1, x0:x1]
    ys, xs = np.nonzero(dark)
    ys, xs = ys + y0, xs + x0
    P_bl = pos[ys, xs]
    P = P_bl.copy()
    P[:, 1] *= -1                      # back to UE coords
    N = nrm[ys, xs].copy()
    N[:, 1] *= -1
    camp = np.array(loc)
    Vdir = camp - P
    Vdir /= np.linalg.norm(Vdir, axis=1)[:, None]
    ndv = (N * Vdir).sum(1)
    # shadow tests by ray casting towards each light (Blender coords)
    lit = {}
    for lname, travel in (("key", KEY_TRAVEL), ("fill", FILL_TRAVEL), ("rim", RIM_TRAVEL)):
        to_light = -travel
        tl_bl = Vector((to_light[0], -to_light[1], to_light[2]))
        occl = 0
        facing = 0
        for p, n in zip(P_bl, N):
            if float(np.dot(n, to_light)) > 0:
                facing += 1
            n_bl = Vector((n[0], -n[1], n[2]))
            hit = scene.ray_cast(depsgraph, Vector(p) + n_bl * 0.01 + tl_bl * 0.02, tl_bl)[0]
            occl += int(hit)
        lit[lname] = {"pixels_facing_light": facing, "pixels_ray_occluded": occl}
    vids = [kd.find(Vector(p))[1] for p in P]
    dists = [kd.find(Vector(p))[2] for p in P]
    vset = sorted(set(vids))
    vert_sets[view] = set(vset)
    # which surface: jaw underside (normal points down) vs neck (normal ~horizontal)
    nz = hn[vids][:, 2]
    report["views"][view] = {
        "camera_ue": list(loc), "silhouette_IoU_head_rows": round(float(inter / max(union, 1)), 4),
        "roi_xyxy": roi, "dark_pixels": int(len(ys)),
        "dark_pixel_positions_ue_min": np.round(P.min(0), 2).tolist() if len(P) else None,
        "dark_pixel_positions_ue_max": np.round(P.max(0), 2).tolist() if len(P) else None,
        "N_dot_V_percentiles_5_50_95": np.round(np.percentile(ndv, [5, 50, 95]), 3).tolist() if len(P) else None,
        "fraction_grazing_NdotV_lt_0.25": round(float((ndv < 0.25).mean()), 3) if len(P) else None,
        "vertex_normal_z_percentiles_5_50_95": np.round(np.percentile(nz, [5, 50, 95]), 3).tolist() if len(P) else None,
        "fraction_on_downfacing_jaw_underside_nz_lt_-0.3": round(float((nz < -0.3).mean()), 3) if len(P) else None,
        "lights": lit, "unique_head_vertices": len(vset),
        "nearest_vertex_dist_cm_max": round(float(max(dists)), 3) if dists else None,
    }
    # overlay: UE capture with dark-line pixels in magenta, plus the Blender silhouette edge in green
    ov = ue.copy()
    ov[ys, xs] = (1, 0, 1)
    edge = fg ^ np.roll(fg, 1, 0) | fg ^ np.roll(fg, 1, 1)
    ov[edge] = (0, 1, 0)
    save_png(ov, PDIR / f"overlay_{view}.png")
    np.save(PDIR / f"darkverts_{view}.npy", np.array(vset))
common = vert_sets["ThreeQuarter"] & vert_sets["Front"]
report["vertex_overlap_front_vs_34"] = {"front": len(vert_sets["Front"]), "three_quarter": len(vert_sets["ThreeQuarter"]),
                                        "common": len(common)}
# where do the 3/4-view dark vertices appear in the FRONT view? (visible there? dark there?)
(OUT / "pixmap_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))
