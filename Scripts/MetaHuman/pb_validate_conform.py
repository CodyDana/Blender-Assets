"""PlayerBase conform input - steps 5 + 6: validate the exported conform files in a FRESH
Blender process (factory startup, empty scene) and render previews of the exported mesh.

    blender -b --factory-startup --python Scripts/MetaHuman/pb_validate_conform.py

Opens no JinMuWon .blend (only the exported PB_* files). Writes
conform_input/pb_validation_report.json and conform_input/preview_*.png.
"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import lock
lock.assert_owner("JinMuWon_v2", "claude")

import json
import math
import os

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/conform_input"
report = {"blender": bpy.app.version_string, "files": {}}

# fresh process started with --factory-startup and no .blend: remove the default cube/camera/light
scene = bpy.context.scene
for _o in list(bpy.data.objects):
    bpy.data.objects.remove(_o, do_unlink=True)
assert scene.unit_settings.system == "METRIC" and abs(scene.unit_settings.scale_length - 1) < 1e-9


def fbx_header(path):
    """Read GlobalSettings from the FBX with Blender's own parser."""
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(path)
    out = {"fbx_version": version}
    for el in root.elems:
        if el.id == b"GlobalSettings":
            for sub in el.elems:
                if sub.id == b"Properties70":
                    for p in sub.elems:
                        name = p.props[0].decode()
                        if name in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis",
                                    "CoordAxisSign", "UnitScaleFactor", "OriginalUnitScaleFactor"):
                            out[name] = p.props[4]
    return out


def import_fbx(path):
    before = set(bpy.data.objects)
    r = bpy.ops.import_scene.fbx(filepath=path)
    assert "FINISHED" in r, r
    return [o for o in bpy.data.objects if o not in before]


def components(bm):
    seen, comps, sizes = set(), 0, []
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        if v.index in seen:
            continue
        comps += 1
        n = 0
        stack = [v]
        seen.add(v.index)
        while stack:
            c = stack.pop()
            n += 1
            for e in c.link_edges:
                w = e.other_vert(c)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        sizes.append(n)
    return comps, sorted(sizes, reverse=True)


def boundary_loops(bm):
    edges = {e for e in bm.edges if e.is_boundary}
    loops = []
    while edges:
        e = edges.pop()
        loop = {e}
        stack = [e]
        while stack:
            c = stack.pop()
            for v in c.verts:
                for e2 in v.link_edges:
                    if e2 in edges:
                        edges.discard(e2)
                        loop.add(e2)
                        stack.append(e2)
        loops.append(len(loop))
    return sorted(loops, reverse=True)


def mesh_checks(ob):
    me = ob.data
    mw = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(mw)
    bm.normal_update()
    comps, sizes = components(bm)
    loops = boundary_loops(bm)
    bm.faces.ensure_lookup_table()
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    # signed volume (positive = outward normals on a closed mesh)
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    # self intersections (triangle pairs that intersect and share no vertex)
    bvh = BVHTree.FromBMesh(bm)
    pairs = bvh.overlap(bvh)
    faces = bm.faces
    real = []
    for a, b in pairs:
        if a >= b:
            continue
        va = {v.index for v in faces[a].verts}
        vb = {v.index for v in faces[b].verts}
        if va & vb:
            continue
        real.append((a, b))
    co = [v.co for v in bm.verts]
    uv_ok = bool(me.uv_layers)
    uv_range = None
    if uv_ok:
        us = [d.uv for d in me.uv_layers.active.data]
        uv_range = [[min(u.x for u in us), min(u.y for u in us)], [max(u.x for u in us), max(u.y for u in us)]]
    res = {
        "object": ob.name, "scale": list(ob.scale), "rotation_euler_deg": [math.degrees(a) for a in ob.rotation_euler],
        "verts": len(bm.verts), "faces": len(bm.faces),
        "tris": sum(len(f.verts) - 2 for f in bm.faces),
        "components": comps, "component_vertex_counts": sizes[:10],
        "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
        "boundary_loops_edge_counts": loops,
        "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
        "non_manifold_verts": sum(1 for v in bm.verts if not v.is_manifold),
        "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
        "loose_edges": sum(1 for e in bm.edges if not e.link_faces),
        "degenerate_faces": degenerate,
        "self_intersecting_face_pairs": len(real),
        "signed_volume_m3": vol,
        "normals_outward": vol > 0,
        "uv_layers": [u.name for u in me.uv_layers], "uv_range": uv_range,
        "materials": [m.name if m else None for m in me.materials],
        "bounds_min_m": [min(c[i] for c in co) for i in range(3)],
        "bounds_max_m": [max(c[i] for c in co) for i in range(3)],
    }
    res["bounds_min_cm"] = [round(x * 100, 3) for x in res["bounds_min_m"]]
    res["bounds_max_cm"] = [round(x * 100, 3) for x in res["bounds_max_m"]]
    res["height_cm"] = round(res["bounds_max_cm"][2] - res["bounds_min_cm"][2], 3)
    # UE mapping for FBX -Y fwd/Z up + unit scale: (x, y, z)m -> (x, -y, z)cm
    res["unreal_expected_bounds_cm"] = {"min": [res["bounds_min_cm"][0], -res["bounds_max_cm"][1], res["bounds_min_cm"][2]],
                                        "max": [res["bounds_max_cm"][0], -res["bounds_min_cm"][1], res["bounds_max_cm"][2]]}
    # texture found?
    tex = []
    for m in me.materials:
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    tex.append({"material": m.name, "image": n.image.filepath,
                                "loaded": n.image.has_data or n.image.size[0] > 0, "size": list(n.image.size)})
    res["textures"] = tex
    return res, bm, bvh


def ray_profile(bvh, xs, zs, y0=-1.0):
    """First hit Y for rays shot along +Y from y0 (in front of the face)."""
    out = {}
    for x in xs:
        col = []
        for z in zs:
            hit = bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)), 3.0)
            col.append(None if hit[0] is None else round(hit[0].y, 5))
        out[round(x, 4)] = col
    return out


# ---------------------------------------------------------------- body FBX
body_fbx = OUT + "/PB_Body_ForConform.fbx"
report["files"]["PB_Body_ForConform.fbx"] = {"header": fbx_header(body_fbx)}
objs = import_fbx(body_fbx)
report["files"]["PB_Body_ForConform.fbx"]["imported_objects"] = [(o.name, o.type) for o in objs]
body = next(o for o in objs if o.type == "MESH")
chk, bm, bvh = mesh_checks(body)
report["files"]["PB_Body_ForConform.fbx"]["checks"] = chk

# ---- openings analysis (pockets behind eyelids / lips; the mesh has no boundary holes)
co = [v.co for v in bm.verts]
nose = min((c for c in co if 1.68 < c.z < 1.74 and abs(c.x) < 0.01), key=lambda c: c.y)
report["nose_tip_m"] = list(nose)
report["facing_axis_blender"] = "-Y" if nose.y < 0 else "+Y"
# mouth: dense vertical scans on the midline and +-1 cm / +-2 cm, band set from the nose tip
nz = nose.z
zs = [nz - 0.080 + i * 0.00025 for i in range(260)]
mouth = ray_profile(bvh, [0.0, 0.01, -0.01, 0.02, -0.02], zs)
lip_summary = {}
for x, col in mouth.items():
    band = [(z, y) for z, y in zip(zs, col) if y is not None and nz - 0.075 < z < nz - 0.020]
    front = min(y for _, y in band)
    deep = max(band, key=lambda t: t[1])
    lip_summary[x] = {"lip_band_front_y_m": front, "deepest_first_hit_y_m": deep[1],
                      "deepest_hit_z_m": round(deep[0], 5),
                      "deepest_minus_front_mm": round((deep[1] - front) * 1000, 2)}
report["mouth_ray_scan"] = lip_summary
report["mouth_midline_profile_z_y"] = [[round(z, 5), y] for z, y in zip(zs, mouth[0.0])]
exp_rep = json.load(open(OUT + "/pb_export_report.json"))
gz = exp_rep["ground_offset_applied_m"][2]
body_bm, body_bvh = bm, bvh

# ---------------------------------------------------------------- previews (body-only, exported mesh + albedo)
scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception:  # noqa: BLE001
    scene.cycles.device = "CPU"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
try:
    scene.view_settings.view_transform = "Khronos PBR Neutral"
except TypeError:
    scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("pbexp_world")
scene.world = world
world.color = (0.18, 0.18, 0.19)
try:
    wn = world.node_tree
    bg = next(n for n in wn.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.22, 0.22, 0.23, 1)
    bg.inputs["Strength"].default_value = 0.35
except Exception:  # noqa: BLE001
    pass


def area(name, loc, rot, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(lo)
    return lo


area("key", (-1.6, -2.6, 2.4), (58, 0, -32), 260, 1.5)
area("fill", (2.2, -2.2, 1.4), (70, 0, 45), 90, 2.0)
area("rim", (0.5, 2.6, 2.3), (-55, 0, 170), 160, 1.2)
floor_me = bpy.data.meshes.new("pbexp_floor")
bmf = bmesh.new()
bmesh.ops.create_grid(bmf, x_segments=1, y_segments=1, size=4)
bmf.to_mesh(floor_me)
floor = bpy.data.objects.new("pbexp_floor", floor_me)
fm = bpy.data.materials.new("pbexp_floor_mat")
fp = next(n for n in fm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
fp.inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1)
fp.inputs["Roughness"].default_value = 0.8
floor_me.materials.append(fm)
scene.collection.objects.link(floor)

cam_d = bpy.data.cameras.new("pbexp_cam")
cam = bpy.data.objects.new("pbexp_cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def shoot(path, cam_loc, target, lens, rx, ry):
    cam.location = cam_loc
    look_at(cam, target)
    cam_d.lens = lens
    scene.render.resolution_x = rx
    scene.render.resolution_y = ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


previews = []
D = 4.6
tgt = (0, -0.03, 0.93)
previews.append(shoot(OUT + "/preview_front.png", (0, -D, 0.95), tgt, 70, 1000, 1400))
previews.append(shoot(OUT + "/preview_side.png", (D, -0.03, 0.95), tgt, 70, 1000, 1400))
a = math.radians(40)
previews.append(shoot(OUT + "/preview_three_quarter.png", (D * math.sin(a), -D * math.cos(a), 1.05), tgt, 70, 1000, 1400))
ft = (0, -0.09, 1.73 + gz)
previews.append(shoot(OUT + "/preview_face_front.png", (0, -1.15, 1.74 + gz), ft, 100, 900, 900))
previews.append(shoot(OUT + "/preview_face_three_quarter.png", (1.06 * math.sin(a), -0.09 - 1.06 * math.cos(a), 1.76 + gz), ft, 100, 900, 900))

# ---------------------------------------------------------------- body+eyes FBX and eyes FBX
bpy.data.objects.remove(body, do_unlink=True)
for name in ("PB_BodyEyes_ForConform.fbx", "PB_Eyes.fbx"):
    p = OUT + "/" + name
    report["files"][name] = {"header": fbx_header(p)}
    objs = import_fbx(p)
    report["files"][name]["imported_objects"] = [(o.name, o.type) for o in objs]
    ob = next(o for o in objs if o.type == "MESH")
    c, cbm, cbvh = mesh_checks(ob)
    report["files"][name]["checks"] = c
    if name == "PB_BodyEyes_ForConform.fbx":
        # eye openings: rays along +Y around each eye; a ray whose first hit is an eyeball face is
        # inside the lid opening. Compare with where the same ray hits the body-only mesh.
        eye_slot = [i for i, m in enumerate(ob.data.materials) if m and "Eyes" in m.name]
        cbm.faces.ensure_lookup_table()
        eye_info = {}
        for side, ex in (("L", 0.0327), ("R", -0.0327)):
            ez = 1.7613 + gz
            cells = []
            for ix in range(-25, 26):
                for iz in range(-12, 13):
                    x = ex + ix * 0.001
                    z = ez + iz * 0.001
                    h = cbvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
                    if h[0] is None or cbm.faces[h[2]].material_index not in eye_slot:
                        continue
                    hb = body_bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
                    cells.append((x, z, h[0].y, hb[0].y if hb[0] is not None else None))
            if cells:
                gaps = [cb - ce for _, _, ce, cb in cells if cb is not None]
                eye_info[side] = {
                    "visible_eyeball_cells_1mm": len(cells),
                    "opening_width_mm": round((max(c[0] for c in cells) - min(c[0] for c in cells)) * 1000, 1),
                    "opening_height_mm": round((max(c[1] for c in cells) - min(c[1] for c in cells)) * 1000, 1),
                    "body_only_pocket_wall_behind_eyeball_surface_mm": {
                        "min": round(min(gaps) * 1000, 2), "max": round(max(gaps) * 1000, 2),
                        "mean": round(sum(gaps) / len(gaps) * 1000, 2)},
                }
            else:
                eye_info[side] = {"visible_eyeball_cells_1mm": 0}
        report["eye_openings"] = eye_info
        previews.append(shoot(OUT + "/preview_face_front_with_eyes.png", (0, -1.15, 1.74 + gz), ft, 100, 900, 900))
    bpy.data.objects.remove(ob, do_unlink=True)

# ---------------------------------------------------------------- OBJ fallback
obj_path = OUT + "/PB_Body_ForConform.obj"
before = set(bpy.data.objects)
r = bpy.ops.wm.obj_import(filepath=obj_path, forward_axis="Y", up_axis="Z", global_scale=0.01)
assert "FINISHED" in r, r
ob = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
c, _bm, _bvh = mesh_checks(ob)
report["files"]["PB_Body_ForConform.obj"] = {"checks": c,
                                             "import_settings": "forward Y, up Z, scale 0.01 (file is cm)"}
report["previews"] = previews
with open(OUT + "/pb_validation_report.json", "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1, default=str)
print(json.dumps(report, indent=1, default=str)[:12000])
print("VALIDATE DONE")
