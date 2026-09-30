"""ROUND 5 fixes track: lean review renders of the composed compound (Cycles, denoised), read-only.

Opens Assets/Dojo/DojoShowcase.blend (never saved) and swaps every placed piece's mesh for the TEXTURED mesh of the
same name from its kit's own source blend (the prefix picks the file, as Scripts/dojo/dressing/dkd_common.py does),
so the pieces this track rebuilt show their new geometry. Cameras: the showcase's own UE capture cameras (same
position / look-at / hfov as the Unreal stills) plus this track's close-ups (CLOSE below).

Run: blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python WorkFiles/dojo/build/round5/fixes/r5_render.py
     -- --cams CAM_Establishing,CU_R4_ShedVending [--samples 64] [--tag after] [--scale 0.5] [--light sunset|studio]
        [--src SM_DKS_=C:/.../start_backup/blends/DojoShed.blend]   (override a prefix's source: the 'before' renders)
Out: WorkFiles/dojo/build/round5/fixes/renders/<tag>/<cam>.png
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
WORK = ROOT / "WorkFiles" / "dojo" / "build"
FIX = WORK / "round5" / "fixes"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


SAMPLES = int(arg("--samples", "64"))
TAG = arg("--tag", "after")
SCALE = float(arg("--scale", "0.5"))
LIGHT = arg("--light", "sunset")
CAMS = [c for c in arg("--cams", "").split(",") if c]
OUT = FIX / "renders" / TAG
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene

SOURCES = [("SM_DKH_", "DojoHall.blend"), ("SM_DKO_", "DojoOutbuildings.blend"), ("SM_DKC_", "DojoCorridors.blend"),
           ("SM_DKS_", "DojoShed.blend"), ("SM_DKV_", "DojoPavilion.blend"), ("SM_DKG_", "DojoGround.blend"),
           ("SM_DKP_Stone_", "CourtyardStone.blend"), ("SM_DKP_Train_", "TrainingProps.blend"),
           ("SM_DKP_Modern_", "ModernProps.blend"), ("SM_DKP_Taiko_", "Taiko.blend"),
           ("SM_DKP_Yard_", "DojoYardPosts.blend"), ("SM_DK_", "DojoKit1.blend")]
OVR = {}
for i, a in enumerate(ARGS):
    if a == "--src":
        k, v = ARGS[i + 1].split("=", 1)
        OVR[k] = v

# close-ups of the fixed items: name -> (loc, look_at, hfov_deg, (w, h))
CLOSE = {
    "FX_ShedFrontOrtho": ((3.1, 5.22, 1.9), (3.1, 0.0, 1.9), -8.4, (1448, 760)),
    "FX_ShedFront": ((3.1, 11.6, 1.75), (3.0, 1.0, 1.5), 62.0, (1920, 1080)),
    "FX_Shed34": ((9.6, 10.4, 3.2), (3.0, 2.2, 1.6), 58.0, (1920, 1080)),
    "FX_ShedEaveEdge": ((6.9, 6.3, 2.2), (4.6, 4.9, 2.45), 50.0, (1920, 1080)),
    "FX_ShedUnder": ((1.3, 4.2, 1.0), (3.2, 0.6, 2.2), 84.0, (1920, 1080)),
    "FX_ResidenceRidge": ((34.0, 22.0, 6.2), (41.0, 31.0, 5.2), 40.0, (1920, 1080)),
    "FX_PierStore": ((1.9, 24.3, 4.2), (-0.6, 27.3, 3.25), 52.0, (1920, 1080)),
    "FX_PierRes": ((42.1, 24.3, 4.2), (44.6, 27.3, 3.25), 52.0, (1920, 1080)),
    "FX_PierStoreTop": ((-0.4, 25.3, 5.0), (-0.4, 27.6, 3.3), 60.0, (1920, 1080)),
    "FX_Shoji": ((19.0, 19.2, 1.5), (18.2, 21.9, 1.5), 52.0, (1920, 1080)),
    "FX_ShojiWide": ((22.0, 16.5, 1.7), (22.0, 22.0, 1.6), 70.0, (1920, 1080)),
    "FX_WallSeamsS": ((10.0, 3.0, 1.6), (6.0, 0.0, 1.4), 60.0, (1920, 1080)),
    "FX_WallSeamsW": ((3.0, 22.0, 1.6), (0.0, 16.0, 1.4), 64.0, (1920, 1080)),
    "FX_Dummy": ((5.4, 10.9, 1.4), (2.03, 12.0, 1.05), 40.0, (1920, 1080)),
    "FX_DummyStudio": ((5.2, 12.0, 1.0), (2.03, 12.0, 1.0), -2.6, (1080, 1080)),
}


def src_for(piece):
    for pre, fn in sorted(SOURCES, key=lambda s: -len(s[0])):
        if piece.startswith(pre):
            return OVR.get(pre, str(ROOT / "Assets" / "Dojo" / fn))
    return None


def piece_of(o):
    return o.name.split("__")[0]


def textured_context():
    asm = list(bpy.data.collections["Assembly"].objects)
    need = {}
    for o in asm:
        s = src_for(piece_of(o))
        if s:
            need.setdefault(s, set()).add(piece_of(o))
    got = {}
    for path, names in need.items():
        if not Path(path).exists():
            print("MISSING SOURCE", path, flush=True)
            continue
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            have = set(src.objects)
            dst.objects = [n for n in names if n in have]
        for o in dst.objects:
            if o is not None and o.type == "MESH":
                got[o.name.split(".")[0] if o.name.split(".")[0] in names else o.name] = o.data
    n = 0
    for o in asm:
        p = piece_of(o)
        if p in got:
            o.data = got[p]
            n += 1
    for o in asm:
        p = piece_of(o)
        o.hide_render = p.startswith("SM_DGB_Boundary") or p.startswith("SM_DKP_Stone_LanternShort") or (
            p.startswith("SM_DKP_Modern_StreetLamp") and o.matrix_world.translation.y > -1.0)
    kit = bpy.data.collections.get("Kit")
    if kit:
        kit.hide_render = True
    # images of meshes loaded from a blend outside Assets/Dojo (the start backups) have broken relative paths:
    # re-find them by file name under Exports/DojoKit and Assets/Dojo
    index = {}
    for base in (ROOT / "Exports" / "DojoKit", ROOT / "Assets" / "Dojo"):
        for f in base.rglob("*.png"):
            index.setdefault(f.name.lower(), f)
    fixed = 0
    for img in bpy.data.images:
        if img.source != "FILE" or not img.filepath:
            continue
        if not Path(bpy.path.abspath(img.filepath, library=img.library)).exists():
            f = index.get(Path(img.filepath).name.lower())
            if f is not None:
                img.filepath = str(f)
                img.reload()
                fixed += 1
    print("TEXTURED", len(got), "pieces", n, "instances; images re-found", fixed, flush=True)
    return got


def setup_cycles():
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.cycles.max_bounces = 8
    sc.render.film_transparent = False


def sunset():
    """The UE sun (layout_showcase 'sun': 12 deg, azimuth 160 from +X) with a warm-horizon sky ramp."""
    L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
    s = L["sun"]
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (1.0, 0.55, 0.30, 1)
    cr.elements[1].position = 0.35
    cr.elements[1].color = (0.32, 0.31, 0.48, 1)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world
    el, az = math.radians(s["elev_deg"]), math.radians(s["azimuth_deg_from_x"])
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = 4.2
    lt.angle = math.radians(0.8)
    lt.color = (1.0, 0.66, 0.40)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.6


def studio():
    world = bpy.data.worlds.new("Grey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1.0)
    bg.inputs["Strength"].default_value = 1.35
    sc.world = world
    for nm, d, e in (("Key", (0.40, -0.62, -0.68), 2.6), ("Fill", (-0.10, -0.97, -0.22), 1.6)):
        lt = bpy.data.lights.new(nm, "SUN")
        lt.energy = e
        lt.angle = math.radians(25.0)
        o = bpy.data.objects.new(nm, lt)
        sc.collection.objects.link(o)
        o.rotation_euler = Vector(d).normalized().to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.35


def camera(name, loc, look, hfov, wh):
    """hfov < 0: an orthographic camera |hfov| metres wide."""
    cam = bpy.data.cameras.new(name)
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    if hfov < 0:
        cam.type = "ORTHO"
        cam.ortho_scale = -hfov
    else:
        cam.lens = 18.0 / math.tan(math.radians(hfov) / 2)
    cam.clip_start = 0.05
    cam.clip_end = 900.0
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o, wh


def experiment(kind):
    """Read-only look experiments on the loaded meshes (never saved)."""
    if kind.startswith("ridge"):
        rm, metal0 = (2.5, True) if kind == "ridge_rough" else (1.0, True)
        for o in bpy.data.collections["Assembly"].objects:
            if piece_of(o) != "SM_DKO_Roof_Ridge":
                continue
            me = o.data
            for i, m in enumerate(me.materials):
                if m and m.name.startswith("M_DJ_RoofTile"):
                    c = bpy.data.materials.get("EXP_Ridge") or m.copy()
                    c.name = "EXP_Ridge"
                    nt = c.node_tree
                    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
                    for lk in list(b.inputs["Metallic"].links):
                        nt.links.remove(lk)
                    b.inputs["Metallic"].default_value = 0.0
                    lk = b.inputs["Roughness"].links
                    if lk:
                        mm = nt.nodes.new("ShaderNodeMath")
                        mm.operation = "MULTIPLY"
                        mm.use_clamp = True
                        nt.links.new(lk[0].from_socket, mm.inputs[0])
                        mm.inputs[1].default_value = rm
                        nt.links.new(mm.outputs[0], b.inputs["Roughness"])
                    me.materials[i] = c
    if kind.startswith("shoji="):
        k = float(kind.split("=")[1])
        m = bpy.data.materials.get("M_DJ_ShojiPaper")
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Emission Strength"].default_value = k
    print("EXPERIMENT", kind, flush=True)


def main():
    setup_cycles()
    textured_context()
    if arg("--exp"):
        experiment(arg("--exp"))
    (sunset if LIGHT == "sunset" else studio)()
    L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
    ue = {c["name"]: (tuple(c["loc"]), tuple(c["look_at"]), c["hfov_deg"], tuple(c["out_wh"])) for c in L["cameras"]}
    ue.update(CLOSE)
    for name in CAMS:
        if name not in ue:
            print("NO CAMERA", name, flush=True)
            continue
        loc, look, hfov, wh = ue[name]
        o, wh = camera(name, loc, look, hfov, wh)
        sc.camera = o
        sc.render.resolution_x = int(wh[0] * SCALE)
        sc.render.resolution_y = int(wh[1] * SCALE)
        sc.render.resolution_percentage = 100
        sc.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath, flush=True)


main()
