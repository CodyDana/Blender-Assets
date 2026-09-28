"""Summarise the Snow Flower v4 Unreal verification into verification_summary.json."""
import hashlib
import json
from pathlib import Path

H = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck")
P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")


def ld(n):
    return json.loads((H / n).read_text(encoding="utf-8"))


p1, p2, p3, rt = ld("pass1.json"), ld("pass2.json"), ld("pass3.json"), ld("roundtrip_compare.json")
ti, tv, tc, uv1 = ld("props_textures_import.json"), ld("props_textures_verify.json"), ld("tex_composite.json"), ld("uv1_overlap.json")
rep = json.loads((P / "WorkFiles/SnowFlower/v4/sword_report.json").read_text(encoding="utf-8"))
fbx = P / "Exports/SnowFlower/v4/SM_SnowFlower.fbx"
sha = hashlib.sha256(fbx.read_bytes()).hexdigest()
logs = {n: sum(1 for l in (H / f"{n}.log").read_text(errors="ignore").splitlines() if "Warning:" in l or "Error:" in l)
        for n in ("pass1", "tex_import", "tex_composite", "tex_verify", "pass2", "pass3")}
# final pass 2026-09-27: the v4 Textures folder also holds the sheath maps (11 top-level PNGs); every one is imported
N_PNG = len(list(Path(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/SnowFlower/v4/Textures").glob("*.png")))
g = dict(p2.get("gates", {}))
g["11_hulls_contain_every_lod0_vertex_in_engine_space"] = bool(rt.get("hull", {}).get("contains_lod0"))
g["13_roundtrip_triangles_and_positions_exact"] = all(
    v.get("shipped_triangles") == v.get("unreal_triangles") and v.get("positions_two_sided_cm", 1) <= 1e-3
    and v.get("shipped_triangles_absent_in_unreal", 1) == 0 for v in rt["lods"].values())
g["14_roundtrip_hull_vertices_1e-4cm"] = rt.get("hull", {}).get("vertices_two_sided_cm", 1) <= 1e-4
g["15_texture_import_and_fresh_verify"] = bool(ti["passed"] and tv["passed"] and tv["processed"] == tv["expected"] == N_PNG)
g["16_zero_warning_error_lines_all_passes"] = all(v == 0 for v in logs.values())
g["17_same_bytes_everywhere"] = (sha == rep["export"]["sha256"]["fbx"] == p1["fbx_sha256"] == p2["fbx_sha256"]
                                 == p3.get("shipped_fbx_sha256"))
g["18_uv1_zero_overlap_1024_every_lod"] = len(uv1) == 3 and all(v.get("overlap_texels_1024") == 0 for v in uv1.values())
g["19_orm_composite_set"] = bool(tc.get("passed"))
out = {"engine": p2.get("engine"), "project": "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject",
       "content_path": p2.get("asset"), "fbx_sha256": sha, "sidecar_sha256": p2.get("sidecar_sha256"),
       "warning_error_lines": logs, "gates": g, "verified": all(g.values()),
       "lod_triangles": p2.get("lod_triangles"), "lod_screen_sizes": p2.get("lod_screen_sizes"),
       "size_cm": p2.get("size_cm"), "bounds_sphere_radius_cm": p2.get("bounds_sphere_radius_cm"),
       "sockets": p2.get("sockets"), "convex_hulls": p2.get("convex_hulls"), "material_slots": p2.get("material_slots"),
       "hull_roundtrip": rt.get("hull"), "roundtrip_lods": rt.get("lods"), "uv1_overlap": uv1,
       "gate_detail": p2.get("gate_detail")}
(H / "verification_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("VERIFIED", out["verified"], json.dumps(g))
