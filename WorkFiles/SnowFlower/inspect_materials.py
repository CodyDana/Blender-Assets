import bpy,json
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\Cody\Desktop\Blender_Projects\Assets\SnowFlower\SnowFlower_Master.blend')
for name in ('M_SnowFlower_Leather','M_SnowFlower_Silk','M_SnowFlower_BlackenedSteel'):
    m=bpy.data.materials[name];p=m.node_tree.nodes.get('Principled BSDF')
    print(name,[(s.name,tuple(s.default_value) if s.type=='RGBA' else s.default_value) for s in p.inputs if s.name in ['Base Color','Metallic','Roughness','Specular IOR Level','Emission Strength','Emission Color']],flush=True)
    print('RAMPS',[(n.name,[(e.position,list(e.color)) for e in n.color_ramp.elements]) for n in m.node_tree.nodes if n.type=='VALTORGB'],flush=True)
    print('LINKS',[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links],flush=True)
