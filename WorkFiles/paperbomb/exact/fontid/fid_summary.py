# -*- coding: utf-8 -*-
"""Summarise runs/*.json: per target, fonts ranked by soft IoU; per font, mean over glyphs."""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
pat = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "runs/run*.json"
R = []
for p in sorted(glob.glob(os.path.join(HERE, pat))):
    R += json.load(open(p, encoding="utf-8"))
R = [r for r in R if 'soft_iou' in r]
keys = []
for r in R:
    if r['target'] not in keys:
        keys.append(r['target'])
print("=== per target, top 6 by soft IoU (bin IoU, edge mean/p95 px, aniso, rot)")
for k in keys:
    rs = sorted([r for r in R if r['target'] == k], key=lambda r: -r['soft_iou'])
    print("\n%s %s  n=%d  median soft %.3f" % (k, rs[0]['char'], len(rs), sorted(r['soft_iou'] for r in rs)[len(rs) // 2]))
    for r in rs[:6]:
        print("   %-40s soft %.3f bin %.3f edge %.2f/%.2f aniso %.2f rot %5.1f" % (
            str(r['font'])[:40], r['soft_iou'], r['bin_iou'], r['edge_mean_px'], r['edge_p95_px'], r['sx_over_sy'], r['rot_deg']))
    tm = [r for r in rs if r['font_id'] == 'template']
    for r in tm:
        print("   [TEMPLATE] %-29s soft %.3f bin %.3f edge %.2f/%.2f" % (r['font'][:29], r['soft_iou'], r['bin_iou'], r['edge_mean_px'], r['edge_p95_px']))
print("\n=== per font, mean over the 10 column glyphs / centre / seal")
fonts = {}
for r in R:
    if r['font_id'] == 'template':
        continue
    fonts.setdefault(r['font'], []).append(r)
rows = []
for f, rs in fonts.items():
    col = [r['soft_iou'] for r in rs if r['target'].startswith('col_')]
    cen = [r['soft_iou'] for r in rs if r['target'] == 'centre_baku']
    seal = [r['soft_iou'] for r in rs if r['target'].startswith('seal_')]
    colb = [r['bin_iou'] for r in rs if r['target'].startswith('col_')]
    rows.append((sum(col) / max(len(col), 1), f, len(col), sum(colb) / max(len(colb), 1), cen[0] if cen else None, sum(seal) / max(len(seal), 1) if seal else None))
for m, f, n, mb, c, s in sorted(rows, reverse=True):
    print("   %-40s cols(n=%2d) soft %.3f bin %.3f | centre %s | seal %s" % (f[:40], n, m, mb, "%.3f" % c if c else "-", "%.3f" % s if s else "-"))
