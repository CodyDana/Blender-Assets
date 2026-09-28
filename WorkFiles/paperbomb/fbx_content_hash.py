"""Content hash of a binary FBX: everything a consumer renders, nothing the exporter stamps.

Blender's FBX writer puts a wall-clock CreationTimeStamp in the header and gives every
object a 64-bit UID drawn fresh each export, so two byte-identical scenes never export
to identical bytes.  This walks the node tree and hashes only the payload: node names,
string/numeric properties and every array, with the whole FBXHeaderExtension subtree and
every scalar int64 ('L', which is what a UID is) left out.
"""
import struct, hashlib, sys, zlib

def read_nodes(buf, pos, end, ver):
    out = []
    fmt = '<QQQB' if ver >= 7500 else '<IIIB'
    sz = struct.calcsize(fmt)
    while pos < end:
        if pos + sz > end:
            break
        end_off, nprops, prop_len, nlen = struct.unpack_from(fmt, buf, pos)
        pos += sz
        if end_off == 0:
            break
        name = buf[pos:pos + nlen].decode('utf8', 'replace'); pos += nlen
        props = []
        p = pos
        for _ in range(nprops):
            t = chr(buf[p]); p += 1
            if t in 'CBY':
                n = {'C': 1, 'B': 1, 'Y': 2}[t]
                props.append((t, buf[p:p + n])); p += n
            elif t == 'I':
                props.append((t, buf[p:p + 4])); p += 4
            elif t == 'F':
                props.append((t, buf[p:p + 4])); p += 4
            elif t == 'D':
                props.append((t, buf[p:p + 8])); p += 8
            elif t == 'L':
                props.append((t, buf[p:p + 8])); p += 8       # UID - dropped below
            elif t in 'SR':
                n = struct.unpack_from('<I', buf, p)[0]; p += 4
                props.append((t, buf[p:p + n])); p += n
            elif t in 'fdlib':
                cnt, enc, clen = struct.unpack_from('<III', buf, p); p += 12
                raw = buf[p:p + clen]; p += clen
                if enc == 1:
                    raw = zlib.decompress(raw)
                props.append((t, raw))
            else:
                raise ValueError('unknown prop type %r at %d' % (t, p))
        kids = read_nodes(buf, p, end_off, ver) if p < end_off else []
        out.append((name, props, kids))
        pos = end_off
    return out

def digest(nodes, h, skip_header=True):
    for name, props, kids in nodes:
        if skip_header and name == 'FBXHeaderExtension':
            continue
        if skip_header and name in ('CreationTime', 'FileId', 'Creator'):
            continue
        h.update(b'<' + name.encode('utf8'))
        for t, v in props:
            if t == 'L':            # object UID: fresh on every export
                continue
            h.update(t.encode() + struct.pack('<I', len(v)) + v)
        digest(kids, h, skip_header)
        h.update(b'>')

def content_hash(path):
    buf = open(path, 'rb').read()
    assert buf[:21] == b'Kaydara FBX Binary\x20\x20\x00', buf[:21]
    ver = struct.unpack_from('<I', buf, 23)[0]
    nodes = read_nodes(buf, 27, len(buf), ver)
    h = hashlib.sha256()
    digest(nodes, h)
    return h.hexdigest(), ver

for p in sys.argv[1:]:
    d, v = content_hash(p)
    print(d[:32], 'fbx%d' % v, p)
