p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
new = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/build_dev/exp/patch_solver_section.txt", encoding="utf-8").read()
a = s.index("# =========================================================================== the solver")
b = s.index("# =========================================================================== instruments")
s = s[:a] + new + s[b:]
s = s.replace('__all__ = ["FoldSolver", "LeafTemplate"', '__all__ = ["FoldSolver", "optimise_bind", "LeafTemplate"')
open(p, "w", encoding="utf-8").write(s)
print("patched")
