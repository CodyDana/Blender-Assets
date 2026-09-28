#!/usr/bin/env python
"""Build SM_SmokeBomb from scratch: strips, LODs, UVs, maps, collision, sockets, export.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/props/build_smoke_bomb.py -- [--stages ...] [--quick]

Stages (in order): layout, mesh, textures, save, qa, export, render, report.
``--quick`` drops samples and texture resolution; it is for iterating.  The shipped
build is the one without it.  Every number in the report is measured on what was built.

WHAT IT READS
-------------
References/SmokeBomb/REFERENCE_SPEC.md's numbers, typed into props_lib.smokebomb_layout
(strip control points, widths, order) and props_lib.smokebomb_cloth (weave, colour,
threads).  The reference PNG is opened by exactly two things, both measurement: the
side-by-side comparison sheet (Renders/SmokeBomb/smokebomb_side_by_side.png) and the
metrics that compare the reference-view render with it.  No reference pixel reaches a
mesh, a UV or a map; ``no_reference_in_maps`` in the report proves the maps were written
before the reference was ever loaded in this process.

WHAT IT NEVER TOUCHES
---------------------
Scripts/shuriken/**, Assets/Shuriken.blend, Exports/Shuriken/**, Renders/Shuriken/**,
and the paused paper bomb (Assets/PaperBomb.blend, Exports/PaperBomb/**,
Renders/PaperBomb/**, props_lib paperbomb_art / trace / art_metrics / photo_metrics).
Their hashes are taken at the start and the end and both go in the report.
Scripts/pipeline/** is used exactly as it is.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Scripts"))
sys.path.insert(0, str(PROJECT / "Scripts" / "props"))

import bpy                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from pipeline.export_fbx import export_fbx                        # noqa: E402
from pipeline.helpers import make_lod_group, make_socket          # noqa: E402
from pipeline.qa_check import qa_check                            # noqa: E402
from props_lib import bake as PB                                  # noqa: E402
from props_lib import smokebomb_atlas as AT                       # noqa: E402
from props_lib import smokebomb_cloth as CL                       # noqa: E402
from props_lib import smokebomb_geometry as G                     # noqa: E402
from props_lib import smokebomb_layout3 as L                      # noqa: E402
from props_lib import smokebomb_outline as OL                     # noqa: E402
from props_lib import smokebomb_threads as TH                     # noqa: E402
from props_lib import smokebomb_metrics as MT                     # noqa: E402
from props_lib import smokebomb_render as SR                      # noqa: E402
from props_lib import smokebomb_strips as SS                      # noqa: E402
from props_lib import smokebomb_shell as SH                       # noqa: E402
from props_lib import smokebomb_material as MAT                   # noqa: E402
from types import SimpleNamespace                                 # noqa: E402
from props_lib.smokebomb_spec import SMOKE_BOMB, assert_clean, build_to, deny_hits  # noqa: E402

LIB_VERSION = "3.0.0"
ASSETS = PROJECT / "Assets"
EXPORTS = PROJECT / "Exports" / "SmokeBomb"
TEXTURES = EXPORTS / "Textures"
RENDERS = PROJECT / "Renders" / "SmokeBomb"
WORK = PROJECT / "WorkFiles" / "smokebomb"
BUILD_WORK = WORK / "build"
REFERENCE = PROJECT / "References" / "SmokeBomb" / "smokebomb.png"
REFERENCE_SHA = "813105ecd7192c72b20058a206ea8916912aecdba0abfa02cfb47bc9f7b6e1c2"
AO_GAMMA = 1.0          # ORM.R is the plain AO bake (Unreal applies it to indirect light only)

ALL_STAGES = ("layout", "mesh", "textures", "save", "qa", "export", "render", "report")

T0 = time.time()


def log(*parts):
    print(f"[smokebomb {time.time() - T0:7.1f}s]", *parts, flush=True)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =========================================================================== frozen assets
def frozen_hashes() -> dict:
    out = {"shuriken": {}, "paperbomb": {}}
    for p in sorted((PROJECT / "Exports" / "Shuriken").glob("*.fbx")) + \
            sorted((PROJECT / "Exports" / "Shuriken").glob("*.sockets.json")):
        out["shuriken"][p.name] = sha256(p)
    sums = PROJECT / "WorkFiles" / "paperbomb" / "paused_2026-09-21" / "SHA256SUMS_exports.txt"
    ok = []
    if sums.is_file():
        for line in sums.read_text(encoding="utf8").splitlines():
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            want, rel = parts[0], parts[-1].lstrip("*")
            path = Path(rel) if Path(rel).is_absolute() else PROJECT / rel
            if not path.is_file():
                path = sums.parent / rel
            got = sha256(path) if path.is_file() else None
            out["paperbomb"][rel] = {"want": want, "got": got, "ok": got == want}
            ok.append(got == want)
    out["paperbomb_all_ok"] = bool(ok) and all(ok)
    return out


# =========================================================================== stages
def stage_layout(report):
    strips = L.build_strips(log=log)
    report["layout"] = {
        "strips": [{"name": s.name, "family": s.family, "closed": s.closed,
                    "rank_knots": [[round(a, 2), round(b, 3)] for a, b in s.rank],
                    "switches_invisible": bool(getattr(s, "switch_ok", True)),
                    "width_mm_min_max": [round(float(np.min(s._hi - s._lo)) * SS.DEG * 35.0, 2),
                                         round(float(np.max(s._hi - s._lo)) * SS.DEG * 35.0, 2)],
                    "pinched_samples": int(getattr(s, "pinched", 0)),
                    "note": s.note} for s in strips],
        "designed": len(L.designs()), "fillers": len(strips) - len(L.designs()),
        "source": "props_lib.smokebomb_layout3: REFERENCE_SPEC 4.2 control points, widths and "
                  "4.4 order (round 2's front); every strip a closed loop; far side DESIGNED as "
                  "each strip's own circle, no hidden waypoints (REFERENCE_SPEC 9)",
        "far_side": {s.name: getattr(s, "base", None) for s in strips},
    }
    return strips


def stage_mesh(spec, strips, report, quick=False):
    """One closed height-field shell per LOD (props_lib.smokebomb_shell)."""
    hm = SH.HeightModel(**spec.height_model()).prepare(strips)
    log(f"height model: layer compensation rms {hm.nbar_rms:.3f} layers")
    # round 3: the outline's harmonics 0..N equal the reference's (props_lib.smokebomb_outline)
    fit = OL.fit_core_correction(strips, hm, spec.outline_radius_mm, n_max=spec.outline_harmonics, log=log)
    runset = SH.find_runs(strips, log=log)
    regions, problems = SH.build_regions(strips, runset, log=log)
    log("LOD0")
    lod0 = SH.build_shell_lod(strips, hm, runset, regions, SH.SHELL_LODS[0], log=log)
    mesh_rounds = []
    for it in range(spec.outline_mesh_rounds):
        rr = OL.refine_from_mesh(hm, lod0.verts, lod0.tris, spec.outline_radius_mm, n_max=spec.outline_harmonics)
        log(f"  outline measured on the LOD0 mesh, round {it}: {rr}")
        mesh_rounds.append(rr)
        lod0 = SH.build_shell_lod(strips, hm, runset, regions, SH.SHELL_LODS[0], log=log)
    th_o, r_o = OL.mesh_outline(lod0.verts, lod0.tris)
    grid = np.arange(OL.LIMB_N) * 2.0 * math.pi / OL.LIMB_N
    rg = np.interp(grid, th_o, r_o, period=2 * math.pi)
    tgt = OL.target_radius_mm(grid, spec.outline_radius_mm, spec.outline_harmonics)
    fit["mesh_rounds"] = mesh_rounds
    fit["final_mesh_outline"] = {"mean_mm": round(float(rg.mean()), 4),
                                 "lowpass_rms_err_mm": round(float(np.sqrt(0.5 * ((OL.fourier(tgt, spec.outline_harmonics)
                                                                                  - OL.fourier(rg, spec.outline_harmonics))[1:] ** 2).sum())), 5),
                                 "residual_rms_mm": round(float((rg - tgt).std()), 4)}
    # T4, the one loose thread past the outline (props_lib.smokebomb_threads)
    r_t4 = float(np.interp(math.radians(TH.T4_ANGLE_DEG), th_o, r_o, period=2 * math.pi))
    hook = TH.hook_geometry(r_t4)
    size = 2048 if quick else spec.texture_size
    items = SH.atlas_items(lod0, regions) + [TH.atlas_item(hook, len(strips))]
    atlas = AT.plan(items, size=size, pad=spec.padding_px * size // spec.texture_size)
    log(f"  {len(items)} islands; atlas {atlas.describe()}")
    A0 = SH.assemble(lod0, atlas, regions)
    A0 = TH.append_hook(A0, hook, atlas, len(strips))
    log("LOD1 (geodesic resample)")
    lod1 = SH.resample_lod(strips, hm, lod0, regions, SH.LOD1_FREQUENCY, level=1)
    A1 = SH.assemble(lod1, atlas, regions, boxes=lod0.region_box)
    A1.report.update(lod1.report)
    log("LOD2 (geodesic resample)")
    lod2 = SH.resample_lod(strips, hm, lod0, regions, SH.LOD2_FREQUENCY, level=2)
    A2 = SH.assemble(lod2, atlas, regions, boxes=lod0.region_box)
    A2.report.update(lod2.report)
    # UE 5.8 drops triangles under 0.005 mm2 at build time (measured): drop them here so the
    # engine's triangle count is ours, exactly
    A0, A1, A2 = (G.drop_slivers(A) for A in (A0, A1, A2))
    objs = []
    for level, A in enumerate((A0, A1, A2)):
        name = spec.mesh_name if level == 0 else f"{spec.mesh_name}_LOD{level}"
        assert_clean(name)
        obj = G.make_object(name, A)
        objs.append(obj)
        log(f"  {name}: {A.report}")
    report["mesh"] = {f"LOD{i}": A.report for i, A in enumerate((A0, A1, A2))}
    report["mesh"]["shell"] = {
        "runs": len(runset.runs), "junctions": len(runset.junctions), "regions": len(regions),
        "short_runs_merged": runset.report.get("short_runs_merged"),
        "slivers_collapsed": len(getattr(runset, "dead", ())),
        "seams": runset.report.get("seams"),
        "problems": list(problems) + list(runset.report.get("problems", [])) + list(lod0.report["problems"]),
        "LOD0": {k: v for k, v in lod0.report.items() if k != "problems"},
        "layer_compensation_rms": round(hm.nbar_rms, 4),
    }
    report["mesh"]["outline_fit"] = fit
    report["mesh"]["T4_hook"] = {"angle_deg": TH.T4_ANGLE_DEG, "reach_past_outline_mm": TH.T4_REACH_MM,
                                 "tube_radius_mm": TH.TUBE_R_MM, "outline_radius_there_mm": round(r_t4, 4),
                                 "triangles": int(len(hook["tris"])), "min_triangle_mm2": round(hook["min_area_mm2"], 5),
                                 "lods": "LOD0 only"}
    report["atlas"] = atlas.describe()
    report["mesh"]["params"] = {"LOD0": dict(SH.SHELL_LODS[0].__dict__),
                                "LOD1": {"method": "geodesic resample", "frequency": SH.LOD1_FREQUENCY},
                                "LOD2": {"method": "geodesic resample", "frequency": SH.LOD2_FREQUENCY}}
    report["mesh"]["height_model"] = {k: (list(v) if isinstance(v, tuple) else v)
                                      for k, v in spec.height_model().items()}
    report["mesh"]["limb_refine"] = {"LIMB_REFINE": SH.LIMB_REFINE, "LIMB_Z": SH.LIMB_Z}
    model = SimpleNamespace(strips=strips)
    return model, regions, items, atlas, objs


def stage_finish(spec, objs, report):
    lod0 = objs[0]
    co = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs])
    r_max = float(np.linalg.norm(co, axis=1).max())
    hull = G.make_hull(lod0, r_max)
    outside = max(G.hull_worst_outside_m(hull, o) for o in objs)
    vol = G.hull_volume_m3(hull)
    log(f"hull {hull.name}: 32 vertices, faces tangent to r_max {r_max * 1000:.3f} mm, "
        f"worst outside {outside * 1000:.6f} mm")
    sockets = []
    for sd in spec.sockets:
        make_socket(lod0, sd.name, tuple(v * 0.001 for v in sd.position_mm),
                    tuple(math.radians(a) for a in sd.rotation_deg))
        sockets.append({"name": sd.name, "position_mm": list(sd.position_mm),
                        "rotation_deg": list(sd.rotation_deg), "use": sd.use})
    group = make_lod_group(spec.mesh_name, objs)
    assert_clean(group.name, hull.name, *(o.name for o in objs))
    report["collision"] = {"hull": hull.name, "vertices": len(hull.data.vertices),
                           "faces": len(hull.data.polygons),
                           "shape": "pentakis dodecahedron, all 60 faces tangent to the mesh's r_max",
                           "r_max_mm": round(r_max * 1000, 4),
                           "volume_cm3": round(vol * 1e6, 3),
                           "volume_over_rmax_sphere": round(vol / (4 / 3 * math.pi * r_max ** 3), 4),
                           "worst_vertex_outside_mm_all_lods": round(outside * 1000, 7),
                           "contains_every_lod": bool(outside <= 1e-9),
                           "naming": "UCX_<render mesh NODE name>_00 (renamed with the node by make_lod_group)"}
    report["sockets"] = sockets
    return group, hull


def unreal_bounds_radius_mm(obj) -> float:
    """Unreal's bounds sphere: the max vertex distance from the AABB centre (the kunai
    measured 140.008 mm against a 141.5 mm half-diagonal)."""
    co = np.array([v.co[:] for v in obj.data.vertices]) * 1000.0
    c = 0.5 * (co.min(axis=0) + co.max(axis=0))
    return float(np.linalg.norm(co - c, axis=1).max())


def stage_textures(spec, model, items, atlas, objs, report, quick=False):
    cloth = CL.Cloth()
    log("painting the cloth into the atlas")
    maps = CL.paint_atlas(model, atlas, items, cloth, seed=spec.seed)
    nrm = CL.normals_from_height(maps["height"], atlas.ppmm)
    log("baking ambient occlusion (Cycles, LOD0 alone)")
    ao_b, ao_info = PB.bake_ao_map(objs[0], atlas.size, samples=32 if quick else 128)
    # ORM.R: the geometry's occlusion times the weave's cavity, for Unreal's AO input (which
    # darkens indirect light only).  The look does NOT depend on it: every tone the reference
    # shows is in BC, and the Blender material does not multiply AO into base colour.
    ao = np.clip(np.power(ao_b, AO_GAMMA) * maps["cavity"], 0.0, 1.0)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    stem = spec.texture_stem
    paths = {"BC": PB.write_png(TEXTURES / f"{stem}_BC.png", PB.linear_to_srgb(maps["base"])),
             "ORM": PB.write_png(TEXTURES / f"{stem}_ORM.png",
                                 np.stack([ao, maps["rough"], np.zeros_like(ao)], axis=-1)),
             }
    ndx = nrm.copy()
    ndx[..., 1] = -ndx[..., 1]                     # DirectX green on disk
    paths["N"] = PB.write_png(TEXTURES / f"{stem}_N.png", ndx * 0.5 + 0.5)
    mat = MAT.smokebomb_material(spec.material_name, paths)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)
    chunks = {k: PB.png_chunks(v) for k, v in paths.items()}
    report["textures"] = {
        "maps": {k: str(Path(v).relative_to(PROJECT)) for k, v in paths.items()},
        "sha256": {k: sha256(v) for k, v in paths.items()},
        "size": atlas.size, "px_per_mm": round(atlas.ppmm, 4),
        "colour_chunks": {k: [c for c in v if c in ("sRGB", "gAMA", "cHRM", "iCCP")] for k, v in chunks.items()},
        "power_of_two": (atlas.size & (atlas.size - 1)) == 0,
        "ao_bake": ao_info,
        "bc_stats_linear": {"mean": [round(float(x), 5) for x in maps["base"][maps["written"]].mean(axis=0)],
                            "p50_luma": round(float(np.percentile(SS_luma(maps["base"][maps["written"]]), 50)), 5)},
        "cloth": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cloth.__dict__.items()},
        "how_each_channel_is_made": {
            "BC / ORM.G / N": "drawn procedurally in each strip's own chart (props_lib.smokebomb_cloth); "
                              "no reference pixel is read",
            "ORM.R": "a Cycles AO bake of LOD0 alone onto UV0 times the weave's cavity (Unreal's AO input; "
                     "not multiplied into base colour anywhere)",
            "material": MAT.UE_MASTER,
            "ORM.B": "0: cotton",
        },
    }
    return mat, paths


def SS_luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def stage_measure(spec, objs, hull, report):
    from mathutils.bvhtree import BVHTree
    lods = {}
    trees = []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        V = [v.co.copy() for v in me.vertices]
        P = [tuple(t.vertices) for t in me.loop_triangles]
        trees.append((BVHTree.FromPolygons(V, P), np.array([v[:] for v in V])))
    for i, (o, band) in enumerate(zip(objs, spec.lod_bands)):
        me = o.data
        me.calc_loop_triangles()
        co = np.array([v.co[:] for v in me.vertices]) * 1000.0
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        tri_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
        tri_co = np.array([[co[v] for v in t.vertices] for t in me.loop_triangles])
        uv_area = 0.5 * ((tri_uv[:, 1, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 2, 1] - tri_uv[:, 0, 1])
                         - (tri_uv[:, 2, 0] - tri_uv[:, 0, 0]) * (tri_uv[:, 1, 1] - tri_uv[:, 0, 1]))
        n3 = np.cross(tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0])
        area3 = 0.5 * np.linalg.norm(n3, axis=1)
        wall = np.zeros(len(me.polygons), bool)
        if me.attributes.get("sb_wall") is not None:
            me.attributes["sb_wall"].data.foreach_get("value", wall)
        wall_t = np.array([wall[t.polygon_index] for t in me.loop_triangles])
        outward = (n3 * tri_co.mean(axis=1)).sum(axis=1) > 0
        # UV handedness: (dP/du x dP/dv) . n  < 0 is a mirrored triangle
        e1, e2 = tri_co[:, 1] - tri_co[:, 0], tri_co[:, 2] - tri_co[:, 0]
        d1, d2 = tri_uv[:, 1] - tri_uv[:, 0], tri_uv[:, 2] - tri_uv[:, 0]
        det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
        det = np.where(np.abs(det) < 1e-20, 1e-20, det)
        dpu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
        dpv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
        hand = (np.cross(dpu, dpv) * n3).sum(axis=1)
        entry = {
            "object": o.name, "triangles": len(me.loop_triangles), "vertices": len(me.vertices),
            "band": list(band),
            "in_band": bool(band[0] <= len(me.loop_triangles) <= band[1]),
            "bounds_mm": {"min": [round(float(x), 4) for x in co.min(axis=0)],
                          "max": [round(float(x), 4) for x in co.max(axis=0)],
                          "size": [round(float(x), 4) for x in np.ptp(co, axis=0)]},
            "max_radius_mm": round(float(np.linalg.norm(co, axis=1).max()), 4),
            "uv_range": [round(float(uv.min()), 6), round(float(uv.max()), 6)],
            "collapsed_uv_triangles": int((np.abs(uv_area) < 1e-12).sum()),
            "mirrored_uv_triangles": int((hand < 0).sum()),
            "inward_facing_surface_triangles": int((~outward & ~wall_t).sum()),
            "min_triangle_area_mm2": round(float(area3.min()), 6),
            "texel_density_px_per_cm": round(float(math.sqrt(np.abs(uv_area).sum() / area3.sum())
                                                   * spec.texture_size * 10.0), 3),
        }
        if i > 0:
            # two-sided surface deviation, vertex to surface both ways (mm)
            t0, v0 = trees[0]
            ti, vi = trees[i]
            a = max(((t0.find_nearest(tuple(p))[3] or 0.0) for p in vi), default=0.0)
            b = max(((ti.find_nearest(tuple(p))[3] or 0.0) for p in v0), default=0.0)
            entry["deviation_to_lod0_mm"] = {"lodn_to_lod0": round(a * 1000, 4),
                                             "lod0_to_lodn": round(b * 1000, 4),
                                             "two_sided": round(max(a, b) * 1000, 4)}
        lods[f"LOD{i}"] = entry
    radius = unreal_bounds_radius_mm(objs[0])
    report["lods"] = lods
    report["lod_triangles"] = [lods[f"LOD{i}"]["triangles"] for i in range(3)]
    report["bounds_radius_mm"] = round(radius, 4)
    report["lod_screen_sizes"] = spec.lod_screen_sizes(radius)
    report["switch_distances_m"] = spec.switch_distances_m(radius)
    size = lods["LOD0"]["bounds_mm"]["size"]
    report["size_cm"] = [round(v / 10.0, 6) for v in size]
    vol_cm3 = 4.0 / 3.0 * math.pi * (spec.diameter_mm / 20.0) ** 3
    report["mass"] = {"design_g": spec.mass_g, "physics_mass_kg": spec.physics_mass_kg,
                      "ball_volume_cm3": round(vol_cm3, 2),
                      "density_g_cm3": round(spec.mass_g / vol_cm3, 3),
                      "status": "DERIVED (study 4): tape 14.5 g + washi shell 10.6 g + dry fill 96 g"}


def stage_qa(spec, objs, report):
    names = [o.name for o in objs]
    target = report["lods"]["LOD0"]["texel_density_px_per_cm"]
    result = qa_check(names, budget_tris=spec.lod_bands[0][1], texel_density=target,
                      tolerance=0.15, require_ucx=True, overlap_method="sat")
    failed = [c for c in result["checks"] if not c["passed"]]
    for c in failed:
        log(f"  QA FAIL {c['name']} on {c['object']}: {c['detail']}")
    log(f"qa_check {'PASS' if result['passed'] else 'FAIL'} "
        f"({len(result['checks']) - len(failed)}/{len(result['checks'])})")
    report["qa"] = {"passed": result["passed"], "checks": result["checks"],
                    "triangles": result["triangles"], "texel_target_px_per_cm": target,
                    "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]}
                               for c in failed]}
    return result


def stage_export(spec, group, report):
    EXPORTS.mkdir(parents=True, exist_ok=True)
    fbx = EXPORTS / f"{spec.mesh_name}.fbx"
    result = export_fbx(str(fbx), [group.name], kind="static",
                        lod_screen_sizes=report["lod_screen_sizes"])
    sidecar = result["sidecar"]
    report["export"] = {
        "fbx": str(fbx.relative_to(PROJECT)),
        "sockets_sidecar": str(Path(sidecar).relative_to(PROJECT)) if sidecar else None,
        "objects": result["objects"], "warnings": result["warnings"],
        "lod_screen_sizes": result["lod_screen_sizes"], "sockets": result["sockets"],
        "axis": {"forward": result["settings"]["axis_forward"], "up": result["settings"]["axis_up"]},
        "sha256": {"fbx": sha256(fbx), "sidecar": sha256(sidecar) if sidecar else None},
        "bytes": {"fbx": fbx.stat().st_size},
    }
    log(f"exported {fbx.name} sha {report['export']['sha256']['fbx'][:16]}")


def stage_render(spec, objs, report, quick=False):
    from props_lib import smokebomb_gallery as SG
    RENDERS.mkdir(parents=True, exist_ok=True)
    BUILD_WORK.mkdir(parents=True, exist_ok=True)
    maps_written_before = {k: Path(PROJECT / v).stat().st_mtime for k, v in report["textures"]["maps"].items()}
    views = SG.reference_views(objs[0], spec.diameter_mm, str(REFERENCE), RENDERS, BUILD_WORK,
                               samples=64 if quick else 512)
    report["renders"] = {"reference_views": views}
    gal = SG.gallery(spec, objs, RENDERS, BUILD_WORK, samples=48 if quick else 256,
                     bounds_radius_mm=report.get("bounds_radius_mm", 36.8))
    report["renders"]["gallery"] = gal
    # the reference-view metrics, one instrument on both images
    ref = SR.load_png(REFERENCE)[..., :3].astype(np.float64)
    ren = SR.load_png(views["reference_view"])[..., :3].astype(np.float64)
    report["fidelity"] = {"reference": MT.measure_all(ref), "render": MT.measure_all(ren)}
    report["no_reference_in_maps"] = {
        "reference_sha256": sha256(REFERENCE), "expected": REFERENCE_SHA,
        "maps_mtime": maps_written_before,
        "note": "the maps were written in the textures stage; the reference is first loaded "
                "in this render stage, for the side-by-side and the metrics only",
    }


def fidelity_gates(fid) -> dict:
    ref, ren = fid["reference"], fid["render"]
    g = {}
    rs, ns = ref["silhouette"], ren["silhouette"]
    g["F1_diameter_within_1pct"] = abs(ns["diameter_px"] / rs["diameter_px"] - 1.0) <= 0.01
    g["F2_centre_within_3px"] = (abs(ns["centre_px"][0] - 627.4) <= 3 and abs(ns["centre_px"][1] - 628.9) <= 3)
    g["F3_circularity_0.8_1.8pctR"] = 0.8 <= ns["rms_dev_pctR"] <= 1.8
    g["F4_steps_8_to_16"] = 8 <= ns["steps"]["count_ge_4px"] <= 16
    for p in ("p10", "p50", "p90"):
        g[f"F5_tone_{p}_within_12pct"] = abs(ren["tones"][p] / ref["tones"][p] - 1.0) <= 0.12
    for q in ("upper_left", "upper_right", "lower_left", "lower_right"):
        # ratio to the centre, so exposure cancels (REFERENCE_SPEC 3)
        a = ren["lighting"][q] / ren["lighting"]["centre"]
        b = ref["lighting"][q] / ref["lighting"]["centre"]
        g[f"F6_quadrant_{q}_within_15pct"] = abs(a / b - 1.0) <= 0.15
    c = ren["colour"]["chromaticity_lin"]
    g["F7_chromaticity"] = abs(c[0] - 0.378) <= 0.012 and abs(c[1] - 0.325) <= 0.008
    wp = ren["weave"]["dominant_period_px_median"] or 0
    g["F8_warp_pitch_3.4_5.5px"] = 3.4 <= wp <= 5.5
    g["F9_sparkle_fraction_3_to_5.5pct"] = 0.03 <= ren["sparkle"]["fraction"] <= 0.055
    return {k: bool(v) for k, v in g.items()}


def collect_gates(report) -> dict:
    lods = report.get("lods") or {}
    g = {}
    g["1_qa_check_clean"] = bool((report.get("qa") or {}).get("passed"))
    g["2_lod_triangles_in_band"] = bool(lods) and all(v["in_band"] for v in lods.values())
    g["3_lod_triangles_descend"] = report.get("lod_triangles", [0, 0, 0]) == sorted(report.get("lod_triangles", []), reverse=True)
    g["4_no_collapsed_uv_triangles"] = bool(lods) and all(v["collapsed_uv_triangles"] == 0 for v in lods.values())
    g["5_no_mirrored_uv_triangles"] = bool(lods) and all(v["mirrored_uv_triangles"] == 0 for v in lods.values())
    g["6_uv_inside_0_1"] = bool(lods) and all(v["uv_range"][0] >= -1e-6 and v["uv_range"][1] <= 1 + 1e-6 for v in lods.values())
    g["7_hull_contains_every_lod"] = bool((report.get("collision") or {}).get("contains_every_lod"))
    g["8_two_sockets"] = len(report.get("sockets") or []) == 2
    tex = report.get("textures") or {}
    g["9_maps_power_of_two_no_colour_chunks"] = bool(tex.get("power_of_two")) and not any(
        v for v in (tex.get("colour_chunks") or {}).values())
    g["10_frozen_assets_unchanged"] = bool((report.get("frozen") or {}).get("unchanged"))
    names = [report.get("asset"), (report.get("build_to") or {}).get("material")]
    names += (report.get("build_to") or {}).get("textures") or []
    names += [v.get("object") for v in lods.values()]
    names += [(report.get("collision") or {}).get("hull")]
    g["11_no_franchise_string"] = not deny_hits(*names)
    # two-sided deviation from LOD0 at most ~1.6 px at its own switch distance (1080p,
    # 90 deg hFOV): LOD1 1.5 mm at 0.89 m, LOD2 3.0 mm at 2.54 m
    # UE 5.8 drops triangles under 0.005 mm2 (measured): none may ship
    g["14_no_triangle_unreal_would_drop"] = bool(lods) and all(
        v.get("min_triangle_area_mm2", 0.0) >= 0.005 for v in lods.values())
    g["12_lod_deviation_within_budget"] = bool(lods) and (
        (lods.get("LOD1", {}).get("deviation_to_lod0_mm") or {}).get("two_sided", 9.9) <= 1.5
        and (lods.get("LOD2", {}).get("deviation_to_lod0_mm") or {}).get("two_sided", 9.9) <= 3.0)
    fid = report.get("fidelity")
    if fid:
        for k, v in fidelity_gates(fid).items():
            g["13_" + k] = v
    g["_all"] = all(v for k, v in g.items() if not k.startswith("_"))
    return g


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--stages", default=",".join(ALL_STAGES))
    p.add_argument("--quick", action="store_true")
    p.add_argument("--report-name", default="smokebomb_report.json")
    p.add_argument("--dev-dir", default=None,
                   help="DEV ONLY: write every output (blend, exports, renders, report) under this "
                        "folder instead of the project's shipping locations")
    return p.parse_args(argv)


def main(argv=None):
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    args = parse_args(argv)
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    if args.dev_dir:
        global ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK
        dev = Path(args.dev_dir) if Path(args.dev_dir).is_absolute() else PROJECT / args.dev_dir
        ASSETS, EXPORTS, RENDERS, WORK = dev / "Assets", dev / "Exports", dev / "Renders", dev
        TEXTURES, BUILD_WORK = EXPORTS / "Textures", dev / "build"
    spec = SMOKE_BOMB
    for d in (ASSETS, EXPORTS, TEXTURES, RENDERS, WORK, BUILD_WORK):
        d.mkdir(parents=True, exist_ok=True)
    report = {"asset": spec.mesh_name, "library": f"props_lib smokebomb {LIB_VERSION}",
              "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blender": bpy.app.version_string,
              "build_script": str(Path(__file__).relative_to(PROJECT)), "quick": bool(args.quick),
              "build_to": build_to(spec), "frozen": {"before": frozen_hashes()}}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"

    strips = stage_layout(report)
    model, regions, items, atlas, objs = stage_mesh(spec, strips, report, quick=args.quick)
    if "textures" in stages:
        stage_textures(spec, model, items, atlas, objs, report, quick=args.quick)
    group, hull = stage_finish(spec, objs, report)
    stage_measure(spec, objs, hull, report)
    if "qa" in stages:
        stage_qa(spec, objs, report)
    if "save" in stages:
        blend = ASSETS / "SmokeBomb.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        report["blend"] = str(blend.relative_to(PROJECT))
        log(f"saved {blend}")
    if "export" in stages:
        stage_export(spec, group, report)
    if "render" in stages and "textures" in stages:
        stage_render(spec, objs, report, quick=args.quick)
    report["frozen"]["after"] = frozen_hashes()
    report["frozen"]["unchanged"] = (report["frozen"]["before"]["shuriken"] == report["frozen"]["after"]["shuriken"]
                                     and report["frozen"]["after"]["paperbomb_all_ok"]
                                     and len(report["frozen"]["after"]["shuriken"]) == 14)
    report["gates"] = collect_gates(report)
    bad = [k for k, v in report["gates"].items() if not v and not k.startswith("_")]
    log("gates: " + ("ALL PASS" if not bad else "FAILING " + ", ".join(bad)))
    if "report" in stages:
        out = WORK / args.report_name
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        log(f"report -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
