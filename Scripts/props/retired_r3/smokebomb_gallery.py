#!/usr/bin/env python
"""props_lib.smokebomb_gallery - SM_SmokeBomb's renders, all from the BAKED maps.

    smokebomb_reference_view.png   the product shot's camera and light on white
                                   (props_lib.smokebomb_render; the fidelity frame)
    smokebomb_side_by_side.png     [reference | reference view] at the same size - a
                                   comparison sheet, the only file that holds reference
                                   pixels, and it ships nowhere
    smokebomb_back.png             the same rig with the ball turned 180 deg: the DESIGNED
                                   far side (REFERENCE_SPEC 9; study question 8)
    smokebomb_hero.png             3/4 on the pack's sweep, the pack's hero camera
    smokebomb_top.png              orthographic from above on the pack's sweep
    smokebomb_wire.png             LOD0's topology in the hero framing, flat-lit
    smokebomb_lods.png             the three LODs side by side, captioned

The pack's rig (props_lib.render: its world, ground sweep, 72 mm hero lens at 29 deg
elevation / -22 deg azimuth, 1600 x 900) is used as it is.  Two things are the ball's own:

* FRAMING.  The pack's framing helper solves a lens shift for a flat card; a ball needs
  none, so the camera is aimed at the ball's centre and dollied to a fixed fill.
* LIGHT.  The pack's hero lamps light a 0.10-albedo steel coat mostly from BEHIND the
  subject (a key at azimuth 152 deg, for specular); on a 0.04 matte cotton ball the face the
  camera sees is left unlit (measured: object p50 0.018, 64 % crushed).  The ball keeps the
  pack's world and sweep and is lit the way its own reference product shot is lit
  (REFERENCE_SPEC 3: a large soft key up-right of the lens, az +60 / el +64, and a fill from
  the left-rear, az -116 / el +4, at 0.67 of the key), placed relative to each camera.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import render as R
from . import smokebomb_render as SR
from .gallery import _drop_to_ground, _label

HERO_FILL_H = 0.72
#: product key power (W at 0.3 m, scaled with distance^2); measured so the hero's object
#: p50 sits near the reference view's own 0.12 on the pack's sweep
LIGHT_SCALE = 10.0
LOD_GAP_MM = 18.0


def _clone(obj, name, matrix=None):
    c = obj.copy()
    c.data = obj.data.copy()
    c.name = name
    c.parent = None
    c.matrix_world = matrix if matrix is not None else obj.matrix_world.copy()
    c.hide_render = False
    bpy.context.scene.collection.objects.link(c)
    return c


def _frame(camera, obj, fill_h: float, centre):
    """Aim at ``centre`` and dolly until the ball's projected height is ``fill_h``."""
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    co = [obj.matrix_world @ v.co for v in obj.data.vertices][::3]
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


def _product_lamps(camera, target, distance, scale):
    cam_dir = (Vector(camera.location) - Vector(target)).normalized()
    world_up = Vector((0.0, 0.0, 1.0))
    if abs(cam_dir.dot(world_up)) > 0.98:            # looking straight down: image-up is +Y
        world_up = Vector((0.0, 1.0, 0.0))
    right = world_up.cross(cam_dir).normalized()
    up = cam_dir.cross(right).normalized()
    # right-handed camera basis: cam_dir toward the camera, right = image right, up = image up
    right = -right if right.dot(camera.matrix_world.to_3x3() @ Vector((1, 0, 0))) < 0 else right
    lamps = []
    for name, az, el, power in (("SB_GalKey", 60.0, 64.0, 1.0), ("SB_GalFill", -116.0, 4.0, 0.67)):
        a, e = math.radians(az), math.radians(el)
        v = (cam_dir * (math.cos(e) * math.cos(a)) + right * (math.cos(e) * math.sin(a))
             + up * math.sin(e)).normalized()
        data = bpy.data.lights.new(name, "AREA")
        data.shape = "DISK"
        data.size = distance * 1.6
        data.energy = power * scale * (distance / 0.3) ** 2
        lo = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = Vector(target) + v * distance * 1.4
        R._aim(lo, Vector(target))
        lamps.append(lo)
    return lamps


def _wire_pair(source, coll, name: str, matrix, thickness: float = 0.00012):
    """A flat solid plus its wireframe, the wires pushed OUT along the radius (0.4 %).

    The paper bomb's helper (props_lib.gallery._wire_pair) lifts the wires 0.8 mm in +Z,
    which suits a flat card and buries the lower half of a ball's wires in its own solid."""
    from .paper_material import flat_emission
    centre = matrix.to_translation()
    solid = _clone(source, f"PREVIEW_{name}Solid", matrix)
    for parent in list(solid.users_collection):
        parent.objects.unlink(solid)
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(flat_emission(f"M_Wire_{name}_Solid", (0.150, 0.162, 0.185), 1.0))
    lift = Matrix.Translation(centre) @ Matrix.Scale(1.004, 4) @ Matrix.Translation(-centre) @ matrix
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


def _remove(objs):
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.lights.remove(data)


def outline_centre_mm(obj):
    """The fitted circle centre of the ball's orthographic outline seen from -Y, in mm
    (x right, z up), from the mesh itself: the max radius per 1 deg bin."""
    co = np.array([v.co[:] for v in obj.data.vertices]) * 1000.0
    x, z = co[:, 0], co[:, 2]
    th = np.degrees(np.arctan2(z, x)) % 360.0
    r = np.hypot(x, z)
    b = np.floor(th).astype(int)
    px, pz = [], []
    for k in range(360):
        m = b == k
        if m.any():
            i = np.argmax(np.where(m, r, -1))
            px.append(x[i])
            pz.append(z[i])
    px, pz = np.array(px), np.array(pz)
    A = np.stack([px, pz, np.ones_like(px)], axis=1)
    c, *_ = np.linalg.lstsq(A, px * px + pz * pz, rcond=None)
    cx, cz = c[0] / 2, c[1] / 2
    return float(cx), float(cz), float(math.sqrt(c[2] + cx * cx + cz * cz))


def reference_views(lod0, diameter_mm: float, ref_png: str, render_dir: Path, work: Path,
                    samples: int = 512, res: int = SR.REF_PX) -> Dict[str, object]:
    """The fidelity frame, its side-by-side, and the back view.  Other objects hidden."""
    stash = [(o, o.hide_render) for o in bpy.data.objects if o is not lod0]
    for o, _ in stash:
        o.hide_render = True
    lod0_state = lod0.hide_render
    lod0.hide_render = False
    out = {}
    try:
        cx, cz, rr = outline_centre_mm(lod0)
        rig = SR.setup_reference(diameter_mm, res=res, samples=samples, denoise=False)
        bpy.context.scene.cycles.filter_width = 1.5     # Blender's default (the round-2 adversary's render)
        # the reference frames the ball's OUTLINE at (627.4, 628.9) px; our outline's centre
        # sits (cx, cz) mm off the pivot (the tape stack is uneven), so the frame follows it
        # round 2: the shell's outline is centred on the pivot (the layer compensation keeps
        # it round), so the camera is NOT shifted by the vertex-based estimate (round 1's
        # shift moved the rendered outline 3.9 px off the reference centre); the estimate is
        # reported only
        frame_mm = rig["camera"].data.ortho_scale * 1000.0
        front = render_dir / "smokebomb_reference_view.png"
        SR.render_reference(front, work / "reference_view.exr", rig)
        SR.side_by_side(ref_png, front, render_dir / "smokebomb_side_by_side.png")
        out["reference_view"] = str(front)
        out["side_by_side"] = str(render_dir / "smokebomb_side_by_side.png")
        saved = lod0.matrix_world.copy()
        lod0.matrix_world = Matrix.Rotation(math.pi, 4, "Z") @ saved
        SR.render_reference(render_dir / "smokebomb_back.png", work / "back_view.exr", rig)
        lod0.matrix_world = saved
        out["back"] = str(render_dir / "smokebomb_back.png")
        out["camera"] = {"type": "ORTHO", "ortho_scale_mm": round(frame_mm, 3),
                         "shift": [round(rig["camera"].data.shift_x, 6), round(rig["camera"].data.shift_y, 6)],
                         "outline_centre_offset_mm": [round(cx, 4), round(cz, 4)],
                         "outline_radius_mm_geometric": round(rr, 4),
                         "resolution": [res, res], "samples": samples, "denoise": False,
                         "levels": rig["levels"]}
        SR.teardown(rig)
    finally:
        for o, was in stash:
            o.hide_render = was
        lod0.hide_render = lod0_state
    return out


def gallery(spec, objects, render_dir: Path, work: Path, samples: int = 256,
            light_scale: float = LIGHT_SCALE, bounds_radius_mm: float = 36.8) -> Dict[str, object]:
    render_dir = Path(render_dir)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    device = R.setup_render(samples=samples)
    # the reference-view stage leaves the scene writing 32-bit EXR; a 16-bit PNG would be
    # loaded back as a linear float buffer and every statistic below would read it wrong
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    rig = R.build_rig(spec, light_scale=1.0)
    out: Dict[str, object] = {"device": device, "samples": samples, "light_scale": light_scale,
                              "shots": {}}
    lod0 = objects[0]
    stash = [(o, o.hide_render) for o in objects]
    for o in objects:
        o.hide_render = True
    try:
        # ---------------------------------------------------------------- hero
        cam = rig["cam_hero"]
        cam.data.dof.use_dof = False
        az = math.radians(R.HERO_AZIMUTH_DEG)
        # the reference face (-Y) turned toward the camera's azimuth
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
        out["shots"]["hero"] = {"path": "Renders/SmokeBomb/smokebomb_hero.png",
                                "camera_distance_m": round(dist, 5), "lens_mm": cam.data.lens,
                                "elevation_deg": R.HERO_ELEVATION_DEG, "azimuth_deg": R.HERO_AZIMUTH_DEG,
                                "lighting": "REFERENCE_SPEC 3 product key / fill, relative to the camera",
                                **R.image_stats(render_dir / "smokebomb_hero.png", work / "hero_mask.png")}
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

        # ---------------------------------------------------------------- wire
        coll = bpy.data.collections.new("PREVIEW_WIRE")
        scene.collection.children.link(coll)
        _wire_pair(lod0, coll, "Lod0", hero_matrix, thickness=0.00012)
        saved_world = scene.world
        scene.world = None
        g_hidden = rig["ground"].hide_render
        rig["ground"].hide_render = True
        R.render_to(render_dir / "smokebomb_wire.png", rig["cam_hero"], ())
        lod0.data.calc_loop_triangles()
        out["shots"]["wire"] = {"path": "Renders/SmokeBomb/smokebomb_wire.png",
                                "triangles": len(lod0.data.loop_triangles),
                                "camera": "the hero camera and framing, flat-lit"}
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)

        # ---------------------------------------------------------------- LOD strip
        pitch = (spec.diameter_mm + LOD_GAP_MM) * 0.001
        tris = []
        sizes = spec.lod_screen_sizes(bounds_radius_mm)
        for i, obj in enumerate(objects):
            obj.data.calc_loop_triangles()
            tris.append(len(obj.data.loop_triangles))
            # the reference face (-Y) turned up to the top camera
            m = Matrix.Translation(((i - 1) * pitch, 0.0, 0.0)) @ Matrix.Rotation(-math.pi / 2, 4, "X") @ obj.matrix_world
            _wire_pair(obj, coll, f"Lod{i}", m, thickness=0.00012)
        for i in range(len(objects)):
            lab = _label(coll, f"PREVIEW_LodLabel{i}",
                         f"LOD{i}   {tris[i]:,} tris   screen size {sizes[i]}",
                         ((i - 1) * pitch, -(spec.diameter_mm * 0.5 + 9.0) * 0.001, 0.05), 3.6 * 0.001)
            lab.rotation_euler = (0.0, 0.0, 0.0)
        cam = rig["cam_flat"]
        cam.rotation_euler = (0.0, 0.0, 0.0)
        cam.location = (0.0, -0.004, 0.40)
        cam.data.shift_x = cam.data.shift_y = 0.0
        cam.data.ortho_scale = (3 * spec.diameter_mm + 2 * LOD_GAP_MM) * 1.12 * 0.001
        R.render_to(render_dir / "smokebomb_lods.png", cam, ())
        out["shots"]["lods"] = {"path": "Renders/SmokeBomb/smokebomb_lods.png", "triangles": tris,
                                "screen_sizes": sizes}
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


__all__ = ["reference_views", "gallery", "outline_centre_mm", "LIGHT_SCALE"]
