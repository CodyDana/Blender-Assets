"""SR01 form renders (headless Blender, Cycles): grey clay and the ROUGH-REAL first look (OD cerakote with orange peel
+ worn edge rim, phosphate steel, polished bolt / inner legs, black anodized bipod and rail, rubber, polymer) on a
studio rig (grey world + soft key / fill / top / rim area lights). Poses from sr_motion (frame M) -> frame B.
Review only: nothing here is exported.

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_render.py --
            [--set form|l8|all] [--samples 64] [--only name,...] [--out Renders/Guns/SR01]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import GRIP, RENDERS, REVIEW, PARTS_COLL  # noqa: E402
import sr_motion as MO  # noqa: E402
from gunlib import look as LK  # noqa: E402
from gunlib import render as RD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


sc = bpy.context.scene
if "--with-scope" in argv:          # W1b: append the attachment (built at its mounted pose in frame M)
    from sr_common import BLEND as _BL
    with bpy.data.libraries.load(str(_BL.parent / "Att_Scope_LongRange.blend")) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith("scope")]
    for o in dst.objects:
        sc.collection.objects.link(o)
OBJS = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
REST = {n: o.matrix_world.copy() for n, o in OBJS.items()}


# ------------------------------------------------------------------------------------------------ poses
def to_B(A):
    S = np.diag([1000.0, 1000.0, 1000.0, 1.0])
    return Matrix((np.linalg.inv(S) @ MO.T(-GRIP) @ A @ MO.T(GRIP) @ S).tolist())


def rec(o):
    try:
        return json.loads(o.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def pose_matrix(bone, P):
    """P: dict bolt=(rot, slide), legs=deg (or legs_l / legs_r), ext=mm, cant=deg, riser=dz, release=deg,
    trigger=deg, selector=deg, mag=drop"""
    fold_l = P.get("legs_l", P.get("legs", 0.0))
    fold_r = P.get("legs_r", P.get("legs", 0.0))
    ext, cant = P.get("ext", 0.0), P.get("cant", 0.0)
    if bone == "bolt":
        return MO.bolt(*P.get("bolt", (0.0, 0.0)))
    if bone == "bipod":
        return MO.cant(cant)
    if bone == "bipod_leg_l":
        return MO.leg("l", fold_l, cant)
    if bone == "bipod_leg_r":
        return MO.leg("r", fold_r, cant)
    if bone == "bipod_leg_l_ext":
        return MO.leg_ext("l", fold_l, ext, cant)
    if bone == "bipod_leg_r_ext":
        return MO.leg_ext("r", fold_r, ext, cant)
    if bone == "cheek_riser":
        return MO.riser(P.get("riser", 0.0))
    if bone == "mag_release":
        return MO.mag_release(P.get("release", 0.0))
    if bone == "trigger":
        return MO.trigger(P.get("trigger", 0.0))
    if bone == "selector":
        return MO.selector(P.get("selector", 0.0))
    if bone == "magazine":
        return MO.magazine(P.get("mag", 0.0))
    return np.eye(4)


def apply_pose(P):
    for n, o in OBJS.items():
        o.matrix_world = to_B(pose_matrix(rec(o).get("bone", "body"), P)) @ REST[n]
        o.hide_render = n in P.get("hide", ())


# ------------------------------------------------------------------------------------------------ materials
def _bsdf(name, rgb, metal, rough, coat=0.0, bump=None, edge=None, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    base = (*LK.srgb_to_lin(rgb), 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # roughness variation (two noise scales)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 220.0
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough * 0.8
    mr.inputs["To Max"].default_value = min(rough * 1.25, 1.0)
    nt.links.new(n1.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    col = base
    if edge is not None:          # worn edge rim from a bevel-node mask
        bv = nt.nodes.new("ShaderNodeBevel")
        bv.inputs["Radius"].default_value = edge[1]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        dp = nt.nodes.new("ShaderNodeVectorMath")
        dp.operation = "DOT_PRODUCT"
        nt.links.new(bv.outputs["Normal"], dp.inputs[0])
        nt.links.new(geo.outputs["Normal"], dp.inputs[1])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.985
        ramp.inputs["From Max"].default_value = 0.92
        nt.links.new(dp.outputs["Value"], ramp.inputs["Value"])
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = 90.0
        nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(ramp.outputs["Result"], mul.inputs[0])
        nt.links.new(n2.outputs["Fac"], mul.inputs[1])
        mul2 = nt.nodes.new("ShaderNodeMath")
        mul2.operation = "MULTIPLY"
        mul2.inputs[1].default_value = 1.8
        nt.links.new(mul.outputs[0], mul2.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.clamp_factor = True
        nt.links.new(mul2.outputs[0], mix.inputs["Factor"])
        mix.inputs["A"].default_value = base
        mix.inputs["B"].default_value = (*LK.srgb_to_lin(edge[0]), 1.0)
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = col
    if bump is not None:          # orange peel / stipple
        n3 = nt.nodes.new("ShaderNodeTexNoise")
        n3.inputs["Scale"].default_value = bump[0]
        n3.inputs["Detail"].default_value = 2.0
        nt.links.new(tc.outputs["Object"], n3.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump[1]
        bp.inputs["Distance"].default_value = 0.0002
        nt.links.new(n3.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def materials():
    return {
        "od": _bsdf("RR_OD_Cerakote", (84, 86, 66), 0.0, 0.52, bump=(900.0, 0.12), edge=((120, 118, 104), 0.0007)),
        "phos": _bsdf("RR_Phosphate", (46, 46, 48), 0.55, 0.55, bump=(1500.0, 0.05), edge=((96, 96, 98), 0.0005)),
        "polish": _bsdf("RR_BoltPolished", (150, 150, 152), 1.0, 0.16),
        "anod": _bsdf("RR_AnodBlack", (30, 30, 32), 0.35, 0.42, bump=(1800.0, 0.04), edge=((80, 80, 84), 0.0005)),
        "rubber": _bsdf("RR_Rubber", (24, 24, 25), 0.0, 0.85, bump=(700.0, 0.25)),
        "poly": _bsdf("RR_Polymer", (28, 28, 29), 0.0, 0.62, bump=(1100.0, 0.2), edge=((52, 52, 54), 0.0006)),
        "grey": _bsdf("Clay", (150, 150, 150), 0.0, 0.6),
        "lens": _bsdf("RR_Lens", (12, 16, 20), 0.0, 0.04),
    }


FINISH = {"chassis": "od", "butt": "od", "cheek_riser": "od", "pad_plate": "od", "butt_pad": "rubber",
          "grip": "poly", "bolt": "polish", "bipod_ext_l": "polish", "bipod_ext_r": "polish", "rail": "anod",
          "bipod_clamp": "anod", "bipod_swivel": "anod", "bipod_knob": "anod", "bipod_leg_l": "anod",
          "bipod_leg_r": "anod", "bipod_foot_l": "rubber", "bipod_foot_r": "rubber", "magazine_floorplate": "poly",
          "riser_lever": "anod"}


TEXM = {}


def tex_materials():
    """W2: the game materials on the BAKED maps only (gunlib.game.game_material; no procedural shading)."""
    from gunlib import game as GM
    tex = Path(arg("--tex", str(Path(RENDERS).parents[2] / "Exports" / "Guns" / "SR01" / "Textures")))
    for slot, stem in (("M_SR01_Metal", "T_SR01_Metal"), ("M_SR01_Chassis", "T_SR01_Chassis"),
                       ("M_SR01_Mag", "T_SR01_Mag"), ("M_Att_Scope_Body", "T_Att_Scope_LongRange_Scope_Body"),
                       ("M_Att_Scope_Lens", "T_Att_Scope_LongRange_Scope_Lens")):
        if (tex / f"{stem}_BC.png").exists():
            TEXM[slot] = GM.game_material(slot + "_tex", stem, tex)


def assign(look, M):
    if look == "tex":
        if not TEXM:
            tex_materials()
        for n, o in OBJS.items():
            o.data.materials.clear()
            m = TEXM.get(rec(o).get("slot"))
            if m is None:
                raise SystemExit(f"no baked material for {n} slot {rec(o).get('slot')}")
            o.data.materials.append(m)
        return
    for n, o in OBJS.items():
        o.data.materials.clear()
        f = FINISH.get(n, "anod" if n.startswith("scope") else "phos")
        if n.startswith("scope_lens"):
            f = "lens"
        o.data.materials.append(M["grey"] if look == "grey" else M[f])


# ------------------------------------------------------------------------------------------------ shots
DEPLOY = {"legs": 90.0, "ext": 38.0}
OPEN = {"bolt": (MO.BOLT_ROT, MO.BOLT_TRAVEL)}
SHOTS = {
    "form": [
        ("right", "ortho_r", {}, None),
        ("left", "ortho_l", {}, None),
        ("top", "ortho_t", {}, None),
        ("q34", ((1180, -820, 260), (560, 0, -40), 30.0), {}, None),
        ("deployed_hero", ((1500, -1050, 40), (560, 0, -110), 36.0), DEPLOY, None),
        ("bolt_open_back", ((420, -520, 160), (360, 0, 0), 30.0), OPEN, None),
    ],
    "l8": [
        ("l8_chassis_action", ((470, -330, 70), (420, 0, -40), 34.0), {}, None),
        ("l8_chassis_forend", ((760, -360, 20), (700, 0, -20), 34.0), {}, None),
        ("l8_bolt_group", ((390, -300, 130), (370, -20, 0), 32.0), OPEN, None),
        ("l8_bolt_closed", ((340, -260, 30), (390, -30, -15), 32.0), {}, None),
        ("l8_bipod_folded", ((860, -300, -150), (800, 0, -60), 30.0), {}, None),
        ("l8_bipod_deployed", ((1010, -470, -150), (725, 0, -175), 40.0), DEPLOY, None),
        ("l8_bipod_yoke", ((830, -260, -120), (712, 0, -70), 34.0), DEPLOY, None),
    ],
    "tex": [
        ("right", "ortho_r", {}, None),
        ("left", "ortho_l", {}, None),
        ("top", "ortho_t", {}, None),
        ("q34", ((1180, -820, 300), (560, 0, -20), 30.0), {}, None),
        ("deployed_hero", ((1500, -1050, 80), (560, 0, -90), 36.0), DEPLOY, None),
        ("fp_action", ((150, -150, 120), (430, -10, 10), 52.0), {}, None),
        ("scope_close", ((330, -260, 150), (420, 0, 60), 34.0), {}, None),
        ("action_close", ((430, -300, 40), (390, 0, -20), 34.0), {}, None),
        ("bipod_close", ((960, -420, -160), (760, 0, -150), 36.0), DEPLOY, None),
    ],
    "scope": [
        ("scope_right", "ortho_r", {}, None),
        ("scope_q34", ((1180, -820, 300), (560, 0, -20), 30.0), {}, None),
        ("scope_rings_close", ((560, -330, 160), (470, 0, 45), 32.0), {}, None),
        ("scope_rear_q", ((60, -330, 200), (330, 0, 50), 32.0), {}, None),
        ("scope_deployed_hero", ((1500, -1050, 80), (560, 0, -90), 36.0), DEPLOY, None),
    ],
}


def studio_rig(cam, target_B):
    """W2 realism rig (the SMG close-up r2 product set, gunlib export_review_job 'studio'): Blender's bundled
    interior.exr (CC0) neutral at 0.15 for ambient reflections, a long softbox in the mirror direction of the side face
    the camera sees, one in the top faces' mirror direction, two strip lights behind left / right whose reflections run
    along the edges; the camera sees a flat sRGB 150 backdrop."""
    w = bpy.data.worlds.new("SR_Studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bgn = next(n for n in nt.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (*RD.srgb_to_lin((150, 150, 150)), 1.0)
    d = Path(bpy.utils.system_resource("DATAFILES", path="studiolights/world"))
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(d / "interior.exr"), check_existing=True)
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = 0.0
    nt.links.new(env.outputs["Color"], hs.inputs["Color"])
    bg2 = nt.nodes.new("ShaderNodeBackground")
    bg2.inputs["Strength"].default_value = 0.15
    nt.links.new(hs.outputs["Color"], bg2.inputs["Color"])
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg2.outputs["Background"], mix.inputs[1])
    nt.links.new(bgn.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    LK.clear_lights()
    Mw = cam.matrix_world
    rgt, up, back = (Vector(Mw.col[i][:3]).normalized() for i in range(3))
    t = Vector(target_B)
    v = (Vector(Mw.translation) - t).normalized()
    if cam.data.type == "ORTHO":
        v = back
    lights = [("Flank", "flank", (0.0, 0.55, 0.0), 1.3, (1.2, 0.3), 2.5),
              ("Top", (0.0, 0.0, 1.0), (0.0, 0.1, 0.0), 1.3, (1.4, 0.3), 7.0),
              ("StripL", None, (-0.9, 0.25, -0.45), 1.2, (0.1, 1.4), 22.0),
              ("StripR", None, (0.9, 0.25, -0.45), 1.2, (0.1, 1.4), 22.0)]
    for name, nrm, nud, dist, size, energy in lights:
        if nrm is None:
            dd = (rgt * nud[0] + up * nud[1] + back * nud[2]).normalized()
        else:
            n = Vector((0.0, 1.0 if v.y >= 0.0 else -1.0, 0.0)) if nrm == "flank" else Vector(nrm)
            dd = (2.0 * n.dot(v) * n - v).normalized()
            dd = (dd + rgt * nud[0] + up * nud[1] + back * nud[2]).normalized()
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
        ld.energy = energy
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.location = t + dd * dist
        ob.rotation_euler = (t - ob.location).to_track_quat("-Z", "Y").to_euler()
        ob.visible_camera = False


def ortho(cam, view):
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.22
    c = Vector(((np.array([550.0, 0, -40.0]) - GRIP) / 1000.0).tolist())
    if view == "ortho_r":
        cam.location = c + Vector((0, -3.0, 0))
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == "ortho_l":
        cam.location = c + Vector((0, 3.0, 0))
        cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    else:
        cam.location = c + Vector((0, 0, 3.0))
        cam.rotation_euler = (0, 0, 0)
    return c


def l5_render(k, ss=4):
    """W2 L5: the GR panel's own px <-> mm map (trace GR_outline: px_per_mm, x_rear_px, bore_y_px; the panel crop's
    size) as an ortho right view at ss x, the physical rig (overhead key tipped toward the camera, a rim behind, the grey
    world 126 as fill; gunlib export_review_job 'l5'), light scale k. -> scratch/w2/l5/side_k<k>.png"""
    from sr_common import TRACE, WORK
    j = json.loads((TRACE / "GR_outline.json").read_text())
    W, H = (int(v) for v in arg("--panel", "619,563").split(","))          # the GR crop's size (sr_l5 passes it)
    ppm, x0, y0 = j["px_per_mm"], j["x_rear_px"], j["bore_y_px"]
    cx, cz = (W / 2.0 - x0) / ppm, (y0 - H / 2.0) / ppm
    cam = RD.camera_object("SR_L5")
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(W, H) / ppm / 1000.0
    c = Vector(((np.array([cx, 0.0, cz]) - GRIP) / 1000.0).tolist())
    cam.location = c + Vector((0, -3.0, 0))
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.clip_start, cam.data.clip_end = 0.01, 50.0
    sc.render.resolution_x, sc.render.resolution_y = W * ss, H * ss
    sc.render.film_transparent = False
    RD.world_flat(sc, RD.srgb_to_lin((126, 126, 126)), 1.0, env=0.2 * k)
    LK.clear_lights()
    bpy.context.view_layer.update()
    Mw = cam.matrix_world
    rgt, up, back = (np.array(Mw.col[i][:3]) for i in range(3))
    tgt = np.array(c)
    e = math.radians(70.0)
    RD.area_light("Key", tuple(tgt + 1.4 * (0.05 * rgt + math.cos(e) * back + math.sin(e) * up)), tuple(tgt), 2.4, 60 * k)
    RD.area_light("Rim", tuple(tgt - back + 0.6 * up), tuple(tgt), 1.5, 10 * k)
    out = WORK / "scratch" / "w2" / "l5"
    out.mkdir(parents=True, exist_ok=True)
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(out / f"side_k{k:.3f}.png")
    bpy.ops.render.render(write_still=True)
    print("[SR01] RENDERED", sc.render.filepath)


def main():
    RD.engine(sc, "CYCLES", int(arg("--samples", "64")))
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa: BLE001
        print("GPU setup failed", e)
    M = materials()
    out = Path(arg("--out", str(RENDERS)))
    out.mkdir(parents=True, exist_ok=True)
    sets = arg("--set", "form")
    if sets == "l5":
        assign("tex", M)
        for kk in arg("--light", "1.0").split(","):
            l5_render(float(kk))
        return
    looks = arg("--looks", "grey,real").split(",")
    only = [v for v in arg("--only", "").split(",") if v]
    cam = RD.camera_object("SR_Cam")
    sc.camera = cam
    for sname in (["form", "l8"] if sets == "all" else [sets]):
        for name, view, P, _ in SHOTS[sname]:
            if only and name not in only:
                continue
            apply_pose(P)
            for look in looks:
                if sname == "l8" and look == "grey":
                    continue
                assign(look, M)
                if arg("--rig", "rough") == "rough":
                    LK.rough_world(sc, (128, 128, 128), 0.55)
                sc.render.film_transparent = False
                if isinstance(view, str):
                    tgt = ortho(cam, view)
                    sc.render.resolution_x, sc.render.resolution_y = 2400, 1000
                    if view == "ortho_t":
                        sc.render.resolution_y = 800
                else:
                    eye, t, fov = view
                    e = Vector(((np.array(eye, float) - GRIP) / 1000.0).tolist())
                    tgt = Vector(((np.array(t, float) - GRIP) / 1000.0).tolist())
                    cam.data.type = "PERSP"
                    cam.data.angle = math.radians(fov)
                    cam.location = e
                    cam.rotation_euler = (tgt - e).to_track_quat("-Z", "Y").to_euler()
                    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
                cam.data.clip_start, cam.data.clip_end = 0.01, 50.0
                bpy.context.view_layer.update()
                if arg("--rig", "rough") == "studio":
                    studio_rig(cam, tuple(tgt))
                else:
                    LK.rough_lights(cam, tuple(tgt), 1.4, 1.2)
                sc.render.image_settings.file_format = "PNG"
                d = out if sname in ("form", "scope", "tex") else REVIEW / "l8"
                d.mkdir(parents=True, exist_ok=True)
                stem = f"form_{look}_{name}" if look != "tex" else f"tex_{name}"
                sc.render.filepath = str(d / f"{stem}.png")
                bpy.ops.render.render(write_still=True)
                print("[SR01] RENDERED", sc.render.filepath)
    apply_pose({})


main()
