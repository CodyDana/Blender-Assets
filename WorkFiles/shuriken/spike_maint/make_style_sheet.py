"""Write spike_maint/style_sheet.py from spike/style_sheet.py (plain Python): new banner, the spike no longer NEW,
and the bar's luminance line gains its side faces (the 3.8.1 wall-anchor gate) and the side-face dot count."""
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
s = (W / "spike" / "style_sheet.py").read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('''"""Comparison sheet, spike build (library 3.8.0): the reference next to every form, hero + top - a new column
for SM_Shuriken_Spike, the pack's first bar.
''', '''"""Comparison sheet, spike maintenance (library 3.8.1): the reference next to every form, hero + top.

Copied from spike/style_sheet.py (the spike build's sheet); only the banner, the spike column title (no longer
NEW) and the bar's luminance line changed: it now gives the coat pixels, the side faces (gated against the anchor
forms' walls in 3.8.1) and the side faces' isolated dark-dot count (render gate hero_bar_walls).

(Spike build history follows.)  Comparison sheet, spike build (library 3.8.0): a new column for
SM_Shuriken_Spike, the pack's first bar.
''')
rep('''         ("spike", "NEW  SPIKE  SM_Shuriken_Spike  (150 mm, 6 mm square)")]''',
    '''         ("spike", "SPIKE  SM_Shuriken_Spike  (150 mm, 6 mm square, rev 2)")]''')
rep('''            f"coat (gated) hero {coat_h.get('mean', float('nan')):.3f}/{coat_h.get('p50', float('nan')):.3f} top "
            f"{coat_t.get('mean', float('nan')):.3f}/{coat_t.get('p50', float('nan')):.3f}   whole hero "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f} (mean/p50)",''',
    '''            f"coat (gated) hero {coat_h.get('mean', float('nan')):.3f}/{coat_h.get('p50', float('nan')):.3f} top "
            f"{coat_t.get('mean', float('nan')):.3f}/{coat_t.get('p50', float('nan')):.3f}   side p50 "
            f"{side.get('p50', float('nan')):.3f} (walls 0.268)   side dots {dots:.1f}/10k   whole hero "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}",''')
rep('''        coat_t = (rs.get(f"{form}_top") or {}).get("coat_luminance") or {}''',
    '''        coat_t = (rs.get(f"{form}_top") or {}).get("coat_luminance") or {}
        side = (rs.get(f"{form}_persp") or {}).get("bar_wall_luminance") or {}
        dots = (((rs.get(f"{form}_persp") or {}).get("bar_wall_dots") or {}).get("30pct") or {}).get("dots_per_10k_px",
                                                                                                    float("nan"))''')
rep('''text("Banner", "Shuriken pack with the spike (library 3.8.0): the reference and every form (four-point, eight-point, "
     "senban, six-point, NEW spike - the hero turns the bar 40 deg about Z, the rig is unchanged) through the SAME "
     "gallery rig, baked maps only, 2026-09-18", GAP_X,''',
     '''text("Banner", "Shuriken pack, spike maintained (library 3.8.1): the reference and every form (four-point, eight-point, "
     "senban, six-point, spike - its hero turns the bar 40 deg, slides it for the stars' lens shift and scales the lamps "
     "with the camera distance) through the SAME gallery rig, baked maps only, 2026-09-18", GAP_X,''')
(W / "spike_maint" / "style_sheet.py").write_text(s, encoding="utf-8")
print("wrote spike_maint/style_sheet.py")
