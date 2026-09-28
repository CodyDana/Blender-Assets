"""Finalise patch 2: lod_pop turns the OBJECT (the camera stays in front of the lights) and masks by alpha."""
from pathlib import Path

p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_gallery.py")
s = p.read_text(encoding="utf-8")
i0 = s.index("def lod_pop(")
i1 = s.index("# =============================================================================== gallery shots")
new = '''def _render_rgba(png):
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    try:
        LK.render(png)
    finally:
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
    im = bpy.data.images.load(str(Path(png).resolve()), check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1].copy()


def lod_pop(lods, switch_m, out_dir: Path, samples=48, res=(1920, 1080), turns=(30.0, 120.0, 240.0)):
    """FINALISE gate (craft review): at each shipped switch distance (90 deg hfov, 1080p) render LODn and LODn+1 with
    the object turned three ways (the camera stays in front, key light as in every render); the fraction of object
    pixels (alpha of either) whose colour changes by more than 20/255 (any channel, over a mid-grey) must be < 2 %."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = {"switch_m": list(switch_m), "views": []}
    worst = 0.0
    tgt0 = Vector((2.0, -3.0, 84.0))
    for k, d in enumerate(switch_m):
        pair = (lods[k], lods[k + 1])
        for turn in turns:
            imgs = []
            for o in pair:
                saved = _hide_all_but([o])
                rig = LK.Rig()
                m0 = o.matrix_world.copy()
                sc = bpy.context.scene
                try:
                    R = Matrix.Rotation(math.radians(turn), 4, "Z")
                    o.matrix_world = R
                    tgt = tuple(R @ tgt0)
                    LK.setup_cycles(samples, res=res)
                    sc.cycles.seed = 7
                    LK.studio(rig, floor=False)
                    _fov_camera(rig, _polar(-90.0, 12.0, d * 1000.0, tgt), tgt, res)
                    png = out_dir / f"lodpop_d{k}_turn{int(turn)}_{o.name}.png"
                    imgs.append(_render_rgba(png))
                finally:
                    rig.teardown()
                    o.matrix_world = m0
                    _restore(saved)
            a, b = imgs
            grey = 0.18
            ca = a[..., :3] + (1 - a[..., 3:4]) * grey
            cb = b[..., :3] + (1 - b[..., 3:4]) * grey
            obj = (a[..., 3] > 0.5) | (b[..., 3] > 0.5)
            diff = np.abs(ca - cb).max(2) > 20 / 255
            frac = float((diff & obj).sum() / max(obj.sum(), 1))
            worst = max(worst, frac)
            rep["views"].append({"switch": k + 1, "distance_m": round(d, 4), "turn": turn,
                                 "object_px": int(obj.sum()), "frac_gt20": round(frac, 5)})
            if k == 0 and turn == turns[0]:
                LK.save_png(out_dir / f"lodpop_diff_d{k}_turn{int(turn)}.png",
                            np.repeat((np.abs(ca - cb).max(2) * 4)[..., None], 3, 2))
    rep["worst_frac_gt20"] = round(worst, 5)
    rep["pass"] = worst < 0.02
    return rep


'''
s = s[:i0] + new + s[i1:]
p.write_text(s, encoding="utf-8")
print("gallery patched (lod_pop v2)")
