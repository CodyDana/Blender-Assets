"""Finalise patch: gallery see-through / LOD pop / back view / coverage (applied once)."""
from pathlib import Path

p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_gallery.py")
s = p.read_text(encoding="utf-8")
add = '''
# =============================================================================== FINALISE checks
def render_row_alpha(lod0, out_png, yaws=YAWS, samples=16):
    """The reference row's four copies with a transparent film and NO backdrop: its alpha says where the background
    shows.  Returns the alpha (H, W) in [0, 1] (row 0 = top)."""
    cps = _copies(lod0, 4)
    m0 = lod0.matrix_world.copy()
    saved = _hide_all_but(cps)
    rig = LK.Rig()
    sc = bpy.context.scene
    try:
        LK.setup_cycles(samples, denoise=False)
        LK.studio(rig, floor=False)
        cam, info = LK.row_camera(rig)
        LK.place_row({v: [c] for v, c in zip(("v1", "v2", "v3", "v4"), cps)}, yaws)
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        LK.render(out_png)
        im = bpy.data.images.load(str(Path(out_png).resolve()), check_existing=False)
        w, h = im.size
        a = np.empty(w * h * 4, np.float32)
        im.pixels.foreach_get(a)
        bpy.data.images.remove(im)
        alpha = a.reshape(h, w, 4)[::-1, :, 3].copy()
    finally:
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
        rig.teardown()
        for c in cps[1:]:
            bpy.data.objects.remove(c, do_unlink=True)
        lod0.matrix_world = m0
        _restore(saved)
    return alpha


def see_through(alpha, spec) -> Dict[str, int]:
    """Background pixels INSIDE each view's perforated body (the band between the cap top and the sleeve step,
    within 0.9 of the body radius of the view's axis): there must be none (the reference's limb holes read dark)."""
    out = {}
    D = spec.body_r * 2.0
    for v in ("v1", "v2", "v3", "v4"):
        cx, by = VIEW_CX[v], VIEW_BOTTOM[v]
        y0 = int(round(by - spec.sleeve_z0 / D * D_PX)) + 2
        y1 = int(round(by - spec.body_z0 / D * D_PX)) - 2
        x0 = int(round(cx - 0.45 * D_PX))
        x1 = int(round(cx + 0.45 * D_PX))
        box = alpha[y0:y1, x0:x1]
        out[v] = int((box < 0.5).sum())
    return out


def _fov_camera(rig, loc_mm, target_mm, res, hfov_deg=90.0):
    cam = bpy.data.cameras.new("FB_FpCam")
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    cam.lens = 18.0 / math.tan(math.radians(hfov_deg / 2.0))
    cam.clip_start = 0.005
    ob = bpy.data.objects.new("FB_FpCam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc_mm) * 0.001
    ob.rotation_euler = (Vector(target_mm) * 0.001 - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    rig.objects.append(ob)
    return ob


def lod_pop(lods, switch_m, out_dir: Path, samples=48, res=(1920, 1080), azimuths=(-60.0, 30.0, 150.0)):
    """FINALISE gate (craft review): at each shipped switch distance (90 deg hfov, 1080p) render LODn and LODn+1 from
    three azimuths; the fraction of object pixels that change by more than 20/255 (any channel) must be < 2 %."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = {"switch_m": list(switch_m), "views": []}
    worst = 0.0
    tgt = (2.0, -3.0, 84.0)
    for k, d in enumerate(switch_m):
        pair = (lods[k], lods[k + 1])
        for az in azimuths:
            imgs = []
            for o in pair:
                saved = _hide_all_but([o])
                rig = LK.Rig()
                m0 = o.matrix_world.copy()
                sc = bpy.context.scene
                try:
                    o.matrix_world = Matrix.Identity(4)
                    LK.setup_cycles(samples, res=res)
                    sc.cycles.seed = 7
                    LK.studio(rig)
                    _fov_camera(rig, _polar(az, 12.0, d * 1000.0, tgt), tgt, res)
                    png = out_dir / f"lodpop_d{k}_az{int(az)}_{o.name}.png"
                    LK.render(png)
                    imgs.append(LK.load_png(png))
                finally:
                    rig.teardown()
                    o.matrix_world = m0
                    _restore(saved)
            a, b = imgs
            bg = np.median(a[:40, :200].reshape(-1, 3), axis=0)
            obj = (np.abs(a - bg).max(2) > 6 / 255) | (np.abs(b - bg).max(2) > 6 / 255)
            diff = np.abs(a - b).max(2) > 20 / 255
            frac = float((diff & obj).sum() / max(obj.sum(), 1))
            worst = max(worst, frac)
            rep["views"].append({"switch": k + 1, "distance_m": round(d, 4), "azimuth": az,
                                 "object_px": int(obj.sum()), "frac_gt20": round(frac, 5)})
    rep["worst_frac_gt20"] = round(worst, 5)
    rep["pass"] = worst < 0.02
    return rep


'''
i = s.index("# =============================================================================== gallery shots")
s = s[:i] + add.lstrip("\n") + s[i:]
a = '''def render_hero(lod0, out_png, samples=256, res=(1600, 900), az=-60.0, el=22.0, dist=860.0):
    saved = _hide_all_but([lod0])
    rig = LK.Rig()
    try:
        LK.setup_cycles(samples, res=res)
        LK.studio(rig)
        tgt = (4.0, -4.0, 84.0)
        _look_camera(rig, _polar(az, el, dist, tgt), tgt, 75.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        _restore(saved)
    return str(out_png)'''
b = '''def render_hero(lod0, out_png, samples=256, res=(1600, 900), az=-60.0, el=22.0, dist=860.0, turn=0.0):
    """``turn`` rotates the OBJECT (the back view): the camera stays in front of the backdrop.  FINALISE: round 1's
    back view put the camera behind the backdrop sweep (an empty frame)."""
    saved = _hide_all_but([lod0])
    rig = LK.Rig()
    m0 = lod0.matrix_world.copy()
    try:
        LK.setup_cycles(samples, res=res)
        LK.studio(rig)
        R = Matrix.Rotation(math.radians(turn), 4, "Z")
        lod0.matrix_world = R
        tgt = tuple(R @ Vector((4.0, -4.0, 84.0)))
        _look_camera(rig, _polar(az, el, dist, tgt), tgt, 75.0, res)
        LK.render(out_png)
    finally:
        rig.teardown()
        lod0.matrix_world = m0
        _restore(saved)
    return str(out_png)


def frame_coverage(png) -> float:
    """Fraction of the frame that differs from its corner backdrop by > 8/255 (a gallery render must show the object:
    > 5 %)."""
    im = LK.load_png(png)
    bg = np.median(im[:30, :30].reshape(-1, 3), axis=0)
    return float((np.abs(im - bg).max(2) > 8 / 255).mean())'''
assert a in s
s = s.replace(a, b)
a = '''    out["back"] = render_hero(lod0, renders / "flashbang_back.png", samples=spp, az=120.0)'''
b = '''    out["back"] = render_hero(lod0, renders / "flashbang_back.png", samples=spp, turn=180.0)'''
assert a in s
s = s.replace(a, b)
a = '''    out["lods"] = render_lods(objs["assembled"], renders / "flashbang_lods.png", report.get("lod_triangles") or [],
                              samples=spp // 2)
    return out'''
b = '''    out["lods"] = render_lods(objs["assembled"], renders / "flashbang_lods.png", report.get("lod_triangles") or [],
                              samples=spp // 2)
    out["coverage"] = {k: round(frame_coverage(out[k]), 4) for k in ("hero", "back", "wire", "lods")}
    out["coverage_pass"] = all(v > 0.05 for v in out["coverage"].values())
    log("render: see-through alpha row")
    alpha = render_row_alpha(lod0, work / "flashbang_row_alpha.png")
    st = see_through(alpha, spec)
    for v, npx in st.items():
        out["row_metrics"].setdefault(v, {})["see_through_px"] = npx
    log(f"  see-through px per view: {st}")
    log("render: LOD pop at the switch distances")
    sw = report["measure"]["assembled"]["switch_distances_m"]
    out["lod_pop"] = lod_pop(objs["assembled"], sw, work / "lodpop", samples=24 if quick else 48)
    log(f"  LOD pop worst frac(>20/255) {out['lod_pop']['worst_frac_gt20']}")
    return out'''
assert a in s
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("gallery patched")
