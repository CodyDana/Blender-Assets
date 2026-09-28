#!/usr/bin/env python
"""props_lib.flashbang_paint - SM_Flashbang's maps: Cycles bakes of the LOD0 game mesh + a numpy painter (round 1).

BAKES (Cycles, on UV0 of LOD0 alone, 16 px EXTEND margin): object position, shading normal, the LOOK and island
ids (face attributes), two edge masks (1 - dot(Bevel normal, normal) at 0.5 mm and 1.6 mm: every real arris, hole
rim, chamfer and step), ambient occlusion (pipeline.textures.bake_ao) and a tangent-space NORMAL bake of a Bevel
node (r 0.3 mm) - the crisp geometric edges read as slightly rounded steel, which is how the reference catches its
bright rims.

PAINTER (numpy, per texel, 3-D noise evaluated at the baked position so nothing breaks at a UV seam):
    paint     olive over steel; low mottling (luminance only, so Detail x Colour == BC), dark grime by AO and
              in the corners, dark flecks
    chips     bare steel where the paint is gone: a score of edge masks + hole-rim / ring-line / sleeve-chamfer /
              step zones + two noise scales, thresholded to the reference's measured fractions (spec 9: 14 % of
              the body chipped, 58 % of the texels within 0.75 mm of a hole edge bare)
    steel     dark antiqued steel with bright worn arrises, fine scratches, pits; the lever lighter with a
              cross-hatch of scratches on its face (v4); the ring smoother
    brass     the inner tube, warm bronze-gold with tarnish and a seam line at each hole row (spec 4)
    relief    height (mm) -> tangent-space detail normal per island (UV axes ARE the tangent frame: no island is
              rotated or mirrored), combined with the bevel bake: ring-line grooves (0.66 mm, spec 4), the paint's
              thickness step at every chip, scratches, pits, the brass seams, housing panel lines, collar line
No reference pixel is read here: the colours are albedo targets set from the Study's measured appearance and
calibrated by rendering the shipped maps in the reference's light (build report).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Tuple

import numpy as np

try:
    import bpy
except ImportError:                                   # pragma: no cover
    bpy = None

from .flashbang_spec import FLASHBANG, FlashbangSpec

POS_SCALE = 0.25          # position bake: p_m * POS_SCALE + 0.5 (covers +-2 m)


# =============================================================================== calibration (albedo targets)
@dataclass
class Look:
    """FINALISE (craft + blind review): darker oxidised steel with bright BROKEN arrises and straight scratch strokes,
    chips with a dark oxidised core and a thin warm bright edge (not pale flecks), heavy dark grime blotches, a wider
    paint tonal range, a hammered paint surface, brighter pitted brass cans, a stamped cross-hatch on the lever."""
    paint_lin: Tuple[float, float, float] = (0.080, 0.080, 0.038)     # olive (lit p50 71,71,54 in the reference)
    paint_mottle: float = 0.30
    paint_fine: float = 0.10
    paint_light: float = 0.45          # lighter worn scuffs 1-4 mm (the reference's p90 101-116)
    paint_grime: float = 0.55          # dark grime blotches (p10 40-44)
    paint_rough: float = 0.46
    chip_frac: float = 0.143           # spec 9
    chip_near_hole_frac: float = 0.577
    chip_core_lin: Tuple[float, float, float] = (0.034, 0.030, 0.026)  # oxidised dark steel (sRGB ~50)
    chip_edge_lin: Tuple[float, float, float] = (0.26, 0.20, 0.135)    # warm bright bronze-steel rim (sRGB ~125)
    chip_rough: float = 0.55
    steel_lin: Tuple[float, float, float] = (0.040, 0.037, 0.034)      # dark antiqued steel (housing p50 42-50)
    steel_edge_lin: Tuple[float, float, float] = (0.50, 0.40, 0.29)
    steel_rough: float = 0.55
    steel_edge_rough: float = 0.36
    lever_lin: Tuple[float, float, float] = (0.055, 0.052, 0.048)
    ring_lin: Tuple[float, float, float] = (0.050, 0.047, 0.043)       # darker antiqued ring wire (sRGB ~60-75 lit)
    inner_lin: Tuple[float, float, float] = (0.020, 0.019, 0.018)
    brass_lin: Tuple[float, float, float] = (0.80, 0.60, 0.33)
    brass_rough: float = 0.40
    wall_lin: Tuple[float, float, float] = (0.045, 0.041, 0.037)       # hole walls: dark cut steel, grimy
    edge_wear_steel: float = 0.95
    seed: int = 20260927


LOOK = Look()


# =============================================================================== noise
def _hash3(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ seed
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return ((h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF))


def value_noise(p, scale, seed=0):
    """Trilinear value noise in [0, 1] at points p (N, 3) (mm), feature size ``scale`` mm."""
    q = p / scale
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)
    i = i.astype(np.int64)
    out = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, scale, octaves=4, seed=0, gain=0.5):
    tot = np.zeros(len(p), np.float32)
    amp, norm, s = 1.0, 0.0, scale
    for o in range(octaves):
        tot += amp * value_noise(p, s, seed + 101 * o)
        norm += amp
        amp *= gain
        s *= 0.5
    return tot / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def strokes(p, n, cell, density, length, width, seed, vertical=0.0):
    """FINALISE: straight scratch STROKES (no closed loops, no lens shapes - the round-1 level-set scratches drew a
    vesica on the housing).  A 3-D grid of ``cell`` mm cells; each cell holds one stroke with probability
    ``density``: a random centre, direction (``vertical`` biases it toward +-Z), length in ``length`` mm and width
    ``width`` x (0.6 .. 1.4) mm.  Evaluated in each point's tangent plane (the offset along the surface normal only
    gates it), so a stroke marks the surface it passes near.  Returns 0..1 (Gaussian across, tapered ends)."""
    out = np.zeros(len(p), np.float32)
    if len(p) == 0:
        return out
    base = np.floor(p / cell).astype(np.int64)
    lim = 0.5 * cell
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + np.array([dx, dy, dz], np.int64)
                present = _hash3(c[:, 0], c[:, 1], c[:, 2], seed) < density
                idx = np.nonzero(present)[0]
                if not len(idx):
                    continue
                cc = c[idx]
                hs = [_hash3(cc[:, 0], cc[:, 1], cc[:, 2], seed + k) for k in range(1, 8)]
                centre = (cc + np.stack(hs[:3], 1)) * cell
                a1 = hs[3] * (2 * math.pi)
                a2 = hs[4] * 2.0 - 1.0
                sq = np.sqrt(np.clip(1.0 - a2 * a2, 0, 1))
                d = np.stack([sq * np.cos(a1), sq * np.sin(a1), a2], 1)
                if vertical:
                    d = d * (1.0 - vertical) + np.array([0.0, 0.0, 1.0]) * vertical * np.where(a2 >= 0, 1.0, -1.0)[:, None]
                    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
                L = length[0] + hs[5] * (length[1] - length[0])
                w = width * (0.6 + 0.8 * hs[6])
                v = p[idx] - centre
                nn = n[idx]
                vn = (v * nn).sum(1)
                vt = v - vn[:, None] * nn
                dt = d - (d * nn).sum(1)[:, None] * nn
                dl = np.linalg.norm(dt, axis=1)
                dt = dt / np.maximum(dl, 1e-9)[:, None]
                along = (vt * dt).sum(1)
                perp = np.linalg.norm(vt - along[:, None] * dt, axis=1)
                taper = np.clip(1.0 - (along / (0.5 * L)) ** 2, 0.0, 1.0)
                val = np.exp(-(perp / w) ** 2) * taper * (dl > 0.35) * (np.abs(vn) < lim)
                out[idx] = np.maximum(out[idx], val.astype(np.float32))
    return out


# =============================================================================== bakes (bpy)
def _img(name, size, float_buffer=True):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    im = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer, is_data=True)
    im.colorspace_settings.name = "Non-Color"
    return im


def _pixels(im):
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def _bake_material(kind, image, bevel_r=0.0005):
    m = bpy.data.materials.new(f"__fb_bake_{kind}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.nodes.active = tex
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    if kind == "normal":
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.samples = 16
        bev.inputs["Radius"].default_value = bevel_r
        b = nt.nodes.new("ShaderNodeBsdfDiffuse")
        nt.links.new(bev.outputs["Normal"], b.inputs["Normal"])
        nt.links.new(b.outputs[0], out.inputs["Surface"])
        return m
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    if kind == "pos":
        mul = nt.nodes.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY_ADD"
        mul.inputs[1].default_value = (POS_SCALE,) * 3
        mul.inputs[2].default_value = (0.5,) * 3
        nt.links.new(geo.outputs["Position"], mul.inputs[0])
        nt.links.new(mul.outputs[0], em.inputs["Color"])
    elif kind == "nrm":
        mul = nt.nodes.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY_ADD"
        mul.inputs[1].default_value = (0.5,) * 3
        mul.inputs[2].default_value = (0.5,) * 3
        nt.links.new(geo.outputs["Normal"], mul.inputs[0])
        nt.links.new(mul.outputs[0], em.inputs["Color"])
    elif kind in ("look", "island"):
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_type = "GEOMETRY"
        at.attribute_name = "fb_look" if kind == "look" else "fb_island"
        div = nt.nodes.new("ShaderNodeMath")
        div.operation = "DIVIDE"
        div.inputs[1].default_value = 256.0
        nt.links.new(at.outputs["Fac"], div.inputs[0])
        nt.links.new(div.outputs[0], em.inputs["Color"])
    elif kind.startswith("edge"):
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.samples = 16
        bev.inputs["Radius"].default_value = bevel_r
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["Normal"], dot.inputs[1])
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[0].default_value = 1.0
        nt.links.new(dot.outputs["Value"], sub.inputs[1])
        nt.links.new(sub.outputs[0], em.inputs["Color"])
    elif kind == "cover":
        em.inputs["Color"].default_value = (1, 1, 1, 1)
    return m


def bake_inputs(obj, size, samples=16, log=print) -> Dict[str, np.ndarray]:
    """Every bake the painter needs, as arrays (rows bottom-up, Blender's order)."""
    from pipeline.helpers import selection
    from pipeline.textures import bake_ao
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = (d.type == "OPTIX")
        sc.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
    except Exception:
        sc.cycles.device = "CPU"
    mats0 = list(obj.data.materials)
    # clearing a mesh's materials resets every face's material_index: keep them and put them back
    mi0 = np.empty(len(obj.data.polygons), np.int32)
    obj.data.polygons.foreach_get("material_index", mi0)
    hidden = [(o, o.hide_render) for o in bpy.data.objects if o is not obj]
    for o, _ in hidden:
        o.hide_render = True
    out = {}
    try:
        sc.render.bake.margin_type = "EXTEND"
        sc.render.bake.use_clear = True
        sc.render.bake.use_selected_to_active = False
        sc.render.bake.target = "IMAGE_TEXTURES"
        jobs = [("cover", "EMIT", 0, 1, 0.0), ("pos", "EMIT", 16, 1, 0.0), ("nrm", "EMIT", 16, 4, 0.0),
                ("look", "EMIT", 16, 1, 0.0), ("island", "EMIT", 0, 1, 0.0),
                ("edge_s", "EMIT", 16, samples, 0.0005), ("edge_l", "EMIT", 16, samples, 0.0016),
                ("normal", "NORMAL", 16, samples, 0.0003)]
        for kind, btype, margin, spp, r in jobs:
            im = _img(f"__fb_{kind}", size)
            mat = _bake_material(kind, im, r)
            obj.data.materials.clear()
            for _ in mats0 or [None]:
                obj.data.materials.append(mat)
            sc.cycles.samples = spp
            sc.render.bake.margin = margin
            kw = {}
            if btype == "NORMAL":
                sc.render.bake.normal_space = "TANGENT"
                kw = dict(normal_space="TANGENT", normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
            with selection([obj], obj):
                res = bpy.ops.object.bake(type=btype, margin=margin, margin_type="EXTEND", use_clear=True,
                                          use_selected_to_active=False, **kw)
            if "FINISHED" not in res:
                raise RuntimeError(f"bake {kind} failed: {res}")
            out[kind] = _pixels(im)[..., :3].copy()
            bpy.data.images.remove(im)
            bpy.data.materials.remove(mat)
            log(f"  baked {kind} ({btype}, {spp} spp, margin {margin})")
        obj.data.materials.clear()
        for m in mats0:
            obj.data.materials.append(m)
        tmp = bpy.data.materials.new("__fb_ao_tmp")
        if not obj.data.materials:
            obj.data.materials.append(tmp)
        im = bake_ao(obj, "__fb_ao", size=size, samples=max(64, samples * 8), margin=16)
        out["ao"] = _pixels(im)[..., 0].copy()
        bpy.data.images.remove(im)
        if tmp.users == 0:
            bpy.data.materials.remove(tmp)
        log("  baked ao (pipeline.textures.bake_ao)")
    finally:
        obj.data.materials.clear()
        for m in mats0:
            obj.data.materials.append(m)
        obj.data.polygons.foreach_set("material_index", mi0)
        obj.data.update()
        for o, was in hidden:
            o.hide_render = was
    return out


# =============================================================================== painter
def _grow(values, known, iters=24):
    """Extend known texels into unknown ones (neighbour average), in place; returns the array."""
    v = values.copy()
    k = known.copy()
    for _ in range(iters):
        if k.all():
            break
        acc = np.zeros_like(v)
        cnt = np.zeros(k.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            kk = np.roll(np.roll(k, dy, 0), dx, 1)
            vv = np.roll(np.roll(v, dy, 0), dx, 1)
            if v.ndim == 3:
                acc += vv * kk[..., None]
            else:
                acc += vv * kk
            cnt += kk
        new = (~k) & (cnt > 0)
        if v.ndim == 3:
            v[new] = acc[new] / cnt[new][:, None]
        else:
            v[new] = acc[new] / cnt[new]
        k = k | new
    return v


def _erode(mask, iters):
    m = mask.copy()
    for _ in range(iters):
        m = (m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    return m


def paint(bk: Dict[str, np.ndarray], spec: FlashbangSpec, packing, look: Look = LOOK, log=print):
    """Compose linear albedo, roughness, metallic, height (mm) from the bakes.  Arrays bottom-up (v up)."""
    H, W = bk["pos"].shape[:2]
    cover = bk["cover"][..., 0] > 0.5
    looks = np.rint(bk["look"][..., 0] * 256.0).astype(np.int32)
    isl = np.rint(bk["island"][..., 0] * 256.0).astype(np.int32)
    P = (bk["pos"] - 0.5) / POS_SCALE * 1000.0                    # mm
    N = bk["nrm"] * 2.0 - 1.0
    es = np.clip(bk["edge_s"][..., 0] * 6.0, 0, 1)                # ~1 at a 90 deg arris
    el = np.clip(bk["edge_l"][..., 0] * 4.0, 0, 1)
    ao = np.clip(bk["ao"], 0, 1)
    idx = np.nonzero(cover.ravel())[0]
    p = P.reshape(-1, 3)[idx]
    n = N.reshape(-1, 3)[idx]
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
    L = looks.ravel()[idx]
    e_s, e_l, a_o = es.ravel()[idx], el.ravel()[idx], ao.ravel()[idx]
    sd = look.seed
    r_xy = np.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]

    # ------------------------------------------------ noise fields (3-D, seam-free)
    n_big = fbm(p, 9.0, 4, sd + 1)
    n_mid = fbm(p, 2.4, 4, sd + 2)
    n_fine = fbm(p, 0.45, 3, sd + 3)
    n_speck = value_noise(p, 0.18, sd + 4)
    n_grime = fbm(p, 5.0, 3, sd + 5)
    n_blot = fbm(p, 7.0, 3, sd + 21)              # FINALISE: grime blotches 3-15 mm
    n_light = fbm(p, 2.8, 3, sd + 22)             # FINALISE: lighter worn paint scuffs
    n_dash = value_noise(p, 1.6, sd + 31)         # FINALISE: breaks every bright arris into dashes

    is_paint = (L == 0)
    is_wall = (L == 6)
    zone = np.zeros(len(idx), np.float32)
    on_body = is_paint & (r_xy < spec.body_r + 0.05) & (z > spec.body_z0) & (z < spec.sleeve_z0 + 0.01)
    on_sleeve = is_paint & (z >= spec.sleeve_z0 - 0.01)
    for zl in spec.ring_lines_z:
        zone += 0.75 * np.exp(-((z - zl) / 0.35) ** 2) * on_body          # chips run along the engraved line
    # FINALISE: the sleeve's top chamfer keeps 50-70 % of its paint (round 1 forced it bare: a chrome band)
    zone += 0.10 * smoothstep(spec.sleeve_z1 - 0.3, spec.sleeve_z1 + 0.8, z) * on_sleeve
    zone += 0.35 * np.exp(-((z - spec.sleeve_z0) / 0.7) ** 2) * is_paint                     # sleeve step
    zone += 0.30 * np.exp(-((z - spec.body_z0) / 1.6) ** 2) * on_body                        # body bottom
    pm = is_paint
    near = pm & (e_s > 0.45)
    n_fleck = value_noise(p, 0.32, sd + 11)
    # FINALISE: chips are 1-3 mm blotches (mid noise) more than fine flecks
    base_sc = (zone + 0.60 * (n_mid - 0.5) + 0.30 * (n_fine - 0.5) + 0.25 * (n_big - 0.5)
               + 0.35 * (n_speck > 0.965) + 0.25 * (n_fleck > 0.92))
    best = None
    for w_e in np.linspace(0.0, 1.6, 33):
        sc_ = base_sc + w_e * e_s + 0.25 * w_e * e_l
        t_ = float(np.quantile(sc_[pm], 1.0 - look.chip_frac))
        f_ = float((sc_[near] > t_).mean()) if near.any() else 0.0
        if best is None or abs(f_ - look.chip_near_hole_frac) < abs(best[2] - look.chip_near_hole_frac):
            best = (w_e, t_, f_)
    w_edge, thr, chip_near = best
    score = base_sc + w_edge * e_s + 0.25 * w_edge * e_l
    chip = pm & (score > thr)
    log(f"  chips: edge weight {w_edge:.2f}, threshold {thr:.3f}, chipped {chip[pm].mean():.3f} of paint, "
        f"near-edge texels bare {chip_near:.3f}")
    # chip core vs its thin bright edge: erode the chip mask 2 texels (~0.23 mm) in the atlas
    chip_img = np.zeros(H * W, bool)
    chip_img[idx] = chip
    chip_img = chip_img.reshape(H, W)
    core_img = _erode(chip_img, 2)
    chip_core = core_img.ravel()[idx] & chip
    chip_edge = chip & ~chip_core

    # ------------------------------------------------ albedo, roughness, metallic, height
    alb = np.zeros((len(idx), 3), np.float32)
    rough = np.zeros(len(idx), np.float32)
    metal = np.zeros(len(idx), np.float32)
    h = np.zeros(len(idx), np.float32)
    # grime zones: hole rims (the wide bevel mask), the ring lines, the body's bottom, the sleeve step
    gzone = np.clip(0.8 * e_l + sum(np.exp(-((z - zl) / 2.0) ** 2) for zl in spec.ring_lines_z)
                    + np.exp(-((z - spec.body_z0) / 6.0) ** 2) + 0.6 * np.exp(-((z - spec.sleeve_z0) / 2.5) ** 2), 0, 1.5)
    blot = smoothstep(0.60, 0.74, n_blot + 0.14 * gzone)                                   # 3-15 mm blotches
    grime_cav = np.clip((1.0 - a_o) * 1.6, 0, 1) * (0.55 + 0.9 * (n_grime - 0.5))
    grime = np.clip(np.maximum(grime_cav, blot * (0.75 + 0.5 * n_mid)), 0, 1)
    # paint (luminance-only variation: Detail x Colour == BC)
    pc = np.array(look.paint_lin, np.float32)
    lumf = (1.0 + look.paint_mottle * (n_big - 0.5) * 2.0 + look.paint_fine * (n_fine - 0.5) * 2.0)
    lumf *= 1.0 + look.paint_light * smoothstep(0.58, 0.78, n_light) * (1.0 - blot)
    lumf *= (1.0 - look.paint_grime * grime)
    lumf *= np.where(n_speck < 0.05, 0.45, 1.0)                                              # dark flecks
    lumf *= np.where(value_noise(p, 1.1, sd + 12) < 0.12, 0.6, 1.0)                           # grime spots
    edge_band = pm & ~chip & (score > thr - 0.07)
    lumf *= np.where(edge_band, 0.70, 1.0)                                                   # paint lip shadow
    lumf = np.clip(lumf, 0.22, 2.2)                   # dielectric paint luminance stays < 0.18 (gate 12)
    alb[pm] = pc[None, :] * lumf[pm, None]
    rough[pm] = np.clip(look.paint_rough + 0.08 * (n_mid[pm] - 0.5) + 0.14 * grime[pm], 0.4, 0.9)
    # FINALISE: hammered / orange-peel paint surface (low amplitude)
    h[pm] = (0.05 + 0.028 * (value_noise(p[pm], 0.85, sd + 13) - 0.5) + 0.012 * (n_fine[pm] - 0.5)
             + 0.015 * (n_mid[pm] - 0.5))
    # chips: dark oxidised core (a little brown), thin warm bright edge
    brown = np.array([0.055, 0.038, 0.024], np.float32)
    core = (np.array(look.chip_core_lin)[None, :] * (1 - n_mid[:, None] * 0.6) + brown[None, :] * n_mid[:, None] * 0.6)
    core *= (0.8 + 0.45 * n_fine)[:, None]
    edge = np.array(look.chip_edge_lin)[None, :] * (0.7 + 0.6 * n_mid)[:, None]
    alb[chip_core] = core[chip_core]
    alb[chip_edge] = edge[chip_edge]
    rough[chip_core] = np.clip(0.62 + 0.1 * (n_fine[chip_core] - 0.5), 0.45, 0.8)
    rough[chip_edge] = 0.36
    metal[chip] = 1.0
    h[chip] = 0.0
    # hole walls: dark cut steel with grime
    wc = np.array(look.wall_lin)[None, :] * (0.75 + 0.5 * n_mid[is_wall, None])
    alb[is_wall] = wc * (1.0 - 0.45 * grime[is_wall, None])
    rough[is_wall] = 0.58
    metal[is_wall] = 1.0
    # steel families: dark antiqued base, BROKEN bright arrises (thin bevel only, in dashes), bright scratch strokes,
    # bronze specks, grime in the corners and blotches
    for lk, base, rgh in ((1, look.steel_lin, look.steel_rough), (4, look.lever_lin, 0.48), (5, look.ring_lin, 0.42),
                          (3, look.inner_lin, 0.6), (6, look.wall_lin, 0.58)):
        m = (L == lk)
        if not m.any():
            continue
        b = np.array(base, np.float32)[None, :]
        var = (0.75 + 0.5 * n_big[m] * n_mid[m] * 2.0 - 0.25)[:, None]
        col = b * np.clip(var, 0.55, 1.35)
        dash = smoothstep(0.42, 0.62, n_dash[m])
        wear = np.clip(look.edge_wear_steel * 1.5 * e_s[m] * (0.5 + 0.9 * n_fine[m]) - 0.15, 0, 1) * dash
        if lk == 5:
            # the ring: bright wear only on the OUTER arc of the loop
            s_ = spec
            tau = math.radians(s_.ring_tilt_deg)
            zdir = np.array([0.0, math.sin(tau), math.cos(tau)])
            xdir = np.array([1.0, 0.0, 0.0])
            nplane = np.cross(xdir, zdir)
            px_, pz_ = s_.pin_c
            c = np.array([px_, s_.pin_eye_y(), pz_]) - s_.ring_major_r * zdir
            v = p[m] - c
            rp = v - (v @ nplane)[:, None] * nplane[None, :]
            rd = rp / np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-6)
            outer = np.clip(((n[m] * rd).sum(1) - 0.45) / 0.4, 0, 1) * (np.linalg.norm(v, axis=1) > 12.0)
            wear = np.maximum(wear, outer * smoothstep(0.35, 0.65, n_dash[m]) * 0.75)
        if lk in (1, 4, 5):
            # fine, short, dense scratch marks (the reference's antiqued steel), then bright bronze specks
            scr = strokes(p[m], n[m], 1.3, 0.6, (0.5, 2.6), 0.03, sd + 300 + lk)
            wear = np.maximum(wear, 0.5 * scr * (0.5 + n_mid[m]))
            wear = np.maximum(wear, 0.6 * (n_speck[m] > 0.955))
        if lk in (3, 6):
            wear *= 0.35
        ecol = np.array(look.steel_edge_lin)[None, :] * (0.65 + 0.6 * n_mid[m])[:, None]
        col = col * (1 - wear[:, None]) + ecol * wear[:, None]
        g2 = np.clip(np.maximum(np.clip((1.0 - a_o[m]) * 1.4, 0, 1), 0.8 * blot[m]), 0, 1)
        col *= (1.0 - 0.55 * g2)[:, None]
        col = col * (1.0 - 0.25 * g2[:, None]) + brown[None, :] * 0.25 * g2[:, None] * (col.mean(1, keepdims=True) / 0.05)
        alb[m] = col
        rough[m] = np.clip(rgh + 0.12 * (n_mid[m] - 0.5) - (rgh - look.steel_edge_rough) * wear + 0.15 * g2, 0.2, 0.85)
        metal[m] = 1.0
        pits = (value_noise(p[m], 0.35, sd + 9) > 0.93).astype(np.float32)
        h[m] -= 0.03 * pits
        if lk in (1, 4, 5):
            h[m] -= 0.02 * scr
    # the lever's stamped diagonal cross-hatch (v4 / pair 7): two line families +-35 deg from vertical, 1.5 mm pitch
    m = (L == 4) & (np.abs(n[:, 1]) < 0.5)            # the web faces only (the flanges face +-Y)
    if m.any():
        y_, z_ = p[m, 1], p[m, 2]
        hat = np.zeros(int(m.sum()), np.float32)
        for sg in (-1.0, 1.0):
            a = math.radians(35.0)
            w_ = -math.cos(a) * y_ * sg + math.sin(a) * z_
            f = w_ / 1.5 - np.round(w_ / 1.5)
            hat = np.maximum(hat, np.exp(-((f * 1.5) / 0.13) ** 2))
        hat *= (0.25 + 0.75 * (value_noise(p[m], 2.0, sd + 77) > 0.45)) * (0.5 + n_mid[m])
        ecol = np.array(look.steel_edge_lin)[None, :] * 0.55
        alb[m] = alb[m] * (1 - 0.15 * hat[:, None]) + ecol * 0.15 * hat[:, None]
        rough[m] -= 0.08 * hat
        h[m] -= 0.03 * hat
    # brass cans: brighter, pitted, vertical scratches, grime in the lower third of each window, the seam and the
    # shoulder just above it (a light band + a height rise)
    m = (L == 2)
    if m.any():
        b = np.array(look.brass_lin, np.float32)[None, :]
        tarn = 0.82 + 0.3 * (n_big[m] - 0.5) * 2 + 0.12 * (n_fine[m] - 0.5)
        col = b * np.clip(tarn, 0.5, 1.1)[:, None]
        vs = strokes(p[m], n[m], 1.4, 0.7, (2.5, 9.0), 0.045, sd + 401, vertical=0.9)
        col *= (1.0 + 0.22 * vs)[:, None]
        pit = value_noise(p[m], 0.22, sd + 402) > 0.9
        col[pit] *= 0.45
        zc = np.array(sorted(spec.hole_rows_z))
        dzr = z[m] - zc[np.argmin(np.abs(z[m][:, None] - zc[None, :]), axis=1)]
        low = smoothstep(-2.5, -8.0, dzr) * (0.6 + 0.6 * n_mid[m])
        col *= (1.0 - 0.5 * np.clip(low, 0, 1))[:, None]
        rgh = np.clip(look.brass_rough + 0.12 * (n_big[m] - 0.5) + 0.12 * np.clip(low, 0, 1) - 0.1 * vs, 0.28, 0.6)
        hh = np.zeros(int(m.sum()), np.float32)
        for zs in spec.tube_seam_z:
            g = np.exp(-((z[m] - zs) / 0.16) ** 2)
            sh = np.exp(-((z[m] - zs - 0.9) / 0.45) ** 2)
            col *= (1.0 - 0.65 * g + 0.25 * sh)[:, None]
            hh += -0.10 * g + 0.20 * smoothstep(zs, zs + 1.2, z[m]) * (z[m] < zs + 12.0)
        col *= (0.55 + 0.45 * a_o[m])[:, None]
        alb[m] = col
        rough[m] = rgh
        metal[m] = 1.0
        h[m] = hh - 0.02 * pit
    # ring lines: the engraved groove, a lighter upper lip (luminance only on the paint)
    for zl in spec.ring_lines_z:
        g = np.exp(-((z - zl) / (spec.ring_line_w * 0.5)) ** 2)
        lip = np.exp(-((z - zl - spec.ring_line_w * 0.8) / (spec.ring_line_w * 0.35)) ** 2)
        sel = on_body | (is_paint & (np.abs(z - zl) < 1.0))
        h[sel] += (-0.07 * g[sel] + 0.03 * lip[sel])
        alb[sel] *= (1.0 - 0.15 * g[sel] + 0.30 * lip[sel] * (~chip[sel]))[:, None]
    # the collar line (the round-1 housing panel lines are gone: the front panel is geometry now)
    m = (L == 1)
    col_sel = m & (np.abs(r_xy - spec.collar_r) < 0.15) & (np.abs(z - spec.collar_groove_z) < 1.0)
    g = np.exp(-((z - spec.collar_groove_z) / 0.22) ** 2)
    h[col_sel] -= 0.12 * g[col_sel]
    # scratches through the paint: thin bright strokes (steel shows), a few
    sp = pm & ~chip
    scr_p = strokes(p[sp], n[sp], 4.0, 0.30, (2.0, 8.0), 0.055, sd + 500)
    hit = scr_p > 0.5
    ii = np.nonzero(sp)[0][hit]
    alb[ii] = np.array(look.chip_edge_lin)[None, :] * 0.85
    metal[ii] = 1.0
    rough[ii] = 0.38
    h[ii] = 0.0
    chip_all = chip.copy()
    chip_all[ii] = True

    # ------------------------------------------------ to images (bottom-up), extended into the padding
    def to_img(vals, ch):
        a = np.zeros((H * W, ch), np.float32)
        a[idx] = vals.reshape(len(idx), ch)
        a = a.reshape(H, W, ch) if ch > 1 else a.reshape(H, W)
        return a

    out = {"albedo": to_img(alb, 3), "rough": to_img(rough, 1), "metal": to_img(metal, 1), "height": to_img(h, 1),
           "ao": ao, "cover": cover, "look": looks, "island": isl, "chip": to_img(chip_all.astype(np.float32), 1),
           "paint_mask": to_img((pm & ~chip_all).astype(np.float32), 1), "bevel_n": bk["normal"]}
    stats = {"chip_threshold": thr, "chipped_fraction_of_paint": float(chip[pm].mean()) if pm.any() else 0,
             "near_edge_bare_fraction": chip_near, "edge_weight": float(w_edge), "paint_texels": int(pm.sum()),
             "chip_core_fraction_of_chips": float(chip_core.sum() / max(chip.sum(), 1)),
             "paint_scratch_texels": int(len(ii)), "grime_blot_fraction_of_paint": float((blot[pm] > 0.5).mean()),
             "texels_covered": int(cover.sum())}
    return out, stats


def detail_normal(height, island, cover, ppmm_by_island: Dict[int, float]):
    """Tangent-space (OpenGL) normal from the height (mm), island-aware central differences."""
    H, W = height.shape
    kx = np.zeros((H, W), np.float32)
    for i, k in ppmm_by_island.items():
        kx[island == i] = k
    kx[kx == 0] = 1.0
    hl, hr = np.roll(height, 1, 1), np.roll(height, -1, 1)
    hd, hu = np.roll(height, 1, 0), np.roll(height, -1, 0)
    il, ir = np.roll(island, 1, 1), np.roll(island, -1, 1)
    idn, iup = np.roll(island, 1, 0), np.roll(island, -1, 0)
    same_l, same_r = (il == island), (ir == island)
    same_d, same_u = (idn == island), (iup == island)
    dx = np.where(same_l & same_r, (hr - hl) * 0.5, np.where(same_r, hr - height, np.where(same_l, height - hl, 0.0)))
    dy = np.where(same_d & same_u, (hu - hd) * 0.5, np.where(same_u, hu - height, np.where(same_d, height - hd, 0.0)))
    dhdu = dx * kx                                   # mm per mm
    dhdv = dy * kx
    n = np.stack([-dhdu, -dhdv, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[~cover] = (0, 0, 1)
    return n


def combine_normals(base_rgb, detail):
    """base: the bevel bake (OpenGL tangent, 0..1 encoded); detail: unit vectors.  UDN blend."""
    b = base_rgb * 2.0 - 1.0
    out = np.stack([b[..., 0] + detail[..., 0], b[..., 1] + detail[..., 1], b[..., 2]], -1)
    out /= np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-6)
    return out


__all__ = ["Look", "LOOK", "bake_inputs", "paint", "detail_normal", "combine_normals", "_grow", "fbm",
           "value_noise", "smoothstep", "strokes"]
