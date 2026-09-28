"""UnrealCheck11 process 6 (fresh): HANDEDNESS IN UNREAL, read from the saved assets' RENDER DATA.

Loads the saved SM_Shuriken_HookedCross (and the six-point control) in a fresh commandlet and reads every LOD's render
buffers (position / tangent-Z normal / UV0 vertex buffers + index buffer) through
ProceduralMeshLibrary.get_section_from_static_mesh (KismetProceduralMeshLibrary.cpp reads
RenderData->LODResources[LOD]).  That call logs a 'PIE: Warning' when the mesh's Allow CPU Access is off, so the flag
is set IN MEMORY ONLY with notify_mode NEVER (no PostEditChange, no rebuild, nothing saved; the saved value is
recorded first).  Then, with the engine's own conventions:
  winding  UE's face normal from corner order is CrossProduct(P2-P0, P1-P0) (StaticMeshOperations.cpp: "We have a
           left-handed coordinate system, but a counter-clockwise winding order"); every render triangle's winding
           normal is compared with its three stored tangent-Z normals
  screen   a camera's screen right / up are its rotator's right / up vectors (unreal.MathLibrary); a viewer above the
           plate is Rotator(pitch=-90) and one below is Rotator(pitch=+90).  The triangles front-facing to that camera
           are projected to its screen and read by hc_chirality (the same code Blender's truth used)
  controls a mirrored copy of the render data (y -> -y, winding reversed) must read as the mirror image, and the
           viewer below must read as the mirror image (the accepted back-face physics)
Raw arrays are written for summarize.py's comparison with the Blender truth (b1_truth.json).
Writes u6_renderdata.json.
"""
import math
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc11_common as C  # noqa: E402
import hc_chirality as HC  # noqa: E402

CAMS = {"viewer_above_plus_z": unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0),
        "viewer_above_plus_z_yaw37": unreal.Rotator(roll=0.0, pitch=-90.0, yaw=37.0),
        "viewer_below_minus_z": unreal.Rotator(roll=0.0, pitch=90.0, yaw=0.0)}


def basis(rot):
    f = unreal.MathLibrary.get_forward_vector(rot)
    r = unreal.MathLibrary.get_right_vector(rot)
    u = unreal.MathLibrary.get_up_vector(rot)
    clean = lambda v: tuple(0.0 if abs(c) < 1e-12 else c for c in (v.x, v.y, v.z))  # noqa: E731
    return {"forward": clean(f), "right": clean(r), "up": clean(u)}


def dirty_packages():
    try:
        return sorted(str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    except Exception as exc:  # noqa: BLE001
        return f"n/a: {exc}"[:120]


def read_lod(mesh, lod):
    verts, tris, normals, uvs, tangents = [], [], [], [], []
    for s in range(int(mesh.get_num_sections(lod))):
        v, t, n, uv, tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, s)
        base = len(verts)
        verts += [(p.x, p.y, p.z) for p in v]
        normals += [(p.x, p.y, p.z) for p in n]
        uvs += [(p.x, p.y) for p in uv]
        tangents += [(p.tangent_x.x, p.tangent_x.y, p.tangent_x.z) for p in tg]
        tris += [(base + t[i], base + t[i + 1], base + t[i + 2]) for i in range(0, len(t), 3)]
    return {"verts_cm": verts, "tris": tris, "normals": normals, "uv0": uvs, "tangent_x": tangents}


def closest_on_tri(p, a, b, c):
    """Ericson, Real-Time Collision Detection 5.1.5."""
    ab, ac, ap = HC.sub(b, a), HC.sub(c, a), HC.sub(p, a)
    d1, d2 = HC.dot(ab, ap), HC.dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = HC.sub(p, b)
    d3, d4 = HC.dot(ab, bp), HC.dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return (a[0] + v * ab[0], a[1] + v * ab[1], a[2] + v * ab[2])
    cp = HC.sub(p, c)
    d5, d6 = HC.dot(ab, cp), HC.dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return (a[0] + w * ac[0], a[1] + w * ac[1], a[2] + w * ac[2])
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (b[0] + w * (c[0] - b[0]), b[1] + w * (c[1] - b[1]), b[2] + w * (c[2] - b[2]))
    den = 1.0 / (va + vb + vc)
    v, w = vb * den, vc * den
    return (a[0] + ab[0] * v + ac[0] * w, a[1] + ab[1] * v + ac[1] * w, a[2] + ab[2] * v + ac[2] * w)


def analyse_lod(d, cams):
    vmm = [tuple(c * 10.0 for c in v) for v in d["verts_cm"]]
    fn = [HC.winding_normal(vmm[i], vmm[j], vmm[k], "unreal") for i, j, k in d["tris"]]
    agree_ue = agree_alg = 0
    worst = 1.0
    for (i, j, k), n in zip(d["tris"], fn):
        m = tuple(d["normals"][i][c] + d["normals"][j][c] + d["normals"][k][c] for c in range(3))
        cu = HC.dot(HC.norm(n), HC.norm(m))
        worst = min(worst, cu)
        agree_ue += cu > 0
        alg = HC.winding_normal(vmm[i], vmm[j], vmm[k], "blender")
        agree_alg += HC.dot(alg, m) > 0
    top = [n for n in fn if HC.norm(n)[2] > 0.999]
    bot = [n for n in fn if HC.norm(n)[2] < -0.999]
    rec = {"triangles": len(d["tris"]), "render_vertices": len(d["verts_cm"]),
           "winding_vs_stored_normals": {
               "unreal_convention_CrossProduct(P2-P0,P1-P0)_agree": agree_ue,
               "right_hand_(P1-P0)x(P2-P0)_agree": agree_alg,
               "min_cos_winding_to_mean_stored_normal": round(worst, 6)},
           "flat_faces": {"winding_normal_plus_z": len(top), "winding_normal_minus_z": len(bot)},
           "bounds_cm": [[min(v[m] for v in d["verts_cm"]) for m in range(3)],
                         [max(v[m] for v in d["verts_cm"]) for m in range(3)]]}
    for name, cam in cams.items():
        t2, areas = HC.screen_view(vmm, d["tris"], fn, cam["forward"], cam["right"], cam["up"])
        r = HC.analyse(t2)
        r["front_facing_triangles_ccw_on_screen"] = sum(1 for s in areas if s > 0)
        r["front_facing_triangles_cw_on_screen"] = sum(1 for s in areas if s <= 0)
        rec[name] = r
    return rec


def engine_projection_views(d):
    """The strongest form of 'how Unreal displays it': push the render vertices through the engine's OWN view and
    projection matrices (GameplayStatics.get_view_projection_matrix for a MinimalViewInfo; LocalPlayer.cpp builds the
    same view rotation matrix, camera right -> view X, camera up -> view Y) to normalised device coordinates (x right,
    y up), keep the triangles whose winding normal faces the camera position, and read them with hc_chirality.
    Perspective camera 100 cm from the plate centre, 90 deg FOV, square aspect; NDC is scaled x1000 so the plate reads
    in ~mm at the plate plane."""
    out = {}
    vmm = [tuple(c * 10.0 for c in v) for v in d["verts_cm"]]
    fn = [HC.winding_normal(vmm[i], vmm[j], vmm[k], "unreal") for i, j, k in d["tris"]]
    for name, (loc, rot) in {"camera_100cm_above_looking_down": ((0.0, 0.0, 100.0), unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)),
                             "camera_100cm_below_looking_up": ((0.0, 0.0, -100.0), unreal.Rotator(roll=0.0, pitch=90.0, yaw=0.0))}.items():
        try:
            vi = unreal.MinimalViewInfo()
            vi.set_editor_property("location", unreal.Vector(*loc))
            vi.set_editor_property("rotation", rot)
            vi.set_editor_property("fov", 90.0)
            vi.set_editor_property("aspect_ratio", 1.0)
            vi.set_editor_property("projection_mode", unreal.CameraProjectionMode.PERSPECTIVE)
            _view, _proj, vp = unreal.GameplayStatics.get_view_projection_matrix(vi)
            ndc = []
            for p in d["verts_cm"]:
                c = vp.transform_position(unreal.Vector(*p))
                ndc.append((c.x / c.w * 1000.0, c.y / c.w * 1000.0))
            tris2d, areas = [], []
            for (i, j, k), n in zip(d["tris"], fn):
                cen = tuple((d["verts_cm"][i][m] + d["verts_cm"][j][m] + d["verts_cm"][k][m]) / 3.0 for m in range(3))
                if HC.dot(n, HC.sub(cen, loc)) >= 0.0:        # faces away from the camera position
                    continue
                t = (ndc[i], ndc[j], ndc[k])
                tris2d.append(t)
                areas.append(HC.signed_area2(*t))
            r = HC.analyse(tris2d)
            r["front_facing_triangles_ccw_in_ndc"] = sum(1 for s in areas if s > 0)
            r["front_facing_triangles_cw_in_ndc"] = sum(1 for s in areas if s <= 0)
            r["camera_location_cm"] = list(loc)
            out[name] = r
        except Exception:  # noqa: BLE001
            out[name] = {"error": traceback.format_exc()[-600:]}
    return out


def mirrored(d):
    return {"verts_cm": [(x, -y, z) for x, y, z in d["verts_cm"]], "tris": [(i, k, j) for i, j, k in d["tris"]],
            "normals": [(x, -y, z) for x, y, z in d["normals"]], "uv0": d["uv0"], "tangent_x": d["tangent_x"]}


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST,
           "fbx_sha256_now": {m: C.sha256(p) for m, p in C.FBX.items()}}
    cams = {k: basis(r) for k, r in CAMS.items()}
    rep["camera_bases_from_unreal_MathLibrary"] = cams
    rep["dirty_packages_before"] = dirty_packages()
    rep["meshes"] = {}
    raw = {}
    for m, path in C.ASSET.items():
        rec = {}
        try:
            mesh = unreal.load_asset(path)
            rec["allow_cpu_access_saved"] = bool(mesh.get_editor_property("allow_cpu_access"))
            mesh.set_editor_property("allow_cpu_access", True,
                                     notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            rec["allow_cpu_access_in_memory_for_this_read"] = bool(mesh.get_editor_property("allow_cpu_access"))
            rec["num_lods"] = int(mesh.get_num_lods())
            rec["sections"] = [int(mesh.get_num_sections(i)) for i in range(rec["num_lods"])]
            lods = {f"LOD{i}": read_lod(mesh, i) for i in range(rec["num_lods"])}
            raw[m] = lods
            if m == C.MESH:
                rec["lods"] = {k: analyse_lod(d, cams) for k, d in lods.items()}
                rec["lod0_mirrored_negative_control"] = analyse_lod(mirrored(lods["LOD0"]), cams)
                rec["engine_view_projection"] = {k: engine_projection_views(d) for k, d in lods.items()}
                rec["engine_view_projection_mirrored_negative_control"] = engine_projection_views(mirrored(lods["LOD0"]))
                sockets = {}
                d0 = lods["LOD0"]
                for sname in ("Grip", "Trail"):
                    s = mesh.find_socket(sname)
                    if s is None:
                        continue
                    loc = s.get_editor_property("relative_location")
                    rot = s.get_editor_property("relative_rotation")
                    p = (loc.x, loc.y, loc.z)
                    best = min(math.dist(p, closest_on_tri(p, d0["verts_cm"][i], d0["verts_cm"][j], d0["verts_cm"][k]))
                               for i, j, k in d0["tris"])
                    fwd = unreal.MathLibrary.get_forward_vector(rot)
                    up = unreal.MathLibrary.get_up_vector(rot)
                    radial = HC.norm((p[0], p[1], 0.0))
                    top = cams["viewer_above_plus_z"]
                    sockets[sname] = {"location_cm": list(p), "distance_to_lod0_render_surface_cm": best,
                                      "forward": [fwd.x, fwd.y, fwd.z], "up": [up.x, up.y, up.z],
                                      "forward_dot_outward_radial": HC.dot((fwd.x, fwd.y, fwd.z), radial)
                                      if any(radial) else None,
                                      "screen_xy_viewer_above_cm": [HC.dot(p, top["right"]), HC.dot(p, top["up"])]}
                rec["sockets_vs_render_data"] = sockets
            else:
                rec["lods"] = {"LOD0": analyse_lod(lods["LOD0"], {})}
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()
        rep["meshes"][m] = rec
    rep["dirty_packages_after"] = dirty_packages()
    rep["raw"] = {m: {k: {"verts_cm": [[round(c, 7) for c in v] for v in d["verts_cm"]], "tris": d["tris"],
                          "normals": [[round(c, 6) for c in v] for v in d["normals"]],
                          "uv0": [[round(c, 7) for c in v] for v in d["uv0"]]}
                      for k, d in lods.items()} for m, lods in raw.items()}
    C.write(C.HERE / "u6_renderdata.json", rep)
    unreal.log("UC11_U6_DONE")


main()
