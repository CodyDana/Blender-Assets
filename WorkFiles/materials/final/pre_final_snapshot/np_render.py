"""Offscreen renders in Unreal (needs a REAL RHI: -AllowCommandletRendering -RenderOffscreen, never -nullrhi).

Two kinds of output, both from the transient editor world (/Temp/Untitled_0, never saved):

1. UV-plane BASE-COLOUR captures (the quantitative check that the default instance equals the baked look).
   The engine Plane is scaled to one world unit per texel and captured orthographically at the texture's own
   resolution, so every pixel centre is a texel centre at mip 0. SCS_BASE_COLOR reads the GBuffer (8-bit sRGB), so
   the capture is the exact stored level Unreal shades with. Written as EXR (RGBA16F) to ue_renders/captures/ and
   analysed by verify/analyse_captures.py in Blender. Variants use MaterialInstanceDynamic objects created at runtime
   (no asset is written): the recolour stress colours, and the paper with Baked AO In Colour = 0.

2. Lit BEAUTY frames of every mesh with its default instances (SCS_FINAL_COLOR_LDR, fixed three-light rig plus a
   sky light, manual exposure), three views each, written as PNG to ue_renders/frames_raw/.

Also records every pack texture's in-memory size (blueprint_get_memory_size needs the RHI), which proves the
16-bit detail maps built as G16 (2 bytes per texel) and not BGRA8.
"""
from __future__ import annotations

import json
import math
import time
import traceback

import unreal

import np_build
import np_spec

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
OUT = np_spec.WORK / "ue_renders"
CAPS = OUT / "captures"
RAW = OUT / "frames_raw"

STRESS = {"white": (0.8, 0.8, 0.8), "saturated_red": (0.8, 0.02, 0.02), "near_black": (0.01, 0.01, 0.01)}
PAPER_PARTS = ("Paper Colour", "Black Ink Colour", "Red Ink Colour")

# beauty rig: exposure bias per item (dark cloth needs more light than bright paper); views (yaw, elevation)
EXPOSURE_BIAS = {}
DEFAULT_BIAS = 0.0
# ONE light level for every item (the capture's exposure is fixed), so the frames keep the items' true relative
# brightness: the dark cloth reads dark and the paper light. A neutral grey floor sits under every item.
LIGHT_SCALE = {}
DEFAULT_LIGHT_SCALE = 3.0
FLOOR_MATERIAL = "/Engine/BasicShapes/BasicShapeMaterial"
SKY_INTENSITY = 1.0
VIEWS = {"threequarter": (35.0, 30.0), "top": (0.0, 88.0), "low": (215.0, 12.0)}
BEAUTY_PX = 2048            # downsampled 2:1 by the analysis step (anti-aliasing)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator's POSITIONAL order is (roll, pitch, yaw): always build it by name."""
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _capture(w, px_w, px_h, source, fmt, loc, rot, ortho_width=None, fov=None, bias=None):
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(w, px_w, px_h, fmt)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", source)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    if ortho_width is not None:
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", float(ortho_width))
    if fov is not None:
        cc.set_editor_property("fov_angle", float(fov))
        # the props are a few cm across: the engine's 10 cm near plane would cut the front off (seen on the smoke bomb)
        for prop, val in (("override_custom_near_clipping_plane", True), ("custom_near_clipping_plane", 0.5)):
            try:
                cc.set_editor_property(prop, val)
            except Exception:  # noqa: BLE001
                pass
    if bias is not None:
        pp = cc.get_editor_property("post_process_settings")
        pp.set_editor_property("override_auto_exposure_method", True)
        pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        pp.set_editor_property("override_auto_exposure_bias", True)
        pp.set_editor_property("auto_exposure_bias", float(bias))
        pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
        pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
    return cap, cc, rt


def _export(w, rt, folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    RL.export_render_target(w, rt, str(folder), name)
    return str(folder / name)


def uv_jobs(plan: dict) -> list:
    """One job per capture: (name, instance path, overrides {param: value}, size, reference info)."""
    jobs = []
    for s in plan["slots"]:
        inst = s["instance"]
        tex = s["textures"]
        bc = next(t for t in plan["textures"].values() if t["asset"] == tex["Base Colour Map"])
        if s["master"] == "M_Steel_Master":
            if "Spike" in inst:          # 2048 x 512: not square, skipped (steel is report-only)
                continue
            jobs.append({"name": f"uv_{inst}_default", "instance": s["instance_path"], "overrides": {},
                         "size": 2048 if "Wrap" not in inst else 1024, "slot": inst, "kind": "steel_default",
                         "reference_png": bc["png"]})
        elif s["master"] == "M_Fabric_Master":
            det = next(t for t in plan["textures"].values() if t["asset"] == tex["Detail Map"])
            size = 4096 if "SmokeBomb" in inst else (1024 if "Wrap" in inst else 2048)
            base = {"instance": s["instance_path"], "size": size, "slot": inst, "reference_png": bc["png"],
                    "detail_png": det["png"], "params": s["params"]}
            jobs.append({**base, "name": f"uv_{inst}_default", "overrides": {}, "kind": "fabric_default"})
            for cname, col in STRESS.items():
                jobs.append({**base, "name": f"uv_{inst}_{cname}", "overrides": {"Colour": list(col) + [1.0]},
                             "kind": "fabric_stress", "colour_name": cname})
        elif s["master"] == "M_PaperInk_Master":
            base = {"instance": s["instance_path"], "size": 2048, "slot": inst, "reference_png": bc["png"],
                    "params": s["params"],
                    "paper_detail_png": next(t for t in plan["textures"].values() if t["asset"] == tex["Paper Detail Map"])["png"],
                    "ink_weights_png": next(t for t in plan["textures"].values() if t["asset"] == tex["Ink Weights Map"])["png"],
                    "orm_png": next(t for t in plan["textures"].values() if t["asset"] == tex["ORM Map"])["png"]}
            jobs.append({**base, "name": f"uv_{inst}_default_aoon", "overrides": {}, "kind": "paper_default_ao"})
            jobs.append({**base, "name": f"uv_{inst}_default", "overrides": {"Baked AO In Colour": 0.0},
                         "kind": "paper_default"})
            for part in PAPER_PARTS:
                for cname, col in STRESS.items():
                    key = part.replace(" Colour", "").replace(" ", "")
                    jobs.append({**base, "name": f"uv_{inst}_{key}_{cname}",
                                 "overrides": {"Baked AO In Colour": 0.0, part: list(col) + [1.0]},
                                 "kind": "paper_stress", "colour_name": cname, "part": part})
    return jobs


PROBE_GAIN = 8.0


def uv_probe_material(size):
    """A TRANSIENT material (never saved): BaseColor = 0.5 + PROBE_GAIN (frac(u*size) - 0.5) (and v), i.e. the offset of
    each pixel's sample point from its texel centre, magnified. Captured like a part, it records WHERE in its texel every
    pixel actually samples (the engine Plane's UV mapping drifts by a few hundredths of a texel, which a bilinear sample
    turns into neighbour bleed on high-contrast texels). Near 0.5 the GBuffer's 8-bit sRGB step is 0.0036, so with the
    gain of 8 the sample position is known to about 0.0002 texel (offsets up to +-0.06 texel stay in range)."""
    mat = unreal.new_object(unreal.Material, name=f"NP_UVProbe_{size}")
    tc = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -800, 0)
    mul = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -600, 0)
    mul.set_editor_property("const_b", float(size))
    MEL.connect_material_expressions(tc, "", mul, "A")
    fr = MEL.create_material_expression(mat, unreal.MaterialExpressionFrac, -400, 0)
    MEL.connect_material_expressions(mul, "", fr, "")
    sub = MEL.create_material_expression(mat, unreal.MaterialExpressionSubtract, -350, 0)
    sub.set_editor_property("const_b", 0.5)
    MEL.connect_material_expressions(fr, "", sub, "A")
    gain = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 0)
    gain.set_editor_property("const_b", float(PROBE_GAIN))
    MEL.connect_material_expressions(sub, "", gain, "A")
    add = MEL.create_material_expression(mat, unreal.MaterialExpressionAdd, -250, 0)
    add.set_editor_property("const_b", 0.5)
    MEL.connect_material_expressions(gain, "", add, "A")
    ap = MEL.create_material_expression(mat, unreal.MaterialExpressionAppendVector, -200, 0)
    MEL.connect_material_expressions(add, "", ap, "A")
    zero = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
    MEL.connect_material_expressions(zero, "", ap, "B")
    MEL.connect_material_property(ap, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.recompile_material(mat)
    MEL.get_statistics(mat)
    return mat


def run_uv_captures(w, plan: dict, only=None) -> dict:
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    results = {}
    jobs = uv_jobs(plan)
    probes = {}
    for size in sorted({j["size"] for j in jobs}):
        probes[size] = uv_probe_material(size)
    probe_jobs = []
    for size in sorted(probes):
        # one probe per job location of that size (the mapping is measured where the part was captured)
        for i, job in enumerate(jobs):
            if job["size"] == size:
                probe_jobs.append((i, {"name": f"uvprobe_{size}_at{i}", "size": size, "probe": True}))
    for i, job in [(i, j) for i, j in enumerate(jobs)] + probe_jobs:
        if only and job["name"] not in only and not job.get("probe"):
            continue
        actors = []
        rec = {k: v for k, v in job.items() if k not in ("params",)}
        try:
            size = job["size"]
            x0 = 20000.0 * (i + 1)
            mi = probes[size] if job.get("probe") else unreal.load_asset(job["instance"])
            mat = mi
            if job.get("overrides"):
                mid = unreal.MaterialLibrary.create_dynamic_material_instance(w, mi, job["name"])
                for k, v in job["overrides"].items():
                    if isinstance(v, list):
                        mid.set_vector_parameter_value(k, unreal.LinearColor(*v))
                    else:
                        mid.set_scalar_parameter_value(k, float(v))
                mat = mid
            a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x0, 0.0, 0.0), rot())
            actors.append(a)
            smc = a.get_editor_property("static_mesh_component")
            smc.set_static_mesh(plane)
            smc.set_material(0, mat)
            a.set_actor_scale3d(unreal.Vector(size / 100.0, size / 100.0, 1.0))
            cap, cc, rt = _capture(w, size, size, unreal.SceneCaptureSource.SCS_BASE_COLOR,
                                   unreal.TextureRenderTargetFormat.RTF_RGBA16F,
                                   unreal.Vector(x0, 0.0, 1000.0), rot(pitch=-90.0), ortho_width=size)
            actors.append(cap)
            cc.capture_scene()
            cc.capture_scene()
            centre = RL.read_render_target_raw_pixel(w, rt, size // 2, size // 2, False)
            rec["centre_pixel"] = [centre.r, centre.g, centre.b]
            rec["exr"] = _export(w, rt, CAPS, job["name"] + ".exr")
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()[-1500:]
        finally:
            for a in actors:
                try:
                    EAS.destroy_actor(a)
                except Exception:  # noqa: BLE001
                    pass
        results[job["name"]] = rec
    (CAPS / "capture_jobs.json").write_text(json.dumps({"jobs": jobs, "probes": {j["name"]: {"size": j["size"], "at_job": jobs[i]["name"], "gain": PROBE_GAIN} for i, j in probe_jobs},
                                                       "results": results}, indent=1,
                                                       default=str), encoding="utf-8")
    return results


def _look_at(src, dst):
    return unreal.MathLibrary.find_look_at_rotation(src, dst)


def setup_lights(w, scale=1.0) -> tuple:
    actors, info = [], {}
    rig = [("key", rot(-40.0, -35.0), 3.0, unreal.LinearColor(1.0, 0.97, 0.92, 1.0)),
           ("fill", rot(-15.0, 140.0), 0.9, unreal.LinearColor(0.85, 0.9, 1.0, 1.0)),
           ("rim", rot(-25.0, 70.0), 2.0, unreal.LinearColor(1.0, 1.0, 1.0, 1.0))]
    for name, lrot, lux, col in rig:
        lt = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), lrot)
        comp = lt.get_editor_property("directional_light_component")
        comp.set_editor_property("intensity", lux * scale)
        comp.set_editor_property("light_color", unreal.Color(int(col.r * 255), int(col.g * 255), int(col.b * 255), 255))
        actors.append(lt)
        info[name] = {"rotation": [lrot.pitch, lrot.yaw, lrot.roll], "lux": lux * scale}
    try:
        # a sky the metals can reflect: SkyAtmosphere + a REAL-TIME-capture sky light (captured inside the scene
        # render itself; a specified-cubemap sky light needs a recapture that a commandlet never ticks)
        atmo = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), rot())
        actors.append(atmo)
        key_comp = actors[0].get_editor_property("directional_light_component")
        key_comp.set_editor_property("atmosphere_sun_light", True)
        sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), rot())
        slc = sky.get_editor_property("light_component")
        slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
        slc.set_editor_property("real_time_capture", True)
        slc.set_editor_property("intensity", SKY_INTENSITY * scale)
        slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        actors.append(sky)
        info["sky"] = {"type": "SkyAtmosphere + real-time-capture SkyLight", "intensity": SKY_INTENSITY * scale}
    except Exception:  # noqa: BLE001
        info["sky_error"] = traceback.format_exc()[-800:]
    return actors, info


def run_beauty(w, plan: dict, only=None) -> dict:
    results = {}
    rigs = {}
    for name, m in sorted(plan["meshes"].items()):
        if only and name not in only:
            continue
        scale = LIGHT_SCALE.get(name, DEFAULT_LIGHT_SCALE)
        lights, rigs[name] = setup_lights(w, scale)
        try:
            mesh = unreal.load_asset(m["asset"])
            actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), rot())
            actor.get_editor_property("static_mesh_component").set_static_mesh(mesh)
            rec = {"mesh": m["asset"], "frames": {}, "light_scale": scale}
            floor = None
            try:
                b = mesh.get_bounds()
                zmin = b.origin.z - b.box_extent.z
                floor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(b.origin.x, b.origin.y, zmin - 0.05), rot())
                fsm = floor.get_editor_property("static_mesh_component")
                fsm.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
                fsm.set_material(0, unreal.load_asset(FLOOR_MATERIAL))
                s_ = max(float(b.sphere_radius) * 20.0 / 100.0, 1.0)
                floor.set_actor_scale3d(unreal.Vector(s_, s_, 1.0))
                rec["floor"] = FLOOR_MATERIAL
                centre = b.origin
                radius = float(b.sphere_radius)
                fov = 20.0
                dist = radius / math.sin(math.radians(fov / 2.0)) * 1.15
                rec["bounds"] = {"origin": [centre.x, centre.y, centre.z], "radius": radius}
                for vname, (yaw, elev) in VIEWS.items():
                    dx = math.cos(math.radians(elev)) * math.cos(math.radians(yaw))
                    dy = math.cos(math.radians(elev)) * math.sin(math.radians(yaw))
                    dz = math.sin(math.radians(elev))
                    loc = unreal.Vector(centre.x + dist * dx, centre.y + dist * dy, centre.z + dist * dz)
                    cam_rot = _look_at(loc, centre)
                    bias = EXPOSURE_BIAS.get(name, DEFAULT_BIAS)
                    cap, cc, rt = _capture(w, BEAUTY_PX, BEAUTY_PX, unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR,
                                           unreal.TextureRenderTargetFormat.RTF_RGBA8, loc, cam_rot, fov=fov, bias=bias)
                    try:
                        for _ in range(3):
                            cc.capture_scene()
                        c0 = BEAUTY_PX // 2 - 32
                        area = RL.read_render_target_raw_pixel_area(w, rt, c0, c0, c0 + 63, c0 + 63, False)
                        rec.setdefault("centre_mean", {})[vname] = [round(sum(getattr(p, ch) for p in area) / max(len(area), 1), 4)
                                                                    for ch in ("r", "g", "b")]
                        rec["frames"][vname] = _export(w, rt, RAW, f"{name}_{vname}.png")
                        rec.setdefault("exposure_bias", bias)
                    finally:
                        EAS.destroy_actor(cap)
            except Exception:  # noqa: BLE001
                rec["error"] = traceback.format_exc()[-1500:]
            finally:
                EAS.destroy_actor(actor)
                if floor is not None:
                    EAS.destroy_actor(floor)
            results[name] = rec
        finally:
            for a in lights:
                try:
                    EAS.destroy_actor(a)
                except Exception:  # noqa: BLE001
                    pass
    return {"rig": rigs, "frames": results}


# V4 sheen calibration grid: Fuzz Colour = Sheen Tint x k, Cloth amount a (plus a = 0, the no-sheen baseline)
SHEEN_TINT = (0.62, 0.60, 0.56)
SHEEN_K = (0.05, 0.1, 0.2, 0.35, 0.62, 1.0)
SHEEN_AMOUNT = (0.35, 0.6, 1.0)
SHEEN_LIGHTS = {"key": (1.0, 1.0, 1.0), "rim": (-1.0, 0.35, 0.6)}     # towards the light; camera on +X


def run_sheen_calibration(w, plan: dict) -> dict:
    """UE half of the V4 sheen calibration (Blender half: verify/sheen_blender_reference.py). A flat-coloured sphere
    (MI_Kunai_Plain_Wrap through a MaterialInstanceDynamic with Detail Strength 0 and Normal Strength 0) under ONE
    directional light, orthographic from +X, SCS_SCENE_COLOR_HDR (linear) into RGBA16F EXR, for every Fuzz Colour /
    Cloth amount pair of the grid. verify/sheen_compare.py picks the pair whose sheen-on / sheen-off ratio per N.V bin
    best matches Blender's."""
    sphere = unreal.load_asset("/Engine/BasicShapes/Sphere")
    shipped = unreal.load_asset(plan["instances"]["MI_Kunai_Plain_Wrap"]["path"])
    # the Cloth permutation: a TRANSIENT instance (never saved) of the shipped wrap with Cloth Sheen on;
    # a MaterialInstanceDynamic cannot change a static switch
    wrap = unreal.new_object(unreal.MaterialInstanceConstant, name="NP_SheenCal_Cloth")
    MEL.set_material_instance_parent(wrap, shipped)
    MEL.set_material_instance_static_switch_parameter_value(wrap, "Cloth Sheen", True)
    MEL.update_material_instance(wrap)
    cloth_on = bool(MEL.get_material_instance_static_switch_parameter_value(wrap, "Cloth Sheen"))
    np_build.stats(wrap)
    folder = OUT / "sheen_calibration"
    out = {"grid": {"tint": SHEEN_TINT, "k": SHEEN_K, "amount": SHEEN_AMOUNT}, "lights": SHEEN_LIGHTS, "frames": {},
           "parent": "transient MIC of MI_Kunai_Plain_Wrap with Cloth Sheen = " + str(cloth_on)}
    actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), rot())
    smc = actor.get_editor_property("static_mesh_component")
    smc.set_static_mesh(sphere)
    cands = [("off", 0.0, 0.0)] + [(f"k{k}_a{a}", k, a) for k in SHEEN_K for a in SHEEN_AMOUNT]
    try:
        for lname, towards in SHEEN_LIGHTS.items():
            n = math.sqrt(sum(c * c for c in towards))
            d = [-c / n for c in towards]
            lt = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500),
                                            rot(math.degrees(math.asin(d[2])), math.degrees(math.atan2(d[1], d[0]))))
            lt.get_editor_property("directional_light_component").set_editor_property("intensity", 3.0)
            try:
                for label, k, amount in cands:
                    mid = unreal.MaterialLibrary.create_dynamic_material_instance(w, wrap, f"cal_{lname}_{label}")
                    mid.set_scalar_parameter_value("Detail Strength", 0.0)
                    mid.set_scalar_parameter_value("Normal Strength", 0.0)
                    mid.set_vector_parameter_value("Sheen Colour", unreal.LinearColor(*[c * k for c in SHEEN_TINT], 1.0))
                    mid.set_scalar_parameter_value("Sheen Amount", float(amount))
                    smc.set_material(0, mid)
                    cap, cc, rt = _capture(w, 512, 512, unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR,
                                           unreal.TextureRenderTargetFormat.RTF_RGBA16F,
                                           unreal.Vector(500.0, 0.0, 0.0), rot(yaw=180.0), ortho_width=100.0)
                    try:
                        cc.capture_scene()
                        cc.capture_scene()
                        out["frames"][f"{lname}_{label}"] = {"k": k, "amount": amount, "light": lname,
                                                             "exr": _export(w, rt, folder, f"ue_sheen_{lname}_{label}.exr")}
                    finally:
                        EAS.destroy_actor(cap)
            finally:
                EAS.destroy_actor(lt)
    finally:
        EAS.destroy_actor(actor)
    (folder / "ue_sheen_frames.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


def texture_memory(plan: dict) -> dict:
    out = {}
    for asset, t in sorted(plan["textures"].items()):
        tex = unreal.load_asset(asset)
        try:
            mem = int(tex.blueprint_get_memory_size())
        except Exception as exc:  # noqa: BLE001
            mem = repr(exc)
        sx, sy = int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
        out[asset] = {"kind": t["kind"], "size": [sx, sy], "memory_bytes": mem,
                      "bytes_per_texel_with_mips": round(mem / (sx * sy), 4) if isinstance(mem, int) and sx * sy else None}
    return out


def run_render(plan: dict, tag: str) -> dict:
    w = world()
    rep = {"mode": "render", "world": w.get_path_name() if w else None}
    t0 = time.time()
    # compile every instance's permutation first (get_statistics blocks until its shaders exist)
    rep["instance_statistics"] = {n: np_build.stats(unreal.load_asset(i["path"])) for n, i in sorted(plan["instances"].items())}
    rep["compile_sec"] = round(time.time() - t0, 1)
    rep["texture_memory"] = texture_memory(plan)
    import os
    parts = os.environ.get("NP_RENDER_PARTS", "uv,beauty").split(",")
    only = [x for x in os.environ.get("NP_RENDER_ONLY", "").split(",") if x] or None
    if "uv" in parts:
        t1 = time.time()
        rep["uv_captures"] = run_uv_captures(w, plan, only)
        rep["uv_sec"] = round(time.time() - t1, 1)
    if "beauty" in parts:
        t1 = time.time()
        rep["beauty"] = run_beauty(w, plan, only)
        rep["beauty_sec"] = round(time.time() - t1, 1)
    if "sheen" in parts:
        rep["sheen_calibration"] = run_sheen_calibration(w, plan)
    rep["passed"] = (all(not v.get("error") for v in rep.get("uv_captures", {}).values())
                     and all(not v.get("error") for v in (rep.get("beauty") or {}).get("frames", {}).values()))
    return rep
