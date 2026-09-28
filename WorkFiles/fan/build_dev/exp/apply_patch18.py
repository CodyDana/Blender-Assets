import re
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_gallery.py"
s = open(p, encoding="utf-8").read()
helper = '''def exposed_render(path, cam, lamps, objs, work: Path, target_p50: float, tag: str) -> Dict[str, float]:
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


def gallery('''
s = s.replace("def gallery(", helper, 1)
# hero
s = s.replace('''            R.render_to(render_dir / "fan_hero.png", cam, lamps)
            R.render_mask(work / "hero_mask.png", cam, [objs[0]])''', '''            exp_hero = exposed_render(render_dir / "fan_hero.png", cam, lamps, [objs[0]], work, 0.20, "hero")''')
s = s.replace('''            out["shots"]["hero"] = {"path": "Renders/Fan/fan_hero.png", "lens_mm": cam.data.lens,''',
              '''            out["shots"]["hero"] = {"path": "Renders/Fan/fan_hero.png", "lens_mm": cam.data.lens, **exp_hero,''')
s = s.replace('''            R.render_to(render_dir / "fan_raking.png", cam, lamps)
            out["shots"]["raking"] = {''', '''            exp_r = exposed_render(render_dir / "fan_raking.png", cam, lamps, [objs[0]], work, 0.15, "raking")
            out["shots"]["raking"] = {**exp_r, ''')
s = s.replace('''                R.render_to(render_dir / fname, cam, lamps)
                R.render_mask(work / f"{nm}_mask.png", cam, [objs[0]])
                out["shots"][nm] = {"path": f"Renders/Fan/{fname}",''', '''                ex = exposed_render(render_dir / fname, cam, lamps, [objs[0]], work, 0.20, nm)
                out["shots"][nm] = {"path": f"Renders/Fan/{fname}", **ex,''')
s = s.replace('''            R.render_to(render_dir / "fan_top.png", cam, lamps)
            R.render_mask(work / "top_mask.png", cam, [objs[0]])
            out["shots"]["top"] = {''', '''            ex = exposed_render(render_dir / "fan_top.png", cam, lamps, [objs[0]], work, 0.20, "top")
            out["shots"]["top"] = {**ex, ''')
s = s.replace('''            R.render_to(render_dir / "fan_underside.png", cam, lamps)
            R.render_mask(work / "under_mask.png", cam, [objs[0]])
            out["shots"]["underside"] = {''', '''            ex = exposed_render(render_dir / "fan_underside.png", cam, lamps, [objs[0]], work, 0.20, "under")
            out["shots"]["underside"] = {**ex, ''')
# LOD strip: wider spacing / camera further
s = s.replace('''        cam_p.data.lens = 50.0
        cam_p.location = (0.0, -1.55, 0.12)''', '''        cam_p.data.lens = 50.0
        cam_p.location = (0.0, -2.05, 0.12)''')
s = s.replace("        width = 0.40\n", "        width = 0.42\n")
open(p, "w", encoding="utf-8").write(s)
print(s.count("exposed_render("))
