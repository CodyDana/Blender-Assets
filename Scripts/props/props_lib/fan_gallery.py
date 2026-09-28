#!/usr/bin/env python
"""props_lib.fan_gallery - SK_Fan's renders from the BAKED maps: the fan2 reference view, the side-by-side
and 3x crops, the pack gallery (hero 3/4, front, back, top, underside, raking, wire, LOD strip), the line
sheet entry, and the fold sheet.

bpy.  The prop line's rig (props_lib.render: 1600 x 900, Cycles, Khronos PBR Neutral, the world's value
ramp, the 72 mm hero lens at 29 deg elevation) with product lamps placed relative to the camera, as the
black hat's gallery (copied, that module is frozen).  The fan is shown STANDING (its plane vertical, the
leaf up, as it is displayed and as fan2 shows it); the sweep is hidden, the world ramp is the backdrop.
Every posed shot moves and poses the ARMATURE: the skinned meshes follow it exactly as in the engine.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import fan_look as LK
from . import fan_refview as RV
from . import render as R
from .fan_spec import D2R, FAN, FanSpec
from .paper_material import flat_emission

LIGHT_SCALE = 10.0
FAN_LIGHT = 0.18
HERO_FILL_H = 0.74
#: the line sheet's caption: the smoke bomb's line pitch (its 0.0019 m text in a 104 mm tall frame)
CAPTION_PX = 900.0 * 0.0019 / (0.185 * 900.0 / 1600.0)
#: [reference | render] crops at 3x (x0, y0, x1, y1) in fan2's 800 x 800 frame
CROPS3X = [(330, 500, 470, 610), (620, 430, 760, 530), (40, 430, 180, 530), (330, 205, 470, 275),
           (440, 400, 580, 520), (180, 560, 330, 650)]
CROP_NAMES = ["rivet, lobe and butts", "front guard tip and leaf corner", "rear corner (leaf over the rear guard)",
              "leaf top: pleats and scallop", "bare ribs and the leaf's inner edge", "tassel: cord, knot, skirt"]


def standing(spec: FanSpec = FAN, yaw_deg: float = 0.0) -> Matrix:
    """Build frame -> world: the fan upright (bisector up), front toward -Y, then turned yaw about Z."""
    a = (90.0 - 0.5 * spec.opening_deg) * D2R
    Rz = Matrix.Rotation(a, 4, "Z")
    Map = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    return Matrix.Rotation(math.radians(yaw_deg), 4, "Z") @ Map @ Rz


def _frame(camera, pts, fill_h: float, centre, fill_w: float = 0.86):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    camera.data.shift_x = camera.data.shift_y = 0.0
    d = (Vector(camera.location) - centre).normalized()
    lo, hi = 0.05, 20.0
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        camera.location = centre + d * mid
        R._aim(camera, centre)
        bpy.context.view_layer.update()
        ps = [world_to_camera_view(scene, camera, p) for p in pts]
        ys = [p.y for p in ps]
        xs = [p.x for p in ps]
        if max(ys) - min(ys) > fill_h or max(xs) - min(xs) > fill_w:
            lo = mid
        else:
            hi = mid
    camera.location = centre + d * hi
    R._aim(camera, centre)
    bpy.context.view_layer.update()
    ps = [world_to_camera_view(scene, camera, p) for p in pts]
    cx = 0.5 * (min(p.x for p in ps) + max(p.x for p in ps))
    cy = 0.5 * (min(p.y for p in ps) + max(p.y for p in ps))
    asp = scene.render.resolution_x / scene.render.resolution_y
    camera.data.shift_x = (cx - 0.5)
    camera.data.shift_y = (cy - 0.5) / asp
    bpy.context.view_layer.update()
    return hi


def _product_lamps(camera, target, distance, scale, key=(60.0, 64.0), fill=(-116.0, 4.0), fill_ratio=0.67,
                   size_scale=1.6, prefix="FAN_Gal", rim=None):
    cam_dir = (Vector(camera.location) - Vector(target)).normalized()
    world_up = Vector((0.0, 0.0, 1.0))
    if abs(cam_dir.dot(world_up)) > 0.98:
        world_up = Vector((0.0, 1.0, 0.0))
    right = world_up.cross(cam_dir).normalized()
    up = cam_dir.cross(right).normalized()
    right = -right if right.dot(camera.matrix_world.to_3x3() @ Vector((1, 0, 0))) < 0 else right
    lamps = []
    specs = [(prefix + "Key", key, 1.0), (prefix + "Fill", fill, fill_ratio)]
    if rim is not None:
        specs.append((prefix + "Rim", rim[:2], rim[2]))
    for name, (az, el), power in specs:
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
            for lib in (bpy.data.lights, bpy.data.meshes, bpy.data.curves, bpy.data.cameras):
                try:
                    lib.remove(data)
                    break
                except Exception:
                    pass


def label(coll, name, text, size, align_x="LEFT", align_y="CENTER", colour=(0.82, 0.82, 0.80)):
    data = bpy.data.curves.new(name, type="FONT")
    data.body = text
    data.size = size
    data.align_x = align_x
    data.align_y = align_y
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.data.materials.append(flat_emission(f"M_{name}", colour, 1.0))
    return obj


def _cam_point(cam, u: float, v: float, depth: float) -> Vector:
    scene = bpy.context.scene
    fr = [Vector(c) for c in cam.data.view_frame(scene=scene)]
    tr, br, bl, tl = fr
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    p = bot.lerp(top, v)
    p = p * (depth / -p.z)
    return cam.matrix_world @ p


def _world_pts(objs, step=3):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        M = o.matrix_world
        pts += [M @ v.co for v in me.vertices][::step]
        ev.to_mesh_clear()
    return pts


class Visible:
    """Show only ``objs`` (meshes) to the renderer; restore on exit."""
    def __init__(self, objs):
        self.objs = set(objs)

    def __enter__(self):
        self.saved = [(o, o.hide_render) for o in bpy.data.objects]
        for o in bpy.data.objects:
            if o.type in {"MESH", "CURVE", "FONT"} and not o.name.startswith("PREVIEW_"):
                o.hide_render = o not in self.objs
        return self

    def __exit__(self, *a):
        for o, was in self.saved:
            try:
                o.hide_render = was
            except ReferenceError:
                pass


# =========================================================================== reference view
#: fan2's tassel (RS 8, measured on the photo's silhouette): the cord runs from the rivet to the knot at image
#: angle -150 deg, the skirt lies out at -161.5 deg (RS 8's -159.7 is the whole tassel's line)
TASSEL_CORD_DEG = -150.0
TASSEL_SKIRT_DEG = -161.5


def tassel_flat_lay(spec, fs_arm, tarm, cord_deg: float = TASSEL_CORD_DEG, skirt_deg: float = TASSEL_SKIRT_DEG):
    """SK_Fan_Tassel at the Tassel socket lying out behind the fan in its plane as fan2 shows it (a flat lay,
    not a hang): returns (the tassel armature's world matrix, a pose that bends the skirt at the knot)."""
    from . import fan_tassel as TS
    zt = 0.5 * spec.stack_mm + spec.rivet_proud

    def frame(image_deg):
        th = (image_deg - RV.ROLL_TO_DEG) * D2R          # image angle -> build-frame angle (the tilt is ~0.1 deg)
        d = Vector((math.cos(th), math.sin(th), 0.0))
        zc = -d                                           # tassel -Z (its hang) -> d
        yc = Vector((0.0, 0.0, -1.0))                     # tassel +Y -> behind the fan
        xc = yc.cross(zc)
        return Matrix((xc, yc, zc)).transposed()
    R0 = frame(cord_deg)
    M = R0.to_4x4()
    # the round skirt (up to 8 mm radius) lies behind the fan's back face
    M.translation = Vector((0.0, 0.0, -zt - 0.6 - 8.5)) * 0.001
    # the skirt turned in the plane about the knot's bottom: in tassel space, R0^-1 R1
    R1 = frame(skirt_deg)
    Rl = np.array(R0.transposed() @ R1)
    st = TS.stations(spec)
    p = np.array([0.0, 0.0, st["neck_bot"]])
    T = np.eye(4)
    T[:3, :3] = Rl
    T[:3, 3] = p - Rl @ p
    pose = {"skirt_01": T, "skirt_02": T}
    return fs_arm.matrix_world @ M, pose


def reference_views(spec, arm, objs, tarm, tobjs, render_dir: Path, work: Path, reference: Path, samples: int):
    out = {}
    LK.pose(arm, {})
    Mt, tpose = tassel_flat_lay(spec, arm, tarm)
    tarm.matrix_world = Mt
    LK.pose(tarm, tpose)
    bpy.context.view_layer.update()
    ref_png = render_dir / "fan_reference_view.png"
    res = RV.render_reference([objs[0], tobjs[0]], spec, work, ref_png, samples=samples,
                              movers=[arm, tarm])
    # the fan alone (its own silhouette numbers without the tassel)
    res_fan = RV.render_reference([objs[0]], spec, work, work / "fan_reference_view_no_tassel.png", samples=16,
                                  movers=[arm, tarm])
    tarm.matrix_world = Matrix.Identity(4)
    out["reference_view"] = "Renders/Fan/fan_reference_view.png"
    LK.side_by_side(str(reference), ref_png, render_dir / "fan_side_by_side.png")
    LK.crops_sheet(str(reference), ref_png, render_dir / "fan_crops_3x.png", CROPS3X, scale=3)
    out["side_by_side"] = "Renders/Fan/fan_side_by_side.png"
    out["crops_3x"] = {"path": "Renders/Fan/fan_crops_3x.png",
                       "rows": [{"box": list(b), "shows": n} for b, n in zip(CROPS3X, CROP_NAMES)]}
    ref = LK.load_png(reference)[..., :3].astype(np.float64)
    ren = LK.load_png(ref_png)[..., :3].astype(np.float64)
    fid = RV.fidelity(ref, ren, res["alpha"], spec)
    fid_fan = RV.fidelity(ref, ren, res_fan["alpha"], spec)
    out["fidelity"] = fid
    out["fidelity_fan_only_silhouette"] = {"mask_iou_vs_photo_with_tassel": fid_fan["mask_iou"],
                                           "extents": fid_fan["extents"]}
    return out


# =========================================================================== the gallery
def _show_lod(objs, i):
    for k, o in enumerate(objs):
        o.hide_render = k != i


def exposed_render(path, cam, lamps, objs, work: Path, target_p50: float, tag: str) -> Dict[str, float]:
    """Render with the lamps scaled so the object's stored median lands on ``target_p50`` (a black fan reads
    black but its pleats still show): a quarter-size, 16-sample probe measures, the lamps are scaled by
    (target / probe)^2.2 (display -> linear), then the full frame is rendered.  Returns the scale used."""
    scene = bpy.context.scene
    mask = Path(work) / f"{tag}_mask.png"
    R.render_mask(mask, cam, objs)
    saved = (scene.render.resolution_percentage, scene.cycles.samples, scene.cycles.use_denoising)
    probe = Path(work) / f"{tag}_probe.png"
    scale = 1.0
    try:
        scene.render.resolution_percentage = 25
        scene.cycles.samples = 16
        for _ in range(2):
            R.render_to(probe, cam, lamps)
            rgb = R.load_pixels(probe)[..., :3]
            a = R.load_pixels(mask)[..., 3]
            h, w = rgb.shape[:2]
            am = a[::max(1, a.shape[0] // h), ::max(1, a.shape[1] // w)][:h, :w] > 0.5
            p50 = float(np.median(R.luma(rgb)[am])) if am.any() else target_p50
            f = float(np.clip((target_p50 / max(p50, 1e-4)) ** 2.2, 0.02, 200.0))
            for lo in lamps:
                lo.data.energy *= f
            scale *= f
            if abs(f - 1.0) < 0.08:
                break
    finally:
        scene.render.resolution_percentage, scene.cycles.samples, scene.cycles.use_denoising = saved
    R.render_to(path, cam, lamps)
    return {"lamp_scale": round(scale, 4), "target_object_p50": target_p50}


def gallery(spec, arm, objs, tarm, tobjs, render_dir: Path, work: Path, samples: int, lod_screen_sizes, tris,
            open_mm: float = 373.0) -> Dict:
    render_dir, work = Path(render_dir), Path(work)
    scene = bpy.context.scene
    device = R.setup_render(samples=samples)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    rig = R.build_rig(spec, light_scale=1.0)
    ground = rig["ground"]
    ground.hide_render = True
    out: Dict[str, object] = {"device": device, "samples": samples, "shots": {}}
    saved_arm = arm.matrix_world.copy()
    LK.pose(arm, {})
    cam = rig["cam_hero"]
    cam.data.dof.use_dof = False
    cam.data.clip_start = 0.02
    try:
        with Visible([objs[0]]):
            # ------------------------------------------------ hero: 3/4, the front toward the camera
            arm.matrix_world = standing(spec, yaw_deg=33.0)
            bpy.context.view_layer.update()
            pts = _world_pts([objs[0]])
            centre = sum(pts, Vector()) / len(pts)
            cam.location = centre + Vector(R._polar(1.5, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG))
            dist = _frame(cam, pts, HERO_FILL_H, centre)
            lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * FAN_LIGHT, key=(-55.0, 50.0), fill=(70.0, 12.0),
                                   fill_ratio=0.45, rim=(175.0, 35.0, 0.9))
            exp_hero = exposed_render(render_dir / "fan_hero.png", cam, lamps, [objs[0]], work, 0.20, "hero")
            out["shots"]["hero"] = {"path": "Renders/Fan/fan_hero.png", "lens_mm": cam.data.lens, **exp_hero,
                                    "elevation_deg": R.HERO_ELEVATION_DEG, "azimuth_deg": R.HERO_AZIMUTH_DEG,
                                    **R.image_stats(render_dir / "fan_hero.png", work / "hero_mask.png")}
            # ------------------------------------------------ raking: a grazing key across the pleats
            _remove(lamps)
            lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 1.2, key=(-82.0, 10.0), fill=(60.0, 30.0),
                                   fill_ratio=0.08, size_scale=0.35, prefix="FAN_Rake")
            exp_r = exposed_render(render_dir / "fan_raking.png", cam, lamps, [objs[0]], work, 0.15, "raking")
            out["shots"]["raking"] = {**exp_r, "path": "Renders/Fan/fan_raking.png", "camera": "the hero camera",
                                      "key": "small disc at az -82 / el 10 relative to the camera (grazing), fill 0.08",
                                      **R.image_stats(render_dir / "fan_raking.png", work / "hero_mask.png")}
            _remove(lamps)
            # ------------------------------------------------ front: straight on
            for nm, yaw, fname in (("front", 0.0, "fan_front.png"), ("back", 180.0, "fan_back.png")):
                arm.matrix_world = standing(spec, yaw_deg=yaw)
                bpy.context.view_layer.update()
                pts = _world_pts([objs[0]])
                centre = sum(pts, Vector()) / len(pts)
                cam.location = centre + Vector((0.0, -1.5, 0.0))
                dist = _frame(cam, pts, 0.80, centre, fill_w=0.80)
                lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * FAN_LIGHT, key=(-35.0, 55.0),
                                       fill=(50.0, 10.0), fill_ratio=0.5)
                ex = exposed_render(render_dir / fname, cam, lamps, [objs[0]], work, 0.20, nm)
                out["shots"][nm] = {"path": f"Renders/Fan/{fname}", **ex,
                                    **R.image_stats(render_dir / fname, work / f"{nm}_mask.png")}
                _remove(lamps)
            # ------------------------------------------------ top: down onto the leaf's top edge (the pleats)
            arm.matrix_world = standing(spec, yaw_deg=0.0)
            bpy.context.view_layer.update()
            pts = _world_pts([objs[0]])
            centre = sum(pts, Vector()) / len(pts)
            cam.location = centre + Vector((0.0, -0.25, 1.5)).normalized() * 1.5
            dist = _frame(cam, pts, 0.60, centre, fill_w=0.86)
            lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 0.5, key=(-30.0, 40.0), fill=(60.0, 10.0),
                                   fill_ratio=0.5)
            ex = exposed_render(render_dir / "fan_top.png", cam, lamps, [objs[0]], work, 0.20, "top")
            out["shots"]["top"] = {**ex, "path": "Renders/Fan/fan_top.png", "camera": "above, looking down the leaf's top edge",
                                   **R.image_stats(render_dir / "fan_top.png", work / "top_mask.png")}
            _remove(lamps)
            # ------------------------------------------------ underside: from below the lobe, looking up
            cam.location = centre + Vector((0.25, -0.9, -1.0)).normalized() * 1.5
            dist = _frame(cam, pts, 0.70, centre, fill_w=0.86)
            lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 0.45, key=(-40.0, 20.0), fill=(70.0, 10.0),
                                   fill_ratio=0.5)
            ex = exposed_render(render_dir / "fan_underside.png", cam, lamps, [objs[0]], work, 0.20, "under")
            out["shots"]["underside"] = {**ex, "path": "Renders/Fan/fan_underside.png",
                                         "camera": "below and in front: the lobe, the eyelet, the butts",
                                         **R.image_stats(render_dir / "fan_underside.png", work / "under_mask.png")}
            _remove(lamps)
        # ---------------------------------------------------- wire (3/4 from the front, above)
        coll = bpy.data.collections.new("PREVIEW_WIRE")
        scene.collection.children.link(coll)
        saved_world = scene.world
        scene.world = None
        arm.matrix_world = standing(spec, yaw_deg=33.0)
        bpy.context.view_layer.update()
        made = []
        for i, o in enumerate(objs):
            o.hide_render = True
        solid, wire = _wire_pair(objs[0], coll, "Lod0", thickness=0.00022)
        made += [solid, wire]
        pts = _world_pts([solid])
        centre = sum(pts, Vector()) / len(pts)
        cam.location = centre + Vector(R._polar(1.5, 25.0, R.HERO_AZIMUTH_DEG))
        _frame(cam, pts, 0.80, centre)
        R.render_to(render_dir / "fan_wire.png", cam, ())
        out["shots"]["wire"] = {"path": "Renders/Fan/fan_wire.png", "triangles": tris[0]}
        _remove(made)
        # ---------------------------------------------------- LOD strip (wire, the three LODs side by side)
        made = []
        width = 0.42
        for i, o in enumerate(objs):
            arm.matrix_world = Matrix.Translation(((i - 1) * width, 0.0, 0.0)) @ standing(spec, yaw_deg=0.0)
            bpy.context.view_layer.update()
            s_, w_ = _wire_pair(o, coll, f"Lod{i}", thickness=0.0005, bake_pose=True)
            made += [s_, w_]
            lab = label(coll, f"PREVIEW_LodLabel{i}", f"LOD{i}   {tris[i]:,} tris   screen {lod_screen_sizes[i]}", 0.016,
                        align_x="CENTER")
            lab.location = ((i - 1) * width, -0.02, -0.06)
            lab.rotation_euler = (math.radians(90.0), 0.0, 0.0)
            made.append(lab)
        cam_p = rig["cam_persp"]
        cam_p.data.lens = 50.0
        cam_p.location = (0.0, -2.05, 0.12)
        R._aim(cam_p, (0.0, 0.0, 0.08))
        cam_p.data.shift_x = cam_p.data.shift_y = 0.0
        R.render_to(render_dir / "fan_lods.png", cam_p, ())
        out["shots"]["lods"] = {"path": "Renders/Fan/fan_lods.png", "triangles": list(tris),
                                "screen_sizes": list(lod_screen_sizes)}
        _remove(made)
        bpy.data.collections.remove(coll)
        scene.world = saved_world
        for i, o in enumerate(objs):
            o.hide_render = i != 0
        # ---------------------------------------------------- line sheet
        out["shots"]["linesheet"] = line_sheet(spec, arm, objs, rig, render_dir, work, tris, open_mm)
    finally:
        arm.matrix_world = saved_arm
        R.teardown(rig)
    return out


def _wire_pair(source, coll, name, thickness=0.0006, bake_pose=False):
    """A frozen copy of the (posed, placed) skinned mesh: flat solid + wire on top."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = source.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    M = source.matrix_world.copy()
    solid = bpy.data.objects.new(f"PREVIEW_{name}Solid", me)
    solid.matrix_world = M
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(flat_emission(f"M_Wire_{name}_Solid", (0.150, 0.162, 0.185), 1.0))
    me2 = me.copy()
    wires = bpy.data.objects.new(f"PREVIEW_{name}Lines", me2)
    c = M.to_translation()
    wires.matrix_world = Matrix.Translation(c) @ Matrix.Scale(1.0015, 4) @ Matrix.Translation(-c) @ M
    coll.objects.link(wires)
    wires.data.materials.clear()
    wires.data.materials.append(flat_emission(f"M_Wire_{name}_Lines", (1.0, 0.48, 0.14), 2.0))
    mod = wires.modifiers.new("Wireframe", "WIREFRAME")
    mod.thickness = thickness
    mod.use_boundary = True
    mod.use_even_offset = False
    mod.use_replace = True
    return solid, wires


def line_sheet(spec, arm, objs, rig, render_dir: Path, work: Path, tris, open_mm: float = 373.0):
    """The house line sheet: a 3/4 view at the hero's angle on the left, the closed fan beside it, the
    caption at the smoke bomb's size and place; composited over the smoke bomb sheet's backdrop gradient."""
    scene = bpy.context.scene
    coll = bpy.data.collections.new("PREVIEW_SHEET")
    scene.collection.children.link(coll)
    made = []
    cam = rig["cam_hero"]
    cam.data.dof.use_dof = False
    try:
        arm.matrix_world = standing(spec, yaw_deg=33.0)
        LK.pose(arm, {})
        bpy.context.view_layer.update()
        hero = bpy.data.objects.new("PREVIEW_SheetHero", bpy.data.meshes.new_from_object(
            objs[0].evaluated_get(bpy.context.evaluated_depsgraph_get())))
        hero.matrix_world = objs[0].matrix_world.copy()
        coll.objects.link(hero)
        for m in objs[0].data.materials:
            hero.data.materials.append(m) if len(hero.data.materials) < len(objs[0].data.materials) else None
        made.append(hero)
        pts = _world_pts([hero])
        centre = sum(pts, Vector()) / len(pts)
        cam.location = centre + Vector(R._polar(1.5, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG))
        dist = _frame(cam, pts, 0.66, centre, fill_w=0.52)
        cam.data.shift_x += 0.20
        cam.data.shift_y += 0.01
        bpy.context.view_layer.update()
        depth = 0.30
        pts2 = [_cam_point(cam, 0.0, 0.5, depth), _cam_point(cam, 1.0, 0.5, depth)]
        px_per_m = 1600.0 / (pts2[1] - pts2[0]).length
        size = CAPTION_PX / px_per_m
        lines = [f"{spec.mesh_name}  +  {spec.tassel_name} (optional)",
                 f"{open_mm:.0f} mm open, {spec.L + spec.butt_mm:.0f} mm closed     "
                 f"{spec.n_sticks} sticks     {spec.mass_g:.0f} g",
                 f"skeletal: {len(arm.data.bones) + 1} bones (a bone per stick + per leaf face)     open / close animation",
                 f"LOD {tris[0]:,} / {tris[1]:,} / {tris[2]:,} tris     physics asset     4 sockets",
                 "recolourable leaf, sticks, tassel: BaseColor = Tint x (Bias + Scale x Detail)"]
        cw = cam.matrix_world.to_3x3()
        lab = label(coll, "PREVIEW_SheetText", chr(10).join(lines), size)
        lab.matrix_world = Matrix.Translation(_cam_point(cam, 0.56, 0.60, depth)) @ cw.to_4x4()
        made.append(lab)
        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * FAN_LIGHT, key=(-55.0, 50.0), fill=(70.0, 12.0),
                               fill_ratio=0.45, rim=(175.0, 35.0, 0.9))
        was = (scene.render.film_transparent, scene.render.image_settings.color_mode)
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
        tmp = Path(work) / "fan_linesheet_rgba.png"
        saved = [(o, o.hide_render) for o in objs]
        for o in objs:
            o.hide_render = True
        try:
            exposed_render(tmp, cam, lamps, [hero], work, 0.20, "sheet")
        finally:
            scene.render.film_transparent, scene.render.image_settings.color_mode = was
            for o, w in saved:
                o.hide_render = w
        _remove(lamps)
        fg = LK.load_png(tmp)
        sb = LK.load_png(Path(__file__).resolve().parents[3] / "Renders" / "SmokeBomb" / "smokebomb_linesheet.png")[..., :3]
        col = np.median(sb[:, 1400:1590], axis=1)
        bg = np.broadcast_to(col[:, None, :], fg[..., :3].shape)
        a = fg[..., 3:4]
        LK.write_png(render_dir / "fan_linesheet.png", fg[..., :3] * a + bg * (1.0 - a))
        return {"path": "Renders/Fan/fan_linesheet.png", "lines": lines,
                "backdrop": "the smoke bomb line sheet's backdrop gradient (its columns 1400-1590), composited"}
    finally:
        for o in made:
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except ReferenceError:
                pass
        bpy.data.collections.remove(coll)


# =========================================================================== fold sheet
FOLD_ANGLES = (0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 163.2)


def _ortho_fit(co, cd, pts, rot3, margin=1.12, aspect=1.2):
    """Aim an orthographic camera with orientation rot3 (columns = camera x, y, z) at the points, fitted."""
    R = np.array(rot3)
    P = np.array([p[:] for p in pts])
    loc = P @ R                                    # camera-space coordinates (x, y, depth)
    lo, hi = loc.min(0), loc.max(0)
    c = 0.5 * (lo + hi)
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    cd.ortho_scale = max(w, h * aspect) * margin
    centre = R @ np.array([c[0], c[1], hi[2] + 1.0])
    M = Matrix(np.eye(4).tolist())
    for i in range(3):
        for j in range(3):
            M[i][j] = R[i, j]
    M.translation = Vector(centre.tolist())
    co.matrix_world = M
    cd.clip_start = 0.001
    cd.clip_end = 5.0
    return float(cd.ortho_scale)


def _view_rot(elev_deg, azim_deg=0.0):
    """Camera orientation looking at the standing fan (front toward -Y) from the front, raised elev_deg."""
    e, a = math.radians(elev_deg), math.radians(azim_deg)
    back = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))   # camera +Z (towards it)
    x = Vector((0, 0, 1)).cross(back).normalized()
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    y = back.cross(x).normalized()
    return [[x.x, y.x, back.x], [x.y, y.y, back.y], [x.z, y.z, back.z]]


def fold_sheet(spec, arm, obj, pose_at: Callable[[float], None], out_png: Path, work: Path, samples: int = 64,
               angles: Sequence[float] = FOLD_ANGLES, tile=(480, 400), closeup_png: Optional[Path] = None):
    """Two rows of tiles: the fan at each opening angle (guard axis to guard axis) straight from the FRONT and
    from ABOVE (raised 60 deg over the leaf's top edge, so the pleats' depth, the fins of the half-closed leaf
    and the page stack read), each tile fitted to the fan; plus a two-panel close-up of the closed stack (end-on
    at the tip, and from above the tip).  ``pose_at(opening_deg)`` poses the armature (the build poses the
    mechanism, the verifier plays the re-imported FBX animation)."""
    scene = bpy.context.scene
    LK._cycles(scene, samples, denoise=True)
    scene.render.resolution_x, scene.render.resolution_y = tile
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    coll = bpy.data.collections.new("FOLD_SHEET_RIG")
    scene.collection.children.link(coll)
    cd = bpy.data.cameras.new("FoldCam")
    cd.type = "ORTHO"
    co = bpy.data.objects.new("FoldCam", cd)
    coll.objects.link(co)
    scene.camera = co
    lamps = []
    for name, loc, en in (("K", (0.35, -0.7, 0.9), 30.0), ("F", (-0.7, -0.8, 0.2), 12.0), ("T", (0.0, 0.2, 1.0), 14.0),
                          ("B", (0.0, 0.8, -0.3), 6.0)):
        ld = bpy.data.lights.new("Fold" + name, "AREA")
        ld.size = 0.5
        ld.energy = en
        lo = bpy.data.objects.new("Fold" + name, ld)
        coll.objects.link(lo)
        lo.location = Vector(loc).normalized() * 1.2
        lo.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        lamps.append(lo)
    wd = bpy.data.worlds.new("FoldWorld")
    wd.use_nodes = True
    bg = next(n for n in wd.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.3
    saved_world = scene.world
    scene.world = wd
    saved_M = arm.matrix_world.copy()
    tiles = {"front": [], "above": []}
    info = {"angles_deg": list(angles), "tiles": []}
    views = {"front": _view_rot(0.0), "above": _view_rot(60.0)}
    try:
        with Visible([obj]):
            for ang in angles:
                pose_at(ang)
                arm.matrix_world = standing(spec, yaw_deg=0.0)
                bpy.context.view_layer.update()
                pts = _world_pts([obj], step=2)
                for view in ("front", "above"):
                    scale = _ortho_fit(co, cd, pts, views[view], aspect=tile[0] / tile[1])
                    a = LK.render_exr(work / f"fold_{view}_{ang:06.2f}.exr")
                    tiles[view].append(LK.composite_over(a, 0.93))
                    info["tiles"].append({"opening_deg": ang, "view": view, "field_mm": round(scale * 1000, 1)})
            if closeup_png is not None:
                pose_at(0.0)
                arm.matrix_world = standing(spec, yaw_deg=0.0)
                bpy.context.view_layer.update()
                pts = _world_pts([obj], step=1)
                P = np.array([p[:] for p in pts])
                # the fan's long axis (closed) in the world: the front guard's direction
                ax = np.array((arm.matrix_world.to_3x3() @ Vector((1, 0, 0)))[:])
                far = P @ ax
                tip = P[far > far.max() - 0.016]
                panels = []
                scene.render.resolution_x, scene.render.resolution_y = (700, 560)
                # (a) end-on: looking back along the fan from beyond its tip
                zc = Vector((-ax).tolist())
                xc = Vector((0, 1, 0)).cross(zc).normalized() if abs(zc.y) < 0.9 else Vector((1, 0, 0))
                yc = zc.cross(xc).normalized()
                rot = [[xc.x, yc.x, -zc.x], [xc.y, yc.y, -zc.y], [xc.z, yc.z, -zc.z]]
                _ortho_fit(co, cd, [Vector(p) for p in tip], rot, margin=1.35, aspect=700 / 560)
                panels.append(LK.composite_over(LK.render_exr(work / "fold_closed_end.exr"), 0.93))
                # (b) from above the tip (raised 55 deg, a little from the side)
                _ortho_fit(co, cd, [Vector(p) for p in P[far > far.max() - 0.05]], _view_rot(55.0, 25.0), margin=1.2,
                           aspect=700 / 560)
                panels.append(LK.composite_over(LK.render_exr(work / "fold_closed_above.exr"), 0.93))
                gap = np.ones((560, 12, 3))
                LK.write_png(closeup_png, np.concatenate([panels[0], gap, panels[1]], 1))
                info["closeup"] = {"path": str(closeup_png),
                                   "panels": ["end-on at the tip: guards either side, the 50 faces lying as a stack of "
                                              "pages between them", "from above the last 50 mm: the page stack's fold "
                                              "edges and the scalloped tip"]}
    finally:
        arm.matrix_world = saved_M
        scene.world = saved_world
        for o in list(coll.objects):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            for lib in (bpy.data.cameras, bpy.data.lights):
                try:
                    lib.remove(d)
                    break
                except Exception:
                    pass
        bpy.data.collections.remove(coll)
        bpy.data.worlds.remove(wd)
    rows = []
    for view in ("front", "above"):
        rows.append(np.concatenate([np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=1.0) for t in tiles[view]], 1))
    sheet = np.concatenate(rows, 0)
    LK.write_png(out_png, sheet)
    info["path"] = str(out_png)
    info["layout"] = "row 1: straight from the front; row 2: from above (raised 60 deg over the leaf edge); each tile " \
                     "fitted to the fan; columns: " + ", ".join(f"{a:g} deg" for a in angles) + \
                     " (0 = closed: the guards stay 1.5 deg apart, the leaf lines coincide)"
    return info


# =========================================================================== orchestration
def stage_render(spec, fs, arm, objs, tarm, tobjs, report, render_dir: Path, work: Path, reference: Path,
                 quick=False, log=print):
    render_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    samples = 64 if quick else 512
    for i, o in enumerate(objs):
        o.hide_render = i != 0
    for i, o in enumerate(tobjs):
        o.hide_render = i != 0
    log("render: fan2 reference view, side-by-side, crops")
    rep = reference_views(spec, arm, objs, tarm, tobjs, render_dir, work, reference, samples)
    log(f"  mask IoU {rep['fidelity']['mask_iou']}, boundary {rep['fidelity']['boundary_px']}")
    for o in tobjs:
        o.hide_render = True
    log("render: gallery")
    rep["gallery"] = gallery(spec, arm, objs, tarm, tobjs, render_dir, work, 48 if quick else 256,
                             report["lod_screen_sizes"], report["lod_triangles"], report["size_open_mm"][0])
    report["renders"] = rep
    report["fidelity"] = rep["fidelity"]


__all__ = ["stage_render", "fold_sheet", "gallery", "reference_views", "standing", "tassel_flat_lay", "FOLD_ANGLES"]
