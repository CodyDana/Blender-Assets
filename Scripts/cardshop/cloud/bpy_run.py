"""Run a Blender script under the pip `bpy` module the way `blender -b --python X -- args` would."""
import runpy, sys
import bpy  # noqa: F401  (must load before bmesh/mathutils)
script = sys.argv[1]
rest = sys.argv[2:]
sys.argv = [script] + (["--"] + rest[1:] if rest[:1] == ["--"] else ([] if not rest else ["--"] + rest))
bpy.ops.wm.read_factory_settings(use_empty=False)
runpy.run_path(script, run_name="__main__")
