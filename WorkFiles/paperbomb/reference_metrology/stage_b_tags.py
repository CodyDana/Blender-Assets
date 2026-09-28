# -*- coding: utf-8 -*-
"""Stage B: detect + rectify every tag, dump the component inventory as TEXT."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as T

OUT = os.path.dirname(os.path.abspath(__file__))

TARGETS = [
    ("V1", r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png", 'guide', 'left'),
    ("V2", r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png", 'guide', 'left'),
    ("OURS_ATLAS", r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png", 'atlas', 'left'),
    ("OURS_ART", r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png", 'atlas', 'left'),
]

res = {}
for name, path, kind, island in TARGETS:
    print(f"\n########## {name}  {os.path.basename(path)}")
    try:
        tg = T.Tag(path, kind, island, name)
    except Exception as e:
        import traceback; traceback.print_exc()
        continue
    d = tg.diag
    print(f"  raw canvas {tg.rgb_raw.shape[1]}x{tg.rgb_raw.shape[0]}  mtime={tg.mtime:.1f}")
    print(f"  quad tl={[round(v,2) for v in d['quad']['tl']]} tr={[round(v,2) for v in d['quad']['tr']]}"
          f" br={[round(v,2) for v in d['quad']['br']]} bl={[round(v,2) for v in d['quad']['bl']]}")
    print(f"  side rms px: {({k: round(v,3) for k,v in d['side_fit_rms_px'].items()})}")
    print(f"  lean deg: {({k: round(v,4) for k,v in d['lean_deg'].items()})}")
    print(f"  rotation applied {d['rotation_deg_applied']:.4f} deg"
          f" (from vsides {d['rotation_deg_from_vertical_sides']:.4f}, hsides {d['rotation_deg_from_horizontal_sides']:.4f})")
    print(f"  keystone: vconv {d['keystone_vertical_convergence_deg']:.4f} deg,"
          f" hconv {d['keystone_horizontal_convergence_deg']:.4f} deg,"
          f" width taper {d['width_taper_pct']:.3f}%, height taper {d['height_taper_pct']:.3f}%")
    print(f"  rectified tag {tg.W}x{tg.H} px  aspect {tg.W/tg.H:.5f} (card 70/156={70/156:.5f})"
          f"  px/mm x={tg.px_per_mm_x:.3f} y={tg.px_per_mm_y:.3f}")
    segtxt = json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in tg.seg.items()})
    print("  seg: " + segtxt)
    res[name] = tg

    for label, mask in (("BLACK", tg.black), ("RED", tg.red)):
        mm = P.close(mask, 2)
        lab, n = P.label_cc(mm)
        st = [s for s in P.cc_stats(lab, n) if s and s['area'] >= max(20, int(0.000004 * tg.W * tg.H))]
        st.sort(key=lambda s: -s['area'])
        print(f"  --- {label} components (>=min area), top 30 of {len(st)}")
        for s in st[:30]:
            b = tg.box(s['x0'], s['y0'], s['x1'], s['y1'])
            print(f"    a={s['area']:7d} x[{b['x0_frac']:.3f}-{b['x1_frac']:.3f}]"
                  f" y[{b['y0_frac']:.3f}-{b['y1_frac']:.3f}]"
                  f" mm[{b['x0_mm']:6.2f},{b['y0_mm']:7.2f}]-[{b['x1_mm']:6.2f},{b['y1_mm']:7.2f}]"
                  f" wh={b['w_mm']:5.2f}x{b['h_mm']:5.2f} c=({b['cx_mm']:5.2f},{b['cy_mm']:6.2f})")
        tot = sum(s['area'] for s in st)
        print(f"    [{label} total area in kept comps = {tot}, coverage {tot/(tg.W*tg.H):.4f}]")
