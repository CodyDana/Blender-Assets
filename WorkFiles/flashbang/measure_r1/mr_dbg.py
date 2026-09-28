import sys
sys.argv = [sys.argv[0], "--", "sweep", r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1/mr_sweep_cfg.json", "x"]
src = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1/mr_render.py").read().replace('{"sweep": sweep, "row": row, "close": close}[MODE]()', '')
exec(src)
lod0 = load_lod0()
co, copies, hc = place_row(lod0, {v: -90 for v in VIEW_CX})
print("DBG hc", hc, co.location, co.rotation_euler)
for c in copies:
    print("DBG", c.name, c.matrix_world.translation, project(co, c.matrix_world.translation), c.hide_render, len(c.data.vertices), c.users_collection)
print("DBG mats", [m.name for m in lod0.data.materials], sc.camera)
