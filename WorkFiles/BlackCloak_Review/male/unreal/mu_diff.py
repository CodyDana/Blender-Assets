import bpy, sys
a, b = sys.argv[sys.argv.index("--")+1:][:2]
A = bpy.data.images.load(a); B = bpy.data.images.load(b)
pa = A.pixels[:]; pb = B.pixels[:]
d = [abs(x - y) for x, y in zip(pa, pb)]
n = sum(1 for k in range(0, len(d), 4) if max(d[k], d[k+1], d[k+2]) > 8/255)
print("DIFF", a.split("/")[-1], b.split("/")[-1], "px>8/255:", n, "of", len(d)//4, "max", round(max(d)*255,1))
