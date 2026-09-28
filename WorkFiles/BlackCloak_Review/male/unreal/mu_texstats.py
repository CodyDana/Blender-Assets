import bpy, sys, json
for p in sys.argv[sys.argv.index("--")+1:]:
    im = bpy.data.images.load(p); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; c = im.channels; px = im.pixels[:]
    step = max(1, (w*h)//200000)
    vals = sorted(px[k] for k in range(0, w*h*c, c*step))
    g = sorted(px[k+1] for k in range(0, w*h*c, c*step))
    pc = lambda a, q: round(a[int(q*(len(a)-1))]*255, 1)
    print("TEX", p.split("/")[-1], w, h, c, "R p1/p50/p99", pc(vals,.01), pc(vals,.5), pc(vals,.99), "G p50", pc(g,.5))
