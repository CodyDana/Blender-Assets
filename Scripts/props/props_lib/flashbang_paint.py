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
    """ROUND 2 (the blind tells + the reference's micro-texture, studied at 4-5x in WorkFiles/flashbang/r2/look/):
    glossier olive paint with a hammered / leathery surface that shows in the highlight; small dark brown-black grime
    specks and smudges (no large camouflage blotches); chips with a dark oxidised core and a thin light tan-bronze
    rim; a ragged bare-metal ring round every hole; light tan lips on the ring-line grooves; darker antiqued steel with
    scattered bright bronze specks and broken bright arrises; a mid-grey etched lever (mottled light swirls, a faint
    irregular diamond stamp); pitted grimy brass with vertical scratches and no painted shoulder band (it is geometry)."""
    paint_lin: Tuple[float, float, float] = (0.080, 0.080, 0.038)     # olive (lit p50 71,71,54 in the reference)
    paint_mottle: float = 0.10          # ROUND 2b: 0.22 read as grey camouflage blotches (the reference is even)
    paint_fine: float = 0.10
    paint_hammer: float = 0.10          # albedo response of the hammered texture
    paint_hammer_h: float = 0.09        # its height (mm): the leathery sheen in the highlight
    paint_grime: float = 0.75          # ROUND 2b: darker rim grime (paint p10 ~10 levels high)
    paint_rough: float = 0.36           # ROUND 2: glossier (0.46): the reference's highlight stripe (paint p90)
    chip_frac: float = 0.143            # spec 9
    chip_near_hole_frac: float = 0.577
    chip_core_lin: Tuple[float, float, float] = (0.030, 0.024, 0.018)  # oxidised dark brown-black steel (sRGB ~45)
    chip_edge_lin: Tuple[float, float, float] = (0.30, 0.22, 0.14)    # light tan-bronze rim (sRGB ~140)
    rim_lin: Tuple[float, float, float] = (0.28, 0.23, 0.17)           # the ragged bare rim round the holes
    steel_lin: Tuple[float, float, float] = (0.048, 0.044, 0.040)      # dark antiqued steel (housing p50 42-50)
    cap_lin: Tuple[float, float, float] = (0.066, 0.060, 0.052)       # the cap reads lighter (cap p90 65-79)
    steel_edge_lin: Tuple[float, float, float] = (0.46, 0.37, 0.26)
    bronze_lin: Tuple[float, float, float] = (0.36, 0.27, 0.17)        # the bright bronze specks
    steel_rough: float = 0.46
    steel_edge_rough: float = 0.30
    lever_lin: Tuple[float, float, float] = (0.046, 0.044, 0.041)      # ROUND 2b: darker (0.058 read light grey, v4)
    ring_lin: Tuple[float, float, float] = (0.050, 0.047, 0.043)       # darker antiqued ring wire (sRGB ~60-75 lit)
    inner_lin: Tuple[float, float, float] = (0.018, 0.017, 0.016)
    brass_lin: Tuple[float, float, float] = (0.36, 0.27, 0.155)       # less saturated (ref lit p50 79,65,44)
    brass_rough: float = 0.32          # ROUND 2b: glossier - the reference's tube shows the strip lights as
                                        # vertical highlight bands (0.48 read as a matte, blotchy capsule)
    wall_lin: Tuple[float, float, float] = (0.040, 0.036, 0.032)       # hole walls: dark cut steel, grimy
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
    """Compose linear albedo, roughness, metallic, height (mm) from the bakes.  Arrays bottom-up (v up).  ROUND 2."""
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
    th = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
    NT = len(idx)

    # ------------------------------------------------ noise fields (3-D, seam-free)
    n_big = fbm(p, 9.0, 4, sd + 1)
    n_mid = fbm(p, 2.4, 4, sd + 2)
    n_fine = fbm(p, 0.45, 3, sd + 3)
    n_speck = value_noise(p, 0.18, sd + 4)
    n_grime = fbm(p, 2.2, 3, sd + 5)              # small grime smudges (1-4 mm), not camouflage blotches
    n_chip = fbm(p, 1.0, 3, sd + 6)               # chip outlines 0.5-3 mm
    n_ham = 0.55 * value_noise(p, 0.42, sd + 7) + 0.45 * value_noise(p, 0.21, sd + 8)   # hammered paint
    n_dash = value_noise(p, 1.6, sd + 31)         # breaks every bright arris into dashes
    n_br = value_noise(p, 0.26, sd + 32)          # bronze specks
    n_cl = fbm(p, 3.5, 2, sd + 33)                # their clusters

    is_paint = (L == 0)
    is_wall = (L == 6)
    pm = is_paint
    on_body = is_paint & (r_xy < spec.body_r + 0.05) & (r_xy > spec.body_r - 0.6) & (z > spec.body_z0) & \
        (z < spec.sleeve_z0 + 0.01)
    on_sleeve = is_paint & (z >= spec.sleeve_z0 - 0.01)
    on_chamfer = on_sleeve & (z > spec.sleeve_z1 - 0.05)

    # distance (mm) from each body texel to the nearest hole edge (the ellipse in the unrolled surface)
    a_mm = spec.body_r * math.radians(spec.hole_ang_w_deg / 2.0)
    b_mm = spec.hole_h / 2.0
    d_hole = np.full(NT, 99.0, np.float32)
    bi = np.nonzero(on_body | (is_wall))[0]
    for hc in spec.hole_thetas():
        du = ((th[bi] - hc + 180.0) % 360.0 - 180.0) * math.pi / 180.0 * spec.body_r
        for zc in spec.hole_rows_z:
            dv = z[bi] - zc
            rho = np.sqrt((du / a_mm) ** 2 + (dv / b_mm) ** 2)
            # radial distance along the ellipse ray (scaled by the local radius)
            loc = np.sqrt((du / np.maximum(rho, 1e-6)) ** 2 + (dv / np.maximum(rho, 1e-6)) ** 2)
            d_hole[bi] = np.minimum(d_hole[bi], (rho - 1.0) * loc)
    d_line = np.min(np.abs(z[:, None] - np.array(spec.ring_lines_z)[None, :]), axis=1)

    # ------------------------------------------------ chips (bare metal): zones + noise, calibrated to spec 9
    zone = np.zeros(NT, np.float32)
    zone += 0.45 * np.exp(-(np.maximum(d_hole, 0.0) / 0.9) ** 2) * on_body          # hole rims
    zone += 0.55 * np.exp(-(np.maximum(d_line - spec.groove_w, 0.0) / 0.8) ** 2) * on_body   # the groove lips
    zone += 0.55 * np.exp(-((z - spec.sleeve_z0) / 0.9) ** 2) * is_paint              # sleeve step
    zone += 0.40 * np.exp(-((z - spec.body_z0) / 1.8) ** 2) * on_body                 # body bottom
    zone += 0.25 * on_chamfer                                                         # 2b: 0.42 read as a chrome band (p1)
    zone += 0.20 * smoothstep(spec.sleeve_z1 - 1.5, spec.sleeve_z1, z) * on_sleeve     # the chamfer's lower edge
    near = pm & (d_hole < 0.75) & on_body
    n_tiny = value_noise(p, 0.45, sd + 34)
    base_sc = (zone + 0.55 * (n_chip - 0.5) + 0.25 * (n_mid - 0.5) + 0.15 * (n_big - 0.5)
               + 0.30 * (n_speck > 0.975) + 0.60 * smoothstep(0.80, 0.90, n_tiny))       # 2b: 0.45
    best = None
    for w_e in np.linspace(0.0, 1.2, 25):
        sc_ = base_sc + w_e * e_s
        t_ = float(np.quantile(sc_[pm], 1.0 - look.chip_frac))
        f_ = float((sc_[near] > t_).mean()) if near.any() else 0.0
        if best is None or abs(f_ - look.chip_near_hole_frac) < abs(best[2] - look.chip_near_hole_frac):
            best = (w_e, t_, f_)
    w_edge, thr, chip_near = best
    score = base_sc + w_edge * e_s
    chip = pm & (score > thr)
    log(f"  chips: edge weight {w_edge:.2f}, threshold {thr:.3f}, chipped {chip[pm].mean():.3f} of paint, "
        f"near-edge texels bare {chip_near:.3f}")
    # a chip's thin light rim (the paint's broken edge catching light) round a dark oxidised core: erode 2 texels
    chip_img = np.zeros(H * W, bool)
    chip_img[idx] = chip
    chip_img = chip_img.reshape(H, W)
    core_img = _erode(chip_img, 2)
    chip_core = core_img.ravel()[idx] & chip
    chip_edge = chip & ~chip_core
    # the ragged bare ring round every hole (0.3-1.1 mm, noise-driven), part of the chips
    rim = on_body & (d_hole < 0.30 + 0.80 * n_fine * (0.5 + n_mid)) & (d_hole > -1.0)
    chip = chip | rim

    # ------------------------------------------------ albedo, roughness, metallic, height
    alb = np.zeros((NT, 3), np.float32)
    rough = np.zeros(NT, np.float32)
    metal = np.zeros(NT, np.float32)
    h = np.zeros(NT, np.float32)
    # grime: small dark smudges collecting at the rims, groove lips, the bottom and the step; cavity grime from AO
    gzone = np.clip(1.2 * np.exp(-(np.maximum(d_hole, 0) / 2.0) ** 2) + np.exp(-(d_line / 2.5) ** 2)
                    + np.exp(-((z - spec.body_z0) / 5.0) ** 2) + 0.6 * np.exp(-((z - spec.sleeve_z0) / 2.0) ** 2),
                    0, 1.5)
    smudge = smoothstep(0.62, 0.76, n_grime + 0.16 * gzone) * (0.5 + 0.8 * n_fine)   # 2b: small smudges at the rims
    cav = np.clip((1.0 - a_o) * 1.5, 0, 1) * (0.5 + 0.8 * (n_mid - 0.5) + 0.3)
    grime = np.clip(np.maximum(smudge, cav), 0, 1)
    # paint (luminance-only variation: Detail x Colour == BC)
    pc = np.array(look.paint_lin, np.float32)
    lumf = (1.0 + look.paint_mottle * (n_big - 0.5) * 2.0 + look.paint_fine * (n_fine - 0.5) * 2.0
            + look.paint_hammer * (n_ham - 0.5) * 2.0)
    lumf *= (1.0 - look.paint_grime * grime)
    lumf *= np.where(n_speck < 0.09, 0.40, 1.0)                                               # dark specks (2b: 0.06)
    # ROUND 2b: the reference's scattered dark flecks (0.4-1.5 mm, all over the paint, not only at the edges)
    n_fl = value_noise(p, 0.80, sd + 36) * 0.7 + 0.3 * n_fine
    lumf *= np.where(n_fl < 0.28, 0.36, 1.0)
    lumf *= 1.0 - 0.10 * smoothstep(0.55, 0.30, fbm(p, 1.2, 2, sd + 35))                       # darker mottle (2b: 0.25)
    edge_band = pm & ~chip & (score > thr - 0.05)
    lumf *= np.where(edge_band, 0.72, 1.0)                                                  # paint lip shadow
    # light hairline scuffs in the paint (the reference's fine light scratches), still paint (dielectric)
    scuff = strokes(p, n, 1.6, 0.70, (0.6, 2.8), 0.03, sd + 501)
    lumf *= 1.0 + 0.60 * scuff * (1.0 - grime)
    lumf = np.clip(lumf, 0.22, 2.1)                   # dielectric paint luminance stays < 0.18 (gate 12)
    alb[pm] = pc[None, :] * lumf[pm, None]
    rough[pm] = np.clip(look.paint_rough + 0.07 * (n_mid[pm] - 0.5) + 0.06 * (n_ham[pm] - 0.5) + 0.22 * grime[pm],
                        0.22, 0.75)
    h[pm] = 0.06 + look.paint_hammer_h * (n_ham[pm] - 0.5) + 0.012 * (n_fine[pm] - 0.5) - 0.012 * scuff[pm]
    # chips: dark oxidised core (brown), thin light tan-bronze rim; the hole rims bright bare steel
    brown = np.array([0.050, 0.034, 0.021], np.float32)
    core = (np.array(look.chip_core_lin)[None, :] * (1 - 0.5 * n_mid[:, None]) + brown[None, :] * 0.5 * n_mid[:, None])
    core *= (0.8 + 0.5 * n_fine)[:, None]
    edge = np.array(look.chip_edge_lin)[None, :] * (0.65 + 0.7 * n_mid)[:, None]
    alb[chip_core] = core[chip_core]
    alb[chip_edge] = edge[chip_edge]
    rc = np.array(look.rim_lin)[None, :] * (0.6 + 0.8 * n_fine * n_mid * 2.0)[:, None]
    rimc = rim & ~chip_core
    alb[rimc] = rc[rimc] * (1.0 - 0.35 * grime[rimc, None])
    rough[chip_core] = np.clip(0.55 + 0.1 * (n_fine[chip_core] - 0.5), 0.45, 0.75)
    rough[chip_edge | rimc] = 0.32
    metal[chip] = 1.0
    h[chip] = 0.0
    # steel families: dark antiqued base, oxidised darker patches, BROKEN bright arrises (thin bevel only, in
    # dashes), bright bronze specks in clusters, fine light scratches, grime in the corners
    is_cap = (L == 1) & (z < spec.body_z0 + 0.3)
    for lk, base, rgh in ((1, look.steel_lin, look.steel_rough), (4, look.lever_lin, 0.42),
                          (5, look.ring_lin, 0.30), (3, look.inner_lin, 0.6), (6, look.wall_lin, 0.55)):
        m = (L == lk)
        if not m.any():
            continue
        b = np.tile(np.array(base, np.float32)[None, :], (int(m.sum()), 1))
        if lk == 1:
            b[is_cap[m]] = np.array(look.cap_lin, np.float32)
        var = np.clip(0.62 + 0.75 * n_big[m] * n_mid[m] * 2.0 - 0.25 + 0.25 * (n_fine[m] - 0.5), 0.45, 1.4)
        col = b * var[:, None]
        dash = smoothstep(0.22, 0.45, n_dash[m])                # ROUND 2b: longer bright runs (0.30-0.55)
        wear = np.clip(2.0 * e_s[m] * (0.6 + 0.8 * n_fine[m]) - 0.12, 0, 1) * dash   # 2b: crisper arrises
        if lk == 5:
            # the ring: bright wear only on the OUTER arc of the loop
            from .flashbang_geom import ring_frame
            _top, xdir, zdir, c = ring_frame(spec)                  # ROUND 2: the fitted ring pose
            nplane = np.cross(xdir, zdir)
            v = p[m] - c
            rp = v - (v @ nplane)[:, None] * nplane[None, :]
            rd = rp / np.maximum(np.linalg.norm(rp, axis=1, keepdims=True), 1e-6)
            outer = np.clip(((n[m] * rd).sum(1) - 0.45) / 0.4, 0, 1) * (np.linalg.norm(v, axis=1) > 12.0)
            wear = np.maximum(wear, outer * smoothstep(0.35, 0.65, n_dash[m]) * 0.75)
        scr = np.zeros(int(m.sum()), np.float32)
        if lk in (1, 4, 5):
            scr = strokes(p[m], n[m], 1.0, 0.32, (0.5, 2.2), 0.026, sd + 300 + lk)     # ROUND 2b: 0.70 density
            wear = np.maximum(wear, 0.30 * scr * (0.5 + n_mid[m]))                     # and 0.55: 'white hairs'
            # bronze specks, clustered (the cap and housing's bright dots)
            spk = (n_br[m] > np.where(is_cap[m], 0.84, 0.90)) & (n_cl[m] > np.where(is_cap[m], 0.30, 0.40))
            wear = np.maximum(wear, 0.85 * spk)
        if lk == 1:
            # ROUND 2b: the cap's top chamfer (up-facing, just under the body) worn to a broken bright bronze line
            # (v1-v4 and p3 show it as the cap's brightest edge; its wide bevel has no sharp arris for e_s to find)
            ctop = is_cap[m] & (n[m, 2] > 0.35) & (z[m] > spec.cap_side_z1 - 0.3) & (z[m] < spec.cap_side_z1 + 0.7)
            wear = np.maximum(wear, ctop * smoothstep(0.35, 0.6, n_dash[m]) * (0.3 + 0.5 * n_fine[m]))
        if lk in (3, 6):
            wear *= 0.35
        ecol = np.array(look.steel_edge_lin)[None, :] * (0.6 + 0.7 * n_mid[m])[:, None]
        if lk in (1, 4, 5):
            bz = np.array(look.bronze_lin)[None, :] * (0.7 + 0.6 * n_fine[m])[:, None]
            ecol = np.where((n_br[m] > 0.9)[:, None], bz, ecol)
        col = col * (1 - wear[:, None]) + ecol * wear[:, None]
        g2 = np.clip(np.maximum(np.clip((1.0 - a_o[m]) * 1.3, 0, 1), 0.6 * smudge[m]), 0, 1)
        col *= (1.0 - 0.45 * g2)[:, None]
        col = col * (1.0 - 0.25 * g2[:, None]) + brown[None, :] * 0.25 * g2[:, None] * (col.mean(1, keepdims=True) / 0.05)
        alb[m] = col
        rgh_m = np.where(is_cap[m], rgh + 0.10, rgh) if lk == 1 else rgh
        rough[m] = np.clip(rgh_m + 0.10 * (n_mid[m] - 0.5) - (rgh_m - look.steel_edge_rough) * wear + 0.15 * g2,
                           0.18, 0.85)
        metal[m] = 1.0
        pits = (value_noise(p[m], 0.35, sd + 9) > 0.93).astype(np.float32)
        h[m] -= 0.03 * pits
        h[m] -= 0.02 * scr
    # the hole walls' outer lip: the cut edge, bright and ragged (the wall texels within ~0.6 mm of the outside)
    m = is_wall & (r_xy > spec.body_r - 0.35 - 0.5 * n_fine)
    alb[m] = np.array(look.rim_lin)[None, :] * (0.55 + 0.7 * n_mid[m])[:, None]
    rough[m] = 0.34
    # the lever: an ETCHED mid-grey face - mottled light swirls (a warped value-noise iso-band) and larger light
    # patches, a faint diamond stamp that is broken and irregular (pitch and angle wander), bright flange arrises
    m = (L == 4)
    if m.any():
        pw = p[m] + 1.2 * np.stack([fbm(p[m], 2.0, 2, sd + 81) - 0.5, fbm(p[m], 2.0, 2, sd + 82) - 0.5,
                                    fbm(p[m], 2.0, 2, sd + 83) - 0.5], 1)
        swirl = np.exp(-((value_noise(pw, 1.3, sd + 84) - 0.5) / 0.035) ** 2)
        patch = smoothstep(0.55, 0.75, fbm(p[m], 2.6, 3, sd + 85))
        y_, z_ = pw[:, 1], pw[:, 2]
        hat = np.zeros(int(m.sum()), np.float32)
        web = np.abs(n[m, 1]) < 0.5
        for sg in (-1.0, 1.0):
            a = math.radians(38.0)
            w_ = -math.cos(a) * y_ * sg + math.sin(a) * z_
            pit = 1.6 * (1.0 + 0.18 * (fbm(p[m], 3.0, 2, sd + 78 + int(sg)) - 0.5))   # ROUND 2b: the pitch wanders
            f = w_ / pit - np.round(w_ / pit)
            hat = np.maximum(hat, np.exp(-((f * pit) / 0.16) ** 2))
        hat *= smoothstep(0.45, 0.72, value_noise(p[m], 2.4, sd + 77)) * web * (0.5 + 0.5 * n_fine[m])
        lite = np.array([0.115, 0.107, 0.095], np.float32)[None, :]
        k_ = np.clip(0.32 * swirl + 0.25 * patch + 0.22 * hat, 0, 1)[:, None] * (0.6 + 0.6 * n_mid[m, None])
        alb[m] = alb[m] * (1 - k_) + lite * k_
        rough[m] = np.clip(rough[m] - 0.06 * k_[:, 0], 0.18, 0.85)
        h[m] -= 0.02 * hat + 0.015 * swirl
    # brass cans: pitted, grimy, vertical scratches, grime in the lower third of each window; the seam and the
    # shoulder are GEOMETRY now (a dark line only at the seam, no painted light band)
    m = (L == 2)
    if m.any():
        b = np.array(look.brass_lin, np.float32)[None, :]
        tarn = 0.80 + 0.30 * (n_big[m] - 0.5) * 2 + 0.15 * (n_fine[m] - 0.5)
        col = b * np.clip(tarn, 0.45, 1.1)[:, None]
        vs = strokes(p[m], n[m], 1.2, 0.75, (2.0, 8.0), 0.04, sd + 401, vertical=0.9)
        col *= (1.0 + 0.45 * vs)[:, None]
        col *= (1.0 - 0.30 * strokes(p[m], n[m], 1.0, 0.6, (1.5, 6.0), 0.05, sd + 404, vertical=0.95))[:, None]
        pit = value_noise(p[m], 0.22, sd + 402) > 0.88
        col[pit] *= 0.65
        dk = smoothstep(0.58, 0.74, fbm(p[m], 1.4, 3, sd + 403))            # dark tarnish smudges
        col *= (1.0 - 0.30 * dk)[:, None]                                   # 2b: 0.55 read as round blotches
        zc = np.array(sorted(spec.hole_rows_z))
        dzr = z[m] - zc[np.argmin(np.abs(z[m][:, None] - zc[None, :]), axis=1)]
        low = smoothstep(-2.0, -8.5, dzr) * (0.6 + 0.6 * n_mid[m])
        col *= (1.0 - 0.45 * np.clip(low, 0, 1))[:, None]
        rgh = np.clip(look.brass_rough + 0.08 * (n_big[m] - 0.5) + 0.10 * np.clip(low, 0, 1) + 0.10 * dk - 0.08 * vs,
                      0.18, 0.60)
        hh = np.zeros(int(m.sum()), np.float32)
        for zs in spec.tube_seam_z:
            g = np.exp(-((z[m] - zs - 0.45) / 0.30) ** 2)             # ROUND 2b: the dark band just above the lip
            col *= (1.0 - 0.45 * g)[:, None]
            hh += -0.05 * g
        col *= (0.80 + 0.20 * a_o[m])[:, None]
        # the lower tube's top edge (the step, facing up) and the top of each window read dark, not a lit band
        # ROUND 2b: the thin dark vertical line down the middle of every window (the reference's 4x crops and p4: the
        # tube's vertical seam), which also breaks the lit tube's 'egg' read
        dth = np.min(np.abs(((th[m][:, None] - np.array(spec.hole_thetas())[None, :]) + 180.0) % 360.0 - 180.0), axis=1)
        vline = np.exp(-((np.radians(dth) * spec.inner_tube_r) / 0.30) ** 2) * (0.7 + 0.3 * n_fine[m])
        col *= (1.0 - 0.55 * vline)[:, None]
        # ROUND 2b: the ledge (up-facing) half-darkened (a thin line, not a bright band); the window tops a little
        col[n[m, 2] > 0.6] *= 0.55
        high = smoothstep(2.0, 8.5, dzr)
        col *= (1.0 - 0.15 * high)[:, None]
        alb[m] = col
        rough[m] = rgh
        metal[m] = 1.0
        h[m] = hh - 0.02 * pit - 0.01 * vs
    # ring lines: the groove (geometry at LOD0) darker with grime, its lips light where the paint wore through
    for zl in spec.ring_lines_z:
        g = np.exp(-((z - zl) / 0.30) ** 2)
        sel = on_body & ~chip
        alb[sel] *= (1.0 - 0.30 * g[sel])[:, None]                # ROUND 2b: 0.55 read as a thick dark line
    # scratches through the paint to the metal: thin light strokes, a few
    sp = pm & ~chip
    scr_p = strokes(p[sp], n[sp], 4.0, 0.30, (2.0, 8.0), 0.05, sd + 500)
    hit = scr_p > 0.5
    ii = np.nonzero(sp)[0][hit]
    alb[ii] = np.array(look.chip_edge_lin)[None, :] * 0.8
    metal[ii] = 1.0
    rough[ii] = 0.34
    h[ii] = 0.0
    chip_all = chip.copy()
    chip_all[ii] = True
    # the ring-line grooves' LIPS: the paint worn through along both edges (a broken light tan line, v2 / p2)
    lipm = on_body & (np.abs(d_line - (spec.groove_w + 0.10)) < 0.10) & (n_dash > 0.45) & (n_fine > 0.35)
    alb[lipm] = np.array(look.rim_lin)[None, :] * (0.55 + 0.7 * n_mid[lipm])[:, None]
    metal[lipm] = 1.0
    rough[lipm] = 0.32
    h[lipm] = 0.0
    chip_all |= lipm

    # ------------------------------------------------ to images (bottom-up), extended into the padding
    def to_img(vals, ch):
        a = np.zeros((H * W, ch), np.float32)
        a[idx] = vals.reshape(len(idx), ch)
        a = a.reshape(H, W, ch) if ch > 1 else a.reshape(H, W)
        return a

    out = {"albedo": to_img(alb, 3), "rough": to_img(rough, 1), "metal": to_img(metal, 1), "height": to_img(h, 1),
           "ao": ao, "cover": cover, "look": looks, "island": isl, "chip": to_img(chip_all.astype(np.float32), 1),
           "paint_mask": to_img((pm & ~chip_all).astype(np.float32), 1), "bevel_n": bk["normal"]}
    body_band = on_body & (z > 30.0) & (z < 105.0)
    stats = {"chip_threshold": thr, "chipped_fraction_of_paint": float(chip[pm].mean()) if pm.any() else 0,
             "near_edge_bare_fraction": chip_near, "edge_weight": float(w_edge), "paint_texels": int(pm.sum()),
             "chip_core_fraction_of_chips": float(chip_core.sum() / max(chip.sum(), 1)),
             "hole_rim_bare_texels": int(rim.sum()),
             "paint_scratch_texels": int(len(ii)), "grime_smudge_fraction_of_paint": float((smudge[pm] > 0.5).mean()),
             "bright_bare_fraction_body_band": float((chip_all & body_band & (alb @ np.array([0.2126, 0.7152, 0.0722])
                                                                              > 0.12)).sum() / max(body_band.sum(), 1)),
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
