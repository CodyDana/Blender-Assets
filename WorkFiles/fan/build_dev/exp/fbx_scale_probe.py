import sys, bpy, addon_utils
addon_utils.enable("io_scene_fbx")
from io_scene_fbx import parse_fbx
def dump(path):
    root, ver = parse_fbx.parse(path)
    out = {}
    for el in root.elems:
        if el.id == b"GlobalSettings":
            for p70 in el.elems:
                if p70.id == b"Properties70":
                    for p in p70.elems:
                        if p.props[0] in (b"UnitScaleFactor", b"OriginalUnitScaleFactor"):
                            out[p.props[0].decode()] = p.props[-1]
        if el.id == b"Objects":
            for m in el.elems:
                if m.id == b"Model":
                    name = m.props[1].split(b"\x00")[0].decode()
                    kind = m.props[2].decode()
                    d = {}
                    for sub in m.elems:
                        if sub.id == b"Properties70":
                            for p in sub.elems:
                                if p.props[0] in (b"Lcl Scaling", b"Lcl Translation"):
                                    d[p.props[0].decode()] = [round(x, 5) for x in p.props[-3:]]
                    if name in ("root", "pivot", "stick_00", "stick_12", "SK_Fan") or kind != "LimbNode":
                        out[name + ":" + kind] = d
    return out
for p in sys.argv[sys.argv.index("--") + 1:]:
    print(p.split("/")[-1], dump(p))
