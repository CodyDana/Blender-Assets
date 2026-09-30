"""DojoLab SHOWCASE step (pythonscript commandlet, -nullrhi): re-assemble /Game/Dojo/Maps/L_Dojo from
layout_showcase.json (grey-box buildings + KIT 1 wall and gatehouse + KIT 2 ground + the prop kits) and save it.

- Re-run safe: destroys only the actors tagged DJ_Managed (the whole previous grey-box assembly) and nothing else.
- One StaticMeshActor per instance (every prop its own actor), labelled <piece>__<nnnn>, in Outliner folders
  Dojo/<folder>: location (x*100, -y*100, z*100) cm; rotation from the Blender XYZ Euler through R_ue = S R S
  (S = diag(1, -1, 1); yaw-only instances reduce to yaw = -rot_z); scale as the layout (the fitted vending machine and
  roof ACs). Mobility static. Collision per class (spec 5.3 + showcase classes): Pawn / Camera / Visibility block or
  ignore; nocollision = NoCollision (wires, rope, bucket, drum sticks, ground dressing); the 1v1 boundary Pawn-only and
  hidden in game.
- GASP traversal: one LevelBlock_Traversable per layout marker (grey-box markers kept; the weapon-rack and roof-AC
  markers re-fitted to the kit props), Traversable channel only, hidden in game.
- Sunset: the sun of layout_showcase.json (13 deg from the W-N-W, 420 lux = Blender 4.2 W/m2 x K 100, 5500 K,
  atmosphere sun), the SkyAtmosphere lifted to Blender's lilac-grey world (S.SKY_FACTOR), a real-time SkyLight at
  S.SKYLIGHT_INTENSITY, height fog, an unbound PPV with manual exposure and a NEUTRAL grade (S.GRADE); point lights
  (candela x S.LAMP_SCALE, the exposure-parity factor) at every lamp; the showcase cameras. Round 2 (2026-09-28): the
  orange cast was the lighting / post chain, not the materials (dj_sc_colour_probe.py; notes in unreal/round2_polish).
- GATE: every mesh actor's world box equals the Blender bounds (showcase/blender_bounds.json), converted, within 1 cm:
  render bounds for non-Nanite meshes; for Nanite meshes the full-detail fallback geometry through the actor transform
  (their render bounds are UE's conservative Nanite DAG box; see dj_sc_nanite.py).
Env: DJ_EXPOSURE_BIAS overrides the exposure bias (EV). Result: WorkFiles/dojo/build/unreal/showcase/level.json
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402
import dj_sc_common as S  # noqa: E402
import dj_sc_nanite as N  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": [], "setp_failed": []}
TOL_CM = 1.0
CH = unreal.CollisionChannel
RESP = {"block": unreal.CollisionResponseType.ECR_BLOCK, "ignore": unreal.CollisionResponseType.ECR_IGNORE}
L = S.load()
# exposure: analytic radiance parity is 0.6 - log2(100) = -6.04 EV; the armory measured Unreal needing about +2.4 EV
# over that analytic figure for the same Blender review look (ak_common EXPOSURE_BIAS history); capture round 1 at
# +2.44 clipped the lit sand, so +2.0
BIAS = float(os.environ.get("DJ_EXPOSURE_BIAS", str(round(L["sun"]["exposure_bias"] + S.EXPOSURE_OVER_ANALYTIC, 3))))
SKY_FACTOR = S.SKY_FACTOR        # round 2: Blender's lilac-grey world (was (3.4, 2.6, 2.1): beige sky, orange fill)
PP = dict(S.GRADE)               # round 2: neutral gain / saturation (was gain (1.06, 1.0, 0.9), saturation 0.85)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["setp_failed"].append(f"{type(obj).__name__}.{k}: {str(exc)[:160]}")
        return False


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def tag(actor, label, folder, *extra):
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.tags = [unreal.Name(S.MANAGED_TAG)] + [unreal.Name(t) for t in extra]
    return actor


def open_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["open_ok"] = bool(les.load_level(C.LEVEL))
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(S.MANAGED_TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    REP["managed_actors_removed"] = removed
    REP["unmanaged_actors_kept"] = sorted(a.get_actor_label() for a in EAS.get_all_level_actors())


def ue_rotator(inst):
    rx, ry, rz = inst["rot_xyz_deg"]
    if abs(rx) < 1e-9 and abs(ry) < 1e-9:
        return rot(yaw=C.yaw_deg(rz))
    x, z = S.ue_axes(inst["rot_xyz_deg"])
    return unreal.MathLibrary.make_rot_from_xz(V(x), V(z))


def apply_collision(comp, cls):
    c = L["collision_classes"][cls]
    if c.get("no_collision"):
        comp.set_collision_profile_name("NoCollision")
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_collision_response_to_all_channels(RESP["ignore"])
        return
    comp.set_collision_profile_name("BlockAll")
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    if cls == "boundary":
        comp.set_collision_response_to_all_channels(RESP["ignore"])
    comp.set_collision_response_to_channel(CH.ECC_PAWN, RESP[c["pawn"]])
    comp.set_collision_response_to_channel(CH.ECC_CAMERA, RESP[c["camera"]])
    comp.set_collision_response_to_channel(CH.ECC_VISIBILITY, RESP[c["visibility"]])


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "showcase"))
import look_r3  # noqa: E402  (round 3: per-actor material overrides)


def place_meshes():
    placed, meshes = {}, {}
    over_mi = {}
    REP["material_overrides"] = {}
    for n, inst in enumerate(L["instances"]):
        piece = inst["piece"]
        if piece not in meshes:
            meshes[piece] = unreal.load_asset(S.mesh_path(L, piece))
        if meshes[piece] is None:
            REP["notes"].append(f"missing mesh {piece}")
            continue
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(inst["loc"])), ue_rotator(inst))
        a.set_actor_scale3d(V(inst["scale"]))
        smc = a.static_mesh_component
        smc.set_static_mesh(meshes[piece])
        for idx, slot in look_r3.ACTOR_MATERIAL_OVERRIDES.get(piece, {}).items():
            if slot not in over_mi:
                over_mi[slot] = unreal.load_asset(S.mat_path(L, slot))
            if over_mi[slot] is None:
                REP["notes"].append(f"override material {slot} missing")
                continue
            smc.set_material(int(idx), over_mi[slot])
            REP["material_overrides"][S.label(inst, n)] = {int(idx): slot}
        smc.set_mobility(unreal.ComponentMobility.STATIC)
        apply_collision(smc, inst["collision_class"])
        if piece in S.NO_SHADOW_PIECES:   # round 3 fix f1: grey-box canopies cast no shadow (judge delta 4)
            setp(smc, "cast_shadow", False)
            REP.setdefault("no_shadow_actors", []).append(S.label(inst, n))
        if L["collision_classes"][inst["collision_class"]].get("hidden_in_game"):
            a.set_actor_hidden_in_game(True)
            setp(smc, "cast_shadow", False)
        tag(a, S.label(inst, n), "Dojo/" + inst["folder"], "DJK_" + inst["kit"], "DJC_" + inst["collision_class"])
        placed[n] = a
    return placed


def expected_transform(inst):
    return V(C.loc_cm(inst["loc"])), ue_rotator(inst), V(inst["scale"])


def bounds_gate(placed):
    """Two measures per actor. (1) TRANSFORM: location, rotation and scale equal the layout conversion (0.01 cm,
    0.001 deg, 1e-5). (2) BOUNDS against the Blender AABB (converted) within 1 cm for EVERY mesh: non-Nanite = the
    actor's render bounds; Nanite = the rendered geometry, i.e. the full-detail fallback's vertex box through the actor
    transform (dj_sc_nanite: UE 5.8's Nanite render bounds are the union of every Nanite DAG level's cluster boxes and
    sit 0.5-27.6 cm outside the surface by design; that culling-box inflation is reported, not gated)."""
    bb = S.bounds()["instances"]
    rows, worst, worst_t, worst_n, infl, fbox = {}, 0.0, 0.0, 0.0, {}, {}
    for n, a in placed.items():
        inst = L["instances"][n]
        loc, rt, sc = expected_transform(inst)
        al, ar, asc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
        dq = unreal.MathLibrary.normalized_delta_rotator(ar, rt)
        terr = max(abs(al.x - loc.x), abs(al.y - loc.y), abs(al.z - loc.z))
        rerr = max(abs(dq.pitch), abs(dq.yaw), abs(dq.roll))
        serr = max(abs(asc.x - sc.x), abs(asc.y - sc.y), abs(asc.z - sc.z))
        worst_t = max(worst_t, terr)
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        b = bb[str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        w = wmin + wmax
        nanite = bool(L["pieces"][inst["piece"]]["nanite"])
        if not nanite and "min_all_lods" in b:   # round 2: UE's render bounds = the union of every LOD
            wmin, wmax = C.bbox_bl_to_ue(b["min_all_lods"], b["max_all_lods"])
            w = wmin + wmax
        if nanite:
            if inst["piece"] not in fbox:
                fbox[inst["piece"]] = N.fallback_box(a.static_mesh_component.get_editor_property("static_mesh"))
            g = N.world_box(a, fbox[inst["piece"]])
            err = max(abs(p - q) for p, q in zip(g, w))
            worst_n = max(worst_n, err)
            infl[inst["piece"]] = max(infl.get(inst["piece"], 0.0), round(max(abs(p - q) for p, q in zip(u, w)), 3))
        else:
            err = max(abs(p - q) for p, q in zip(u, w))
            worst = max(worst, err)
        ok_b = err <= TOL_CM
        ok = ok_b and terr <= 0.01 and rerr <= 0.001 and serr <= 1e-5
        rows[n] = {"label": a.get_actor_label(), "nanite": nanite, "bounds_err_cm": round(err, 4),
                   "t_err_cm": round(terr, 5), "r_err_deg": round(rerr, 5), "s_err": round(serr, 7), "ok": ok}
    fails = {k: v for k, v in rows.items() if not v["ok"]}
    return {"tolerance_cm": TOL_CM, "n_checked": len(rows), "n_layout": len(L["instances"]),
            "max_err_cm_all": round(max(worst, worst_n), 4), "max_err_cm_non_nanite": round(worst, 4),
            "max_err_cm_nanite_geometry": round(worst_n, 4),
            "max_transform_err_cm": round(worst_t, 5), "n_nanite_actors": sum(1 for r in rows.values() if r["nanite"]),
            "nanite_culling_bounds_inflation_cm_by_piece": dict(sorted(infl.items())),
            "nanite_fallback_box_cm_by_piece": {k: [[round(x, 3) for x in v[0]], [round(x, 3) for x in v[1]]]
                                                for k, v in sorted(fbox.items())},
            "failures": fails, "passed": len(rows) == len(L["instances"]) and not fails}


def expected_ledges(x0, x1, y0, y1, z1):
    X0, X1, Y0, Y1, Z = x0 * 100.0, x1 * 100.0, -y1 * 100.0, -y0 * 100.0, z1 * 100.0
    return {"Ledge_1": [[X0, Y0, Z], [X1, Y0, Z], [0.0, -1.0, 0.0]], "Ledge_2": [[X0, Y1, Z], [X1, Y1, Z], [0.0, 1.0, 0.0]],
            "Ledge_3": [[X0, Y0, Z], [X0, Y1, Z], [-1.0, 0.0, 0.0]], "Ledge_4": [[X1, Y0, Z], [X1, Y1, Z], [1.0, 0.0, 0.0]]}


def place_markers():
    cls = EAL.load_blueprint_class(C.TRAVERSABLE_BLOCK)
    out = []
    for m in L["traversal_markers"]:
        x0, x1, y0, y1, z0, z1 = m["box"]
        a = EAS.spawn_actor_from_class(cls, V((x0 * 100.0, -y1 * 100.0, z0 * 100.0)), rot())
        a.set_actor_scale3d(V((x1 - x0, y1 - y0, z1 - z0)))
        for comp in a.get_components_by_class(unreal.PrimitiveComponent):
            if isinstance(comp, unreal.StaticMeshComponent):
                comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
                comp.set_collision_response_to_all_channels(RESP["ignore"])
                comp.set_collision_response_to_channel(CH.ECC_TRAVERSABLE, RESP["block"])
                setp(comp, "cast_shadow", False)
        a.set_actor_hidden_in_game(True)
        tag(a, "TRV_" + m["name"], "Dojo/Traversal", "DJ_Traversal", "route_" + m["route"])
        want, err = expected_ledges(x0, x1, y0, y1, z1), 0.0
        for sp in a.get_components_by_class(unreal.SplineComponent):
            p0 = sp.get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            p1 = sp.get_location_at_spline_point(1, unreal.SplineCoordinateSpace.WORLD)
            up = sp.get_up_vector_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            w = want.get(sp.get_name())
            if w is None:
                err = 1e9
                continue
            err = max(err, max(abs(g - q) for g, q in zip([p0.x, p0.y, p0.z, p1.x, p1.y, p1.z], w[0] + w[1])),
                      100.0 * max(abs(g - q) for g, q in zip([up.x, up.y, up.z], w[2])))
        out.append({"name": m["name"], "route": m["route"], "ledge_err_cm": round(err, 3), "top_z_cm": round(z1 * 100, 1)})
    return out


CLOUD_PARENT = "/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud"
CLOUD_MI = "/Game/DojoKit/Showcase/Materials/MI_DJ_SunsetClouds"


def cloud_mi(scalars, vectors):
    """Round 3 fix f1: our own instance of the engine's simple volumetric cloud material (the engine asset is never
    edited), created or updated here and saved."""
    MEL = unreal.MaterialEditingLibrary
    mi = unreal.load_asset(CLOUD_MI)
    if mi is None:
        d, n = CLOUD_MI.rsplit("/", 1)
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.MaterialInstanceConstant,
                                                                     unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(CLOUD_PARENT))
    for k, v in scalars.items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in vectors.items():
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*[float(x) for x in v]))
    MEL.update_material_instance(mi)
    EAL.save_asset(CLOUD_MI, only_if_is_dirty=False)
    REP["cloud_mi"] = {"path": CLOUD_MI, "scalars": scalars, "vectors": vectors}
    return mi


SKY_TEX_SRC = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\DojoKit\Showcase\Textures\T_DJS_SunsetClouds.png")
SKY_DIR = "/Game/DojoKit/Showcase"
SKY_MAT = SKY_DIR + "/Materials/M_DJS_SkyClouds"


def sky_dome(cfg):
    """Round 3 fix f1: the painted sunset cloud layer (showcase/make_sky_clouds.py) on the engine's SM_SkySphere
    (radius 40.96 m, scaled), an unlit translucent two-sided material that maps the texture by the view direction from
    the dome centre (u = atan2(y, x) / 2 pi + 0.5, v = 1 - asin(z) / (pi / 2)), so the mesh UVs do not matter. The
    SkyAtmosphere shows through the gaps. Showcase dressing only: NoCollision, no shadows."""
    MEL = unreal.MaterialEditingLibrary
    task = unreal.AssetImportTask()
    for k, v in (("filename", str(SKY_TEX_SRC)), ("destination_path", SKY_DIR + "/Textures"),
                 ("destination_name", "T_DJS_SunsetClouds"), ("automated", True), ("replace_existing", True),
                 ("save", True)):
        task.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.load_asset(SKY_DIR + "/Textures/T_DJS_SunsetClouds")
    setp(tex, "srgb", True)
    setp(tex, "address_y", unreal.TextureAddress.TA_CLAMP)
    setp(tex, "lod_group", unreal.TextureGroup.TEXTUREGROUP_SKYBOX)
    setp(tex, "never_stream", True)
    EAL.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    mat = unreal.load_asset(SKY_MAT)
    if mat is None:
        d, n = SKY_MAT.rsplit("/", 1)
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(mat)
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    setp(mat, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    setp(mat, "two_sided", True)
    fog_off = []
    for k in ("use_translucency_vertex_fog", "apply_fogging"):
        try:
            mat.set_editor_property(k, False)
            fog_off.append(k)
        except Exception:  # noqa: BLE001
            pass

    def node(cls, x, y, **kw):
        n = MEL.create_material_expression(mat, cls, x, y)
        for k, v in kw.items():
            n.set_editor_property(k, v)
        return n

    wp = node(unreal.MaterialExpressionWorldPosition, -1600, 0)
    op = node(unreal.MaterialExpressionObjectPositionWS, -1600, 200)
    sub = node(unreal.MaterialExpressionSubtract, -1400, 100)
    MEL.connect_material_expressions(wp, "", sub, "A")
    MEL.connect_material_expressions(op, "", sub, "B")
    nrm = node(unreal.MaterialExpressionNormalize, -1250, 100)
    MEL.connect_material_expressions(sub, "", nrm, "")
    mx = node(unreal.MaterialExpressionComponentMask, -1100, 0, r=True, g=False, b=False, a=False)
    my = node(unreal.MaterialExpressionComponentMask, -1100, 100, r=False, g=True, b=False, a=False)
    mz = node(unreal.MaterialExpressionComponentMask, -1100, 200, r=False, g=False, b=True, a=False)
    for m_ in (mx, my, mz):
        MEL.connect_material_expressions(nrm, "", m_, "")
    at = node(unreal.MaterialExpressionArctangent2, -950, 50)
    MEL.connect_material_expressions(my, "", at, "Y")
    MEL.connect_material_expressions(mx, "", at, "X")
    u1 = node(unreal.MaterialExpressionMultiply, -800, 50, const_b=1.0 / (2.0 * math.pi))
    MEL.connect_material_expressions(at, "", u1, "A")
    u2 = node(unreal.MaterialExpressionAdd, -650, 50, const_b=0.5)
    MEL.connect_material_expressions(u1, "", u2, "A")
    zs = node(unreal.MaterialExpressionSaturate, -950, 200)
    MEL.connect_material_expressions(mz, "", zs, "")
    asn = node(unreal.MaterialExpressionArcsine, -800, 200)
    MEL.connect_material_expressions(zs, "", asn, "")
    v1 = node(unreal.MaterialExpressionMultiply, -650, 200, const_b=-2.0 / math.pi)
    MEL.connect_material_expressions(asn, "", v1, "A")
    v2 = node(unreal.MaterialExpressionAdd, -500, 200, const_b=1.0)
    MEL.connect_material_expressions(v1, "", v2, "A")
    uv = node(unreal.MaterialExpressionAppendVector, -400, 100)
    MEL.connect_material_expressions(u2, "", uv, "A")
    MEL.connect_material_expressions(v2, "", uv, "B")
    ts = node(unreal.MaterialExpressionTextureSample, -250, 100, texture=tex,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
              mip_value_mode=unreal.TextureMipValueMode.TMVM_MIP_LEVEL, const_mip_value=0)
    MEL.connect_material_expressions(uv, "", ts, "UVs")
    inten = node(unreal.MaterialExpressionScalarParameter, -250, 350, parameter_name="Intensity",
                 default_value=float(cfg.get("intensity", 1.0)))
    em = node(unreal.MaterialExpressionMultiply, 0, 100)
    MEL.connect_material_expressions(ts, "RGB", em, "A")
    MEL.connect_material_expressions(inten, "", em, "B")
    opm = node(unreal.MaterialExpressionScalarParameter, -250, 450, parameter_name="OpacityMult",
               default_value=float(cfg.get("opacity", 1.0)))
    op2 = node(unreal.MaterialExpressionMultiply, 0, 300)
    MEL.connect_material_expressions(ts, "A", op2, "A")
    MEL.connect_material_expressions(opm, "", op2, "B")
    MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(op2, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    EAL.save_asset(SKY_MAT, only_if_is_dirty=False)
    c = cfg.get("centre", (22.0, 18.0, 0.0))
    sc = float(cfg.get("radius_m", 2400.0)) / 40.96
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(c)), rot())
    a.set_actor_scale3d(V((sc, sc, sc)))
    smc = a.static_mesh_component
    smc.set_static_mesh(unreal.load_asset("/Engine/EngineSky/SM_SkySphere"))
    smc.set_material(0, mat)
    smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    smc.set_collision_profile_name("NoCollision")
    setp(smc, "cast_shadow", False)
    setp(smc, "affect_distance_field_lighting", False)
    return {"material": SKY_MAT, "texture": tex.get_path_name(), "centre_m": list(c), "radius_m": round(sc * 40.96, 2),
            "intensity": cfg.get("intensity", 1.0), "opacity": cfg.get("opacity", 1.0), "fog_off": fog_off,
            "actor": tag(a, "SkyClouds_Dome", "Dojo/Lighting", "DJ_SkyDome").get_actor_label()}


def environment():
    env = {}
    s = L["sun"]
    d = C.dir_bl_to_ue(s["travel_dir"])
    pitch, yaw = C.pitch_yaw_of(d)
    a = EAS.spawn_actor_from_class(unreal.DirectionalLight, V((2200.0, -1800.0, 1500.0)), rot(pitch, yaw))
    comp = a.get_editor_property("directional_light_component")
    for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity", float(s["lux"])),
                 ("use_temperature", True), ("temperature", float(s["kelvin"])), ("atmosphere_sun_light", True),
                 ("light_source_angle", 0.53), ("cast_shadows", True), ("forward_shading_priority", 1)):
        setp(comp, k, v)
    tag(a, "Sun_Sunset", "Dojo/Lighting")
    f = a.get_actor_forward_vector()
    env["sun"] = {"pitch": round(pitch, 3), "yaw": round(yaw, 3), "lux": s["lux"], "kelvin": s["kelvin"],
                  "forward_ue": [round(f.x, 4), round(f.y, 4), round(f.z, 4)], "expected": [round(v, 4) for v in d]}
    a = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V((0, 0, 0)), rot())
    sac = a.get_component_by_class(unreal.SkyAtmosphereComponent)
    setp(sac, "sky_luminance_factor", unreal.LinearColor(*SKY_FACTOR, 1.0))
    tag(a, "SkyAtmosphere", "Dojo/Lighting")
    if S.CLOUDS:   # round 3 fix f1: a volumetric cloud layer lit by the low sun (the judges' sky blocker)
        a = EAS.spawn_actor_from_class(unreal.VolumetricCloud, V((0, 0, 0)), rot())
        vc = a.get_component_by_class(unreal.VolumetricCloudComponent)
        for k, v in S.CLOUDS.items():
            if k in ("material_scalars", "material_vectors"):
                continue
            setp(vc, k, v)
        if S.CLOUDS.get("material_scalars") or S.CLOUDS.get("material_vectors"):
            setp(vc, "material", cloud_mi(S.CLOUDS.get("material_scalars", {}), S.CLOUDS.get("material_vectors", {})))
        mi = vc.get_editor_property("material")
        env["clouds"] = {"material": mi.get_path_name() if mi else None,
                         **{k: v for k, v in S.CLOUDS.items() if k not in ("material", "material_scalars")}}
        tag(a, "VolumetricCloud", "Dojo/Lighting")
    if S.SKY_DOME:
        env["sky_dome"] = sky_dome(S.SKY_DOME)
    a = EAS.spawn_actor_from_class(unreal.SkyLight, V((2200.0, -1800.0, 1200.0)), rot())
    slc = a.get_editor_property("light_component")
    for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE),
                 ("real_time_capture", True), ("intensity", float(S.SKYLIGHT_INTENSITY))):
        setp(slc, k, v)
    tag(a, "SkyLight", "Dojo/Lighting")
    a = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V((2200.0, -1800.0, 0.0)), rot())
    fc = a.get_editor_property("component")
    for k, v in (("fog_density", 0.02), ("fog_height_falloff", 0.12), ("enable_volumetric_fog", True),
                 ("volumetric_fog_scattering_distribution", 0.6), ("volumetric_fog_extinction_scale", 0.5),
                 ("start_distance", 1500.0)):
        setp(fc, k, v)
    tag(a, "ExponentialHeightFog", "Dojo/Lighting")
    a = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V((2200.0, -1800.0, 300.0)), rot())
    setp(a, "unbound", True)
    pp = a.get_editor_property("settings")
    items = [("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
             ("override_auto_exposure_bias", True), ("auto_exposure_bias", BIAS),
             ("override_auto_exposure_apply_physical_camera_exposure", True),
             ("auto_exposure_apply_physical_camera_exposure", False)]
    for k, v in PP.items():
        items += [("override_" + k, True), (k, unreal.Vector4(*v) if isinstance(v, tuple) else v)]
    for k, v in items:
        setp(pp, k, v)
    setp(a, "settings", pp)
    tag(a, "PostProcess_Dojo", "Dojo/Lighting")
    env["post_process"] = {"exposure": "manual", "bias_ev": BIAS, "grade": {k: list(v) if isinstance(v, tuple) else v
                                                                            for k, v in PP.items()},
                           "sky_luminance_factor": SKY_FACTOR, "skylight_intensity": S.SKYLIGHT_INTENSITY,
                           "lamp_scale": S.LAMP_SCALE}
    env["lights"] = []
    for li in L["lights"]:
        a = EAS.spawn_actor_from_class(unreal.PointLight, V(C.loc_cm(li["loc"])), rot())
        comp = a.get_editor_property("point_light_component")
        for k, v in (("mobility", unreal.ComponentMobility.MOVABLE), ("intensity_units", unreal.LightUnits.CANDELAS),
                     ("intensity", float(li["candela"]) * S.LAMP_SCALE), ("use_temperature", True),
                     ("temperature", float(li["kelvin"])),
                     ("attenuation_radius", li["radius_m"] * 100.0), ("source_radius", 3.0),
                     ("cast_shadows", bool(li["shadows"]))):
            setp(comp, k, v)
        tag(a, li["name"], "Dojo/Lighting/Lamps", "DJ_Lamp")
        env["lights"].append({"name": li["name"], "loc_cm": list(C.loc_cm(li["loc"])),
                              "cd": round(li["candela"] * S.LAMP_SCALE, 2), "cd_blender_parity": li["candela"],
                              "kelvin": li["kelvin"]})
    env["player_starts"] = []
    for ps in L["player_starts"]:
        x, y, _z = C.loc_cm(ps["loc"])
        a = EAS.spawn_actor_from_class(unreal.PlayerStart, V((x, y, 95.0)), rot(yaw=C.yaw_deg(ps["rot_z"])))
        setp(a, "player_start_tag", unreal.Name(ps["tag"]))
        tag(a, ps["name"], "Dojo/Gameplay", ps["tag"])
        env["player_starts"].append({"name": ps["name"], "loc_cm": [x, y, 95.0]})
    return env


def cameras():
    out = {}
    for c in L["cameras"]:
        loc = C.loc_cm(c["loc"])
        pitch, yaw = C.pitch_yaw_of(C.dir_bl_to_ue([a - b for a, b in zip(c["look_at"], c["loc"])]))
        a = EAS.spawn_actor_from_class(unreal.CineCameraActor, V(loc), rot(pitch, yaw))
        cc = a.get_cine_camera_component()
        w, h = c["out_wh"]
        fb = cc.get_editor_property("filmback")
        fb.set_editor_property("sensor_width", 36.0)
        fb.set_editor_property("sensor_height", 36.0 * h / w)
        setp(cc, "filmback", fb)
        setp(cc, "current_focal_length", 18.0 / math.tan(math.radians(c["hfov_deg"]) / 2.0))
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        setp(cc, "focus_settings", fs)
        tag(a, c["name"], "Dojo/Cameras")
        out[c["name"]] = {"loc_cm": loc, "pitch": round(pitch, 3), "yaw": round(yaw, 3), "hfov": c["hfov_deg"]}
    return out


def world_settings():
    ws = world().get_world_settings()
    gm = EAL.load_blueprint_class(C.DOJO_GAME_MODE)
    ok = setp(ws, "default_game_mode", gm) and setp(ws, "kill_z", -1000.0)
    return {"game_mode": gm.get_path_name() if gm else None, "kill_z": -1000.0, "ok": ok}


def save():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les.save_current_level():
            return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"save_current_level: {exc}")
    return bool(unreal.EditorLoadingAndSavingUtils.save_map(world(), C.LEVEL))


def delete_retired():
    """Round 3: delete the meshes a round retired (layout 'retired_meshes', e.g. the path slabs the paver courses
    replace) once the saved level no longer uses them. A mesh something still references is kept and reported."""
    out = {}
    used = {i["piece"] for i in L["instances"]}
    for piece, path in sorted(L.get("retired_meshes", {}).items()):
        if piece in used:
            out[piece] = "still placed: kept"
            continue
        if not EAL.does_asset_exist(path):
            out[piece] = "absent"
            continue
        refs = [str(r) for r in EAL.find_package_referencers_for_asset(path, False)]
        if refs:
            out[piece] = {"kept, referenced by": refs[:8]}
            continue
        out[piece] = "deleted" if EAL.delete_asset(path) else "delete failed"
    return out


def main():
    t0 = time.time()
    try:
        open_level()
        placed = place_meshes()
        REP["mesh_actors"] = len(placed)
        REP["bounds_gate"] = bounds_gate(placed)
        REP["markers"] = place_markers()
        REP["marker_max_ledge_err_cm"] = max(m["ledge_err_cm"] for m in REP["markers"])
        REP["environment"] = environment()
        REP["cameras"] = cameras()
        REP["world_settings"] = world_settings()
        REP["n_actors"] = len(EAS.get_all_level_actors())
        REP["saved"] = save()
        REP["retired_meshes"] = delete_retired() if REP["saved"] else {"skipped": "level not saved"}
        sun = REP["environment"]["sun"]
        REP["sun_direction_ok"] = max(abs(p - q) for p, q in zip(sun["forward_ue"], sun["expected"])) < 1e-3
        REP["passed"] = (REP["bounds_gate"]["passed"] and REP["saved"] and REP["sun_direction_ok"]
                         and REP["marker_max_ledge_err_cm"] <= TOL_CM and REP["world_settings"]["ok"]
                         and not REP["setp_failed"] and not REP["notes"])
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        REP["passed"] = False
    REP["sec"] = round(time.time() - t0, 1)
    S.write_json(S.SC_OUT / "level.json", REP)
    g = REP.get("bounds_gate", {})
    unreal.log(f"DJ_STEP_DONE sc_level passed={REP['passed']} meshes={REP.get('mesh_actors')} "
               f"markers={len(REP.get('markers', []))} gate_max_err_cm={g.get('max_err_cm_all')} "
               f"gate_fails={len(g.get('failures', {}))} saved={REP.get('saved')}")


main()
