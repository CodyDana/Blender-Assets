p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/verify_fan.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:80]
    s = s.replace(old, new, 1)
rep('''    for aname in ("A_Fan_Openness", "A_Fan_OpenClose", "A_Fan_OpenPose"):
        o3 = import_fbx(EXP / f"{aname}.fbx")''', '''    for aname in ("A_Fan_Openness", "A_Fan_OpenClose", "A_Fan_OpenPose"):
        # the importer turns FBX seconds into frames at the SCENE's rate: import at the file's own rate so
        # every key lands on a whole frame, then interpolate linearly between keys (as Unreal does)
        fps = next(x["fps"] for x in sidecar["animations"] if x["file"] == f"{aname}.fbx")
        bpy.context.scene.render.fps = int(fps)
        bpy.context.scene.render.fps_base = 1.0
        o3 = import_fbx(EXP / f"{aname}.fbx")''')
rep('''        act.name = aname
        for o in o3:''', '''        act.name = aname
        LK._linear(act)
        for o in o3:''')
rep('''            n_ll, _ = FF.count_intersections(T3[Li], T3[Li], same=True,''', '''            n_ll, _ = count(T3[Li], T3[Li], same=True,''')
rep('''            n_ls, ex_ls = FF.count_intersections(T3[Li], T3[Si], exclude=own)
            n_ss, _ = FF.count_intersections(T3[Si], T3[Si], same=True, exclude=lambda x, y: stick_of[Si][x] == stick_of[Si][y])
            n_lr, _ = FF.count_intersections(T3[Li], T3[Ri])''', '''            n_ls, ex_ls = count(T3[Li], T3[Si], exclude=own)
            n_ss, _ = count(T3[Si], T3[Si], same=True, exclude=lambda x, y: stick_of[Si][x] == stick_of[Si][y])
            n_lr, _ = count(T3[Li], T3[Ri])''')
rep('''def world_positions(obj):''', '''EPS_MM = 1e-3        # touching within 1 um (float32 FBX round trip) is contact, not a crossing


def count(TA, TB, same=False, exclude=None):
    ia, ib = FF.pairs_by_aabb(TA, TB, same=same)
    if exclude is not None and len(ia):
        keep = ~exclude(ia, ib)
        ia, ib = ia[keep], ib[keep]
    if not len(ia):
        return 0, []
    hit = FF.tri_tri_intersect(TA[ia], TB[ib], eps=EPS_MM)
    idx = np.nonzero(hit)[0]
    return int(len(idx)), [(int(ia[k]), int(ib[k])) for k in idx[:20]]


def world_positions(obj):''')
# textures path absolute
rep('''    EXP, REN, WORK = Path(a.exports), Path(a.renders), Path(a.work)''', '''    EXP, REN, WORK = Path(a.exports).resolve(), Path(a.renders).resolve(), Path(a.work).resolve()''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_spec.py"
s = open(p, encoding="utf-8").read()
old = '''    def stick_z(self, i: int) -> Tuple[float, float]:
        """(bottom, top) of stick i in Z: front guard on top."""
        top = 0.5 * self.stack_mm
        if i == 0:
            return top - self.guard_thick_mm, top
        g = self.guard_thick_mm
        if i == self.n_sticks - 1:
            return -0.5 * self.stack_mm, -0.5 * self.stack_mm + g
        t0 = top - g - (i - 1) * self.rib_thick_mm
        return t0 - self.rib_thick_mm, t0'''
new = '''    @property
    def stack_pitch_mm(self) -> float:
        """a rib's Z pitch: its thickness plus a 5 um clearance, so stacked plates touch but never overlap
        after a float32 round trip (FBX)"""
        return self.rib_thick_mm + STACK_CLEARANCE_MM

    def stick_z(self, i: int) -> Tuple[float, float]:
        """(bottom, top) of stick i in Z: front guard on top."""
        top = 0.5 * self.stack_mm
        g = self.guard_thick_mm
        if i == 0:
            return top - g, top
        if i == self.n_sticks - 1:
            return -0.5 * self.stack_mm, -0.5 * self.stack_mm + g
        t0 = top - g - STACK_CLEARANCE_MM - (i - 1) * self.stack_pitch_mm
        return t0 - self.rib_thick_mm, t0'''
assert old in s
s = s.replace(old, new)
old = '''    @property
    def stack_mm(self) -> float:
        return 2 * self.guard_thick_mm + (self.n_sticks - 2) * self.rib_thick_mm'''
new = '''    @property
    def stack_mm(self) -> float:
        return 2 * self.guard_thick_mm + (self.n_sticks - 2) * self.stack_pitch_mm + STACK_CLEARANCE_MM'''
assert old in s
s = s.replace(old, new)
s = s.replace('''D2R = math.pi / 180.0
''', '''D2R = math.pi / 180.0
STACK_CLEARANCE_MM = 0.005
''', 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
