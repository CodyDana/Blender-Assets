"""Iteration-3 patch (after the it2 captures): lumpy banks, far-bank firs, pebble material, billboard density,
distant forest floor + canopy, fir tint MIs, water foam, the PeaksOverHall camera. Idempotent (skips applied hunks)."""
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


patch("make_terrain.py", [(
    '''    er = load_stamp("T_Land_Erosion00")
    if rough and er is not None:
        amp = G.smoothstep(15, 70, dp) * np.clip((N + 2.0) / 15.0, 0.25, 1.0)''',
    '''    er = load_stamp("T_Land_Erosion00")
    if rough and er is not None:
        # the banks: lumpy, not a levee (a 26 m stamp tile, 1.3 m, fading in from the water and out by 60 m)
        bank = G.smoothstep(0.5, 4.0, dp) * (1 - G.smoothstep(25.0, 60.0, dp))
        N = (N + 1.3 * bank * tiled_stamp(er, X, Y, 26.0, 2.3, (5.0, 9.0))
             + 0.5 * bank * tiled_stamp(er, X, Y, 9.0, 0.4, (1.0, 2.0)))
        amp = G.smoothstep(15, 70, dp) * np.clip((N + 2.0) / 15.0, 0.25, 1.0)''')])

patch("make_world_layout.py", [
    ('''      ("FZ3_east_valley", [(92, -80), (260, -70), (330, 320), (140, 270), (104, 95), (88, 20)])]''',
     '''      ("FZ3_east_valley", [(92, -80), (260, -70), (330, 320), (140, 270), (104, 95), (88, 20)]),
      # build addition: the far bank E1 (plan 3.6) carried no trees and read as a bare levee; firs 14 m or more from
      # the water (the cherry-slot row keeps its clearances, the camera wedge stays open)
      ("FZ3b_far_bank", [(70, 45), (69, 15), (65, -20), (45, -27), (33, -38), (27, -52), (45, -75), (100, -70),
                         (92, 20), (100, 95), (80, 60)])]'''),
    ('''        else:
            def dens(X, Y):''',
     '''        elif zid.startswith("FZ3b"):
            def dens(X, Y):
                D, WZ, WID = G.river_fields(X, Y)[:3]
                return np.where((D - WID / 2) < 14.0, 0.0, 25.0 / 70.0)
        else:
            def dens(X, Y):'''),
    ('''                    "folder": "Landscape/Cover", "collision": "none", "shadow": False, "bury_m": 0.03, "cull_cm": 6000,
                    "material": ROCK_MI})''',
     '''                    "folder": "Landscape/Cover", "collision": "none", "shadow": False, "bury_m": 0.03, "cull_cm": 6000})'''),
    ('''dens = np.clip(1.0 - (r - 230.0) / 5000.0, 0.45, 1.0) * 0.15''',
     '''dens = np.clip(1.0 - (r - 230.0) / 5000.0, 0.45, 1.0) * 0.30'''),
    ('''                        "folder": "Landscape/Forest", "collision": "block", "shadow": True, "wpo_disable_cm": 6000.0,
                        "bury_m": 0.6, "cull_cm": 0})''',
     '''                        "folder": "Landscape/Forest", "collision": "block", "shadow": True, "wpo_disable_cm": 6000.0,
                        "bury_m": 0.6, "cull_cm": 0,
                        "slot_materials": {"1": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves"}})'''),
    ('''                "rows": bb, "folder": "Landscape/Forest", "collision": "none", "shadow": False, "bury_m": 0.3,
                "cull_cm": 0})''',
     '''                "rows": bb, "folder": "Landscape/Forest", "collision": "none", "shadow": False, "bury_m": 0.3,
                "cull_cm": 0, "slot_materials": {"0": "/Game/DojoLandscape/Materials/MI_DJL_FirBillboard"}})'''),
    ('''    Gm = np.zeros(X.shape)
    for zid, poly in FZ:
        Gm = np.maximum(Gm, G.poly_contains(X, Y, poly).astype(float))''',
     '''    Gm = np.zeros(X.shape)
    for zid, poly in FZ:
        Gm = np.maximum(Gm, G.poly_contains(X, Y, poly).astype(float))
    # the hills beyond the near field are forest floor under the billboard forest (plan FZ4: canopy beyond)
    Rr = np.hypot(X - 22.0, Y - 18.0)
    Gm = np.maximum(Gm, G.smoothstep(180.0, 260.0, Rr) * (dp > 8.0))'''),
])

patch("dj_ls_world.py", [(
    '''    if g.get("material"):
        mi = unreal.load_asset(g["material"])
        for i in range(len(m.get_editor_property("static_materials"))):
            ism.set_material(i, mi)
    bmin, _ = _BB[path]''',
    '''    if g.get("material"):
        mi = unreal.load_asset(g["material"])
        for i in range(len(m.get_editor_property("static_materials"))):
            ism.set_material(i, mi)
    for i, mp in (g.get("slot_materials") or {}).items():
        mi = unreal.load_asset(mp)
        if mi is not None and int(i) < len(m.get_editor_property("static_materials")):
            ism.set_material(int(i), mi)
    bmin, _ = _BB[path]''')])

patch("dj_ls_materials.py", [
    ('''def rocks():''',
     '''def firs():
    """The Fishermans fir needles carry a warm Color Multiply (2.0, 1.3, 0.43) that read yellow at sunset; the
    reference's slope conifers are dark blue-green: child MIs, the pack's MIs untouched."""
    base = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Foliage/MI_Tree_Leaves")
    make_mi(f"{LMAT}/MI_DJL_FirLeaves", base, vectors={"Color Multiply": [0.62, 0.86, 0.55, 1.0]})
    bb = unreal.load_asset("/Game/Fishermans_Cabin/Materials/Material_Instances/Foliage/MI_Tree_Billboard")
    vn = [str(n) for n in MEL.get_vector_parameter_names(bb)]
    REP["billboard_params"] = {"vectors": vn, "scalars": [str(n) for n in MEL.get_scalar_parameter_names(bb)]}
    vec = {"Color Multiply": [0.62, 0.86, 0.55, 1.0]} if "Color Multiply" in vn else {}
    make_mi(f"{LMAT}/MI_DJL_FirBillboard", bb, vectors=vec)


def rocks():'''),
    ('''("landscape", landscape), ("water", water), ("rocks", rocks), ("fx", fx)):''',
     '''("landscape", landscape), ("water", water), ("rocks", rocks), ("firs", firs), ("fx", fx)):'''),
    ('''            vectors={"Absorption": [ab[0] * 1.2, 260.0, 320.0, ab[3]],
                     "Scattering": [0.35, 1.0, 0.9, sc[3]]})''',
     '''            vectors={"Absorption": [ab[0] * 1.2, 260.0, 320.0, ab[3]],
                     "Scattering": [0.35, 1.0, 0.9, sc[3]]},
            # white water: more, finer, harder foam on the fast reach (velocity-driven in the engine graph)
            scalars={"Foam Boost": 3.0, "FoamContrast": 2.0, "River Foam Scale": 700.0,
                     "River Flowmap Detection Velocity": 32.0, "Foam powr": 0.12})'''),
    ('''    canopy = g.mul(g.vector("Canopy", (0.022, 0.036, 0.026)), g.add(g.const(0.6), g.mul(noise, g.const(0.9))))''',
     '''    canopy = g.mul(g.vector("Canopy", (0.016, 0.028, 0.022)), g.add(g.const(0.55), g.mul(noise, g.const(0.9))))'''),
    ('''    forest_w = g.mul(tree, g.smoothstep(nz, 0.62, 0.78))''',
     '''    forest_w = g.mul(tree, g.smoothstep(nz, 0.5, 0.66))'''),
    ('''    col = g.mul(col, g.lerp(g.const(1.0), g.mul((macro, "RGB"), g.const(1.6)), g.scalar("MacroAmount", 0.35, "Mask")))''',
     '''    col = g.mul(col, g.lerp(g.const(1.0), g.mul((macro, "RGB"), g.const(1.6)), g.scalar("MacroAmount", 0.35, "Mask")))
    # plan FZ4: beyond the near field the forest is a canopy colour under the billboards (not bare grass)
    dxy = g.sub(xy, g.append(g.const(2200.0), g.const(-1800.0)))
    dist = g.un(unreal.MaterialExpressionLength, dxy)
    far_w = g.mul(g.smoothstep(dist, 21000.0, 42000.0), g.sub(g.const(1.0), (mk, "A")))
    canopy = g.mul(g.vector("Canopy", (0.016, 0.028, 0.022), "Look"),
                   g.add(g.const(0.55), g.mul(g.mask((macro, "RGB"), "R"), g.const(0.9))))
    col = g.lerp(col, canopy, g.mul(far_w, g.sub(g.const(1.0), g.mul(rock_w, g.const(0.6)))))'''),
])

patch("apply_landscape.py", [(
    '''    {"name": "CAM_PeaksOverHall", "loc": [22.0, -6.5, 1.2], "look_at": [260.0, 7400.0, 700.0], "hfov_deg": 50.0,''',
    '''    {"name": "CAM_PeaksOverHall", "loc": [30.0, -7.0, 1.2], "look_at": [1800.0, 7200.0, 1300.0], "hfov_deg": 50.0,''')])
print("PATCH_IT3 ok")
