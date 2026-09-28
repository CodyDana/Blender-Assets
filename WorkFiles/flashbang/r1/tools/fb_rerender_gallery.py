"""Re-render the hero / back / wire shots from the SAVED Assets/Flashbang.blend (baked maps packed in it), without
touching the exports (a rebuild would re-write the FBX bytes the Unreal check verified)."""
import sys
from pathlib import Path
P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts")); sys.path.insert(0, str(P / "Scripts/props"))
import bpy
bpy.ops.wm.open_mainfile(filepath=str(P / "Assets/Flashbang.blend"))
from props_lib import flashbang_gallery as GAL
R = P / "Renders/Flashbang"
lod0 = bpy.data.objects["SM_Flashbang_LOD0"]
GAL.render_hero(lod0, R / "flashbang_hero.png", samples=384)
GAL.render_hero(lod0, R / "flashbang_back.png", samples=384, az=120.0)
GAL.render_wire(lod0, R / "flashbang_wire.png", samples=64)
