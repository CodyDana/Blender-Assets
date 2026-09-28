import bpy, math, mathutils, numpy as np
FBX=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/BlackCloak.fbx"
TEX=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/"
def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def import_lod0():
    bpy.ops.import_scene.fbx(filepath=FBX)
    return [o for o in bpy.data.objects if o.type=='MESH']
def shipped_materials(objs, uvscale=1.0):
    """Replicates exported MI_Cloak_Black (M_Cloak_Recolor) using the exported textures:
    Base = CloakColor(Black preset) * saturate(BC.R_linear/0.013702083); Rough = T_Roughness.R; Spec 0.08;
    Normal = exported normal (OpenGL copy in Blender == DirectX copy in UE); UV0 with tiling 1.0."""
    m=bpy.data.materials.new("REV_ShippedCloth"); m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links
    bs=next(n for n in N if n.type=='BSDF_PRINCIPLED')
    def img(name,cs):
        t=N.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(TEX+name, check_existing=True); t.image.colorspace_settings.name=cs; return t
    bc=img("T_BlackCloak_BaseColor.png","sRGB"); rg=img("T_BlackCloak_Roughness.png","Non-Color"); nm=img("T_BlackCloak_Normal_OpenGL.png","Non-Color")
    uv=N.new('ShaderNodeUVMap'); uv.uv_map="UVMap"
    vm=N.new('ShaderNodeVectorMath'); vm.operation='SCALE'; vm.inputs['Scale'].default_value=uvscale; L.new(uv.outputs[0],vm.inputs[0])
    for t in (bc,rg,nm): L.new(vm.outputs[0],t.inputs[0])
    sep=N.new('ShaderNodeSeparateColor'); L.new(bc.outputs[0],sep.inputs[0])
    div=N.new('ShaderNodeMath'); div.operation='DIVIDE'; div.use_clamp=True; div.inputs[1].default_value=0.013702083
    L.new(sep.outputs[0],div.inputs[0])
    mul=N.new('ShaderNodeMix'); mul.data_type='RGBA'; mul.blend_type='MULTIPLY'; mul.inputs['Factor'].default_value=1.0
    mul.inputs[6].default_value=(0.013702083,0.01355,0.0134,1); L.new(div.outputs[0],mul.inputs[7])
    L.new(mul.outputs[2],bs.inputs['Base Color'])
    sr=N.new('ShaderNodeSeparateColor'); L.new(rg.outputs[0],sr.inputs[0]); L.new(sr.outputs[0],bs.inputs['Roughness'])
    nmap=N.new('ShaderNodeNormalMap'); nmap.uv_map="UVMap"; L.new(nm.outputs[0],nmap.inputs['Color']); L.new(nmap.outputs[0],bs.inputs['Normal'])
    bs.inputs['Specular IOR Level'].default_value=0.08; bs.inputs['Metallic'].default_value=0.0
    steel=bpy.data.materials.new("REV_Steel"); steel.use_nodes=True; b=steel.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(0.012,0.013,0.012,1); b.inputs['Metallic'].default_value=1; b.inputs['Roughness'].default_value=0.73
    lea=bpy.data.materials.new("REV_Leather"); lea.use_nodes=True; b=lea.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(0.014,0.011,0.008,1); b.inputs['Roughness'].default_value=0.66
    for o in objs:
        for s in o.material_slots:
            n=s.material.name if s.material else ''
            s.material = steel if 'Steel' in n else lea if 'Leather' in n else m
    return m
def bbox(objs):
    pts=np.array([o.matrix_world@mathutils.Vector(c) for o in objs for c in o.bound_box])
    return pts.min(0),pts.max(0)
def camera(target,yaw,pitch,focal,dist):
    cam=bpy.data.cameras.new("REV_Cam"); cam.lens=focal; cam.sensor_fit='VERTICAL'; cam.sensor_height=24
    co=bpy.data.objects.new("REV_Cam",cam); bpy.context.scene.collection.objects.link(co)
    y,p=math.radians(yaw),math.radians(pitch)
    d=mathutils.Vector((math.sin(y)*math.cos(p),-math.cos(y)*math.cos(p),math.sin(p)))*dist
    co.location=mathutils.Vector(target)+d
    co.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera=co; return co
def lights(target):
    sc=bpy.context.scene
    w=bpy.data.worlds.new("REV_World"); sc.world=w; w.use_nodes=True
    bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(1,1,1,1); bg.inputs[1].default_value=0.45
    def area(name,loc,size,power):
        l=bpy.data.lights.new(name,'AREA'); l.shape='RECTANGLE'; l.size=size[0]; l.size_y=size[1]; l.energy=power
        o=bpy.data.objects.new(name,l); sc.collection.objects.link(o); o.location=loc
        o.rotation_euler=(mathutils.Vector(target)-mathutils.Vector(loc)).to_track_quat('-Z','Y').to_euler(); return o
    t=target
    area("REV_Key",(t[0]-1.2,t[1]-3.2,t[2]+1.0),(2.5,2.5),900)
    area("REV_Fill",(t[0]+1.6,t[1]-3.0,t[2]+0.2),(2.5,2.5),450)
