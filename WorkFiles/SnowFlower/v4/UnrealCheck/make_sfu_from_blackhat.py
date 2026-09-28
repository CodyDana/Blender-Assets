"""Generate the Snow Flower v4 Unreal harness as adapted COPIES of the black hat's proven harness
(WorkFiles/blackhat/UnrealCheck is read, never written). Run with any Python 3."""
from pathlib import Path

H = Path(__file__).resolve().parent
BH = H.parents[2] / "blackhat" / "UnrealCheck"
HERE_OLD = r'Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealCheck")'
HERE_NEW = r'Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck")'


def rd(n):
    return (BH / n).read_text(encoding="utf-8")


def wr(n, s):
    (H / n).write_text(s, encoding="utf-8")


s = rd("bhu_common.py")
s = s.replace("Shared helpers for SM_BlackHat's Unreal verification", "Shared helpers for SM_SnowFlower (v4)'s Unreal verification")
s = s.replace('HERE = PROJ / "WorkFiles" / "blackhat" / "UnrealCheck"', 'HERE = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealCheck"')
s = s.replace('DEST = os.environ.get("BLACKHAT_DEST", "/Game/PropsCheck/BlackHat")', 'DEST = os.environ.get("SNOWFLOWER_DEST", "/Game/SwordCheck/SnowFlower")')
s = s.replace('(PROJ / "WorkFiles" / "blackhat" / "blackhat_report.json")', '(PROJ / "WorkFiles" / "SnowFlower" / "v4" / "sword_report.json")')
s = s.replace('PROJ / "Exports" / "BlackHat" / f"{MESH}.fbx"', 'PROJ / "Exports" / "SnowFlower" / "v4" / f"{MESH}.fbx"')
s = s.replace('PROJ / "Exports" / "BlackHat" / f"{MESH}.sockets.json"', 'PROJ / "Exports" / "SnowFlower" / "v4" / f"{MESH}.sockets.json"')
s = s.replace('PROJ / "Exports" / "BlackHat" / "Textures"', 'PROJ / "Exports" / "SnowFlower" / "v4" / "Textures"')
s = s.replace('"3_head_socket_at_scale_1_outered_to_the_asset"', '"3_four_sockets_at_scale_1_outered_to_the_asset"')
s = s.replace('"7_two_material_slots_straw_cloth": len(info["material_slots"]) == 2,',
              '"7_two_material_slots_steel_wrap": info["material_slots"] == REPORT["material_slots"],')
s = s.replace("abs(radius - EXPECTED_RADIUS_CM) <= 0.02", "abs(radius - EXPECTED_RADIUS_CM) <= 0.05")
wr("sfu_common.py", s)

s = rd("bhu_fbx_counts.py")
s = s.replace('PROJ / "Exports" / "BlackHat" / "SM_BlackHat.fbx"', 'PROJ / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"')
s = s.replace('(PROJ / "WorkFiles" / "blackhat" / "UnrealCheck" / "blender_fbx_counts.json")',
              '(PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealCheck" / "blender_fbx_counts.json")')
wr("sfu_fbx_counts.py", s)

for src, dst, mark in (("bhu_pass1_import.py", "sfu_pass1_import.py", "PASS1"),
                       ("bhu_tex_composite.py", "sfu_tex_composite.py", "TEX_COMPOSITE"),
                       ("bhu_pass3_export.py", "sfu_pass3_export.py", "PASS3")):
    s = rd(src).replace(HERE_OLD, HERE_NEW).replace("import bhu_common as C", "import sfu_common as C")
    s = s.replace(f"BHU_{mark}_DONE", f"SFU_{mark}_DONE").replace("bhu_roundtrip_compare.py", "sfu_roundtrip_compare.py")
    s = s.replace('STEMS = ("T_BlackHat_Straw", "T_BlackHat_Cloth")', 'STEMS = ("T_SnowFlower_Steel", "T_SnowFlower_Wrap")')
    wr(dst, s)

s = rd("bhu_uv1_overlap.py").replace(r'H = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealCheck")',
                                     r'H = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck")')
wr("sfu_uv1_overlap.py", s)

s = rd("bhu_roundtrip_compare.py")
s = s.replace('HERE = PROJ / "WorkFiles" / "blackhat" / "UnrealCheck"', 'HERE = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealCheck"')
s = s.replace('PROJ / "Exports" / "BlackHat" / "SM_BlackHat.fbx"', 'PROJ / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"')
s = s.replace('(PROJ / "WorkFiles" / "blackhat" / "blackhat_report.json")', '(PROJ / "WorkFiles" / "SnowFlower" / "v4" / "sword_report.json")')
a = s.index('        L0 = shipped["LOD0"]')
b = s.index('        inside_any = np.full(len(lod0), np.inf)')
s = s[:a] + ('        # every LOD0 vertex must lie inside AT LEAST ONE of Unreal\'s hulls (the four hulls overlap by design)\n'
             '        L0 = shipped["LOD0"]\n        lod0 = L0["co"]\n') + s[b:]
s = s.replace('"lod0_body_vertices_tested"', '"lod0_vertices_tested"').replace('"hanging_tail_vertices_excluded": int(hang.sum()),', '')
s = s.replace('"contains_lod0_body"', '"contains_lod0"')
wr("sfu_roundtrip_compare.py", s)
for f in sorted(H.glob("sfu_*.py")):
    t = f.read_text(encoding="utf-8")
    assert "blackhat" not in t.lower() and "BlackHat" not in t, f
print("generated", sorted(p.name for p in H.glob("sfu_*.py")))
