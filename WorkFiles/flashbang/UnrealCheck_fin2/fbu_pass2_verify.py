"""Pass 2: a FRESH process reloads the saved assets and gates them against the build report and the sidecars:
LOD triangles, hull counts, the 5 sockets at scale 1 equal to the sidecar (assembled + body), screen sizes,
lightmap index 1, slot counts, Nanite off, the exact bytes, plus the plan-11 checks: (3) the PullRing / Lever at
their sockets with identity rebuild the assembled LOD0's vertices, (4) +100 deg pitch in the lever's socket frame
swings its tip outward (+X)."""
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealCheck_fin2")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import fbu_common as C  # noqa: E402

rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "meshes": {}, "gates": {}}
G = rep["gates"]
try:
    loaded = {}
    for key, name in C.MESHES.items():
        mesh = unreal.load_asset(f"{C.DEST}/{name}")
        if mesh is None:
            rep["meshes"][key] = {"error": "did not load"}
            G[f"{key}_loads"] = False
            continue
        loaded[key] = mesh
        info = C.inspect(mesh)
        side = json.loads((C.EXP / f"{name}.sockets.json").read_text(encoding="utf-8"))
        exp_tri = C.REPORT["measure"][key]["triangles"]
        info["expected_triangles"] = exp_tri
        rep["meshes"][key] = info
        G[f"{key}_lod_triangles"] = info["lod_triangles"] == exp_tri
        G[f"{key}_hulls"] = info["convex_hulls"] == C.HULLS[key]
        G[f"{key}_slots"] = len(info["material_slots"]) == C.SLOTS[key]
        G[f"{key}_nanite_off"] = info["nanite_enabled"] is False
        sub = C.subsystem()
        info["uv_channels"] = [C.safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(info["num_lods"])]
        # FINALISE: ASSET_GUIDELINES 6.5 - Generate Lightmap UVs ON (as the pack importer); the lightmap is UV index 1
        G[f"{key}_lightmap_generated_index_1"] = bool(
            info["light_map_coordinate_index"] == 1
            and all(isinstance(b, dict) and b.get("generate_lightmap_u_vs") for b in info["lod_build_settings"])
            and all(c == 2 for c in info["uv_channels"]))
        ss = side.get("lod_screen_sizes")
        G[f"{key}_screen_sizes"] = isinstance(info["lod_screen_sizes"], list) and len(info["lod_screen_sizes"]) == 3 \
            and all(abs(a - b) < 1e-5 for a, b in zip(info["lod_screen_sizes"], ss))
        G[f"{key}_exact_bytes"] = C.sha256(C.EXP / f"{name}.fbx") == C.REPORT["export"][key]["sha256"]["fbx"]
        exp_s = {r["socket"]: r for r in side["sockets"]}
        ok = set(s["name"] for s in info["sockets"]) == set(exp_s)
        for s in info["sockets"]:
            e = exp_s.get(s["name"])
            if e is None:
                ok = False
                continue
            ok = ok and all(abs(a - b) < 1e-3 for a, b in zip(s["location_cm"], e["location_cm"]))
            er = e["rotation_deg"]
            for got, want in zip(s["rotation"], (er["roll"], er["pitch"], er["yaw"])):
                ok = ok and abs((got - want + 180) % 360 - 180) < 0.05
            ok = ok and s["relative_scale"] == [1.0, 1.0, 1.0] and (s["outer"] or "").startswith(f"{C.DEST}/{name}")
        G[f"{key}_sockets_match_sidecar"] = ok
    if all(k in loaded for k in C.MESHES):
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(loaded["body"])
        A = C.lod_positions_cm(loaded["assembled"])
        res = {}
        for key, sock in (("pullring", "Pin"), ("lever", "LeverHinge")):
            T = comp.get_socket_transform(sock, unreal.RelativeTransformSpace.RTS_COMPONENT)
            worst = 0.0
            for p in C.lod_positions_cm(loaded[key]):
                w = T.transform_location(unreal.Vector(*p))
                d = min((w.x - a[0]) ** 2 + (w.y - a[1]) ** 2 + (w.z - a[2]) ** 2 for a in A)
                worst = max(worst, math.sqrt(d))
            res[key] = {"worst_cm": round(worst, 6)}
        rep["assembly_identity_engine"] = res
        G["assembly_identity_0.01mm"] = all(v["worst_cm"] <= 0.001 for v in res.values())
        L = C.lod_positions_cm(loaded["lever"])
        tip = min(L, key=lambda p: p[2])
        t2 = unreal.Rotator(roll=0.0, pitch=100.0, yaw=0.0).quaternion().rotate_vector(unreal.Vector(*tip))
        rep["lever_open_engine"] = {"tip_cm": [round(v, 4) for v in tip], "after_plus100_pitch_cm": C.vec(t2)}
        G["lever_positive_pitch_swings_out"] = bool(t2.x > tip[0])
    rep["passed_all"] = bool(G) and all(G.values())
except Exception:  # noqa: BLE001
    rep["error"] = traceback.format_exc()
(C.HERE / "pass2.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
unreal.log("FBU_PASS2_DONE")
