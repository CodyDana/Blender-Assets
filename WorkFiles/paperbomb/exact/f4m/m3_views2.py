import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/f4m")
exec(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/f4m/m3_views.py", encoding="utf8").read().split("# emblem zoom")[0])
for n, (x0, x1, y0, y1, f) in {"dou16": (236, 262, 570, 600, 16), "sealTL16": (38, 60, 492, 512, 16), "sealBR16": (86, 108, 580, 598, 16)}.items():
    ps = panel(x0, x1, y0, y1, f); save(hcat(ps[:3]), OUT+f"m3_zoom_{n}.png")
print("ok")
