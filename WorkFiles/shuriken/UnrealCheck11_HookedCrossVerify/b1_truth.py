"""UnrealCheck11 (independent Unreal verifier incl. handedness, SM_Shuriken_HookedCross) - Blender-side truth.
READ ONLY, never saves:

    blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python b1_truth.py

Written fresh for this verification.  Expectations come from three independent places:
  SPEC   the brief (tips at r = 50 mm, 35 deg CCW of each arm, plate 2.5 mm, R 98 mm back arc crossing the arm axis at
         41.46 mm, 0.56 mm junction fillets on arm edges 5.62 - 0.0397 u), the pack's 1.0 / 0.10 / 0.035 screen sizes
         scaled by bounds radius / 50 mm, and the LOD ceilings 2500 / 900 / 250
  BLEND  the hooked-cross objects in Assets/Shuriken.blend (evaluated meshes, UCX, SOCKET_ Empties, LodGroup)
  FBX    a factory-startup re-import of the exact shipped bytes (SHA-256 recorded), world matrices baked
Handedness truth: hc_chirality.analyse on what a viewer ABOVE (+Z) and BELOW (-Z) sees, in the viewer's own screen
coordinates, for every LOD of both the .blend and the FBX re-import, plus a mirrored negative control.
The six-point CONTROL: its SOCKET Grip Empty (polar angle in Blender) and its FBX LOD0 corners (position, UV0) for
the UV-labelled mapping fit done later against Unreal's render data.
Writes b1_truth.json next to this file.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck11_HookedCrossVerify"
sys.path.insert(0, str(HERE))
import hc_chirality as HC  # noqa: E402

MESH = "SM_Shuriken_HookedCross"
CTRL = "SM_Shuriken_SixPoint"
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
CTRL_FBX = PROJ / "Exports" / "Shuriken" / f"{CTRL}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"

TOP = {"forward": (0.0, 0.0, -1.0), "right": (1.0, 0.0, 0.0), "up": (0.0, 1.0, 0.0)}      # Blender top view
BOTTOM = {"forward": (0.0, 0.0, 1.0), "right": (1.0, 0.0, 0.0), "up": (0.0, -1.0, 0.0)}   # the same camera turned 180 deg about X


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spec():
    R, cross_x = 98.0, 41.46
    tip = (50.0 * math.cos(math.radians(35.0)), 50.0 * math.sin(math.radians(35.0)))
    tx, ty = tip
    # the arc centre lies on the perpendicular bisector of the chord (cross_x, 0) -> tip, on the far side (cx < 0)
    mx, my = (cross_x + tx) / 2.0, ty / 2.0
    chord = math.hypot(tx - cross_x, ty)
    h = math.sqrt(R * R - (chord / 2.0) ** 2)
    dx, dy = -(ty) / chord, (tx - cross_x) / chord
    cands = [(mx + h * dx, my + h * dy), (mx - h * dx, my - h * dy)]
    cx, cy = min(cands, key=lambda c: c[0])
    arc_max_x = cx + R if 0.0 <= cy <= ty else None
    # concave junction fillet midpoint: edges y = 5.62 - 0.0397 x and x = 5.62 - 0.0397 y meet on the diagonal
    corner = 5.62 / 1.0397
    half_gap = math.radians(45.0 + math.degrees(math.atan(0.0397)))
    fil = corner + (0.56 / math.sin(half_gap) - 0.56) / math.sqrt(2.0)
    sizes = [1.0, 0.10, 0.035]
    return {"tip_radius_mm": 50.0, "tip_offset_ccw_deg": 35.0, "thickness_mm": 2.5, "arc_radius_mm": R,
            "arc_axis_crossing_mm": cross_x, "arc_centre_mm": [cx, cy], "tip_xy_mm": list(tip),
            "plan_half_extent_mm_analytic": arc_max_x,
            "size_cm_analytic": [2 * arc_max_x / 10.0, 2 * arc_max_x / 10.0, 0.25],
            "grip_fillet_midpoint_mm": [fil, fil, 0.0],
            "lod_ceilings": [2500, 900, 250],
            "screen_sizes_expected": sizes,
            "switch_distance_m_16x9_90deg": [None] + [round(1.7778 * 0.05 / x, 4) for x in sizes[1:]]}


def ue_cm(v):
    """Blender metres -> Unreal cm under the legacy importer's documented conversion (ConvertPos: X kept, Y negated,
    Z kept).  Used only to PREDICT; summarize.py establishes the conversion independently from the control."""
    return [v[0] * 100.0, -v[1] * 100.0, v[2] * 100.0]


def mesh_arrays(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world.copy()
    m3 = mw.to_3x3()
    verts = [tuple(mw @ v.co) for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    tri_loops = [tuple(t.loops) for t in me.loop_triangles]
    loop_vert = [lp.vertex_index for lp in me.loops]
    uvs = [uv.name for uv in me.uv_layers]
    uv0 = [tuple(d.uv) for d in me.uv_layers[0].data] if me.uv_layers else []
    nrm = [tuple((m3 @ n.vector).normalized()) for n in me.corner_normals]   # det > 0 is checked separately
    npoly = len(me.polygons)
    ev.to_mesh_clear()
    return {"verts": verts, "tris": tris, "tri_loops": tri_loops, "loop_vert": loop_vert, "uv_names": uvs,
            "uv0": uv0, "loop_normals": nrm, "polygons": npoly, "det": m3.determinant()}


def bbox(verts):
    return ([min(v[i] for v in verts) for i in range(3)], [max(v[i] for v in verts) for i in range(3)])


def views(a):
    """What a viewer above and a viewer below see, read by hc_chirality; plus winding vs stored normals."""
    vmm = [tuple(c * 1000.0 for c in v) for v in a["verts"]]
    fn = [HC.winding_normal(vmm[i], vmm[j], vmm[k], "blender") for i, j, k in a["tris"]]
    agree, disagree = 0, 0
    for tl, n in zip(a["tri_loops"], fn):
        m = [sum(a["loop_normals"][li][c] for li in tl) for c in range(3)]
        if HC.dot(n, m) > 0:
            agree += 1
        else:
            disagree += 1
    rec = {"winding_vs_stored_normals": {"convention": "blender (P1-P0)x(P2-P0)", "agree": agree,
                                         "disagree": disagree}}
    for name, cam in (("viewer_above_plus_z", TOP), ("viewer_below_minus_z", BOTTOM)):
        t2, areas = HC.screen_view(vmm, a["tris"], fn, cam["forward"], cam["right"], cam["up"])
        r = HC.analyse(t2)
        r["front_facing_triangles_ccw_on_screen"] = sum(1 for s in areas if s > 0)
        r["front_facing_triangles_cw_on_screen"] = sum(1 for s in areas if s <= 0)
        rec[name] = r
    return rec


def mirrored(a):
    """Negative control: the same mesh mirrored y -> -y (winding reversed so it stays a consistent closed mesh)."""
    b = dict(a)
    b["verts"] = [(x, -y, z) for x, y, z in a["verts"]]
    b["tris"] = [(i, k, j) for i, j, k in a["tris"]]
    b["tri_loops"] = [(i, k, j) for i, j, k in a["tri_loops"]]
    b["loop_normals"] = [(x, -y, z) for x, y, z in a["loop_normals"]]
    return b


def com_volume(verts, tris):
    vol, c = 0.0, [0.0, 0.0, 0.0]
    for i, j, k in tris:
        a, b, cc = verts[i], verts[j], verts[k]
        d = HC.dot(a, HC.cross(b, cc)) / 6.0
        vol += d
        for m in range(3):
            c[m] += d * (a[m] + b[m] + cc[m]) / 4.0
    return vol, [x / vol for x in c]


def planes_of(verts, tris):
    cen = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    out = []
    for i, j, k in tris:
        n = HC.cross(HC.sub(verts[j], verts[i]), HC.sub(verts[k], verts[i]))
        ln = math.sqrt(HC.dot(n, n))
        if ln < 1e-18:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        if HC.dot(n, HC.sub(cen, verts[i])) > 0:
            n = (-n[0], -n[1], -n[2])
        out.append((n, verts[i]))
    return out


def max_outside(planes, pts):
    return max(max(HC.dot(n, HC.sub(p, a)) for n, a in planes) for p in pts)


def read_scene(mesh_name, full=True):
    import mathutils
    rec = {"objects": sorted((o.name, o.type) for o in bpy.data.objects if mesh_name in o.name), "lods": {},
           "hulls": {}, "sockets": {}, "lod_group": None}
    lod = {}
    for i in range(6):
        ob = bpy.data.objects.get(f"{mesh_name}_LOD{i}")
        if ob is None:
            break
        a = mesh_arrays(ob)
        lod[i] = a
        lo, hi = bbox(a["verts"])
        ue = [ue_cm(v) for v in a["verts"]]
        ulo, uhi = bbox(ue)
        c = [(ulo[m] + uhi[m]) / 2.0 for m in range(3)]
        r = {"triangles": len(a["tris"]), "vertices": len(a["verts"]), "polygons": a["polygons"],
             "uv_layers": a["uv_names"], "matrix_world_det": round(a["det"], 12),
             "any_negative_scale": any(s < 0 for s in ob.matrix_world.to_scale()),
             "modifiers": [(m.type, m.name) for m in ob.modifiers],
             "parent": ob.parent.name if ob.parent else None,
             "parent_fbx_type": ob.parent.get("fbx_type") if ob.parent else None,
             "material_slots": [s.material.name if s.material else None for s in ob.material_slots],
             "bbox_min_mm": [x * 1000.0 for x in lo], "bbox_max_mm": [x * 1000.0 for x in hi],
             "ue_bounds_min_cm": ulo, "ue_bounds_max_cm": uhi,
             "ue_size_cm": [uhi[m] - ulo[m] for m in range(3)],
             "ue_bounds_sphere_radius_cm": max(math.dist(p, c) for p in ue)}
        if full:
            r["views"] = views(a)
        rec["lods"][f"LOD{i}"] = r
        if ob.parent and ob.parent.type == "EMPTY":
            rec["lod_group"] = {"name": ob.parent.name, "fbx_type": ob.parent.get("fbx_type"),
                                "det": round(ob.parent.matrix_world.to_3x3().determinant(), 12)}
    if full and 0 in lod:
        v0, t0 = lod[0]["verts"], lod[0]["tris"]
        vol, com = com_volume(v0, t0)
        rec["lod0_volume_mm3"] = vol * 1e9
        rec["lod0_com_mm"] = [x * 1000.0 for x in com]
        rec["lod0_mirrored_negative_control"] = views(mirrored(lod[0]))
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith("UCX_") and mesh_name in ob.name:
            a = mesh_arrays(ob)
            pl = planes_of(a["verts"], a["tris"])
            uniq = {tuple(round(c, 9) for c in v) for v in a["verts"]}
            h = {"triangles": len(a["tris"]), "vertices": len(a["verts"]), "unique_vertices": len(uniq),
                 "parent": ob.parent.name if ob.parent else None,
                 "keys_to_render_node": ob.name == f"UCX_{mesh_name}_LOD0_00",
                 "convex_self_max_outside_mm": max_outside(pl, a["verts"]) * 1000.0,
                 "volume_mm3": com_volume(a["verts"], a["tris"])[0] * 1e9}
            for i, la in lod.items():
                h[f"LOD{i}_max_outside_mm"] = max_outside(pl, la["verts"]) * 1000.0
            rec["hulls"][ob.name] = h
        if ob.name.startswith("SOCKET_") and mesh_name in ob.name:
            lod0 = bpy.data.objects.get(f"{mesh_name}_LOD0")
            m = (lod0.matrix_world.inverted() @ ob.matrix_world) if lod0 else ob.matrix_world
            loc, rot, scl = m.decompose()
            eul = rot.to_euler()
            fx = (m.to_3x3().normalized() @ mathutils.Vector((1.0, 0.0, 0.0)))
            rec["sockets"][ob.name] = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                                       "location_mm": [x * 1000.0 for x in loc],
                                       "polar_deg": math.degrees(math.atan2(loc[1], loc[0])),
                                       "euler_deg": [math.degrees(e) for e in eul],
                                       "scale": list(scl), "local_plus_x": list(fx),
                                       "predicted_ue_location_cm": ue_cm(loc)}
    return rec, lod


def dump(a):
    """Arrays for summarize.py / b3: positions (m), triangles, corner (vertex, uv0, normal)."""
    return {"verts_m": [[round(c, 10) for c in v] for v in a["verts"]], "tris": a["tris"],
            "tri_loops": a["tri_loops"], "loop_vert": a["loop_vert"],
            "uv0": [[round(c, 8) for c in uv] for uv in a["uv0"]],
            "loop_normals": [[round(c, 7) for c in n] for n in a["loop_normals"]]}


def main():
    out = {"blend": bpy.data.filepath, "blend_sha256": sha256(bpy.data.filepath), "blender": bpy.app.version_string,
           "fbx": str(FBX), "fbx_sha256": sha256(FBX), "sidecar_sha256": sha256(SIDECAR),
           "control_fbx": str(CTRL_FBX), "control_fbx_sha256": sha256(CTRL_FBX), "spec": spec()}
    out["blend_scene"], _ = read_scene(MESH)
    out["blend_control"], _ = read_scene(CTRL, full=False)
    # every modifier / negative scale / mirror anywhere near the form in the .blend
    out["blend_mirror_audit"] = {
        "mirror_modifiers": [(o.name, m.name) for o in bpy.data.objects for m in o.modifiers if m.type == "MIRROR"
                             and MESH in o.name],
        "negative_scale_objects": [o.name for o in bpy.data.objects if MESH in o.name
                                   and o.matrix_world.to_3x3().determinant() < 0]}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    out["fbx_scene"], lods = read_scene(MESH)
    out["fbx_scene"]["all_nodes"] = sorted((o.name, o.type, o.parent.name if o.parent else None,
                                            round(o.matrix_world.to_3x3().determinant(), 12)) for o in bpy.data.objects)
    out["fbx_arrays"] = {f"LOD{i}": dump(a) for i, a in lods.items()}
    ucx = [o for o in bpy.data.objects if o.name.startswith("UCX_")]
    out["fbx_hull_arrays"] = {o.name: dump(mesh_arrays(o)) for o in ucx}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(CTRL_FBX))
    ctrl, clods = read_scene(CTRL, full=False)
    out["control_fbx_scene"] = ctrl
    out["control_fbx_arrays"] = {"LOD0": dump(clods[0])}
    out["fbx_sha256_after"] = sha256(FBX)
    out["control_fbx_sha256_after"] = sha256(CTRL_FBX)
    (HERE / "b1_truth.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("UC11_B1_DONE")


main()
