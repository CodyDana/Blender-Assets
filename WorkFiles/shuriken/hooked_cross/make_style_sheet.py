"""Write hooked_cross/style_sheet.py from spike_maint/style_sheet.py (plain Python): new banner, a HOOKED CROSS column
(the pack's first outline plate) and its footer lines (blade grind, masses, handedness)."""
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
s = (W / "spike_maint" / "style_sheet.py").read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('''"""Comparison sheet, spike maintenance (library 3.8.1): the reference next to every form, hero + top.
''', '''"""Comparison sheet, hooked-cross build (library 3.9.0): the reference next to every form, hero + top - a new column
for SM_Shuriken_HookedCross, the pack's first outline plate.

Copied from spike_maint/style_sheet.py; only the banner, the new column and its footer lines are new (the hooked
cross's line gives the blade grind and its extent, the masses, and the handedness gate on the presented +Z face).
Its plan silhouette is checked against its own un-ground outline (hooked_cross/silhouette_ref.py).

(Spike maintenance history follows.)  Comparison sheet, spike maintenance (library 3.8.1).
''')
rep('''         ("spike", "SPIKE  SM_Shuriken_Spike  (150 mm, 6 mm square, rev 2)")]''',
    '''         ("spike", "SPIKE  SM_Shuriken_Spike  (150 mm, 6 mm square, rev 2)"),
         ("hooked_cross", "NEW  HOOKED CROSS  SM_Shuriken_HookedCross  (100 mm tip to tip, 2.5 mm)")]''')
rep('''    ref = {"six_point": "un-ground outline", "spike": "square-arris bar"}.get(form, "pass 1")''',
    '''    ref = {"six_point": "un-ground outline", "spike": "square-arris bar",
           "hooked_cross": "un-ground outline"}.get(form, "pass 1")''')
rep('''    if r.get("geometry") == "bar":''', '''    if r.get("geometry") == "outline_plate":
        ext = (m.get("grind_extent") or {}).get("design") or {}
        hand = r.get("handedness") or {}
        gal = r.get("gallery_presented_face") or {}
        ctl = (hand.get("negative_control") or {})
        return [
            f"blade edge peak p90 {mt.get('edge_peak_p90', float('nan')):.2f} (arm edges: chamfer + wall)   bright bevel "
            f"hero {100 * mh.get('bright_facet_share', float('nan')):.1f} %   fine dark / bright "
            f"{mt.get('fine_dark', float('nan')):.4f} / {mt.get('fine_bright', float('nan')):.4f}",
            f"knife grind on the hook blades {g['grind_angle_deg']['area_weighted_mean']:.1f} deg/side, {width:.2f} mm wide, "
            f"land {g['edge_land_mm']['max']:.2f} mm, tip radius {g['tip_radius_mm']:.3f} mm; elsewhere 0.45 mm chamfer + wall",
            f"grind extent: back arc {(ext.get('back_arc') or {}).get('full_knife_from_tip_mm', float('nan')):.1f} mm + 3 mm "
            f"run-out to the shoulder, inner edge {(ext.get('inner_edge') or {}).get('full_knife_from_tip_mm', float('nan')):.1f}"
            f" mm + 3 mm to the fillet",
            f"mass: outline {m['outline_mass_g']:.2f} g (photo outline 37.09 +-2, gate "
            f"{'PASS' if m['mass_within_tolerance'] else 'FAIL'})   ground {m['ground_mass_g']:.2f} g   hero lum "
            f"{hero.get('mean', float('nan')):.3f}/{hero.get('p50', float('nan')):.3f}  top {top.get('mean', float('nan')):.3f}/"
            f"{top.get('p50', float('nan')):.3f}",
            f"handedness (left-facing on +Z) {'PASS' if hand.get('passed') else 'FAIL'}, mirrored control "
            f"{'caught' if ctl.get('caught') else 'MISSED'}; gallery +Z {'PASS' if gal.get('passed') else 'FAIL'}   "
            f"photo outline IoU {(r.get('photo_check') or {}).get('analytic_outline', {}).get('iou', float('nan')):.5f}",
            f"LODs {'/'.join(str(t) for t in r['lod_triangles'])}   qa {'pass' if r['qa']['passed'] else 'FAIL'} "
            f"({len(r['qa']['checks'])})   Unreal 5.8: {ec}   {sil}",
        ]
    if r.get("geometry") == "bar":''')
rep('''text("Banner", "Shuriken pack, spike maintained (library 3.8.1): the reference and every form (four-point, eight-point, "
     "senban, six-point, spike - its hero turns the bar 40 deg, slides it for the stars' lens shift and scales the lamps "
     "with the camera distance) through the SAME gallery rig, baked maps only, 2026-09-18", GAP_X,''',
    '''text("Banner", "Shuriken pack with the hooked cross (library 3.9.0): the reference and every form (four-point, "
     "eight-point, senban, six-point, spike, NEW hooked cross - its hero turns the plate 40 deg; every image shows the "
     "presented +Z face) through the SAME gallery rig, baked maps only, 2026-09-18", GAP_X,''')
(W / "hooked_cross" / "style_sheet.py").write_text(s, encoding="utf-8")
print("wrote hooked_cross/style_sheet.py")
