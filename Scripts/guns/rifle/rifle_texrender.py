"""AR-01 renders from the BAKED MAPS only (headless Blender, Cycles): the game materials (M_AR01_Metal / _Furniture /
_Mag on T_AR01_<Set>_{BC,ORM,N}.png) on the LOD0 parts or the static twin's LODs; no procedural shading anywhere.

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_texrender.py -- \
        --set side|realism|closeups|lods [--out DIR] [--samples 128] [--light 1.0]

side      the sheet-matched side view (the LEFT-labelled panel's px <-> mm frame, 3x), studio light, grey backdrop
          (126): the L5 colour comparison input -> <out>/tex_side.png
realism   the four realism-judge views of RIFLE_BUILD_PLAN 9 (first person 35 cm, ADS, third person 3 m, hero 3/4),
          the ADS one twice: the spec's Sight line (notch bottom -> post tip) and the post-level-with-notch-top hold
closeups  receiver right (c1 camera), front sight (c3 camera), grip, stock, magazine, butt plate
lods      SM_AR01_LOD0..3 side by side at their switch distances (same camera, 2560 x 1440, 90 deg)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, TRACE, RENDERS, REVIEW  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

from gunlib import render as RD  # noqa: E402
from gunlib import look as LK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


SET = arg("--set", "side")
OUT = Path(arg("--out", str(REVIEW / "tex"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SAMPLES = int(arg("--samples", "128"))
LIGHT = float(arg("--light", "1.0"))
SPECF = float(arg("--spec", "1.0"))        # legacy L5 rig only (--rig fitted): the lights' specular factor
RIG = arg("--rig", "physical")             # L5 rig: physical (default, specular factor 1) | fitted (legacy, r4)
KEY_ELEV = float(arg("--key-elev", "62"))  # physical rig: key elevation above the horizon toward the camera (deg)
ENV = float(arg("--env", "0.30"))          # physical rig: grey world strength seen by lighting / reflections
sc = bpy.context.scene


def show_only(objs):
    keep = set(o.name for o in objs)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep


def lod0_parts():
    return [o for o in bpy.data.collections["AR01_Parts"].objects if o.type == "MESH"]


def B(p):
    return Vector(((np.asarray(p, float) - GRIP) / 1000.0).tolist())


def trace_frame(view):
    j = json.loads((TRACE / f"{view}_outline.json").read_text())
    b = j["panel_box_sheet_px"]
    return j["px_per_mm"], j["bore_dir_px"], j["origin_px"], (b[3] - b[1] + 1, b[2] - b[0] + 1)


def studio_lights(k=1.0):
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    RD.area_light("Key", (0.35, -0.9, 0.75), (0.25, 0, -0.02), 1.6, 34 * k)
    RD.area_light("Fill", (0.9, -0.8, -0.2), (0.3, 0, 0.0), 2.0, 10 * k)
    RD.area_light("Top", (0.3, 0.1, 1.2), (0.3, 0, 0.0), 2.0, 16 * k)
    RD.area_light("Rim", (0.2, 0.9, 0.5), (0.3, 0, 0.0), 1.2, 10 * k)


def sheet_lights(k=1.0):
    """L5 rig (the sheet's look: highlights on the top surfaces, the side flats lit at a grazing angle so they show
    their own colour, not a reflected light): a large soft key above and slightly in front, a weak front fill high
    up, a rim behind. Positions in frame B metres round the gun's centre."""
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = (0.2, 0.0, 0.0)
    RD.area_light("Key", (0.25, -0.45, 1.3), c, 2.4, 60 * k)
    RD.area_light("Fill", (0.1, -1.6, 0.9), c, 2.0, 14 * k)
    RD.area_light("Rim", (0.2, 1.0, 0.6), c, 1.5, 10 * k)


def sheet_lights_physical(k=1.0, elev_deg=62.0):
    """Physical L5 rig (specular factor 1 on every light; 2026-10-05 look-polish round). The sheet's look: the side
    flats show their own colour while the top surfaces and rounded steel carry highlights. A side flat faces the camera
    (-Y), so it mirrors what is behind the camera: no light sits there (the r4 rig's front fill did, which whitened the
    shellac and forced its specular factor to 0, leaving blued steel black). One large soft key overhead, tipped toward
    the camera by elev_deg above the horizon (its mirror direction is 2 x (90 - elev) off the camera ray for a side
    flat, outside the 0.4-0.6 roughness lobe), a rim behind, and the grey world (126) at strength ENV x k as the fill
    and the environment that metal reflects."""
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    c = np.array((0.2, 0.0, 0.0))
    e = math.radians(elev_deg)
    RD.area_light("Key", tuple(c + 1.4 * np.array((0.05, -math.cos(e), math.sin(e)))), tuple(c), 2.4, 60 * k)
    RD.area_light("Rim", (0.2, 1.0, 0.6), tuple(c), 1.5, 10 * k)


def persp(cam, eye_M, target_M, fov_deg, res, up=(0.0, 0.0, 1.0)):
    eye, tgt = B(eye_M), B(target_M)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(fov_deg)
    cam.data.clip_start = 0.01
    cam.data.clip_end = 60.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    sc.render.resolution_x, sc.render.resolution_y = res


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def realism_shots():
    """The realism judge's four views, the same cameras as rifle_realism.py (review/realism_form4): first person 35 cm,
    ADS from the Sight socket (B4 / R48: 0.25 m behind the socket on its line, notch top -> post tip), third person
    3 m, hero 3/4."""
    soc = {s["socket"]: s for s in SPEC.sockets["rifle"]}["Sight"]
    p = math.radians(soc["unreal_rotation_deg"]["pitch"])
    d = np.array([math.cos(p), 0.0, math.sin(p)])
    sight = np.array(soc["M_mm"], float)
    post = np.array(SPEC.key["sight_line"]["post_tip_M"], float)
    fp_eye = np.array([350.0, 0.0, 0.0]) + 350.0 * unit([-0.93, 0.22, 0.30])
    hero_t = np.array([450.0, 0.0, -20.0])
    # ADS: EXACTLY the B4 / S2 camera (rifle_b4.sight_camera): the eye 250 mm behind the Sight socket on its line, the
    # view ALONG the socket's pitch (not aimed at the post tip), 55 deg, 2560 x 1440 (realism-tex round: at 1600 px the
    # 2 mm post in the notch was ~4 px and the judges could not find it; the gate's own resolution is kept)
    return [("fp_35cm", fp_eye, np.array([620.0, 0.0, 10.0]), 70.0, 1.1),
            ("ads_55deg", sight - 250.0 * d, sight + 1000.0 * d, 55.0, 1.1),
            ("tp_3m", hero_t + 3000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, 3.2),
            ("hero_34", hero_t + 1500.0 * unit([0.55, -0.78, 0.30]), hero_t, 38.0, 1.6)]


def _pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1]          # top-down rows
    bpy.data.images.remove(im)
    return a


def ads_check(cam, png):
    """The textured ADS picture's post vs its surround: a second render with every other part a holdout gives the
    post's VISIBLE pixels (occlusion by the rear sight kept); from the beauty render: the post's mean luminance, the
    luminance of the opening beside it (the notch gap, same rows, 2-6 px off each side, not post) and of the rear
    sight lobes; Weber contrast. Writes <out>/ads_check.json and a 6x crop of the notch (ads_55deg_notch.png)."""
    from bpy_extras.object_utils import world_to_camera_view
    post = bpy.data.objects["front_sight_post"]
    others = [o for o in lod0_parts() if o.name != post.name and not o.hide_render]
    for o in others:
        o.is_holdout = True
    mpath = OUT / "_ads_post_visible.png"
    sp = sc.cycles.samples
    sc.cycles.samples = 16
    RD.still(sc, mpath, transparent=True)
    sc.cycles.samples = sp
    for o in others:
        o.is_holdout = False
    sc.render.film_transparent = False
    beauty = _pixels(png)
    vis = _pixels(mpath)[..., 3] > 0.5
    mpath.unlink()
    H, W = vis.shape
    # Image.pixels of an 8-bit PNG are the stored (sRGB-encoded) values: decode to linear for the luminance
    lin_ = np.where(beauty[..., :3] <= 0.04045, beauty[..., :3] / 12.92, ((beauty[..., :3] + 0.055) / 1.055) ** 2.4)
    lum = lin_ @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    soc = {s["socket"]: s for s in SPEC.sockets["rifle"]}["Sight"]
    tip = world_to_camera_view(sc, cam, B(SPEC.key["sight_line"]["post_tip_M"]))
    notch = world_to_camera_view(sc, cam, B(soc["M_mm"]))
    tip_px = (tip.x * W, (1 - tip.y) * H)
    rec = {"camera": "B4 / S2: eye 250 mm behind the Sight socket on its line, forward = the socket pitch, 55 deg, "
                     "%d x %d" % (W, H),
           "post_tip_projected_px": [round(tip_px[0], 2), round(tip_px[1], 2)],
           "notch_socket_projected_px": [round(notch.x * W, 2), round((1 - notch.y) * H, 2)],
           "post_visible_px": int(vis.sum())}
    if vis.any():
        ys, xs = np.nonzero(vis)
        rows = np.unique(ys)
        sur = np.zeros_like(vis)
        for y in rows:
            xr = xs[ys == y]
            for x0 in list(range(xr.min() - 6, xr.min() - 1)) + list(range(xr.max() + 2, xr.max() + 7)):
                if 0 <= x0 < W:
                    sur[y, x0] = True
        sur &= ~vis
        lp, ls = float(lum[vis].mean()), float(np.median(lum[sur])) if sur.any() else float("nan")
        bg = float(np.median(lum[:40, :40]))
        rec.update({"post_visible_rows": int(len(rows)), "post_visible_width_px_median": float(np.median(
                    [np.sum(ys == y) for y in rows])),
                    "post_tip_visible_px": [round(float(xs[ys == rows[0]].mean()), 2), int(rows[0])],
                    "lum_post_linear": round(lp, 5), "lum_beside_post_linear": round(ls, 5),
                    "lum_backdrop_linear": round(bg, 5),
                    "weber_contrast_post_vs_beside": round((lp - ls) / max(ls, 1e-6), 3),
                    "weber_contrast_post_vs_backdrop": round((lp - bg) / max(bg, 1e-6), 3)})
    rec["post_found"] = bool(vis.sum() >= 20)
    (OUT / "ads_check.json").write_text(json.dumps(rec, indent=1))
    print("[AR01] ADS_CHECK", json.dumps(rec))
    # 6x crop of the notch window (nearest), the post's visible outline marked in a side panel
    cx, cy = int(round(tip_px[0])), int(round(tip_px[1]))
    x0, y0 = max(cx - 80, 0), max(cy - 45, 0)
    crop = beauty[y0:y0 + 90, x0:x0 + 160, :3]
    mk = vis[y0:y0 + 90, x0:x0 + 160]
    side = crop.copy()
    side[mk] = (side[mk] * 0.3 + np.array([0.9, 0.05, 0.05], np.float32) * 0.7)
    both = np.concatenate([crop, side], 1).repeat(6, 0).repeat(6, 1)
    hh, ww = both.shape[:2]
    img = bpy.data.images.new("ads_notch", ww, hh, alpha=False, float_buffer=False)   # byte: values stay sRGB
    rgba = np.concatenate([both, np.ones((hh, ww, 1), np.float32)], 2)[::-1]
    img.pixels[:] = rgba.ravel()
    img.filepath_raw = str(OUT / "ads_55deg_notch.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def main():
    RD.engine(sc, "CYCLES", SAMPLES)
    sc.render.resolution_percentage = 100
    cam = RD.camera_object("TexCam")
    if SET == "side":
        show_only(lod0_parts())
        if RIG == "physical":
            RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=ENV * LIGHT)
            sheet_lights_physical(LIGHT, KEY_ELEV)
        else:
            RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=0.25)
            sheet_lights(LIGHT)
        # (legacy rig) Cycles ignores a light's specular factor: each light becomes a diffuse-only copy at (1 - s) of
        # its energy plus the full light at s, so the diffuse light stays k and the specular light is k x s
        for lo in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            if RIG != "physical" and SPECF < 1.0:
                d = lo.copy()
                d.data = lo.data.copy()
                bpy.context.scene.collection.objects.link(d)
                d.data.energy = lo.data.energy * (1.0 - SPECF)
                d.visible_glossy = False
                lo.data.energy = lo.data.energy * SPECF
        s, u, p0, shape = trace_frame("LEFT")
        RD.ortho_side(cam, sc, s, u, p0, shape, GRIP, 3)
        RD.still(sc, OUT / "tex_side.png")
    elif SET == "realism":
        show_only(lod0_parts())
        post_tip = np.array(SPEC.key["sight_line"]["post_tip_M"], float)
        for name, eye, tgt, fov, ld in realism_shots():
            LK.rough_world(sc, (126, 126, 126), 0.55)
            sc.render.film_transparent = False
            ads = name == "ads_55deg"
            persp(cam, eye, tgt, fov, (2560, 1440) if ads else (1600, 900))
            bpy.context.view_layer.update()
            # the lights aim at the post tip in the ADS view (as before), at the view target otherwise
            LK.rough_lights(cam, tuple(B(post_tip if ads else tgt)), ld, 1.35 * LIGHT)
            RD.still(sc, OUT / f"{name}.png")
            if ads:
                ads_check(cam, OUT / f"{name}.png")
    elif SET == "closeups":
        show_only(lod0_parts())
        RD.world_flat(sc, RD.srgb_to_lin((123, 123, 123)), 1.0, env=0.35)
        studio_lights(LIGHT)
        for k, nm in (("c1", "receiver_right"), ("c3", "front_sight")):
            camd = json.loads((SCRATCH / "q34" / f"camera_{k}.json").read_text())
            Rm = np.array(camd["R_rows_right_up_fwd_M"], float)
            c = np.array(camd["image_centre_point_M"], float)
            W, H = camd["panel_px"]
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2] = Rm[0], Rm[1], -Rm[2]
            M[:3, 3] = (c - Rm[2] * 800.0 - GRIP) / 1000.0
            cam.matrix_world = Matrix(M.tolist())
            cam.data.type = "ORTHO"
            cam.data.sensor_fit = "HORIZONTAL"
            cam.data.ortho_scale = camd["ortho_width_mm"] / 1000.0
            cam.data.shift_x = cam.data.shift_y = 0.0
            cam.data.clip_start = 0.05
            cam.data.clip_end = 5.0
            sc.render.resolution_x, sc.render.resolution_y = W * 3, H * 3
            RD.still(sc, OUT / f"cu_{nm}.png")
        for nm, (eye, tgt, fov) in {
                "grip_checker": ((330, -170, -70), (270, 0, -88), 30.0),
                "stock_r34": ((60, -420, 120), (110, 0, -40), 38.0),
                "mag_left": ((420, 330, -130), (440, 0, -95), 40.0),
                "buttplate": ((-160, -170, 0), (10, 0, -40), 34.0),
                "receiver_top": ((300, -150, 330), (360, 0, 10), 40.0),
                "muzzle_34": ((960, -150, 60), (840, 0, 0), 32.0)}.items():
            persp(cam, eye, tgt, fov, (1600, 1100))
            RD.still(sc, OUT / f"cu_{nm}.png")
    elif SET == "lods":
        sizes = json.loads((ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "game_lod_sizes.json").read_text())
        r = sizes["bounds_radius_m"]
        s_ = sizes["SM_AR01"]
        RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=0.45)
        studio_lights(LIGHT)
        V0 = np.array([v.co[:] for v in bpy.data.objects["SM_AR01_LOD0"].data.vertices])
        cB = 0.5 * (V0.min(0) + V0.max(0))
        for k in range(4):
            for j in ((k - 1, k) if k else (0, 1)):
                pass
        for k in range(1, 4):
            d = 1.778 * r / s_[k]
            for lv in (k - 1, k):
                show_only([bpy.data.objects[f"SM_AR01_LOD{lv}"]])
                eye = cB + np.array([0.35, -0.9, 0.2]) / np.linalg.norm([0.35, -0.9, 0.2]) * d
                cam.location = Vector(eye.tolist())
                cam.rotation_euler = (Vector(cB.tolist()) - cam.location).to_track_quat("-Z", "Y").to_euler()
                cam.data.type = "PERSP"
                cam.data.sensor_fit = "HORIZONTAL"
                cam.data.angle = math.radians(90.0)
                cam.data.clip_end = 100.0
                sc.render.resolution_x, sc.render.resolution_y = 2560, 1440
                RD.still(sc, OUT / f"lod_switch{k}_lod{lv}.png")
    print("[AR01] TEXRENDER_DONE", SET)


main()
