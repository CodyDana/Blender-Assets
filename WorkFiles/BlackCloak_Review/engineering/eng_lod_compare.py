"""Import the three static LOD FBXs into a fresh scene, measure LOD1/LOD2 deviation from LOD0 (BVH nearest),
silhouette IoU from front and side, and render LOD0|LOD1|LOD2 side by side (Workbench). Writes only into the
review folder."""
import bpy, json, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

outdir = sys.argv[sys.argv.index("--") + 1]
X = "C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
groups = {}
for i, f in enumerate(["BlackCloak.fbx", "BlackCloak_LOD1.fbx", "BlackCloak_LOD2.fbx"]):
    before = set(sc.objects)
    bpy.ops.import_scene.fbx(filepath=X + f, use_anim=False)
    new = [o for o in sc.objects if o not in before and o.type == "MESH"]
    groups[i] = new


def world_tris(objs):
    V = []; P = []
    for o in objs:
        me = o.data; me.calc_loop_triangles(); mw = o.matrix_world
        base = len(V)
        V.extend([(mw @ v.co)[:] for v in me.vertices])
        P.extend([tuple(base + k for k in t.vertices) for t in me.loop_triangles])
    return np.array(V), P

res = {}
V0, P0 = world_tris(groups[0])
T0 = BVHTree.FromPolygons(V0.tolist(), P0)


def sil(V, P, axes, res_px=400, lo=None, hi=None):
    pts = V[:, axes]
    g = np.zeros((res_px, res_px), bool)
    t = (pts - lo) / (hi - lo) * (res_px - 1)
    for tri in P:
        a, b, c = t[list(tri)]
        x0 = int(max(0, math.floor(min(a[0], b[0], c[0])))); x1 = int(min(res_px - 1, math.ceil(max(a[0], b[0], c[0]))))
        y0 = int(max(0, math.floor(min(a[1], b[1], c[1])))); y1 = int(min(res_px - 1, math.ceil(max(a[1], b[1], c[1]))))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (1 - l1 - l2 >= -1e-6)
        g[y0:y1 + 1, x0:x1 + 1] |= m
    return g

lo_f = V0[:, [0, 2]].min(0) - 0.02; hi_f = V0[:, [0, 2]].max(0) + 0.02
lo_s = V0[:, [1, 2]].min(0) - 0.02; hi_s = V0[:, [1, 2]].max(0) + 0.02
S0f = sil(V0, P0, [0, 2], lo=lo_f, hi=hi_f); S0s = sil(V0, P0, [1, 2], lo=lo_s, hi=hi_s)
for i in (1, 2):
    V, P = world_tris(groups[i])
    d = np.array([T0.find_nearest(Vector(p))[3] for p in V])
    Sf = sil(V, P, [0, 2], lo=lo_f, hi=hi_f); Ss = sil(V, P, [1, 2], lo=lo_s, hi=hi_s)
    res[f"LOD{i}"] = {"tris": len(P), "ratio_vs_lod0": round(len(P) / len(P0), 3),
                      "vert_to_lod0_surface_cm_mean_p95_max": [round(float(x) * 100, 3) for x in (d.mean(), np.percentile(d, 95), d.max())],
                      "front_silhouette_iou": round(float((Sf & S0f).sum() / (Sf | S0f).sum()), 4),
                      "side_silhouette_iou": round(float((Ss & S0s).sum() / (Ss | S0s).sum()), 4)}
res["LOD0"] = {"tris": len(P0)}
# render
for i, objs in groups.items():
    for o in objs:
        o.location.x += (i - 1) * 1.25
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 4.0
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.55, 0.55, 0.58)
sc.display.shading.show_cavity = True
sc.display.shading.show_object_outline = False
sc.render.resolution_x = 1800; sc.render.resolution_y = 1000
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w
renders = {}
for name, loc, rot in [("front", (0, -6, 0.87), (math.radians(90), 0, 0)),
                       ("back", (0, 6, 0.87), (math.radians(90), 0, math.radians(180)))]:
    cam.location = loc; cam.rotation_euler = rot
    p = f"{outdir}/eng_lod_compare_{name}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    renders[name] = p
# close-up of the collar/shoulder at LOD0 vs LOD2 wireframe-free
cam_data.ortho_scale = 0.9
for i in (0, 2):
    cam.location = ((i - 1) * 1.25, -6, 1.45); cam.rotation_euler = (math.radians(90), 0, 0)
    p = f"{outdir}/eng_lod{i}_collar_closeup.png"
    sc.render.filepath = p; sc.render.resolution_x = 900; sc.render.resolution_y = 900
    bpy.ops.render.render(write_still=True)
    renders[f"lod{i}_collar"] = p
res["renders"] = renders
with open(outdir + "/eng_lod_compare.json", "w") as f:
    json.dump(res, f, indent=1)
print("LOD_DONE", json.dumps(res))
