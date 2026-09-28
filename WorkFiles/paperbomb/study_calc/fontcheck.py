# -*- coding: utf-8 -*-
"""Read the cmap of the project fonts and report coverage of every character the
paper bomb needs.  Pure struct parsing: no fontTools in Blender's Python."""
import struct, os, json

FONTS = {
 "MasaFont-Bold": r"C:/Users/Cody/Desktop/Blender_Projects/References/Fonts/MasaFont-Bold.ttf",
 "YujiBoku-Regular": r"C:/Users/Cody/Desktop/Blender_Projects/References/Fonts/YujiBoku-Regular.ttf",
}
STRINGS = {
 "centre": "\u7206",
 "upper_left": "\u706b\u9041\u8853",
 "upper_right": "\u7206\u708e\u9663",
 "lower_right": "\u713c\u5c3d",
 "lower_centre": "\u77ac\u696d",
 "small_seal": "\u706b\u9053",
}

def read_cmap(path):
    d = open(path,'rb').read()
    tag, numTables = struct.unpack(">IH", d[0:6])
    tables = {}
    for i in range(numTables):
        off = 12 + 16*i
        t = d[off:off+4].decode('latin-1')
        o, l = struct.unpack(">II", d[off+8:off+16])
        tables[t] = (o, l)
    if 'cmap' not in tables:
        return None, tables
    co = tables['cmap'][0]
    ver, n = struct.unpack(">HH", d[co:co+4])
    best = None
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", d[co+4+8*i:co+4+8*i+8])
        fmt = struct.unpack(">H", d[co+off:co+off+2])[0]
        if (pid, eid) in ((3,10),(3,1),(0,4),(0,3),(0,6)):
            best = (pid, eid, fmt, co+off) if best is None or fmt == 12 else best
    if best is None:
        return None, tables
    pid, eid, fmt, so = best
    cmap = {}
    if fmt == 4:
        length, lang, segX2 = struct.unpack(">HHH", d[so+2:so+8])
        seg = segX2//2
        endo = so+14
        starto = endo+segX2+2
        deltao = starto+segX2
        rangeo = deltao+segX2
        for s in range(seg):
            end = struct.unpack(">H", d[endo+2*s:endo+2*s+2])[0]
            sta = struct.unpack(">H", d[starto+2*s:starto+2*s+2])[0]
            delta = struct.unpack(">h", d[deltao+2*s:deltao+2*s+2])[0]
            ro = struct.unpack(">H", d[rangeo+2*s:rangeo+2*s+2])[0]
            if sta == 0xFFFF: continue
            for c in range(sta, min(end, 0xFFFE)+1):
                if ro == 0:
                    g = (c + delta) & 0xFFFF
                else:
                    gi = rangeo + 2*s + ro + 2*(c - sta)
                    if gi+2 > len(d): continue
                    g = struct.unpack(">H", d[gi:gi+2])[0]
                    if g: g = (g + delta) & 0xFFFF
                if g: cmap[c] = g
    elif fmt == 12:
        ngroups = struct.unpack(">I", d[so+12:so+16])[0]
        for i in range(ngroups):
            o = so+16+12*i
            s_, e_, g_ = struct.unpack(">III", d[o:o+12])
            if e_ - s_ > 200000: continue
            for c in range(s_, e_+1):
                cmap[c] = g_ + (c - s_)
    return cmap, (pid, eid, fmt)

out = {}
for name, path in FONTS.items():
    cmap, info = read_cmap(path)
    rec = {"file": os.path.basename(path), "size_bytes": os.path.getsize(path),
           "cmap_subtable": str(info), "n_mapped": len(cmap) if cmap else 0, "chars": {}}
    for slot, s in STRINGS.items():
        rec["chars"][slot] = [{"cp": "U+%04X" % ord(ch), "glyph_id": cmap.get(ord(ch), 0),
                               "covered": bool(cmap.get(ord(ch)))} for ch in s]
    out[name] = rec
    print("==", name, rec["cmap_subtable"], "mapped", rec["n_mapped"])
    for slot, lst in rec["chars"].items():
        print("   %-13s %s" % (slot, " ".join("%s gid=%d %s" % (e["cp"], e["glyph_id"],
              "OK" if e["covered"] else "MISSING") for e in lst)))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"font_coverage.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print("WROTE font_coverage.json")
