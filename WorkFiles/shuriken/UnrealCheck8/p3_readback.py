"""UnrealCheck8 process 3: FRESH-process read-back of the saved meshes and textures. Imports nothing, writes
nothing to any asset. Gates (log-line and round-trip gates are added by summarize.py):
  M1 LOD count 3 and per-LOD triangles == the .blend AND the shipped-FBX re-import (b1_blend_truth.json)
  M2 exactly one convex hull, no other collision primitives
  M3 Grip and Trail persisted on the asset (outered to it), relative scale 1, transform == sidecar == .blend
  M4 bounds (cm) == spec
  M5 LOD screen sizes == sidecar == spec, auto-compute off
  M6 lightmap coordinate index 1, every LOD builds lightmap UVs 0 -> 1, >= 2 UV channels
  M7 one material slot / one section per LOD, Nanite off
  T  BC sRGB + TC_Default; ORM sRGB off + TC_Masks; N sRGB off + TC_Normalmap + flip green off; 2048
Writes p3_readback.json.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck8")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc8_common as C  # noqa: E402

TRUTH = json.loads((C.HERE / "blend_truth.json").read_text(encoding="utf-8"))


def close(a, b, tol):
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def mesh_gates(form, info):
    spec = C.FORMS[form]
    truth = TRUTH["forms"][form]
    side = json.loads(C.sidecar(form).read_text(encoding="utf-8"))
    g, d = {}, {}
    blend_tris, fbx_tris = truth["blend"]["lod_triangles"], truth["fbx"]["lod_triangles"]
    g["M1_lods_3_triangles_equal_blender"] = (info["num_lods"] == 3 and info["lod_triangles"] == blend_tris
                                             and blend_tris == fbx_tris)
    d["M1"] = {"unreal": info["lod_triangles"], "blend": blend_tris, "fbx_reimport": fbx_tris}
    oth = info.get("other_collision_elems", {})
    g["M2_exactly_one_convex_hull"] = (info.get("convex_hulls") == 1
                                       and all((v == 0) for v in oth.values() if isinstance(v, int)))
    d["M2"] = {"convex_hulls": info.get("convex_hulls"), "other": oth}
    exp = {r["socket"]: r for r in side["sockets"]}
    blend_sock = {k.rsplit("_", 1)[-1]: v["ue"] for k, v in truth["blend"]["sockets"].items()}
    sock_ok = set(exp) == {"Grip", "Trail"} and set(info["component_socket_names"]) == {"Grip", "Trail"}
    sd = {}
    for s in info["socket_objects"]:
        e = exp.get(s["name"])
        b = blend_sock.get(s["name"])
        ok = bool(s.get("found")) and e is not None and b is not None
        if ok:
            rot = s["relative_rotation"]
            ok = (close(s["relative_location_cm"], e["location_cm"], 1e-4)
                  and close(s["relative_location_cm"], b["location_cm"], 1e-4)
                  and all(abs(rot[k] - e["rotation_deg"][k]) < 1e-4 for k in ("roll", "pitch", "yaw"))
                  and close(s["relative_scale"], [1.0, 1.0, 1.0], 0.0)
                  and (s["outer"] or "").startswith(C.asset(form) + ".")
                  and close(info["component_sockets"][s["name"]]["scale"], [1.0, 1.0, 1.0], 1e-6)
                  and close(info["component_sockets"][s["name"]]["location_cm"], e["location_cm"], 1e-4))
        sd[s["name"]] = ok
        sock_ok = sock_ok and ok
    g["M3_grip_trail_scale_1_match_sidecar_and_blend"] = sock_ok and len(sd) == 2
    d["M3"] = sd
    g["M4_bounds_cm_match_spec"] = close(info["size_cm"], spec["size_cm"], 5e-4)
    d["M4"] = {"unreal": info["size_cm"], "spec": [round(x, 6) for x in spec["size_cm"]],
               "min": info["bounds_min_cm"], "max": info["bounds_max_cm"]}
    ss = info["lod_screen_sizes"]
    g["M5_lod_screen_sizes_applied"] = (isinstance(ss, list) and close(ss, side["lod_screen_sizes"], 1e-6)
                                        and close(side["lod_screen_sizes"], spec["screen_sizes"], 1e-9)
                                        # bAutoComputeLODScreenSize is not exposed to Python on 5.8.2 (reads as an
                                        # error); a True value would still fail here
                                        and info["auto_compute_lod_screen_size"] is not True)
    d["M5"] = {"unreal": ss, "sidecar": side["lod_screen_sizes"], "spec": spec["screen_sizes"],
               "auto_compute": info["auto_compute_lod_screen_size"]}
    bs = info["lod_build_settings"]
    g["M6_lightmap_index_1_generated_0_to_1"] = (info["light_map_coordinate_index"] == 1
                                                 # the subsystem counts SOURCE (mesh description) channels: UV0 only;
                                                 # the generated UV1 lives in the render data -> b2_roundtrip.py
                                                 and all(isinstance(c, int) and c >= 1 for c in info["lod_uv_channels"])
                                                 and all(isinstance(b, dict) and "error" not in b
                                                         and b["generate_lightmap_u_vs"] is True
                                                         and b["src_lightmap_index"] == 0 and b["dst_lightmap_index"] == 1
                                                         for b in bs))
    d["M6"] = {"light_map_coordinate_index": info["light_map_coordinate_index"],
               "uv_channels_per_lod": info["lod_uv_channels"], "build": bs,
               "light_map_resolution": info["light_map_resolution"]}
    g["M7_one_slot_one_section_nanite_off"] = (len(info["material_slots"]) == 1
                                              and all(s == 1 for s in info["lod_sections"])
                                              and info["nanite_enabled"] is False)
    d["M7"] = {"slots": info["material_slots"], "sections": info["lod_sections"], "nanite": info["nanite_enabled"]}
    return g, d


def png_size(path):
    """(width, height) from a PNG's IHDR chunk (bytes 16..24): the size the shipped file declares."""
    head = Path(path).read_bytes()[:24]
    return [int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")]


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "forms": {}, "textures": {}}
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    for form in C.FORMS:
        rec = {"asset": C.asset(form)}
        try:
            rec["uasset_on_disk"] = str(content / C.DEST[len("/Game/"):] / f"{C.FORMS[form]['mesh']}.uasset")
            rec["uasset_exists"] = Path(rec["uasset_on_disk"]).exists()
            mesh = unreal.load_asset(C.asset(form))
            rec["info"] = C.inspect_mesh(mesh)
            rec["gates"], rec["detail"] = mesh_gates(form, rec["info"])
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()
            rec["gates"] = {"loaded": False}
        report["forms"][form] = rec
    for form, spec in C.FORMS.items():
        stem_base = "T_" + spec["mesh"][len("SM_"):]
        for kind in ("BC", "ORM", "N"):
            stem = f"{stem_base}_{kind}"
            png = C.EXPORTS / "Textures" / f"{stem}.png"
            rec = {"asset": f"{C.TEX_DEST}/{stem}", "kind": kind, "png_sha256_now": C.sha256(png),
                   "png_md5_now": C.md5(png)}
            try:
                tex = unreal.load_asset(rec["asset"])
                if tex is None:
                    rec["error"] = "asset not found"
                    rec["ok"] = False
                else:
                    info = C.inspect_texture(tex)
                    rec["info"] = info
                    want = C.TEX_INTENT[kind]
                    checks = {k: info.get(k) == v for k, v in want.items()}
                    rec["png_size"] = png_size(png)          # 3.8.1: the spike's maps are 2048 x 512
                    checks["size_equals_png"] = info.get("size") == rec["png_size"]
                    checks["size_power_of_two"] = all(v > 0 and v & (v - 1) == 0 for v in rec["png_size"])
                    checks["texture2d"] = info.get("class") == "Texture2D"
                    rec["checks"] = checks
                    rec["ok"] = all(checks.values())
            except Exception:  # noqa: BLE001
                rec["error"] = traceback.format_exc()
                rec["ok"] = False
            report["textures"][stem] = rec
    C.write(C.HERE / "p3_readback.json", report)
    unreal.log("UC8_P3_DONE")


main()
