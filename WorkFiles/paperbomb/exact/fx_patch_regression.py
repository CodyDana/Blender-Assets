import io
d = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/regression/"
s = io.open(d + "snapshot.py", encoding="utf-8").read()
old = '''    hashed += copy_tree(PROJECT / "Scripts" / "props", dest / "scripts")
'''
new = '''    # the Recolour maps (make_paperbomb_recolour_maps.py + derive_constants.py) ship with the item
    rec = exports / "Textures" / "Recolour"
    if rec.is_dir():
        (dest / "recolour").mkdir()
        for src in sorted(p for p in rec.iterdir() if p.is_file()):
            shutil.copy2(src, dest / "recolour" / src.name)
            hashed.append(dest / "recolour" / src.name)

    # ONLY the paper bomb's scripts (2026-09-26): Scripts/props is shared with the other props'
    # chats, whose fan_/blackhat_/smokebomb_ files move on their own schedule and made every
    # compare report a false difference.  The shared modules the paper bomb build imports stay
    # in the set - a change there can move the paper bomb's bytes.
    hashed += copy_paperbomb_scripts(PROJECT / "Scripts" / "props", dest / "scripts")
'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''def main(argv=None) -> int:'''
new = '''#: the Scripts/props files the paper bomb build reads (its own + the shared modules it imports)
PB_SCRIPTS = ("build_paper_bomb.py", "props_lib/__init__.py", "props_lib/atlas.py", "props_lib/bake.py",
              "props_lib/gallery.py", "props_lib/geometry.py", "props_lib/measure.py",
              "props_lib/paper_material.py", "props_lib/render.py", "props_lib/sheet.py", "props_lib/spec.py",
              "props_lib/trace.py", "props_lib/art_metrics.py", "props_lib/photo_metrics.py")
PB_GLOBS = ("props_lib/paperbomb_*.py", "props_lib/paperbomb_*.json")


def copy_paperbomb_scripts(src: Path, dst: Path) -> list:
    files = [src / f for f in PB_SCRIPTS if (src / f).is_file()]
    for g in PB_GLOBS:
        files += sorted(src.glob(g))
    out = []
    for item in sorted(set(files)):
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        out.append(target)
    return out


def main(argv=None) -> int:'''
assert s.count(old) == 1; s = s.replace(old, new)
io.open(d + "snapshot.py", "w", encoding="utf-8", newline="\n".encode().decode("unicode_escape")).write(s)
c = io.open(d + "compare.py", encoding="utf-8").read()
old = '''    "textures": PROJECT / "Exports" / "PaperBomb" / "Textures",
'''
new = '''    "textures": PROJECT / "Exports" / "PaperBomb" / "Textures",
    "recolour": PROJECT / "Exports" / "PaperBomb" / "Textures" / "Recolour",
'''
assert c.count(old) == 1; c = c.replace(old, new)
io.open(d + "compare.py", "w", encoding="utf-8", newline="\n".encode().decode("unicode_escape")).write(c)
print("ok")
