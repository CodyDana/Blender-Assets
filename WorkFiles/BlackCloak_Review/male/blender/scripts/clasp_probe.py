import sys, os, json, bpy
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from bpy_extras.object_utils import world_to_camera_view
cl = cloak(); me = cl.data
sc = bpy.context.scene
fit = json.load(open(D + "logs/camfit_male_refine3_constrained.json")); b = fit["top"][0]
Hh = fit["height_m"]; f = b[1]; dist = (Hh / 2 * 1.08) / (12 / f)
cam = make_camera(Vector(fit["target"]), b[2], b[3], f, dist)
sc.render.resolution_x, sc.render.resolution_y = REF_W * 4, REF_H * 4; bpy.context.view_layer.update()
A = json.load(open(D + "compare/measurements_male.json"))["align"]
out = {}
for slot in (2, 3):
    vs = set()
    for p in me.polygons:
        if p.material_index == slot: vs.update(p.vertices)
    pts = [cl.matrix_world @ me.vertices[i].co for i in vs]
    lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
    c = sum(pts, Vector()) / len(pts)
    pc = world_to_camera_view(sc, cam, c)
    xr = pc.x * REF_W; yr = (1 - pc.y) * REF_H
    # corner projections for apparent size
    px = [world_to_camera_view(sc, cam, p) for p in pts]
    xs = [q.x * REF_W * A["s"] + A["tx"] for q in px]; ys = [(1 - q.y) * REF_H * A["s"] + A["ty"] for q in px]
    out[me.materials[slot].name] = {"verts": len(vs), "world_centroid_m": list(c), "world_size_cm": [(hi[i] - lo[i]) * 100 for i in range(3)],
                                    "ref_frame_centre_px": [xr * A["s"] + A["tx"], yr * A["s"] + A["ty"]],
                                    "ref_frame_extent_px": [min(xs), min(ys), max(xs), max(ys)]}
# ring band thickness: radial spread of steel verts around centroid in the ring plane (approx via distances)
vs = set()
for p in me.polygons:
    if p.material_index == 2: vs.update(p.vertices)
pts = [cl.matrix_world @ me.vertices[i].co for i in vs]
c = sum(pts, Vector()) / len(pts)
d = sorted((p - c).length for p in pts)
out["steel_radial_cm_p5_p50_p95_max"] = [d[len(d)//20]*100, d[len(d)//2]*100, d[len(d)*19//20]*100, d[-1]*100]
# the pin: steel verts far from the ring's median radius band
json.dump(out, open(D + "logs/clasp_probe.json", "w"), indent=1)
print("CLASP", json.dumps(out))
