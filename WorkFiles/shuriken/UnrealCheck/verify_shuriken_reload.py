"""Pass 2 of 2: reload the asset pass 1 saved, in a FRESH commandlet process.

ASSET_GUIDELINES 6.5: an assertion made in the process that did the write proves
nothing about what reached disk. This process imports nothing; it loads the saved
Static Mesh off disk and evaluates the acceptance gates.
"""
import json
import sys
import traceback
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CHECK_DIR = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck"
SOURCE = CHECK_DIR / "import_report.json"
REPORT = CHECK_DIR / "reload_report.json"
if str(CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(CHECK_DIR))

from verify_shuriken_import import inspect, EXPECTED_LOD_TRIS  # noqa: E402

ASSET = "/Game/ShurikenCheck/SM_Shuriken_FourPoint"
TOL_CM = 0.01


def gate(report, name, ok, detail):
    report["gates"].append({"gate": name, "pass": bool(ok), "detail": detail})


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": ASSET, "gates": []}
    try:
        asset_path = ASSET
        if SOURCE.is_file():
            asset_path = json.loads(SOURCE.read_text(encoding="utf-8")).get("asset_path", ASSET)
        report["asset"] = asset_path
        mesh = unreal.load_asset(asset_path)
        report["exists"] = isinstance(mesh, unreal.StaticMesh)
        gate(report, "asset_exists_on_disk", report["exists"], f"load_asset({asset_path}) -> {type(mesh).__name__}")
        if not report["exists"]:
            raise RuntimeError("asset did not reload")
        info = inspect(mesh)
        report["reloaded"] = info

        # 1. LOD count and per-LOD triangles
        gate(report, "lod_count_3", info.get("num_lods") == 3, f"num_lods={info.get('num_lods')}")
        gate(report, "lod_triangles_match_build",
             info.get("lod_triangles") == EXPECTED_LOD_TRIS,
             f"unreal={info.get('lod_triangles')} blender={EXPECTED_LOD_TRIS}")
        tris = info.get("lod_triangles") or []
        gate(report, "lod_triangles_descending", all(a > b for a, b in zip(tris, tris[1:])), f"{tris}")
        gate(report, "lod0_within_budget_2500", bool(tris) and tris[0] <= 2500, f"LOD0={tris[0] if tris else None}")

        # 2. Convex collision present, exactly one, nothing auto-generated
        gate(report, "convex_hull_count_is_1", info.get("convex") == 1, f"convex={info.get('convex')}")
        gate(report, "no_auto_generated_primitives",
             info.get("box") == 0 and info.get("sphere") == 0 and info.get("sphyl") == 0,
             f"box={info.get('box')} sphere={info.get('sphere')} sphyl={info.get('sphyl')}")

        # 3. Sockets persisted with the sidecar transforms
        sockets = {s["name"]: s for s in info.get("sockets", [])}
        gate(report, "socket_Grip_persisted", "Grip" in sockets, f"sockets={sorted(sockets)}")
        gate(report, "socket_Trail_persisted", "Trail" in sockets, f"sockets={sorted(sockets)}")
        for nm, want_loc in (("Grip", [0.7778, -0.7778, 0.0]), ("Trail", [0.0, 0.0, 0.0])):
            s = sockets.get(nm)
            if s is None:
                gate(report, f"socket_{nm}_location_cm", False, "socket missing")
                gate(report, f"socket_{nm}_scale_is_1", False, "socket missing")
                continue
            close = all(abs(a - b) <= TOL_CM for a, b in zip(s["location_cm"], want_loc))
            gate(report, f"socket_{nm}_location_cm", close, f"got={s['location_cm']} want={want_loc}")
            gate(report, f"socket_{nm}_scale_is_1", s["scale"] == [1.0, 1.0, 1.0],
                 f"scale={s['scale']} (100 would be the FBX unit-scale trap)")
        grip = sockets.get("Grip")
        if grip:
            r = (grip["location_cm"][0] ** 2 + grip["location_cm"][1] ** 2) ** 0.5
            gate(report, "socket_Grip_on_hub_rim_1.1cm", abs(r - 1.1) <= 0.02,
                 f"radius={round(r, 4)} cm, hub radius is 1.1 cm")

        # 4. Bounds: the scale gate
        size = info.get("size_cm") or []
        if len(size) == 3:
            gate(report, "bounds_across_9.7cm", abs(size[0] - 9.7) <= 0.05 and abs(size[1] - 9.7) <= 0.05,
                 f"x={size[0]} y={size[1]} cm")
            gate(report, "bounds_thickness_0.3cm", abs(size[2] - 0.3) <= 0.01, f"z={size[2]} cm")
            mn, mx = info.get("bounds_min_cm"), info.get("bounds_max_cm")
            centred = all(abs(a + b) <= 0.01 for a, b in zip(mn, mx))
            gate(report, "pivot_at_geometric_centre", centred, f"min={mn} max={mx}")
        else:
            gate(report, "bounds_across_9.7cm", False, "bounds unreadable")

        # 5. Lightmap UVs
        idx = info.get("lightmap_coord_index")
        chans = info.get("lod_uv_channels")
        gate(report, "lightmap_coord_index_is_1", idx == 1, f"light_map_coordinate_index={idx}")
        gate(report, "uv1_generated_on_every_lod",
             isinstance(chans, list) and bool(chans) and all(c >= 2 for c in chans),
             f"uv channels per LOD={chans}")
        report["lightmap_resolution"] = info.get("lightmap_resolution")
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
        gate(report, "script_completed", False, report["error"][-400:])
    report["gates_passed"] = sum(1 for g in report["gates"] if g["pass"])
    report["gates_total"] = len(report["gates"])
    report["all_passed"] = report["gates_passed"] == report["gates_total"]
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_RELOAD " + json.dumps(report, default=str)[:6000])
    unreal.log("SHURIKEN_RELOAD_DONE " + str(REPORT))


if __name__ == "__main__":
    main()
