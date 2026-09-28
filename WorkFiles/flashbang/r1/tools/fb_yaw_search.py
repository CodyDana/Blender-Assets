"""DEV/MEASURE: per-view yaw and hole-phase fit by rendering flat label masks of LOD0 in the reference's camera.

    blender -b --factory-startup --python fb_yaw_search.py -- out.json [step_deg]

For every yaw y (the object's local azimuth facing the camera) all four copies are rendered with flat emission:
paint (LOOK 0) green, every other surface red, background black.  Scores per view (inside that view's column band):
  S_sil(v, y)   IoU of our silhouette with the Study's traced silhouette polygon (spec outlines)
  S_paint(v, y) IoU of our paint with the reference's olive-paint mask (|R-G| <= 6, G-B >= 8, G >= 22)
A hole-phase shift D (holes rotated by D relative to the lever) is scored as
  T(D) = sum_v max_y [ S_sil(v, y) + S_paint(v, y - D) ]   (the paint mask moves with the holes)
"""
import sys, json, math
from pathlib import Path
P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts")); sys.path.insert(0, str(P / "Scripts/props"))
import bpy, numpy as np
from props_lib import flashbang_geom as G, flashbang_blender as FB, flashbang_look as LK
from props_lib.flashbang_spec import FLASHBANG as S

a = sys.argv[sys.argv.index("--") + 1:]
out = Path(a[0]).resolve()
step = float(a[1]) if len(a) > 1 else 4.0
work = out.parent / "yaw_frames"
work.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
mb = G.build_lod(S, 0)[0]
FB.fix_island_handedness(mb)
pk = G.pack_islands([mb])


def emis(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = 1.0
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


mp, ms = emis("paint", (0, 1, 0)), emis("steel", (1, 0, 0))
ob = FB.to_blender(mb, pk, "SM_Flashbang_LOD0", materials=[mp, ms])
# walls are in the paint slot but are not paint: give LOOK 6 faces the steel material via a third slot
ob.data.materials.append(ms)
looks = np.empty(len(ob.data.polygons), np.int32)
ob.data.attributes["fb_look"].data.foreach_get("value", looks)
mi = np.empty(len(ob.data.polygons), np.int32)
ob.data.polygons.foreach_get("material_index", mi)
mi[looks == 6] = 2
ob.data.polygons.foreach_set("material_index", mi)
objs = {"v1": [ob]}
for v in ("v2", "v3", "v4"):
    o2 = ob.copy()
    bpy.context.scene.collection.objects.link(o2)
    objs[v] = [o2]
sc = LK.setup_cycles(4, denoise=False)
sc.cycles.use_denoising = False
sc.cycles.filter_width = 0.01
w = bpy.data.worlds.new("black")
w.use_nodes = True
next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Color"].default_value = (0, 0, 0, 1)
sc.world = w
rig = LK.Rig()
LK.row_camera(rig)

ref = np.load(P / "WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3] * 255.0
R, Gc, B = ref[..., 0], ref[..., 1], ref[..., 2]
ref_paint = (np.abs(R - Gc) <= 6) & ((Gc - B) >= 8) & (Gc >= 22)
spec = json.load(open(P / "WorkFiles/flashbang/flashbang_spec.json"))
H, W = ref.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]


def poly_mask(poly):
    poly = np.asarray(poly, float)
    m = np.zeros((H, W), bool)
    x0, y0 = poly.min(0).astype(int)
    x1, y1 = poly.max(0).astype(int) + 1
    sub_y, sub_x = yy[y0:y1, x0:x1] + 0.5, xx[y0:y1, x0:x1] + 0.5
    inside = np.zeros(sub_x.shape, bool)
    n = len(poly)
    for i in range(n):
        xa, ya = poly[i]
        xb, yb = poly[(i + 1) % n]
        cond = ((ya > sub_y) != (yb > sub_y))
        xi = (xb - xa) * (sub_y - ya) / (yb - ya + 1e-12) + xa
        inside ^= cond & (sub_x < xi)
    m[y0:y1, x0:x1] = inside
    return m


sil = {v: poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"]) for v in ("v1", "v2", "v3", "v4")}
bands = {"v1": (40, 345), "v2": (345, 615), "v3": (615, 950), "v4": (950, 1240)}
rows = (30, 725)
yaws = np.arange(-180.0, 180.0, step)
S_sil = {v: [] for v in bands}
S_paint = {v: [] for v in bands}
for y in yaws:
    LK.place_row(objs, {v: float(y) for v in objs})
    f = work / "yaw.png"
    LK.render(f)
    im = LK.load_png(f)
    ours_obj = im.max(axis=2) > 0.5
    ours_paint = (im[..., 1] > 0.5) & (im[..., 0] < 0.5)
    for v, (x0, x1) in bands.items():
        sl = (slice(rows[0], rows[1]), slice(x0, x1))
        a_, b_ = ours_obj[sl], sil[v][sl]
        S_sil[v].append(float((a_ & b_).sum() / max((a_ | b_).sum(), 1)))
        a_, b_ = ours_paint[sl], ref_paint[sl]
        S_paint[v].append(float((a_ & b_).sum() / max((a_ | b_).sum(), 1)))
    print("yaw", y, {v: (round(S_sil[v][-1], 3), round(S_paint[v][-1], 3)) for v in bands}, flush=True)
n = len(yaws)
best_D = None
table = []
for k in range(n):
    D = float(yaws[k] + 180.0)            # shift in steps
    tot = 0.0
    per = {}
    for v in bands:
        sc_ = [S_sil[v][i] + S_paint[v][(i - k) % n] for i in range(n)]
        i = int(np.argmax(sc_))
        per[v] = {"yaw": float(yaws[i]), "score": round(sc_[i], 4), "sil": round(S_sil[v][i], 4),
                  "paint": round(S_paint[v][(i - k) % n], 4)}
        tot += sc_[i]
    table.append({"shift_deg": (D % 360.0), "total": round(tot, 4), "per_view": per})
table.sort(key=lambda t: -t["total"])
res = {"hole_phase_now": S.hole_phase_deg, "step": step, "best": table[:8],
       "no_shift": next(t for t in table if abs(t["shift_deg"]) < 1e-6 or abs(t["shift_deg"] - 360) < 1e-6),
       "curves": {"yaws": yaws.tolist(), "sil": S_sil, "paint": S_paint}}
out.write_text(json.dumps(res, indent=1))
print(json.dumps(res["best"][:3], indent=1))
print("no shift", json.dumps(res["no_shift"], indent=1))
