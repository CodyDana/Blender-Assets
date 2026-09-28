from pathlib import Path
p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/blackhat_gallery.py")
s = p.read_text(encoding="utf8")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('''    hero / raking / underside   the sweep is HIDDEN: the tails are the lowest thing on the hat,
                                so standing it on the sweep would float the rim 9 cm up or push the
                                tails through the floor; the world's dark ramp is the backdrop
    top / line sheet            on the sweep, seen from above (the tails' tips touch it)
    wire / LOD strip            flat-lit emission, as the pack's''', '''    hero / raking / underside   the sweep is HIDDEN: the tails are the lowest thing on the hat,
                                so standing it on the sweep would float the rim 9 cm up or push the
                                tails through the floor; the world's dark ramp is the backdrop
    top                         on the sweep, seen from above (the tails' tips touch it)
    line sheet                  the house framing (final pass): a 3/4 view at the hero's angle on
                                the left, a top view beside it, a small caption as the smoke bomb's
    wire                        a 3/4 view from above (40 deg) so the ribs, band and rim read
    LOD strip                   flat-lit emission, as the pack's
    Every shaded shot uses the hero's black-hat exposure (final pass: round 1 lit the underside
    and top 8x brighter, which made the black tails and lashings read nearly white / silver).''')
rep('''LIGHT_SCALE = 10.0
HERO_FILL_H = 0.70''', '''LIGHT_SCALE = 10.0
HERO_FILL_H = 0.70
#: the black hat's product-lamp scale (the hero's), used by every shaded gallery shot
HAT_LIGHT = 0.15
#: the line sheet's caption: the smoke bomb's line pitch (its 0.0019 m text in a 104 mm tall frame)
CAPTION_PX = 900.0 * 0.0019 / (0.185 * 900.0 / 1600.0)''')
rep('''        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * 1.2, key=(-40.0, 20.0), fill=(70.0, 10.0),
                               fill_ratio=0.5)''', '''        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * HAT_LIGHT * 1.6, key=(-40.0, 20.0), fill=(70.0, 10.0),
                               fill_ratio=0.5)''')
rep('''                                     "note": "the plain inner woven skin; no head ring, lining or chin cord",''',
    '''                                     "note": "the plain inner woven skin (the reference never shows the underside); "
                                             "no head ring, lining or chin cord; lit at the hero's black-hat exposure",''')
rep('''        lamps = _product_lamps(cam, tc, 1.2, LIGHT_SCALE * 1.2)
        R.render_to(render_dir / f"{stem}_top.png", cam, lamps)''', '''        lamps = _product_lamps(cam, tc, 1.2, LIGHT_SCALE * HAT_LIGHT * 1.6)
        R.render_to(render_dir / f"{stem}_top.png", cam, lamps)''')
i0 = s.index("        # ------------------------------------------------------------ line sheet")
i1 = s.index("        # ------------------------------------------------------------ wire (hero camera)")
s = s[:i0] + '''        bpy.data.objects.remove(top, do_unlink=True)
        ground.hide_render = True
        # ------------------------------------------------------------ line sheet (house framing)
        out["shots"]["linesheet"] = _line_sheet(spec, lod0, rig, yaw, render_dir, tris)
''' + s[i1:]
rep('''        yaw_m = yaw @ lod0.matrix_world
        _wire_pair(lod0, coll, "Lod0", yaw_m)
        saved_world = scene.world
        scene.world = None
        ground.hide_render = True
        hero_c = rig["cam_hero"]
        R.render_to(render_dir / f"{stem}_wire.png", hero_c, ())
        out["shots"]["wire"] = {"path": f"Renders/BlackHat/{stem}_wire.png", "triangles": tris[0]}''',
    '''        yaw_m = yaw @ lod0.matrix_world
        wsolid, _wl = _wire_pair(lod0, coll, "Lod0", yaw_m)
        saved_world = scene.world
        scene.world = None
        ground.hide_render = True
        hero_c = rig["cam_hero"]
        # a 3/4 view from ABOVE (round 1 reused the camera the underside shot had moved below the rim)
        wc, _co = _bbox_centre(wsolid)
        hero_c.location = wc + Vector(R._polar(1.5, 40.0, R.HERO_AZIMUTH_DEG))
        _frame(hero_c, wsolid, 0.80, wc)
        R.render_to(render_dir / f"{stem}_wire.png", hero_c, ())
        out["shots"]["wire"] = {"path": f"Renders/BlackHat/{stem}_wire.png", "triangles": tris[0],
                                "camera": "3/4 from above, elevation 40 deg, the hero's azimuth"}''')
rep('''def lod_switch_frame(''', '''def _cam_point(cam, u: float, v: float, depth: float) -> Vector:
    """World point seen at image (u, v) (0..1, v up) at camera-space depth ``depth`` (m)."""
    scene = bpy.context.scene
    fr = [Vector(c) for c in cam.data.view_frame(scene=scene)]      # tr, br, bl, tl (camera space)
    tr, br, bl, tl = fr
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    p = bot.lerp(top, v)
    p = p * (depth / -p.z)
    return cam.matrix_world @ p


def _line_sheet(spec, lod0, rig, yaw, render_dir: Path, tris, stem: str = "blackhat"):
    """The house line sheet (Renders/SmokeBomb/smokebomb_linesheet.png's framing, the shuriken
    sheet's 3/4 + top pairing): 1600 x 900, the hat at the hero's 3/4 angle on the left, a top
    view (the same hat turned to face the camera) at the right, the caption at the smoke bomb's
    size and place.  One render, lit by the hero's black-hat lamps; the sweep is hidden (the tails
    hang below the rim), the world ramp is the backdrop."""
    scene = bpy.context.scene
    coll = bpy.data.collections.new("PREVIEW_SHEET")
    scene.collection.children.link(coll)
    made = []
    cam = rig["cam_hero"]
    cam.data.dof.use_dof = False
    cam.data.clip_start = 0.05
    try:
        hero = _clone(lod0, "PREVIEW_SheetHero", yaw @ lod0.matrix_world)
        made.append(hero)
        centre, _co = _bbox_centre(hero)
        cam.location = centre + Vector(R._polar(1.5, R.HERO_ELEVATION_DEG, R.HERO_AZIMUTH_DEG))
        dist = _frame(cam, hero, 0.62, centre, fill_w=0.50)
        # the 3/4 view on the left: its centre at 29 % of the width
        cam.data.shift_x += 0.21
        cam.data.shift_y += 0.01
        bpy.context.view_layer.update()
        # the top view: the hat turned so its crown faces the camera, knot to the right
        cw = cam.matrix_world.to_3x3()
        right, up, back = cw.col[0].normalized(), cw.col[1].normalized(), cw.col[2].normalized()
        # object X (forward) -> image down, Y (the knot side) -> image right, Z (crown) -> the camera
        Mrot = Matrix([[-up.x, right.x, back.x], [-up.y, right.y, back.y], [-up.z, right.z, back.z]])
        top = _clone(lod0, "PREVIEW_SheetTop", Mrot.to_4x4() @ lod0.matrix_world)
        made.append(top)
        tc_local, _ = _bbox_centre(top)
        target = _cam_point(cam, 0.79, 0.34, dist * 2.25)
        top.matrix_world = Matrix.Translation(target - tc_local) @ top.matrix_world
        bpy.context.view_layer.update()
        # the caption, parented to the camera, at the smoke bomb's line pitch
        depth = 0.30
        pts = [_cam_point(cam, 0.0, 0.5, depth), _cam_point(cam, 1.0, 0.5, depth)]
        px_per_m = 1600.0 / (pts[1] - pts[0]).length
        size = CAPTION_PX / px_per_m
        lines = [f"{spec.mesh_name}",
                 f"{2 * spec.R:.0f} mm across     {spec.mass_g:.0f} g",
                 f"LOD {tris[0]:,} / {tris[1]:,} / {tris[2]:,} tris     1 convex hull     1 socket (HEAD)",
                 f"T_BlackHat_Straw_ / _Cloth_  BC, ORM, N, Detail  {spec.texture_size} px",
                 "recolourable: BaseColor = Tint x (Bias + Scale x Detail), Tint = the mean colour"]
        lab = _label(coll, "PREVIEW_SheetText", chr(10).join(lines), (0, 0, 0), size, align_x="LEFT", align_y="CENTER")
        lab.matrix_world = Matrix.Translation(_cam_point(cam, 0.53, 0.74, depth)) @ cw.to_4x4()
        tl = _label(coll, "PREVIEW_SheetTopText", "top view", (0, 0, 0), size, align_x="CENTER", align_y="CENTER")
        tl.matrix_world = Matrix.Translation(_cam_point(cam, 0.79, 0.07, depth)) @ cw.to_4x4()
        made += [lab, tl]
        lamps = _product_lamps(cam, centre, dist, LIGHT_SCALE * HAT_LIGHT, key=(-70.0, 45.0), fill=(80.0, 15.0),
                               fill_ratio=0.45, rim=(180.0, 35.0, 0.8))
        R.render_to(render_dir / f"{stem}_linesheet.png", cam, lamps)
        _remove(lamps)
        return {"path": f"Renders/BlackHat/{stem}_linesheet.png", "lines": lines,
                "layout": "3/4 view (hero angle) left, top view right, caption at the smoke bomb's line pitch "
                          f"({CAPTION_PX:.1f} px)"}
    finally:
        for o in made:
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except ReferenceError:
                pass
        bpy.data.collections.remove(coll)


def lod_switch_frame(''')
p.write_text(s, encoding="utf8")
print("ok")
