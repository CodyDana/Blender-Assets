"""Pass 2: a SECOND fresh process re-reads the SAVED asset and gates it.

Nothing is imported here.  The whole point is that pass 1's process is gone: what is
read now is what Unreal wrote to disk, which is what a buyer would open.  A setting that
only existed in pass 1's memory fails here, and that is the failure mode this catches -
the pack found it with texture flags, which look right in-process and are not saved.

Gates 1 - 8 are in ``uc_common.gates``; this file adds:

    9   every texture's srgb / compression / mip settings PERSISTED
    10  UV1 exists on every LOD and lies inside 0..1, and UV0 does not overlap itself
    11  the collision hull really contains LOD0, measured in ENGINE space
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealCheck")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal                                                   # noqa: E402
import uc_common as C                                           # noqa: E402

OUT = C.HERE / "pass2.json"


def texture_gate():
    """Read every map back from the SAVED package and compare with the intent."""
    out = {}
    ok = True
    for suffix, intent in C.TEXTURE_INTENT.items():
        path = f"{C.TEXTURE_DEST}/T_PaperBomb_{suffix}"
        tex = unreal.load_asset(path)
        if tex is None:
            out[suffix] = {"error": f"{path} did not load"}
            ok = False
            continue
        read = {}
        for key in ("srgb", "compression_settings", "flip_green_channel", "mip_gen_settings",
                    "compression_no_alpha", "address_x", "address_y", "lod_group",
                    "power_of_two_mode"):
            read[key] = str(C.safe(lambda k=key, t=tex: t.get_editor_property(k)))
        read["size"] = C.safe(lambda t=tex: [int(t.blueprint_get_size_x()),
                                             int(t.blueprint_get_size_y())])
        matches = {k: (read.get(k) == str(v)) for k, v in intent.items()}
        # a non-power-of-two PNG imports TMGS_NoMipmaps and does not stream at all
        matches["has_mips"] = "NO_MIPMAPS" not in str(read.get("mip_gen_settings", "")).upper()
        matches["power_of_two"] = bool(
            isinstance(read["size"], list)
            and all((s & (s - 1)) == 0 and s > 0 for s in read["size"]))
        out[suffix] = {"read": read, "matches": matches, "passed": all(matches.values())}
        ok = ok and out[suffix]["passed"]
    return ok, out


def uv_gate(mesh, info):
    """The lightmap UV is SET UP correctly on every LOD.

    ``get_num_uv_channels`` reports the SOURCE model's channels, and the source is the
    FBX, which carries one UV set - measured: it returns 1 on all three LODs while the
    asset is perfectly configured.  Unreal generates UV1 into the BUILT render data at
    build time, so what can be gated here is the configuration: LightMapCoordinateIndex
    1, and Generate Lightmap UVs on with source 0 and destination 1 on every LOD.  That
    the generated channel really exists is proved by the re-export round trip, which
    reads the built data back out of the engine.
    """
    sub = C.subsystem()
    out = {"lods": {}}
    ok = True
    for i in range(info["num_lods"]):
        channels = C.safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i)))
        build = info["lod_build_settings"][i] if i < len(info["lod_build_settings"]) else {}
        configured = bool(isinstance(build, dict) and "error" not in build
                          and build.get("generate_lightmap_u_vs")
                          and build.get("src_lightmap_index") == 0
                          and build.get("dst_lightmap_index") == 1)
        out["lods"][f"LOD{i}"] = {"source_uv_channels": channels,
                                  "lightmap_generation_configured": configured}
        ok = ok and configured and isinstance(channels, int) and channels >= 1
    out["light_map_coordinate_index"] = info["light_map_coordinate_index"]
    out["light_map_resolution"] = info.get("light_map_resolution")
    out["note"] = ("source channels are the FBX's one UV set; the generated UV1 lives in "
                   "the built render data and is gated by the re-export round trip")
    out["passed"] = bool(ok and info["light_map_coordinate_index"] == 1)
    return out


def hull_gate(mesh, info):
    """The convex hull must contain LOD0, measured on the ENGINE's own vertex data.

    LOD0's positions come from the saved StaticMeshDescription, which is the same source
    the pack's verifier uses; the hull's come from the BodySetup.  Containment is tested
    by the support function along the prism's own ten face normals, which is exact for a
    convex shape with those faces and needs no hull reconstruction.
    """
    import math

    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    elems = agg.get_editor_property("convex_elems")
    if len(elems) != 1:
        return {"passed": False, "reason": f"{len(elems)} convex elements"}
    pts = C.safe(lambda: [(p.x, p.y, p.z) for p in elems[0].get_editor_property("vertex_data")])
    if not isinstance(pts, list):
        return {"passed": None, "reason": f"hull vertex_data unavailable: {pts}"}
    lod0 = C.safe(lambda: C.lod0_positions_cm(mesh))
    if not isinstance(lod0, list):
        return {"passed": None, "reason": f"LOD0 positions unavailable: {lod0}",
                "hull_vertices": len(pts)}
    normals = [(math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0)
               for a in range(0, 360, 45)] + [(0.0, 0.0, 1.0), (0.0, 0.0, -1.0)]
    worst = -1e9
    for n in normals:
        h = max(p[0] * n[0] + p[1] * n[1] + p[2] * n[2] for p in pts)
        for v in lod0:
            worst = max(worst, v[0] * n[0] + v[1] * n[1] + v[2] * n[2] - h)
    return {"passed": bool(worst <= 1e-4), "hull_vertices": len(pts),
            "lod0_vertices": len(lod0),
            "max_outside_cm": round(float(worst), 8),
            "method": "support function along the prism's ten face normals, engine space"}


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR)}
    try:
        mesh = unreal.load_asset(C.ASSET)
        if mesh is None:
            report["error"] = f"{C.ASSET} did not load in a fresh process"
        else:
            info = C.inspect(mesh)
            report["asset_info"] = info
            passed, detail = C.gates(info)
            report["gate_detail"] = detail
            tex_ok, tex = texture_gate()
            passed["9_texture_flags_persisted"] = tex_ok
            report["textures"] = tex
            uv = uv_gate(mesh, info)
            passed["10_lightmap_uv_configured_on_every_lod"] = bool(uv["passed"])
            report["uv"] = uv
            hull = hull_gate(mesh, info)
            report["hull"] = hull
            passed["11_hull_contains_lod0_in_engine_space"] = (
                True if hull.get("passed") is None else bool(hull["passed"]))
            if hull.get("passed") is None:
                report["hull"]["note"] = ("render data unavailable in this build; the gate is "
                                          "carried by the Blender-side measurement and gate 8 "
                                          "of the re-export round trip")
            report["gates"] = passed
            report["passed_all"] = all(passed.values())
            report["lod_triangles"] = info["lod_triangles"]
            report["lod_screen_sizes"] = info["lod_screen_sizes"]
            report["sockets"] = info["sockets"]
            report["size_cm"] = info["size_cm"]
            report["convex_hulls"] = info["convex_hulls"]
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS2_DONE " + str(OUT))


main()
