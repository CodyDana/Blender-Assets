"""One-off patch (spike maintenance, 3.8.1): the Unreal texture gates take the expected size from the shipped
PNG's own header instead of a hard-coded 2048 x 2048 (the spike's maps are 2048 x 512; the stars' stay 2048 x 2048,
so their check is unchanged in effect).  UnrealCheck8/p3_readback.py and UnrealCheck10_SpikeVerify/summarize.py."""
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


HELPER = '''

def png_size(path):
    """(width, height) from a PNG's IHDR chunk (bytes 16..24): the size the shipped file declares."""
    head = Path(path).read_bytes()[:24]
    return [int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")]
'''

name = "UnrealCheck8/p3_readback.py"
p = W / name
s = p.read_text(encoding="utf-8")
rep('''                    checks["size_2048"] = info.get("size") == [2048, 2048]''',
    '''                    rec["png_size"] = png_size(png)          # 3.8.1: the spike's maps are 2048 x 512
                    checks["size_equals_png"] = info.get("size") == rec["png_size"]
                    checks["size_power_of_two"] = all(v > 0 and v & (v - 1) == 0 for v in rec["png_size"])''')
rep('''

def main''', HELPER + '''

def main''')
if "from pathlib import Path" not in s:
    s = s.replace("import unreal", "import unreal\nfrom pathlib import Path", 1)
p.write_text(s, encoding="utf-8")

name = "UnrealCheck10_SpikeVerify/summarize.py"
p = W / name
s = p.read_text(encoding="utf-8")
rep('''          and (flip is None or info.get("flip_green_channel") == flip) and info.get("size") == [2048, 2048]''',
    '''          and (flip is None or info.get("flip_green_channel") == flip) and info.get("size") == png_size(rec["png"])''')
rep('''                "flip_green": info.get("flip_green_channel"), "lod_group": info.get("lod_group"), "size": info.get("size"),''',
    '''                "flip_green": info.get("flip_green_channel"), "lod_group": info.get("lod_group"), "size": info.get("size"),
                "png_size": png_size(rec["png"]),''')
rep('''# G7 textures''', HELPER.strip("\n") + '''


# G7 textures''')
if "from pathlib import Path" not in s:
    s = "from pathlib import Path\n" + s
p.write_text(s, encoding="utf-8")
print("patched UC8 p3_readback, UC10 summarize")
