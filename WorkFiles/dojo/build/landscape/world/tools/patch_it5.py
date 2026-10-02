"""Iteration-5 patch: white water as a translucent foam surface over the rapids reach (the engine river material showed
no foam at 250-750 cm/s in it2-it4), Voxelize on the copied Fishermans firs (their masked needles thinned to bare poles
at 60+ m in it3 / it4: plan 3.11 asks for Voxelize). Idempotent."""
from pathlib import Path

D = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\landscape")


def patch(name, pairs):
    p = D / name
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s:
            continue
        assert s.count(old) == 1, (name, old[:90])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


patch("make_world_layout.py", [
    ('''def fx():''',
     '''def foam_strips():
    """The rapids' white water: one 1 m engine plane per ~6 m of the R4..R7.4 reach, 3 cm over the water surface, 85 %
    of the channel width, yawed along the flow, the foam material (M_DJL_RapidsFoam) panning down-stream in world UVs."""
    out = []
    R = G.RIVER
    idx = [j for j in range(0, len(R) - 3, 3) if 3.8 <= R[j, 6] <= 7.6]
    for k, j in enumerate(idx):
        a, b = R[j], R[min(j + 3, len(R) - 1)]
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        L = math.hypot(b[0] - a[0], b[1] - a[1]) + 1.2
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        wz = (a[2] + b[2]) / 2 + 0.03
        wid = 0.85 * (a[3] + b[3]) / 2
        out.append(rec("fx", f"RapidsFoam_{k + 1:02d}", "/Engine/BasicShapes/Plane", cx, cy, wz, yaw, [L, wid, 1.0],
                       folder="Landscape/Water/Foam", collision="none", shadow=False,
                       material="/Game/DojoLandscape/Materials/MI_DJL_RapidsFoam", key=round(float(a[6]), 3)))
    return out


def fx():'''),
    ('''    W["actors"] += la + pines() + rocks() + cherry() + boundary() + far_meshes()''',
     '''    W["actors"] += la + pines() + rocks() + cherry() + boundary() + far_meshes() + foam_strips()'''),
])

patch("dj_ls_materials.py", [
    ('''def rocks():''',
     '''def foam():
    """M_DJL_RapidsFoam: translucent lit white water on the rapids strips. Two layers of the engine's
    T_WaterFlow_01_Foam_Tiled (2K) panning down-stream (world UVs, the reach's mean flow direction), broken up by our
    T_DKF_Foam_M, faded at the strip's long edges (plane UV v)."""
    path = f"{LMAT}/M_DJL_RapidsFoam"
    m = get_or_create(path, unreal.Material, unreal.MaterialFactoryNew())
    reset(m, blend=unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    except Exception:  # noqa: BLE001
        pass
    g = G(m)
    xy = g.div(g.mask(g.wp(), "RG"), g.const(100.0))            # metres
    flow = g.const3((-0.63, 0.77, 0.0))                         # UE xy of the R4 -> R7 mean flow
    t = g.time()
    ft = tex("/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled")
    fm = tex("/Game/DojoKit/FX/Textures/T_DKF_Foam_M")
    uv1 = g.sub(g.div(xy, g.const(3.2)), g.mul(g.mask(flow, "RG"), g.mul(t, g.scalar("Speed1", 0.55))))
    uv2 = g.sub(g.div(xy, g.const(1.4)), g.mul(g.mask(flow, "RG"), g.mul(t, g.scalar("Speed2", 0.9))))
    f1 = g.t2d("Foam1", "L", ft, uv1, group="Foam")
    f2 = g.t2d("Foam2", "L", ft, uv2, group="Foam")
    br = g.t2d("Breakup", "L", fm, g.div(xy, g.const(9.0)), group="Foam")
    v = g.mask(g.uv(0), "G")
    edge = g.mul(g.smoothstep(v, 0.0, 0.22), g.smoothstep(g.sub(g.const(1.0), v), 0.0, 0.22))
    f = g.mul(g.add(g.mask((f1, "RGB"), "R"), g.mul(g.mask((f2, "RGB"), "R"), g.const(0.7))), g.mask((br, "RGB"), "R"))
    op = g.sat(g.mul(g.mul(g.smoothstep(f, g.scalar("Threshold", 0.25), g.scalar("Soft", 0.45)), edge),
                     g.scalar("Opacity", 0.9)))
    g.out(g.vector("FoamColour", (0.82, 0.86, 0.86)), MP.MP_BASE_COLOR)
    g.out(g.const(0.6), MP.MP_ROUGHNESS)
    g.out(op, MP.MP_OPACITY)
    finish(m, path)
    make_mi(f"{LMAT}/MI_DJL_RapidsFoam", m)


def fir_voxelize():
    """Plan 3.11: the forest firs Voxelize (our DojoLab copies only; the vault source is never written)."""
    try:
        sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sms = None
    sms = sms or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    rec = {}
    for i in range(1, 9):
        p = f"/Game/Fishermans_Cabin/Meshes/Foliage/Tree/SM_Fir_Tree_0{i}"
        mesh = unreal.load_asset(p)
        ns = mesh.get_editor_property("nanite_settings")
        before = str(ns.get_editor_property("shape_preservation")).split(".")[-1].split(":")[0]
        if "VOXEL" not in before.upper():
            ns.set_editor_property("shape_preservation", unreal.NaniteShapePreservation.VOXELIZE)
            sms.set_nanite_settings(mesh, ns, True)
            EAL.save_loaded_asset(mesh, False)
        after = str(mesh.get_editor_property("nanite_settings").get_editor_property("shape_preservation")).split(".")[-1]
        rec[p] = {"before": before, "after": after.split(":")[0]}
    REP["fir_voxelize"] = rec


def rocks():'''),
    ('''("rocks", rocks), ("firs", firs), ("fx", fx)):''',
     '''("rocks", rocks), ("firs", firs), ("foam", foam), ("fir_voxelize", fir_voxelize), ("fx", fx)):'''),
])
print("PATCH_IT5 ok")
