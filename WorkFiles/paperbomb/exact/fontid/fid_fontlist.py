# -*- coding: utf-8 -*-
"""Candidate list: every CJK-capable font face found on this machine (face 0 of each
unique file - Blender's loader opens face 0), plus Blender's bundled Noto Sans CJK."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "font_scan.json"), encoding="utf-8"))
out = []
seen = set()
for r in d['cjk']:
    if r.get('loaded_by'):
        continue
    if r.get('face', 0) != 0 or r.get('dup_of'):
        continue
    if 'LastResort' in (r.get('family') or ''):
        continue
    if r['sha256'] in seen:
        continue
    seen.add(r['sha256'])
    out.append(dict(name=(r.get('full') or r.get('family')), path=r['path'], covered=r['covered'],
                    sha256=r['sha256'], fsType=r.get('fsType'), license=r.get('license', '')[:300],
                    licenseURL=r.get('licenseURL', ''), copyright=r.get('copyright', '')[:200],
                    manufacturer=r.get('manufacturer', ''), designer=r.get('designer', ''), version=r.get('version', '')))
# brush fonts first
out.sort(key=lambda f: (0 if ('MasaFont' in f['name'] or 'Yuji' in f['name']) else 1, f['name']))
bl = r"C:/Program Files/Blender Foundation/Blender 5.2/5.2/datafiles/fonts/Noto Sans CJK Regular.woff2"
import hashlib
out.append(dict(name="Noto Sans CJK Regular (Blender bundled, woff2)", path=bl, covered="火遁術爆炎陣焼尽瞬業道",
                sha256=hashlib.sha256(open(bl, 'rb').read()).hexdigest(), fsType=None, license="SIL OFL 1.1 (Noto CJK)",
                note="woff2: cmap not parsed (no brotli); coverage assumed, verified visually in previews"))
json.dump(out, open(os.path.join(HERE, "fonts.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for i, f in enumerate(out):
    print(i, f['name'], "|", f['covered'], "|", f['path'])
