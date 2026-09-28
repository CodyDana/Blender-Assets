#!/usr/bin/env python
"""props_lib.blackhat_gallery - SM_BlackHat's pack gallery on the shared rig, from the BAKED maps.

bpy.  The prop line's rig (props_lib.render: 1600 x 900, Cycles, Khronos PBR Neutral, the world's
value ramp, the ground sweep, the 72 mm hero lens at 29 deg elevation) with the smoke bomb's
product lamps relative to the camera (copied from smokebomb_look, which is frozen).  What changed
for a 600 mm hat whose tails hang 90 mm below its rim:

    hero / raking / underside   the sweep is HIDDEN: the tails are the lowest thing on the hat,
                                so standing it on the sweep would float the rim 9 cm up or push the
                                tails through the floor; the world's dark ramp is the backdrop
    top / line sheet            on the sweep, seen from above (the tails' tips touch it)
    wire / LOD strip            flat-lit emission, as the pack's
    LOD switch                  each LOD shaded under the reference-view lights at its switch size
                                on a 1080p, 90 deg hFOV screen, [LODn-1 | LODn | 3x diff], magnified
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Sequence

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import render as R
from . import blackhat_look as LK
from .gallery import _label
from .paper_material import flat_emission

LIGHT_SCALE = 10.0
HERO_FILL_H = 0.70


def _clone(obj, name, matrix=None):
    c = obj.copy()
    c.data = obj.data.copy()
    c.name = name
    c.parent = None
    c.matrix_world = matrix if matrix is not None else obj.matrix_world.copy()
    c.hide_render = False
    bpy.context.scene.collection.objects.link(c)
    return c


def _frame(camera, obj, fill_h: float, centre, fill_w: float = 0.86):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    co = [obj.matrix_world @ v.co for v in obj.data.vertices][::5]
    camera.data.shift_x = camera.data.shift_y = 0.0
    d = (Vector(camera.location) - centre).normalized()
    lo, hi = 0.1, 20.0
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        camera.location = centre + d * mid
        R._aim(camera, centre)
        bpy.context.view_layer.update()
        ps = [world_to_camera_view(scene, camera, p) for p in co]
        ys = [p.y for p in ps]
        xs = [p.x for p in ps]
        if max(ys) - min(ys) > fill_h or max(xs) - min(xs) > fill_w:
            lo = mid
        else:
            hi = mid
    camera.location = centre + d * hi
    R._aim(camera, centre)
    bpy.context.view_layer.update()
    ps = [world_to_camera_view(scene, camera, p) for p in co]
    cx = 0.5 * (min(p.x for p in ps) + max(p.x for p in ps))
    cy = 0.5 * (min(p.y for p in ps) + max(p.y for p in ps))
    asp = scene.render.resolution_x / scene.render.resolution_y
    camera.data.shift_x = (cx - 0.5)
    camera.data.shift_y = (cy - 0.5) / asp
    bpy.context.view_layer.update()
    return hi


def _product_lamps(camera, target, distance, scale, key=(60.0, 64.0), fill=(-116.0, 4.0), fill_ratio=0.67,
                   size_scale=1.6, prefix="BH_Gal", rim=None):
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
            for lib in (bpy.data.lights, bpy.data.meshes):
                try:
                    lib.remove(data)
                    break
                except Exception:
                    pass


def _wire_pair(source, coll, name: str, matrix, thickness: float = 0.0006):
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


def _bbox_centre(obj):
    co = np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices])
    return Vector(0.5 * (co.min(0) + co.max(0))), co


def gallery(spec, lods: List, render_dir: Path, work: Path, samples: int = 192, lod_screen_sizes=(1.0, 0.6, 0.2),
            tris=(0, 0, 0), stem: str = "blackhat") -> Dict[str, object]:
    render_dir, work = Path(render_dir), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    device = R.setup_render(samples=samples)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_border = False
    rig = R.build_rig(spec, light_scale=1.0)
    ground = rig["ground"]
    out: Dict[str, object] = {"device": device, "samples": samples, "shots": {}}
    lod0 = lods[0]
    stash = [(o, o.hide_render) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("SM_", "UCX_"))]
    for o, _ in stash:
        o.hide_render = True
    D = 2.0 * spec.R * 0.001
    try:
        # ------------------------------------------------------------ hero (3/4 from the knot side)
        cam = rig["cam_hero"]
        cam.data.dof.use_dof = False
        # turn the hat so the pack's hero camera sees it as the reference camera does
        yaw = Matrix.Rotation(math.radians(R.HERO_AZIMUTH_DEG - 29.0), 4, "Z")
        hero = _clone(lod0, "PREVIEW_Hero", yaw @ lod0.matrix_world)
        centre, _co = _bbox_centre(hero)
        cam.location = centre + Vector(R._polar(1.5, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG))
        ground.hide_render = True
        dist = _frame(cam, hero, HERO_FILL_H, centre)
        # a black hat: the lamps are set so the object's stored p50 sits near 0.2 (it reads black,
        # the weave and the wear still show); the pack's LIGHT_SCALE put it at 0.50 (grey-white)
        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 0.15, key=(-70.0, 45.0), fill=(80.0, 15.0),
                               fill_ratio=0.45, rim=(180.0, 35.0, 0.8))
        R.render_to(render_dir / f"{stem}_hero.png", cam, lamps)
        R.render_mask(work / "hero_mask.png", cam, [hero])
        out["shots"]["hero"] = {"path": f"Renders/BlackHat/{stem}_hero.png", "camera_distance_m": round(dist, 4),
                                "lens_mm": cam.data.lens, "elevation_deg": R.HERO_ELEVATION_DEG,
                                "azimuth_deg": R.HERO_AZIMUTH_DEG, "ground": "hidden (the tails hang below the rim)",
                                **R.image_stats(render_dir / f"{stem}_hero.png", work / "hero_mask.png")}
        _remove(lamps)
        # ------------------------------------------------------------ raking
        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 1.3, key=(-80.0, 8.0), fill=(60.0, 30.0),
                               fill_ratio=0.10, size_scale=0.35, prefix="BH_Rake")
        R.render_to(render_dir / f"{stem}_raking.png", cam, lamps)
        out["shots"]["raking"] = {"path": f"Renders/BlackHat/{stem}_raking.png", "camera": "the hero camera",
                                  "key": "small disc at az -80 / el 8 relative to the camera (grazing), fill 0.10",
                                  **R.image_stats(render_dir / f"{stem}_raking.png", work / "hero_mask.png")}
        _remove(lamps)
        bpy.data.objects.remove(hero, do_unlink=True)
        # ------------------------------------------------------------ underside (the plain inner skin)
        under = _clone(lod0, "PREVIEW_Under", lod0.matrix_world.copy())
        centre, _co = _bbox_centre(under)
        cam.location = centre + Vector(R._polar(1.5, -38.0, R.HERO_AZIMUTH_DEG))
        dist = _frame(cam, under, HERO_FILL_H, centre)
        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 1.2, key=(-40.0, 20.0), fill=(70.0, 10.0),
                               fill_ratio=0.5)
        R.render_to(render_dir / f"{stem}_underside.png", cam, lamps)
        R.render_mask(work / "under_mask.png", cam, [under])
        out["shots"]["underside"] = {"path": f"Renders/BlackHat/{stem}_underside.png", "elevation_deg": -38.0,
                                     "note": "the plain inner woven skin; no head ring, lining or chin cord",
                                     **R.image_stats(render_dir / f"{stem}_underside.png", work / "under_mask.png")}
        _remove(lamps)
        bpy.data.objects.remove(under, do_unlink=True)
        # ------------------------------------------------------------ top (ortho, on the sweep)
        ground.hide_render = False
        top = _clone(lod0, "PREVIEW_Top")
        co = np.array([(top.matrix_world @ v.co)[:] for v in top.data.vertices])
        top.matrix_world = Matrix.Translation((0.0, 0.0, ground.location.z - co[:, 2].min())) @ top.matrix_world
        tc, _co = _bbox_centre(top)
        cam = rig["cam_flat"]
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (tc.x, tc.y, 2.5)
        cam.data.ortho_scale = D * 1.25 * R.RES_X / R.RES_Y
        cam.data.clip_end = 10.0
        cam.data.shift_x = cam.data.shift_y = 0.0
        bpy.context.view_layer.update()
        lamps = _product_lamps(cam, tc, 1.2, LIGHT_SCALE * 1.2)
        R.render_to(render_dir / f"{stem}_top.png", cam, lamps)
        R.render_mask(work / "top_mask.png", cam, [top])
        out["shots"]["top"] = {"path": f"Renders/BlackHat/{stem}_top.png",
                               "ortho_scale_mm": round(cam.data.ortho_scale * 1000, 1),
                               **R.image_stats(render_dir / f"{stem}_top.png", work / "top_mask.png")}
        _remove(lamps)
        # ------------------------------------------------------------ line sheet
        lcoll = bpy.data.collections.new("PREVIEW_SHEET")
        scene.collection.children.link(lcoll)
        top.matrix_world = Matrix.Translation((-0.22, 0.0, 0.0)) @ top.matrix_world
        tsz = spec.texture_size
        lines = [f"{spec.mesh_name}",
                 f"{2 * spec.R:.0f} mm across   {spec.mass_g:.0f} g",
                 f"LOD {tris[0]:,} / {tris[1]:,} / {tris[2]:,} tris",
                 "2 convex hulls   1 socket (HEAD)",
                 f"2 slots: straw, cloth   {tsz} px maps",
                 "recolourable: BaseColor = Detail x Tint"]
        lab = _label(lcoll, "PREVIEW_SheetText", chr(10).join(lines), (0.19, 0.0, 0.02), 0.022,
                     align_x="LEFT", align_y="CENTER")
        lab.rotation_euler = (0.0, 0.0, 0.0)
        lab.location = (0.13, 0.0, 0.02)
        cam.location = (0.0, 0.0, 2.5)
        cam.data.ortho_scale = (D + 0.62) * 1.02
        bpy.context.view_layer.update()
        lamps = _product_lamps(cam, Vector((0, 0, 0)), 1.2, LIGHT_SCALE * 1.2)
        R.render_to(render_dir / f"{stem}_linesheet.png", cam, lamps)
        out["shots"]["linesheet"] = {"path": f"Renders/BlackHat/{stem}_linesheet.png", "lines": lines}
        _remove(lamps)
        for o in list(lcoll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(lcoll)
        bpy.data.objects.remove(top, do_unlink=True)
        # ------------------------------------------------------------ wire (hero camera)
        coll = bpy.data.collections.new("PREVIEW_WIRE")
        scene.collection.children.link(coll)
        yaw_m = yaw @ lod0.matrix_world
        _wire_pair(lod0, coll, "Lod0", yaw_m)
        saved_world = scene.world
        scene.world = None
        ground.hide_render = True
        hero_c = rig["cam_hero"]
        R.render_to(render_dir / f"{stem}_wire.png", hero_c, ())
        out["shots"]["wire"] = {"path": f"Renders/BlackHat/{stem}_wire.png", "triangles": tris[0]}
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        # ------------------------------------------------------------ LOD strip (wire, from above-front)
        pitch = D * 1.08
        for i, obj in enumerate(lods):
            m = Matrix.Translation(((i - 1) * pitch, 0.0, 0.0)) @ yaw @ obj.matrix_world
            _wire_pair(obj, coll, f"Lod{i}", m, thickness=0.0009)
            lab = _label(coll, f"PREVIEW_LodLabel{i}", f"LOD{i}   {tris[i]:,} tris   screen {lod_screen_sizes[i]}",
                         ((i - 1) * pitch, -(0.5 * D + 0.06), 0.0), 0.028)
            lab.rotation_euler = (math.radians(55.0), 0.0, 0.0)
        cam = rig["cam_persp"]
        cam.data.lens = 50.0
        cam.location = (0.0, -2.9, 2.2)
        R._aim(cam, (0.0, 0.0, 0.03))
        cam.data.shift_x = cam.data.shift_y = 0.0
        R.render_to(render_dir / f"{stem}_lods.png", cam, ())
        out["shots"]["lods"] = {"path": f"Renders/BlackHat/{stem}_lods.png", "triangles": list(tris),
                                "screen_sizes": list(lod_screen_sizes)}
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(coll)
        scene.world = saved_world
        ground.hide_render = False
    finally:
        R.teardown(rig)
        for o, was in stash:
            try:
                o.hide_render = was
            except ReferenceError:
                pass
    return out


def lod_switch_frame(lods: List, cam_ref, bounds_radius_mm: float, screen_sizes: Sequence[float], out_png: Path,
                     work: Path, samples: int = 128, screen_h: int = 1080, mag: int = 4) -> Dict:
    """Each LOD shaded from the baked maps under the reference-view lights, at the size it has
    on a 1080p screen when it switches (the bounds sphere's diameter is screen_size x the screen
    height): [LODn-1 | LODn | 3x |diff|], magnified."""
    work = Path(work)
    info = {"screen_height_px": screen_h, "magnification": mag, "pairs": []}
    rows = []
    full_w = cam_ref.res[0]
    for sw_i in (1, 2):
        diam_px = screen_sizes[sw_i] * screen_h
        # the reference view frames the bounds sphere at about 700 px across: scale the render
        scale = diam_px / (2.0 * bounds_radius_mm * 796.7 / (2.6 * 300.0 * 1.0) / 1.0)
        k = max(0.05, min(1.0, diam_px / 700.0))
        res = (max(16, int(round(cam_ref.res[0] * k))), max(16, int(round(cam_ref.res[1] * k))))
        pair = []
        for lod in (sw_i - 1, sw_i):
            saved = LK.hide_all_but([lods[lod]])
            try:
                rig = LK.setup_reference(cam_ref, samples, res=res)
                a = LK.render_exr(work / f"lodswitch_{sw_i}_lod{lod}.exr")
                LK.teardown(rig)
            finally:
                LK.restore(saved)
            pair.append(LK.composite_white(a))
        diff = np.abs(pair[0] - pair[1])
        info["pairs"].append({"switch": f"LOD{sw_i - 1}->LOD{sw_i}", "screen_size": screen_sizes[sw_i],
                              "frame_px": list(res), "bounds_diameter_px": round(diam_px, 1),
                              "mean_abs_diff_stored": round(float(diff.mean()), 5),
                              "p99_abs_diff_stored": round(float(np.percentile(diff, 99)), 5)})
        mm = max(1, int(round(mag * 700.0 / max(res[0], 1) / 3.0)))
        f = lambda x: np.repeat(np.repeat(x, mm, 0), mm, 1)
        A, B, C = f(pair[0]), f(pair[1]), f(np.clip(diff * 3.0, 0, 1))
        g = np.ones((A.shape[0], 10, 3))
        rows.append(np.concatenate([A, g, B, g, C], 1))
    w = max(r.shape[1] for r in rows)
    sheet = []
    for r in rows:
        pad = np.ones((r.shape[0], w, 3))
        pad[:, :r.shape[1]] = r
        sheet += [pad, np.ones((14, w, 3))]
    LK.write_png(out_png, np.concatenate(sheet[:-1], 0))
    info["path"] = str(out_png)
    return info


__all__ = ["gallery", "lod_switch_frame"]
