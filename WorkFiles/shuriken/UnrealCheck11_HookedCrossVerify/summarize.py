"""UnrealCheck11 summary: every gate for SM_Shuriken_HookedCross in Unreal 5.8, including HANDEDNESS.  Plain Python
(no numpy), reads only the JSON / logs written by b1_truth.py (Blender truth), u1..u6 (Unreal, one fresh process
each) and b2_roundtrip.py (Blender, Unreal's re-export).  Writes verification_summary.json.

    py summarize.py

Gates
  G0 exact bytes + fresh content path        G1 LODs + per-LOD triangles equal Blender (4 sources)
  G2 exactly one convex hull, stored hull == shipped UCX (round trip), LOD0 0.0 cm outside
  G3 Grip / Trail relative scale 1 at sane cm locations (Grip on the LOD0 render surface, +X outward)
  G4 bounds in cm match (Blender LOD0 truth and the analytic outline)
  G5 LOD screen sizes applied (1.0 / 0.10 / 0.035 scaled by bounds radius / 5 cm)
  G6 lightmap index 1, UV1 in 0-1, no overlap (with a negative control)
  G7 BC sRGB / ORM linear masks / N normal map (fresh-process read-back)
  G8 zero Warning / Error lines in every Unreal process
Handedness
  H1 mapping CONTROL A: the six-point Grip socket (known asymmetric position) Blender -> Unreal
  H2 mapping CONTROL B: the six-point LOD0 RENDER DATA fitted to its Blender corners by UV0 labels alone (no position
     assumption): the linear map Unreal cm = A * Blender m + t
  H3 the hooked cross's render data (all LODs) equals the Blender truth under A; the mirrored alternative does not;
     render normals equal A-mapped Blender normals; UV-label fit on the hooked cross itself gives the same A
  H4 triangle winding vs stored normals (render data): 100 % agree with UE's own rule CrossProduct(P2-P0, P1-P0),
     0 % with the right-hand rule, exactly like the control (the importer keeps corner order and negates Y)
  H5 display: with Unreal's own camera basis (a viewer above = Rotator pitch -90) every front-facing triangle is
     counter-clockwise on screen and the +Z face reads left-facing (U+534D) on every LOD; Unreal's top-view image
     equals Blender's top view turned +90 deg (a proper rotation); the viewer below reads the mirror image (physics);
     the mirrored render data reads the mirror image (negative control caught)
  H6 no import step mirrored: import settings, build scale, FBX node determinants, the round trip back to Blender
     reads left-facing, the hull is chirally matched
"""
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify")
MESH, CTRL = "SM_Shuriken_HookedCross", "SM_Shuriken_SixPoint"


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


B1, U1, U3, U6, B2 = (load(n) for n in ("b1_truth.json", "u1_import.json", "u3_readback.json", "u6_renderdata.json",
                                          "b2_roundtrip.json"))
U2, U4 = load("u2_textures_import.json"), load("u4_textures_verify.json")
U5 = load("u5_export.json")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ small linear algebra
def solve(M, b):
    n = len(b)
    A = [row[:] + [b[i]] for i, row in enumerate(M)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        for r in range(n):
            if r != c:
                f = A[r][c] / A[c][c]
                for k in range(c, n + 1):
                    A[r][k] -= f * A[c][k]
    return [A[i][n] / A[i][i] for i in range(n)]


def fit_affine(pairs):
    """Least squares q = A p + t over (p, q) pairs; returns A (3x3), t, max residual."""
    X = [[p[0], p[1], p[2], 1.0] for p, _ in pairs]
    XtX = [[sum(r[i] * r[j] for r in X) for j in range(4)] for i in range(4)]
    rows = []
    for k in range(3):
        Xty = [sum(X[n][i] * pairs[n][1][k] for n in range(len(pairs))) for i in range(4)]
        rows.append(solve(XtX, Xty))
    A = [r[:3] for r in rows]
    t = [r[3] for r in rows]
    res = max(math.sqrt(sum((sum(A[k][m] * p[m] for m in range(3)) + t[k] - q[k]) ** 2 for k in range(3)))
              for p, q in pairs)
    return A, t, res


def det3(A):
    return (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
            + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))


def uv_label_pairs(truth, render, flip_v):
    """Pair Unreal render vertices with Blender vertices by UV0 ALONE (no position used): a render vertex is paired
    only when every Blender corner within the float16 half-ulp of its UV sits at one Blender position."""
    tol = 2.0 ** -12 + 2e-6
    g = 0.002
    buckets = {}
    for li, uv in enumerate(truth["uv0"]):
        v = 1.0 - uv[1] if flip_v else uv[1]
        buckets.setdefault((int(math.floor(uv[0] / g)), int(math.floor(v / g))), []).append((uv[0], v, li))
    pairs, ambiguous, unmatched = [], 0, 0
    for p, uv in zip(render["verts_cm"], render["uv0"]):
        bx, by = int(math.floor(uv[0] / g)), int(math.floor(uv[1] / g))
        cands = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for u, v, li in buckets.get((bx + dx, by + dy), ()):
                    if abs(u - uv[0]) <= tol and abs(v - uv[1]) <= tol:
                        cands.add(tuple(round(c, 9) for c in truth["verts_m"][truth["loop_vert"][li]]))
        if not cands:
            unmatched += 1
        elif len(cands) > 1:
            ambiguous += 1
        else:
            pairs.append((next(iter(cands)), tuple(p)))
    return pairs, ambiguous, unmatched


def mapping_fit(truth, render):
    out = {}
    for flip in (True, False):
        pairs, amb, un = uv_label_pairs(truth, render, flip)
        rec = {"render_vertices": len(render["verts_cm"]), "uniquely_labelled_pairs": len(pairs),
               "ambiguous": amb, "no_label_match": un}
        if len(pairs) >= 8:
            A, t, res = fit_affine(pairs)
            rec.update({"A_cm_per_m": [[round(x, 5) for x in r] for r in A], "t_cm": [round(x, 7) for x in t],
                        "max_residual_cm": res, "det_A": det3(A)})
        out["uv_v_flipped (v_ue = 1 - v_blender)" if flip else "uv_v_as_is"] = rec
    return out


def nn_two_sided(a, b, cell=0.1):
    """Two-sided nearest-neighbour (Hausdorff) distance between point sets, bucketed on the first two coordinates
    (the plate is thin in the third).  Exact: a ring is widened until no unvisited bucket can hold a closer point."""
    def one(src, dst):
        grid = {}
        for q in dst:
            grid.setdefault((int(math.floor(q[0] / cell)), int(math.floor(q[1] / cell))), []).append(q)
        worst = 0.0
        for p in src:
            kx, ky = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
            best, ring = float("inf"), 0
            while True:
                for dx in range(-ring, ring + 1):
                    for dy in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy)) != ring:
                            continue
                        for q in grid.get((kx + dx, ky + dy), ()):
                            dd = math.dist(p, q)
                            if dd < best:
                                best = dd
                if best <= ring * cell or ring > 100000:
                    break
                ring += 1
            worst = max(worst, best)
        return worst
    return max(one(a, b), one(b, a))


def apply(A, p):
    return tuple(sum(A[k][m] * p[m] for m in range(3)) for k in range(3))


# ------------------------------------------------------------------ logs
def log_check(step):
    log = HERE / f"{step}.log"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    strict = [ln for ln in lines if re.search(r":\s*(Warning|Error)\s*:", ln)]
    summary = [ln for ln in lines if "Success - " in ln and "error(s)" in ln]
    err = HERE / f"{step}.log.stderr"
    return {"lines": len(lines), "strict_warning_error_lines": len(strict), "first": strict[:3],
            "summary_line": summary[-1].split("LogInit: Display: ")[-1] if summary else None,
            "stderr_bytes": err.stat().st_size if err.exists() else None}


def main():
    g, d = {}, {}
    m3 = U3["mesh"][MESH]
    fbx_sha = B1["fbx_sha256"]
    imp = U1["imports"][MESH]
    reg = m3["registry_import_tag"].get("parsed", [{}])[0]
    # ---------------------------------------------------------------- G0
    d["G0"] = {"fbx_sha256": fbx_sha, "u1_before": imp["fbx_sha256_before"], "u1_after": imp["fbx_sha256_after"],
               "u3_now": U3["fbx_sha256_now"][MESH], "u6_now": U6["fbx_sha256_now"][MESH],
               "b1_after": B1["fbx_sha256_after"], "unreal_recorded_md5": reg.get("FileMD5"),
               "fbx_md5": U3["fbx_md5_now"][MESH], "sidecar_sha256": imp["sidecar_sha256_before"],
               "sidecar_sha256_blend_truth": B1["sidecar_sha256"],
               "fresh_dest": U1["dest"], "dest_existed_before": U1["dest_existed_before"],
               "dest_assets_before": U1["dest_assets_before"], "import_source": m3["import_filenames"]}
    g["G0_exact_bytes"] = (len({fbx_sha, imp["fbx_sha256_before"], imp["fbx_sha256_after"], U3["fbx_sha256_now"][MESH],
                                U6["fbx_sha256_now"][MESH], B1["fbx_sha256_after"]}) == 1
                           and reg.get("FileMD5") == U3["fbx_md5_now"][MESH]
                           and imp["sidecar_sha256_before"] == imp["sidecar_sha256_after"] == B1["sidecar_sha256"])
    g["G0_fresh_content_path"] = (not U1["dest_existed_before"]) and U1["dest_assets_before"] == []
    # ---------------------------------------------------------------- G1
    blend = [B1["blend_scene"]["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
    fbx = [B1["fbx_scene"]["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
    render = [U6["meshes"][MESH]["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
    reexp = [B2["lods"][f"LOD{i}"]["unreal_tris"] for i in range(3)]
    d["G1"] = {"unreal_asset": m3["lod_triangles"], "unreal_render_data": render, "blend": blend,
               "fbx_reimport": fbx, "unreal_reexport": reexp, "ceilings": B1["spec"]["lod_ceilings"],
               "num_lods": m3["num_lods"], "sections": m3["lod_sections"], "unreal_render_vertices": m3["lod_vertices"],
               "blend_vertices": [B1["blend_scene"]["lods"][f"LOD{i}"]["vertices"] for i in range(3)]}
    g["G1_3_lods_tris_equal_blender"] = (m3["num_lods"] == 3 and m3["lod_triangles"] == blend == fbx == render == reexp
                                         and all(t <= c for t, c in zip(blend, B1["spec"]["lod_ceilings"])))
    # ---------------------------------------------------------------- G2
    h = B2["hull"]
    d["G2"] = {"convex_hulls": m3["convex_hulls"], "other_elems": m3["other_collision_elems"], "hull": h,
               "blend_hull": B1["blend_scene"]["hulls"],
               "lod0_max_outside_cm_rounded_5dp": round(max(h["lod0_shipped_max_outside_unreal_hull_cm"],
                                                            h["lod0_unreal_max_outside_unreal_hull_cm"]), 5) + 0.0}
    g["G2_exactly_one_convex_hull"] = m3["convex_hulls"] == 1 and all(v == 0 for v in m3["other_collision_elems"].values()) \
        and len(B2["unreal_hull_nodes"]) == 1
    g["G2_stored_hull_identical_to_shipped_ucx"] = (h["vertex_sets_equal_1e-5cm"] and h["shipped"]["tris"] == h["unreal"]["tris"]
                                                    and h["two_sided_vertex_distance_cm"] < 1e-5
                                                    and abs(h["shipped"]["volume_cm3"] - h["unreal"]["volume_cm3"]) < 1e-4)
    g["G2_lod0_0.0cm_outside_hull"] = d["G2"]["lod0_max_outside_cm_rounded_5dp"] == 0.0 \
        and h["lod1_lod2_unreal_max_outside_unreal_hull_cm"] < 1e-5
    # ---------------------------------------------------------------- G3
    so = {s["name"]: s for s in m3["socket_objects"]}
    cs = m3["component_sockets"]
    bs = B1["blend_scene"]["sockets"]
    rs = U6["meshes"][MESH]["sockets_vs_render_data"]
    fil = B1["spec"]["grip_fillet_midpoint_mm"]
    grip_pred = bs[f"SOCKET_{MESH}_LOD0_Grip"]["predicted_ue_location_cm"]
    d["G3"] = {"asset_sockets": so, "component_sockets": cs, "render_data": rs,
               "blend_grip_mm": bs[f"SOCKET_{MESH}_LOD0_Grip"]["location_mm"],
               "blend_grip_polar_deg": bs[f"SOCKET_{MESH}_LOD0_Grip"]["polar_deg"],
               "spec_fillet_midpoint_mm": fil,
               "grip_plan_radius_cm": math.hypot(*so["Grip"]["relative_location_cm"][:2]),
               "spec_fillet_midpoint_radius_cm": math.hypot(fil[0], fil[1]) / 10.0}
    ok3 = all(so[n]["found"] and so[n]["relative_scale"] == [1.0, 1.0, 1.0] and cs[n]["scale"] == [1.0, 1.0, 1.0]
              for n in ("Grip", "Trail"))
    ok3 &= all(abs(a - b) < 1e-4 for a, b in zip(so["Grip"]["relative_location_cm"], grip_pred))
    ok3 &= abs(d["G3"]["grip_plan_radius_cm"] - d["G3"]["spec_fillet_midpoint_radius_cm"]) < 2e-4
    ok3 &= rs["Grip"]["distance_to_lod0_render_surface_cm"] < 1e-3 and rs["Grip"]["forward_dot_outward_radial"] > 0.9999
    ok3 &= abs(so["Grip"]["relative_rotation"]["yaw"] + 45.0) < 1e-4 and so["Trail"]["relative_location_cm"] == [0.0, 0.0, 0.0]
    ok3 &= rs["Trail"]["up"][2] > 0.9999
    g["G3_grip_trail_scale_1_sane_locations"] = bool(ok3)
    # ---------------------------------------------------------------- G4
    bl = B1["blend_scene"]["lods"]["LOD0"]
    d["G4"] = {"unreal_size_cm": m3["size_cm"], "blend_lod0_size_cm": bl["ue_size_cm"],
               "analytic_size_cm": B1["spec"]["size_cm_analytic"], "unreal_bounds_min_cm": m3["bounds_min_cm"],
               "unreal_bounds_max_cm": m3["bounds_max_cm"], "blend_min_cm": bl["ue_bounds_min_cm"],
               "blend_max_cm": bl["ue_bounds_max_cm"], "bounds_origin_cm": m3["bounds_origin_cm"],
               "sphere_radius_cm": m3["bounds_sphere_radius_cm"], "blend_sphere_radius_cm": bl["ue_bounds_sphere_radius_cm"],
               "render_lod0_bounds_cm": U6["meshes"][MESH]["lods"]["LOD0"]["bounds_cm"]}
    g["G4_bounds_cm_match"] = (all(abs(a - b) < 1e-5 for a, b in zip(m3["size_cm"], bl["ue_size_cm"]))
                               and all(abs(a - b) < 1e-5 for a, b in zip(m3["bounds_min_cm"], bl["ue_bounds_min_cm"]))
                               and all(abs(a - b) < 1e-5 for a, b in zip(m3["bounds_max_cm"], bl["ue_bounds_max_cm"]))
                               and all(0.0 <= b - a < 2e-3 for a, b in zip(m3["size_cm"][:2], B1["spec"]["size_cm_analytic"][:2]))
                               and abs(m3["size_cm"][2] - 0.25) < 1e-5 and all(abs(c) < 1e-5 for c in m3["bounds_origin_cm"])
                               and abs(m3["bounds_sphere_radius_cm"] - bl["ue_bounds_sphere_radius_cm"]) < 1e-4)
    # ---------------------------------------------------------------- G5
    r = m3["bounds_sphere_radius_cm"]
    exp = [1.0, 0.10 * r / 5.0, 0.035 * r / 5.0]
    d["G5"] = {"applied": m3["lod_screen_sizes"], "expected_scaled": exp, "sidecar": U1["imports"][MESH]["sidecar_result"]["lod_screen_sizes"],
               "switch_distance_m_16x9_90deg": [None] + [round(1.7778 * r / 100.0 / x, 4) for x in m3["lod_screen_sizes"][1:]]}
    g["G5_lod_screen_sizes_applied"] = len(m3["lod_screen_sizes"]) == 3 and all(
        abs(a - b) < 1e-4 for a, b in zip(m3["lod_screen_sizes"], exp))
    # ---------------------------------------------------------------- G6
    uv1 = {k: B2["lods"][k]["uv1"] for k in ("LOD0", "LOD1", "LOD2")}
    neg = {k: B2["lods"][k]["uv1_negative_control"] for k in uv1}
    d["G6"] = {"light_map_coordinate_index": m3["light_map_coordinate_index"],
               "dst_lightmap_index": [b["dst_lightmap_index"] for b in m3["lod_build_settings"]],
               "light_map_resolution": m3["light_map_resolution"], "uv1": uv1, "negative_control": neg,
               "reexport_uv_channels": [B2["lods"][k]["unreal_uv_channels"] for k in uv1]}
    g["G6_lightmap_index_1_uv1_0_1_no_overlap"] = (m3["light_map_coordinate_index"] == 1
                                                   and all(b["dst_lightmap_index"] == 1 for b in m3["lod_build_settings"])
                                                   and all(u["inside_0_1"] and u["overlapping_pairs"] == 0
                                                           and u["texels_claimed_by_two_charts"] == 0 for u in uv1.values())
                                                   and all(n["detects"] for n in neg.values()))
    # ---------------------------------------------------------------- G7
    tx = {}
    ok7 = True
    want = {"BC": ("True", "TC_DEFAULT", None), "ORM": ("False", "TC_MASKS", None), "N": ("False", "TC_NORMALMAP", "False")}
    for k, rec in U3["textures"].items():
        info = rec["info"]
        srgb, comp, flip = want[k]
        ok = info["srgb"] == srgb and comp in info["compression_settings"] and (flip is None or info["flip_green_channel"] == flip)
        tag = info["registry_import_tag"].get("parsed", [{}])[0]
        ok &= tag.get("FileMD5") == rec["png_md5_now"] and info["size"] == [2048, 2048]
        v = U4["maps"].get(f"T_Shuriken_HookedCross_{k}", {})
        ok &= bool(v.get("matches_intent", {}).get("all"))
        tx[k] = {"srgb": info["srgb"], "compression": info["compression_settings"], "flip_green": info["flip_green_channel"],
                 "lod_group": info["lod_group"], "size": info["size"], "png_sha256": rec["png_sha256_now"],
                 "unreal_md5_matches_png": tag.get("FileMD5") == rec["png_md5_now"],
                 "u4_verify_fresh_matches_intent": v.get("matches_intent"), "ok": ok}
        ok7 &= ok
    d["G7"] = {"maps": tx, "u2_import_passed": U2["passed"], "u4_verify_passed_all_18": U4["passed"]}
    g["G7_bc_srgb_orm_linear_masks_n_normalmap"] = bool(ok7 and U2["passed"] and U4["passed"])
    # ---------------------------------------------------------------- G8
    logs = {s: log_check(s) for s in ("u1", "u2", "u3", "u4", "u5", "u6")}
    d["G8"] = logs
    g["G8_zero_warning_error_lines"] = all(v["strict_warning_error_lines"] == 0 and v["stderr_bytes"] == 0
                                           and v["summary_line"] == "Success - 0 error(s), 0 warning(s)"
                                           for v in logs.values())

    # ================================================================ HANDEDNESS
    # H1 control A: the six-point Grip socket
    cb = B1["blend_control"]["sockets"][f"SOCKET_{CTRL}_LOD0_Grip"]
    c3 = {s["name"]: s for s in U3["mesh"][CTRL]["socket_objects"]}["Grip"]
    cc = U3["mesh"][CTRL]["component_sockets"]["Grip"]
    bl_cm = [x / 10.0 for x in cb["location_mm"]]
    ue_cm = c3["relative_location_cm"]
    d["H1"] = {"blender_location_cm": bl_cm, "blender_polar_deg": cb["polar_deg"],
               "blender_authored_yaw_deg (Empty z-rot, the 180-deg-Y ue_correction aside)": cb["euler_deg"][2],
               "unreal_location_cm": ue_cm, "unreal_yaw_deg": c3["relative_rotation"]["yaw"],
               "unreal_forward_x_axis": cc["forward_x_axis"],
               "per_axis_ratio_unreal_over_blender": [round(u / b, 5) if abs(b) > 1e-9 else None for u, b in zip(ue_cm, bl_cm)],
               "reads": "Blender (+1.5588, +0.9000, 0) cm at polar +30 deg arrives as Unreal (+1.5588, -0.9000, 0) cm, "
                        "yaw -30: X kept, Y negated, Z kept, yaw negated (via the pipeline sidecar)"}
    g["H1_control_socket_maps_x_-y_z"] = (abs(cb["polar_deg"] - 30.0) < 1e-3 and abs(ue_cm[0] - bl_cm[0]) < 1e-4
                                          and abs(ue_cm[1] + bl_cm[1]) < 1e-4 and abs(ue_cm[2] - bl_cm[2]) < 1e-6
                                          and abs(c3["relative_rotation"]["yaw"] + 30.0) < 1e-4)
    # H2 control B: the six-point render data by UV labels alone
    ctrl_truth = B1["control_fbx_arrays"]["LOD0"]
    ctrl_render = U6["raw"][CTRL]["LOD0"]
    fitc = mapping_fit(ctrl_truth, ctrl_render)
    fc = fitc["uv_v_flipped (v_ue = 1 - v_blender)"]
    d["H2"] = {"six_point_lod0": fitc}
    A = fc.get("A_cm_per_m")
    expA = [[100.0, 0.0, 0.0], [0.0, -100.0, 0.0], [0.0, 0.0, 100.0]]
    g["H2_control_render_data_uv_fit_is_diag_100_-100_100"] = bool(
        A and fc["uniquely_labelled_pairs"] > 100 and all(abs(A[i][j] - expA[i][j]) < 0.01 for i in range(3) for j in range(3))
        and fc["max_residual_cm"] < 1e-3 and fc["det_A"] < 0
        and fitc["uv_v_as_is"]["uniquely_labelled_pairs"] < fc["uniquely_labelled_pairs"] / 4)
    # H3 the hooked cross under the established map
    Aexp = expA
    Amir = [[100.0, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]]    # what a mirror anywhere in the chain would give
    h3 = {}
    ok_h3 = True
    for i in range(3):
        k = f"LOD{i}"
        tr, rd = B1["fbx_arrays"][k], U6["raw"][MESH][k]
        mapped = [apply(Aexp, p) for p in tr["verts_m"]]
        mirr = [apply(Amir, p) for p in tr["verts_m"]]
        rv = [tuple(p) for p in rd["verts_cm"]]
        dp, dm = nn_two_sided(rv, mapped, 0.2), nn_two_sided(rv, mirr, 0.2)
        # normals: every render vertex vs the Blender corners at its mapped position with its UV
        worst_n = 0.0
        bykey = {}
        for li, vi in enumerate(tr["loop_vert"]):
            bykey.setdefault(tuple(round(c, 4) for c in mapped[vi]), []).append(li)
        miss = 0
        for p, n, uv in zip(rd["verts_cm"], rd["normals"], rd["uv0"]):
            key = tuple(round(c, 4) for c in p)
            best = None
            for li in bykey.get(key, []):
                if abs(tr["uv0"][li][0] - uv[0]) <= 3e-4 and abs(1.0 - tr["uv0"][li][1] - uv[1]) <= 3e-4:
                    nb = tr["loop_normals"][li]
                    nm = (nb[0], -nb[1], nb[2])
                    ln = math.sqrt(sum(c * c for c in n)) or 1.0
                    cosang = max(-1.0, min(1.0, sum(a * b for a, b in zip(n, nm)) / ln))
                    ang = math.degrees(math.acos(cosang))
                    best = ang if best is None or ang < best else best
            if best is None:
                miss += 1
            else:
                worst_n = max(worst_n, best)
        h3[k] = {"render_vertices": len(rv), "truth_vertices": len(mapped),
                 "two_sided_max_cm_under_A": dp, "two_sided_max_cm_under_mirrored_A": dm,
                 "normals_max_deg_vs_A_mapped_blender": worst_n, "render_vertices_without_corner_match": miss}
        ok_h3 &= dp < 1e-4 and dm > 0.5 and worst_n < 1.0 and miss == 0
    fith = mapping_fit(B1["fbx_arrays"]["LOD0"], U6["raw"][MESH]["LOD0"])
    fh = fith["uv_v_flipped (v_ue = 1 - v_blender)"]
    h3["hooked_cross_lod0_uv_label_fit"] = fith
    ok_h3 &= bool(fh.get("A_cm_per_m")) and all(abs(fh["A_cm_per_m"][i][j] - expA[i][j]) < 0.01
                                                for i in range(3) for j in range(3))
    d["H3"] = h3
    g["H3_render_data_equals_truth_under_control_map_not_mirror"] = bool(ok_h3)
    # H4 winding vs normals
    w = {k: U6["meshes"][MESH]["lods"][k]["winding_vs_stored_normals"] for k in ("LOD0", "LOD1", "LOD2")}
    wc = U6["meshes"][CTRL]["lods"]["LOD0"]["winding_vs_stored_normals"]
    wb = {k: B1["fbx_scene"]["lods"][k]["views"]["winding_vs_stored_normals"] for k in ("LOD0", "LOD1", "LOD2")}
    d["H4"] = {"unreal_render_hooked_cross": w, "unreal_render_six_point_control": wc, "blender_fbx_truth": wb,
               "flat_faces": {k: U6["meshes"][MESH]["lods"][k]["flat_faces"] for k in w}}
    tris = {k: U6["meshes"][MESH]["lods"][k]["triangles"] for k in w}
    g["H4_winding_vs_normals_consistent_like_control"] = (
        all(w[k]["unreal_convention_CrossProduct(P2-P0,P1-P0)_agree"] == tris[k]
            and w[k]["right_hand_(P1-P0)x(P2-P0)_agree"] == 0 for k in w)
        and wc["unreal_convention_CrossProduct(P2-P0,P1-P0)_agree"] == U6["meshes"][CTRL]["lods"]["LOD0"]["triangles"]
        and wc["right_hand_(P1-P0)x(P2-P0)_agree"] == 0
        and all(wb[k]["disagree"] == 0 for k in wb))
    # H5 display
    cams = U6["camera_bases_from_unreal_MathLibrary"]
    h5 = {"camera_bases": cams, "lods": {}}
    ok5 = True
    for k in ("LOD0", "LOD1", "LOD2"):
        L = U6["meshes"][MESH]["lods"][k]
        rec = {}
        for vn in ("viewer_above_plus_z", "viewer_above_plus_z_yaw37", "viewer_below_minus_z"):
            a = L[vn]
            rec[vn] = {"reads": a["reads"], "offsets_ccw_deg": [t.get("offset_ccw_deg") for t in a["tips"]],
                       "tip_angles_on_screen_deg": [t["angle_deg"] for t in a["tips"]],
                       "arm_axes_on_screen_deg": [x["axis_deg"] for x in a["arms"]],
                       "screen_right_arm_hooks": a.get("screen_right_arm_hooks"),
                       "screen_up_arm_hooks": a.get("screen_up_arm_hooks"),
                       "front_facing_ccw_on_screen": a["front_facing_triangles_ccw_on_screen"],
                       "front_facing_cw_on_screen": a["front_facing_triangles_cw_on_screen"]}
        h5["lods"][k] = rec
        ok5 &= rec["viewer_above_plus_z"]["reads"].startswith("left-facing") and rec["viewer_above_plus_z_yaw37"]["reads"].startswith("left-facing")
        ok5 &= rec["viewer_above_plus_z"]["front_facing_cw_on_screen"] == 0
        ok5 &= rec["viewer_below_minus_z"]["reads"].startswith("right-facing")
    nc = U6["meshes"][MESH]["lod0_mirrored_negative_control"]["viewer_above_plus_z"]
    h5["negative_control_mirrored_render_data_viewer_above"] = {"reads": nc["reads"],
                                                                "offsets": [t.get("offset_ccw_deg") for t in nc["tips"]]}
    caught = not nc["reads"].startswith("left-facing")
    # Unreal's top-view image vs Blender's top view turned +90 deg (proper) and mirrored (improper)
    top = cams["viewer_above_plus_z"]
    rd0 = U6["raw"][MESH]["LOD0"]["verts_cm"]
    scr = [(sum(p[m] * top["right"][m] for m in range(3)) * 10.0, sum(p[m] * top["up"][m] for m in range(3)) * 10.0, 0.0)
           for p in rd0]
    tb = B1["fbx_arrays"]["LOD0"]["verts_m"]
    rot90 = [(-p[1] * 1000.0, p[0] * 1000.0, 0.0) for p in tb]
    refl = [(p[1] * 1000.0, p[0] * 1000.0, 0.0) for p in tb]
    h5["unreal_top_view_vs_blender_top_view_mm"] = {"rotated_plus_90_deg_two_sided_max": nn_two_sided(scr, rot90, 2.0),
                                                   "reflected_two_sided_max": nn_two_sided(scr, refl, 2.0)}
    ok5 &= h5["unreal_top_view_vs_blender_top_view_mm"]["rotated_plus_90_deg_two_sided_max"] < 1e-3 \
        and h5["unreal_top_view_vs_blender_top_view_mm"]["reflected_two_sided_max"] > 5.0
    # the engine's own view + projection matrices (GameplayStatics.get_view_projection_matrix), perspective cameras
    evp = U6["meshes"][MESH]["engine_view_projection"]
    evn = U6["meshes"][MESH]["engine_view_projection_mirrored_negative_control"]
    h5["engine_view_projection_ndc"] = {
        k: {c: {"reads": r.get("reads"), "offsets": [t.get("offset_ccw_deg") for t in r.get("tips", [])],
                "front_facing_ccw_in_ndc": r.get("front_facing_triangles_ccw_in_ndc"),
                "front_facing_cw_in_ndc": r.get("front_facing_triangles_cw_in_ndc"), "error": r.get("error")}
            for c, r in v.items()} for k, v in evp.items()}
    h5["engine_view_projection_mirrored_negative_control"] = {c: r.get("reads") for c, r in evn.items()}
    for k, v in evp.items():
        up, dn = v["camera_100cm_above_looking_down"], v["camera_100cm_below_looking_up"]
        ok5 &= "error" not in up and up["reads"].startswith("left-facing") and up["front_facing_triangles_cw_in_ndc"] == 0
        ok5 &= "error" not in dn and dn["reads"].startswith("right-facing")
    caught &= evn["camera_100cm_above_looking_down"].get("reads", "").startswith("right-facing")
    d["H5"] = h5
    g["H5_plus_z_face_reads_left_facing_in_unreal_view"] = bool(ok5)
    g["H5_negative_control_mirror_caught"] = bool(caught)
    # H6 no import step mirrored
    ims = m3["import_settings"]
    h6 = {"import_settings": ims, "build_scale3d": [b["build_scale3d"] for b in m3["lod_build_settings"]],
          "build_reversed_index_buffer (extra buffer for negative-scale COMPONENTS; not what renders here)":
              [b["build_reversed_index_buffer"] for b in m3["lod_build_settings"]],
          "fbx_nodes_det": B1["fbx_scene"]["all_nodes"], "blend_mirror_audit": B1["blend_mirror_audit"],
          "blend_lod_det": [B1["blend_scene"]["lods"][f"LOD{i}"]["matrix_world_det"] for i in range(3)],
          "reexport_viewer_above": {k: B2["lods"][k]["handedness_unreal_reexport"]["viewer_above_plus_z"]["reads"]
                                    for k in ("LOD0", "LOD1", "LOD2")},
          "reexport_node_det": B2["unreal_nodes"],
          "hull_mirrored_distance_cm": h["two_sided_vertex_distance_cm_if_mirrored"],
          "lod0_mirrored_pokes_out_of_stored_hull_cm": h["lod0_mirrored_max_outside_unreal_hull_cm"],
          "dirty_packages_after_render_read": U6["dirty_packages_after"],
          "allow_cpu_access_saved": U6["meshes"][MESH]["allow_cpu_access_saved"]}
    ok6 = (ims["import_uniform_scale"] > 0 and ims["convert_scene"] and not ims["force_front_x_axis"]
           and ims["import_rotation"] == {"roll": 0.0, "pitch": 0.0, "yaw": 0.0} and ims["import_translation"] == [0.0, 0.0, 0.0]
           and all(b == [1.0, 1.0, 1.0] for b in h6["build_scale3d"])
           and all(n[3] > 0 for n in B1["fbx_scene"]["all_nodes"])
           and not B1["blend_mirror_audit"]["mirror_modifiers"] and not B1["blend_mirror_audit"]["negative_scale_objects"]
           and all(v.startswith("left-facing") for v in h6["reexport_viewer_above"].values())
           and all(n[3] > 0 for n in B2["unreal_nodes"])
           and h["two_sided_vertex_distance_cm_if_mirrored"] > 0.5 and h["lod0_mirrored_max_outside_unreal_hull_cm"] > 0.1
           and U6["dirty_packages_after"] == [])
    d["H6"] = h6
    g["H6_no_import_step_mirrored"] = bool(ok6)
    # Blender-side truth (for completeness): every LOD of the .blend and the FBX re-import reads left-facing from above
    bt = {sc: {k: B1[sc]["lods"][k]["views"]["viewer_above_plus_z"]["reads"] for k in ("LOD0", "LOD1", "LOD2")}
          for sc in ("blend_scene", "fbx_scene")}
    d["blender_truth_viewer_above"] = bt
    d["blender_truth_negative_control"] = B1["fbx_scene"]["lod0_mirrored_negative_control"]["viewer_above_plus_z"]["reads"]
    g["H0_blender_truth_left_facing_and_control_caught"] = (
        all(v.startswith("left-facing") for s in bt.values() for v in s.values())
        and d["blender_truth_negative_control"].startswith("right-facing"))
    out = {"asset": U3["assets"][MESH], "control_asset": U3["assets"][CTRL], "engine": U3["engine"],
           "fbx": B1["fbx"], "fbx_sha256": fbx_sha, "gates": g, "all_passed": all(g.values()),
           "handedness_ok": all(v for k, v in g.items() if k.startswith("H")), "detail": d,
           "u5_export": U5}
    (HERE / "verification_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k, v in g.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    print("ALL", out["all_passed"], "HANDEDNESS", out["handedness_ok"])


main()
