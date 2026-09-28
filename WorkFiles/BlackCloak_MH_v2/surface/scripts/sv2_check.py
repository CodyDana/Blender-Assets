# Fabric check renders + measurements at the photo's scale (2.734 mm/px, sv2_photo_probe.json).
#   swatch: a flat 1.2 m panel facing the camera, ortho, rendered 4x and box-downsampled to 1x (no denoiser)
#   drape : the test drape (sv2_test_drape.blend), ortho front at 1x scale (rendered 2x, downsampled), + a 3/4 beauty
# Calibrated studio (Scripts/garments/blackcloak_v2/bcv2_studio.py): white card 0.90 linear, view transform Standard.
# args after --: tag tex_dir mode(swatch|drape) [overrides_json] [samples]
import sys, os, json, time, math
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/garments/blackcloak_v2")
import bpy, bmesh
import numpy as np
from mathutils import Vector
import sv2_imgmetrics as M
import bcv2_material as BM
import bcv2_studio as ST

a = sys.argv[sys.argv.index("--") + 1:]
tag, tex_dir, mode = a[0], a[1], a[2]
ov = json.loads(a[3]) if len(a) > 3 and a[3] not in ("", "-") else {}
spp = int(a[4]) if len(a) > 4 else 64
S = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/"
R = S + "renders/"
MMPX = json.load(open(S + "logs/sv2_photo_probe.json"))["mm_per_px_estimate"]
P = BM.load_params()
sc = bpy.context.scene
info = {"tag": tag, "tex_dir": tex_dir, "mode": mode, "overrides": ov, "samples": spp, "mm_per_px": MMPX}


def cam_ortho(name, loc, look_at, ortho_m):
    c = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    sc.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    c.data.type = "ORTHO"
    c.data.ortho_scale = ortho_m
    return c


def render(cam, w, h, path, samples, denoise=False, transparent=True):
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "16"
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 1)


def load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"   # raw stored (sRGB-encoded) values, also for 16-bit PNGs
    w, h = img.size
    arr = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(arr)
    bpy.data.images.remove(img)
    return arr.reshape(h, w, 4)[::-1].astype(np.float64)


def down_over_white(rgba, f):
    """box-downsample in linear light, composite over white; returns sRGB 0..255 rgb and alpha."""
    lin = M.s2l(rgba[..., :3]) * rgba[..., 3:4]           # premultiplied linear
    h, w = rgba.shape[:2]
    lin = lin[:h // f * f, :w // f * f].reshape(h // f, f, w // f, f, 3).mean((1, 3))
    al = rgba[:h // f * f, :w // f * f, 3].reshape(h // f, f, w // f, f).mean((1, 3))
    comp = lin + (1 - al[..., None])
    return M.l2s(comp) * 255.0, al


if mode == "swatch":
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=0.6)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x / 0.45 + 0.137, l.vert.co.y / 0.45 + 0.291)
    me = bpy.data.meshes.new("SV2_Swatch")
    bm.to_mesh(me)
    bm.free()
    sw = bpy.data.objects.new("SV2_Swatch", me)
    sc.collection.objects.link(sw)
    sw.location = (0, 0, 1.0)
    sw.rotation_euler = (math.radians(90), 0, 0)          # stands up, faces -Y
    mat = BM.cloth_material(P, tex_dir=tex_dir, overrides=ov)
    me.materials.append(mat)
    W1 = 384
    cam = cam_ortho("SV2_Cam", (0, -3.0, 1.0), (0, 0, 1.0), W1 * MMPX / 1000.0)
    info["studio"] = ST.studio(sc, cam, centre=(0, 0, 1.0))
    bpy.data.objects["ST_Floor"].hide_render = True
    p4 = R + tag + "_swatch_4x.png"
    info["render_s"] = render(cam, W1 * 4, W1 * 4, p4, spp)
    rgb, al = down_over_white(load_rgba(p4), 4)
    M.save(R + tag + "_swatch_1x.png", rgb)
    L = M.lum(rgb)
    Llin = M.s2l(L / 255.0)
    rows = []
    for gy in range(3):
        for gx in range(3):
            y, x = 60 + gy * 96, 60 + gx * 96
            r = M.patch_stats(L[y:y + 32, x:x + 32], MMPX)
            r["xy"] = [x, y]
            rows.append(r)
    info["swatch_1x"] = {"median_lum_srgb": float(np.median(L[40:344, 40:344])),
                         "mean_rgb_linear": [float(v) for v in M.s2l(rgb[40:344, 40:344] / 255.0).reshape(-1, 3).mean(0)],
                         "patches_agg": M.agg(rows),
                         "bands": M.radial_bands_mm(Llin[64:320, 64:320], MMPX)}
    # close view: 0.5 mm/px (the in-game close camera), 512 px, denoiser off, 256 spp
    cam2 = cam_ortho("SV2_CamClose", (0, -3.0, 1.0), (0, 0, 1.0), 0.256)
    info["render_close_s"] = render(cam2, 512, 512, R + tag + "_swatch_close_0p5mm.png", 256)
elif mode == "drape":
    bpy.ops.wm.open_mainfile(filepath=S + "sv2_test_drape.blend")
    sc = bpy.context.scene
    cl = bpy.data.objects["SV2_Drape"]
    mat = BM.cloth_material(P, tex_dir=tex_dir, overrides=ov)
    cl.data.materials.clear()
    cl.data.materials.append(mat)
    dg = bpy.context.evaluated_depsgraph_get()
    co = np.array([cl.matrix_world @ v.co for v in cl.data.vertices])
    zmax = float(co[:, 2].max())
    cz = zmax / 2 + 0.02
    H1 = int(math.ceil((zmax + 0.08) * 1000 / MMPX))
    W1 = int(math.ceil((co[:, 0].max() - co[:, 0].min() + 0.12) * 1000 / MMPX))
    cx = float((co[:, 0].max() + co[:, 0].min()) / 2)
    cam = cam_ortho("SV2_Cam", (cx, -4.0, cz), (cx, 0, cz), max(W1, H1) * MMPX / 1000.0)
    info["studio"] = ST.studio(sc, cam, centre=(0, 0, 1.0))
    bpy.data.objects["ST_Floor"].hide_render = True
    p2 = R + tag + "_drape_2x.png"
    info["render_s"] = render(cam, W1 * 2, H1 * 2, p2, spp)
    rgb, al = down_over_white(load_rgba(p2), 2)
    M.save(R + tag + "_drape_1x.png", rgb)
    L = M.lum(rgb)
    m = al > 0.98
    info["drape_1x"] = {"size": [W1, H1], "garment_px": int(m.sum()), "median_lum_srgb": float(np.median(L[m])),
                        "p10_p90_lum_srgb": [float(np.percentile(L[m], 10)), float(np.percentile(L[m], 90))],
                        "mean_rgb_linear": [float(v) for v in M.s2l(rgb[m] / 255.0).mean(0)]}
    pat = M.flat_patches(L, m, n=32, k=8, x_rng=(0, W1), y_rng=(0, H1), mm_per_px=MMPX)
    info["drape_1x"]["flat_patches_agg"] = M.agg(pat) if pat else None
    info["drape_1x"]["flat_patches_xy"] = [p["xy"] for p in pat]
    # beauty 3/4 (perspective, 85 mm, denoised) and a close crop for the eye
    bpy.data.objects["ST_Floor"].hide_render = False
    c = bpy.data.objects.new("SV2_CamQ", bpy.data.cameras.new("SV2_CamQ"))
    sc.collection.objects.link(c)
    c.data.lens = 85
    tgt = Vector((0, 0, 0.85))
    d = Vector((-0.55, -1.0, 0.12)).normalized()
    c.location = tgt + d * 6.2
    c.rotation_euler = (tgt - c.location).to_track_quat("-Z", "Y").to_euler()
    info["render_q_s"] = render(c, 560, 800, R + tag + "_drape_q34.png", 128, denoise=True, transparent=False)
    c2 = bpy.data.objects.new("SV2_CamM", bpy.data.cameras.new("SV2_CamM"))
    sc.collection.objects.link(c2)
    c2.data.lens = 50
    tgt = Vector((0.05, -0.3, 1.05))
    c2.location = tgt + Vector((-0.25, -0.9, 0.15))
    c2.rotation_euler = (tgt - c2.location).to_track_quat("-Z", "Y").to_euler()
    info["render_m_s"] = render(c2, 640, 640, R + tag + "_drape_macro.png", 256, denoise=False, transparent=False)
json.dump(info, open(S + "logs/" + tag + "_" + mode + ".json", "w"), indent=1)
print("CHECK", json.dumps({k: v for k, v in info.items() if k in ("swatch_1x", "drape_1x", "render_s")})[:3000])
print("CAL", json.dumps(info["studio"]["calibration"]))
