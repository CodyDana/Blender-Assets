"""Write WorkFiles/kunai/plain_build/style_sheet.py from WorkFiles/shuriken/hooked_cross_maint/style_sheet.py (plain
Python): new banner (library 3.10, the plain kunai), a NEW column for SM_Kunai_Plain and a knife branch in form_lines
(grind, shoulder, masses and pivot, the steel coat pixels the like-with-like gate reads beside the whole object and the
cloth wrap, the blank lettering band)."""
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles")
s = (W / "shuriken" / "hooked_cross_maint" / "style_sheet.py").read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('''"""Comparison sheet, hooked-cross MAINTENANCE (library 3.9.1): the reference next to every form, hero + top.
''', '''"""Comparison sheet, the PLAIN KUNAI build (library 3.10): the reference next to every form, hero + top - a new column
for SM_Kunai_Plain, the pack's first knife.

Copied from WorkFiles/shuriken/hooked_cross_maint/style_sheet.py by WorkFiles/kunai/plain_build/make_style_sheet.py; only
the banner, the hooked cross's title (no longer the newest) and the new column with its knife footer lines are new.  The
kunai's top view is drawn at 5.0 px/mm (its own 0.18 m frame; the stars' at 6.9 px/mm), which its title says.

(Hooked-cross maintenance history follows.)  Comparison sheet, hooked-cross MAINTENANCE (library 3.9.1).
''')
rep('''         ("hooked_cross", "HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm, rev 2)")]''',
    '''         ("hooked_cross", "HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm, rev 2)"),
         ("kunai_plain", "NEW  KUNAI  SM_Kunai_Plain  (280 mm, 5 mm stock; top view at 5.0 px/mm)")]''')
rep('''    if r.get("geometry") == "outline_plate":''', '''    if r.get("geometry") == "kunai":
        coat_h = (rs.get(f"{form}_persp") or {}).get("coat_luminance") or {}
        coat_t = (rs.get(f"{form}_top") or {}).get("coat_luminance") or {}
        wrap_h = (rs.get(f"{form}_persp") or {}).get("wrap_luminance") or {}
        mk = r.get("mass_check_kunai") or {}
        sh = m.get("shoulder") or {}
        gw = g.get("grind_width_mm") or {}
        cc = r.get("collision_choice") or {}
        return [
            f"knife grind {g['grind_angle_deg']:.0f} deg/side, land {g['edge_land_mm']:.2f} mm, tip radius "
            f"{m.get('tip_radius_mm') or float('nan'):.3f} mm, grind {min(gw.values()):.2f}-{max(gw.values()):.2f} mm wide; "
            f"0.7 mm polished band + satin; apex {m['apex_x_mm']:.1f} mm",
            f"shoulder: 16 mm blade base on the 16 x 5 mm neck, {sh.get('runout_mm', 3):g} mm run-out into a "
            f"{sh.get('chamfer_mm', 0.45):g} mm chamfer, V plunge at x {sh.get('plunge_ridge_x_mm', float('nan')):.1f} mm",
            f"steel: un-ground {m['outline_mass_g']:.1f} g (study basis {m['mass_target_g']:.1f} +-2, gate "
            f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'}), finished {m['steel_ground_mass_g']:.1f} g + wrap "
            f"{m['wrap_mass_g']:.1f} g = {m['assembled_mass_g']:.1f} g",
            f"coat (gated) hero {coat_h.get('mean', float('nan')):.3f}/{coat_h.get('p50', float('nan')):.3f} top "
            f"{coat_t.get('mean', float('nan')):.3f}/{coat_t.get('p50', float('nan')):.3f}   whole hero "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}   wrap p50 "
            f"{wrap_h.get('p50', float('nan')):.3f}",
            f"pivot = mass centre x {m['pivot_design_x_mm']:.1f} mm (by volume {m['masses_finished']['centre_if_uniform_density_x_mm']:.1f}); "
            f"2 hulls ({cc.get('two_hulls_mm3', 0) / 1000:.1f} vs one {cc.get('one_hull_mm3', 0) / 1000:.1f} cm3); "
            f"blank 72 x 12 mm lettering band",
            f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
            f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   slots steel + wrap",
        ]
    if r.get("geometry") == "outline_plate":''')
rep('''text("Banner", "Shuriken pack after the hooked-cross maintenance (library 3.9.1): the reference and every form "
     "(four-point, eight-point, senban, six-point, spike, hooked cross rev 2 - its hero turns the plate 40 deg; every image "
     "shows the presented +Z face) through the SAME gallery rig, baked maps only, 2026-09-19", GAP_X,''',
    '''text("Banner", "Shuriken pack with the plain kunai (library 3.10): the reference and every form (four-point, "
     "eight-point, senban, six-point, spike, hooked cross, NEW kunai - its hero points the blade at the viewer, its top "
     "view has its own frame) through the SAME gallery rig, baked maps only, 2026-09-19", GAP_X,''')
out = W / "kunai" / "plain_build" / "style_sheet.py"
out.write_text(s, encoding="utf-8")
print("WROTE", out)
