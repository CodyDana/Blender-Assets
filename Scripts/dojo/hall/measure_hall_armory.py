"""HALL + ARMORY round (2026-10-01), stage 2: measurements on the composed blend (read-only; nothing is saved).

  1 envelope: every hall-shell vertex (SM_DKH_* instances of the composed level) inside the armory envelope
    (interface.json envelope.with_walls in world: X 15.70-28.30, Y 24.00-44.30, Z 0.38-5.50) outside the listed shell
    intrusions; the lowest shell vertex over the envelope's plan above the armory (the rafter clearance); the highest
    armory vertex
  2 visibility of the new rear pieces (SM_DKH_Rear_Roof / _RoofRidge / _RoofGable / Rear_Frame) from the layout cameras:
    Cycles renders with every other object as a holdout, 1 sample, alpha > 0.5 counted (pixels and the share of the
    frame); trees, terrain and Unreal-only content are not in this blend (the survey's geometry did the same)
  3 the opened doors: the clear opening measured on the meshes (sill top, head-track underside, jamb faces)
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase_HallArmory.blend --python Scripts/dojo/hall/measure_hall_armory.py
Out: WorkFiles/dojo/build/hall_armory/blender/measure.json, renders/vis_<camera>.png
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUTD = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "blender"
L = json.loads((OUTD / "layout_checks.json").read_text(encoding="utf-8"))
I = json.loads((ROOT / "WorkFiles/shared/armory_hall/interface.json").read_text(encoding="utf-8"))
sc = bpy.context.scene
ASM = bpy.data.collections["Assembly"]
OFF = Vector((22.0, 24.0, 0.5))
RES = {}


def piece_of(o):
    return o.name.split("__")[0]


def world_verts(o):
    me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    M = np.array(o.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def envelope():
    ww = I["envelope"]["with_walls"]
    x0, x1 = ww["x"][0] + OFF.x, ww["x"][1] + OFF.x
    y0, y1 = ww["y"][0] + OFF.y, ww["y"][1] + OFF.y
    z0, z1 = ww["z"][0] + OFF.z, ww["z"][1] + OFF.z
    intr = []
    for s in I["envelope"]["shell_intrusions"]:
        b = [s["x"], s["y"], s["z"]]
        intr.append(b)
        if "mirror" in s:
            mx = [float(v) for v in s["mirror"].split("[")[1].rstrip("]").split(",")]
            intr.append([mx, s["y"], s["z"]])
    tol = 0.012
    viol, lowest_over, per_piece = [], None, {}
    for o in ASM.objects:
        p = piece_of(o)
        if not p.startswith("SM_DKH_") or o.type != "MESH":
            continue
        V = world_verts(o)
        inside = (V[:, 0] > x0 + tol) & (V[:, 0] < x1 - tol) & (V[:, 1] > y0 + tol) & (V[:, 1] < y1 - tol) & \
                 (V[:, 2] > z0 + tol) & (V[:, 2] < z1 - tol)
        if inside.any():
            H = V[inside] - np.array(OFF)
            ok = np.zeros(len(H), dtype=bool)
            for b in intr:
                ok |= (H[:, 0] >= b[0][0] - tol) & (H[:, 0] <= b[0][1] + tol) & (H[:, 1] >= b[1][0] - tol) & \
                      (H[:, 1] <= b[1][1] + tol) & (H[:, 2] >= b[2][0] - tol) & (H[:, 2] <= b[2][1] + tol)
            if (~ok).any():
                bad = H[~ok]
                viol.append({"instance": o.name, "n": int(len(bad)),
                             "min_hl": [round(float(v), 3) for v in bad.min(axis=0)],
                             "max_hl": [round(float(v), 3) for v in bad.max(axis=0)]})
        over = (V[:, 0] > x0 + 0.02) & (V[:, 0] < x1 - 0.02) & (V[:, 1] > y0 + 0.13) & (V[:, 1] < y1 - 0.02) & \
               (V[:, 2] >= z1 - tol)
        if over.any():
            zmin = float(V[over][:, 2].min())
            per_piece[p] = min(per_piece.get(p, 99.0), zmin)
            if lowest_over is None or zmin < lowest_over[1]:
                lowest_over = (o.name, zmin)
    akz = max(float(world_verts(o)[:, 2].max()) for o in ASM.objects if piece_of(o).startswith("SM_AK_"))
    RES["envelope"] = {"world_box": [x0, x1, y0, y1, z0, z1], "violations": viol, "n_violations": len(viol),
                       "lowest_shell_vertex_over_the_armory": {"instance": lowest_over[0],
                                                                "z_world": round(lowest_over[1], 4),
                                                                "clearance_over_armory_top_m": round(lowest_over[1] - z1, 4)},
                       "lowest_shell_z_over_the_armory_by_piece": {k: round(v, 4) for k, v in sorted(per_piece.items())},
                       "armory_top_vertex_z_world": round(akz, 4)}


def doors():
    """Clear opening of each centre door bay measured by rays on the render meshes of every hall piece and armory piece
    near the front wall (Y 23.0-25.5): down from +2.0 / up from +1.0 on the door axis (the sill top, the head-track
    underside) and sideways at +0.5, +1.0 and +1.8 above the floor (the jamb faces; the narrowest is kept)."""
    from mathutils.bvhtree import BVHTree
    verts, polys = [], []
    for o in ASM.objects:
        p = piece_of(o)
        if not (p.startswith("SM_DKH_") or p.startswith("SM_AK_")) or o.type != "MESH":
            continue
        V = world_verts(o)
        if V[:, 1].max() < 23.0 or V[:, 1].min() > 25.5:
            continue
        base = len(verts)
        verts += [Vector(v) for v in V]
        polys += [[base + i for i in pl.vertices] for pl in o.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    out = []
    for xc in (20.0, 22.0, 24.0):
        res = {"bay_centre_x": xc}
        for y in (23.95, 24.0, 24.05):
            hd = bvh.ray_cast(Vector((xc, y, 2.0)), Vector((0, 0, -1)), 3.0)
            hu = bvh.ray_cast(Vector((xc, y, 1.0)), Vector((0, 0, 1)), 3.0)
            res.setdefault("sill_top_world", -1.0)
            res.setdefault("head_underside_world", 99.0)
            if hd[0] is not None:
                res["sill_top_world"] = max(res["sill_top_world"], round(hd[0].z, 4))
            if hu[0] is not None:
                res["head_underside_world"] = min(res["head_underside_world"], round(hu[0].z, 4))
        jl, jr = -99.0, 99.0
        for z in (1.0, 1.5, 2.3):
            for y in (23.95, 24.0, 24.05):
                a = bvh.ray_cast(Vector((xc, y, z)), Vector((-1, 0, 0)), 3.0)
                b = bvh.ray_cast(Vector((xc, y, z)), Vector((1, 0, 0)), 3.0)
                if a[0] is not None:
                    jl = max(jl, a[0].x)
                if b[0] is not None:
                    jr = min(jr, b[0].x)
        res["jambs_x"] = [round(jl, 4), round(jr, 4)]
        res["clear_width_m"] = round(jr - jl, 4)
        res["clear_height_m"] = round(res["head_underside_world"] - res["sill_top_world"], 4)
        res["headroom_over_the_gasp_capsule_m"] = round(res["clear_height_m"] - 1.72, 4)
        out.append(res)
    RES["doors"] = out


def visibility():
    rear = {"SM_DKH_Rear_Roof", "SM_DKH_Rear_RoofRidge", "SM_DKH_Rear_RoofGable", "SM_DKH_Rear_Frame"}
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("Black")
    sc.world = w
    em = bpy.data.materials.new("VisWhite")
    em.use_nodes = True
    nt = em.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], out.inputs[0])
    for o in ASM.objects:
        p = piece_of(o)
        k = o.name.split("__")[-1]
        o.hide_render = p.startswith("SM_DGB_Boundary") or p.startswith("SM_DKX_1v1") or p.startswith("SM_DGB_Tree")
        if p in rear:
            o.is_holdout = False
            o.material_slots  # noqa: B018
            o.data = o.data.copy()
            o.data.materials.clear()
            o.data.materials.append(em)
        else:
            o.is_holdout = True
    for c in ("HallArmory_Removed", "Landscape_Removed"):
        cc = bpy.data.collections.get(c)
        if cc:
            for o in cc.objects:
                o.hide_render = True
    names = ["CAM_Establishing", "CAM_EstablishingRef2", "CAM_Ref2Match", "CAM_PlayerEyeSand", "CAM_GateFromStreet",
             "CU_GateFront", "CAM_HallVeranda", "CU_R5_Skyline", "CAM_PeaksOverHall", "CAM_LandscapeRef",
             "CAM_EastYard", "CAM_WallCorner", "CAM_WallTop", "CAM_StairPath", "CU_R5_FarBackground", "CAM_Overview",
             "CAM_HallRoofClimb", "CU_HallUpperRoof", "CAM_FromGateOut"]
    cams = {c["name"]: c for c in L["cameras"]}
    vis = {}
    for nm in names:
        c = cams.get(nm)
        if not c:
            continue
        cam = bpy.data.cameras.new(nm)
        cam.sensor_fit = "HORIZONTAL"
        cam.sensor_width = 36.0
        cam.lens = 18.0 / math.tan(math.radians(c["hfov_deg"]) / 2)
        cam.clip_end = 3000.0
        o = bpy.data.objects.new(nm, cam)
        sc.collection.objects.link(o)
        o.location = c["loc"]
        o.rotation_euler = (Vector(c["look_at"]) - Vector(c["loc"])).to_track_quat("-Z", "Y").to_euler()
        W, H = c.get("out_wh", [1920, 1080])
        sc.camera = o
        sc.render.resolution_x, sc.render.resolution_y = W, H
        sc.render.resolution_percentage = 50
        fp = OUTD / "renders" / f"vis_{nm}.png"
        sc.render.filepath = str(fp)
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(str(fp))
        w_, h_ = im.size
        buf = np.empty(w_ * h_ * 4, dtype=np.float32)
        im.pixels.foreach_get(buf)
        a = buf.reshape(h_, w_, 4)[:, :, 3]
        m = a > 0.5
        n = int(m.sum())
        cols = np.where(m.any(axis=0))[0]
        rows = np.where(m.any(axis=1))[0]
        vis[nm] = {"pixels_at_full_res": n * 4, "share_of_frame": round(n / float(w_ * h_), 6),
                   "bbox_px_full_res": ([int(cols.min()) * 2, int((h_ - 1 - rows.max())) * 2, int(cols.max()) * 2,
                                         int((h_ - 1 - rows.min())) * 2] if n else None), "out_wh": [W, H]}
        print("VIS", nm, vis[nm], flush=True)
    RES["rear_visibility"] = vis


def main():
    if "--doors-only" in sys.argv:
        doors()
        print("DOORS", json.dumps(RES["doors"]), flush=True)
        return
    envelope()
    doors()
    (OUTD / "measure.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
    visibility()
    (OUTD / "measure.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
    print("MEASURE", json.dumps({k: v for k, v in RES.items() if k != "rear_visibility"}), flush=True)


if __name__ == "__main__":
    main()
