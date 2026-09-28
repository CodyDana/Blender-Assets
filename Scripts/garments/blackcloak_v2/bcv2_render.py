"""BlackCloak_MH_v2: builder's renders of the EXPORTED FBX (Blender 5.2 headless, Cycles).

    blender -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_render.py -- --out Renders/BlackCloak_MH_v2/r1
            [--views photo,jin,front,back,side,q34,collar,clasp,hem,fray,fabric_far,fabric_close] [--samples 256]

* the shipped SK_BlackCloak_MH_v2.fbx is imported and re-bound to the locked fitting body (spec tool v2m_common, read
  only), posed ARMS_DOWN_V2 (the cloak is spine-weighted, so its bind shape is its arms-down drape);
* materials from the stage-1 kit (bcv2_material + material_params.json) with the fray alpha on UV1, exactly the
  contract in SK_BlackCloak_MH_v2.material_params.json; textures from Exports/Garments/BlackCloak_MH_v2/Textures;
* calibrated studio bcv2_studio (white Lambertian card at (0, -0.25, 1.30) = 0.90 linear, Standard, look None,
  exposure 0) with a shadow-catcher floor; renders are composited over white (the photo's backdrop) and also kept
  with alpha (<view>_rgba.png).
Cameras: the spec's (v2m_common.VIEWS): photo = cloak alone, 100 mm, garment bbox x 1.08, 417x674 x3; jin / front /
back / side_r / q34 with the body; close-ups defined here.
"""
import sys, os, json, math, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcv2_common as C
sys.path.insert(0, C.ROOT + "/WorkFiles/BlackCloak_MH_v2/spec/scripts")
import bpy, bmesh
import numpy as np
from mathutils import Vector
import v2m_common as V            # read-only use of the spec tools (fit body, FBX re-bind, cameras)
import bcv2_material as BM
import bcv2_studio as ST

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--fbx", default=C.EXPORT_FBX)
ap.add_argument("--views", default="photo,jin,front,back,side,q34,q34_other,collar,clasp,hem,fray,fabric_far,fabric_close")
ap.add_argument("--samples", type=int, default=256)
A = ap.parse_args(argv)
os.chdir(C.ROOT)
A.out = os.path.abspath(A.out)
os.makedirs(A.out, exist_ok=True)
T0 = time.time()
LOG = {"fbx": A.fbx, "views": {}}

fit = V.fitbody()
V.drop_haircards()
arm = fit["armature"]
meshes = V.import_garment(A.fbx, arm)
V.apply_pose(arm, C.ARMS_DOWN_V2)
if fit.get("head_parts"):
    fit["head_parts"].hide_render = False
LOG["uv_layers"] = {o.name: [l.name for l in o.data.uv_layers] for o in meshes}
LOG["slots"] = {o.name: [s.material.name if s.material else None for s in o.material_slots] for o in meshes}

P = BM.load_params()


def wool(name):
    m = BM.cloth_material(P, name=name, uv_map=C.UV0, overrides={"uv_scale": C.UV_SCALE})
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = C.UV1
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(C.TEX_DIR, P["textures"]["fray_bca"]), check_existing=True)
    t.image.alpha_mode = "STRAIGHT"
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    return m


MAT = {}
for o in meshes:
    for s in o.material_slots:
        n = s.material.name if s.material else ""
        base = n.split(".")[0]
        if base not in MAT:
            MAT[base] = BM.clasp_material(P, name="R_" + base) if "Clasp" in base else wool("R_" + base)
        s.material = MAT[base]
for o in meshes:
    for p in o.data.polygons:
        p.use_smooth = True

sc = bpy.context.scene
sc.cycles.samples = A.samples
sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
sc.cycles.max_bounces = 8
sc.cycles.transparent_max_bounces = 16
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "16"


def evaluated(o):
    return V.evaluated_coords(o)[0]


G = np.concatenate([evaluated(o) for o in meshes])
# clasp centre (clasp slot vertices) and a fringe point on the front edge for the macro shots
clasp_c = None
for o in meshes:
    for i, s in enumerate(o.material_slots):
        if s.material and "Clasp" in s.material.name:
            co = evaluated(o)
            idx = sorted({v for p in o.data.polygons if p.material_index == i for v in p.vertices})
            clasp_c = co[idx].mean(0)
LOG["clasp_centre"] = None if clasp_c is None else clasp_c.tolist()
# fringe (fray row) vertices: UV1 V below the cut edge; pick a front hem point and a front-edge point for the macros
fr_pts = []
for o in meshes:
    l1 = o.data.uv_layers.get(C.UV1)
    if l1 is None:
        continue
    co = evaluated(o)
    vs = set()
    for li, lp in enumerate(o.data.loops):
        if l1.data[li].uv[1] < C.FRAY_EDGE_V - 0.05:
            vs.add(lp.vertex_index)
    fr_pts += [co[v] for v in vs]
fr_pts = np.array(fr_pts) if fr_pts else np.zeros((0, 3))
hem_t = fray_t = None
if len(fr_pts):
    h = fr_pts[fr_pts[:, 2] < 0.03]
    if len(h):
        hem_t = h[np.argmin(h[:, 1])]
    e = fr_pts[(fr_pts[:, 2] > 0.35) & (fr_pts[:, 2] < 0.95)]
    if len(e):
        fray_t = e[np.argmin(e[:, 1])]
LOG["hem_target"] = None if hem_t is None else hem_t.tolist()
LOG["fray_target"] = None if fray_t is None else fray_t.tolist()

BODY = [fit["body"], fit["head"], fit["hair_proxy"]] + ([fit["head_parts"]] if fit.get("head_parts") else [])
VIEWS = {
    "photo": dict(view="photo", body=False),
    "jin": dict(view="jin", body=True),
    "front": dict(view="front", body=True),
    "back": dict(view="back", body=True),
    "side": dict(view="side_r", body=True),
    "side_l": dict(view="side_l", body=True),
    "q34": dict(view="q34", body=True),
    "q34_other": dict(view="q34_other", body=True),
    "collar": dict(view="face", body=True, over={"span_m": 0.36, "target": (0.0, -0.06, 1.64), "yaw": 18.0, "res": (800, 800)}),
    "clasp": dict(view="face", body=True, over={"span_m": 0.16, "target": tuple(clasp_c) if clasp_c is not None else (-0.18, -0.12, 1.49),
                                               "yaw": -25.0, "pitch": 5.0, "res": (800, 800)}),
    "hem": dict(view="hem", body=True, over={"res": (1200, 800), "span_m": 0.40, "pitch": 10.0,
                                            "target": tuple(hem_t + np.array([0.0, 0.05, 0.08])) if hem_t is not None else (0.0, -0.1, 0.12)}),
    "fray": dict(view="hem", body=True, over={"span_m": 0.10, "target": tuple(fray_t) if fray_t is not None else (-0.22, -0.30, 0.06),
                                             "yaw": -15.0, "pitch": 5.0, "res": (900, 900)}),
    "fabric_far": dict(view="back", body=True, over={"span_m": 0.55, "target": (0.0, 0.2, 1.05), "res": (900, 900)}),
    "fabric_close": dict(view="back", body=True, over={"span_m": 0.14, "target": (0.02, 0.2, 1.10), "res": (900, 900)}),
}


def _s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _l2s(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def composite_white(src, dst):
    """Straight-alpha render (Standard view = sRGB-encoded PNG) over a white backdrop, composited in linear light."""
    im = bpy.data.images.load(src, check_existing=False)
    im.colorspace_settings.name = "Non-Color"          # read the stored (encoded) values
    w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(h, w, 4)
    bpy.data.images.remove(im)
    lin = _s2l(a[:, :, :3]) * a[:, :, 3:4] + (1.0 - a[:, :, 3:4])
    out = np.dstack([_l2s(lin), np.ones((h, w, 1), np.float32)]).astype(np.float32)
    o = bpy.data.images.new("comp", w, h, alpha=True)
    o.colorspace_settings.name = "Non-Color"
    o.pixels.foreach_set(out.ravel())
    o.filepath_raw = dst; o.file_format = "PNG"; o.save()
    bpy.data.images.remove(o)


for name in A.views.split(","):
    spec = VIEWS[name]
    for o in list(bpy.data.objects):
        if o.name.startswith(("ST_", "V2M_Cam")):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in BODY:
        o.hide_render = not spec["body"]
    arm.hide_render = True
    over = dict(spec.get("over", {}))
    if spec["view"] == "photo":
        over["res"] = (V.REF_W * 3, V.REF_H * 3)
    cam, rec = V.make_camera(spec["view"], meshes, over)
    info = ST.studio(sc, cam, centre=(0.0, 0.0, 1.05), yaw_deg=rec.get("yaw", 0.0), card_offset=(0.0, -0.25, 0.25))
    sc.camera = cam
    rgba = os.path.join(A.out, "%s_rgba.png" % name)
    sc.render.filepath = rgba
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    composite_white(rgba, os.path.join(A.out, "%s.png" % name))
    LOG["views"][name] = {"camera": {k: rec[k] for k in ("focal", "yaw", "pitch", "cam_loc", "dist_m") if k in rec},
                          "calibration": info["calibration"], "seconds": round(time.time() - t1, 1),
                          "file": os.path.join(A.out, "%s.png" % name)}
    print("BCV2R", name, round(time.time() - t1, 1), "s", info["calibration"]["white_card_linear_after"], flush=True)
json.dump(LOG, open(os.path.join(A.out, "renders.json"), "w"), indent=1, default=float)
print("BCV2R DONE", round(time.time() - T0, 1))
