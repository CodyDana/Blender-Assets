"""Extra checks: HEAD socket clearance by ray casts on the shipped LOD0, and ORM/N channel facts.

    blender.exe -b --factory-startup --python bhv_extra.py
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v2")
TEX = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\BlackHat\Textures")
side = json.loads(Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\BlackHat\SM_BlackHat.sockets.json").read_text())
out = {}
v = np.load(HERE / "truth_SM_BlackHat_LOD0_verts_cm.npy")
tv = np.load(HERE / "truth_SM_BlackHat_LOD0_tv.npy")
bvh = BVHTree.FromPolygons([Vector(p) for p in v.tolist()], tv.tolist())
s = Vector(side["sockets"][0]["location_cm"])
rays = {}
for name, d in (("up", (0, 0, 1)), ("down", (0, 0, -1))):
    hit = bvh.ray_cast(s, Vector(d))
    rays[name] = None if hit[0] is None else {"distance_cm": hit[3], "hit_z": hit[0].z}
# clearance in a ring of upward-tilted directions (how far the inner cone is around the socket)
ring = []
for el in (0, 15, 30, 45):
    ds = []
    for az in range(0, 360, 30):
        dvec = Vector((math.cos(math.radians(az)) * math.cos(math.radians(el)),
                       math.sin(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
        hit = bvh.ray_cast(s, dvec)
        ds.append(None if hit[0] is None else round(hit[3], 3))
    ring.append({"elevation_deg": el, "distances_cm": ds})
nearest = bvh.find_nearest(s)
out["socket"] = {"location_cm": list(s), "ray_up": rays["up"], "ray_down": rays["down"],
                 "nearest_surface_cm": nearest[3], "ring": ring}
for n in ("T_BlackHat_Straw_ORM", "T_BlackHat_Cloth_ORM", "T_BlackHat_Straw_N", "T_BlackHat_Cloth_N"):
    img = bpy.data.images.load(str(TEX / f"{n}.png"))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rec = {"channels": img.channels, "depth": img.depth,
           "min": px.min(0).round(4).tolist(), "max": px.max(0).round(4).tolist(), "mean": px.mean(0).round(4).tolist()}
    if n.endswith("_N"):
        xyz = px[:, :3] * 2 - 1
        L = np.linalg.norm(xyz, axis=1)
        rec["len_p1_p50_p99"] = np.percentile(L, [1, 50, 99]).round(4).tolist()
        rec["z_min"] = float(xyz[:, 2].min())
    out[n] = rec
    bpy.data.images.remove(img)
(HERE / "extra.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("BHV_EXTRA_DONE")
