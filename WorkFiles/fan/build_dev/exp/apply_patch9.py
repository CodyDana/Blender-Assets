p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_fan.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)
rep('''    def interp(Ma, Mb, u):
        qa = Quaternion(np.array(Ma[:3, :3]).tolist() and __import__("mathutils").Matrix(Ma[:3, :3].tolist()).to_quaternion())
        qb = __import__("mathutils").Matrix(Mb[:3, :3].tolist()).to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()''', '''    from mathutils import Matrix as _Mx

    def interp(Ma, Mb, u):
        qa = _Mx(Ma[:3, :3].tolist()).to_quaternion()
        qb = _Mx(Mb[:3, :3].tolist()).to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()''')
rep('''    closed = {}
    for o in objs:
        me = o.data
        # every stick is a closed solid; the eyelet is a closed solid (per LOD)
        groups = {}
        for poly in me.polygons:
            pass
        closed[o.name] = _closed_groups(o)
    res = SKP.qa_skeletal(objs, arm, max_influences=1, bone_budget=128, closed_groups=closed, max_slots=3)
    tres = SKP.qa_skeletal(tobjs, tarm_named_root(tarm), max_influences=2, bone_budget=16, max_slots=1)''', '''    # every stick is a closed solid; so is the eyelet (per LOD)
    closed = {o.name: _closed_groups(o) for o in objs}
    res = SKP.qa_skeletal(objs, arm, max_influences=1, bone_budget=128, closed_groups=closed, max_slots=3)
    # the tassel's armature carries the name 'root' in its own files: check it under that name
    arm.name = "root_fan"
    tarm.name = "root"
    try:
        tres = SKP.qa_skeletal(tobjs, tarm, max_influences=2, bone_budget=16, max_slots=1)
    finally:
        tarm.name = "root_tassel"
        arm.name = "root"''')
a = s.index("_TASSEL_NAME_SWAP = {}")
b = s.index("def _closed_groups(obj):")
s = s[:a] + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("ok")
