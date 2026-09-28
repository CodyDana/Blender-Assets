import sys
from io_scene_fbx import parse_fbx
for p in sys.argv[sys.argv.index("--")+1:]:
    root,v=parse_fbx.parse(p); gs={}
    def walk(e):
        if e.id==b"GlobalSettings":
            for c in e.elems:
                if c.id==b"Properties70":
                    for q in c.elems:
                        k=q.props[0].decode()
                        if "Axis" in k or "Unit" in k: gs[k]=q.props[4]
        for c in e.elems: walk(c)
    walk(root); print("AXES",p.split('/')[-1],gs)
