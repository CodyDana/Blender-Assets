"""Shared helpers for UnrealCheck6 (runs inside the UE 5.8.2 pythonscript commandlet).

3.10 (the plain kunai, SM_Kunai_Plain): FORM_SPECS["kunai_plain"] from the build SPEC (Scripts/shuriken/
build_kunai_plain.py, pure Python); a form may expect several convex hulls ("hulls"), other socket names ("sockets") and
several material slots ("material_slots"); ``kunai_checks`` reads the RENDER data of every LOD (Allow CPU Access set in
memory only, as for the hooked cross) and gates the two material sections, the wrap section's UV tile (u 1..2) against
the steel's (u 0..1), and the lettering band's rectangle (V flipped by the importer) landing on the grip's +Z face with
U toward the tip.

3.10.1: the band is a rectangle of the grip's own straight unroll, not a separate island, so the band gate is now on
the MAPPING - every band corner in the render data within 0.1 texel of the map the rectangle defines (u linear in
design x, Blender's v linear in the angle about +Z), on the +Z face, covering the 72 mm - and pass 1 imports with
save=False so the sidecar's save is the package's only save (the triple save raced Unreal's changelist scan).

3.9.1 (hooked-cross maintenance): ``handedness_render_check`` - the hooked cross's gate on the RENDER data of every LOD
(build scale, winding vs normals, positions vs the FBX truth, the reading from a camera above, the texture sheets),
with mirrored negative controls; pass 2 gates 11 and 12.  It reuses UnrealCheck11_HookedCrossVerify/hc_chirality.py
(copied here unchanged).

Maintenance-pass verification of the rebuilt pack (library 3.2). Adapted from the verifier's
UnrealCheck5 (uc5_common.py), with three changes:
  * it runs in the shuriken-only WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject
    (legacy FBX importer) into /Game/ShurikenCheck6/Verify, not in the JinMuWon-named UnrealTest project;
  * the expected LOD screen sizes are the pack's 1.0 / 0.10 / 0.035, read from the sidecar and
    cross-checked against the build report and against the pack constant;
  * pass 1 records the SHA-256 of the exact FBX and sidecar it imported, so the evidence is tied to
    those bytes (attach_engine_check.py compares them with the build report's export_sha256).

Expectations are the SPEC figures (study 2.1/2.2/2.3 + study 4), not only the build report, so a report
that drifted from the spec cannot pass itself.

Parameterized per form (senban build, library 3.3): FORM_SPECS holds each form's study size and its
expected LOD screen sizes, computed here from the study figures - the pack's 1.0 / 0.10 / 0.035 for a
~50 mm star, scaled by bounding radius / 50 mm for a form of another size (study 4, amended
2026-09-17), which is what the build must have written into the sidecar.  A new form adds one entry.
"""
import math
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
# A fresh content path per verification run (SHURIKEN_DEST), so a re-run never reads an asset a
# previous run saved: the style pass (library 3.4) verified into /Game/ShurikenCheck6/Restyle.
DEST = os.environ.get("SHURIKEN_DEST", "/Game/ShurikenCheck6/Verify")
FORM = os.environ.get("SHURIKEN_FORM", "eight_point")
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{FORM}_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
ASSET = f"{DEST}/{MESH}"

PACK_SCREEN_SIZES = [1.0, 0.1, 0.035]               # for a star of tip radius ~50 mm


def _scaled_screen_sizes(radius_mm, reference_mm=50.0):
    return [1.0] + [round(s * radius_mm / reference_mm, 4) for s in PACK_SCREEN_SIZES[1:]]


_SENBAN_SIDE_MM = 76.2                                # study 2.3: the [17] pair, a 76.2 mm square
FORM_SPECS = {
    "eight_point": {"size_cm": [10.0, 10.0, 0.25],    # study 2.2: 100 mm, 2.5 mm
                    "screen_sizes": PACK_SCREEN_SIZES,
                    "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    "four_point": {"size_cm": [9.7, 9.7, 0.3],        # study 2.1: 97 mm, 3.0 mm
                   "screen_sizes": PACK_SCREEN_SIZES,
                   "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    "square_plate": {"size_cm": [round(_SENBAN_SIDE_MM * math.sqrt(2.0) / 10.0, 6)] * 2 + [0.19],   # 107.763 mm, 1.9 mm
                     "screen_sizes": _scaled_screen_sizes(_SENBAN_SIDE_MM / math.sqrt(2.0)),   # corner radius 53.88 mm
                     "lod_bands": [(1200, 2500), (500, 900), (0, 250)]},   # plate: no floor at LOD2
    # study 2.4: 98 mm tip to tip, 2.0 mm; +X down one tip, so the Y span is 2 x 49 sin 60 = 84.87 mm.
    # Tip radius 49 mm: the pack sizes scaled by 49 / 50 (1.0 / 0.098 / 0.0343).
    "six_point": {"size_cm": [9.8, round(2.0 * 4.9 * math.sin(math.radians(60.0)), 6), 0.2],
                  "screen_sizes": _scaled_screen_sizes(49.0),
                  "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    # study 2.5: 150 mm square bar, 6 mm section, lying on a face, +X toward the point. Unreal's bounds sphere
    # radius is the butt corners' distance from the box centre, sqrt(75^2 + 2 x 1.5^2) = 75.03 mm: the pack sizes
    # scaled by 75.03 / 50 (1.0 / 0.1501 / 0.0525). Bar LOD bands: ceilings only (bar_spec.BAR_LOD_BANDS).
    "spike": {"size_cm": [15.0, 0.6, 0.6],
              "screen_sizes": _scaled_screen_sizes(math.sqrt(75.0 ** 2 + 2.0 * 1.5 ** 2)),
              "lod_bands": [(0, 150), (0, 100), (0, 48)]},
}


def _hooked_cross_spec():
    """The hooked cross (library 3.9): the plan span is the LOD0 outline's own extent - the outline is analytic, so it
    is computed from the build SPEC (Scripts/shuriken/build_hooked_cross.py, pure Python through outline_spec), not
    read from the report; plate 2.5 mm; tips at r = 50 mm, the pack's reference radius, so the screen sizes are the
    pack's own; ceilings only (no star floors)."""
    import sys as _sys
    shuriken = str(PROJ / "Scripts" / "shuriken")
    if shuriken not in _sys.path:
        _sys.path.insert(0, shuriken)
    import build_hooked_cross as _B
    o = _B.SPEC.outline()
    xs = []
    for run in o.columns(_B.SPEC.lods[0]):
        for c in run.columns:
            for x, y in ((c.x, c.y), (c.ex, c.ey)):
                xs += [x, -y, -x, y]                       # the four quarter turns' x coordinates
    span_cm = round((max(xs) - min(xs)) * 100.0, 6)
    return {"size_cm": [span_cm, span_cm, round(_B.SPEC.thickness_mm / 10.0, 6)],
            "screen_sizes": _scaled_screen_sizes(_B.SPEC.tip_radius_mm),
            "lod_bands": [tuple(lod.band) for lod in _B.SPEC.lods]}


def _kunai_plain_spec():
    """The plain kunai (library 3.10): the bounds are the build-to extents - 280 mm tip to ring end, 36 mm across the
    blade's widest point, and the grip's own diameter (3.10.1: 20.0 mm over the tape's overlap ridges, where 3.10 had
    21.2 mm over the raised collars the review removed) - the screen sizes the pack's scaled by Unreal's bounds radius
    (the tip and the ring's outer wall, sqrt(140^2 + 1.5^2)), the LOD bands, sockets, hulls and slots from the SPEC."""
    import sys as _sys
    shuriken = str(PROJ / "Scripts" / "shuriken")
    if shuriken not in _sys.path:
        _sys.path.insert(0, shuriken)
    import build_kunai_plain as _K
    from shuriken_lib import kunai_spec as _S
    return {"size_cm": [round(_S.OVERALL / 10.0, 6), round(2.0 * _S.BLADE_MAX_HALF / 10.0, 6),
                        round(2.0 * _S.WRAP_R / 10.0, 6)],
            "screen_sizes": _scaled_screen_sizes(math.hypot(140.0, 1.5)),
            "lod_bands": [tuple(lod.band) for lod in _K.SPEC.lods],
            "hulls": 2, "sockets": ["Grip", "Trail", "Tip", "Ring"],
            "material_slots": ["M_Shuriken_Master", "M_Kunai_Wrap"],
            "shift_mm": None}


if FORM == "hooked_cross":
    FORM_SPECS["hooked_cross"] = _hooked_cross_spec()
if FORM == "kunai_plain":
    FORM_SPECS["kunai_plain"] = _kunai_plain_spec()
SPEC = FORM_SPECS[FORM]
LOD_BANDS = SPEC["lod_bands"]
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
BLENDER_FBX_COUNTS = json.loads((HERE / "blender_fbx_counts.json").read_text(encoding="utf-8"))["forms"][FORM]
FBX_LOD_TRIANGLES = [BLENDER_FBX_COUNTS["nodes"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]
SIDECAR_PAYLOAD = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXPECTED_SCREEN_SIZES = SIDECAR_PAYLOAD.get("lod_screen_sizes")
EXPECTED_SOCKETS = {r["socket"]: r for r in SIDECAR_PAYLOAD["sockets"]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v, nd=4):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def subsystem():
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    if sub is None:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
    return sub


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:200]} if default is None else default


def inspect(mesh):
    """Everything the gates need, read from a loaded StaticMesh."""
    sub = subsystem()
    info = {"asset": mesh.get_path_name()}
    n = mesh.get_num_lods()
    info["num_lods"] = n
    info["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
    info["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
    info["lod_sections"] = [safe(lambda i=i: mesh.get_num_sections(i)) for i in range(n)]
    info["lod_screen_sizes"] = safe(lambda: [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)])
    info["lod_source_uv_channels"] = [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]
    info["auto_compute_lod_screen_size"] = safe(lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: bs.get_editor_property(k) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "min_lightmap_resolution",
                "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
    info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)), default=-1)
                                     for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
    info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
    b = mesh.get_bounding_box()
    info["bounds_min_cm"] = vec(b.min)
    info["bounds_max_cm"] = vec(b.max)
    info["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4), round(b.max.z - b.min.z, 4)]
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    info["socket_array"] = []
    comp0 = unreal.new_object(unreal.StaticMeshComponent)
    comp0.set_static_mesh(mesh)
    for sname in comp0.get_all_socket_names():
        s = mesh.find_socket(sname)
        if s is None:
            info["socket_array"].append({"name": str(sname), "find_socket": None})
            continue
        info["socket_array"].append({
            "name": str(s.get_editor_property("socket_name")),
            "outer": s.get_outer().get_path_name() if s.get_outer() else None,
            "relative_location": vec(s.get_editor_property("relative_location")),
            "relative_rotation": [round(s.get_editor_property("relative_rotation").roll, 4),
                                  round(s.get_editor_property("relative_rotation").pitch, 4),
                                  round(s.get_editor_property("relative_rotation").yaw, 4)],
            "relative_scale": vec(s.get_editor_property("relative_scale")),
        })
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    info["sockets"] = []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        info["sockets"].append({"name": str(name), "location_cm": vec(t.translation),
                                "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                                "scale": vec(t.scale3d)})
    return info


def lod0_positions_cm(mesh):
    """LOD0 source vertex positions (Unreal cm, Unreal frame) from the saved StaticMeshDescription."""
    desc = mesh.get_static_mesh_description(0)
    out = []

    def make_id(i):
        for field in ("id_value", "value"):
            try:
                vid = unreal.VertexID()
                vid.set_editor_property(field, i)
                return vid
            except Exception:  # noqa: BLE001
                pass
        return unreal.VertexID(i)

    for i in range(desc.get_vertex_count()):
        p = desc.get_vertex_position(make_id(i))
        out.append((p.x, p.y, p.z))
    return out


def handedness_check(mesh):
    """The hooked cross in Unreal (library 3.9): does the SAVED asset carry the left-facing outline on +Z?

    1. Positions: every LOD0 vertex Unreal saved against the Blender truth (hooked_cross_truth.py: the shipped FBX
       re-imported in a fresh Blender), mapped by the legacy importer's documented axis conversion - Blender metres
       (x, y, z) -> Unreal cm (100 x, -100 y, 100 z), a change of frame, not a mirror of the object (Unreal is
       left-handed) - two-sided nearest-vertex distance must be ~0; the same truth MIRRORED (100 x, +100 y, 100 z)
       must NOT match (the negative control: a mirror anywhere in the chain would swap which of the two matches).
    2. Reading: in a right-handed plan frame built from Unreal's (X, -Y) - Unreal's top view with +Z toward the viewer
       - the four farthest vertices (the hook tips) must sit 35 deg COUNTER-clockwise of the nearest axis.
    """
    import math as _m
    truth = json.loads((HERE / "hooked_cross_truth.json").read_text(encoding="utf-8"))
    ue = lod0_positions_cm(mesh)
    tb = truth["lod0_vertices_m"]
    proper = [(100.0 * x, -100.0 * y, 100.0 * z) for x, y, z in tb]
    mirrored = [(100.0 * x, 100.0 * y, 100.0 * z) for x, y, z in tb]

    def nn_max(a, b):
        worst = 0.0
        for p in a:
            best = min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 for q in b)
            worst = max(worst, best)
        return _m.sqrt(worst)

    d_proper = max(nn_max(ue, proper), nn_max(proper, ue))
    d_mirror = max(nn_max(ue, mirrored), nn_max(mirrored, ue))
    radial = [_m.hypot(x, y) for x, y, _z in ue]
    rmax = max(radial)
    tips = []
    for (x, y, _z), r in zip(ue, radial):
        if r > rmax - 1e-4:
            a = _m.degrees(_m.atan2(-y, x))                 # right-handed plan frame (X, -Y), +Z toward the viewer
            if not any(abs(((a - b) + 180.0) % 360.0 - 180.0) < 1.0 for b in tips):
                tips.append(a)
    offsets = sorted(round(((a + 45.0) % 90.0) - 45.0, 3) for a in tips)   # angle past the nearest axis
    out = {"lod0_vertices_unreal": len(ue), "lod0_vertices_truth": len(tb),
           "truth_fbx_sha256": truth.get("fbx_sha256"), "fbx_sha256_now": sha256(FBX),
           "max_distance_cm_documented_conversion": round(d_proper, 7),
           "max_distance_cm_if_mirrored": round(d_mirror, 4),
           "tip_radius_cm": round(rmax, 5), "tip_angles_deg_right_handed_plan": sorted(round(a, 3) for a in tips),
           "tip_offsets_from_nearest_axis_deg": offsets,
           "blender_truth_gate": truth.get("handedness_gate_passed")}
    out["passed"] = bool(len(ue) == len(tb) and d_proper < 1e-4 and d_mirror > 0.5 and len(tips) == 4
                         and all(34.5 < v < 35.5 for v in offsets) and truth.get("handedness_gate_passed")
                         and truth.get("fbx_sha256") == out["fbx_sha256_now"])
    return out


def _dirty_packages():
    try:
        return sorted(str(pk.get_name()) for pk in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    except Exception as exc:  # noqa: BLE001
        return f"n/a: {exc}"[:120]


def _render_lod(mesh, lod):
    """One LOD's RENDER data (position / tangent-Z normal / UV0 vertex buffers + index buffer), Unreal cm."""
    verts, tris, normals, uvs = [], [], [], []
    for sec in range(int(mesh.get_num_sections(lod))):
        v, t, n, uv, _tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, sec)
        base = len(verts)
        verts += [(p.x, p.y, p.z) for p in v]
        normals += [(p.x, p.y, p.z) for p in n]
        uvs += [(p.x, p.y) for p in uv]
        tris += [(base + t[i], base + t[i + 1], base + t[i + 2]) for i in range(0, len(t), 3)]
    return {"verts_cm": verts, "tris": tris, "normals": normals, "uv0": uvs}


def _basis(rot):
    f = unreal.MathLibrary.get_forward_vector(rot)
    r = unreal.MathLibrary.get_right_vector(rot)
    u = unreal.MathLibrary.get_up_vector(rot)
    clean = lambda v: tuple(0.0 if abs(c) < 1e-12 else c for c in (v.x, v.y, v.z))  # noqa: E731
    return {"forward": clean(f), "right": clean(r), "up": clean(u)}


def handedness_render_check(mesh):
    """3.9.1 (the geometry and Unreal reviews of the hooked-cross build): the gate on what Unreal RENDERS, every LOD.

    Gate 10 reads the SOURCE StaticMeshDescription of LOD0 only; BuildSettings.BuildScale3D is applied when the render
    data is built (StaticMeshBuilder.cpp), so a negative build scale, or a mirror on LOD1 / LOD2, would change what
    renders and still pass it.  This reads every LOD's render buffers (ProceduralMeshLibrary.get_section_from_static_mesh,
    which needs Allow CPU Access: set IN MEMORY ONLY with notify_mode NEVER - no PostEditChange, no rebuild, nothing
    saved; the dirty-package list is recorded before and after), and per LOD requires:
      * build_scale3d == (1, 1, 1);
      * every triangle's winding agrees with its stored normals under Unreal's own rule CrossProduct(P2-P0, P1-P0);
      * the render positions equal the Blender truth of the shipped FBX (hooked_cross_truth.json, every LOD) under the
        importer's documented conversion (100 x, -100 y, 100 z) within 1e-4 cm, and NOT under the mirrored mapping;
      * seen by a camera above the plate (Rotator pitch -90: its screen right / up from unreal.MathLibrary), the
        front-facing triangles read LEFT-facing (hc_chirality: four arms, four tips, each tip +35 deg counter-clockwise
        of its arm) and all wind counter-clockwise on screen;
      * the texture sheets: every plate triangle (|N.z| = 1) turns the same way in the texture as displayed (u right,
        1 - v up: Unreal's V is flipped from Blender's) as in that top view, so both plate islands of the maps read
        as the presented face;
    and, as negative controls, the same LOD0 render data mirrored (y -> -y, winding reversed) must NOT read left-facing,
    and u-mirrored UVs must fail the texture reading.  The camera below the plate (pitch +90) reads the mirror image -
    the accepted back-face physics - and is recorded, not gated."""
    import hc_chirality as HC
    sub = subsystem()
    truth = json.loads((HERE / "hooked_cross_truth.json").read_text(encoding="utf-8"))
    cams = {"above": _basis(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)),
            "below": _basis(unreal.Rotator(roll=0.0, pitch=90.0, yaw=0.0))}
    out = {"dirty_packages_before": _dirty_packages(), "camera_bases_from_unreal_MathLibrary": cams, "lods": {}}
    out["allow_cpu_access_saved"] = bool(mesh.get_editor_property("allow_cpu_access"))
    mesh.set_editor_property("allow_cpu_access", True, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)

    def nn_max(a, b):
        worst = 0.0
        for p in a:
            best = min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 for q in b)
            worst = max(worst, best)
        return math.sqrt(worst)

    def uniq(points):
        seen = {}
        for p in points:
            seen[(round(p[0], 5), round(p[1], 5), round(p[2], 5))] = p
        return list(seen.values())

    def texture_reading(d, mirror_u=False):
        top, same, opposite = cams["above"], 0, 0
        for i, j, k in d["tris"]:
            n = HC.winding_normal(d["verts_cm"][i], d["verts_cm"][j], d["verts_cm"][k], "unreal")
            if abs(HC.norm(n)[2]) < 0.999:
                continue
            scr = [(HC.dot(d["verts_cm"][m], top["right"]), HC.dot(d["verts_cm"][m], top["up"])) for m in (i, j, k)]
            img = [((-1.0 if mirror_u else 1.0) * d["uv0"][m][0], 1.0 - d["uv0"][m][1]) for m in (i, j, k)]
            if HC.signed_area2(*scr) * HC.signed_area2(*img) > 0.0:
                same += 1
            else:
                opposite += 1
        return {"plate_triangles_same_turn_as_top_view": same, "plate_triangles_mirrored": opposite,
                "passed": same > 0 and opposite == 0}

    all_ok = True
    for lod in range(int(mesh.get_num_lods())):
        rec = {}
        bs = sub.get_lod_build_settings(mesh, lod)
        scale = bs.get_editor_property("build_scale3d")
        rec["build_scale3d"] = [scale.x, scale.y, scale.z]
        rec["build_reversed_index_buffer"] = bool(bs.get_editor_property("build_reversed_index_buffer"))
        d = _render_lod(mesh, lod)
        vmm = [tuple(c * 10.0 for c in v) for v in d["verts_cm"]]
        fn = [HC.winding_normal(vmm[i], vmm[j], vmm[k], "unreal") for i, j, k in d["tris"]]
        agree = 0
        for (i, j, k), n in zip(d["tris"], fn):
            m = tuple(d["normals"][i][c] + d["normals"][j][c] + d["normals"][k][c] for c in range(3))
            agree += HC.dot(HC.norm(n), HC.norm(m)) > 0.0
        rec["triangles"] = len(d["tris"])
        rec["winding_agrees_with_normals_unreal_rule"] = agree
        tb = truth["lod_vertices_m"][f"LOD{lod}"]
        proper = uniq([(100.0 * x, -100.0 * y, 100.0 * z) for x, y, z in tb])
        mirrored = uniq([(100.0 * x, 100.0 * y, 100.0 * z) for x, y, z in tb])
        ue = uniq(d["verts_cm"])
        rec["position_max_cm_documented_conversion"] = round(max(nn_max(ue, proper), nn_max(proper, ue)), 7)
        rec["position_max_cm_if_mirrored"] = round(max(nn_max(ue, mirrored), nn_max(mirrored, ue)), 4)
        t2, areas = HC.screen_view(vmm, d["tris"], fn, cams["above"]["forward"], cams["above"]["right"],
                                   cams["above"]["up"])
        above = HC.analyse(t2)
        rec["viewer_above"] = {k: above.get(k) for k in ("reads", "left_facing", "tips", "arms", "four_tips_four_arms_c4",
                                                          "screen_right_arm_hooks", "screen_up_arm_hooks")}
        rec["viewer_above"]["front_facing_ccw_on_screen"] = sum(1 for a in areas if a > 0)
        rec["viewer_above"]["front_facing_cw_on_screen"] = sum(1 for a in areas if a <= 0)
        t2b, _ab = HC.screen_view(vmm, d["tris"], fn, cams["below"]["forward"], cams["below"]["right"],
                                  cams["below"]["up"])
        rec["viewer_below_accepted_back_face"] = HC.analyse(t2b).get("reads")
        rec["texture_sheets"] = texture_reading(d)
        ok = (rec["build_scale3d"] == [1.0, 1.0, 1.0] and agree == len(d["tris"]) and len(d["tris"]) > 0
              and rec["position_max_cm_documented_conversion"] < 1e-4 and rec["position_max_cm_if_mirrored"] > 0.5
              and above.get("left_facing") is True and rec["viewer_above"]["front_facing_cw_on_screen"] == 0
              and rec["texture_sheets"]["passed"])
        rec["passed"] = bool(ok)
        all_ok = all_ok and ok
        if lod == 0:
            mir = {"verts_cm": [(x, -y, z) for x, y, z in d["verts_cm"]], "tris": [(i, k, j) for i, j, k in d["tris"]]}
            mvmm = [tuple(c * 10.0 for c in v) for v in mir["verts_cm"]]
            mfn = [HC.winding_normal(mvmm[i], mvmm[j], mvmm[k], "unreal") for i, j, k in mir["tris"]]
            mt2, _ma = HC.screen_view(mvmm, mir["tris"], mfn, cams["above"]["forward"], cams["above"]["right"],
                                      cams["above"]["up"])
            neg = HC.analyse(mt2)
            neg_tex = texture_reading(d, mirror_u=True)
            out["negative_control"] = {"mirrored_render_data_reads": neg.get("reads"),
                                       "mirrored_left_facing": neg.get("left_facing"),
                                       "u_mirrored_texture_passes": neg_tex["passed"],
                                       "caught": neg.get("left_facing") is not True and not neg_tex["passed"]}
        out["lods"][f"LOD{lod}"] = rec
    out["allow_cpu_access_in_memory_after"] = bool(mesh.get_editor_property("allow_cpu_access"))
    out["dirty_packages_after"] = _dirty_packages()
    out["truth_fbx_sha256"] = truth.get("fbx_sha256")
    out["fbx_sha256_now"] = sha256(FBX)
    out["texture_sheets_passed"] = bool(out["lods"]) and all(r["texture_sheets"]["passed"] for r in out["lods"].values())
    out["passed"] = bool(all_ok and len(out["lods"]) == 3 and out["negative_control"]["caught"]
                         and truth.get("fbx_sha256") == out["fbx_sha256_now"])
    return out


def kunai_checks(mesh, info):
    """3.10, the plain kunai: two material slots and two sections on every LOD; in the RENDER data of every LOD the steel
    section's UV0 in u 0..1 and the wrap section's in u 1..2 (Wrap addressing), v in 0..1; and the lettering band - the
    wrap triangles whose UV0 lies in the build's band rectangle (Unreal's V = 1 - Blender's) - on the +Z face, inside the
    band's x range, with U growing toward the tip (+X) and Unreal's V growing toward Unreal's +Y (Blender's -Y: the FBX
    importer's change of frame; Blender's V grows toward Blender's +Y).  Allow CPU Access is set in memory only
    (notify NEVER: nothing rebuilt or saved; dirty packages recorded before and after)."""
    lett = REPORT["lettering"]["uv"]
    rect_b = lett["uv0_blender"]
    rect = {"u_min": rect_b["u_min"], "u_max": rect_b["u_max"], "v_min": 1.0 - rect_b["v_max"],
            "v_max": 1.0 - rect_b["v_min"]}
    shift_mm = REPORT["measured"]["pivot_design_x_mm"]
    band = lett["on_the_model_mm"]
    x_lo_cm, x_hi_cm = (band["x_from"] - shift_mm) / 10.0, (band["x_to"] - shift_mm) / 10.0
    z_min_cm = band["grip_radius_mm"] * math.cos(math.radians(band["half_angle_about_plus_z_deg"])) / 10.0
    # 3.10.1: the band is no longer its own UV island but a rectangle of the grip's own straight unroll, so the gate
    # proves the MAPPING instead of an island's outline.  From the band's rectangle and its own millimetres the map is
    # fixed: u grows linearly with design x (u_min at x_from, u_max at x_to) and Blender's v with the angle about +Z
    # (v_min at -half_angle, v_max at +half_angle), Unreal's v = 1 - Blender's.  Every band triangle corner in the
    # engine's render data must sit where that map says, to a tenth of a texel.
    half_rad = math.radians(band["half_angle_about_plus_z_deg"])
    u_per_mm = (rect_b["u_max"] - rect_b["u_min"]) / (band["x_to"] - band["x_from"])
    v_per_rad = (rect_b["v_max"] - rect_b["v_min"]) / (2.0 * half_rad)
    v_mid_b = 0.5 * (rect_b["v_min"] + rect_b["v_max"])
    v_period = v_per_rad * 2.0 * math.pi                       # one turn of the grip in v
    # Unreal stores UV0 as float16: at u ~1.8 one step is 2^-10, so half a step is 0.5 texels at 1024 (0.25 in v).
    map_tolerance_texels = 0.6
    x_tolerance_cm = 0.6     # a band triangle's CENTROID may sit this far past the rectangle on a coarse LOD
    z_min_fraction = 0.5     # ... and must stay well on the +Z half: within 60 deg of +Z

    def band_map_error(x_cm, y_cm, z_cm, u, v):
        """(du, dv) in UV units between a band corner's stored UV and the map the rectangle defines."""
        design_x = x_cm * 10.0 + shift_mm
        phi = math.atan2(-y_cm, z_cm)                          # Blender's angle about +Z (the importer flips Y)
        u_pred = rect_b["u_min"] + (design_x - band["x_from"]) * u_per_mm
        v_pred = 1.0 - (v_mid_b + phi * v_per_rad)             # Unreal's V
        dv = (v - v_pred + 0.5 * v_period) % v_period - 0.5 * v_period
        return abs(u - u_pred), abs(dv)
    out = {"dirty_packages_before": _dirty_packages(), "slots": [s["slot"] for s in info["material_slots"]],
           "expected_slots": SPEC["material_slots"], "lod_sections": info["lod_sections"], "rect_unreal": rect,
           "lods": {}}
    out["allow_cpu_access_saved"] = bool(mesh.get_editor_property("allow_cpu_access"))
    mesh.set_editor_property("allow_cpu_access", True, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    ok = out["slots"] == SPEC["material_slots"] and info["lod_sections"] == [2, 2, 2]
    for lod in range(int(mesh.get_num_lods())):
        rec = {"sections": {}}
        band_pts, band_uv, band_centroids = [], [], []
        for sec in range(int(mesh.get_num_sections(lod))):
            v, t, _n, uv, _tg = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, sec)
            us = [p.x for p in uv]
            vs = [p.y for p in uv]
            rec["sections"][str(sec)] = {"vertices": len(v), "triangles": len(t) // 3,
                                         "u_range": [round(min(us), 6), round(max(us), 6)],
                                         "v_range": [round(min(vs), 6), round(max(vs), 6)]}
            for i in range(0, len(t), 3):
                tri = (t[i], t[i + 1], t[i + 2])
                cu = sum(uv[k].x for k in tri) / 3.0
                cv = sum(uv[k].y for k in tri) / 3.0
                if rect["u_min"] - 1e-5 <= cu <= rect["u_max"] + 1e-5 and rect["v_min"] - 1e-5 <= cv <= rect["v_max"] + 1e-5:
                    band_centroids.append((sum(v[k].x for k in tri) / 3.0, sum(v[k].y for k in tri) / 3.0,
                                           sum(v[k].z for k in tri) / 3.0))
                    for k in tri:
                        band_pts.append((v[k].x, v[k].y, v[k].z))
                        band_uv.append((uv[k].x, uv[k].y))
        s0, s1 = rec["sections"].get("0", {}), rec["sections"].get("1", {})
        tiles_ok = (bool(s0) and bool(s1) and s0["u_range"][0] >= -1e-5 and s0["u_range"][1] <= 1.0 + 1e-5
                    and s1["u_range"][0] >= 1.0 - 1e-5 and s1["u_range"][1] <= 2.0 + 1e-5
                    and all(-1e-5 <= s["v_range"][0] and s["v_range"][1] <= 1.0 + 1e-5 for s in (s0, s1)))

        def corr(a, b):
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
            den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) or 1.0
            return num / den
        if band_pts:
            xs = [p[0] for p in band_pts]
            ys = [p[1] for p in band_pts]
            zs = [p[2] for p in band_pts]
            us = [q[0] for q in band_uv]
            vs = [q[1] for q in band_uv]
            errors = [band_map_error(p[0], p[1], p[2], q[0], q[1]) for p, q in zip(band_pts, band_uv)]
            du_max = max(e[0] for e in errors)
            dv_max = max(e[1] for e in errors)
            cx = [c[0] for c in band_centroids]
            cz_min = min(c[2] for c in band_centroids)
            # coverage is measured on the band triangles' CORNERS: a coarse LOD's grip faces are longer than the band
            # itself, so their centroids cluster in the middle while the faces still carry the whole band
            covered = (min(max(xs), x_hi_cm) - max(min(xs), x_lo_cm)) / (x_hi_cm - x_lo_cm)
            z_floor_cm = z_min_fraction * band["grip_radius_mm"] / 10.0
            band_rec = {"corners": len(band_pts), "triangles": len(band_centroids),
                        "corner_x_cm": [round(min(xs), 4), round(max(xs), 4)],
                        "centroid_x_cm": [round(min(cx), 4), round(max(cx), 4)],
                        "expected_x_cm": [round(x_lo_cm, 4), round(x_hi_cm, 4)],
                        "centroid_z_min_cm": round(cz_min, 4), "z_floor_cm": round(z_floor_cm, 4),
                        "band_z_on_the_circle_cm": round(z_min_cm, 4),
                        "corr_u_x": round(corr(us, xs), 5), "corr_v_unreal_y": round(corr(vs, ys), 5),
                        "map_max_du_texels": round(du_max * 1024.0, 4), "map_max_dv_texels": round(dv_max * 1024.0, 4),
                        "map_tolerance_texels": map_tolerance_texels,
                        "band_length_covered": round(covered, 4),
                        "rule": ("every band corner within half a float16 step of the map the rectangle defines (0.5 "
                                 "texel in u, 0.25 in v), every band triangle's centroid inside the band's x range "
                                 "(0.6 cm of slack for a coarse LOD's long faces) and on the +Z half, the band "
                                 "covering its 72 mm, U toward the tip and V toward Unreal's +Y")}
            band_ok = (du_max * 1024.0 < map_tolerance_texels and dv_max * 1024.0 < map_tolerance_texels
                       and covered > 0.9 and cz_min >= z_floor_cm
                       and min(cx) >= x_lo_cm - x_tolerance_cm and max(cx) <= x_hi_cm + x_tolerance_cm
                       and band_rec["corr_u_x"] > 0.99 and band_rec["corr_v_unreal_y"] > 0.9)
        else:
            band_rec, band_ok = {"corners": 0}, False
        rec["lettering_band"] = band_rec
        rec["tiles_ok"] = tiles_ok
        rec["band_ok"] = band_ok
        rec["passed"] = bool(tiles_ok and band_ok)
        ok = ok and rec["passed"]
        out["lods"][f"LOD{lod}"] = rec
    out["allow_cpu_access_in_memory_after"] = bool(mesh.get_editor_property("allow_cpu_access"))
    out["dirty_packages_after"] = _dirty_packages()
    out["passed"] = bool(ok and len(out["lods"]) == 3)
    return out


def gates(info):
    """Gates 1-6 (gate 7, the zero Warning/Error log lines, is added by attach_engine_check.py)."""
    n = info["num_lods"]
    tri_delta = [a - b for a, b in zip(info["lod_triangles"], BLENDER_LOD_TRIANGLES)]
    size_ok = all(abs(a - e) < 1e-3 for a, e in zip(info["size_cm"], SPEC["size_cm"]))
    want_sockets = SPEC.get("sockets") or ["Grip", "Trail"]
    sockets_ok = (len(info["sockets"]) == len(want_sockets) and len(info["socket_array"]) == len(want_sockets))
    socket_detail = {}
    for s in info["sockets"]:
        exp = EXPECTED_SOCKETS.get(s["name"])
        ok = (exp is not None
              and all(abs(a - e) < 1e-3 for a, e in zip(s["location_cm"], exp["location_cm"]))
              and abs(s["rpy"][2] - exp["rotation_deg"]["yaw"]) < 1e-3
              and abs(s["rpy"][0]) < 1e-3 and abs(s["rpy"][1]) < 1e-3
              and s["scale"] == [1.0, 1.0, 1.0])
        socket_detail[s["name"]] = ok
        sockets_ok = sockets_ok and ok
    sockets_ok = sockets_ok and set(socket_detail) == set(want_sockets)
    raw_ok = all(r["relative_scale"] == [1.0, 1.0, 1.0] and (r["outer"] or "").startswith(ASSET)
                 for r in info["socket_array"])
    lm_builds = [b for b in info["lod_build_settings"] if isinstance(b, dict) and "error" not in b]
    lightmap_ok = (info["light_map_coordinate_index"] == 1
                   and all(isinstance(c, int) and c >= 1 for c in info["lod_source_uv_channels"])
                   and len(lm_builds) == n
                   and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0
                           and b["dst_lightmap_index"] == 1 for b in lm_builds))
    auto_ss = info.get("auto_compute_lod_screen_size")
    screen = info["lod_screen_sizes"]
    screen_ok = (isinstance(screen, list) and len(screen) == 3
                 and all(abs(a - e) < 1e-6 for a, e in zip(screen, EXPECTED_SCREEN_SIZES))
                 and EXPECTED_SCREEN_SIZES == REPORT["lod_screen_sizes"] == SPEC["screen_sizes"]
                 and auto_ss is not True)
    want_hulls = SPEC.get("hulls", 1)
    hulls_ok = (info["convex_hulls"] == want_hulls
                and all(v == 0 for k, v in info["other_collision_elems"].items() if k != "tapered_capsule_elems")
                and info["other_collision_elems"].get("tapered_capsule_elems", 0) in (0, -1))
    out = {
        "1_lod_count_and_triangles_delta_0": n == 3 and tri_delta == [0, 0, 0]
        and BLENDER_LOD_TRIANGLES == FBX_LOD_TRIANGLES,
        ("2_exactly_one_convex_hull" if want_hulls == 1 else f"2_exactly_{want_hulls}_convex_hulls"): hulls_ok,
        ("3_grip_trail_scale_1_sane_cm" if want_sockets == ["Grip", "Trail"]
         else "3_sockets_" + "_".join(s.lower() for s in want_sockets) + "_scale_1_sane_cm"): sockets_ok and raw_ok,
        "4_bounds_cm": size_ok,
        "5_screen_sizes_from_sidecar": screen_ok,
        "6_lightmap_coordinate_index_1": lightmap_ok,
    }
    detail = {"triangle_delta": tri_delta, "blender_report_lod_triangles": BLENDER_LOD_TRIANGLES,
              "blender_fbx_reimport_lod_triangles": FBX_LOD_TRIANGLES, "expected_size_cm": SPEC["size_cm"],
              "socket_detail": socket_detail, "raw_socket_array_scale_1_and_outered_to_asset": raw_ok,
              "expected_screen_sizes": EXPECTED_SCREEN_SIZES, "report_screen_sizes": REPORT["lod_screen_sizes"],
              "spec_screen_sizes": SPEC["screen_sizes"],
              "lod_bands_ok": [lo <= t <= hi for t, (lo, hi) in zip(info["lod_triangles"], LOD_BANDS)]}
    return out, detail
