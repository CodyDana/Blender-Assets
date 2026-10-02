"""Minimal UE5 package-summary reader: name map + import table (hard imports), no editor.
Used to tell HARD imports (packages the loader must find) from names that are only soft / editor references."""
import struct, sys


class R:
    def __init__(s, b, o=0):
        s.b, s.o = b, o

    def i32(s):
        v = struct.unpack_from("<i", s.b, s.o)[0]; s.o += 4; return v

    def u32(s):
        v = struct.unpack_from("<I", s.b, s.o)[0]; s.o += 4; return v

    def skip(s, n):
        s.o += n

    def fstr(s):
        n = s.i32()
        if n == 0:
            return ""
        if n > 0:
            v = s.b[s.o:s.o + n - 1].decode("latin-1"); s.o += n; return v
        n = -n
        v = s.b[s.o:s.o + 2 * n - 2].decode("utf-16-le"); s.o += 2 * n; return v


def read(path):
    b = open(path, "rb").read()
    r = R(b)
    tag = r.u32()
    assert tag == 0x9E2A83C1, "bad tag"
    legacy = r.i32()
    if legacy != -4:
        r.i32()
    ue4 = r.i32()
    ue5 = r.i32() if legacy <= -8 else 0
    r.i32()  # licensee
    if ue5 >= 1016:
        r.skip(20)  # FIoHash SavedHash
        r.i32()     # TotalHeaderSize
    if legacy <= -2:
        n = r.i32()
        r.skip(n * 20)
    if ue5 < 1016:
        r.i32()
    pkgname = r.fstr()
    flags = r.u32()
    name_count, name_off = r.i32(), r.i32()
    soft_count = soft_off = 0
    if ue5 >= 1008:
        soft_count, soft_off = r.i32(), r.i32()
    if not (flags & 0x80000000):  # PKG_FilterEditorOnly
        r.fstr()
    r.i32(); r.i32()  # gatherable text
    exp_count, exp_off = r.i32(), r.i32()
    imp_count, imp_off = r.i32(), r.i32()
    if ue5 >= 1015:
        r.skip(16)
    if ue5 >= 1014:
        r.i32()
    r.i32()  # DependsOffset
    spr_count, spr_off = r.i32(), r.i32()
    # names
    names = []
    nr = R(b, name_off)
    for _ in range(name_count):
        names.append(nr.fstr())
        nr.skip(4)  # hashes
    def fname(rr):
        i, num = rr.i32(), rr.i32()
        s = names[i] if 0 <= i < len(names) else "?%d" % i
        return s if num == 0 else "%s_%d" % (s, num - 1)
    imps = []
    ir = R(b, imp_off)
    editor = not (flags & 0x80000000)
    for _ in range(imp_count):
        cp, cn, outer, on = fname(ir), fname(ir), ir.i32(), fname(ir)
        pn = fname(ir) if editor else ""
        opt = ir.i32() if ue5 >= 1003 else 0
        imps.append((cp, cn, outer, on, pn, opt))
    softpk = []
    sr = R(b, spr_off)
    for _ in range(spr_count if 0 <= spr_count < 100000 else 0):
        softpk.append(fname(sr))
    softobj = []
    so = R(b, soft_off)
    for _ in range(soft_count if 0 <= soft_count < 100000 else 0):
        pk, an = fname(so), fname(so)
        sub = so.fstr()
        softobj.append(pk)
    return {"soft_packages": softpk, "soft_objects": softobj, "ue4": ue4, "ue5": ue5, "package": pkgname, "flags": flags, "names": names, "imports": imps}


def hard_packages(info):
    return sorted({on for cp, cn, outer, on, pn, opt in info["imports"] if outer == 0 and cn == "Package"})


if __name__ == "__main__":
    for p in sys.argv[1:]:
        i = read(p)
        print(p, "ue4", i["ue4"], "ue5", i["ue5"], "imports", len(i["imports"]))
        for h in hard_packages(i):
            print("   HARD", h)
        print("   SOFTPKG", i["soft_packages"][:20])
        print("   SOFTOBJ", sorted(set(i["soft_objects"]))[:30])
