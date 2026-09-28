p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
old = '''    def triangles(self) -> int:
        return len(self.T)'''
new = '''    def triangles(self) -> int:
        return len(self.T)

    def subset(self, keep: Sequence[int]) -> "FanMesh":
        """A compact copy holding only triangles ``keep`` (unused vertices dropped)."""
        out = FanMesh(self.bone_names)
        used = sorted({v for t in keep for v in self.T[t]})
        remap = {v: k for k, v in enumerate(used)}
        out.P = [self.P[v] for v in used]
        out.B = [self.B[v] for v in used]
        if self.W is not None:
            out.W = [self.W[v] for v in used]
        for t in keep:
            out.T.append(tuple(remap[v] for v in self.T[t]))
            for a in ("TUV", "TN", "TS", "TP", "TG", "TL", "TK", "TLAY"):
                getattr(out, a).append(getattr(self, a)[t])
        return out'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_fan.py"
s = open(p, encoding="utf-8").read()
old = '''    front = G.FanMesh(fan[0].bone_names)
    keep = [t for t in range(len(fan[0].T)) if fan[0].TLAY[t] != "back"]
    front.P, front.B = fan[0].P, fan[0].B
    front.T = [fan[0].T[t] for t in keep]
    front.TUV = [fan[0].TUV[t] for t in keep]
    front.TN = [fan[0].TN[t] for t in keep]
    front.TS = [fan[0].TS[t] for t in keep]
'''
new = '''    front = fan[0].subset([t for t in range(len(fan[0].T)) if fan[0].TLAY[t] != "back"])
'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("ok")
