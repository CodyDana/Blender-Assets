"""Blender-side analysis of Unreal's round-trip export + LOD1-switch legibility render (read-only)."""
import json
import math
from pathlib import Path

import bpy
import mathutils
import numpy as np

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\exact\pbuv0926")
PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
RT = HERE / "pbuv_roundtrip.fbx"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
BC = PROJ / "Exports" / "PaperBomb" / "Textures" / "T_PaperBomb_BC.png"
OUT = HERE / "pbuv_post.json"
rep = {}


def plan_hull(co):
    pts = sorted(set((round(float(x), 3), round(float(y), 3)) for x, y in co[:, :2]))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 1e-6:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 1e-6:
            up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    edges = []
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        edges.append([round(math.hypot(b[0] - a[0], b[1] - a[1]), 3),
                      round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0, 2)])
    return h, edges


def uv_overlap(o, idx, n=256):
    me = o.data
    me.calc_loop_triangles()
    if len(me.uv_layers) <= idx:
        return None
    lay = me.uv_layers[idx]
    uv = np.empty(len(me.loops) * 2)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    cnt = np.zeros((n, n), np.int32)
    ys, xs = np.mgrid[0:n, 0:n]
    px = (xs + 0.5) / n
    py = (ys + 0.5) / n
    for t in me.loop_triangles:
        a, b, c = uv[t.loops[0]], uv[t.loops[1]], uv[t.loops[2]]
        x0 = int(max(0, math.floor(min(a[0], b[0], c[0]) * n)))
        x1 = int(min(n, math.ceil(max(a[0], b[0], c[0]) * n)))
        y0 = int(max(0, math.floor(min(a[1], b[1], c[1]) * n)))
        y1 = int(min(n, math.ceil(max(a[1], b[1], c[1]) * n)))
        if x1 <= x0 or y1 <= y0:
            continue
        X = px[y0:y1, x0:x1]
        Y = py[y0:y1, x0:x1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-14:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        l3 = 1 - l1 - l2
        cnt[y0:y1, x0:x1] += ((l1 > 1e-3) & (l2 > 1e-3) & (l3 > 1e-3)).astype(np.int32)
    return {"covered_frac": round(float((cnt > 0).mean()), 4), "overlap_texels_256": int((cnt > 1).sum())}


# ---------------- round trip -----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(RT))
rt = {}
for o in bpy.data.objects:
    e = {"type": o.type, "parent": o.parent.name if o.parent else None}
    if o.type == "MESH":
        me = o.data
        me.calc_loop_triangles()
        mw = np.array(o.matrix_world)
        co = np.array([v.co[:] for v in me.vertices])
        co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3] * 1000.0
        e["triangles"] = len(me.loop_triangles)
        e["vertices"] = len(me.vertices)
        e["size_mm"] = [round(float(x), 3) for x in np.ptp(co, axis=0)]
        e["uv_layers"] = []
        for lay in me.uv_layers:
            uv = np.empty(len(me.loops) * 2)
            lay.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            e["uv_layers"].append({"name": lay.name, "min": [round(float(v), 5) for v in uv.min(0)],
                                   "max": [round(float(v), 5) for v in uv.max(0)]})
        e["materials"] = [m.name if m else None for m in me.materials]
        if o.name.upper().startswith("UCX"):
            h, ed = plan_hull(co)
            e["plan_hull_vertices"] = len(h)
            e["plan_edges_len_angle"] = ed
            e["world_min_mm"] = [round(float(x), 3) for x in co.min(0)]
            e["world_max_mm"] = [round(float(x), 3) for x in co.max(0)]
    rt[o.name] = e
rep["roundtrip"] = rt
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.upper().startswith("UCX")]
lod0 = max(meshes, key=lambda o: len(o.data.polygons))
rep["roundtrip_lod0_name"] = lod0.name
rep["lightmap_uv1_overlap"] = uv_overlap(lod0, 1)

# ---------------- LOD1-switch legibility render -----------------
SS1 = 0.1768
R_CM = 8.53969                    # Unreal's own bounds sphere radius (pass B)
PX_PER_MM = SS1 * 1080.0 / (2.0 * R_CM * 10.0)
rep["lod1_switch_px_per_mm_1080p"] = round(PX_PER_MM, 4)


def render_lod(lodname, res_px, out_png, ppmm):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    sc = bpy.context.scene
    keep = None
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name == lodname:
            keep = o
        elif o.type == "MESH":
            o.hide_render = True
    img = bpy.data.images.load(str(BC))
    img.colorspace_settings.name = "sRGB"
    mat = bpy.data.materials.new("pbuv_bc")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.interpolation = "Linear"
    em = nt.nodes.new("ShaderNodeEmission")
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], outn.inputs["Surface"])
    keep.data.materials.clear()
    keep.data.materials.append(mat)
    cam_d = bpy.data.cameras.new("c")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = res_px / ppmm / 1000.0
    cam = bpy.data.objects.new("c", cam_d)
    sc.collection.objects.link(cam)
    mw = keep.matrix_world
    ctr = sum((mw @ v.co for v in keep.data.vertices), mathutils.Vector()) / len(keep.data.vertices)
    cam.location = (ctr.x, ctr.y, ctr.z + 1.0)
    cam.rotation_euler = (0, 0, math.radians(90))
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
    sc.cycles.device = "CPU"
    sc.render.resolution_x = res_px
    sc.render.resolution_y = res_px
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.18, 0.18, 0.18)
    sc.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(out_png))
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    return np.flipud(px.reshape(h, w, 4)[:, :, :3])


res = 260
a1 = render_lod("SM_PaperBomb_LOD1", res, HERE / "pbuv_lod1_at_switch.png", PX_PER_MM)
a0 = render_lod("SM_PaperBomb_LOD0", res, HERE / "pbuv_lod0_at_switch.png", PX_PER_MM)
# 4x reference view of LOD1 for eyeballing (same framing, 4x the pixels)
render_lod("SM_PaperBomb_LOD1", res * 4, HERE / "pbuv_lod1_x4_reference.png", PX_PER_MM * 4)
diff = np.abs(a1 - a0)
rep["lod0_vs_lod1_at_switch"] = {"mean_abs": round(float(diff.mean()), 5),
                                 "p99_abs": round(float(np.percentile(diff, 99)), 4),
                                 "max_abs": round(float(diff.max()), 4)}
lum = 0.2126 * a1[..., 0] + 0.7152 * a1[..., 1] + 0.0722 * a1[..., 2]
bgv = float(np.median(np.r_[lum[0, :], lum[-1, :], lum[:, 0], lum[:, -1]]))
card = np.abs(lum - bgv) > 0.02
ys, xs = np.nonzero(card)
rep["background_lum"] = round(bgv, 4)
rep["card_px_bbox_at_switch"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()),
                                 int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
paper = float(np.percentile(lum[card], 90))
ink = float(np.percentile(lum[card], 3))
rep["lod1_render_lum_paper_p90"] = round(paper, 4)
rep["lod1_render_lum_ink_p3"] = round(ink, 4)
rep["lod1_render_michelson"] = round((paper - ink) / (paper + ink), 4)
rep["lod1_dark_frac"] = round(float((lum[card] < 0.5 * paper).mean()), 4)
OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
print("PBUV_POST", json.dumps(rep)[:5000])
