"""Iteration-4 patch (after the it3 captures): billboard slot fix (swap by the original material, not by index), greener
grass, meadow only on the valley floor, the canopy blend nearer, white-water velocities + MaxFlowVelocity, more far-bank
cover. Idempotent."""
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
    ('''                        "slot_materials": {"1": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves"}})''',
     '''                        "material_swaps": {"MI_Tree_Leaves": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves"}})'''),
    ('''                "cull_cm": 0, "slot_materials": {"0": "/Game/DojoLandscape/Materials/MI_DJL_FirBillboard"}})''',
     '''                "cull_cm": 0, "material_swaps": {"MI_Tree_Leaves": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves",
                                                 "MI_Tree_Billboard": "/Game/DojoLandscape/Materials/MI_DJL_FirBillboard"}})'''),
    ('''    # far bank bush line
    for key in np.linspace(3.0, 10.0, 22):''',
     '''    # far bank bush line (it4: 22 -> 60, two rows)
    for key in np.concatenate([np.linspace(3.0, 10.0, 34), np.linspace(3.2, 9.8, 26)]):'''),
    ('''        d = wid / 2 + RNG.uniform(2.5, 6.0)
        x, y = cx - ny / n * d, cy + nx / n * d
        m = bush[int(RNG.integers(0, 10))]''',
     '''        d = wid / 2 + RNG.uniform(2.0, 11.0)
        x, y = cx - ny / n * d, cy + nx / n * d
        m = bush[int(RNG.integers(0, 10))]'''),
])
patch("ls_geo.py", [(
    '''VEL = {"R0": 100, "R1": 100, "R2": 110, "R3": 120, "R4": 250, "R5": 330, "R6": 350, "R7": 280, "R8": 110,''',
    '''# it4: the rapids reach doubled (the engine river material only foams near its MaxFlowVelocity; the plan's 250-350
# cm/s left the white water invisible in it2 / it3): a visual flow value, the water depth / levels unchanged
VEL = {"R0": 100, "R1": 100, "R2": 110, "R3": 140, "R4": 520, "R5": 700, "R6": 750, "R7": 600, "R8": 160,''')])
patch("dj_ls_world.py", [(
    '''    for i, mp in (g.get("slot_materials") or {}).items():
        mi = unreal.load_asset(mp)
        if mi is not None and int(i) < len(m.get_editor_property("static_materials")):
            ism.set_material(int(i), mi)''',
    '''    for i, sm in enumerate(m.get_editor_property("static_materials")):
        cur = sm.get_editor_property("material_interface")
        new = (g.get("material_swaps") or {}).get(cur.get_name() if cur else "")
        if new:
            ism.set_material(i, unreal.load_asset(new))''')])
patch("dj_ls_materials.py", [
    ('''        ("Grass", f"{FT}/Ground_Grass/T_Grass_D", f"{FT}/Ground_Grass/T_Grass_N", 4.0, (0.85, 0.9, 0.7)),''',
     '''        ("Grass", f"{FT}/Ground_Grass/T_Grass_D", f"{FT}/Ground_Grass/T_Grass_N", 4.0, (0.55, 0.74, 0.46)),'''),
    ('''    far_w = g.mul(g.smoothstep(dist, 21000.0, 42000.0), g.sub(g.const(1.0), (mk, "A")))''',
     '''    far_w = g.mul(g.smoothstep(dist, 13000.0, 32000.0), g.sub(g.const(1.0), (mk, "A")))'''),
    ('''    low = g.sub(g.const(1.0), g.smoothstep(zm, 30.0, 90.0))''',
     '''    low = g.sub(g.const(1.0), g.smoothstep(zm, 2.0, 14.0))'''),
    ('''            scalars={"Foam Boost": 3.0, "FoamContrast": 2.0, "River Foam Scale": 700.0,
                     "River Flowmap Detection Velocity": 32.0, "Foam powr": 0.12})''',
     '''            scalars={"Foam Boost": 3.0, "FoamContrast": 2.0, "River Foam Scale": 700.0,
                     "River Flowmap Detection Velocity": 32.0, "Foam powr": 0.12, "MaxFlowVelocity": 700.0})'''),
])
print("PATCH_IT4 ok")
