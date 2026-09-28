#!/usr/bin/env python
"""props_lib.smokebomb_look - SM_SmokeBomb's Blender side: material, collision, renders.

bpy.  Everything rendered here is rendered from the BAKED maps through M_SmokeBomb, the
graph an Unreal material reproduces node for node (smokebomb_tape.preview_material with
base_from_detail=True; unreal_material_spec gives the Unreal side):

    BaseColor  = T_SmokeBomb_Detail.R x Tint            (Tint default in the sidecar; the Detail is
                                                          sRGB-encoded, sampled sRGB ON)
    Specular   = 0.5 x T_SmokeBomb_ORM.A                (the baked specular mask; final pass)
    Roughness  = T_SmokeBomb_ORM.G      Metallic = ORM.B (0)
    Normal     = T_SmokeBomb_N (DirectX on disk; green flipped for Blender here)
    sheen 0, no coat, no subsurface, Lambert diffuse.  ORM.R (AO) is Unreal's indirect
    occlusion; Cycles traces its own, so it is not wired here.

    reference view   REFERENCE_SPEC 2 / 3: orthographic on -Y, frame 1.351 D, 1254 px, the ball
                     centre at (627.4, 628.9), key az 60 / el 64, fill az -116 / el 4 at 0.67,
                     ambient 0.42, 40 deg suns, composited onto a 0.996 backdrop
    side by side     [reference | reference view] - the only file holding reference pixels
    gallery          the pack rig (props_lib.render): hero, top, back, raking, wire, LOD strip,
                     and a SHADED LOD-switch frame (each LOD at the size it is on screen when it
                     switches, 1080p, 90 deg hFOV)
"""
from __future__ import annotations

import itertools
import math
import struct
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import render as R
from . import smokebomb_tape as T
from .gallery import _drop_to_ground, _label

REF_PX = 1254
REF_CENTRE_PX = (627.38, 628.92)
ORTHO_D_PER_FRAME = 1254.0 / 928.2
KEY_DIR_CAM = (0.3796, 0.8988, 0.2192)
FILL_DIR_CAM = (-0.8966, 0.0698, -0.4373)
FILL_OVER_KEY = 0.67
AMBIENT_OVER_KEY = 0.42
BACKDROP_STORED = 0.996
SUN_ANGLE_DEG = 40.0
#: the reference-view pixel filter (Cycles Blackman-Harris width, px).  Round 2: 1.0 (was the
#: default 1.5): the reference photo keeps 1-px fibre detail (it is a sharpened product
#: still) and the blind judge read our 1.5-px-filtered render as "blurrier, softer"; 1.0 px
#: is still a full anti-aliasing filter (no aliasing at 512 spp), a sharper lens, nothing more
REF_FILTER_PX = 1.0


def cam_to_build(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], -v[..., 2], v[..., 1]], -1)


def light_levels(key_scale: float = 1.0) -> Dict[str, float]:
    k = 1.0 / (1.0 + AMBIENT_OVER_KEY)
    return {"sun_key": math.pi * k * key_scale, "sun_fill": math.pi * FILL_OVER_KEY * k * key_scale,
            "world": AMBIENT_OVER_KEY * k * key_scale, "k": k}


def write_png(path, arr) -> str:
    return T.write_png(path, np.clip(np.asarray(arr, np.float64), 0, 1))


def load_png(path) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1])
    finally:
        bpy.data.images.remove(img)


def _cycles(scene, samples: int, denoise: bool = False):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    except Exception:                                          # pragma: no cover
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.cycles.use_adaptive_sampling = False


# =========================================================================== material
def make_material(name: str, paths: Dict[str, str], tint_linear, shading: T.Shading = T.SHADING, pack: bool = True):
    mat = T.preview_material(name, paths["BC"], paths["ORM"], paths["N"], shading, detail_path=paths["DETAIL"],
                             tint_linear=tint_linear, base_from_detail=True)
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image is not None:
            n.image.name = Path(n.image.filepath).stem
            if pack:
                n.image.pack()
    mat["ue_master"] = str(T.unreal_material_spec({"tint_linear": tint_linear, "tint_srgb": list(T.srgb_encode(np.asarray(tint_linear)))}, shading))
    return mat


# =========================================================================== collision
def pentakis_hull(r_max_m: float):
    """A pentakis dodecahedron whose 60 faces are all TANGENT to the sphere r_max: 32
    vertices, circumscribed, 1.064 x the sphere's volume (copied from the retired
    smokebomb_geometry, unchanged)."""
    t = (1.0 + 5 ** 0.5) / 2.0
    base = [(0.0, 1.0, 3 * t), (1.0, 2 + t, 2 * t), (t, 2.0, 2 * t + 1)]
    normals = set()
    for a, b, c in base:
        for sa in (1, -1):
            for sb in (1, -1):
                for sc in (1, -1):
                    v = (a * sa, b * sb, c * sc)
                    for perm in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
                        normals.add(tuple(round(v[i], 9) for i in perm))
    N = np.array(sorted(normals))
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    assert len(N) == 60, len(N)
    pts = []
    for i, j, k in itertools.combinations(range(60), 3):
        A = N[[i, j, k]]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        x = np.linalg.solve(A, np.full(3, r_max_m))
        if (N @ x <= r_max_m * (1 + 1e-9)).all():
            pts.append(x)
    V = []
    for x in pts:
        if not any(np.linalg.norm(x - y) < 1e-9 * r_max_m + 1e-12 for y in V):
            V.append(x)
    V = np.array(V)
    if len(V) != 32:
        raise RuntimeError(f"pentakis hull has {len(V)} vertices, not 32")
    faces = []
    for n in N:
        on = np.nonzero(np.abs(V @ n - r_max_m) < 1e-6 * r_max_m)[0]
        if len(on) != 3:
            raise RuntimeError(f"pentakis face has {len(on)} vertices")
        a, b, c = on
        if np.dot(np.cross(V[b] - V[a], V[c] - V[a]), n) < 0:
            b, c = c, b
        faces.append((int(a), int(b), int(c)))
    return V, faces


def make_hull(obj, r_max_m: float, index: int = 0):
    name = f"UCX_{obj.name}_{index:02d}"
    V, F = pentakis_hull(r_max_m)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in V], [], F)
    mesh.update()
    if mesh.validate(verbose=False):
        raise RuntimeError(f"{name}: invalid hull")
    hull = bpy.data.objects.new(name, mesh)
    for parent in obj.users_collection:
        parent.objects.link(hull)
    hull.parent = obj
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    hull.hide_render = True
    hull.display_type = "WIRE"
    hull["ue_collision"] = "UCX"
    return hull


def hull_worst_outside_m(hull, obj) -> float:
    hc = np.array([v.co[:] for v in hull.data.vertices])
    co = np.array([v.co[:] for v in obj.data.vertices])
    worst = -1e9
    for poly in hull.data.polygons:
        n = np.array(poly.normal[:])
        n /= np.linalg.norm(n)
        d = float(n @ hc[poly.vertices[0]])
        worst = max(worst, float((co @ n - d).max()))
    return worst


def hull_volume_m3(hull) -> float:
    co = np.array([v.co[:] for v in hull.data.vertices])
    vol = 0.0
    for poly in hull.data.polygons:
        a, b, c = (co[i] for i in poly.vertices)
        vol += float(np.dot(a, np.cross(b, c))) / 6.0
    return abs(vol)


# =========================================================================== reference view
def setup_reference(diameter_mm: float, res: int = REF_PX, samples: int = 512, key_scale: float = 1.0):
    scene = bpy.context.scene
    _cycles(scene, samples)
    scene.cycles.filter_width = REF_FILTER_PX
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_border = False
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    coll = bpy.data.collections.new("SB_REFERENCE_RIG")
    scene.collection.children.link(coll)
    cam_d = bpy.data.cameras.new("SB_RefCam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = diameter_mm * 0.001 * ORTHO_D_PER_FRAME
    cam_d.shift_x = -(REF_CENTRE_PX[0] - REF_PX / 2) / REF_PX
    cam_d.shift_y = (REF_CENTRE_PX[1] - REF_PX / 2) / REF_PX
    cam_d.clip_start = 0.01
    cam_d.clip_end = 2.0
    cam = bpy.data.objects.new("SB_RefCam", cam_d)
    coll.objects.link(cam)
    cam.location = (0.0, -0.6, 0.0)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    scene.camera = cam
    lv = light_levels(key_scale)
    lamps = []
    for name, v, e in (("SB_Key", KEY_DIR_CAM, lv["sun_key"]), ("SB_Fill", FILL_DIR_CAM, lv["sun_fill"])):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = e
        ld.angle = math.radians(SUN_ANGLE_DEG)
        lo = bpy.data.objects.new(name, ld)
        coll.objects.link(lo)
        vb = Vector(cam_to_build(np.array(v)))
        lo.rotation_euler = vb.to_track_quat("Z", "Y").to_euler()
        lamps.append(lo)
    world = bpy.data.worlds.new("SB_RefWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = lv["world"]
    scene.world = world
    return {"collection": coll, "camera": cam, "lamps": lamps, "world": world, "levels": lv}


def teardown(rig) -> None:
    for o in list(rig["collection"].objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        for lib in (bpy.data.cameras, bpy.data.lights):
            try:
                lib.remove(data)
                break
            except Exception:
                pass
    bpy.data.collections.remove(rig["collection"])
    if rig.get("world") is not None:
        bpy.data.worlds.remove(rig["world"])


def render_exr(exr_path) -> np.ndarray:
    scene = bpy.context.scene
    scene.render.filepath = str(exr_path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(exr_path), check_existing=False)
    try:
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1]).astype(np.float64)
    finally:
        bpy.data.images.remove(img)


def render_reference(path_png, exr_path, rig) -> np.ndarray:
    bpy.context.scene.camera = rig["camera"]
    a = render_exr(exr_path)
    bg = T.srgb_decode(np.array(BACKDROP_STORED))
    lin = a[..., :3] + (1.0 - a[..., 3:4]) * bg
    stored = T.srgb_encode(lin)
    write_png(path_png, stored)
    return stored


def side_by_side(ref_png, render_png, out_png, gap: int = 12, crop=None):
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    if crop is not None:
        x0, y0, x1, y1 = crop
        ref, ren = ref[y0:y1, x0:x1], ren[y0:y1, x0:x1]
    h = max(ref.shape[0], ren.shape[0])
    sheet = np.ones((h, ref.shape[1] + gap + ren.shape[1], 3))
    sheet[:ref.shape[0], :ref.shape[1]] = ref
    sheet[:ren.shape[0], ref.shape[1] + gap:] = ren
    write_png(out_png, sheet)
    return str(out_png)


def crops_sheet(ref_png, render_png, out_png, boxes: Sequence[Tuple[int, int, int, int]], scale: int = 3,
                bright: float = 1.0, gap: int = 8):
    """[reference | render] pairs of crops, each magnified ``scale`` x (nearest), stacked."""
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    rows = []
    for (x0, y0, x1, y1) in boxes:
        a = np.repeat(np.repeat(ref[y0:y1, x0:x1], scale, 0), scale, 1)
        b = np.repeat(np.repeat(ren[y0:y1, x0:x1], scale, 0), scale, 1)
        row = np.ones((a.shape[0], a.shape[1] * 2 + gap, 3))
        row[:, :a.shape[1]] = a
        row[:, a.shape[1] + gap:] = b
        rows.append(row)
    w = max(r.shape[1] for r in rows)
    out = []
    for r in rows:
        pad = np.ones((r.shape[0], w, 3))
        pad[:, :r.shape[1]] = r
        out.append(pad)
        out.append(np.ones((gap, w, 3)))
    sheet = np.concatenate(out[:-1], 0)
    if bright != 1.0:
        sheet = np.clip(sheet * bright, 0, 1)
    write_png(out_png, sheet)
    return str(out_png)


# =========================================================================== gallery helpers
def _clone(obj, name, matrix=None):
    c = obj.copy()
    c.data = obj.data.copy()
    c.name = name
    c.parent = None
    c.matrix_world = matrix if matrix is not None else obj.matrix_world.copy()
    c.hide_render = False
    bpy.context.scene.collection.objects.link(c)
    return c


def _join_clone(objs, name, matrix=None):
    """One temporary object holding copies of ``objs`` (LOD0 + its threads)."""
    import bmesh
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    # custom normals are lost by bmesh; copy the first object's material only
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in objs[0].data.materials:
        me.materials.append(m)
    ob.matrix_world = matrix if matrix is not None else Matrix.Identity(4)
    return ob


def _frame(camera, obj, fill_h: float, centre):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    co = [obj.matrix_world @ v.co for v in obj.data.vertices][::7]
    camera.data.shift_x = camera.data.shift_y = 0.0
    d = (Vector(camera.location) - centre).normalized()
    lo, hi = 0.05, 3.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        camera.location = centre + d * mid
        R._aim(camera, centre)
        bpy.context.view_layer.update()
        ys = [world_to_camera_view(scene, camera, p).y for p in co]
        if max(ys) - min(ys) > fill_h:
            lo = mid
        else:
            hi = mid
    camera.location = centre + d * hi
    R._aim(camera, centre)
    bpy.context.view_layer.update()
    return hi


def _product_lamps(camera, target, distance, scale, key=(60.0, 64.0), fill=(-116.0, 4.0), fill_ratio=0.67,
                   size_scale=1.6, prefix="SB_Gal"):
    cam_dir = (Vector(camera.location) - Vector(target)).normalized()
    world_up = Vector((0.0, 0.0, 1.0))
    if abs(cam_dir.dot(world_up)) > 0.98:
        world_up = Vector((0.0, 1.0, 0.0))
    right = world_up.cross(cam_dir).normalized()
    up = cam_dir.cross(right).normalized()
    right = -right if right.dot(camera.matrix_world.to_3x3() @ Vector((1, 0, 0))) < 0 else right
    lamps = []
    for name, (az, el), power in ((prefix + "Key", key, 1.0), (prefix + "Fill", fill, fill_ratio)):
        if power <= 0:
            continue
        a, e = math.radians(az), math.radians(el)
        v = (cam_dir * (math.cos(e) * math.cos(a)) + right * (math.cos(e) * math.sin(a)) + up * math.sin(e)).normalized()
        data = bpy.data.lights.new(name, "AREA")
        data.shape = "DISK"
        data.size = distance * size_scale
        data.energy = power * scale * (distance / 0.3) ** 2
        lo = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = Vector(target) + v * distance * 1.4
        R._aim(lo, Vector(target))
        lamps.append(lo)
    return lamps


def _remove(objs):
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            try:
                bpy.data.lights.remove(data)
            except Exception:
                try:
                    bpy.data.meshes.remove(data)
                except Exception:
                    pass


def _wire_pair(source, coll, name: str, matrix, thickness: float = 0.00008):
    from .paper_material import flat_emission
    centre = matrix.to_translation()
    solid = _clone(source, f"PREVIEW_{name}Solid", matrix)
    for parent in list(solid.users_collection):
        parent.objects.unlink(solid)
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(flat_emission(f"M_Wire_{name}_Solid", (0.150, 0.162, 0.185), 1.0))
    lift = Matrix.Translation(centre) @ Matrix.Scale(1.002, 4) @ Matrix.Translation(-centre) @ matrix
    wires = _clone(source, f"PREVIEW_{name}Lines", lift)
    for parent in list(wires.users_collection):
        parent.objects.unlink(wires)
    coll.objects.link(wires)
    wires.data.materials.clear()
    wires.data.materials.append(flat_emission(f"M_Wire_{name}_Lines", (1.0, 0.48, 0.14), 2.0))
    mod = wires.modifiers.new("Wireframe", "WIREFRAME")
    mod.thickness = thickness
    mod.use_boundary = True
    mod.use_even_offset = False
    mod.use_replace = True
    return solid, wires


def _hide_all_but(keep):
    keep = set(keep)
    saved = [(o, o.hide_render) for o in bpy.data.objects]
    for o in bpy.data.objects:
        if o.type in {"MESH", "CURVE", "FONT"} and o not in keep:
            o.hide_render = True
    return saved


def _restore(saved):
    for o, was in saved:
        try:
            o.hide_render = was
        except ReferenceError:
            pass


# =========================================================================== reference views
def reference_views(lod0_objs, diameter_mm: float, ref_png: str, render_dir: Path, work: Path,
                    samples: int = 512, res: int = REF_PX) -> Dict[str, object]:
    saved = _hide_all_but(lod0_objs)
    for o in lod0_objs:
        o.hide_render = False
    out = {}
    try:
        rig = setup_reference(diameter_mm, res=res, samples=samples)
        front = Path(render_dir) / "smokebomb_reference_view.png"
        render_reference(front, Path(work) / "reference_view.exr", rig)
        side_by_side(ref_png, front, Path(render_dir) / "smokebomb_side_by_side.png")
        out["reference_view"] = str(front)
        out["side_by_side"] = str(Path(render_dir) / "smokebomb_side_by_side.png")
        mats = [o.matrix_world.copy() for o in lod0_objs]
        for o in lod0_objs:
            o.matrix_world = Matrix.Rotation(math.pi, 4, "Z") @ o.matrix_world
        back = Path(render_dir) / "smokebomb_back.png"
        render_reference(back, Path(work) / "back_view.exr", rig)
        for o, m in zip(lod0_objs, mats):
            o.matrix_world = m
        out["back"] = str(back)
        out["camera"] = {"type": "ORTHO", "ortho_scale_mm": round(rig["camera"].data.ortho_scale * 1000.0, 4),
                         "shift": [round(rig["camera"].data.shift_x, 6), round(rig["camera"].data.shift_y, 6)],
                         "resolution": [res, res], "samples": samples, "denoise": False, "filter_width": REF_FILTER_PX,
                         "levels": rig["levels"], "key_dir_cam": KEY_DIR_CAM, "fill_dir_cam": FILL_DIR_CAM,
                         "sun_angle_deg": SUN_ANGLE_DEG, "backdrop_stored": BACKDROP_STORED}
        teardown(rig)
    finally:
        _restore(saved)
    return out


def clay_reference(lod0_objs, diameter_mm: float, out_png: Path, work: Path, samples: int = 128,
                   res: int = REF_PX, albedo: float = 0.25):
    """The reference view with a uniform grey clay material: the SHAPE alone."""
    saved = _hide_all_but(lod0_objs)
    mats = [(o, list(o.data.materials)) for o in lod0_objs]
    clay = bpy.data.materials.new("SB_Clay")
    clay.use_nodes = True
    b = next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (albedo, albedo, albedo, 1.0)
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.2
    try:
        for o in lod0_objs:
            o.hide_render = False
            o.data.materials.clear()
            o.data.materials.append(clay)
        rig = setup_reference(diameter_mm, res=res, samples=samples)
        render_reference(out_png, Path(work) / "clay.exr", rig)
        teardown(rig)
    finally:
        for o, ms in mats:
            o.data.materials.clear()
            for m in ms:
                o.data.materials.append(m)
        bpy.data.materials.remove(clay)
        _restore(saved)
    return str(out_png)


# =========================================================================== gallery
HERO_FILL_H = 0.72
LIGHT_SCALE = 10.0
LOD_GAP_MM = 18.0


def gallery(spec, lods: List[list], render_dir: Path, work: Path, samples: int = 256,
            light_scale: float = LIGHT_SCALE, lod_screen_sizes=(1.0, 0.0746, 0.0261),
            bounds_radius_mm: float = 37.3) -> Dict[str, object]:
    """``lods``: per LOD the list of objects (LOD0: the mesh; threads live in the LOD0 mesh)."""
    render_dir, work = Path(render_dir), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    device = R.setup_render(samples=samples)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_border = False
    rig = R.build_rig(spec, light_scale=1.0)
    out: Dict[str, object] = {"device": device, "samples": samples, "light_scale": light_scale, "shots": {}}
    lod0 = lods[0][0]
    all_objs = [o for L in lods for o in L]
    stash = [(o, o.hide_render) for o in all_objs]
    for o in all_objs:
        o.hide_render = True
    try:
        # ---------------------------------------------------------------- hero (3/4, the pack's camera)
        cam = rig["cam_hero"]
        cam.data.dof.use_dof = False
        az = math.radians(R.HERO_AZIMUTH_DEG)
        yaw = Matrix.Rotation(az + math.pi / 2, 4, "Z")
        hero = _clone(lod0, "PREVIEW_Hero", yaw @ lod0.matrix_world)
        _drop_to_ground(hero, rig["ground"])
        hero_matrix = hero.matrix_world.copy()
        centre = hero_matrix.to_translation()
        cam.location = centre + Vector(R._polar(0.4, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG))
        dist = _frame(cam, hero, HERO_FILL_H, centre)
        lamps = _product_lamps(cam, centre, dist, light_scale)
        R.render_to(render_dir / "smokebomb_hero.png", cam, lamps)
        R.render_mask(work / "hero_mask.png", cam, [hero])
        out["shots"]["hero"] = {"path": "Renders/SmokeBomb/smokebomb_hero.png", "camera_distance_m": round(dist, 5),
                                "lens_mm": cam.data.lens, "elevation_deg": R.HERO_ELEVATION_DEG,
                                "azimuth_deg": R.HERO_AZIMUTH_DEG,
                                "lighting": "REFERENCE_SPEC 3 product key / fill, relative to the camera",
                                **R.image_stats(render_dir / "smokebomb_hero.png", work / "hero_mask.png")}
        _remove(lamps)

        # ---------------------------------------------------------------- raking (grazing light, the relief)
        lamps = _product_lamps(cam, centre, dist, light_scale * 1.25, key=(-78.0, 8.0), fill=(60.0, 30.0),
                               fill_ratio=0.12, size_scale=0.35, prefix="SB_Rake")
        R.render_to(render_dir / "smokebomb_raking.png", cam, lamps)
        out["shots"]["raking"] = {"path": "Renders/SmokeBomb/smokebomb_raking.png",
                                  "camera": "the hero camera", "key": "small disc at az -78 / el 8 relative to the "
                                  "camera (grazing from the left), fill 0.12 at az 60 / el 30",
                                  **R.image_stats(render_dir / "smokebomb_raking.png", work / "hero_mask.png")}
        _remove(lamps)
        bpy.data.objects.remove(hero, do_unlink=True)

        # ---------------------------------------------------------------- top
        top = _clone(lod0, "PREVIEW_Top")
        _drop_to_ground(top, rig["ground"])
        tc = top.matrix_world.to_translation()
        cam = rig["cam_flat"]
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (tc.x, tc.y, 0.40)
        cam.data.ortho_scale = (spec.diameter_mm / 0.62) * 0.001 * R.RES_X / R.RES_Y
        cam.data.shift_x = cam.data.shift_y = 0.0
        bpy.context.view_layer.update()
        lamps = _product_lamps(cam, tc, 0.25, light_scale * 1.7)
        R.render_to(render_dir / "smokebomb_top.png", cam, lamps)
        R.render_mask(work / "top_mask.png", cam, [top])
        out["shots"]["top"] = {"path": "Renders/SmokeBomb/smokebomb_top.png",
                               "ortho_scale_mm": round(cam.data.ortho_scale * 1000, 2),
                               **R.image_stats(render_dir / "smokebomb_top.png", work / "top_mask.png")}
        _remove(lamps)
        bpy.data.objects.remove(top, do_unlink=True)

        # ---------------------------------------------------------------- line sheet (final pass)
        # the pack's line-sheet entry (Renders/Shuriken/modern_line_sheet.png, Renders/PaperBomb/
        # paperbomb_linesheet.png): the ball from above on the sweep, and its tag - name, size, mass,
        # LODs, maps - at the same 1600 x 900, so it can be set beside the paper and the steel
        lcoll = bpy.data.collections.new("PREVIEW_SHEET")
        scene.collection.children.link(lcoll)
        card = _clone(lod0, "PREVIEW_SheetCard", Matrix.Translation((-0.045, 0.0, 0.0)) @ lod0.matrix_world)
        _drop_to_ground(card, rig["ground"])
        ltris = []
        for L in lods:
            L[0].data.calc_loop_triangles()
            ltris.append(len(L[0].data.loop_triangles))
        tsz = dict(spec.texture_sizes)
        lines = [f"{spec.mesh_name}",
                 f"{spec.diameter_mm:.0f} mm diameter     {spec.mass_g:.0f} g",
                 f"LOD {ltris[0]:,} / {ltris[1]:,} / {ltris[2]:,} tris     1 convex hull     {len(spec.sockets)} sockets",
                 f"{spec.texture_stem}_BC / _Detail {tsz['BC']} px     _ORM / _N {tsz['ORM']} px",
                 "recolourable: BaseColor = Detail x Tint"]
        cz = card.matrix_world.to_translation()
        # the same share of the frame height as the paper bomb's tag (its frame is 196 mm tall, this one 104 mm)
        lab = _label(lcoll, "PREVIEW_SheetText", chr(10).join(lines), (0.0, 0.0, cz.z + 0.036), 0.0019,
                     align_x="LEFT", align_y="CENTER")
        lab.rotation_euler = (0.0, 0.0, 0.0)          # this camera is not rolled
        cam = rig["cam_flat"]
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (0.0, 0.0, 0.40)
        cam.data.shift_x = cam.data.shift_y = 0.0
        cam.data.ortho_scale = (spec.diameter_mm + 34.0) * 0.001 * R.RES_X / R.RES_Y
        bpy.context.view_layer.update()
        lamps = _product_lamps(cam, cz, 0.25, light_scale * 1.7)
        R.render_to(render_dir / "smokebomb_linesheet.png", cam, lamps)
        out["shots"]["linesheet"] = {"path": "Renders/SmokeBomb/smokebomb_linesheet.png", "lines": lines}
        _remove(lamps)
        for o in list(lcoll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(lcoll)

        # ---------------------------------------------------------------- wire
        coll = bpy.data.collections.new("PREVIEW_WIRE")
        scene.collection.children.link(coll)
        _wire_pair(lod0, coll, "Lod0", hero_matrix)
        saved_world = scene.world
        scene.world = None
        g_hidden = rig["ground"].hide_render
        rig["ground"].hide_render = True
        R.render_to(render_dir / "smokebomb_wire.png", rig["cam_hero"], ())
        lod0.data.calc_loop_triangles()
        out["shots"]["wire"] = {"path": "Renders/SmokeBomb/smokebomb_wire.png",
                                "triangles": len(lod0.data.loop_triangles), "camera": "the hero camera, flat-lit"}
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)

        # ---------------------------------------------------------------- LOD strip (wire)
        pitch = (spec.diameter_mm + LOD_GAP_MM) * 0.001
        tris = []
        for i, L in enumerate(lods):
            obj = L[0]
            obj.data.calc_loop_triangles()
            tris.append(len(obj.data.loop_triangles))
            m = Matrix.Translation(((i - 1) * pitch, 0.0, 0.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X") @ obj.matrix_world
            _wire_pair(obj, coll, f"Lod{i}", m)
        for i in range(len(lods)):
            lab = _label(coll, f"PREVIEW_LodLabel{i}", f"LOD{i}   {tris[i]:,} tris   screen size {lod_screen_sizes[i]}",
                         ((i - 1) * pitch, -(spec.diameter_mm * 0.5 + 9.0) * 0.001, 0.05), 3.6 * 0.001)
            lab.rotation_euler = (0.0, 0.0, 0.0)
        cam = rig["cam_flat"]
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (0.0, -0.004, 0.40)
        cam.data.shift_x = cam.data.shift_y = 0.0
        cam.data.ortho_scale = (3 * spec.diameter_mm + 2 * LOD_GAP_MM) * 1.12 * 0.001
        R.render_to(render_dir / "smokebomb_lods.png", cam, ())
        out["shots"]["lods"] = {"path": "Renders/SmokeBomb/smokebomb_lods.png", "triangles": tris,
                                "screen_sizes": list(lod_screen_sizes)}
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(coll)
        scene.world = saved_world
        rig["ground"].hide_render = g_hidden
    finally:
        R.teardown(rig)
        for o, was in stash:
            o.hide_render = was
    return out


def lod_switch_frame(lods: List[list], diameter_mm: float, bounds_radius_mm: float, screen_sizes: Sequence[float],
                     out_png: Path, work: Path, samples: int = 256, screen_h: int = 1080, mag: int = 6) -> Dict:
    """Each LOD SHADED, from the baked maps, under the reference view's lights, at the
    size it has on a 1080p screen when it switches (the bounds sphere's projected diameter
    is screen_size x the screen height): [LOD0 | LOD1] at LOD1's switch and [LOD1 | LOD2]
    at LOD2's, each magnified ``mag`` x (nearest) so the pixels can be seen, plus the
    two pairs' absolute difference."""
    work = Path(work)
    tiles = {}
    info = {"screen_height_px": screen_h, "magnification": mag, "pairs": []}
    for sw_i in (1, 2):
        ball_px = screen_sizes[sw_i] * screen_h * (0.5 * diameter_mm) / bounds_radius_mm
        res = int(math.ceil(ball_px * ORTHO_D_PER_FRAME / 2.0)) * 2 + 2
        frame_mm = res / ball_px * diameter_mm
        pair = []
        for lod in (sw_i - 1, sw_i):
            saved = _hide_all_but(lods[lod])
            for o in lods[lod]:
                o.hide_render = False
            try:
                rig = setup_reference(diameter_mm, res=res, samples=samples)
                rig["camera"].data.ortho_scale = frame_mm * 0.001
                rig["camera"].data.shift_x = rig["camera"].data.shift_y = 0.0
                png = work / f"lodswitch_{sw_i}_lod{lod}.png"
                st = render_reference(png, work / f"lodswitch_{sw_i}_lod{lod}.exr", rig)
                teardown(rig)
            finally:
                _restore(saved)
            pair.append(st)
        diff = np.abs(pair[0] - pair[1])
        info["pairs"].append({"switch": f"LOD{sw_i - 1}->LOD{sw_i}", "screen_size": screen_sizes[sw_i],
                              "ball_px": round(ball_px, 2), "frame_px": res,
                              "mean_abs_diff_stored": round(float(diff.mean()), 5),
                              "p99_abs_diff_stored": round(float(np.percentile(diff, 99)), 5)})
        tiles[sw_i] = (pair, diff)
    # sheet: two rows, [a | b | 3x diff] magnified
    rows = []
    for sw_i in (1, 2):
        (a, b), diff = tiles[sw_i]
        m = lambda x: np.repeat(np.repeat(x, mag * (2 if sw_i == 2 else 1), 0), mag * (2 if sw_i == 2 else 1), 1)
        A, B, D = m(a), m(b), m(np.clip(diff * 3.0, 0, 1))
        g = np.ones((A.shape[0], 10, 3))
        rows.append(np.concatenate([A, g, B, g, D], 1))
    w = max(r.shape[1] for r in rows)
    sheet = []
    for r in rows:
        pad = np.ones((r.shape[0], w, 3))
        pad[:, :r.shape[1]] = r
        sheet += [pad, np.ones((14, w, 3))]
    write_png(out_png, np.concatenate(sheet[:-1], 0))
    info["path"] = str(out_png)
    return info


__all__ = ["make_material", "pentakis_hull", "make_hull", "hull_worst_outside_m", "hull_volume_m3",
           "setup_reference", "render_reference", "teardown", "side_by_side", "crops_sheet", "reference_views",
           "clay_reference", "gallery", "lod_switch_frame", "load_png", "write_png", "light_levels"]
