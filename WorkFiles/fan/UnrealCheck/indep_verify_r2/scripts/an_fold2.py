"""Offline part 2: (a) leaf beyond a guard's face INSIDE that guard's footprint (a real poke-through) from the
engine's poses; (b) lateral overhang of sticks/leaf past the guards when closed; (c) see-through holes in the engine's
HDR coverage renders; (d) tassel vs fan interpenetration at the Tassel socket."""
import bpy, json, math, sys, glob, os
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

D = sys.argv[sys.argv.index("--") + 1]
B = json.load(open(D + "/ueout/ivB.json"))
RAW = json.load(open(D + "/ueout/ivB_raw.json"))
RUN = json.load(open(D + "/ueout/ivB_runtime.json"))
REF = B["skeleton"]["ref_comp"]
arm = bpy.data.objects["root"]
out = {}


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def fwd(P, b, pts):      # bind comp -> posed comp
    R = REF[b]
    return (pts - np.array(R[:3])) @ quat_mat(R[3:7]) @ quat_mat(P[b][3:7]).T + np.array(P[b][:3])


def inv(P, b, pts):      # posed comp -> bind comp of bone b
    R = REF[b]
    return (pts - np.array(P[b][:3])) @ quat_mat(P[b][3:7]) @ quat_mat(R[3:7]).T + np.array(R[:3])


def mesh_bones(name):
    o = bpy.data.objects[name]
    M = arm.matrix_world.inverted() @ o.matrix_world
    gn = [g.name for g in o.vertex_groups]
    per = {}
    for v in o.data.vertices:
        b = max((g.weight, gn[g.group]) for g in v.groups if g.weight > 0)[1]
        p = M @ v.co
        per.setdefault(b, []).append([p.x * 100, -p.y * 100, p.z * 100])
    return {b: np.array(v) for b, v in per.items()}


LODV = {L: mesh_bones(n) for L, n in enumerate(["SK_Fan", "SK_Fan_LOD1", "SK_Fan_LOD2"])}


def guard_outline(gv, nb=200):
    r = np.hypot(gv[:, 0], gv[:, 1])
    th = np.arctan2(gv[:, 1], gv[:, 0])
    edges = np.linspace(0, r.max() + 1e-6, nb + 1)
    lo = np.full(nb, np.nan); hi = np.full(nb, np.nan)
    idx = np.clip(np.digitize(r, edges) - 1, 0, nb - 1)
    for i in range(nb):
        m = idx == i
        if m.any():
            lo[i] = th[m].min(); hi[i] = th[m].max()
    return edges, lo, hi


GUARD = {}
for g in ("stick_00", "stick_25"):
    gv = LODV[0][g]
    GUARD[g] = {"outline": guard_outline(gv), "zmax": gv[:, 2].max(), "zmin": gv[:, 2].min()}


def poke(P, lods=(0, 1, 2)):
    """leaf vertices beyond the front guard's front face (or the rear guard's back face) that lie INSIDE that
    guard's footprint (seen along the rivet axis): the leaf would show through / over the guard."""
    worst = {"front": 0.0, "rear": 0.0, "front_n": 0, "rear_n": 0}
    for L in lods:
        for b, v in LODV[L].items():
            if not b.startswith("leaf_"):
                continue
            X = fwd(P, b, v)
            for g, side in (("stick_00", "front"), ("stick_25", "rear")):
                G = GUARD[g]
                sel = X[:, 2] > G["zmax"] if side == "front" else X[:, 2] < G["zmin"]
                if not sel.any():
                    continue
                Y = inv(P, g, X[sel])
                r = np.hypot(Y[:, 0], Y[:, 1]); th = np.arctan2(Y[:, 1], Y[:, 0])
                edges, lo, hi = G["outline"]
                k = np.clip(np.digitize(r, edges) - 1, 0, len(lo) - 1)
                inside = (r <= edges[-1]) & ~np.isnan(lo[k]) & (th >= lo[k] - 1e-6) & (th <= hi[k] + 1e-6)
                if inside.any():
                    depth = (X[sel][inside, 2] - G["zmax"]) if side == "front" else (G["zmin"] - X[sel][inside, 2])
                    worst[side] = max(worst[side], float(depth.max()) * 10)
                    worst[side + "_n"] += int(inside.sum())
    return worst


pk = {}
for label, sets in (("raw", RAW), ("runtime", RUN)):
    for anim, poses in sets.items():
        w = {"front": 0.0, "rear": 0.0, "front_n": 0, "rear_n": 0, "worst_t": None}
        for t, P in poses.items():
            r = poke(P)
            if r["front"] + r["rear"] > w["front"] + w["rear"]:
                w["worst_t"] = t
            for k in ("front", "rear"):
                w[k] = max(w[k], r[k]); w[k + "_n"] = max(w[k + "_n"], r[k + "_n"])
        pk[f"{label}:{anim}"] = w
out["poke_through_mm"] = pk
# ---------------------------------------------------------------- closed: lateral overhang past the guards (tip region)
P0 = RAW["A_Fan_Openness"]["0.00000"]
def lat(P, b, L=0):
    X = fwd(P, b, LODV[L][b])
    m = X[:, 0] > 15.0            # tip region, x > 150 mm
    return (X[m, 1].min(), X[m, 1].max()) if m.any() else None
g0 = lat(P0, "stick_00"); g25 = lat(P0, "stick_25")
glo = min(g0[0], g25[0]); ghi = max(g0[1], g25[1])
over = {}
for b in LODV[0]:
    r = lat(P0, b)
    if r is None:
        continue
    o = max(glo - r[0], r[1] - ghi)
    if o > 0.005:
        over[b] = round(o * 10, 3)
out["closed_tip_region"] = {"guards_union_y_cm": [glo, ghi], "front_guard_y_cm": list(g0), "rear_guard_y_cm": list(g25),
                            "bones_overhanging_mm": dict(sorted(over.items(), key=lambda kv: -kv[1])[:12]),
                            "leaf_overhang_max_mm": max([v for k, v in over.items() if k.startswith("leaf")] or [0]),
                            "stick_overhang_max_mm": max([v for k, v in over.items() if k.startswith("stick")] or [0])}
# closed overall extents
pts = np.vstack([fwd(P0, b, v) for b, v in LODV[0].items()])
out["closed_extent_mm"] = ((pts.max(0) - pts.min(0)) * 10).round(3).tolist()
# ---------------------------------------------------------------- see-through holes in the HDR coverage captures
holes = {}
for f in sorted(glob.glob(D + "/ueout/renders/*_hdr.exr")):
    im = bpy.data.images.load(f)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    a = px[..., 3]
    bg = a > 0.5                       # alpha 1 = empty (nothing rendered)
    reach = np.zeros_like(bg)
    reach[0, :] = bg[0, :]; reach[-1, :] = bg[-1, :]; reach[:, 0] = bg[:, 0]; reach[:, -1] = bg[:, -1]
    for _ in range(4000):
        n = reach.copy()
        n[1:, :] |= reach[:-1, :]; n[:-1, :] |= reach[1:, :]; n[:, 1:] |= reach[:, :-1]; n[:, :-1] |= reach[:, 1:]
        n &= bg
        if (n == reach).all():
            break
        reach = n
    hole = bg & ~reach
    # connected hole blobs (4-neighbour) count via simple labelling on the sparse set
    ys, xs = np.nonzero(hole)
    lab = {}
    blobs = 0
    s = set(zip(ys.tolist(), xs.tolist()))
    seen = set()
    sizes = []
    for p in s:
        if p in seen:
            continue
        blobs += 1
        stack = [p]; seen.add(p); n_ = 0
        while stack:
            y, x = stack.pop(); n_ += 1
            for q in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if q in s and q not in seen:
                    seen.add(q); stack.append(q)
        sizes.append(n_)
    holes[os.path.basename(f)] = {"geometry_px": int((~bg).sum()), "hole_px": int(hole.sum()), "hole_blobs": blobs,
                                  "largest_blob_px": max(sizes) if sizes else 0,
                                  "hole_mask_bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None}
    if hole.sum():
        m = np.zeros((h, w, 4), np.float32)
        m[..., 0] = hole; m[..., 1] = (~bg) * 0.25; m[..., 2] = (~bg) * 0.25; m[..., 3] = 1
        o = bpy.data.images.new("m", w, h, alpha=True)
        o.pixels[:] = m.ravel()
        o.filepath_raw = D + "/holes_" + os.path.basename(f).replace("_hdr.exr", ".png"); o.file_format = "PNG"; o.save()
out["see_through_holes"] = holes
# ---------------------------------------------------------------- tassel on its socket vs the fan (BVH, Blender, rest)
SC = json.load(open(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/Fan/SK_Fan.skeletal.json"))
s = next(x for x in SC["sockets"] if x["name"] == "Tassel")
Ms = Matrix(s["matrix"]).to_4x4()
Ms.translation = Vector([c / 1000.0 for c in s["location_mm"]])
tarm = bpy.data.objects["root_tassel"]
dg = bpy.context.evaluated_depsgraph_get()


def bvh_of(obj, M):
    e = obj.evaluated_get(dg)
    me = e.to_mesh()
    vs = [M @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs), vs


tas = bpy.data.objects["SK_Fan_Tassel"]
Mt = Ms @ tarm.matrix_world.inverted() @ tas.matrix_world          # tassel mesh -> fan armature space
tb, tv = bvh_of(tas, Mt)
fan = bpy.data.objects["SK_Fan"]
Mf = arm.matrix_world.inverted() @ fan.matrix_world
tres = {}
if arm.animation_data is None:
    arm.animation_data_create()
act = bpy.data.actions["A_Fan_Openness"]
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass
for f in (0, 3, 9, 30, 60):
    bpy.context.scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    fb, fv = bvh_of(fan, Mf)
    pairs = fb.overlap(tb)
    # which fan parts: polygon index -> material
    me = fan.evaluated_get(dg).to_mesh()
    mats = sorted({fan.data.materials[me.polygons[i].material_index].name for i, _ in pairs})
    fan.evaluated_get(dg).to_mesh_clear()
    tres[str(f)] = {"overlapping_face_pairs": len(pairs), "fan_materials": mats}
# tassel vertices inside the fan's closed parts: depth of the deepest cord vertex behind the fan's back face
tvz = np.array([[v.x, v.y, v.z] for v in tv]) * 1000.0     # mm, fan armature space
near = tvz[(tvz[:, 1] > -25) & (tvz[:, 1] < 0.5)]
tres["cord_z_mm_near_lobe"] = [float(near[:, 2].min()), float(near[:, 2].max())] if len(near) else None
tres["fan_back_face_z_mm"] = float(min((Mf @ v.co).z for v in fan.data.vertices) * 1000.0)
out["tassel_vs_fan"] = tres
json.dump(out, open(D + "/an_fold2.json", "w"), indent=1)
print("FOLD2_DONE")
print(json.dumps({k: v for k, v in out.items() if k != "see_through_holes"}, indent=1))
print(json.dumps(out["see_through_holes"], indent=0)[:6000])
