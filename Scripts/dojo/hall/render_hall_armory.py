"""HALL + ARMORY round (2026-10-01), stage 2: the hall sheet renders (Cycles, headless) from
Assets/Dojo/DojoShowcase_HallArmory.blend (read-only: nothing is saved).

Views (each 'before' = the hall as built, with the 27 removed / replaced instances of collection HallArmory_Removed
back in and the new hall / armory pieces hidden; 'after' = the composed layout):
  front_before / front_after   ortho front elevation of the hall from the courtyard (26 m wide) + a pixel diff
  estab_before / estab_after   CAM_Establishing (layout camera, the owner's reference framing) + a pixel diff
  rear34                       the extension and its lower rear roof from the north-east, above the new alley
  side_after                   ortho west elevation (the rear roof's ridge under the main roof)
  section                      north-south section at X 22 looking east (the camera clips everything west of X 22)
  door_view                    from the veranda through the open centre doors into the armory
  valley                       the valley and the cut eave stub from above
  top_after                    plan view
The armory's interior uses its FBX materials (flat colours, the armory chat's textures are not loaded here); the hall
uses the shared dojo material library (M_DJ_*). Lighting: the sheet's neutral key + fill; the armory's design lights
(lights_design.json) as point lights for the interior views.
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase_HallArmory.blend --python Scripts/dojo/hall/render_hall_armory.py
     -- [--samples 64] [--scale 1.0] [--only a,b]
Out: WorkFiles/dojo/build/hall_armory/blender/renders/*.png + views.json + diff.json
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return ARGS[ARGS.index(n) + 1] if n in ARGS else d


SAMPLES = int(arg("--samples", "64"))
SCALE = float(arg("--scale", "1.0"))
ONLY = arg("--only", "")
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "blender" / "renders"
OUT.mkdir(parents=True, exist_ok=True)
L = json.loads((ROOT / "WorkFiles/dojo/build/hall_armory/blender/layout_checks.json").read_text(encoding="utf-8"))
LD = json.loads((ROOT / "WorkFiles/shared/armory_hall/lights_design.json").read_text(encoding="utf-8"))
sc = bpy.context.scene
ASM = bpy.data.collections["Assembly"]
REM = bpy.data.collections["HallArmory_Removed"]
VIEWS = {}


def piece_of(o):
    return o.name.split("__")[0]


def index_of(o):
    t = o.name.split("__")[-1]
    return int(t) if t.isdigit() else None


# ------------------------------------------------------------------------------------------------ setup
def setup():
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
    sc.cycles.max_bounces = 6
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("SheetGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1.0)
    bg.inputs["Strength"].default_value = 1.2
    sc.world = world
    for nm, e, ang, d in (("Key", 2.8, 25.0, (0.40, 0.84, -0.38)), ("Fill", 1.2, 40.0, (-0.25, 0.96, -0.10)),
                          ("Back", 1.4, 30.0, (-0.35, -0.80, -0.45))):
        lt = bpy.data.lights.new(nm, "SUN")
        lt.energy = e
        lt.angle = math.radians(ang)
        o = bpy.data.objects.new(nm, lt)
        sc.collection.objects.link(o)
        o.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.3


def library_materials():
    """FBX-imported M_DJ_* slots (flat) -> the shared library's textured materials."""
    n = 0
    built = {}
    for m in list(bpy.data.materials):
        base = m.name.split(".")[0]
        if base not in djm.MATERIALS:
            continue
        if base not in built:
            built[base] = djm.make_material(base, rebuild=True)
        lib = built[base]
        if lib is not m:
            m.user_remap(lib)
            n += 1
    print("LIBRARY MATERIALS remapped", n, flush=True)


def design_lights(energy=18.0):
    c = bpy.data.collections.new("DesignLights")
    sc.collection.children.link(c)
    for i, lt in enumerate(LD["lights"]):
        p = Vector(lt["loc_m"]) + Vector((22.0, 24.0, 0.5))
        d = bpy.data.lights.new(f"DL{i}", "POINT")
        k = lt["design"].get("kelvin", 3200)
        d.color = (1.0, 0.80, 0.62) if k < 4000 else (1.0, 0.95, 0.88)
        d.energy = energy * (2.0 if lt["type"] == "rect" else 1.0)
        d.shadow_soft_size = 0.15
        o = bpy.data.objects.new(f"DL{i}", d)
        c.objects.link(o)
        o.location = p - Vector((0, 0, 0.05))
    return c


# ------------------------------------------------------------------------------------------------ states
REMOVED_LANDSCAPE = {k for k, it in enumerate(L["instances"]) if it.get("removed") and it["removed"] != "hall_armory_rev1"}
NEW_HA = {k for k, it in enumerate(L["instances"]) if it.get("hall_armory") == "hall_armory_rev1"}


def is_hall(p):
    return p.startswith("SM_DKH_")


def state(which, scope):
    """which: 'before' | 'after'; scope: 'hall' (the hall + its extension only) | 'all' (the compound)."""
    for o in ASM.objects:
        p = piece_of(o)
        k = index_of(o)
        hide = p.startswith("SM_DGB_Boundary") or p.startswith("SM_DKX_1v1") or (k in REMOVED_LANDSCAPE)
        if p.startswith("SM_DGB_Tree"):
            hide = True
        if which == "before" and (p.startswith("SM_AK_") or k in NEW_HA):
            hide = True
        if scope == "hall" and not (is_hall(p) or p.startswith("SM_AK_")):
            hide = True
        o.hide_render = hide
    for o in REM.objects:
        p = piece_of(o)
        o.hide_render = not (which == "before" and (scope == "all" or is_hall(p))) or p.startswith("SM_DKX_1v1")
    # before: the north wall at its old place (the moved instances carry their pre-move translation in the report)
    for o in ASM.objects:
        k = index_of(o)
        if k is not None and k in MOVED:
            o.matrix_world.translation = Vector(MOVED[k] if which == "before" else L["instances"][k]["loc"])


REPORT = json.loads((ROOT / "WorkFiles/dojo/build/hall_armory/blender/compose_report.json").read_text(encoding="utf-8"))
MOVED = {int(k): v for k, v in REPORT["blend"]["moved_from"].items()}


# ------------------------------------------------------------------------------------------------ cameras
def cam_obj(name, cam):
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    return o


def ortho(name, centre, forward, width, clip_start=0.1, dist=80.0):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = width
    cam.clip_start = clip_start
    cam.clip_end = 500.0
    o = cam_obj(name, cam)
    f = Vector(forward).normalized()
    o.matrix_world = Matrix.Translation(Vector(centre) - f * dist) @ f.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return o


def persp(name, loc, look, hfov=None, lens=35.0):
    cam = bpy.data.cameras.new(name)
    cam.sensor_width = 36.0
    cam.sensor_fit = "HORIZONTAL"
    cam.lens = lens if hfov is None else 18.0 / math.tan(math.radians(hfov) / 2)
    cam.clip_start = 0.05
    cam.clip_end = 2000.0
    o = cam_obj(name, cam)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(cam, name, w, h, meta=None):
    if ONLY and name not in ONLY.split(","):
        return
    sc.camera = cam
    sc.render.resolution_x = int(w * SCALE)
    sc.render.resolution_y = int(h * SCALE)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    VIEWS[name] = {"w": int(w * SCALE), "h": int(h * SCALE), "camera": cam.name, **(meta or {})}
    print("RENDERED", name, flush=True)


def diff(a, b, name, region=None):
    """Mean absolute difference and the share of pixels that changed by more than 0.05 (0-1 PNG values, max over RGB);
    region = (u0, v0, u1, v1) in image fractions, v from the bottom."""
    import numpy as np
    pa, pb = OUT / f"{a}.png", OUT / f"{b}.png"
    if not (pa.exists() and pb.exists()):
        return None
    arr = []
    for pth in (pa, pb):
        im = bpy.data.images.load(str(pth))
        w, h = im.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        arr.append(buf.reshape(h, w, 4)[:, :, :3])
    A, B = arr
    if region is not None:
        y0, y1 = int(region[1] * h), int(region[3] * h)
        x0, x1 = int(region[0] * w), int(region[2] * w)
        A, B = A[y0:y1, x0:x1], B[y0:y1, x0:x1]
    d = np.abs(A - B).max(axis=2)
    return {"pair": [a, b], "region_uv": region, "mean_abs": round(float(d.mean()), 5),
            "changed_share": round(float((d > 0.05).mean()), 5), "pixels": int(d.size)}


# ------------------------------------------------------------------------------------------------ main
def main():
    setup()
    library_materials()
    dl = design_lights()
    DIFF = {}
    # front elevation (hall only), before / after
    dl.hide_render = True
    cam = ortho("CAM_front", (22.0, 20.0, 5.2), (0, 1, 0), 26.0)
    for w in ("before", "after"):
        state(w, "hall")
        render(cam, f"front_{w}", 2600, 1300, {"ppm": 2600 * SCALE / 26.0, "centre": [22.0, 20.0, 5.2]})
    DIFF["front_all"] = diff("front_before", "front_after", "front")
    # the roof band only (above +5.5: the silhouette the owner's reference shows), rows from the top of the image
    z_lo = 5.5
    v_lo = (z_lo - (5.2 - 6.5)) / 13.0
    DIFF["front_roof_above_5p5"] = diff("front_before", "front_after", "roofband", (0.0, v_lo, 1.0, 1.0))
    DIFF["front_outside_door_band"] = diff("front_before", "front_after", "outer", (0.0, 0.0, (19.0 - 9.0) / 26.0, 1.0))
    # the establishing view (the owner's reference framing), before / after, whole compound
    cams = {c["name"]: c for c in L["cameras"]}
    ce = cams["CAM_Establishing"]
    cam = persp("CAM_Establishing", ce["loc"], ce["look_at"], hfov=ce["hfov_deg"])
    for w in ("before", "after"):
        state(w, "all")
        dl.hide_render = w == "before"
        render(cam, f"estab_{w}", 1448, 1086)
    DIFF["estab_all"] = diff("estab_before", "estab_after", "estab")
    DIFF["estab_upper_half"] = diff("estab_before", "estab_after", "estab_up", (0.0, 0.5, 1.0, 1.0))
    state("after", "all")
    dl.hide_render = False
    render(persp("CAM_rear34", (41.0, 60.0, 15.0), (22.0, 38.0, 4.0), lens=32), "rear34", 1800, 1200)
    render(persp("CAM_rear34w", (3.0, 57.0, 9.0), (22.0, 39.0, 4.5), lens=30), "rear34_west_low", 1800, 1200)
    state("after", "hall")
    dl.hide_render = True
    render(ortho("CAM_side", (10.0, 34.0, 4.8), (1, 0, 0), 28.0), "side_after", 2400, 1100,
           {"ppm": 2400 * SCALE / 28.0})
    state("before", "hall")
    render(ortho("CAM_side_b", (10.0, 34.0, 4.8), (1, 0, 0), 28.0), "side_before", 2400, 1100)
    state("after", "all")
    dl.hide_render = False
    render(ortho("CAM_section", (22.0, 34.5, 4.6), (1, 0, 0), 30.0, clip_start=80.0), "section", 2600, 1100,
           {"ppm": 2600 * SCALE / 30.0, "cut_x": 22.0})
    render(persp("CAM_door", (22.0, 19.6, 1.62), (22.0, 34.0, 1.45), lens=24), "door_view", 1600, 1000)
    render(persp("CAM_interior", (22.0, 25.4, 1.62), (22.0, 40.0, 1.6), lens=20), "interior_view", 1600, 1000)
    dl.hide_render = True
    render(persp("CAM_valley", (11.0, 36.0, 10.5), (21.0, 34.4, 5.8), lens=30), "valley", 1600, 1000)
    render(ortho("CAM_top", (22.0, 34.0, 0.0), (0, 0, -1), 30.0), "top_after", 1600, 1600)
    state("after", "all")
    render(persp("CAM_junction", (8.5, 41.0, 3.2), (14.6, 34.4, 5.0), lens=26), "junction_nw", 1600, 1000)
    render(persp("CAM_alley", (27.5, 46.5, 1.65), (19.0, 44.0, 3.2), lens=20), "alley_view", 1600, 1000)
    (OUT / "views.json").write_text(json.dumps(VIEWS, indent=1), encoding="utf-8")
    (OUT / "diff.json").write_text(json.dumps(DIFF, indent=1), encoding="utf-8")
    print("DIFF", json.dumps(DIFF), flush=True)


if __name__ == "__main__":
    main()
