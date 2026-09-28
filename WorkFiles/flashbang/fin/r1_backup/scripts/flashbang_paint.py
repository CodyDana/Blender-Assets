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
    paint_lin: Tuple[float, float, float] = (0.080, 0.080, 0.038)     # olive (lit p50 71,71,54 in the reference)
    paint_mottle: float = 0.28
    paint_fine: float = 0.10
    paint_grime: float = 0.70
    paint_rough: float = 0.50
    chip_frac: float = 0.143           # spec 9
    chip_near_hole_frac: float = 0.577
    chip_steel_lin: Tuple[float, float, float] = (0.50, 0.45, 0.38)
    chip_dark_lin: Tuple[float, float, float] = (0.22, 0.19, 0.16)
    chip_rough: float = 0.55
    steel_lin: Tuple[float, float, float] = (0.085, 0.078, 0.070)
    steel_edge_lin: Tuple[float, float, float] = (0.62, 0.49, 0.36)
    steel_rough: float = 0.55
    steel_edge_rough: float = 0.38
    lever_lin: Tuple[float, float, float] = (0.15, 0.14, 0.13)
    ring_lin: Tuple[float, float, float] = (0.30, 0.28, 0.25)
    inner_lin: Tuple[float, float, float] = (0.05, 0.047, 0.043)
    brass_lin: Tuple[float, float, float] = (0.55, 0.41, 0.23)
    brass_rough: float = 0.28
    wall_lin: Tuple[float, float, float] = (0.42, 0.38, 0.32)
    edge_wear_steel: float = 0.95      # how much of the steel arrises go bright
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
    L = looks.ravel()[idx]
    e_s, e_l, a_o = es.ravel()[idx], el.ravel()[idx], ao.ravel()[idx]
    sd = look.seed
    r_xy = np.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]
    rng = np.random.default_rng(sd)

    # ------------------------------------------------ noise fields (3-D, seam-free)
    n_big = fbm(p, 9.0, 4, sd + 1)
    n_mid = fbm(p, 2.4, 4, sd + 2)
    n_fine = fbm(p, 0.45, 3, sd + 3)
    n_speck = value_noise(p, 0.18, sd + 4)
    n_grime = fbm(p, 5.0, 3, sd + 5)

    # distance-like hole-rim term on the painted tube: its own edge mask near a hole (the wall is LOOK 6)
    is_paint = (L == 0)
    is_wall = (L == 6)
    # zones (spec 9)
    zone = np.zeros(len(idx), np.float32)
    on_body = is_paint & (r_xy < spec.body_r + 0.05) & (z > spec.body_z0) & (z < spec.sleeve_z0 + 0.01)
    on_sleeve = is_paint & (z >= spec.sleeve_z0 - 0.01)
    for zl in spec.ring_lines_z:
        zone += 0.40 * np.exp(-((z - zl) / 0.30) ** 2) * on_body
    zone += 0.75 * smoothstep(spec.sleeve_z1 - 0.3, spec.sleeve_z1 + 0.8, z) * on_sleeve      # top chamfer: bare
    zone += 0.35 * np.exp(-((z - spec.sleeve_z0) / 0.7) ** 2) * is_paint                     # sleeve step
    zone += 0.30 * np.exp(-((z - spec.body_z0) / 1.6) ** 2) * on_body                        # body bottom
    # the score: edges dominate (hole rims, steps), patches from mid noise, flecks from fine noise
    pm = is_paint
    near = pm & (e_s > 0.45)
    n_fleck = value_noise(p, 0.32, sd + 11)
    base_sc = zone + 0.35 * (n_mid - 0.5) + 0.75 * (n_fine - 0.5) + 0.25 * (n_big - 0.5) + 0.55 * (n_speck > 0.95) + 0.5 * (n_fleck > 0.88)
    # the edge weight is solved so that, at the measured chipped fraction (spec 9: 14.3 % of the painted body),
    # the texels on an arris (hole rims, steps) are bare in the measured proportion (58 %)
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
    log(f"  chips: edge weight {w_edge:.2f}, threshold {thr:.3f}, chipped {chip[pm].mean():.3f} of paint, near-edge texels bare {chip_near:.3f}")

    # ------------------------------------------------ albedo, roughness, metallic, height
    alb = np.zeros((len(idx), 3), np.float32)
    rough = np.zeros(len(idx), np.float32)
    metal = np.zeros(len(idx), np.float32)
    h = np.zeros(len(idx), np.float32)
    # paint (luminance-only variation: Detail x Colour reproduces it exactly)
    pc = np.array(look.paint_lin, np.float32)
    lumf = (1.0 + look.paint_mottle * (n_big - 0.5) * 2.0 + look.paint_fine * (n_fine - 0.5) * 2.0)
    grime = np.clip((1.0 - a_o) * 1.6, 0, 1) * (0.55 + 0.9 * (n_grime - 0.5)) + 0.25 * zone * (n_mid < 0.45)
    lumf *= (1.0 - look.paint_grime * np.clip(grime, 0, 1))
    lumf *= (1.0 - 0.35 * smoothstep(0.56, 0.78, n_grime))                                  # grime blotches
    lumf *= np.where(n_speck < 0.05, 0.45, 1.0)                                              # dark flecks
    lumf *= np.where(value_noise(p, 1.1, sd + 12) < 0.12, 0.55, 1.0)                          # grime spots
    # a slight darkening right next to a chip (the paint edge's shadow line)
    edge_band = pm & ~chip & (score > thr - 0.07)
    lumf *= np.where(edge_band, 0.72, 1.0)
    alb[pm] = pc[None, :] * lumf[pm, None]
    rough[pm] = np.clip(look.paint_rough + 0.08 * (n_mid[pm] - 0.5) + 0.12 * grime[pm], 0.4, 0.9)
    h[pm] = 0.04 + 0.012 * (n_fine[pm] - 0.5) + 0.02 * (n_mid[pm] - 0.5)          # orange peel / dents
    # chips: bare steel (bright where fresh, darker where old)
    fresh = smoothstep(0.35, 0.75, n_mid + 0.35 * e_s)
    ccol = (np.array(look.chip_dark_lin)[None, :] * (1 - fresh[:, None]) + np.array(look.chip_steel_lin)[None, :] * fresh[:, None])
    ccol *= (0.85 + 0.3 * n_fine)[:, None]
    alb[chip] = ccol[chip]
    rough[chip] = np.clip(look.chip_rough + 0.12 * (0.5 - fresh[chip]) + 0.1 * (n_fine[chip] - 0.5), 0.25, 0.7)
    metal[chip] = 1.0
    h[chip] = 0.0
    # hole walls: cut steel, darker, a little paint lip at the outer edge is left to the chips' edge
    wc = np.array(look.wall_lin)[None, :] * (0.7 + 0.6 * n_mid[is_wall, None])
    alb[is_wall] = wc
    rough[is_wall] = 0.5
    metal[is_wall] = 1.0
    # steel families
    for lk, base, rgh in ((1, look.steel_lin, look.steel_rough), (4, look.lever_lin, 0.46), (5, look.ring_lin, 0.50),
                          (3, look.inner_lin, 0.6)):
        m = (L == lk)
        if not m.any():
            continue
        b = np.array(base, np.float32)[None, :]
        var = (0.75 + 0.5 * n_big[m] * n_mid[m] * 2.0 - 0.25)[:, None]
        col = b * np.clip(var, 0.5, 1.4)
        # antiqued: bright worn arrises + fine bright scratches, dark grime in the corners
        wear = np.clip(look.edge_wear_steel * (1.3 * e_s[m] + 0.4 * e_l[m]) * (0.55 + 0.9 * n_fine[m]) - 0.12, 0, 1)
        # antiqued: rubbed lighter patches and bright specks over the whole part (the reference's cap and fuze)
        wear = np.maximum(wear, 0.55 * smoothstep(0.62, 0.8, n_mid[m] * 0.6 + n_fine[m] * 0.6 - 0.1))
        wear = np.maximum(wear, 0.8 * (n_speck[m] > 0.955))
        if lk == 3:
            wear *= 0.2
        col = col * (1 - wear[:, None]) + np.array(look.steel_edge_lin)[None, :] * wear[:, None]
        g2 = np.clip((1.0 - a_o[m]) * 1.4, 0, 1)
        col *= (1.0 - 0.5 * g2)[:, None]
        alb[m] = col
        rough[m] = np.clip(rgh + 0.12 * (n_mid[m] - 0.5) - (rgh - look.steel_edge_rough) * wear + 0.15 * g2, 0.2, 0.85)
        metal[m] = 1.0
        # pits (small dents) on the cap and fuze
        pits = (value_noise(p[m], 0.35, sd + 9) > 0.93).astype(np.float32)
        h[m] -= 0.03 * pits
    # brass tube
    m = (L == 2)
    if m.any():
        b = np.array(look.brass_lin, np.float32)[None, :]
        tarn = 0.62 + 0.5 * n_big[m] + 0.15 * (n_fine[m] - 0.5)
        alb[m] = b * np.clip(tarn, 0.4, 1.1)[:, None]
        rough[m] = np.clip(look.brass_rough + 0.12 * (0.5 - n_big[m]), 0.2, 0.6)
        metal[m] = 1.0
        for zs in spec.tube_seam_z:
            g = np.exp(-((z[m] - zs) / 0.14) ** 2)
            alb[m] *= (1.0 - 0.6 * g)[:, None]
            h[m] -= 0.09 * g
    # ring lines (the paint is worn along them: the zone handles the chips; here the groove)
    for zl in spec.ring_lines_z:
        g = np.exp(-((z - zl) / (spec.ring_line_w * 0.5)) ** 2)
        lip = np.exp(-((z - zl - spec.ring_line_w * 0.7) / (spec.ring_line_w * 0.35)) ** 2)
        sel = on_body | (is_paint & (np.abs(z - zl) < 1.0))
        h[sel] += (-0.14 * g[sel] + 0.025 * lip[sel])
        alb[sel] *= (1.0 - 0.45 * g[sel])[:, None]
    # collar line and housing panel lines
    m = (L == 1)
    col_sel = m & (np.abs(r_xy - spec.collar_r) < 0.15) & (np.abs(z - spec.collar_groove_z) < 1.0)
    g = np.exp(-((z - spec.collar_groove_z) / 0.22) ** 2)
    h[col_sel] -= 0.12 * g[col_sel]
    hh = spec.housing_half
    in_house = m & (z > spec.housing_z0 + 0.8) & (z < spec.housing_z1 - 0.8)
    xface = in_house & (np.abs(np.abs(p[:, 0]) - hh) < 0.05)
    yface = in_house & (np.abs(np.abs(p[:, 1]) - hh) < 0.05)
    for yl in (-4.6, 4.6):
        g = np.exp(-((p[:, 1] - yl) / 0.2) ** 2)
        h[xface & (p[:, 0] < 0)] -= 0.15 * g[xface & (p[:, 0] < 0)]
        alb[xface & (p[:, 0] < 0)] *= (1 - 0.5 * g[xface & (p[:, 0] < 0)])[:, None]
    for xl in (-3.8,):
        g = np.exp(-((p[:, 0] - xl) / 0.2) ** 2)
        h[yface] -= 0.15 * g[yface]
        alb[yface] *= (1 - 0.5 * g[yface])[:, None]
    # scratches: thin 3-D line features (bands of a noise's level set), finer and denser on the lever face
    for lk, dens_, amp in ((0, 0.6, 1.0), (1, 0.6, 1.0), (4, 1.6, 1.0), (5, 0.5, 1.0)):
        m = (L == lk)
        if not m.any():
            continue
        for k, (sc_, ax) in enumerate(((3.0, (1.0, 0.35, 0.2)), (3.0, (-0.3, 1.0, 0.6)), (2.2, (0.4, -0.2, 1.0)))):
            q = p[m] * np.array(ax, np.float32)[None, :] * np.array([1.0, 1.0, 0.18])[None, :]
            f = fbm(q, sc_, 2, sd + 40 + 7 * k + lk)
            line = np.exp(-((f - 0.5) / (0.0022 * dens_)) ** 2) * (value_noise(p[m], 6.0, sd + 60 + k) > 0.55)
            line = line * amp
            h[m] -= 0.015 * line
            if lk == 0:
                # a scratch through paint shows steel only where it is deep: darken + slight lift
                alb[m] *= (1.0 - 0.25 * line)[:, None]
            else:
                bright = np.array(look.steel_edge_lin)[None, :]
                alb[m] = alb[m] * (1 - 0.35 * line[:, None]) + bright * 0.35 * line[:, None]
                rough[m] = rough[m] - 0.1 * line
    if (L == 4).any():                        # the lever face's fine cross-hatch (v4)
        m = (L == 4)
        u1 = (p[m, 1] + p[m, 2]) / 0.9
        u2 = (p[m, 1] - p[m, 2]) / 0.9
        hatch = (np.abs(np.sin(u1 * math.pi)) ** 18 + np.abs(np.sin(u2 * math.pi)) ** 18) * \
                (0.4 + 0.6 * (value_noise(p[m], 2.0, sd + 77) > 0.4))
        alb[m] *= (1.0 + 0.35 * hatch)[:, None]
        h[m] -= 0.008 * hatch

    # ------------------------------------------------ to images (bottom-up), extended into the padding
    def to_img(vals, ch):
        a = np.zeros((H * W, ch), np.float32)
        a[idx] = vals.reshape(len(idx), ch)
        a = a.reshape(H, W, ch) if ch > 1 else a.reshape(H, W)
        return a

    out = {"albedo": to_img(alb, 3), "rough": to_img(rough, 1), "metal": to_img(metal, 1), "height": to_img(h, 1),
           "ao": ao, "cover": cover, "look": looks, "island": isl, "chip": to_img(chip.astype(np.float32), 1),
           "paint_mask": to_img((pm & ~chip).astype(np.float32), 1), "bevel_n": bk["normal"]}
    stats = {"chip_threshold": thr, "chipped_fraction_of_paint": float(chip[pm].mean()) if pm.any() else 0,
             "near_edge_bare_fraction": chip_near, "edge_weight": float(w_edge), "paint_texels": int(pm.sum()),
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
           "value_noise", "smoothstep"]
