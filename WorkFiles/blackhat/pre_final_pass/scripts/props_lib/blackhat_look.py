#!/usr/bin/env python
"""props_lib.blackhat_look - SM_BlackHat's Blender side: meshes, materials, AO bake, collision,
and every render, from the BAKED maps only.

bpy.  The two materials are the graph an Unreal material reproduces node for node:

    BaseColor  = T_BlackHat_<Part>_Detail.R x Tint     (Detail sRGB-encoded, sampled sRGB ON;
                                                          Tint default in the sidecar)
    Specular   = SPEC_SCALE x T_BlackHat_<Part>_ORM.A  (the baked specular mask; SPEC_SCALE 1.0: the
                                                       lacquered strand tops reach F0 0.08)
    Roughness  = ORM.G      Metallic = 0      Normal = _N (DirectX on disk; green flipped here)
    sheen 0, no coat, no subsurface, Lambert diffuse.  ORM.R (AO) is Unreal's indirect occlusion;
    Cycles traces its own, so it is not wired here.

    reference view   REFERENCE_SPEC 1's camera (blackhat_camera.RefCamera), 670 x 599, the
                     hat lit by soft area lights and a white environment, composited onto the
                     white backdrop (stored 0.996) with no cast shadow (REFERENCE_SPEC 2)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import blackhat_paint as BP
from . import render as R
from .blackhat_camera import RefCamera
from .blackhat_geom import MeshBuilder, PSI_DEG, D2R
from .gallery import _drop_to_ground, _label

MM = 0.001
#: Specular = SPEC_SCALE x ORM.A (Unreal's Specular pin, F0 = 0.08 x value)
SPEC_SCALE = 1.0
BACKDROP_STORED = 0.996


# =========================================================================== meshes
def to_blender(mb: MeshBuilder, uvs: List[np.ndarray], name: str, materials=(), collection=None):
    P = np.asarray(mb.P, np.float64) * MM
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in P], [], [list(f) for f in mb.F])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    flat = np.concatenate([np.asarray(u, np.float64) for u in uvs]).ravel()
    uvl.data.foreach_set("uv", flat)
    me.polygons.foreach_set("material_index", list(mb.FS))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    for m in materials:
        me.materials.append(m)
    nl = np.concatenate([np.asarray(n, np.float64) for n in mb.FN])
    nl /= np.maximum(np.linalg.norm(nl, axis=1, keepdims=True), 1e-12)
    me.normals_split_custom_set([tuple(n) for n in nl])
    me.validate(verbose=False)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


# =========================================================================== material
def make_material(name: str, paths: Dict[str, str], tint_linear, pack: bool = True, uv_name: str = "UVMap"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = uv_name

    def tex(path, cs):
        im = bpy.data.images.load(str(path), check_existing=False)
        im.colorspace_settings.name = cs
        im.name = Path(path).stem
        if pack:
            im.pack()
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = im
        tn.interpolation = "Linear"
        tn.extension = "REPEAT"
        nt.links.new(uvn.outputs[0], tn.inputs[0])
        return tn
    det = tex(paths["Detail"], "sRGB")
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(det.outputs["Color"], mul.inputs["A"])
    mul.inputs["B"].default_value = (tint_linear[0], tint_linear[1], tint_linear[2], 1.0)
    nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    orm = tex(paths["ORM"], "Non-Color")
    orm.image.alpha_mode = "CHANNEL_PACKED"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    ms = nt.nodes.new("ShaderNodeMath")
    ms.operation = "MULTIPLY"
    ms.inputs[1].default_value = SPEC_SCALE
    nt.links.new(orm.outputs["Alpha"], ms.inputs[0])
    nt.links.new(ms.outputs[0], bsdf.inputs["Specular IOR Level"])
    nrm = tex(paths["N"], "Non-Color")
    sepn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sepn.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sepn.outputs[1], inv.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sepn.outputs[0], comb.inputs[0])
    nt.links.new(inv.outputs[0], comb.inputs[1])
    nt.links.new(sepn.outputs[2], comb.inputs[2])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.space = "TANGENT"
    nmap.uv_map = uv_name
    nt.links.new(comb.outputs[0], nmap.inputs["Color"])
    nt.links.new(nmap.outputs[0], bsdf.inputs["Normal"])
    bsdf.inputs["IOR"].default_value = 1.5
    for nm, v in (("Sheen Weight", 0.0), ("Coat Weight", 0.0), ("Subsurface Weight", 0.0),
                  ("Diffuse Roughness", 0.0), ("Transmission Weight", 0.0)):
        if nm in bsdf.inputs:
            bsdf.inputs[nm].default_value = v
    mat["tint_linear"] = [float(x) for x in tint_linear]
    return mat


def unreal_material_spec(stem: str, maps: Dict[str, object]) -> Dict[str, object]:
    return {
        "shading_model": "Default Lit (or Substrate Slab); opaque; no Cloth/Fuzz layer",
        "BaseColor": f"{stem}_Detail.R x Tint (Tint default = tint_linear; equals {stem}_BC at the default Tint, "
                     f"at every mip)",
        "BaseColor_alt": f"{stem}_BC (sRGB) directly, for a fixed-colour instance",
        "Detail_encoding": "sRGB-encoded LINEAR detail d = albedo / Tint luminance, full range, quantised once "
                           "from linear float data; import sRGB ON (TC_Grayscale, G8)",
        "Tint_default_linear": [round(float(x), 6) for x in maps["tint_linear"]],
        "Tint_default_srgb": [round(float(x), 6) for x in maps["tint_srgb"]],
        "Specular": f"{SPEC_SCALE:g} x {stem}_ORM.A (the baked specular mask; linear, mip-safe). A constant 0.5 greys the "
                    f"weave gaps and seams",
        "Roughness": f"{stem}_ORM.G", "Metallic": "0", "AmbientOcclusion": f"{stem}_ORM.R",
        "Normal": f"{stem}_N (DirectX; TC_Normalmap, flip green OFF)",
        "textures": {"BC": "sRGB, TC_Default", "ORM": "linear (sRGB OFF), TC_Masks, RGBA (A = specular mask)",
                     "N": "TC_Normalmap", "Detail": "sRGB ON, TC_Grayscale, R channel",
                     "all": "MipGenSettings TMGS_FROM_TEXTURE_GROUP; 2048, power of two"},
    }


# =========================================================================== AO bake
def bake_ao(obj, cloth_slot: int, size: int, samples: int = 128, distance_m: float = 0.06):
    """Cycles AO of ``obj`` (alone) into one image per material slot.  The cloth's UV0 lives
    in the second tile (U + 1), so the bake uses a temporary UV layer with it moved back."""
    scene = bpy.context.scene
    saved_engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in pr.devices) else "CPU"
    except Exception:
        scene.cycles.device = "CPU"
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("W_AO")
        scene.world = world
    world.light_settings.distance = distance_m
    hidden = [(o, o.hide_render) for o in bpy.data.objects if o is not obj]
    me = obj.data
    src = me.uv_layers["UVMap"]
    tmp = me.uv_layers.new(name="__BakeUV")
    uv = np.empty(len(me.loops) * 2)
    src.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    uv[:, 0] = np.where(uv[:, 0] > 1.0, uv[:, 0] - 1.0, uv[:, 0])
    tmp.data.foreach_set("uv", uv.ravel())
    me.uv_layers.active = tmp
    images, nodes = [], []
    for i, slot in enumerate(obj.material_slots):
        im = bpy.data.images.new(f"__ao_{i}", size, size, alpha=False, is_data=True)
        im.colorspace_settings.name = "Non-Color"
        nt = slot.material.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = im
        for o in nt.nodes:
            o.select = False
        n.select = True
        nt.nodes.active = n
        images.append(im)
        nodes.append((nt, n))
    try:
        for o, _ in hidden:
            o.hide_render = True
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="AO", margin=8, margin_type="EXTEND", use_clear=True,
                            use_selected_to_active=False)
        out = []
        for im in images:
            px = np.empty(size * size * 4, np.float32)
            im.pixels.foreach_get(px)
            a = np.ascontiguousarray(px.reshape(size, size, 4)[::-1, :, 0])
            out.append(a)
    finally:
        for o, was in hidden:
            o.hide_render = was
        for nt, n in nodes:
            nt.nodes.remove(n)
        for im in images:
            bpy.data.images.remove(im)
        me.uv_layers.active = src
        me.uv_layers.remove(me.uv_layers["__BakeUV"])
        scene.render.engine = saved_engine
    return out


# =========================================================================== collision
def _hull_object(name, V, F, parent):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], [list(f) for f in F])
    me.update()
    me.validate(verbose=False)
    ob = bpy.data.objects.new(name, me)
    for c in parent.users_collection:
        c.objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.hide_render = True
    ob.display_type = "WIRE"
    ob["ue_collision"] = "UCX"
    return ob


def convex_faces(V):
    """Faces of the convex hull of V (bmesh), returned as (vertices, faces) of the hull only."""
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(v)) for v in V]
    res = bmesh.ops.convex_hull(bm, input=vs)
    keep = {f for f in res["geom"] if isinstance(f, bmesh.types.BMFace)}
    for f in list(bm.faces):
        if f not in keep:
            bm.faces.remove(f)
    for v in list(bm.verts):
        if not v.link_faces:
            bm.verts.remove(v)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    Vo = np.array([tuple(v.co) for v in bm.verts])
    Fo = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return Vo, Fo


def body_hull_points(co_mm: np.ndarray, n_sides: int = 15, margin: float = 0.3):
    """A 2 x n-gon band round the rim plus a raised apex, circumscribing every given vertex:
    31 vertices (the study's shape)."""
    r = np.hypot(co_mm[:, 0], co_mm[:, 1])
    z = co_mm[:, 2]
    rmax = float(r.max()) + margin
    r_out = rmax / math.cos(math.pi / n_sides)
    z0 = float(z.min()) - margin
    # the band top: as high as keeps the cone faces above every vertex, try a few heights
    best = None
    for z1 in np.linspace(z0 + 8.0, z0 + 40.0, 33):
        inner = r < rmax
        need = z1 + (z - z1) / np.maximum(1.0 - r / rmax, 1e-6)
        za = float(np.max(np.where(inner & (z > z1), need, z1))) + margin
        vol = za - z1
        if best is None or vol + 0.5 * (z1 - z0) < best[0]:
            best = (vol + 0.5 * (z1 - z0), z1, za)
    _, z1, za = best
    ph = (np.arange(n_sides) + 0.5) * 2 * math.pi / n_sides
    ring = np.stack([r_out * np.cos(ph), r_out * np.sin(ph)], -1)
    V = np.concatenate([np.c_[ring, np.full(n_sides, z0)], np.c_[ring, np.full(n_sides, z1)], [[0, 0, za]]])
    return V


def obb_points(co_mm: np.ndarray, margin: float = 0.5):
    c = co_mm.mean(0)
    X = co_mm - c
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    loc = X @ vt.T
    lo, hi = loc.min(0) - margin, loc.max(0) + margin
    corners = np.array([[a, b, cc] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for cc in (lo[2], hi[2])])
    return corners @ vt + c


def hull_worst_outside_mm(hull_V_mm, hull_F, co_mm):
    worst = -1e9
    Vh = np.asarray(hull_V_mm)
    cen = Vh.mean(0)
    for f in hull_F:
        a, b, c = Vh[f[0]], Vh[f[1]], Vh[f[2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        if (cen - a) @ n > 0:
            n = -n
        worst = max(worst, float(((co_mm - a) @ n).max()))
    return worst


# =========================================================================== reference view
#: REFERENCE_SPEC 2: soft sources, camera-facing bays darkest, sides 2-4x brighter (left ~1.3x
#: right): grazing sheen plus lights behind both sides.  (theta, elevation, distance x R, size x R,
#: power W at R = 300 mm, colour)  - tuned on the brightness-vs-azimuth rows
REF_LIGHTS = [
    # fitted (non-negative least squares over REFERENCE_SPEC 2's azimuth rows and the part regions,
    # WorkFiles/blackhat/build_dev/tools/fit_lights.py) - soft discs 3 R across at 4 R
    ("BackTop", 180.0, 50.0, 4.0, 3.0, 0.204, (1.0, 1.0, 1.0)),
    ("FrontLeft", -45.0, 30.0, 4.0, 3.0, 1.120, (1.0, 1.0, 1.0)),
    ("FrontRight", 45.0, 30.0, 4.0, 3.0, 1.665, (1.0, 1.0, 1.0)),
    ("Front", 0.0, 15.0, 4.0, 3.0, 1.675, (1.0, 1.0, 1.0)),
    ("Key", -112.0, 32.0, 4.0, 3.0, 1.636, (1.0, 1.0, 1.0)),
    ("LeftBackLow", -150.0, 10.0, 4.0, 3.0, 0.081, (1.0, 1.0, 1.0)),
    ("Left", -90.0, 20.0, 4.0, 3.0, 0.780, (1.0, 1.0, 1.0)),
    ("LeftHigh", -110.0, 60.0, 4.0, 3.0, 1.000, (1.0, 1.0, 1.0)),
    ("LeftRake", -75.0, 5.0, 4.0, 3.0, 1.133, (1.0, 1.0, 1.0)),
    ("RightBack", 150.0, 10.0, 4.0, 3.0, 0.442, (1.0, 1.0, 1.0)),
    ("Right", 90.0, 20.0, 4.0, 3.0, 0.666, (1.0, 1.0, 1.0)),
]
REF_WORLD = 0.027


def _cycles(scene, samples, denoise=False):
    scene.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in pr.devices) else "CPU"
    except Exception:
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.cycles.use_adaptive_sampling = False


def setup_reference(cam: RefCamera, samples: int = 256, lights=None, world: float = None, res=None):
    scene = bpy.context.scene
    _cycles(scene, samples)
    scene.cycles.filter_width = 1.5
    w, h = res or cam.res
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    coll = bpy.data.collections.new("BH_REFERENCE_RIG")
    scene.collection.children.link(coll)
    b = cam.blender()
    cd = bpy.data.cameras.new("BH_RefCam")
    cd.lens = b["lens_mm"]
    cd.sensor_width = 36.0
    cd.sensor_fit = "HORIZONTAL"
    cd.shift_x, cd.shift_y = b["shift_x"], b["shift_y"]
    cd.clip_start = 0.02
    cd.clip_end = 20.0
    co = bpy.data.objects.new("BH_RefCam", cd)
    coll.objects.link(co)
    M = Matrix(np.array(b["matrix3"]).tolist()).to_4x4()
    M.translation = [x * MM for x in b["location_mm"]]
    co.matrix_world = M
    scene.camera = co
    lamps = []
    R = cam.R
    centre = Vector((0.0, 0.0, 0.2 * R * MM))
    for name, th, el, dist, size, power, col in (REF_LIGHTS if lights is None else lights):
        ld = bpy.data.lights.new("BH_" + name, "AREA")
        ld.shape = "DISK"
        ld.size = size * R * MM
        ld.energy = power
        ld.color = col
        lo = bpy.data.objects.new("BH_" + name, ld)
        coll.objects.link(lo)
        ph = (th + PSI_DEG) * D2R
        e = el * D2R
        lo.location = centre + Vector((math.cos(ph) * math.cos(e), math.sin(ph) * math.cos(e), math.sin(e))) * dist * R * MM
        d = (centre - lo.location).normalized()
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        lamps.append(lo)
    wd = bpy.data.worlds.new("BH_RefWorld")
    wd.use_nodes = True
    bg = next(n for n in wd.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = REF_WORLD if world is None else world
    scene.world = wd
    return {"collection": coll, "camera": co, "lamps": lamps, "world": wd}


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


def composite_white(a) -> np.ndarray:
    bg = BP.srgb_decode(np.array(BACKDROP_STORED))
    lin = a[..., :3] + (1.0 - a[..., 3:4]) * bg
    return BP.srgb_encode(lin)


def write_png(path, arr) -> str:
    """Plain PNG (no colour chunks): uint8 or float 0..1; grey / RGB / RGBA; rows top-down."""
    import struct
    import zlib
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = np.rint(np.clip(a.astype(np.float64), 0, 1) * 255).astype(np.uint8)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, {1: 0, 3: 2, 4: 6}[c], 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6))
                           + chunk(b"IEND", b""))
    return str(path)


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


def hide_all_but(keep):
    keep = set(keep)
    saved = [(o, o.hide_render) for o in bpy.data.objects]
    for o in bpy.data.objects:
        if o.type in {"MESH", "CURVE", "FONT"}:
            o.hide_render = o not in keep
    return saved


def restore(saved):
    for o, was in saved:
        try:
            o.hide_render = was
        except ReferenceError:
            pass


def reference_view(obj, cam: RefCamera, out_png, work: Path, samples: int = 256, lights=None, world=None):
    saved = hide_all_but([obj])
    try:
        rig = setup_reference(cam, samples, lights, world)
        a = render_exr(Path(work) / "bh_reference_view.exr")
        stored = composite_white(a)
        write_png(out_png, stored)
        teardown(rig)
    finally:
        restore(saved)
    return stored


def side_by_side(ref_png, render_png, out_png, gap: int = 12):
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    h = max(ref.shape[0], ren.shape[0])
    sheet = np.ones((h, ref.shape[1] + gap + ren.shape[1], 3))
    sheet[:ref.shape[0], :ref.shape[1]] = ref
    sheet[:ren.shape[0], ref.shape[1] + gap:] = ren
    write_png(out_png, sheet)
    return str(out_png)


def crops_sheet(ref_png, render_png, out_png, boxes, scale: int = 3, gap: int = 8):
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
        out += [pad, np.ones((gap, w, 3))]
    write_png(out_png, np.concatenate(out[:-1], 0))
    return str(out_png)


__all__ = ["to_blender", "make_material", "unreal_material_spec", "bake_ao", "body_hull_points", "obb_points",
           "convex_faces", "hull_worst_outside_mm", "setup_reference", "teardown", "render_exr", "reference_view",
           "side_by_side", "crops_sheet", "load_png", "write_png", "REF_LIGHTS", "REF_WORLD", "composite_white"]
