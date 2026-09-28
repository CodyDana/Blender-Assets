p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
new = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/exp/leaf_section.txt", encoding="utf-8").read()
a = s.index("def development_uv(")
b = s.index("# =========================================================================== rivet (lathe)")
s = s[:a] + new + s[b:]
old = '''    side = build_leaf(mb, spec, tpl)
    build_rivet(mb, spec, plan)
    info = {"lod": lod, "triangles": mb.triangles(), "vertices": len(mb.P), "parts": mb.part_triangles(),
            "leaf_uv_side_mm": round(side, 3), "stick_ppmm": round(s_px, 4)}'''
assert old in s
s = s.replace(old, '''    leaf_info = build_leaf(mb, spec, tpl)
    build_rivet(mb, spec, plan)
    info = {"lod": lod, "triangles": mb.triangles(), "vertices": len(mb.P), "parts": mb.part_triangles(),
            **leaf_info, "stick_ppmm": round(s_px, 4)}''')
s = s.replace('"SLOTS", "LEAF_BACK_OFFSET_MM", "development_uv"]', '"SLOTS", "LEAF_BACK_OFFSET_MM", "leaf_corners", "leaf_uv_layout"]')
open(p, "w", encoding="utf-8").write(s)
print("patched")
