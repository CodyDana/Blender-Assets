import bpy
m=bpy.data.materials['M_BlackCloak_WovenWool']
for n in m.node_tree.nodes:
    s=[(i.name, tuple(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value) for i in n.inputs if not i.is_linked and hasattr(i,'default_value')]
    print("NODE",n.type,n.name,getattr(n,'operation',''),getattr(n,'from_instancer',''),s[:6])
for l in m.node_tree.links: print("LINK",l.from_node.name,l.from_socket.name,'->',l.to_node.name,l.to_socket.name)
