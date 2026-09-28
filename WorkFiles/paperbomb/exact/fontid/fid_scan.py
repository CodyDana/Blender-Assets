# -*- coding: utf-8 -*-
"""Scan every font file on the machine; keep the ones whose cmap covers the kanji
on the card.  Pure struct parsing (TTF/OTF/TTC/WOFF1); WOFF2 checked by loading
into Blender and testing for outline geometry."""
import os, sys, struct, zlib, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = "火遁術爆炎陣焼尽瞬業道"
NAMEIDS = {1: "family", 2: "subfamily", 4: "full", 5: "version", 0: "copyright", 13: "license", 14: "licenseURL", 8: "manufacturer", 9: "designer", 7: "trademark"}

def tables_at(d, off):
    tag, num = struct.unpack(">IH", d[off:off + 6])
    t = {}
    for i in range(num):
        o = off + 12 + 16 * i
        t[d[o:o + 4].decode('latin-1')] = struct.unpack(">II", d[o + 8:o + 16])
    return t

def woff1_to_tables(d):
    num = struct.unpack(">H", d[12:14])[0]
    out = {}
    for i in range(num):
        o = 44 + 20 * i
        tag = d[o:o + 4].decode('latin-1')
        off, clen, olen = struct.unpack(">III", d[o + 4:o + 16])
        raw = d[off:off + clen]
        out[tag] = zlib.decompress(raw) if clen < olen else raw
    return out

def cmap_from(buf):
    ver, n = struct.unpack(">HH", buf[0:4])
    cands = []
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", buf[4 + 8 * i:12 + 8 * i])
        fmt = struct.unpack(">H", buf[off:off + 2])[0]
        cands.append((pid, eid, fmt, off))
    cm = {}
    for pid, eid, fmt, so in cands:
        if not ((pid == 3 and eid in (1, 10)) or pid == 0):
            continue
        if fmt == 4:
            segX2 = struct.unpack(">H", buf[so + 6:so + 8])[0]; seg = segX2 // 2
            endo = so + 14; starto = endo + segX2 + 2; deltao = starto + segX2; rangeo = deltao + segX2
            for s in range(seg):
                end = struct.unpack(">H", buf[endo + 2 * s:endo + 2 * s + 2])[0]
                sta = struct.unpack(">H", buf[starto + 2 * s:starto + 2 * s + 2])[0]
                delta = struct.unpack(">h", buf[deltao + 2 * s:deltao + 2 * s + 2])[0]
                ro = struct.unpack(">H", buf[rangeo + 2 * s:rangeo + 2 * s + 2])[0]
                for ch in CHARS:
                    c = ord(ch)
                    if sta <= c <= end:
                        if ro == 0: g = (c + delta) & 0xFFFF
                        else:
                            gi = rangeo + 2 * s + ro + 2 * (c - sta)
                            g = struct.unpack(">H", buf[gi:gi + 2])[0] if gi + 2 <= len(buf) else 0
                            if g: g = (g + delta) & 0xFFFF
                        if g: cm[ch] = g
        elif fmt == 12:
            ng = struct.unpack(">I", buf[so + 12:so + 16])[0]
            for i in range(ng):
                o = so + 16 + 12 * i
                s_, e_, g_ = struct.unpack(">III", buf[o:o + 12])
                for ch in CHARS:
                    if s_ <= ord(ch) <= e_: cm[ch] = g_ + ord(ch) - s_
    return cm

def names_from(buf):
    fmt, count, so = struct.unpack(">HHH", buf[0:6]); rec = {}
    for i in range(count):
        pid, eid, lid, nid, ln, off = struct.unpack(">HHHHHH", buf[6 + 12 * i:18 + 12 * i])
        if nid not in NAMEIDS: continue
        raw = buf[so + off:so + off + ln]
        try: s = raw.decode('utf-16-be') if pid in (0, 3) else raw.decode('latin-1')
        except Exception: continue
        k = NAMEIDS[nid]
        if k not in rec or (pid == 3 and lid == 0x409): rec[k] = s
    return rec

def fstype(buf):
    return struct.unpack(">H", buf[8:10])[0] if len(buf) >= 10 else None

def faces(path):
    d = open(path, 'rb').read()
    sig = d[:4]
    res = []
    if sig == b'ttcf':
        n = struct.unpack(">I", d[8:12])[0]
        offs = [struct.unpack(">I", d[12 + 4 * i:16 + 4 * i])[0] for i in range(n)]
        for fi, off in enumerate(offs):
            t = tables_at(d, off)
            get = lambda tag: d[t[tag][0]:t[tag][0] + t[tag][1]] if tag in t else None
            res.append((fi, get))
    elif sig == b'wOFF':
        tb = woff1_to_tables(d)
        res.append((0, lambda tag: tb.get(tag)))
    elif sig == b'wOF2':
        return 'woff2', d
    else:
        t = tables_at(d, 0)
        res.append((0, lambda tag: d[t[tag][0]:t[tag][0] + t[tag][1]] if tag in t else None))
    return res, d

paths = [l.strip() for l in open(os.path.join(HERE, "all_font_files.txt"), encoding="utf-8") if l.strip()]
seen = {}; out = []; woff2 = []
for p in paths:
    try:
        r, d = faces(p)
    except Exception as e:
        out.append(dict(path=p, error=str(e))); continue
    h = hashlib.sha256(d).hexdigest()
    if r == 'woff2':
        woff2.append(dict(path=p, sha256=h)); continue
    for fi, get in r:
        try:
            cm = cmap_from(get('cmap')) if get('cmap') else {}
            nm = names_from(get('name')) if get('name') else {}
            os2 = get('OS/2'); fst = fstype(os2) if os2 else None
        except Exception as e:
            out.append(dict(path=p, face=fi, error=str(e))); continue
        cov = "".join(ch for ch in CHARS if ch in cm)
        rec = dict(path=p, face=fi, sha256=h, covered=cov, n_cov=len(cov), fsType=fst, dup_of=seen.get((h, fi)), **nm)
        seen.setdefault((h, fi), p)
        out.append(rec)
# WOFF2: probe by loading in Blender
import bpy
for w in woff2:
    try:
        f = bpy.data.fonts.load(w['path'])
        cov = ""
        for ch in CHARS:
            cu = bpy.data.curves.new("t", 'FONT'); cu.body = ch; cu.font = f
            ob = bpy.data.objects.new("t", cu); bpy.context.scene.collection.objects.link(ob)
            dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            if me is not None and len(me.polygons) > 0: cov += ch
            ev.to_mesh_clear(); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        w.update(covered=cov, n_cov=len(cov), family=f.name, face=0, loaded_by="blender")
    except Exception as e:
        w.update(error=str(e))
    out.append(w)
cjk = [r for r in out if r.get('n_cov', 0) > 0]
json.dump(dict(chars=CHARS, n_files=len(paths), all=out, cjk=cjk), open(os.path.join(HERE, "font_scan.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("files", len(paths), "faces", len(out), "cjk faces", len(cjk))
for r in cjk:
    print("%2d %-11s %-40s f%s fsType=%s %s%s" % (r['n_cov'], r['covered'], (r.get('full') or r.get('family') or '')[:40], r.get('face'), r.get('fsType'), r['path'], "  DUP" if r.get('dup_of') else ""))
