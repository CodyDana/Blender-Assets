#!/usr/bin/env python
"""props_lib.gallery - the paper bomb's six gallery shots, and the gates on them.

    paperbomb_hero.png      3/4 on the pack's ground: the product shot
    paperbomb_front.png     orthographic front flat: the print, to scale
    paperbomb_back.png      orthographic back: aged paper and the show-through
    paperbomb_raking.png    a close-up under a 6 deg key: the fibre, the cockling,
                            the creases - the reason a paper asset is not a decal
    paperbomb_wire.png      LOD0's topology over a flat-lit solid
    paperbomb_lods.png      the three LODs side by side, labelled

All six render through ``M_PaperBomb``, built from T_PaperBomb_BC / _ORM / _N / _M.  The
pack's rule is that a gallery image shows what the maps carry: a procedural material
rendered straight into a shot advertises a finish the buyer never receives.

THE BACK SHOT TURNS THE CARD OVER, NOT THE CAMERA
-------------------------------------------------
A camera underneath would look up at a card with the ground behind the lens and nothing
in frame but world, and it would need its own lamps.  Turning the object 180 deg about
its long axis is what a person does with a card, keeps the ground as backdrop, and keeps
the lighting identical to the front shot - so the two flats are comparable, which is
what a line sheet is for.

THE GATES
---------
``front_face_gate``  the flat front must correlate with the art as drawn and beat its
                     own mirror, its own flip and its own 180 deg rotation by a clear
                     margin.  This is what catches a mirrored island or an upside-down
                     PNG, which no amount of looking at a thumbnail reliably does.
``luminance gates``  the study asks for a stored object p50 of 0.62 - 0.72 with p99
                     below 0.95, against a backdrop that runs ~0.36 at the top of frame
                     to ~0.55 mid-frame with a whole-frame mean near 0.52 - the pack's
                     own numbers, so the tag sits in the same product line.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import render as R
from .paper_material import flat_emission

# The pack's answer to a long form is YAW, not a different camera (shuriken_lib.render
# 3.8: "a 150 mm bar on +X seen from the rig's -22 deg camera is end-on; turned it lies
# across the frame"), so the elevation and azimuth stay the pack's 29 / -22.
# 198 rather than 18: the rig's camera sits on +X, so world +X projects DOWN the frame -
# at 18 the tag lay diagonally but upside down, with its top edge at the bottom right.
HERO_YAW_DEG = 198.0
HERO_FILL_FRAC = (0.80, 0.74)
#: the form shot: low and nearly end-on, where a 4.2 mm curl and a 7 deg crease read
PERSP_YAW_DEG = 205.0
PERSP_ELEVATION_DEG = 11.0
PERSP_AZIMUTH_DEG = -34.0
PERSP_FILL_FRAC = (0.86, 0.56)
FLAT_FILL = 0.86
LOD_GAP_MM = 26.0
LABEL_MM = 5.4

#: the study's own target for this asset, and the pack's backdrop.
#:
#: THIS BAND IS RELATIVE TO THE PAPER, not absolute.  It was calibrated when the sheet's
#: albedo was ``PALETTE_FLOORED.paper`` - stored luma 0.797 - and it is a statement about
#: the LIGHTING RIG: is the card exposed the way the pack exposes things?  REFERENCE_SPEC
#: row 15 moves the paper to the guide's measured #F6E6C6, stored luma 0.906, on purpose,
#: and a card that is 14 % lighter by design renders 14 % lighter.  Holding the band
#: fixed would have meant darkening the lamps until the render hid the very change the
#: reference asked for, so the band travels with the declared palette and
#: ``object_p50_band`` is where that is done.  The floored policy still measures against
#: exactly the study's numbers.
STUDY_OBJECT_P50_BAND = (0.62, 0.72)
STUDY_PAPER_STORED_LUMA = 0.7965          # PALETTE_FLOORED.paper, the band's calibration
OBJECT_P50_BAND = STUDY_OBJECT_P50_BAND   # kept as a name; see object_p50_band()
OBJECT_P99_MAX = 0.95
BACKDROP_MEAN_BAND = (0.40, 0.64)


def _stored_luma(linear_rgb) -> float:
    a = [max(0.0, min(1.0, float(c))) for c in linear_rgb]
    s = [c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055 for c in a]
    return 0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2]


def object_p50_band(ink_floor: str | None = None) -> tuple:
    """The study's exposure band, carried onto whatever paper this policy ships."""
    from . import paperbomb_art as art

    pal = art.PALETTES.get(ink_floor or art.DEFAULT_INK_FLOOR, art.PALETTE_REFERENCE)
    k = _stored_luma(pal.paper) / STUDY_PAPER_STORED_LUMA
    return (round(STUDY_OBJECT_P50_BAND[0] * k, 4), round(STUDY_OBJECT_P50_BAND[1] * k, 4))


def _clone(obj, name: str, matrix=None):
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = name
    copy.parent = None
    copy.matrix_world = matrix if matrix is not None else obj.matrix_world.copy()
    # the shipped LODs are hidden from the renderer while the gallery runs, and
    # Object.copy() carries that flag across
    copy.hide_render = False
    bpy.context.scene.collection.objects.link(copy)
    return copy


def _label(coll, name: str, text: str, location, size: float,
           align_x: str = "CENTER", align_y: str = "CENTER"):
    """A flat-lit caption, turned so it reads upright under the LOD sheet's camera.

    That camera is rolled -90 deg about Z (so the tag's long axis runs up the frame), and
    a text object advances along its own +X, so the text has to be rolled -90 deg too or
    it reads bottom-to-top across the mesh - which is what the first sheet did.
    """
    data = bpy.data.curves.new(name, type="FONT")
    data.body = text
    data.size = size
    data.align_x = align_x
    data.align_y = align_y
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    obj.data.materials.append(flat_emission(f"M_{name}", R.LABEL_COLOUR, 1.0))
    return obj


def _wire_pair(source, coll, name: str, matrix, thickness: float = 0.00018):
    solid = _clone(source, f"PREVIEW_{name}Solid", matrix)
    for parent in list(solid.users_collection):
        parent.objects.unlink(solid)
    coll.objects.link(solid)
    solid.data.materials.clear()
    solid.data.materials.append(flat_emission(f"M_Wire_{name}_Solid", (0.150, 0.162, 0.185), 1.0))

    lift = Matrix.Translation((0.0, 0.0, 0.0008)) @ matrix
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


def render_all(spec, plan, objects, render_dir: Path, work_dir: Path,
               quick: bool = False, samples: Optional[int] = None,
               light_scale: float = 1.0, ink_floor: Optional[str] = None) -> Dict[str, object]:
    """Render the six shots and gate them.  The rig is torn down before returning."""
    render_dir = Path(render_dir)
    diag = Path(work_dir) / "diag"
    render_dir.mkdir(parents=True, exist_ok=True)
    diag.mkdir(parents=True, exist_ok=True)

    n = samples or (48 if quick else 320)
    device = R.setup_render(samples=n)
    rig = R.build_rig(spec, light_scale=light_scale)
    scene = bpy.context.scene
    out: Dict[str, object] = {"device": device, "samples": n, "light_scale": light_scale,
                              "ink_floor": ink_floor,
                              "shots": {}, "gates": {}}

    lod0, lod1, lod2 = objects
    stash = [(o, o.hide_render) for o in objects]
    for o in objects:
        o.hide_render = True

    try:
        # ---------------------------------------------------------- hero
        hero = _clone(lod0, "PREVIEW_Hero",
                      Matrix.Rotation(math.radians(HERO_YAW_DEG), 4, "Z") @ lod0.matrix_world)
        _drop_to_ground(hero, rig["ground"])
        hero_matrix = hero.matrix_world.copy()          # the wire shot reuses this framing
        fitted = R.fit_perspective(rig["cam_hero"], [hero], *HERO_FILL_FRAC)
        shift = R.centre_perspective(rig["cam_hero"], [hero], R.RES_X, R.RES_Y)
        dof = R.solve_depth_of_field(rig["cam_hero"], [hero], R.RES_X)
        scale = fitted / R.HERO_RIG_REFERENCE_M
        saved = R.scale_lamps(rig["hero"], scale)
        R.render_to(render_dir / "paperbomb_hero.png", rig["cam_hero"], rig["hero"])
        R.render_mask(diag / "hero_mask.png", rig["cam_hero"], [hero])
        R.restore_lamps(saved)
        out["shots"]["hero"] = {
            "path": "Renders/PaperBomb/paperbomb_hero.png",
            "camera_distance_m": round(fitted, 5), "lamp_scale": round(scale, 4),
            "yaw_deg": HERO_YAW_DEG, "composition": shift, "depth_of_field": dof,
            **R.image_stats(render_dir / "paperbomb_hero.png", diag / "hero_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_hero.png",
                                             diag / "hero_mask.png"),
        }
        bpy.data.objects.remove(hero, do_unlink=True)

        # --------------------------------------------------------- flats
        flat_cam = rig["cam_flat"]
        flat_cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
        flat_cam.location = (0.0, 0.0, 0.40)
        flat_cam.data.ortho_scale = (spec.height_mm / FLAT_FILL) * 0.001 * R.RES_X / R.RES_Y

        front = _clone(lod0, "PREVIEW_Front")
        R.render_to(render_dir / "paperbomb_front.png", flat_cam, rig["flat"])
        R.render_mask(diag / "front_mask.png", flat_cam, [front])
        out["shots"]["front"] = {
            "path": "Renders/PaperBomb/paperbomb_front.png",
            "ortho_scale_mm": round(flat_cam.data.ortho_scale * 1000.0, 2),
            "note": "camera up is +X (the top of the tag); camera right is -Y (the right of the print)",
            **R.image_stats(render_dir / "paperbomb_front.png", diag / "front_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_front.png",
                                             diag / "front_mask.png"),
        }
        bpy.data.objects.remove(front, do_unlink=True)

        # turn the CARD over about its long axis, not the camera
        back = _clone(lod0, "PREVIEW_Back",
                      Matrix.Rotation(math.radians(180.0), 4, "X") @ lod0.matrix_world)
        R.render_to(render_dir / "paperbomb_back.png", flat_cam, rig["flat"])
        R.render_mask(diag / "back_mask.png", flat_cam, [back])
        out["shots"]["back"] = {
            "path": "Renders/PaperBomb/paperbomb_back.png",
            "note": "the card is turned 180 deg about its long axis; the camera and lamps do not move",
            **R.image_stats(render_dir / "paperbomb_back.png", diag / "back_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_back.png",
                                             diag / "back_mask.png"),
        }
        bpy.data.objects.remove(back, do_unlink=True)

        # -------------------------------------------------------- raking
        rake_obj = _clone(lod0, "PREVIEW_Rake")
        cam = rig["cam_rake"]
        target = Vector((0.020, 0.0, 0.002))
        cam.location = Vector(R._polar(0.24, 34.0, -28.0)) + target
        R._aim(cam, target)
        cam.data.lens = 110.0
        R.render_to(render_dir / "paperbomb_raking.png", rig["cam_rake"], rig["rake"])
        R.render_mask(diag / "raking_mask.png", rig["cam_rake"], [rake_obj])
        out["shots"]["raking"] = {
            "path": "Renders/PaperBomb/paperbomb_raking.png",
            "key_elevation_deg": R.RAKE_ELEVATION_DEG, "lens_mm": cam.data.lens,
            **R.image_stats(render_dir / "paperbomb_raking.png", diag / "raking_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_raking.png",
                                             diag / "raking_mask.png"),
        }
        # the same frame with the Normal input unplugged: the control for the relief gate
        material = rake_obj.data.materials[0]
        tree = material.node_tree
        bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        # `socket is bsdf.inputs["Normal"]` is FALSE in bpy - each access builds a fresh
        # wrapper - so the first version of this found no link, removed nothing, and the
        # gate compared a frame with itself and reported a ratio of exactly 1.000.
        link = next((l for l in tree.links
                     if l.to_node == bsdf and l.to_socket.name == "Normal"), None)
        from_socket = link.from_socket if link else None
        if link is None:
            raise RuntimeError("M_PaperBomb has no Normal input connected: the relief "
                               "gate cannot run and the map is not being used")
        tree.links.remove(link)
        R.render_to(diag / "relief_off.png", rig["cam_rake"], rig["relief"])
        if from_socket is not None:
            tree.links.new(from_socket, bsdf.inputs["Normal"])
        R.render_to(diag / "relief_on.png", rig["cam_rake"], rig["relief"])
        out["gates"]["relief"] = R.relief_gate(diag / "relief_on.png",
                                               diag / "relief_off.png",
                                               diag / "raking_mask.png")
        out["gates"]["relief"]["note"] = (
            "measured on a DIAGNOSTIC pair under a 6 deg key nearly opposite the "
            "camera, not on the shipped close-up: that arrangement makes the normal "
            "map modulate the specular lobe, which is the loudest test of whether the "
            "map is connected and doing work, and is also exactly the lighting that "
            "veiled the ink in the first build's gallery image.  "
            + out["gates"]["relief"].get("note", ""))
        bpy.data.objects.remove(rake_obj, do_unlink=True)

        # ---------------------------------------------------------- wire
        wire_coll = bpy.data.collections.new("PREVIEW_WIRE")
        scene.collection.children.link(wire_coll)
        _wire_pair(lod0, wire_coll, "Lod0", hero_matrix)
        saved_world = scene.world
        scene.world = None
        ground_hidden = rig["ground"].hide_render
        rig["ground"].hide_render = True
        R.render_to(render_dir / "paperbomb_wire.png", rig["cam_hero"], ())
        lod0.data.calc_loop_triangles()
        out["shots"]["wire"] = {"path": "Renders/PaperBomb/paperbomb_wire.png",
                                "camera": "the hero camera and framing, flat-lit",
                                "triangles": len(lod0.data.loop_triangles)}

        # ---------------------------------------------------------- LODs
        for obj in list(wire_coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        # the screen sizes printed on the sheet are the SHIPPED ones: the pack rule
        # applied to the mesh's MEASURED bounds radius, not to the spec's estimate of it
        co = np.array([v.co[:] for v in lod0.data.vertices], np.float64) * 1000.0
        half = np.ptp(co, axis=0) * 0.5
        screen_sizes = spec.lod_screen_sizes(float(np.sqrt((half ** 2).sum())))
        out["lod_screen_sizes_on_the_sheet"] = screen_sizes
        pitch = (spec.width_mm + LOD_GAP_MM) * 0.001
        for i, obj in enumerate(objects):
            offset = Matrix.Translation(((0.0), (1 - i) * pitch, 0.0))
            _wire_pair(obj, wire_coll, f"Lod{i}", offset @ obj.matrix_world)
            obj.data.calc_loop_triangles()
            _label(wire_coll, f"PREVIEW_LodLabel{i}",
                   f"LOD{i}    {len(obj.data.loop_triangles)} tris\n"
                   f"screen size {screen_sizes[i]}",
                   ((-spec.height_mm * 0.5 - 15.0) * 0.001, (1 - i) * pitch, 0.002),
                   LABEL_MM * 0.001)
        lod_cam = rig["cam_flat"]
        lod_cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
        lod_cam.location = (0.0, 0.0, 0.40)
        lod_cam.location.x = -7.0 * 0.001                # room for the captions below
        span = 3 * spec.width_mm + 2 * LOD_GAP_MM
        lod_cam.data.ortho_scale = max(span * 1.14,
                                       (spec.height_mm + 44.0) * R.RES_X / R.RES_Y) * 0.001
        R.render_to(render_dir / "paperbomb_lods.png", lod_cam, ())
        out["shots"]["lods"] = {
            "path": "Renders/PaperBomb/paperbomb_lods.png",
            "triangles": [len(o.data.loop_triangles) for o in objects],
        }
        scene.world = saved_world
        rig["ground"].hide_render = ground_hidden
        for obj in list(wire_coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(wire_coll)

        # --------------------------------------------------- persp (the form)
        # The hero sells the print; this one sells the SHAPE.  A near-end-on camera is
        # the only view in which a curl reads as a curl, and the whole reason this is a
        # mesh and not a decal is the form, so the line gets a shot of it.
        persp = _clone(lod0, "PREVIEW_Persp",
                       Matrix.Rotation(math.radians(PERSP_YAW_DEG), 4, "Z") @ lod0.matrix_world)
        _drop_to_ground(persp, rig["ground"])
        cam = rig["cam_persp"]
        cam.data.lens = R.HERO_LENS_MM
        cam.location = Vector(R._polar(0.30, PERSP_ELEVATION_DEG, PERSP_AZIMUTH_DEG))
        R._aim(cam, (0.0, 0.0, 0.004))
        fitted_p = R.fit_perspective(cam, [persp], *PERSP_FILL_FRAC)
        R.centre_perspective(cam, [persp], R.RES_X, R.RES_Y)
        saved = R.scale_lamps(rig["hero"], fitted_p / R.HERO_RIG_REFERENCE_M)
        R.render_to(render_dir / "paperbomb_persp.png", cam, rig["hero"])
        R.render_mask(diag / "persp_mask.png", cam, [persp])
        R.restore_lamps(saved)
        out["shots"]["persp"] = {
            "path": "Renders/PaperBomb/paperbomb_persp.png",
            "camera_distance_m": round(fitted_p, 5),
            "yaw_deg": PERSP_YAW_DEG, "elevation_deg": PERSP_ELEVATION_DEG,
            "note": "low, near end-on: the curl, the two creases and the dog-ear in "
                    "silhouette - the shot that says this is paper and not a decal",
            **R.image_stats(render_dir / "paperbomb_persp.png", diag / "persp_mask.png"),
            "ink_colour": R.ink_colour_stats(render_dir / "paperbomb_persp.png",
                                             diag / "persp_mask.png"),
        }
        bpy.data.objects.remove(persp, do_unlink=True)

        # ----------------------------------------------------------- lodgrind
        # The pack's own LOD grind: each LOD under the hero rig with its band printed
        # under it, three panels in one 1600 x 900 frame.  Renders/Shuriken carries one
        # for every form in the line and Renders/PaperBomb did not.
        grind = _lod_grind(spec, objects, rig, render_dir, diag, screen_sizes=None)
        out["shots"]["lodgrind"] = grind

        # ---------------------------------------------------------- line sheet
        out["shots"]["linesheet"] = _line_sheet(spec, objects, rig, render_dir, diag)

        # --------------------------------------------------------- gates
        out["gates"]["front_face"] = _front_face_gate(spec, plan, render_dir, diag)
        out["gates"]["luminance"] = _luminance_gate(out["shots"], ink_floor)
        # the gate the first build had no equivalent of: every frame must show the
        # SAME ink and the same red, measured against the flat front
        out["gates"]["ink_consistency"] = R.ink_consistency_gate(out["shots"])
    finally:
        R.teardown(rig)
        for obj, was in stash:
            obj.hide_render = was
    return out


def _lod_grind(spec, objects, rig, render_dir: Path, diag: Path,
               screen_sizes=None) -> Dict[str, object]:
    """The pack's LOD grind: three panels, one per LOD, each captioned with its band.

    Renders/Shuriken ships one of these for every form in the line and
    Renders/PaperBomb did not, so the two galleries did not sit together.  Each panel is
    a full render at a third of the frame width under the hero rig at the hero framing,
    with its caption as a text object PARENTED TO THE CAMERA - which is what keeps it
    crisp and square to the frame instead of foreshortened onto the ground.  The three
    are then stitched into one 1600 x 900.
    """
    scene = bpy.context.scene
    lod0 = objects[0]
    co = np.array([v.co[:] for v in lod0.data.vertices], np.float64) * 1000.0
    half = np.ptp(co, axis=0) * 0.5
    sizes = screen_sizes or spec.lod_screen_sizes(float(np.sqrt((half ** 2).sum())))
    bands = [f"screen size > {sizes[1]:.4f}",
             f"screen size {sizes[2]:.4f} - {sizes[1]:.4f}",
             f"screen size < {sizes[2]:.4f}"]

    # Rendered at the full 1600 x 900 and cropped to the middle third, NOT at a third
    # of the width: ``centre_perspective``'s lens-shift formula is written for the
    # pack's landscape frame and puts the card off the side if the render is portrait.
    panel_w = R.RES_X // 3
    x0 = (R.RES_X - panel_w) // 2
    coll = bpy.data.collections.new("PREVIEW_GRIND")
    scene.collection.children.link(coll)
    # a camera of its own: cam_hero carries the hero shot's own lens shift
    cam_data = bpy.data.cameras.new("PREVIEW_CamGrind")
    cam_data.lens = R.HERO_LENS_MM
    cam = bpy.data.objects.new("PREVIEW_CamGrind", cam_data)
    coll.objects.link(cam)
    cam.location = R._polar(0.42, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG)
    R._aim(cam)
    images = []
    captions = []
    saved = None
    try:
        for i, obj in enumerate(objects):
            shot = _clone(obj, f"PREVIEW_Grind{i}",
                          Matrix.Rotation(math.radians(HERO_YAW_DEG), 4, "Z") @ obj.matrix_world)
            _drop_to_ground(shot, rig["ground"])
            if i == 0:
                fitted = R.fit_perspective(cam, [shot], 0.295, 0.46)
                R.centre_perspective(cam, [shot], R.RES_X, R.RES_Y, target=(0.5, 0.46))
                saved = R.scale_lamps(rig["hero"], fitted / R.HERO_RIG_REFERENCE_M)
            obj.data.calc_loop_triangles()
            caption = f"LOD{i}   {len(obj.data.loop_triangles):,} tris   {bands[i]}"
            label = _label(coll, f"PREVIEW_GrindLabel{i}", caption, (0.0, 0.0, 0.0), 0.00082)
            # square to the frame: parented to the camera, sitting in its local -Z
            label.rotation_euler = (0.0, 0.0, 0.0)
            label.parent = cam
            label.matrix_parent_inverse = Matrix.Identity(4)
            label.location = (0.0, -0.0132, -0.115)
            R.render_to(diag / f"grind_lod{i}.png", cam, rig["hero"])
            images.append(R.load_pixels(diag / f"grind_lod{i}.png")[..., :3][:, x0:x0 + panel_w])
            captions.append(caption)
            bpy.data.objects.remove(label, do_unlink=True)
            bpy.data.objects.remove(shot, do_unlink=True)
    finally:
        if saved is not None:
            R.restore_lamps(saved)
        for obj in list(coll.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Camera):
                bpy.data.cameras.remove(data)
        bpy.data.collections.remove(coll)

    h = images[0].shape[0]
    sheet = np.zeros((h, panel_w * 3, 3), np.float32)
    for i, img in enumerate(images):
        sheet[:, i * panel_w:(i + 1) * panel_w] = img
    for i in range(1, 3):                       # a hairline between the panels
        sheet[:, i * panel_w - 1:i * panel_w + 1] = 0.10
    out = render_dir / "paperbomb_lodgrind.png"
    R._write_png(out, sheet)
    return {"path": "Renders/PaperBomb/paperbomb_lodgrind.png",
            "captions": captions,
            "triangles": [len(o.data.loop_triangles) for o in objects],
            "screen_sizes": sizes,
            "note": "one render per LOD at a third of the frame width under the hero "
                    "rig, captions parented to the camera, stitched"}


def _line_sheet(spec, objects, rig, render_dir: Path, diag: Path) -> Dict[str, object]:
    """One labelled entry in the pack's line-sheet style, ready to drop into a combined sheet.

    Renders/Shuriken/modern_line_sheet.png carries a name, a size and a mass for every
    form in that pack.  This is the paper bomb's row, at the same 1600 x 900, so the tag
    can be set beside the steel when the two lines are sold together.
    """
    coll = bpy.data.collections.new("PREVIEW_SHEET")
    bpy.context.scene.collection.children.link(coll)
    lod0 = objects[0]
    card = _clone(lod0, "PREVIEW_SheetCard")
    for parent in list(card.users_collection):
        parent.objects.unlink(card)
    coll.objects.link(card)
    card.matrix_world = Matrix.Translation((0.0, 0.048, 0.0)) @ lod0.matrix_world

    lod0.data.calc_loop_triangles()
    tris = [0, 0, 0]
    for i, o in enumerate(objects):
        o.data.calc_loop_triangles()
        tris[i] = len(o.data.loop_triangles)
    mass_g = spec.mass_g
    lines = [
        f"{spec.mesh_name}",
        f"{spec.width_mm:.0f} x {spec.height_mm:.0f} x {spec.thickness_mm:.2f} mm     {mass_g:.2f} g",
        f"LOD {tris[0]:,} / {tris[1]:,} / {tris[2]:,} tris     1 convex hull     4 sockets",
        f"{spec.texture_stem}_BC / _ORM / _N / _M     {spec.texture_size} px"
        f"     {spec.texel_density_px_per_cm():.0f} px/cm",
    ]
    # left-aligned and clear of the card: a text object advances along its own +X, and
    # this camera's -90 deg roll maps that to world -Y, i.e. to the right of frame
    _label(coll, "PREVIEW_SheetText", "\n".join(lines),
           (0.006, -0.018, 0.0), 0.0034, align_x="LEFT", align_y="CENTER")

    cam = rig["cam_flat"]
    cam.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    cam.location = (0.0, 0.0, 0.40)
    cam.data.ortho_scale = (spec.height_mm + 34.0) * 0.001 * R.RES_X / R.RES_Y
    R.render_to(render_dir / "paperbomb_linesheet.png", cam, rig["flat"])
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(coll)
    return {"path": "Renders/PaperBomb/paperbomb_linesheet.png", "lines": lines}


def _drop_to_ground(obj, ground):
    """Sit the card on the sweep: its lowest vertex just touches the ground plane."""
    co = np.array([(obj.matrix_world @ v.co)[2] for v in obj.data.vertices], np.float64)
    obj.matrix_world = Matrix.Translation((0.0, 0.0, ground.location.z - co.min())) @ obj.matrix_world


def _front_face_gate(spec, plan, render_dir: Path, diag: Path) -> Dict[str, object]:
    """Read the SHIPPED BC map back and correlate the flat front render against it."""
    path = Path(diag).parent.parent.parent / "Exports" / "PaperBomb" / "Textures" / f"{spec.texture_stem}_BC.png"
    if not path.is_file():
        return {"passed": False, "reason": f"{path} not found"}
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        image.colorspace_settings.name = "Non-Color"
        w, h = image.size
        buf = np.empty(w * h * 4, np.float32)
        image.pixels.foreach_get(buf)
        stored = np.ascontiguousarray(buf.reshape(h, w, 4)[::-1, :, :3]).astype(np.float64)
    finally:
        bpy.data.images.remove(image)
    linear = np.where(stored <= 0.04045, stored / 12.92, ((stored + 0.055) / 1.055) ** 2.4)
    return R.front_face_gate(render_dir / "paperbomb_front.png", diag / "front_mask.png",
                             linear, plan)


def _luminance_gate(shots: Dict[str, object],
                    ink_floor: str | None = None) -> Dict[str, object]:
    band = object_p50_band(ink_floor)
    out: Dict[str, object] = {"band_p50": list(band), "max_p99": OBJECT_P99_MAX,
                              "study_band_p50": list(STUDY_OBJECT_P50_BAND),
                              "ink_floor": ink_floor,
                              "band_note": ("the study's band scaled by this policy's "
                                            "paper stored luma over the 0.7965 it was "
                                            "calibrated on; see object_p50_band"),
                              "backdrop_mean_band": list(BACKDROP_MEAN_BAND), "shots": {}}
    ok = True
    for name in ("hero", "front", "back"):
        shot = shots.get(name) or {}
        lum = shot.get("object_luminance") or {}
        back = shot.get("backdrop") or {}
        entry = {
            "p50": lum.get("p50"), "p99": lum.get("p99"), "mean": lum.get("mean"),
            "clipped_fraction": lum.get("clipped_fraction"),
            "backdrop_mean": back.get("mean"), "frame_mean": shot.get("frame_mean"),
        }
        entry["p50_in_band"] = bool(lum.get("p50") is not None
                                    and band[0] <= lum["p50"] <= band[1])
        entry["p99_ok"] = bool(lum.get("p99") is not None and lum["p99"] <= OBJECT_P99_MAX)
        ok = ok and entry["p50_in_band"] and entry["p99_ok"]
        out["shots"][name] = entry
    out["passed"] = ok
    return out


__all__ = ["render_all", "OBJECT_P50_BAND", "OBJECT_P99_MAX",
           "PERSP_YAW_DEG", "PERSP_ELEVATION_DEG"]
