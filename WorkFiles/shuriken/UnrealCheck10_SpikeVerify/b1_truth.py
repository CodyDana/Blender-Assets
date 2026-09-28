"""UnrealCheck10 (independent Unreal verifier for SM_Shuriken_Spike) - Blender-side truth. READ ONLY, never saves.

    blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python b1_truth.py

Written fresh for this verification (not a copy of UnrealCheck6/8). Expectations come from three independent places:
  SPEC   the brief / study 2.5 numbers (150 mm, 6 mm square, 25 mm point, tail 20 mm -> 3 mm, 0.15 mm tip flat,
         0.3 mm arris round), the bar generator's closed-form triangle count 16 K + 28 (K = 4 / 2 / 0 chords),
         and the pack's 1.0 / 0.10 / 0.035 screen sizes scaled by the bounds-sphere radius / 50 mm
  BLEND  the spike objects in Assets/Shuriken.blend (evaluated meshes, UCX, SOCKET_ Empties, LodGroup)
  FBX    a factory-startup re-import of the exact shipped bytes (SHA-256 recorded)
Also computes, from the LOD0 triangles themselves, the centre of mass by volume (divergence theorem) so the
Unreal bounds can be checked against the pivot rule, and the Unreal-style bounds-sphere radius (largest vertex
distance from the bounding-box centre).
Writes b1_truth.json next to this file.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck10_SpikeVerify"
MESH = "SM_Shuriken_Spike"
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spec():
    L, s, lp, lt, e, tip, arris = 150.0, 6.0, 25.0, 20.0, 3.0, 0.15, 0.30
    r_ue = math.sqrt((L / 2.0) ** 2 + 2.0 * (e / 2.0) ** 2)      # butt corners from the bbox centre, mm
    sizes = [1.0, round(0.10 * r_ue / 50.0, 4), round(0.035 * r_ue / 50.0, 4)]
    # un-ground outline volume (the brief's hand check, exact)
    v = L * s * s - (lp * s * s - s * s * lp / 3.0) - (lt * s * s - lt / 3.0 * (s * s + e * e + s * e))
    return {"length_mm": L, "section_mm": s, "point_mm": lp, "tail_taper_mm": lt, "tail_end_mm": e,
            "tip_flat_mm": tip, "arris_mm": arris,
            "lod_triangles_formula": [16 * k + 28 for k in (4, 2, 0)],
            "bounds_sphere_radius_mm_expected": r_ue, "screen_sizes_expected": sizes,
            "switch_distance_m_16x9_90deg": [None] + [round(1.7778 * r_ue / 1000.0 / x, 4) for x in sizes[1:]],
            "outline_volume_mm3": v, "outline_mass_g": v * 7.85 / 1000.0,
            "size_cm_expected": [L / 10.0, s / 10.0, s / 10.0],
            "grip_from_butt_mm_design": 40.0}


def ue_cm(v):
    """Blender metres -> Unreal cm (legacy FBX importer, Forward -Y / Up Z: X kept, Y flipped, Z kept)."""
    return [v[0] * 100.0, -v[1] * 100.0, v[2] * 100.0]


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world
    verts = [tuple(mw @ v.co) for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    uvs = [uv.name for uv in me.uv_layers]
    npoly = len(me.polygons)
    ev.to_mesh_clear()
    return verts, tris, uvs, npoly


def com_volume(verts, tris):
    vol, cx, cy, cz = 0.0, 0.0, 0.0, 0.0
    for i, j, k in tris:
        a, b, c = verts[i], verts[j], verts[k]
        d = (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
             + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        vol += d
        cx += d * (a[0] + b[0] + c[0]) / 4.0
        cy += d * (a[1] + b[1] + c[1]) / 4.0
        cz += d * (a[2] + b[2] + c[2]) / 4.0
    return vol, (cx / vol, cy / vol, cz / vol)


def bbox(verts):
    return ([min(v[i] for v in verts) for i in range(3)], [max(v[i] for v in verts) for i in range(3)])


def planes_of(verts, tris):
    cen = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    out = []
    for i, j, k in tris:
        a, b, c = verts[i], verts[j], verts[k]
        u = [b[m] - a[m] for m in range(3)]
        w = [c[m] - a[m] for m in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        ln = math.sqrt(sum(x * x for x in n))
        if ln < 1e-18:
            continue
        n = [x / ln for x in n]
        if sum(n[m] * (cen[m] - a[m]) for m in range(3)) > 0:
            n = [-x for x in n]
        out.append((n, a))
    return out


def max_outside(planes, pts):
    return max(max(sum(n[m] * (p[m] - a[m]) for m in range(3)) for n, a in planes) for p in pts)


def read_scene():
    rec = {"objects": sorted(o.name for o in bpy.data.objects if MESH in o.name), "lods": {}, "hulls": {},
           "sockets": {}, "lod_group": None}
    lod_verts = {}
    for i in range(6):
        ob = bpy.data.objects.get(f"{MESH}_LOD{i}")
        if ob is None:
            break
        verts, tris, uvs, npoly = evaluated(ob)
        lod_verts[i] = (verts, tris)
        lo, hi = bbox(verts)
        ue = [ue_cm(v) for v in verts]
        ulo, uhi = bbox(ue)
        c = [(ulo[m] + uhi[m]) / 2.0 for m in range(3)]
        rec["lods"][f"LOD{i}"] = {
            "triangles": len(tris), "vertices": len(verts), "polygons": npoly, "uv_layers": uvs,
            "matrix_world_identity": all(abs(ob.matrix_world[r][cc] - (1.0 if r == cc else 0.0)) < 1e-12
                                         for r in range(4) for cc in range(4)),
            "parent": ob.parent.name if ob.parent else None,
            "parent_fbx_type": ob.parent.get("fbx_type") if ob.parent else None,
            "material_slots": [s.material.name if s.material else None for s in ob.material_slots],
            "ue_bounds_min_cm": [round(x, 7) for x in ulo], "ue_bounds_max_cm": [round(x, 7) for x in uhi],
            "ue_size_cm": [round(uhi[m] - ulo[m], 7) for m in range(3)],
            "ue_bounds_sphere_radius_cm": max(math.dist(p, c) for p in ue),
        }
        if ob.parent and ob.parent.type == "EMPTY":
            rec["lod_group"] = {"name": ob.parent.name, "fbx_type": ob.parent.get("fbx_type")}
    if 0 in lod_verts:
        v0, t0 = lod_verts[0]
        vol, com = com_volume(v0, t0)
        lo, hi = bbox(v0)
        rec["lod0_volume_mm3"] = vol * 1e9
        rec["lod0_com_mm"] = [x * 1000.0 for x in com]
        rec["lod0_x_range_mm"] = [lo[0] * 1000.0, hi[0] * 1000.0]
        rec["lod0_com_from_butt_mm"] = -lo[0] * 1000.0
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.startswith("UCX_"):
            verts, tris, _, npoly = evaluated(ob)
            pl = planes_of(verts, tris)
            uniq = {tuple(round(c, 9) for c in v) for v in verts}
            h = {"triangles": len(tris), "vertices": len(verts), "unique_vertices": len(uniq),
                 "parent": ob.parent.name if ob.parent else None,
                 "keys_to_render_node": ob.name == f"UCX_{MESH}_LOD0_00",
                 "convex_self_max_outside_mm": max_outside(pl, verts) * 1000.0,
                 "ue_size_cm": [round(x, 7) for x in (lambda b: [b[1][m] - b[0][m] for m in range(3)])(bbox([ue_cm(v) for v in verts]))],
                 "volume_mm3": com_volume(verts, tris)[0] * 1e9}
            for i, (lv, _) in lod_verts.items():
                h[f"LOD{i}_max_outside_mm"] = max_outside(pl, lv) * 1000.0
            rec["hulls"][ob.name] = h
        if ob.name.startswith("SOCKET_"):
            lod0 = bpy.data.objects.get(f"{MESH}_LOD0")
            m = (lod0.matrix_world.inverted() @ ob.matrix_world) if lod0 else ob.matrix_world
            loc, rot, scl = m.decompose()
            eul = rot.to_euler()
            fx = m.to_3x3() @ __import__("mathutils").Vector((1.0, 0.0, 0.0))
            rec["sockets"][ob.name] = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                                       "ue_location_cm": [round(x, 6) for x in ue_cm(loc)],
                                       "euler_deg": [round(math.degrees(a), 6) for a in eul],
                                       "scale": [round(x, 9) for x in scl],
                                       "local_plus_x_in_mesh_space": [round(x, 9) for x in fx]}
    return rec


def main():
    out = {"blend": bpy.data.filepath, "blend_sha256": sha256(bpy.data.filepath), "blender": bpy.app.version_string,
           "fbx": str(FBX), "fbx_sha256": sha256(FBX), "sidecar_sha256": sha256(SIDECAR), "spec": spec()}
    out["blend_scene"] = read_scene()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    out["fbx_scene"] = read_scene()
    out["fbx_scene"]["all_nodes"] = sorted((o.name, o.type) for o in bpy.data.objects)
    out["fbx_sha256_after"] = sha256(FBX)
    (HERE / "b1_truth.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("UC10_B1_DONE")


main()
