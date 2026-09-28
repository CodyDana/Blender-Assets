import bpy, numpy as np
low = bpy.data.objects["SM_SnowFlower_Throat_TP_LOD0"]
mt = low.data.materials[0]
for n in mt.node_tree.nodes:
    if n.type == 'TEX_IMAGE':
        im = n.image
        px = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(im.size[1], im.size[0], 4)
        # sample at face UV centres
        uv = low.data.uv_layers[0].data
        vals = []
        for p in list(low.data.polygons)[::50]:
            u = sum(uv[li].uv.x for li in p.loop_indices) / len(p.loop_indices); v = sum(uv[li].uv.y for li in p.loop_indices) / len(p.loop_indices)
            vals.append(px[int(v * (im.size[1] - 1)), int(u * (im.size[0] - 1)), :3])
        vals = np.array(vals)
        print(im.name, im.colorspace_settings.name, "links->", [l.to_socket.name for l in n.outputs["Color"].links], "pct R", np.percentile(vals[:, 0], [5, 25, 50, 75, 95]).round(3))
