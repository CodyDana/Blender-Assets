"""One-off source patch (spike maintenance, library 3.8.1): the bar's side-face render gate, the version."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


name = "pack.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''from .render import facet_gate, plate_gate, render_previews, wall_gate''',
    '''from .render import bar_wall_gate, facet_gate, plate_gate, render_previews, wall_gate''')
rep('''        "top_plate": plate_gate(top, cls),
    }''', '''        "top_plate": plate_gate(top, cls),
    }
    if cls == "bar":
        report["render_gates"]["hero_bar_walls"] = bar_wall_gate(persp)     # 3.8.1: no pepper on the side faces''')
p.write_text(s, encoding="utf-8")

name = "__init__.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''VERSION = "3.8.0"   # 3.8.0 (the spike, SM_Shuriken_Spike - the pack's first BAR): bar_spec + bar (BarGeometry through''',
    '''VERSION = "3.8.1"   # 3.8.1 (spike maintenance, after its visual / geometry / Unreal reviews; the plate forms' geometry,
                    # UVs, hulls, sockets and maps unchanged): hero lamps scaled with a bar's fitted camera distance
                    # (render HERO_RIG_REFERENCE_M), backdrop points + pack_consistency backdrop gate, a bar's side-face
                    # dark-dot gate and wall anchor, the LOD strip's end-on section insets; M_Shuriken_Master bar mode:
                    # pits at BAR_PIT_SCALE, no worn band / nicks on the shoulder, a satin-bright arris round; bar:
                    # analytic custom normals on the round, a deterministic 2048 x 512 UV layout (gaps, border,
                    # every LOD on its island's exact map), bake of non-square maps + unused-texel fill; uv: per-loop
                    # island-map deviation; hooks: texture_size, fill_unused_texels, lod_deviation_headline,
                    # bounds_radius, surface_snapshot, noun / outline_wording (all default to the old paths)
                    # 3.8.0 (the spike, SM_Shuriken_Spike - the pack's first BAR): bar_spec + bar (BarGeometry through''')
p.write_text(s, encoding="utf-8")
print("patched pack.py render gate, version 3.8.1")
