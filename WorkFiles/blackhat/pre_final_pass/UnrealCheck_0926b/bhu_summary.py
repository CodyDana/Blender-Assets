import json, hashlib
from pathlib import Path
H = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealCheck")
P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
p1 = json.loads((H / "pass1.json").read_text()); p2 = json.loads((H / "pass2.json").read_text())
p3 = json.loads((H / "pass3.json").read_text()); rt = json.loads((H / "roundtrip_compare.json").read_text())
ti = json.loads((H / "props_textures_import.json").read_text()); tv = json.loads((H / "props_textures_verify.json").read_text())
rep = json.loads((P / "WorkFiles/blackhat/blackhat_report.json").read_text())
fbx = P / "Exports/BlackHat/SM_BlackHat.fbx"
sha = hashlib.sha256(fbx.read_bytes()).hexdigest()
logs = {n: sum(1 for l in (H / f"{n}.log").read_text(errors="ignore").splitlines() if "Warning:" in l or "Error:" in l)
        for n in ("pass1", "tex_import", "tex_verify", "pass2", "pass3")}
g = dict(p2["gates"])
g["11_hull_contains_lod0_in_engine_space"] = bool(rt["hull"].get("contains_lod0"))
g["13_roundtrip_triangles_and_positions_exact"] = all(
    v["shipped_triangles"] == v["unreal_triangles"] and v["positions_two_sided_cm"] <= 1e-4
    and v["shipped_triangles_absent_in_unreal"] == 0 for v in rt["lods"].values())
# a 600 mm hat: float32 resolution at 30 cm is ~3e-6 cm, so the smoke bomb's 1e-6 cm (a 70 mm ball) cannot hold
g["14_roundtrip_hull_vertices_1e-5cm"] = rt["hull"]["vertices_two_sided_cm"] <= 1e-5
g["15_texture_import_and_fresh_verify"] = bool(ti["passed"] and tv["passed"] and tv["processed"] == tv["expected"] == 8)
g["16_zero_warning_error_lines_all_passes"] = all(v == 0 for v in logs.values())
uv1 = json.loads((H / "uv1_overlap.json").read_text())
g["18_uv1_zero_overlap_1024_2048_every_lod"] = all(v.get("overlap_texels_1024") == 0 and v.get("overlap_texels_2048") == 0 for v in uv1.values()) and len(uv1) == 3
g["17_same_bytes_everywhere"] = (sha == rep["export"]["sha256"]["fbx"] == p1["fbx_sha256"] == p2["fbx_sha256"] == p3["shipped_fbx_sha256"])
out = {"engine": p2["engine"], "project": "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject",
       "content_path": p2["asset"], "fbx_sha256": sha, "sidecar_sha256": p2["sidecar_sha256"],
       "processes": ["pass1 import + sidecar (one save)", "tex_import (props importer)", "tex_verify (fresh)",
                     "pass2 reload + gates (fresh)", "pass3 Unreal FBX export (fresh)", "Blender round-trip compare"],
       "warning_error_lines": logs, "gates": g, "verified": all(g.values()),
       "lod_triangles": p2["lod_triangles"], "lod_screen_sizes": p2["lod_screen_sizes"],
       "bounds_sphere_radius_cm": p2["bounds_sphere_radius_cm"], "size_cm": p2["size_cm"],
       "sockets": p2["sockets"], "convex_hulls": p2["convex_hulls"], "hull_roundtrip": rt["hull"],
       "roundtrip_lods": {k: {kk: v[kk] for kk in ("shipped_triangles", "unreal_triangles", "positions_two_sided_cm", "shipped_triangles_absent_in_unreal")} for k, v in rt["lods"].items()},
       "uv1_overlap": uv1,
       "textures": {k: {kk: v.get("flags", {}).get(kk) for kk in ("srgb", "compression_settings", "mip_gen_settings", "flip_green_channel", "size")} for k, v in tv["maps"].items()},
       "textures_pass2": p2.get("textures"),
       "notes": ["BlackHat: two hulls, one HEAD socket, two material slots (straw, cloth), 8 maps at 2048", "UE 5.8 Python has no KConvexElem.vertex_data, so pass 2's own hull gate cannot read the points; gate 11 is carried by the Unreal FBX round trip (pass 3 + Blender)",
                 "final pass (maintainer, 2026-09-25): shingled fan + hidden widening, ClothSpec6, Detail sRGB ON (BaseColor = Detail.R x Tint), ORM RGBA with the baked specular mask in A; verified under a new content path; round 4 record stays in WorkFiles/smokebomb/UnrealCheck_rw4/"]}
(H / "verification_summary.json").write_text(json.dumps(out, indent=2))
print("VERIFIED", out["verified"], json.dumps(g))
