#!/usr/bin/env python
"""props_lib.paperbomb_gallery - the paper bomb's own additions to the shared gallery.

``props_lib.gallery`` is shared with the other props, so the paper bomb's two gallery
fixes live here and run after ``gallery.render_all``, rendering from the same BAKED maps
(the card wears ``M_PaperBomb`` and nothing else):

1.  THE BACK SHOT SITS ON THE SWEEP.  The shared back shot turns the card 180 deg about
    its long axis in place.  The card is cupped (a 4 mm curl) and creased, so turned over
    its edges dip up to ~4.6 mm below where they were - through the sweep, 4 mm under the
    mid-surface - and the ground plane clipped the lower half into a pinched, torn-looking
    silhouette that the mesh does not have.  Here the turned card is dropped onto the
    sweep (its lowest vertex just touching it), exactly as the hero is, and the back shot,
    its mask, its statistics and the luminance / ink-consistency gates are redone.

2.  THE SCAN (``paperbomb_front_scan.png``).  The pack's flat front is lit to the pack's
    exposure band (a gate), which leaves the paper ~40 % darker than the user's flat
    reference and rakes enough light to make the normal map's grain three times the
    reference's.  The scan is the same orthographic front under the light a flatbed gives:
    a uniform white dome (no direction, so the relief reads only as it does on a scan),
    cross-polarised (the paper's specular sheen off: the same four baked maps worn by a copy
    of M_PaperBomb whose specular, coat and sheen are zero - a white 4 % sheen otherwise
    lifts the sumi to grey L 20), the Standard view transform (no tone curve), and ONE
    exposure number calibrated so the
    rendered paper equals the baked BC map's own paper - the scanner's white calibration,
    against the shipped map, never against the reference.  It is the shot to hold beside
    the reference; the gate on it compares it with the reference at the same height.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict

import bpy
import numpy as np
from mathutils import Matrix

from . import render as R
from . import gallery as G

PB_GALLERY_VERSION = "1.0.0"
SCAN_NAME = "paperbomb_front_scan.png"
#: the scan's tolerances against the reference (CIEDE2000 on the median colours)
SCAN_TOL = {"paper_de": 2.0, "red_de": 3.0, "black_de": 3.0}


def _flat_camera(rig, spec):
    cam = rig["cam_flat"]
    cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    cam.location = (0.0, 0.0, 0.40)
    cam.data.ortho_scale = (spec.height_mm / G.FLAT_FILL) * 0.001 * R.RES_X / R.RES_Y
    return cam


def rerender_back(spec, objects, renders: Dict[str, object], render_dir: Path,
                  work_dir: Path, light_scale: float = 1.0, ink_floor=None) -> Dict[str, object]:
    """Redo the back shot with the turned card sitting on the sweep; update ``renders``."""
    render_dir = Path(render_dir)
    diag = Path(work_dir) / "diag"
    rig = R.build_rig(spec, light_scale=light_scale)
    lod0 = objects[0]
    stash = [(o, o.hide_render) for o in objects]
    for o in objects:
        o.hide_render = True
    try:
        back = G._clone(lod0, "PREVIEW_Back",
                        Matrix.Rotation(math.radians(180.0), 4, "X") @ lod0.matrix_world)
        zs_before = np.array([(back.matrix_world @ v.co)[2] for v in back.data.vertices])
        G._drop_to_ground(back, rig["ground"])
        zs_after = np.array([(back.matrix_world @ v.co)[2] for v in back.data.vertices])
        cam = _flat_camera(rig, spec)
        R.render_to(render_dir / "paperbomb_back.png", cam, rig["flat"])
        R.render_mask(diag / "back_mask.png", cam, [back])
        shot = {
            "path": "Renders/PaperBomb/paperbomb_back.png",
            "note": ("the card is turned 180 deg about its long axis and dropped onto the "
                     "sweep (paperbomb_gallery); the camera and lamps do not move"),
            "turned_min_z_mm_before_drop": round(float(zs_before.min()) * 1000.0, 3),
            "ground_z_mm": round(float(rig["ground"].location.z) * 1000.0, 3),
            "lift_mm": round(float(zs_after.min() - zs_before.min()) * 1000.0, 3),
            **R.image_stats(render_dir / "paperbomb_back.png", diag / "back_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_back.png",
                                             diag / "back_mask.png"),
        }
        bpy.data.objects.remove(back, do_unlink=True)
    finally:
        R.teardown(rig)
        for obj, was in stash:
            obj.hide_render = was
    shots = renders.setdefault("shots", {})
    shots["back"] = shot
    gates = renders.setdefault("gates", {})
    gates["luminance"] = G._luminance_gate(shots, ink_floor)
    gates["ink_consistency"] = R.ink_consistency_gate(shots)
    # the silhouette check: every vertex of the turned card is above the sweep
    gates["back_on_the_sweep"] = {
        "passed": bool(zs_after.min() >= rig_ground_z(shot) - 1e-6),
        "turned_min_z_mm_before_drop": shot["turned_min_z_mm_before_drop"],
        "ground_z_mm": shot["ground_z_mm"],
    }
    return shot


def rig_ground_z(shot) -> float:
    return shot["ground_z_mm"] / 1000.0


def _stored_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _bc_paper_linear(spec) -> np.ndarray:
    """Median linear colour of the baked BC map's bare paper (its card interior, off the
    ink): the scanner's white-calibration target."""
    tex = Path(__file__).resolve().parents[3] / "Exports" / "PaperBomb" / "Textures" / \
        f"{spec.texture_stem}_BC.png"
    img = bpy.data.images.load(str(tex), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        st = buf.reshape(h, w, 4)[..., :3].astype(np.float64)
    finally:
        bpy.data.images.remove(img)
    lum = st @ np.array([0.2126, 0.7152, 0.0722])
    # bare paper: the bright, warm mode of the map (ink is far darker or redder)
    warm = st[..., 0] - st[..., 2]
    cand = (lum > np.percentile(lum, 55)) & (warm > 0.08) & (warm < 0.30) \
        & (st[..., 0] - st[..., 1] < 0.08)
    return _stored_to_linear(np.median(st[cand], 0))


def render_scan(spec, objects, render_dir: Path, work_dir: Path,
                samples: int = 256) -> Dict[str, object]:
    """The front under flatbed light, exposure calibrated on the baked BC's paper."""
    scene = bpy.context.scene
    render_dir = Path(render_dir)
    diag = Path(work_dir) / "diag"
    diag.mkdir(parents=True, exist_ok=True)
    vs = scene.view_settings
    saved = dict(world=scene.world, transform=vs.view_transform, look=vs.look,
                 exposure=vs.exposure, gamma=vs.gamma, samples=scene.cycles.samples,
                 camera=scene.camera, film=scene.render.film_transparent)
    world = bpy.data.worlds.new("W_PaperBomb_Scan")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    bg = next(n for n in nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    cam_data = bpy.data.cameras.new("PREVIEW_CamScan")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("PREVIEW_CamScan", cam_data)
    scene.collection.objects.link(cam)
    cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    cam.location = (0.0, 0.0, 0.40)
    cam_data.ortho_scale = (spec.height_mm / G.FLAT_FILL) * 0.001 * R.RES_X / R.RES_Y
    lod0 = objects[0]
    stash = [(o, o.hide_render) for o in objects]
    out: Dict[str, object] = {"version": PB_GALLERY_VERSION, "path": "Renders/PaperBomb/" + SCAN_NAME}
    try:
        for o in objects:
            o.hide_render = True
        card = G._clone(lod0, "PREVIEW_Scan")
        # CROSS-POLARISED: a scan records the diffuse albedo; the paper's specular sheen
        # (a white ~4 % lift that turns sumi to grey L 20 under any dome) is what a
        # scanner's polarisers remove.  A COPY of M_PaperBomb with the specular, coat and
        # sheen lobes at zero - same four baked maps, same UVs - is worn for this shot only.
        scan_mats = []
        for slot in card.material_slots:
            if slot.material is None:
                continue
            mat = slot.material.copy()
            mat.name = slot.material.name + "_ScanDiffuse"
            for n in mat.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    for inp, v in (("Specular IOR Level", 0.0), ("Coat Weight", 0.0),
                                   ("Sheen Weight", 0.0)):
                        if inp in n.inputs and not n.inputs[inp].is_linked:
                            n.inputs[inp].default_value = v
                        elif inp in n.inputs:
                            for link in list(n.inputs[inp].links):
                                mat.node_tree.links.remove(link)
                            n.inputs[inp].default_value = v
            slot.material = mat
            scan_mats.append(mat)
        scene.world = world
        vs.view_transform = "Standard"
        try:
            vs.look = "None"
        except Exception:
            pass
        vs.gamma = 1.0
        vs.exposure = 0.0
        target = _bc_paper_linear(spec)
        R.render_mask(diag / "scan_mask.png", cam, [card])
        mask = R.load_pixels(diag / "scan_mask.png")[..., 3] > 0.5
        inner = mask.copy()
        # well inside the card: erode the silhouette by ~2 % of its height
        k = max(2, int(0.02 * mask.sum(0).max()))
        for _ in range(k):
            inner = inner & np.roll(inner, 1, 0) & np.roll(inner, -1, 0) \
                & np.roll(inner, 1, 1) & np.roll(inner, -1, 1)
        # calibration pass (the paper of the render against the BC's paper)
        scene.cycles.samples = 48
        R.render_to(diag / "scan_calib.png", cam, [])
        px = R.load_pixels(diag / "scan_calib.png")[..., :3].astype(np.float64)
        lin = _stored_to_linear(px)
        lum = lin @ np.array([0.2126, 0.7152, 0.0722])
        sel = inner & (lum > np.percentile(lum[inner], 55))
        got = np.median(lin[sel], 0)
        gain = float((target @ np.array([0.2126, 0.7152, 0.0722]))
                     / max(1e-6, got @ np.array([0.2126, 0.7152, 0.0722])))
        vs.exposure = round(math.log2(gain), 4)
        scene.cycles.samples = samples
        R.render_to(render_dir / SCAN_NAME, cam, [])
        out.update({"exposure_stops": vs.exposure, "calibration_target_linear":
                    [round(float(v), 4) for v in target],
                    "calibration_rendered_linear": [round(float(v), 4) for v in got],
                    "light": ("uniform white dome, strength 1; Standard view transform; "
                              "cross-polarised (M_PaperBomb copy with specular, coat and "
                              "sheen at zero)"),
                    "samples": samples})
        bpy.data.objects.remove(card, do_unlink=True)
        for mat in scan_mats:
            bpy.data.materials.remove(mat)
    finally:
        scene.world = saved["world"]
        vs.view_transform = saved["transform"]
        try:
            vs.look = saved["look"]
        except Exception:
            pass
        vs.exposure = saved["exposure"]
        vs.gamma = saved["gamma"]
        scene.cycles.samples = saved["samples"]
        scene.camera = saved["camera"]
        scene.render.film_transparent = saved["film"]
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        bpy.data.worlds.remove(world)
        for obj, was in stash:
            obj.hide_render = was
    out["gate"] = scan_gate(render_dir / SCAN_NAME)
    return out


def scan_gate(path) -> Dict[str, object]:
    """The scan beside the reference at the same height: median paper, red core and black
    core colours, CIEDE2000, with the render's card found by the tracer's own edge fit."""
    from . import trace as T
    from . import paperbomb_tracedart as TA
    img = R.load_pixels(path)[..., :3].astype(np.float64)
    rsrc = T.Source(path="scan", sha256="", nbytes=0, rgb=img, info={})
    try:
        rfit = T.fit_card(rsrc)
    except Exception as exc:                                     # pragma: no cover
        return {"passed": False, "error": f"card fit: {exc}"}
    m = TA.reference_model()
    ref, fit = m.L.src.rgb, m.L.fit
    H, W = ref.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    xm, ym = fit.px_to_mm(xx, yy)
    rx, ry = rfit.mm_to_px(xm, ym)
    j = np.clip(rx.astype(int), 0, img.shape[1] - 1); i = np.clip(ry.astype(int), 0, img.shape[0] - 1)
    ours = img[i, j]
    card = (xm > 2) & (xm < 68) & (ym > 2) & (ym < 160)
    pa = card & ((m.L.black + m.L.red) < 0.03)
    rd = card & (m.L.red_behind > 0.95) & (m.L.black < 0.05)
    bk = card & (m.L.black > 0.95)
    res = {"render_card_ppmm": round(float(rfit.ppmm), 4), "tolerance": SCAN_TOL}
    ok = True
    for name, sel, key in (("paper", pa, "paper_de"), ("red", rd, "red_de"), ("black", bk, "black_de")):
        a = T.srgb_to_lab(np.median(ref[sel], 0)); b = T.srgb_to_lab(np.median(ours[sel], 0))
        d = float(T.delta_e2000(a, b))
        res[key] = round(d, 3)
        res[name + "_lab_ref"] = [round(float(v), 2) for v in a]
        res[name + "_lab_scan"] = [round(float(v), 2) for v in b]
        ok = ok and d <= SCAN_TOL[key]
    lum = np.array([0.2126, 0.7152, 0.0722])
    res["paper_grain_luma_std"] = {"reference": round(float((ref[pa] @ lum).std() * 100), 3),
                                   "scan": round(float((ours[pa] @ lum).std() * 100), 3)}
    res["passed"] = bool(ok)
    return res
