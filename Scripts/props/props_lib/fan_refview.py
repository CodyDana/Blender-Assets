#!/usr/bin/env python
"""props_lib.fan_refview - REFERENCE_SPEC 1's fan2 camera, the reference-view render and the fidelity
instruments (bpy for the render, numpy for the metrics).

CAMERA (RS 1, "Blender recipe"): 800 x 800, sensor fit horizontal 36 mm, lens 46.4 mm, shift 0.  The fan
goes from the build frame (XY plane, +Z front, stick_00 along +X) to RS's frame by:
    turn 9.4 deg about the build Z (the front guard's axis lands at image angle 9.4, the bisector at 91.0 =
    RS's +1.0 deg roll), map build (x, y, z) -> world (x, -z, y) (fan in XZ, front face toward -Y), then tilt
    11.5 deg about world X with the top going to +Y (away from the camera); camera level at
    (0.006, -3.0, 0.4246) L looking along +Y.  The rivet then projects to (398.2, 547.0) px (asserted).
LIGHT: a product shot - a broad soft key above and in front, a soft fill, a white environment; the levels
were set by measuring the render against RS 7 / RS 9 (lit and unlit faces, ribs), not by eye.
BACKDROP: the render has a transparent film and is composited over RS 0's uniform stored grey 0.9647;
fan2's soft ground shadow is not part of the asset and is not added.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .fan_spec import D2R, FAN, FanSpec

BACKDROP_STORED = 0.9647
RES = (800, 800)
LENS_MM = 46.4
SENSOR_MM = 36.0
TILT_DEG = 11.5
ROLL_TO_DEG = 9.4
CAM_L = (0.006, -3.0, 0.4246)
RIVET_PX = (398.2, 547.0)
#: (name, direction in the RS world frame, size x L, energy W, colour); the fan is ~0.38 m across
REF_LIGHTS = [
    # fitted on RS 7 / RS 9's tones (leaf p10/p50/p90, bare ribs, lobe; WorkFiles/fan/build_dev/exp/tune_light.py):
    # a big soft key above the camera, a faint front fill, a near-black studio (the camera side reflects dark)
    ("Key", (0.0, -0.4, 1.0), 3.0, 3.2, (1.0, 1.0, 1.0)),
    ("Fill", (0.0, -1.0, 0.2), 3.0, 0.12, (1.0, 1.0, 1.0)),
]
REF_WORLD = 0.03


def placement(spec: FanSpec = FAN) -> np.ndarray:
    """4x4 (metres): build frame -> RS world frame."""
    a = ROLL_TO_DEG * D2R
    Rz = np.array([[math.cos(a), -math.sin(a), 0, 0], [math.sin(a), math.cos(a), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
    Map = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    t = -TILT_DEG * D2R
    Rx = np.array([[1, 0, 0, 0], [0, math.cos(t), -math.sin(t), 0], [0, math.sin(t), math.cos(t), 0], [0, 0, 0, 1.0]])
    return Rx @ Map @ Rz


def camera_matrix(spec: FanSpec = FAN) -> np.ndarray:
    L = spec.L * 0.001
    M = np.eye(4)
    # a Blender camera looks down its -Z with +Y up: level, looking along world +Y
    M[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float64)
    M[:3, 3] = np.array(CAM_L) * L
    return M


def project(points_world_m: np.ndarray, spec: FanSpec = FAN) -> np.ndarray:
    """Pinhole projection with the RS camera -> pixel (x right, y down)."""
    C = camera_matrix(spec)
    Rinv = C[:3, :3].T
    p = (np.asarray(points_world_m) - C[:3, 3]) @ Rinv.T
    f_px = LENS_MM / SENSOR_MM * RES[0]
    x = RES[0] / 2 + f_px * p[:, 0] / (-p[:, 2])
    y = RES[1] / 2 - f_px * p[:, 1] / (-p[:, 2])
    return np.stack([x, y], 1)


def rivet_check(spec: FanSpec = FAN) -> Dict[str, float]:
    P = placement(spec)
    px = project(P[:3, 3][None], spec)[0]
    return {"rivet_px": [round(float(px[0]), 2), round(float(px[1]), 2)], "expected_px": list(RIVET_PX),
            "error_px": round(float(np.hypot(px[0] - RIVET_PX[0], px[1] - RIVET_PX[1])), 3)}


# =========================================================================== render (bpy)
def render_reference(objects, spec: FanSpec, work: Path, out_png: Path, samples: int = 256, movers=None,
                     extra_objects=()):
    import bpy
    from mathutils import Matrix, Vector
    from . import fan_look as LK
    scene = bpy.context.scene
    LK._cycles(scene, samples, denoise=False)
    scene.cycles.filter_width = 1.5          # round 2: Blender's default (1.0 read as stair-stepped edges)
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    coll = bpy.data.collections.new("FAN_REFERENCE_RIG")
    scene.collection.children.link(coll)
    cd = bpy.data.cameras.new("FanRefCam")
    cd.lens = LENS_MM
    cd.sensor_width = SENSOR_MM
    cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.02
    cd.clip_end = 20.0
    co = bpy.data.objects.new("FanRefCam", cd)
    coll.objects.link(co)
    co.matrix_world = Matrix(camera_matrix(spec).tolist())
    scene.camera = co
    L = spec.L * 0.001
    lamps = []
    for name, d, size, energy, col in REF_LIGHTS:
        ld = bpy.data.lights.new("FanRef_" + name, "AREA")
        ld.shape = "DISK"
        ld.size = size * L
        ld.energy = energy
        ld.color = col
        lo = bpy.data.objects.new("FanRef_" + name, ld)
        coll.objects.link(lo)
        v = Vector(d).normalized()
        lo.location = v * 4.0 * L + Vector((0, 0, 0.3 * L))
        lo.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
        lamps.append(lo)
    wd = bpy.data.worlds.new("FanRefWorld")
    wd.use_nodes = True
    bg = next(n for n in wd.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = REF_WORLD
    saved_world = scene.world
    scene.world = wd
    place = Matrix(placement(spec).tolist())
    movers = list(movers) if movers else list(objects)
    saved_M = [(o, o.matrix_world.copy()) for o in movers]
    for o, M in saved_M:
        o.matrix_world = place @ M
    for o in extra_objects:
        pass
    bpy.context.view_layer.update()
    saved = LK.hide_all_but(list(objects) + list(extra_objects))
    try:
        a = LK.render_exr(Path(work) / "fan_reference_view.exr")
    finally:
        LK.restore(saved)
        for o, M in saved_M:
            o.matrix_world = M
        scene.world = saved_world
        for o in list(coll.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            for lib in (bpy.data.cameras, bpy.data.lights):
                try:
                    lib.remove(data)
                    break
                except Exception:
                    pass
        bpy.data.collections.remove(coll)
        bpy.data.worlds.remove(wd)
    stored = LK.composite_over(a, BACKDROP_STORED)
    LK.write_png(out_png, stored)
    return {"png": str(out_png), "alpha": a[..., 3], "linear": a[..., :3]}


# =========================================================================== fidelity (numpy)
LUMA = np.array([0.2126, 0.7152, 0.0722])


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """Holes = background components not touching the border (4-connected flood fill from the border)."""
    H, W = mask.shape
    bg = ~mask
    reach = np.zeros_like(bg)
    reach[0, :] = bg[0, :]
    reach[-1, :] = bg[-1, :]
    reach[:, 0] = bg[:, 0]
    reach[:, -1] = bg[:, -1]
    for _ in range(4000):
        grown = reach.copy()
        grown[1:, :] |= reach[:-1, :]
        grown[:-1, :] |= reach[1:, :]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= bg
        if (grown == reach).all():
            break
        reach = grown
    return mask | (bg & ~reach)


def photo_mask(stored_rgb: np.ndarray) -> np.ndarray:
    lum = stored_rgb @ LUMA
    return _fill_holes(lum < 0.62)


def design_mask(stored_rgb: np.ndarray, obj: np.ndarray) -> np.ndarray:
    """fan2's painting (bright or saturated pixels inside the fan), dilated 2 px (RS 0's design mask rule)."""
    lum = stored_rgb @ LUMA
    mx, mn = stored_rgb.max(-1), stored_rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    d = obj & ((lum > 0.30) | ((sat > 0.35) & (mx > 0.15)))
    for _ in range(2):
        g = d.copy()
        g[1:, :] |= d[:-1, :]
        g[:-1, :] |= d[1:, :]
        g[:, 1:] |= d[:, :-1]
        g[:, :-1] |= d[:, 1:]
        d = g
    return d & obj


def _extents(mask):
    ys, xs = np.nonzero(mask)
    return {"x": [int(xs.min()), int(xs.max())], "y": [int(ys.min()), int(ys.max())]}


def fidelity(ref_rgb: np.ndarray, ren_rgb: np.ndarray, ren_alpha: np.ndarray, spec: FanSpec = FAN,
             fan_only_alpha: Optional[np.ndarray] = None) -> Dict[str, object]:
    """RS instruments on the shipped render vs fan2 (both stored 0..1 RGB).  The tassel counts in the
    silhouette (it is in fan2); ``fan_only_alpha`` (no tassel) gives the fan's own numbers."""
    m_ref = photo_mask(ref_rgb)
    m_ren = ren_alpha > 0.5
    iou = float((m_ref & m_ren).sum() / max((m_ref | m_ren).sum(), 1))
    out = {"mask_iou": round(iou, 4), "extents": {"reference": _extents(m_ref), "render": _extents(m_ren)}}
    # leaf top (min y) over the central columns, and the leaf corners' rows
    def top_row(m, x0, x1):
        cols = [np.nonzero(m[:, x])[0] for x in range(x0, x1)]
        ys = [c.min() for c in cols if len(c)]
        return float(np.median(ys)) if ys else None
    out["leaf_top_y_380_420"] = {"reference": top_row(m_ref, 380, 420), "render": top_row(m_ren, 380, 420)}
    # silhouette boundary distance (symmetric mean of nearest-boundary distances, px)
    def boundary(m):
        e = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        return np.argwhere(e)
    br, bn = boundary(m_ref), boundary(m_ren)
    def mean_nn(a, b):
        d = []
        for k in range(0, len(a), 7):
            p = a[k]
            d.append(np.sqrt(((b - p) ** 2).sum(1)).min())
        return float(np.mean(d)), float(np.percentile(d, 95))
    m1, p1 = mean_nn(br, bn)
    m2, p2 = mean_nn(bn, br)
    out["boundary_px"] = {"mean_ref_to_render": round(m1, 3), "mean_render_to_ref": round(m2, 3),
                          "p95_ref_to_render": round(p1, 3), "p95_render_to_ref": round(p2, 3)}
    # tones: the leaf band (radii 0.55 - 0.95 L about the rivet, image space) and the bare-rib band
    H, W = m_ref.shape
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - RIVET_PX[0], yy - RIVET_PX[1]) / 343.0
    phi = np.degrees(np.arctan2(RIVET_PX[1] - yy, xx - RIVET_PX[0]))
    dm = design_mask(ref_rgb, m_ref)
    lin_ref = _decode(ref_rgb) @ LUMA
    lin_ren = _decode(ren_rgb) @ LUMA
    zones = {"leaf": (r > 0.55) & (r < 0.93) & (phi > 15) & (phi < 165),
             "bare_ribs": (r > 0.15) & (r < 0.40) & (phi > 15) & (phi < 165),
             "lobe": (r < 0.10) & (phi < -20) & (phi > -160)}
    tones = {}
    for k, z in zones.items():
        a = z & m_ref & ~dm
        b = z & m_ren
        if a.sum() < 50 or b.sum() < 50:
            continue
        tones[k] = {"reference_lin_p10_50_90": [round(float(v), 5) for v in np.percentile(lin_ref[a], [10, 50, 90])],
                    "render_lin_p10_50_90": [round(float(v), 5) for v in np.percentile(lin_ren[b], [10, 50, 90])],
                    "p50_ratio": round(float(np.median(lin_ren[b]) / max(np.median(lin_ref[a]), 1e-9)), 4),
                    "reference_chroma": [round(float(v), 4) for v in (_decode(ref_rgb)[a].mean(0) / _decode(ref_rgb)[a].mean(0).sum())],
                    "render_chroma": [round(float(v), 4) for v in (_decode(ren_rgb)[b].mean(0) / _decode(ren_rgb)[b].mean(0).sum())]}
    out["tones"] = tones
    out["design_mask_fraction_of_leaf"] = round(float((dm & zones["leaf"]).sum() / max((m_ref & zones["leaf"]).sum(), 1)), 4)
    return out


def _decode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


__all__ = ["placement", "camera_matrix", "project", "rivet_check", "render_reference", "fidelity", "photo_mask",
           "design_mask", "BACKDROP_STORED", "RIVET_PX"]
