#!/usr/bin/env python
"""Rebuild the shuriken pack: Assets/Shuriken.blend FROM SCRATCH with every listed form.

Scripts are the source of truth: the .blend is never patched incrementally.  Each form
lands in its own collection, exports its own FBX (one form per FBX: study 4 - only the
first mesh's custom collision imports from a multi-mesh file) with its .sockets.json
sidecar, renders its own gallery images with the other forms hidden, and writes its own
JSON report; the run also writes WorkFiles/shuriken/pack_report.json.

Forms are discovered from Scripts/shuriken/build_<form>.py files that define ``FORM``
(a shuriken_lib.Form: a spec plus its generator hook, shuriken_lib.hooks.FormGeometry; a
radial star without one runs RadialGeometry, the senban brings plate.SquarePlateGeometry).
``--list`` prints what is available.

HEADLESS ONLY:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate [options]

Exit code 0 when every form passed qa_check, every LOD landed in its study 4 band, the
cross-LOD UV gate passed and (when rendered) the render gates passed.  Blender only
propagates a Python exception as a non-zero exit with ``--python-exit-code N``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import VERSION, add_common_args, blender_argv, build_pack, discover_forms  # noqa: E402
from shuriken_lib import options_from_args, report_passed, summary, write_report  # noqa: E402
from shuriken_lib.pack import DEFAULT_EXPORT_DIR, DEFAULT_REPORT_DIR, PACK_REPORT_NAME  # noqa: E402
from shuriken_lib.render import pack_consistency  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="build_pack.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forms", default="all",
                        help="comma-separated form names, in build order (default: all discovered)")
    parser.add_argument("--list", action="store_true", help="print the available forms and exit")
    parser.add_argument("--export-dir", default=str(DEFAULT_EXPORT_DIR),
                        help="FBX + sidecar directory; each form writes <mesh name>.fbx")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR),
                        help="per-form <form>_report.json and pack_report.json")
    add_common_args(parser)
    return parser.parse_args(blender_argv(argv))


def main() -> int:
    args = parse_args()
    available = discover_forms()
    if args.list:
        print(json.dumps({name: {"mesh": form.spec.mesh_name, "points": form.spec.points,
                                 "geometry": getattr(form.geometry, "kind", "radial_star"),
                                 "script": form.module_path} for name, form in available.items()},
                         indent=2))
        return 0
    wanted = list(available) if args.forms.strip().lower() == "all" else \
        [name.strip() for name in args.forms.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in available]
    if unknown or not wanted:
        print(f"ERROR: unknown form(s) {unknown}; available: {sorted(available)}")
        return 2
    forms = [available[name] for name in wanted]
    options = options_from_args(args)

    started = time.time()
    reports = build_pack(forms, options)
    pack = {
        "pack": "Shuriken",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "library_version": VERSION,
        "blend": str(Path(options.blend)),
        "forms": wanted,
        "results": {},
        "seconds": None,
    }
    for form in forms:
        report = reports[form.name]
        path = options.report_path(form)
        write_report(report, path)
        pack["results"][form.name] = {
            "asset": report["asset"],
            "collection": form.spec.mesh_name[len("SM_"):],
            "report": str(path),
            "fbx": report.get("fbx"),
            "sidecar": report.get("sockets_sidecar"),
            "renders": report["renders"],
            "textures": (report.get("textures") or {}).get("maps"),
            "lod_triangles": report["lod_triangles"],
            "lod_screen_sizes": report.get("lod_screen_sizes"),
            "lod_bands_ok": report["lod_bands_ok"],
            "gates": report.get("gates"),
            "render_gates": report.get("render_gates"),
            "fbx_sha256": (report.get("export_sha256") or {}).get("fbx"),
            "engine_check_status": (report.get("engine_check") or {}).get("status"),
            "lod1_max_surface_deviation_mm": (report.get("lod1_is_distinct") or {}).get("max_surface_deviation_mm"),
            "symmetry_max_deviation_mm": report["symmetry"]["max_deviation_mm"],
            "mass_g": report["measured"]["mass_g"],
            "outline_mass_g": report["measured"].get("outline_mass_g"),
            "ground_mass_g": report["measured"].get("ground_mass_g"),
            "grind": {k: (report["measured"].get("grind") or {}).get(k) for k in
                      ("grind_angle_deg", "edge_land_mm", "tip_radius_mm", "tip_edge_height_mm")},
            "physics_mass_kg_override": (report.get("physics") or {}).get("mass_kg_override"),
            "qa_passed": report["qa"]["passed"],
            "qa_checks": len(report["qa"]["checks"]),
            "passed": report_passed(report),
        }
    # The forms against each other (STYLE_TARGET.md, gallery consequence): one rig, one product line.
    pack["pack_consistency"] = pack_consistency(reports)
    pack["passed"] = all(result["passed"] for result in pack["results"].values()) and (
        pack["pack_consistency"]["passed"] or not any(r["renders"] for r in pack["results"].values()))
    pack["seconds"] = round(time.time() - started, 2)
    write_report(pack, Path(options.report_dir) / PACK_REPORT_NAME)

    print("=== SHURIKEN PACK REPORT ===")
    for form in forms:
        print(json.dumps(summary(reports[form.name]), indent=2))
    print(json.dumps({k: v for k, v in pack.items() if k != "results"}, indent=2))
    print("=== END REPORT ===")
    return 0 if pack["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
