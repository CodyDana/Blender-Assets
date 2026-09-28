"""Write hooked_cross_maint/style_sheet.py from hooked_cross/style_sheet.py (plain Python): new banner (library 3.9.1,
the hooked-cross maintenance), the hooked cross column no longer NEW (revision 2), and its handedness footer line also
reports the texture-sheet gate."""
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
s = (W / "hooked_cross" / "style_sheet.py").read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('''"""Comparison sheet, hooked-cross build (library 3.9.0): the reference next to every form, hero + top - a new column
for SM_Shuriken_HookedCross, the pack's first outline plate.
''', '''"""Comparison sheet, hooked-cross MAINTENANCE (library 3.9.1): the reference next to every form, hero + top.

Copied from hooked_cross/style_sheet.py; only the banner, the hooked cross column title (revision 2, no longer NEW) and
its handedness footer line (it now also reports the texture-sheet gate) changed.

(Hooked-cross build history follows.)  Comparison sheet, hooked-cross build (library 3.9.0): a new column
for SM_Shuriken_HookedCross, the pack's first outline plate.
''')
rep('''         ("hooked_cross", "NEW  HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm)")]''',
    '''         ("hooked_cross", "HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm, rev 2)")]''')
rep('''            f"{'caught' if ctl.get('caught') else 'MISSED'}; gallery +Z {'PASS' if gal.get('passed') else 'FAIL'}   "''',
    '''            f"{'caught' if ctl.get('caught') else 'MISSED'}; gallery +Z {'PASS' if gal.get('passed') else 'FAIL'}; texture "
            f"sheets +Z {'PASS' if (r.get('texture_handedness') or {}).get('passed') else 'FAIL'}   "''')
rep('''text("Banner", "Shuriken pack with the hooked cross (library 3.9.0): the reference and every form (four-point, "
     "eight-point, senban, six-point, spike, NEW hooked cross - its hero turns the plate 40 deg; every image shows the "
     "presented +Z face) through the SAME gallery rig, baked maps only, 2026-09-18", GAP_X,''',
    '''text("Banner", "Shuriken pack after the hooked-cross maintenance (library 3.9.1): the reference and every form "
     "(four-point, eight-point, senban, six-point, spike, hooked cross rev 2 - its hero turns the plate 40 deg; every image "
     "shows the presented +Z face) through the SAME gallery rig, baked maps only, 2026-09-19", GAP_X,''')
(W / "hooked_cross_maint" / "style_sheet.py").write_text(s, encoding="utf-8")
print("WROTE", W / "hooked_cross_maint" / "style_sheet.py")
