import bpy
c=bpy.data.objects['SKM_BlackCloak_MH']
for s in c.material_slots:
    print("SLOT", s.link, s.material.name if s.material else None)
m=bpy.data.materials['GAME_M_BlackCloak_UV0']
for l in m.node_tree.links: print("LINK", l.from_node.name, l.from_socket.name, '->', l.to_node.name, l.to_socket.name, l.is_valid)
for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE': print("IMG", n.image.name, n.image.filepath, n.image.has_data, n.image.size[:])
print("DATA mats", [x.name if x else None for x in c.data.materials])
